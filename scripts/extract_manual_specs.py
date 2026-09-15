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


def fetch(url, attempts=3, delay=2.0):
    """Bytes, or raise. 429/5xx back off; they are never read as 'no data'."""
    for n in range(attempts):
        time.sleep(delay if n else 0)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(30_000_000), r.geturl(), r.headers.get("Content-Type", "")
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


def readings_from(pages, url):
    """Every stated kW/wattage reading, with page, span and tier. Both guards
    applied; an implausible value is kept as REJECTED, never dropped."""
    accepted, rejected = [], []
    for page_no, text in pages:
        flat = re.sub(r"[ \t]+", " ", text)
        for r in read_kw(flat, "manual_pdf", url) + read_watts(flat, "manual_pdf", url):
            r = dict(r, page=page_no)
            r["tier"] = "spec_plate" if SPEC_PLATE_RX.search(r["span"]) else "body_copy"
            if RECOMMENDATION_RX.search(r["span"]):
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

    # spec plate must sort ahead of body copy
    acc, _ = readings_from([(1, "warms with 3 kW of gentle heat"),
                            (2, "Rated power: 6 kW")], "u")
    if not (acc and acc[0]["kw"] == 6.0 and acc[0]["page"] == 2):
        fails.append("body copy outranked a spec plate: %r" % acc)
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="data/own-page-census.json")
    ap.add_argument("--out", default="data/facts/manual_specs.json")
    ap.add_argument("--limit", type=int, default=5,
                    help="stop after N products. The client reads the first five "
                         "pairs before anything scales; do not raise this without "
                         "that review.")
    ap.add_argument("--delay", type=float, default=2.0)
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

    rows = json.loads((ROOT / args.census).read_text())["rows"]
    targets = [r for r in rows if r.get("manual_candidates")][:args.limit]
    print(f"{len(targets)} product(s) with a manual candidate, limit {args.limit}\n")

    out, needs_ocr = [], 0
    for r in targets:
        for m in r["manuals"]:
            if m["role"] != "manual_candidate":
                continue
            url = m.get("url") or drive_download_url(m["file_id"])
            rec = {"handle": r["handle"], "vendor": r["vendor"], "skus": r["skus"],
                   "model_numbers": [x["value"] for x in r["model_numbers"]],
                   "pdf_url": url, "file_id": m.get("file_id")}
            try:
                raw, final, ctype = fetch(url, delay=args.delay)
            except Exception as e:
                rec["status"] = "FETCH_FAILED"
                rec["error"] = f"{type(e).__name__}: {str(e)[:160]}"
                out.append(rec)
                print(f"  {r['handle']:44s} FETCH_FAILED {rec['error'][:60]}")
                continue
            rec["final_url"], rec["content_type"] = final, ctype
            if not raw.startswith(b"%PDF"):
                # Drive serves an HTML interstitial for large or restricted files,
                # and a video is not a manual. Either way this is not a PDF.
                rec["status"] = "NOT_A_PDF"
                rec["first_bytes"] = raw[:16].decode("latin-1", "replace")
                out.append(rec)
                print(f"  {r['handle']:44s} NOT_A_PDF ({ctype})")
                continue
            pages = pages_of(raw)
            if not pages:
                rec["status"] = "NEEDS_OCR"
                needs_ocr += 1
                out.append(rec)
                print(f"  {r['handle']:44s} NEEDS_OCR (no text layer)")
                continue
            acc, rej = readings_from(pages, final)
            ctx, npages_elec, sample, chars = electrical_context(pages)
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
