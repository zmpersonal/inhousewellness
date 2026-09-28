#!/usr/bin/env python3
"""INH Verified Round 3 — gap diagnosis for records below the page threshold.

    .venv/bin/python scripts/verified_gaps.py --fetch      # ONLINE: static page, headless render, linked PDFs
    .venv/bin/python scripts/verified_gaps.py              # OFFLINE: classify from the cache -> data/verified/gap-diagnosis.json

For every published record of the target brands that misses the threshold, each missing
field (heat type, capacity, exterior dimensions, electrical) gets exactly one class:

  OPTION_DEPENDENT  the product page makes the buyer choose something in that field's group
                    (heater/electrical, size, sauna type); the option text is quoted.
  STATED_MISSED     a document we fetched WITHOUT JavaScript (product JSON, static page HTML,
                    a PDF the page links) states it; the snippet is quoted. The extractor or
                    the adapter missed it.
  JS_ONLY           it appears only in the headless render of the page.
  NOT_STATED        the page (static AND rendered) and EVERY document it links were fetched
                    and read, and none states it. `checked` lists what was read.
  NOT_VERIFIED      anything needed for the above failed to fetch or parse: never NOT_STATED.

The detectors are deliberately BROAD (a candidate statement, quoted for a human), so they
err toward STATED_MISSED and away from NOT_STATED: a wrong NOT_STATED would later print
"Not stated on the manufacturer's page" about a manufacturer that does state it. Link text
(<a>…</a>), navigation, headers and footers are removed before searching, because a menu
entry like "4-5 Person Saunas" is not a statement about this product.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "data/verified/gap-diagnosis.json"
TARGETS = ["Almost Heaven Saunas", "Clearlight", "Sun Home Saunas", "Redwood Outdoors", "Heavenly Heat Saunas"]
ALSO = ["Dundalk Leisurecraft", "SaunaLife", "Scandia"]      # "which fixes would help these automatically"
FIELDS = ["heat type", "capacity", "exterior dimensions", "electrical"]
GROUP = {"electrical": "electrical", "heat type": "type", "capacity": "size", "exterior dimensions": "size"}

# Whole inches with an optional fraction: "51 3/4", "86-5/8", "75 ⅜", "80⁵⁄₁₆".
FRAC = r"\d+(?:\.\d+)?(?:(?:\s+|-)\d/\d+|\s?[¼½¾⅛⅜⅝⅞⅓⅔]|\s?[⁰¹²³⁴⁵⁶⁷⁸⁹]+⁄[₀₁₂₃₄₅₆₇₈₉]+)?"
INCH = r"(?:\"|″|”|''|\s?in\.?\b|\s?inch(?:es)?\b)"
UNIT_P = r"(?:people|persons?|adults?|users?)"
# Each field: [(rank, regex)]. Lower rank = more specific; the best-ranked candidate is quoted.
DETECT = {
    "capacity": [
        (0, re.compile(rf"(?i)\b(?:seats?|seating(?:\s+for)?|accommodates?|comfortably\s+seats?)\s*\d{{1,2}}(?:\s*(?:-|–|to)\s*\d{{1,2}})?\s*{UNIT_P}?\b")),
        (0, re.compile(rf"(?i)\b(?:fits|holds|up\s+to|room\s+for|capacity(?:\s+of)?:?)\s*\d{{1,2}}(?:\s*(?:-|–|to)\s*\d{{1,2}})?\s*{UNIT_P}\b")),
        (1, re.compile(r"(?i)\b\d{1,2}(?:\s*(?:-|–|to)\s*\d{1,2})?[\s-]*(?:person|people|persons)\b(?!\s+saunas)")),
    ],
    "exterior dimensions": [
        (0, re.compile(rf"(?i)\b(?:exterior|outside|overall|external|outer)\s+(?:dimensions?|size|measurements?)\b[^\n]{{0,80}}?{FRAC}\s*(?:{INCH}|[xX×])")),
        (0, re.compile(rf"(?i)\b(?:assembled\s+)?exterior\s*[·:\-–]?\s*(?:W\s*[×x]\s*D\s*[×x]\s*H)?\s*{FRAC}\s*{INCH}?\s*[×x]\s*{FRAC}")),
        (0, re.compile(rf"(?i)\b(?:exterior|outside|overall|external)\s+(?:width|depth|height|length)\s*:?\s*{FRAC}")),
        (1, re.compile(rf"(?i)\b(?:dimensions?|size)\s*(?:\((?:[WDHL]\s*x\s*){{1,2}}[WDHL]\))?\s*:?\s*{FRAC}\s*{INCH}?\s*[xX×]\s*{FRAC}")),
        (1, re.compile(rf"(?i)\bwidth\s*:?\s*{FRAC}\s*{INCH}?[^\n]{{0,40}}\bdepth\s*:?\s*{FRAC}")),
        (1, re.compile(rf"{FRAC}\s*{INCH}\s*\(?[WDHL]\)?\s*[xX×]\s*{FRAC}\s*{INCH}\s*\(?[WDHL]\)?\s*[xX×]\s*{FRAC}\s*{INCH}\s*\(?[WDHL]\)?")),
        (2, re.compile(rf"(?i){FRAC}\s*{INCH}\s*(?:\(?[WDHL]\)?|wide|deep|high|tall)?\s*[xX×]\s*{FRAC}\s*{INCH}?\s*(?:\(?[WDHL]\)?|wide|deep|high|tall)?\s*[xX×]\s*{FRAC}")),
    ],
    "heat type": [
        (0, re.compile(r"(?i)\b(?:far[- ]infrared|full[- ]spectrum|near[- ]infrared)\b")),
        (0, re.compile(r"(?i)\b(?:traditional\s+sauna|infrared\s+sauna)\b")),
        (2, re.compile(r"(?i)\bsteam\s+(?:room|sauna)\b")),
        (2, re.compile(r"(?i)\b(?:sauna\s+stove|wood[- ](?:burning|fired)\s+(?:sauna\s+)?(?:stove|heater)|electric\s+(?:sauna\s+)?heater)\b")),
        (2, re.compile(r"(?i)\b(?:harvia|huum|homecraft|saunum)\b")),
    ],
    "electrical": [
        (0, re.compile(r"\b(?:1[12]0|2[0-4]0|208)\s*-?\s*(?:V|VAC|[Vv]olts?)\b")),
        (0, re.compile(r"\b\d{2}\s*-?\s*(?:[Aa]mps?|[Aa]mperes?|AMPS?)\b")),
        (0, re.compile(r"\b(?:1[12]0|2[0-4]0|208)\s*V\s*/\s*\d{2}\s*A\b")),
        (0, re.compile(r"\b\d+(?:\.\d+)?\s*-?\s*(?:kW|KW|kw)\b")),
        (1, re.compile(r"(?i)\bhard[- ]?wired\b|\bplug[- ]and[- ]play\b|\bNEMA\s*\d")),
    ],
}
NOT_EXTERIOR = re.compile(r"(?i)\b(?:interior|inside|internal|bench|shipping|package|packag|crate|crated|carton|box|mat|pad|treatment|heater|stove|door|window|glass|rock|stone)\b")
EXTERIOR_WORD = re.compile(r"(?i)\b(?:exterior|outside|overall|external|outer)\b")
OPTION_TEXT = re.compile(r"(?i)\bheater\s+options?\b\s*\*?[^\n]{0,220}")
OPTION_CHOICE = re.compile(r"(?i)\b\d+(?:\.\d+)?\s*kw\b|\bwood\s+heater\b|\bno\s+heater\b|\belectric\s+heater\b")
BAD_DIM_LABEL = re.compile(r"(?i)\b(?:bench|porch|canopy|cradle|door|window|interior|inside|shipping|package|crate|box|heater|stove)\b")
HEAT_OPTION_NAME = re.compile(r"(?i)sauna\s+type|heat(?:ing)?\s+type")
HEAT_OPTION_VALUE = re.compile(r"(?i)\b(?:infrared|traditional|hybrid|steam)\b")
# The field is NAMED (a heading, a label) somewhere we read. Without figures, that is not "not stated".
FIELD_MENTION = {
    "exterior dimensions": re.compile(r"(?i)\bdimensions?\b|\bexterior\s+size\b"),
    "capacity": re.compile(r"(?i)\bcapacity\b|\bseating\b|\bseats\b"),
    "electrical": re.compile(r"(?i)\belectrical\b|\bvoltage\b|\bamperage\b|\bcircuit\b"),
    "heat type": re.compile(r"(?i)\bheat(?:ing)?\s+(?:type|source|method)\b|\bheater\b"),
}
INTERIOR_ONLY = re.compile(r"(?i)\b(?:interior|inside|internal|bench)\b")


# ------------------------------------------------------------------- fetch --

def targets(brands):
    import verified_pages as vp
    ds = vp.load_dataset()
    src = json.loads((ROOT / "data/verified/sources.json").read_text())["brands"]
    disp = {}
    import verified_build as vb
    for b, s in src.items():
        disp[vb.brand_label(s, b)] = b
    for r, t in vp.threshold(ds):
        b = disp.get(r["identity"]["brand"]["value"])
        if b in brands and not t["meets"]:
            yield r, t, b, src[b]


def pdf_links_of(vb, html_text, base, src):
    """PDF links from a page, including ones inside script-escaped JSON (`\\/`, trailing `\\"`):
    the Round 1 extractor kept the escape characters, so the real document was never read."""
    t = html_text.replace("\\/", "/").replace('\\"', '"')
    return {re.sub(r"[\\\"']+$", "", u) for u in vb.page_pdf_links(t, base, src)}


def page_urls(r):
    return sorted(u for u in r["provenance"]["origin_urls"] if not re.search(r"(?i)\.pdf(\?|$)|\.json(\?|$)", u))


def fetch_all(brands):
    import verified_build as vb
    import verified_fetch as vf
    from playwright.sync_api import sync_playwright
    m = vf.load_manifest()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for r, t, brand, src in targets(brands):
            own = lambda u: any(d in u for d in src["manufacturer_domains"])
            for u in page_urls(r):
                st = vf.fetch(u, m, own_site=own(u))
                rd = vf.fetch_rendered(u, m, b, own_site=own(u))
                links = set()
                for e in (st, rd):
                    if e.get("status") == 200:
                        links |= pdf_links_of(vb, (vf.CACHE / e["cache_file"]).read_text("utf-8", "replace"), u, src)
                for pdf in sorted(links):
                    vf.fetch(pdf, m, linked_asset=True)
        for extra_brand in brands:
            for extra in json.loads((ROOT / "data/verified/sources.json").read_text())["brands"][extra_brand].get("extra_urls", []):
                vf.fetch_rendered(extra, m, b)
        b.close()


# ---------------------------------------------------------------- classify --

def main_text(h: str) -> str:
    """Visible product text: scripts, styles, nav, header, footer, aside and ALL link text removed."""
    h = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|template)\b.*?</\1>", " ", h)
    # Link text is KEPT but marked: a size switcher ("1 Person · 2 Person …") is not a sentence
    # about this model, yet it is not nothing either. find() ranks matches inside links as weak.
    h = re.sub(r"(?is)<a\b[^>]*>(.*?)</a>", lambda m: " ⟦" + re.sub(r"<[^>]+>", " ", m.group(1)) + "⟧ ", h)
    import verified_build as vb
    return vb.html_to_text(h)


def meta_text(h: str) -> str:
    """The manufacturer's own page metadata: meta/Open Graph descriptions and JSON-LD
    name/description. Not visible body text, so it is reported under its own label."""
    parts = [htmllib.unescape(m.group(1)) for m in re.finditer(
        r'(?is)<meta[^>]+(?:name|property)="(?:description|og:description|og:title|twitter:description)"[^>]+content="([^"]*)"', h)]
    for blk in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h):
        parts += [htmllib.unescape(x) for x in re.findall(r'"(?:name|description)"\s*:\s*"((?:[^"\\]|\\.){0,600})"', blk)]
    return "\n".join(dict.fromkeys(parts))


def find(field, text):
    """Candidate statements, best-ranked first: [(rank, snippet)]."""
    out = []
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)     # a label and its figures may sit in separate elements
    for rank, rx in DETECT[field]:
        for m in rx.finditer(text):
            if text.rfind("⟦", 0, m.start()) > text.rfind("⟧", 0, m.start()):
                rank = 2                               # inside link text: weak by construction
            before = text[max(0, m.start() - 60): m.start() + 20]
            if field == "exterior dimensions":
                if NOT_EXTERIOR.search(before) and not EXTERIOR_WORD.search(before + m.group(0)):
                    continue   # an interior, bench, shipping, heater or door size is not the exterior
                label = re.split(r"\d", text[max(0, m.start() - 40): m.end()], 1)[0][-40:] if rank else \
                    re.split(r"\d", m.group(0), 1)[0]
                if BAD_DIM_LABEL.search(label):
                    continue   # "Exterior Bench Dimensions", "Canopy Porch Size": a part, not the sauna
            if field == "heat type" and re.search(r"(?i)steam\s+sauna\s+stones", text[m.start(): m.end() + 8]):
                continue       # "Authentic Steam / Sauna stones …": a heading run into a sentence
            out.append((rank, re.sub(r"\s+", " ", text[max(0, m.start() - 70): m.end() + 70]).strip()))
    return sorted(out, key=lambda x: x[0])


def option_text(srcs):
    """Option wording in the page text itself (configurators the product data does not expose)."""
    for s in srcs:
        if s[3] == 200 and s[0] == "page":
            for m in OPTION_TEXT.finditer(re.sub(r"\s+", " ", s[4])):
                if len({x.group(0).lower() for x in OPTION_CHOICE.finditer(m.group(0))}) >= 2:
                    return s, m.group(0).strip()   # a real choice list, not a promotion or an FAQ line
    return None, None


def sources_for(r, cache, brand, src, products):
    """[(label, url, method, status, text)] for everything this record's diagnosis may read."""
    import verified_build as vb
    import verified_fetch as vf
    out = []
    p = products.get(r["_product_handle"]) if r.get("_product_handle") else None
    if p is not None:
        body = vb.html_to_text(re.sub(r"(?is)<a\b[^>]*>.*?</a>", " ", p.body_html or ""))
        out.append(("product data (title, description)", p.fetched_url, "static", 200, f"{p.title}\n{p.product_type}\n{body}"))
    for u in page_urls(r):
        for label, key, method in (("page", u, "static"), ("page", vf.rendered_key(u), "headless")):
            data, e = cache.get(key)
            status = (e or {}).get("status", "not fetched")
            out.append((label, u, method, status, main_text(data.decode("utf-8", "replace")) if data else ""))
            out.append(("page metadata", u, method, status, meta_text(data.decode("utf-8", "replace")) if data else ""))
            if data:
                for pdf in sorted(pdf_links_of(vb, data.decode("utf-8", "replace"), u, src)):
                    man, why = vb.load_manual(cache, pdf)
                    out.append(("linked document", pdf, "static", 200 if man else why,
                                "\n".join(t for _, t in man.pages) if man else ""))
    # de-duplicate linked documents that two page versions both link
    seen, uniq = set(), []
    for s in out:
        k = (s[0], s[1], s[2])
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    return uniq


def classify_field(field, option_note, srcs, page_url):
    if option_note:
        return {"class": "OPTION_DEPENDENT", "source_url": page_url, "method": "static", "where": "product options",
                "snippet": option_note}
    if field == "electrical":
        s, txt = option_text(srcs)
        if s:
            return {"class": "OPTION_DEPENDENT", "source_url": s[1], "method": s[2], "where": "page text", "snippet": txt}
    def hits(method):
        return sorted(((rank, s, h) for s in srcs if s[2] == method and s[3] == 200 for rank, h in find(field, s[4])),
                      key=lambda x: x[0])

    def confirmed(rank, s, h=""):
        # A statement counts only when it is labelled or a plain sentence on the PAGE, or labelled
        # in a linked document (parts lists and drawings make everything else noise). A drawing's
        # "OVERALL DIMENSIONS 13’ 3-1/4” 10’ 3-1/4”" has no axes: from a document, a size needs a ×.
        if s[0] == "linked document" and field == "exterior dimensions" and not re.search(r"\d\s*(?:\"|″|”|in)?\s*[xX×]\s*\d", h):
            return False
        return rank == 0 or (rank == 1 and s[0] != "linked document")

    if field == "electrical":
        for method in ("static", "headless"):
            for rank, s, h in hits(method):
                if s[0] == "linked document":
                    continue   # a multi-model comparison sheet lists OTHER models' heaters
                if len({round(float(x), 1) for x in re.findall(r"(?i)(\d+(?:\.\d+)?)\s*-?\s*kw\b", h)}) >= 2:
                    return {"class": "OPTION_DEPENDENT", "source_url": s[1], "where": s[0], "method": method,
                            "snippet": h, "why": ["the text names two or more heater ratings: the buyer chooses"]}
    for method, cls in (("static", "STATED_MISSED"), ("headless", "JS_ONLY")):
        good = [h for h in hits(method) if confirmed(h[0], h[1], h[2])]
        if good:
            rank, (label, url, m_, _, _), snippet = good[0]
            return {"class": cls, "source_url": url, "where": label, "method": m_, "snippet": snippet,
                    "candidates": len(good), "strength": ["labelled", "plain"][rank]}
    weak = hits("static") + hits("headless")
    if weak:
        rank, (label, url, m_, _, _), snippet = weak[0]
        return {"class": "NOT_VERIFIED", "source_url": url, "where": label, "method": m_, "snippet": snippet,
                "strength": "weak", "why": ["unconfirmed candidate: it names a related thing but does not state this "
                                            "field for this model; a human decides"]}
    mention = FIELD_MENTION[field]
    named = next((s for s in srcs if s[3] == 200 and mention.search(s[4])), None)
    failed = [f"{s[0]} {s[1]} ({s[2]}): {s[3]}" for s in srcs if s[3] != 200]
    if named and not failed:
        m = mention.search(named[4])
        return {"class": "NOT_VERIFIED", "source_url": named[1], "where": named[0], "method": named[2],
                "snippet": re.sub(r"\s+", " ", named[4][max(0, m.start() - 60): m.end() + 100]).strip(),
                "why": ["the source has a section or wording for this field but no figure in its text; "
                        "the content may be an image or a document we cannot read, so it is not called not stated"]}
    if failed or not srcs:
        return {"class": "NOT_VERIFIED", "why": failed or ["nothing fetched for this record"]}
    return {"class": "NOT_STATED"}


def heat_option(p):
    """A heat-type option: its NAME is a sauna/heat type, or its VALUES name heat types.
    Round 1's `\btype\b` also caught 'Lumber Type (Rustic Red Cedar, Onyx)'."""
    for o in p.options:
        vals = o.get("values", [])
        if len(vals) > 1 and (HEAT_OPTION_NAME.search(o.get("name", "")) or
                              sum(1 for v in vals if HEAT_OPTION_VALUE.search(v)) >= 1 and
                              len({m.group(0).lower() for v in vals for m in HEAT_OPTION_VALUE.finditer(v)}) >= 2):
            return f"the buyer chooses '{o['name']}' ({', '.join(vals[:4])})"
    return None


def classify(brands):
    import verified_build as vb
    import verified_pages as vp
    cache = vb.Cache()
    leads = json.loads(vb.LEADS.read_text())["products"]
    out = {"_comment": "Round 3 Part A gap diagnosis. Basis for a LATER round's 'Not stated on the manufacturer's "
                       "page' wording; that wording is not rendered yet. Classes are defined in scripts/verified_gaps.py.",
           "records": {}}
    prod_cache = {}
    for r, t, brand, src in targets(brands):
        if brand not in prod_cache:
            prod_cache[brand] = vb.products_for(cache, brand, src, [l for l in leads if l["brand"] == brand])
        products = prod_cache[brand]
        by_url = {p.url.rstrip("/"): p for p in products.values()}
        pu = page_urls(r)
        p = next((by_url[u.rstrip("/")] for u in pu if u.rstrip("/") in by_url), None)
        r = dict(r, _product_handle=p.handle if p else None)
        srcs = sources_for(r, cache, brand, src, products)
        rec = {"brand": brand, "missing": t["missing"], "fields": {},
               "checked": [{"what": s[0], "url": s[1], "method": s[2], "status": s[3]} for s in srcs]}
        for field in t["missing"]:
            if field not in FIELDS:
                continue
            note = heat_option(p) if (p and field == "heat type") else (vb.option_dependent(p, GROUP[field]) if p else None)
            cap_note = r["capacity_min"].get("note") or ""
            if not note and field in ("capacity", "exterior dimensions") and cap_note.startswith("withheld: "):
                note = cap_note[len("withheld: "):]      # Round 1 recorded the size choice with its text
            c = classify_field(field, note, srcs, pu[0] if pu else None)
            if c["class"] in ("OPTION_DEPENDENT", "STATED_MISSED", "JS_ONLY"):
                data, e = cache.get(c["source_url"] if c["method"] == "static" else "headless:" + c["source_url"])
                if e:
                    c.update(fetched_at=e["fetched_at"], content_sha256=e.get("sha256"))
            rec["fields"][field] = c
        out["records"][r["inh_id"]] = rec
    out["records"] = dict(sorted(out["records"].items()))
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return out


def report(d):
    per = defaultdict(Counter)
    for iid, rec in d["records"].items():
        for f, c in rec["fields"].items():
            per[(rec["brand"], f)][c["class"]] += 1
    return per


def write_samples(d, path):
    """The reviewer's appendix: counts, then up to 5 quoted snippets per brand per class."""
    per, samples, causes, proj, base = summary(d)
    L = ["# Round 3 Part A: gap diagnosis samples", "",
         "Generated by `scripts/verified_gaps.py --samples` from `data/verified/gap-diagnosis.json`.", "",
         "## Counts per brand and field", "", "| Brand | Field | " + " | ".join(
             ["STATED_MISSED", "JS_ONLY", "OPTION_DEPENDENT", "NOT_STATED", "NOT_VERIFIED"]) + " |",
         "|---|---|---|---|---|---|---|"]
    for (b, f), c in sorted(per.items()):
        L.append(f"| {b} | {f} | " + " | ".join(str(c.get(k, 0)) for k in
                                                ["STATED_MISSED", "JS_ONLY", "OPTION_DEPENDENT", "NOT_STATED", "NOT_VERIFIED"]) + " |")
    L += ["", "## Why the extractor missed each STATED_MISSED value (the fix it needs)", ""]
    for (b, f), c in sorted(causes.items()):
        L.append(f"- **{b}, {f}:** " + "; ".join(f"{k} ({v})" for k, v in c.most_common()))
    L += ["", "## Samples (up to 5 per brand per class)", ""]
    for (b, cl), xs in sorted(samples.items()):
        L.append(f"### {b}: {cl}")
        for x in xs:
            q = x["snippet"].replace("|", "¦").replace("⟦", "[link: ").replace("⟧", "]")
            L.append(f"- `{x['inh_id'].rsplit('/', 1)[1]}` {x['field']} ({x['method']}): “{q}” — {x['url']}")
        L.append("")
    Path(path).write_text("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=None, help="write the reviewer's samples appendix to this path")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--brands", nargs="*", default=TARGETS + ALSO)
    a = ap.parse_args(argv)
    if a.fetch:
        fetch_all(a.brands)
        return 0
    if a.samples:
        write_samples(json.loads(OUT.read_text()), a.samples)
        return 0
    d = classify(a.brands)
    for k, v in sorted(report(d).items()):
        print(k, dict(v))
    return 0




# ------------------------------------------------------------------ report --

# Why a STATED_MISSED snippet was missed: the fix it needs. Checked in order; first match wins.
CAUSES = [
    ("non-rectangular: diameter or wall lengths (needs a decision)", "exterior dimensions", re.compile(r"(?i)diameter|back\s+walls?|side\s+walls?")),
    ("two-model spec table (column must be assigned to the model)", "exterior dimensions", re.compile(r"(?i)SPEC(?:IFICATION)?S?\s+(?:[A-Z]+\s+\d(?:-PERSON)?\s+){2,}")),
    ("Unicode fractions (⅞, ⁵⁄₁₆)", "exterior dimensions", re.compile(r"[¼½¾⅛⅜⅝⅞]|⁄")),
    ("fractional inches (e.g. 51 3/4″)", "exterior dimensions", re.compile(r"\d+[\s-]+\d/\d+\s*(?:\"|″|”|in)")),
    ("'Assembled size' label", "exterior dimensions", re.compile(r"(?i)assembled\s+(?:size|exterior)")),
    ("per-axis 'Width: … Depth: … Height:' labels", "exterior dimensions", re.compile(r"(?i)width\s*:?\s*\d[^\n]{0,60}depth\s*:?\s*\d")),
    ("L × W × H order, or letter after the inch mark", "exterior dimensions", re.compile(r"(?i)\d\s*(?:\"|″|”|in)\s*[LWDH]\b")),
    ("labelled Width/Depth/Height list", "exterior dimensions", re.compile(r"(?i)width\s*:?\s*\d[^\n]{0,40}depth\s*:?\s*\d")),
    ("unlabelled or differently labelled W x D x H", "exterior dimensions", re.compile(r"(?i)\d\s*(?:\"|″|”|in)?\s*[xX×]\s*\d")),
    ("'fits / seats / accommodates N'", "capacity", re.compile(r"(?i)\b(fits|seats?|seating|accommodates?|room for|up to)\b")),
    ("'N-person' outside the title", "capacity", re.compile(r"(?i)\d\s*(?:-|–|to)?\s*\d*[\s-]*(person|people)")),
    ("generic copy: 'löyly … defines a traditional sauna'", "heat type", re.compile(r"(?i)l[öo]yly|defines\s+a\s+traditional")),
    ("'traditional sauna' in the product description", "heat type", re.compile(r"(?i)traditional\s+sauna")),
    ("heater/stove named in text", "heat type", re.compile(r"(?i)stove|heater|harvia|huum|homecraft|saunum|wood")),
    ("infrared named in text", "heat type", re.compile(r"(?i)infrared|spectrum")),
    ("voltage / amperage / kW stated", "electrical", re.compile(r"(?i)\d\s*(?:v|vac|volts?|a|amps?|kw)\b")),
    ("connection wording (hardwired, plug, breaker, circuit)", "electrical", re.compile(r"(?i)hard[- ]?wired|plug|breaker|circuit|nema")),
]


def cause_of(field, snippet):
    for name, f, rx in CAUSES:
        if f == field and rx.search(snippet):
            return name
    return "other (read the snippet)"


def summary(d, n=5):
    import verified_pages as vp
    per_brand_field = defaultdict(Counter)
    samples = defaultdict(list)
    causes = defaultdict(Counter)
    projected = Counter()
    base = Counter()
    for iid, rec in d["records"].items():
        fixable = all(c["class"] in ("STATED_MISSED", "JS_ONLY", "OPTION_DEPENDENT")
                      and (c["class"] != "OPTION_DEPENDENT" or f == "electrical")   # the amendment covers electrical only
                      for f, c in rec["fields"].items()) and set(rec["fields"]) == set(m for m in rec["missing"] if m in FIELDS)
        base[rec["brand"]] += 1
        if fixable:
            projected[rec["brand"]] += 1
        for f, c in rec["fields"].items():
            per_brand_field[(rec["brand"], f)][c["class"]] += 1
            key = (rec["brand"], c["class"])
            if len(samples[key]) < n and c.get("snippet"):
                samples[key].append({"inh_id": iid, "field": f, "snippet": c["snippet"][:240], "url": c.get("source_url"),
                                     "method": c.get("method")})
            if c["class"] == "STATED_MISSED":
                causes[(rec["brand"], f)][cause_of(f, c["snippet"])] += 1
    return per_brand_field, samples, causes, projected, base


if __name__ == "__main__":
    sys.exit(main())
