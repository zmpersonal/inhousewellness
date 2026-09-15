#!/usr/bin/env python3
"""Compare two themes file by file, by CHECKSUM, and say exactly what differs.

WHY THIS EXISTS
Round 4 takes the calculator live. The obvious route -- publish theme 13 -- would
swap the whole storefront to a copy of MAIN taken days earlier, silently
reverting anything changed on MAIN since. The safe route is to write the eleven
calculator files INTO MAIN, and the question that decides whether that is safe is
"what else has moved". This script answers it with evidence instead of memory.

It is also the measurement of the risk that publishing WOULD have carried: every
file that differs beyond the eleven is a change to MAIN that publishing theme 13
would have thrown away.

BY CHECKSUM, NOT BY SIZE OR DATE
Two files of equal size can differ in every byte, and `updatedAt` moves when a
theme is duplicated without any content changing. Shopify returns `checksumMd5`
per file; that is the only field here that answers "are these the same bytes".

A FILE PRESENT IN ONE THEME AND ABSENT IN THE OTHER IS NOT A DIFFERENCE IN
CONTENT -- it is a different fact, and the two are reported separately. Folding
them together would let "we added a file" read the same as "someone edited one".

    python3 scripts/diff_themes.py --a 146278776899 --b 146149867587
    python3 scripts/diff_themes.py --a ... --b ... --expect-only-manifest
    python3 scripts/diff_themes.py --self-test

Exit codes
    0  the comparison ran (and matched --expect-only-manifest, if given)
    1  the comparison ran and the difference is NOT the manifest alone
    2  refused: no credentials
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_theme_asset_path import gql, load_env          # noqa: E402

FILES_Q = """query($id: ID!, $after: String) {
  theme(id: $id) {
    id name role
    files(first: 250, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { filename checksumMd5 size }
    } } }"""


def all_files(shop, token, theme_id):
    """Every file in a theme, as {filename: (md5, size)}.

    Paginated to exhaustion. A partial listing compared against a full one
    reports every unread file as "missing from A", which is a confident and
    entirely false finding -- the same shape as the one-hop redirect check.
    """
    gid = f"gid://shopify/OnlineStoreTheme/{theme_id}"
    out, after, meta = {}, None, None
    while True:
        theme = gql(shop, token, FILES_Q, {"id": gid, "after": after})["theme"]
        if theme is None:
            raise RuntimeError(f"no theme with id {theme_id}")
        meta = (theme["name"], theme["role"])
        page = theme["files"]
        for n in page["nodes"]:
            out[n["filename"]] = (n["checksumMd5"], int(n["size"]))
        if not page["pageInfo"]["hasNextPage"]:
            return meta, out
        after = page["pageInfo"]["endCursor"]


def compare(a, b):
    """(only_in_a, only_in_b, changed). `changed` is [(name, md5_a, md5_b)].

    Pure, so the controls below exercise it with no network.
    """
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = sorted((n, a[n][0], b[n][0]) for n in set(a) & set(b)
                     if a[n][0] != b[n][0])
    return only_a, only_b, changed


def self_test():
    a = {"x": ("aaa", 1), "y": ("bbb", 2), "gone": ("ccc", 3)}
    b = {"x": ("aaa", 1), "y": ("ZZZ", 9), "new": ("ddd", 4)}
    cases = []
    only_a, only_b, changed = compare(a, b)
    cases.append((only_a == ["gone"], "a file only A holds is only_in_a"))
    cases.append((only_b == ["new"], "a file only B holds is only_in_b"))
    cases.append((changed == [("y", "bbb", "ZZZ")], "a moved checksum is a change"))
    cases.append(("x" not in [c[0] for c in changed], "an identical file is not a change"))
    # identity
    oa, ob, ch = compare(a, dict(a))
    cases.append((not oa and not ob and not ch, "a theme differs from itself in nothing"))
    # SIZE IS NEVER THE TEST: same bytes-count, different bytes, must be a change.
    s1, s2 = {"f": ("111", 100)}, {"f": ("222", 100)}
    cases.append((compare(s1, s2)[2] == [("f", "111", "222")],
                  "equal size with different md5 is still a change"))
    bad = 0
    for ok, why in cases:
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {why}")
    print("self-test: " + ("compare() holds" if not bad else f"{bad} FAILED"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", help="numeric theme id (the one carrying the change)")
    ap.add_argument("--b", help="numeric theme id (the baseline, e.g. MAIN)")
    ap.add_argument("--expect-only-manifest", action="store_true",
                    help="exit 1 unless the ONLY differences are the deploy manifest")
    ap.add_argument("--json", help="also write the full comparison here")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not (args.a and args.b):
        ap.error("--a and --b are required (or pass --self-test)")

    shop, token = load_env()
    if not (shop and token):
        print("REFUSED: SHOPIFY_SHOP / SHOPIFY_ADMIN_TOKEN not set.", file=sys.stderr)
        return 2

    (name_a, role_a), fa = all_files(shop, token, args.a)
    (name_b, role_b), fb = all_files(shop, token, args.b)
    print(f"A  {args.a}  {name_a!r}  role={role_a}  {len(fa)} files")
    print(f"B  {args.b}  {name_b!r}  role={role_b}  {len(fb)} files")
    print()

    only_a, only_b, changed = compare(fa, fb)

    print(f"only in A ({len(only_a)}):")
    for n in only_a:
        print(f"  + {n}  {fa[n][0]}  {fa[n][1]} bytes")
    print(f"\nonly in B ({len(only_b)}):")
    for n in only_b:
        print(f"  - {n}  {fb[n][0]}  {fb[n][1]} bytes")
    print(f"\ndifferent content ({len(changed)}):")
    for n, ma, mb in changed:
        print(f"  ~ {n}\n      A {ma}  {fa[n][1]} bytes\n      B {mb}  {fb[n][1]} bytes")

    differing = sorted(set(only_a) | set(only_b) | {c[0] for c in changed})
    print(f"\n{len(differing)} file(s) differ in total.")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps({
            "a": {"id": args.a, "name": name_a, "role": role_a, "files": len(fa)},
            "b": {"id": args.b, "name": name_b, "role": role_b, "files": len(fb)},
            "only_in_a": only_a, "only_in_b": only_b,
            "changed": [{"filename": n, "a": ma, "b": mb} for n, ma, mb in changed],
        }, indent=2) + "\n")

    if args.expect_only_manifest:
        from scripts.deploy_theme_files import MANIFEST
        extra = [n for n in differing if n not in set(MANIFEST)]
        if extra:
            print(f"\nSTOP: {len(extra)} file(s) differ that are NOT in the deploy "
                  f"manifest. Each one is a change made to B since A was copied, "
                  f"and is exactly what publishing A would have reverted:")
            for n in extra:
                print(f"  ! {n}")
            return 1
        print("\nthe difference is the deploy manifest and nothing else.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
