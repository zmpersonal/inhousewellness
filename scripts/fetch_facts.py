#!/usr/bin/env python3
"""Fetch the network's machine-readable datasets into a local fact cache.

Round 4 wrongly concluded the satellites yield no numbers. The failure was the
TOOL: blotato_create_source is an LLM summarizer, not a scraper -- it read prose,
wrote prose, and truthfully reported that its own output contained no numbers.
Several satellites publish data directly.

Parsing these is exact, deterministic, costs zero tokens and carries no
hallucination risk -- strictly better than summarizing for a brand positioned on
published measurements.

`create_source` stays available for PROSE CONTEXT ONLY. It must never source a number.

Usage:  python3 scripts/fetch_facts.py [--force]
"""
import argparse, csv, datetime as dt, io, json, pathlib, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-facts)"}
CACHE = pathlib.Path("data/facts")
MAX_AGE_DAYS = 7

SOURCES = {
    "bhis_saunas": {
        "url": "https://besthomeinfraredsauna.com/data/infrared_saunas.csv",
        "kind": "csv",
        "note": "90 infrared models: dimensions, voltage, amps, watts, EMF claims, price",
    },
    "outdoor_climate": {
        "url": "https://outdoorsteamsauna.com/data/outdoor-sauna-index.csv",
        "kind": "csv",
        "note": "75 US metros: NOAA 1991-2020 normals, EIA rates, cost per 9 kW session",
    },
    "outdoor_cities": {
        "url": "https://outdoorsteamsauna.com/data/cities.json",
        "kind": "json",
        "note": "per-city climate and cost detail",
    },
    "hrd_topics": {
        "url": "https://healthresearchdatabase.com/data/topics.json",
        "kind": "json",
        "note": "normalized research topics",
    },
    "hrd_studies": {
        "url": "https://healthresearchdatabase.com/data/studies.csv",
        "kind": "csv",
        "note": "indexed publications",
    },
}


def get(url, timeout=90):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        if r.status != 200:
            raise SystemExit(f"FAIL: {url} returned HTTP {r.status}")
        return r.read().decode("utf-8", "replace")


def fetch(name, spec, force=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"{name}.json"
    if dest.exists() and not force:
        meta = json.loads(dest.read_text())
        age = (dt.date.today() - dt.date.fromisoformat(meta["fetched_at"][:10])).days
        if age < MAX_AGE_DAYS:
            print(f"  {name:18s} cached ({age}d old, {meta['row_count']} rows)")
            return meta
    body = get(spec["url"])
    if spec["kind"] == "csv":
        rows = list(csv.DictReader(io.StringIO(body)))
    else:
        parsed = json.loads(body)
        rows = parsed if isinstance(parsed, list) else (
            parsed.get("items") or parsed.get("data") or parsed.get("cities") or
            parsed.get("topics") or [parsed])
    meta = {
        "name": name, "url": spec["url"], "note": spec["note"],
        "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "row_count": len(rows),
        "fields": sorted(rows[0].keys()) if rows and isinstance(rows[0], dict) else [],
        "rows": rows,
    }
    dest.write_text(json.dumps(meta, indent=1))
    print(f"  {name:18s} fetched {len(rows)} rows -> {dest}")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    print("fetching network datasets:")
    ok = 0
    for name, spec in SOURCES.items():
        try:
            fetch(name, spec, a.force)
            ok += 1
        except Exception as e:
            # One dataset failing must not take down the others.
            print(f"  {name:18s} FAILED: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(SOURCES)} datasets cached in {CACHE}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
