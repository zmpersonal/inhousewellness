#!/usr/bin/env python3
"""INH Verified — build the verified dataset from the lead list and the origin cache.

    .venv/bin/python scripts/verified_build.py --brands "Golden Designs Inc" "Salus Saunas" ...

OFFLINE. Reads only data/verified/cache-manifest.json and out/verified/cache/.
Same cache in, byte-identical files out.

THE RULE (CLAUDE.md, editorial independence; D11): a lead value is never
published. A value is published only when an origin source states it:
  documented  manufacturer manual / spec sheet the manufacturer links
  listed      manufacturer product page (source_type manufacturer)
  listed      approved distributor page (none approved)
Retailer pages, including inhousewellness.com, are never evidence.

Per field, the SOURCE decides, and it must decide unambiguously:
  - the source states exactly one value      -> that value is published
      equal to the lead                        confirmed
      different from the lead                  changed  (lead mismatch logged)
      and there was no lead                    source_only
  - the source states two or more values     -> nothing published, ambiguity logged
  - the source states nothing                -> not_verified (lead -> not_found)
Never inferred, computed, or carried over from the lead.

ADAPTERS (sources.json "adapter")
  shopify_json   the manufacturer's Shopify product data (title, SKUs, body_html)
  shopify_html   Shopify product data + the rendered product page (html_mode
                 "disclosure": labelled accordion panels; "range": the text
                 between html_start_rx and html_stop_rx)
  html_page      a non-Shopify product page (range mode); title from <h1>
DISCOVERY (sources.json "discovery")
  catalogue      /products.json; leads matched by the SKU the manufacturer states
  lead_urls      /products/<handle>.json for each lead URL on the manufacturer's domain
  sitemap        product URLs from the manufacturer's sitemap; leads matched by name
                 (only where "name_match" is set), logged as a name match

Outputs
  data/verified/saunas.json                  records with status published|backlog
  data/verified/conflicts.json               lead mismatches, tier disagreements,
                                             within-source ambiguities
  data/verified/internal/verification-log.json   per-lead, per-field audit (internal)
  data/verified/internal/backlog.json            leads with no origin page (internal)
  out/verified/report-<label>.json               counts and samples for the report
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

VERSION = "0.3.0-b2"
CACHE = ROOT / "out/verified/cache"
MANIFEST = ROOT / "data/verified/cache-manifest.json"
SOURCES = ROOT / "data/verified/sources.json"
LEADS = ROOT / "data/verified/internal/leads/infinite-sauna-2026-09-21.json"
OUT = ROOT / "data/verified"
TITLE_OVERRIDES = OUT / "title-overrides.json"

RECOMMENDATION_RX = re.compile(r"(?i)\brecommend(?:ed|s)?\b|\bsuggest(?:ed)?\b|\boptional\b|\bupgrade\b")
OPTION_WORD_RX = re.compile(r"(?i)\bupgrades?\b|\boptional\b|\badd[- ]on\b|\bavailable\b|\badd during\b|\bstarting in \d{4}\b|\bchoose\b|\bchoice\b|\bselect\b|\belect to\b|\bfor those who\b|\bif you (?:prefer|choose|want)\b")
NEGATION_RX = re.compile(r"(?i)\b(?:no|not|never|without|don'?t|do not)\b[^.]{0,25}$")


# ------------------------------------------------------------------ cache --

class Cache:
    def __init__(self, manifest_override=None):
        if manifest_override is not None:
            raw = json.dumps(manifest_override, indent=2, sort_keys=True).encode()
            self.entries = manifest_override["entries"]
        else:
            raw = MANIFEST.read_bytes()
            self.entries = json.loads(raw)["entries"]
        self.sha = hashlib.sha256(raw).hexdigest()

    def get(self, url):
        e = self.entries.get(url)
        if not e or e.get("status") != 200:
            return None, e
        data = (CACHE / e["cache_file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != e["sha256"]:
            raise SystemExit(f"cache corrupt for {url}: sha256 does not match the manifest")
        return data, e


def html_to_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</(p|li|div|h[1-6]|tr|td|th|ul|ol|dt|dd|section|span)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")]
    return "\n".join(l for l in lines if l)


def snip(text, m, pad=60):
    s = text[max(0, m.start() - pad): m.end() + pad]
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------- products --

class Product:
    """One product on the manufacturer's own site."""
    def __init__(self, handle, url, title, skus, body_html, product_type, options, images,
                 fetched_url, entry, vendor=None, variants=()):
        self.handle, self.url, self.title, self.skus = handle, url, title, list(skus)
        self.body_html, self.product_type = body_html or "", product_type or ""
        self.options, self.images = options or [], images or []
        self.fetched_url, self.entry, self.vendor, self.variants = fetched_url, entry, vendor, list(variants)


def catalogue_url(domain, page):
    return f"https://{domain}/products.json?limit=250&page={page}"


def _shop_product(domain, p, fetched_url, entry):
    return Product(p["handle"], f"https://{domain}/products/{p['handle']}", html.unescape(p["title"]).strip(),  # missing-ok: absent optional Shopify fields yield no statement, so they can never publish a value
                   [v.get("sku") for v in p.get("variants", []) if v.get("sku")],
                   p.get("body_html"), p.get("product_type"), p.get("options"),  # missing-ok: an absent optional field yields no statement, so it can never publish a value
                   [i.get("src") for i in p.get("images", []) if i.get("src")],
                   fetched_url, entry, p.get("vendor"), p.get("variants", []))  # missing-ok: an absent vendor only shortens the evidence snippet


def lead_product_urls(src, leads):
    urls = set()
    for r in leads:
        for u in r["source_urls"]:
            parts = urllib.parse.urlsplit(u)
            if parts.netloc in src["manufacturer_domains"] and "/products/" in parts.path:
                h = parts.path.rstrip("/").split("/")[-1]
                urls.add(f"https://{parts.netloc}/products/{h}.json")
    return sorted(urls)


def discovery_urls(src, leads, read):
    """URLs the fetcher must request before products can be listed (besides catalogue pages)."""
    if src["discovery"] == "lead_urls":
        return lead_product_urls(src, leads)
    if src["discovery"] == "sitemap":
        return [src["sitemap_url"]]
    return []


def sitemap_product_urls(cache, src):
    data, _ = cache.get(src["sitemap_url"])
    if data is None:
        return []
    locs = re.findall(r"<loc>\s*(?:<!\[CDATA\[)?([^<\]]+)", data.decode("utf-8", "replace"))
    pref = src["product_path_prefix"]
    inc, exc = src.get("product_url_include_rx"), src.get("product_url_exclude_rx")
    out = set()
    for u in (x.strip() for x in locs):
        path = urllib.parse.urlsplit(u).path
        if not path.startswith(pref) or path.rstrip("/") in ("", pref.rstrip("/")):
            continue
        if re.search(r"\.(jpe?g|png|webp|gif|xml)$", u, re.I):
            continue
        if inc and not re.search(inc, path):
            continue
        if exc and re.search(exc, path):
            continue
        out.add(u)
    return sorted(out)


def page_title(hh):
    """The product's name as the page states it: its <h1>, else og:title, else <title>,
    with a trailing ' - SiteName' / ' | SiteName' removed (SaunaLife has no <h1>)."""
    for rx in (r"<h1[^>]*>(.*?)</h1>", r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', r"<title[^>]*>(.*?)</title>"):
        m = re.search(rx, hh, re.S | re.I)
        if m:
            t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()
            if rx.startswith("<h1"):
                return t
            return re.split(r"\s+[-|–]\s+(?=[^-|–]+$)", t)[0].strip()
    return ""


def products_for(cache, brand, src, leads):
    """{handle: Product} for everything the manufacturer's own site lists."""
    domain = src["manufacturer_domains"][0]
    out = {}
    if src["discovery"] == "catalogue":
        page = 1
        while True:
            url = catalogue_url(domain, page)
            data, e = cache.get(url)
            if data is None:
                break
            batch = json.loads(data)["products"]
            for p in batch:
                if src.get("product_handle_exclude_rx") and re.search(src["product_handle_exclude_rx"], p["handle"]):
                    continue   # the manufacturer's own test / draft listings
                out[p["handle"]] = _shop_product(domain, p, url, e)
            if len(batch) < 250:
                break
            page += 1
    elif src["discovery"] == "lead_urls":
        for url in lead_product_urls(src, leads):
            data, e = cache.get(url)
            if data is not None:
                p = json.loads(data)["product"]
                out[p["handle"]] = _shop_product(urllib.parse.urlsplit(url).netloc, p, url, e)
    elif src["discovery"] == "sitemap":
        for url in sitemap_product_urls(cache, src):
            h = urllib.parse.urlsplit(url).path.rstrip("/").split("/")[-1]
            data, e = cache.get(url)
            title, skus = "", []
            if data is not None:
                hh = data.decode("utf-8", "replace")
                title = page_title(hh)
                if src.get("sku_rx"):
                    rng = html_range(hh, src) or ""
                    # Only SKUs printed in the product's own visible content, whole lines.
                    skus = sorted({l.strip() for l in rng.split("\n") if re.fullmatch(src["sku_rx"], l.strip())})
            out[h] = Product(h, url, title, skus, "", "", [], [], url, e)
    # The brand's own Shopify file store, derived from its own product images.
    prefixes = Counter()
    for p in out.values():
        for img in p.images:
            m = re.search(r"cdn\.shopify\.com(/s/files/1/\d+/\d+/\d+/)", img)
            if m:
                prefixes[m.group(1)] += 1
    if prefixes and not src.get("pdf_path_prefix"):
        src["_shop_prefix"] = prefixes.most_common(1)[0][0]
    return out


NUM_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight"}


def name_tokens(s):
    s = unicodedata_fold(s).lower()
    toks = set(re.findall(r"[a-z]+|\d+", s))
    return toks | {NUM_WORDS[t] for t in toks if t in NUM_WORDS}


def unicodedata_fold(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def match_leads(src, leads, products):
    """({handle: [(lead, how)]}, [unmatched leads]). SKU first, then the lead's own
    manufacturer-domain URL, then (only where configured) a unique name match."""
    by_sku = {}
    for h in sorted(products):
        for s in products[h].skus:
            by_sku.setdefault(norm_model(s), h)
    matched, none = defaultdict(list), []
    for r in sorted(leads, key=lambda r: r["model_key"]):
        h, how = by_sku.get(norm_model(r["model"])), "manufacturer sku"
        if not h:
            for u in r["source_urls"]:
                parts = urllib.parse.urlsplit(u)
                if parts.netloc in src["manufacturer_domains"]:
                    cand = parts.path.rstrip("/").split("/")[-1]
                    if cand in products:
                        h, how = cand, "lead URL on the manufacturer's domain"
                        break
        if not h and src.get("slug_model_match"):
            core = norm_model(re.sub(src["slug_model_match"], "", r["model"], flags=re.I))
            hits = sorted(hh for hh in products if len(core) >= 3 and core in norm_model(hh))
            if len(hits) == 1:
                h, how = hits[0], "model number in the manufacturer's page address"
        if not h and src.get("name_match"):
            lt = name_tokens(r["title"])
            scored = sorted(((len(set(hh.split("-"))), hh) for hh in products
                             if set(hh.split("-")) <= lt), reverse=True)
            if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]):
                h, how = scored[0][1], "name (every word of the manufacturer's page slug is in the lead title)"
        if h:
            matched[h].append((r, how))
        else:
            none.append(r)
    return matched, none


def option_uniform_kw(p):
    """The heater rating when EVERY buyer choice on the page names the same kW
    ("8kW KIP Heater w/ Dials", "8kW KIP Smart Heater + Fenix"). None otherwise:
    a choice without a kW, two different ratings, or a wood-burning option."""
    for o in p.options:
        if re.search(r"(?i)heater|stove|package", o.get("name", "")) and len(o.get("values", [])) > 1:
            kws = []
            for v in o["values"]:
                found = {float(x) for x in re.findall(r"(?i)(\d{1,2}(?:\.\d)?)\s*kw\b", v)}
                if len(found) != 1 or re.search(r"(?i)wood", v):
                    return None
                kws.append(found.pop())
            return kws[0] if len(set(kws)) == 1 else None
    return None


OPTION_GROUPS = {
    "electrical": r"(?i)heater|stove|power|voltage|package|electrical",
    "wood": r"(?i)lumber|wood|material|finish|interior",
    "size": r"(?i)\bsize\b|capacity|person",
    "type": r"(?i)sauna\s+type|heat(?:ing)?\s+type",
}
# Round 3 (D-5): Round 1's `\btype\b` also caught "Lumber Type (Rustic Red Cedar, Onyx)" and
# withheld heat types over a wood choice. An option decides heat type only when its NAME is a
# sauna/heat type, or its VALUES name two or more heat types ("Traditional & Cedar", "Infrared (Hybrid) & Cedar").
HEAT_WORD_RX = re.compile(r"(?i)\b(?:infrared|traditional|hybrid|steam)\b")


def option_dependent(p, group="electrical"):
    """A product whose buyer chooses something on the manufacturer's page that decides
    this field group (Almost Heaven: 'Heater', 'Lumber Type', 'Size', 'Sauna Type + Lumber Type')."""
    for o in p.options:
        vals = o.get("values", [])
        if len(vals) <= 1:
            continue
        hit = re.search(OPTION_GROUPS[group], o.get("name", ""))
        if group == "type" and not hit:
            hit = len({m.group(0).lower() for v in vals for m in HEAT_WORD_RX.finditer(v)}) >= 2
        if hit:
            return f"the buyer chooses '{o['name']}' ({', '.join(vals[:4])})"
    return None


# ------------------------------------------------------------------ docs --

class Doc:
    """One fetched origin document. segments = [(locator, text)]."""
    def __init__(self, source_url, fetched_url, entry, tier, source_type, segments, title="", skus=(), kind="data"):
        self.source_url = source_url
        self.fetched_url = fetched_url
        self.sha = entry["sha256"]
        self.fetched_at = entry["fetched_at"]
        self.tier = tier                  # "documented" | "listed"
        self.source_type = source_type    # manufacturer | manufacturer_manual
        self.segments = segments
        self.title = title
        self.skus = list(skus)
        self.kind = kind                  # data | html | pdf | meta
        self.option_note = None
        self.method = "static"            # static | headless (Round 3: recorded on every value's evidence)


SPEC_PANEL_RX = re.compile(r"(?i)specification|feature|overview|detail|description|what'?s included")


def salus_panels(h: str):
    """[(panel title, text)] from the product accordion. Panels are split on their titles."""
    heads = list(re.finditer(r'<h2 class="disclosure__title[^"]*"[^>]*>(.*?)</h2>', h, re.S))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else min(len(h), m.end() + 20000)
        out.append((html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip(), html_to_text(h[m.end():end])))
    return out


def html_range(h, src):
    """The product's own content: lines between start and stop markers, minus excluded ranges."""
    lines = html_to_text(h).split("\n")
    start = next((i for i, l in enumerate(lines) if re.search(src["html_start_rx"], l)), None)
    if start is None:
        return None
    stop = next((i for i in range(start + 1, len(lines)) if re.search(src["html_stop_rx"], lines[i])), None)
    if stop is None:
        return None
    keep = lines[start + 1:stop]
    for a, b in src.get("html_exclude", []):
        out, skipping = [], False
        for l in keep:
            if not skipping and re.search(a, l):
                skipping = True
                continue
            if skipping and re.search(b, l):
                skipping = False
            if not skipping:
                out.append(l)
        keep = out
    return "\n".join(keep)


def spec_blocks(h, blocks):
    """Round 3: extra line ranges of the product page (e.g. Almost Heaven's 'Features … Specifications'
    list), read as their own document so the existing ranges, and every value they give, are untouched."""
    lines = html_to_text(h).split("\n")
    out = []
    for a, b in blocks:
        i = next((k for k, l in enumerate(lines) if re.search(a, l)), None)
        if i is None:
            continue
        j = next((k for k in range(i + 1, len(lines)) if re.search(b, lines[k])), None)
        if j is not None:
            out.append("\n".join(lines[i:j]))
    return out


META_RX = re.compile(r'(?is)<meta[^>]+(?:name|property)="(?:description|og:description)"[^>]+content="([^"]*)"')


def page_extra_docs(cache, src, p, title):
    docs = []
    data, e = cache.get(p.url)
    if data is not None:
        h = data.decode("utf-8", "replace")
        blocks = spec_blocks(h, src.get("html_spec_blocks", []))
        if src.get("html_description_before_rx"):
            # The product description as one line right before a marker (Clearlight: the paragraph before
            # "Product Highlights"), which the configured range starts after.
            lines = html_to_text(h).split("\n")
            k = next((i for i, l in enumerate(lines) if re.search(src["html_description_before_rx"], l)), None)
            if k and len(lines[k - 1]) > 60:
                blocks.insert(0, lines[k - 1])
        if blocks:
            docs.append(Doc(p.url, p.url, e, "listed", "manufacturer",
                            [("product page specifications", b) for b in blocks], title, p.skus, "html"))
        metas = list(dict.fromkeys(html.unescape(m.group(1)).strip() for m in META_RX.finditer(h) if m.group(1).strip()))
        if metas:   # D-2: capacity only, and only when the page itself states none (see run())
            docs.append(Doc(p.url, p.url, e, "listed", "manufacturer", [("page metadata (meta description)", "\n".join(metas))],
                            title, p.skus, "meta"))
    if src.get("headless_fallback"):
        data, e = cache.get("headless:" + p.url)
        if data is not None:
            h = data.decode("utf-8", "replace")
            segs = [("rendered product page specifications", b) for b in spec_blocks(h, src.get("headless_spec_blocks", []))]
            rng = html_range(h, src)
            if rng:
                segs.append(("rendered product page main content", rng))
            if segs:
                d = Doc(p.url, "headless:" + p.url, e, "listed", "manufacturer", segs, title, p.skus, "html")
                d.method = "headless"
                docs.append(d)
    return docs


def product_docs(cache, src, p):
    t = p.title
    base = f"product '{p.handle}'"
    docs = []
    if p.entry is not None and src["discovery"] != "sitemap":
        segs = [(f"{base} title", t)]
        if p.product_type:
            segs.append((f"{base} product_type", p.product_type))
        body = html_to_text(p.body_html)
        if body:
            segs.append((f"{base} body_html", body))
        docs.append(Doc(p.url, p.fetched_url, p.entry, "listed", "manufacturer", segs, t, p.skus, "data"))
    if src["adapter"] in ("shopify_html", "html_page"):
        data, e = cache.get(p.url)
        if data is not None:
            h = data.decode("utf-8", "replace")
            if src.get("html_mode") == "disclosure":
                segs = [(f"product page panel '{pt}'", txt) for pt, txt in salus_panels(h) if SPEC_PANEL_RX.search(pt)]
            else:
                rng = html_range(h, src)
                segs = [("product page main content", rng)] if rng else []
            if src["adapter"] == "html_page":
                segs.insert(0, (f"{base} title", t))
            docs.append(Doc(p.url, p.url, e, "listed", "manufacturer", segs, t, p.skus, "html"))
    docs += page_extra_docs(cache, src, p, t)
    note, ukw = option_dependent(p), option_uniform_kw(p)
    notes = {g: option_dependent(p, g) for g in OPTION_GROUPS}
    titled = any(_ex_heat_type_title(d) for d in docs)
    hi = heater_items(p, docs)
    if hi and hi[4] >= 2 and not note:
        # Round 3: a heater CHOICE named in the page text ("... with upgrades available: 8kW ...", a
        # configurator's Electric / Wood / No heater) makes electrical values option-dependent, exactly
        # as a Shopify heater option does. kW publishes only when every choice names the same kW.
        note = hi[1]
        kws = {round(float(k), 2) for x in hi[0] for k in re.findall(r"(?i)(\d+(?:\.\d+)?)\s*kw", x)}
        ukw = kws.pop() if len(kws) == 1 and all(re.search(r"(?i)\d\s*kw", x) for x in hi[0]) else None
    for d in docs:
        d.title_states_type = titled
        d.option_note = note
        d.option_kw = ukw
        d.option_notes = notes
        d.heater = hi
    return docs


TRAD_HEATER_RX = re.compile(r"(?i)\b\d+(?:\.\d+)?\s*kw\b|\bwood\b|\bstove\b|\bkip\b|\bvirta\b|\bspirit\b|\bhomecraft\b|\bhuum\b|\bharvia\b|\bcilindro\b|\belectric\s+heater\b")
NOT_TRAD_RX = re.compile(r"(?i)infrared|\bIR\b|carbon|panel|red\s+light|3-phase|commercial|option available upon")
UPGRADE_RX = re.compile(r"(?i)([^.\n]{0,80}(?:\bheater\b|\d\s*kw\b)[^.\n]{0,40}?)\s*[,(]?\s*(?:with\s+upgrades?\s+(?:options\s+)?available|with\s+the\s+option\s+to\s+upgrade)\s*\)?\s*:\s*([^\n]{0,400})")
CONFIG_RX = re.compile(r"(?i)\bheater\s+options?\b\s*\*?([^\n]{0,240})")


def is_plain(d):
    """A plain document: neither page metadata (D-2) nor a headless render (D-4)."""
    return d.kind != "meta" and getattr(d, "method", "static") != "headless"


def cap_nests(a, b):
    """Two capacity statements nest when one range sits inside the other ((4,4) in (2,4))."""
    return isinstance(a, tuple) and isinstance(b, tuple) and (a[0] >= b[0] and a[1] <= b[1] or b[0] >= a[0] and b[1] <= a[1])


def resolve_fallbacks(field, per_doc):
    """per_doc = [(tier, doc, statements)]. Page metadata (D-2) and a headless render (D-4) count
    for a field ONLY when the plain page states nothing for it, so neither can displace it. D-2
    guard, both ways: metadata that does not nest with the page ("fits up to five people" against
    "built to fit up to 4 adults") is kept beside the page statement, which leaves capacity
    ambiguous rather than letting either win."""
    raw_doc = list(per_doc)
    if any(sts for _, d, sts in per_doc if is_plain(d)):
        per_doc = [(t, d, sts if is_plain(d) else []) for t, d, sts in per_doc]
    elif any(sts for _, d, sts in per_doc if getattr(d, "method", "static") != "headless"):
        per_doc = [(t, d, sts if getattr(d, "method", "static") != "headless" else []) for t, d, sts in per_doc]
    meta_sts = [v for _, d, sts in raw_doc if d.kind == "meta" for v, _, _ in sts]
    page_sts = [v for _, d, sts in per_doc if is_plain(d) for v, _, _ in sts]
    if field == "capacity" and meta_sts and page_sts and any(not all(cap_nests(m, p_) for p_ in page_sts) for m in meta_sts):
        per_doc = [(t, d, sts if d.kind != "meta" else []) for t, d, sts in per_doc]
        meta_doc, meta_raw = next((d, sts) for _, d, sts in raw_doc if d.kind == "meta" and sts)
        per_doc.append(("listed", meta_doc, [st for st in meta_raw if not all(cap_nests(st[0], p_) for p_ in page_sts)][:1]))
    return per_doc


def woods_all_nest(vals):
    """Round 3: nested names ("Cedar" in "Red Cedar" in "Canadian Red Cedar") are one wood only if
    EVERY pair nests; containment alone is order-dependent and would merge two different cedars
    through a generic "Cedar"."""
    return all(a in b or b in a for a in vals for b in vals)


def heater_items(p, docs):
    """The heater choices the product's OWN page names, with the text that names them.
    Sources, in order: the product's heater option (Shopify), an 'X heater, with upgrades available:
    A, B' sentence, a configurator 'Heater Option(s)' list. None when the page names no choice."""
    for o in p.options:
        if re.search(OPTION_GROUPS["electrical"], o.get("name", "")) and len(o.get("values", [])) > 1:
            vals = list(o["values"])
            return vals, f"the buyer chooses '{o['name']}' ({', '.join(vals)})", docs[0], f"product '{p.handle}' options", len(vals)
    for d in docs:
        if d.kind not in ("data", "html"):
            continue
        for loc, text in d.segments:
            t = re.sub(r"\s*\n\s*", " ", text)
            m = UPGRADE_RX.search(t)
            if m:
                lead = re.split(r"(?i)what[’']s\s+included\s*:\s*", m.group(0))[-1]
                chunks = [c.strip(" ,;") for c in re.split(r"(?i)(?=\b\d+(?:\.\d+)?\s*kw\b)", m.group(2))]
                items = [re.search(r"(?i)\d+(?:\.\d+)?\s*kw[^,]*", m.group(1)).group(0).strip()] if re.search(r"(?i)\d+(?:\.\d+)?\s*kw", m.group(1)) else []
                items += [c for c in chunks if c]
                if len(items) >= 2:
                    return items, re.sub(r"\s+", " ", lead).strip()[:300], d, loc, len(items)
            m = CONFIG_RX.search(t)
            if m:
                # A configurator: the CHOICES are the heater kinds offered (electric, wood, none); a kW
                # figure beside "Most common for your Sauna" is a recommendation, not a choice.
                choices = list(dict.fromkeys(x.lower() for x in re.findall(r"(?i)electric\s+heater|wood\s+heater|no\s+heater", m.group(1))))
                if len(choices) >= 2:
                    heaters = [c for c in choices if c != "no heater"]
                    return heaters, re.sub(r"\s+", " ", m.group(0)).strip()[:300], d, loc, len(choices)
    return None


def heater_items_heat(items):
    """D-3 (approved): traditional only if EVERY named heater is a traditional heater."""
    return "traditional" if items and all(TRAD_HEATER_RX.search(x) and not NOT_TRAD_RX.search(x) for x in items) else None


def option_group(fn, group):
    """Wood / size / type statements on a product where the buyer picks that thing."""
    def wrapped(doc):
        out = list(fn(doc))
        note = (getattr(doc, "option_notes", None) or {}).get(group)
        if note and out:
            out.append(("depends on the buyer's choice", out[0][1], note))
        return out
    return wrapped


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
NUMWORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
# Round 3: sentences that state seating as a maximum ("fits up to 4 adults", "Holds up to four people",
# "Up to 6 Persons", "Comfortably Seats 4 People"). Read on every segment, like a label. The locator
# is marked so the record can say the manufacturer stated a maximum.
CAP_PHRASE_RX = re.compile(r"(?i)\b(?:(?:fits?|accommodates?|holds?|seats?|seating\s+for|designed\s+for|built\s+to\s+fit|can\s+hold|room\s+for)\s+up\s+to|comfortably\s+seats|up\s+to)\s+"
                           r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:adults|people|persons)\b")
UP_TO_MARK = " (stated as a maximum: 'up to')"
CAP_LABEL_RX = re.compile(r"(?im)(?:^|\b(?:max(?:imum)?\s+))capacity\s*:?\s*(?:up to\s+)?(\d{1,2})(?:\s*(?:-|–|to)\s*(\d{1,2}))?(?=\s*(?:persons?|people|adults?|$))")


NOT_SEATING_AFTER_RX = re.compile(r"(?i)^[^.\n]{0,25}?(?:recommend|required|to install|to assemble|crew|lift|carry)")
NOT_SEATING_BEFORE_RX = re.compile(r"(?i)(?:recommend\w*|install\w*|crew|ideal for|best for|perfect for|great for)[^.\n]{0,20}$")


def _seating(text, m):
    """A people count is seating unless the words right beside it say otherwise:
    '2 Person Recommended' (install crew), 'Ideal for 1 Person' (advice).
    'Assembled Dimensions ... 2 person capacity' is seating."""
    return not (NOT_SEATING_AFTER_RX.search(text[m.end():m.end() + 30])
                or NOT_SEATING_BEFORE_RX.search(text[max(0, m.start() - 22):m.start()]))


def ex_capacity(doc):
    """On a rendered page, sibling-model selectors ('1 Person / 2 Person') sit beside
    the title, so only the title and labelled 'Capacity' lines count there."""
    out = []
    for loc, text in doc.segments:
        free = doc.kind != "html" or loc.endswith("title")
        masked = text
        for m in CAP_PHRASE_RX.finditer(text):
            g = m.group(1).lower()
            n = int(g) if g.isdigit() else NUMWORD[g]
            upto = "up to" in m.group(0).lower()
            out.append(((n, n), loc + (UP_TO_MARK if upto else ""), snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        text_for_labels = masked
        for m in CAP_LABEL_RX.finditer(text_for_labels):
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
            out.append(((a, b), loc, snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        if not free:
            continue
        for m in CAP_RANGE_RX.finditer(masked):
            if _seating(text, m):
                out.append(((int(m.group(1)), int(m.group(2))), loc, snip(text, m)))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
        for m in CAP_ONE_RX.finditer(masked):
            if _seating(text, m):
                n = int(m.group(1))
                out.append(((n, n), loc, snip(text, m)))
    return out


_ex_capacity = ex_capacity


DESC_LOC_RX = re.compile(r"body_html$|main content$|panel '(?:Description|Features|Features & Specifications|Overview|Details|Specifications)'$", re.I)
DESC_TRAD_RX = re.compile(r"(?i)\bstove\b|harvia|\bkip\b|homecraft|\bhuum\b|electric (?:sauna )?heater|wood[- ]burning|\bstone heater\b|traditional (?:stone )?heater")


def sentences(text):
    return [x for x in re.split(r"(?<=[.!?])\s+|\n", text) if x.strip()]


def ex_heat_type_description(doc):
    if getattr(doc, "method", "static") == "headless":
        return []   # Round 3: a rendered configurator line ("electric heater | 6 KW") is not a description
    """B2-D2: heat type from the product's OWN description, only when it names exactly
    one heating system. Cross-sell, option and negated sentences never count."""
    ir, trad = [], []
    for loc, text in doc.segments:
        if not DESC_LOC_RX.search(loc):
            continue
        in_list = False
        for sen in sentences(text):
            if in_list:
                # Short lines after "…upgrades available:" are the option list itself.
                if len(sen) <= 80 and not sen.rstrip().endswith(":"):
                    continue
                in_list = False
            if sen.rstrip().endswith(":") and OPTION_WORD_RX.search(sen):
                in_list = True
                continue
            if CROSS_SELL_RX.search(sen) or OPTION_WORD_RX.search(sen) or re.search(r"(?i)\bunlike\b|\bcompared\b|\bvs\.?\b|\bversus\b", sen):
                continue
            for rx, bucket in ((IR_TEXT, ir), (DESC_TRAD_RX, trad)):
                m = rx.search(sen)
                if m and not NEGATION_RX.search(sen[max(0, m.start() - 30):m.start()]):
                    bucket.append((loc, re.sub(r"\s+", " ", sen).strip()[:220]))
    out = [("infrared", loc, sn) for loc, sn in ir[:1]] + [("traditional", loc, sn) for loc, sn in trad[:1]]
    return out


def ex_heat_from_heaters(doc):
    """D-3: every heater the product's own page names is a traditional heater -> traditional,
    citing the option text. Emitted once, on the document that names the heaters."""
    hi = getattr(doc, "heater", None)
    if not hi or hi[2] is not doc:
        return []
    items, text, _, loc, _ = hi
    v = heater_items_heat(items)
    return [(v, f"{loc} (every named heater option is a traditional heater)", text)] if v else []


def ex_heat_type(doc):
    out = _ex_heat_type_title(doc)
    if out or getattr(doc, "title_states_type", False):
        return out   # a title elsewhere for this product decides; the description is only a fallback
    return ex_heat_type_description(doc)


def _ex_heat_type_title(doc):
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


MODEL_PAREN_RX = re.compile(r"\(([A-Z]{2,5}-[A-Z0-9]+(?:-[A-Z0-9]+)*(?:\s+(?:Elite|CED|HEM|FS|ZF))*)\)")
MODEL_LABEL_RX = re.compile(r"(?i)\bmodel(?:\s*(?:no\.?|number|#))?\s*[:#]\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\s+(?:Elite|CED|HEM|FS))?)")


def ex_model(doc):
    """Model strings the page states. When one extends another ("DYN-6103-01" as the
    SKU, "DYN-6103-01 Elite" in the title), the more specific one is the model: the
    suffix names a different configuration, and dropping it merged Avila with Avila Elite."""
    # A purely numeric SKU ("37", "5335") is a store item id, not a manufacturer part number.
    out = [(sku.strip(), "catalogue product variant sku", f"sku: {sku.strip()}") for sku in doc.skus
           if not re.fullmatch(r"\d+", sku.strip())]
    for loc, text in doc.segments:
        for m in MODEL_LABEL_RX.finditer(text):
            out.append((m.group(1).strip(), loc, snip(text, m)))
        if loc.endswith("title"):
            for m in MODEL_PAREN_RX.finditer(text):
                out.append((m.group(1).strip(), loc, snip(text, m)))
    specific = []
    for v, loc, sn in out:
        nv_ = norm_model(v)
        if any(norm_model(w) != nv_ and norm_model(w).startswith(nv_) for w, _, _ in out):
            continue   # a longer string on the same page extends this one
        specific.append((v, loc, sn))
    return specific


WOODS = ["Pacific Premium Clear Cedar", "Pacific Premium Cedar", "Eastern White Cedar", "Northern White Cedar",
         "Alaskan Yellow Cedar", "Yellow Cedar", "Spanish Cedar", "Western Hemlock", "Canadian Red Cedar", "Western Red Cedar", "Pacific Cedar",
         "Red Cedar", "White Cedar", "Canadian Hemlock", "Thermally Modified Nordic Pine", "Thermally Modified Pine", "Nordic Pine", "Thermo-Spruce",
         "Thermo Spruce", "Nordic White Spruce", "Nordic Spruce", "White Spruce", "Thermo-Aspen", "Thermo Aspen",
         "Thermo-Pine", "Hemlock", "Cedar", "Spruce", "Aspen", "Alder", "Basswood", "Pine", "ThermoWood",
         "Mahogany", "Eucalyptus", "Poplar", "Birch", "Teak", "Walnut", "Oak", "Abachi", "Meranti", "Obeche"]
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
    out = _scan(doc, rx, v)
    # "Ultra Low" contains "Low": a bare "low" match inside an "ultra low" phrase is the same statement.
    return [x for x in out if not (x[0] == "Low" and re.search(r"(?i)ultra[- ]low\s+emf", x[2]))]


CROSS_SELL_RX = re.compile(r"(?i)\bexplore\b|\bshop\b|\bbrowse\b|\bour red light saunas\b|\bcollection\b|\bsee all\b")


def ex_red_light(doc):
    """True only for this model's feature. 'Red light therapy Not included' is an
    explicit no; 'explore our red light saunas' is a cross-sell; 'Upgrade available'
    is an option."""
    out = []
    for loc, text in doc.segments:
        for m in re.finditer(r"(?i)\bred[- ]light\b", text):
            s = snip(text, m)
            if re.match(r"(?i)[\s\w]{0,20}?\bnot included\b|\s*(?:therapy\s*)?[:\-]?\s*(?:no|none)\b", text[m.end():m.end() + 30]):
                out.append((False, loc, s))
                continue
            if NEGATION_RX.search(text[max(0, m.start() - 30):m.start()]):
                continue
            a0 = max(text.rfind(c, 0, m.start()) for c in ".!?\n")
            b0 = min([i for i in (text.find(c, m.end()) for c in ".!?\n") if i >= 0] or [len(text)])
            if CROSS_SELL_RX.search(text[a0 + 1:b0]):
                continue   # the sentence is a cross-sell, not a feature of this model
            out.append((True, loc, s))
            if OPTION_WORD_RX.search(s):
                out.append(("offered as an option", loc, s))
    return out


VOLT_RX = re.compile(r"(?i)(?<![\d.])(208\s*[-–/]\s*240|220\s*/\s*240|120|208|220|230|240)\s*(?:v(?:ac)?\b|volts?\b)")
PLURAL_CIRCUITS_RX = re.compile(r"(?i)^[^.]{0,40}?\bcircuits\s+required")
MULTI_CIRCUIT_RX = re.compile(r"(?i)\b(?:dual|two|double)\b|\b2\s*x\b|\bx\s*2\b|\b(?:2|3|three)\s+(?:separate|dedicated|independent)\b")


def ex_voltage(doc):
    def v(m):
        s = re.sub(r"\s", "", m.group(1))
        return {"208-240": "208–240V", "208–240": "208–240V", "208/240": "208–240V"}.get(s, s + "V")
    out = []
    for loc, text in doc.segments:
        for m in VOLT_RX.finditer(text):
            if re.search(r"(?i)\b(?:not|no)\s*\(?\s*$", text[max(0, m.start() - 6):m.start()]):
                continue   # "(Not 220/240 V)"
            out.append((v(m), loc, snip(text, m)))
            if MULTI_CIRCUIT_RX.search(text[max(0, m.start() - 40): m.start()]) or PLURAL_CIRCUITS_RX.match(text[m.end():m.end() + 60]):
                out.append(("multiple circuits", loc, snip(text, m)))
    return out


# Decimals are captured: "18.83 Amps" (a draw) beside "20 Amp outlet" is two
# stated amperages, and dropping the decimal one would make the other look sole.
# "30-amp" (hyphenated) is read (B2-D5). The hyphen is allowed only before a spelled unit,
# never before a bare "A": "AR-3A" stays a drawing label.
AMP_RX = re.compile(r"(?<![A-Za-z\-\d.])(\d{1,2}(?:\.\d{1,2})?)\s*(A\b|AMPS?\b|[Aa]mps?\b|[Aa]mperes?\b|-[Aa]mps?\b|-AMPS?\b)")


ELECTRIC_CONTEXT_RX = re.compile(r"(?i)\d\s*v(?:ac)?\b|volt|circuit|breaker|outlet|receptacle|electric|\bamp")


def amp_ok(m, text=None):
    """A bare "A" is an amperage only beside electrical words: "AR-3A" is a drawing
    label and "Step 10.2A – Install Lower Bench" is a step number. A bare single
    digit with "A" is never taken."""
    if m.group(2) != "A":
        return True
    if "." not in m.group(1) and len(m.group(1)) == 1:
        return False
    if text is None:
        return True
    around = text[max(0, m.start() - 25): m.start()] + text[m.end(): m.end() + 25]
    return bool(ELECTRIC_CONTEXT_RX.search(around))


# Round 3: skipped are figures the text says are NOT enough ("A standard 15 A household outlet is not
# sufficient"), figures in a prohibition, and a household outlet's rating. A unit's DRAW is NOT skipped:
# Sun Home's sheets print "RATED ELECTRICAL 120V / 2,820W / 23.5A" and "Dedicated 120V / 30A circuit",
# and choosing the circuit over the draw would be the build picking one stated value (reverted after
# assertion replay; see RUNLOG Round 3 Part B).
# "A standard 15A household receptacle will not accept the NEMA 5-20P plug": the figure describes a
# common household outlet, not the product's requirement.
AMP_HOUSEHOLD_AFTER_RX = re.compile(r"(?i)^\s*(?:standard\s+)?household\s+(?:outlet|receptacle)")
AMP_PROHIBITED_BEFORE_RX = re.compile(r"(?i)\b(?:do\s+not|don't|never)\s+use\b[^.]{0,110}$")   # a PDF line break may sit inside
AMP_NEGATED_RX = re.compile(r"(?i)^[^.]{0,40}\b(?:is\s+not\s+(?:sufficient|enough)|won't\s+work|will\s+not\s+(?:work|be\s+enough|suffice)|is\s+not\s+suitable)")


def ex_amps(doc, breaker=False):
    out = []
    for loc, text in doc.segments:
        for m in AMP_RX.finditer(text):
            if not amp_ok(m, text):
                continue
            # Round 3: "is not sufficient", "do not use a 15 amp extension cord" and "a 15 amp household
            # outlet" are about something else. A DRAW is still a stated amperage (schema D2; the
            # Round 1 assertion "120 Volts 18.83 A draw" -> 18.83): a sheet stating a draw AND a
            # circuit is ambiguous and withheld, never resolved by choosing one.
            if AMP_NEGATED_RX.match(text[m.end(): m.end() + 60]) \
                    or AMP_PROHIBITED_BEFORE_RX.search(text[max(0, m.start() - 120): m.start()]) \
                    or AMP_HOUSEHOLD_AFTER_RX.match(text[m.end(): m.end() + 40]):
                continue
            around = text[max(0, m.start() - 30): m.end() + 30]
            if breaker and not re.search(r"(?i)\bbreaker\b", around):
                continue
            if MULTI_CIRCUIT_RX.search(text[max(0, m.start() - 40): m.start()]) or PLURAL_CIRCUITS_RX.match(text[m.end():m.end() + 60]):
                # "Dual x 120v/15 AMP", "20AMP Dedicated Circuits Required": one amperage would misstate it.
                out.append((float(m.group(1)), loc, snip(text, m)))
                out.append(("multiple circuits", loc, snip(text, m)))
                continue
            out.append((float(m.group(1)), loc, snip(text, m)))
    return out


def ex_plug(doc):
    # A plug is named with its P suffix. "NEMA 5-20" or "NEMA L5-30" without it names
    # a receptacle or nothing specific, and is not published as the unit's plug.
    out = _scan(doc, re.compile(r"(?i)\bNEMA\s*(L?\d{1,2})\s*-\s*(\d{2})\s*P\b"),
                lambda m: f"NEMA {m.group(1).upper()}-{m.group(2)}P", guard_negation=True)
    out += _scan(doc, re.compile(r"(?i)\bhard[- ]?wired?\b"), lambda m: "Hardwired", guard_negation=True)
    return out


GFCI_CONDITIONAL_RX = re.compile(r"(?i)\b(?:where|if|when)\b[^.\n]{0,40}\b(?:code|local|jurisdiction|inspector)\b[^.\n]{0,20}$")


def ex_gfci(doc):
    # Round 3: "where your local electrical code requires GFCI protection ..., ask your electrician"
    # is conditional on local code, not the product's requirement.
    out = _scan(doc, re.compile(r"(?i)\bGFCI\b[^.\n]{0,30}\brequired\b|\brequires?\s+(?:a\s+)?GFCI\b"),
                lambda m: "Required", guard_negation=True)
    keep = []
    for v, loc, sn in out:
        text = dict(doc.segments).get(loc, "")
        i = text.find(sn[:40])
        if i >= 0 and GFCI_CONDITIONAL_RX.search(text[max(0, i - 10): i + len(sn) // 2]):
            continue
        keep.append((v, loc, sn))
    return keep


def ex_circuit(doc):
    """'Dedicated required' only when the sentence REQUIRES it. 'Dedicated Circuit
    Recommended', 'turn OFF the dedicated circuit breaker' and '15AMP Dedicated
    Circuit or 20AMP Dedicated Circuit' are not requirements."""
    out = []
    for v, loc, s in _scan(doc, re.compile(r"(?i)\bdedicated\b[^.\n]{0,30}\bcircuit\b"),
                           lambda m: "Dedicated required", guard_negation=True):
        if re.search(r"(?i)recommend", s):
            continue
        if not re.search(r"(?i)\brequire[ds]?\b|\bmust\b|\brequirement", s):
            continue
        out.append((v, loc, s))
    return out


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


# Round 3 (D-5): whole inches with an optional fraction in every form the manufacturers print:
# "51 3/4", "86-5/8", "75 ⅜", "80⁵⁄₁₆". Round 1 read none of the last three.
VULGAR = {"¼": 0.25, "½": 0.5, "¾": 0.75, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875, "⅓": 1 / 3, "⅔": 2 / 3}
SUPSUB = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉", "01234567890123456789")
NUM = r"\d+(?:\.\d+)?(?:(?:\s+|-)\d+/\d+|\s?[¼½¾⅛⅜⅝⅞⅓⅔]|\s?[⁰¹²³⁴⁵⁶⁷⁸⁹]+⁄[₀₁₂₃₄₅₆₇₈₉]+)?"
INCH_MARK = r"(?:″|”|\"|in\.?(?![a-z])|inches)"
INCH = r"(" + NUM + r")\s*" + INCH_MARK


def to_inches(s: str) -> float:
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(?:(?:\s+|-)(\d+)/(\d+)|\s?([¼½¾⅛⅜⅝⅞⅓⅔])|\s?([⁰¹²³⁴⁵⁶⁷⁸⁹]+)⁄([₀₁₂₃₄₅₆₇₈₉]+))?", s)
    if not m:
        raise ValueError(s)
    v = float(m.group(1))
    if m.group(2):
        v += float(m.group(2)) / float(m.group(3))
    elif m.group(4):
        v += VULGAR[m.group(4)]
    elif m.group(5):
        v += float(m.group(5).translate(SUPSUB)) / float(m.group(6).translate(SUPSUB))
    return round(v, 4)


def _inch(m, i):
    return to_inches(m.group(i))


def _dims(doc, label):
    rx = re.compile(r"(?i)\b" + label + r"\s+dimensions?\s*(\(WDH\))?\s*:\s*"
                    r"(" + NUM + r")\s*" + INCH_MARK + r"?\s*(W)?\s*x\s*(" + NUM + r")\s*" + INCH_MARK + r"?\s*(D)?\s*x\s*"
                    r"(" + NUM + r")\s*" + INCH_MARK + r"?\s*(H)?")
    axes = re.compile(r"(?is)\b" + label + r"\s+dimensions?\s*:?\s*Width:\s*" + INCH + r"\s*Depth:\s*" + INCH + r"\s*Height:\s*" + INCH)
    out = []
    for loc, text in doc.segments:
        for m in rx.finditer(text):
            # The order is only known when the source labels it (WDH, or W/D/H letters).
            if not (m.group(1) or (m.group(3) and m.group(5) and m.group(7))):
                continue
            out.append(((to_inches(m.group(2)), to_inches(m.group(4)), to_inches(m.group(6))), loc, snip(text, m)))
        for m in axes.finditer(text):
            out.append(((_inch(m, 1), _inch(m, 2), _inch(m, 3)), loc, snip(text, m, pad=10)))
    return out


# ------------------------------------------------ exterior, in the maker's own shape (Round 3, D-1)
# A size counts only when the COMPLETE set for the product's shape is stated, and it is kept exactly
# as stated, never converted: rectangular = width, depth (or length) and height; barrel = length and
# diameter; round/dome = diameter and height; corner = every wall length the source lists and the height.
EXT_LABEL = r"(?:exterior|outside|overall|external|outer|assembled|footprint)"
# Between the label and the figures: no part word and no other number. "Exterior BENCH Dimensions: 16″W …"
# and "Assembled Weight 600 lb CRATE Dimensions 55.1 in W …" are not the sauna's exterior.
EXT_GAP = (r"(?:(?!\b(?:bench|porch|canopy|cradle|door|window|interior|inside|crate|crated|shipping|packag|box|heater|stove"
           r"|weight|light|mat|glass|room)\w*)[^\n.;\d])")
AXIS_NAME = {"w": "Width", "d": "Depth", "l": "Length", "h": "Height", "width": "Width", "depth": "Depth",
             "length": "Length", "height": "Height"}
_M = r"\s*" + INCH_MARK + r"?\s*"
# Round 3: SaunaLife prints each axis with its metric twin, '95.3"W (242.1 cm) x 86.6"D (220 cm) x …'.
# The parenthetical is the same figure in another unit and is skipped; the inch figure is what renders.
_CM = r"(?:\s*\(\s*\d+(?:\.\d+)?\s*cm\s*\))?"
EXT_LETTERS_RX = re.compile(r"(?i)\b" + EXT_LABEL + r"\b" + EXT_GAP + r"{0,40}?(?:at\s+just\s+)?(" + NUM + r")" + _M + r"\(?([WDHL])\)?" + _CM + r"\s*[x×X]\s*(" + NUM + r")"
                            + _M + r"\(?([WDHL])\)?" + _CM + r"\s*[x×X]\s*(" + NUM + r")" + _M + r"\(?([WDHL])\)?(?![a-z])")
EXT_HEADER_RX = re.compile(r"(?i)\b" + EXT_LABEL + r"\b" + EXT_GAP + r"{0,30}?\(?\s*W\s*[x×]\s*D\s*[x×]\s*H\s*\)?\s*[:·\-–]?\s*(" + NUM + r")" + _M + r"[x×X]\s*("
                           + NUM + r")" + _M + r"[x×X]\s*(" + NUM + r")" + INCH_MARK + r"?(?!\s*[x×X]\s*\d)(?!\s+" + NUM + r"\s*" + INCH_MARK + r"?\s*[x×X])")
EXT_BARREL_RX = re.compile(r"(?i)\b" + EXT_LABEL + r"\b" + EXT_GAP + r"{0,30}?(" + NUM + r")" + _M + r"L\s*[x×X]\s*(" + NUM + r")" + _M + r"Diameter\b")
EXT_ROUND_RX = re.compile(r"(?i)\b" + EXT_LABEL + r"\b" + EXT_GAP + r"{0,30}?Diameter\s*(" + NUM + r")" + _M + r"[x×X]\s*H\s*(" + NUM + r")" + INCH_MARK + r"?")
EXT_AXIS_RX = re.compile(r"(?i)\b(width|depth|length|height)\s*:?\s*(" + NUM + r")\s*" + INCH_MARK)
EXT_PER_AXIS_RX = re.compile(r"(?i)\b(?:exterior|outside)\s+(width|depth|length|height)\s*:?\s*(" + NUM + r")\s*" + INCH_MARK)
EXT_WALL_RX = re.compile(r"(?i)\b(back|side|front)\s+walls?(\s+exterior|\s+interior)?\s*:\s*(" + NUM + r")" + _M + r"W?(?:\s*[x×X]\s*(" + NUM + r")" + _M + r"H)?")
EXT_BLOCK_RX = re.compile(r"(?i)\b(?:exterior|outside|overall)\s+(?:dimensions?|size)\b(?:\s+with\s+roof\s+cap)?\s*:?")
EXT_BLOCK_END_RX = re.compile(r"(?i)\b(?:interior|inside|weight|bench|when building|heaters?\b|natural wood)")


def _part(label, stated):
    return (label, to_inches(stated), stated.strip())


def ex_exterior(doc):
    out = []
    for loc, text in doc.segments:
        t = re.sub(r"\s*\n\s*", " ", text)
        for m in EXT_LETTERS_RX.finditer(t):
            axes = [m.group(2).lower(), m.group(4).lower(), m.group(6).lower()]
            if len(set(axes)) == 3 and "w" in axes and "h" in axes and ({"d", "l"} & set(axes)):
                parts = tuple(_part(AXIS_NAME[a], m.group(i)) for a, i in zip(axes, (1, 3, 5)))
                # "Exterior Dimensions Roof: 96 1/4” L x …": the size is stated for the roof, and says so
                qual = "roof" if re.search(r"(?i)\broof\s*:", m.group(0)[:m.start(1) - m.start()]) else ""
                out.append((("rectangular", parts, qual), loc, snip(t, m, pad=30)))
        for m in EXT_HEADER_RX.finditer(t):
            parts = tuple(_part(n, m.group(i)) for n, i in (("Width", 1), ("Depth", 2), ("Height", 3)))
            out.append((("rectangular", parts, ""), loc, snip(t, m, pad=30)))
        for m in EXT_BARREL_RX.finditer(t):
            out.append((("barrel", (_part("Length", m.group(1)), _part("Diameter", m.group(2))), ""), loc, snip(t, m, pad=30)))
        for m in EXT_ROUND_RX.finditer(t):
            out.append((("round", (_part("Diameter", m.group(1)), _part("Height", m.group(2))), ""), loc, snip(t, m, pad=30)))
        # per-axis labels after an "Exterior Dimensions" label: "Width: 51 3/4″ Depth: 47 3/4″ Height: 77″"
        for b in EXT_BLOCK_RX.finditer(t):
            rest = t[b.end(): b.end() + 220]
            end = EXT_BLOCK_END_RX.search(rest)
            win = rest[:end.start()] if end else rest
            axes = [(a.group(1).lower(), a.group(2)) for a in EXT_AXIS_RX.finditer(win)]
            names = [a for a, _ in axes]
            if axes and len(names) == len(set(names)) and {"width", "height"} <= set(names) and ({"depth", "length"} & set(names)) \
                    and len(names) == 3:
                out.append((("rectangular", tuple(_part(AXIS_NAME[a], v) for a, v in axes), ""), loc, (b.group(0) + " " + win).strip()[:200]))
            walls = [w for w in EXT_WALL_RX.finditer(win + " " + t[b.end() + len(win): b.end() + len(win) + 400])
                     if not (w.group(2) or "").strip().lower() == "interior"]
            if walls:
                corner = corner_parts(walls, win)
                if corner:
                    out.append((("corner", corner, ""), loc, (b.group(0) + " " + win).strip()[:200]))
        # labelled axes each carrying "Exterior": "Exterior Depth 84.75″ … Exterior Width 86.25″ … Exterior Height 86.25″"
        per = [(a.group(1).lower(), a.group(2)) for a in EXT_PER_AXIS_RX.finditer(t)]
        names = [a for a, _ in per]
        if per and len(names) == 3 and len(set(names)) == 3 and {"width", "height"} <= set(names) and ({"depth", "length"} & set(names)):
            out.append((("rectangular", tuple(_part(AXIS_NAME[a], v) for a, v in per), ""),
                        loc, " ".join(f"Exterior {a.title()} {v}″" for a, v in per)))
    # one statement per value: the same size found by two forms is one statement
    seen, uniq = set(), []
    for v, loc, sn in out:
        k = ext_key(v)
        if (k, loc) not in seen:
            seen.add((k, loc))
            uniq.append((v, loc, sn))
    return uniq


def corner_parts(walls, win):
    """Every wall the source lists, each with its length, plus one height. Walls stated with
    their own heights must agree on the height, or the set is ambiguous and nothing is read."""
    parts, heights = [], set()
    for w in walls:
        label = w.group(1).title() + (" walls" if w.group(1).lower() != "front" else " wall")
        if any(p[0] == label for p in parts):
            return None                        # the same wall stated twice: ambiguous
        parts.append(_part(label, w.group(3)))
        if w.group(4):
            heights.add(w.group(4).strip())
    h = re.search(r"(?i)\bheight\s*:?\s*(" + NUM + r")\s*" + INCH_MARK, win)
    if h:
        heights.add(h.group(1).strip())
    if len({to_inches(x) for x in heights}) != 1 or len(parts) < 2:
        return None
    return tuple(parts) + (_part("Height", sorted(heights)[0]),)


def ext_key(v):
    if not (isinstance(v, tuple) and len(v) == 3 and isinstance(v[1], tuple)):
        return v                      # an option-dependence marker from option_group
    shape, parts, qual = v
    return (shape, tuple((lab.lower(), inch) for lab, inch, _ in parts), qual)


def ext_value(v):
    shape, parts, qual = v
    out = {"shape": shape, "parts": [{"label": lab, "inches": inch, "stated": st} for lab, inch, st in parts]}
    if qual:
        out["qualifier"] = qual       # e.g. "roof": the manufacturer states the size at the roof
    return out


def ex_dims_assembled(doc):
    return _dims(doc, r"(?:exterior|outside)")


def ex_dims_crated(doc):
    return _dims(doc, r"shipping")


def ex_warranty(doc, lead):
    if not lead:
        return []
    return _scan(doc, re.compile(re.escape(lead), re.I), lambda m: lead)


# Labelled circuits (B1-D4). Two shapes a source uses:
#   "240V / 40AMP (Stove) and 120V / 15AMP (Lights and Music)"
#   "Infrared heaters and lighting require a dedicated 120V/20A circuit"
CIRC_PAREN_RX = re.compile(r"(?i)(?<![\d.])(\d{3})\s*V(?:AC)?\s*/\s*(\d{1,2})\s*A(?:MPS?)?\b\s*\(([^)]{2,60})\)")
LOAD_WORD_RX = re.compile(r"(?i)stove|heater|light|music|control|infrared|spectrum|panel|radio|audio|chromo|steam|emitter")
CIRC_PROSE_RX = re.compile(r"(?i)\b((?:(?!circuits?\b|required\b|separate\b|two\b|three\b|dedicated\b)[a-z][\w&-]*\s+){0,2}(?:heaters?|lighting|lights|stove|controls?|panels?)(?:\s+(?:and|&)\s+[\w-]+)?)"
                           r"\s+requires?\s+(?:a\s+|an\s+)?(?:(?:dedicated|hardwired|separate)\s+)*(\d{3})\s*V\s*/\s*(\d{1,2})\s*A\b")
PAIR_RX = re.compile(r"(?i)(?<![\d.])(\d{3})\s*V\w*\s*/\s*(\d{1,2})\s*A")
COUNT_RX = re.compile(r"(?i)\b(two|three|2|3)\s+(?:separate\s+|dedicated\s+)*circuits\b")


def ex_circuits(doc):
    """One statement per segment: the tuple of labelled circuits. If the segment also
    holds an unlabelled voltage/amperage pair, or states a different circuit count,
    a second statement makes the field ambiguous: every circuit must be labelled."""
    out = []
    for loc, text in doc.segments:
        found = {}
        spans = []
        for m in CIRC_PAREN_RX.finditer(text):
            if not LOAD_WORD_RX.search(m.group(3)):
                continue   # "(Please consult a certified electrician.)" labels nothing
            found[m.group(3).strip().lower()] = (m.group(3).strip(), f"{m.group(1)}V", float(m.group(2)), snip(text, m))
            spans.append((m.start(), m.end()))
        for m in CIRC_PROSE_RX.finditer(text):
            purpose = re.sub(r"(?i)^(?:the|all|and)\s+", "", m.group(1).strip())
            found.setdefault(purpose.lower(), (purpose, f"{m.group(2)}V", float(m.group(3)), snip(text, m)))
            spans.append((m.start(), m.end()))
        if not found:
            continue
        circuits = tuple(sorted((p, v, a) for p, v, a, _ in found.values()))
        snippet = " … ".join(sorted({s for *_, s in found.values()}))[:400]
        out.append((circuits, loc, snippet))
        labelled = {(v, a) for _, v, a in circuits}
        for m in PAIR_RX.finditer(text):
            inside = any(a <= m.start() < b for a, b in spans)
            if not inside and (f"{m.group(1)}V", float(m.group(2))) not in labelled:
                out.append(("an unlabelled circuit is also stated", loc, snip(text, m)))
        for m in COUNT_RX.finditer(text):
            n = {"two": 2, "three": 3}.get(m.group(1).lower(), None) or int(m.group(1))
            if n != len(circuits):
                out.append((f"the source states {n} circuits", loc, snip(text, m)))
    return out


# A passage that lists heater OPTIONS ("4.5kw and 6kw heaters require a 30 amp
# connection, 8kw ... 40 amp ... wood burning stoves require no electrical
# hookup") states what each option needs, not what this model is. Every
# electrical statement drawn from such a passage is paired with a
# "depends on heater option" statement, so the field is withheld as ambiguous.
# The same applies to every electrical statement on a product whose page lets the
# buyer choose the heater package (Shopify option named heater/stove/power...).
KW_ANY_RX = re.compile(r"(?i)(?<![\d.])(\d{1,2}(?:\.\d)?)\s*kw\b")


def is_option_table(text):
    kws = {float(m.group(1)) for m in KW_ANY_RX.finditer(text)}
    return len(kws) >= 2 or bool(re.search(r"(?i)wood[- ]burning", text))


def option_aware(fn, kw_field=False):
    def wrapped(doc):
        out = []
        for v, loc, snip_ in fn(doc):
            out.append((v, loc, snip_))
            if getattr(doc, "option_note", None):
                if kw_field and getattr(doc, "option_kw", None) is not None and v == doc.option_kw:
                    continue   # every choice the page offers names this same rating
                out.append(("depends on the buyer's package choice", loc, doc.option_note))
                continue
            seg = next((t for l, t in doc.segments if l == loc), "")
            if is_option_table(seg):
                # Only the sentence around the statement decides, not the whole panel.
                around = seg[max(0, seg.find(snip_[:40]) - 200): seg.find(snip_[:40]) + 260] if snip_[:40] in seg else seg
                if is_option_table(around):
                    out.append(("depends on heater option", loc, snip_))
        return out
    return wrapped


# ------------------------------------------------------------------ manuals --
# A PDF counts as the manufacturer's document when the manufacturer's own site
# links it from an origin host (its own domain, its own Shopify file store, or a
# listed asset host). Two ways it can attach to a record:
#
#  1. MODEL BINDING (every brand). Our model number appears in it as a token, and
#     a figure is taken only when OUR model number governs it (the model token
#     that most recently precedes it; CLAUDE.md, Round 15). A PDF found this way
#     must also name the brand in its text.
#  2. LINK (brands with "link_attach", approved for Salus in B1-D3/D8). The PDF is
#     linked from this record's own product page and from no other product page.
#     Its figures are used unless they depend on a buyer's option choice.

def origin_pdf(url, src):
    parts = urllib.parse.urlsplit(url)
    if parts.netloc == "cdn.shopify.com":
        prefix = src.get("pdf_path_prefix") or src.get("_shop_prefix")
        return bool(prefix) and parts.path.startswith(prefix)
    return parts.netloc in set(src.get("pdf_hosts", [])) | set(src["manufacturer_domains"])


PDF_LINK_RX = re.compile(r'(?:https?:)?//[^\s"\'<>]+?\.pdf(?:\?[^\s"\'<>]*)?', re.I)


def page_pdf_links(text, base, src):
    # Round 3 (D-5): links inside script-escaped JSON keep `\/` and a trailing `\"`; unescaped,
    # or the real document is never read.
    text = text.replace("\\/", "/").replace('\\"', '"')
    out = set()
    for m in PDF_LINK_RX.finditer(text):
        u = html.unescape(m.group(0))
        u = ("https:" + u) if u.startswith("//") else u
        u = re.sub(r"[\\\"']+$", "", u)
        if origin_pdf(u, src):
            out.add(u)
    for m in re.finditer(r'href="(/[^"]+?\.pdf(?:\?[^"]*)?)"', text, re.I):
        u = f"https://{urllib.parse.urlsplit(base).netloc}{html.unescape(m.group(1))}"
        if origin_pdf(u, src):
            out.add(u)
    return out


def pdf_links(cache, src, p):
    links = page_pdf_links(p.body_html or "", p.url, src)
    data, _ = cache.get(p.url)
    if data is not None:
        links |= page_pdf_links(data.decode("utf-8", "replace"), p.url, src)
    return links


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


def load_manual(cache, url):
    """(Manual | None, reason)."""
    data, e = cache.get(url)
    if data is None:
        return None, f"not fetched ({(e or {}).get('status', 'absent')})"
    if not data.startswith(b"%PDF"):
        return None, "not a PDF (magic bytes)"
    try:
        pages = pdf_pages(data, e["sha256"])
    except Exception as ex:  # a parse failure is recorded, not guessed around
        return None, f"unreadable: {type(ex).__name__}"
    if not pages:
        return None, "no text layer (NEEDS_OCR); nothing inferred"
    return Manual(url, e, pages), "ok"


def manual_doc(man, keys, exact_models=frozenset()):
    """Model binding: a Doc whose statements are only those our model governs.
    A model number is recorded only when the manual prints exactly the page's model
    string, suffix included: 'DYN-6103-01' in 'DYN-6103-01 / DYN-6103-01 Elite' is not
    the Elite's number."""
    d = Doc(man.url, man.url, man.entry, "documented", "manufacturer_manual", [], kind="pdf")
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
                if rx is AMP_RX and not amp_ok(m, flat):
                    continue
                owner = manual_owner(flat, m)
                if owner is None or not any(vb_norm(o) in keys for o in owner.split("|")):
                    continue
                after = flat[m.end():m.end() + 60]
                if NOT_SUPPLY_RX.search(after):
                    # "120VAC 15AMP Outlet Needed For Lights/Radio": a lighting outlet, not the supply.
                    continue
                st = snip(flat, m)
                d.bound.append((field, conv(m), f"pdf page {page_no}", st))
                if (MULTI_CIRCUIT_RX.search(flat[max(0, m.start() - 40): m.start()])
                        or PLURAL_CIRCUITS_RX.match(after)
                        or re.search(r"\d\s*/\s*$", flat[max(0, m.start() - 4): m.start()])):
                    # "TWO SEPARATE ... CIRCUITS", "Dedicated Circuits Required", "30/40AMP".
                    d.bound.append((field, "multiple circuits or a conditional figure", f"pdf page {page_no}", st))
                if field == "stated_amperage" and re.search(r"(?i)\bbreaker\b", flat[max(0, m.start() - 30):m.end() + 30]):
                    d.bound.append(("breaker_amps", conv(m), f"pdf page {page_no}", st))
        for t, a, b in model_tokens(flat):
            suf = re.match(r"\s*(Elite|CED|HEM|FS|ZF)\b", flat[b:b + 8])
            full = f"{t} {suf.group(1)}" if suf else t
            if vb_norm(full) in exact_models:
                d.bound.append(("model_number", full, f"pdf page {page_no}", flat[max(0, a - 60):b + 60].replace("\n", " ")))
                break
    return d


NOT_SUPPLY_RX = re.compile(r"(?i)^[^.]{0,40}?\b(?:for\s+)?(?:lights?|lighting|radio|audio|controls?)\b")
PAREN_MODEL_RX = re.compile(r"^[^.()]{0,50}\(([^)]{3,80})\)")


def manual_owner(flat, m):
    """The model a figure in a manual belongs to.

    Two layouts exist, and a manual may use either:
      label-then-spec   "GDI-8503-01 - 240VAC 30AMP Circuit Required"  (Golden Designs)
      spec-then-label   "120VAC 20AMP Dedicated Circuit Required (DYN-6315-05)"  (Dynamic)
    A model number in a parenthetical right after the figure is an explicit label and
    wins. Otherwise the model that most recently precedes it governs (Round 15).
    If the parenthetical names several models, the figure is theirs jointly."""
    after = PAREN_MODEL_RX.match(flat[m.end():m.end() + 140])
    if after:
        toks = [t for t, _, _ in model_tokens(after.group(1))]
        if toks:
            return toks[0] if len(toks) == 1 else "|".join(toks)
        if re.search(r"(?i)\bperson\b|\bmodel\b", after.group(1)):
            return None   # "(2 Person Model)": labelled for a configuration we cannot tie to a number
    lo = max(0, m.start() - 160)
    return governing_model(flat[lo:m.end() + 40], m.start() - lo)


GENERIC_TITLE_WORDS = {"traditional", "far", "full", "spectrum", "infrared", "indoor", "outdoor", "sauna", "barrel",
                       "hybrid", "luxury", "ir", "the", "a", "person", "with", "and"}


def series_name(title):
    """The product's own series words from its title: 'Majestic Far Infrared Indoor
    Sauna - 8 Person' -> 'majestic'; 'Grand Laurel ...' -> 'grand laurel'."""
    # Round 3: "Eclipse™" folded to "eclipsetm", which no document prints; marks are dropped first.
    words = re.findall(r"[A-Za-z]+", unicodedata_fold(re.sub(r"[™®©]", "", re.split(r"\s+-\s+", title)[0])))
    out = []
    for w in words:
        if w.lower() in GENERIC_TITLE_WORDS:
            break
        out.append(w.lower())
    if len(out) == 1 and out[0] in ("grand", "king", "new", "mini"):
        return ""
    return " ".join(out)


def linked_doc(man, option_note, title="", brand=""):
    """Link attachment (B1-D3): only pages that name this product's series speak for
    it. A manual's generic pages ('Information for your electrician: 4.5kW and 6.0kW
    KIP Heaters ...', '120VAC 15AMP ... or 120VAC 20AMP ...') state options for
    other configurations, not this model."""
    # Round 3: a title that starts with the brand ("Sun Home Eclipse 2-Person ...") gave the series
    # "sun home eclipse", which the spec sheet (it says "ECLIPSE 2") never prints, so every page was dropped.
    if brand:
        title = re.sub(r"(?i)^\s*" + re.escape(brand) + r"\b\s*", "", title)
    ser = series_name(title)
    segs = [(f"pdf page {n}", re.sub(r"[ \t]+", " ", t)) for n, t in man.pages
            if ser and re.search(r"(?i)\b" + re.escape(ser).replace("\\ ", r"\s+") + r"\b", re.sub(r"\s+", " ", t))]
    d = Doc(man.url, man.url, man.entry, "documented", "manufacturer_manual", segs, kind="pdf")
    d.option_note = option_note
    return d


# Capacity is never read from a manual: manuals count people for ASSEMBLY
# ("2 Person Recommended" is the install crew), not seating.
PDF_FIELDS = {"supply_voltage", "stated_amperage", "breaker_amps", "connection_type", "gfci",
              "circuit_requirement", "heater_kw", "circuits", "max_temp_f", "dims_assembled", "dims_crated", "exterior"}


# ----------------------------------------------------------------- deciding --

def decide(statements_by_tier, lead, eq=lambda a, b: a == b):
    """statements_by_tier: [(tier, doc, [(value, loc, snippet)])] highest tier first.
    Returns (outcome, chosen | None, notes[])."""
    chosen, notes, singles = None, [], []
    blocked = False
    for tier, doc, sts in statements_by_tier:
        if not sts:
            continue
        if blocked:
            # An ambiguous higher tier ("TWO SEPARATE ... CIRCUITS", "30AMP/40AMP") is not
            # overridden by a simpler figure lower down.
            continue
        distinct = []
        for v, loc, s in sts:
            if not any(eq(v, d[0]) for d in distinct):
                distinct.append((v, loc, s))
        if len(distinct) == 1:
            singles.append((tier, doc, distinct[0]))
        else:
            notes.append(("within_source_ambiguity", tier, doc, distinct))
            if not singles:
                blocked = True
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
                         "snippet": s, "fetch_method": getattr(doc, "method", "static")}}


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
    """Exact, after normalisation. 'DYN-6103-01' and 'DYN-6103-01 Elite' are different models."""
    return norm_model(a) == norm_model(b)


# ------------------------------------------------------------------ build --

FIELDS = [
    # (field, extractor, eq)
    ("heat_type", option_group(lambda d: ex_heat_type(d) + ex_heat_from_heaters(d), "type"), None),
    ("placement", ex_placement, None),
    ("capacity", option_group(ex_capacity, "size"), None),
    # Round 3: "Nordic Pine" and "Thermally Modified Nordic Pine", "Spruce" and "Nordic Spruce" name one wood
    # at two levels of detail; one name containing the other is consistent, and the first statement stays.
    ("wood_species", option_group(ex_wood, "wood"), lambda a, b: str(a).lower() in str(b).lower() or str(b).lower() in str(a).lower()),
    ("spectrum", ex_spectrum, lambda a, b: str(a).lower() == str(b).lower()),
    ("emf_claim", ex_emf, lambda a, b: str(a).lower() == str(b).lower()),
    ("red_light", ex_red_light, None),
    ("supply_voltage", option_aware(ex_voltage), lambda a, b: str(a).replace(" ", "").lower() == str(b).replace(" ", "").lower()),
    ("stated_amperage", option_aware(ex_amps), None),
    ("breaker_amps", option_aware(lambda d: ex_amps(d, breaker=True)), None),
    ("connection_type", option_aware(ex_plug), None),
    ("gfci", option_aware(ex_gfci), None),
    ("circuit_requirement", option_aware(ex_circuit), None),
    ("circuits", option_aware(ex_circuits), None),
    ("heater_kw", option_aware(ex_kw, kw_field=True), None),
    ("max_temp_f", ex_max_temp, None),
    ("dims_assembled", option_group(ex_dims_assembled, "size"), None),
    ("dims_crated", option_group(ex_dims_crated, "size"), None),
    ("exterior", option_group(ex_exterior, "size"), lambda a, b: ext_key(a) == ext_key(b)),
]
RECORD_PATHS = {
    "spectrum": ("infrared", "spectrum"), "emf_claim": ("infrared", "emf_claim"), "red_light": ("infrared", "red_light"),
    "heater_kw": ("electrical", "heater_kw"), "supply_voltage": ("electrical", "supply_voltage"),
    "stated_amperage": ("electrical", "stated_amperage"), "connection_type": ("electrical", "connection_type"),
    "breaker_amps": ("electrical", "breaker_amps"), "model_number": ("identity", "model_number"),
    "heat_type": ("heat_type",), "placement": ("placement",), "capacity": ("capacity_max",),
    "wood_species": ("materials", "wood_species"), "max_temp_f": ("thermal", "max_temp_f"),
    "warranty": ("warranty", "summary"),
}
NO_LEAD = ("dims_assembled", "dims_crated", "breaker_amps", "gfci", "circuit_requirement", "circuits", "exterior")


def brand_label(src, brand):
    return src.get("display") or BRAND_DISPLAY.get(brand, brand)


def build_brand(cache, brand, src, leads_all):
    disp = brand_label(src, brand)
    leads = sorted([r for r in leads_all if r["brand"] == brand], key=lambda r: r["model_key"])
    products = products_for(cache, brand, src, leads)
    matched, no_page = match_leads(src, leads, products)

    # Which product pages link which PDFs (for link attachment's "no other page" test).
    link_map = defaultdict(set)
    if src.get("link_attach", True):
        for h, p in sorted(products.items()):
            for u in pdf_links(cache, src, p):
                link_map[u].add(h)
    manuals, manual_notes, manual_use = {}, {}, defaultdict(list)
    # Model numbers this brand itself publishes. A document that names any of them is a
    # line document and goes through model binding (Round 15); link attachment is only
    # for documents that name no model number of the brand (Salus's series spec sheets).
    brand_tokens = {vb_norm(x) for pp in products.values() for x in pp.skus if x}
    brand_tokens |= {vb_norm(t) for pp in products.values() for x in pp.skus if x for t, _, _ in model_tokens(x.upper())}
    brand_tokens = {k for k in brand_tokens if len(k) >= 5}

    def manual(url):
        if url not in manuals:
            m, why = load_manual(cache, url)
            manuals[url] = m
            if m is None:
                manual_notes[url] = why
        return manuals[url]

    records, log, conflicts = [], [], []
    for handle in sorted(matched):
        p = products[handle]
        docs = product_docs(cache, src, p)
        if not docs:
            continue
        lead_pairs = matched[handle]
        keys = {vb_norm(x) for x in p.skus + [r["model"] for r, _ in lead_pairs] if x}
        keys |= {vb_norm(t) for x in p.skus for t, _, _ in model_tokens(x.upper())}
        keys = {k for k in keys if len(k) >= 5}
        for u in sorted(pdf_links(cache, src, p)):
            m = manual(u)
            if m is None:
                continue
            names_brand_models = bool(m.tokens & brand_tokens)
            if src.get("link_attach", True) and link_map.get(u) == {handle} and not names_brand_models:
                docs.append(linked_doc(m, docs[0].option_note, p.title, disp))
                manual_use[u].append((handle, "link: linked from this product page only"))
            elif m.tokens & keys:
                if not any(re.search(src.get("brand_word", disp), t, re.I) for _, t in m.pages):
                    manual_notes[u] = f"names our model but not the brand ({src.get('brand_word', disp)})"
                    continue
                exact = frozenset(vb_norm(v) for d0 in docs if not hasattr(d0, "bound") and d0.kind != "pdf"
                                  for v, _, _ in ex_model(d0))
                docs.append(manual_doc(m, keys, exact))
                manual_use[u].append((handle, "model binding"))
            else:
                reason = ("linked from more than one product page" if src.get("link_attach", True) and len(link_map.get(u, ())) > 1
                          else "does not contain this product's model number")
                manual_notes.setdefault(u, reason)
        lead = lead_values(lead_pairs[0][0])
        rec_log = {"handle": handle, "leads": [{"lead_key": r["model_key"], "lead_model": r["model"], "matched_by": how}
                                                for r, how in lead_pairs],
                   "fields": {}}
        results = {}

        def run(field, fn, lead_v, eq=None):
            per_doc = []
            for d in docs:
                if hasattr(d, "bound"):
                    sts = [(v, loc, s) for f_, v, loc, s in d.bound if f_ == field]
                elif d.kind == "pdf" and field not in PDF_FIELDS:
                    sts = []
                elif d.kind == "meta" and field != "capacity":
                    sts = []            # D-2: page metadata speaks for capacity only
                else:
                    sts = fn(d)
                per_doc.append((d.tier, d, sts))
            per_doc = resolve_fallbacks(field, per_doc)

            by_tier = []
            for t in ("documented", "listed"):
                sts = [(v, loc, s, d) for tt, d, ss in per_doc if tt == t for v, loc, s in ss]
                if sts:
                    by_tier.append((t, sts))
            flat = [(t, sts[0][3], [(v, loc, s) for v, loc, s, _ in sts]) for t, sts in by_tier]
            outcome, chosen, notes = decide(flat, lead_v, eq or (lambda a, b: a == b))
            if field == "wood_species" and chosen is not None:
                # Round 3: nested names ("Cedar" ⊂ "Red Cedar" ⊂ "Canadian Red Cedar") are one wood only if
                # EVERY pair nests; containment alone is order-dependent and would merge two different
                # cedars through a generic "Cedar".
                vals = {str(v).lower() for _, sts in by_tier for v, _, _, _ in sts if isinstance(v, str)
                        and v != "depends on the buyer's choice"}
                if not woods_all_nest(vals):
                    outcome, chosen = "ambiguous", None
            if chosen is not None:
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
                    conflicts.append({"kind": "within_source_ambiguity", "brand": disp,
                                      "handle": handle, "field": field, "source_url": d.source_url,
                                      "fetched_at": d.fetched_at, "values": [
                                          {"value": v, "locator": loc, "snippet": s} for v, loc, s in distinct]})
                elif n[0] == "tier_disagreement":
                    _, a, b = n
                    conflicts.append({"kind": "tier_disagreement", "brand": disp,
                                      "handle": handle, "field": field,
                                      "published": {"value": a[2][0], "grade": a[0], "source_url": a[1].source_url, "fetched_at": a[1].fetched_at, "snippet": a[2][2]},
                                      "other": {"value": b[2][0], "grade": b[0], "source_url": b[1].source_url, "fetched_at": b[1].fetched_at, "snippet": b[2][2]}})
            if outcome == "changed":
                conflicts.append({"kind": "lead_mismatch", "brand": disp, "handle": handle,
                                  "field": field, "lead_value": lead_v, "source_value": chosen[2][0],
                                  "source_url": chosen[1].source_url, "fetched_at": chosen[1].fetched_at,
                                  "snippet": chosen[2][2]})
            return outcome, chosen

        run("model_number", ex_model, lead["model_number"], model_eq)
        if results["model_number"][0] == "ambiguous" and lead["model_number"]:
            # Several model strings on the page; confirm only if one of them IS the lead.
            hits = [(d, s) for d in docs if not hasattr(d, "bound") and d.kind != "pdf"
                    for s in ex_model(d) if model_eq(lead["model_number"], s[0])]
            if hits:
                labelled = [h for h in hits if "sku" not in h[1][1]] or hits
                d0, s0 = labelled[0]
                results["model_number"] = ("confirmed", ("listed", d0, s0))
                rec_log["fields"]["model_number"].update(outcome="confirmed", value=s0[0], tier="listed")

        for field, fn, eq in FIELDS:
            lv = lead.get(field) if field not in NO_LEAD else None
            if field == "supply_voltage" and lv:
                lv = lv.replace(" ", "")
            run(field, fn, lv, eq)
        run("warranty", lambda d: ex_warranty(d, lead["warranty"]), lead["warranty"],
            lambda a, b: str(a).lower() == str(b).lower())

        rec = assemble(brand, src, p, docs, results, cache)
        # The record decides what was published. A value the heat type makes
        # not_applicable was not confirmed, whatever the page said.
        for fld, path in RECORD_PATHS.items():
            node = rec
            for k in path:
                node = node[k]
            x = rec_log["fields"].get(fld)
            if not x or x["outcome"] not in ("confirmed", "changed", "source_only"):
                continue
            if node["grade"] == "not_applicable":
                x.update(outcome="not_applicable", value=None, tier=None)
            elif node["grade"] not in ("listed", "documented", "claimed"):
                # e.g. spectrum on a page whose heat type is unknown: not published.
                x.update(outcome="withheld_heat_type_unknown", value=None, tier=None)
            else:
                continue
            conflicts[:] = [c for c in conflicts if not (c.get("handle") == handle and c.get("field") == fld)]
        if src.get("status") == "pending_decision":
            rec["_pending"] = src["status_note"]
        records.append(rec)
        log.append(rec_log)
    manual_report = {"pdfs_considered": len(manuals), "readable": sum(1 for m in manuals.values() if m),
                     "attached": {u: sorted(set(h)) for u, h in sorted(manual_use.items())},
                     "not_attached": dict(sorted((u, why) for u, why in manual_notes.items() if u not in manual_use))}
    return records, log, conflicts, no_page, leads, manual_report, matched


def assemble(brand, src, p, docs, res, cache):
    disp = brand_label(src, brand)
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
    cap_note = "the manufacturer states this as a maximum ('up to')" if cap and cap[2][1].endswith(UP_TO_MARK) else None
    ext_o, ext_c = res.get("exterior", ("absent", None))
    exterior = graded(ext_c, ext_value(ext_c[2][0])) if ext_c else nv("the source states more than one exterior size" if ext_o == "ambiguous" else None)
    hi = page.heater if hasattr(page, "heater") else None
    option_dep = None
    if hi and hi[4] >= 2:
        _, text, hd, hloc, _ = hi
        option_dep = {"value": "heater option", "unit": None, "grade": "listed", "source_url": hd.source_url,
                      "source_type": hd.source_type, "observed_at": hd.fetched_at[:10],
                      "note": "The buyer chooses the heater, and the electrical requirements depend on that choice.",
                      "evidence": {"fetched_at": hd.fetched_at, "content_sha256": hd.sha,
                                   "locator": hloc if hd.fetched_url == hd.source_url else f"{hloc} (fetched as {hd.fetched_url})",
                                   "snippet": text, "fetch_method": getattr(hd, "method", "static")}}

    supply = f("supply_voltage")
    if supply["value"] is not None and supply["value"] not in ("120V", "240V", "208–240V"):
        supply = nv("the source states a voltage outside the single-supply values this schema publishes")

    def box(field):
        o, c = res[field]
        if c is None:
            return {k: nv(None, "in") for k in ("width_in", "depth_in", "height_in")}
        w, d, h = c[2][0]
        return {"width_in": graded(c, w, "in"), "depth_in": graded(c, d, "in"), "height_in": graded(c, h, "in")}

    circ_o, circ_c = res["circuits"]
    if circ_c is not None:
        circuits = [{"purpose": graded(circ_c, pp), "voltage": graded(circ_c, vv), "stated_amperage": graded(circ_c, aa, "A")}
                    for pp, vv, aa in circ_c[2][0]]
        circuits_required = graded(circ_c, len(circ_c[2][0]), "circuits")
    else:
        circuits = []
        circuits_required = nv("the source does not label every circuit" if circ_o == "ambiguous" else None, "circuits")

    loc_base = f"product '{p.handle}'"
    brand_f = {"value": disp, "unit": None, "grade": "listed", "source_url": page.source_url,
               "source_type": "manufacturer", "observed_at": page.fetched_at[:10], "note": None,
               "evidence": {"fetched_at": page.fetched_at, "content_sha256": page.sha,
                            "locator": f"{loc_base} on the manufacturer's own site" + ("" if page.fetched_url == page.source_url else f" (fetched as {page.fetched_url})"),
                            "snippet": (f"vendor: {p.vendor}; " if p.vendor else "") + f"listed on {urllib.parse.urlsplit(page.source_url).netloc}"}}
    name_f = ({"value": name, "unit": None, "grade": "listed", "source_url": page.source_url,
               "source_type": "manufacturer", "observed_at": page.fetched_at[:10],
               "note": "Model name taken from the manufacturer's product title (brand, capacity and marketing claims removed).",
               "evidence": {"fetched_at": page.fetched_at, "content_sha256": page.sha,
                            "locator": f"{loc_base} title" + ("" if page.fetched_url == page.source_url else f" (fetched as {page.fetched_url})"),
                            "snippet": title}} if name else nv())
    offers = []
    variants = [v for v in p.variants if v.get("price")]
    if len(variants) == 1:
        offers.append({"retailer": f"{disp} (manufacturer direct)", "url": page.source_url,
                       "price_usd": float(variants[0]["price"]),
                       "reference_price_usd": float(variants[0]["compare_at_price"]) if variants[0].get("compare_at_price") else None,
                       "retailer_type": "manufacturer_direct", "inh_sells": False,
                       "observed_at": page.fetched_at[:10]})

    rec = {
        "schema_version": "0.3.0",
        "inh_id": f"sauna/{slugify(disp)}/{slugify(res['model_number'][1][2][0]) if res['model_number'][1] else slugify(p.handle)}",
        "category": "sauna",
        "status": "published",
        "withheld_reasons": [],
        "identity": {
            "brand": brand_f,
            "model_number": f("model_number"),
            "model_name": name_f,
            "configuration": nv(),
            "display_title": display_title(disp, name, cmin, cmax) if name else p.handle,
            "aliases": [],
        },
        "heat_type": f("heat_type"),
        "placement": f("placement"),
        "capacity_min": graded(cap, cmin, "persons", cap_note) if cap else nv(unit="persons"),
        "capacity_max": graded(cap, cmax, "persons", cap_note) if cap else nv(unit="persons"),
        "dimensions": {"assembled": box("dims_assembled"), "crated": box("dims_crated"), "exterior": exterior},
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
            "circuits": circuits,
            "circuits_required": circuits_required,
            **({"option_dependence": option_dep} if option_dep else {}),
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
                       "origin_urls": sorted({d.source_url for d in docs}),
                       **({"origin_basis": {k: src["origin_basis"][k] for k in
                           ("document_url", "content_sha256", "fetched_at", "locator", "snippet", "relationship")}}
                          if src.get("origin_basis") else {})},
        "_rule_inputs": {"text": "\n".join(t for d in docs if d.kind != "pdf" for _, t in d.segments), "title": title,
                         "cap_ambiguous": res["capacity"][0] == "ambiguous",
                         "size_option": (getattr(page, "option_notes", None) or {}).get("size")
                                        or next((f"the page lists sizes: “{c[2][:90]}”" for d in docs if d.kind != "pdf"
                                                 for c in ex_capacity(d) if re.search(r"(?i)\bsizes\b", c[2])), None),
                         "cap_statements": [c for d in docs if d.kind != "pdf" for c in ex_capacity(d)],
                         "cap_chosen": [(d.tier, d, c) for d in docs if d.kind != "pdf" for c in ex_capacity(d)]},
    }
    return rec


# ------------------------------------------------------------------ rules --

def apply_rules(records):
    for rec in records:
        ri = rec["_rule_inputs"]
        e = rec["electrical"]
        why = []
        kw = e["heater_kw"]["value"]
        amps = e["breaker_amps"]["value"] or e["stated_amperage"]["value"]
        v = e["supply_voltage"]["value"]
        volts = {"120V": [120], "240V": [240], "208–240V": [208, 240]}.get(v, [])
        if kw and amps and volts:
            bad = [(x, kw * 1000 / x) for x in volts if kw * 1000 / x > amps]
            if bad:
                why.append(("R1_ELECTRICAL", "; ".join(f"{kw:g} kW at {x}V = {a:.1f} A > {amps:g} A stated" for x, a in bad)))
        for c in e.get("circuits", []):
            if kw and re.search(r"(?i)stove|heater", c["purpose"]["value"]) and not re.search(r"(?i)infrared|panel|light", c["purpose"]["value"]):
                cv = int(c["voltage"]["value"].rstrip("V")) if c["voltage"]["value"][:3].isdigit() else None
                ca = c["stated_amperage"]["value"]
                if cv and ca and kw * 1000 / cv > ca:
                    why.append(("R1_ELECTRICAL", f"{kw:g} kW on the '{c['purpose']['value']}' circuit at {cv}V = {kw * 1000 / cv:.1f} A > {ca:g} A stated"))
        if rec["heat_type"]["value"] == "hybrid" and not (IR_TEXT.search(ri["text"]) and TRAD_TEXT.search(ri["text"])):
            why.append(("R2_HYBRID", "the manufacturer calls it hybrid but its page does not name both a traditional heater and an infrared system"))
        tuples = sorted({v for v, _, _ in ri["cap_statements"] if isinstance(v, tuple)})
        vals = [f"{a}" if a == b else f"{a}–{b}" for a, b in tuples]
        # R5 as defined in the Part A brief: "4–6 person" is min 4, max 6; a MISMATCH is a
        # stated capacity outside another stated range. Nested statements ("6 Person" and
        # "seating 5–6") are consistent: the field is withheld, the record is not quarantined.
        nested = all((a[0] >= b[0] and a[1] <= b[1]) or (b[0] >= a[0] and b[1] <= a[1])
                     for i, a in enumerate(tuples) for b in tuples[i + 1:])
        if ri["cap_ambiguous"] and ri.get("size_option"):
            rec["capacity_min"] = nv(f"withheld: {ri['size_option']}", "persons")
            rec["capacity_max"] = nv(f"withheld: {ri['size_option']}", "persons")
        elif ri["cap_ambiguous"] and len(tuples) >= 2 and not nested:
            why.append(("R5_CAPACITY", f"the manufacturer's page states capacity as {', '.join(vals)}"))
        elif ri["cap_ambiguous"] and len(tuples) >= 2:
            # R2-D6 (approved): nested statements publish the WIDEST stated range, cited to the
            # statement that states it. Nested means one statement contains all the others, so
            # the published range is always a range the manufacturer actually wrote.
            lo, hi = min(t[0] for t in tuples), max(t[1] for t in tuples)
            chosen = ri["cap_chosen"] if "cap_chosen" in ri else []   # absent: no statement can be cited, so withheld below
            widest = sorted(((tier, d, c) for tier, d, c in chosen if c[0] == (lo, hi)),
                            key=lambda x: (x[1].source_url, x[2][1], x[2][2]))
            note = f"R2-D6: the page states {' and '.join(vals)}; the widest stated range is published"
            if widest:
                rec["capacity_min"] = graded(widest[0], lo, "persons", note)
                rec["capacity_max"] = graded(widest[0], hi, "persons", note)
            else:
                rec["capacity_min"] = nv(note + " but no single statement states it; withheld", "persons")
                rec["capacity_max"] = nv(note + " but no single statement states it; withheld", "persons")
        if not rec["identity"]["model_name"]["value"]:
            why.append(("R4_TITLE", "no model name recoverable from the manufacturer's title"))
        rec["_why"] = why

    groups = defaultdict(list)
    for rec in records:
        groups[rec["identity"]["display_title"]].append(rec)
    for t, recs in groups.items():
        if len(recs) == 1:
            continue
        done = False
        for path, fmt in ((("materials", "wood_species"), "{}"), (("electrical", "heater_kw"), "{:g} kW heater"),
                          (("identity", "model_number"), "{}")):
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
        verified += sum(1 for fld in [x for x in rec["electrical"].values() if isinstance(x, dict)] + list(rec["infrared"].values()) +
                        [rec["materials"]["wood_species"], rec["thermal"]["max_temp_f"], rec["identity"]["model_number"]]
                        if fld["grade"] not in ("not_verified", "not_applicable"))
        if verified == 0:
            rec["_why"].append(("NO_VERIFIED_VALUE", "the manufacturer's page confirmed no value beyond brand and name"))
        if rec.get("_pending"):
            rec["_why"].append(("ORIGIN_PENDING", rec["_pending"]))
        rec["withheld_reasons"] = [{"rule": r, "reason": w} for r, w in rec["_why"]]
        rec["status"] = "backlog" if rec["_why"] else "published"
        rec.pop("_why"); rec.pop("_rule_inputs"); rec.pop("_pending", None)


GAP_DIAGNOSIS = OUT / "gap-diagnosis.json"


def apply_gap_diagnosis(records):
    """Round 3: attach the committed gap diagnosis (scripts/verified_gaps.py) to its records.
    Read from a committed file, so the rebuild stays byte-identical. Never changes a value."""
    if not GAP_DIAGNOSIS.exists():
        return
    diag = json.loads(GAP_DIAGNOSIS.read_text())["records"]
    for rec in records:
        if rec["inh_id"] in diag and rec["status"] == "published":
            d = diag[rec["inh_id"]]
            rec["gap_diagnosis"] = {"fields": d["fields"], "checked": d["checked"]}


def apply_title_overrides(records):
    """B1-D9: reviewed titles only. An entry applies only when "approved": true."""
    if not TITLE_OVERRIDES.exists():
        return
    ov = json.loads(TITLE_OVERRIDES.read_text()).get("overrides", {})
    for rec in records:
        o = ov.get(rec["inh_id"])
        if o and o.get("approved") is True:
            # An override may only REMOVE words from the title built from the manufacturer's
            # own name (B1-D9, R2-D2): a word it adds would be a fact nobody verified.
            have = set(re.findall(r"[\w–-]+", rec["identity"]["display_title"].lower()))
            extra = [w for w in re.findall(r"[\w–-]+", o["display_title"].lower()) if w not in have]
            if extra:
                raise SystemExit(f"HALT: title override for {rec['inh_id']} adds {extra}; overrides only remove words")
            rec["identity"]["display_title"] = o["display_title"]


# ------------------------------------------------------------------- lint --

def lint(records, conflicts, sources, built_src=None):
    """The gates Part B promised. Raises on any failure.
    `built_src` is the brand configuration AS THE BUILD USED IT, including the Shopify file prefix it
    derived (_shop_prefix): checking manual URLs against the raw configuration refused every one."""
    from jsonschema import Draft202012Validator
    schema = json.loads((OUT / "schema/inh-verified.schema.json").read_text())
    v = Draft202012Validator(schema)
    errs = []
    for rec in records:
        for e in v.iter_errors(rec):
            errs.append(f"{rec['inh_id']}: schema: {'/'.join(map(str, e.absolute_path))}: {e.message[:160]}")
    disp_to_brand = {brand_label(s, b): b for b, s in sources["brands"].items()}
    distributors = {d["domain"] for d in sources.get("distributors", [])}
    for rec in records:
        bname = disp_to_brand[rec["identity"]["brand"]["value"]]
        bsrc = (built_src or {}).get(bname) or sources["brands"][bname]
        hosts = set(bsrc["manufacturer_domains"]) | distributors
        for path, fld in walk_fields(rec):
            if fld.get("source_url"):
                h = urllib.parse.urlsplit(fld["source_url"]).netloc
                if fld.get("source_type") == "manufacturer_manual" and origin_pdf(fld["source_url"], bsrc):
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


ADAPTER_KIND = {"shopify_json": "structured data", "shopify_html": "structured data + page layout", "html_page": "page layout"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", nargs="+", required=True)
    ap.add_argument("--label", default="latest")
    a = ap.parse_args(argv)
    quieten_pdf_font_chatter()
    cache = Cache()
    sources = json.loads(SOURCES.read_text())
    leads_all = json.loads(LEADS.read_text())["products"]

    all_recs, all_log, all_conf, backlog, per_brand = [], [], [], [], {}
    for brand in a.brands:
        src = dict(sources["brands"][brand])
        if src.get("blocked"):
            bl = sorted([r for r in leads_all if r["brand"] == brand], key=lambda r: r["model_key"])
            backlog += [{"brand": brand, "lead_key": r["model_key"], "lead_model": r["model"], "lead_title": r["title"],
                         "reason": f"origin source not fetchable: {src['blocked']}"} for r in bl]
            per_brand[brand] = {"src": src, "leads": len(bl), "no_manufacturer_page": len(bl), "log": [],
                                "manuals": {"pdfs_considered": 0, "readable": 0, "attached": {}, "not_attached": {}},
                                "matched_by": {}, "blocked": src["blocked"]}
            continue
        recs, log, conf, no_page, leads, man_rep, matched = build_brand(cache, brand, src, leads_all)
        all_recs += recs; all_log += log; all_conf += conf
        backlog += [{"brand": brand, "lead_key": r["model_key"], "lead_model": r["model"], "lead_title": r["title"],
                     "reason": "no page on the manufacturer's own site matches this lead"} for r in no_page]
        per_brand[brand] = {"src": src, "leads": len(leads), "no_manufacturer_page": len(no_page), "log": log,
                            "manuals": man_rep,
                            "matched_by": dict(Counter(how.split(" (")[0] for pairs in matched.values() for _, how in pairs))}

    apply_rules(all_recs)
    apply_title_overrides(all_recs)
    apply_gap_diagnosis(all_recs)
    all_recs.sort(key=lambda r: r["inh_id"])
    all_conf.sort(key=lambda c: json.dumps(c, sort_keys=True, ensure_ascii=False))
    # R2-D15: every output is ordered by its content, never by the order --brands was typed.
    # The backlog and the log used to follow argument order, so a build from one brand list
    # and a rebuild from another produced different bytes from identical inputs.
    backlog.sort(key=lambda b: (b["brand"], b["lead_key"]))
    all_log.sort(key=lambda e: json.dumps(e, sort_keys=True, ensure_ascii=False))
    lint(all_recs, all_conf, sources, {b: v["src"] for b, v in per_brand.items()})

    dump(OUT / "saunas.json", {"schema_version": "0.3.0", "cache_manifest_sha256": cache.sha,
                               "record_count": len(all_recs),
                               "published": sum(r["status"] == "published" for r in all_recs),
                               "records": all_recs})
    dump(OUT / "conflicts.json", {"conflict_count": len(all_conf), "conflicts": all_conf})
    dump(OUT / "internal/verification-log.json", {"records": all_log})
    dump(OUT / "internal/backlog.json", {"leads_without_origin_page": backlog})

    rep = {"cache_manifest_sha256": cache.sha, "brands": {}}
    lead_fields = ["model_number", "heat_type", "placement", "capacity", "wood_species", "spectrum", "emf_claim",
                   "red_light", "supply_voltage", "stated_amperage", "connection_type", "heater_kw", "max_temp_f", "warranty"]
    confirmed_by_brand = defaultdict(list)
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
                    confirmed_by_brand[brand].append((rl["handle"], fld))
        disp = brand_label(info["src"], brand)
        brecs = [r for r in all_recs if r["identity"]["brand"]["value"] == disp]
        kind = ADAPTER_KIND[info["src"]["adapter"]] + (" + PDF" if info["manuals"]["attached"] else "")
        rep["brands"][brand] = {
            "adapter": kind, "status": "blocked" if info.get("blocked") else info["src"].get("status", "active"),
            "blocked": info.get("blocked"),
            "leads_in": info["leads"], "leads_without_manufacturer_page": info["no_manufacturer_page"],
            "matched_by": info["matched_by"], "records_built": len(brecs),
            "published": sum(r["status"] == "published" for r in brecs),
            "backlog": sum(r["status"] == "backlog" for r in brecs),
            "withheld_by_rule": dict(sorted(Counter(w["rule"] for r in brecs for w in r["withheld_reasons"]).items())),
            "lead_values_in": c["lead_values"], "confirmed": c["confirmed"], "changed_by_source": c["changed"],
            "not_found": c["not_found"], "ambiguous_in_source": c["ambiguous"], "not_applicable": c["not_applicable"],
            "source_only_values": c["source_only"], "manuals": info["manuals"],
        }
    rep["conflicts_by_kind"] = dict(sorted(Counter(c["kind"] for c in all_conf).items()))
    rep["fetch_problems"] = {u: e for u, e in sorted(cache.entries.items()) if e.get("status") != 200}
    rng = random.Random(20260927)
    rep["confirmed_sample"] = {b: rng.sample(sorted(v), min(12, len(v))) for b, v in sorted(confirmed_by_brand.items())}
    dump(ROOT / f"out/verified/report-{a.label}.json", rep)
    print(json.dumps({b: {k: v for k, v in x.items() if k != "manuals"} for b, x in rep["brands"].items()}, indent=1))
    print("conflicts:", rep["conflicts_by_kind"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
