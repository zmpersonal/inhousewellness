#!/usr/bin/env python3
"""Prove the exact Admin API call a scheduled job will make to ship a JSON asset.

This is the Round 0 "path confirmation": write a small JSON file to an
UNPUBLISHED theme's assets using only the token from the environment, read it
back, confirm it matches byte for byte, then remove it. No connector, no
interactive auth, no Shopify CLI -- the same mechanism a GitHub Actions cron has.

    SHOPIFY_SHOP=inhousewellness.myshopify.com SHOPIFY_ADMIN_TOKEN=... \
        python3 scripts/verify_theme_asset_path.py --theme-id 146147868739

Exit codes
    0  the round trip succeeded and the probe file was removed
    2  refused to run: no credentials, or the target is the live theme
    1  the round trip failed; the message names which step

SAFETY
    The script reads the target theme's role first and REFUSES on role == MAIN.
    inhousewellness.com is a live commercial store; "I meant to pass the other
    id" is not a recoverable mistake. --theme-id is required; there is no
    default, because a default is how the wrong theme gets written to.

ON READING BACK
    The read-back is done through the Admin API rather than through the CDN url
    that `{{ 'x.json' | asset_url }}` renders. A CDN miss is not evidence the
    write failed -- it is evidence of caching -- and the project has been bitten
    before by reading a delivery-layer symptom as a storage-layer fact. If you
    also want the rendered-URL leg, request it against the theme PREVIEW with
    the preview cookie primed, exactly as inh-seo/scripts/audit/verify-render.js
    learned to do; fetching without priming reads the LIVE theme and reports a
    false failure.
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROBE_PATH = "assets/_inh-path-check.json"
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2026-07")


def load_env():
    """Environment first, .env second. A CI runner has no file; a laptop has no
    exported vars. Returns (shop, token), either of which may be None -- the
    caller branches, it does not default."""
    shop = os.environ.get("SHOPIFY_SHOP")
    token = os.environ.get("SHOPIFY_ADMIN_TOKEN")
    for candidate in (ROOT / ".env", ROOT / "inh-seo" / ".env"):
        if shop and token:
            break
        if not candidate.exists():
            continue
        for line in candidate.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            if k.strip() == "SHOPIFY_SHOP" and not shop:
                shop = v
            elif k.strip() == "SHOPIFY_ADMIN_TOKEN" and not token:
                token = v
    return shop, token


def gql(shop, token, query, variables):
    req = urllib.request.Request(
        f"https://{shop}/admin/api/{API_VERSION}/graphql.json",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read())
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {json.dumps(body['errors'])}")
    return body["data"]


ROLE_Q = "query($id: ID!) { theme(id: $id) { id name role } }"
READ_Q = """query($id: ID!, $f: [String!]) {
  theme(id: $id) { files(first: 1, filenames: $f) { nodes { filename size
    body { ... on OnlineStoreThemeFileBodyText { content } } } } } }"""
UPSERT_M = """mutation($id: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $id, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { filename code message } } }"""
DELETE_M = """mutation($id: ID!, $files: [String!]!) {
  themeFilesDelete(themeId: $id, files: $files) {
    deletedThemeFiles { filename }
    userErrors { filename code message } } }"""


def refusal_for(theme, theme_id, allow_live_theme_id=None):
    """The live-theme guard, split out so it can be exercised without a network.

    The guard protects a live commercial store and, in this environment, it has
    never fired against Shopify -- the transport is blocked before the role check
    is reached. A guard that has never failed has not been tested, so --self-test
    fires it here instead. Returns a message to refuse with, or None to proceed.

    THE LIVE OVERRIDE NAMES ITS TARGET, WHICH IS WHY IT IS NOT A `--force`.
    Round 4 deploys the calculator into MAIN deliberately, so the guard needs an
    exception -- but an exception spelled `--force` unlocks whatever id happens
    to be in the variable, and "I meant to pass the other id" is exactly the
    mistake this guard exists to catch. `allow_live_theme_id` must equal the id
    being written to. Naming the WRONG id does not unlock anything: it is a
    second chance to notice, not a second key.

    The guard is not weakened. MAIN is still refused by default, a missing theme
    is still refused, and unlocking is not silent -- `announce_live_override`
    prints the used exception, and every caller prints it before writing.
    """
    if theme is None:
        return f"FAILED: no theme with id {theme_id}"
    if theme.get("role") == "MAIN":
        if allow_live_theme_id is not None and str(allow_live_theme_id) == str(theme_id):
            return None
        if allow_live_theme_id is not None:
            return (f"REFUSED: theme {theme_id} ({theme.get('name')!r}) is the LIVE theme "
                    f"and the live override names {allow_live_theme_id}, not {theme_id}. "
                    f"The override must name the theme it unlocks.")
        return (f"REFUSED: theme {theme_id} ({theme.get('name')!r}) is the LIVE theme. "
                f"Pass an unpublished theme.")
    return None


def announce_live_override(theme, theme_id, allow_live_theme_id):
    """The one line that must appear in the log when the guard was unlocked.

    A guard that can be turned off without leaving a trace is a guard nobody can
    audit afterwards. Returns None when no override was in play, so a caller can
    print it unconditionally.
    """
    if allow_live_theme_id is None or theme is None:
        return None
    if theme.get("role") != "MAIN":
        return None
    if str(allow_live_theme_id) != str(theme_id):
        return None
    return (f"LIVE-THEME OVERRIDE USED: writing to MAIN theme {theme_id} "
            f"({theme.get('name')!r}). The guard refused by default and was "
            f"unlocked by an override naming this exact id.")


def self_test():
    MAIN = {"name": "Round 12 — live", "role": "MAIN"}
    cases = [
        (MAIN, "123", None, True, "live theme must be refused"),
        ({"name": "Round 11 — staging", "role": "UNPUBLISHED"}, "123", None, False,
         "unpublished theme must pass"),
        ({"name": "odd", "role": "DEVELOPMENT"}, "123", None, False,
         "development theme must pass"),
        (None, "123", None, True, "missing theme must be refused"),
        # The override names its target, so a MISMATCHED override unlocks nothing.
        (MAIN, "123", "999", True, "an override naming another id must still refuse"),
        (MAIN, "123", "123", False, "an override naming this id unlocks it"),
        # and it cannot resurrect a theme that is not there
        (None, "123", "123", True, "an override cannot unlock a missing theme"),
    ]
    bad = 0
    for theme, tid, allow, want_refusal, why in cases:
        got = refusal_for(theme, tid, allow) is not None
        ok = got == want_refusal
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {why}")

    # Unlocking is never silent, and nothing else announces an override.
    noisy = [
        (announce_live_override(MAIN, "123", "123") is not None, "a used override is announced"),
        (announce_live_override(MAIN, "123", "999") is None, "a refused override announces nothing"),
        (announce_live_override(MAIN, "123", None) is None, "no override, no announcement"),
        (announce_live_override({"role": "UNPUBLISHED"}, "123", "123") is None,
         "an unpublished theme never announces an override"),
    ]
    for ok, why in noisy:
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {why}")
    print("self-test: " + ("all guards fire as specified" if not bad else f"{bad} FAILED"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id", help="numeric id of an UNPUBLISHED theme (no default, on purpose)")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise the live-theme guard offline and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.theme_id:
        ap.error("--theme-id is required (or pass --self-test)")

    shop, token = load_env()
    missing = [n for n, v in (("SHOPIFY_SHOP", shop), ("SHOPIFY_ADMIN_TOKEN", token)) if not v]
    if missing:
        print(f"REFUSED: {' and '.join(missing)} not set in the environment or a .env file.",
              file=sys.stderr)
        print("This script exists to prove the credentialed path; it will not fall back to "
              "a connector, because a connector is not what the cron will use.", file=sys.stderr)
        return 2

    gid = f"gid://shopify/OnlineStoreTheme/{args.theme_id}"
    payload = json.dumps({"probe": "inh-path-check", "schema": 1}, indent=1) + "\n"

    theme = gql(shop, token, ROLE_Q, {"id": gid})["theme"]
    refusal = refusal_for(theme, args.theme_id)
    if refusal:
        print(refusal, file=sys.stderr)
        return 1 if theme is None else 2
    print(f"target: {theme['name']!r}  role={theme['role']}  -- not live, proceeding")

    up = gql(shop, token, UPSERT_M, {
        "id": gid, "files": [{"filename": PROBE_PATH, "body": {"type": "TEXT", "value": payload}}]})
    errs = up["themeFilesUpsert"]["userErrors"]
    if errs:
        print(f"FAILED at write: {json.dumps(errs)}", file=sys.stderr)
        return 1
    print(f"wrote {PROBE_PATH} ({len(payload)} bytes)")

    nodes = gql(shop, token, READ_Q, {"id": gid, "f": [PROBE_PATH]})["theme"]["files"]["nodes"]
    if not nodes:
        # Absence is not proof of anything except absence. Say so and stop --
        # do not re-write and do not report success on a silent read.
        print("FAILED at read-back: the file is not listed. The write reported no error, so "
              "this is unresolved, not a clean failure. Check the theme in admin before rerunning.",
              file=sys.stderr)
        return 1
    got = nodes[0]["body"]["content"]
    if got != payload:
        print(f"FAILED: round trip changed the bytes.\n  sent {len(payload)}  got {len(got)}",
              file=sys.stderr)
        return 1
    print("read back byte-identical")

    dl = gql(shop, token, DELETE_M, {"id": gid, "files": [PROBE_PATH]})
    errs = dl["themeFilesDelete"]["userErrors"]
    if errs:
        print(f"WROTE AND VERIFIED, BUT CLEANUP FAILED -- remove {PROBE_PATH} by hand: "
              f"{json.dumps(errs)}", file=sys.stderr)
        return 1
    print(f"removed {PROBE_PATH}")
    print("PATH CONFIRMED: env token -> Admin API -> unpublished theme asset -> read back -> removed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"FAILED at transport: {e}", file=sys.stderr)
        sys.exit(1)
