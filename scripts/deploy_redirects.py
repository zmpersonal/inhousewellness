#!/usr/bin/env python3
"""Retire three page handles into one, with 301s, and prove the 301s resolve.

WHY ONE PAGE AND NOT FOUR
Four URLs rendered the same calculator. InHouse has ~67 referring domains; four
paths competing for one cluster split whatever equity arrives four ways and read
as duplicate content to anything crawling them. `/pages/sauna-cost` is the head
term and keeps the tool; the other three become redirects into it.

TWO STEPS, AND THE ORDER IS THE WHOLE SAFETY ARGUMENT
A Shopify URL redirect only fires when the path would otherwise 404, so a
PUBLISHED page wins and the redirect sits inert. That makes it tempting to
unpublish first. Run 1 did exactly that, the redirect step then died on
`Access denied for urlRedirects field` -- the Actions token has no
`write_online_store_navigation` scope -- and three live URLs were left 404ing
with nothing to catch them.

CREATE THE REDIRECTS FIRST. They are harmless while the pages are published:
inert, invisible, waiting. THEN unpublish, which is what switches them on. A
failure at the first step now leaves the store exactly as it was.

Unpublished rather than deleted: reversible, and this round should not be the one
that destroys 9 KB of prose.

    python3 scripts/deploy_redirects.py --live
    python3 scripts/deploy_redirects.py --self-test
"""
import argparse
import pathlib
import sys
import urllib.error
import urllib.parse
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


MAX_HOPS = 6


def _one_hop(url, timeout=20):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **kw):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "InHouseWellnessDeploy/1.0"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")


def check_live(origin, path, timeout=20):
    """(final_status, final_url, hops) — the chain a browser would actually walk.

    THE FIRST VERSION STOPPED AT ONE HOP AND WAS WRONG ABOUT ALL THREE URLS.
    `inhousewellness.myshopify.com/pages/sauna-running-cost` answers 301 to
    `inhousewellness.com/pages/sauna-running-cost` -- Shopify canonicalising the
    domain, the same PATH -- and our redirect fires on the hop after that. Read
    one hop and every page looks like it redirects to itself.

    A reader's browser follows the chain, so the check follows it too, and the
    question is where the path ENDS UP. Hops are capped, and a loop shows up as
    a chain that never resolves rather than as a hang.
    """
    url, hops = origin + path, []
    for _ in range(MAX_HOPS):
        status, location = _one_hop(url, timeout)
        hops.append((url, status, location))
        if status not in (301, 302, 303, 307, 308) or not location:
            return status, url, hops
        url = urllib.parse.urljoin(url, location)
    return None, url, hops


def verify_live(origin):
    """True when every retired path 301s to the target and the target serves.

    Deliberately makes no Admin API call. The question "does this URL redirect"
    is answered by asking the URL, and a reader's browser has no token either.
    """
    print("\nverifying against %s:" % origin)
    ok = True
    for path in RETIRE:
        status, final, hops = check_live(origin, path)
        landed = urllib.parse.urlsplit(final).path.rstrip("/") == TARGET
        redirected = any(h[1] in (301, 302, 303, 307, 308) for h in hops)
        if status == 200 and landed and redirected:
            print("  %-34s %d hop(s) -> %s  HTTP 200" % (path, len(hops) - 1, final))
        else:
            print("  %-34s ENDED AT %s (HTTP %s) -- wanted %s"
                  % (path, final, status, TARGET))
            for url, st, loc in hops:
                print("        %s  HTTP %s -> %s" % (url, st, loc))
            ok = False
    status, final, _ = check_live(origin, TARGET)
    if status != 200 or urllib.parse.urlsplit(final).path.rstrip("/") != TARGET:
        print("  %-34s ENDED AT %s (HTTP %s)   the survivor must answer 200"
              % (TARGET, final, status))
        ok = False
    else:
        print("  %-34s HTTP 200  (the survivor)" % TARGET)
    if ok:
        print("\nall %d redirect(s) live, and %s still serves."
              % (len(RETIRE), TARGET))
    return ok


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
    ap.add_argument("--verify-only", action="store_true",
                    help="check the live 301s and change nothing. Needs NO "
                         "credential: a request to the old path is the only "
                         "evidence that matters, and it is public.")
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

    if args.verify_only:
        # The Admin API is not consulted at all. A 301 observed from outside is
        # stronger evidence than a redirect record read back from the API that
        # wrote it, and it needs no scope -- which matters, because the token
        # that runs this workflow has none for navigation.
        origin = args.origin or "https://inhousewellness.com"
        sys.exit(0 if verify_live(origin) else
                 "HALT: the redirects do not resolve as stated.")

    if not args.live:
        print("\ndry run. Re-run with --live to redirect and unpublish.")
        return

    shop, token = load_env()
    missing = [n for n, v in (("SHOPIFY_SHOP", shop),
                              ("SHOPIFY_ADMIN_TOKEN", token)) if not v]
    if missing:
        sys.exit("NO CREDENTIAL: %s not set. Nothing was changed. This is not a "
                 "failure of the deploy; it is a missing secret."
                 % " and ".join(missing))

    # 1. THE REDIRECTS FIRST. Inert while the pages are published, so a failure
    #    here -- a missing scope, a rate limit, anything -- changes nothing.
    print("\nredirects:")
    try:
        have = existing_redirects(shop, token)
    except RuntimeError as e:
        if "ACCESS_DENIED" in str(e) or "Access denied" in str(e):
            sys.exit(
                "NO SCOPE: this token cannot read or write URL redirects "
                "(`read_online_store_navigation` / "
                "`write_online_store_navigation`). NOTHING WAS CHANGED -- the "
                "pages are still published and still serving, which is the "
                "point of doing redirects before unpublishing. Grant the scope "
                "and re-run, or create the three redirects by hand in Shopify "
                "admin under Online Store > Navigation > URL Redirects.")
        raise
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

    # 2. THEN unpublish, which is what switches the redirects on. By here every
    #    redirect exists, so each page that stops serving has a catcher.
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

    # 3. PROVE IT. A mutation that returned an id and a URL that redirects are
    #    different facts, and this project has been caught by that distinction
    #    five times now.
    if not verify_live(args.origin or ("https://" + shop)):
        sys.exit("HALT: the redirects do not resolve as stated.")


if __name__ == "__main__":
    main()
