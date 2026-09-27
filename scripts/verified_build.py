#!/usr/bin/env python3
"""INH Verified — build the verified dataset from the lead list and the origin cache.

    .venv/bin/python scripts/verified_build.py --brands "Golden Designs Inc" "Salus Saunas"

OFFLINE. Reads only data/verified/cache-manifest.json and out/verified/cache/.
Same cache in, byte-identical files out.

THE RULE (CLAUDE.md, editorial independence; D11): a lead value is never
published. A value is published only when an origin source states it:
  documented  manufacturer manual / spec sheet the manufacturer hosts
  listed      manufacturer product page (source_type manufacturer)
  listed      approved distributor page (none approved yet)
Retailer pages, including inhousewellness.com, are never evidence.

Per field, the SOURCE decides, and it must decide unambiguously:
  - the source states exactly one value      -> that value is published
      equal to the lead                        confirmed
      different from the lead                  changed  (lead mismatch logged)
      and there was no lead                    source_only
  - the source states two or more values     -> nothing published, ambiguity logged
  - the source states nothing                -> not_verified (lead -> not_found)
Never inferred, computed, or carried over from the lead.

Outputs
  data/verified/saunas.json                  records with status published|backlog
  data/verified/conflicts.json               lead mismatches, tier disagreements,
                                             within-source ambiguities
  data/verified/internal/verification-log.json   per-lead, per-field audit (internal)
  data/verified/internal/backlog.json            leads with no origin page (internal)
  out/verified/b1-report.json                    counts and samples for the report
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from verified_import import (  # noqa: E402
    BANNED_PHRASE, BRAND_DISPLAY, HYBRID_WORD, IR_TEXT, TRAD_TEXT,
    build_name, display_title, parse_amps, parse_kw, slugify, title_capacity)
from src.power_parse import read_kw  # noqa: E402
from extract_manual_specs import (  # noqa: E402
    governing_model, model_tokens, pages_of, quieten_pdf_font_chatter, readings_from)

VERSION = "0.2.0-b1"
CACHE = ROOT / "out/verified/cache"
MANIFEST = ROOT / "data/verified/cache-manifest.json"
SOURCES = ROOT / "data/verified/sources.json"
LEADS = ROOT / "data/verified/internal/leads/infinite-sauna-2026-09-21.json"
OUT = ROOT / "data/verified"
REPORT = ROOT / "out/verified/b1-report.json"

RECOMMENDATION_RX = re.compile(r"(?i)\brecommend(?:ed|s)?\b|\bsuggest(?:ed)?\b|\boptional\b|\bupgrade\b")
NEGATION_RX = re.compile(r"(?i)\b(?:no|not|never|without|don'?t|do not)\b[^.]{0,25}$")


# ------------------------------------------------------------------ cache --

class Cache:
    def __init__(self):
        raw = MANIFEST.read_bytes()
        self.sha = hashlib.sha256(raw).hexdigest()
        self.entries = json.loads(raw)["entries"]

    def get(self, url):
        e = self.entries.get(url)
        if not e or e.get("status") != 200:
            return None, e
        data = (CACHE / e["cache_file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != e["sha256"]:
            raise SystemExit(f"cache corrupt for {url}: sha256 does not match the manifest")
        return data, e


def html_to_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</(p|li|div|h[1-6]|tr|td|ul|ol)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")]
    return "\n".join(l for l in lines if l)


def snip(text, m, pad=60):
    s = text[max(0, m.start() - pad): m.end() + pad]
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- sources --

class Doc:
    """One fetched origin document. segments = [(locator, text)]."""
    def __init__(self, source_url, fetched_url, entry, tier, source_type, segments, title="", skus=()):
        self.source_url = source_url
        self.fetched_url = fetched_url
        self.sha = entry["sha256"]
        self.fetched_at = entry["fetched_at"]
        self.tier = tier                  # "documented" | "listed"
        self.source_type = source_type    # manufacturer | manufacturer_manual
        self.segments = segments
        self.title = title
        self.skus = list(skus)


def catalogue(cache, domain):
    prods = []
    for page in range(1, 20):
        url = f"https://{domain}/products.json?limit=250&page={page}"
        data, e = cache.get(url)
        if data is None:
            break
        batch = json.loads(data)["products"]
        prods += [(p, url, e) for p in batch]
        if len(batch) < 250:
            break
    return prods


SPEC_PANEL_RX = re.compile(r"(?i)specification|feature|overview|detail|description|what'?s included")


def salus_panels(h: str):
    """[(panel title, text)] from the product accordion. Panels are split on their titles."""
    heads = list(re.finditer(r'<h2 class="disclosure__title[^"]*"[^>]*>(.*?)</h2>', h, re.S))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else min(len(h), m.end() + 20000)
        out.append((html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip(), html_to_text(h[m.end():end])))
    return out


def product_docs(cache, brand, src, p, cat_url, cat_entry):
    domain = src["manufacturer_domains"][0]
    page_url = f"https://{domain}/products/{p['handle']}"
    title = html.unescape(p["title"]).strip()
    skus = [v.get("sku") for v in p.get("variants", []) if v.get("sku")]
    segs = [(f"catalogue product '{p['handle']}' title", title)]
    if p.get("product_type"):
        segs.append((f"catalogue product '{p['handle']}' product_type", p["product_type"]))
    body = html_to_text(p.get("body_html") or "")
    if body:
        segs.append((f"catalogue product '{p['handle']}' body_html", body))
    docs = [Doc(page_url, cat_url, cat_entry, "listed", "manufacturer", segs, title, skus)]
    if src["adapter"] == "shopify_html_disclosure":
        data, e = cache.get(page_url)
        if data is not None:
            panels = salus_panels(data.decode("utf-8", "replace"))
            keep = [(f"product page panel '{t}'", txt) for t, txt in panels if SPEC_PANEL_RX.search(t)]
            docs.append(Doc(page_url, page_url, e, "listed", "manufacturer", keep, title, skus))
    return docs


# -------------------------------------------------------------- extractors --
# Each returns [(value, locator, snippet)]. Values are normalised so that two
# statements of the same fact compare equal.

def _scan(doc, rx, value_fn, title_only=False, guard_negation=False):
    out = []
    for loc, text in doc.segments:
        if title_only and not loc.endswith("title") and not loc.endswith("product_type"):
            continue
        for m in rx.finditer(text):
            if guard_negation and (NEGATION_RX.search(text[max(0, m.start() - 30):m.start()])
                                   or re.search(r"(?i)\b(?:not|no|never)\b", m.group(0))
                                   or re.match(r"(?i)\s*(?:is\s+|are\s+)?not\s+(?:required|necessary|needed)",
                                               text[m.end():m.end() + 30])):
                continue
            v = value_fn(m)
            if v is not None:
                out.append((v, loc, snip(text, m)))
    return out


CAP_RANGE_RX = re.compile(r"(?i)(?<![\d.])(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})[\s-]*(?:persons?|people|per)\b")
CAP_ONE_RX = re.compile(r"(?i)(?<![\d.\-–])(\d{1,2})[\s-]*(?:persons?|people)\b")
CAP_LABEL_RX = re.compile(r"(?i)\b(?:max(?:imum)?\s+)?capacity\s*:\s*(\d{1,2})(?:\s*(?:-|–|to)\s*(\d{1,2}))?")


def ex_capacity(doc):
    out = []
    for loc, text in doc.segments:
        masked = text
        for m in CAP_RANGE_RX.finditer(text):
            out.append(((int(m.group(1)), int(m.group(2))), loc, snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        for m in CAP_LABEL_RX.finditer(masked):
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
            out.append(((a, b), loc, snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        for m in CAP_ONE_RX.finditer(masked):
            n = int(m.group(1))
            out.append(((n, n), loc, snip(text, m)))
    return out


def ex_heat_type(doc):
    out = []
    for loc, text in doc.segments:
        if not (loc.endswith("title") or loc.endswith("product_type")):
            continue
        m = HYBRID_WORD.search(text)
        if m:
            out.append(("hybrid", loc, snip(text, m)))
            continue
        t = re.search(r"(?i)\btraditional\b|\bstove\b|\bsteam\b", text)
        i = IR_TEXT.search(text) or re.search(r"(?i)\bfar\s+ir\b", text)
        if t:
            out.append(("traditional", loc, snip(text, t)))
        if i:
            out.append(("infrared", loc, snip(text, i)))
    return out


PLACE_BOTH_RX = re.compile(r"(?i)\b(?:indoor\s*(?:/|-|or|&|and)\s*outdoor|outdoor\s*(?:/|-|or|&|and)\s*indoor)\b")
# "Indoor or covered exterior use" permits exterior use under a condition. It is
# neither indoor-only nor a plain indoor/outdoor rating, so it yields BOTH
# statements and the field is withheld as ambiguous.
PLACE_CONDITIONAL_RX = re.compile(r"(?i)\bindoor\s+or\s+(?:covered\s+)?(?:exterior|outdoor)\b")
PLACE_RX = re.compile(r"(?i)\b(indoor|outdoor)\b")


def ex_placement(doc):
    out = []
    for loc, text in doc.segments:
        masked = text
        for m in PLACE_CONDITIONAL_RX.finditer(text):
            out.append(("indoor", loc, snip(text, m)))
            out.append(("outdoor (conditional)", loc, snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        for m in PLACE_BOTH_RX.finditer(masked):
            out.append(("indoor_outdoor", loc, snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        for m in PLACE_RX.finditer(masked):
            out.append((m.group(1).lower(), loc, snip(text, m)))
    return out


def norm_model(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


MODEL_LABEL_RX = re.compile(r"(?i)\bmodel(?:\s*(?:no\.?|number|#))?\s*[:#]\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\s+(?:Elite|CED|HEM|FS))?)")


def ex_model(doc):
    out = [(sku.strip(), f"catalogue product variant sku", f"sku: {sku.strip()}") for sku in doc.skus]
    for loc, text in doc.segments:
        for m in MODEL_LABEL_RX.finditer(text):
            out.append((m.group(1).strip(), loc, snip(text, m)))
    return out


WOODS = ["Pacific Premium Clear Cedar", "Pacific Premium Cedar", "Canadian Red Cedar", "Western Red Cedar", "Pacific Cedar",
         "Red Cedar", "White Cedar", "Canadian Hemlock", "Thermally Modified Pine", "Thermo-Spruce",
         "Thermo Spruce", "Nordic Spruce", "White Spruce", "Thermo-Aspen", "Thermo Aspen", "Hemlock",
         "Cedar", "Spruce", "Aspen", "Alder", "Basswood", "Pine", "ThermoWood"]
WOOD_RX = re.compile(r"(?i)\b(" + "|".join(re.escape(w) for w in WOODS) + r")\b")


def ex_wood(doc):
    return _scan(doc, WOOD_RX, lambda m: next(w for w in WOODS if w.lower() == m.group(1).lower()))


def ex_spectrum(doc):
    out = _scan(doc, re.compile(r"(?i)\bfull[- ]spectrum\b"), lambda m: "Full Spectrum")
    if out:
        return out
    return _scan(doc, re.compile(r"(?i)\bfar[- ]?(?:infrared|ir)\b"), lambda m: "Far Infrared")


def ex_emf(doc):
    rx = re.compile(r"(?i)\b(near[- ]zero|ultra[- ]low|low)\s+emf\b")
    def v(m):
        w = m.group(1).lower().replace("-", " ")
        return {"near zero": "Near Zero", "ultra low": "Ultra Low", "low": "Low"}[w]
    out = []
    for val, loc, s in _scan(doc, rx, v):
        out.append((val, loc, s))
    # "Ultra Low" contains "Low": a bare "low" match inside an "ultra low" phrase is the same statement.
    return [x for x in out if not (x[0] == "Low" and re.search(r"(?i)ultra[- ]low\s+emf", x[2]))]


def ex_red_light(doc):
    return _scan(doc, re.compile(r"(?i)\bred[- ]light\b"), lambda m: True, guard_negation=True)


VOLT_RX = re.compile(r"(?i)(?<![\d.])(208\s*[-–/]\s*240|220\s*/\s*240|120|208|220|230|240)\s*(?:v(?:ac)?\b|volts?\b)")


def ex_voltage(doc):
    def v(m):
        s = re.sub(r"\s", "", m.group(1))
        return {"208-240": "208–240V", "208–240": "208–240V", "208/240": "208–240V"}.get(s, s + "V")
    out = []
    for loc, text in doc.segments:
        for m in VOLT_RX.finditer(text):
            out.append((v(m), loc, snip(text, m)))
            if MULTI_CIRCUIT_RX.search(text[max(0, m.start() - 25): m.start()]):
                out.append(("multiple circuits", loc, snip(text, m)))
    return out


AMP_RX = re.compile(r"(?<![\d.])(\d{2})\s*(?:A\b|AMPS?\b|[Aa]mps?\b|[Aa]mperes?\b)")


MULTI_CIRCUIT_RX = re.compile(r"(?i)\b(?:dual|two|double)\b|\b2\s*x\b|\bx\s*2\b")


def ex_amps(doc, breaker=False):
    out = []
    for loc, text in doc.segments:
        for m in AMP_RX.finditer(text):
            around = text[max(0, m.start() - 30): m.end() + 30]
            if MULTI_CIRCUIT_RX.search(text[max(0, m.start() - 25): m.start()]):
                # "Dual x 120v/15 AMP": two circuits. One amperage would misstate it.
                out.append((float(m.group(1)), loc, snip(text, m)))
                out.append(("multiple circuits", loc, snip(text, m)))
                continue
            if breaker and not re.search(r"(?i)\bbreaker\b", around):
                continue
            out.append((float(m.group(1)), loc, snip(text, m)))
    return out


def ex_plug(doc):
    out = _scan(doc, re.compile(r"(?i)\bNEMA\s*(L?\d{1,2})\s*-\s*(\d{2})\s*P\b"),
                lambda m: f"NEMA {m.group(1).upper()}-{m.group(2)}P", guard_negation=True)
    out += _scan(doc, re.compile(r"(?i)\bhard[- ]?wired?\b"), lambda m: "Hardwired", guard_negation=True)
    return out


def ex_gfci(doc):
    return _scan(doc, re.compile(r"(?i)\bGFCI\b[^.\n]{0,30}\brequired\b|\brequires?\s+(?:a\s+)?GFCI\b"),
                 lambda m: "Required", guard_negation=True)


def ex_circuit(doc):
    return _scan(doc, re.compile(r"(?i)\bdedicated\b[^.\n]{0,30}\bcircuit\b"),
                 lambda m: "Dedicated required", guard_negation=True)


def ex_kw(doc):
    out = []
    for loc, text in doc.segments:
        for r in read_kw(text, "origin", None):
            if RECOMMENDATION_RX.search(r["span"]):
                continue
            out.append((float(r["kw"]), loc, re.sub(r"\s+", " ", r["span"]).strip()))
    return out


MAXT_RX = re.compile(r"(?i)(?:up to|as high as|heats?\s+(?:up\s+)?to|reach(?:es|ing)?|max(?:imum)?\s+temp(?:erature)?\s*(?:of|:)?)\s*(\d{3})\s*(?:°|º|degrees)?\s*F\b")


def ex_max_temp(doc):
    return _scan(doc, MAXT_RX, lambda m: float(m.group(1)))


def _dims(doc, label):
    rx = re.compile(r"(?i)\b" + label + r"\s+dimensions?\s*(\(WDH\))?\s*:\s*"
                    r"([\d.]+)\s*(?:″|”|\"|in\.?|inches)?\s*(W)?\s*x\s*([\d.]+)\s*(?:″|”|\"|in\.?|inches)?\s*(D)?\s*x\s*"
                    r"([\d.]+)\s*(?:″|”|\"|in\.?|inches)?\s*(H)?")
    out = []
    for loc, text in doc.segments:
        for m in rx.finditer(text):
            # The order is only known when the source labels it (WDH, or W/D/H letters).
            if not (m.group(1) or (m.group(3) and m.group(5) and m.group(7))):
                continue
            out.append(((float(m.group(2)), float(m.group(4)), float(m.group(6))), loc, snip(text, m)))
    return out


def ex_dims_assembled(doc):
    return _dims(doc, r"(?:exterior|outside)")


def ex_dims_crated(doc):
    return _dims(doc, r"shipping")


def ex_warranty(doc, lead):
    if not lead:
        return []
    return _scan(doc, re.compile(re.escape(lead), re.I), lambda m: lead)


# ------------------------------------------------------------------ manuals --
# A PDF counts as the manufacturer's document only when (1) the manufacturer's
# own site links it from a host listed in sources.json pdf_hosts, and (2) its
# text names the brand. A Harvia heater manual hosted on a sauna maker's CDN is
# Harvia's document, not the sauna maker's statement about its cabin.
#
# A manual is a document about a product LINE (CLAUDE.md, Round 15). It is
# attached to a record only when our model number appears in it as a token, and
# a figure is taken only when OUR model number governs it (the model token that
# most recently precedes it). Unbound figures are not used: a line manual with
# several models cannot say which one an unbound figure describes.

def origin_pdf(url, src):
    parts = urllib.parse.urlsplit(url)
    return parts.netloc in src.get("pdf_hosts", []) and parts.path.startswith(src.get("pdf_path_prefix", "/"))


PDFTEXT = ROOT / "out/verified/pdftext"


def pdf_pages(data, sha):
    """pypdf text per page, cached by the PDF's sha256. Derived only from the cached
    bytes, so it changes nothing about determinism; it only avoids re-parsing."""
    f = PDFTEXT / f"{sha}.json"
    if f.exists():
        return [tuple(x) for x in json.loads(f.read_text())]
    pages = pages_of(data)
    PDFTEXT.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(pages))
    return pages


class Manual:
    def __init__(self, url, entry, pages):
        self.url, self.entry, self.pages = url, entry, pages
        self.tokens = {vb_norm(t) for _, txt in pages for t, _, _ in model_tokens(re.sub(r"[ \t]+", " ", txt))}


def vb_norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def load_manuals(cache, src, brand_word):
    quieten_pdf_font_chatter()
    out, skipped = [], []
    for url, e in sorted(cache.entries.items()):
        if not url.lower().split("?")[0].endswith(".pdf"):
            continue
        if not origin_pdf(url, src):
            continue
        data, e = cache.get(url)
        if data is None:
            continue
        if not data.startswith(b"%PDF"):
            skipped.append((url, "not a PDF (magic bytes)"))
            continue
        try:
            pages = pdf_pages(data, e["sha256"])
        except Exception as ex:  # a parse failure is recorded, not guessed around
            skipped.append((url, f"unreadable: {type(ex).__name__}"))
            continue
        if not pages:
            skipped.append((url, "no text layer (NEEDS_OCR); nothing inferred"))
            continue
        if not any(re.search(brand_word, t, re.I) for _, t in pages):
            skipped.append((url, f"does not name the brand ({brand_word}); not treated as the manufacturer's document"))
            continue
        out.append(Manual(url, e, pages))
    return out, skipped


def manual_doc(man, keys):
    """A Doc whose statements are only those our model governs."""
    segs = []
    d = Doc(man.url, man.url, man.entry, "documented", "manufacturer_manual", segs)
    d.bound = []   # [(field, value, locator, snippet)]
    accepted, _ = readings_from(man.pages, man.url, frozenset(keys))
    for r in accepted:
        if r.get("governing_model") and vb_norm(r["governing_model"]) in keys:
            d.bound.append(("heater_kw", float(r["kw"]), f"pdf page {r['page']}", re.sub(r"\s+", " ", r["span"]).strip()))
    for page_no, txt in man.pages:
        flat = re.sub(r"[ \t]+", " ", txt)
        for rx, field, conv in ((VOLT_RX, "supply_voltage", lambda m: re.sub(r"\s", "", m.group(1)) + "V"),
                                (AMP_RX, "stated_amperage", lambda m: float(m.group(1)))):
            for m in rx.finditer(flat):
                lo = max(0, m.start() - 160)
                window = flat[lo:m.end() + 40]
                gov = governing_model(window, m.start() - lo)
                if gov and vb_norm(gov) in keys:
                    d.bound.append((field, conv(m), f"pdf page {page_no}", snip(flat, m)))
                    if field == "stated_amperage" and re.search(r"(?i)\bbreaker\b", flat[m.start() - 30:m.end() + 30]):
                        d.bound.append(("breaker_amps", conv(m), f"pdf page {page_no}", snip(flat, m)))
        for t, a, b in model_tokens(flat):
            if vb_norm(t) in keys:
                d.bound.append(("model_number", t, f"pdf page {page_no}", flat[max(0, a - 60):b + 60].replace("\n", " ")))
                break
    return d


# ----------------------------------------------------------------- deciding --

def decide(statements_by_tier, lead, eq=lambda a, b: a == b):
    """statements_by_tier: [(tier, doc, [(value, loc, snippet)])] highest tier first.
    Returns (outcome, chosen | None, notes[])."""
    chosen, notes, singles = None, [], []
    for tier, doc, sts in statements_by_tier:
        if not sts:
            continue
        distinct = []
        for v, loc, s in sts:
            if not any(eq(v, d[0]) for d in distinct):
                distinct.append((v, loc, s))
        if len(distinct) == 1:
            singles.append((tier, doc, distinct[0]))
        else:
            notes.append(("within_source_ambiguity", tier, doc, distinct))
    if singles:
        chosen = singles[0]
        for other in singles[1:]:
            if not eq(other[2][0], chosen[2][0]):
                notes.append(("tier_disagreement", chosen, other))
    if chosen is None:
        if any(n[0] == "within_source_ambiguity" for n in notes):
            return "ambiguous", None, notes
        return ("not_found" if lead is not None else "absent"), None, notes
    if lead is None:
        return "source_only", chosen, notes
    return ("confirmed" if eq(lead, chosen[2][0]) else "changed"), chosen, notes


def graded(chosen, value, unit=None, note=None):
    tier, doc, (v, loc, s) = chosen
    return {"value": value, "unit": unit, "grade": tier, "source_url": doc.source_url,
            "source_type": doc.source_type, "observed_at": doc.fetched_at[:10], "note": note,
            "evidence": {"fetched_at": doc.fetched_at, "content_sha256": doc.sha,
                         "locator": loc if doc.fetched_url == doc.source_url else f"{loc} (fetched as {doc.fetched_url})",
                         "snippet": s}}


def nv(note=None, unit=None):
    return {"value": None, "unit": unit, "grade": "not_verified", "source_url": None,
            "source_type": "none", "observed_at": None, "note": note}


def na(note=None, unit=None):
    return dict(nv(note, unit), grade="not_applicable")


# ------------------------------------------------------------------ leads --

def lead_values(r):
    kw, _ = parse_kw(r.get("heater_kw"))  # missing-ok: parser returns None for an absent value; None is withheld, never published
    tc = title_capacity(r["title"])
    cap = tc or ((r["capacity"], r["capacity"]) if r.get("capacity") else None)
    mt = re.search(r"(\d{3})", r.get("max_temp") or "")
    volts = r.get("voltage")
    return {
        "model_number": r["model"] if "|" not in r["model"] and not re.fullmatch(r"[a-z0-9-]+", r["model"]) else None,
        "heat_type": r["type"].lower(),
        "placement": r["placement"].lower(),
        "capacity": cap,
        "wood_species": r.get("wood"),
        "spectrum": r.get("spectrum"),
        "emf_claim": r.get("emf"),
        "red_light": True if r.get("red_light") else None,
        "supply_voltage": volts,
        "stated_amperage": parse_amps(r.get("amperage")),  # missing-ok: parser returns None for an absent value; None is withheld, never published
        "connection_type": ("NEMA 6-30P" if r.get("plug") == "NEMA6-30P" else None),
        "heater_kw": kw,
        "max_temp_f": float(mt.group(1)) if mt else None,
        "warranty": r.get("warranty"),
    }


def model_eq(a, b):
    na_, nb = norm_model(a), norm_model(b)
    return na_ == nb or (len(na_) >= 6 and (na_.startswith(nb) or nb.startswith(na_)) and abs(len(na_) - len(nb)) <= 5)


# ------------------------------------------------------------------ build --

# A passage that lists heater OPTIONS ("4.5kw and 6kw heaters require a 30 amp
# connection, 8kw ... 40 amp ... wood burning stoves require no electrical
# hookup") states what each option needs, not what this model is. Every
# electrical statement drawn from such a passage is paired with a
# "depends on heater option" statement, so the field is withheld as ambiguous.
KW_ANY_RX = re.compile(r"(?i)(?<![\d.])(\d{1,2}(?:\.\d)?)\s*kw\b")


def is_option_table(text):
    kws = {float(m.group(1)) for m in KW_ANY_RX.finditer(text)}
    return len(kws) >= 2 or bool(re.search(r"(?i)wood[- ]burning", text))


def option_aware(fn):
    def wrapped(doc):
        out = []
        for v, loc, snip_ in fn(doc):
            out.append((v, loc, snip_))
            seg = next((t for l, t in doc.segments if l == loc), "")
            if is_option_table(seg):
                # Only the sentence around the statement decides, not the whole panel.
                around = seg[max(0, seg.find(snip_[:40]) - 200): seg.find(snip_[:40]) + 260] if snip_[:40] in seg else seg
                if is_option_table(around):
                    out.append(("depends on heater option", loc, snip_))
        return out
    return wrapped


FIELDS = [
    # (field, extractor, applicability, eq)
    ("heat_type", ex_heat_type, "all", None),
    ("placement", ex_placement, "all", None),
    ("capacity", ex_capacity, "all", None),
    ("wood_species", ex_wood, "all", lambda a, b: str(a).lower() == str(b).lower()),
    ("spectrum", ex_spectrum, "ir", lambda a, b: str(a).lower() == str(b).lower()),
    ("emf_claim", ex_emf, "ir", lambda a, b: str(a).lower() == str(b).lower()),
    ("red_light", ex_red_light, "ir", None),
    ("supply_voltage", option_aware(ex_voltage), "all", lambda a, b: str(a).replace(" ", "").lower() == str(b).replace(" ", "").lower()),
    ("stated_amperage", option_aware(ex_amps), "all", None),
    ("breaker_amps", option_aware(lambda d: ex_amps(d, breaker=True)), "all", None),
    ("connection_type", option_aware(ex_plug), "all", None),
    ("gfci", option_aware(ex_gfci), "all", None),
    ("circuit_requirement", option_aware(ex_circuit), "all", None),
    ("heater_kw", option_aware(ex_kw), "heater", None),
    ("max_temp_f", ex_max_temp, "all", None),
    ("dims_assembled", ex_dims_assembled, "all", None),
    ("dims_crated", ex_dims_crated, "all", None),
]


def build_brand(cache, brand, src, leads_all, sources):
    leads = sorted([r for r in leads_all if r["brand"] == brand], key=lambda r: r["model_key"])
    domain = src["manufacturer_domains"][0]
    cat = catalogue(cache, domain)
    by_sku, by_handle = {}, {}
    for p, url, e in cat:
        by_handle[p["handle"]] = (p, url, e)
        for v in p.get("variants", []):
            if v.get("sku"):
                by_sku.setdefault(norm_model(v["sku"]), (p, url, e))

    manuals, manual_skips = load_manuals(cache, src, src.get("brand_word", src["display"]))
    manual_use = defaultdict(list)
    matched = defaultdict(list)     # handle -> [lead]
    no_page = []
    for r in leads:
        hit = by_sku.get(norm_model(r["model"])) if r["model"] else None
        how = "manufacturer sku"
        if not hit:
            for u in r["source_urls"]:
                parts = urllib.parse.urlsplit(u)
                if parts.netloc in src["manufacturer_domains"]:
                    h = parts.path.rstrip("/").split("/")[-1]
                    if h in by_handle:
                        hit, how = by_handle[h], "lead URL on the manufacturer's domain"
                        break
        if hit:
            matched[hit[0]["handle"]].append((r, how))
        else:
            no_page.append(r)

    records, log, conflicts = [], [], []
    for handle in sorted(matched):
        p, cat_url, cat_e = by_handle[handle]
        docs = product_docs(cache, brand, src, p, cat_url, cat_e)
        lead_pairs = matched[handle]
        keys = {vb_norm(x) for x in docs[0].skus + [r["model"] for r, _ in lead_pairs] if x}
        keys |= {vb_norm(t) for x in docs[0].skus for t, _, _ in model_tokens(x.upper())}
        keys = {k for k in keys if len(k) >= 5}
        for man in manuals:
            if man.tokens & keys:
                docs.append(manual_doc(man, keys))
                manual_use[man.url].append(handle)
        lead = lead_values(lead_pairs[0][0])
        rec_log = {"handle": handle, "leads": [{"lead_key": r["model_key"], "lead_model": r["model"], "matched_by": how}
                                                for r, how in lead_pairs],
                   "fields": {}}
        results = {}

        def run(field, fn, lead_v, eq=None):
            tiers = [(d.tier, d, ([(v, loc, s) for f_, v, loc, s in d.bound if f_ == field]
                                  if hasattr(d, "bound") else fn(d))) for d in docs]
            # Merge the listed docs (catalogue + rendered page) into one tier: both are the same page.
            merged = []
            for t in ("documented", "listed"):
                sts = [(v, loc, s, d) for tt, d, ss in tiers if tt == t for v, loc, s in ss]
                if sts:
                    merged.append((t, sts))
            by_tier = []
            for t, sts in merged:
                # keep the doc attached to each statement via the first doc that produced it
                by_tier.append((t, sts))
            flat = []
            for t, sts in by_tier:
                # one doc per tier for grading: the one that produced the first statement
                flat.append((t, sts[0][3], [(v, loc, s) for v, loc, s, _ in sts]))
            outcome, chosen, notes = decide(flat, lead_v, eq or (lambda a, b: a == b))
            if chosen is not None:
                # re-attach the doc that actually produced the chosen statement
                t, _, st = chosen
                src_doc = next(d for tt, sts in by_tier if tt == t for v, loc, s, d in sts if (v, loc, s) == st)
                chosen = (t, src_doc, st)
            results[field] = (outcome, chosen)
            rec_log["fields"][field] = {"lead": lead_v, "outcome": outcome,
                                        "value": chosen[2][0] if chosen else None,
                                        "tier": chosen[0] if chosen else None}
            for n in notes:
                if n[0] == "within_source_ambiguity":
                    _, t, d, distinct = n
                    conflicts.append({"kind": "within_source_ambiguity", "brand": BRAND_DISPLAY.get(brand, brand),
                                      "handle": handle, "field": field, "source_url": d.source_url,
                                      "fetched_at": d.fetched_at, "values": [
                                          {"value": v, "locator": loc, "snippet": s} for v, loc, s in distinct]})
                elif n[0] == "tier_disagreement":
                    _, a, b = n
                    conflicts.append({"kind": "tier_disagreement", "brand": BRAND_DISPLAY.get(brand, brand),
                                      "handle": handle, "field": field,
                                      "published": {"value": a[2][0], "grade": a[0], "source_url": a[1].source_url, "fetched_at": a[1].fetched_at},
                                      "other": {"value": b[2][0], "grade": b[0], "source_url": b[1].source_url, "fetched_at": b[1].fetched_at}})
            if outcome == "changed":
                conflicts.append({"kind": "lead_mismatch", "brand": BRAND_DISPLAY.get(brand, brand), "handle": handle,
                                  "field": field, "lead_value": lead_v, "source_value": chosen[2][0],
                                  "source_url": chosen[1].source_url, "fetched_at": chosen[1].fetched_at,
                                  "snippet": chosen[2][2]})
            return outcome, chosen

        # Identity first: the model number on the manufacturer's own page.
        run("model_number", ex_model, lead["model_number"], model_eq)
        mo, mc = results["model_number"]
        if mo == "ambiguous" and lead["model_number"]:
            # Several model strings on the page; confirm only if one of them IS the lead.
            sts = [s for d in docs for s in ex_model(d) if model_eq(lead["model_number"], s[0])]
            if sts:
                d0 = docs[0]
                labelled = [s for s in sts if "sku" not in s[1]] or sts
                results["model_number"] = ("confirmed", ("listed", d0, labelled[0]))
                rec_log["fields"]["model_number"].update(outcome="confirmed", value=labelled[0][0], tier="listed")

        for field, fn, appl, eq in FIELDS:
            lv = lead.get(field) if field not in ("dims_assembled", "dims_crated", "breaker_amps", "gfci", "circuit_requirement") else None
            if field == "supply_voltage" and lv:
                lv = lv.replace(" ", "")
            run(field, fn, lv, eq)
        run("warranty", lambda d: ex_warranty(d, lead["warranty"]), lead["warranty"],
            lambda a, b: str(a).lower() == str(b).lower())

        rec = assemble(brand, src, p, docs, results, cache)
        # The record decides what was published. A value the heat type makes
        # not_applicable was not confirmed, whatever the page said.
        paths = {"spectrum": ("infrared", "spectrum"), "emf_claim": ("infrared", "emf_claim"),
                 "red_light": ("infrared", "red_light"), "heater_kw": ("electrical", "heater_kw")}
        for fld, (blk, key) in paths.items():
            if rec[blk][key]["grade"] == "not_applicable" and fld in rec_log["fields"]:
                rec_log["fields"][fld].update(outcome="not_applicable", value=None, tier=None)
                conflicts[:] = [c for c in conflicts if not (c.get("handle") == handle and c.get("field") == fld)]
        records.append(rec)
        log.append(rec_log)
    manual_report = {"readable_brand_manuals": len(manuals), "skipped": manual_skips,
                     "attached": {u: sorted(h) for u, h in manual_use.items()},
                     "unattached": sorted(m.url for m in manuals if m.url not in manual_use)}
    return records, log, conflicts, no_page, leads, manual_report


def assemble(brand, src, p, docs, res, cache):
    disp = src["display"]
    page = docs[0]
    title = page.title
    name, _ = build_name(title, disp)

    def f(field, unit=None, conv=lambda v: v):
        o, c = res.get(field, ("absent", None))
        if c is None:
            note = {"ambiguous": "the source states more than one value"}.get(o)
            return nv(note, unit)
        return graded(c, conv(c[2][0]), unit)

    heat = res["heat_type"][1][2][0] if res["heat_type"][1] else None
    ir = heat in ("infrared", "hybrid")
    heater = heat in ("traditional", "hybrid")
    cap = res["capacity"][1]
    cmin, cmax = (cap[2][0] if cap else (None, None))

    def volt_value(v):
        return v if v in ("120V", "240V", "208–240V") else None

    sv = res["supply_voltage"]
    supply = f("supply_voltage")
    if supply["value"] is not None and volt_value(supply["value"]) is None:
        supply = nv("the source states a voltage outside the single-supply values this schema publishes")

    def box(field):
        o, c = res[field]
        if c is None:
            return {k: nv(None, "in") for k in ("width_in", "depth_in", "height_in")}
        w, d, h = c[2][0]
        return {"width_in": graded(c, w, "in"), "depth_in": graded(c, d, "in"), "height_in": graded(c, h, "in")}

    vendor_doc = page
    brand_f = {"value": disp, "unit": None, "grade": "listed", "source_url": page.source_url,
               "source_type": "manufacturer", "observed_at": page.fetched_at[:10], "note": None,
               "evidence": {"fetched_at": page.fetched_at, "content_sha256": page.sha,
                            "locator": f"catalogue product '{p['handle']}' vendor (fetched as {page.fetched_url})",
                            "snippet": f"vendor: {p.get('vendor')}; sold on the manufacturer's own site"}}
    name_f = ({"value": name, "unit": None, "grade": "listed", "source_url": page.source_url,
               "source_type": "manufacturer", "observed_at": page.fetched_at[:10],
               "note": "Model name taken from the manufacturer's product title (brand, capacity and marketing claims removed).",
               "evidence": {"fetched_at": page.fetched_at, "content_sha256": page.sha,
                            "locator": f"catalogue product '{p['handle']}' title (fetched as {page.fetched_url})",
                            "snippet": title}} if name else nv())
    offers = []
    variants = [v for v in p.get("variants", []) if v.get("price")]
    if len(variants) == 1:
        offers.append({"retailer": f"{disp} (manufacturer direct)", "url": page.source_url,
                       "price_usd": float(variants[0]["price"]),
                       "reference_price_usd": float(variants[0]["compare_at_price"]) if variants[0].get("compare_at_price") else None,
                       "retailer_type": "manufacturer_direct", "inh_sells": False,
                       "observed_at": page.fetched_at[:10]})

    rec = {
        "schema_version": "0.2.0",
        "inh_id": f"sauna/{slugify(disp)}/{slugify(res['model_number'][1][2][0]) if res['model_number'][1] else slugify(p['handle'])}",
        "category": "sauna",
        "status": "published",
        "withheld_reasons": [],
        "identity": {
            "brand": brand_f,
            "model_number": f("model_number"),
            "model_name": name_f,
            "configuration": nv(),
            "display_title": display_title(disp, name, cmin, cmax) if name else p["handle"],
            "aliases": [],
        },
        "heat_type": f("heat_type"),
        "placement": f("placement"),
        "capacity_min": graded(cap, cmin, "persons") if cap else nv(unit="persons"),
        "capacity_max": graded(cap, cmax, "persons") if cap else nv(unit="persons"),
        "dimensions": {"assembled": box("dims_assembled"), "crated": box("dims_crated")},
        "materials": {"wood_species": f("wood_species")},
        "electrical": {
            "supply_voltage": supply,
            "heater_voltage": nv(),
            "connection_type": f("connection_type"),
            "circuit_requirement": f("circuit_requirement") if res["circuit_requirement"][1] else nv("Not documented"),
            "breaker_amps": f("breaker_amps", "A"),
            "gfci": f("gfci") if res["gfci"][1] else nv("Not documented"),
            "heater_kw": f("heater_kw", "kW") if heater else (na("no traditional heater on an infrared model", "kW") if heat == "infrared" else nv(unit="kW")),
            "stated_amperage": f("stated_amperage", "A"),
        },
        "infrared": {
            "spectrum": f("spectrum") if ir else (na() if heat == "traditional" else nv()),
            "emf_claim": (dict(f("emf_claim"), grade="claimed", note="Manufacturer terminology, not a measurement")
                          if ir and res["emf_claim"][1] else (na() if heat == "traditional" else nv())),
            "red_light": f("red_light") if ir else (na() if heat == "traditional" else nv()),
        },
        "thermal": {"max_temp_f": f("max_temp_f", "F")},
        "warranty": {"stub": True, "summary": f("warranty")},
        "offers": offers,
        "provenance": {"verifier_version": VERSION, "cache_manifest_sha256": cache.sha,
                       "origin_urls": sorted({d.source_url for d in docs})},
        "_rule_inputs": {"text": "\n".join(t for d in docs for _, t in d.segments), "title": title,
                         "cap_ambiguous": res["capacity"][0] == "ambiguous",
                         "cap_statements": [c for d in docs for c in ex_capacity(d)]},
    }
    return rec


# ------------------------------------------------------------------ rules --

def apply_rules(records):
    for rec in records:
        ri = rec["_rule_inputs"]
        e = rec["electrical"]
        why = []
        # R1 on final values
        kw = e["heater_kw"]["value"]
        amps = e["breaker_amps"]["value"] or e["stated_amperage"]["value"]
        v = e["supply_voltage"]["value"]
        volts = {"120V": [120], "240V": [240], "208–240V": [208, 240]}.get(v, [])
        if kw and amps and volts:
            bad = [(x, kw * 1000 / x) for x in volts if kw * 1000 / x > amps]
            if bad:
                why.append(("R1_ELECTRICAL", "; ".join(f"{kw:g} kW at {x}V = {a:.1f} A > {amps:g} A stated" for x, a in bad)))
        # R2 on final values
        if rec["heat_type"]["value"] == "hybrid" and not (IR_TEXT.search(ri["text"]) and TRAD_TEXT.search(ri["text"])):
            why.append(("R2_HYBRID", "the manufacturer calls it hybrid but its page does not name both a traditional heater and an infrared system"))
        # R5 on final values
        if ri["cap_ambiguous"]:
            vals = sorted({f"{a}" if a == b else f"{a}–{b}" for (a, b), _, _ in ri["cap_statements"]})
            why.append(("R5_CAPACITY", f"the manufacturer's page states capacity as {', '.join(vals)}"))
        # R4
        if not rec["identity"]["model_name"]["value"]:
            why.append(("R4_TITLE", "no model name recoverable from the manufacturer's title"))
        rec["_why"] = why

    # R3: unique display titles; wood, then heater kW, tried as the distinguishing configuration.
    groups = defaultdict(list)
    for rec in records:
        groups[rec["identity"]["display_title"]].append(rec)
    for t, recs in groups.items():
        if len(recs) == 1:
            continue
        done = False
        for path, fmt in ((("materials", "wood_species"), "{}"), (("electrical", "heater_kw"), "{:g} kW heater")):
            vals = [r[path[0]][path[1]] for r in recs]
            if all(x["value"] is not None for x in vals) and len({x["value"] for x in vals}) == len(vals):
                for r, x in zip(recs, vals):
                    r["identity"]["configuration"] = dict(x, value=fmt.format(x["value"]), unit=None)
                    r["identity"]["display_title"] += ", " + fmt.format(x["value"])
                done = True
                break
        if not done:
            ids = ", ".join(sorted(r["identity"]["model_number"]["value"] or r["inh_id"] for r in recs))
            for r in recs:
                r["_why"].append(("R3_IDENTITY", f"display title '{t}' is shared by {len(recs)} records ({ids}) and the sources state no distinguishing configuration"))

    for rec in records:
        verified = sum(1 for blk in ("heat_type", "placement", "capacity_max") if rec[blk]["grade"] not in ("not_verified", "not_applicable"))
        verified += sum(1 for fld in list(rec["electrical"].values()) + list(rec["infrared"].values()) +
                        [rec["materials"]["wood_species"], rec["thermal"]["max_temp_f"], rec["identity"]["model_number"]]
                        if fld["grade"] not in ("not_verified", "not_applicable"))
        if verified == 0:
            rec["_why"].append(("NO_VERIFIED_VALUE", "the manufacturer's page confirmed no value beyond brand and name"))
        rec["withheld_reasons"] = [{"rule": r, "reason": w} for r, w in rec["_why"]]
        rec["status"] = "backlog" if rec["_why"] else "published"
        del rec["_why"], rec["_rule_inputs"]


# ------------------------------------------------------------------- lint --

def lint(records, conflicts, sources):
    """The gates Part B promised. Raises on any failure."""
    from jsonschema import Draft202012Validator
    schema = json.loads((OUT / "schema/inh-verified.schema.json").read_text())
    v = Draft202012Validator(schema)
    errs = []
    for rec in records:
        for e in v.iter_errors(rec):
            errs.append(f"{rec['inh_id']}: schema: {'/'.join(map(str, e.absolute_path))}: {e.message[:160]}")
    allowed = {b: set(s["manufacturer_domains"]) for b, s in sources["brands"].items()}
    disp_to_brand = {s["display"]: b for b, s in sources["brands"].items()}
    distributors = {d["domain"] for d in sources.get("distributors", [])}
    for rec in records:
        hosts = allowed[disp_to_brand[rec["identity"]["brand"]["value"]]] | distributors
        for path, fld in walk_fields(rec):
            if fld.get("source_url"):
                h = urllib.parse.urlsplit(fld["source_url"]).netloc
                brand_src = sources["brands"][disp_to_brand[rec["identity"]["brand"]["value"]]]
                if fld.get("source_type") == "manufacturer_manual" and origin_pdf(fld["source_url"], brand_src):
                    continue
                if h not in hosts:
                    errs.append(f"{rec['inh_id']}: {path}: source host {h} is not an origin host on the allow-list")
    blob = json.dumps(records, ensure_ascii=False) + json.dumps(conflicts, ensure_ascii=False)
    if BANNED_PHRASE.lower() in blob.lower():
        errs.append(f"the phrase '{BANNED_PHRASE}' appears in the dataset")
    if re.search(r"(?i)infinite\s*sauna|infinitesauna", blob):
        errs.append("the lead list's source is named in the dataset (D1)")
    for rec in records:
        for blk in ("heat_type", "placement", "capacity_min", "capacity_max"):
            if not isinstance(rec[blk], dict) or "grade" not in rec[blk]:
                errs.append(f"{rec['inh_id']}: {blk} is a bare value")
    if errs:
        raise SystemExit("LINT FAILED\n  " + "\n  ".join(errs[:40]))


def walk_fields(obj, path=""):
    if isinstance(obj, dict):
        if "grade" in obj and "value" in obj:
            yield path, obj
            return
        for k, v in obj.items():
            yield from walk_fields(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_fields(v, f"{path}[{i}]")


# ------------------------------------------------------------------- main --

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", nargs="+", required=True)
    a = ap.parse_args(argv)
    cache = Cache()
    sources = json.loads(SOURCES.read_text())
    leads_all = json.loads(LEADS.read_text())["products"]

    all_recs, all_log, all_conf, backlog, per_brand = [], [], [], [], {}
    for brand in a.brands:
        recs, log, conf, no_page, leads, man_rep = build_brand(cache, brand, sources["brands"][brand], leads_all, sources)
        all_recs += recs; all_log += log; all_conf += conf
        backlog += [{"brand": brand, "lead_key": r["model_key"], "lead_model": r["model"], "lead_title": r["title"],
                     "reason": "no page on the manufacturer's own site matches this lead by SKU or by a lead URL on the manufacturer's domain"}
                    for r in no_page]
        per_brand[brand] = {"leads": len(leads), "no_manufacturer_page": len(no_page), "log": log, "manuals": man_rep}

    apply_rules(all_recs)
    all_recs.sort(key=lambda r: r["inh_id"])
    all_conf.sort(key=lambda c: json.dumps(c, sort_keys=True, ensure_ascii=False))
    lint(all_recs, all_conf, sources)

    dump(OUT / "saunas.json", {"schema_version": "0.2.0", "cache_manifest_sha256": cache.sha,
                               "record_count": len(all_recs),
                               "published": sum(r["status"] == "published" for r in all_recs),
                               "records": all_recs})
    dump(OUT / "conflicts.json", {"conflict_count": len(all_conf), "conflicts": all_conf})
    dump(OUT / "internal/verification-log.json", {"records": all_log})
    dump(OUT / "internal/backlog.json", {"leads_without_origin_page": backlog})

    # ---- report
    rep = {"cache_manifest_sha256": cache.sha, "brands": {}}
    lead_fields = ["model_number", "heat_type", "placement", "capacity", "wood_species", "spectrum", "emf_claim",
                   "red_light", "supply_voltage", "stated_amperage", "connection_type", "heater_kw", "max_temp_f", "warranty"]
    confirmed_pool = []
    for brand, info in per_brand.items():
        c = Counter()
        for rl in info["log"]:
            for fld, x in rl["fields"].items():
                if fld in lead_fields and x["lead"] is not None:
                    c["lead_values"] += 1
                    c[x["outcome"]] += 1
                elif x["outcome"] == "source_only":
                    c["source_only"] += 1
                if x["outcome"] == "confirmed":
                    confirmed_pool.append((brand, rl["handle"], fld))
        disp = sources["brands"][brand]["display"]
        brecs = [r for r in all_recs if r["identity"]["brand"]["value"] == disp]
        rep["brands"][brand] = {
            "leads_in": info["leads"], "leads_without_manufacturer_page": info["no_manufacturer_page"],
            "records_built": len(brecs),
            "published": sum(r["status"] == "published" for r in brecs),
            "backlog": sum(r["status"] == "backlog" for r in brecs),
            "withheld_by_rule": dict(Counter(w["rule"] for r in brecs for w in r["withheld_reasons"])),
            "lead_values_in": c["lead_values"], "confirmed": c["confirmed"], "changed_by_source": c["changed"],
            "not_found": c["not_found"], "ambiguous_in_source": c["ambiguous"], "source_only_values": c["source_only"],
            "manuals": info["manuals"],
        }
    rng = random.Random(20260927)
    sample = rng.sample(sorted(confirmed_pool), min(10, len(confirmed_pool)))
    by_handle = {}
    for r in all_recs:
        for u in r["provenance"]["origin_urls"]:
            by_handle[u.rstrip("/").split("/")[-1]] = r
    spot = []
    for brand, handle, fld in sample:
        r = by_handle[handle]
        loc = {"model_number": ("identity", "model_number"), "wood_species": ("materials", "wood_species"),
               "max_temp_f": ("thermal", "max_temp_f"), "warranty": ("warranty", "summary"),
               "capacity": ("capacity_max",)}.get(fld)
        if loc is None:
            loc = next(((b, fld) for b in ("electrical", "infrared") if fld in r[b]), (fld,))
        node = r
        for k in loc:
            node = node[k]
        spot.append({"record": r["identity"]["display_title"], "field": fld, "value": node["value"],
                     "grade": node["grade"], "source_url": node["source_url"],
                     "snippet": node.get("evidence", {}).get("snippet"), "locator": node.get("evidence", {}).get("locator")})
    rep["spot_check"] = spot
    rep["conflicts_by_kind"] = dict(Counter(c["kind"] for c in all_conf))
    rep["fetch_problems"] = {u: e for u, e in cache.entries.items() if e.get("status") != 200}
    dump(REPORT, rep)
    print(json.dumps({b: {k: v for k, v in x.items()} for b, x in rep["brands"].items()}, indent=1))
    print("conflicts:", rep["conflicts_by_kind"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
