#!/usr/bin/env python3
"""r3-electrical D3 (approved 2026-10-07): a manual linked from OUR product page counts only when it is
byte-identical (sha256) to a copy on the manufacturer's own host, and then the MANUFACTURER's URL is
cited, never ours.

    .venv/bin/python scripts/r3_ownpage_hash.py            # download + hash, match against the cache
    .venv/bin/python scripts/r3_ownpage_hash.py --match    # re-match only (after new manufacturer fetches)

Scope: manuals on the pages of priced INH saunas that have no live record. Downloads go to
out/verified/r3-ownpage/ (not committed), one request every 2 s, honest user agent. Nothing from our
pages is ever used as evidence by this script: it only proves identity with a manufacturer copy.
Writes data/verified/r3/ownpage-manual-hashes.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out/verified/r3-ownpage"
RESULT = ROOT / "data/verified/r3/ownpage-manual-hashes.json"
UA = "InHouseWellness-verified/1.0 (+https://inhousewellness.com; manual identity check)"


def scope_handles() -> set[str]:
    d = json.loads((ROOT / "assets/inh-electrical-data.json").read_text())
    return {p["handle"] for p in d["unmapped_inh_products"]}


def manufacturer_hashes() -> dict[str, str]:
    m = json.loads((ROOT / "data/verified/cache-manifest.json").read_text())["entries"]
    return {e["sha256"]: k.replace("headless:", "") for k, e in m.items() if e.get("sha256") and e.get("cache_file")}


def on_brand_host(url: str, vendor: str) -> bool:
    import urllib.parse
    reg = json.loads((ROOT / "data/verified/sources.json").read_text())["brands"]
    cfg = reg.get(vendor) or next((c for b, c in reg.items() if vendor.lower().split()[0] in b.lower()), None)
    if not cfg:
        return False
    u = urllib.parse.urlsplit(url)
    hosts = set(cfg.get("manufacturer_domains", [])) | set(cfg.get("pdf_hosts", []))
    if u.netloc == "cdn.shopify.com":
        prefix = cfg.get("pdf_path_prefix")
        return bool(prefix) and u.path.startswith(prefix)
    return u.netloc in hosts


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", action="store_true")
    a = ap.parse_args(argv)
    rows = [r for r in json.loads((ROOT / "data/facts/manual_specs.json").read_text())["rows"]
            if r.get("status") == "OK" and r["handle"] in scope_handles()]
    prev = json.loads(RESULT.read_text())["manuals"] if RESULT.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    out = {}
    for r in rows:
        key = r["file_id"]
        rec = prev.get(key, {"file_id": key, "handles": [], "vendor": r["vendor"]})
        rec["handles"] = sorted(set(rec["handles"]) | {r["handle"]})
        f = OUT / f"{key}.pdf"
        if not a.match and not f.exists():
            req = urllib.request.Request(r["final_url"], headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    b = resp.read(120_000_001)
                rec["download"] = {"status": resp.status, "bytes": len(b), "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
                if b[:4] == b"%PDF" and len(b) <= 120_000_000:
                    f.write_bytes(b)
            except Exception as ex:
                rec["download"] = {"error": f"{type(ex).__name__}: {ex}"[:200]}
            time.sleep(2)
        if f.exists():
            rec["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        out[key] = rec
    mh = manufacturer_hashes()
    for rec in out.values():
        u = mh.get(rec["sha256"]) if rec.get("sha256") else None   # no hash (download failed): no match, never a guess
        # The copy must sit on THIS brand's own registered host. The first run matched a Golden Designs
        # page's file to a Harvia heater manual on Salus's Shopify store: identical bytes on another
        # company's host prove nothing about who published it.
        ok = bool(u) and on_brand_host(u, rec["vendor"])
        rec["manufacturer_copy"] = u if ok else None
        rec["identical_copy_elsewhere"] = u if (u and not ok) else None
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps({"_comment": __doc__.strip().splitlines()[0], "checked": datetime.now(timezone.utc).date().isoformat(),
                                  "manuals": dict(sorted(out.items()))}, indent=1, ensure_ascii=False) + "\n")
    matched = [r for r in out.values() if r.get("manufacturer_copy")]
    print(f"{len(out)} our-page manuals in scope; {sum(1 for r in out.values() if r.get('sha256'))} hashed; "
          f"{len(matched)} byte-identical to a cached manufacturer copy")
    for r in matched:
        print(f"  {r['vendor']:20} {','.join(r['handles'])[:60]:60} -> {r['manufacturer_copy']}")


if __name__ == "__main__":
    main()
