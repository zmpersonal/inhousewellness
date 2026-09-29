#!/usr/bin/env python3
"""Round 4 (Discovery): contextual links from blog articles to INH Verified pages. PROPOSE ONLY.

    .venv/bin/python scripts/verified_blog_links.py --articles out/verified/r4/articles.json

Reads published articles (fetched read-only from the Admin API) and proposes, per article:
  * model links: the FIRST eligible mention of a brand + model that resolves to exactly ONE active
    model page gets a link to that page; at most 3 new links per article;
  * a hub link, only for articles that discuss electrical requirements, sizing or comparisons and
    name no model with a page: an existing phrase is linked (no new words) where one exists.

Eligible text is visible body text that is NOT inside a heading, an existing link, a script/style,
or a product/CTA block (an element whose class or id names product, cta, btn, button or shop).
Alt text is an attribute, never text, so it is never touched. No other word changes: a proposal is
the original HTML with one span wrapped in <a href="...">, and `apply_link` refuses anything else.

A mention that could be two pages (a series with variants, e.g. "Dynamic Heming" when both Heming
and Heming Elite have pages) is AMBIGUOUS and is listed for review, never linked.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

HUB = "/pages/sauna-database"
BLOCK_TAGS = {"p", "li", "td", "th", "div", "section", "article", "blockquote", "figcaption", "dd", "dt", "h1", "h2",
              "h3", "h4", "h5", "h6", "table", "ul", "ol", "tr"}
SKIP_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "a", "script", "style", "button", "select", "option", "label"}
CTA_RX = re.compile(r"(?i)product|cta|btn|button|shop")
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
BRAND_ALIASES = {
    "Almost Heaven": ["Almost Heaven"],
    "Clearlight": ["Clearlight"],
    "Dundalk LeisureCraft": ["Dundalk LeisureCraft", "Dundalk Leisurecraft", "Dundalk", "LeisureCraft", "Leisurecraft", "Leisure Craft"],
    "Dynamic Saunas": ["Dynamic Saunas", "Dynamic Sauna", "Dynamic"],
    "Golden Designs": ["Golden Designs"],
    "Maxxus": ["Maxxus"],
    "Redwood Outdoors": ["Redwood Outdoors", "Redwood"],
    "Salus": ["Salus Saunas", "Salus"],
    "Sun Home": ["Sun Home Saunas", "Sun Home"],
}
VARIANT_TOKENS = {"elite": r"Elite", "zf": r"ZF", "fs": r"(?:FS|Full[\s-]+Spectrum)"}
SP = r"(?:\s|&nbsp;|&#160;)+"


def variants_of(text):
    t = text.lower()
    return frozenset(k for k, rx in VARIANT_TOKENS.items() if re.search(r"(?i)\b" + rx + r"\b", t))


def page_index():
    """One entry per ACTIVE model page: brand, series words, variant tokens, model numbers."""
    import verified_pages as vp
    from verified_build import series_name
    ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
    state = json.loads((ROOT / "data/verified/golive/launch-state.json").read_text())
    active = set(state["active_handles"])
    out = []
    for p in (ROOT / "out/verified/pages").glob("*.json"):
        pd = json.loads(p.read_text())
        if pd["handle"] not in active:
            continue
        r = ds[pd["inh_id"]]
        mn = r["identity"]["model_number"]
        out.append({"handle": pd["handle"], "url": f"{HUB}/{pd['handle']}", "title": pd["title"], "brand": pd["brand"],
                    "series": series_name(r["identity"]["model_name"]["value"] or ""),
                    "variants": variants_of(pd["title"]),
                    "model_numbers": [x for x in (mn["value"] or "").split("|") if x] if vp.ok(mn) else []})
    return out


def mention_patterns(pages):
    """(regex, brand, series) per brand alias and series; the match captures up to 3 following words so
    variant tokens (Elite, ZF, Full Spectrum) decide between variants."""
    pats = []
    seen = set()
    for p in pages:
        if not p["series"]:
            continue
        key = (p["brand"], p["series"])
        if key in seen:
            continue
        seen.add(key)
        series_rx = SP.join(re.escape(w) for w in p["series"].split())
        for alias in BRAND_ALIASES[p["brand"]]:
            rx = (r"(?<![\w-])(" + SP.join(re.escape(w) for w in alias.split()) + r"(?:" + SP + r"Saunas?)?" + SP
                  + series_rx + r")(?![\w-])((?:" + SP + r"[A-Za-z][\w-]*){0,3})")
            pats.append((re.compile(rx, re.I), p["brand"], p["series"]))
    for p in pages:
        for mn in p["model_numbers"]:
            for alias in BRAND_ALIASES[p["brand"]]:
                rx = r"(?<![\w-])(" + SP.join(re.escape(w) for w in alias.split()) + SP + re.escape(mn) + r")(?![\w-])()"
                pats.append((re.compile(rx, re.I), p["brand"], "#" + mn))
    return pats


def resolve(pages, brand, series, following):
    """Pages a mention can mean. By model number: exact. By series: pages whose variant tokens equal the
    mention's; when the series has ONE page, a mention whose tokens it carries resolves to it ("Golden
    Designs Toledo" -> the Toledo Full Spectrum page: "Full Spectrum" is part of that product's name).
    A token the page lacks ("Santiago Elite" when only Santiago has a page) never resolves."""
    if series.startswith("#"):
        return [p for p in pages if p["brand"] == brand and series[1:] in p["model_numbers"]]
    v = variants_of(following)
    in_series = [p for p in pages if p["brand"] == brand and p["series"] == series]
    hits = [p for p in in_series if p["variants"] == v]
    if not hits and len(in_series) == 1 and v <= in_series[0]["variants"]:
        hits = in_series
    return hits


def variant_span(following):
    """Length of the leading variant tokens in `following` (so "Gracia FS" is the whole anchor)."""
    m = re.match(r"(?i)((?:" + SP + r"(?:Elite|ZF|FS|Full" + SP + r"Spectrum))+)", following)
    return len(m.group(1)) if m else 0


def tokens(body):
    """(kind, raw, start) for tags and text, with the open-element stack at each text token."""
    stack, out = [], []
    for m in re.finditer(r"<!--.*?-->|<[^>]+>|[^<]+", body, re.S):
        raw = m.group(0)
        if raw.startswith("<!--"):
            continue
        if raw.startswith("</"):
            name = raw[2:].strip(" >").split()[0].lower() if raw[2:].strip(" >") else ""
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == name:
                    del stack[i:]
                    break
            out.append(("close", raw, m.start(), list(stack), name))
        elif raw.startswith("<"):
            nm = re.match(r"<\s*([a-zA-Z0-9]+)", raw)
            name = nm.group(1).lower() if nm else ""
            attrs = " ".join(re.findall(r'(?:class|id)\s*=\s*"([^"]*)"', raw))
            out.append(("open", raw, m.start(), list(stack), name))
            if name and name not in VOID and not raw.endswith("/>"):
                stack.append((name, attrs))
        else:
            out.append(("text", raw, m.start(), list(stack), None))
    return out


def eligible(stack):
    return not any(n in SKIP_TAGS or CTA_RX.search(a or "") for n, a in stack)


def visible(s):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def sentence_around(body, start, end):
    """The visible sentence containing body[start:end], read from its enclosing block element."""
    toks = tokens(body)
    blk_start, blk_end = 0, len(body)
    for kind, raw, pos, stack, name in toks:
        if kind == "open" and name in BLOCK_TAGS and pos <= start:
            blk_start = pos
        if kind == "close" and name in BLOCK_TAGS and pos >= end:
            blk_end = pos
            break
    block = body[blk_start:blk_end]
    marker = "\u0000"
    rel0, rel1 = start - blk_start, end - blk_start
    vis = visible(block[:rel0] + marker + block[rel0:rel1] + marker + block[rel1:])
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", vis)
    for s in parts:
        if marker in s:
            return s
    return vis


def apply_link(body, start, end, url):
    """The ONLY edit: wrap body[start:end] in one link. Everything else byte-identical."""
    return body[:start] + f'<a href="{url}">' + body[start:end] + "</a>" + body[end:]


def model_proposals(article, pages, pats):
    body = article["body"] or ""
    props, ambiguous, done = [], [], set()
    for kind, raw, pos, stack, _ in tokens(body):
        if kind != "text" or not eligible(stack):
            continue
        cands = []
        for rx, brand, series in pats:
            for m in rx.finditer(raw):
                cands.append((m.start(1), m.end(1), m.group(1), m.group(2), brand, series))
        for s0, s1, text, following, brand, series in sorted(cands):
            hits = resolve(pages, brand, series, following)
            key = (brand, series, variants_of(following))
            if key in done:
                continue
            if len(hits) != 1:
                if hits or not series.startswith("#"):
                    ambiguous.append({"mention": visible(text + following)[:80], "candidates": [h["title"] for h in hits]})
                done.add(key)
                continue
            target = hits[0]
            if any(p["target"] == target["url"] for p in props):
                done.add(key)
                continue
            start, end = pos + s0, pos + s1 + variant_span(following)
            before = sentence_around(body, start, end)
            if CITATION_RX.search(before):
                continue      # a reference-list entry (it carries a URL); try the next mention
            text = body[start:end]
            siblings = [p for p in pages if p["brand"] == brand and p["series"] == series and p is not target]
            after_body = apply_link(body, start, end, target["url"])
            props.append({"kind": "model", "start": start, "end": end, "anchor": visible(text), "target": target["url"],
                          "target_title": target["title"],
                          "sentence_before": before.replace("\u0000", ""),
                          "sentence_after": re.sub("\u0000(.*?)\u0000", lambda mm: f"[{mm.group(1)}]({target['url']})", before),
                          "note": (f"other pages in this series: {[x['title'] for x in siblings]}; the mention names no variant, "
                                   "so it resolves to the one whose name carries none" if siblings else None)})
            done.add(key)
            if len(props) == 3:
                return props, ambiguous
    return props, ambiguous


TOPIC_RX = {
    "electrical": re.compile(r"(?i)\b(?:electrical requirements?|240\s?V|120\s?V|dedicated circuit|breaker|amps?\b|wiring|electrician)"),
    "sizing": re.compile(r"(?i)\b(?:dimensions|footprint|how much space|sizing|ceiling height|person capacity|\d-person)"),
    "comparison": re.compile(r"(?i)\b(?:vs\.?|versus|compare[ds]?|comparison)\b"),
}
# Only a phrase that names what the hub holds. "specifications" alone was rejected in review: in a
# Finnmark review it would read as if the database covered Finnmark.
ANCHOR_PHRASES = ["electrical requirements", "electrical requirement"]


CITATION_RX = re.compile(r"https?://|www\.")


def hub_proposal(article, pages, pats):
    """Only a SAUNA article (the sauna blog, or 'sauna' at least 8 times) that names NO model with a page
    and discusses electrical requirements, sizing or comparisons (a topic word at least 3 times)."""
    body = article["body"] or ""
    text = visible(body)
    if article["blog"]["handle"] == "institute":
        return None          # the Wellness Institute blog is noindexed by client ruling (layout, Round 8)
    if article["blog"]["handle"] not in ("saunas", "news") and len(re.findall(r"(?i)\bsaunas?\b", text)) < 8:
        return None
    if any(rx.search(text) for rx, _, _ in pats):
        return None
    topics = [k for k, rx in TOPIC_RX.items() if len(rx.findall(text)) >= 3]
    if not ({"electrical", "sizing"} & set(topics)):
        return None          # "comparison" alone (a research article comparing studies) is not a fit
    for phrase in ANCHOR_PHRASES:
        rx = re.compile(r"(?<![\w-])(" + SP.join(re.escape(w) for w in phrase.split()) + r")(?![\w-])", re.I)
        for kind, raw, pos, stack, _ in tokens(body):
            if kind != "text" or not eligible(stack):
                continue
            if any(n in ("strong", "b") for n, _ in stack):
                continue      # a bold run-in label reads as a heading
            m = rx.search(raw)
            if m:
                start, end = pos + m.start(1), pos + m.end(1)
                before = sentence_around(body, start, end)
                if CITATION_RX.search(before):
                    continue
                return {"kind": "hub", "topics": topics, "start": start, "end": end, "anchor": visible(m.group(1)),
                        "target": HUB, "target_title": "Verified Sauna Database",
                        "sentence_before": before.replace("\u0000", ""),
                        "sentence_after": re.sub("\u0000(.*?)\u0000", lambda mm: f"[{mm.group(1)}]({HUB})", before),
                        "new_words": False}
    return {"kind": "hub", "topics": topics, "start": None, "end": None, "anchor": None, "target": HUB,
            "target_title": "Verified Sauna Database", "new_words": True,
            "sentence_before": None,
            "sentence_after": "Electrical requirements and exterior sizes for specific models, each cited to the "
                              f"manufacturer, are in the [Verified Sauna Database]({HUB}).",
            "note": "no existing phrase to link; this adds ONE new sentence at the end of the article body"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--articles", default=str(ROOT / "out/verified/r4/articles.json"))
    ap.add_argument("--out", default=str(ROOT / "docs/verified/r4"))
    a = ap.parse_args(argv)
    from src.health_claims import find_banned_claims
    arts = json.loads(Path(a.articles).read_text())
    pages = page_index()
    pats = mention_patterns(pages)
    rows, hub_rows, amb_rows = [], [], []
    for art in sorted(arts, key=lambda x: (x["blog"]["handle"], x["handle"])):
        url = f"https://inhousewellness.com/blogs/{art['blog']['handle']}/{art['handle']}"
        props, amb = model_proposals(art, pages, pats)
        for p in props:
            rows.append(dict(p, article=url, article_id=art["id"]))
        for x in amb:
            amb_rows.append(dict(x, article=url))
        if not props:
            h = hub_proposal(art, pages, pats)
            if h:
                if h["new_words"] and find_banned_claims(h["sentence_after"]):
                    h["health_gate"] = "FAILED"
                hub_rows.append(dict(h, article=url, article_id=art["id"]))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "blog-link-proposals.json").write_text(json.dumps({"model_links": rows, "hub_links": hub_rows,
                                                               "ambiguous": amb_rows}, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(arts)} articles; {len(rows)} model links in {len({r['article'] for r in rows})} articles; "
          f"{len(hub_rows)} hub-link candidates ({sum(1 for h in hub_rows if not h['new_words'])} link an existing phrase); "
          f"{len(amb_rows)} ambiguous mentions not linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
