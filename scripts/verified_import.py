#!/usr/bin/env python3
"""InHouse Wellness Verified — import from Infinite Sauna's published dataset.

ROUND 1 PART A: DRY RUN ONLY. Writes a report to out/verified/, never a dataset.

    python3 scripts/verified_import.py --dry-run
    python3 scripts/verified_import.py --dry-run --input data/verified/upstream/<file>.json

Infinite Sauna is read-only: this reads a pinned local snapshot of its public
JSON and nothing else. Problems in its data are handled here and reported.

Stdlib only. Deterministic: same input bytes, same report bytes.

WHAT THE UPSTREAM DATA CAN AND CANNOT SUPPORT
Infinite Sauna attributes sources per RECORD (`source_urls`, `retailer_offers`),
never per field, and none of those URLs is a manual. So no imported value can be
`documented`, and none can name the page it came from. Every imported factual
value is therefore graded `listed` with source_type
`secondary_dataset_record_level` — the lowest factual grade in the table — and
the schema refuses anything higher for that source type. Marketing terms are
`claimed`. Everything else is `not_verified`.

The integrity rules quarantine; they never repair. A record that fails any rule
is withheld with the rule and the reason, including the numbers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data/verified/internal/leads/infinite-sauna-2026-09-21.json"
OUT_DIR = ROOT / "out/verified"
IMPORTER_VERSION = "0.1.0-dryrun"
SOURCE_URL = "https://infinitesauna.com/data/saunas.json"
RECORD_LEVEL_NOTE = ("Infinite Sauna attributes sources per record, not per field; "
                     "see provenance.upstream_source_urls. Not re-checked by INH.")

# The one string the dataset may never contain, anywhere (lint in Part B).
BANNED_PHRASE = "Standard 120V outlet"

# Display brand names. Upstream canonical brand -> the name the manufacturer uses.
BRAND_DISPLAY = {
    "Almost Heaven Saunas": "Almost Heaven",
    "Golden Designs Inc": "Golden Designs",
    "Salus Saunas": "Salus",
    "Sun Home Saunas": "Sun Home",
    "Heavenly Heat Saunas": "Heavenly Heat",
    "Dundalk Leisurecraft": "Dundalk LeisureCraft",
}
# Words stripped from the front of a title before the display brand is re-prefixed.
BRAND_TITLE_TOKENS = [
    "Golden Designs Maxxus", "Dynamic Saunas", "Dynamic", "Golden Designs",
    "LeisureCraft", "Maxxus", "Clearlight", "SaunaLife", "Ripavi", "Scandia",
    "Kohler", "Almost Heaven", "Salus", "Sun Home", "Medical Saunas", "Heavenly Heat",
]
ACRONYMS = {"EMF", "IR", "LED", "GDI", "CT", "MX", "HEM", "KIP", "IS", "C", "II", "III", "FS", "XL", "MW12", "MW16", "MW20", "G3", "G6", "G11"}

RULES = {
    "R1_ELECTRICAL": "Electrical plausibility: heater watts / supply voltage must not exceed the stated amperage",
    "R2_HYBRID": "Hybrid only when the model explicitly combines traditional and infrared systems",
    "R3_IDENTITY": "Canonical identity: one record per configuration, no two records share a display title",
    "R4_TITLE": "Titles: brand + model name + capacity + configuration; no slug as a model number",
    "R5_CAPACITY": "Capacity: ranges parse to min/max; title and field must agree",
}


# ---------------------------------------------------------------- fields --

def fld(value=None, unit=None, grade="not_verified", source_url=None,
        source_type="none", observed_at=None, note=None):
    return {"value": value, "unit": unit, "grade": grade, "source_url": source_url,
            "source_type": source_type, "observed_at": observed_at, "note": note}


def listed(value, release, unit=None, note=None):
    return fld(value, unit, "listed", SOURCE_URL, "secondary_dataset_record_level",
               release, note or RECORD_LEVEL_NOTE)


def claimed(value, release, note):
    return fld(value, None, "claimed", SOURCE_URL, "secondary_dataset_record_level", release, note)


def nv(note=None, unit=None):
    return fld(None, unit, "not_verified", None, "none", None, note)


def na(note=None, unit=None):
    return fld(None, unit, "not_applicable", None, "none", None, note)


# --------------------------------------------------------------- parsing --

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse_kw(raw):
    """'8 kW' / '8.0 kW' -> 8.0. A range ('6-8 kW') is not one rating: None + reason."""
    if raw is None:
        return None, None
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*kW\s*", raw)
    if m:
        return float(m.group(1)), None
    return None, f"upstream heater_kw '{raw}' is not a single rating"


def parse_amps(raw):
    if raw is None:
        return None
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*A\s*", raw)
    return float(m.group(1)) if m else None


def parse_voltages(raw):
    """'120V/240V' -> [120, 240]. Returned in the order stated."""
    if raw is None:
        return []
    return [int(v) for v in re.findall(r"(\d{3})\s*V", raw)]


CAP_RANGE = re.compile(r"(\d+)\s*(?:-|–|to)\s*(\d+)[\s-]*(?:person|people|per)\b", re.I)
CAP_SINGLE = re.compile(r"(\d+)[\s-]*(?:person|people)\b|seats\s+(\d+)|up to\s+(\d+)\s+people|\((\d+)\s*person\)", re.I)


def title_capacity(title: str):
    m = CAP_RANGE.search(title)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = CAP_SINGLE.search(title)
    if m:
        n = int(next(g for g in m.groups() if g))
        return n, n
    return None


SLUG_MODEL = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){3,}$")


def is_slug_model(model: str) -> bool:
    """A model string that is a URL slug: lowercase, 4+ hyphenated words."""
    return bool(SLUG_MODEL.fullmatch(model))


# ------------------------------------------------------------ Rule 4: titles --

EMF_PHRASE = re.compile(r"\b(?:ultra[- ]?low|near[- ]zero|low)\s+emf\b(?:\s*\([^)]*\))?", re.I)
SEPARATORS = re.compile(r"\s+(?:–|—|\||-)\s+")
CAP_PHRASES = [
    CAP_RANGE,
    re.compile(r"\(?\b\d+[\s-]*(?:person|people)\b\)?(?:\s+capacity)?", re.I),
    re.compile(r"\bfits\s+\d+(?:\s*[-–]\s*\d+)?\s+people\b", re.I),
    re.compile(r"\bfor up to \d+ people\b", re.I),
    re.compile(r"\bseats \d+\b", re.I),
    re.compile(r"\bper\b", re.I),
]


def fix_case(word: str) -> str:
    core = re.sub(r"[^A-Za-z0-9-]", "", word)
    if core.upper() in ACRONYMS or re.search(r"\d", core):
        return word
    if core.isupper() and len(core) > 1:
        return word[0] + word[1:].lower() if word[0].isalpha() else word.lower()
    return word


def build_name(title: str, brand_display: str):
    """Returns (model_name, transforms[]). Heuristic and reported, never silent."""
    t = title
    transforms = []
    for ch in "®™“”\"":
        if ch in t:
            t = t.replace(ch, "")
            transforms.append("strip_marks")
    if t.lower().startswith("quick ship - "):
        t = t[len("quick ship - "):]
        transforms.append("strip_quick_ship")
    if t.startswith("NEW "):
        t = t[4:]
        transforms.append("strip_new")
    t2 = re.sub(r"(?i)^[\s*]*(?:new\b[\s*]*)?(?:(?:19|20)\d\d\b[\s*]*)(?:model\b[\s*]*)?", "", t)
    if t2 != t:
        t = t2
        transforms.append("strip_year")
    t2 = re.sub(r"\s*\([^)]*\)", "", t)
    if t2 != t:
        t = t2
        transforms.append("strip_parenthetical")
    segs = SEPARATORS.split(t)
    head = segs[0]
    # A named edition that lives after the separator is the model name.
    for s in segs[1:]:
        if re.search(r"\bedition\b", s, re.I) and not re.search(r"\bedition\b", head, re.I):
            head = s
            transforms.append("edition_from_suffix")
            break
    if len(segs) > 1:
        transforms.append("drop_suffix")
    for tok in sorted(BRAND_TITLE_TOKENS, key=len, reverse=True):
        if head.lower().startswith(tok.lower() + " "):
            head = head[len(tok) + 1:]
            break
    new = EMF_PHRASE.sub("", head)
    if new != head:
        transforms.append("strip_emf_claim")
        head = new
    for rx in CAP_PHRASES:
        head = rx.sub("", head)
    head = re.sub(r"\bModel\b", "", head)
    words = head.split()
    cased = [fix_case(w) for w in words]
    if cased != words:
        transforms.append("normalize_caps")
    name = re.sub(r"\s{2,}", " ", " ".join(cased)).strip(" ,-–")
    return name, sorted(set(transforms))


def display_title(brand, name, cmin, cmax, config=None):
    cap = ""
    if cmin and cmax:
        cap = f"{cmin} Person" if cmin == cmax else f"{cmin}–{cmax} Person"
    parts = [f"{brand} {name}".strip()]
    if cap:
        parts.append(cap)
    if config:
        parts.append(config)
    return ", ".join(parts)


# ------------------------------------------------------------- Rule 2: hybrid --

IR_TEXT = re.compile(r"infrared|full spectrum|carbon heating|far ir", re.I)
# A bare "kW" is not traditional evidence: Maxxus prints infrared emitter totals in kW.
TRAD_TEXT = re.compile(r"\bstove\b|harvia|\bkip\b|electric heater|wood[- ]burning", re.I)
HYBRID_WORD = re.compile(r"\bhybrid\b|\bcombination\b", re.I)


def hybrid_check(r):
    text = " ".join(filter(None, [r.get("title"), r.get("heater")]))
    ir_text, trad_text = bool(IR_TEXT.search(text)), bool(TRAD_TEXT.search(text))
    word = bool(HYBRID_WORD.search(r["title"]))
    has_spec, has_kw = bool(r.get("spectrum")), bool(r.get("heater_kw"))
    explicit = (ir_text and trad_text) or (word and has_spec and has_kw)
    up = r["type"]
    if up == "Hybrid":
        if explicit:
            return None
        return ("upstream type Hybrid, but neither the title nor the heater text names both "
                f"a traditional heater and an infrared system (title: '{r['title']}'; "
                f"spectrum field: {r.get('spectrum')!r}; heater_kw: {r.get('heater_kw')!r})")
    if word or explicit:
        why = "the title says hybrid/combination" if word else "the title/heater text names both systems"
        return (f"upstream type {up}, but {why} (title: '{r['title']}'; heater: {r.get('heater')!r}; "
                f"heater_kw: {r.get('heater_kw')!r}). Conflict left unresolved: needs a manual")
    if up == "Infrared" and has_kw and not IR_TEXT.search(r["title"]):
        return (f"upstream type Infrared, but the record carries a heater rating ({r.get('heater_kw')}) and "
                f"the title never says infrared (title: '{r['title']}'). Heat type unresolved: needs a manual")
    return None


# ---------------------------------------------------------- Rule 1: electrical --

def electrical_check(r):
    kw, _ = parse_kw(r.get("heater_kw"))  # missing-ok: parser returns None for an absent value; None is withheld, never published
    amps = parse_amps(r.get("amperage"))  # missing-ok: parser returns None for an absent value; None is withheld, never published
    volts = parse_voltages(r.get("voltage"))  # missing-ok: parser returns None for an absent value; None is withheld, never published
    # Evaluated on every heat type: watts / volts above the stated amperage is impossible
    # whether the kW is a stove rating or an emitter total.
    if kw is None or amps is None or not volts:
        return None, "not_evaluable"
    bad = [(v, kw * 1000 / v) for v in volts if kw * 1000 / v > amps]
    if not bad:
        return None, "pass"
    detail = "; ".join(f"{kw:g} kW at {v}V = {a:.1f} A > {amps:g} A stated" for v, a in bad)
    return (f"upstream states {r.get('voltage')}, {r.get('amperage')}, {r.get('heater_kw')}: {detail}. "
            "Impossible as stated; not resolved from a manual in this round"), "fail"


# ---------------------------------------------------------------- mapping --

def map_record(r, release, sha):
    brand = BRAND_DISPLAY.get(r["brand"], r["brand"])
    heat = {"Traditional": "traditional", "Infrared": "infrared", "Hybrid": "hybrid"}[r["type"]]
    name, transforms = build_name(r["title"], brand)
    tc = title_capacity(r["title"])
    fc = r.get("capacity")
    cmin, cmax = (tc if tc else (fc, fc))

    model = r["model"]
    components = model.split("|") if "|" in model else None
    if is_slug_model(model):
        model_f = nv("Model number not documented (upstream model field is a URL slug)")
        transforms.append("slug_model_withheld")
    else:
        model_f = listed(model, release)

    kw, kw_reason = parse_kw(r.get("heater_kw"))  # missing-ok: parser returns None for an absent value; None is withheld, never published
    volts = r.get("voltage")
    amps = parse_amps(r.get("amperage"))  # missing-ok: parser returns None for an absent value; None is withheld, never published
    plug = r.get("plug")

    if heat == "infrared":
        heater_kw = (nv("upstream gives a kW figure on an infrared record; not published as a heater rating")
                     if r.get("heater_kw") else na("no traditional heater on an infrared model"))
    elif kw is not None:
        heater_kw = listed(kw, release, "kW")
    else:
        heater_kw = nv(kw_reason, "kW")

    if volts in ("120V", "240V"):
        supply = listed(volts, release)
    elif volts:
        supply = nv(f"upstream states '{volts}', which is not a single supply voltage", None)
    else:
        supply = nv()

    if plug == "NEMA6-30P":
        conn = listed("NEMA 6-30P", release)
    elif plug and "NEMA" in plug and plug.endswith("R"):
        conn = nv(f"upstream names a receptacle ({plug.replace('NEMA', 'NEMA ')}), not a plug")
    elif plug:
        conn = nv("upstream gives a generic household-outlet label, which names no plug "
                  "and is not permission to share a circuit")
    else:
        conn = nv()

    stated_amps = listed(amps, release, "A",
                         "upstream 'amperage' does not say breaker size or draw. " + RECORD_LEVEL_NOTE
                         ) if amps is not None else nv(unit="A")

    ir = heat in ("infrared", "hybrid")
    rec = {
        "schema_version": "0.1.0",
        "inh_id": f"sauna/{slugify(brand)}/{slugify(model if not is_slug_model(model) else r['model_key'])}",
        "category": "sauna",
        "identity": {
            "brand": listed(brand, release),
            "model_number": model_f,
            "model_name": listed(name, release, note="Derived from the upstream title by rule 4. " + RECORD_LEVEL_NOTE) if name else nv(),
            "configuration": nv(),
            "display_title": None,  # set after identity resolution
            "aliases": [],
            **({"package_components": components} if components else {}),
        },
        "heat_type": listed(heat, release),
        "placement": listed(r["placement"].lower(), release),
        "capacity_min": listed(cmin, release, "persons", "Manufacturer-stated capacity. " + RECORD_LEVEL_NOTE) if cmin else nv(),
        "capacity_max": listed(cmax, release, "persons", "Manufacturer-stated capacity. " + RECORD_LEVEL_NOTE) if cmax else nv(),
        "dimensions": {
            "assembled": {k: nv("upstream dimension strings not parsed in Round 1", "in") for k in ("width_in", "depth_in", "height_in")},
            "crated": {k: nv(unit="in") for k in ("width_in", "depth_in", "height_in")},
        },
        "materials": {"wood_species": listed(r["wood"], release) if r.get("wood") else nv()},
        "electrical": {
            "supply_voltage": supply,
            "heater_voltage": nv(),
            "connection_type": conn,
            "circuit_requirement": nv("Not documented"),
            "breaker_amps": nv("no upstream field states a breaker size", "A"),
            "gfci": nv("Not documented"),
            "heater_kw": heater_kw,
            "stated_amperage": stated_amps,
        },
        "infrared": {
            "spectrum": (listed(r["spectrum"], release) if r.get("spectrum") else nv()) if ir else na(),
            "emf_claim": (claimed(r["emf"], release, "Manufacturer terminology, not a measurement")
                          if r.get("emf") else nv()) if ir else na(),
            "red_light": (listed(True, release) if r.get("red_light") else nv()) if ir else na(),
        },
        "thermal": {"max_temp_f": nv("upstream max temperature strings not parsed in Round 1", "F")},
        "warranty": {"stub": True, "summary": listed(r["warranty"], release) if r.get("warranty") else nv()},
        "offers": [{
            "retailer": o["retailer"], "url": o["url"], "price_usd": o.get("price"),
            "reference_price_usd": o.get("reference_price"),
            "retailer_type": {"manufacturer-direct": "manufacturer_direct", "featured": "inh"}.get(o["source_type"], "retailer"),
            "inh_sells": o["source_type"] == "featured", "observed_at": o["checked_at"],
        } for o in sorted(r["retailer_offers"], key=lambda o: (o["retailer"], o["url"]))],
        "provenance": {
            "source_dataset": SOURCE_URL, "source_release": release, "source_sha256": sha,
            "upstream_model_key": r["model_key"], "upstream_source_urls": sorted(r["source_urls"]),
            "importer_version": IMPORTER_VERSION,
        },
    }
    return rec, {"name": name, "brand": brand, "cmin": cmin, "cmax": cmax,
                 "title_cap": tc, "field_cap": fc, "transforms": transforms}


# ---------------------------------------------------------------- import --

def run(input_path: Path):
    raw = input_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    doc = json.loads(raw)
    release = doc["generated_at"][:10]
    upstream = sorted(doc["products"], key=lambda r: r["model_key"])

    quarantine = defaultdict(list)   # model_key -> [(rule, reason)]
    built = {}
    meta = {}
    for r in upstream:
        rec, m = map_record(r, release, sha)
        built[r["model_key"]] = rec
        meta[r["model_key"]] = m
        why = hybrid_check(r)
        if why:
            quarantine[r["model_key"]].append(("R2_HYBRID", why))
        why, _ = electrical_check(r)
        if why:
            quarantine[r["model_key"]].append(("R1_ELECTRICAL", why))
        tc, fc = m["title_cap"], m["field_cap"]
        if tc and fc is not None and not (tc[0] <= fc <= tc[1]):
            quarantine[r["model_key"]].append(("R5_CAPACITY",
                f"title states {tc[0]}{'–%d' % tc[1] if tc[1] != tc[0] else ''} person, capacity field states {fc}"))
        # No capacity anywhere is an ABSENCE, not a contradiction: the field is withheld
        # (not_verified) and the record is listed in the report. Decision D5.
        if not m["name"]:
            quarantine[r["model_key"]].append(("R4_TITLE", f"no model name recoverable from '{r['title']}'"))

    # Rule 3a — Quick Ship: merge into the standard record when no known field disagrees.
    by_name = defaultdict(list)
    for r in upstream:
        if not r["title"].lower().startswith("quick ship"):
            by_name[(r["brand"], slugify(meta[r["model_key"]]["name"]), meta[r["model_key"]]["cmax"])].append(r)
    merges = []
    for r in upstream:
        if not r["title"].lower().startswith("quick ship"):
            continue
        m = meta[r["model_key"]]
        cands = by_name.get((r["brand"], slugify(m["name"]), m["cmax"]), [])
        if not cands:
            merges.append({"quick_ship": r["model"], "outcome": "standalone",
                           "reason": "no standard listing of this model in the source"})
            continue
        std = cands[0]
        diffs = [f for f in ("heater_kw", "wood", "type", "placement", "voltage", "amperage")
                 if r.get(f) and std.get(f) and r.get(f) != std.get(f)]
        if len(cands) > 1:
            quarantine[r["model_key"]].append(("R3_IDENTITY", f"Quick Ship listing matches {len(cands)} standard records; not merged"))
            merges.append({"quick_ship": r["model"], "outcome": "quarantined", "reason": f"{len(cands)} standard candidates"})
            continue
        if diffs:
            # A different configuration is a separate record, distinguished by title (rule 3).
            merges.append({"quick_ship": r["model"], "outcome": "separate_record",
                           "reason": f"differs from {std['model']} on " + ", ".join(f"{f}: {r.get(f)} vs {std.get(f)}" for f in diffs)})
            continue
        target = built[std["model_key"]]
        target["identity"]["aliases"].append({"model_number": r["model"], "reason": "Quick Ship listing of the same configuration"})
        for o in built[r["model_key"]]["offers"]:
            o = dict(o, retailer=o["retailer"] + " (Quick Ship)")
            target["offers"].append(o)
        target["offers"].sort(key=lambda o: (o["retailer"], o["url"]))
        target["provenance"]["upstream_source_urls"] = sorted(set(target["provenance"]["upstream_source_urls"]) | set(r["source_urls"]))
        merges.append({"quick_ship": r["model"], "outcome": "merged", "into": std["model"],
                       "unknown_on_both": [f for f in ("heater_kw", "wood") if not r.get(f) and not std.get(f)]})
        del built[r["model_key"]]

    # Rule 3b — display titles unique; wood is tried as the distinguishing configuration.
    def title_of(k, config=None):
        m = meta[k]
        return display_title(m["brand"], m["name"], m["cmin"], m["cmax"], config)

    by_key_up = {r["model_key"]: r for r in upstream}
    titles = defaultdict(list)
    for k in built:
        titles[title_of(k)].append(k)
    for t, ks in list(titles.items()):
        if len(ks) == 1:
            continue
        # Try each source-stated distinguishing attribute in turn; never invent one.
        resolved = False
        for attr, fmt in (("wood", "{}"), ("heater_kw", "{} heater")):
            vals = [by_key_up[k].get(attr) for k in ks]
            if all(vals) and len(set(vals)) == len(vals):
                for k, v in zip(ks, vals):
                    built[k]["identity"]["configuration"] = listed(fmt.format(v), release)
                resolved = True
                break
        if resolved:
            continue
        for k in ks:
            quarantine[k].append(("R3_IDENTITY",
                f"display title '{t}' shared by {len(ks)} records ({', '.join(sorted(built[x]['identity']['model_number']['value'] or x for x in ks))}); "
                "no distinguishing configuration in the source"))
    for k, rec in built.items():
        cfg = rec["identity"]["configuration"]["value"]
        rec["identity"]["display_title"] = title_of(k, cfg)

    passing = {k: v for k, v in built.items() if k not in quarantine}
    held = {k: v for k, v in built.items() if k in quarantine}
    return upstream, built, passing, held, quarantine, merges, meta, sha, release


# ---------------------------------------------------------------- report --

def has(f):
    return f["grade"] not in ("not_verified", "not_applicable")


def coverage(recs, upstream_by_key):
    rows = defaultdict(lambda: Counter())
    for rec in recs:
        b = rec["identity"]["brand"]["value"]
        e = rec["electrical"]
        c = rows[b]
        c["n"] += 1
        c["inh"] += any(o["inh_sells"] for o in rec["offers"])
        c["voltage"] += has(e["supply_voltage"])
        c["breaker_amps"] += has(e["breaker_amps"])
        c["stated_amperage"] += has(e["stated_amperage"])
        c["connection_type"] += has(e["connection_type"])
        if rec["heat_type"]["value"] != "infrared":
            c["kw_den"] += 1
            c["heater_kw"] += has(e["heater_kw"])
        c["documented_any"] += any(f["grade"] == "documented" for f in e.values())
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", required=True,
                    help="Round 1 Part A: report only; no dataset is written")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    a = ap.parse_args(argv)

    upstream, built, passing, held, quarantine, merges, meta, sha, release = run(a.input)
    by_key = {r["model_key"]: r for r in upstream}

    per_rule = Counter(rule for items in quarantine.values() for rule in {x[0] for x in items})
    qlist = []
    for k in sorted(quarantine):
        r = by_key[k]
        qlist.append({"model": r["model"], "brand": r["brand"], "upstream_title": r["title"],
                      "inh_sells": bool(r.get("inhouse_url")),
                      "rules": [{"rule": rule, "reason": why} for rule, why in quarantine[k]]})

    all_recs = list(built.values())
    cov = coverage(all_recs, by_key)
    inh = [x for x in all_recs if any(o["inh_sells"] for o in x["offers"])]
    non = [x for x in all_recs if not any(o["inh_sells"] for o in x["offers"])]

    def share(rs, path):
        n = len(rs)
        k = sum(1 for x in rs if has(path(x)))
        return {"n": n, "with_value": k, "pct": round(100 * k / n, 1) if n else None}

    trad = lambda rs: [x for x in rs if x["heat_type"]["value"] != "infrared"]
    skew = {grp: {
        "records": len(rs),
        "supply_voltage": share(rs, lambda x: x["electrical"]["supply_voltage"]),
        "breaker_amps": share(rs, lambda x: x["electrical"]["breaker_amps"]),
        "stated_amperage": share(rs, lambda x: x["electrical"]["stated_amperage"]),
        "connection_type": share(rs, lambda x: x["electrical"]["connection_type"]),
        "heater_kw_traditional_and_hybrid": share(trad(rs), lambda x: x["electrical"]["heater_kw"]),
    } for grp, rs in (("inh_sells", inh), ("not_sold_by_inh", non))}

    banned_hits = sum(json.dumps(x).count(BANNED_PHRASE) for x in all_recs)
    report = {
        "importer_version": IMPORTER_VERSION,
        "input": str(a.input.relative_to(ROOT)), "input_sha256": sha, "source_release": release,
        "upstream_records": len(upstream),
        "after_identity_resolution": len(built),
        "passing": len(passing),
        "quarantined": len(held),
        "quarantined_per_rule": {r: per_rule.get(r, 0) for r in RULES},
        "rules": RULES,
        "quick_ship": merges,
        "rule4_transforms": dict(sorted(Counter(t for m in meta.values() for t in m["transforms"]).items())),
        "banned_phrase_occurrences": banned_hits,
        "grades_used": dict(sorted(Counter(
            f["grade"] for x in all_recs for blk in ("electrical", "infrared") for f in x[blk].values()).items())),
        "coverage_by_brand": {b: dict(sorted(c.items())) for b, c in sorted(cov.items())},
        "coverage_inh_vs_not": skew,
        "quarantine": qlist,
        "capacity_withheld": sorted(by_key[k]["model"] for k, x in built.items()
                                    if x["capacity_max"]["grade"] == "not_verified"),
        "sample_titles": sorted(x["identity"]["display_title"] for x in passing.values())[:400],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "dry-run-report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"upstream {len(upstream)} -> {len(built)} after identity resolution; "
          f"passing {len(passing)}, quarantined {len(held)}")
    for r in RULES:
        print(f"  {r:14} {per_rule.get(r, 0)}")
    print(f"banned phrase occurrences: {banned_hits}")
    print(f"report: {out.relative_to(ROOT)}  sha256 {hashlib.sha256(out.read_bytes()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
