#!/usr/bin/env python3
"""Electrical tool, Round 1 Part B: build the tool's data and the server-rendered page bodies.

    .venv/bin/python scripts/electrical_build.py              # writes the outputs below
    .venv/bin/python scripts/electrical_build.py --check      # rebuilds in memory; exit 1 on drift
    .venv/bin/python scripts/electrical_build.py --self-test

Outputs (all committed, all deterministic):
    assets/inh-electrical-data.json        the tool's model list, quotes and sizing charts
    data/electrical/pages/<handle>.html    page bodies: 3 answer pages, methodology, tool fallback
    data/electrical/pages/index.json       handle -> title, template, SEO description

THE RULE THIS ROUND (Part B §1): only what a manufacturer states is shown. A circuit or breaker is
quoted in the manufacturer's own words, as a verbatim substring of the evidence the database holds
for that value, never parsed into a cleaner number and never reworded. Nothing here computes a
breaker size, a wire gauge or a code minimum. The one calculation is the heater's current draw,
amps = kW x 1000 / volts, made only when the rated kW AND the heater's voltage are both sourced, and
labelled as calculated. kW is never derived from volts x amps.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

ASSET = ROOT / "assets/inh-electrical-data.json"
PAGES = ROOT / "data/electrical/pages"
CHARTS = ROOT / "data/electrical/sizing-charts.json"
GAPS = ROOT / "data/electrical/known-gaps.json"
DEAD = ROOT / "data/electrical/dead-links.json"

TOOL = {"handle": "sauna-electrical-requirements", "suffix": "inh-electrical-tool",
        "title": "Sauna Electrical Requirements and Heater Size"}
SIZING = {"handle": "sauna-heater-size-calculator", "suffix": "inh-electrical-tool",
          "title": "Sauna Heater Size Calculator"}
METHOD = {"handle": "sauna-electrical-methodology", "suffix": "inh-electrical-page",
          "title": "How the Sauna Electrical Tool Works"}
ANSWER_6 = {"handle": "6-kw-sauna-heater-breaker-size", "suffix": "inh-electrical-page", "kw": 6.0,
            "title": "What Size Breaker Does a 6 kW Sauna Heater Need?"}
ANSWER_8 = {"handle": "8-kw-sauna-heater-breaker-size", "suffix": "inh-electrical-page", "kw": 8.0,
            "title": "What Size Breaker Does an 8 kW Sauna Heater Need?"}
ANSWER_IR = {"handle": "infrared-sauna-dedicated-circuit", "suffix": "inh-electrical-page",
             "title": "Does an Infrared Sauna Need a Dedicated Circuit?"}
ALL_PAGES = [TOOL, SIZING, METHOD, ANSWER_6, ANSWER_8, ANSWER_IR]

DB_NAME = "InHouse Wellness Verified Sauna Database"
LOCAL_CODE_LINE = ("Local electrical codes vary. The manufacturer's installation manual and your local code govern, "
                   "and a licensed electrician sizes and installs the circuit.")
NO_CIRCUIT_LINE = ("The manufacturer doesn't publish a circuit requirement for this model in the sources we've verified. "
                   "Your electrician sizes the circuit to your local code.")
NOT_STATED_CELL = "Not stated in the manufacturer sources we've verified"
GAP_CELL = "Not yet in our verified record; see the manufacturer's manual"

FIELD_ORDER = [("breaker_amps", "Breaker"), ("stated_amperage", "Stated amperage"), ("supply_voltage", "Supply voltage"),
               ("connection_type", "Plug / receptacle"), ("circuit_requirement", "Dedicated circuit"),
               ("gfci", "GFCI"), ("heater_kw", "Heater power")]
QUOTE_MAX = 170
# A statement about the circuit, in the manufacturer's words: an amperage tied to a circuit word, or
# a breaker. Used to decide where a quote is SHOWN, never to extract a value from it.
CIRCUIT_RX = re.compile(r"(?i)(\d+\s*-?\s*(?:a|amps?|amperes?)\b[^.]{0,45}\b(circuit|outlet|receptacle|breaker|service)"
                        r"|\b(circuit|outlet|receptacle|breaker|service)\b[^.]{0,30}?\d+\s*-?\s*(?:a|amps?)\b|breaker)")
DEDICATED_CIRCUIT_RX = re.compile(r"(?i)dedicated[^.]{0,30}\b(circuit|receptacle|outlet)")
TRAILING_LABEL_RX = re.compile(r"[^()\n]{0,60}?\(\s*((?:[A-Z]{2,4}-[A-Z0-9]+(?:-[A-Z0-9]+)*\s*(?:/|,|&)?\s*)+)\)")
# Round 3 launch A2 (approved 2026-10-07): a figure IMMEDIATELY followed, on the same line, by "Separate
# Dedicated Circuit(s) Required" (optionally with a count) is quoted through the phrase, verbatim, so the
# count travels with the figure as D12 stores it. GDI-8260-01: "Two 120VAC 15AMP Separate Dedicated
# Circuits Required". No other quote logic changes.
SEPARATE_TAIL_RX = re.compile(r"[ \t]+(?:(?:two|three|four|\d+|\(\d+\))[ \t]+)?separate[ \t]+dedicated[ \t]+circuits?"
                              r"[ \t]+required\b", re.I)
FIGURE_RX = re.compile(r"(?i)\d{2,3}\s*-?\s*(?:V|VAC|A|AMPS?)\b")
MODEL_TOKEN = re.compile(r"\b[A-Z]{2,4}-[A-Z0-9]{3,6}(?:-[A-Z0-9]{1,4})*\b")
# Two label styles: a spec list ("Glass : Tempered Glass Hardware : 120V") puts a SPACE before the
# colon and its label is the one word before it; prose ("Electrical service: 240V") has none and
# may run to three words.
LABEL = re.compile(r"(?:(?<=\s)|^)(?:[A-Z][A-Za-z/&()'-]* : |[A-Z][A-Za-z/&()'-]*(?: [A-Za-z][A-Za-z/&()'-]*){0,1}: )")
# Brand voice: no fear copy. A quote never carries a hazard warning; it ends before the clause that
# does, and a hazard word ahead of the value means the passage is a warning, not a requirement.
FEAR = re.compile(r"(?i)\b(fatal|death|deadly|fire|shock|electrocut\w*|burns?|injur\w*|explosion|hazard\w*)\b")
HEADING = re.compile(r"^(?:[A-Z]{2,}[ ·]+){1,4}(?=[A-Z][a-z])")
SENT_END = re.compile(r"[.!?·](?=\s|$)|\s·\s")
# Flattened spec HTML has no punctuation between items ("…Dedicated Circuit Required Carefully and
# thoroughly…"). After the value, a Title-Case word that is not electrical vocabulary starts the next
# item, so the quote ends before it. Inside parentheses the manufacturer's sentence continues.
CONT = {"dedicated", "circuit", "circuits", "required", "requires", "receptacle", "receptacles", "outlet", "outlets",
        "breaker", "breakers", "gfci", "gfi", "non", "amp", "amps", "ampere", "amperes", "plug", "plugs", "nema",
        "volts", "volt", "watts", "watt", "phase", "hardwired", "hard-wired", "stove", "heater", "control", "lights",
        "music", "recommended", "special", "electrical", "only", "service", "components", "connection", "power",
        "supply", "rated", "twist-lock", "twist-locking", "double", "pole", "standard", "household", "kw", "and", "or"}
LEFT_MAX = 60


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def num(v) -> str:
    return f"{v:g}"


# ------------------------------------------------------------------ quotes --

def anchor_rx(key: str, value):
    """Where in the evidence the value sits. Returns None when the field has no anchor rule."""
    if key in ("stated_amperage", "breaker_amps"):
        return re.compile(rf"(?<![\d.]){re.escape(num(value))}(?:\.0)?\s*-?\s*(?:a|amps?|amperes?)\b", re.I)
    if key in ("supply_voltage", "voltage"):
        n = re.sub(r"\D", "", str(value))
        return re.compile(rf"(?<![\d.]){n}\s*-?\s*(?:v\b|vac\b|volts?\b)", re.I)
    if key == "heater_kw":
        return re.compile(rf"(?<![\d.]){re.escape(num(value))}(?:\.0)?\s*-?\s*kw\b", re.I)
    if key == "connection_type":
        if str(value).lower() == "hardwired":
            return re.compile(r"hard-?wired", re.I)
        parts = str(value).replace("NEMA", "").strip()
        return re.compile(rf"(?:NEMA\s*)?{re.escape(parts)}", re.I)
    if key == "circuit_requirement":
        return re.compile(r"dedicated", re.I)
    if key == "gfci":
        return re.compile(r"GFCI|GFI\b|ground[- ]fault", re.I)
    return None


def quote(field: dict, key: str, own_models: set[str]):
    """The shortest clause of the field's own evidence snippet that carries the value, verbatim.

    Returns {"text", "lead", "trail"}: `text` is an exact substring of the snippet; `lead`/`trail`
    say the quote is cut from a longer passage (rendered as an ellipsis OUTSIDE the quotation
    marks). None when the value cannot be found in its evidence: an unquotable value is not shown
    as a quote, and the caller falls back to the value with its source."""
    ev = (field.get("evidence") or {}).get("snippet") or ""
    if "value" not in field or field["value"] is None:
        return None   # no value, nothing to quote: the caller shows the missing state
    rx = anchor_rx(key, field["value"])
    if not ev or rx is None:
        return None
    # The snippet may join two windows with an ellipsis; a quote never spans one.
    segs, pos = [], 0
    for m in re.finditer(r"\s*…\s*", ev):
        segs.append((pos, m.start()))
        pos = m.end()
    segs.append((pos, len(ev)))
    for a, b in segs:
        seg = ev[a:b]
        tokens = {t.group(0) for t in MODEL_TOKEN.finditer(seg)}
        mid = (field.get("evidence") or {}).get("snippet_starts_mid_word") is True
        for m in rx.finditer(seg):
            got = _clause(ev, seg, a, m, own_models, mid)
            if got is None:
                continue
            inside = [(t.start(), t.group(0)) for t in MODEL_TOKEN.finditer(got["text"])]
            at = got["text"].find(m.group(0))
            if got.pop("trailing", None):
                # r3-electrical D2 (approved): spec-then-label. The parenthesised label right after the
                # requirement names this model; co-labelled models inside that one parenthesis are fine.
                return got
            # A passage naming model numbers is a line table: the quote must name THIS model before the
            # value (label-then-spec, CLAUDE.md "a rating belongs to the model number beside it"), and
            # no other model at all.
            if tokens and (not any(t in own_models and p < at for p, t in inside)
                           or any(t not in own_models for _, t in inside)):
                continue
            return got
    return None


def _clause(ev: str, seg: str, a: int, m, own_models: set[str], mid: bool = False):
    if True:  # noqa: SIM108  (kept flat for the diff; one clause per anchor)
        lo, hi = 0, len(seg)
        for s in SENT_END.finditer(seg):
            if s.end() <= m.start():
                lo = max(lo, s.end())
            elif s.start() >= m.end() and hi == len(seg):
                hi = s.end()
        for lab in LABEL.finditer(seg):
            if lab.start() <= m.start():
                lo = max(lo, lab.start())
            elif lab.start() >= m.end():
                hi = min(hi, lab.start())
        # r3-electrical D2: a parenthesised model list right after the requirement labels IT
        # ("120VAC 15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05)").
        trail = TRAILING_LABEL_RX.match(seg[m.end():])
        trailing = bool(trail and set(MODEL_TOKEN.findall(trail.group(1))) & own_models
                        and not FIGURE_RX.search(seg[m.end():m.end() + trail.start(1)]))
        if trailing:
            prev = seg.rfind(")", 0, m.start())
            lo = max(lo, prev + 1)             # never reach back into the previous row's own label
            hi = m.end() + trail.end()
        else:
            # A line manual lists several models: the clause belongs to the model token before it.
            for t in MODEL_TOKEN.finditer(seg):
                in_parens = seg.rfind("(", 0, t.start()) > seg.rfind(")", 0, t.start())
                if t.start() <= m.start() and in_parens:
                    # "(DYN-6115-05/DYN-6215-05) 120VAC 20AMP": a parenthesised model list closes the
                    # PREVIOUS clause; it never labels the figure after it.
                    lo = max(lo, seg.find(")", t.end()) + 1)
                    continue
                if t.start() <= m.start() and t.group(0) in own_models:
                    lo = max(lo, t.start())
                elif t.start() >= m.end():
                    hi = min(hi, t.start())   # the next model number starts the next row
        sep = None if trailing else SEPARATE_TAIL_RX.match(seg, m.end())
        if sep and sep.end() <= hi:
            hi = sep.end()
        depth, i = 0, m.end()
        for tok in ([] if (trailing or sep) else re.finditer(r"\S+", seg[m.end():hi])):
            t = tok.group(0)
            word = t.strip("()[],.;:*").lower()
            if depth == 0 and re.match(r"[A-Z][a-z]", t.lstrip("(")) and word not in CONT:
                hi = m.end() + tok.start()
                break
            depth += t.count("(") - t.count(")")
            depth = max(depth, 0)
        if m.start() - lo > LEFT_MAX:
            cut = seg.find(" ", m.start() - LEFT_MAX)
            lo = cut + 1 if 0 <= cut < m.start() else lo
        text = seg[lo:hi].rstrip()
        lead_cut, trail_cut = (a + lo) > 0, (a + lo + len(text)) < len(ev)
        # A clause running into the snippet's own edge starts or ends mid-word: drop the fragment.
        # Round 4 A8: a quote opening at the snippet's first character drops that first token when the
        # build recorded the window as cut inside a word ("ARBON MODEL…" was "CARBON MODEL…").
        if a + lo == 0 and (mid or not re.match(r"[A-Z0-9]", text)):
            text = text[text.find(" ") + 1:] if " " in text else text
            lead_cut = True
        if a + hi == len(ev) and not re.search(r"[.!?)]$", text.rstrip()):
            cut = text.rstrip()
            text = cut[:cut.rfind(" ")] if " " in cut[(m.end() - lo):] else cut
            trail_cut = True
        if len(text) > QUOTE_MAX:   # a window around the value, cut on word boundaries
            off = text.find(m.group(0))
            s = max(0, off - 70)
            e = min(len(text), off + len(m.group(0)) + 80)
            if s > 0:
                s = text.find(" ", s) + 1
                lead_cut = True
            if e < len(text):
                e = text.rfind(" ", 0, e)
                trail_cut = True
            text = text[s:e]
        hd = HEADING.match(text)
        if hd and hd.end() <= text.find(m.group(0)):
            text, lead_cut = text[hd.end():], True
        fz = FEAR.search(text)
        if fz:
            if fz.start() < text.find(m.group(0)) + len(m.group(0)):
                return None
            cut = max(text.rfind(" and ", 0, fz.start()), text.rfind(",", 0, fz.start()), text.rfind(" which ", 0, fz.start()))
            if cut <= text.find(m.group(0)):
                return None
            text, trail_cut = text[:cut], True
        text = text.strip(" ;,")
        if not text or m.group(0) not in text or text not in ev:
            return None
        out = {"text": text, "lead": lead_cut, "trail": trail_cut}
        if trailing:
            out["trailing"] = True
        return out


def doc_page(field: dict) -> str | None:
    loc = (field.get("evidence") or {}).get("locator") or ""
    m = re.search(r"\b(?:page|p\.)\s*(\d+)", loc, re.I)
    return m.group(1) if m else None


def statement(field: dict, key: str, label: str, own_models: set[str]):
    q = quote(field, key, own_models)
    if q is None:
        return None
    return {"labels": [label], "quote": q, "grade": field["grade"], "source_type": field["source_type"],
            "source_url": field["source_url"], "verified": field["observed_at"], "page": doc_page(field)}


# ------------------------------------------------------------------ models --

def own_model_numbers(r) -> set[str]:
    ident = r["identity"]
    out = set()
    for k in ("model_number", "manufacturer_model_number", "sku", "configuration"):
        f = ident.get(k)
        if isinstance(f, dict) and f.get("value"):
            v = f["value"]
            out.update(v if isinstance(v, list) else [v])
    toks = {str(x).upper() for x in out}
    for x in list(toks):
        toks.update(t.group(0) for t in MODEL_TOKEN.finditer(x))   # "DYN-6210-01 Elite" -> DYN-6210-01
    return toks


def heater_voltage(e: dict):
    """(value, field) of the voltage the HEATER is stated to run on. Same order as Part A."""
    from electrical_coverage import HEATER_PURPOSE
    if e["heater_voltage"]["value"]:
        return e["heater_voltage"]["value"], e["heater_voltage"]
    for c in e["circuits"]:
        p = (c["purpose"]["value"] or "").lower()
        if c["voltage"]["value"] and any(w in p for w in HEATER_PURPOSE):
            return c["voltage"]["value"], c["voltage"]
    if not e["circuits"] and e["supply_voltage"]["value"]:
        return e["supply_voltage"]["value"], e["supply_voltage"]
    return None, None


def manual_url(r) -> str | None:
    urls = set()

    def walk(x):
        if isinstance(x, dict):
            if x.get("source_type") == "manufacturer_manual" and x.get("source_url"):
                urls.add(x["source_url"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk({k: v for k, v in r.items() if k not in ("offers", "gap_diagnosis")})
    dead = {d["url"] for d in json.loads(DEAD.read_text())["dead"]} if DEAD.exists() else set()
    live = sorted(urls - dead)
    return live[0] if live else None


def heater_circuit_value(e: dict):
    """The heater circuit as structured DATABASE values (voltage, amps), for the answer sentence's
    counts only. The table shows the quote, never this tuple."""
    from verified_pages import amperage_is_circuit
    from electrical_coverage import HEATER_PURPOSE
    for c in e["circuits"]:
        p = (c["purpose"]["value"] or "").lower()
        if any(w in p for w in HEATER_PURPOSE) and c["voltage"]["value"] and c["stated_amperage"]["value"]:
            return c["voltage"]["value"], c["stated_amperage"]["value"]
    if e["breaker_amps"]["value"] and e["supply_voltage"]["value"]:
        return e["supply_voltage"]["value"], e["breaker_amps"]["value"]
    sa = e["stated_amperage"]
    if sa["value"] and e["supply_voltage"]["value"] and amperage_is_circuit(sa) and not e["circuits"]:
        return e["supply_voltage"]["value"], sa["value"]
    return None


def model_entry(r, handle: str, title: str, mapped: bool, gaps: dict) -> dict:
    e = r["electrical"]
    own = own_model_numbers(r)
    stmts, seen = [], {}

    def add(s):
        if s is None:
            return
        k = s["quote"]["text"]
        for old in list(seen):
            if k in old or old in k:   # one clause quoted twice for two fields: keep the longer, merge labels
                keep, drop = (seen[old], s) if len(old) >= len(k) else (s, seen[old])
                for lab in drop["labels"]:
                    if lab not in keep["labels"]:
                        keep["labels"].append(lab)
                if keep is s:
                    stmts[stmts.index(seen.pop(old))] = s
                    seen[k] = s
                return
        if k in seen:
            for lab in s["labels"]:
                if lab not in seen[k]["labels"]:
                    seen[k]["labels"].append(lab)
            return
        seen[k] = s
        stmts.append(s)
    for i, c in enumerate(e["circuits"]):
        purpose = c["purpose"]["value"] or f"circuit {i + 1}"
        add(statement(c["stated_amperage"], "stated_amperage", f"Circuit ({purpose})", own))
        add(statement(c["voltage"], "voltage", f"Circuit ({purpose})", own))
    for key, label in FIELD_ORDER:
        f = e[key]
        if f["value"] is not None:
            add(statement(f, key, label, own))
    for s in stmts:
        s["about_circuit"] = bool(CIRCUIT_RX.search(s["quote"]["text"]) or DEDICATED_CIRCUIT_RX.search(s["quote"]["text"])) \
            or any(lab.startswith(("Breaker", "Circuit (", "Dedicated circuit")) for lab in s["labels"])
    kw = e["heater_kw"]["value"]
    hv, hv_field = heater_voltage(e)
    heater = None
    if kw:
        heater = {"kw": kw, "kw_quote": quote(e["heater_kw"], "heater_kw", own), "kw_grade": e["heater_kw"]["grade"],
                  "kw_source_url": e["heater_kw"]["source_url"], "kw_verified": e["heater_kw"]["observed_at"]}
        if hv:
            volts = float(re.sub(r"[^\d.]", "", hv))
            heater.update({"volts": volts, "volts_source_url": hv_field["source_url"],
                           "volts_grade": hv_field["grade"], "volts_verified": hv_field["observed_at"],
                           "draw_amps": round(kw * 1000 / volts, 1)})
    return {
        "handle": handle, "title": title, "brand": r["identity"]["brand"]["value"],
        "heat_type": r["heat_type"]["value"], "inh_sells": mapped,
        "url": f"/pages/sauna-database/{handle}",
        "statements": stmts,
        "circuit_stated": any(s["about_circuit"] for s in stmts),
        "heater": heater, "manual_url": manual_url(r),
        "gap": gaps.get(handle),
        "_heater_circuit": heater_circuit_value(e),
    }


def load_models():
    from verified_pages import load_dataset, page_records
    from electrical_coverage import load
    _, handles, active, mapped, cost = load()
    gaps = {g["handle"]: g for g in json.loads(GAPS.read_text())["gaps"]}
    models = []
    for r, handle, title, _ in page_records(load_dataset()):
        if handle in active:
            models.append(model_entry(r, handle, title, r["inh_id"] in mapped, gaps))
    models.sort(key=lambda m: (m["brand"], m["title"]))
    by_product = {v["product_handle"] for v in mapped.values()}
    product_to_model = {}
    hd = {k: v["handle"] for k, v in handles.items()}
    for rid, v in mapped.items():
        if hd.get(rid) in active:
            product_to_model[v["product_handle"]] = hd[rid]
    # Every priced INH sauna the tool cannot show a live record for gets manual entry, with the
    # reason in words: no record at all, or a record that is not published yet. Never coverage.
    unmapped = sorted(({"handle": x["handle"], "title": x["title"],
                        "reason": "not_live" if x["handle"] in by_product else "no_record"} for x in cost
                       if x["fields"]["price_usd"]["value"] is not None and x["handle"] not in product_to_model),
                      key=lambda p: p["title"])
    return models, unmapped, product_to_model


def as_of(models, charts) -> str:
    return max([m["heater"]["kw_verified"] for m in models if m["heater"] and m["heater"].get("kw_verified")]
               + [s["verified"] for m in models for s in m["statements"] if s["verified"]] + [charts["retrieved"]])


# ------------------------------------------------------------------ render --

def quote_html(s: dict) -> str:
    q = s["quote"]
    t = ("…" if q["lead"] else "") + "“" + esc(q["text"]) + "”" + ("…" if q["trail"] else "")
    return f'<span class="inhe-quote">{t}</span>'


def source_html(s: dict) -> str:
    kind = "manual" if s["source_type"] == "manufacturer_manual" else "manufacturer page"
    pg = f", p. {s['page']}" if s.get("page") else ""
    return (f'<a href="{esc(s["source_url"])}" rel="nofollow noopener" target="_blank">{kind}{pg}</a>')


def grade_label(g: str) -> str:
    return {"listed": "Listed", "documented": "Documented"}.get(g, g)


def circuit_cell(m: dict) -> str:
    """Block elements, not <br>: this theme does not break lines on <br> inside table cells."""
    cs = [s for s in m["statements"] if s["about_circuit"]]
    amp = [s for s in m["statements"] if not s["about_circuit"] and "Stated amperage" in s["labels"]]
    parts = [f'<span class="inhe-line">{quote_html(s)}</span>' for s in cs]
    if not cs:
        parts.append(f'<span class="inhe-line inhe-missing">{NOT_STATED_CELL}</span>')
    for s in amp:
        parts.append(f'<span class="inhe-line"><span class="inhe-note">Amperage stated, not described as a circuit:</span> {quote_html(s)}</span>')
    if m.get("gap"):
        g = m["gap"]
        parts.append(f'<span class="inhe-line inhe-missing">Circuit amperage: {GAP_CELL} '
                     f'(<a href="{esc(g["doc_url"])}" rel="nofollow noopener" target="_blank">manual, p. {esc(g["page"])}</a>)</span>')
    return "".join(parts)


def model_rows(models) -> str:
    rows = []
    for m in models:
        shown = [s for s in m["statements"] if s["about_circuit"] or "Stated amperage" in s["labels"]]
        src = "".join(f'<span class="inhe-line">{grade_label(s["grade"])} · {source_html(s)} · {esc(s["verified"])}</span>'
                      for s in shown) if shown else '<span class="inhe-missing">—</span>'
        rows.append(f'<tr><th scope="row"><a href="{esc(m["url"])}">{esc(m["title"])}</a></th>'
                    f'<td>{circuit_cell(m)}</td><td>{src}</td></tr>')
    return "\n".join(rows)


def table(models, cols=("Model", "What the manufacturer states about the circuit", "Grade · source · verified")) -> str:
    head = "".join(f'<th scope="col">{c}</th>' for c in cols)
    return (f'<table class="inhe-table"><thead><tr>{head}</tr></thead>\n<tbody>\n{model_rows(models)}\n</tbody></table>')


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def kw_answer(models, kw: float) -> tuple[str, list]:
    """Counts what the TABLE shows. A model whose database record holds the heater circuit as values
    is grouped by those values; one whose manufacturer describes a circuit only in words is counted
    as stating a circuit "in other words" (the quote is in the table); never parsed into a number."""
    sel = [m for m in models if m["heater"] and m["heater"]["kw"] == kw]
    groups: dict = {}
    words = []
    for m in sel:
        hc = m["_heater_circuit"]
        if hc:
            groups.setdefault(hc, []).append(m)
        elif m["circuit_stated"]:
            words.append(m)
    parts = [f"{len(v)} state a {esc(hv.replace('V', ' V'))}, {num(a)} A circuit for the heater"
             for (hv, a), v in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    if words:
        parts.append(f"{len(words)} more describe a circuit in other words, quoted below")
    rest = len(sel) - sum(len(v) for v in groups.values()) - len(words)
    art = "an" if num(kw).startswith(("8", "11", "18")) else "a"
    sent = (f"Of the {len(sel)} saunas with {art} {num(kw)} kW heater in the {DB_NAME}, the manufacturers of "
            + ("; ".join(parts) if parts else "none describe a heater circuit")
            + (f"; for the other {rest}, the manufacturer sources we've verified describe no heater circuit." if rest else "."))
    return sent, sel


DEDICATED_REQ = re.compile(r"(?i)dedicated[^.]{0,40}\brequired|requires? a dedicated|required[^.]{0,20}dedicated|must be (?:on|connected to) a dedicated")
DEDICATED_REC = re.compile(r"(?i)recommended dedicated|dedicated[^.]{0,25}recommended")
DEDICATED_ANY = re.compile(r"(?i)\bdedicated\b")


def dedicated_class(m) -> str:
    text = " ".join(s["quote"]["text"] for s in m["statements"])
    if DEDICATED_REQ.search(text):
        return "required"
    if DEDICATED_REC.search(text):
        return "recommended"
    if DEDICATED_ANY.search(text):
        return "specified"
    return "none"


def ir_answer(models) -> tuple[str, list, dict]:
    sel = [m for m in models if m["heat_type"] == "infrared" and m["circuit_stated"]]
    c = {k: [m for m in sel if dedicated_class(m) == k] for k in ("required", "specified", "recommended", "none")}
    sent = (f"Of the {len(sel)} infrared saunas in the {DB_NAME} whose manufacturer states an electrical requirement, "
            f"{len(c['required'])} say a dedicated circuit is required, {len(c['specified'])} call for a dedicated "
            f"outlet or circuit without saying \"required\", {len(c['recommended'])} recommend one, and "
            f"{len(c['none'])} do not mention a dedicated circuit.")
    return sent, sel, c


def cite_block(title: str, handle: str, updated: str) -> str:
    return (f'<aside class="inhe-cite"><h2>Cite this page</h2><p>{DB_NAME}. “{esc(title)}.” InHouse Wellness, '
            f'updated {updated}. https://inhousewellness.com/pages/{handle}</p></aside>')


def page_frame(spec: dict, updated: str, inner: str) -> str:
    return (f'<p class="inhe-updated">Last updated {updated}</p>\n{inner}\n'
            f'<p class="inhe-local">{LOCAL_CODE_LINE}</p>\n'
            f'<p class="inhe-links"><a href="/pages/{TOOL["handle"]}">Check a model in the electrical tool</a> · '
            f'<a href="/pages/{METHOD["handle"]}">How this page is built</a> · '
            f'<a href="/pages/sauna-database">{DB_NAME}</a></p>\n'
            + cite_block(spec["title"], spec["handle"], updated))


def answer_kw_body(models, spec, updated) -> str:
    sent, sel = kw_answer(models, spec["kw"])
    brands = {}
    for m in sel:
        brands[m["brand"]] = brands.get(m["brand"], 0) + 1
    top, n = max(brands.items(), key=lambda kv: (kv[1], kv[0]))
    conc = f'<p class="inhe-note">{n} of the {len(sel)} listed models are from {esc(top)}.</p>' if n * 2 > len(sel) else ""
    inner = (f'<p class="inhe-answer">{sent}</p>\n'
             f'<p>Each row quotes the manufacturer\'s own words, with its grade, source and the date we verified it. '
             f'InHouse Wellness does not calculate a breaker or wire size: those depend on your local code and your '
             f'electrician.</p>\n{conc}\n' + table(sel))
    return page_frame(spec, updated, inner)


def answer_ir_body(models, updated) -> str:
    sent, sel, c = ir_answer(models)
    inner = (f'<p class="inhe-answer">{sent}</p>\n'
             f'<p>Each row quotes the manufacturer\'s own words. A recommendation is not a requirement, and the two '
             f'are counted separately.</p>\n' + table(sel))
    return page_frame(ANSWER_IR, updated, inner)


def methodology_body(models, charts, updated) -> str:
    rows = []
    for ch in charts["charts"]:
        g = ch.get("glass")
        rule = (f'{esc(g["stated"])} ({esc(g["rule_page"])})' if g else "No glass or wall rule stated")
        if ch.get("log_walls"):
            rule += f'; log walls: {esc(ch["log_walls"]["stated"])}'
        sizes = ", ".join(f'{num(r["kw"])} kW' for r in ch["rows"])
        rows.append(f'<tr><th scope="row">{esc(ch["maker"])}</th><td><a href="{esc(ch["url"])}" rel="nofollow noopener" '
                    f'target="_blank">{esc(ch["document"])}</a>, {esc(ch["table_page"])}</td><td>{sizes}</td><td>{rule}</td></tr>')
    not_used = "".join(f"<li>{esc(n['maker'])}: {esc(n['why'])}.</li>" for n in charts["not_used"])
    n_models = len(models)
    n_circ = sum(1 for m in models if m["circuit_stated"])
    n_draw = sum(1 for m in models if m["heater"] and m["heater"].get("draw_amps") is not None)
    inner = f"""<h2>What the tool shows</h2>
<p>The tool covers the {n_models} models published in the {DB_NAME}. For {n_circ} of them the manufacturer states something
about the circuit: a voltage and amperage, a breaker, a receptacle or a dedicated circuit. The tool quotes that statement in
the manufacturer's own words, with its grade, its source and the date we verified it. A quote is copied from the source and
is never reworded or turned into a cleaner number.</p>
<p>Where the manufacturer states nothing about the circuit, the tool says so and shows what is sourced: heater power,
supply voltage, a stated amperage, a plug type. It links the model's manual where we hold one.</p>
<h2>What the tool does not do</h2>
<p>It does not calculate a breaker size, a wire gauge or any code minimum. Electrical codes differ by state and
by city, and by which edition of the National Electrical Code a jurisdiction has adopted. A licensed electrician applies
your local code to your home. The tool never says whether a home can or cannot run a sauna; panel details you enter become
questions for your electrician.</p>
<h2>The one calculation: heater current draw</h2>
<p>Where the manufacturer states the heater's rated power and the voltage it runs on, the tool shows the heater's
current draw, calculated as <code>amps = kW × 1000 ÷ volts</code>. A 6 kW heater on 240 V draws 6 × 1000 ÷ 240 = 25.0 A.
This is the current the heater uses, not a breaker size, and it is labelled as calculated wherever it appears. For
{n_draw} models both inputs are sourced.</p>
<p>The tool never works backwards from volts and amps to power. A stated "240V / 30A" describes the circuit a
manufacturer asks for, not what the heater draws.</p>
<h2>Heater size: manufacturer charts, side by side</h2>
<p>Heater makers publish their own tables of room volume per heater. The tool applies each chart separately to the room
you enter, using that maker's own rule for glass and uninsulated walls, and shows every result. The charts are not
averaged. They disagree, and the disagreement is information. Glass is the clearest case: for each square foot of
glass, Harvia adds about 3.9 cubic feet of volume, HUUM about 3.3 and Tylö 1, while Finnleo, Saunacore and Scandia state
no glass rule at all.</p>
<table class="inhe-table"><thead><tr><th scope="col">Maker</th><th scope="col">Document</th><th scope="col">Heater sizes</th>
<th scope="col">Glass and wall rule, as stated</th></tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table>
<p>Not used this round:</p><ul>{not_used}</ul>
<p>Metric charts (HUUM, and Harvia's glass rule) are applied in metric: the room you enter in feet is converted at
1 ft = 0.3048 m. Saunacore's method divides cubic feet by 50 and picks the next heater size up. Scandia publishes
maximum room sizes only, so it sets no upper limit on heater size.</p>
<h2>When a value is missing</h2>
<p>A missing value is shown as missing, never as zero and never borrowed from a similar model. If a model has no rated
heater power on record, the tool asks for it from the heater's spec plate or the manual; without it, no current draw is
shown. A sauna sold by InHouse Wellness that is not yet in the database gets the same manual entry and is never shown as
covered.</p>
<h2>Sources and independence</h2>
<p>Every value comes from the {DB_NAME}, which copies each value from the manufacturer's own product page or manual and
grades it. InHouse Wellness sells some of the brands listed. Results are published whether or not they favour a brand
InHouse Wellness sells, and InHouse Wellness's own product pages are never used as evidence.
<a href="/pages/sauna-database-methodology">How the database is verified</a>. To report an error, email
<a href="mailto:data@inhousewellness.com">data@inhousewellness.com</a> with the source that shows the correct value.</p>"""
    return page_frame(METHOD, updated, inner)


def tool_fallback_body(updated) -> str:
    return (f'<p class="inhe-updated">Last updated {updated}</p>\n'
            f'<p>Pick a sauna from the {DB_NAME} to see what its manufacturer states about the electrical circuit, in the '
            f'manufacturer\'s own words, or enter a heater\'s power and voltage yourself. A second mode sizes a heater '
            f'for your room against each manufacturer\'s own chart.</p>\n'
            f'<p>The interactive tool needs JavaScript. The same information is on these pages:</p>\n<ul>'
            f'<li><a href="/pages/{ANSWER_6["handle"]}">{ANSWER_6["title"]}</a></li>'
            f'<li><a href="/pages/{ANSWER_8["handle"]}">{ANSWER_8["title"]}</a></li>'
            f'<li><a href="/pages/{ANSWER_IR["handle"]}">{ANSWER_IR["title"]}</a></li>'
            f'<li><a href="/pages/{METHOD["handle"]}">{METHOD["title"]}</a></li>'
            f'<li><a href="/pages/sauna-database">{DB_NAME}</a> (every model page lists its electrical requirements)</li></ul>\n'
            f'<p class="inhe-local">{LOCAL_CODE_LINE}</p>')


def descriptions(models) -> dict:
    s6, _ = kw_answer(models, 6.0)
    s8, _ = kw_answer(models, 8.0)
    return {
        TOOL["handle"]: "What each sauna's manufacturer states about its electrical circuit, quoted and sourced, plus heater sizing by manufacturer chart.",
        SIZING["handle"]: "Size a sauna heater for your room against each manufacturer's own chart, side by side, with glass and wall rules as each maker states them.",
        METHOD["handle"]: "How the sauna electrical tool sources every value, why it calculates no breaker or wire size, and how heater charts are applied.",
        ANSWER_6["handle"]: "The circuit each manufacturer states for saunas with a 6 kW heater, quoted with source and date.",
        ANSWER_8["handle"]: "The circuit each manufacturer states for saunas with an 8 kW heater, quoted with source and date.",
        ANSWER_IR["handle"]: "Whether infrared sauna manufacturers require, call for or recommend a dedicated circuit, quoted with source and date.",
    }


# ------------------------------------------------------------------- build --

def build() -> dict[Path, str]:
    models, unmapped, product_to_model = load_models()
    charts = json.loads(CHARTS.read_text())
    updated = as_of(models, charts)
    public = [{k: v for k, v in m.items() if not k.startswith("_")} for m in models]
    data = {"schema": "inh-electrical/1", "updated": updated, "db_name": DB_NAME,
            "lines": {"local_code": LOCAL_CODE_LINE, "no_circuit": NO_CIRCUIT_LINE},
            "models": public, "unmapped_inh_products": unmapped, "product_to_model": product_to_model,
            "charts": charts["charts"], "pages": {p["handle"]: p["title"] for p in ALL_PAGES}}
    out = {ASSET: json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n"}
    bodies = {ANSWER_6["handle"]: answer_kw_body(models, ANSWER_6, updated),
              ANSWER_8["handle"]: answer_kw_body(models, ANSWER_8, updated),
              ANSWER_IR["handle"]: answer_ir_body(models, updated),
              METHOD["handle"]: methodology_body(models, charts, updated),
              TOOL["handle"]: tool_fallback_body(updated),
              SIZING["handle"]: tool_fallback_body(updated)}
    for h, b in bodies.items():
        out[PAGES / f"{h}.html"] = b + "\n"
    desc = descriptions(models)
    idx = [{"handle": p["handle"], "title": p["title"], "template_suffix": p["suffix"], "description": desc[p["handle"]],
            "mode": "sizing" if p is SIZING else ("electrical" if p is TOOL else None)} for p in ALL_PAGES]
    out[PAGES / "index.json"] = json.dumps({"updated": updated, "pages": idx}, indent=1, ensure_ascii=False) + "\n"
    return out


def self_test() -> None:
    f = {"value": 15.0, "evidence": {"snippet": "ith WiFi Capability FOR INDOOR USE ONLY MX-J206-01 120VAC 15AMP Dedicated "
                                                 "Circuit Required MX-J306-01 120VAC 20AMP Dedicat"}}
    q = quote(f, "stated_amperage", {"MX-J206-01"})
    assert q and q["text"] == "MX-J206-01 120VAC 15AMP Dedicated Circuit Required", q
    f = {"value": 20.0, "evidence": {"snippet": "mber : Rustic Cedar Glass : Tempered Glass Hardware : 120V, 20 amp "
                                                 "dedicated outlet Lighting : Full Spectrum: Far & Near Acces"}}
    q = quote(f, "stated_amperage", set())
    assert q and q["text"] == "Hardware : 120V, 20 amp dedicated outlet", q
    f = {"value": "NEMA 5-15P", "evidence": {"snippet": "720 Watts 14.5 Amps Plugs into a standard household outlet. NEMA 5-15P"}}
    q = quote(f, "connection_type", set())
    assert q and q["text"].endswith("NEMA 5-15P") and q["text"] in f["evidence"]["snippet"], q
    f = {"value": 30.0, "evidence": {"snippet": "nothing about amps here"}}
    assert quote(f, "stated_amperage", set()) is None
    assert dedicated_class({"statements": [{"quote": {"text": "120V/15amp Non GFCI plug & play (Recommended Dedicated Outlet)"}}]}) == "recommended"
    assert dedicated_class({"statements": [{"quote": {"text": "240V/30AMP DEDICATED CIRCUIT/RECEPTACLE REQUIRED"}}]}) == "required"
    assert dedicated_class({"statements": [{"quote": {"text": "Hardware : 120V, 20 amp dedicated outlet"}}]}) == "specified"
    f = {"value": "120V", "evidence": {"snippet": "J206-01 120VAC 15AMP Dedicated Circuit Required MX-J306-01 120VAC 20AMP "
                                                   "Dedicated Circuit Required Carefully and thoroughly"}}
    q = quote(f, "supply_voltage", {"MX-J306-01"})
    assert q and q["text"] == "MX-J306-01 120VAC 20AMP Dedicated Circuit Required", q
    assert quote(f, "supply_voltage", {"MX-K999-01"}) is None   # passage names models, none of them ours
    f = {"value": "Hardwired", "evidence": {"snippet": "ELECTRIC SHOCK The Nova 3 is hardwired to a dedicated 240 V circuit and can cause fatal electric"}}
    q = quote(f, "connection_type", set())
    assert q and q["text"] == "The Nova 3 is hardwired to a dedicated 240 V circuit", q
    assert not FEAR.search(q["text"])
    # r3 D2 regression: Dynamic's spec-then-label manual. DYN-6215-05 is 15 A; the 20 A row is DYN-6315-05's.
    sn = ("SAUNA IS FOR INDOOR USE ONLY 120VAC 15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05) "
          "120VAC 20AMP Dedicated Circuit Required (DYN-6315-05) Carefully and thoroughly")
    q = quote({"value": 15.0, "evidence": {"snippet": sn}}, "stated_amperage", {"DYN-6215-05"})
    assert q and q["text"].endswith("15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05)"), q
    assert quote({"value": 20.0, "evidence": {"snippet": sn}}, "stated_amperage", {"DYN-6215-05"}) is None
    q = quote({"value": 20.0, "evidence": {"snippet": sn}}, "stated_amperage", {"DYN-6315-05"})
    assert q and q["text"] == "120VAC 20AMP Dedicated Circuit Required (DYN-6315-05)", q
    assert quote({"value": 15.0, "evidence": {"snippet": sn}}, "stated_amperage", {"DYN-6315-05"}) is None
    print("electrical_build self-test: ok")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        self_test()
        return
    out = build()
    if a.check:
        drift = [str(p.relative_to(ROOT)) for p, s in out.items() if not p.exists() or p.read_text() != s]
        if drift:
            sys.exit(f"DRIFT: {drift}")
        print(f"no drift: {len(out)} files")
        return
    PAGES.mkdir(parents=True, exist_ok=True)
    for p, s in out.items():
        p.write_text(s)
    print(f"wrote {len(out)} files")


if __name__ == "__main__":
    main()
