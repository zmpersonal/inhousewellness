#!/usr/bin/env python3
"""INH Verified go-live: the approved step that may write to the LIVE theme.

    .venv/bin/python scripts/verified_golive.py setup --write          # definition + 131 DRAFT entries + metafields
    .venv/bin/python scripts/verified_golive.py verify-entries         # read every entry back, value-check vs saunas.json
    .venv/bin/python scripts/verified_golive.py preview-proof          # link renders nothing while its entry is draft
    .venv/bin/python scripts/verified_golive.py snapshot-main          # MAIN's files this deploy touches -> repo
    .venv/bin/python scripts/verified_golive.py deploy-main --allow-live-theme-id ID [--write]
    .venv/bin/python scripts/verified_golive.py rollback [--execute --allow-live-theme-id ID]   # default: dry run
    .venv/bin/python scripts/verified_golive.py activate --handles H [H ...] [--write]
    .venv/bin/python scripts/verified_golive.py publish-pages [--write]
    .venv/bin/python scripts/verified_golive.py live-check [--links]  # value match etc. against the LIVE html
    .venv/bin/python scripts/verified_golive.py live-shots

GUARDS
  * MAIN is resolved from the Admin API at run time and logged. A write to it needs
    --allow-live-theme-id naming that exact id; the banner is printed BEFORE any upsert.
  * The snapshot gate runs seconds before the upsert: MAIN's patched files must still be
    byte-identical (MD5) to the committed snapshot, and every file this deploy creates must
    still be absent. Otherwise nothing is written.
  * The layout and product template are PATCHED from the snapshot (MAIN's own files), never
    copied from the preview theme.
  * Entries are created DRAFT. Only `activate` sets ACTIVE, and only for the handles named.
  * Every write is read back: MD5 for theme files, parsed JSON for Shopify-reformatted JSON
    templates, value-by-value for entries and metafields.
"""
from __future__ import annotations

import argparse
import difflib
import html as htmllib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_deploy as vd  # noqa: E402

GOLIVE = ROOT / "data/verified/golive"
STATE = GOLIVE / "launch-state.json"
EVIDENCE = ROOT / "docs/verified/golive"
NEW_FILES = vd.PASS_1 + vd.PASS_2 + vd.PASS_3 + ["templates/llms.txt.liquid"]   # llms.txt: Round 4
STORE = "https://inhousewellness.com"
UA = "InHouseWellness-verify/1.0 (+data@inhousewellness.com)"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(**kv):
    s = load_state()
    s.update(kv)
    GOLIVE.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2, sort_keys=True) + "\n")


# --------------------------------------------------------------- entries --

DEF_FULL_Q = """query { metaobjectDefinitionByType(type: "sauna") { id type name access { admin storefront }
  capabilities { publishable { enabled } renderable { enabled } onlineStore { enabled data { urlHandle } } }
  fieldDefinitions { key required type { name } } } }"""
LIST_Q = """query($a: String) { metaobjects(type: "sauna", first: 100, after: $a) { pageInfo { hasNextPage endCursor }
  nodes { id handle capabilities { publishable { status } } fields { key value } } } }"""
STATUS_M = """mutation($id: ID!, $m: MetaobjectUpdateInput!) { metaobjectUpdate(id: $id, metaobject: $m) {
  metaobject { id handle capabilities { publishable { status } } } userErrors { field message code } } }"""


def all_entries(q):
    out, after = [], None
    while True:
        r = q(LIST_Q, {"a": after})["metaobjects"]
        out += r["nodes"]
        if not r["pageInfo"]["hasNextPage"]:
            return out
        after = r["pageInfo"]["endCursor"]


def check_definition(q):
    d = q(DEF_FULL_Q)["metaobjectDefinitionByType"]
    want = {f["key"]: f["type"] for f in vd.definition_input()["fieldDefinitions"]}
    errs = []
    if not d:
        return ["no 'sauna' definition"], None
    if d["capabilities"]["onlineStore"] is None or not d["capabilities"]["onlineStore"]["enabled"]:
        errs.append("online store (web pages) not enabled")
    elif d["capabilities"]["onlineStore"]["data"]["urlHandle"] != "sauna-database":
        errs.append(f"urlHandle {d['capabilities']['onlineStore']['data']['urlHandle']!r} != 'sauna-database'")
    if not d["capabilities"]["publishable"]["enabled"]:
        errs.append("publishable (draft/active) not enabled")
    if d["access"]["storefront"] != "PUBLIC_READ":
        errs.append(f"storefront access {d['access']['storefront']}")
    got = {f["key"]: f["type"]["name"] for f in d["fieldDefinitions"]}
    if got != want:
        errs.append(f"fields differ: {sorted(set(got.items()) ^ set(want.items()))}")
    return errs, d


def verify_entries(q=None, expect_active=()):
    """Every entry read back and value-checked against saunas.json, independently of the
    payload builder: the record is compared with the dataset record minus internal keys."""
    import verified_pages as vp
    q = q or vd.admin()
    ds = {r["inh_id"]: r for r in json.loads((ROOT / "data/verified/saunas.json").read_text())["records"]}
    expected = {pd["handle"]: (pd, gid) for pd, _, gid in vd._pages_and_records()}
    got = {e["handle"]: e for e in all_entries(q)}
    errs = []
    if set(got) != set(expected):
        errs.append(f"entry set differs: missing {sorted(set(expected) - set(got))[:5]}, extra {sorted(set(got) - set(expected))[:5]}")
    for h, (pd, gid) in expected.items():
        e = got.get(h)
        if not e:
            continue
        f = {x["key"]: x["value"] for x in e["fields"]}
        status = e["capabilities"]["publishable"]["status"]
        want_status = "ACTIVE" if h in expect_active else "DRAFT"
        if status != want_status:
            errs.append(f"{h}: status {status}, expected {want_status}")
        rec = json.loads(f.get("record") or "null")
        truth = {k: v for k, v in ds[pd["inh_id"]].items() if k not in vp.INTERNAL_KEYS}
        if rec != truth:
            errs.append(f"{h}: record differs from saunas.json")
        if json.loads(f.get("page_data") or "null") != pd:
            errs.append(f"{h}: page_data differs from the built page")
        for k in ("title", "inh_id", "brand", "heat_type", "capacity_label", "seo_title", "seo_description", "verified_date"):
            if f.get(k) != pd[k]:
                errs.append(f"{h}: field {k} {f.get(k)!r} != {pd[k]!r}")
        if (f.get("store_product") or None) != gid:
            errs.append(f"{h}: store_product {f.get('store_product')} != {gid}")
        try:
            vd.lint_payload(json.dumps(f, ensure_ascii=False), h)
        except SystemExit as x:
            errs.append(str(x))
    return errs, len(got)


MF_LIST_Q = """query($id: ID!) { product(id: $id) { id handle metafield(namespace: "inh_verified", key: "sauna") { value } } }"""


def verify_metafields(q):
    errs, n = [], 0
    for pd, _, gid in vd._pages_and_records():
        if not gid:
            continue
        e = vd._entry_gid(q, pd["handle"])
        mf = q(MF_LIST_Q, {"id": gid})["product"]["metafield"]
        n += 1
        if not mf or mf["value"] != e:
            errs.append(f"{gid}: metafield {mf and mf['value']} != entry {e}")
    return errs, n


def setup(write):
    q = vd.admin()
    missing = {"write_metaobject_definitions", "write_metaobjects", "write_products"} - vd.scopes(q)
    if missing:
        raise SystemExit(f"HALT: token lacks {sorted(missing)}")
    if not write:
        print("dry run: would create the definition, 131 DRAFT entries, the metafield definition and the metafields")
        return
    if not vd.deploy_entries(True, q):
        raise SystemExit("HALT: entries not written")
    errs, d = check_definition(q)
    print(f"definition read back: {d and d['id']} urlHandle "
          f"{d and d['capabilities']['onlineStore'] and d['capabilities']['onlineStore']['data']['urlHandle']}; "
          f"{'OK' if not errs else errs}")
    if errs:
        raise SystemExit("HALT: definition read-back failed")
    errs, n = verify_entries(q)
    print(f"entries read back: {n}; value check {'PASS' if not errs else errs[:5]}")
    if errs:
        raise SystemExit("HALT: entry read-back failed")
    before = sorted(vd.REVERSALS.glob("*.jsonl")) if vd.REVERSALS.exists() else []
    vd.deploy_metafields(True, q)
    log = [p for p in sorted(vd.REVERSALS.glob("*.jsonl")) if p not in before]
    errs, n = verify_metafields(q)
    print(f"metafields read back: {n}; {'PASS' if not errs else errs[:5]}")
    if errs:
        raise SystemExit("HALT: metafield read-back failed")
    save_state(definition_id=d["id"], entries=n and len(all_entries(q)),
               reversal_file=str(log[-1].relative_to(ROOT)) if log else None, setup_at=now())


# ---------------------------------------------------------- storefront --

def fetch(url, cookies=None):
    """GET with our user agent. 429 is backoff, never a result."""
    import http.cookiejar
    jar = cookies if cookies is not None else http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    for _ in range(6):
        try:
            with opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8)
                continue
            return e.code, e.read().decode("utf-8", "replace")
        finally:
            time.sleep(2)
    return 429, ""


def visitor_get(url):
    """THE fetch for every live check: a logged-out visitor. Refuses a preview parameter, starts
    from an empty cookie jar, sends no cookie it did not receive in this same request chain, and
    returns what theme answered so the caller can refuse anything but MAIN. A staff browser
    carrying a preview cookie for an older theme sees a different page (go-live, 2026-09-29)."""
    import http.cookiejar
    if "preview_theme_id" in url:
        raise SystemExit(f"REFUSED: a live check may not use a preview URL: {url}")
    jar = http.cookiejar.CookieJar()
    status, page = fetch(url, jar)
    th = theme_of(page)
    return status, page, {"url": url, "status": status, "cookie_jar_at_start": "empty (new jar per fetch)",
                          "preview_cookie_received": any("preview" in c.name for c in jar),
                          "theme_id": th["id"] if th else None, "theme_role": th["role"] if th else None}


def hub_rows_problem(page, active_inh_ids):
    """None when the hub renders exactly one row per active entry; otherwise the reason.
    A theme without the hub template falls back to the default page template, which prints
    only the page body ('This page lists every model ...') and no rows."""
    rows = sorted(re.findall(r'data-inh-id="([^"]*)"', page))
    want = sorted(active_inh_ids)
    if 'data-inhv="model-count"' not in page:
        return f"hub section not rendered (0 rows; default page template?) for {len(want)} active entries"
    if len(rows) < len(want):
        return f"hub renders {len(rows)} rows for {len(want)} active entries"
    if rows != want:
        return f"hub rows {rows} are not the active entries {want}"
    cnt = re.search(r'data-inhv="model-count">(\d+)<', page)
    if not cnt or int(cnt.group(1)) != len(want):
        return f"hub count {cnt and cnt.group(1)} != {len(want)} active"
    return None


UNKNOWN_MSG = "This model page isn't available."


def head_of(page):
    return page.split("</head>", 1)[0]


def real_hub_problems(page, url):
    """The real hub: self-canonical, indexable, the full table."""
    p = []
    head = head_of(page)
    if re.findall(r'<link rel="canonical" href="([^"]*)"', head) != [url]:
        p.append("real hub: canonical is not exactly itself")
    if re.search(r'<meta\s+name="robots"[^>]*noindex', page):
        p.append("real hub: noindex present")
    if 'data-inhv="table"' not in page or 'data-inhv="unknown-path"' in page:
        p.append("real hub: the table is not rendered")
    return p


def unknown_path_problems(page, url):
    """A path under the hub that is no active model page: noindex, exactly one canonical and it points
    at the requested URL itself (Shopify's content_for_header injects that self-canonical whenever the
    theme omits one; noindex conflicts only with a canonical to a DIFFERENT URL, so anything else
    fails), no structured data, the short message and the hub link, no table. (Option A, approved
    2026-09-29.)"""
    p = []
    head = head_of(page)
    if len(re.findall(r'<meta\s+name="robots"\s+content="noindex">', head)) != 1:
        p.append("unknown path: <meta name=\"robots\" content=\"noindex\"> not exactly once in <head>")
    canon = [htmllib.unescape(x) for x in re.findall(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', page)]
    if canon != [url]:
        p.append(f"unknown path: canonical {canon} is not exactly the requested URL {url}")
    if re.search(r'<script[^>]*type="application/ld\+json"', page):
        p.append("unknown path: structured data present")
    if UNKNOWN_MSG not in htmllib.unescape(page) or '<a href="/pages/sauna-database">' not in page:
        p.append("unknown path: message or hub link missing")
    if 'data-inh-id="' in page or 'data-inhv="table"' in page:
        p.append("unknown path: the hub table rendered")
    return p


def theme_of(page):
    m = re.search(r'Shopify\.theme = (\{[^}]*\})', page)
    return json.loads(m.group(1)) if m else None


def link_section(page):
    """(section wrapper present, link rendered) for the product-link section."""
    return bool(re.search(r'id="shopify-section-[^"]*__inh_verified_link"', page)), 'data-inhv="product-link"' in page


def preview_proof(handle="golden-designs-copenhagen"):
    """On the preview theme: the metafield is set, the entry is DRAFT, and the link section
    renders nothing (its wrapper is present, so the section is on the template)."""
    import http.cookiejar
    q = vd.admin()
    target = next((pd, gid) for pd, _, gid in vd._pages_and_records() if gid and
                  q(MF_LIST_Q, {"id": gid})["product"]["handle"] == handle)
    pd, gid = target
    entry = q(vd.ENTRY_Q, {"h": {"type": "sauna", "handle": pd["handle"]}})["metaobjectByHandle"]
    mf = q(MF_LIST_Q, {"id": gid})["product"]["metafield"]
    jar = http.cookiejar.CookieJar()
    status, page = fetch(f"{STORE}/products/{handle}?preview_theme_id={vd.PREVIEW_THEME}", jar)
    th = theme_of(page)
    wrap, link = link_section(page)
    result = {"product": handle, "status": status, "rendered_by_theme": th and th.get("id"),
              "metafield_set_to_entry": bool(mf) and mf["value"] == entry["id"],
              "entry_status": entry["capabilities"]["publishable"]["status"],
              "link_section_wrapper_present": wrap, "link_rendered": link, "checked_at": now()}
    ok = (status == 200 and str(result["rendered_by_theme"]) == vd.PREVIEW_THEME and result["metafield_set_to_entry"]
          and result["entry_status"] == "DRAFT" and wrap and not link)
    result["pass"] = ok
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "preview-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not ok:
        raise SystemExit("HALT: preview proof failed")


# ------------------------------------------------------------- live theme --

def resolve_main_logged():
    from verify_theme_asset_path import resolve_main, load_env
    mid, name = resolve_main(*load_env())
    print(f"MAIN resolved at run time: {mid} {name!r}")
    return str(mid), name


def snap_dir(mid):
    return GOLIVE / f"main-{mid}-snapshot"


def snapshot_main():
    q = vd.admin()
    mid, name = resolve_main_logged()
    cur = vd.read_files(q, mid, vd.PATCHED + NEW_FILES)
    present_new = sorted(set(cur) & set(NEW_FILES))
    if present_new:
        raise SystemExit(f"HALT: MAIN already holds files this deploy would create: {present_new}")
    d = snap_dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    man = {"theme_id": mid, "theme_name": name, "taken_at": now(), "files": {}, "absent_before_deploy": NEW_FILES}
    for n in vd.PATCHED:
        body = cur[n]["body"]["content"]
        if vd.md5(body.encode()) != cur[n]["checksumMd5"]:
            raise SystemExit(f"HALT: {n} body does not match its own MD5 as served")
        (d / n.replace("/", "__")).write_text(body)
        man["files"][n] = {"md5": cur[n]["checksumMd5"], "size": int(cur[n]["size"]), "path": str((d / n.replace('/', '__')).relative_to(ROOT))}
    (d / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    save_state(main_theme_id=mid, snapshot=str(d.relative_to(ROOT)))
    print(f"snapshot of {len(man['files'])} files -> {d.relative_to(ROOT)}; {len(NEW_FILES)} new files confirmed absent")


def live_guard(q, mid, allow):
    from verify_theme_asset_path import refusal_for, main_refusal, announce_live_override
    theme = q(vd.THEME_Q, {"id": f"gid://shopify/OnlineStoreTheme/{mid}"})["theme"]
    for why in (refusal_for(theme, mid, allow), main_refusal(mid, mid, allow)):
        if why:
            raise SystemExit(why)
    banner = announce_live_override(theme, mid, allow)
    if not banner:
        raise SystemExit("REFUSED: the live override was not in play")
    print("=" * 78 + "\n" + banner + "\n" + "=" * 78)
    return theme


def snapshot_gate(q, mid):
    """Evaluated seconds before the write: MAIN still equals the committed snapshot."""
    d = snap_dir(mid)
    man = json.loads((d / "manifest.json").read_text())
    cur = vd.read_files(q, mid, vd.PATCHED + NEW_FILES)
    bad = [n for n in vd.PATCHED if cur.get(n, {}).get("checksumMd5") != man["files"][n]["md5"]]
    early = sorted(set(cur) & set(NEW_FILES))
    if bad or early:
        raise SystemExit(f"HALT: MAIN changed since the snapshot (differs: {bad}; new files already present: {early}). Nothing written.")
    return {n: (d / n.replace("/", "__")).read_text() for n in vd.PATCHED}


def deploy_main(allow, write):
    q = vd.admin()
    mid, _ = resolve_main_logged()
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id {allow} does not name MAIN ({mid})")
    before = snapshot_gate(q, mid)
    patched = {"layout/theme.liquid": vd.patch_layout(before["layout/theme.liquid"]),
               "templates/product.json": vd.patch_product(before["templates/product.json"])}
    if not vd.product_prefix_unchanged(before["templates/product.json"], patched["templates/product.json"]):
        raise SystemExit("HALT: the product patch changes something above the reviews")
    files = {n: (ROOT / n).read_bytes() for n in NEW_FILES}
    files.update({n: v.encode() for n, v in patched.items()})
    vd.lint_payload(b"\n".join(files.values()).decode("utf-8", "replace"), "live theme files")
    for n in files:
        print(f"  {'write' if write else 'would write'}  {n}  {len(files[n])} B  md5 {vd.md5(files[n])}")
    if not write:
        return
    live_guard(q, mid, allow)
    before = snapshot_gate(q, mid)          # again, at the last moment it can still be true
    for batch in (vd.PASS_1, vd.PASS_2 + vd.PATCHED, vd.PASS_3):
        payload = [{"filename": n, "body": {"type": "TEXT", "value": files[n].decode()}} for n in batch]
        r = q(vd.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": payload})["themeFilesUpsert"]
        if r["userErrors"]:
            raise SystemExit(f"HALT after partial write {batch}: {r['userErrors']}. Roll back with: rollback --execute")
    back = vd.read_files(q, mid, list(files))
    report, bad = {}, []
    for n in files:
        got = back.get(n)
        if not got:
            bad.append(f"{n} missing")
            continue
        if got["checksumMd5"] == vd.md5(files[n]):
            report[n] = "byte-identical (MD5)"
        elif n.endswith(".json") and vd.split_json_template(got["body"]["content"])[1] == vd.split_json_template(files[n].decode())[1]:
            report[n] = "JSON identical after Shopify's reformat"
        else:
            bad.append(f"{n} differs")
    # the patched files may differ from the snapshot ONLY in the intended lines
    diffs = []
    lay_back = back["layout/theme.liquid"]["body"]["content"]
    if lay_back != patched["layout/theme.liquid"]:
        bad.append("layout differs from snapshot + patch")
    prod_back = back["templates/product.json"]["body"]["content"]
    _, pb = vd.split_json_template(prod_back)
    _, sb = vd.split_json_template(before["templates/product.json"])
    extra = {k: v for k, v in pb["sections"].items() if k not in sb["sections"]}
    if set(extra) != {vd.LINK_SECTION_ID} or any(pb["sections"][k] != sb["sections"][k] for k in sb["sections"]) \
            or [k for k in pb["order"] if k != vd.LINK_SECTION_ID] != sb["order"] \
            or not vd.product_prefix_unchanged(before["templates/product.json"], prod_back):
        bad.append("product template differs from snapshot beyond the link section")
    for n, a, b in (("layout/theme.liquid", before["layout/theme.liquid"], lay_back),
                    ("templates/product.json", json.dumps(sb, indent=2, ensure_ascii=False, sort_keys=False),
                     json.dumps(pb, indent=2, ensure_ascii=False, sort_keys=False))):
        diffs += list(difflib.unified_diff(a.splitlines(True), b.splitlines(True), f"MAIN {mid} snapshot/{n}", f"MAIN {mid} live/{n}", n=2))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "main-patch.diff").write_text("".join(diffs))
    print(f"read-back: {json.dumps(report, indent=1)}")
    print(f"patch diff -> {(EVIDENCE / 'main-patch.diff').relative_to(ROOT)} "
          f"(+{sum(1 for l in diffs if l.startswith('+') and not l.startswith('+++'))} / "
          f"-{sum(1 for l in diffs if l.startswith('-') and not l.startswith('---'))} lines)")
    if bad:
        raise SystemExit(f"HALT: read-back failed {bad}. Roll back with: rollback --execute")
    save_state(main_deployed_at=now(), main_readback=report)


# --------------------------------------------------------------- rollback --

def rollback(execute, allow=None):
    """Four steps, in the order that strands no reader on a broken link:
    1 entries -> DRAFT, 2 pages -> hidden, 3 metafields reversed, 4 MAIN's files restored
    from the committed snapshot and the files this deploy created deleted."""
    q = vd.admin()
    st = load_state()
    mid, _ = resolve_main_logged()
    plan, problems = [], []
    active = [e for e in all_entries(q) if e["capabilities"]["publishable"]["status"] == "ACTIVE"]
    plan.append(f"1 set {len(active)} ACTIVE entries to DRAFT: {[e['handle'] for e in active]}")
    pages = [n for spec in (vd.HUB, vd.METHOD) for n in q(vd.PAGE_FIND_Q, {"q": f"handle:{spec['handle']}"})["pages"]["nodes"]
             if n["handle"] == spec["handle"]]
    plan.append(f"2 hide pages: {[(p['handle'], 'published' if p['isPublished'] else 'already hidden') for p in pages]}")
    rev = st.get("reversal_file")
    if rev and (ROOT / rev).exists():
        lines = [json.loads(x) for x in (ROOT / rev).read_text().splitlines()]
        plan.append(f"3 reverse {len(lines)} metafield writes from {rev} "
                    f"({sum(1 for x in lines if x['previous_value'] is None)} deleted, the rest restored)")
    else:
        plan.append("3 no metafield reversal file recorded (nothing to reverse)")
    d = snap_dir(mid)
    if (d / "manifest.json").exists():
        man = json.loads((d / "manifest.json").read_text())
        for n, meta in man["files"].items():
            body = (ROOT / meta["path"]).read_text()
            if vd.md5(body.encode()) != meta["md5"]:
                problems.append(f"snapshot file {n} does not match its recorded MD5")
        for sd in sorted(GOLIVE.glob("step-*/manifest.json"), key=lambda p: json.loads(p.read_text())["taken_at"]):
            for n, meta in json.loads(sd.read_text())["files"].items():
                if n not in man["files"] and n not in NEW_FILES:      # a pre-existing file a later step patched
                    man["files"][n] = meta
        cur = vd.read_files(q, mid, NEW_FILES)
        plan.append(f"4 restore {list(man['files'])} on MAIN {mid} from their first snapshots (MD5 checked) and delete "
                    f"{len(cur)} created files present now: {sorted(cur)}")
    else:
        problems.append(f"no snapshot for MAIN {mid}")
    print("ROLLBACK PLAN" + (" (dry run: nothing written)" if not execute else ""))
    print("\n".join("  " + p for p in plan))
    print("  prerequisites: " + ("OK" if not problems else "; ".join(problems)))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / ("rollback-dry-run.txt" if not execute else "rollback-executed.txt")).write_text(
        f"{now()}\n" + "\n".join(plan) + f"\nprerequisites: {'OK' if not problems else problems}\n")
    if problems:
        raise SystemExit(1)
    if not execute:
        return
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: rollback writes to MAIN; --allow-live-theme-id must name {mid}")
    for e in active:
        r = q(STATUS_M, {"id": e["id"], "m": {"capabilities": {"publishable": {"status": "DRAFT"}}}})["metaobjectUpdate"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {r['userErrors']}")
    for p in pages:
        if p["isPublished"]:
            vd.page_update_checked(q, p["id"], {"isPublished": False}, vd.suffix_for(p["handle"]))
    if rev and (ROOT / rev).exists():
        vd.reverse(ROOT / rev, q=q)
    live_guard(q, mid, allow)
    payload = [{"filename": n, "body": {"type": "TEXT", "value": (ROOT / meta["path"]).read_text()}} for n, meta in man["files"].items()]
    r = q(vd.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": payload})["themeFilesUpsert"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: restore refused {r['userErrors']}")
    present = sorted(vd.read_files(q, mid, NEW_FILES))
    if present:
        r = q(vd.DELETE_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": present})["themeFilesDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: delete refused {r['userErrors']}")
    back = vd.read_files(q, mid, vd.PATCHED + NEW_FILES)

    def restored(n):
        # A JSON template recreated or rewritten is re-serialised by Shopify (proved on the preview
        # theme at go-live): identical parsed content is a restore; anything else is not.
        snap = (ROOT / man["files"][n]["path"]).read_text()
        return back[n]["checksumMd5"] == man["files"][n]["md5"] or (
            n.endswith(".json") and vd.split_json_template(back[n]["body"]["content"])[1] == vd.split_json_template(snap)[1])
    ok = all(n in back and restored(n) for n in man["files"]) and not (set(back) & set(NEW_FILES))
    print(f"rollback read-back: {'MAIN equals the snapshot' if ok else 'MISMATCH'}")


# ------------------------------------------------------------- activation --

def activate(handles, write):
    q = vd.admin()
    known = {pd["handle"] for pd, _, _ in vd._pages_and_records()}
    unknown = [h for h in handles if h not in known]
    if unknown:
        raise SystemExit(f"HALT: not page handles: {unknown}")
    for h in handles:
        e = q(vd.ENTRY_Q, {"h": {"type": "sauna", "handle": h}})["metaobjectByHandle"]
        print(f"  {'activate' if write else 'would activate'} {h} (now {e['capabilities']['publishable']['status']})")
        if write:
            r = q(STATUS_M, {"id": e["id"], "m": {"capabilities": {"publishable": {"status": "ACTIVE"}}}})["metaobjectUpdate"]
            if r["userErrors"] or r["metaobject"]["capabilities"]["publishable"]["status"] != "ACTIVE":
                raise SystemExit(f"HALT at {h}: {r['userErrors']}")
    if write:
        active = sorted(set(load_state().get("active_handles", [])) | set(handles))
        errs, n = verify_entries(q, expect_active=active)
        print(f"read back {n} entries: {len(active)} ACTIVE, {n - len(active)} DRAFT; {'PASS' if not errs else errs[:5]}")
        if errs:
            raise SystemExit("HALT: status read-back failed")
        save_state(active_handles=active, activated_at=now())


def deactivate(handles, write):
    """Set the named entries back to DRAFT (a failed batch), read back, update the launch state."""
    q = vd.admin()
    for h in handles:
        e = q(vd.ENTRY_Q, {"h": {"type": "sauna", "handle": h}})["metaobjectByHandle"]
        print(f"  {'draft' if write else 'would draft'} {h} (now {e['capabilities']['publishable']['status']})")
        if write:
            r = q(STATUS_M, {"id": e["id"], "m": {"capabilities": {"publishable": {"status": "DRAFT"}}}})["metaobjectUpdate"]
            if r["userErrors"]:
                raise SystemExit(f"HALT at {h}: {r['userErrors']}")
    if write:
        active = sorted(set(load_state().get("active_handles", [])) - set(handles))
        save_state(active_handles=active)
        errs, n = verify_entries(q, expect_active=active)
        print(f"read back: {len(active)} ACTIVE; {'PASS' if not errs else errs[:5]}")


def publish_pages(write):
    q = vd.admin()
    vd.deploy_pages(write)       # refresh the hidden pages' bodies first (refuses a published page)
    for spec in (vd.HUB, vd.METHOD):
        p = next(n for n in q(vd.PAGE_FIND_Q, {"q": f"handle:{spec['handle']}"})["pages"]["nodes"] if n["handle"] == spec["handle"])
        print(f"  {'publish' if write else 'would publish'} {spec['handle']}")
        if write:
            vd.page_update_checked(q, p["id"], {"isPublished": True}, spec["templateSuffix"])
    if write:
        save_state(pages_published_at=now())


DESC_Q = """query($id: ID!) { page(id: $id) { metafield(namespace: "global", key: "description_tag") { value } } }"""


def active_count(q):
    return sum(1 for e in all_entries(q) if e["capabilities"]["publishable"]["status"] == "ACTIVE")


def finish_pages(write):
    """The staged-launch copy, finished: the hub description counts ACTIVE entries (read from the Admin
    API at write time, never typed) and the methodology body is rebuilt without the staged sentence.
    Every write names its template and is read back; bodies compared as visible text."""
    import html as _h
    q = vd.admin()
    n = active_count(q)
    total = len(list(vd._pages_and_records()))
    if n != total:
        raise SystemExit(f"HALT: {n} of {total} entries are active; the staged copy stays until all are")
    desc = {vd.HUB["handle"]: f"Verified specifications and electrical requirements for {n} home sauna models. "
                              "Every value is cited to the manufacturer, graded and dated.",
            vd.METHOD["handle"]: vd.page_descriptions()[vd.METHOD["handle"]]}
    bodies = {vd.HUB["handle"]: vd.HUB_BODY, vd.METHOD["handle"]: (ROOT / "out/verified/methodology.html").read_text()}
    if "published in stages" in bodies[vd.METHOD["handle"]]:
        raise SystemExit("HALT: the methodology build still carries the staged sentence")
    vis = lambda s: re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    for spec in (vd.HUB, vd.METHOD):
        h = spec["handle"]
        vd.lint_payload(bodies[h] + desc[h], h)
        p = next(x for x in q(vd.PAGE_FIND_Q, {"q": f"handle:{h}"})["pages"]["nodes"] if x["handle"] == h)
        print(f"  {'write' if write else 'would write'} {h}: description {desc[h]!r}")
        if not write:
            continue
        back = vd.page_update_checked(q, p["id"], {"body": bodies[h], "isPublished": True, "metafields": [
            {"namespace": "global", "key": "description_tag", "type": "single_line_text_field", "value": desc[h]}]},
            spec["templateSuffix"])
        got = q(DESC_Q, {"id": p["id"]})["page"]["metafield"]
        if vis(back["body"]) != vis(bodies[h]) or not got or got["value"] != desc[h]:
            raise SystemExit(f"HALT: {h} read back differs (body or description)")
        print(f"    read back: template {back['templateSuffix']}, published {back['isPublished']}, body and description identical")


def hub_body(write):
    """Rewrite the published hub page's body (its fallback text) with its template named and read back."""
    import html as _h
    q = vd.admin()
    p = next(n for n in q(vd.PAGE_FIND_Q, {"q": f"handle:{vd.HUB['handle']}"})["pages"]["nodes"] if n["handle"] == vd.HUB["handle"])
    vd.lint_payload(vd.HUB_BODY, "hub body")
    print(f"  {'write' if write else 'would write'} hub body ({len(vd.HUB_BODY)} chars), template {vd.HUB['templateSuffix']}")
    if not write:
        return
    before = q(vd.PAGE_READ_Q, {"id": p["id"]})["page"]
    GOLIVE.mkdir(parents=True, exist_ok=True)
    (GOLIVE / "hub-body-before.html").write_text(before["body"])
    back = vd.page_update_checked(q, p["id"], {"body": vd.HUB_BODY}, vd.HUB["templateSuffix"])
    vis = lambda s: re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    if vis(back["body"]) != vis(vd.HUB_BODY) or not back["isPublished"]:
        raise SystemExit("HALT: hub body read back differs, or the page is no longer published")
    print(f"  read back: template {back['templateSuffix']}, published {back['isPublished']}, visible text identical")


# ------------------------------------------------ a later template step --

STEP_FILES = ["sections/inh-verified-model.liquid", "snippets/inh-verified-fact.liquid",
              "sections/inh-verified-hub.liquid", "assets/inh-verified.css"]
ENTRY_KEYS = ("title", "inh_id", "brand", "heat_type", "capacity_label", "supply_voltage", "placement",
              "verified_date", "seo_title", "seo_description", "record", "page_data", "store_product")


PT_Q = "query($id: ID!) { product(id: $id) { handle templateSuffix } }"


def product_templates_in_use(q):
    """Every product template a mapped product renders with: templates/product.json, plus
    templates/product.<suffix>.json for each templateSuffix in use."""
    names = {"templates/product.json"}
    for _, _, gid in vd._pages_and_records():
        if gid:
            suf = q(PT_Q, {"id": gid})["product"]["templateSuffix"]
            if suf:
                names.add(f"templates/product.{suf}.json")
    return sorted(names)


def step_content(n, snapshot_body):
    """What a step writes for file n: MAIN's OWN layout and product templates patched in place
    (never copied), every other file from the repo."""
    if n == "layout/theme.liquid":
        return vd.fix_unknown_comment(vd.patch_layout(snapshot_body))
    if n.startswith("templates/product"):
        after = vd.patch_product(snapshot_body)
        if not vd.product_prefix_unchanged(snapshot_body, after):
            raise SystemExit(f"HALT: the patch changes something above the reviews in {n}")
        return after
    return (ROOT / n).read_text()


def step_dir(name):
    return GOLIVE / f"step-{name}"


def snapshot_files(name, files=None):
    """MAIN's current copies of the files a later step changes, and every entry's current fields."""
    q = vd.admin()
    mid, mname = resolve_main_logged()
    STEP = files or STEP_FILES
    cur = vd.read_files(q, mid, STEP)
    missing = [n for n in STEP if n not in cur and n not in NEW_FILES]
    if missing:
        raise SystemExit(f"HALT: MAIN lacks {missing}")
    absent = [n for n in STEP if n not in cur]      # files this step CREATES: recorded as absent
    d = step_dir(name)
    (d / "files").mkdir(parents=True, exist_ok=True)
    man = {"theme_id": mid, "theme_name": mname, "taken_at": now(), "files": {}}
    for n in absent:
        man["files"][n] = {"absent": True}
    for n in [x for x in STEP if x not in absent]:
        body = cur[n]["body"]["content"]
        if vd.md5(body.encode()) != cur[n]["checksumMd5"]:
            # A JSON template saved in the theme editor is served as a re-serialised rendering, not its
            # stored bytes (product.Bundle.json: size 60623, body 60986 bytes). The body must still parse;
            # the served checksum is what the before-write gate compares. Anything else halts.
            if not n.endswith(".json"):
                raise SystemExit(f"HALT: {n} does not match its own MD5")
            vd.split_json_template(body)
        (d / "files" / n.replace("/", "__")).write_text(body)
        man["files"][n] = {"md5": cur[n]["checksumMd5"], "path": str((d / "files" / n.replace("/", "__")).relative_to(ROOT))}
    ents = {e["handle"]: {"status": e["capabilities"]["publishable"]["status"],
                          "fields": {x["key"]: x["value"] for x in e["fields"] if x["key"] in ENTRY_KEYS}}
            for e in all_entries(q)}
    (d / "entries.json").write_text(json.dumps(ents, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (d / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    print(f"snapshot: {len(STEP)} MAIN files {STEP} and {len(ents)} entries -> {d.relative_to(ROOT)}")


def update_entries(write):
    """Rewrite every entry's fields from the current build, keeping its status exactly as it is."""
    q = vd.admin()
    st = load_state()
    n = 0
    for pd, record, gid in vd._pages_and_records():
        fields = vd.entry_fields(pd, record, gid)
        vd.lint_payload(json.dumps(fields, ensure_ascii=False), pd["handle"])
        if write:
            h = {"type": "sauna", "handle": pd["handle"]}
            before = q(vd.ENTRY_Q, {"h": h})["metaobjectByHandle"]["capabilities"]["publishable"]["status"]
            r = q(vd.UPSERT_ENTRY_M, {"h": h, "m": {"fields": fields}})["metaobjectUpsert"]
            if r["userErrors"]:
                raise SystemExit(f"HALT at {pd['handle']}: {r['userErrors']}")
            if r["metaobject"]["capabilities"]["publishable"]["status"] != before:
                raise SystemExit(f"HALT: {pd['handle']} changed status {before} -> {r['metaobject']['capabilities']['publishable']['status']}")
        n += 1
    print(f"  {'updated' if write else 'would update'} {n} entries (status unchanged)")
    if write:
        errs, m = verify_entries(q, expect_active=st.get("active_handles", []))
        print(f"  read back {m} entries: {'PASS' if not errs else errs[:5]}")
        if errs:
            raise SystemExit("HALT: entry read-back failed; restore with: restore-step")


def deploy_files(name, allow, write):
    q = vd.admin()
    mid, _ = resolve_main_logged()
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id {allow} does not name MAIN ({mid})")
    d = step_dir(name)
    man = json.loads((d / "manifest.json").read_text())

    STEP = list(man["files"])

    def gate():
        cur = vd.read_files(q, mid, STEP)
        def moved(n):
            if man["files"][n].get("absent"):
                return n in cur          # a file this step creates must still be absent
            return cur.get(n, {}).get("checksumMd5") != man["files"][n]["md5"]
        bad = [n for n in STEP if moved(n)]
        if bad:
            raise SystemExit(f"HALT: MAIN changed since the step snapshot: {bad}. Nothing written.")
    gate()
    snap = {n: ("" if man["files"][n].get("absent") else (ROOT / man["files"][n]["path"]).read_text()) for n in STEP}
    files = {n: step_content(n, snap[n]).encode() for n in STEP}
    unchanged = [n for n in STEP if files[n].decode() == snap[n]]
    STEP = [n for n in STEP if n not in unchanged]
    files = {n: files[n] for n in STEP}
    print(f"  unchanged, not written: {unchanged}")
    vd.lint_payload(b"\n".join(files.values()).decode("utf-8", "replace"), "step files")
    for n in files:
        print(f"  {'write' if write else 'would write'}  {n}  {len(files[n])} B  md5 {vd.md5(files[n])}")
    if not write:
        return
    live_guard(q, mid, allow)
    gate()
    r = q(vd.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}",
                        "files": [{"filename": n, "body": {"type": "TEXT", "value": files[n].decode()}} for n in STEP]})["themeFilesUpsert"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}. Restore with: restore-step")
    back = vd.read_files(q, mid, STEP)
    bad = [n for n in STEP if back.get(n, {}).get("checksumMd5") != vd.md5(files[n])
           and not (n.endswith(".json") and vd.split_json_template(back[n]["body"]["content"])[1]
                    == vd.split_json_template(files[n].decode())[1])]
    for n in STEP:
        if n.startswith("templates/product") and not vd.product_prefix_unchanged(snap[n], back[n]["body"]["content"]):
            bad.append(f"{n}: changed above the reviews")
    diffs = []
    for n in STEP:
        a = snap[n]
        diffs += list(difflib.unified_diff(a.splitlines(True), back[n]["body"]["content"].splitlines(True),
                                           f"MAIN {mid} before/{n}", f"MAIN {mid} after/{n}", n=1))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / f"{name}.diff").write_text("".join(diffs))
    print(f"read-back: {len(STEP) - len(bad)} of {len(STEP)} identical {bad or ''}; "
          f"diff -> {(EVIDENCE / f'{name}.diff').relative_to(ROOT)}")
    if bad:
        raise SystemExit("HALT: read-back failed. Restore with: restore-step")
    save_state(**{f"{name}_deployed_at": now()})


def restore_step(name, allow, execute):
    """Undo a later template step: MAIN's files from the step snapshot, and every entry's fields
    as they were (status untouched here; `rollback` handles status)."""
    q = vd.admin()
    mid, _ = resolve_main_logged()
    d = step_dir(name)
    man = json.loads((d / "manifest.json").read_text())
    ents = json.loads((d / "entries.json").read_text()) if (d / "entries.json").exists() else {}
    print(f"RESTORE {name}: {len(man['files'])} files on MAIN {mid}, fields of {len(ents)} entries"
          + ("" if execute else " (dry run)"))
    if not execute:
        return
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id must name {mid}")
    for h, e in ents.items():
        r = q(vd.UPSERT_ENTRY_M, {"h": {"type": "sauna", "handle": h},
                                  "m": {"fields": [{"key": k, "value": v} for k, v in e["fields"].items()]}})["metaobjectUpsert"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at {h}: {r['userErrors']}")
    live_guard(q, mid, allow)
    created = [n for n, m in man["files"].items() if m.get("absent")]
    kept = {n: m for n, m in man["files"].items() if not m.get("absent")}
    r = q(vd.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": [
        {"filename": n, "body": {"type": "TEXT", "value": (ROOT / m["path"]).read_text()}} for n, m in kept.items()]})["themeFilesUpsert"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}")
    present = sorted(vd.read_files(q, mid, created)) if created else []
    if present:
        r = q(vd.DELETE_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": present})["themeFilesDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {r['userErrors']}")
    if created and vd.read_files(q, mid, created):
        raise SystemExit("HALT: a file this step created is still present")
    man = {"files": kept}
    back = vd.read_files(q, mid, list(man["files"]))
    ok = all(back[n]["checksumMd5"] == m["md5"] or (n.endswith(".json") and vd.split_json_template(back[n]["body"]["content"])[1]
             == vd.split_json_template((ROOT / m["path"]).read_text())[1]) for n, m in man["files"].items())
    print(f"restore read-back: files {'identical to the snapshot' if ok else 'MISMATCH'}")


# -------------------------------------------------------------- live check --

def live_urls():
    st = load_state()
    urls = {"hub": f"{STORE}/pages/sauna-database", "methodology": f"{STORE}/pages/sauna-database-methodology"}
    for h in st.get("active_handles", []):
        urls[f"model:{h}"] = f"{STORE}/pages/sauna-database/{h}"
    return urls


def live_check(links=False, product_link="golden-designs-copenhagen", product_draft="golden-designs-toledo"):
    import verified_checks as vc
    import verified_pages as vp
    from src.health_claims import find_banned_claims
    st = load_state()
    ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
    titles = vp.load_titles()
    pages = {pd["handle"]: pd for pd, _, _ in vd._pages_and_records()}
    active = st.get("active_handles", [])
    errs, report, html_by = [], {"checked_at": now(), "pages": {}}, {}
    V = vc.vocab()
    shop_suffix = None
    for key, url in live_urls().items():
        status, page, seen = visitor_get(url)
        th = theme_of(page)
        html_by[key] = page
        report["pages"][key] = {"url": url, "status": status, "theme": th["id"] if th else None, "visitor": seen}
        if seen["preview_cookie_received"]:
            errs.append(f"{key}: a preview cookie was set during a visitor fetch")
        if status != 200:
            errs.append(f"{key}: HTTP {status}")
            continue
        if th is None or th["role"] != "main":
            errs.append(f"{key}: not served by the live theme ({th})")
        if key.startswith("model:"):
            h = key.split(":", 1)[1]
            pd = pages[h]
            n = vc.check_model(ds[pd["inh_id"]], titles[pd["inh_id"]], page, pd, errs)
            report["pages"][key]["fact_rows_checked"] = len(n)
            vc.check_head("model", page, pd["seo_title"], pd["url"], errs, key)
            d = re.findall(r'<meta\s+name="description"\s+content="([^"]*)"', page)
            if [htmllib.unescape(x) for x in d] != [pd["seo_description"]]:
                errs.append(f"{key}: meta description is not exactly the page's SEO description")
            report["pages"][key]["meta_description_matches"] = [htmllib.unescape(x) for x in d] == [pd["seo_description"]]
            vc.check_jsonld(vc.jsonlds(page), key, errs, V)
        else:
            t = re.search(r"<title>(.*?)</title>", page, re.S)
            report["pages"][key]["title"] = htmllib.unescape(t.group(1)).strip() if t else None
            c = re.findall(r'<link rel="canonical" href="([^"]*)"', page)
            if c != [url]:
                errs.append(f"{key}: canonical {c} != [{url}]")
            vc.check_jsonld(vc.jsonlds(page), key, errs, V)
    hub = html_by.get("hub", "")
    want = [pages[h]["inh_id"] for h in active]
    report["hub_rows"] = sorted(re.findall(r'data-inh-id="([^"]*)"', vc.main_of(hub)))
    problem = hub_rows_problem(vc.main_of(hub), want)
    report["hub_rows_check"] = problem or f"PASS: {len(want)} rows for {len(want)} active entries"
    if problem:
        errs.append(f"hub: {problem}")
    report["real_hub"] = real_hub_problems(hub, live_urls()["hub"]) or "PASS"
    if report["real_hub"] != "PASS":
        errs += report["real_hub"]
    drafts = sorted(set(pages) - set(active))
    first = (f"{STORE}/pages/sauna-database/{drafts[0]}" if drafts          # a real draft handle while any exist
             else f"{STORE}/pages/sauna-database/{sorted(pages)[0]}-retired")   # else a near-miss of a real handle
    report["unknown_paths"] = {}
    for u in (first, f"{STORE}/pages/sauna-database/no-such-model-{now()[:10]}"):
        status, page, seen = visitor_get(u)
        probs = unknown_path_problems(page, u) if status == 200 else [f"HTTP {status}"]
        if seen["theme_role"] != "main":
            probs.append(f"not served by the live theme ({seen})")
        report["unknown_paths"][u] = probs or "PASS"
        errs += [f"{u}: {x}" for x in probs]
    intro = re.search(r'data-inhv="intro-count">(\d+)<', hub)
    if intro and int(intro.group(1)) != len(active):
        errs.append(f"hub intro count {intro.group(1)} != {len(active)} active")
    d = re.findall(r'<meta\s+name="description"\s+content="([^"]*)"', hub)
    m = re.search(r"for (\d+) home sauna models", htmllib.unescape(d[0])) if d else None
    if m and int(m.group(1)) != len(active):
        errs.append(f"hub meta description says {m.group(1)} models; {len(active)} are active")
    report["hub_counts"] = {"intro": intro and int(intro.group(1)), "description": m and int(m.group(1)), "active": len(active)}
    cells_checked = 0
    for iid, cells in re.findall(r'(?s)<tr data-heat="[^"]*" data-cap="[^"]*" data-brand="[^"]*" data-inh-id="([^"]*)">(.*?)</tr>', vc.main_of(hub)):
        errs += vc.hub_row_problems(ds[iid], iid, cells, titles[iid])
        cells_checked += 5
    report["hub_cells_checked"] = cells_checked
    for key, page in html_by.items():
        main = vc.main_of(page)
        for rx, what in ((vc.PRICE_RX, "price/currency"), (vc.BANNED_RX, "banned phrase")):
            m = rx.search(main)
            if m:
                errs.append(f"{key}: {what} {m.group(0)!r} in our content")
        bad = find_banned_claims(vc.visible(main))
        if bad:
            errs.append(f"{key}: health-claims gate {bad[:2]}")
        ext = vc.external_links_problem(main)
        if ext:
            errs.append(f"{key}: outbound links without rel=\"nofollow noopener\": {sorted(set(ext))}")
    # product pages: every mapped product; the link renders exactly when its entry is ACTIVE
    prod = {}
    for handle, want_link, _ in mapped_products():
        status, page, seen = visitor_get(f"{STORE}/products/{handle}")
        if seen["theme_role"] != "main":
            errs.append(f"product {handle}: not served by the live theme ({seen})")
        wrap, link = link_section(page)
        href = re.search(r'data-inhv="product-link">\s*<p><a href="([^"]*)"', page)
        prod[handle] = {"status": status, "section_wrapper": wrap, "link_rendered": link, "href": href and href.group(1),
                        "theme": (theme_of(page) or {}).get("id")}
        want_href = f"/pages/sauna-database/{_}" if want_link else None
        if status != 200 or link != want_link or (href and href.group(1)) != want_href:
            errs.append(f"product {handle}: link rendered {link} -> {href and href.group(1)}, expected {want_link} -> {want_href}")
        (EVIDENCE / "products").mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "products" / f"live-product-{handle}.html").write_text(page)
        if (ROOT / f"out/verified/golive/baseline/products-{handle}.html").exists():
            prod[handle]["above_reviews"] = above_reviews_unchanged(handle, errs)
        elif want_link:
            errs.append(f"product {handle}: no pre-activation baseline to compare against")
    report["products"] = prod
    report["products_with_link"] = sorted(h for h, v in prod.items() if v["link_rendered"])
    report["products_without_link"] = sorted(h for h, v in prod.items() if not v["link_rendered"])
    if links:
        report["links"] = vc.check_links({k: v for k, v in html_by.items()}, errs)
    # every product a live "Similar models" block links to is ACTIVE (Admin) and answers 200 (visitor)
    sim = sorted({u for k, page in html_by.items() if k.startswith("model:") for u in similar_links(page)})
    q = vd.admin()
    sim_report = {}
    for ph in sim:
        prod = q('query($h: String!) { productByHandle(handle: $h) { status } }', {"h": ph})["productByHandle"]
        status, page, seen = visitor_get(f"{STORE}/products/{ph}")
        sim_report[ph] = {"admin_status": prod and prod["status"], "http": status, "theme_role": seen["theme_role"]}
        if not prod or prod["status"] != "ACTIVE" or status != 200 or seen["theme_role"] != "main":
            errs.append(f"similar-model product {ph}: {sim_report[ph]}")
    report["similar_products"] = sim_report
    report["similar_blocks_checked"] = sum(1 for k, page in html_by.items() if k.startswith("model:") and 'data-inhv="similar"' in page)
    report["failures"] = errs
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "live-checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "links"}, indent=1, default=str)[:4000])
    print("LIVE CHECKS:", "PASS" if not errs else f"FAIL ({len(errs)})")
    return 1 if errs else 0


def similar_links(page):
    """Product handles a page's "Similar models" block links to (none when there is no block)."""
    blk = re.search(r'(?s)data-inhv="similar">(.*?)</section>', page)
    return re.findall(r'<li><a href="/products/([^"]+)">', blk.group(1)) if blk else []


def mapped_products():
    """(product handle, entry active?, entry handle) for every product carrying the metafield."""
    q = vd.admin()
    active = set(load_state().get("active_handles", []))
    out = []
    for pd, _, gid in vd._pages_and_records():
        if gid:
            ph = q(MF_LIST_Q, {"id": gid})["product"]["handle"]
            out.append((ph, pd["handle"] in active, pd["handle"]))
    return sorted(out)


def baseline_products(only_draft=True):
    """Pre-activation copies of product pages (visitor fetch) for the above-the-reviews comparison."""
    d = ROOT / "out/verified/golive/baseline"
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for ph, active, _ in mapped_products():
        if only_draft and active:
            continue
        status, page, seen = visitor_get(f"{STORE}/products/{ph}")
        if status != 200 or seen["theme_role"] != "main" or link_section(page)[1]:
            raise SystemExit(f"HALT: baseline for {ph}: HTTP {status}, {seen}, link rendered {link_section(page)[1]}")
        (d / f"products-{ph}.html").write_text(page)
        n += 1
    print(f"baselined {n} product pages (logged-out visitor, live theme, no link yet)")


def sections_above_reviews(page):
    """The ordered product sections up to and including the reviews section, as visible text."""
    ids = re.findall(r'id="shopify-section-(template--\d+__[^"]+)"', page)
    out = []
    for sid in ids:
        if sid.endswith("__inh_verified_link"):
            break
        m = re.search(r'id="shopify-section-' + re.escape(sid) + r'"[^>]*>(.*?)(?=<(?:div|section)[^>]*id="shopify-section-|</main>)', page, re.S)
        out.append((sid.split("__", 1)[1], m.group(1) if m else ""))
    return out


# The theme's delivery estimate is computed from today's date ("Order Now to Receive it By: October 12,
# 2026"), so it moves at every UTC day boundary without anyone changing anything (found 2026-09-29:
# 39 products "differed" by exactly that date). Only that date is neutralised; every other word counts.
DELIVERY_DATE_RX = re.compile(r"(Receive it By:\s*)(?:January|February|March|April|May|June|July|August|September"
                              r"|October|November|December)\s+\d{1,2},\s+\d{4}")


def norm(fragment):
    """Visible text with per-request tokens removed (CSRF, cart and tracking ids differ per load) and the
    clock-derived delivery date neutralised."""
    t = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", fragment)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", t))
    t = DELIVERY_DATE_RX.sub(r"\1<date>", t)
    return re.sub(r"\s+", " ", t).strip()


def above_reviews_unchanged(handle, errs):
    base = (ROOT / f"out/verified/golive/baseline/products-{handle}.html").read_text()
    live = (EVIDENCE / "products" / f"live-product-{handle}.html").read_text()
    b_ids = [s for s, _ in sections_above_reviews(base)]
    l = sections_above_reviews(live)
    l_ids = [s for s, _ in l]
    same_order = l_ids == b_ids[:len(l_ids)] and len(l_ids) > 0
    b = dict(sections_above_reviews(base))
    diff = [s for s, frag in l if norm(frag) != norm(b.get(s, ""))]
    if not same_order or diff:
        errs.append(f"product {handle}: sections above the link differ from the pre-deploy baseline: order {same_order}, text {diff}")
    return {"sections_compared": l_ids, "same_order": same_order, "visible_text_differs": diff}


def live_shots(handles=None):
    from playwright.sync_api import sync_playwright
    st = load_state()
    pages = {pd["handle"]: pd for pd, _, _ in vd._pages_and_records()}
    if handles:
        targets = [("hub", live_urls()["hub"])] + [(f"model:{h}", f"{STORE}/pages/sauna-database/{h}") for h in handles]
    else:
        targets = list(live_urls().items()) + [("product:golden-designs-copenhagen", f"{STORE}/products/golden-designs-copenhagen")]
    out = EVIDENCE / "shots"
    out.mkdir(parents=True, exist_ok=True)
    made = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for key, url in targets:
            for vw, name in ((1280, "desktop"), (390, "mobile")):
                if "preview_theme_id" in url:
                    raise SystemExit(f"REFUSED: a live screenshot may not use a preview URL: {url}")
                ctx = b.new_context(viewport={"width": vw, "height": 900}, user_agent=UA, device_scale_factor=1)
                if ctx.cookies():
                    raise SystemExit("REFUSED: the browser context is not empty")
                pg = ctx.new_page()
                pg.goto(url, wait_until="load", timeout=120000)
                pg.wait_for_timeout(2500)
                th = pg.evaluate("window.Shopify && Shopify.theme ? [String(Shopify.theme.id), Shopify.theme.role] : null")
                if not th or th[1] != "main" or any("preview" in c["name"] for c in ctx.cookies()):
                    raise SystemExit(f"HALT: {url} was not served to a logged-out visitor by the live theme ({th})")
                if key == "hub":
                    problem = hub_rows_problem(pg.content(), [pages[h]["inh_id"] for h in st.get("active_handles", [])])
                    if problem:
                        raise SystemExit(f"HALT: live hub in a clean browser: {problem}")
                if key.startswith("product:"):
                    el = pg.locator('[data-inhv="product-link"]')
                    el.scroll_into_view_if_needed(timeout=30000)
                    pg.wait_for_timeout(800)
                    f = out / f"live-{key.replace(':', '-')}-{name}.png"
                    pg.screenshot(path=str(f), full_page=False)
                else:
                    f = out / f"live-{key.replace(':', '-')}-{name}.png"
                    pg.screenshot(path=str(f), full_page=True)
                made.append(f)
                ctx.close()
                time.sleep(2)
        b.close()
    print("\n".join(str(m.relative_to(ROOT)) for m in made))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["setup", "verify-entries", "preview-proof", "snapshot-main", "deploy-main", "rollback",
                                     "activate", "publish-pages", "live-check", "live-shots", "hub-body",
                                     "update-entries", "snapshot-files", "deploy-files", "restore-step",
                                     "baseline-products", "deactivate", "finish-pages"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--allow-live-theme-id")
    ap.add_argument("--handles", nargs="*", default=[])
    ap.add_argument("--links", action="store_true")
    ap.add_argument("--step-name", default="design")
    ap.add_argument("--files", nargs="*", default=None,
                    help="snapshot-files: MAIN files this step changes; 'product-templates' expands to every product template in use")
    a = ap.parse_args(argv)
    if a.step == "setup":
        setup(a.write)
    elif a.step == "verify-entries":
        errs, n = verify_entries(expect_active=load_state().get("active_handles", []))
        print(f"{n} entries; {'PASS' if not errs else errs[:10]}")
        return 1 if errs else 0
    elif a.step == "preview-proof":
        preview_proof()
    elif a.step == "snapshot-main":
        snapshot_main()
    elif a.step == "deploy-main":
        if not a.allow_live_theme_id:
            raise SystemExit("REFUSED: deploy-main needs --allow-live-theme-id naming MAIN")
        deploy_main(a.allow_live_theme_id, a.write)
    elif a.step == "rollback":
        rollback(a.execute, a.allow_live_theme_id)
    elif a.step == "activate":
        activate(a.handles, a.write)
    elif a.step == "publish-pages":
        publish_pages(a.write)
    elif a.step == "live-check":
        return live_check(a.links)
    elif a.step == "live-shots":
        live_shots(a.handles or None)
    elif a.step == "hub-body":
        hub_body(a.write)
    elif a.step == "snapshot-files":
        files = a.files
        if files and "product-templates" in files:
            files = [f for f in files if f != "product-templates"] + product_templates_in_use(vd.admin())
        snapshot_files(a.step_name, files)
    elif a.step == "update-entries":
        update_entries(a.write)
    elif a.step == "deploy-files":
        deploy_files(a.step_name, a.allow_live_theme_id, a.write)
    elif a.step == "finish-pages":
        finish_pages(a.write)
    elif a.step == "baseline-products":
        baseline_products()
    elif a.step == "deactivate":
        deactivate(a.handles, a.write)
    elif a.step == "restore-step":
        restore_step(a.step_name, a.allow_live_theme_id, a.execute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
