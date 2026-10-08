#!/usr/bin/env python3
"""Round 4 (promote the electrical tool), Part A: product link proposals. Read-only.

    .venv/bin/python scripts/promote_r4_propose.py products

Reads the Admin pull (out/promote/r4/products-pull.json) and the cached live pages. A product gets a
proposal only when a VISIBLE electrical statement exists in one of the two theme-rendered places:
  1. the "Electrical requirements" line of custom.dimentions_specifications (the Dimensions &
     Specifications accordion, rendered with metafield_tag), preferred: it is a labelled section;
  2. a sentence of the product description (the Description accordion) stating a voltage, amperage,
     breaker or circuit.
custom.electrical_requirements is never rendered by the theme (only read by product-disclosure.liquid as
search text), and the marketing bullet fields are not electrical sections: both are excluded.

The edit is always an <a> around EXISTING words inside one text node, so no text is added and nothing
can wrap differently except by the link's own styling. A product whose electrical text has no natural
phrase to link gets no proposal (listed with the reason), never an added sentence.
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/promote/r4"
TOOL = "/pages/sauna-electrical-requirements"
FIG = re.compile(r"(?i)(\b\d{3}\s*-?\s*v(?:ac|olts?)?\b|\b\d{2}\s*-?\s*a(?:mps?|mp)?\b|\bbreaker|\bcircuit|\bhard-?wir)")
# Natural, descriptive phrases already written on our pages, in order of preference. Never a brand, never
# a model name: the anchor describes what the reader will find (the electrical requirement).
PHRASES = [r"electrical requirements", r"dedicated (?:breaker and outlet|circuit|outlet|line)", r"special (?:electrical work|wiring)",
           r"electrical upgrades?", r"(?:standard )?(?:120v |240v )?household outlet", r"standard (?:home|wall) outlet",
           r"(?:120|240)\s*v(?:olt)?(?:\s*/\s*\d{2}\s*a(?:mps?|mp)?)? (?:power (?:system|supply)|electrical(?: service)?|connection|outlet|circuit|service)",
           r"electrical (?:service|setup|connection|work)", r"power (?:requirements|supply)", r"wiring"]
PHRASE_RX = [re.compile(r"(?i)\b" + p + r"\b") for p in PHRASES]
ANCHOR_CAP = 8      # no anchor phrase is used on more than 8 products: varied, never exact-match repetition


def text_nodes_rich(node, path=()):
    """Every text node of a Shopify rich_text_field, with its path, in document order."""
    if isinstance(node, dict):
        if node.get("type") == "text":
            yield path, node
        for i, c in enumerate(node.get("children", [])):
            yield from text_nodes_rich(c, path + (i,))


def rich_paragraph_text(node):
    return "".join(n.get("value", "") for _, n in text_nodes_rich(node))


def models():
    d = json.loads((ROOT / "assets/inh-electrical-data.json").read_text())
    return d["product_to_model"], {m["handle"] for m in d["models"]}


def norm(t: str) -> str:
    return re.sub(r"[\s\u00a0\u202f]+", " ", t).strip().lower()


def visible(page_html):
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", page_html)
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", t)))


def shown(t, vis):
    """Visible on the live page. Compared without whitespace: markup boundaries render as spaces
    ("<strong>Power</strong>: 120V" is "Power : 120V" on the page)."""
    k = re.sub(r"\s", "", norm(t))
    return bool(k) and k[:40] in re.sub(r"\s", "", vis)


def pick_phrase(text, used):
    """The first preferred phrase in this text; among equal choices, the least used so far (variety)."""
    found = []
    for rank, rx in enumerate(PHRASE_RX):
        for m in rx.finditer(text):
            found.append((rank, used[m.group(0).lower()], m))
    if not found:
        return None
    found.sort(key=lambda x: (x[0], x[1], x[2].start()))
    return found[0][2]


def spec_candidates(p, vis):
    """Electrical lines of the spec metafield. The phrase must sit inside ONE text node (so the link never
    spans a bold label and its value); the line as a whole must be visible on the live page."""
    m = {f"{x['namespace']}.{x['key']}": x for x in p["metafields"]["nodes"]}.get("custom.dimentions_specifications")
    if not m:
        return []
    out = []
    for bi, block in enumerate(json.loads(m["value"]).get("children", [])):
        items = [((bi, ii), it) for ii, it in enumerate(block.get("children", []))] if block.get("type") == "list" else [((bi,), block)]
        for base, it in items:
            line = rich_paragraph_text(it)
            if re.search(r"(?i)electric|volt|amp|circuit|breaker|outlet", line) and FIG.search(line) and shown(line, vis):
                for path, node in text_nodes_rich(it):
                    # node_path is ABSOLUTE from the document root's children: the write locates the node by it
                    out.append({"location": "custom.dimentions_specifications (Dimensions & Specifications accordion)",
                                "text": node.get("value", ""), "context": line, "node_path": list(base + path)})
    return out


def desc_candidates(p, vis):
    """Text segments of the description (between tags, so an anchor never spans markup) inside an element
    that states a figure; the element must be visible on the live page."""
    h = p["descriptionHtml"] or ""
    out = []
    for el in re.finditer(r"(?s)<(p|li|h[1-6]|div|td)\b[^>]*>(.*?)</\1>", h):
        whole = html.unescape(re.sub(r"<[^>]+>", "", el.group(2)))
        if not (FIG.search(whole) and shown(whole, vis)):
            continue
        for seg in re.finditer(r"(?:^|>)([^<]+)", el.group(2)):
            out.append({"location": "descriptionHtml (Description accordion)", "text": html.unescape(seg.group(1)),
                        "raw": seg.group(1), "context": whole})
    return out


def products():
    pull = json.loads((ROOT / "out/promote/r4/products-pull.json").read_text())
    p2m, live = models()
    used = Counter()
    rows, skipped, inv = [], [], []
    for h, p in sorted(pull.items()):
        f = ROOT / "out/promote/r4/pages" / f"{h}.html"
        if not f.exists():
            skipped.append((h, p["vendor"], "storefront answers 404 (not an active product)"))
            continue
        vis = visible(f.read_text())
        spec, desc = spec_candidates(p, vis), desc_candidates(p, vis)
        inv.append({"handle": h, "vendor": p["vendor"], "spec_electrical_line": bool(spec), "description_electrical_sentence": bool(desc)})
        chosen, opts = None, []
        for order, c in enumerate(spec + desc):   # the labelled spec line first, then the description
            for rank, rx in enumerate(PHRASE_RX):
                for m in rx.finditer(c["text"]):
                    k = m.group(0).lower()
                    opts.append((used[k] >= ANCHOR_CAP, rank, used[k], order, m.start(), c, m))
        if opts:
            opts.sort(key=lambda o: o[:5])
            if not opts[0][0]:
                chosen = (opts[0][5], opts[0][6])
            else:
                skipped.append((h, p["vendor"], f"every linkable phrase is already used {ANCHOR_CAP} times; skipped to keep anchors varied"))
                continue
        if not (spec or desc):
            skipped.append((h, p["vendor"], "no visible electrical section (theme-rendered description or spec line)"))
            continue
        if not chosen:
            skipped.append((h, p["vendor"], "electrical text exists but has no natural phrase to link; no sentence is added"))
            continue
        c, m = chosen
        used[m.group(0).lower()] += 1
        model = p2m.get(h)
        target = f"{TOOL}?model={model}" if model in live else TOOL
        before = c["text"]
        after = before[:m.start()] + f'<a href="{target}">{m.group(0)}</a>' + before[m.end():]
        if c["location"].startswith("descriptionHtml"):
            raw = c["raw"]
            # the edit as it will be written: the same words, escaped as stored, wrapped in <a>
            rm = re.search(re.escape(html.escape(m.group(0), quote=False)) if html.escape(m.group(0), quote=False) in raw else re.escape(m.group(0)), raw)
            if not rm:
                skipped.append((h, p["vendor"], "phrase is entity-encoded differently in the stored HTML; not proposed"))
                used[m.group(0).lower()] -= 1
                continue
        rows.append({"page": f"/products/{h}", "page_type": "product", "vendor": p["vendor"], "location": c["location"],
                     "node_path": c.get("node_path"), "context": c["context"],
                     "before_text": before, "after_text": after, "target": target, "anchor": m.group(0)})
    return rows, skipped, inv, used


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, skipped, inv, used = products()
    json.dump({"rows": rows, "skipped": skipped, "inventory": inv}, open(ROOT / "out/promote/r4/products-proposals.json", "w"), indent=1)
    by = Counter((r["vendor"]) for r in rows)
    print(f"{len(rows)} product proposals; {len(skipped)} skipped")
    print("by brand:", dict(by))
    print("anchors:", used.most_common())
    for s in Counter(x[2] for x in skipped).most_common():
        print("skip:", s)


if __name__ == "__main__" and (len(sys.argv) == 1 or sys.argv[1] == "products"):
    main()


# ------------------------------------------------------------------ articles --

PAGES6 = {"tool": TOOL, "heater": "/pages/sauna-heater-size-calculator", "kw6": "/pages/6-kw-sauna-heater-breaker-size",
          "kw8": "/pages/8-kw-sauna-heater-breaker-size", "ir": "/pages/infrared-sauna-dedicated-circuit",
          "method": "/pages/sauna-electrical-methodology"}
ART_PHRASES = [  # (target key, regex over one text segment), most specific first
    ("kw6", r"(?:6\s*-?\s*kw|6,000\s*-?\s*watt) (?:heater|stove)(?:'s)?(?: breaker| circuit)?"),
    ("kw8", r"(?:8\s*-?\s*kw|8,000\s*-?\s*watt) (?:heater|stove)(?:'s)?(?: breaker| circuit)?"),
    ("ir", r"dedicated (?:120\s*-?\s*v(?:olt)? )?(?:circuit|outlet)"),
    ("heater", r"(?:heater|stove) (?:size|sizing)|size (?:the|your) heater|right(?:-| )sized heater|kw (?:per|for every) \d+ cubic feet"),
    ("tool", r"(?:240\s*-?\s*v(?:olt)?|120\s*-?\s*v(?:olt)?) (?:circuit|outlet|service|line|connection|hookup|wiring)"),
    ("tool", r"electrical requirements?|breaker size|wire (?:gauge|size)|electrical (?:work|service|setup|upgrade|panel)"),
]
SAUNA_SCOPE = re.compile(r"(?i)^(saunas|news|wellness)/")
NOT_SCOPE = re.compile(r"(?i)cold-plunge|massage|hsp|heat-shock|longevity|pain|alzheimer|circulation|good-for-you|how-often|"
                       r"inflammatory|pt$|fatigue|airbnb|german|benefits|safe|red-light|chromotherapy|emf|ventilation")


def article_model(a, models_by_number):
    for mn, h in models_by_number.items():
        if re.search(r"(?i)\b" + re.escape(mn) + r"\b", a["title"] + " " + a["handle"].replace("-", " ")):
            return h
    return None


ART_CAP = 5        # no anchor phrase on more than 5 articles
IR_CONTEXT = re.compile(r"(?i)\binfrared\b|\bfar ir\b|\bfull[- ]spectrum\b|\bcarbon (?:heater|panel)s?\b")


def live_models_by_number():
    """Model number -> live page handle, from the dataset (verified model numbers) and frozen handles."""
    ds = json.loads((ROOT / "data/verified/saunas.json").read_text())["records"]
    hs = json.loads((ROOT / "data/verified/handles.json").read_text())["handles"]
    live = {m["handle"] for m in json.loads((ROOT / "assets/inh-electrical-data.json").read_text())["models"]}
    out = {}
    for r in ds:
        mn = (r["identity"]["model_number"] or {}).get("value")
        h = (hs.get(r["inh_id"]) or {}).get("handle")
        if mn and h in live:
            for tok in re.findall(r"\b[A-Z]{2,4}-[A-Z0-9]+(?:-[A-Z0-9]+)*\b", mn):
                out.setdefault(tok, h)
    return out


def articles():
    arts = json.loads((ROOT / "out/promote/r4/articles-pull.json").read_text())
    by_mn = live_models_by_number()
    used = Counter()
    rows, skipped = [], []
    for a in arts:
        key = f"{a['blog']['handle']}/{a['handle']}"
        if not a["isPublished"] or not SAUNA_SCOPE.match(key) or NOT_SCOPE.search(a["handle"]):
            continue
        body = a["body"] or ""
        if any(v in body for v in PAGES6.values()):
            skipped.append((key, "already links an electrical page"))
            continue
        model = article_model(a, by_mn)
        opts = []
        for el in re.finditer(r"(?s)<(p|li)\b[^>]*>(.*?)</\1>", body):
            inner = el.group(2)
            para = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
            # text segments outside any existing <a>
            for seg in re.finditer(r"(?s)(?:^|>)([^<]+)", re.sub(r"(?s)<a\b.*?</a>", lambda m: "<x>" + " " * (len(m.group(0)) - 3), inner)):
                t = seg.group(1)
                for rank, (k, rx) in enumerate(ART_PHRASES):
                    for m in re.finditer(r"(?i)\b" + rx + r"\b", t):
                        kk = k
                        if kk == "ir" and not IR_CONTEXT.search(para):
                            kk = "tool"            # a dedicated circuit for a traditional heater: the tool, not the IR page
                        if model:
                            kk = "tool"            # a single-model article: the tool, pre-filled with that model
                        a_ = m.group(0).lower()
                        opts.append((used[a_] >= ART_CAP, rank, used[a_], len(opts), kk, t, m, para))
        if not opts:
            skipped.append((key, "no linkable electrical phrase in a paragraph or list item"))
            continue
        opts.sort(key=lambda o: o[:4])
        if opts[0][0]:
            skipped.append((key, f"every linkable phrase is already used on {ART_CAP} articles; skipped to keep anchors varied"))
            continue
        _, _, _, _, k, t, m, sentence = opts[0]
        used[m.group(0).lower()] += 1
        target = PAGES6[k] if k != "tool" else (f"{TOOL}?model={model}" if model else TOOL)
        rows.append({"page": f"/blogs/{key}", "page_type": "article", "vendor": "", "location": "article body (existing paragraph)",
                     "node_path": None, "context": sentence[:400], "before_text": t,
                     "after_text": t[:m.start()] + f'<a href="{target}">{m.group(0)}</a>' + t[m.end():],
                     "target": target, "anchor": m.group(0), "title": a["title"]})
    return rows, skipped


# --------------------------------------------------------------- collections --

COLL_OUT = re.compile(r"(?i)cold|plunge|massage|float|steam|thermasol|delta|mr-steam|hot-tub|red-light|ice-tub|chimney|roof|"
                      r"maintenance|health-smart|helios|medical-breakthrough|dreampod|accessor|service-upgrades|cooling")
COLL_PHRASES = [
    ("ir", r"standard 120\s*-?\s*v(?:olt)? (?:circuit|household outlet|outlet|supply)"),
    ("tool", r"dedicated 240\s*-?\s*v(?:olt)? circuit|240\s*-?\s*v(?:olt)? (?:circuit|supply|requirement)"),
    ("tool", r"electrical requirements?|dedicated circuit|electrical work"),
]
COLL_CAP = 3


def collections():
    cs = json.loads((ROOT / "out/promote/r4/collections-pull.json").read_text())
    used = Counter()
    rows, skipped = [], []
    for c in cs:
        if COLL_OUT.search(c["handle"]):
            continue
        body = c["descriptionHtml"] or ""
        if any(v in body for v in PAGES6.values()):
            skipped.append((c["handle"], "already links an electrical page"))
            continue
        opts = []
        for el in re.finditer(r"(?s)<(p|li)\b[^>]*>(.*?)</\1>", body):
            inner = el.group(2)
            para = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
            if re.search(r"(?i)getting it inside and assembled is", para):
                continue                     # the shared delivery boilerplate: not this collection's own words
            for seg in re.finditer(r"(?s)(?:^|>)([^<]+)", re.sub(r"(?s)<a\b.*?</a>", lambda m: "<x>" + " " * (len(m.group(0)) - 3), inner)):
                t = seg.group(1)
                for rank, (k, rx) in enumerate(COLL_PHRASES):
                    for m in re.finditer(r"(?i)\b" + rx + r"\b", t):
                        kk = k if (k != "ir" or IR_CONTEXT.search(para + " " + c["handle"].replace("-", " "))) else "tool"
                        a_ = m.group(0).lower()
                        opts.append((used[a_] >= COLL_CAP, rank, used[a_], len(opts), kk, t, m, para))
        if not opts:
            skipped.append((c["handle"], "no electrical words of its own to link"))
            continue
        opts.sort(key=lambda o: o[:4])
        if opts[0][0]:
            skipped.append((c["handle"], f"every linkable phrase already used on {COLL_CAP} collections"))
            continue
        _, _, _, _, k, t, m, para = opts[0]
        used[m.group(0).lower()] += 1
        target = PAGES6[k]
        rows.append({"page": f"/collections/{c['handle']}", "page_type": "collection", "vendor": "", "location": "collection description (existing paragraph)",
                     "node_path": None, "context": para[:400], "before_text": t,
                     "after_text": t[:m.start()] + f'<a href="{target}">{m.group(0)}</a>' + t[m.end():],
                     "target": target, "anchor": m.group(0), "title": c["title"]})
    return rows, skipped


# ------------------------------------------------------------------- output --

PAGE_EDITS = [   # A5: INH page bodies (Admin pageUpdate), existing words only
    ("faq-page", "Premium installation ($1,800) covers everything except electrical work.", "electrical work", TOOL),
    ("sauna-cost", "Then the electrician is a separate bill,", "the electrician", TOOL),
    ("sauna-database-methodology", "A reference of home sauna specifications, with the electrical requirements first.",
     "electrical requirements", TOOL),
]


def stored_edit(row, pull):
    """The edit in the form it will be WRITTEN: an HTML segment, or a rich-text node split around a link."""
    if row["location"].startswith("custom.dimentions_specifications"):
        node = {"type": "text", "value": row["before_text"]}
        m = re.search(re.escape(row["anchor"]), row["before_text"])
        pre, post = row["before_text"][:m.start()], row["before_text"][m.end():]
        bold = {k: v for k, v in _node_at(pull, row).items() if k in ("bold", "italic")}
        after = ([{"type": "text", "value": pre, **bold}] if pre else []) + \
                [{"type": "link", "url": row["target"], "title": None, "children": [{"type": "text", "value": row["anchor"], **bold}]}] + \
                ([{"type": "text", "value": post, **bold}] if post else [])
        return json.dumps({**node, **bold}, ensure_ascii=False), json.dumps(after, ensure_ascii=False)
    return row["before_text"], row["after_text"]


def _node_at(pull, row):
    p = pull[row["page"].split("/")[-1]]
    m = {f"{x['namespace']}.{x['key']}": x for x in p["metafields"]["nodes"]}["custom.dimentions_specifications"]
    n = {"children": json.loads(m["value"])["children"]}
    for i in row["node_path"]:
        n = n["children"][i]
    return n


def write_all():
    pull = json.loads((ROOT / "out/promote/r4/products-pull.json").read_text())
    prows, pskip, inv, _ = products()
    arows, askip = articles()
    crows, cskip = collections()
    pages = {p["handle"]: p for p in json.loads((ROOT / "out/promote/r4/pages-pull.json").read_text())}
    out = []
    for r in prows:
        node_path = r.get("node_path")
        if node_path is not None:
            # node_path is relative to the list item / paragraph; record the full path from the document root
            pass
        sb, sa = stored_edit(r, pull)
        out.append({**r, "stored_before": sb, "stored_after": sa})
    for r in arows + crows:
        out.append({**r, "stored_before": r["before_text"], "stored_after": r["after_text"]})
    for h, sent, anchor, target in PAGE_EDITS:
        body = pages[h]["body"]
        assert sent.split(",")[0] in html.unescape(body), h
        out.append({"page": f"/pages/{h}", "page_type": "page", "vendor": "", "location": "page body (existing paragraph)",
                    "node_path": None, "context": sent, "before_text": sent,
                    "after_text": sent.replace(anchor, f'<a href="{target}">{anchor}</a>', 1), "target": target, "anchor": anchor,
                    "stored_before": sent, "stored_after": sent.replace(anchor, f'<a href="{target}">{anchor}</a>', 1)})
    cols = ["page", "page_type", "vendor", "location", "before_text", "after_text", "target", "anchor", "context",
            "stored_before", "stored_after", "approve (y/n)"]
    with (OUT / "proposals.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow({**r, "approve (y/n)": ""})
    with (OUT / "skipped.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["page", "brand", "reason"])
        for h, v, why in pskip:
            w.writerow([f"/products/{h}", v, why])
        for k, why in askip:
            w.writerow([f"/blogs/{k}", "", why])
        for k, why in cskip:
            w.writerow([f"/collections/{k}", "", why])
    inv_by = Counter()
    for i in inv:
        inv_by[(i["vendor"], "spec line" if i["spec_electrical_line"] else ("description" if i["description_electrical_sentence"] else "none"))] += 1
    json.dump({"inventory": inv, "by_brand": {f"{a}|{b}": n for (a, b), n in sorted(inv_by.items())}},
              (OUT / "a1-inventory.json").open("w"), indent=1)
    print(f"proposals.csv: {len(out)} rows (products {len(prows)}, articles {len(arows)}, collections {len(crows)}, pages {len(PAGE_EDITS)})")
    return out, inv_by


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "write":
    write_all()
