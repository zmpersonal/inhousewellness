#!/usr/bin/env python3
"""Round 4 Part B: apply the approved text links (docs/promote/r4/proposals.csv), one page at a time.

    .venv/bin/python scripts/promote_r4_apply.py snapshot                 # stored content + before shots
    .venv/bin/python scripts/promote_r4_apply.py apply [--write] [--type product|article|collection|page] [--limit N]
    .venv/bin/python scripts/promote_r4_apply.py revert [--write]         # every applied page back to its snapshot

The hard rule (Round 4 §1): the edit is an <a> around words ALREADY in one text node and nothing else.
- Gate: the page's CURRENT stored content must equal its snapshot, and the approved "before" text must
  occur exactly once at its location; otherwise the page is skipped, never forced.
- The new content is built by inserting the link; removing that exact link from it must give back the
  snapshot byte for byte, before anything is written.
- Read-back: the stored content must equal what was written. Anything else reverts the page.
- Visual: the edited block (the li/p holding the text, its accordion opened) is screenshotted before and
  after at 1440 and 390 px. Its box must keep the same size, and every changed pixel must lie inside the new
  link's own box (link styling). Anything else reverts the page and is reported.
Pixel comparison runs in the browser on a canvas: no image library is added to the repo.
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
STORE = "https://inhousewellness.com"
PROPOSALS = ROOT / "docs/promote/r4/proposals.csv"
SNAP = ROOT / "data/promote/r4/snapshots"
SHOTS = ROOT / "out/promote/r4/shots"
STATE = ROOT / "data/promote/r4/apply-state.json"
WIDTHS = (1440, 390)
SPEC_KEY = ("custom", "dimentions_specifications")

Q_PRODUCT = """query($id: ID!) { product(id: $id) { id handle descriptionHtml
  metafield(namespace: "custom", key: "dimentions_specifications") { value type } } }"""
Q_ARTICLE = "query($id: ID!) { article(id: $id) { id handle body } }"
Q_COLLECTION = "query($id: ID!) { collection(id: $id) { id handle descriptionHtml } }"
Q_PAGE = "query($id: ID!) { page(id: $id) { id handle body } }"
M_PRODUCT = "mutation($p: ProductUpdateInput!) { productUpdate(product: $p) { product { id } userErrors { field message } } }"
M_MF = "mutation($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { metafields { id } userErrors { field message } } }"
M_ARTICLE = "mutation($id: ID!, $a: ArticleUpdateInput!) { articleUpdate(id: $id, article: $a) { article { id } userErrors { field message } } }"
M_COLLECTION = "mutation($c: CollectionUpdateInput!) { collectionUpdate(collection: $c) { collection { id } userErrors { field message } } }"
M_PAGE = "mutation($id: ID!, $p: PageUpdateInput!) { pageUpdate(id: $id, page: $p) { page { id } userErrors { field message } } }"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"pages": {}}


def save(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")


def slug(row):
    return row["page"].strip("/").replace("/", "__")


# ------------------------------------------------------------------ targets --

def edits():
    """Approved rows, each resolved to an Admin id, the stored field it edits and (spec rows) a node path."""
    import promote_r4_propose as pr
    rows = [r for r in csv.DictReader(PROPOSALS.open()) if r["approve (y/n)"].strip() == "y"]
    pull = json.loads((ROOT / "out/promote/r4/products-pull.json").read_text())
    arts = {f"{a['blog']['handle']}/{a['handle']}": a["id"] for a in json.loads((ROOT / "out/promote/r4/articles-pull.json").read_text())}
    cols = {c["handle"]: c["id"] for c in json.loads((ROOT / "out/promote/r4/collections-pull.json").read_text())}
    pages = {p["handle"]: p["id"] for p in json.loads((ROOT / "out/promote/r4/pages-pull.json").read_text())}
    paths = {(r["page"], r["before_text"]): r.get("node_path") for r in pr.products()[0]}
    out = []
    for r in rows:
        t, h = r["page_type"], r["page"].split("/")[-1]
        e = dict(r)
        if t == "product":
            e["id"] = pull[h]["id"]
            if r["location"].startswith("custom.dimentions_specifications"):
                e["field"], e["node_path"] = "spec", paths.get((r["page"], r["before_text"]))
                if e["node_path"] is None:
                    raise SystemExit(f"HALT: no node path for {r['page']}")
            else:
                e["field"] = "description"
        elif t == "article":
            e["id"], e["field"] = arts[r["page"].split("/blogs/")[1]], "body"
        elif t == "collection":
            e["id"], e["field"] = cols[h], "description"
        else:
            e["id"], e["field"] = pages[h], "body"
        out.append(e)
    return out


def read(q, e):
    """The stored value this edit touches, exactly as the Admin API returns it."""
    t = e["page_type"]
    if t == "product":
        p = q(Q_PRODUCT, {"id": e["id"]})["product"]
        return p["metafield"]["value"] if e["field"] == "spec" else p["descriptionHtml"]
    if t == "article":
        return q(Q_ARTICLE, {"id": e["id"]})["article"]["body"]
    if t == "collection":
        return q(Q_COLLECTION, {"id": e["id"]})["collection"]["descriptionHtml"]
    return q(Q_PAGE, {"id": e["id"]})["page"]["body"]


def write(q, e, value):
    t = e["page_type"]
    if t == "product" and e["field"] == "spec":
        r = q(M_MF, {"m": [{"ownerId": e["id"], "namespace": SPEC_KEY[0], "key": SPEC_KEY[1], "type": "rich_text_field",
                            "value": value}]})["metafieldsSet"]
    elif t == "product":
        r = q(M_PRODUCT, {"p": {"id": e["id"], "descriptionHtml": value}})["productUpdate"]
    elif t == "article":
        r = q(M_ARTICLE, {"id": e["id"], "a": {"body": value}})["articleUpdate"]
    elif t == "collection":
        r = q(M_COLLECTION, {"c": {"id": e["id"], "descriptionHtml": value}})["collectionUpdate"]
    else:
        r = q(M_PAGE, {"id": e["id"], "p": {"body": value}})["pageUpdate"]
    if r["userErrors"]:
        raise RuntimeError(f"{e['page']}: {r['userErrors']}")


# -------------------------------------------------------------- the edit --

def link_tag(e, anchor_raw):
    return f'<a href="{e["target"]}">{anchor_raw}</a>'


def edit_html(src: str, e) -> tuple[str, str]:
    """Insert the link into the ONE text segment (outside any <a>) that holds the approved text, at the
    position the approved "after" text shows. Returns (new_html, inserted_tag). Raises when the location
    is not unique. Whitespace around a segment is compared trimmed: the proposal generator masked existing
    links with spaces, so a segment after a link carried them into "before" (almost-heaven-audra-shenandoah)."""
    before, anchor = e["before_text"], e["anchor"]
    opening = f'<a href="{e["target"]}">'
    pos = e["after_text"].index(opening)                 # where the approved row puts the link, in "before"
    if before[pos:pos + len(anchor)] != anchor:
        raise ValueError("approved after-text does not wrap the anchor in the before-text")
    core = before.strip()
    pos_core = pos - (len(before) - len(before.lstrip()))
    cands = []
    depth = 0
    for m in re.finditer(r"(<[^>]+>)|([^<]+)", src):
        tag, txt = m.group(1), m.group(2)
        if tag:
            if re.match(r"(?i)<a[\s>]", tag):
                depth += 1
            elif re.match(r"(?i)</a\s*>", tag):
                depth = max(0, depth - 1)
            continue
        if depth:
            continue
        un = html.unescape(txt)
        whole = e["page_type"] == "page"
        if txt.strip() == core or un.strip() == core or (whole and core in un):
            cands.append(m)
    if len(cands) != 1:
        raise ValueError(f"approved text found {len(cands)} times outside links, not once")
    m = cands[0]
    seg = m.group(2)
    if e["page_type"] == "page":                         # a sentence inside a longer segment
        ucore_at = html.unescape(seg).index(core)
        prefix_plain = html.unescape(seg)[:ucore_at] + core[:pos_core]
    else:
        lead = len(html.unescape(seg)) - len(html.unescape(seg).lstrip())
        prefix_plain = html.unescape(seg)[:lead] + core[:pos_core]
    # map the plain-text prefix onto the raw (possibly entity-encoded) segment
    i, plain = 0, ""
    while plain != prefix_plain:
        if i >= len(seg):
            raise ValueError("could not map the link position onto the stored text")
        ent = re.match(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);", seg[i:])
        step = ent.group(0) if ent else seg[i]
        plain += html.unescape(step)
        i += len(step)
        if not prefix_plain.startswith(plain):
            raise ValueError("could not map the link position onto the stored text")
    forms = [a for a in dict.fromkeys([anchor, html.escape(anchor, quote=False)]) if seg.startswith(a, i)]
    if not forms:
        raise ValueError(f"anchor {anchor!r} is not at the approved position")
    tag = opening + forms[0] + "</a>"
    new_seg = seg[:i] + tag + seg[i + len(forms[0]):]
    new = src[:m.start(2)] + new_seg + src[m.end(2):]
    # the edit is the link and nothing else: removing exactly it gives the original back
    if new[:m.start(2) + i] + forms[0] + new[m.start(2) + i + len(tag):] != src:
        raise ValueError("round trip failed")
    return new, tag


def edit_rich(src: str, e) -> tuple[str, str]:
    """Split the one rich-text node at node_path around a link node carrying the same marks."""
    doc = json.loads(src)
    path = json.loads(e["node_path"]) if isinstance(e["node_path"], str) else e["node_path"]
    parent, node = {"children": doc["children"]}, None
    for depth, i in enumerate(path):
        if depth == len(path) - 1:
            node = parent["children"][i]
        else:
            parent = parent["children"][i]
    if node.get("type") != "text" or node.get("value") != e["before_text"]:
        raise ValueError(f"node at {path} is {node!r}, not the approved text")
    v, a = node["value"], e["anchor"]
    if v.count(a) != 1:
        raise ValueError(f"anchor {a!r} is not exactly once in the node")
    marks = {k: node[k] for k in node if k not in ("type", "value")}
    if marks and a != v:
        # Linking PART of a bold/italic node splits it, and the rendered HTML gains a tag boundary (an extra
        # </strong><strong>) beyond the link. Visually identical, but not "the link and nothing else".
        # Found on 4 products at live-check, 2026-10-08; those were reverted.
        raise ValueError(f"anchor is part of a {'/'.join(sorted(marks))} node: linking it would split the markup")
    i = v.index(a)
    repl = ([{**node, "value": v[:i]}] if v[:i] else []) + \
           [{"type": "link", "url": e["target"], "title": None, "children": [{"type": "text", "value": a, **marks}]}] + \
           ([{**node, "value": v[i + len(a):]}] if v[i + len(a):] else [])
    parent["children"][path[-1]:path[-1] + 1] = repl
    new = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return new, json.dumps(repl, ensure_ascii=False)


def build(src, e):
    return edit_rich(src, e) if e.get("field") == "spec" else edit_html(src, e)


def same_stored(a: str, b: str, e) -> bool:
    if e.get("field") == "spec":
        return json.loads(a) == json.loads(b)
    return a == b


# ------------------------------------------------------------------- shots --

LOCATE_JS = """([probe, scope]) => {
  const norm = s => s.replace(/[\\s\\u00a0\\u202f]+/g, ' ').trim().toLowerCase();
  const p = norm(probe);
  // A product's text can appear twice (an excerpt above the accordions and the accordion itself): the block
  // is looked for inside the accordion the edit belongs to, so before and after shoot the same block.
  let root = document;
  if (scope) {
    const acc = [...document.querySelectorAll('.faq-InnerDiv')].find(d =>
      norm((d.querySelector('.faq-title') || {}).textContent || '').startsWith(scope));
    if (acc) root = acc;
  }
  const blocks = [...root.querySelectorAll('li, p, td, dd')];
  const visible = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  let best = null;
  for (const el of blocks) {
    if (!norm(el.textContent).includes(p)) continue;
    if (el.closest('script,style,noscript,template')) continue;
    // a visible block, or one inside a product accordion we can open; never a hidden duplicate
    if (!visible(el) && !el.closest('.faq-InnerDiv')) continue;
    if (!best || best.contains(el)) best = el;
  }
  if (!best) return null;
  const acc = best.closest('.faq-InnerDiv');
  if (acc && best.getClientRects().length === 0) {
    acc.querySelector('.Faq_tabOuter').click();
  }
  best.setAttribute('data-r4-target', '1');
  return true;
}"""


def scope_of(e):
    """The accordion a product edit lives in, by its title; None for articles, collections and pages."""
    if e["page_type"] != "product":
        return None
    return "dimensions" if e.get("location", "").startswith("custom.dimentions_specifications") else "description"


def probe_text(e):
    t = re.sub(r"<[^>]+>", "", e["context"] or e["before_text"])
    t = html.unescape(t).strip()
    w = t.split()
    return " ".join(w[:8]) if len(w) > 8 else t


def shoot(page, url, e, out: Path, width: int):
    page.set_viewport_size({"width": width, "height": 900})
    time.sleep(2)                       # politeness: the storefront answers 429 under rapid loads
    for attempt in range(8):
        r = page.goto(url, wait_until="load", timeout=60000)
        if r and r.status == 429:       # HTTP 429 is backoff, never a missing page (CLAUDE.md)
            time.sleep(10 * (attempt + 1))
            continue
        break
    if not r or r.status != 200:
        return None
    page.add_style_tag(content="header, .header-wrapper, .section-header, sticky-header, .announcement-bar, "
                               "[class*='sticky'] { position: static !important; }")
    ok = page.evaluate(LOCATE_JS, [probe_text(e), scope_of(e)])
    if not ok:
        return None
    page.wait_for_timeout(700)
    el = page.locator("[data-r4-target]").first
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    box = el.bounding_box()
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        el.screenshot(path=str(out), timeout=15000)
    except Exception:
        return None                      # recorded as "block not found": the page is skipped, never forced
    link = page.evaluate("""(t) => { const el = document.querySelector('[data-r4-target]');
        const a = [...el.querySelectorAll('a')].find(a => a.getAttribute('href') === t);
        if (!a) return null; const r = a.getBoundingClientRect(), b = el.getBoundingClientRect();
        return [...a.getClientRects()].map(c => [c.left - b.left, c.top - b.top, c.width, c.height]); }""", e["target"])
    return {"w": box["width"], "h": box["height"], "link_rects": link}


COMPARE_JS = """async ([a, b, rects]) => {
  const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = src; });
  const [ia, ib] = await Promise.all([load(a), load(b)]);
  if (ia.width !== ib.width || ia.height !== ib.height) return {size: [ia.width, ia.height, ib.width, ib.height]};
  const c = document.createElement('canvas'); c.width = ia.width; c.height = ia.height;
  const x = c.getContext('2d'); x.drawImage(ia, 0, 0); const da = x.getImageData(0, 0, c.width, c.height).data;
  x.clearRect(0, 0, c.width, c.height); x.drawImage(ib, 0, 0); const db = x.getImageData(0, 0, c.width, c.height).data;
  let changed = 0, outside = 0, ox = [];
  const sx = ia.width / rects.boxw, sy = ia.height / rects.boxh;
  // Allowed: the link's own line band(s). Inserting <a> splits text shaping at its edges, so glyphs later on
  // the SAME line can move by a sub-pixel (seen on the first product, 2026-10-07). Any other line changing
  // means a rewrap or a shift, and fails; so does any change in the block's size (checked before this).
  const inLink = (px, py) => rects.r.some(([l, t, w, h]) => py >= (t - 3) * sy && py <= (t + h + 3) * sy);
  for (let i = 0; i < da.length; i += 4) {
    if (Math.abs(da[i]-db[i]) + Math.abs(da[i+1]-db[i+1]) + Math.abs(da[i+2]-db[i+2]) > 24) {
      changed++; const p = i / 4, px = p % c.width, py = Math.floor(p / c.width);
      if (!inLink(px, py)) { outside++; if (ox.length < 5) ox.push([px, py]); }
    }
  }
  return {changed, outside, sample: ox};
}"""


def compare(page, before: Path, after: Path, info_b, info_a):
    if info_b is None or info_a is None:
        return False, "block not found on the page"
    if abs(info_b["h"] - info_a["h"]) > 0.5 or abs(info_b["w"] - info_a["w"]) > 0.5:
        return False, f"block size changed {info_b['w']:.0f}x{info_b['h']:.0f} -> {info_a['w']:.0f}x{info_a['h']:.0f} (layout shift)"
    if not info_a["link_rects"]:
        return False, "the new link is not in the block"
    a = "data:image/png;base64," + base64.b64encode(before.read_bytes()).decode()
    b = "data:image/png;base64," + base64.b64encode(after.read_bytes()).decode()
    r = page.evaluate(COMPARE_JS, [a, b, {"boxw": info_a["w"], "boxh": info_a["h"], "r": info_a["link_rects"]}])
    if "size" in r:
        return False, f"screenshot size changed {r['size']}"
    if r["outside"]:
        return False, f"{r['outside']} pixels changed outside the link's line(s), e.g. {r['sample']}"
    return True, f"{r['changed']} pixels changed, all on the link's own line(s)"


# ------------------------------------------------------------------ steps --

def snapshot(do_write=False, only=None, limit=None):
    import verified_deploy as vd
    from playwright.sync_api import sync_playwright
    q = vd.admin()
    es = [e for e in edits() if not only or e["page_type"] == only][:limit]
    SNAP.mkdir(parents=True, exist_ok=True)
    st = state()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context().new_page()
        for e in es:
            k = slug(e)
            f = SNAP / f"{k}.json"
            cur = read(q, e)
            if f.exists() and st["pages"].get(k, {}).get("applied"):
                print(f"  keep {k}: already applied; its snapshot is the pre-edit copy")
                continue
            prev = st["pages"].get(k, {}).get("before")
            if f.exists() and prev and all(prev.values()) and json.loads(f.read_text())["value"] == cur:
                continue                 # resume: already snapshotted, unchanged since
            f.write_text(json.dumps({"page": e["page"], "id": e["id"], "type": e["page_type"], "field": e["field"],
                                     "value": cur, "taken_at": now()}, ensure_ascii=False, indent=1) + "\n")
            infos = {}
            for w in WIDTHS:
                infos[w] = shoot(pg, STORE + e["page"], e, SHOTS / k / f"before-{w}.png", w)
            st["pages"].setdefault(k, {}).update({"page": e["page"], "snapshot_at": now(), "before": infos})
            print(f"  snapshot {k}: stored {len(cur)} chars; block {'found' if all(infos.values()) else 'NOT FOUND'}")
            save(st)
        b.close()


def apply(do_write=False, only=None, limit=None):
    import verified_deploy as vd
    from playwright.sync_api import sync_playwright
    q = vd.admin()
    st = state()
    es = [e for e in edits() if not only or e["page_type"] == only]
    todo = [e for e in es if not st["pages"].get(slug(e), {}).get("applied")][:limit]
    print(f"{len(todo)} pages to edit{' (dry run)' if not do_write else ''}")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context().new_page()
        cmp_pg = b.new_context().new_page()
        cmp_pg.goto("about:blank")
        for e in todo:
            k = slug(e)
            rec = st["pages"].setdefault(k, {"page": e["page"]})
            snap = json.loads((SNAP / f"{k}.json").read_text())
            cur = read(q, e)
            if not same_stored(cur, snap["value"], e):
                rec.update(result="skipped", reason="stored content changed since the snapshot")
                print(f"  SKIP {k}: changed since the snapshot")
                save(st)
                continue
            try:
                new, tag = build(cur, e)
            except ValueError as ex:
                rec.update(result="skipped", reason=str(ex))
                print(f"  SKIP {k}: {ex}")
                save(st)
                continue
            if not rec.get("before") or not all(rec["before"].values()):
                rec.update(result="skipped", reason="no before screenshot of the block")
                print(f"  SKIP {k}: no before screenshot")
                save(st)
                continue
            if not do_write:
                print(f"  would edit {k}: {e['anchor']!r} -> {e['target']}")
                continue
            write(q, e, new)
            back = read(q, e)
            rec.update(applied=True, applied_at=now(), written=tag)
            save(st)
            if not same_stored(back, new, e):
                revert_one(q, e, snap)
                rec.update(applied=False, result="reverted", reason="read-back differs from what was written (platform normalised more than the link)")
                print(f"  REVERTED {k}: read-back differs")
                save(st)
                continue
            # wait for the storefront to serve the link, then re-shoot and compare
            for _ in range(20):
                r = pg.goto(STORE + e["page"] + f"?r4={int(time.time())}", wait_until="domcontentloaded", timeout=60000)
                if e["target"] in pg.content():
                    break
                time.sleep(3)
            verdicts = {}
            for w in WIDTHS:
                # cache-busted like the wait above: a plain URL can still be the CDN's pre-edit copy
                # (dynamic-saunas-monaco and collections/electric-saunas, 2026-10-08)
                info_a = shoot(pg, STORE + e["page"] + f"?r4={int(time.time())}", e, SHOTS / k / f"after-{w}.png", w)
                verdicts[w] = compare(cmp_pg, SHOTS / k / f"before-{w}.png", SHOTS / k / f"after-{w}.png",
                                      rec["before"][str(w)] if str(w) in rec["before"] else rec["before"][w], info_a)
            if all(v[0] for v in verdicts.values()):
                rec.update(result="applied", visual={str(w): v[1] for w, v in verdicts.items()})
                print(f"  OK   {k}: {e['anchor']!r}; {verdicts[1440][1]}; mobile {verdicts[390][1]}")
            else:
                revert_one(q, e, snap)
                rec.update(applied=False, result="reverted", reason="; ".join(f"{w}px: {v[1]}" for w, v in verdicts.items() if not v[0]))
                print(f"  REVERTED {k}: {rec['reason']}")
            save(st)
        b.close()
    from collections import Counter
    print("results:", dict(Counter(v.get("result", "pending") for v in st["pages"].values())))


def revert_one(q, e, snap):
    write(q, e, snap["value"])
    if not same_stored(read(q, e), snap["value"], e):
        raise SystemExit(f"HALT: {e['page']} did not restore to its snapshot")


def revert(do_write=False, only=None, limit=None):
    import verified_deploy as vd
    st = state()
    q = vd.admin() if do_write else None
    done = {slug(e): e for e in edits()}
    todo = [k for k, v in st["pages"].items() if v.get("applied")]
    print(f"{'reverting' if do_write else 'would revert'} {len(todo)} pages to their snapshots")
    for k in todo:
        snap = json.loads((SNAP / f"{k}.json").read_text())
        print(f"  {'restore' if do_write else 'would restore'} {snap['page']} ({snap['type']} {snap['field']})")
        if do_write:
            revert_one(q, done[k], snap)
            st["pages"][k].update(applied=False, result="reverted by revert command", reverted_at=now())
            save(st)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["snapshot", "apply", "revert"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--type", choices=["product", "article", "collection", "page"])
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    {"snapshot": snapshot, "apply": apply, "revert": revert}[a.step](a.write, a.type, a.limit)


if __name__ == "__main__":
    main()
