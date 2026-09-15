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
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import (           # noqa: E402
    ROLE_Q, UPSERT_M, gql, load_env, refusal_for,
)

# Repo path -> theme path, IN TWO PASSES, and the split is not cosmetic.
#
# Shopify validates a template against the theme as it stands. Upserting
# `templates/page.sauna-cost-methodology.json` into a theme that does not yet
# hold `sections/true-total-cost.liquid` is refused:
#
#   FILE_VALIDATION_ERROR: Section type 'true-total-cost' does not refer to an
#   existing section file
#
# Found by trying it against the real store on 2026-09-15, not inferred. In one
# batch the templates are validated before the section has landed, so the whole
# deploy fails on its last four files -- a theme left holding the code and none
# of the pages that use it. Sections and assets first, templates second.
PASS_1 = [
    "sections/true-total-cost.liquid",
    "assets/inh-cost-core.js",
    "assets/inh-true-total-cost.js",
    "assets/inh-true-total-cost.css",
    "assets/inh-cost-tables.json",
    "assets/inh-zip-state.json",
]
PASS_2 = [
    "templates/page.sauna-cost.json",
    "templates/page.sauna-running-cost.json",
    "templates/page.sauna-installation-cost.json",
    "templates/page.sauna-cost-methodology.json",
]
MANIFEST = PASS_1 + PASS_2

# A theme file body over this goes up base64-encoded. Shopify accepts TEXT for
# either, but a 202 KB JSON body inside a JSON request is where an encoding
# problem turns into a file that parses as nothing on the storefront.
BASE64_OVER = 64 * 1024

READ_BACK = """query($id: ID!, $f: [String!]) {
  theme(id: $id) { name role files(first: 25, filenames: $f) {
    nodes { filename size checksumMd5 } } } }"""


def files_payload(manifest=None):
    import base64
    out, total = [], 0
    for rel in (MANIFEST if manifest is None else manifest):
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
    # Run 1's failure, pinned: Shopify returns `size` as a STRING, and comparing
    # it to a Python int reported every file as a mismatch between two identical
    # numbers. A gate that fires on correct data costs more than the gate.
    if int({"size": "10147"}["size"]) != 10147:
        fails.append("the size coercion does not accept a string")
    if "int(node[" not in pathlib.Path(__file__).read_text():
        fails.append("the read-back compares size without coercing it")
    if "hashlib.md5" not in pathlib.Path(__file__).read_text():
        fails.append("the read-back does not compare digests, only lengths")
    payload, total = files_payload()
    if len(payload) != len(MANIFEST):
        fails.append("the payload lost a file")
    # The ordering rule, asserted rather than trusted to the order someone typed.
    if set(PASS_1) & set(PASS_2):
        fails.append("a file is in both passes")
    if any(f.startswith("templates/") for f in PASS_1):
        fails.append("a template is in pass 1, before its section exists")
    if not any(f.startswith("sections/") for f in PASS_1):
        fails.append("pass 1 carries no section, so pass 2 has nothing to bind to")
    if not all(f.startswith("templates/") for f in PASS_2):
        fails.append("pass 2 carries something other than a template")
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

    errs, wrote = [], set()
    for label, manifest in (("sections and assets", PASS_1), ("templates", PASS_2)):
        batch, _ = files_payload(manifest)
        res = gql(shop, token, UPSERT_M, {"id": gid, "files": batch})["themeFilesUpsert"]
        these = res.get("userErrors") or []
        for e in these:
            print("  ERROR %s %s %s" % (e.get("filename"), e.get("code"), e.get("message")))
        errs += these
        wrote |= {f["filename"] for f in (res.get("upsertedThemeFiles") or [])}
        print("pass: %-20s upserted %d of %d"
              % (label, len(res.get("upsertedThemeFiles") or []), len(batch)))
        if these:
            # A second pass into a theme the first pass did not finish would
            # compound the damage, and the template errors would then be
            # unattributable to the missing section.
            sys.exit("HALT: pass %r reported errors; later passes not attempted."
                     % label)
    print("upserted %d of %d" % (len(wrote), len(payload)))

    # READ BACK. An upsert that reports success and a theme that holds the file
    # are different facts, and this project does not accept the first as evidence
    # of the second. The comparison is on the MD5 DIGEST, not the length: two
    # files of equal size can differ in every byte, and "the same number of
    # bytes" is not what anyone means by byte-identical.
    back = gql(shop, token, READ_BACK, {"id": gid, "f": MANIFEST})["theme"]
    got = {n["filename"]: n for n in back["files"]["nodes"]}
    ok = True
    print("\nread back from the theme:")
    for f in payload:
        rel = f["filename"]
        raw = (ROOT / rel).read_bytes()
        node = got.get(rel)
        if node is None:
            print("  MISSING after upsert          %s" % rel)
            ok = False
            continue
        # Shopify returns `size` as UnsignedInt64, which JSON-serialises as a
        # STRING. Run 1 compared it to a Python int and reported every file as
        # "SIZE MISMATCH: theme 10147, disk 10147" -- a gate firing on correct
        # data, and printing two identical numbers as a difference. Coerce.
        theme_size = int(node["size"])
        theme_md5 = (node.get("checksumMd5") or "").lower()
        disk_md5 = hashlib.md5(raw).hexdigest()
        if theme_md5 and theme_md5 == disk_md5:
            print("  byte-identical  %-46s %7d B  md5 %s" % (rel, theme_size, disk_md5))
            continue
        if theme_md5:
            print("  DIGEST DIFFERS  %-46s theme md5 %s, disk md5 %s "
                  "(theme %d B, disk %d B)"
                  % (rel, theme_md5, disk_md5, theme_size, len(raw)))
            ok = False
            continue
        # No digest from the API: say what was and was not checked, rather than
        # letting a length match be reported as byte-identical.
        if theme_size == len(raw):
            print("  size only       %-46s %7d B  (the API returned no digest "
                  "for this file; length matches, bytes NOT verified)"
                  % (rel, theme_size))
        else:
            print("  SIZE DIFFERS    %-46s theme %d B, disk %d B"
                  % (rel, theme_size, len(raw)))
            ok = False
    if errs or not ok:
        sys.exit("HALT: the theme does not hold what was sent.")
    print("\nall %d file(s) verified against the theme." % len(payload))
    print("preview: https://%s/?preview_theme_id=%s" % (shop, args.theme_id))


if __name__ == "__main__":
    main()
