#!/usr/bin/env python3
"""INH Verified — which records get a public page, and the data each page renders.

    .venv/bin/python scripts/verified_pages.py --threshold    # counts, per brand, sold vs not sold
    .venv/bin/python scripts/verified_pages.py --build        # out/verified/pages/*.json + methodology body

THE MINIMUM-CONTENT THRESHOLD (Round 2 brief + Part A answers). A record gets a page
only if it is published, is not a ledger record, and has all of:
  * an approved title and a frozen handle
  * a verified heat type
  * a verified capacity (single value or labelled range)
  * verified exterior dimensions            (assembled width, depth AND height)
  * electrical: a verified supply voltage, stated amperage, labelled circuit or heater
    kW, OR option-dependence recorded WITH EVIDENCE (a source_url and a snippet), which
    the page renders as "Depends on the heater option chosen" with its source link.
"Verified" means grade certified, documented, listed or reviewer_measured.

THE PAGE DATA. Everything a page prints is computed here from saunas.json, so the
Liquid templates only loop and print: no template composes a value, and a value the
dataset does not hold cannot appear. Rules the builder enforces:
  * every value carries its grade, source link and verified date;
  * every gap reads "Not verified" (Part A answer D-C; the other gap wording is not
    used anywhere until a per-field absence check exists);
  * quoted source text is capped at 160 characters and dropped when it fails the
    health-claims gate (the value and its link still show);
  * no price, and no offer, ever enters page data (D-G).

"Sold by InHouse Wellness" is decided per BRAND from the store's own active products.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
SAUNAS = Path(os.environ.get("INH_SAUNAS", ROOT / "data/verified/saunas.json"))
NAV = ROOT / "data/verified/inh-navigation.json"
HANDLES = ROOT / "data/verified/handles.json"
OVERRIDES = ROOT / "data/verified/title-overrides.json"
PAGES_OUT = ROOT / "out/verified/pages"
VERIFIED = {"certified", "documented", "listed", "reviewer_measured"}
BASE = "https://inhousewellness.com"
HUB_PATH = "/pages/sauna-database"
METHOD_PATH = "/pages/sauna-database-methodology"
MODEL_PREFIX = "/pages/sauna-database/"
DB_NAME = "InHouse Wellness Verified Sauna Database"
CORRECTIONS = "data@inhousewellness.com"
RESPONSIBLE = "Daniel Mercer, Partnerships & Business Strategy, InHouse Wellness"
SNIPPET_MAX = 160
GAP = "Not verified"
OPTION_DEP = "Depends on the heater option chosen"
# The four manufacturer-page inconsistencies (R2-D5). They are backlog records today; this
# guard keeps them off every page even if a later build publishes them.
LEDGER_IDS = {"sauna/golden-designs/gdi-8206-01", "sauna/salus/san02m017", "sauna/salus/san08m009",
              "sauna/almost-heaven/mk100014"}
GRADE_LABEL = {"certified": "Certified", "documented": "Documented", "listed": "Listed",
               "reviewer_measured": "Reviewer measured", "owner_measured": "Owner measured",
               "modeled": "Modeled", "claimed": "Claimed", "not_verified": "Not verified",
               "not_applicable": "Not applicable"}
GRADE_DEFINITION = {
    "certified": "An independent certification body's listing states this value.",
    "documented": "The manufacturer's own manual or specification sheet states this value.",
    "listed": "The manufacturer's own product page states this value.",
    "reviewer_measured": "An independent reviewer measured this value and published how.",
    "owner_measured": "An owner measured this value and reported how it was measured.",
    "modeled": "This value is calculated from other values rather than stated by a source.",
    "claimed": "The manufacturer's own term, shown as their claim and not as a verified measurement.",
    "not_verified": "No source we could read states a single value for this, so we show none.",
    "not_applicable": "The field does not apply to this model, such as a stove rating on an infrared-only sauna.",
}
# Store collections that describe merchandising, not the product; never offered as navigation.
NON_NAV_COLLECTIONS = re.compile(r"(?i)^(frontpage|non-bb|free-bonus|avada-.*|newest-products|best-selling-products|"
                                 r".*favorites|all|sale.*|new.*)$")
BROWSE = {"infrared": ("infrared-saunas", "Browse infrared saunas at InHouse Wellness"),
          "traditional": ("saunas", "Browse saunas at InHouse Wellness"),
          "hybrid": ("hybrid", "Browse hybrid saunas at InHouse Wellness")}


def ok(f) -> bool:
    return isinstance(f, dict) and f.get("value") is not None and f.get("grade") in VERIFIED


def load_dataset() -> dict:
    return json.loads(SAUNAS.read_text())


def load_navigation() -> dict:
    return json.loads(NAV.read_text())


def load_handles() -> dict:
    return {k: v["handle"] for k, v in json.loads(HANDLES.read_text())["handles"].items()} if HANDLES.exists() else {}


def load_titles() -> dict:
    ov = json.loads(OVERRIDES.read_text())["overrides"] if OVERRIDES.exists() else {}
    return {k: v["display_title"] for k, v in ov.items() if v.get("approved") is True}


_SOLD: set | None = None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"(?i)\b(saunas?|inc|llc|manufacturing)\b", "", s).lower())


def brand_sold(r) -> bool:
    global _SOLD
    if _SOLD is None:
        from verified_inh_map import SNAPSHOT, from_census
        snap = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else from_census()
        _SOLD = {_norm(p["vendor"]) for p in snap["products"] if p["status"] == "ACTIVE"}
    b = _norm(r["identity"]["brand"]["value"] or "")
    return bool(b) and any(b in v or v in b for v in _SOLD if v)


def up_to(r) -> bool:
    """Round 3: the manufacturer stated capacity as a maximum ("fits up to 4 adults")."""
    return "up to" in (r["capacity_max"].get("note") or "")


def capacity_label(r) -> str | None:
    a, b = r["capacity_min"], r["capacity_max"]
    if not (ok(a) and ok(b)):
        return None
    lo, hi = int(a["value"]), int(b["value"])
    if up_to(r) and lo == hi:
        return f"up to {hi}"
    return f"{lo}" if lo == hi else f"{lo}–{hi}"


def has_rect_dims(r) -> bool:
    a = r["dimensions"]["assembled"]
    return all(ok(a[k]) for k in ("width_in", "depth_in", "height_in"))


def has_exterior_dims(r) -> bool:
    """Rectangular W/D/H (Round 1), or the complete exterior set for the product's own shape as stated
    (Round 3, D-1): barrel = length + diameter; round = diameter + height; corner = every wall + height."""
    a = r["dimensions"]["assembled"]
    return all(ok(a[k]) for k in ("width_in", "depth_in", "height_in")) or ok(r["dimensions"]["exterior"])


def option_dependence(r):
    """The evidence object, or None. Counted only with a source_url AND a snippet."""
    od = r["electrical"].get("option_dependence")
    if isinstance(od, dict) and od.get("source_url") and (od.get("evidence") or {}).get("snippet"):
        return od
    return None


def has_electrical(r) -> bool:
    e = r["electrical"]
    return (ok(e["supply_voltage"]) or ok(e["stated_amperage"]) or bool(e["circuits"]) or ok(e["heater_kw"])
            or option_dependence(r) is not None)


def is_ledger(r) -> bool:
    return r["inh_id"] in LEDGER_IDS


def threshold(ds):
    for r in ds["records"]:
        if r["status"] != "published":
            continue
        missing = [name for name, good in (("heat type", ok(r["heat_type"])),
                                           ("capacity", capacity_label(r) is not None),
                                           ("exterior dimensions", has_exterior_dims(r)),
                                           ("electrical", has_electrical(r))) if not good]
        if is_ledger(r):
            missing.append("ledger record (R2-D5)")
        yield r, {"meets": not missing, "missing": missing, "capacity_label": capacity_label(r)}


def page_records(ds):
    """Records that get a page: the threshold PLUS an approved title and a frozen handle."""
    handles, titles = load_handles(), load_titles()
    for r, t in threshold(ds):
        if t["meets"] and r["inh_id"] in handles and r["inh_id"] in titles:
            yield r, handles[r["inh_id"]], titles[r["inh_id"]], t


def threshold_report(ds) -> dict:
    per_brand, missing = {}, Counter()
    for r, t in threshold(ds):
        b = r["identity"]["brand"]["value"]
        row = per_brand.setdefault(b, {"sold_by_inh": brand_sold(r), "published": 0, "meets": 0})
        row["published"] += 1
        row["meets"] += t["meets"]
        for m in t["missing"]:
            missing[m] += 1
    sold = [v for v in per_brand.values() if v["sold_by_inh"]]
    not_sold = [v for v in per_brand.values() if not v["sold_by_inh"]]
    with_od = sum(1 for r in ds["records"] if r["status"] == "published" and option_dependence(r))
    return {"per_brand": dict(sorted(per_brand.items())),
            "totals": {"published": sum(v["published"] for v in per_brand.values()),
                       "meets": sum(v["meets"] for v in per_brand.values()),
                       "sold_by_inh": {"published": sum(v["published"] for v in sold), "meets": sum(v["meets"] for v in sold)},
                       "not_sold_by_inh": {"published": sum(v["published"] for v in not_sold),
                                           "meets": sum(v["meets"] for v in not_sold)}},
            "records_with_option_dependence_evidence": with_od,
            "below_threshold_missing_field_counts": dict(missing.most_common())}


# ------------------------------------------------------------------ format --

def num(v) -> str:
    return f"{int(v)}" if float(v).is_integer() else f"{v:g}"


def people(lo, hi, upto=False) -> str:
    if lo == hi and upto:
        return f"Manufacturer states up to {hi} {'person' if hi == 1 else 'people'}"
    if lo == hi:
        return f"{lo} person" if lo == 1 else f"{lo} people"
    return f"Manufacturer states {lo} to {hi} people"


SHAPE_LABEL = {"rectangular": "Exterior", "barrel": "Exterior (barrel)", "round": "Exterior (round)",
               "corner": "Exterior (corner unit)"}


def exterior_text(v) -> str:
    """Exactly as stated, in the product's own shape; never converted (D-1)."""
    sep = " · " if v["shape"] == "corner" else " × "
    body = sep.join(f"{p['label']} {p['stated'].replace(' ', chr(160))}″" for p in v["parts"])   # "76 ½" never wraps
    return ("At the roof: " + body) if v.get("qualifier") == "roof" else body


def host(url: str) -> str:
    return urlsplit(url).netloc.removeprefix("www.")


def trim(s: str, n: int = SNIPPET_MAX) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n - 1]
    cut = cut[:cut.rfind(" ")] if " " in cut[n // 2:] else cut
    return cut.rstrip(" ,.;:") + "…"


def health_ok(text: str) -> bool:
    from src.health_claims import find_banned_claims, is_health_adjacent
    return not find_banned_claims(text) and not is_health_adjacent(text)


def fetched_date(f):
    """The date the cited document was fetched (evidence.fetched_at), for the Sources list."""
    ev = f.get("evidence") or {}
    return ev["fetched_at"][:10] if ev.get("fetched_at") else None


def per_circuit(f) -> bool:
    """r3 D12 (approved 2026-10-07): a figure the manufacturer states for EACH of several circuits. Its
    note travels with the value wherever it is shown, so "20 A" never reads as the whole requirement."""
    return bool(f) and (f.get("note") or "").startswith("per circuit")


def fact(label, f, text, path, *, raw=None):
    """One displayed row. `raw` is the dataset value the row claims to show, for the value-match check."""
    if ok(f) or (f.get("grade") == "claimed" and f.get("value") is not None):
        return {"label": label, "state": "value", "text": text, "grade": f["grade"],
                "grade_label": GRADE_LABEL[f["grade"]], "source_url": f["source_url"], "source_host": host(f["source_url"]),
                "verified": f["observed_at"], "field": path, "raw": json.dumps(f["value"] if raw is None else raw),
                "fetched": fetched_date(f), "note": f["note"] if (f.get("grade") == "claimed" or per_circuit(f)) else None}
    if f.get("grade") == "not_applicable":
        return {"label": label, "state": "not_applicable", "text": "Not applicable", "grade": "not_applicable",
                "grade_label": GRADE_LABEL["not_applicable"], "field": path, "raw": "null",
                "note": f.get("note")}
    return {"label": label, "state": "gap", "text": GAP, "grade": "not_verified",
            "grade_label": GRADE_LABEL["not_verified"], "field": path, "raw": "null"}


def option_row(label, path, od):
    return {"label": label, "state": "option", "text": OPTION_DEP, "grade": od.get("grade", "listed"),
            "grade_label": GRADE_LABEL.get(od.get("grade", "listed")), "source_url": od["source_url"],
            "source_host": host(od["source_url"]), "verified": od.get("observed_at"), "field": path, "raw": "null",
            "fetched": fetched_date(od)}


def dims_rows(r, which="assembled", label="Exterior (W × D × H)"):
    e = r["dimensions"]["exterior"]
    if which == "assembled" and not has_rect_dims(r) and ok(e):
        return [fact(SHAPE_LABEL[e["value"]["shape"]], e, exterior_text(e["value"]), "dimensions.exterior")]
    a = r["dimensions"][which]
    w, d, h = a["width_in"], a["depth_in"], a["height_in"]
    if all(ok(x) for x in (w, d, h)) and len({w["source_url"], d["source_url"], h["source_url"]}) == 1:
        row = fact(label, w, f"{num(w['value'])} × {num(d['value'])} × {num(h['value'])} in",
                   f"dimensions.{which}", raw=[w["value"], d["value"], h["value"]])
        row["verified"] = max(x["observed_at"] for x in (w, d, h))
        return [row]
    axis = {"width_in": "Width", "depth_in": "Depth", "height_in": "Height"}
    base = label.split(" (")[0]
    return [fact(f"{base} {axis[k].lower()}", a[k], f"{num(a[k]['value'])} in" if ok(a[k]) else GAP,
                 f"dimensions.{which}.{k}") for k in ("width_in", "depth_in", "height_in")]


SEE_CIRCUITS = {"supply_voltage", "stated_amperage"}


def see_circuits(label, path):
    """A unit with labelled circuits states voltage and amperage PER CIRCUIT; a single
    whole-unit figure is not stated. Pointing at the circuits is accurate; 'Not verified'
    beside a verified 40 A circuit would read as a contradiction."""
    return {"label": label, "state": "see_circuits", "text": "See the labelled circuits above", "grade": "not_verified",
            "grade_label": GRADE_LABEL["not_verified"], "field": path, "raw": "null"}


def electrical_rows(r):
    e = r["electrical"]
    od = option_dependence(r)
    rows = []
    keys = ("circuits_required", "supply_voltage", "stated_amperage", "connection_type", "circuit_requirement", "heater_kw")
    if od and not e["circuits"] and not any(ok(e[k]) for k in keys):
        # Every electrical value depends on the heater the buyer picks: one cited row, not six identical ones.
        row = option_row("Electrical requirements", "electrical.option_dependence", od)
        return [row]

    def row(label, key, fmt):
        f = e[key]
        if not ok(f) and key in SEE_CIRCUITS and e["circuits"]:
            return see_circuits(label, f"electrical.{key}")
        if not ok(f) and od and f.get("grade") != "not_applicable":
            return option_row(label, f"electrical.{key}", od)
        return fact(label, f, fmt(f["value"]) if f.get("value") is not None else GAP, f"electrical.{key}")

    rows.append(row("Circuits required", "circuits_required", lambda v: f"{int(v)}"))
    for i, c in enumerate(e["circuits"]):
        p, v, a = c["purpose"], c["voltage"], c["stated_amperage"]
        parts = [x for x in (v["value"] if ok(v) else None, f"{num(a['value'])} A" if ok(a) else None) if x]
        r0 = fact(f"Circuit: {p['value']}", v if ok(v) else a, " · ".join(parts) or GAP, f"electrical.circuits[{i}]",
                  raw=[p["value"], v["value"], a["value"]])
        r0["circuit"] = True
        rows.append(r0)
    rows.append(row("Supply voltage", "supply_voltage", str))
    rows.append(row("Stated amperage", "stated_amperage", lambda v: f"{num(v)} A"))
    rows.append(row("Connection", "connection_type", str))
    rows.append(row("Dedicated circuit", "circuit_requirement",
                    lambda v: "Dedicated circuit required" if v == "Dedicated required" else str(v)))
    rows.append(row("Heater", "heater_kw", lambda v: f"{num(v)} kW"))
    return rows


# Templated questions, keyed by the missing field. One fixed sentence per field.
ASK = [("supply_voltage", "What supply voltage does this model need: 120V or 240V?"),
       ("stated_amperage", "What amperage does its circuit need to be rated for?"),
       ("circuits_required", "How many circuits does it need, and what is each one for?"),
       ("connection_type", "Does it plug in, and with which plug type, or is it hardwired?"),
       ("circuit_requirement", "Does it need a dedicated circuit?"),
       ("gfci", "Does it need GFCI protection?"),
       ("heater_kw", "What is the heater's rated power in kW?")]


def ask_seller(r):
    e = r["electrical"]
    qs = []
    for key, q in ASK:
        f = e[key]
        if f.get("grade") == "not_applicable":
            continue
        if key == "stated_amperage" and any(ok(c["stated_amperage"]) for c in e["circuits"]):
            continue
        if key == "supply_voltage" and any(ok(c["voltage"]) for c in e["circuits"]):
            continue
        if key == "circuits_required" and e["circuits"] and ok(f):
            continue
        if not ok(f):
            qs.append({"field": f"electrical.{key}", "question": q})
    if capacity_label(r) and r["capacity_min"]["value"] != r["capacity_max"]["value"]:
        qs.append({"field": "capacity", "question": "How many people is it designed to seat, and how many can use it comfortably?"})
    return qs


def article(word):
    """'an' before a vowel sound: 'an infrared', 'an 8-person', 'an 11-person'."""
    w = word.lower()
    return "an" if w[:1] and w[:1] in "aeio" or w.startswith(("8", "11", "18")) else "a"


CIRCUIT_WORD_RX = re.compile(r"(?i)circuit|breaker|outlet|receptacle|service")
WATTS_BEFORE_RX = re.compile(r"(?i)[\d,.]+\s*(?:watts?|w)\b[^\d]{0,12}$")


def amperage_is_circuit(f):
    """True when the source ties this amperage to a circuit: a circuit word within 40
    characters after the figure, or within 25 before it, and no wattage immediately before it.
    "240 Volts 3,330 Watts 13.9 Amps Plugs into a 240V outlet" is the unit's draw; the outlet
    that follows is the plug, not the amperage's subject (R3-B1)."""
    sn = ((f.get("evidence") or {}).get("snippet") or "")
    v = f["value"]
    figs = {num(v), f"{v:g}" if isinstance(v, (int, float)) else str(v)}
    for m in re.finditer(r"(?<![\d.])(\d+(?:\.\d+)?)\s*-?\s*(?:a|amps?|amperes?)\b", sn, re.I):
        if m.group(1) not in figs:
            continue
        before, after = sn[max(0, m.start() - 25):m.start()], sn[m.end():m.end() + 40]
        if WATTS_BEFORE_RX.search(sn[:m.start()]):
            return False
        if CIRCUIT_WORD_RX.search(before) or CIRCUIT_WORD_RX.search(after):
            return True
    return False


def answer_sentence(r, title):
    """[Title] is a [capacity] [placement] [heat type] sauna that [electrical].

    Electrical wording follows what the source called the figure (R3-B1). A labelled circuit is
    a circuit. A whole-unit amperage (`stated_amperage`) is only an amperage the source states:
    the schema defines it as NOT a breaker size, and Clearlight's "240 Volts 3,330 Watts
    13.9 Amps" is the unit's draw. So unless the source ties the figure to a circuit
    (`amperage_is_circuit`), it reads "that the manufacturer lists at 240V and 13.9 A"."""
    e = r["electrical"]
    lo, hi = int(r["capacity_min"]["value"]), int(r["capacity_max"]["value"])
    kind = []
    if ok(r["placement"]):
        kind.append(r["placement"]["value"])
    kind.append(r["heat_type"]["value"])
    if lo == hi and up_to(r):
        what = f"{article(kind[0])} {' '.join(kind)} sauna for up to {hi} people"
    else:
        cap = f"{lo}-person" if lo == hi else f"{lo}- to {hi}-person"
        what = f"{article(cap)} {cap} {' '.join(kind)} sauna"
    circ = []
    for c in e["circuits"]:
        v, a = c["voltage"], c["stated_amperage"]
        if ok(v) and ok(a):
            circ.append(f"a {v['value']}, {num(a['value'])} A circuit ({c['purpose']['value']})")
    if circ:
        n = {1: "one", 2: "two", 3: "three"}.get(len(circ), str(len(circ)))
        tail = " that requires " + (f"{n} circuits: " + " and ".join(circ) if len(circ) > 1 else circ[0])
    elif ok(e["supply_voltage"]) and ok(e["stated_amperage"]) and per_circuit(e["stated_amperage"]):
        # r3 D12: one figure per circuit, several circuits. Never "a ... circuit" (singular).
        v, a = e["supply_voltage"]["value"], num(e["stated_amperage"]["value"])
        cr = e["circuits_required"]
        m = re.match(r"stated as (\d+) separate (\w+)", cr.get("note") or "") if ok(cr) else None
        if m:
            n = {2: "two", 3: "three", 4: "four"}.get(int(m.group(1)), m.group(1))
            tail = f" that requires {n} separate {v}, {a} A {m.group(2)}"
        else:
            tail = f" that the manufacturer lists at {v} and {a} A per circuit, for more than one circuit"
    elif ok(e["supply_voltage"]) and ok(e["stated_amperage"]) and amperage_is_circuit(e["stated_amperage"]):
        tail = f" that requires a {e['supply_voltage']['value']}, {num(e['stated_amperage']['value'])} A circuit"
    elif ok(e["supply_voltage"]) and ok(e["stated_amperage"]):
        tail = f" that the manufacturer lists at {e['supply_voltage']['value']} and {num(e['stated_amperage']['value'])} A"
    elif ok(e["supply_voltage"]):
        tail = f" that requires a {e['supply_voltage']['value']} supply"
    elif ok(e["heater_kw"]):
        kw = num(e['heater_kw']['value'])
        tail = f" with {article(kw)} {kw} kW heater"
    else:
        tail = ""
    return f"{title} is {what}{tail}."


def snippets(rows_by_field, r):
    """Quoted source text for displayed values: unique, <=160 chars, health-gated."""
    out, seen, dropped = [], set(), 0
    for path, f in rows_by_field:
        ev = (f or {}).get("evidence") or {}
        s = ev.get("snippet")
        if not s or not ok(f) and f.get("grade") != "claimed":
            continue
        t = trim(s)
        key = (f["source_url"], t)
        if key in seen:
            continue
        seen.add(key)
        if not health_ok(s):
            dropped += 1
            continue
        out.append({"field": path, "text": t, "source_url": f["source_url"], "source_host": host(f["source_url"]),
                    "fetched": fetched_date(f)})
    return out, dropped


def spec_fields(r):
    """Every graded field for the full specifications table, in reading order."""
    I, E, D = r["identity"], r["electrical"], r["dimensions"]
    rows = [("Brand", I["brand"], str, "identity.brand"),
            ("Model", I["model_name"], str, "identity.model_name"),
            ("Model number", I["model_number"], lambda v: v.replace("|", " / "), "identity.model_number"),
            ("Heat type", r["heat_type"], lambda v: v.capitalize(), "heat_type"),
            ("Placement", r["placement"], lambda v: v.capitalize(), "placement"),
            ("Wood", r["materials"]["wood_species"], str, "materials.wood_species")]
    for k, lab in (("width_in", "Exterior width"), ("depth_in", "Exterior depth"), ("height_in", "Exterior height")):
        rows.append((lab, D["assembled"][k], lambda v: f"{num(v)} in", f"dimensions.assembled.{k}"))
    for k, lab in (("width_in", "Crated width"), ("depth_in", "Crated depth"), ("height_in", "Crated height")):
        rows.append((lab, D["crated"][k], lambda v: f"{num(v)} in", f"dimensions.crated.{k}"))
    for k, lab, fm in (("supply_voltage", "Supply voltage", str), ("stated_amperage", "Stated amperage", lambda v: f"{num(v)} A"),
                       ("breaker_amps", "Breaker", lambda v: f"{num(v)} A"), ("circuits_required", "Circuits required", lambda v: f"{int(v)}"),
                       ("connection_type", "Connection", str), ("circuit_requirement", "Dedicated circuit", str),
                       ("gfci", "GFCI", str), ("heater_kw", "Heater", lambda v: f"{num(v)} kW"),
                       ("heater_voltage", "Heater voltage", str)):
        rows.append((lab, E[k], fm, f"electrical.{k}"))
    ir = r["infrared"]
    rows += [("Infrared spectrum", ir["spectrum"], str, "infrared.spectrum"),
             ("EMF (manufacturer's term)", ir["emf_claim"], str, "infrared.emf_claim"),
             ("Red light", ir["red_light"], lambda v: "Yes" if v is True else ("No" if v is False else str(v)), "infrared.red_light"),
             ("Maximum temperature", r["thermal"]["max_temp_f"], lambda v: f"{num(v)} °F", "thermal.max_temp_f"),
             ("Warranty", r["warranty"]["summary"], str, "warranty.summary")]
    return rows


def store_block(r, nav):
    m = nav["mapped"].get(r["inh_id"])
    heat = r["heat_type"]["value"]
    if m:
        cols = [c for c in m["collections"] if not NON_NAV_COLLECTIONS.match(c["handle"])][:4]
        return {"sold": True, "product_url": f"/products/{m['product_handle']}",
                "product_label": "See price and availability at InHouse Wellness",
                "collections": [{"url": f"/collections/{c['handle']}", "title": c["title"]} for c in cols]}
    src = next((u for u in r["provenance"]["origin_urls"] if not u.endswith(".json") and not u.endswith(".pdf")),
               r["heat_type"]["source_url"])
    handle, label = BROWSE[heat]
    return {"sold": False, "manufacturer_url": src, "manufacturer_host": host(src),
            "browse_url": f"/collections/{handle}", "browse_label": label}


def page_data(r, handle, title, nav):
    url = BASE + MODEL_PREFIX + handle
    lo, hi = int(r["capacity_min"]["value"]), int(r["capacity_max"]["value"])
    key = [fact("Heat type", r["heat_type"], r["heat_type"]["value"].capitalize(), "heat_type"),
           fact("Capacity", r["capacity_min"], people(lo, hi, up_to(r)), "capacity", raw=[lo, hi])] + dims_rows(r)
    key[1]["verified"] = max(r["capacity_min"]["observed_at"], r["capacity_max"]["observed_at"])
    elec = electrical_rows(r)
    specs = []
    for lab, f, fm, path in spec_fields(r):
        key_ = path.split(".")[-1]
        if path.startswith("dimensions.assembled.") and not has_rect_dims(r) and ok(r["dimensions"]["exterior"]):
            continue    # the exterior is stated in its own shape (key facts); no W/D/H rows beside it
        if path.startswith("electrical.") and key_ in SEE_CIRCUITS and not ok(f) and r["electrical"]["circuits"]:
            specs.append(see_circuits(lab, path))
            continue
        specs.append(fact(lab, f, fm(f["value"]) if f.get("value") is not None else GAP, path))
    shown = [row for row in key + elec + specs if row["state"] in ("value", "option")]
    verified = max(x["verified"] for x in shown if x.get("verified"))
    evidence_fields = [(p, f) for _, f, _, p in spec_fields(r)] + [("capacity", r["capacity_min"])] + \
                      [(f"electrical.circuits[{i}]", c["voltage"]) for i, c in enumerate(r["electrical"]["circuits"])] + \
                      [(f"electrical.circuits[{i}].amperage", c["stated_amperage"]) for i, c in enumerate(r["electrical"]["circuits"])]
    snips, dropped = snippets(evidence_fields, r)
    answer = answer_sentence(r, title)
    e = r["electrical"]
    elec_bits = []
    if e["circuits"]:
        elec_bits.append(f"{len(e['circuits'])} labelled circuit{'s' if len(e['circuits']) > 1 else ''}")
    elif ok(e["supply_voltage"]):
        elec_bits.append(e["supply_voltage"]["value"] + (f", {num(e['stated_amperage']['value'])} A" if ok(e["stated_amperage"]) else ""))
    if ok(e["heater_kw"]):
        elec_bits.append(f"{num(e['heater_kw']['value'])} kW heater")
    dim = r["dimensions"]["assembled"]
    size = (f"{num(dim['width_in']['value'])} × {num(dim['depth_in']['value'])} × {num(dim['height_in']['value'])} in"
            if has_rect_dims(r) else exterior_text(r["dimensions"]["exterior"]["value"]))
    who = ('up to ' if up_to(r) else '') + ('1 person' if lo == hi == 1 else (f'{lo} people' if lo == hi else f'{lo} to {hi} people'))
    meta = (f"Verified specs for the {title}: {r['heat_type']['value']} sauna, {who}, {size}"
            + (f", {', '.join(elec_bits)}" if elec_bits else "") + ". Every value cites the manufacturer.")
    ld = jsonld_model(r, title, url, verified)
    mn = model_number_display(r)
    sells_brand = brand_sold(r)
    # Title tag (go-live design, approved): the model number is added ONLY for brands InHouse Wellness
    # does not sell (a mapping can miss a model INH sells; the brand test cannot), only when a single
    # model number is verified, and never when the title already carries it. URLs and handles never change.
    seo_title = (f"{title} ({mn}): Verified Specs & Electrical Requirements"
                 if mn and not sells_brand and "/" not in mn and mn.lower() not in title.lower()
                 else f"{title}: Verified Specs & Electrical Requirements")
    pd = {"inh_id": r["inh_id"], "handle": handle, "url": url, "path": MODEL_PREFIX + handle, "title": title,
            "seo_title": seo_title, "seo_description": meta, "model_number": mn, "inh_sells_brand": sells_brand,
            "brand": r["identity"]["brand"]["value"], "heat_type": r["heat_type"]["value"],
            "capacity_label": capacity_label(r), "supply_voltage": e["supply_voltage"]["value"] if ok(e["supply_voltage"]) else "",
            "placement": r["placement"]["value"] if ok(r["placement"]) else "",
            "verified_date": verified, "answer": answer, "key_facts": key, "electrical": elec,
            "ask_seller": ask_seller(r), "specs": [x for x in specs if x["state"] != "gap"],
            "spec_gaps": [{"label": x["label"], "field": x["field"]} for x in specs if x["state"] == "gap"], "snippets": snips, "snippets_withheld_by_health_gate": dropped,
            "cite": {"text": f"{title}. {DB_NAME}. {url}. Verified {verified}.", "corrections": CORRECTIONS},
            "store": store_block(r, nav),
            "similar": None if sells_brand else similar_models(r, nav),
            "disclosure": "InHouse Wellness sells some of the brands listed.",
            "methodology_path": METHOD_PATH, "hub_path": HUB_PATH, "jsonld": ld}
    number_sources(pd)
    pd["hub_power"] = hub_power(pd)
    return pd


def model_number_display(r):
    f = r["identity"]["model_number"]
    return f["value"].replace("|", " / ") if ok(f) else None


SOURCE_GRADE_ORDER = ["certified", "documented", "listed", "reviewer_measured", "claimed"]


def number_sources(pd):
    """Footnotes: every cited URL gets one number, in order of first appearance down the page; each
    row and quote carries `source_n`; `sources` lists each URL once with the grades of the values that
    cite it and the date it was fetched. The row keeps `source_url` for the value-match check."""
    info = {}
    rows = pd["key_facts"] + pd["electrical"] + pd["specs"] + pd["snippets"]
    for row in rows:
        u = row.get("source_url")
        if not u:
            continue
        s = info.setdefault(u, {"n": len(info) + 1, "url": u, "host": host(u), "grades": set(), "fetched": set()})
        row["source_n"] = s["n"]
        if row.get("grade") in SOURCE_GRADE_ORDER:
            s["grades"].add(row["grade"])
        if row.get("fetched"):
            s["fetched"].add(row["fetched"])
    pd["sources"] = [{"n": s["n"], "url": s["url"], "host": s["host"],
                      "grades": " · ".join(GRADE_LABEL[g] for g in SOURCE_GRADE_ORDER if g in s["grades"]),
                      "fetched": ", ".join(sorted(s["fetched"]))} for s in sorted(info.values(), key=lambda x: x["n"])]
    return pd


def hub_power(pd):
    """The hub's Power supply cell, read from the rows the model page itself renders."""
    rows = pd["electrical"]
    sv = next((x for x in rows if x["field"] == "electrical.supply_voltage"), None)
    if sv and sv["state"] == "value":
        return sv["text"]
    if any(x.get("circuit") for x in rows):
        return "Multiple circuits"
    if any(x["state"] == "option" for x in rows):
        return "Depends on heater"
    return GAP


def series_key(r):
    """(brand, series words from the model name). An empty series ('Maxxus Far IR Sauna') is its own
    group: two unnamed models are never assumed to be variants of each other."""
    from verified_build import series_name
    s = series_name(r["identity"]["model_name"]["value"] or "")
    return (r["identity"]["brand"]["value"], s) if s else (r["identity"]["brand"]["value"], "#" + r["inh_id"])


CRITERIA_FULL = "Same heat type and placement, similar capacity"
CRITERIA_HEAT = "Same heat type, similar capacity"


def similar_models(r, nav):
    """Up to 3 InHouse-sold models with a product mapping, by a fixed rule (approved 2026-09-29):
    same verified heat type; same verified placement WHEN this page's placement is verified (else
    heat type only, and the criteria line says so); nearest verified capacity (distance between range
    midpoints); one model per series (the nearest in capacity, ties to the shorter title); remaining
    ties by title. Never a claim of equivalence."""
    heat = r["heat_type"]["value"]
    handle_, label = BROWSE[heat]
    use_placement = ok(r["placement"])
    out = {"criteria": CRITERIA_FULL if use_placement else CRITERIA_HEAT, "items": [],
           "collection_url": f"/collections/{handle_}", "collection_label": label}
    mid = (r["capacity_min"]["value"] + r["capacity_max"]["value"]) / 2
    best = {}
    for c in _dataset_records():
        m = nav["mapped"].get(c["inh_id"])
        if not m or c["inh_id"] == r["inh_id"] or not (ok(c["heat_type"]) and ok(c["capacity_min"]) and ok(c["capacity_max"])):
            continue
        if c["heat_type"]["value"] != heat:
            continue
        if use_placement and not (ok(c["placement"]) and c["placement"]["value"] == r["placement"]["value"]):
            continue
        t = c["identity"]["display_title"]
        cand = (abs((c["capacity_min"]["value"] + c["capacity_max"]["value"]) / 2 - mid), len(t), t, m["product_handle"])
        k = series_key(c)
        if k not in best or cand < best[k]:
            best[k] = cand
    seen = set()
    for dist, _, t, ph in sorted(best.values(), key=lambda x: (x[0], x[2])):
        if ph in seen:
            continue
        seen.add(ph)
        out["items"].append({"title": t, "url": f"/products/{ph}"})
        if len(out["items"]) == 3:
            break
    return out


_DS = None


def _dataset_records():
    global _DS
    if _DS is None:
        _DS = [x for x in load_dataset()["records"] if x["status"] == "published"]
    return _DS


def jsonld_model(r, title, url, verified):
    props = []
    e = r["electrical"]
    def add(name, f, unit=None, fmt=lambda v: v):
        if ok(f):
            p = {"@type": "PropertyValue", "name": name, "value": fmt(f["value"])}
            if unit:
                p["unitText"] = unit
            props.append(p)
    add("Heat type", r["heat_type"])
    add("Capacity (minimum)", r["capacity_min"], "people")
    add("Capacity (maximum)", r["capacity_max"], "people")
    for k, n in (("width_in", "Exterior width"), ("depth_in", "Exterior depth"), ("height_in", "Exterior height")):
        add(n, r["dimensions"]["assembled"][k], "in")
    ext = r["dimensions"]["exterior"]
    if not has_rect_dims(r) and ok(ext):
        for p_ in ext["value"]["parts"]:
            props.append({"@type": "PropertyValue", "name": f"Exterior {p_['label'].lower()}", "value": p_["inches"], "unitText": "in"})
    add("Supply voltage", e["supply_voltage"])
    add("Stated amperage", e["stated_amperage"], "A")
    add("Circuits required", e["circuits_required"])
    add("Heater power", e["heater_kw"], "kW")
    product = {"@context": "https://schema.org", "@type": "Product", "name": title, "url": url,
               "brand": {"@type": "Brand", "name": r["identity"]["brand"]["value"]},
               "category": "Sauna", "additionalProperty": props}
    if ok(r["identity"]["model_number"]):
        product["model"] = r["identity"]["model_number"]["value"].split("|")[0]
        if "|" not in r["identity"]["model_number"]["value"]:
            product["mpn"] = r["identity"]["model_number"]["value"]   # one verified model number only
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Sauna database", "item": BASE + HUB_PATH},
        {"@type": "ListItem", "position": 3, "name": title, "item": url}]}
    return [product, crumbs]


# ------------------------------------------------------------- methodology --

def methodology_html(ds, pages, updated: str) -> str:
    """The methodology page body. Counts come from the dataset; the clause is read from CLAUDE.md."""
    clause = re.search(r"(?s)> \*\*Editorial independence\.\*\*(.*?)\n\nGovernance", (ROOT / "CLAUDE.md").read_text()).group(1)
    clause = "Editorial independence. " + re.sub(r"\s*\n>\s*", " ", clause).strip()
    rep = threshold_report(ds)
    below = rep["totals"]["published"] - rep["totals"]["meets"]
    backlog = [r for r in ds["records"] if r["status"] == "backlog"]
    ident = sum(1 for r in backlog if any(w["rule"] == "R3_IDENTITY" for w in r["withheld_reasons"]))
    consist = len(backlog) - ident
    bl = json.loads((ROOT / "data/verified/internal/backlog.json").read_text())["leads_without_origin_page"]
    unreachable = sum(1 for b in bl if b["reason"].startswith("origin source not fetchable"))
    no_page = len(bl) - unreachable
    blocked_brands = len({b["brand"] for b in bl if b["reason"].startswith("origin source not fetchable")})
    miss = rep["below_threshold_missing_field_counts"]
    brands = Counter(p["brand"] for p in pages)
    e = html.escape
    grades = "".join(f"<dt>{e(GRADE_LABEL[g])}</dt><dd>{e(GRADE_DEFINITION[g])}</dd>" for g in GRADE_LABEL)
    brand_rows = "".join(f"<li>{e(b)}: {n}</li>" for b, n in sorted(brands.items()))
    miss_rows = "".join(f"<li>{e(k)}: {v}</li>" for k, v in miss.items() if not k.startswith("ledger"))
    return f"""<p class="inhv-meta">Last updated {e(updated)}. Responsible for the data: {e(RESPONSIBLE)}. Corrections: <a href="mailto:{CORRECTIONS}">{CORRECTIONS}</a>.</p>
<h2>What this database is</h2>
<p>A reference of home sauna specifications, with the electrical requirements first. Every value on a model page is copied from a source we can link to, and shows that link, a grade and the date we read it. Where no source we could read states a single value, the page says <strong>{GAP}</strong> and lists the question to ask the seller instead of guessing.</p>
<h2>Where values come from</h2>
<ol>
<li><strong>The manufacturer's own product page.</strong> Graded <em>Listed</em>.</li>
<li><strong>The manufacturer's own manual or specification sheet</strong>, linked from its own site. Graded <em>Documented</em>. A figure in a manual counts for a model only when the manual ties it to that model's number.</li>
<li><strong>A distributor the manufacturer names</strong>, when the manufacturer publishes nothing itself. No value in the current database comes from one.</li>
</ol>
<p>Retailer pages are never used as evidence, including InHouse Wellness's own product pages. Two brands, Maxxus and Dynamic Saunas, are sourced from their parent company's site because the parent's own published warranty documents state that it manufactures or distributes them; each of those records links that document.</p>
<p>When a source states two different values for the same thing, or the value depends on an option the buyer chooses, we publish neither. When a page states a capacity both as a range and as a single figure inside that range, we publish the widest range the manufacturer states and label it as theirs.</p>
<h2>Grades</h2>
<dl class="inhv-grades">{grades}</dl>
<h2>Editorial independence</h2>
<blockquote>{e(clause)}</blockquote>
<h2>Gaps</h2>
<p>Every gap on a model page reads <strong>{GAP}</strong>. It means no source we could read states a single value for that field. It does not mean the manufacturer never states it: a value may be printed somewhere we have not read, or stated in a way we could not attribute to one model. Each model page turns its electrical gaps into questions to ask the seller.</p>
<h2>What gets a page, and what does not</h2>
<p>A model gets a page only when its manufacturer's sources give us a verified heat type, capacity, exterior dimensions and at least one electrical value. {len(pages)} models meet that today:</p>
<ul>{brand_rows}</ul>
<p>{below} more models are in the dataset without a page because at least one of those is missing. Counted by what is missing (a model can miss more than one):</p>
<ul>{miss_rows}</ul>
<p>{len(backlog)} further records are held back entirely: {ident} because the manufacturer's sources do not let us tell the model apart from another one, and {consist} because the manufacturer's own stated values are inconsistent with each other. {no_page} models we track have no page on their manufacturer's own site that we could match, and {unreachable} more belong to {blocked_brands} manufacturers whose sites we could not read within our fetching rules.</p>
<h2>How we fetch</h2>
<p>We read each site's robots.txt first and never request a page it disallows, send at most one request every two seconds to any site, identify ourselves in every request, and never bypass a security error.</p>
<h2>Corrections</h2>
<p>If a value is wrong or out of date, email <a href="mailto:{CORRECTIONS}">{CORRECTIONS}</a> with the page address and the source that shows the correct value. Corrections are made from the manufacturer's own sources, whoever reports them.</p>
"""


def build(updated: str):
    ds = load_dataset()
    nav = load_navigation()
    PAGES_OUT.mkdir(parents=True, exist_ok=True)
    for f in PAGES_OUT.glob("*.json"):
        f.unlink()
    pages = []
    for r, handle, title, _ in page_records(ds):
        pd = page_data(r, handle, title, nav)
        pages.append(pd)
        (PAGES_OUT / f"{handle}.json").write_text(json.dumps(pd, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    pages.sort(key=lambda p: (p["brand"], p["title"]))
    (PAGES_OUT.parent / "methodology.html").write_text(methodology_html(ds, pages, updated))
    index = [{k: p[k] for k in ("handle", "path", "title", "brand", "heat_type", "capacity_label", "supply_voltage",
                               "placement", "verified_date", "inh_id")} for p in pages]
    (PAGES_OUT.parent / "pages-index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    return pages


INTERNAL_KEYS = {"offers", "gap_diagnosis"}


def record_payload(r) -> dict:
    """The record as it may leave the repo: every offer (and so every price) removed (D-G), and
    the Round 3 gap diagnosis, which is internal, quotes raw page text (prices included) and is
    not rendered until a later round decides its wording."""
    return {k: v for k, v in r.items() if k not in INTERNAL_KEYS}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--updated", default=None, help="methodology 'last updated' date (default: latest verified date)")
    ap.add_argument("--preliminary", metavar="REVIEW_CSV", default=None,
                    help="Round 3: page data for new pages from PROPOSED titles/handles (local renders only)")
    a = ap.parse_args(argv)
    if a.preliminary:
        print(f"{build_preliminary(a.preliminary)} preliminary page data files -> out/verified/pages-preliminary")
    if a.threshold:
        print(json.dumps(threshold_report(load_dataset()), indent=2, ensure_ascii=False))
    if a.build:
        ds = load_dataset()
        upd = a.updated or max(pd["verified_date"] for pd in
                               (page_data(r, h, t, load_navigation()) for r, h, t, _ in page_records(ds)))
        pages = build(upd)
        print(f"{len(pages)} page data files -> {PAGES_OUT.relative_to(ROOT)}; methodology updated {upd}")
    return 0



def build_preliminary(review_csv: str, out_dir: Path = ROOT / "out/verified/pages-preliminary"):
    """Round 3: page data for records that newly meet the threshold, from the PROPOSED title and
    handle in the review CSV. For local renders only; nothing here is final until its row is approved."""
    import csv
    ds = load_dataset()
    nav = load_navigation()
    rows = {r["inh_id"]: r for r in csv.DictReader(open(review_csv))}
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.json"):
        f.unlink()
    n = 0
    for r, t in threshold(ds):
        if t["meets"] and r["inh_id"] in rows:
            row = rows[r["inh_id"]]
            pd = page_data(r, row["proposed_handle"], row["proposed_title"], nav)
            pd["preliminary"] = True
            (out_dir / f"{row['proposed_handle']}.json").write_text(json.dumps(pd, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


if __name__ == "__main__":
    sys.exit(main())
