#!/usr/bin/env python3
"""INH Verified — fetch origin sources into a local cache.

    .venv/bin/python scripts/verified_fetch.py --brands "Redwood Outdoors" "Clearlight"

ONLINE step. Everything downstream (scripts/verified_build.py) reads only the
cache, so verification re-runs offline and deterministically.

Source policy (CLAUDE.md, "Source policy — INH Verified fetching"):
  * robots.txt first, for every host; a disallowed URL is never requested.
  * Crawl-delay is honoured when longer than our own 2-second gap.
  * robots.txt answering 4xx: access allowed (RFC 9309 §2.3.1.3) ONLY for an
    asset host the manufacturer links from its own product/manual pages, and
    only for the files it links. Anywhere else a 4xx robots.txt skips the host.
  * robots.txt answering 5xx or timing out: host skipped.
  * TLS is never bypassed. Retailers are never fetched as evidence.
  * Headless renders (Round 3, approved) follow the same policy: see fetch_rendered().

Cache: out/verified/cache/<sha256-of-url>  (gitignored)
Manifest: data/verified/cache-manifest.json (committed). Every entry records
the robots outcome it was fetched under.
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
sys.path.insert(0, str(ROOT / "scripts"))
CACHE = ROOT / "out/verified/cache"
MANIFEST = ROOT / "data/verified/cache-manifest.json"
SOURCES = ROOT / "data/verified/sources.json"
LEADS = ROOT / "data/verified/internal/leads/infinite-sauna-2026-09-21.json"
UA = "INH-Verified-bot/0.1 (+https://inhousewellness.com; spec verification, 1 req/2s)"
MIN_GAP = 2.0
MAX_BYTES = 60_000_000

_last: dict[str, float] = {}
_gap: dict[str, float] = {}
_robots: dict[str, tuple] = {}


def url_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"entries": {}}


def save_manifest(m: dict, key: str | None = None) -> None:
    """Write the manifest. With `key`, merge ONLY that entry into what is on disk, under an
    exclusive lock: several fetchers (one per host, Round 3) can then run at once without one
    overwriting another's entries."""
    if key is None:
        m["entries"] = dict(sorted(m["entries"].items()))
        MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
        return
    import fcntl
    with open(MANIFEST.with_suffix(".lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        disk = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"entries": {}}
        disk["entries"][key] = m["entries"][key]
        disk["entries"] = dict(sorted(disk["entries"].items()))
        tmp = MANIFEST.with_suffix(".tmp")
        tmp.write_text(json.dumps(disk, indent=2, sort_keys=True) + "\n")
        tmp.replace(MANIFEST)
        m["entries"].update(disk["entries"])


HOSTGAP = ROOT / "out/verified/hostgap"


def polite_wait(host: str) -> None:
    """At most one request per host per gap, ACROSS processes: the last request time for each
    host lives in a lock-protected file, so parallel fetchers (one per brand, Round 3) sharing
    a host such as cdn.shopify.com still respect 1 request every 2 s to it."""
    import fcntl
    gap = max(MIN_GAP, _gap.get(host, 0.0))
    HOSTGAP.mkdir(parents=True, exist_ok=True)
    f = HOSTGAP / re.sub(r"[^A-Za-z0-9.-]", "_", host)
    with open(f, "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        raw = fh.read().strip()
        last = float(raw) if raw else 0.0
        wait = last + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        fh.seek(0)
        fh.truncate()
        fh.write(f"{time.time():.3f}")
    _last[host] = time.monotonic()


def raw_get(url: str):
    host = urllib.parse.urlsplit(url).netloc
    polite_wait(host)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read(MAX_BYTES + 1)
            declared = r.headers.get("Content-Length")
            # A short read is OUR transfer failing, not the publisher's file: Round 1 stored
            # 1,039,467 of 11,490,346 bytes of a manual and pypdf's complaint was then read as
            # the file being broken. Recorded as its own status, never as a 200.
            if declared and declared.isdigit() and len(body) < int(declared) and len(body) <= MAX_BYTES:
                return "TRUNCATED_TRANSFER", f"received {len(body)} of {declared} declared bytes", b"", r.geturl()
            return r.status, r.headers.get("Content-Type", ""), body, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", b"", url
    except Exception as e:  # recorded, never guessed around; TLS failures land here
        return None, f"error: {type(e).__name__}: {e}", b"", url


def robots_for(host: str):
    """(kind, parser) where kind is 'ok' | '4xx' | 'unreadable'."""
    if host in _robots:
        return _robots[host]
    status, ctype, body, _ = raw_get(f"https://{host}/robots.txt")
    if status == 200:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.decode("utf-8", "replace").splitlines())
        delay = rp.crawl_delay(UA) or rp.crawl_delay("*")
        if delay:
            _gap[host] = float(delay)
        _robots[host] = ("ok", rp)
    elif status is not None and 400 <= status < 500:
        _robots[host] = ("4xx", status)
    else:
        _robots[host] = ("unreadable", status if status is not None else ctype)
    return _robots[host]


def fetch(url: str, manifest: dict, refresh: bool = False, linked_asset: bool = False, own_site: bool = False) -> dict:
    ent = manifest["entries"].get(url)
    if ent and not refresh and (ent["status"] != 200 or (CACHE / ent.get("cache_file", "-")).exists()):
        return ent
    host = urllib.parse.urlsplit(url).netloc
    kind, rp = robots_for(host)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if kind == "ok" and not rp.can_fetch(UA, url):
        ent = {"status": "ROBOTS_DISALLOWED", "fetched_at": now, "robots": "disallowed"}
    elif kind == "4xx" and not (linked_asset or own_site):
        ent = {"status": "ROBOTS_4XX_NOT_AN_ORIGIN_HOST", "fetched_at": now,
               "robots": f"robots.txt answered {rp}; host is neither the manufacturer's own site nor a linked asset host"}
    elif kind == "unreadable":
        ent = {"status": "ROBOTS_UNREADABLE", "fetched_at": now, "robots": f"robots.txt: {rp}"}
    else:
        status, ctype, body, final = raw_get(url)
        ent = {"status": status if status is not None else ctype, "content_type": ctype if status else "",
               "fetched_at": now, "final_url": final,
               "robots": "allowed" if kind == "ok" else
                         (f"robots.txt answered {rp}: allowed for a manufacturer-linked asset (RFC 9309, B1-D2)" if linked_asset else
                          f"robots.txt answered {rp}: allowed on the manufacturer's own site (RFC 9309, final-batch decision)")}
        if status == 200:
            if len(body) > MAX_BYTES:
                ent["status"] = "TOO_LARGE"
                ent["note"] = f"exceeds our own {MAX_BYTES}-byte cap; not the source's defect"
            else:
                CACHE.mkdir(parents=True, exist_ok=True)
                (CACHE / url_key(url)).write_bytes(body)
                ent.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), cache_file=url_key(url))
    manifest["entries"][url] = ent
    save_manifest(manifest, url)
    print(f"  {str(ent['status']):>4}  {url}", flush=True)
    return ent


RENDER_WAIT_MS = 2500


def rendered_key(url: str) -> str:
    """Cache key for a HEADLESS render of `url`. Distinct from the static fetch of the same URL:
    the two are different evidence and both are kept."""
    return "headless:" + url


def fetch_rendered(url: str, manifest: dict, browser, refresh: bool = False, own_site: bool = True) -> dict:
    """Round 3 (approved): fetch a page with a headless browser, under the SAME policy as fetch().

      * robots.txt for the page's host decides first, exactly as for a static fetch; and every
        same-host subresource the page requests is checked against that robots.txt too, and
        aborted when disallowed.
      * one page render per host per MIN_GAP (or Crawl-delay), via the same polite_wait().
      * images, media and fonts are never requested; the user agent is ours.
      * the rendered DOM is cached with its sha256 and fetch time; the manifest entry records
        method "headless". The build reads only the cache, so rebuilds stay byte-identical.
    """
    key = rendered_key(url)
    ent = manifest["entries"].get(key)
    if ent and not refresh and (ent["status"] != 200 or (CACHE / ent.get("cache_file", "-")).exists()):
        return ent
    host = urllib.parse.urlsplit(url).netloc
    kind, rp = robots_for(host)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if kind == "ok" and not rp.can_fetch(UA, url):
        ent = {"status": "ROBOTS_DISALLOWED", "fetched_at": now, "robots": "disallowed", "method": "headless"}
    elif kind == "4xx" and not own_site:
        ent = {"status": "ROBOTS_4XX_NOT_AN_ORIGIN_HOST", "fetched_at": now, "method": "headless",
               "robots": f"robots.txt answered {rp}"}
    elif kind == "unreadable":
        ent = {"status": "ROBOTS_UNREADABLE", "fetched_at": now, "robots": f"robots.txt: {rp}", "method": "headless"}
    else:
        polite_wait(host)
        blocked, same_host = [], []
        ctx = browser.new_context(user_agent=UA, java_script_enabled=True)
        page = ctx.new_page()

        def route(r):
            req = r.request
            if req.resource_type in ("image", "media", "font", "stylesheet"):
                return r.abort()
            h = urllib.parse.urlsplit(req.url).netloc
            if h == host and kind == "ok" and not rp.can_fetch(UA, req.url):
                blocked.append(req.url)
                return r.abort()
            if h == host and req.url != url:
                polite_wait(host)          # every same-host request counts against the per-host gap
                same_host.append(req.url)
            return r.continue_()
        page.route("**/*", route)
        try:
            resp = page.goto(url, wait_until="load", timeout=300000)
            page.wait_for_timeout(RENDER_WAIT_MS)
            status = resp.status if resp else None
            body = page.content().encode("utf-8")
            final = page.url
        except Exception as e:  # recorded, never guessed around
            status, body, final = f"error: {type(e).__name__}: {str(e)[:120]}", b"", url
        finally:
            ctx.close()
        ent = {"status": status, "fetched_at": now, "final_url": final, "method": "headless",
               "robots": "allowed" if kind == "ok" else f"robots.txt answered {rp}: allowed on the manufacturer's own site",
               "subresources_blocked_by_robots": len(blocked), "same_host_subrequests": len(same_host)}
        if status == 200:
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / url_key(key)).write_bytes(body)
            ent.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), cache_file=url_key(key),
                       content_type="text/html; rendered")
    manifest["entries"][key] = ent
    save_manifest(manifest, key)
    print(f"  {str(ent['status']):>4}  [headless] {url}", flush=True)
    return ent


def main(argv=None):
    import verified_build as vb   # discovery + matching live in one place, shared with the build
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", nargs="+", required=True, help="lead-list brand names")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--refresh-discovery", action="store_true",
                    help="re-fetch ONLY catalogue/sitemap discovery pages (r3 D11: fetch only what is needed)")
    ap.add_argument("--only-matched", action="store_true",
                    help="fetch product pages only for products matched to a lead (r3 D11)")
    a = ap.parse_args(argv)
    sources = json.loads(SOURCES.read_text())
    leads = json.loads(LEADS.read_text())["products"]
    for extra in sorted(LEADS.parent.glob("inh-priced-r3-*.json")):   # r3-electrical D6/D11 identity leads
        leads += json.loads(extra.read_text())["products"]
    manifest = load_manifest()

    for brand in a.brands:
        src = sources["brands"][brand]
        domain = src["manufacturer_domains"][0]
        brand_leads = [r for r in leads if r["brand"] == brand]
        print(f"== {brand} ({domain}, discovery={src['discovery']})", flush=True)
        # 1. discovery
        if src.get("blocked"):
            print(f"   BLOCKED: {src['blocked']}", flush=True)
            continue
        own = lambda u: urllib.parse.urlsplit(u).netloc in src["manufacturer_domains"]
        rd = a.refresh or a.refresh_discovery
        for url in vb.discovery_urls(src, brand_leads, manifest_reader(manifest)):
            fetch(url, manifest, rd, own_site=own(url))
        if src["discovery"] == "catalogue":
            page = 1
            while True:
                url = vb.catalogue_url(domain, page)
                ent = fetch(url, manifest, rd, own_site=True)
                if ent["status"] != 200:
                    break
                if len(json.loads((CACHE / ent["cache_file"]).read_bytes())["products"]) < 250:
                    break
                page += 1
        cache = vb.Cache(manifest_override=manifest)
        products = vb.products_for(cache, brand, src, brand_leads)
        matched, _ = vb.match_leads(src, brand_leads, products)
        print(f"   products: {len(products)}, matched to leads: {len(matched)}", flush=True)
        # 2. rendered product pages where the adapter reads the page layout
        if src["adapter"] in ("shopify_html", "html_page"):
            want = (list(products.values()) if src.get("fetch_all_product_pages", src.get("link_attach", True))
                    and not a.only_matched else [products[h] for h in matched])
            for p in sorted(want, key=lambda p: p.url):
                fetch(p.url, manifest, a.refresh, own_site=True)
            for extra in src.get("extra_urls", []):
                fetch(extra, manifest, a.refresh, own_site=own(extra))
        # 3. PDFs the manufacturer links from the matched products' own pages
        cache = vb.Cache(manifest_override=manifest)
        products = vb.products_for(cache, brand, src, brand_leads)
        links = set()
        for h in matched:
            links |= vb.pdf_links(cache, src, products[h])
        print(f"   PDFs linked from matched product pages on origin asset hosts: {len(links)}", flush=True)
        for u in sorted(links):
            fetch(u, manifest, a.refresh, linked_asset=True)
    return 0


def manifest_reader(manifest):
    def read(url):
        e = manifest["entries"].get(url)
        if not e or e.get("status") != 200:
            return None
        return (CACHE / e["cache_file"]).read_bytes()
    return read


if __name__ == "__main__":
    sys.exit(main())
