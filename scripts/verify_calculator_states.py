#!/usr/bin/env python3
"""Drive the calculator through its six states and photograph each one.

WHY A LOCAL HARNESS AND NOT THE PREVIEW URL
Shopify answers 403 on CONNECT from this environment's egress proxy, so no
`*.myshopify.com` preview can be loaded or screenshotted from here. These
screenshots are of `preview/true-total-cost/sauna-cost.html`, which loads the
byte-identical JS, CSS and JSON assets the theme gets. They prove the ARITHMETIC
and the STATES. They are not, and must never be described as, the live preview.

The six states, from the brief:
  1 known-kW SKU computes running cost
  2 unknown-kW SKU renders the invite, never an estimate
  3 reader-entered kW computes and is LABELLED reader-supplied
  4 reader declines -> partial total with an explicit exclusion line
  5 unresolvable ZIP renders the gap
  6 same inputs -> identical total

    .venv/bin/python scripts/verify_calculator_states.py
"""
import contextlib
import functools
import http.server
import json
import pathlib
import socketserver
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "preview" / "true-total-cost" / "sauna-cost.html"
SHOTS = ROOT / "out" / "true-total-cost"

# requirements.txt pins Playwright 1.49.1 for TWO reasons -- macOS 13 cannot
# install a current one, and render determinism -- and this Linux runner ships a
# NEWER browser build than 1.49.1 expects. Pointing at the installed binary
# honours the pin without downloading a second browser; a mismatch here would
# otherwise read as "Playwright is broken" when it means "the pin is doing its
# job". Falls back to Playwright's own resolution when the path is absent.
CHROMIUM = pathlib.Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def launch(pw):
    if CHROMIUM.exists():
        return pw.chromium.launch(executable_path=str(CHROMIUM))
    return pw.chromium.launch()


@contextlib.contextmanager
def serve(directory):
    """A static server over the repo root.

    `fetch()` refuses a file:// URL, so a harness opened straight off disk shows
    an empty calculator and the failure looks like a bug in the page. Serving it
    is the difference between testing the code and testing the browser's CORS
    policy.
    """
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d" % httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


def pick(tables):
    """One SKU with a published kW and one without. Chosen from the data rather
    than hardcoded, so a rebuild cannot leave this test pointing at a handle
    that no longer carries what the test assumes."""
    known = next(p for p in tables["products"] if p["kw"]["v"] is not None)
    unknown = next(p for p in tables["products"] if p["kw"]["v"] is None)
    return known, unknown


def main():
    from playwright.sync_api import sync_playwright
    tables = json.loads((ROOT / "assets" / "inh-cost-tables.json").read_text())
    known, unknown = pick(tables)
    SHOTS.mkdir(parents=True, exist_ok=True)
    fails, shots = [], []

    def note(ok, msg):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            fails.append(msg)

    with serve(ROOT) as base, sync_playwright() as pw:
        page_url = base + "/" + str(PAGE.relative_to(ROOT))
        b = launch(pw)
        pg = b.new_page(viewport={"width": 1180, "height": 1500})
        pg.on("pageerror", lambda e: fails.append("page error: %s" % e))
        # The console's own 404 message does not name the URL, so it is covered
        # by the response listener below, which does. Keeping both would report
        # one missing favicon as two unexplained failures.
        pg.on("console", lambda m: fails.append("console %s: %s" % (m.type, m.text))
              if m.type == "error" and "Failed to load resource" not in m.text else None)
        # A 404 on an asset is named, not summarised. "a resource 404'd" is the
        # console's phrasing and it is useless: WHICH resource is the finding.
        pg.on("response", lambda r: fails.append("HTTP %d for %s" % (r.status, r.url))
              if r.status >= 400 and not r.url.endswith("/favicon.ico") else None)

        def load():
            pg.goto(page_url)
            pg.wait_for_selector("[data-inh-ttc][data-ready=true]", timeout=15000)

        def set_(sel, value):
            pg.fill(sel, value)
            pg.dispatch_event(sel, "input")

        def shot(name):
            p = SHOTS / (name + ".png")
            pg.locator("[data-inh-ttc]").screenshot(path=str(p))
            shots.append(p)
            return p

        def total():
            return float(pg.get_attribute(".ttc-total-figure", "data-value"))

        def line(lid):
            el = pg.locator("[data-line=%s]" % lid)
            return el.get_attribute("data-state"), el.inner_text()

        # ── 1. a known-kW SKU computes running cost ────────────────────────
        print("\n1. known kW computes running cost")
        load()
        pg.select_option("[name=model]", known["h"])
        set_("[name=zip]", "58102")                       # Fargo, ND
        st, txt = line("running")
        note(st == "computed", "running line state=%s" % st)
        rate = tables["energy"]["rates_cents_per_kwh"]["ND"]
        want = round(known["kw"]["v"] * 0.75 * 3 * 52 * rate / 100, 2)
        got = float(pg.evaluate(
            "() => document.querySelector('[data-line=running] .ttc-figure')"
            ".textContent.replace(/[$,]/g,'')"))
        note(abs(got - want) < 0.01,
             "%.1f kW in ND at %s c/kWh -> $%.2f (expected $%.2f)"
             % (known["kw"]["v"], rate, got, want))
        note("EIA" in txt or "electricity price" in txt,
             "the running line carries its source inline")
        shot("state-1-known-kw")

        # ── 2. an unknown-kW SKU invites, and never estimates ──────────────
        print("\n2. unknown kW renders the invite")
        pg.select_option("[name=model]", unknown["h"])
        st, txt = line("running")
        note(st == "invite", "running line state=%s" % st)
        note(pg.locator("div[data-state=invite]").count() == 1, "the invite is rendered")
        note(pg.locator("[data-line=running] .ttc-figure").count() == 0,
             "no figure is rendered for an unrated model")
        shot("state-2-unknown-kw-invite")

        # ── 3. a reader-entered kW computes and is labelled ────────────────
        print("\n3. reader-entered kW computes, labelled reader-supplied")
        set_("[name=reader_kw]", "6")
        st, txt = line("running")
        note(st == "computed", "running line state=%s" % st)
        note(pg.locator("div[data-state=reader_kw]").count() == 1,
             "the reader-supplied label is shown")
        note("reader-supplied" in pg.locator("div[data-state=reader_kw]").inner_text(),
             "the label says reader-supplied in words")
        shot("state-3-reader-kw")

        # ── 4. the reader declines -> a partial total that says so ─────────
        print("\n4. reader declines -> partial total with an exclusion line")
        set_("[name=reader_kw]", "")
        pg.check("[name=decline_kw]")
        st, _ = line("running")
        note(st == "excluded", "running line state=%s" % st)
        note(pg.locator("div[data-state=partial]").count() == 1,
             "the total is labelled as partial")
        note(pg.locator("li[data-excluded=running]").count() == 1,
             "running cost appears in the exclusion list")
        note(pg.locator(".ttc-total-head").inner_text().lower().endswith("known"),
             "the total's own heading says it is of what is known")
        shot("state-4-declined-partial")

        # ── 5. an unresolvable ZIP renders the gap, never an average ───────
        print("\n5. unresolvable ZIP renders a coverage gap")
        pg.uncheck("[name=decline_kw]")
        pg.select_option("[name=model]", known["h"])
        set_("[name=zip]", "00001")            # a real ZIP prefix with no ZCTA
        note(pg.locator("div[data-state=zip_gap]").count() == 1, "the gap is rendered")
        st, _ = line("running")
        note(st == "zip_gap", "running line state=%s" % st)
        gap = pg.locator("div[data-state=zip_gap]").inner_text()
        note("do not substitute" in gap, "the gap says the average is not used")
        note(pg.locator("[data-line=price] .ttc-figure").count() == 1,
             "everything not depending on the rate is still computed")
        shot("state-5-zip-gap")

        # 5b. a territory and a multi-state ZIP are their own gaps, not this one
        set_("[name=zip]", "00601")            # Puerto Rico
        note("territories" in pg.locator("div[data-state=zip_gap]").inner_text(),
             "a territory says why it has no rate")
        set_("[name=zip]", "02861")            # straddles MA/RI
        note("straddles" in pg.locator("div[data-state=zip_gap]").inner_text(),
             "a multi-state ZIP says it has two answers, not none")
        shot("state-5b-territory-and-multistate")

        # ── 6. same inputs -> identical total ──────────────────────────────
        print("\n6. same inputs, identical total")
        def run_once():
            load()
            pg.select_option("[name=model]", known["h"])
            set_("[name=zip]", "02108")
            pg.check("[data-freight][value=inside_and_assembled]")
            set_("[name=sessions]", "4")
            set_("[name=minutes]", "50")
            set_("[name=electrical]", "2,400")
            set_("[name=foundation]", "900")
            set_("[name=maintenance]", "120")
            return total()
        a, bb, c = run_once(), run_once(), run_once()
        note(a == bb == c, "three identical runs -> %s / %s / %s" % (a, bb, c))
        note(pg.locator("div[data-state=complete]").count() == 1,
             "with every figure supplied the total is labelled complete")
        shot("state-6-complete-deterministic")

        # the $ signs must be real figures, never NaN or undefined leaking through
        body = pg.locator("[data-inh-ttc]").inner_text()
        for bad in ("NaN", "undefined", "null"):
            note(bad not in body, "no %r rendered anywhere on the page" % bad)

        # ── a zero is a measurement or an absence, and never both ──────────
        # A screenshot of state 2 read "$4,099.00 once, plus $0.00 a year" while
        # the running cost AND the maintenance line were both excluded. That zero
        # is a claim that nothing recurs, made about two figures nobody holds --
        # the missing-value bug rendered at 2.4rem. Checked in EVERY state now,
        # not only the one where everything happens to be supplied.
        print("\n7. no zero stands in for an absence, in any state")
        def recurring_text():
            return pg.locator(".ttc-total-basis").inner_text()
        load()
        pg.select_option("[name=model]", unknown["h"])
        set_("[name=zip]", "58102")
        note("$0.00 a year" not in recurring_text(),
             "unknown-kW state does not print $0.00 a year: %r" % recurring_text())
        note("Nothing recurring is known" in recurring_text(),
             "it says so in words instead")
        set_("[name=maintenance]", "0")
        note("$0.00 a year" in recurring_text(),
             "a maintenance figure the reader TYPED as zero is still shown as "
             "$0.00 -- a real zero is a measurement: %r" % recurring_text())
        shot("state-7-zero-is-not-absence")

        b.close()

    print("\nscreenshots:")
    for s in shots:
        print("  " + str(s.relative_to(ROOT)))
    if fails:
        print("\n%d FAILURE(S)" % len(fails))
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print("\nall six states verified against the local harness. "
          "The live preview URL could not be loaded: Shopify is 403 on CONNECT here.")


if __name__ == "__main__":
    main()
