#!/usr/bin/env python3
"""Create or update the four Shopify pages the calculator renders into.

WHY A SCRIPT AND NOT A HANDFUL OF CONNECTOR CALLS
The methodology page body is 9 KB of prose. Relaying it through an agent's own
output means retyping it, and a typo in retyped prose is invisible until someone
reads the live page. Here the body is read from `content/pages/` as bytes and
sent as bytes, and the script reads it back and compares lengths before it says
anything happened.

WHY THE PAGES MATTER AT ALL
A theme preview renders a PAGE. `?preview_theme_id=` on a handle that does not
exist is a 404 with a preview parameter on it -- it looks like the theme is
broken when the truth is that nothing was ever created to preview.

⚠️ A PUBLISHED PAGE IS LIVE ON THE STORE IMMEDIATELY, on whatever theme is
currently MAIN. Until the preview theme is published, these four render through
MAIN's DEFAULT page template: the body text, no calculator. They are not linked
from any navigation, and `--pages draft` leaves them invisible -- at the cost of
the preview URLs returning 404, which is the trade the caller is making.

    python3 scripts/deploy_pages.py --pages publish
    python3 scripts/deploy_pages.py --self-test
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import gql, load_env      # noqa: E402

# handle -> (title, template suffix, body file). Stated as data so "which pages
# this round owns" is one list, and so the template suffix a page carries and
# the template file the theme deploy sends cannot drift apart silently --
# `self_test` asserts every suffix here has a `templates/page.<suffix>.json`.
PAGES = {
    "sauna-cost": ("Home Sauna Cost Calculator", "sauna-cost"),
    "sauna-running-cost": ("Home Sauna Running Cost Calculator", "sauna-running-cost"),
    "sauna-installation-cost": ("Home Sauna Installation Cost", "sauna-installation-cost"),
    "sauna-cost-methodology": ("How We Calculate Home Sauna Costs",
                               "sauna-cost-methodology"),
}

FIND_Q = """query($q: String!) {
  pages(first: 50, query: $q) { nodes { id handle title isPublished templateSuffix } } }"""
CREATE_M = """mutation($page: PageCreateInput!) {
  pageCreate(page: $page) { page { id handle isPublished templateSuffix }
    userErrors { field code message } } }"""
UPDATE_M = """mutation($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) { page { id handle isPublished templateSuffix }
    userErrors { field code message } } }"""
# READ BACK BY ID, never by search. Run 2 created all four pages correctly and
# then reported every one as "MISSING after write", because the read-back used a
# full-text query for "sauna" -- a different, weaker lookup than the one the
# existence check uses, and one a brand-new page may not be indexed for yet.
# The id comes back from the write itself, so there is nothing to search for.
READ_Q = """query($id: ID!) {
  page(id: $id) { id handle isPublished templateSuffix body } }"""


def body_of(handle):
    p = ROOT / "content" / "pages" / (handle + ".html")
    if not p.exists():
        sys.exit("HALT: no body for %s at %s. A page created with no body is a "
                 "blank page on a live store." % (handle, p.relative_to(ROOT)))
    return p.read_text()


def existing(shop, token):
    """handle -> page node, for the handles this script owns.

    Shopify's page search is a full-text query, not a handle filter: asking for
    "sauna" returns pages with no "sauna" in the handle at all. So the result is
    filtered HERE by exact handle. Trusting the search to have filtered would
    make an unrelated page look like ours and get overwritten.
    """
    found = {}
    for handle in PAGES:
        nodes = gql(shop, token, FIND_Q, {"q": handle})["pages"]["nodes"]
        for n in nodes:
            if n["handle"] == handle:
                found[handle] = n
    return found


def self_test():
    fails = []
    for handle, (title, suffix) in PAGES.items():
        if not (ROOT / "content" / "pages" / (handle + ".html")).exists():
            fails.append("no body file for %s" % handle)
        tpl = ROOT / "templates" / ("page.%s.json" % suffix)
        if not tpl.exists():
            fails.append("page %s wants templateSuffix %r and there is no %s"
                         % (handle, suffix, tpl.relative_to(ROOT)))
        if not title.strip():
            fails.append("page %s has no title" % handle)
    # The deploy manifest must actually SEND those templates, or the suffix
    # points at a file the theme will never hold.
    from scripts.deploy_theme_files import MANIFEST
    for _, suffix in PAGES.values():
        rel = "templates/page.%s.json" % suffix
        if rel not in MANIFEST:
            fails.append("%s is not in the theme deploy manifest" % rel)
    # A page search that returns unrelated pages must not be mistaken for a hit.
    fake = [{"handle": "about-us-page"}, {"handle": "sauna-payment-plans"}]
    if [n for n in fake if n["handle"] in PAGES]:
        fails.append("the handle filter would accept an unrelated page")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", choices=["skip", "draft", "publish"], default="draft",
                    help="draft = created but invisible (preview URLs 404). "
                         "publish = visible on the live store immediately.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: the page deploy failed its own controls:\n  "
                     + "\n  ".join(fails))
        print("page deploy self-test: every page has a body, a title and a "
              "template the theme deploy actually sends")
        return

    if args.pages == "skip":
        print("--pages skip: nothing created or changed.")
        return

    publish = args.pages == "publish"
    shop, token = load_env()
    missing = [n for n, v in (("SHOPIFY_SHOP", shop),
                              ("SHOPIFY_ADMIN_TOKEN", token)) if not v]
    if missing:
        sys.exit("NO CREDENTIAL: %s not set. Nothing was created. This is not a "
                 "failure of the deploy; it is a missing secret."
                 % " and ".join(missing))

    have = existing(shop, token)
    written = {}
    for handle, (title, suffix) in PAGES.items():
        body = body_of(handle)
        fields = {"title": title, "body": body, "templateSuffix": suffix,
                  "isPublished": publish}
        if handle in have:
            res = gql(shop, token, UPDATE_M,
                      {"id": have[handle]["id"], "page": fields})["pageUpdate"]
            verb = "updated"
        else:
            res = gql(shop, token, CREATE_M,
                      {"page": dict(fields, handle=handle)})["pageCreate"]
            verb = "created"
        errs = res.get("userErrors") or []
        if errs:
            for e in errs:
                print("  ERROR %s %s %s" % (e.get("field"), e.get("code"),
                                            e.get("message")))
            sys.exit("HALT: %s %s failed." % (verb, handle))
        written[handle] = res["page"]["id"]
        print("  %-9s %-26s suffix=%s published=%s"
              % (verb, handle, res["page"]["templateSuffix"],
                 res["page"]["isPublished"]))

    # READ BACK. A mutation that reports success and a store that holds the page
    # are different facts. Body LENGTH is compared, so a truncated or re-encoded
    # body cannot pass as a written one.
    print("\nread back (by id, from the write itself):")
    ok = True
    for handle, (title, suffix) in PAGES.items():
        want = body_of(handle)
        n = gql(shop, token, READ_Q, {"id": written[handle]})["page"]
        if n is None:
            print("  MISSING after write: %s (%s)" % (handle, written[handle]))
            ok = False
            continue
        same = len(n["body"] or "") == len(want)
        if not same:
            print("  BODY LENGTH MISMATCH %s: store %d, repo %d"
                  % (handle, len(n["body"] or ""), len(want)))
            ok = False
        if n["templateSuffix"] != suffix:
            print("  SUFFIX MISMATCH %s: store %r, wanted %r"
                  % (handle, n["templateSuffix"], suffix))
            ok = False
        if same and n["templateSuffix"] == suffix:
            print("  %-26s %d bytes, suffix %s, published=%s"
                  % (handle, len(want), suffix, n["isPublished"]))
    if not ok:
        sys.exit("HALT: the store does not hold what was sent.")

    print("\npreview URLs (unpublished theme):")
    for handle in PAGES:
        print("  https://%s/pages/%s?preview_theme_id=<THEME_ID>" % (shop, handle))
    print("\npage ids:")
    for handle, pid in written.items():
        print("  %-26s %s" % (handle, pid))
    if not publish:
        print("\nNOTE: --pages draft. These are NOT visible, so the URLs above "
              "return 404 until they are published.")


if __name__ == "__main__":
    main()
