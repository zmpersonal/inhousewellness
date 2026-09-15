#!/usr/bin/env python3
"""Emit the two JSON theme assets the True Total Cost calculator reads.

WHY THE STOREFRONT GETS ITS OWN PAYLOAD RATHER THAN data/cost-tables.json
`data/cost-tables.json` is 369 KB of provenance, per-field reasons and rejected
readings -- the right shape for a human auditing a figure, the wrong shape for a
page a customer loads on a phone. This script projects it down to what the
calculator actually reads, and **carries the provenance of every figure it
keeps**, because the page prints source and fetch date beside each number.

Nothing is invented here. A field that `cost-tables.json` records as null with a
reason arrives as null WITH THAT REASON, so the page can say why a line is
missing instead of rendering a blank or a zero.

THE ZIP TABLE IS RANGE-COMPRESSED, AND THE COMPRESSION IS PROVED LOSSLESS
33,505 ZCTAs as a flat object is ~470 KB. As sorted [start, end, state] ranges it
is a fraction of that and binary-searchable. The risk in compressing a lookup is
that a RANGE SWALLOWS A GAP: a ZIP that legitimately does not resolve starts
resolving to its neighbour's state, which is this project's oldest failure shape
wearing a new hat. So `--self-test` replays all 33,505 keys through the
compressed form AND asserts a sample of known-absent ZIPs still misses.

    python3 scripts/build_storefront_assets.py
    python3 scripts/build_storefront_assets.py --self-test
"""
import argparse
import json
import pathlib
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

SCHEMA_VERSION = "1.0.0"

# The session the published article computes with, and its source. Carried as
# DATA so the page can cite it, and so a change lands in one place rather than
# in a call site. inh-seo/content/articles/true-total-cost-home-sauna.md,
# published 2026-09-09: "Three 45-minute sessions a week, every week of the
# year" and "kilowatts x hours x sessions per week x your state's rate".
SESSION = {
    "minutes_default": 45,
    "sessions_per_week_default": 3,
    "weeks_per_year": 52,
    "formula": "kW x hours x sessions per week x weeks x state rate",
    "source": "inhousewellness.com/blogs/saunas/true-total-cost-home-sauna",
    "published": "2026-09-09",
    "note": "Session length is a READER INPUT defaulting to 45 minutes. A longer "
            "preheat is the reader's fact about their own room, not a climate "
            "model we hold a source for.",
}


def compress(zip_to_state):
    """[[start, end, state], ...] over an integer ZIP space, sorted by start.

    Only CONSECUTIVE integers in the SAME state are merged. A gap of even one
    ZIP ends the range, so an absent ZIP stays absent -- that is the whole point.
    """
    items = sorted((int(z), s) for z, s in zip_to_state.items())
    out = []
    for z, s in items:
        if out and out[-1][2] == s and z == out[-1][1] + 1:
            out[-1][1] = z
        else:
            out.append([z, z, s])
    return out


def lookup(ranges, zipcode):
    """Binary search, mirroring exactly what the browser does. Returns the state
    or None. Kept here so the self-test exercises the same algorithm."""
    try:
        n = int(zipcode)
    except (TypeError, ValueError):
        return None
    lo, hi = 0, len(ranges) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b, s = ranges[mid]
        if n < a:
            hi = mid - 1
        elif n > b:
            lo = mid + 1
        else:
            return s
    return None


def build_zip_asset():
    src = json.loads((DATA / "zip-to-state.json").read_text())
    ranges = compress(src["zip_to_state"])
    return {
        "schema_version": SCHEMA_VERSION,
        "built_at": date.today().isoformat(),
        "source": src["source"],
        "source_name": src["source_name"],
        "fetched_at": src["fetched_at"],
        "what_this_is": src["what_this_is"],
        "counts": dict(src["counts"], ranges=len(ranges)),
        "unresolvable": src["unresolvable"],
        "ranges": ranges,
        # Kept as their own maps, NOT merged into ranges. A multi-state ZCTA has
        # two answers and a territory has none in the EIA dataset; folding either
        # into the lookup would turn "we cannot say" into a confident answer.
        "multi_state": src["multi_state"],
        "territories": src["territories"],
    }, src


def manual_urls():
    """Product handle -> a manual URL we have actually READ.

    Only rows the run-10 extraction resolved to a parseable PDF. 5 of the 142
    Drive embeds serve a Google sign-in page and 1 is a 404, and offering a
    reader a link we know is broken is worse than offering none.
    """
    p = DATA / "facts" / "manual_specs.json"
    if not p.exists():
        return {}, "data/facts/manual_specs.json absent", None
    doc = json.loads(p.read_text())
    out = {}
    for r in doc["rows"]:
        if r.get("status") != "OK":
            continue
        url = r.get("final_url") or r.get("pdf_url")
        if url:
            out.setdefault(r["handle"], url)
    return out, None, doc["fetched_at"]


def field(f):
    """A cost-tables cell, projected. Value AND provenance, or null AND reason."""
    if f.get("value") is None:
        return {"v": None, "reason": f.get("reason"), "detail": f.get("detail")}
    return {"v": f["value"], "src": f.get("source"), "at": f.get("fetched_at"),
            "span": f.get("span"), "unit": f.get("unit")}


def build_cost_asset():
    ct = json.loads((DATA / "cost-tables.json").read_text())
    manuals, manual_note, manual_at = manual_urls()
    products = []
    for r in ct["rows"]:
        price = r["fields"]["price_usd"]
        if price.get("value") is None:
            continue          # not priced = not sellable = not offered as a choice
        kw = field(r["fields"]["rated_power_kw"])
        products.append({
            "h": r["handle"], "t": r["title"], "u": r["url"],
            "price": field(price), "kw": kw,
            # Volts / amps / dedicated-circuit travel with the SKU because the
            # "do I already have the right circuit?" question is answered by what
            # the unit needs, and the reader takes that to their electrician. They
            # are never multiplied together: 240V x 30A is the BREAKER's capacity,
            # and there is no code anywhere in this round that derives kW from it.
            "volts": field(r["fields"]["volts"]),
            "amps": field(r["fields"]["amps"]),
            "dedicated": field(r["fields"]["dedicated_circuit_required"]),
            "type": r["fields"]["type"].get("value"),
            "io": r["fields"]["indoor_outdoor"].get("value"),
            "manual": manuals.get(r["handle"]),
        })
    products.sort(key=lambda p: p["t"])
    with_kw = sum(1 for p in products if p["kw"]["v"] is not None)
    energy = ct["energy"]
    return {
        "schema_version": SCHEMA_VERSION,
        "built_at": date.today().isoformat(),
        "built_from": f"data/cost-tables.json built_at {ct['built_at']}",
        "scope": ct["scope"],
        "freight": ct["freight"],
        "energy": {
            "source": energy["source"],
            "dataset": energy["dataset"],
            "fetched_at": energy["fetched_at"],
            "latest_period": energy["latest_period"],
            "granularity": energy["granularity"],
            "rates_cents_per_kwh": energy["rates_cents_per_kwh"],
            "territories_not_covered": energy["territories_not_covered"],
            # Shipped so the methodology page can PRINT them and say why they are
            # not used. Held under their own key, never in the rates map, so no
            # lookup can reach them by accident.
            "non_fallback_reference": energy["national_and_regional_reference"],
        },
        "session": SESSION,
        "manuals": {"count": len(manuals), "fetched_at": manual_at,
                    "note": manual_note or
                    "only manuals the run-10 extraction fetched and parsed; "
                    "sign-in pages and one dead Drive id are deliberately absent"},
        "coverage": {
            "priced_skus": len(products),
            "with_rated_power_kw": with_kw,
            "with_rated_power_pct": round(100.0 * with_kw / len(products), 1),
            "without_rated_power": len(products) - with_kw,
            "manual_pdfs_read": 142, "manual_pages_read": 3569,
            "note": "rated power is the majority-absent field. The calculator "
                    "treats its absence as a designed state, not an error.",
        },
        "products": products,
    }


def self_test():
    fails = []
    zip_asset, src = build_zip_asset()
    ranges, flat = zip_asset["ranges"], src["zip_to_state"]

    # 1. LOSSLESS: every key resolves to the same state through the compressed form.
    wrong = [z for z, s in flat.items() if lookup(ranges, z) != s]
    if wrong:
        fails.append(f"compression lost {len(wrong)} ZIP(s), e.g. {wrong[:5]}")

    # 2. NO SWALLOWED GAPS: a ZIP absent from the table must stay absent. These
    #    are real US ZIP prefixes with no ZCTA -- exactly the PO-box and
    #    point-ZIP case the source file warns about.
    absent = [z for z in ("00001", "09999", "20599", "34999", "99999", "56999")
              if z not in flat]
    if not absent:
        fails.append("the known-absent control found nothing absent to test with")
    for z in absent:
        if lookup(ranges, z) is not None:
            fails.append(f"a range swallowed the gap at {z} -> {lookup(ranges, z)}")

    # 3. A multi-state ZCTA must NOT resolve through the single-state lookup.
    for z in list(src["multi_state"])[:20]:
        if lookup(ranges, z) is not None:
            fails.append(f"multi-state ZCTA {z} resolved to one state "
                         f"({lookup(ranges, z)}); it has two")

    # 4. A territory must NOT resolve: the EIA dataset has no row for it.
    for z in list(src["territories"])[:20]:
        if lookup(ranges, z) is not None:
            fails.append(f"territory ZCTA {z} resolved to {lookup(ranges, z)}")

    # 5. Non-numeric and short input must not throw and must not resolve.
    for bad in ("", "abc", "0100", None, "01001-1234"):
        if lookup(ranges, bad) is not None:
            fails.append(f"malformed ZIP {bad!r} resolved")

    # 6. The non-fallback aggregates must be unreachable from the rates map.
    cost = build_cost_asset()
    rates = cost["energy"]["rates_cents_per_kwh"]
    for k in cost["energy"]["non_fallback_reference"]["values"]:
        if k in rates:
            fails.append(f"census/national aggregate {k} is inside the rates map")
    if "US" in rates:
        fails.append("the EIA US row is reachable as if it were a state")

    # 7. Every product carries either a value or a reason -- never a bare null.
    for p in cost["products"]:
        for name in ("price", "kw"):
            cell = p[name]
            if cell["v"] is None and not cell.get("reason"):
                fails.append(f"{p['h']}.{name} is null with no reason")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out-dir", default="assets")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: storefront assets failed their own controls:\n  "
                     + "\n  ".join(fails))
        print("storefront assets self-test: ZIP compression is lossless, no gap "
              "is swallowed, and no national aggregate is reachable as a state")
        return

    out = ROOT / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    zip_asset, src = build_zip_asset()
    cost = build_cost_asset()
    (out / "inh-zip-state.json").write_text(json.dumps(zip_asset, separators=(",", ":")) + "\n")
    (out / "inh-cost-tables.json").write_text(json.dumps(cost, separators=(",", ":")) + "\n")

    zb = (out / "inh-zip-state.json").stat().st_size
    cb = (out / "inh-cost-tables.json").stat().st_size
    print(f"assets/inh-zip-state.json    {zb/1024:8.1f} KB   "
          f"{src['counts']['single_state_zctas']:,} ZCTAs -> "
          f"{len(zip_asset['ranges']):,} ranges")
    print(f"assets/inh-cost-tables.json  {cb/1024:8.1f} KB   "
          f"{len(cost['products'])} priced SKUs, "
          f"{cost['coverage']['with_rated_power_kw']} with kW "
          f"({cost['coverage']['with_rated_power_pct']}%)")
    print(f"\nZIP resolution coverage")
    print(f"  single-state ZCTAs resolvable : {src['counts']['single_state_zctas']:,}")
    print(f"  multi-state, deliberately not : {src['counts']['multi_state_zctas']}")
    print(f"  US territories, no EIA row    : {src['counts']['territory_zctas']}")
    print(f"  PO-box / point ZIPs           : absent from the source by "
          f"construction; they render a coverage gap")
    print(f"  manual links offered          : {cost['manuals']['count']} products")


if __name__ == "__main__":
    main()
