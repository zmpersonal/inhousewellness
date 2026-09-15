#!/usr/bin/env python3
"""Remove the True Total Cost files from a theme, and prove they are gone.

THIS IS THE ROLLBACK, AND IT IS EXERCISED RATHER THAN DESCRIBED.
A rollback nobody has run is a paragraph, not a plan. This project already
learned that about the live-theme guard -- a guard that has never fired has not
been tested -- and the lesson applies harder here, because the moment a rollback
is needed is the moment nobody wants to discover it was never tried.

WHAT IT REMOVES
Exactly `deploy_theme_files.MANIFEST`, which is the same list the deploy writes.
One list, so removal and deployment cannot drift into disagreeing about what the
calculator IS. Nothing else is touched: no settings, no config, no app block, no
template that was already in the theme.

REMOVING FROM THE LIVE THEME IS STILL A WRITE TO THE LIVE THEME
So it goes through the same guard, with the same named override. `--force` would
be wrong here for exactly the reason it is wrong in the deploy: the id has to be
typed twice and the two have to agree.

ORDER: THE TEMPLATE FIRST, THEN THE SECTION.
The mirror of the deploy's two passes, and for the same reason. Shopify refuses
a template whose section is missing, so a theme holding
`templates/page.sauna-cost.json` with `sections/true-total-cost.liquid` already
deleted is a theme that may not validate. Remove the thing that NAMES first,
then the thing NAMED.

    python3 scripts/rollback_calculator.py --theme-id 146278776899           # dry
    python3 scripts/rollback_calculator.py --theme-id 146278776899 --live
    python3 scripts/rollback_calculator.py --theme-id 146149867587 --live \
        --allow-live-theme-id 146149867587
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import (           # noqa: E402
    DELETE_M, ROLE_Q, announce_live_override, gql, load_env, refusal_for,
)
from scripts.deploy_theme_files import PASS_1, PASS_2, MANIFEST   # noqa: E402

# The mirror of the deploy order. See the module docstring.
REMOVE_ORDER = [("templates", list(PASS_2)), ("sections and assets", list(PASS_1))]

READ_Q = """query($id: ID!, $f: [String!]) {
  theme(id: $id) { name role files(first: 25, filenames: $f) {
    nodes { filename checksumMd5 } } } }"""


def removal_plan():
    """The passes, flattened, with nothing lost and nothing invented."""
    flat = [f for _, batch in REMOVE_ORDER for f in batch]
    return flat


def self_test():
    fails = []
    flat = removal_plan()
    if sorted(flat) != sorted(MANIFEST):
        fails.append("the removal plan and the deploy manifest disagree")
    if len(flat) != len(set(flat)):
        fails.append("a file appears twice in the removal plan")
    # The template is removed BEFORE the section it names.
    if flat.index("templates/page.sauna-cost.json") > flat.index("sections/true-total-cost.liquid"):
        fails.append("the section is removed before the template that names it")
    # Nothing outside the manifest can ever be reached.
    for f in flat:
        if not f.startswith(("assets/", "sections/", "templates/")):
            fails.append(f"removal plan names {f}, outside the three deploy folders")
        if "settings" in f or f.startswith("config/") or f.startswith("locales/"):
            fails.append(f"removal plan names {f}, which is a setting")
    # The guard is the deploy's guard, including the named override.
    if refusal_for({"name": "live", "role": "MAIN"}, "1") is None:
        fails.append("the live-theme guard did not refuse MAIN")
    if refusal_for({"name": "live", "role": "MAIN"}, "1", "2") is None:
        fails.append("an override naming another theme unlocked MAIN")
    if refusal_for({"name": "live", "role": "MAIN"}, "1", "1") is not None:
        fails.append("an override naming this theme did not unlock it")
    for f in fails:
        print("  FAIL " + f)
    if not fails:
        print(f"  ok   {len(flat)} file(s), template before section, manifest shared "
              f"with the deploy")
        print("  ok   the live-theme guard and its named override both fire")
    print("rollback self-test: " + ("clean" if not fails else f"{len(fails)} FAILED"))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id")
    ap.add_argument("--live", action="store_true", help="actually delete")
    ap.add_argument("--allow-live-theme-id", default=None,
                    help="DELIBERATE override, naming the theme it unlocks")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.theme_id:
        ap.error("--theme-id is required (or pass --self-test)")

    shop, token = load_env()
    if not (shop and token):
        sys.exit("NO CREDENTIAL: SHOPIFY_SHOP / SHOPIFY_ADMIN_TOKEN not set. "
                 "Nothing was sent. This is not a rollback failure; it is a "
                 "missing secret.")

    gid = f"gid://shopify/OnlineStoreTheme/{args.theme_id}"
    theme = gql(shop, token, ROLE_Q, {"id": gid})["theme"]
    refusal = refusal_for(theme, args.theme_id, args.allow_live_theme_id)
    if refusal:
        sys.exit(refusal)
    print(f"target: {theme['name']!r}  role={theme['role']}")
    used = announce_live_override(theme, args.theme_id, args.allow_live_theme_id)
    if used:
        print("\n" + "!" * 72 + f"\n{used}\n" + "!" * 72)

    flat = removal_plan()
    print(f"\nwould remove {len(flat)} file(s):")
    for f in flat:
        print("  - " + f)
    if not args.live:
        print("\ndry run. Re-run with --live to delete.")
        return 0

    for label, batch in REMOVE_ORDER:
        res = gql(shop, token, DELETE_M, {"id": gid, "files": batch})["themeFilesDelete"]
        errs = res.get("userErrors") or []
        gone = [n["filename"] for n in (res.get("deletedThemeFiles") or [])]
        print(f"\n{label}: deleted {len(gone)} of {len(batch)}")
        for e in errs:
            print(f"  error {e.get('filename')}: {e.get('code')} {e.get('message')}")
        if errs:
            # Do not carry on into the next pass: a half-removed calculator is a
            # theme holding a template whose section may already be gone.
            sys.exit("HALTED after an error. The theme is part-way; re-run.")

    # ABSENCE IS THE THING BEING CLAIMED, SO ABSENCE IS WHAT IS READ BACK.
    # A mutation that reported success and a file that is actually gone are
    # different facts -- the same rule the deploy reads its own writes by.
    nodes = gql(shop, token, READ_Q, {"id": gid, "f": flat})["theme"]["files"]["nodes"]
    left = sorted(n["filename"] for n in nodes)
    if left:
        print(f"\nFAILED: {len(left)} file(s) still present after the delete:")
        for n in left:
            print("  ! " + n)
        return 1
    print(f"\nread back: none of the {len(flat)} files remain in "
          f"{theme['name']!r}. The calculator is removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
