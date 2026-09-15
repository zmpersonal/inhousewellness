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
    1. MANUFACTURER MANUAL     -- data/facts/manual_specs.json. The manufacturer's
       own document, reached through the Drive link on OUR product page, so it
       works even for vendors whose hosts are unreadable.
    2. manufacturer website    -- UNAVAILABLE: every product_url_template is still
       null, so data/facts/manufacturer_specs.json does not exist. The tier is
       wired and empty, not skipped.
    3. custom.electrical_requirements, then custom.dimentions_specifications
    4. product body, then product title (derived copy, flagged as such)
    5. satellite CSVs (infinite_saunas heater_kw)
A higher tier never silently overwrites a lower one: where they differ, BOTH
values and BOTH spans are recorded on the field and a human decides.
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
MANUAL_SUPPLY_SPEC_ONLY = "MANUAL_SUPPLY_SPEC_ONLY"   # the manual states volts/amps, never a wattage
MANUAL_AMBIGUOUS = "MANUAL_AMBIGUOUS"        # a line-wide manual states ratings for several models
NO_SOURCE = "NO_SOURCE"                       # nothing carries the field
POWER_CONFLICT = "POWER_CONFLICT"             # sources state different ratings
CONFIGURABLE = "RATING_DEPENDS_ON_CONFIGURATION"  # e.g. 6kW stove fitted, 8kW optional
MULTI_CIRCUIT = "MULTIPLE_CIRCUITS_STATED"    # e.g. 240V stove + 120V lighting
IMPLAUSIBLE = "IMPLAUSIBLE_RATING"            # outside PLAUSIBLE_KW: a parse failure
VOLTS_CONFLICT = "VOLTS_CONFLICT"
DUAL_MODE = "DUAL_MODE_TWO_RATINGS"           # combo unit: IR and traditional both stated

# ---- patterns and guards: ONE definition, in src/power_parse.py ------------
# Imported rather than restated so the manufacturer fetcher added in Round 1b
# and this builder cannot drift apart about what a valid rating is. The two
# guards that caught real bugs (comma-aware wattage, and the plausibility band)
# live there with the evidence that produced them.
sys.path.insert(0, str(ROOT))
from src.power_parse import (  # noqa: E402
    KW_RX, W_RX, V_RX, A_RX, W_EXCLUDE, PLAUSIBLE_KW,
    span_around, read_kw, read_watts, read_scalar, read_dedicated_circuit,
    self_test as power_self_test,
)

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
    # ---- tier 1: manufacturer specs, when the Actions fetcher has run --------
    # Absent file = tier 1 simply unavailable. It is NOT an error and NOT an
    # empty result: "we have not fetched" and "the manufacturer states nothing"
    # are different facts and are reported differently.
    mfg_path = DATA / "facts" / "manufacturer_specs.json"
    mfg, mfg_at = {}, None
    if mfg_path.exists():
        mdoc = json.loads(mfg_path.read_text())
        mfg_at = mdoc["fetched_at"]
        for r in mdoc["rows"]:
            if r["status"] != "OK":
                continue
            reads = r["readings"]["kw"]
            if reads:
                mfg[r["handle"]] = {"readings": reads, "final_url": r["final_url"],
                                    "volts": r["readings"]["volts"],
                                    "amps": r["readings"]["amps"],
                                    "dedicated": r["readings"]["dedicated_circuit"]}

    # TIER 1: the manufacturer's own manual. Keyed by handle; a manual shared
    # across a product line is flagged, because a figure in a line-wide document
    # cannot be attributed to one SKU without the span naming the model.
    man_path = DATA / "facts" / "manual_specs.json"
    man, man_at = {}, None
    man_stats = {"pdfs": 0, "ok": 0, "needs_ocr": 0, "with_reading": 0,
                 "supply_spec_only": 0, "rejected_readings": 0}
    if man_path.exists():
        mdoc = json.loads(man_path.read_text())
        man_at = mdoc["fetched_at"]
        man_stats["pdfs"] = len(mdoc["rows"])
        man_stats["needs_ocr"] = mdoc.get("needs_ocr", 0)
        for r in mdoc["rows"]:
            if r.get("status") != "OK":
                continue
            man_stats["ok"] += 1
            man_stats["rejected_readings"] += len(r.get("rejected", []))
            reads = r.get("readings") or []
            entry = man.setdefault(r["handle"], {
                "readings": [], "rejected": [], "urls": [], "shared": False,
                "elec_terms": set()})
            entry["readings"] += reads
            entry["rejected"] += r.get("rejected", [])
            final = r.get("final_url")
            if final:                 # a row that never resolved has no URL to cite
                entry["urls"].append(final)
            if r.get("manual_shared_with"):
                entry["shared"] = True
            for s in r.get("electrical_context", []):
                entry["elec_terms"].add(s["term"])
            if reads:
                man_stats["with_reading"] += 1
            elif r.get("electrical_context"):
                man_stats["supply_spec_only"] += 1

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
        # TIER 1 OUTRANKS EVERYTHING BELOW IT -- but a disagreement is a finding,
        # never a silent overwrite. The metafield reading is kept alongside and
        # the pair is reported.
        # TIER 1: the manufacturer's own manual.
        #
        # A HIGHER TIER THAT STATES NOTHING MUST NOT NULLIFY A LOWER ONE. The
        # first version of this block emitted MANUAL_AMBIGUOUS and
        # MANUAL_SUPPLY_SPEC_ONLY as VALUES, which suppressed metafield and
        # satellite figures we already publish and dropped coverage 58 -> 55. A
        # manual that cannot be attributed has not contradicted us; it has said
        # nothing about this SKU. Precedence orders values, not silence. So the
        # manual either supplies a value or it steps aside, leaving a note on
        # whatever wins.
        man_cell, man_note = None, None
        if h in man:
            e = man[h]
            vals = sorted({r["kw"] for r in e["readings"]})
            plausible_vals = [v for v in vals if PLAUSIBLE_KW[0] <= v <= PLAUSIBLE_KW[1]]
            if len(plausible_vals) == 1 and len(vals) == 1:
                man_cell = e["readings"][0]      # spec_plate sorts first upstream
            elif len(vals) > 1:
                # One Finnmark PDF serves FD-4 and FD-5; page 22 lists BOTH
                # "Trinity = 1750 watts" and "Harvia Vega Compact = 1900 watts".
                # Picking one would be attributing by guess.
                man_note = {
                    "manual_states_several_ratings": vals,
                    "manual_shared_across_line": e["shared"],
                    "readings": [{"kw": r["kw"], "page": r["page"], "tier": r["tier"],
                                  "span": r["span"]} for r in e["readings"]],
                    "note": "not attributable to this SKU from the document alone; "
                            "attribute by hand from the spans",
                }
            elif vals and not plausible_vals:
                man_note = {"manual_reading_outside_band": vals,
                            "note": f"outside the {PLAUSIBLE_KW[0]}-{PLAUSIBLE_KW[1]} kW "
                                    f"band; treated as a parse failure, not a measurement"}
            elif e["elec_terms"]:
                man_note = {
                    "manual_states_supply_spec_only": sorted(e["elec_terms"]),
                    "note": "the manual gives electrical information but no wattage "
                            "or kW. A supply spec is what to wire, not what the unit "
                            "draws; volts x amps is breaker capacity and is never "
                            "derived here.",
                }
            if e["rejected"]:
                man_note = dict(man_note or {}, manual_rejected_readings=[
                    {"kw": r["kw"], "page": r["page"], "span": r["span"],
                     "because": r["rejected_because"]} for r in e["rejected"]])

        if man_cell is not None:
            chosen = man_cell
            mf_vals = sorted({r["kw"] for r in combined})
            F["rated_power_kw"] = cell(
                chosen["kw"], "manufacturer_manual", chosen["span"], man_at,
                unit="kW", basis=chosen["basis"], precedence_tier=1,
                source_url=(chosen.get("source_url")
                            or (man[h]["urls"][0] if man[h]["urls"] else None)))
            F["rated_power_kw"]["manual_page"] = chosen["page"]
            F["rated_power_kw"]["manual_tier"] = chosen["tier"]
            if man[h]["shared"]:
                F["rated_power_kw"]["manual_shared_across_line"] = True
            if mf_vals and chosen["kw"] not in mf_vals:
                F["rated_power_kw"]["disagrees_with_metafield"] = {
                    "manual_kw": chosen["kw"], "manual_span": chosen["span"],
                    "manual_page": chosen["page"],
                    "metafield_kw": mf_vals, "metafield_span": combined[0]["span"],
                    "note": "tier 1 wins, and the disagreement is reported, "
                            "not resolved away",
                }
            elif mf_vals:
                F["rated_power_kw"]["corroborated_by_metafield"] = {
                    "metafield_kw": mf_vals[0],
                    "metafield_span": combined[0]["span"]}
        elif h in mfg:
            m = mfg[h]
            vals = sorted({r["kw"] for r in m["readings"]})
            if len(vals) > 1:
                F["rated_power_kw"] = gap(POWER_CONFLICT,
                                          f"manufacturer page states {vals} kW")
                F["rated_power_readings"] = m["readings"]
            elif not PLAUSIBLE_KW[0] <= vals[0] <= PLAUSIBLE_KW[1]:
                F["rated_power_kw"] = gap(IMPLAUSIBLE,
                                          f"manufacturer page states {vals[0]} kW")
            else:
                chosen = m["readings"][0]
                F["rated_power_kw"] = cell(
                    chosen["kw"], "manufacturer_page", chosen["span"], mfg_at,
                    unit="kW", basis=chosen["basis"], precedence_tier=2,
                    source_url=m["final_url"])
                mf_vals = sorted({r["kw"] for r in combined})
                if mf_vals and vals[0] not in mf_vals:
                    F["rated_power_kw"]["disagrees_with_metafield"] = {
                        "manufacturer_kw": vals[0], "metafield_kw": mf_vals,
                        "metafield_span": combined[0]["span"],
                        "note": "tier 1 wins, and the disagreement is reported, "
                                "not resolved away",
                    }
        elif not combined and h in inf_kw:
            val, raw = inf_kw[h]
            F["rated_power_kw"] = cell(val, "infinitesauna.com/data/saunas.csv", raw,
                                       inf_at, unit="kW", basis="traditional_heater_kw",
                                       precedence_tier=5,
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
        elif h in man and man[h]["elec_terms"] and not man[h]["readings"]:
            # More precise than POWER_NOT_STATED: we READ the manufacturer's own
            # manual and it gives a supply spec, not a rating.
            F["rated_power_kw"] = gap(
                MANUAL_SUPPLY_SPEC_ONLY,
                f"the manual states electrical information "
                f"({', '.join(sorted(man[h]['elec_terms']))}) but no wattage or kW, and "
                f"no other source states a rating. A supply spec is what to wire, not "
                f"what the unit draws; volts x amps is breaker capacity and is never "
                f"derived here.")
        elif h in man and len({r["kw"] for r in man[h]["readings"]}) > 1:
            F["rated_power_kw"] = gap(
                MANUAL_AMBIGUOUS,
                f"a manual shared across this product line states "
                f"{sorted({r['kw'] for r in man[h]['readings']})} kW and no other source "
                f"states a rating. Which applies to this SKU is not decidable from the "
                f"document; attribute by hand from the spans.")
        else:
            F["rated_power_kw"] = gap(
                POWER_NOT_STATED,
                "sources state no kW or wattage rating. NOT derived from volts x amps: "
                "that is the breaker's capacity, not the heater's rating.")

        # The manual's own evidence travels with the field whichever tier won,
        # including when the manual itself supplied nothing.
        if man_note:
            F["rated_power_kw"]["manual_evidence"] = man_note

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
            hit = read_dedicated_circuit(text)
            if hit is not None:
                value, qualifier, span = hit
                ded = cell(value, field, span, at) if qualifier is None else \
                    cell(value, field, span, at, qualifier=qualifier)
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
