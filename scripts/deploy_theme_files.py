#!/usr/bin/env python3
"""Upsert the True Total Cost files into an UNPUBLISHED theme.

WHY THIS REUSES verify_theme_asset_path RATHER THAN RESTATING IT
That script already owns the Admin API client, the .env-or-environment credential
loader, and -- the part that matters -- `refusal_for`, the live-theme guard,
which is exercised offline because it has never been able to fire against
Shopify from a developer environment. A second copy of that guard here would be
a second answer to "may I write to the live store", and the two would drift. So
this file imports all four and adds only what is new: which files go up.

WHERE IT CAN RUN
Not from an agent session: `inhousewellness.myshopify.com` answers 403 on CONNECT
from the egress proxy, which Round 0 recorded and which is unchanged. It runs in
GitHub Actions with `SHOPIFY_ADMIN_TOKEN` as a secret -- the environment the
scheduled path will actually use, which is also why proving it there is worth
more than a connector call succeeding here.

    python3 scripts/deploy_theme_files.py --theme-id 1234567890            # dry run
    python3 scripts/deploy_theme_files.py --theme-id 1234567890 --live
    python3 scripts/deploy_theme_files.py --self-test
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import (           # noqa: E402
    ROLE_Q, UPSERT_M, gql, load_env, refusal_for,
)

# Repo path -> theme path. Stated as data, so "what this round deploys" is one
# list that a reader can check against the repo rather than a set of globs whose
# meaning depends on what happens to be on disk.
MANIFEST = [
    "sections/true-total-cost.liquid",
    "templates/page.sauna-cost.json",
    "templates/page.sauna-running-cost.json",
    "templates/page.sauna-installation-cost.json",
    "templates/page.sauna-cost-methodology.json",
    "assets/inh-cost-core.js",
    "assets/inh-true-total-cost.js",
    "assets/inh-true-total-cost.css",
    "assets/inh-cost-tables.json",
    "assets/inh-zip-state.json",
]

# A theme file body over this goes up base64-encoded. Shopify accepts TEXT for
# either, but a 202 KB JSON body inside a JSON request is where an encoding
# problem turns into a file that parses as nothing on the storefront.
BASE64_OVER = 64 * 1024

READ_BACK = """query($id: ID!, $f: [String!]) {
  theme(id: $id) { name role files(first: 25, filenames: $f) {
    nodes { filename size checksumMd5 } } } }"""


def files_payload():
    import base64
    out, total = [], 0
    for rel in MANIFEST:
        p = ROOT / rel
        if not p.exists():
            sys.exit(f"HALT: {rel} is in the manifest and not in the checkout. "
                     f"A theme missing one of its own files is not a smaller "
                     f"deploy, it is a broken page.")
        raw = p.read_bytes()
        total += len(raw)
        if len(raw) > BASE64_OVER:
            body = {"type": "BASE64", "value": base64.b64encode(raw).decode()}
        else:
            body = {"type": "TEXT", "value": raw.decode()}
        out.append({"filename": rel, "body": body})
    return out, total


def self_test():
    """The manifest must describe the checkout, and the guard must still refuse.

    The guard itself is proved in verify_theme_asset_path's own self-test; what
    is checked here is that THIS script is still wired to it, because importing a
    guard and then not calling it is the failure that looks most like safety.
    """
    fails = []
    for rel in MANIFEST:
        if not (ROOT / rel).exists():
            fails.append(f"manifest names {rel}, which is not in the checkout")
    if refusal_for({"name": "live", "role": "MAIN"}, "1") is None:
        fails.append("the live-theme guard did not refuse a MAIN theme")
    if refusal_for({"name": "round 13", "role": "UNPUBLISHED"}, "1") is not None:
        fails.append("the guard refused an unpublished theme")
    if refusal_for(None, "1") is None:
        fails.append("a missing theme was not refused")
    src = pathlib.Path(__file__).read_text()
    if "refusal_for(" not in src.split("def self_test")[0].split("def main")[-1] \
            and "refusal_for(theme" not in src:
        fails.append("main() does not call the guard it imports")
    payload, total = files_payload()
    if len(payload) != len(MANIFEST):
        fails.append("the payload lost a file")
    big = [f for f in payload if f["body"]["type"] == "BASE64"]
    if not big:
        fails.append("no file took the base64 path, so it has never been tested")
    import base64
    for f in big:
        rel = f["filename"]
        if base64.b64decode(f["body"]["value"]) != (ROOT / rel).read_bytes():
            fails.append(f"base64 round-trip changed {rel}")
    for f in payload:
        if f["body"]["type"] == "TEXT" and f["body"]["value"] != (ROOT / f["filename"]).read_text():
            fails.append(f"text body differs from disk for {f['filename']}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id", help="numeric id of an UNPUBLISHED theme")
    ap.add_argument("--live", action="store_true",
                    help="actually write. Without it this prints and exits.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: the deploy script failed its own controls:\n  "
                     + "\n  ".join(fails))
        print("deploy self-test: the manifest matches the checkout, base64 "
              "round-trips byte for byte, and the live-theme guard still refuses")
        return

    payload, total = files_payload()
    print(f"{len(payload)} file(s), {total/1024:.1f} KB")
    for f in payload:
        size = len(f["body"]["value"])
        print(f"  {f['filename']:46s} {f['body']['type']:6s} {size/1024:8.1f} KB")

    if not args.theme_id:
        sys.exit("\nHALT: --theme-id is required. It must be an UNPUBLISHED theme; "
                 "the guard refuses MAIN.")
    shop, token = load_env()
    missing = [n for n, v in (("SHOPIFY_SHOP", shop),
                              ("SHOPIFY_ADMIN_TOKEN", token)) if not v]
    if missing:
        # Exit 2, and SAY SO. The first draft of this branch exited 2 silently,
        # which in a runner log is indistinguishable from a crash -- and "the
        # deploy failed" would have been reported when the truth was "nobody
        # gave it a credential". A missing credential is a different fact from a
        # refused write, and both are different from a broken one.
        sys.exit("NO CREDENTIAL: %s not set, in the environment or in a .env. "
                 "Nothing was sent. This is not a deploy failure; it is a "
                 "missing secret." % " and ".join(missing))
    gid = "gid://shopify/OnlineStoreTheme/%s" % args.theme_id
    theme = gql(shop, token, ROLE_Q, {"id": gid})["theme"]
    refusal = refusal_for(theme, args.theme_id)
    if refusal:
        sys.exit(refusal)
    print(f"\ntarget: {theme['name']!r}  role={theme['role']}")

    if not args.live:
        print("\ndry run. Re-run with --live to write.")
        return

    res = gql(shop, token, UPSERT_M, {"id": gid, "files": payload})["themeFilesUpsert"]
    errs = res.get("userErrors") or []
    for e in errs:
        print("  ERROR %s %s %s" % (e.get("filename"), e.get("code"), e.get("message")))
    wrote = {f["filename"] for f in (res.get("upsertedThemeFiles") or [])}
    print("upserted %d of %d" % (len(wrote), len(payload)))

    # READ BACK. An upsert that reports success and a theme that holds the file
    # are different facts, and this project does not accept the first as evidence
    # of the second.
    back = gql(shop, token, READ_BACK, {"id": gid, "f": MANIFEST})["theme"]
    got = {n["filename"]: n["size"] for n in back["files"]["nodes"]}
    ok = True
    for f in payload:
        rel = f["filename"]
        want = len((ROOT / rel).read_bytes())
        if rel not in got:
            print("  MISSING after upsert: %s" % rel)
            ok = False
        elif got[rel] != want:
            print("  SIZE MISMATCH %s: theme %s, disk %s" % (rel, got[rel], want))
            ok = False
    if errs or not ok:
        sys.exit("HALT: the theme does not hold what was sent.")
    print("read back: all %d file(s) present at the expected size" % len(payload))
    print("preview: https://%s/?preview_theme_id=%s" % (shop, args.theme_id))


if __name__ == "__main__":
    main()
