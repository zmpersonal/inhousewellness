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
ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "facts"
MAX_AGE_DAYS = 7

# Free public APIs, added Round 10. No key required for any of these.
# Licence note: all are US federal or CC0/ODbL open data and permit
# redistribution of derived figures with attribution, which the card's source
# line carries. Recorded here so it is not re-litigated per probe.
API_SOURCES = {
    "cpsc_recalls": {
        "urls": [
            "https://www.saferproducts.gov/RestWebServices/Recall?format=json&ProductName=sauna",
            "https://www.saferproducts.gov/RestWebServices/Recall?format=json&ProductName=heater",
            "https://www.saferproducts.gov/RestWebServices/Recall?format=json&ProductName=infrared",
            "https://www.saferproducts.gov/RestWebServices/Recall?format=json&ProductName=hot%20tub",
        ],
        "kind": "json-list",
        "note": "CPSC recalls for sauna, heater, infrared and hot tub products. "
                "Nobody in this category publishes this.",
        "licence": "US federal government work, public domain",
    },
    "openalex_topics": {
        "urls": [
            "https://api.openalex.org/works?filter=title_and_abstract.search:sauna&"
            "group_by=publication_year",
            "https://api.openalex.org/works?filter=title_and_abstract.search:"
            "cold%20water%20immersion&group_by=publication_year",
        ],
        "kind": "openalex-group",
        "note": "Scholarly volume by year for sauna and cold-water immersion.",
        "licence": "CC0",
    },
    "clinical_trials": {
        "urls": [
            "https://clinicaltrials.gov/api/v2/studies?query.term=sauna&pageSize=200",
            "https://clinicaltrials.gov/api/v2/studies?query.term=cold%20water%20immersion&pageSize=200",
        ],
        "kind": "ctgov",
        "note": "Trials studying heat therapy and cold immersion right now.",
        "licence": "US federal government work, public domain",
    },
    "fda_device_events": {
        "urls": [
            "https://api.fda.gov/device/event.json?search=device.generic_name:"
            "%22infrared%22&count=device.generic_name.exact&limit=50",
            "https://api.fda.gov/device/event.json?search=device.generic_name:"
            "%22heating%22&count=device.generic_name.exact&limit=50",
        ],
        "kind": "openfda-count",
        "note": "Device adverse-event counts for infrared and heating devices.",
        "licence": "openFDA, public domain (not for clinical decisions)",
    },
}

# Keyed sources. The fetcher is built and wired; it SKIPS when the key is absent
# and says so, rather than failing the run or silently returning nothing.
KEYED_SOURCES = {
    "eia_electricity": {
        "env": "EIA_API_KEY", "kind": "eia", "host": "api.eia.gov",
        "why": "electricity rates including historical trend",
        "url": ("https://api.eia.gov/v2/electricity/retail-sales/data/"
                "?frequency=monthly&data[0]=price&facets[sectorid][]=RES"
                "&start=2015-01&sort[0][column]=period&sort[0][direction]=desc"
                "&length=5000&api_key={key}"),
        "note": "US residential electricity price by state and month, 2015 onward.",
        "licence": "US federal government work, public domain",
    },
    "census_housing": {
        "env": "CENSUS_API_KEY", "kind": "census", "host": "api.census.gov",
        "why": "housing stock: home size, detached share, recent construction",
        "url": ("https://api.census.gov/data/2023/acs/acs1"
                "?get=NAME,B25041_001E,B25024_002E,B25034_002E&for=state:*&key={key}"),
        "note": "Housing stock by state: units, detached share, recent construction.",
        "licence": "US federal government work, public domain",
    },
    "fred_series": {
        "env": "FRED_API_KEY", "kind": "fred", "host": "fred.stlouisfed.org",
        "why": "electricity price and home-improvement spend over time",
        "url": ("https://api.stlouisfed.org/fred/series/observations"
                "?series_id=APU000072610&file_type=json&observation_start=2015-01-01"
                "&api_key={key}"),
        "note": "US average electricity price per kWh, monthly since 2015.",
        "licence": "FRED terms permit derived figures with attribution",
    },
}


def _key_for(env_name):
    """Environment first, then .env at the REPO ROOT -- never the cwd.

    CI has no .env; the six secrets arrive as environment variables there.
    """
    import os
    val = (os.environ.get(env_name) or "").strip()
    if val:
        return val
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    return (dotenv_values(ROOT / ".env").get(env_name) or "").strip() or None


def _rows_keyed(kind, body):
    j = json.loads(body)
    if kind == "eia":
        return [{"period": r.get("period"), "state": r.get("stateid"),
                 "state_name": r.get("stateDescription"),
                 "price_cents_kwh": r.get("price")}
                for r in j.get("response", {}).get("data", [])]
    if kind == "census":
        if not isinstance(j, list) or len(j) < 2:
            return []
        head, *rows = j
        return [dict(zip(head, r)) for r in rows]
    if kind == "fred":
        return [{"date": o.get("date"), "value": o.get("value")}
                for o in j.get("observations", []) if o.get("value") not in (".", None)]
    return []


def fetch_keyed(name, spec, force=False):
    key = _key_for(spec["env"])
    if not key:
        print(f"  {name:18s} SKIPPED — {spec['env']} not set "
              f"({spec['host']}: {spec['why']})")
        return None
    dest = CACHE / f"{name}.json"
    if dest.exists() and not force:
        meta = json.loads(dest.read_text())
        age = (dt.date.today() - dt.date.fromisoformat(meta["fetched_at"][:10])).days
        if age < MAX_AGE_DAYS:
            print(f"  {name:18s} cached ({age}d old, {meta['row_count']} rows)")
            return meta
    rows = _rows_keyed(spec["kind"], get(spec["url"].format(key=key)))
    meta = {"name": name, "url": spec["url"].split("&api_key")[0].split("&key=")[0],
            "note": spec["note"], "licence": spec.get("licence"),
            "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "row_count": len(rows),
            "fields": sorted(rows[0].keys()) if rows and isinstance(rows[0], dict) else [],
            "rows": rows}
    CACHE.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(meta, indent=1))
    print(f"  {name:18s} fetched {len(rows)} rows -> {dest}")
    return meta

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
    "infinite_saunas": {
        "url": "https://infinitesauna.com/data/saunas.csv",
        "kind": "csv",
        "note": "190 models: 88 Traditional, 77 Infrared, 25 Hybrid, with heater "
                "kW, voltage, amperage, capacity and dimensions. This is the "
                "traditional/steam side the infrared-only index was missing.",
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


def _rows_from(kind, body):
    """Normalise each API's envelope into a flat list of dicts."""
    j = json.loads(body)
    if kind == "json-list":
        return j if isinstance(j, list) else []
    if kind == "openalex-group":
        return [{"year": g.get("key"), "works": g.get("count")}
                for g in j.get("group_by", []) if str(g.get("key", "")).isdigit()]
    if kind == "ctgov":
        out = []
        for st in j.get("studies", []):
            pr = st.get("protocolSection", {})
            ident, status = pr.get("identificationModule", {}), pr.get("statusModule", {})
            design = pr.get("designModule", {})
            out.append({
                "nct_id": ident.get("nctId"),
                "title": (ident.get("briefTitle") or "")[:220],
                "status": status.get("overallStatus"),
                "start": (status.get("startDateStruct") or {}).get("date"),
                "phase": ",".join(design.get("phases") or []),
                "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
                "type": design.get("studyType"),
            })
        return out
    if kind == "openfda-count":
        return [{"term": r.get("term"), "count": r.get("count")}
                for r in j.get("results", [])]
    return []


def fetch_api(name, spec, force=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"{name}.json"
    if dest.exists() and not force:
        meta = json.loads(dest.read_text())
        age = (dt.date.today() - dt.date.fromisoformat(meta["fetched_at"][:10])).days
        if age < MAX_AGE_DAYS:
            print(f"  {name:18s} cached ({age}d old, {meta['row_count']} rows)")
            return meta
    rows, seen = [], set()
    for url in spec["urls"]:
        try:
            body = get(url)
        except Exception as e:
            print(f"  {name:18s} one endpoint failed: {type(e).__name__}")
            continue
        for r in _rows_from(spec["kind"], body):
            key = json.dumps(r, sort_keys=True)
            if key not in seen:
                seen.add(key)
                rows.append(r)
    meta = {"name": name, "url": spec["urls"][0], "note": spec["note"],
            "licence": spec.get("licence"),
            "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "row_count": len(rows),
            "fields": sorted(rows[0].keys()) if rows and isinstance(rows[0], dict) else [],
            "rows": rows}
    dest.write_text(json.dumps(meta, indent=1))
    print(f"  {name:18s} fetched {len(rows)} rows -> {dest}")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="",
                    help="comma-separated dataset names; blank = all. Unknown "
                         "names are an error, not a silent no-op -- a typo that "
                         "quietly fetched nothing would look like a clean run.")
    a = ap.parse_args()
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    known = set(SOURCES) | set(API_SOURCES) | set(KEYED_SOURCES)
    unknown = only - known
    if unknown:
        raise SystemExit(f"HALT: unknown dataset name(s) {sorted(unknown)}. "
                         f"Known: {sorted(known)}")
    print("fetching network datasets:")
    ok = 0
    for name, spec in SOURCES.items():
        if only and name not in only:
            continue
        try:
            fetch(name, spec, a.force)
            ok += 1
        except Exception as e:
            # One dataset failing must not take down the others.
            print(f"  {name:18s} FAILED: {type(e).__name__}: {e}")
    print("\nfetching free public APIs:")
    for name, spec in API_SOURCES.items():
        if only and name not in only:
            continue
        try:
            fetch_api(name, spec, a.force)
            ok += 1
        except Exception as e:
            # One API failing must not take down the others.
            print(f"  {name:18s} FAILED: {type(e).__name__}: {e}")

    print("\nkeyed APIs:")
    missing = []
    for name, spec in KEYED_SOURCES.items():
        if only and name not in only:
            continue
        try:
            if fetch_keyed(name, spec, a.force):
                ok += 1
            else:
                missing.append((spec["env"], spec["host"], spec["why"]))
        except Exception as e:
            print(f"  {name:18s} FAILED: {type(e).__name__}: {e}")

    total = len(SOURCES) + len(API_SOURCES) + len(KEYED_SOURCES)
    print(f"\n{ok}/{total} datasets cached in {CACHE}")
    if missing:
        print("\nSKIPPED — add these to .env at the repo root, one line each:")
        for env, host, why in missing:
            print(f"  {env:16s} {host:26s} {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
