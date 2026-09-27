#!/usr/bin/env python3
"""INH Verified — fetch origin sources into a local cache.

    .venv/bin/python scripts/verified_fetch.py --brands "Golden Designs Inc" "Salus Saunas"

ONLINE step. Everything downstream (scripts/verified_build.py) reads only the
cache, so verification re-runs offline and deterministically.

Rules, each from the round brief:
  * robots.txt is read first for every host, and a URL it disallows is never
    requested. An unreadable robots.txt means the host is skipped: stricter than
    RFC 9309, same stance as scripts/fetch_manufacturer_specs (see CLAUDE.md).
  * At most one request every 2 seconds per host.
  * The user agent says who we are.
  * Only origin hosts are fetched: the brand's own domain from
    data/verified/sources.json. Retailers, including inhousewellness.com, are
    never fetched as evidence.

Cache: out/verified/cache/<sha256-of-url>  (gitignored, large)
Manifest: data/verified/cache-manifest.json  (committed: url -> sha256, bytes,
status, fetched_at). Re-running skips URLs already cached unless --refresh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "out/verified/cache"
MANIFEST = ROOT / "data/verified/cache-manifest.json"
SOURCES = ROOT / "data/verified/sources.json"
LEADS = ROOT / "data/verified/internal/leads/infinite-sauna-2026-09-21.json"
UA = "INH-Verified-bot/0.1 (+https://inhousewellness.com; spec verification, 1 req/2s)"
MIN_GAP = 2.0
MAX_BYTES = 60_000_000

_last: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def url_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"entries": {}}


def save_manifest(m: dict) -> None:
    m["entries"] = dict(sorted(m["entries"].items()))
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def polite_wait(host: str) -> None:
    gap = time.monotonic() - _last.get(host, 0.0)
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    _last[host] = time.monotonic()


def raw_get(url: str):
    host = urllib.parse.urlsplit(url).netloc
    polite_wait(host)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read(MAX_BYTES + 1)
            return r.status, r.headers.get("Content-Type", ""), body, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", b"", url
    except Exception as e:  # network failure is recorded, never guessed around
        return None, f"error: {type(e).__name__}: {e}", b"", url


def robots_for(host: str):
    if host in _robots:
        return _robots[host]
    status, _, body, _ = raw_get(f"https://{host}/robots.txt")
    if status != 200:
        _robots[host] = None
    else:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.decode("utf-8", "replace").splitlines())
        _robots[host] = rp
    return _robots[host]


def fetch(url: str, manifest: dict, refresh: bool = False) -> dict:
    ent = manifest["entries"].get(url)
    if ent and not refresh and (ent["status"] != 200 or (CACHE / ent["cache_file"]).exists()):
        return ent
    host = urllib.parse.urlsplit(url).netloc
    rp = robots_for(host)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if rp is None:
        ent = {"status": "ROBOTS_UNREADABLE", "fetched_at": now}
    elif not rp.can_fetch(UA, url):
        ent = {"status": "ROBOTS_DISALLOWED", "fetched_at": now}
    else:
        status, ctype, body, final = raw_get(url)
        ent = {"status": status, "content_type": ctype, "fetched_at": now, "final_url": final}
        if status == 200:
            if len(body) > MAX_BYTES:
                ent["status"] = "TOO_LARGE"
                ent["note"] = f"exceeds our own {MAX_BYTES}-byte cap; not the source's defect"
            else:
                sha = hashlib.sha256(body).hexdigest()
                CACHE.mkdir(parents=True, exist_ok=True)
                (CACHE / url_key(url)).write_bytes(body)
                ent.update(sha256=sha, bytes=len(body), cache_file=url_key(url))
    manifest["entries"][url] = ent
    save_manifest(manifest)
    print(f"  {ent['status']:>4}  {url}")
    return ent


def shopify_catalog(domain: str, manifest: dict, refresh: bool) -> list[str]:
    urls = []
    for page in range(1, 20):
        url = f"https://{domain}/products.json?limit=250&page={page}"
        ent = fetch(url, manifest, refresh)
        urls.append(url)
        if ent["status"] != 200:
            break
        prods = json.loads((CACHE / ent["cache_file"]).read_bytes())["products"]
        if len(prods) < 250:
            break
    return urls


def catalog_products(urls, manifest):
    out = []
    for u in urls:
        ent = manifest["entries"].get(u, {})
        if ent.get("status") == 200:
            out += json.loads((CACHE / ent["cache_file"]).read_bytes())["products"]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", nargs="+", required=True, help="lead-list brand names")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    sources = json.loads(SOURCES.read_text())
    leads = json.loads(LEADS.read_text())["products"]
    manifest = load_manifest()

    for brand in a.brands:
        src = sources["brands"][brand]
        domain = src["manufacturer_domains"][0]
        print(f"== {brand} ({domain})")
        cat_urls = shopify_catalog(domain, manifest, a.refresh)
        prods = catalog_products(cat_urls, manifest)
        print(f"   catalogue: {len(prods)} products")
        # Product pages: HTML where the adapter needs the rendered specs panel.
        if src["adapter"] == "shopify_html_disclosure":
            handles = set()
            brand_leads = [r for r in leads if r["brand"] == brand]
            by_sku = {re.sub(r"[^A-Z0-9]", "", (v.get("sku") or "").upper()): p["handle"]
                      for p in prods for v in p["variants"] if v.get("sku")}
            for r in brand_leads:
                h = by_sku.get(re.sub(r"[^A-Z0-9]", "", r["model"].upper()))
                if not h:
                    for u in r["source_urls"]:
                        if urllib.parse.urlsplit(u).netloc.endswith(domain.replace("www.", "")):
                            h = urllib.parse.urlsplit(u).path.rstrip("/").split("/")[-1]
                if h:
                    handles.add(h)
            for h in sorted(handles):
                fetch(f"https://{domain}/products/{h}", manifest, a.refresh)
        # Manufacturer pages that index manuals or name partners/dealers.
        texts = [p.get("body_html") or "" for p in prods]
        for path in src.get("extra_paths", []):
            ent = fetch(f"https://{domain}{path}", manifest, a.refresh)
            if ent.get("status") == 200:
                texts.append((CACHE / ent["cache_file"]).read_bytes().decode("utf-8", "replace"))
        for ent in list(manifest["entries"].items()):
            u, e = ent
            if u.startswith(f"https://{domain}/products/") and e.get("status") == 200 and "cache_file" in e:
                texts.append((CACHE / e["cache_file"]).read_bytes().decode("utf-8", "replace"))
        # PDFs the manufacturer itself hosts, linked from its own pages.
        pdfs = sorted({m.replace("&amp;", "&") for t in texts for m in re.findall(
            r'(?:https?:)?//[^\s"\'<>]+?\.pdf(?:\?[^\s"\'<>]*)?', t, re.I)})
        pdfs = sorted({("https:" + u) if u.startswith("//") else u for u in pdfs})
        own = [u for u in pdfs if urllib.parse.urlsplit(u).netloc in src["pdf_hosts"]]
        print(f"   PDFs linked from the manufacturer's own pages: {len(pdfs)} ({len(own)} on its own hosts)")
        for u in own:
            fetch(u, manifest, a.refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
