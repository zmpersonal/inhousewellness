#!/usr/bin/env python3
"""Build a ZIP -> state table so the calculator can resolve a ZIP to an EIA rate.

RUNS IN GITHUB ACTIONS. census.gov is egress-blocked from the agent session.

    python3 scripts/fetch_zip_state.py --out data/zip-to-state.json

SOURCE
US Census Bureau, 2020 ZCTA-to-County national relationship file. Public domain,
no key, one plain-text download, parsed directly -- never through a summarizer.
A county GEOID's first two digits are the state FIPS code, which maps to the USPS
state abbreviation the EIA rate table is keyed on.

THE THING THIS FILE MUST NOT LET ANYONE FORGET: A ZCTA IS NOT A ZIP
A ZIP code is a USPS delivery route. A ZCTA is the Census Bureau's areal
approximation of one. They mostly coincide and they are not the same thing:

  * PO-box-only and single-building "point" ZIPs have NO ZCTA at all. They are
    real ZIPs a customer will type, and they will NOT resolve here.
  * A handful of ZCTAs span two states. Those are recorded with every state they
    touch, not silently assigned to the largest one -- an arbitrary pick would
    be a confident, precise, wrong electricity rate.

So this table answers "which state, if we can tell" and explicitly does not
answer "every ZIP". `unresolvable` is a first-class output, not an error.

AND THE BOUNDARY THAT MUST HOLD
An unresolved ZIP renders a coverage gap. It never falls back to the national
average. cost-tables.json already separates EIA's `US` row and the 10
census-division aggregates into a non-fallback block for exactly this reason;
this file does not undo that by supplying a default here.
"""
import argparse
import json
import pathlib
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
       "tab20_zcta520_county20_natl.txt")

# State FIPS -> USPS. Fixed public reference data, not a derived value. DC is
# included because EIA carries it; the territories are listed so an out-of-scope
# ZIP is recognised as out of scope rather than silently dropped.
FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}
TERRITORY_FIPS = {"60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI"}


def parse(text):
    """Parse the pipe-delimited relationship file. Returns (zcta -> {states}).

    The column layout is read from the HEADER, not assumed by position: a
    fixed index silently reads the wrong column if Census reorders, and the
    result would be a table of confident, wrong states.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header = lines[0].split("|")
    def col(*names):
        for n in names:
            if n in header:
                return header.index(n)
        sys.exit(f"HALT: none of {names} in header {header}. Refusing to guess a "
                 f"column index -- that yields a wrong state per ZIP, silently.")
    zi = col("GEOID_ZCTA5_20", "GEOID_ZCTA520_20", "ZCTA5")
    ci = col("GEOID_COUNTY_20", "GEOID_COUNTY_20 ", "COUNTY")
    out = defaultdict(set)
    for ln in lines[1:]:
        f = ln.split("|")
        if len(f) <= max(zi, ci):
            continue
        z, c = f[zi].strip(), f[ci].strip()
        if not z or not c or len(c) < 2:
            continue
        out[z.zfill(5)].add(c[:2])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/zip-to-state.json")
    ap.add_argument("--source", default=SRC)
    args = ap.parse_args()

    print(f"fetching {args.source}")
    req = urllib.request.Request(args.source, headers={
        "User-Agent": "InHouseWellnessSpecBot/1.0 (+https://inhousewellness.com)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        text = r.read().decode("utf-8", "replace")
    print(f"  {len(text):,} bytes")

    raw = parse(text)
    if len(raw) < 30000:
        # ~33k ZCTAs exist. A short read means a truncated download, and a
        # truncated table would report real ZIPs as unresolvable.
        sys.exit(f"HALT: only {len(raw)} ZCTAs parsed; expected ~33,000. "
                 f"Treating this as a truncated download, not a finding.")

    table, multi, territory = {}, {}, {}
    for z, fips in sorted(raw.items()):
        states = sorted({FIPS[f] for f in fips if f in FIPS})
        terr = sorted({TERRITORY_FIPS[f] for f in fips if f in TERRITORY_FIPS})
        if terr and not states:
            territory[z] = terr
            continue
        if len(states) == 1:
            table[z] = states[0]
        elif len(states) > 1:
            # Recorded with every state it touches. The calculator must ask the
            # customer which, or render a gap -- it must not pick one.
            multi[z] = states

    doc = {
        "schema_version": "1.0.0",
        "built_at": datetime.now(timezone.utc).date().isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": args.source,
        "source_name": "US Census Bureau 2020 ZCTA-to-County relationship file",
        "licence": "public domain (US federal government work)",
        "what_this_is": "ZCTA -> USPS state. A ZCTA is the Census approximation "
                        "of a ZIP code, not the ZIP itself.",
        "unresolvable": {
            "po_box_and_point_zips": "ZIPs with no ZCTA (PO-box-only and "
                                     "single-building ZIPs) are ABSENT from this "
                                     "table by construction. They are real ZIPs a "
                                     "customer will type and they do not resolve.",
            "multi_state_zctas": len(multi),
            "us_territories": len(territory),
            "required_behaviour": "An unresolved ZIP renders a coverage gap. It "
                                  "MUST NOT fall back to the EIA national average "
                                  "or to a census-division aggregate; those are "
                                  "held in a separate non-fallback block in "
                                  "cost-tables.json for this reason.",
        },
        "counts": {
            "single_state_zctas": len(table),
            "multi_state_zctas": len(multi),
            "territory_zctas": len(territory),
            "total_parsed": len(raw),
        },
        "zip_to_state": table,
        "multi_state": multi,
        "territories": territory,
    }
    out = ROOT / args.out
    out.write_text(json.dumps(doc, indent=0, ensure_ascii=False) + "\n")
    size = out.stat().st_size
    print(f"\nwrote {args.out}  {size/1024:.0f} KB")
    print(f"  single-state ZCTAs : {len(table):,}")
    print(f"  multi-state ZCTAs  : {len(multi):,}  (recorded with every state, never picked)")
    print(f"  territory ZCTAs    : {len(territory):,}  (no EIA rate; out of scope)")

    # Cross-check against the rate table actually in use.
    cost = ROOT / "data" / "cost-tables.json"
    if cost.exists():
        rates = json.loads(cost.read_text())["energy"]["rates_cents_per_kwh"]
        missing = sorted({s for s in table.values()} - set(rates))
        print(f"  states in this table with NO EIA rate: {len(missing)} {missing}")


if __name__ == "__main__":
    main()
