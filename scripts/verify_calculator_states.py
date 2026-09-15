#!/usr/bin/env python3
"""Drive the calculator through its states and photograph each one.

TWO TARGETS, ONE SET OF CHECKS
By default this drives `preview/true-total-cost/sauna-cost.html` -- a local
harness loading the byte-identical JS, CSS and JSON the theme gets. With `--url`
it drives a real page, which is how the DEPLOYED theme is verified from GitHub
Actions, where egress to the storefront is open.

The checks are written once and run against both. A second copy of them for the
deployed page would be a second definition of "does this work", and the two would
disagree at the worst possible moment. An agent session cannot use `--url`
against Shopify: 403 on CONNECT from the egress proxy, unchanged since Round 0.
Screenshots taken locally are never described as the preview URL.

The states, from the brief:
  1 known-kW SKU computes running cost
  2 unknown-kW SKU renders the invite, never an estimate
  3 reader-entered kW computes and is LABELLED reader-supplied
  4 reader declines -> partial total with an explicit exclusion line
  5 unresolvable ZIP renders the gap
  6 same inputs -> identical total

    .venv/bin/python scripts/verify_calculator_states.py
"""
import argparse
import contextlib
import urllib.parse
import functools
import http.server
import json
import pathlib
import re
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


@contextlib.contextmanager
def target(url):
    """The page to drive: a given URL, or the local harness on a local server.

    A `--url` that is given is used VERBATIM. It is never rewritten, never
    given a fallback and never quietly swapped for the local copy if it fails to
    load -- a run that says it verified the deployed theme and actually verified
    a file on disk is the worst result this script could produce.
    """
    if url:
        yield url
    else:
        with serve(ROOT) as base:
            yield base + "/" + str(PAGE.relative_to(ROOT))


def main():
    from playwright.sync_api import sync_playwright
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="a real page to drive, e.g. a theme preview "
                                  "URL. Omit to use the local harness.")
    ap.add_argument("--shots", default=str(SHOTS))
    ap.add_argument("--label", default="local-harness",
                    help="stamped into the screenshot filenames, so a picture "
                         "of the harness can never be mistaken for the preview")
    args = ap.parse_args()

    tables = json.loads((ROOT / "assets" / "inh-cost-tables.json").read_text())
    known, unknown = pick(tables)
    shots_dir = pathlib.Path(args.shots)
    shots_dir.mkdir(parents=True, exist_ok=True)
    fails, shots = [], []

    def note(ok, msg):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            fails.append(msg)

    # A REAL STOREFRONT IS NOT A TEST HARNESS. The first run against the
    # deployed theme passed every one of the states and then failed the job
    # on two lines that have nothing to do with this page:
    #
    #   HTTP 403 for https://shop.app/pay/hop?...
    #   Refused to frame 'https://shop.app/' because an ancestor violates ...
    #
    # That is Shop Pay's own widget, loaded by the live store on every page,
    # behaving as it does in any headless browser. These listeners were written
    # where the only resources on the page were ours. Scoping them by ORIGIN
    # keeps every failure in OUR code failing, and moves the store's other apps
    # to a noted list -- a gate that fires on correct data costs more than the
    # gate is worth, and this is the third time that rule has come up this round.
    own_host = urllib.parse.urlsplit(
        args.url if args.url else "http://127.0.0.1").hostname
    third_party = []

    def note_response(r):
        if r.status < 400 or r.url.endswith("/favicon.ico"):
            return
        host = urllib.parse.urlsplit(r.url).hostname
        line = "HTTP %d for %s" % (r.status, r.url)
        (fails if host == own_host else third_party).append(line)

    def note_console(m):
        if m.type != "error" or "Failed to load resource" in m.text:
            return
        line = "console %s: %s" % (m.type, m.text)
        # A console error naming another origin is that origin's problem. One
        # naming ours, or naming none, is ours.
        hosts = re.findall(r"https?://([^/\s')\"]+)", m.text)
        (third_party if hosts and own_host not in hosts else fails).append(line)

    with target(args.url) as page_url, sync_playwright() as pw:
        print("driving: %s" % page_url)
        b = launch(pw)
        pg = b.new_page(viewport={"width": 1180, "height": 1500})
        pg.on("pageerror", lambda e: fails.append("page error: %s" % e))
        pg.on("console", note_console)
        pg.on("response", note_response)

        def load():
            pg.goto(page_url)
            pg.wait_for_selector("[data-inh-ttc][data-ready=true]", timeout=15000)

        def set_(sel, value):
            pg.fill(sel, value)
            pg.dispatch_event(sel, "input")

        def shot(name):
            p = shots_dir / ("%s--%s.png" % (name, args.label))
            pg.locator("[data-inh-ttc]").screenshot(path=str(p))
            shots.append(p)
            return p

        groups = []

        def group(title):
            """Announce a state group AND record it.

            The closing summary used to say "all six states" while seven groups
            ran. A report that miscounts its own checks is the same failure as a
            gate that fires on correct data: the number was written once, by
            hand, and then the seventh group was added. It is derived now.
            """
            groups.append(title)
            print("\n%d. %s" % (len(groups), title))

        def total():
            return float(pg.get_attribute(".ttc-total-figure", "data-value"))

        def line(lid):
            el = pg.locator("[data-line=%s]" % lid)
            return el.get_attribute("data-state"), el.inner_text()

        # ── 1. a known-kW SKU computes running cost ────────────────────────
        group("known kW computes running cost")
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
        group("unknown kW renders the invite")
        pg.select_option("[name=model]", unknown["h"])
        st, txt = line("running")
        note(st == "invite", "running line state=%s" % st)
        note(pg.locator("div[data-state=invite]").count() == 1, "the invite is rendered")
        note(pg.locator("[data-line=running] .ttc-figure").count() == 0,
             "no figure is rendered for an unrated model")
        shot("state-2-unknown-kw-invite")

        # ── 3. a reader-entered kW computes and is labelled ────────────────
        group("reader-entered kW computes, labelled reader-supplied")
        set_("[name=reader_kw]", "6")
        st, txt = line("running")
        note(st == "computed", "running line state=%s" % st)
        note(pg.locator("div[data-state=reader_kw]").count() == 1,
             "the reader-supplied label is shown")
        note("reader-supplied" in pg.locator("div[data-state=reader_kw]").inner_text(),
             "the label says reader-supplied in words")
        shot("state-3-reader-kw")

        # ── 4. the reader declines -> a partial total that says so ─────────
        group("reader declines -> partial total with an exclusion line")
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
        group("unresolvable ZIP renders a coverage gap")
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
        group("same inputs, identical total")
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
        group("no zero stands in for an absence, in any state")
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

        ran = len(groups)

        b.close()

    print("\nscreenshots:")
    for s in shots:
        print("  " + str(s))
    if third_party:
        # Reported, never hidden, and never counted as a failure of this page.
        print("\n%d third-party console/network line(s) from the storefront's "
              "own apps, not from this page:" % len(third_party))
        for t in sorted(set(third_party)):
            print("  " + t)
    if fails:
        print("\n%d FAILURE(S)" % len(fails))
        for f in fails:
            print("  " + f)
        sys.exit(1)
    where = args.url if args.url else "the local harness"
    print("\nall %d state group(s) verified against %s."
          % (ran, where))


if __name__ == "__main__":
    main()
