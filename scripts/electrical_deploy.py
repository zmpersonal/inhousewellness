#!/usr/bin/env python3
"""Electrical tool, Round 1 Part B: the preview, end to end. Dry run unless --write.

    .venv/bin/python scripts/electrical_deploy.py duplicate [--write]   # MAIN -> a new preview theme (D9)
    .venv/bin/python scripts/electrical_deploy.py theme     [--write]   # files -> the preview theme only
    .venv/bin/python scripts/electrical_deploy.py pages     [--write] [--only HANDLE]
    .venv/bin/python scripts/electrical_deploy.py check                 # visitor-side proofs, read-only
    .venv/bin/python scripts/electrical_deploy.py teardown  [--write]   # the ONE-COMMAND undo
    .venv/bin/python scripts/electrical_deploy.py --self-test

Every id this script creates is recorded in data/electrical/preview-state.json, and teardown
deletes exactly those and nothing else: the pages it created and the preview theme it duplicated.

Guards (CLAUDE.md, "MAIN is resolved at run time"):
  * MAIN is resolved from the Admin API on every run and is never a write target here;
  * the Round 13 preview (146278776899) is never a target (Part B §2, D9);
  * a page that exists and was NOT created by this script is never updated or deleted.

Pages are created PUBLISHED with seo.hidden = 1 (D8): an unpublished page 404s even with
?preview_theme_id, so a hidden published page is the only way to load a real preview URL. Their
template exists only on the preview theme; on MAIN they render through the default page template.
The model-page and hub links are patched into the PREVIEW theme's own copies at deploy time; the
repo's INH Verified sections are not edited, so MAIN keeps matching the repo (CLAUDE.md governance).
"""
from __future__ import annotations

import argparse
import hashlib
import html as _h
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

STATE = ROOT / "data/electrical/preview-state.json"
INDEX = ROOT / "data/electrical/pages/index.json"
PAGES_DIR = ROOT / "data/electrical/pages"
ROUND13 = "146278776899"
PREVIEW_NAME = "Electrical R1 preview (duplicate of MAIN)"
STORE = "https://inhousewellness.com"
UA = "InHouseWellness-electrical-preview-check/1.0 (+https://inhousewellness.com)"

PASS_1 = ["assets/inh-electrical.css", "assets/inh-electrical.js", "assets/inh-electrical-data.json",
          "sections/inh-electrical-tool.liquid", "sections/inh-electrical-page.liquid"]
PASS_2 = ["templates/page.inh-electrical-tool.json", "templates/page.inh-electrical-page.json"]
PATCHED = ["sections/inh-verified-model.liquid", "sections/inh-verified-hub.liquid"]

MODEL_ANCHOR = '    <p class="inhv-small">Have a licensed electrician confirm the circuit before installation.</p>\n'
MODEL_LINK = ('    <p class="inhv-small" data-inhe="model-link"><a href="/pages/sauna-electrical-requirements?model='
              '{{ d.handle | url_encode }}">Check your home\'s electrical for this model</a></p>\n')
HUB_ANCHOR = '<a href="/pages/sauna-database-methodology">How records are verified</a>.</p>'
HUB_LINK = ('<a href="/pages/sauna-database-methodology">How records are verified</a>. '
            '<a href="/pages/sauna-electrical-requirements" data-inhe="hub-link">Sauna electrical requirements by model</a>.</p>')


# ------------------------------------------------------------------ guards --

def state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"theme": None, "pages": {}}


def save(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")


def admin():
    from verify_theme_asset_path import load_env, gql
    shop, token = load_env()
    if not (shop and token):
        raise SystemExit("HALT: no Shopify credentials")
    return lambda q, v=None: gql(shop, token, q, v or {})


def target_refusal(theme_id: str | None, main_id: str, role: str | None) -> str | None:
    """Pure, so --self-test can fire it without a network."""
    if not theme_id:
        return "REFUSED: no preview theme recorded; run `duplicate --write` first"
    if str(theme_id) == str(main_id) or role == "MAIN":
        return f"REFUSED: theme {theme_id} is the live theme; this round never writes to MAIN"
    if str(theme_id) == ROUND13:
        return f"REFUSED: {ROUND13} is the Round 13 preview, which Part B leaves untouched"
    if role is not None and role != "UNPUBLISHED":
        return f"REFUSED: theme {theme_id} has role {role}; only an UNPUBLISHED theme is a target"
    return None


def guard(q, theme_id):
    from verify_theme_asset_path import load_env, resolve_main
    main_id, main_name = resolve_main(*load_env())
    print(f"live theme (role MAIN, resolved at run time): {main_id} {main_name!r}")
    t = q("query($id: ID!) { theme(id: $id) { id name role } }", {"id": f"gid://shopify/OnlineStoreTheme/{theme_id}"})["theme"] \
        if theme_id else None
    why = target_refusal(theme_id, main_id, t["role"] if t else None)
    if why or not t:
        raise SystemExit(why or f"REFUSED: theme {theme_id} not found")
    return t, main_id


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


# --------------------------------------------------------------- duplicate --

def duplicate(write: bool) -> None:
    q = admin()
    st = state()
    if st.get("theme"):
        raise SystemExit(f"HALT: a preview theme is already recorded ({st['theme']['id']}); teardown first")
    from verify_theme_asset_path import load_env, resolve_main
    main_id, main_name = resolve_main(*load_env())
    n = len(q("{ themes(first: 30) { nodes { id } } }")["themes"]["nodes"])
    print(f"MAIN {main_id} {main_name!r}; theme slots used {n} of 20")
    if n >= 20:
        raise SystemExit("HALT: no free theme slot (Part B §7: anything needing a slot beyond what is free stops)")
    print(f"  {'duplicate' if write else 'would duplicate'} MAIN {main_id} as {PREVIEW_NAME!r}")
    if not write:
        return
    r = q("mutation($id: ID!, $name: String) { themeDuplicate(id: $id, name: $name) { newTheme { id name role } "
          "userErrors { field message } } }", {"id": f"gid://shopify/OnlineStoreTheme/{main_id}", "name": PREVIEW_NAME})["themeDuplicate"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}")
    t = r["newTheme"]
    tid = t["id"].rsplit("/", 1)[1]
    st["theme"] = {"id": tid, "name": t["name"], "duplicated_from": main_id,
                   "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    save(st)
    print(f"  created theme {tid} role {t['role']} -> recorded in {STATE.relative_to(ROOT)}")


# ------------------------------------------------------------------- theme --

FILES_Q = """query($id: ID!, $f: [String!]) { theme(id: $id) { files(first: 50, filenames: $f) {
  nodes { filename checksumMd5 size body { ... on OnlineStoreThemeFileBodyText { content } } } } } }"""
UPSERT_M = """mutation($id: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $id, files: $files) { upsertedThemeFiles { filename } userErrors { filename code message } } }"""


def patch_model(src: str) -> str:
    if 'data-inhe="model-link"' in src:
        return src
    if src.count(MODEL_ANCHOR) != 1:
        raise SystemExit("HALT: the model section's electrical anchor is not where it was; not patching blind")
    return src.replace(MODEL_ANCHOR, MODEL_ANCHOR + MODEL_LINK)


def patch_hub(src: str) -> str:
    if 'data-inhe="hub-link"' in src:
        return src
    if src.count(HUB_ANCHOR) != 1:
        raise SystemExit("HALT: the hub's disclosure anchor is not where it was; not patching blind")
    return src.replace(HUB_ANCHOR, HUB_LINK)


def read_files(q, tid, names):
    nodes = q(FILES_Q, {"id": f"gid://shopify/OnlineStoreTheme/{tid}", "f": names})["theme"]["files"]["nodes"]
    return {n["filename"]: n for n in nodes}


def theme(write: bool) -> None:
    from verified_deploy import lint_payload
    q = admin()
    st = state()
    tid = (st.get("theme") or {}).get("id")
    t, _ = guard(q, tid)
    print(f"target: {t['name']} ({tid}), role {t['role']}")
    cur = read_files(q, tid, PATCHED)
    files = {n: (ROOT / n).read_bytes() for n in PASS_1 + PASS_2}
    files[PATCHED[0]] = patch_model(cur[PATCHED[0]]["body"]["content"]).encode()
    files[PATCHED[1]] = patch_hub(cur[PATCHED[1]]["body"]["content"]).encode()
    lint_payload(b"\n".join(files.values()).decode("utf-8", "replace"), "electrical theme files")
    for n, b in files.items():
        print(f"  {'write' if write else 'would write'}  {n}  {len(b)} B  md5 {md5(b)}")
    if not write:
        return
    for batch in (PASS_1 + PATCHED, PASS_2):     # sections before the templates that name them
        payload = [{"filename": n, "body": {"type": "TEXT", "value": files[n].decode()}} for n in batch]
        r = q(UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{tid}", "files": payload})["themeFilesUpsert"]
        if r["userErrors"]:
            raise SystemExit(f"HALT after partial write: {r['userErrors']}")
    back = read_files(q, tid, list(files))
    exact, same_json, bad = [], [], []
    for n, b in files.items():
        got = back.get(n)
        if got and got.get("checksumMd5") == md5(b):
            exact.append(n)
        elif got and n.endswith(".json") and json.loads(re.sub(r"/\*.*?\*/", "", got["body"]["content"], flags=re.S)) == json.loads(b):
            same_json.append(n)
        else:
            bad.append(n)
    print(f"read-back: {len(exact)} byte-identical by MD5, {len(same_json)} JSON-identical after Shopify's reformat {same_json}, "
          f"{len(bad)} mismatched {bad}")
    st["theme"]["files"] = {n: md5(b) for n, b in files.items()}
    st["theme"]["deployed_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    save(st)
    if bad:
        raise SystemExit(1)


# ------------------------------------------------------------------- pages --

PAGE_FIND_Q = "query($q: String!) { pages(first: 10, query: $q) { nodes { id handle isPublished templateSuffix } } }"
PAGE_READ_Q = """query($id: ID!) { page(id: $id) { id handle title isPublished templateSuffix body
  hidden: metafield(namespace: "seo", key: "hidden") { value } desc: metafield(namespace: "global", key: "description_tag") { value } } }"""
PAGE_CREATE_M = "mutation($p: PageCreateInput!) { pageCreate(page: $p) { page { id handle } userErrors { field message } } }"
PAGE_UPDATE_M = "mutation($id: ID!, $p: PageUpdateInput!) { pageUpdate(id: $id, page: $p) { page { id handle } userErrors { field message } } }"
PAGE_DELETE_M = "mutation($id: ID!) { pageDelete(id: $id) { deletedPageId userErrors { field message } } }"


def visible(s: str) -> str:
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def pages(write: bool, only: str | None) -> None:
    from verified_deploy import lint_payload
    q = admin()
    st = state()
    idx = json.loads(INDEX.read_text())["pages"]
    for p in idx:
        if only and p["handle"] != only:
            continue
        body = (PAGES_DIR / f"{p['handle']}.html").read_text()
        lint_payload(body, p["handle"])
        found = [n for n in q(PAGE_FIND_Q, {"q": f"handle:{p['handle']}"})["pages"]["nodes"] if n["handle"] == p["handle"]]
        ours = st["pages"].get(p["handle"], {}).get("id")
        if found and found[0]["id"] != ours:
            raise SystemExit(f"HALT: page {p['handle']} exists and was not created by this script; not touching it")
        fields = {"title": p["title"], "body": body, "isPublished": True, "templateSuffix": p["template_suffix"],
                  "metafields": [{"namespace": "seo", "key": "hidden", "type": "number_integer", "value": "1"},
                                 {"namespace": "global", "key": "description_tag", "type": "single_line_text_field",
                                  "value": p["description"]}]}
        print(f"  {'write' if write else 'would write'} page {p['handle']} (published, seo.hidden=1, template {p['template_suffix']}) {len(body)} chars")
        if not write:
            continue
        if found:
            r = q(PAGE_UPDATE_M, {"id": found[0]["id"], "p": fields})["pageUpdate"]
        else:
            r = q(PAGE_CREATE_M, {"p": dict(fields, handle=p["handle"])})["pageCreate"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {p['handle']}: {r['userErrors']}")
        pid = r["page"]["id"]
        st["pages"][p["handle"]] = {"id": pid, "created_at": st["pages"].get(p["handle"], {}).get("created_at")
                                    or datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        save(st)                                   # recorded before the read-back, so teardown can always find it
        back = q(PAGE_READ_Q, {"id": pid})["page"]
        wrong = []
        if back["handle"] != p["handle"]:
            wrong.append(("handle", back["handle"]))
        if back["templateSuffix"] != p["template_suffix"]:
            wrong.append(("templateSuffix", back["templateSuffix"]))
        if back["isPublished"] is not True:
            wrong.append(("isPublished", back["isPublished"]))
        if (back.get("hidden") or {}).get("value") != "1":
            wrong.append(("seo.hidden", back.get("hidden")))
        if visible(back["body"]) != visible(body):    # Shopify pretty-prints markup; words must match exactly
            wrong.append(("body visible text", "differs"))
        if wrong:
            raise SystemExit(f"HALT: {p['handle']} read back differs: {wrong}")
        print(f"    read-back: {pid} published, seo.hidden=1, template {back['templateSuffix']}, visible text identical")


# ------------------------------------------------------------------- check --

def fetch(url: str) -> tuple[int, str]:
    """A fresh cookie jar per request: ?preview_theme_id answers 302 + a cookie before it renders."""
    import http.cookiejar
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def sitemap_urls() -> set[str]:
    """Every URL in the live sitemap, following the index into each child sitemap."""
    urls, todo, seen = set(), [f"{STORE}/sitemap.xml"], set()
    while todo:
        u = todo.pop()
        if u in seen:
            continue
        seen.add(u)
        _, x = fetch(u)
        is_index = "<sitemapindex" in x
        for loc in re.findall(r"<loc>([^<]+)</loc>", x):
            loc = _h.unescape(loc)
            (todo.append(loc) if is_index else urls.add(loc))
    return urls


ROBOTS_RX = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']', re.I)


def check() -> int:
    """Visitor-side: every page answers on MAIN and on the preview, carries noindex in its HTML, is
    absent from the live sitemap, and is linked from no live page, menu or MAIN theme file."""
    st = state()
    tid = (st.get("theme") or {}).get("id")
    handles = [p["handle"] for p in json.loads(INDEX.read_text())["pages"]]
    sm = sitemap_urls()
    fails = []
    for h in handles:
        for label, url in (("live", f"{STORE}/pages/{h}"), ("preview", f"{STORE}/pages/{h}?preview_theme_id={tid}")):
            code, body = fetch(url)
            robots = ROBOTS_RX.findall(body)
            noindex = any("noindex" in r.lower() for r in robots)
            print(f"  {label:7} {h:40} {code} robots={robots or 'none'}")
            if code != 200 or not noindex:
                fails.append(f"{label} {h}: status {code}, noindex {noindex}")
        if any(f"/pages/{h}" in u for u in sm):
            fails.append(f"{h} is IN the live sitemap")
    print(f"  sitemap: {len(sm)} URLs read; none of the {len(handles)} handles present: {not any('in the live sitemap' in f for f in fails)}")
    q = admin()
    from verify_theme_asset_path import load_env, resolve_main
    main_id, _ = resolve_main(*load_env())
    inbound = inbound_links(q, main_id, handles, {v["id"] for v in st["pages"].values()})
    for x in inbound:
        fails.append(f"inbound link: {x}")
    print(f"  inbound links from live pages, articles, menus and MAIN theme files: {len(inbound)}")
    for f in fails:
        print(f"FAIL {f}")
    print("check: PASS" if not fails else f"check: {len(fails)} failure(s)")
    return 1 if fails else 0


def inbound_links(q, main_id: str, handles: list[str], own_ids: set[str]) -> list[str]:
    # OUR links only: relative, or on our own hosts. A path is not a page: the first run flagged an
    # article linking thesaunaheater.com/pages/sauna-heater-size-calculator, another store's page.
    paths = "|".join(re.escape(f"/pages/{h}") for h in handles)
    rx = re.compile(rf"""(?:href=["']|"url":\s*"|^|\s)(?:https?://(?:www\.)?(?:inhousewellness\.com|inhousewellness\.myshopify\.com))?(?:{paths})(?![\w-])""")
    out = []
    after = None
    while True:   # every page body on the store, except the ones this round created
        d = q("query($a: String) { pages(first: 100, after: $a) { nodes { id handle body } pageInfo { hasNextPage endCursor } } }",
              {"a": after})["pages"]
        out += [f"page {n['handle']}" for n in d["nodes"] if n["id"] not in own_ids and rx.search(n["body"] or "")]
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
    after = None
    while True:
        d = q("query($a: String) { articles(first: 100, after: $a) { nodes { handle body } pageInfo { hasNextPage endCursor } } }",
              {"a": after})["articles"]
        out += [f"article {n['handle']}" for n in d["nodes"] if rx.search(n["body"] or "")]
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
    menus = q("{ menus(first: 50) { nodes { handle items { url items { url items { url } } } } } }")["menus"]["nodes"]
    out += [f"menu {m['handle']}" for m in menus if rx.search(json.dumps(m))]
    after = None
    while True:   # every text file of the LIVE theme
        d = q("""query($id: ID!, $a: String) { theme(id: $id) { files(first: 250, after: $a) { nodes { filename
              body { ... on OnlineStoreThemeFileBodyText { content } } } pageInfo { hasNextPage endCursor } } } }""",
              {"id": f"gid://shopify/OnlineStoreTheme/{main_id}", "a": after})["theme"]["files"]
        out += [f"MAIN theme file {n['filename']}" for n in d["nodes"] if rx.search((n.get("body") or {}).get("content") or "")]
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
    return out


# ---------------------------------------------------------------- teardown --

def teardown(write: bool) -> None:
    """Deletes exactly what this round created: its pages, then its preview theme. Never MAIN,
    never Round 13, never a page it did not create (ids come only from preview-state.json)."""
    st = state()
    pg = st.get("pages") or {}
    t = st.get("theme")
    if not pg and not t:
        print("teardown: nothing recorded; nothing to do")
        return
    q = admin()
    for h, rec in sorted(pg.items()):
        live = q("query($id: ID!) { page(id: $id) { id handle } }", {"id": rec["id"]})["page"]
        if live and live["handle"] != h:
            raise SystemExit(f"HALT: {rec['id']} is now {live['handle']!r}, not {h!r}; not deleting")
        print(f"  {'delete' if write else 'would delete'} page {h} ({rec['id']}){'' if live else ' -- already gone'}")
        if write and live:
            r = q(PAGE_DELETE_M, {"id": rec["id"]})["pageDelete"]
            if r["userErrors"]:
                raise SystemExit(f"HALT: {r['userErrors']}")
    if t:
        tt, _ = guard(q, t["id"])
        print(f"  {'delete' if write else 'would delete'} theme {t['id']} {tt['name']!r} (role {tt['role']})")
        if write:
            r = q("mutation($id: ID!) { themeDelete(id: $id) { deletedThemeId userErrors { field message } } }",
                  {"id": f"gid://shopify/OnlineStoreTheme/{t['id']}"})["themeDelete"]
            if r["userErrors"]:
                raise SystemExit(f"HALT: {r['userErrors']}")
    if write:
        save({"theme": None, "pages": {}, "torn_down_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
        print("teardown: done; preview-state.json cleared")
    else:
        print("teardown: DRY RUN, nothing deleted. Re-run with --write to delete the above.")


# --------------------------------------------------------------- self-test --

def self_test() -> None:
    assert target_refusal("999", "999", "MAIN")
    assert target_refusal("1", "999", "MAIN")                 # role says MAIN even if the id differs
    assert target_refusal(ROUND13, "999", "UNPUBLISHED")
    assert target_refusal(None, "999", None)
    assert target_refusal("1", "999", "DEVELOPMENT")
    assert target_refusal("1", "999", "UNPUBLISHED") is None
    src = "x\n" + MODEL_ANCHOR + "y\n"
    assert patch_model(src).count('data-inhe="model-link"') == 1 and patch_model(patch_model(src)) == patch_model(src)
    try:
        patch_model("no anchor here")
        raise AssertionError("patched blind")
    except SystemExit:
        pass
    assert patch_hub("a " + HUB_ANCHOR).count('data-inhe="hub-link"') == 1
    paths = "|".join(re.escape(f"/pages/{h}") for h in ["sauna-heater-size-calculator"])
    rx = re.compile(rf"""(?:href=["']|"url":\s*"|^|\s)(?:https?://(?:www\.)?(?:inhousewellness\.com|inhousewellness\.myshopify\.com))?(?:{paths})(?![\w-])""")
    assert not rx.search('<a href="https://thesaunaheater.com/pages/sauna-heater-size-calculator">')
    assert rx.search('<a href="/pages/sauna-heater-size-calculator">') and rx.search('<a href="https://inhousewellness.com/pages/sauna-heater-size-calculator?x=1">')
    print("electrical_deploy self-test: ok")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", nargs="?", choices=["duplicate", "theme", "pages", "check", "teardown"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        self_test()
        return
    if a.step == "duplicate":
        duplicate(a.write)
    elif a.step == "theme":
        theme(a.write)
    elif a.step == "pages":
        pages(a.write, a.only)
    elif a.step == "check":
        sys.exit(check())
    elif a.step == "teardown":
        teardown(a.write)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
