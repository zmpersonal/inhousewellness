#!/usr/bin/env python3
"""Prove the card fonts render from the repo's woff2, not a system fallback.

CDN fonts fail in CI, so the fonts are self-hosted. But a MISSING self-hosted
font does not error -- the browser silently substitutes a fallback and the card
still renders, just wrong. That is invisible in a screenshot diff unless you
measure it, so this measures it.

Method: render one line in the real face and again in a deliberately absent
family, and compare advance widths. Identical widths mean the real face never
loaded and both fell back to the same default.

Exits non-zero on failure, so CI halts before publishing a mis-set card.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
EXPECTED = ["fraunces-latin-700-normal.woff2",
            "ibm-plex-sans-latin-400-normal.woff2",
            "ibm-plex-sans-latin-600-normal.woff2",
            "ibm-plex-sans-latin-700-normal.woff2"]
PROBE = "Traditional units cost $3,746 more 0123456789"


def main():
    missing = [f for f in EXPECTED if not (TEMPLATES / "fonts" / f).exists()]
    for f in EXPECTED:
        p = TEMPLATES / "fonts" / f
        print(f"  {'✅' if p.exists() else '❌'} {f}"
              f"{'  ' + format(p.stat().st_size, ',') + ' bytes' if p.exists() else ''}")
    if missing:
        print(f"\n🔴 BLOCKED: {len(missing)} font file(s) missing from templates/fonts/")
        return 2

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        # goto(file://) exactly as scripts/render.py does. set_content() has no
        # base URL, so the relative fonts/ paths cannot resolve and EVERY face
        # falls back -- which would make this check fail against a template
        # that is actually fine.
        page.goto((TEMPLATES / "cards.html").as_uri())
        page.wait_for_function("document.fonts.ready.then(()=>true)")
        # A @font-face is fetched LAZILY -- only when something actually uses
        # it. document.fonts.ready resolves happily with every face still
        # "unloaded", so asking for status alone proves nothing. Force the load,
        # which is what fails loudly if the woff2 is missing or corrupt.
        result = page.evaluate(
            """async (probe) => {
                const want = ["700 48px Fraunces", "400 48px 'IBM Plex Sans'",
                              "600 48px 'IBM Plex Sans'", "700 48px 'IBM Plex Sans'"];
                const errors = [];
                for (const spec of want) {
                    try {
                        const got = await document.fonts.load(spec, probe);
                        if (!got.length) errors.push(`no face matched ${spec}`);
                    } catch (e) { errors.push(`${spec}: ${e}`); }
                }
                await document.fonts.ready;
                const measure = (family) => {
                    const c = document.createElement('canvas').getContext('2d');
                    c.font = `700 48px ${family}`;
                    return c.measureText(probe).width;
                };
                return {
                    fraunces:        measure("'Fraunces', serif"),
                    fraunces_absent: measure("'NoSuchFace12345', serif"),
                    plex:            measure("'IBM Plex Sans', sans-serif"),
                    plex_absent:     measure("'NoSuchFace12345', sans-serif"),
                    faces:  [...document.fonts].map(f => `${f.family}|${f.status}`),
                    errors: errors,
                };
            }""", PROBE)
        browser.close()

    print(f"\n  faces registered: {result['faces']}")
    print(f"  Fraunces {result['fraunces']:8.1f}px  vs serif fallback "
          f"{result['fraunces_absent']:8.1f}px")
    print(f"  IBM Plex {result['plex']:8.1f}px  vs sans fallback "
          f"{result['plex_absent']:8.1f}px")

    bad = []
    for name in ("fraunces", "plex"):
        if abs(result[name] - result[f"{name}_absent"]) < 0.5:
            bad.append(f"{name} matched its fallback width")
    if result["errors"]:
        bad.append(f"font load errors: {result['errors']}")
    unloaded = [f for f in result["faces"] if not f.endswith("|loaded")]
    if unloaded:
        bad.append(f"faces still unloaded after an explicit load: {unloaded}")

    if bad:
        print(f"\n🔴 BLOCKED: fonts fell back instead of loading: {bad}")
        return 2
    print("\n✅ fonts render from the repo's woff2, not a fallback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
