#!/usr/bin/env python3
"""InHouse Wellness pin renderer.

Usage:  python3 render.py payload.json outdir/
Writes one 1000x1500 PNG per item, named <id>.png.
Fails loudly on wrong dimensions or zero-byte output.
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
# cards.html lives in templates/ — works whether render.py sits beside it
# or one level up in scripts/
TEMPLATES = HERE if (HERE / "cards.html").exists() else HERE.parent / "templates"

SIZES = {
    "pinterest": (1000, 1500),   # 2:3 — Pinterest
    "ig":        (1080, 1350),   # 4:5 — Instagram feed / carousel, Facebook
    "story":     (1080, 1920),   # 9:16 — Reels cover, Stories
}


def render(payload, outdir):
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 2000},
                                device_scale_factor=1)
        page.goto((TEMPLATES / "cards.html").as_uri())
        # Fonts must be ready before any screenshot or glyphs render as fallback.
        page.wait_for_function("document.fonts.ready.then(()=>true)")
        page.evaluate("payload => window.render(payload)", payload)
        page.wait_for_timeout(150)

        for item in payload:
            el = page.query_selector(f"#card-{item['id']}")
            if el is None:
                raise SystemExit(f"FAIL: no element for {item['id']}")
            box = el.bounding_box()
            want = SIZES[item.get("size", "pinterest")]
            if (round(box["width"]), round(box["height"])) != want:
                raise SystemExit(
                    f"FAIL: {item['id']} rendered "
                    f"{round(box['width'])}x{round(box['height'])}, "
                    f"expected {want[0]}x{want[1]}")
            dest = outdir / f"{item['id']}.png"
            el.screenshot(path=str(dest))
            if dest.stat().st_size == 0:
                raise SystemExit(f"FAIL: {item['id']} wrote zero bytes")
            written.append(dest)
        browser.close()
    return written


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    out = sys.argv[2] if len(sys.argv) > 2 else "out"
    for f in render(data, out):
        print(f"ok  {f}  {f.stat().st_size:,} bytes")
