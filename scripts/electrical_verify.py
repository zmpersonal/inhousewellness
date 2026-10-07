#!/usr/bin/env python3
"""Electrical tool, Round 1 Part B: render-side verification against the REAL preview URLs.

    .venv/bin/python scripts/electrical_verify.py [--theme-id ID] [--out docs/electrical/r1/shots]

Drives Chromium (Playwright, pinned 1.49.1 on this host) through every state Part B §7 names,
asserts what must and must not render, and saves a screenshot per state. Read-only: it loads
pages and fills form fields in the browser, nothing else. The theme id defaults to the one
recorded in data/electrical/preview-state.json. Every URL is used verbatim (no local fallback).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = "https://inhousewellness.com"
# Nothing a code calculation would print. Manufacturer quotes may say "breaker"; these may not
# appear anywhere OUTSIDE a quote on any page.
FORBIDDEN = [re.compile(p, re.I) for p in (r"\b\d{1,2}\s*AWG\b", r"\bwire (?:size|gauge)\s*[:=]?\s*\d", r"code[- ]based",
                                            r"code minimum\s*[:=]?\s*\d", r"125\s*%", r"below code", r"\b1\.25\b")]
BREAKER_NUM = re.compile(r"breaker[^.]{0,25}\b\d{2}\s*a(?:mps?)?\b|\b\d{2}\s*a(?:mps?)?\b[^.]{0,25}breaker", re.I)


def outside_quotes(page) -> str:
    return page.evaluate("""() => { const c = document.querySelector('article.inhe').cloneNode(true);
      c.querySelectorAll('.inhe-quote, script, .inhe-sheet').forEach(e => e.remove()); return c.innerText; }""")


def assert_clean(page, label, results):
    text = outside_quotes(page)
    bad = [p.pattern for p in FORBIDDEN if p.search(text)] + (["breaker with a number outside a quote"] if BREAKER_NUM.search(text) else [])
    results.append((label + ": no code-based breaker/wire value outside manufacturer quotes", not bad, bad))


def run(theme_id: str, out: Path) -> int:
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "assets/inh-electrical-data.json").read_text())
    by = {m["handle"]: m for m in data["models"]}
    R = []   # (name, ok, detail)
    # Shopify answers ?preview_theme_id with a 302 that sets a preview cookie and DROPS the query
    # string, so each browser context is put into preview once, then given clean URLs. Every page
    # then asserts it is the preview by finding this round's own markup.
    def enter_preview(pg):
        pg.goto(f"{STORE}/?preview_theme_id={theme_id}", wait_until="load")
        # Shopify's preview bar floats over the page; hide it in THIS test browser only, so it does
        # not cover what the screenshots are meant to show. Nothing on the store changes.
        # Also un-stick the theme's sticky header, which otherwise overlaps element screenshots.
        pg.context.add_init_script("""document.addEventListener('DOMContentLoaded', () => { const st = document.createElement('style');
          st.textContent = 'iframe[src*="preview_bar"], #preview-bar-iframe, #PBarNextFrameWrapper, [id^="PBar"] { display: none !important; }'
            + ' header, .header-wrapper, .section-header, sticky-header { position: static !important; top: auto !important; }';
          document.head.appendChild(st); });""")
    pv = "?"

    def tool(page, qs, wait='[data-inhe="result"] *'):
        page.goto(f"{STORE}/pages/sauna-electrical-requirements?{qs}", wait_until="load")
        page.wait_for_selector(wait, timeout=30000)

    def shot(page, name, el='article.inhe'):
        page.locator(el).first.screenshot(path=str(out / f"{name}.png"))

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        enter_preview(page)

        # 1. a model with a manufacturer-stated circuit, quoted verbatim
        h = "maxxus-seattle-2-person"
        tool(page, f"model={h}")
        q = [s["quote"]["text"] for s in by[h]["statements"] if s["about_circuit"]][0]
        card = page.locator('[data-inhe="circuit"]').inner_text()
        R.append(("1 stated circuit renders verbatim with grade and source", q in card and "verified 20" in card and
                  ("Listed" in card or "Documented" in card), q))
        assert_clean(page, "1", R)
        shot(page, "01-stated-circuit-maxxus-seattle")

        # 2. one of Part A's 18: the stated circuit, no flag, no code note
        h = "salus-solara-6-person"
        tool(page, f"model={h}")
        card = page.locator('[data-inhe="circuit"]').inner_text()
        q = [s["quote"]["text"] for s in by[h]["statements"] if s["about_circuit"]][0]
        R.append(("2 Part A model: stated circuit verbatim, no flag", q in card and not re.search(r"flag|code|below", card, re.I), q))
        R.append(("2 heater current draw is labelled calculated and sits in its own card",
                  page.locator('[data-inhe="heater"] [data-inhe="draw"]').count() == 1 and
                  "calculated from rated kW and voltage" in page.locator('[data-inhe="heater"]').inner_text() and
                  page.locator('[data-inhe="circuit"] [data-inhe="draw"]').count() == 0, ""))
        assert_clean(page, "2", R)
        shot(page, "02-part-a-model-salus-solara")

        # 3. rated kW, no stated circuit (voltage not sourced; the reader enters 240 V)
        h = "almost-heaven-sutton-2-person"
        tool(page, f"model={h}&v=240")
        txt = page.locator('[data-inhe="result"]').inner_text()
        R.append(("3 'not published' state + labelled calculated draw, no breaker or wire",
                  "doesn't publish a circuit requirement" in txt and "Heater current draw (calculated from rated kW and voltage)" in txt
                  and "25.0 A" in txt and "the voltage is the one you entered" in txt, ""))
        assert_clean(page, "3", R)
        shot(page, "03-rated-kw-no-circuit-almost-heaven-sutton")

        # 4. no rated kW: the designed unknown state
        h = "almost-heaven-allegheny-cabin-6-person"
        tool(page, f"model={h}")
        txt = page.locator('[data-inhe="result"]').inner_text()
        R.append(("4 unknown kW: designed state, nothing computed", "Not stated in the sources we've verified" in txt and
                  "never estimated from a similar model" in txt and page.locator('[data-inhe="draw"]').count() == 0, ""))
        assert_clean(page, "4", R)
        shot(page, "04-no-rated-kw-almost-heaven-allegheny")

        # 5. a priced INH sauna with no database record: manual entry, no false coverage
        prod = data["unmapped_inh_products"][0]["handle"]
        tool(page, f"product={prod}&kw=6&v=240")
        txt = page.locator('[data-inhe="result"]').inner_text()
        R.append(("5 unmapped INH sauna: no coverage claimed, draw from the reader's figures only",
                  ("not yet in the" in txt or "not published yet" in txt) and "doesn't publish" not in txt and page.locator('[data-inhe="circuit"]').count() == 0 and
                  "Both inputs are the figures you entered" in txt, prod))
        assert_clean(page, "5", R)
        shot(page, "05-unmapped-inh-product")

        # 6. a 120 V plug-in infrared model
        h = "clearlight-premier-2-2-person"
        tool(page, f"model={h}")
        txt = page.locator('[data-inhe="result"]').inner_text()
        R.append(("6 120 V plug-in: 'standard household outlet' and NEMA 5-15P from sourced quotes",
                  "Plugs into a standard household outlet" in txt and "NEMA 5-15P" in txt, ""))
        assert_clean(page, "6", R)
        shot(page, "06-plug-in-120v-clearlight-premier-2")

        # 7. heater sizing, 6x6x7 ft with a 12 sq ft glass door: each chart separately
        page.goto(f"{STORE}/pages/sauna-heater-size-calculator?len=6&wid=6&hgt=7&glass=12", wait_until="load")
        page.wait_for_selector('[data-inhe="charts"]', timeout=30000)
        items = page.locator('[data-inhe="charts"] li').all_inner_texts()
        R.append(("7 sizing: every chart rendered separately, glass divergence stated",
                  len(items) == len(data["charts"]) and page.locator('[data-inhe="glass-diverge"]').count() == 1, " | ".join(i.split("\n")[0] for i in items)))
        assert_clean(page, "7", R)
        shot(page, "07-sizing-6x6x7-glass-door")

        # 8. the 6 kW answer page with JavaScript OFF
        nojs = b.new_context(java_script_enabled=False, viewport={"width": 1100, "height": 900})
        p2 = nojs.new_page()
        enter_preview(p2)
        p2.goto(f"{STORE}/pages/6-kw-sauna-heater-breaker-size{pv}", wait_until="load")
        rows = p2.locator("table.inhe-table tbody tr").count()
        # Derived from the built asset, never pinned: r3 publishing moved it 15 -> 17 (CLAUDE.md, literals).
        want_6kw = sum(1 for m in json.loads((ROOT / "assets/inh-electrical-data.json").read_text())["models"]
                       if m["heater"] and m["heater"]["kw"] == 6.0)
        R.append(("8 6 kW page, JavaScript off: full table readable", rows == want_6kw and p2.locator("table.inhe-table").is_visible(), f"{rows} rows, {want_6kw} expected"))
        assert_clean(p2, "8", R)
        p2.locator("article.inhe").screenshot(path=str(out / "08-answer-6kw-js-off.png"))
        for hh in ("8-kw-sauna-heater-breaker-size", "infrared-sauna-dedicated-circuit", "sauna-electrical-methodology"):
            p2.goto(f"{STORE}/pages/{hh}{pv}", wait_until="load")
            assert_clean(p2, f"8 {hh}", R)
            p2.locator("article.inhe").screenshot(path=str(out / f"08-{hh}-js-off.png"))
        nojs.close()

        # 9. the electrician sheet in print preview
        tool(page, "model=salus-solara-6-person&panel=100&slots=2")
        page.locator('[data-inhe="panel"]').select_option("100")
        page.locator('[data-inhe="slots"]').fill("2")
        page.emulate_media(media="print")
        sheet = page.locator('[data-inhe="sheet"]')
        R.append(("9 print shows the electrician sheet with questions, not a verdict", sheet.is_visible() and
                  "Questions for your electrician" in sheet.inner_text() and "100 A" in sheet.inner_text(), ""))
        page.screenshot(path=str(out / "09-electrician-sheet-print.png"), full_page=True)
        page.pdf(path=str(out / "09-electrician-sheet.pdf"), format="Letter")
        page.emulate_media(media="screen")

        # 10. determinism: same inputs, identical output twice
        outs = []
        for _ in range(2):
            tool(page, "model=golden-designs-sundsvall-2-person")
            outs.append(page.locator('[data-inhe="result"]').inner_html())
        R.append(("10 determinism: identical output twice", outs[0] == outs[1], f"{len(outs[0])} chars"))

        # 11. the model-page link exists in the PREVIEW only
        page.goto(f"{STORE}/pages/sauna-database/salus-solara-6-person{pv}", wait_until="load")
        page.wait_for_selector("article.inhv-model", timeout=30000)
        prev = page.locator('[data-inhe="model-link"]').count()
        page.locator('[data-inhe="model-link"]').first.screenshot(path=str(out / "11-model-page-link-preview.png")) if prev else None
        ctx2 = b.new_context()
        live = ctx2.new_page()
        live.goto(f"{STORE}/pages/sauna-database/salus-solara-6-person", wait_until="load"); live.wait_for_selector("article.inhv-model", timeout=30000)
        R.append(("11 model-page link in the preview theme only", prev == 1 and live.locator('[data-inhe="model-link"]').count() == 0, ""))
        ctx2.close()
        b.close()

    ok = all(r[1] for r in R)
    for name, good, det in R:
        print(f"{'PASS' if good else 'FAIL'}  {name}" + (f"  [{det}]" if det else ""))
    (out / "verify-results.json").write_text(json.dumps([{"check": n, "pass": g, "detail": d if isinstance(d, str) else str(d)}
                                                          for n, g, d in R], indent=1) + "\n")
    print(f"verify: {'PASS' if ok else 'FAIL'} ({sum(r[1] for r in R)}/{len(R)})")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id")
    ap.add_argument("--out", default=str(ROOT / "docs/electrical/r1/shots"))
    a = ap.parse_args()
    tid = a.theme_id or json.loads((ROOT / "data/electrical/preview-state.json").read_text())["theme"]["id"]
    sys.exit(run(tid, Path(a.out)))


if __name__ == "__main__":
    main()
