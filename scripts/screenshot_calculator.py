#!/usr/bin/env python3
"""Full-page screenshots of the calculator at a stated viewport width.

Separate from `verify_calculator_states.py` on purpose. That script proves the
seven states and photographs the SECTION; this one photographs the PAGE at a
width, which is a design question, not a correctness one. Keeping them apart
means a design review cannot quietly become the thing that says the states pass.

The width is in the filename, because a screenshot whose viewport nobody
recorded is evidence of nothing.

    python3 scripts/screenshot_calculator.py --width 1280 --label desktop
    python3 scripts/screenshot_calculator.py --url <preview> --width 390 --label mobile
"""
import argparse
import contextlib
import functools
import http.server
import pathlib
import socketserver
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "preview" / "true-total-cost" / "sauna-cost.html"
CHROMIUM = pathlib.Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


@contextlib.contextmanager
def serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d" % httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


@contextlib.contextmanager
def target(url):
    """A given URL verbatim, or the local harness. Never a silent substitution."""
    if url:
        yield url
    else:
        with serve(ROOT) as base:
            yield base + "/" + str(PAGE.relative_to(ROOT))


def main():
    from playwright.sync_api import sync_playwright
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--label", default="shot")
    ap.add_argument("--out", default=str(ROOT / "out" / "design"))
    ap.add_argument("--full", action="store_true", default=True)
    ap.add_argument("--fold-only", action="store_true",
                    help="just the first viewport, which is what most readers see")
    # A SHOT THAT CANNOT LEAVE THE RUNNER IS NOT EVIDENCE ANYONE CAN SEE.
    # Artifact blob storage is unreachable from an agent session (403 on
    # CONNECT, org policy), so a screenshot of the LIVE page can be proved to
    # exist and still never be looked at. `--jpeg` writes a form small enough to
    # travel through the job log itself. It is a transport choice, not a quality
    # one: the PNG is still written for the artifact.
    ap.add_argument("--jpeg", type=int, metavar="QUALITY", default=None,
                    help="also write a JPEG at this quality, at scale 1")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with target(args.url) as url, sync_playwright() as pw:
        b = (pw.chromium.launch(executable_path=str(CHROMIUM))
             if CHROMIUM.exists() else pw.chromium.launch())
        pg = b.new_page(viewport={"width": args.width, "height": args.height},
                        device_scale_factor=2)
        pg.goto(url)
        pg.wait_for_selector("[data-inh-ttc][data-ready=true]", timeout=20000)
        pg.wait_for_timeout(400)          # let the webfonts land before the shutter
        dest = out / ("%s-%dpx.png" % (args.label, args.width))
        pg.screenshot(path=str(dest), full_page=not args.fold_only)
        if args.jpeg is not None:
            # scale 1, because the point is size on the wire, not fidelity.
            pg2 = b.new_page(viewport={"width": args.width, "height": args.height},
                             device_scale_factor=1)
            pg2.goto(url)
            pg2.wait_for_selector("[data-inh-ttc][data-ready=true]", timeout=20000)
            pg2.wait_for_timeout(400)
            jdest = out / ("%s-%dpx.jpg" % (args.label, args.width))
            pg2.screenshot(path=str(jdest), full_page=not args.fold_only,
                           type="jpeg", quality=args.jpeg)
            print("wrote %s  (%d bytes)" % (jdest, jdest.stat().st_size))
            pg2.close()
        b.close()
    print("driving: %s" % (args.url or "local harness"))
    print("wrote %s  (%dpx viewport%s)"
          % (dest, args.width, ", first fold only" if args.fold_only else ", full page"))


if __name__ == "__main__":
    main()
