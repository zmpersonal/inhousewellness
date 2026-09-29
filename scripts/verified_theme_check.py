#!/usr/bin/env python3
"""Governance gate (CLAUDE.md, "Before any theme is published"): does theme ID carry INH Verified?

    .venv/bin/python scripts/verified_theme_check.py --theme-id 1234567890

Run by ANY project in this repo (inh-seo included) before publishing a theme. Exit 0 only when:
  1. the theme holds every INH Verified template, section, snippet and asset, each identical to the
     repo's copy (MD5, or parsed JSON for templates Shopify re-serialises);
  2. its layout carries the metaobject title branch, and its product template places the
     `inh_verified_link` section directly after the enabled reviews section;
  3. on that theme's PREVIEW, the hub renders exactly one row per ACTIVE entry (the hub row check)
     and one active model page passes the value-match check.
Read-only: it never writes to the theme or the store. A preview is the only way to see an
unpublished theme, so this is the one check that uses preview_theme_id on purpose.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_deploy as vd  # noqa: E402
import verified_golive as g  # noqa: E402

LAYOUT_MARK = "INH Verified model pages (Round 2)"


def file_problems(q, theme_id):
    names = g.NEW_FILES + vd.PATCHED
    got = vd.read_files(q, theme_id, names)
    probs = []
    for n in g.NEW_FILES:
        if n not in got:
            probs.append(f"missing {n}")
            continue
        local = (ROOT / n).read_bytes()
        if got[n]["checksumMd5"] == vd.md5(local):
            continue
        if n.endswith(".json") and vd.split_json_template(got[n]["body"]["content"])[1] == vd.split_json_template(local.decode())[1]:
            continue
        probs.append(f"{n} differs from the repo")
    lay = got.get("layout/theme.liquid")
    if not lay or LAYOUT_MARK not in lay["body"]["content"]:
        probs.append("layout/theme.liquid lacks the metaobject title branch")
    prod = got.get("templates/product.json")
    if not prod:
        probs.append("missing templates/product.json")
    else:
        _, d = vd.split_json_template(prod["body"]["content"])
        rev = [k for k in d["order"] if any(vd.REVIEW_BLOCK in b["type"] and not b.get("disabled")
                                            for b in d["sections"][k].get("blocks", {}).values())]
        i = d["order"].index(vd.LINK_SECTION_ID) if vd.LINK_SECTION_ID in d["order"] else -1
        if len(rev) != 1 or i < 1 or d["order"][i - 1] != rev[0]:
            probs.append("product template: the link section is not directly after the reviews section")
    return probs


def preview_problems(q, theme_id):
    import verified_checks as vc
    import verified_pages as vp
    active = [e for e in g.all_entries(q) if e["capabilities"]["publishable"]["status"] == "ACTIVE"]
    ids = [{x["key"]: x["value"] for x in e["fields"]}["inh_id"] for e in active]
    probs, jar = [], http.cookiejar.CookieJar()
    status, page = g.fetch(f"{g.STORE}/pages/sauna-database?preview_theme_id={theme_id}", jar)
    th = g.theme_of(page)
    if status != 200 or not th or str(th["id"]) != str(theme_id):
        return [f"hub preview not served by theme {theme_id} (HTTP {status}, theme {th})"], len(ids)
    p = g.hub_rows_problem(vc.main_of(page), ids)
    if p:
        probs.append(f"hub: {p}")
    if active:
        ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
        pages = {pd["handle"]: pd for pd, _, _ in vd._pages_and_records()}
        h = sorted(e["handle"] for e in active)[0]
        status, page = g.fetch(f"{g.STORE}/pages/sauna-database/{h}", jar)   # same jar: still the preview
        th = g.theme_of(page)
        errs = []
        if status != 200 or not th or str(th["id"]) != str(theme_id):
            errs.append(f"model preview not served by theme {theme_id} (HTTP {status})")
        else:
            vc.check_model(ds[pages[h]["inh_id"]], vp.load_titles()[pages[h]["inh_id"]], page, pages[h], errs)
        probs += [f"model {h}: {e}" for e in errs]
    return probs, len(ids)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme-id", required=True)
    a = ap.parse_args(argv)
    q = vd.admin()
    theme = q(vd.THEME_Q, {"id": f"gid://shopify/OnlineStoreTheme/{a.theme_id}"})["theme"]
    if not theme:
        print(f"THEME CHECK: FAIL (no theme {a.theme_id})")
        return 1
    print(f"theme {a.theme_id} {theme['name']!r} role {theme['role']}")
    probs = file_problems(q, a.theme_id)
    print(f"files: {'PASS' if not probs else probs}")
    pprobs, n_active = preview_problems(q, a.theme_id) if not probs else (["skipped: files incomplete"], 0)
    print(f"preview ({n_active} active entries): {'PASS' if not pprobs else pprobs}")
    ok = not probs and not pprobs
    print("THEME CHECK:", "PASS" if ok else "FAIL: do not publish this theme")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
