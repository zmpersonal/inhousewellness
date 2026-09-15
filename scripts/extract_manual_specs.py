#!/usr/bin/env python3
"""PHASE 3 -- read rated power out of manufacturer manuals.

WHERE THE MANUALS ARE
Not on manufacturer servers, and not as .pdf links. The Phase 1 census found 102
of 165 active sauna SKUs carrying a document reference in the
`custom.product_documents` metafield, every one a Google Drive embed. That is
the cheap path: it reaches Dynamic Saunas (host unreachable, TLS self-signed) and
every other blocked vendor WITHOUT touching their server.

WHY A MISREAD DIGIT MATTERS MORE HERE THAN ANYWHERE ELSE
Rated power is the headline running-cost number. A wrong kW is not a blank -- it
is a precise, confident, false dollar figure in a card the reader is told to
trust. So BOTH existing guards are imported from src/power_parse.py rather than
restated:
  * the comma-aware wattage parser, which caught "1,800 watts" reading as 800 W;
  * the 0.8-30 kW plausibility band, which rejected the 0.2/0.75 kW "saunas"
    that bug produced.
A value outside the band is recorded as REJECTED with its span, never dropped
silently and never clamped.

PRECEDENCE, and it is not resolved here
  manufacturer manual > manufacturer page > InHouse metafield > InHouse body
  > satellite CSV
This script only READS manuals. Disagreement with an existing value is recorded
as a finding for build_cost_tables.py to carry, never silently resolved.

A SPEC PLATE OUTRANKS MARKETING COPY. A reading whose span carries rating-label
vocabulary ("rating", "rated", "model no", "nameplate", "specification") is
marked tier `spec_plate`; everything else is `body_copy`. Both are kept with
their page number and verbatim span so a human can see which is which.

TEXT LAYER ONLY. A scanned manual has no text layer; it is counted and reported
as NEEDS_OCR and nothing is guessed from it. No OCR is performed.

    python3 scripts/extract_manual_specs.py --census data/own-page-census.json --limit 5
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.power_parse import (  # noqa: E402
    plausible, read_kw, read_watts, self_test as power_self_test,
)

UA = ("InHouseWellnessSpecBot/1.0 (+https://inhousewellness.com; "
      "support@inhousewellness.com) - reads manuals already linked from our own "
      "product pages; contact us to be excluded")

# Vocabulary that marks a rating label / spec table rather than marketing prose.
SPEC_PLATE_RX = re.compile(
    r"(?i)\b(rated|rating|nameplate|name plate|model\s*(?:no|number|#)|"
    r"specification|specs?\b|electrical\s+data|technical\s+data|serial)\b")

# "recommended" is not a rating. data/manufacturer-registry.json records the
# Dundalk case verbatim: "an 8 kW electric heater is recommended" states what to
# BUY, not what the unit draws, and reading it as a rating would put a number
# nobody measured into a running-cost line.
RECOMMENDATION_RX = re.compile(
    r"(?i)\b(recommend(?:ed|s|ation)?|suggest(?:ed|s)?|minimum|at least|up to|"
    r"optional|compatible with|suitable for)\b")


def drive_download_url(file_id):
    return "https://drive.google.com/uc?export=download&id=" + file_id


# Run 9 recorded three SaunaLife manuals as PDF_UNREADABLE, "Stream has ended
# unexpectedly" -- and all three were exactly 30,000,000 bytes long, which is the
# number that used to sit in the read() below. They were not damaged; WE cut them
# off, handed the stump to pypdf, and filed our own cap as a defect in the file.
# The same shape as every other failure in this project: a limit of ours arriving
# disguised as a fact about the source.
#
# A truncated read is now impossible to mistake for a short file: one byte MORE
# than the cap is requested, so going over is detectable, and a file over the cap
# is reported as TOO_LARGE with the cap named -- never parsed.
MAX_PDF_BYTES = 120_000_000


def fetch(url, attempts=3, delay=2.0):
    """(bytes, final_url, content_type, truncated). 429/5xx back off; they are
    never read as 'no data'."""
    for n in range(attempts):
        time.sleep(delay if n else 0)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read(MAX_PDF_BYTES + 1)
                return (raw[:MAX_PDF_BYTES], r.geturl(),
                        r.headers.get("Content-Type", ""), len(raw) > MAX_PDF_BYTES)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < attempts - 1:
                time.sleep(int(e.headers.get("Retry-After") or 0) or 2 ** (n + 2))
                continue
            raise
        except urllib.error.URLError:
            if n < attempts - 1:
                time.sleep(2 ** (n + 2))
                continue
            raise
    raise RuntimeError("exhausted retries for " + url)


def diagnose_non_pdf(final_url, ctype):
    """WHY it is not a PDF, from the response itself -- so "retry or lost" has an
    answer in the data instead of in someone's memory of the run."""
    if "accounts.google.com" in (final_url or ""):
        return ("Drive served a SIGN-IN page: this file is not shared publicly. "
                "Retrying the same URL cannot help -- the fix is on our own "
                "product page, by sharing the file or linking one that is shared")
    if "text/html" in (ctype or ""):
        return ("Drive served HTML, not a document -- typically an interstitial "
                "or an error page rather than the file")
    return "the bytes are not a PDF; content type " + repr(ctype)


def quieten_pdf_font_chatter():
    """fontTools and pypdf log a warning per substituted glyph. Run 4 buried its
    own output under hundreds of those lines, which is how a run that read FIVE
    products while printing "limit 102" went unnoticed. Only these two loggers
    are quietened, and only below ERROR: our own halts go through sys.exit and
    print, so nothing this script decides can be hidden by it."""
    import logging
    for name in ("fontTools", "fontTools.subset", "fontTools.ttLib", "pypdf"):
        logging.getLogger(name).setLevel(logging.ERROR)


def pages_of(raw):
    """[(page_number, text)] for a text-layer PDF. Empty list means no text
    layer -- a scan. Page numbers are 1-based, as a human reads them."""
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(raw))
    out = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            out.append((i, txt))
    return out


# ── MODEL-ADJACENT ATTRIBUTION ───────────────────────────────────────────────
# A manual is a document about a PRODUCT LINE, not about one SKU, and the run-8
# data showed three different ways that bites.
#
#   Golden Designs, one cover line, two models:
#     "GDI-8503-01 - 240VAC 30AMP Circuit Required (6kW Heater)
#      GDI-8506-01 - 240VAC 40AMP Circuit Required (8kW Heater)"
#   Both 6.0 and 8.0 were accepted for GDI-8503-01. Only 6.0 is that SKU's; the
#   model number sits immediately beside its own rating, and the 8 kW belongs to
#   a different cabin in the same line.
#
#   Dundalk Luna (CTC22LU), page 2, a HUUM HEATER PRICE LIST:
#     "BDB60 Designer B Electric Heater - 6KW ... BHUDR6L Huum Drop Heater - 6KW
#      ... BKIP60 Harvia KIP 6KW ... BRV60 Homecraft Revive Heater - 6KW"
#   Six kilowatts, five times, none of it this cabin's rating: that is a
#   catalogue of heaters someone can buy separately. Same rule as
#   recommendation-is-not-a-rating -- a number attached to a DIFFERENT product's
#   part number is a fact about that product.
#
# THE RULE: a rating is governed by the model number that most recently PRECEDES
# it in its span. Not the nearest one -- on the Golden Designs line the nearest
# token to the 6 kW is GDI-8506-01, nine characters AFTER it, and binding to it
# gives exactly the wrong answer. Variant tables and price lists are written
# label-then-spec, so "the record this value falls inside" is the relationship
# the page actually encodes.
#
# A rating with no model token before it in its window is UNBOUND, not bound to
# whatever follows. Dynamic's dimension drawing reads "Total power:1650W
# DYN-6225-02 200W 125W+125W": our model number is there, after the figure, and
# treating adjacency-after as ownership would be reading a layout as a claim.
# An unbound rating is left to the other guards, exactly as before this rule.
MODEL_TOKEN_RX = re.compile(
    # Letters first, so "240VAC", "30AMP" and "10AWG" -- a voltage, a breaker
    # size and a wire gauge -- can never be read as part numbers. A preceding
    # DIGIT is allowed: the Dundalk price list prints "1.00BHUDR6L", the unit
    # price glued to the item code, and a lookbehind excluding digits lost four
    # of the five Huum listings.
    r"(?<![A-Za-z])"
    r"([A-Z]{2,6}(?:-[A-Z0-9]{1,6})?-?\d{1,6}[A-Z]{0,3}(?:-\d{1,3})?)"
    r"(?![A-Za-z0-9])")

# Standards marks are shaped like part numbers and are not products. Binding a
# rating to "UL1026" and rejecting it would be a silent, confident loss.
STANDARDS_RX = re.compile(
    r"(?i)^(UL|CSA|ANSI|NFPA|NEC|NEMA|IEC|ISO|EN|CE|ETL|IEEE|ASTM|IP|AWG|"
    r"MIL|DIN|JIS|BS|AS|SAE)\d")


def model_tokens(text):
    """[(token, start, end)] for every part-number-shaped token in `text`."""
    return [(m.group(1), m.start(), m.end())
            for m in MODEL_TOKEN_RX.finditer(text)
            if not STANDARDS_RX.match(m.group(1))]


def norm_model(s):
    """Uppercase alphanumerics only. 'GDI-8503-01' and 'gdi 8503 01' are one
    model; nothing else about the string is allowed to decide identity."""
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def our_model_keys(skus, model_numbers):
    """Every string by which this SKU could be named in a manual.

    Both the whole identifier and the part-number token inside it: our variant
    SKU is "DYN-6225-02 Elite" and the manual prints "DYN-6225-02", so matching
    on the whole string alone would miss our own model sitting in plain sight.
    """
    keys = set()
    for raw in list(skus or []) + list(model_numbers or []):
        if not raw:
            continue
        keys.add(norm_model(raw))
        for tok, _, _ in model_tokens(raw.upper()):
            keys.add(norm_model(tok))
    return {k for k in keys if k}


def governing_model(span, at):
    """The model token this reading belongs to, or None if it is unbound."""
    gov = None
    for tok, _, end in model_tokens(span):
        if end <= at:
            gov = tok
    return gov


def model_binding(reading, our_keys):
    """(verdict, governing_model, models_seen_in_the_span).

    verdict is one of:
      None           -- no model token precedes the reading; not our business
      "OURS"         -- the governing model is this SKU
      "OTHER"        -- the governing model is a different product
      "UNVERIFIABLE" -- a model governs it and we hold no identifier to check
    """
    span, at = reading["span"], reading.get("at", 0)
    seen = [t for t, _, _ in model_tokens(span)]
    gov = governing_model(span, at)
    if gov is None:
        return None, None, seen
    if not our_keys:
        return "UNVERIFIABLE", gov, seen
    return ("OURS" if norm_model(gov) in our_keys else "OTHER"), gov, seen


def _binding_reason(gov, page_models, our_keys):
    """Two different facts, and the reason has to say which one this is.

    Our model ON THE SAME PAGE, bound to a different rating -> a variant table:
    the value is another cabin's, in a line we belong to. Our model NOWHERE on
    the page -> a catalogue of other products entirely. Both are rejections;
    conflating them would send a human looking for the wrong thing. The scope is
    the page, not the +/-70 character span: on the Golden Designs cover our SKU
    sits 45 characters outside the window around the OTHER model's rating, and
    judging by the window alone reported a variant table as a foreign catalogue.
    """
    ours_here = [t for t in page_models if norm_model(t) in our_keys]
    if ours_here:
        return (f"the span binds this rating to {gov}, and this SKU "
                f"({', '.join(sorted(set(ours_here)))}) appears on the same page "
                f"against a different rating. A model number sits immediately "
                f"beside its own rating, so this value belongs to another model "
                f"in the line -- it is not an alternative reading for this SKU")
    return (f"the span binds this rating to {gov}, which is not this SKU. A part "
            f"number in a catalogue of separately-sold heaters is a fact about "
            f"THAT heater, not this unit's rating -- the same rule as "
            f"recommendation-is-not-a-rating")


def readings_from(pages, url, our_keys=frozenset()):
    """Every stated kW/wattage reading, with page, span and tier. Both guards
    applied; an implausible value is kept as REJECTED, never dropped.

    `our_keys` is what this SKU is called (see our_model_keys). Model-adjacent
    attribution is checked FIRST, before the recommendation rule and before the
    plausibility band: "this number describes a different product" is a stronger
    statement than either, and a value rejected for belonging to another model
    must say so rather than be filed under a band it happens also to fail.
    """
    accepted, rejected = [], []
    for page_no, text in pages:
        flat = re.sub(r"[ \t]+", " ", text)
        page_models = [t for t, _, _ in model_tokens(flat)]
        for r in read_kw(flat, "manual_pdf", url) + read_watts(flat, "manual_pdf", url):
            r = dict(r, page=page_no)
            r["tier"] = "spec_plate" if SPEC_PLATE_RX.search(r["span"]) else "body_copy"
            verdict, gov, seen = model_binding(r, our_keys)
            if seen:
                r["models_in_span"] = seen
            if gov is not None:
                r["governing_model"] = gov
            if verdict == "OTHER":
                r["belongs_to_model"] = gov
                r["rejected_because"] = _binding_reason(gov, page_models, our_keys)
                rejected.append(r)
            elif verdict == "UNVERIFIABLE":
                r["belongs_to_model"] = gov
                r["rejected_because"] = (
                    f"the span binds this rating to {gov} and we hold no SKU or "
                    f"model number for this product, so it cannot be confirmed as "
                    f"ours. An unconfirmed attribution is not a rating")
                rejected.append(r)
            elif RECOMMENDATION_RX.search(r["span"]):
                r["rejected_because"] = ("the span states a recommendation, not a "
                                         "rating -- 'an 8 kW heater is recommended' "
                                         "says what to buy, not what this unit draws")
                rejected.append(r)
            elif not plausible(r["kw"]):
                r["rejected_because"] = "outside the 0.8-30 kW plausibility band"
                rejected.append(r)
            else:
                accepted.append(r)
    # A spec plate outranks marketing copy; within a tier, order is page order.
    accepted.sort(key=lambda r: (r["tier"] != "spec_plate", r["page"]))
    return accepted, rejected


# ── WHY A ZERO NEEDS ITS OWN EVIDENCE ───────────────────────────────────────
# Run 1 read nine real PDFs, 278 pages, no OCR needed -- and found not one rated
# power. That is either "the manuals do not state it" or "we could not read what
# they state", and this project's whole discipline is that those two are
# different facts. A bare zero cannot tell them apart.
#
# So every PDF now carries what its pages DO say near electrical vocabulary, and
# a raw sample of the page that says the most. If a manual states "Power Supply
# 120V 15A" and no wattage, that shows up as volts and amps with no watts. If
# pypdf is mangling glyphs, the sample shows "1 8 0 0 W" or mojibake and the
# zero is ours, not the manual's. No gate is loosened to get this: it is recorded
# beside the reading, never promoted into one.
ELECTRICAL_RX = re.compile(
    r"(?i)\b(volts?|voltage|amp(?:s|ere|erage)?|watt(?:s|age)?|kw|kilowatt|"
    r"power|rated|rating|breaker|circuit|hertz|hz|electrical|supply|consumption)\b")
MAX_CONTEXT_SPANS = 25
CONTEXT_PAD = 80


def electrical_context(pages):
    """What the pages say near power vocabulary, whether or not anything parsed.

    Returns (spans, pages_with_vocabulary, text_sample, chars_extracted). The
    sample is taken from the page with the most matches, so garbled extraction
    is visible at a glance rather than inferred from a silence.
    """
    spans, per_page, chars = [], {}, 0
    for page_no, text in pages:
        flat = re.sub(r"[ \t]+", " ", text)
        chars += len(flat)
        hits = list(ELECTRICAL_RX.finditer(flat))
        if hits:
            per_page[page_no] = (len(hits), flat)
        for m in hits:
            if len(spans) >= MAX_CONTEXT_SPANS:
                break
            lo = max(0, m.start() - CONTEXT_PAD)
            hi = min(len(flat), m.end() + CONTEXT_PAD)
            spans.append({"page": page_no, "term": m.group(1).lower(),
                          "span": re.sub(r"\s+", " ", flat[lo:hi]).strip()})
    sample = None
    if per_page:
        best = max(per_page, key=lambda k: per_page[k][0])
        sample = {"page": best,
                  "text": re.sub(r"\s+", " ", per_page[best][1])[:400]}
    return spans, len(per_page), sample, chars


# ── the deliberate sample, and checking a reading against what we already hold ──
SAMPLE = ROOT / "data" / "manual-sample.json"


def announce_scope(source, available, targets, limit):
    """Say WHERE the product list came from and HOW MANY, on one line, before any
    fetch. Run 4 printed "deliberate sample: 5 product(s), limit 102" -- the
    scope and the limit disagreed by twenty-fold and neither named its source.
    """
    pdfs = sum(t["manual_candidates"] for t in targets)
    print("SCOPE")
    print(f"  product list source : {source}")
    print(f"  candidates available: {available}")
    print(f"  products selected   : {len(targets)}   (limit {limit})")
    print(f"  PDFs to fetch       : {pdfs}")
    if len(targets) != available:
        print(f"  NOTE: reading {len(targets)} of {available}; this run does NOT "
              f"cover every candidate.")
    print()


def load_sample():
    """Handles to read, in order, from data/manual-sample.json. Run 1 took the
    first five products with a manual candidate -- 4 products, 3 vendors, one of
    them a cabin whose heater is bought separately. A sample that cannot separate
    'these manuals do not state wattage' from 'we read the wrong manuals' answers
    nothing, so which SKUs are read is now data with a reason attached."""
    doc = json.loads(SAMPLE.read_text())
    return [(s["handle"], s) for s in doc["sample"]]


def our_stated_kw(census_row):
    """What OUR OWN pages state for this SKU, from the census. The deliberate
    sample file may override it, because that file was hand-checked.

    Every plausible value is returned, not just one: "6 kW stove, 8 kW optional
    upgrade" is a configurable product, and collapsing it to a single number here
    would manufacture a disagreement out of a choice.
    """
    override = (census_row.get("_sample") or {}).get("our_metafield_kw")
    if override is not None:
        return override
    vals = sorted({x["kw"] for x in census_row.get("rated_power_stated") or []
                   if x.get("within_plausible_band")})
    return vals or None


def compare_to_our_value(our_kw, readings):
    """Corroboration or a finding -- recorded, never resolved.

    EVERY reading is considered, not just the first. The first version compared
    only readings[0] and reported FD-4 as DISAGREES: our metafields say 1.9 kW,
    and page 22 of the shared Trinity manual says
    "Trinity(TM) = 15a 120v 1750 watts * Harvia(TM) Vega Compact = 20a 120v 1900
    watts". readings[0] was the 1750 W; the 1900 W sitting beside it matches ours
    EXACTLY. A confident, precise, wrong verdict from looking at one of two
    numbers on one line -- this project's own recurring failure shape.

    "DISAGREES" is also the wrong word for a line-wide manual. One Finnmark PDF
    serves FD-4 and FD-5, one Scandia PDF serves two barrel kits; a rating absent
    from such a document usually means it covers a different variant, not that
    the two sources contradict each other. So the verdict is NO_MATCHING_READING
    and every manual value is listed with its span, for a human to attribute.
    """
    ours = ([] if our_kw is None else
            [our_kw] if isinstance(our_kw, (int, float)) else sorted(set(our_kw)))
    if not ours:
        return {"verdict": "NO_VALUE_OF_OURS",
                "manual_kw": [r["kw"] for r in readings],
                "detail": "we hold no rated_power_kw for this SKU, so a manual "
                          "reading would be new information, not a check"}
    our_kw = ours[0] if len(ours) == 1 else ours
    if not readings:
        return {"verdict": "NO_MANUAL_READING", "our_kw": our_kw,
                "detail": "our metafields state a kW and the manual yielded none; "
                          "that is a gap in the manual path, not a disagreement"}

    matches = [r for r in readings if any(abs(r["kw"] - o) < 0.051 for o in ours)]
    listed = [{"kw": r["kw"], "page": r["page"], "tier": r["tier"],
               "span": r["span"]} for r in readings]
    if matches:
        m = matches[0]
        return {"verdict": "AGREES", "our_kw": our_kw, "manual_kw": m["kw"],
                "manual_page": m["page"], "manual_span": m["span"],
                "manual_tier": m["tier"], "all_manual_readings": listed,
                "detail": "a stated rating in the manual matches ours exactly"}
    return {"verdict": "NO_MATCHING_READING", "our_kw": our_kw,
            "all_manual_readings": listed,
            "detail": "the manual states ratings, none of which is ours. On a "
                      "manual shared across a product line this usually means the "
                      "document covers a different variant -- not that the two "
                      "sources contradict. Attribute by hand from the spans; "
                      "nothing is overwritten here."}


def annotate_shared(rows):
    """Which other SKUs are served by the same PDF.

    Every manual in the run-2 sample is shared by two SKUs: one Finnmark PDF
    serves FD-4 and FD-5, one Scandia PDF serves two barrel kits. A figure in a
    line-wide document cannot be attributed to one SKU without the span naming
    the model -- and on page 22 of the Finnmark manual it does exactly that.
    """
    by_file = {}
    for r in rows:
        fid = r.get("file_id")
        if fid is None:
            continue          # a .pdf href carries no Drive id; it groups with nothing
        by_file.setdefault(fid, set()).add(r["handle"])
    for r in rows:
        fid = r.get("file_id")
        if fid is None:
            # Explicit: unknown sharing is recorded as unknown, not as "shared
            # with nobody". Grouping every id-less row under a None key would
            # have reported them as sharing one another.
            r["manual_shared_with"] = None
            r["manual_shared_with_reason"] = "no Drive file id; sharing not determinable"
            continue
        r["manual_shared_with"] = sorted(by_file[fid] - {r["handle"]})
    return rows


def recompare(path):
    """Recompute comparisons and sharing from readings already on disk. No
    request is made: a fixed verdict must never cost another vendor a fetch."""
    doc = json.loads(pathlib.Path(path).read_text())
    for r in doc["rows"]:
        if r.get("status") != "OK":
            continue
        our = r["our_metafield_kw"] if "our_metafield_kw" in r else None
        r["comparison"] = compare_to_our_value(our, r.get("readings", []))
    annotate_shared(doc["rows"])
    doc["recompared_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pathlib.Path(path).write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def self_test():
    """Both guards, the tiering, and the recommendation rule -- fired at text
    that must and must not yield a rating."""
    fails = []
    fails += ["power_parse: " + f for f in power_self_test()]

    def rd(text):
        return readings_from([(1, text)], "u")

    ok, bad = rd("RATED POWER: 1,800 watts")
    if not (ok and ok[0]["kw"] == 1.8):
        fails.append("the comma-aware parser did not read 1,800 watts as 1.8 kW: %r" % ok)
    if ok and ok[0]["tier"] != "spec_plate":
        fails.append("a RATED line was not tiered as a spec plate: %r" % ok)

    ok, bad = rd("Heater rating 9 kW")
    if not (ok and ok[0]["kw"] == 9.0 and ok[0]["page"] == 1):
        fails.append("kW not read, or page lost: %r" % ok)

    ok, bad = rd("This unit sips just 200 W on standby")
    if ok:
        fails.append("a 0.2 kW value passed the plausibility band: %r" % ok)
    if not (bad and "plausibility band" in bad[0]["rejected_because"]):
        fails.append("an implausible value was dropped instead of recorded: %r" % bad)

    ok, bad = rd("An 8 kW electric heater is recommended for optimal performance.")
    if ok:
        fails.append("a RECOMMENDED heater size was read as this unit's rating: %r" % ok)
    if not (bad and "recommendation" in bad[0]["rejected_because"]):
        fails.append("the recommendation was not recorded as rejected: %r" % bad)

    ok, _ = rd("Our saunas feel wonderful. Specification: 4.5 kW")
    if not (ok and ok[0]["tier"] == "spec_plate"):
        fails.append("Specification: not tiered as a spec plate: %r" % ok)

    # the diagnostic must show what a silent manual DOES say
    spans, npages, sample, chars = electrical_context(
        [(1, "Nothing relevant here."), (7, "Power Supply 120V 15A dedicated circuit")])
    if npages != 1:
        fails.append("electrical vocabulary counted on the wrong number of pages")
    terms = {s["term"] for s in spans}
    if not {"power", "supply", "circuit"} <= terms:
        fails.append("the diagnostic missed volts/amps vocabulary: %r" % terms)
    if not (spans and spans[0]["page"] == 7):
        fails.append("the diagnostic lost the page number: %r" % spans)
    if not (sample and sample["page"] == 7 and "120V" in sample["text"]):
        fails.append("the text sample did not come from the densest page: %r" % sample)
    if chars <= 0:
        fails.append("chars_extracted not counted")
    if electrical_context([])[0]:
        fails.append("the diagnostic invented context for an empty PDF")

    # the comparison against our own metafield never resolves anything
    c = compare_to_our_value(9.0, [{"kw": 9.0, "page": 3, "span": "s", "tier": "spec_plate"}])
    if c["verdict"] != "AGREES":
        fails.append("identical ratings not reported as agreement: %r" % c)
    # THE REAL CASE: two ratings on one FAQ line, the SECOND one matching ours.
    trinity = [{"kw": 1.75, "page": 22, "span": "Trinity 1750 watts", "tier": "body_copy"},
               {"kw": 1.9, "page": 22, "span": "Harvia Vega Compact 1900 watts",
                "tier": "body_copy"}]
    c = compare_to_our_value(1.9, trinity)
    if c["verdict"] != "AGREES" or c["manual_kw"] != 1.9:
        fails.append("a match on the SECOND reading was missed -- the run-2 bug: %r" % c)
    if len(c.get("all_manual_readings", [])) != 2:
        fails.append("the non-matching reading was dropped instead of listed")
    c = compare_to_our_value(4.5, trinity)
    if c["verdict"] != "NO_MATCHING_READING" or c["our_kw"] != 4.5:
        fails.append("no matching reading was not reported as such: %r" % c)
    if [x["kw"] for x in c["all_manual_readings"]] != [1.75, 1.9]:
        fails.append("every manual value must be listed for attribution: %r" % c)
    if compare_to_our_value(9.0, [])["verdict"] != "NO_MANUAL_READING":
        fails.append("a missing manual reading was not distinguished from a disagreement")
    if compare_to_our_value(None, [])["verdict"] != "NO_VALUE_OF_OURS":
        fails.append("no value of ours was not distinguished from no manual reading")

    # ── MODEL-ADJACENT ATTRIBUTION, fired at the three real spans ──────────
    GDI = ("FOR INDOOR/OUTDOOR USE GDI-8503-01 - 240VAC 30AMP Circuit Required "
           "(6kW Heater) GDI-8506-01 - 240VAC 40AMP Circuit Required (8kW Heater) "
           "Carefully and thoroughly read this Owner's Manual before using.")
    KAS = GDI.replace("GDI-8503-01", "GDI-8523-01").replace("GDI-8506-01",
                                                            "GDI-8526-01")
    HUUM = ("BDB60 Designer B Electric Heater - 6KW 1.00BHUDR6L Huum Drop Heater - "
            "6KW LOCAL CONTROL 1.00BKIP60 Harvia KIP 6KW Sauna Heater 1.00BRV60 "
            "Homecraft Revive Heater - 6KW Includes Rocks, 1.00")
    DYN = ('21.9" Total power:1650W DYN-6225-02 200W 125W+125W 20" 46.8"1.6"')

    for text, sku, want_kw, want_other in (
            (GDI, "GDI-8503-01", 6.0, "GDI-8506-01"),
            # The client's note said "same on GDI-8526-01", meaning 6.0. The span
            # says otherwise: on the Kaskinen cover GDI-8523-01 carries the 6 kW
            # and GDI-8526-01 -- our SKU -- carries the 8 kW. The rule follows the
            # document, and this control pins that it does.
            (KAS, "GDI-8526-01", 8.0, "GDI-8523-01")):
        acc, rej = readings_from([(1, text)], "u", our_model_keys([sku], []))
        if [r["kw"] for r in acc] != [want_kw]:
            fails.append(f"{sku}: model-adjacent binding kept "
                         f"{[r['kw'] for r in acc]}, wanted [{want_kw}]")
        if not (rej and rej[0].get("belongs_to_model") == want_other):
            fails.append(f"{sku}: the other model's rating was not recorded as "
                         f"belonging to {want_other}: {rej}")

    acc, rej = readings_from([(2, HUUM)], "u", our_model_keys(["CTC22LU"], []))
    if acc:
        fails.append("a catalogue of separately-sold heaters was read as this "
                     "cabin's rating: %r" % [r["kw"] for r in acc])
    if len(rej) != 4 or not all("not this SKU" in r["rejected_because"] for r in rej):
        fails.append("the Huum price list was not rejected item by item: %r"
                     % [(r["kw"], r.get("belongs_to_model")) for r in rej])

    acc, _ = readings_from([(1, DYN)], "u", our_model_keys(["DYN-6225-02 Elite"], []))
    if [r["kw"] for r in acc] != [1.65]:
        fails.append("a stated total whose model number FOLLOWS it was lost: %r"
                     % [r["kw"] for r in acc])
    if acc and acc[0].get("governing_model") is not None:
        fails.append("a rating was bound to a model that comes after it")

    acc, rej = readings_from([(1, GDI)], "u", frozenset())
    if acc or not (rej and "hold no SKU" in rej[0]["rejected_because"]):
        fails.append("with no identifier of ours, a model-bound rating was not "
                     "recorded as unverifiable: %r" % (acc or rej))

    acc, _ = readings_from([(1, "Conforms to UL1026. Rated power 6 kW")], "u",
                           our_model_keys(["ABC-1"], []))
    if [r["kw"] for r in acc] != [6.0]:
        fails.append("a standards mark was treated as a product model number: %r"
                     % acc)

    # spec plate must sort ahead of body copy
    acc, _ = readings_from([(1, "warms with 3 kW of gentle heat"),
                            (2, "Rated power: 6 kW")], "u")
    if not (acc and acc[0]["kw"] == 6.0 and acc[0]["page"] == 2):
        fails.append("body copy outranked a spec plate: %r" % acc)
    return fails


def main():
    quieten_pdf_font_chatter()
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="data/own-page-census.json")
    ap.add_argument("--out", default="data/facts/manual_specs.json")
    ap.add_argument("--limit", type=int, default=5,
                    help="stop after N products. With --sample, a limit larger "
                         "than the sample HALTS rather than silently capping.")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--all", action="store_true",
                    help="read every product carrying a manual candidate, in "
                         "census order. Mutually exclusive with --sample.")
    ap.add_argument("--sample", action="store_true",
                    help="read the deliberate sample in data/manual-sample.json "
                         "instead of the first N products with a manual")
    ap.add_argument("--recompare", action="store_true",
                    help="recompute comparisons from readings already on disk, "
                         "without fetching anything")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: the manual extractor failed its own controls:\n  "
                     + "\n  ".join(fails))
        print("extract_manual_specs self-test: both guards fire, a recommendation "
              "is never read as a rating, and a spec plate outranks body copy")
        return

    if args.recompare:
        doc = recompare(ROOT / args.out)
        print(f"recompared {len(doc['rows'])} row(s) from {args.out}, no fetch")
        for r in doc["rows"]:
            c = r.get("comparison") or {}
            print(f"  {r['handle'][:40]:42s} {c.get('verdict')}")
        return

    rows = {r["handle"]: r for r in
            json.loads((ROOT / args.census).read_text())["rows"]}
    if args.sample and args.all:
        sys.exit("HALT: --sample and --all name different scopes. Pick one.")

    if args.all:
        available = [r for r in rows.values() if r.get("manual_candidates")]
        if args.limit > len(available):
            sys.exit(f"HALT: --limit {args.limit} exceeds the {len(available)} "
                     f"products carrying a manual candidate in {args.census}. "
                     f"A limit larger than the supply cannot be met, and capping "
                     f"it silently is how run 4 printed 'limit 102' beside "
                     f"'5 product(s)'.")
        targets = available[:args.limit]
        announce_scope(f"{args.census} (ALL candidates)", len(available), targets,
                       args.limit)
    elif args.sample:
        chosen = load_sample()
        if args.limit > len(chosen):
            # Run 4 was dispatched as "limit 102" and read FIVE products, because
            # --sample truncates to the sample file's length and a bigger --limit
            # silently meant nothing. A run whose name says 102 and whose scope is
            # 5 is the worst kind of wrong: it looks like coverage. Halt instead.
            sys.exit(
                f"HALT: --limit {args.limit} exceeds the {len(chosen)} entries in "
                f"{SAMPLE.relative_to(ROOT)}, so it would silently read only "
                f"{len(chosen)}. Use --all for every candidate, or lower --limit.")
        n_available = len(chosen)
        chosen = chosen[:args.limit]
        missing = [h for h, _ in chosen if h not in rows]
        if missing:
            sys.exit("HALT: data/manual-sample.json names handles absent from the "
                     "census: " + ", ".join(missing))
        targets = [dict(rows[h], _sample=meta) for h, meta in chosen]
        announce_scope(str(SAMPLE.relative_to(ROOT)) + " (DELIBERATE SAMPLE)",
                       n_available, targets, args.limit)
        for r in targets:
            m = r["_sample"]
            print(f"  {r['handle']:42s} {m['vendor']:18s} "
                  f"our_kW={m['our_metafield_kw']}  manuals={r['manual_candidates']}")
        print()
    else:
        sys.exit("HALT: pick a scope -- --sample for the deliberate five, or "
                 "--all for every product carrying a manual candidate.")

    out, needs_ocr = [], 0
    for r in targets:
        for m in r["manuals"]:
            if m["role"] != "manual_candidate":
                continue
            url = m.get("url") or drive_download_url(m["file_id"])
            model_numbers = [x["value"] for x in r["model_numbers"]]
            our_keys = our_model_keys(r["skus"], model_numbers)
            rec = {"handle": r["handle"], "vendor": r["vendor"], "skus": r["skus"],
                   "model_numbers": model_numbers, "our_model_keys": sorted(our_keys),
                   "pdf_url": url, "file_id": m.get("file_id")}
            try:
                raw, final, ctype, truncated = fetch(url, delay=args.delay)
            except Exception as e:
                rec["status"] = "FETCH_FAILED"
                rec["error"] = f"{type(e).__name__}: {str(e)[:160]}"
                if "404" in str(e):
                    rec["diagnosis"] = ("the Drive id embedded on our own product "
                                        "page resolves to nothing. A broken embed "
                                        "on our page, not a vendor problem; "
                                        "retrying cannot fix it")
                out.append(rec)
                print(f"  {r['handle']:44s} FETCH_FAILED {rec['error'][:60]}")
                continue
            rec["final_url"], rec["content_type"] = final, ctype
            rec["bytes"] = len(raw)
            if truncated:
                rec["status"] = "TOO_LARGE"
                rec["error"] = (f"over the {MAX_PDF_BYTES:,}-byte read cap; NOT "
                                f"parsed. A truncated PDF is not a damaged PDF, "
                                f"and reporting it as one blames the publisher "
                                f"for our limit")
                out.append(rec)
                print(f"  {r['handle']:44s} TOO_LARGE (> {MAX_PDF_BYTES:,} bytes)")
                continue
            if not raw.startswith(b"%PDF"):
                # Drive serves an HTML interstitial for large or restricted files,
                # and a video is not a manual. Either way this is not a PDF.
                rec["status"] = "NOT_A_PDF"
                rec["first_bytes"] = raw[:16].decode("latin-1", "replace")
                rec["diagnosis"] = diagnose_non_pdf(final, ctype)
                out.append(rec)
                print(f"  {r['handle']:44s} NOT_A_PDF ({ctype})")
                continue
            try:
                pages = pages_of(raw)
            except Exception as e:
                # A malformed PDF is a finding about that file, never a reason to
                # discard the run. Run 5 read ~140 of 142 manuals and then died on
                # one truncated stream, committing nothing -- the same shape as a
                # gate that destroys the evidence it was meant to check.
                rec["status"] = "PDF_UNREADABLE"
                rec["error"] = f"{type(e).__name__}: {str(e)[:160]}"
                out.append(rec)
                print(f"  {r['handle']:44s} PDF_UNREADABLE {rec['error'][:56]}")
                continue
            if not pages:
                rec["status"] = "NEEDS_OCR"
                needs_ocr += 1
                out.append(rec)
                print(f"  {r['handle']:44s} NEEDS_OCR (no text layer)")
                continue
            acc, rej = readings_from(pages, final, our_keys)
            ctx, npages_elec, sample, chars = electrical_context(pages)
            our_kw = our_stated_kw(r)
            rec["our_metafield_kw"] = our_kw
            rec["comparison"] = compare_to_our_value(our_kw, acc)
            rec.update(status="OK", pages=len(pages), readings=acc, rejected=rej,
                       chars_extracted=chars,
                       pages_with_electrical_vocabulary=npages_elec,
                       electrical_context=ctx, text_sample=sample)
            out.append(rec)
            best = acc[0] if acc else None
            print(f"  {r['handle']:44s} {len(pages):>3}pp  "
                  f"{(str(best['kw']) + ' kW') if best else 'no rating found':>16}"
                  f"   elec-vocab on {npages_elec}/{len(pages)}pp, "
                  f"{chars:,} chars extracted")

    annotate_shared(out)
    doc = {"name": "manual_specs",
           "note": "Source precedence tier 1 (manuals). Stated ratings only; never "
                   "derived from volts x amps. Guards imported from "
                   "src/power_parse.py. A recommendation is not a rating.",
           "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "row_count": len(out), "needs_ocr": needs_ocr, "rows": out}
    dest = ROOT / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"\nwrote {args.out}  rows={len(out)}  needs_ocr={needs_ocr}")

    print("\n" + "=" * 78)
    print("THE PAIRS -- read these before anything scales")
    print("=" * 78)
    for rec in out:
        if rec.get("status") != "OK":
            print(f"\n  {rec['handle']}  [{rec.get('status')}]  {rec['pdf_url']}")
            continue
        for rd in rec.get("readings", [])[:2]:
            print(f"\n  SKU        {', '.join(rec['skus']) or '(none)'}")
            print(f"  model no.  {', '.join(rec['model_numbers']) or '(none on our page)'}")
            print(f"  rated      {rd['kw']} kW   [{rd['basis']} / {rd['tier']}]")
            print(f"  page       {rd['page']} of {rec['pages']}")
            print(f"  span       ...{rd['span']}...")
            print(f"  url        {rec['final_url']}")
        for rd in rec.get("rejected", [])[:2]:
            print(f"\n  SKU        {', '.join(rec['skus']) or '(none)'}   REJECTED")
            print(f"  value      {rd['kw']} kW -- {rd['rejected_because']}")
            print(f"  page       {rd['page']}   span ...{rd['span']}...")


if __name__ == "__main__":
    main()
