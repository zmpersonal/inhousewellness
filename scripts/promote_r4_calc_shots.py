#!/usr/bin/env python3
"""Round 4 Part B: before/after screenshots of the cost calculator's model-step help text, 1440 and 390 px.

    .venv/bin/python scripts/promote_r4_calc_shots.py before|after

The block is the help text under "Which model" (span.ttc-help). After the link is added, the block must keep
its size and every changed pixel must lie inside the link's box (same rule and comparator as
promote_r4_apply.py)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import promote_r4_apply as pa  # noqa: E402

URL = "https://inhousewellness.com/pages/sauna-cost"
OUT = ROOT / "out/promote/r4/shots/pages__sauna-cost__calculator"
STATE = ROOT / "data/promote/r4/calc-shots.json"
TARGET = "/pages/sauna-electrical-requirements"


def shoot(page, w, name):
    page.set_viewport_size({"width": w, "height": 900})
    page.goto(URL + f"?r4={int(time.time())}", wait_until="load", timeout=60000)
    page.wait_for_selector("label[for=ttc-model]", timeout=30000)
    el = page.locator("label[for=ttc-model] ~ span.ttc-help").first
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    box = el.bounding_box()
    OUT.mkdir(parents=True, exist_ok=True)
    el.screenshot(path=str(OUT / f"{name}-{w}.png"))
    rects = page.evaluate("""([sel, t]) => { const el = document.querySelector(sel);
        const a = [...el.querySelectorAll('a')].find(a => a.getAttribute('href') === t);
        if (!a) return null; const b = el.getBoundingClientRect();
        return [...a.getClientRects()].map(c => [c.left - b.left, c.top - b.top, c.width, c.height]); }""",
                          ["label[for=ttc-model] ~ span.ttc-help", TARGET])
    return {"w": box["width"], "h": box["height"], "link_rects": rects}


def main(which):
    from playwright.sync_api import sync_playwright
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context().new_page()
        cmp_pg = b.new_context().new_page()
        res = {w: shoot(pg, w, which) for w in pa.WIDTHS}
        st[which] = {str(w): v for w, v in res.items()}
        if which == "after":
            st["verdict"] = {str(w): pa.compare(cmp_pg, OUT / f"before-{w}.png", OUT / f"after-{w}.png", st["before"][str(w)], res[w])
                             for w in pa.WIDTHS}
        b.close()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1) + "\n")
    print(json.dumps(st.get("verdict") or st[which], indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
