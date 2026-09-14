#!/usr/bin/env python3
"""Build data/cost-tables.json -- the dataset the True Total Cost calculator reads.

SCOPE: active sauna SKUs only. Cold plunge, steam generators and float tanks are
out of launch scope (Round 1 ruling 4) -- they matched 0% of the spec table, and a
calculator that silently covers them would be inventing their inputs.

WHAT IS DELIBERATELY ABSENT
No installation figure. No electrician estimate. No BLS-derived range, no default,
no midpoint. Round 1 ruling 1: electrical cost is a READER INPUT, taken from their
own electrician's quote, and Build Brief v2 section 5's BLS-OEWS range is void.
Ruling 3: the $1,800 covers InHouse's delivery and assembly only, and third-party
electrician labour is never summed into it. So this file carries freight and
energy, and stops.

HOW POWER IS READ, AND THE ONE THING NEVER DONE
`rated_power_kw` is only ever taken from a figure a source STATES. It is NEVER
derived from the circuit:

    240V x 30A = 7.2kW is the BREAKER's capacity, not the heater's rating.

Heaters are sized below their breaker, so that multiplication yields a number that
is precise, confident and wrong -- and it would land directly in the running-cost
line, which is the one number the competing SERP already gets wrong. Every SKU
whose sources state volts and amps but no power rating is therefore null with
reason POWER_NOT_STATED, even though the arithmetic is right there. A null means
the calculator declines to compute running cost for that model, which is correct.

TWO BASES, NOT ONE, AND THEY ARE LABELLED
A traditional cabin states a heater rating in kW ("8 kW Harvia"). An infrared
cabin states a rated draw in watts ("Power Consumption: 1750W"). For a kWh
calculation these are the same physical quantity -- rated draw -- but they are
NOT the same field in the sources, and a reader checking our number needs to know
which was used. Every value carries `basis`, either `traditional_heater_kw` or
`infrared_rated_watts`, plus the verbatim span it was read from.

SOURCE PRECEDENCE (Round 1 ruling 5: metafields outrank satellite CSVs)
    1. manufacturer websites   -- UNAVAILABLE, see the report; egress-blocked
    2. custom.electrical_requirements, then custom.dimentions_specifications
    3. product body, then product title (derived copy, flagged as such)
    4. satellite CSVs (infinite_saunas heater_kw)
A satellite value is never allowed to overwrite a metafield value; it only fills a
hole. And where BHIS agrees with the catalogue that is ONE source counted twice,
not corroboration -- 84 of its 90 rows were sourced from InHouse itself.
"""
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "cost-tables.json"
SCHEMA_VERSION = "1.0.0"
BUILT_AT = "2026-09-14"

# ---- reason codes ----------------------------------------------------------
POWER_NOT_STATED = "POWER_NOT_STATED"        # sources give volts/amps but no rating
NO_SOURCE = "NO_SOURCE"                       # nothing carries the field
POWER_CONFLICT = "POWER_CONFLICT"             # sources state different ratings
CONFIGURABLE = "RATING_DEPENDS_ON_CONFIGURATION"  # e.g. 6kW stove fitted, 8kW optional
MULTI_CIRCUIT = "MULTIPLE_CIRCUITS_STATED"    # e.g. 240V stove + 120V lighting
IMPLAUSIBLE = "IMPLAUSIBLE_RATING"            # outside PLAUSIBLE_KW: a parse failure
VOLTS_CONFLICT = "VOLTS_CONFLICT"
DUAL_MODE = "DUAL_MODE_TWO_RATINGS"           # combo unit: IR and traditional both stated

# ---- patterns. Each requires an explicit unit adjacent to the number. -------
KW_RX = re.compile(r"(\d{1,3}(?:\.\d{1,2})?)\s*k\.?\s*w\b", re.I)
# Thousands separators are MANDATORY here. Without the comma alternative,
# "1,800 watts" matched only "800" and produced a 0.8 kW sauna; "2,200 watts"
# produced 0.2 kW. Both parsed cleanly, passed every structural check, and would
# have gone straight into the running-cost line as a precise, confident, false
# number. The plausibility band below is the guard that catches the class.
W_RX = re.compile(r"(\d{1,2},\d{3}|\d{3,5})\s*(?:w\b|watts\b)", re.I)
# A home sauna's rated draw. Anything outside this is a parse failure or a
# figure about something else, and is refused rather than emitted.
PLAUSIBLE_KW = (0.8, 30.0)
V_RX = re.compile(r"(\d{3})\s*v\b", re.I)
A_RX = re.compile(r"(\d{1,3}(?:\.\d)?)\s*(?:a\b|amp|amps|amperage)", re.I)
# "Dedicated ... required" is a requirement; "recommended" is not. The two must
# not collapse into one boolean -- that would turn advice into a spec.
DED_REQ_RX = re.compile(r"dedicated[^.;]{0,40}(required|require)", re.I)
DED_REC_RX = re.compile(r"dedicated[^.;]{0,40}recommended", re.I)
# "120V / 20AMP dedicated circuit." states the requirement without the word
# "required". Matching only on "required" missed it and left the field null on a
# SKU whose source says plainly what it needs. Ordered AFTER the "recommended"
# check so advice is never promoted into a specification.
DED_NOUN_RX = re.compile(r"dedicated\s+(?:\d{1,3}\s*-?\s*amp\s+)?(?:non-\w+\s+)?"
                         r"(?:circuit|receptacle|breaker|outlet)", re.I)
# Contexts where a wattage is NOT the cabin's rated draw.
W_EXCLUDE = re.compile(r"per panel|each panel|bulb|light|speaker|chromotherapy", re.I)


def text_of(node):
    if node.get("type") == "text":
        return node.get("value", "")
    return "".join(text_of(c) for c in node.get("children", []))


def plain(value):
    """Rich-text JSON -> plain text. Non-JSON values pass through."""
    if value is None or value == "":
        return ""
    try:
        return text_of(json.loads(value))
    except (ValueError, TypeError):
        return str(value)


def strip_html(s):
    return re.sub(r"<[^>]+>", " ", s or "")


def span_around(text, match, pad=70):
    lo, hi = max(0, match.start() - pad), min(len(text), match.end() + pad)
    return re.sub(r"\s+", " ", text[lo:hi]).strip()


def read_kw(text, field):
    """Stated heater kW. Returns a list of readings; never derives."""
    out = []
    for m in KW_RX.finditer(text):
        out.append({"kw": float(m.group(1)), "basis": "traditional_heater_kw",
                    "source_field": field, "span": span_around(text, m)})
    return out


def read_watts(text, field):
    """Stated rated draw in watts. Returns a list of readings; never derives."""
    out = []
    for m in W_RX.finditer(text):
        sp = span_around(text, m)
        if W_EXCLUDE.search(sp):
            continue
        out.append({"kw": round(float(m.group(1).replace(",", "")) / 1000.0, 3),
                    "basis": "infrared_rated_watts",
                    "source_field": field, "span": sp})
    return out


def read_scalar(text, field, rx, key):
    out = []
    for m in rx.finditer(text):
        out.append({key: float(m.group(1)), "source_field": field,
                    "span": span_around(text, m)})
    return out


def cell(value, source, span, fetched_at, **extra):
    d = {"value": value, "source": source, "span": span, "fetched_at": fetched_at}
    d.update(extra)
    return d


def gap(reason, detail=None):
    d = {"value": None, "reason": reason}
    if detail is not None:
        d["detail"] = detail
    return d


def pick(readings, key):
    """Collapse readings to one value, or report a conflict. Never averages.

    Readings are already in precedence order, so the first distinct value wins
    ONLY when every reading agrees or the disagreement is between a
    higher-precedence source and a lower one. Two readings of equal precedence
    that disagree are a conflict, not a vote.
    """
    if not readings:
        return None, None
    vals = [r[key] for r in readings]
    distinct = sorted(set(vals))
    if len(distinct) == 1:
        return readings[0], None
    # Same field disagreeing with itself, or two metafields disagreeing.
    top_field = readings[0]["source_field"]
    same_field = [r for r in readings if r["source_field"] == top_field]
    if len({r[key] for r in same_field}) > 1:
        return None, distinct
    return readings[0], distinct


def load_products(files, active):
    seen = {}
    for f in files:
        doc = json.loads(pathlib.Path(f).read_text())
        for n in doc["data"]["products"]["nodes"]:
            h = n["handle"]
            if h in seen:
                continue
            elec = n["elec"] if n["elec"] is not None else {}
            dims = n["dims"] if n["dims"] is not None else {}
            seen[h] = {
                "handle": h,
                "title": n["title"],
                "body": strip_html(n["descriptionHtml"]),
                "elec": plain(elec["value"]) if "value" in elec else "",
                "elec_updated": elec["updatedAt"] if "updatedAt" in elec else None,
                "dims": plain(dims["value"]) if "value" in dims else "",
            }
    missing = sorted(set(active) - set(seen))
    if missing:
        sys.exit(f"HALT: {len(missing)} ACTIVE sauna SKUs were not covered by the "
                 f"pull, so any coverage figure would be computed on an incomplete "
                 f"population: {missing}")
    return {h: r for h, r in seen.items() if h in active}


def main():
    active = set(json.loads((ROOT / "data" / "active-sauna-handles.json").read_text()))
    files = sys.argv[1:]
    prods = load_products(files, active)

    spec = json.loads((DATA / "spec-table.json").read_text())
    spec_by = {r["shopify_handle"]: r for r in spec["rows"]}
    snap = json.loads((DATA / "shopify-catalog-snapshot-2026-09-14.json").read_text())
    snap_by = {p["handle"]: p for p in snap["products"]}
    shop_at = snap["fetched_at"]
    freight = json.loads((DATA / "freight-tiers.json").read_text())
    inf = json.loads((DATA / "facts" / "infinite_saunas.json").read_text())
    inf_at = inf["fetched_at"]
    inf_kw = {}
    for r in inf["rows"]:
        u = r["inhouse_url"]
        if not u or "/products/" not in u:
            continue
        h = u.split("/products/")[-1].split("?")[0].strip("/").lower()
        raw = r["heater_kw"]
        if raw is not None and str(raw).strip():
            m = KW_RX.search(str(raw))
            if m:
                inf_kw[h] = (float(m.group(1)), str(raw))

    rows = []
    for h in sorted(prods):
        p = prods[h]
        mf_at = p["elec_updated"] if p["elec_updated"] is not None else shop_at
        # Precedence: elec metafield, dims metafield, body, title.
        sources = [(p["elec"], "custom.electrical_requirements", mf_at),
                   (p["dims"], "custom.dimentions_specifications", shop_at),
                   (p["body"], "product_body", shop_at),
                   (p["title"], "product_title", shop_at)]

        kw_reads, w_reads, v_reads, a_reads = [], [], [], []
        for text, field, at in sources:
            if not text:
                continue
            for r in read_kw(text, field):
                r["fetched_at"] = at
                kw_reads.append(r)
            for r in read_watts(text, field):
                r["fetched_at"] = at
                w_reads.append(r)
            for r in read_scalar(text, field, V_RX, "volts"):
                r["fetched_at"] = at
                v_reads.append(r)
            for r in read_scalar(text, field, A_RX, "amps"):
                r["fetched_at"] = at
                a_reads.append(r)

        row = {"handle": h, "title": p["title"],
               "url": f"https://inhousewellness.com/products/{h}", "fields": {}}
        F = row["fields"]

        sp = spec_by[h] if h in spec_by else None
        sn = snap_by[h] if h in snap_by else None

        # --- price ---------------------------------------------------------
        if sn is not None and sn["variants"] and sn["variants"][0]["price"] is not None:
            F["price_usd"] = cell(float(sn["variants"][0]["price"]), "shopify-admin-api",
                                  None, shop_at, unit="USD")
        else:
            F["price_usd"] = gap(NO_SOURCE)

        # --- rated power ----------------------------------------------------
        combined = kw_reads + w_reads
        if not combined and h in inf_kw:
            val, raw = inf_kw[h]
            F["rated_power_kw"] = cell(val, "infinitesauna.com/data/saunas.csv", raw,
                                       inf_at, unit="kW", basis="traditional_heater_kw",
                                       precedence_tier=4,
                                       note="satellite fill; no metafield, body or title stated a rating")
        elif kw_reads and w_reads:
            # A combo cabin stating both an IR draw and a stove rating. Which one
            # applies depends on the mode the owner runs, and we do not know that.
            F["rated_power_kw"] = gap(DUAL_MODE,
                                      f"both stated: traditional {sorted({r['kw'] for r in kw_reads})} kW "
                                      f"and infrared {sorted({r['kw'] for r in w_reads})} kW")
            F["rated_power_readings"] = combined
        elif combined:
            chosen, conflict = pick(combined, "kw")
            if chosen is None:
                # "6 kW stove included, 8 kW optional upgrade" is a configurable
                # product, not two sources contradicting each other. Calling it a
                # conflict would send a human to adjudicate a question that has no
                # single answer; the rating genuinely depends on what was ordered.
                joined = " ".join(r["span"] for r in combined).lower()
                cfg = re.search(r"option(al)?|upgrade|or 8|compatible with", joined)
                F["rated_power_kw"] = gap(CONFIGURABLE if cfg else POWER_CONFLICT,
                                          f"sources state {conflict} kW")
                F["rated_power_readings"] = combined
            elif not (PLAUSIBLE_KW[0] <= chosen["kw"] <= PLAUSIBLE_KW[1]):
                F["rated_power_kw"] = gap(
                    IMPLAUSIBLE,
                    f"read {chosen['kw']} kW from {chosen['source_field']}, outside the "
                    f"{PLAUSIBLE_KW[0]}-{PLAUSIBLE_KW[1]} kW band a home sauna occupies. "
                    f"Treated as a parse failure, not a measurement. Span: {chosen['span']!r}")
            else:
                F["rated_power_kw"] = cell(chosen["kw"], chosen["source_field"], chosen["span"],
                                           chosen["fetched_at"], unit="kW", basis=chosen["basis"])
                if conflict:
                    F["rated_power_kw"]["also_reported"] = conflict
        else:
            F["rated_power_kw"] = gap(
                POWER_NOT_STATED,
                "sources state no kW or wattage rating. NOT derived from volts x amps: "
                "that is the breaker's capacity, not the heater's rating.")

        # --- volts / amps ---------------------------------------------------
        cv, vconf = pick(v_reads, "volts")
        if cv is not None:
            F["volts"] = cell(cv["volts"], cv["source_field"], cv["span"], cv["fetched_at"], unit="V")
            if vconf:
                F["volts"]["also_reported"] = vconf
        elif vconf:
            # A cabin listing "240V / 30AMP (stove)" and "120V / 15AMP (lighting)"
            # is not contradicting itself -- it has two circuits. Recording that as
            # a conflict would send a human to resolve a disagreement that does not
            # exist; picking the larger silently would assert a spec nobody stated.
            F["volts"] = gap(MULTI_CIRCUIT, f"distinct circuits stated: {vconf} V")
            F["volts_circuits_stated"] = v_reads
        else:
            F["volts"] = gap(NO_SOURCE)
        ca, aconf = pick(a_reads, "amps")
        F["amps"] = (cell(ca["amps"], ca["source_field"], ca["span"], ca["fetched_at"], unit="A")
                     if ca else gap(NO_SOURCE))
        if ca and aconf:
            F["amps"]["also_reported"] = aconf

        # --- dedicated circuit ----------------------------------------------
        ded = None
        for text, field, at in sources:
            if not text:
                continue
            m = DED_REQ_RX.search(text)
            if m:
                ded = cell(True, field, span_around(text, m), at)
                break
            m = DED_REC_RX.search(text)
            if m:
                # Recommended is not required. Recorded as its own state so the
                # calculator cannot read advice as a specification.
                ded = cell(False, field, span_around(text, m), at,
                           qualifier="recommended_not_required")
                break
            m = DED_NOUN_RX.search(text)
            if m:
                ded = cell(True, field, span_around(text, m), at,
                           qualifier="stated_as_a_noun_phrase_not_the_word_required")
                break
        F["dedicated_circuit_required"] = ded if ded else gap(NO_SOURCE)

        # --- type / placement, from the committed spec table -----------------
        for out_key, spec_key in (("type", "type"), ("indoor_outdoor", "indoor_outdoor")):
            if sp is not None and sp["fields"][spec_key]["value"] is not None:
                f = sp["fields"][spec_key]
                F[out_key] = cell(f["value"], f["source"], None, f["fetched_at"])
            else:
                F[out_key] = gap(NO_SOURCE)
        rows.append(row)

    # ---- energy --------------------------------------------------------------
    eia = json.loads((DATA / "facts" / "eia_electricity.json").read_text())
    latest = max(r["period"] for r in eia["rows"])
    # EIA mixes 50 states + DC with 10 census-division aggregates and a national
    # 'US' row in the same column. They are SEPARATED here, not merged: a ZIP
    # never resolves to 'ENC', and leaving 'US' among the states is an invitation
    # to quietly fall back to the national average for an uncovered location --
    # the silent interpolation this project forbids. An uncovered ZIP must render
    # an honest gap instead.
    AGGREGATES = {"US", "ENC", "ESC", "MAT", "MTN", "NEW", "PACC", "PACN",
                  "SAT", "WNC", "WSC"}
    by_state, reference = {}, {}
    for r in eia["rows"]:
        if r["period"] != latest or r["price_cents_kwh"] in (None, ""):
            continue
        target = reference if r["state"] in AGGREGATES else by_state
        target[r["state"]] = float(r["price_cents_kwh"])

    def cov(f):
        n = sum(1 for r in rows if r["fields"][f]["value"] is not None)
        return {"populated": n, "of": len(rows), "pct": round(100 * n / len(rows), 1)}

    doc = {
        "schema_version": SCHEMA_VERSION,
        "built_at": BUILT_AT,
        "scope": "active Shopify products of productType 'Sauna'",
        "row_count": len(rows),
        "excluded_by_ruling": {
            "installation_cost": "NOT PUBLISHED. Reader input from their own electrician's "
                                 "quote (ruling 1). No estimate, range or default appears in "
                                 "this file, and none may be added downstream.",
            "electrician_labour": "third-party, never summed into freight (ruling 3)",
            "cold_plunge_steam_float": "out of launch scope (ruling 4)",
        },
        "freight": {
            "basis": "three flat tiers, not weight-derived (ruling 2)",
            "source": "data/freight-tiers.json",
            "fetched_at": freight["inh_own_charges"]["tiers"][0]["fetched_at"],
            "tiers": [{"tier": t["tier"], "usd": t["price_usd"], "source_type": t["source_type"]}
                      for t in freight["inh_own_charges"]["tiers"]],
        },
        "energy": {
            "source": eia["url"],
            "dataset": "EIA residential electricity price, state x month",
            "fetched_at": eia["fetched_at"],
            "latest_period": latest,
            "granularity": "state",
            "zip_resolution": None,
            "zip_resolution_reason": "NO_ZIP_TO_STATE_TABLE_IN_REPO -- the calculator must "
                                     "map ZIP to state itself; this file does not invent one",
            "states_covered": len(by_state),
            "states_expected": 51,
            "jurisdiction_coverage_pct": round(100 * len(by_state) / 51, 1),
            "territories_not_covered": "Puerto Rico and other US territories have no EIA "
                                       "row in this dataset and are an honest gap, not a "
                                       "case for substituting a national figure",
            "rates_cents_per_kwh": by_state,
            "national_and_regional_reference": {
                "values": reference,
                "DO_NOT_USE_AS_FALLBACK": "These are census-division and national "
                                          "aggregates. They exist for methodology "
                                          "reference only. Using one for an uncovered "
                                          "location would be interpolation presented as "
                                          "a local rate.",
            },
        },
        "coverage": {f: cov(f) for f in
                     ("price_usd", "rated_power_kw", "volts", "amps",
                      "dedicated_circuit_required", "type", "indoor_outdoor")},
        "null_reasons": dict(Counter(
            r["fields"][f]["reason"] for r in rows for f in r["fields"]
            if isinstance(r["fields"][f], dict) and r["fields"][f].get("value", "x") is None
            and "reason" in r["fields"][f]).most_common()),
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    size = OUT.stat().st_size
    print(f"wrote {OUT.relative_to(ROOT)}  rows={len(rows)}  size={size/1024:.1f} KB")
    print("\ncoverage (of 165 active sauna SKUs):")
    for f, c in doc["coverage"].items():
        print(f"  {f:28s} {c['populated']:3d}/{c['of']}  {c['pct']:5.1f}%")
    print("\nnull reasons:", doc["null_reasons"])
    print(f"\nenergy: {len(by_state)} states at period {latest}, EIA fetched {eia['fetched_at'][:10]}")
    basis = Counter(r["fields"]["rated_power_kw"].get("basis")
                    for r in rows if r["fields"]["rated_power_kw"]["value"] is not None)
    print("power basis:", dict(basis))


if __name__ == "__main__":
    main()
