#!/usr/bin/env python3
"""INH Verified — read-only map from each record to an InHouse Wellness product (R2-D12).

    .venv/bin/python scripts/verified_inh_map.py --pull     # Admin API, read-only
    .venv/bin/python scripts/verified_inh_map.py            # offline: map from the snapshot

NAVIGATION ONLY. The map says where a reader can see price and availability at
InHouse Wellness. It is written to data/verified/inh-navigation.json, never into a
record, and nothing in it is evidence for any value (CLAUDE.md, editorial
independence). No price is read or stored.

Matching is exact or nothing:
  * a record's manufacturer model number equals one of the product's variant SKUs
    (case- and separator-insensitive), and
  * the product's vendor names the record's brand.
Two products claiming one record, or one product claiming two records, maps nobody:
an ambiguous link is withheld the same way an ambiguous value is. No title or
fuzzy-name matching.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SNAPSHOT = ROOT / "data/verified/internal/inh-products-snapshot.json"
SAUNAS = Path(__import__('os').environ.get('INH_SAUNAS', str(ROOT / 'data/verified/saunas.json')))
OUT = ROOT / "data/verified/inh-navigation.json"

PRODUCTS_Q = """query($after: String) {
  products(first: 100, after: $after, sortKey: ID) {
    nodes { id handle title vendor status productType
      variants(first: 100) { nodes { sku } }
      collections(first: 50) { nodes { handle title } } }
    pageInfo { hasNextPage endCursor } } }"""


def pull() -> dict:
    from verify_theme_asset_path import load_env, gql   # stdlib-only helpers, read-only use
    shop, token = load_env()
    if not (shop and token):
        sys.exit("HALT: no SHOPIFY_SHOP / SHOPIFY_ADMIN_TOKEN; nothing pulled")
    out, after = [], None
    while True:
        page = gql(shop, token, PRODUCTS_Q, {"after": after})["products"]
        for n in page["nodes"]:
            out.append({"id": n["id"], "handle": n["handle"], "title": n["title"], "vendor": n["vendor"],
                        "status": n["status"], "product_type": n["productType"],
                        "skus": sorted({v["sku"] for v in n["variants"]["nodes"] if v["sku"]}),
                        "collections": sorted(({"handle": c["handle"], "title": c["title"]}
                                               for c in n["collections"]["nodes"]), key=lambda c: c["handle"])})
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    from datetime import datetime, timezone
    snap = {"pulled_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source": "Shopify Admin API products query (read-only)",
            "products": sorted(out, key=lambda p: p["handle"])}
    SNAPSHOT.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")
    return snap


def from_census() -> dict:
    """The census rows are the active sauna products of an earlier Admin API pull.
    Collections were not part of that pull, so they are empty here, not guessed."""
    import subprocess
    census = ROOT / "data/own-page-census.json"
    when = subprocess.run(["git", "log", "-1", "--format=%cI", "--", str(census)], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    rows = json.loads(census.read_text())["rows"]
    return {"pulled_at": f"census committed {when}", "source": "data/own-page-census.json (Admin API pull, active sauna products)",
            "products": [{"handle": r["handle"], "title": r["title"], "vendor": r["vendor"], "status": "ACTIVE",
                          "skus": r["skus"], "collections": []} for r in rows]}


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def brand_key(s: str) -> str:
    return norm(re.sub(r"(?i)\b(saunas?|inc|llc|co)\b", "", s))


def catalogue_skus() -> dict:
    """{(host, product handle): [variant SKUs]} from the manufacturer catalogues we have cached."""
    man = json.loads((ROOT / "data/verified/cache-manifest.json").read_text())["entries"]
    out = {}
    for k, e in man.items():
        if "products.json" not in k or not e.get("cache_file"):
            continue
        host = re.sub(r"https?://([^/]+).*", r"\1", k.replace("headless:", ""))
        try:
            for p in json.loads((ROOT / "out/verified/cache" / e["cache_file"]).read_text()).get("products", []):
                out[(host, p["handle"])] = [v.get("sku") for v in p.get("variants", []) if v.get("sku")]
        except (OSError, ValueError):
            continue
    return out


def origin_products(r):
    for u in r.get("provenance", {}).get("origin_urls", []):
        m = re.search(r"https?://([^/]+)/products/([^/?#]+)", u)
        if m:
            yield m.group(1), m.group(2)


def build(snap: dict, records: list) -> dict:
    sku_index: dict[str, list] = {}
    for p in snap["products"]:
        if p["status"] != "ACTIVE":
            continue
        for s in p["skus"]:
            sku_index.setdefault(norm(s), []).append(p)
    claims: dict[str, list] = {}
    reasons: dict[str, str] = {}
    for r in records:
        mn = r["identity"]["model_number"]["value"]
        brand = r["identity"]["brand"]["value"] or ""
        if not mn:
            reasons[r["inh_id"]] = "no verified model number to match on"
            continue
        hits = {}
        for tok in mn.split("|"):
            for p in sku_index.get(norm(tok), []):
                if brand_key(brand) and brand_key(brand) in brand_key(p["vendor"]):
                    hits[p["handle"]] = p
        if len(hits) == 1:
            claims.setdefault(next(iter(hits)), []).append(r["inh_id"])
        elif len(hits) > 1:
            reasons[r["inh_id"]] = "ambiguous: " + ", ".join(sorted(hits))
        else:
            # A store SKU that EXTENDS the model number ("MX-K306-01 CED" for "MX-K306-01") may be
            # a wood or edition variant of it, or a different product. Reported, never mapped.
            ext = sorted({p["handle"] for tok in mn.split("|") for k, ps in sku_index.items()
                          if norm(tok) and k.startswith(norm(tok)) and k != norm(tok) for p in ps
                          if brand_key(brand) and brand_key(brand) in brand_key(p["vendor"])})
            reasons[r["inh_id"]] = ("no exact SKU match; store SKU extends the model number on: " + ", ".join(ext)
                                    if ext else "no active InHouse Wellness product carries this model number")
    # r3-electrical D14 (approved 2026-10-07): a record still unlinked is linked where the MANUFACTURER's
    # own catalogue lists, for the product the record was built from, a variant SKU EXACTLY equal (same
    # normalisation as above) to an active InHouse Wellness product's SKU. One-to-one, as above; both
    # SKUs are logged on the link. No vendor-name test: the catalogue SKU is the manufacturer's own.
    d14 = {}
    claimed = {h for h in claims}
    cat = catalogue_skus()
    for r in records:
        rid = r["inh_id"]
        if any(rid in ids for ids in claims.values()):
            continue
        hits = {}
        for host, h in origin_products(r):
            for msku in cat.get((host, h), []):
                for p in sku_index.get(norm(msku), []):
                    hits[p["handle"]] = (p, msku, next(s for s in p["skus"] if norm(s) == norm(msku)))
        if len(hits) == 1:
            ph, (p, msku, isku) = next(iter(hits.items()))
            if ph not in claimed:
                claims.setdefault(ph, []).append(rid)
                d14[rid] = {"via": "r3 D14: manufacturer catalogue SKU", "manufacturer_sku": msku, "inh_sku": isku,
                            "manufacturer_vendor_note": p["vendor"]}
        elif len(hits) > 1:
            reasons[rid] = "D14 ambiguous: " + ", ".join(sorted(hits))
    by_handle = {p["handle"]: p for p in snap["products"]}
    mapping = {}
    for handle, ids in claims.items():
        if len(ids) > 1:
            for i in ids:
                reasons[i] = f"ambiguous: product {handle} matches {len(ids)} records"
            continue
        p = by_handle[handle]
        mapping[ids[0]] = {"product_handle": handle, "product_title": p["title"],
                           "collections": p["collections"], **d14.get(ids[0], {})}
    return {"note": "Navigation only. Not evidence for any value; never read by the verifier.",
            "snapshot_pulled_at": snap["pulled_at"],
            "mapped": dict(sorted(mapping.items())),
            "unmapped": dict(sorted((k, v) for k, v in reasons.items() if k not in mapping))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--from-census", action="store_true",
                    help="PRELIMINARY: map from data/own-page-census.json (an earlier Admin API pull of the "
                         "165 active sauna products). It carries no collections. Written to a separate file.")
    a = ap.parse_args(argv)
    global OUT
    if a.from_census:
        snap = from_census()
        OUT = OUT.with_name("inh-navigation-preliminary.json")
    else:
        snap = pull() if a.pull else json.loads(SNAPSHOT.read_text())
    recs = [r for r in json.loads(SAUNAS.read_text())["records"] if r["status"] == "published"]
    nav = build(snap, recs)
    OUT.write_text(json.dumps(nav, indent=2, sort_keys=True) + "\n")
    print(f"products in snapshot: {len(snap['products'])}; published records: {len(recs)}; "
          f"mapped: {len(nav['mapped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
