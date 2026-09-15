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
import html as htmllib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import gql, load_env      # noqa: E402

# handle -> (title, template suffix, body file). Stated as data so "which pages
# this round owns" is one list, and so the template suffix a page carries and
# the template file the theme deploy sends cannot drift apart silently --
# `self_test` asserts every suffix here has a `templates/page.<suffix>.json`.
# ONE PAGE. Round 3 retired the other three into it -- four URLs rendering the
# same calculator split link equity four ways across ~67 referring domains and
# read as duplicate content. `scripts/deploy_redirects.py` owns the 301s, and its
# self-test asserts none of the retired handles has crept back into this map:
# republishing one would silently stop its redirect firing, because a published
# page beats a redirect.
PAGES = {
    "sauna-cost": ("Home Sauna Cost Calculator", "sauna-cost"),
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


# WHAT SHOPIFY DOES TO A PAGE BODY ON SAVE, established by reading one back
# rather than assumed: it PRETTY-PRINTS the markup. The methodology body went in
# as `<thead><tr><th>Figure</th>...` and came back as `<thead><tr>\n<th>Figure
# </th>\n...`, and `<li><strong>90 of` came back as `<li>\n<strong>90 of`.
# Sixteen bytes across 9 KB, every one of them whitespace inside block markup.
#
# So a byte or length comparison of a page body is a gate GUARANTEED to fire on
# correct data -- the EMF-literal lesson, in a different pipeline. The
# comparison is on the VISIBLE TEXT instead, and that is stricter about the
# thing that matters, not looser: it requires the reader-facing content to be
# IDENTICAL, character for character, where a length check would have passed a
# body with two words swapped.
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def visible_text(markup):
    """What a reader sees: tags removed, entities resolved, whitespace collapsed.

    Markup whitespace is the platform's to normalise. Words are not.
    """
    if markup is None:
        return ""
    txt = htmllib.unescape(_TAG.sub(" ", markup))
    return _WS.sub(" ", txt.replace("\u00a0", " ")).strip()


def first_difference(a, b, pad=60):
    """Where two texts diverge, with context. A mismatch has to be readable or
    nobody can act on it -- run 1 printed '10147, disk 10147' as a difference."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return ("at char %d\n      repo:  ...%s...\n      store: ...%s..."
            % (i, a[max(0, i - pad):i + pad], b[max(0, i - pad):i + pad]))


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

    # The text comparison, fired at the EXACT reflow Shopify performed on the
    # methodology body, and at a real content change that must still be caught.
    sent = "<table><thead><tr><th>Figure</th><th>Read on</th></tr></thead></table>"
    reflowed = ("<table>\n<thead><tr>\n<th>Figure</th>\n<th>Read on</th>\n"
                "</tr></thead>\n</table>")
    if visible_text(sent) != visible_text(reflowed):
        fails.append("the text comparison fails on Shopify's own reflow: %r vs %r"
                     % (visible_text(sent), visible_text(reflowed)))
    if len(sent) == len(reflowed):
        fails.append("the reflow control does not actually change the byte length, "
                     "so it cannot show that a length check would have failed")
    if visible_text("<p>47 of 139</p>") == visible_text("<p>48 of 139</p>"):
        fails.append("a changed FIGURE passes the text comparison")
    if visible_text("<li><strong>90 of 135</strong> state a spec</li>") != \
            "90 of 135 state a spec":
        fails.append("tag removal leaves markup in the text: %r"
                     % visible_text("<li><strong>90 of 135</strong> state a spec</li>"))
    if visible_text("8&nbsp;kW") != "8 kW":
        fails.append("a non-breaking space is not normalised")
    if visible_text(None) != "":
        fails.append("a missing body is not the empty string")
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
        want_txt, got_txt = visible_text(want), visible_text(n["body"])
        same = want_txt == got_txt
        if not same:
            print("  TEXT DIFFERS %s (%d chars stored vs %d in the repo) %s"
                  % (handle, len(got_txt), len(want_txt),
                     first_difference(want_txt, got_txt)))
            ok = False
        if n["templateSuffix"] != suffix:
            print("  SUFFIX MISMATCH %s: store %r, wanted %r"
                  % (handle, n["templateSuffix"], suffix))
            ok = False
        if same and n["templateSuffix"] == suffix:
            reflowed = len(n["body"] or "") != len(want)
            print("  %-26s text identical (%d chars)%s, suffix %s, published=%s"
                  % (handle, len(want_txt),
                     ", markup reflowed by Shopify" if reflowed else "",
                     suffix, n["isPublished"]))
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
