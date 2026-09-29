#!/usr/bin/env python3
"""Round 4 Part B live checks, all through the logged-out visitor fetch (no preview, empty jar).

    .venv/bin/python scripts/verified_r4_checks.py
"""
from __future__ import annotations

import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_checks as vc  # noqa: E402
import verified_deploy as vd  # noqa: E402
import verified_golive as g  # noqa: E402
import verified_pages as vp  # noqa: E402
import verified_r4_apply as ra  # noqa: E402

MODELS = ["golden-designs-copenhagen-3-person", "almost-heaven-pinnacle-barrel-4-person", "salus-solara-6-person",
          "dynamic-santiago-2-person", "maxxus-seattle-2-person"]


def main():
    errs, rep = [], {}
    st = g.load_state()
    ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
    pages = {pd["handle"]: pd for pd, _, _ in vd._pages_and_records()}
    titles = vp.load_titles()
    V = vc.vocab()
    # hub
    s, p, seen = g.visitor_get(f"{g.STORE}/pages/sauna-database")
    hub_probs = g.real_hub_problems(p, f"{g.STORE}/pages/sauna-database") + \
        [x for x in [g.hub_rows_problem(vc.main_of(p), [pages[h]["inh_id"] for h in st["active_handles"]])] if x]
    rep["hub"] = {"status": s, "theme": seen["theme_role"], "problems": hub_probs or "PASS"}
    errs += [f"hub: {x}" for x in hub_probs]
    # 5 model pages
    rep["models"] = {}
    for h in MODELS:
        s, p, seen = g.visitor_get(f"{g.STORE}/pages/sauna-database/{h}")
        e = []
        if s != 200 or seen["theme_role"] != "main":
            e.append(f"HTTP {s} / {seen['theme_role']}")
        else:
            n = vc.check_model(ds[pages[h]["inh_id"]], titles[pages[h]["inh_id"]], p, pages[h], e)
            vc.check_head("model", p, pages[h]["seo_title"], pages[h]["url"], e, h)
            vc.check_jsonld(vc.jsonlds(p), h, e, V)
        rep["models"][h] = e or "PASS"
        errs += [f"model {h}: {x}" for x in e]
    # edited articles
    q = vd.admin()
    log = json.loads(ra.LOG.read_text())
    rep["articles"] = {}
    for rec in log:
        e = []
        before = json.loads((ra.SNAP / f"{rec['article_id'].rsplit('/', 1)[1]}.json").read_text())
        stored = q(ra.READ_Q, {"id": rec["article_id"]})["article"]["body"]
        cs = [c for c in ra.approved_changes()[rec["article_id"]]]
        expected = ra.expected_body(before["body"], cs)
        if stored != expected and not ra.formatter_only(expected, stored, {c["target"] for c in cs}):
            e.append("stored body is not the snapshot plus only the approved edits")
        url = f"{g.STORE}/blogs/{rec['blog']}/{rec['handle']}"
        s, page, seen = g.visitor_get(url)
        if s != 200 or seen["theme_role"] != "main":
            e.append(f"HTTP {s} / {seen['theme_role']}")
        if stored not in page:
            e.append("the storefront does not serve the stored body verbatim")
        for c in cs:
            tag = f'<a href="{c["target"]}">'
            if tag not in page:
                e.append(f"{c['id']}: link to {c['target']} missing")
            if re.search(re.escape(tag[:-1]) + r'[^>]*rel="[^"]*nofollow', page):
                e.append(f"{c['id']}: internal link carries nofollow")
            ts, tp, tseen = g.visitor_get(g.STORE + c["target"])
            kind = ("model" if 'data-inhv="model"' in tp else "hub" if 'data-inhv="table"' in tp else "other")
            if ts != 200 or tseen["theme_role"] != "main" or kind == "other" or \
                    (kind == "model" and c["target"].rsplit("/", 1)[1] not in st["active_handles"]):
                e.append(f"{c['id']}: target {c['target']} -> HTTP {ts}, {kind}")
        rep["articles"][url] = e or f"PASS ({len(cs)} link{'s' if len(cs) > 1 else ''}; read-back: {rec['readback']})"
        errs += [f"{url}: {x}" for x in e]
    # footer on 3 pages
    rep["footer"] = {}
    for u in ["/", "/products/golden-designs-copenhagen", "/blogs/saunas/dry-sauna-for-home"]:
        s, p, seen = g.visitor_get(g.STORE + u)
        col = re.search(r'(?s)>\s*Blogs\s*<.*?</ul>', p)
        items = [(h, htmllib.unescape(t)) for h, t in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*([^<]+?)\s*<', col.group(0))] if col else []
        ok = items[-1:] == [("/pages/sauna-database", "Sauna Database")] and len(items) == 6
        rep["footer"][u] = [t for _, t in items] if ok else f"FAIL {items}"
        if not ok:
            errs.append(f"footer {u}: {items}")
    # llms.txt
    s, body, seen = g.visitor_get(f"{g.STORE}/llms.txt")
    want = (ROOT / "docs/verified/r4/llms.txt.rendered-preview.md").read_text()
    rep["llms.txt"] = "PASS (byte-identical to the approved draft)" if s == 200 and body == want else f"FAIL HTTP {s}"
    if rep["llms.txt"].startswith("FAIL"):
        errs.append("llms.txt differs from the approved draft")
    rep["failures"] = errs
    out = ROOT / "docs/verified/r4/live-checks.json"
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(rep, indent=1, ensure_ascii=False)[:6000])
    print("LIVE CHECKS:", "PASS" if not errs else f"FAIL ({len(errs)})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
