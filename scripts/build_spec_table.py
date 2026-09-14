#!/usr/bin/env python3
"""Build the versioned model spec table by joining three existing sources.

    data/facts/infinite_saunas.json   190 rows, parsed from infinitesauna.com/data/saunas.csv
    data/facts/bhis_saunas.json        90 rows, parsed from besthomeinfraredsauna.com/data/infrared_saunas.csv
    data/shopify-catalog-snapshot-*.json   Shopify Admin API, 211 Sauna SKUs (142 in detail)

  -> data/spec-table.json

THE JOIN KEY IS NOT FUZZY.
Both satellite CSVs already carry an inhousewellness.com product URL per row
(`inhouse_url` on infinite, `source_url` on bhis). The handle in that URL is
compared for EXACT equality against the Shopify product handle. No brand-string
normalisation, no model-number similarity, no token overlap -- so the
false-positive rate of the match is zero by construction, not by threshold.
This was checked against Shopify: `handle:<nonexistent>` returns nothing and the
bare prefix `handle:dynamic` returns nothing, so `handle:` is exact-match and a
dead URL fails to match rather than matching its neighbour.

HONESTY GATE -- absence is not a value.
Every field is either {"value": ..., "source": ..., "fetched_at": ...} or
{"value": null, "reason": "<CODE>"}. There is no third state, no ""/0/None
standing in for a measurement, and no estimate carried over from a similar
model. In particular:

  * Shopify shipping weight of 0 lb is NOT a weight. It is the default a
    merchant leaves when they never entered one. It becomes null with
    SHOPIFY_WEIGHT_ZERO rather than a 0 that would flow into a freight sum and
    produce a confident, precise, false number. This is the project's own
    recurring failure shape (`lint_missing_values.py`, instances 1-5).
  * `plug` on the infinite feed reads "Standard 120V outlet". That is a prose
    description of an outlet, not a NEMA designation. Turning it into
    "NEMA 5-15" would be inference, so nema_plug stays null with
    NOT_A_NEMA_DESIGNATION and the prose is kept beside it under its own name.
  * `circuits` on the bhis feed is a COUNT of circuits, not a dedicated-circuit
    yes/no. dedicated_circuit stays null; circuits_count carries the count.
  * bhis `watts` is infrared panel wattage. It is a different quantity from a
    traditional heater's kW rating and is never written into heater_kw.

Conflicting sources are recorded, never resolved silently: the field carries
every source's value and conflict=true. Picking a winner here would bury the
disagreement in a file that later gets published as fact.
"""
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SNAPSHOT = DATA / "shopify-catalog-snapshot-2026-09-14.json"
OUT = DATA / "spec-table.json"

SCHEMA_VERSION = "1.0.0"

# --- reason codes -----------------------------------------------------------
NO_SATELLITE_ROW = "NO_SATELLITE_ROW"            # SKU has no row in either CSV
NO_SOURCE_CARRIES_FIELD = "NO_SOURCE_CARRIES_FIELD"  # no joined source has the field at all
EMPTY_IN_SOURCE = "EMPTY_IN_SOURCE"              # source has the column, this row is blank
SHOPIFY_WEIGHT_ZERO = "SHOPIFY_WEIGHT_ZERO"      # 0 lb is a default, not a measurement
NOT_A_NEMA_DESIGNATION = "NOT_A_NEMA_DESIGNATION"
NOT_IN_DETAIL_SNAPSHOT = "NOT_IN_DETAIL_SNAPSHOT"  # census-only row, no field pull made
UNPARSEABLE = "UNPARSEABLE"

# Fields the brief asks for that NO joined source carries. Named here so the gap
# report reads off the table instead of being written by hand, and so adding a
# source later is a one-line change that the completeness table picks up.
STRUCTURALLY_ABSENT = {
    "crate_length_in": "no source carries crate dimensions",
    "crate_width_in": "no source carries crate dimensions",
    "crate_height_in": "no source carries crate dimensions",
    "crate_weight_lb": "no source carries CRATE weight; Shopify ships a variant weight, which is a different quantity and is recorded as shipping_weight",
    "door_width_required_in": "no source carries the doorway clearance needed to move the crate in",
    "preheat_minutes": "no source carries a preheat time as a number; the infinite `heater` column mentions one in prose ('heats to 180F in an hour') and prose is not a measurement",
    "clearances_in": "no source carries wall/ceiling clearances",
    "warranty_doc_url": "no source carries a warranty DOCUMENT url; the infinite `warranty` column is a prose term ('Limited lifetime warranty') and is recorded as warranty_term_text",
    "nema_plug": "the infinite `plug` column is a prose outlet description, not a NEMA designation; recorded as plug_description",
    "dedicated_circuit_required": "the bhis `circuits` column is a circuit COUNT, not a dedicated-circuit flag; recorded as circuits_count",
}


def blank(v):
    """True when a source cell carries no value. Explicit, not a falsy check --
    0 and 0.0 are legitimate measurements and must not be swallowed here."""
    return v is None or str(v).strip() in ("", "None", "nan")


def cell(value, source, fetched_at, unit=None, note=None):
    d = {"value": value, "source": source, "fetched_at": fetched_at}
    if unit is not None:
        d["unit"] = unit
    if note is not None:
        d["note"] = note
    return d


def gap(reason, detail=None):
    d = {"value": None, "reason": reason}
    if detail is not None:
        d["detail"] = detail
    return d


def num(raw):
    """Pull a single number out of a source cell like '8 kW', '240V', '20A',
    '1526 lbs', '15.0'. Returns None when the cell holds no number -- the caller
    must branch on that, never default it."""
    if blank(raw):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(raw))
    return float(m.group()) if m else None


def first_present(candidates):
    """candidates: list of (value, source, fetched_at, unit, note).
    Returns (present, conflict) where present is the list of source-tagged
    readings that actually carry a value. Nothing is chosen here."""
    return [c for c in candidates if c[0] is not None]


def merged(candidates, field_unit=None):
    """Build a field from several sources without resolving disagreement."""
    present = first_present(candidates)
    if not present:
        return None
    values = [p[0] for p in present]
    distinct = {v if not isinstance(v, float) else round(v, 4) for v in values}
    head = present[0]
    out = cell(head[0], head[1], head[2], unit=head[3] if head[3] else field_unit, note=head[4])
    if len(present) > 1:
        out["also_reported"] = [
            {"value": p[0], "source": p[1], "fetched_at": p[2]} for p in present[1:]
        ]
        if len(distinct) > 1:
            out["conflict"] = True
    return out


def handle_of(url):
    if blank(url):
        return None
    u = str(url)
    if "inhousewellness.com" not in u or "/products/" not in u:
        return None
    return u.split("/products/")[-1].split("?")[0].split("#")[0].strip("/").lower()


def main():
    inf_doc = json.loads((DATA / "facts" / "infinite_saunas.json").read_text())
    bhi_doc = json.loads((DATA / "facts" / "bhis_saunas.json").read_text())
    snap = json.loads(SNAPSHOT.read_text())

    inf_at, bhi_at, shop_at = inf_doc["fetched_at"], bhi_doc["fetched_at"], snap["fetched_at"]
    INF, BHI, SHOP = "infinitesauna.com/data/saunas.csv", "besthomeinfraredsauna.com/data/infrared_saunas.csv", "shopify-admin-api"

    inf_by = {}
    for r in inf_doc["rows"]:
        h = handle_of(r.get("inhouse_url"))
        if h:
            inf_by.setdefault(h, []).append(r)
    bhi_by = {}
    for r in bhi_doc["rows"]:
        h = handle_of(r.get("source_url"))
        if h:
            bhi_by.setdefault(h, []).append(r)

    # A handle claimed by two rows of the same feed would make the join ambiguous.
    # Assert rather than silently take the first -- "one of these is right" is a
    # decision, and it is not this script's to make.
    for name, idx in (("infinite", inf_by), ("bhis", bhi_by)):
        dupes = {h: len(v) for h, v in idx.items() if len(v) > 1}
        if dupes:
            sys.exit(f"{name}: handle claimed by more than one row, join is ambiguous: {dupes}")

    detail = {p["handle"]: p for p in snap["products"]}
    census = snap["sauna_type_census"]

    rows = []
    for entry in census:
        h, status = entry["handle"], entry["status"]
        i = inf_by.get(h, [None])[0]
        b = bhi_by.get(h, [None])[0]
        s = detail.get(h)

        matched_sources = [n for n, r in ((INF, i), (BHI, b)) if r is not None]
        row = {
            "shopify_handle": h,
            "shopify_status": status,
            "shopify_url": f"https://inhousewellness.com/products/{h}",
            "join": {
                "matched": bool(matched_sources),
                "satellite_sources": matched_sources,
                "method": "exact equality on the inhousewellness.com product handle carried by the satellite row",
                "fuzzy_matching_used": False,
            },
            "fields": {},
        }
        F = row["fields"]

        if s is None:
            # Census-only: the handle is known to exist and to be a Sauna, but no
            # per-field pull was made for it. That is a different state from
            # "pulled and empty" and is labelled as such.
            row["join"]["shopify_detail"] = "census_only"
            for k in ("brand", "model", "sku", "type", "msrp_usd", "inh_price_usd"):
                F[k] = gap(NOT_IN_DETAIL_SNAPSHOT)
        else:
            row["join"]["shopify_detail"] = "full"
            v0 = s["variants"][0] if s["variants"] else None

            F["brand"] = merged([
                (s["vendor"], SHOP, shop_at, None, "Shopify product vendor"),
                (i["brand"] if i and not blank(i.get("brand")) else None, INF, inf_at, None, None),
                (b["brand"] if b and not blank(b.get("brand")) else None, BHI, bhi_at, None, None),
            ]) or gap(EMPTY_IN_SOURCE)

            # A product TITLE is not a reading of the model number, so it is not a
            # candidate here -- listing it as one made every row report a
            # conflict, which is a count that says nothing. It gets its own field.
            F["model"] = merged([
                (i["model"] if i and not blank(i.get("model")) else None, INF, inf_at, None, None),
                (b["model"] if b and not blank(b.get("model")) else None, BHI, bhi_at, None, None),
            ]) or gap(EMPTY_IN_SOURCE)
            F["shopify_title"] = cell(s["title"], SHOP, shop_at)

            sku = v0["sku"] if v0 and not blank(v0.get("sku")) else None
            F["sku"] = cell(sku, SHOP, shop_at) if sku else gap(EMPTY_IN_SOURCE, "variant carries no SKU in Shopify")
            F["variant_count"] = cell(s["nvariants"], SHOP, shop_at)

            price = num(v0["price"]) if v0 else None
            F["inh_price_usd"] = cell(price, SHOP, shop_at, unit="USD") if price is not None \
                else gap(EMPTY_IN_SOURCE)

            F["msrp_usd"] = merged([
                (num(v0["compareAtPrice"]) if v0 else None, SHOP, shop_at, "USD", "Shopify compareAtPrice"),
                (num(b.get("msrp")) if b else None, BHI, bhi_at, "USD", None),
                (num(i.get("reference_price")) if i else None, INF, inf_at, "USD", None),
            ], field_unit="USD") or gap(EMPTY_IN_SOURCE)

            # Shipping weight, explicitly NOT crate weight, and explicitly not 0.
            if v0 is not None:
                w = v0.get("weight")
                if w is None:
                    F["shipping_weight"] = gap(EMPTY_IN_SOURCE)
                elif float(w) == 0.0:
                    F["shipping_weight"] = gap(
                        SHOPIFY_WEIGHT_ZERO,
                        "Shopify reports 0 for this variant; 0 is the untouched default, not a measured weight",
                    )
                else:
                    F["shipping_weight"] = cell(float(w), SHOP, shop_at, unit=v0["weightUnit"],
                                                note="Shopify variant shipping weight; NOT crate weight")
            else:
                F["shipping_weight"] = gap(EMPTY_IN_SOURCE)

        if i is None and b is None:
            for k in ("type", "heater_kw", "volts", "amps", "circuits_count", "indoor_outdoor",
                      "assembled_width_in", "assembled_depth_in", "assembled_height_in",
                      "capacity_persons", "max_temp_f", "spectrum", "wood", "emf_label",
                      "emf_claim", "emf_distance", "plug_description", "warranty_term_text",
                      "ir_panel_watts", "satellite_weight"):
                F.setdefault(k, gap(NO_SATELLITE_ROW))
        else:
            if b is not None:
                t = ("hybrid" if b.get("hybrid") == "True"
                     else "traditional" if b.get("traditional") == "True"
                     else "infrared" if b.get("pure_infrared") == "True" else None)
            else:
                t = None
            it = i.get("type").lower() if i and not blank(i.get("type")) else None
            F["type"] = merged([
                (it, INF, inf_at, None, None),
                (t, BHI, bhi_at, None, "derived from the pure_infrared/traditional/hybrid flags"),
            ]) or gap(EMPTY_IN_SOURCE)

            F["heater_kw"] = merged([
                (num(i.get("heater_kw")) if i else None, INF, inf_at, "kW", None),
            ], field_unit="kW") or gap(EMPTY_IN_SOURCE)

            F["ir_panel_watts"] = merged([
                (num(b.get("watts")) if b else None, BHI, bhi_at, "W", "infrared panel wattage, a different quantity from heater kW"),
            ], field_unit="W") or gap(EMPTY_IN_SOURCE)

            F["volts"] = merged([
                (num(i.get("voltage")) if i else None, INF, inf_at, "V", None),
                (num(b.get("voltage")) if b else None, BHI, bhi_at, "V", None),
            ], field_unit="V") or gap(EMPTY_IN_SOURCE)

            F["amps"] = merged([
                (num(i.get("amperage")) if i else None, INF, inf_at, "A", None),
                (num(b.get("amps")) if b else None, BHI, bhi_at, "A", None),
            ], field_unit="A") or gap(EMPTY_IN_SOURCE)

            F["circuits_count"] = merged([
                (num(b.get("circuits")) if b else None, BHI, bhi_at, "circuits", None),
            ]) or gap(EMPTY_IN_SOURCE)

            io = None
            if i and not blank(i.get("placement")):
                io = i["placement"].lower()
            io_b = None
            if b and not blank(b.get("indoor")):
                io_b = "indoor" if b["indoor"] == "True" else "outdoor"
            F["indoor_outdoor"] = merged([
                (io, INF, inf_at, None, None),
                (io_b, BHI, bhi_at, None, "derived from the bhis `indoor` boolean"),
            ]) or gap(EMPTY_IN_SOURCE)

            for key, col in (("assembled_width_in", "width"),
                             ("assembled_depth_in", "depth"),
                             ("assembled_height_in", "height")):
                F[key] = merged([
                    (num(b.get(col)) if b else None, BHI, bhi_at, "in",
                     "the source states no unit; inches is the convention of the feed and is recorded as an assumption, not a reading"),
                ], field_unit="in") or gap(EMPTY_IN_SOURCE)

            F["capacity_persons"] = merged([
                (num(i.get("capacity")) if i else None, INF, inf_at, "persons", None),
                (num(b.get("capacity")) if b else None, BHI, bhi_at, "persons", None),
            ]) or gap(EMPTY_IN_SOURCE)

            F["max_temp_f"] = merged([
                (num(i.get("max_temp")) if i else None, INF, inf_at, "F", None),
                (num(b.get("max_temp")) if b else None, BHI, bhi_at, "F", None),
            ], field_unit="F") or gap(EMPTY_IN_SOURCE)

            for key, ic, bc in (("spectrum", "spectrum", "spectrum"),
                                ("wood", "wood", "wood")):
                F[key] = merged([
                    (i.get(ic) if i and not blank(i.get(ic)) else None, INF, inf_at, None, None),
                    (b.get(bc) if b and not blank(b.get(bc)) else None, BHI, bhi_at, None, None),
                ]) or gap(EMPTY_IN_SOURCE)

            for key, col in (("emf_label", "emf_label"), ("emf_claim", "emf_claim"),
                             ("emf_distance", "emf_distance")):
                F[key] = merged([
                    (b.get(col) if b and not blank(b.get(col)) else None, BHI, bhi_at, None, None),
                ]) or gap(EMPTY_IN_SOURCE)

            F["plug_description"] = merged([
                (i.get("plug") if i and not blank(i.get("plug")) else None, INF, inf_at, None,
                 "prose outlet description; see nema_plug for why it is not a NEMA type"),
            ]) or gap(EMPTY_IN_SOURCE)

            F["warranty_term_text"] = merged([
                (i.get("warranty") if i and not blank(i.get("warranty")) else None, INF, inf_at, None,
                 "prose warranty term; see warranty_doc_url for why it is not a document"),
            ]) or gap(EMPTY_IN_SOURCE)

            F["satellite_weight"] = merged([
                (num(i.get("weight")) if i else None, INF, inf_at, "lb", "satellite-reported unit weight"),
            ], field_unit="lb") or gap(EMPTY_IN_SOURCE)

        for field, why in STRUCTURALLY_ABSENT.items():
            F[field] = gap(NO_SOURCE_CARRIES_FIELD, why)

        rows.append(row)

    # ---- completeness, computed from the table rather than asserted ----------
    all_fields = sorted({k for r in rows for k in r["fields"]})
    matched = [r for r in rows if r["join"]["matched"]]

    def completeness(subset):
        out = {}
        n = len(subset)
        for f in all_fields:
            have = sum(1 for r in subset if r["fields"].get(f, {}).get("value") is not None)
            out[f] = {"populated": have, "of": n, "pct": round(100 * have / n, 1) if n else 0.0}
        return out

    reasons = Counter()
    conflicts = Counter()
    for r in rows:
        for f, v in r["fields"].items():
            if v.get("value") is None:
                reasons[v.get("reason", "?")] += 1
            if v.get("conflict"):
                conflicts[f] += 1

    doc = {
        "schema_version": SCHEMA_VERSION,
        "built_at": "2026-09-14",
        "row_definition": "one row per Shopify product of productType 'Sauna'",
        "sources": [
            {"name": "infinite_saunas", "url": inf_doc["url"], "fetched_at": inf_at, "rows": inf_doc["row_count"]},
            {"name": "bhis_saunas", "url": bhi_doc["url"], "fetched_at": bhi_at, "rows": bhi_doc["row_count"]},
            {"name": "shopify_catalog", "url": "Shopify Admin GraphQL API", "fetched_at": shop_at,
             "rows": len(snap["products"]), "census_rows": len(census)},
        ],
        "join": {
            "key": "inhousewellness.com product handle",
            "comparison": "exact string equality, case-normalised",
            "fuzzy_matching_used": False,
            "false_positive_risk": "zero by construction: a satellite row supplies the INH URL itself, and a dead handle returns no Shopify product rather than a neighbouring one (verified with a negative control)",
        },
        "match_rate": {
            "sauna_skus_total": len(rows),
            "matched": len(matched),
            "unmatched": len(rows) - len(matched),
            "pct": round(100 * len(matched) / len(rows), 1),
            "active_only": {
                "sauna_skus_active": sum(1 for r in rows if r["shopify_status"] == "ACTIVE"),
                "matched": sum(1 for r in matched if r["shopify_status"] == "ACTIVE"),
                "pct": round(100 * sum(1 for r in matched if r["shopify_status"] == "ACTIVE")
                             / sum(1 for r in rows if r["shopify_status"] == "ACTIVE"), 1),
            },
        },
        "field_completeness_matched_only": completeness(matched),
        "field_completeness_all_rows": completeness(rows),
        "null_reason_counts": dict(reasons.most_common()),
        "fields_with_source_conflicts": dict(conflicts.most_common()),
        "structurally_absent_fields": STRUCTURALLY_ABSENT,
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    print(f"wrote {OUT.relative_to(ROOT)}  rows={len(rows)}")
    print(f"match rate: {len(matched)}/{len(rows)} = {doc['match_rate']['pct']}%  "
          f"(ACTIVE only: {doc['match_rate']['active_only']['matched']}/"
          f"{doc['match_rate']['active_only']['sauna_skus_active']} = "
          f"{doc['match_rate']['active_only']['pct']}%)")
    print("\nfield completeness, matched rows only:")
    for f, c in sorted(doc["field_completeness_matched_only"].items(), key=lambda kv: -kv[1]["pct"]):
        print(f"  {f:26s} {c['populated']:3d}/{c['of']}  {c['pct']:5.1f}%")
    print("\nnull reasons:", doc["null_reason_counts"])
    print("conflicts:", doc["fields_with_source_conflicts"])


if __name__ == "__main__":
    main()
