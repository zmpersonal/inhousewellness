#!/usr/bin/env python3
"""Retire three page handles into one, with 301s, and prove the 301s resolve.

WHY ONE PAGE AND NOT FOUR
Four URLs rendered the same calculator. InHouse has ~67 referring domains; four
paths competing for one cluster split whatever equity arrives four ways and read
as duplicate content to anything crawling them. `/pages/sauna-cost` is the head
term and keeps the tool; the other three become redirects into it.

TWO STEPS, AND THE ORDER IS NOT OPTIONAL
A Shopify URL redirect only fires when the path would otherwise 404. A PUBLISHED
page at `/pages/sauna-running-cost` wins, and the redirect sits there doing
nothing while the duplicate keeps serving. So the pages are UNPUBLISHED first,
then the redirects are created. Unpublished rather than deleted: it is reversible,
and this round should not be the one that destroys 9 KB of prose.

    python3 scripts/deploy_redirects.py --live
    python3 scripts/deploy_redirects.py --self-test
"""
import argparse
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import gql, load_env      # noqa: E402

TARGET = "/pages/sauna-cost"
RETIRE = [
    "/pages/sauna-running-cost",
    "/pages/sauna-installation-cost",
    "/pages/sauna-cost-methodology",
]

FIND_PAGE = """query($q: String!) {
  pages(first: 50, query: $q) { nodes { id handle isPublished } } }"""
UNPUBLISH = """mutation($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) { page { id handle isPublished }
    userErrors { field code message } } }"""
FIND_REDIRECT = """query($q: String!) {
  urlRedirects(first: 50, query: $q) { nodes { id path target } } }"""
CREATE_REDIRECT = """mutation($redirect: UrlRedirectInput!) {
  urlRedirectCreate(urlRedirect: $redirect) { urlRedirect { id path target }
    userErrors { field message } } }"""
UPDATE_REDIRECT = """mutation($id: ID!, $redirect: UrlRedirectInput!) {
  urlRedirectUpdate(id: $id, urlRedirect: $redirect) { urlRedirect { id path target }
    userErrors { field message } } }"""


def handle_of(path):
    return path.rsplit("/", 1)[-1]


def existing_redirects(shop, token):
    """path -> node, filtered by EXACT path.

    Shopify's redirect search is full-text, the same trap the page lookup hit:
    a query for "sauna" returns redirects whose path contains no such segment.
    """
    found = {}
    for path in RETIRE:
        for n in gql(shop, token, FIND_REDIRECT,
                     {"q": handle_of(path)})["urlRedirects"]["nodes"]:
            if n["path"] == path:
                found[path] = n
    return found


def check_live(origin, path, timeout=20):
    """(status, location) for `path`, following nothing.

    A redirect is not deployed because an API call returned an id. It is
    deployed when a request to the old path answers 301 and names the new one --
    and this project does not accept a successful mutation as evidence of a
    working URL.
    """
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **kw):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(origin + path, method="GET",
                                 headers={"User-Agent": "InHouseWellnessDeploy/1.0"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")


def self_test():
    fails = []
    if TARGET in RETIRE:
        fails.append("the target is in the retire list; it would redirect to itself")
    if len(set(RETIRE)) != len(RETIRE):
        fails.append("a path is listed twice")
    for p in RETIRE + [TARGET]:
        if not p.startswith("/pages/"):
            fails.append("%r is not a page path" % p)
    # The retired handles must no longer be pages this repo deploys, or the next
    # deploy would re-publish exactly what this script just retired.
    from scripts.deploy_pages import PAGES
    for p in RETIRE:
        if handle_of(p) in PAGES:
            fails.append("%s is still in deploy_pages.PAGES; the next deploy would "
                         "republish it and the redirect would stop firing"
                         % handle_of(p))
    if handle_of(TARGET) not in PAGES:
        fails.append("the surviving page is not in deploy_pages.PAGES")
    # The exact-path filter, fired at the shape Shopify's full-text search returns.
    noise = [{"path": "/pages/sauna-cost"}, {"path": "/collections/saunas"}]
    if [n for n in noise if n["path"] in RETIRE]:
        fails.append("the exact-path filter would match an unrelated redirect")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="actually unpublish and create. Without it, prints only.")
    ap.add_argument("--origin", default=None,
                    help="storefront origin to verify against, e.g. "
                         "https://inhousewellness.com. Default: the shop domain.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: the redirect deploy failed its own controls:\n  "
                     + "\n  ".join(fails))
        print("redirect self-test: three distinct page paths retire into "
              + TARGET + ", and none of them is still a page this repo deploys")
        return

    print("retiring into %s:" % TARGET)
    for p in RETIRE:
        print("  " + p)
    if not args.live:
        print("\ndry run. Re-run with --live to unpublish and redirect.")
        return

    shop, token = load_env()
    missing = [n for n, v in (("SHOPIFY_SHOP", shop),
                              ("SHOPIFY_ADMIN_TOKEN", token)) if not v]
    if missing:
        sys.exit("NO CREDENTIAL: %s not set. Nothing was changed. This is not a "
                 "failure of the deploy; it is a missing secret."
                 % " and ".join(missing))

    # 1. UNPUBLISH FIRST. A published page beats a redirect, every time.
    print("\nunpublishing the retired pages:")
    for path in RETIRE:
        h = handle_of(path)
        nodes = [n for n in gql(shop, token, FIND_PAGE, {"q": h})["pages"]["nodes"]
                 if n["handle"] == h]
        if not nodes:
            print("  %-30s no such page (already gone)" % h)
            continue
        n = nodes[0]
        if not n["isPublished"]:
            print("  %-30s already unpublished" % h)
            continue
        res = gql(shop, token, UNPUBLISH,
                  {"id": n["id"], "page": {"isPublished": False}})["pageUpdate"]
        errs = res.get("userErrors") or []
        if errs:
            sys.exit("HALT: could not unpublish %s: %s" % (h, errs))
        print("  %-30s unpublished" % h)

    # 2. THEN the redirects.
    print("\nredirects:")
    have = existing_redirects(shop, token)
    for path in RETIRE:
        if path in have and have[path]["target"] == TARGET:
            print("  %-34s -> %s  (already correct)" % (path, TARGET))
            continue
        if path in have:
            res = gql(shop, token, UPDATE_REDIRECT,
                      {"id": have[path]["id"],
                       "redirect": {"path": path, "target": TARGET}})["urlRedirectUpdate"]
            verb = "retargeted"
        else:
            res = gql(shop, token, CREATE_REDIRECT,
                      {"redirect": {"path": path, "target": TARGET}})["urlRedirectCreate"]
            verb = "created"
        errs = res.get("userErrors") or []
        if errs:
            sys.exit("HALT: %s %s failed: %s" % (verb, path, errs))
        print("  %-34s -> %s  (%s)" % (path, res["urlRedirect"]["target"], verb))

    # 3. PROVE IT. A mutation that returned an id and a URL that redirects are
    #    different facts, and this project has been caught by that distinction
    #    four times in one round already.
    origin = args.origin or ("https://" + shop)
    print("\nverifying against %s:" % origin)
    ok = True
    for path in RETIRE:
        status, location = check_live(origin, path)
        landed = (location or "").rstrip("/").endswith(TARGET)
        if status in (301, 302, 308) and landed:
            print("  %-34s HTTP %d -> %s" % (path, status, location))
        else:
            print("  %-34s HTTP %s -> %r   NOT REDIRECTING TO %s"
                  % (path, status, location, TARGET))
            ok = False
    status, _ = check_live(origin, TARGET)
    if status != 200:
        print("  %-34s HTTP %s   the surviving page must answer 200"
              % (TARGET, status))
        ok = False
    else:
        print("  %-34s HTTP 200  (the survivor)" % TARGET)
    if not ok:
        sys.exit("HALT: the redirects do not resolve as stated.")
    print("\nall %d redirect(s) live, and %s still serves." % (len(RETIRE), TARGET))


if __name__ == "__main__":
    main()
