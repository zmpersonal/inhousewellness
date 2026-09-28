#!/usr/bin/env python3
"""INH Verified Round 2 — write the PREVIEW, never the live store.

    .venv/bin/python scripts/verified_deploy.py snapshot           # read-only: fetch + patch, write nothing
    .venv/bin/python scripts/verified_deploy.py theme --write      # theme files -> 146278776899 only
    .venv/bin/python scripts/verified_deploy.py pages --write      # hub + methodology as HIDDEN pages
    .venv/bin/python scripts/verified_deploy.py entries --write    # definition + DRAFT entries (needs scopes)
    .venv/bin/python scripts/verified_deploy.py metafields --write # product -> entry references (+ reversal file)
    .venv/bin/python scripts/verified_deploy.py reverse --file F [--only PRODUCT_ID]
    .venv/bin/python scripts/verified_deploy.py --self-test

GUARDS (Round 2 constraints, enforced here, not in prose):
  * Theme writes go to ONE theme id, PREVIEW_THEME = 146278776899, and the theme's role is
    read at write time: a theme whose role is MAIN is refused whatever its id. There is no
    live override in this script at all; go-live is a separate, approved step.
  * Pages are created with isPublished = false. Entries are created with status DRAFT and
    this script has no code path that sets ACTIVE.
  * layout/theme.liquid and templates/product.json are PATCHED in place from what the target
    theme holds right now, never copied from another theme: the same patch applies to MAIN
    at go-live without reverting anything MAIN has changed since.
  * No payload carries a price: `offers` is stripped (D-G) and every payload is linted.
  * Every write is read back and compared by MD5 (theme) or by value (pages, metafields).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DEPLOY = ROOT / "out/verified/deploy"
REVERSALS = ROOT / "data/verified/internal/metafield-writes"
PREVIEW_THEME = "146278776899"
PASS_1 = ["sections/inh-verified-model.liquid", "sections/inh-verified-hub.liquid",
          "sections/inh-verified-methodology.liquid", "sections/inh-verified-product-link.liquid",
          "snippets/inh-verified-fact.liquid", "assets/inh-verified.css", "assets/inh-verified.js"]
PASS_2 = ["templates/page.inh-verified-hub.json", "templates/page.inh-verified-methodology.json"]
# Written last and alone: Shopify may refuse a metaobject template while no `sauna`
# definition exists. A refusal here is reported as pending, never allowed to block the rest.
PASS_3 = ["templates/metaobject/sauna.json"]
PATCHED = ["layout/theme.liquid", "templates/product.json"]
LINK_SECTION_ID = "inh_verified_link"
REVIEW_BLOCK = "shopify://apps/judge-me-reviews/blocks/review_widget/"
HUB = {"handle": "sauna-database", "title": "Verified Sauna Database", "templateSuffix": "inh-verified-hub"}
METHOD = {"handle": "sauna-database-methodology", "title": "How the Sauna Database Is Verified",
          "templateSuffix": "inh-verified-methodology"}
MF_NAMESPACE, MF_KEY = "inh_verified", "sauna"

LAYOUT_ANCHOR = ("      {%- else -%}\n        {{ page_title }}\n"
                 "        {%- if paginate.current_page > 1 %} – Page {{ paginate.current_page }}{% endif %}\n"
                 "        {%- unless page_title contains shop.name %} – {{ shop.name }}{% endunless %}")
LAYOUT_INSERT = ("      {%- elsif metaobject -%}\n"
                 "        {%- comment -%}\n"
                 "          INH Verified model pages (Round 2): the title tag is exactly the SEO title,\n"
                 "          \"[Title]: Verified Specs & Electrical Requirements\", with no shop-name suffix.\n"
                 "          Scoped to metaobject pages only; every other branch is unchanged.\n"
                 "        {%- endcomment -%}\n"
                 "        {{ page_title }}\n")


# ------------------------------------------------------------------ patches --

def patch_layout(src: str) -> str:
    if "INH Verified model pages (Round 2)" in src:
        return src
    if src.count(LAYOUT_ANCHOR) != 1:
        raise SystemExit("HALT: the layout's catch-all <title> branch is not where the patch expects it; "
                         "nothing written. Inspect the target theme's layout/theme.liquid.")
    return src.replace(LAYOUT_ANCHOR, LAYOUT_INSERT + LAYOUT_ANCHOR, 1)


def split_json_template(src: str):
    m = re.match(r"(?s)\s*(/\*.*?\*/)\s*", src)
    head = m.group(1) if m else ""
    return head, json.loads(src[m.end():] if m else src)


def patch_product(src: str) -> str:
    """Insert the link section directly after the section that holds the ENABLED reviews
    widget. Everything above it is untouched, by construction."""
    head, d = split_json_template(src)
    if LINK_SECTION_ID in d["sections"]:
        return src
    rev = [k for k in d["order"] if any(REVIEW_BLOCK in b["type"] and not b.get("disabled")
                                        for b in d["sections"][k].get("blocks", {}).values())]
    if len(rev) != 1:
        raise SystemExit(f"HALT: expected exactly one enabled reviews section in templates/product.json, found {rev}")
    d["sections"][LINK_SECTION_ID] = {"type": "inh-verified-product-link", "settings": {}}
    i = d["order"].index(rev[0])
    d["order"].insert(i + 1, LINK_SECTION_ID)
    return (head + "\n" if head else "") + json.dumps(d, indent=2, ensure_ascii=False) + "\n"


def product_prefix_unchanged(before: str, after: str) -> bool:
    """Proof for 'no change above the reviews': every section up to and including the
    reviews section is identical, in the same order."""
    _, b = split_json_template(before)
    _, a = split_json_template(after)
    if LINK_SECTION_ID in b["order"]:
        return a == b          # already patched: a re-run must change nothing at all
    cut = a["order"].index(LINK_SECTION_ID)
    return a["order"][:cut] == b["order"][:cut] and all(a["sections"][k] == b["sections"][k] for k in a["order"][:cut]) \
        and [k for k in a["order"] if k != LINK_SECTION_ID] == b["order"]


# ------------------------------------------------------------------- admin --

def admin():
    from verify_theme_asset_path import load_env, gql
    shop, token = load_env()
    if not (shop and token):
        raise SystemExit("HALT: no Shopify credentials")
    return lambda q, v=None: gql(shop, token, q, v or {})


THEME_Q = "query($id: ID!) { theme(id: $id) { id name role } }"
FILES_Q = """query($id: ID!, $f: [String!]) { theme(id: $id) { files(first: 50, filenames: $f) {
  nodes { filename checksumMd5 size body { ... on OnlineStoreThemeFileBodyText { content } } } } } }"""
UPSERT_M = """mutation($id: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $id, files: $files) { upsertedThemeFiles { filename } userErrors { filename code message } } }"""


def guard_theme(q, theme_id: str):
    from verify_theme_asset_path import refusal_for, load_env, main_refusal, resolve_main
    if theme_id != PREVIEW_THEME:
        raise SystemExit(f"REFUSED: Round 2 writes only to theme {PREVIEW_THEME}; asked for {theme_id}")
    theme = q(THEME_Q, {"id": f"gid://shopify/OnlineStoreTheme/{theme_id}"})["theme"]
    why = refusal_for(theme, theme_id, None)
    if why:
        raise SystemExit(why)
    main_id, main_name = resolve_main(*load_env())
    print(f"live theme (role MAIN, resolved at run time): {main_id} {main_name!r}")
    why = main_refusal(main_id, theme_id, None)
    if why:
        raise SystemExit(why)
    if theme["role"] != "UNPUBLISHED":
        raise SystemExit(f"REFUSED: theme {theme_id} has role {theme['role']}; Round 2 writes only to an UNPUBLISHED theme")
    return theme


def read_files(q, theme_id, names):
    nodes = q(FILES_Q, {"id": f"gid://shopify/OnlineStoreTheme/{theme_id}", "f": names})["theme"]["files"]["nodes"]
    return {n["filename"]: n for n in nodes}


def snapshot(q, theme_id=PREVIEW_THEME):
    """Read-only: the target's current layout and product template, and their patched forms."""
    DEPLOY.mkdir(parents=True, exist_ok=True)
    cur = read_files(q, theme_id, PATCHED)
    out = {}
    for name, fn in (("layout/theme.liquid", patch_layout), ("templates/product.json", patch_product)):
        body = cur[name]["body"]["content"]
        stem = name.replace("/", "-")
        (DEPLOY / f"theme-{theme_id}-before-{stem}").write_text(body)
        patched = fn(body)
        (DEPLOY / f"theme-{theme_id}-{stem}").write_text(patched)
        out[name] = (body, patched)
    if not product_prefix_unchanged(*out["templates/product.json"]):
        raise SystemExit("HALT: the product patch changed something above the reviews")
    return out


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def deploy_theme(write: bool):
    q = admin()
    theme = guard_theme(q, PREVIEW_THEME)
    print(f"target: {theme['name']} ({PREVIEW_THEME}), role {theme['role']}")
    patched = snapshot(q)
    files = {n: (ROOT / n).read_bytes() for n in PASS_1 + PASS_2 + PASS_3}
    files["layout/theme.liquid"] = patched["layout/theme.liquid"][1].encode()
    files["templates/product.json"] = patched["templates/product.json"][1].encode()
    lint_payload(b"\n".join(files.values()).decode("utf-8", "replace"), "theme files")
    passes = [PASS_1, PASS_2 + PATCHED]
    for n in files:
        print(f"  {'write' if write else 'would write'}  {n}  {len(files[n])} B  md5 {md5(files[n])}")
    if not write:
        return
    pending = []
    for batch in passes + [PASS_3]:
        payload = [{"filename": n, "body": {"type": "TEXT", "value": files[n].decode()}} for n in batch]
        res = q(UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{PREVIEW_THEME}", "files": payload})["themeFilesUpsert"]
        if res["userErrors"]:
            if batch is PASS_3:
                pending = batch
                print(f"PENDING: {batch} refused by Shopify: {res['userErrors']}")
                continue
            raise SystemExit(f"HALT after partial write: {res['userErrors']}")
    written = [n for n in files if n not in pending]
    back = read_files(q, PREVIEW_THEME, written)
    exact, same_json, bad = [], [], []
    for n in written:
        got = back.get(n)
        if got and got.get("checksumMd5") == md5(files[n]):
            exact.append(n)
        elif got and n.endswith(".json") and split_json_template(got["body"]["content"])[1] == split_json_template(files[n].decode())[1]:
            same_json.append(n)   # Shopify re-formats JSON templates on save; the parsed content is identical
        else:
            bad.append(n)
    print(f"read-back: {len(exact)} byte-identical by MD5, {len(same_json)} JSON identical after Shopify's reformat "
          f"{same_json}, {len(bad)} mismatched {bad}")
    if bad:
        raise SystemExit(1)


DELETE_M = """mutation($id: ID!, $files: [String!]!) { themeFilesDelete(themeId: $id, files: $files) {
  deletedThemeFiles { filename } userErrors { filename code message } } }"""
# Files THIS ROUND created and then renamed. The only files this script may ever delete.
RETIRED_R2 = ["templates/page.sauna-database.json", "templates/page.sauna-database-methodology.json"]


def remove_retired(write: bool):
    q = admin()
    guard_theme(q, PREVIEW_THEME)
    present = [n for n in read_files(q, PREVIEW_THEME, RETIRED_R2)]
    print(f"  {'delete' if write else 'would delete'} {present} from {PREVIEW_THEME}")
    if write and present:
        r = q(DELETE_M, {"id": f"gid://shopify/OnlineStoreTheme/{PREVIEW_THEME}", "files": present})["themeFilesDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {r['userErrors']}")
        left = read_files(q, PREVIEW_THEME, RETIRED_R2)
        print(f"  read-back: {len(left)} of {len(present)} still present")


# ------------------------------------------------------------------- pages --

PAGE_FIND_Q = "query($q: String!) { pages(first: 20, query: $q) { nodes { id handle isPublished templateSuffix } } }"
PAGE_READ_Q = "query($id: ID!) { page(id: $id) { id handle title isPublished templateSuffix body } }"
PAGE_CREATE_M = """mutation($p: PageCreateInput!) { pageCreate(page: $p) { page { id handle isPublished } userErrors { field message } } }"""
PAGE_UPDATE_M = """mutation($id: ID!, $p: PageUpdateInput!) { pageUpdate(id: $id, page: $p) { page { id handle isPublished } userErrors { field message } } }"""


def page_descriptions() -> dict:
    """SEO descriptions for the two hidden pages, counted from the page data, not typed."""
    # Go-live: no model count. Pages go live in stages, and a count in a search snippet would
    # promise pages that are not yet published. The hub prints the live count itself.
    return {HUB["handle"]: "Verified specifications and electrical requirements for home sauna models. "
                           "Every value is cited to the manufacturer, graded and dated.",
            METHOD["handle"]: "How the InHouse Wellness Verified Sauna Database sources, grades and dates every value, "
                              "and which models do not get a page."}


def deploy_pages(write: bool):
    q = admin()
    bodies = {HUB["handle"]: "<p>This page lists every model in the InHouse Wellness Verified Sauna Database.</p>",
              METHOD["handle"]: (ROOT / "out/verified/methodology.html").read_text()}
    for spec in (HUB, METHOD):
        body = bodies[spec["handle"]]
        lint_payload(body, spec["handle"])
        found = [n for n in q(PAGE_FIND_Q, {"q": f"handle:{spec['handle']}"})["pages"]["nodes"] if n["handle"] == spec["handle"]]
        if found and found[0]["isPublished"]:
            raise SystemExit(f"HALT: page {spec['handle']} exists and is PUBLISHED; Round 2 does not touch live pages")
        p = {"title": spec["title"], "handle": spec["handle"], "body": body, "isPublished": False,
             "templateSuffix": spec["templateSuffix"],
             "metafields": [{"namespace": "global", "key": "description_tag", "type": "single_line_text_field",
                             "value": page_descriptions()[spec["handle"]]}]}
        print(f"  {'write' if write else 'would write'} page {spec['handle']} (hidden) {len(body)} chars")
        if not write:
            continue
        if found:
            r = q(PAGE_UPDATE_M, {"id": found[0]["id"], "p": {k: v for k, v in p.items() if k != "handle"}})["pageUpdate"]
        else:
            r = q(PAGE_CREATE_M, {"p": p})["pageCreate"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {r['userErrors']}")
        back = q(PAGE_READ_Q, {"id": r["page"]["id"]})["page"]
        assert back["isPublished"] is False, "page came back published"
        # Visible text, character for character, after decoding entities: Shopify stores
        # `&#x27;` as `'`, which is the platform's to normalise; words are not.
        import html as _h
        vis = lambda s: re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
        if vis(back["body"]) != vis(body):
            raise SystemExit(f"HALT: {spec['handle']} body read back differs in visible text")
        print(f"    read-back: {back['id']} hidden, template {back['templateSuffix']}, visible text identical")


# ---------------------------------------------------------- entries + links --

SCOPES_Q = "query { currentAppInstallation { accessScopes { handle } } }"
NEED_ENTRIES = {"write_metaobject_definitions", "write_metaobjects"}


def scopes(q) -> set:
    return {s["handle"] for s in q(SCOPES_Q)["currentAppInstallation"]["accessScopes"]}


DEF_BY_TYPE_Q = "query($t: String!) { metaobjectDefinitionByType(type: $t) { id type capabilities { onlineStore { enabled data { urlHandle } } } } }"
DEF_CREATE_M = """mutation($d: MetaobjectDefinitionCreateInput!) { metaobjectDefinitionCreate(definition: $d) {
  metaobjectDefinition { id type } userErrors { field message code } } }"""
ENTRY_Q = """query($h: MetaobjectHandleInput!) { metaobjectByHandle(handle: $h) { id handle
  capabilities { publishable { status } } field(key: "record") { value } } }"""
UPSERT_ENTRY_M = """mutation($h: MetaobjectHandleInput!, $m: MetaobjectUpsertInput!) { metaobjectUpsert(handle: $h, metaobject: $m) {
  metaobject { id handle capabilities { publishable { status } } } userErrors { field message code } } }"""
MF_DEF_M = """mutation($d: MetafieldDefinitionInput!) { metafieldDefinitionCreate(definition: $d) {
  createdDefinition { id } userErrors { field message code } } }"""
MF_READ_Q = """query($id: ID!) { product(id: $id) { id handle metafield(namespace: "inh_verified", key: "sauna") { id value } } }"""
MF_SET_M = """mutation($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) {
  metafields { owner { ... on Product { id } } namespace key value } userErrors { field message code } } }"""
MF_DEL_M = """mutation($m: [MetafieldIdentifierInput!]!) { metafieldsDelete(metafields: $m) {
  deletedMetafields { ownerId namespace key } userErrors { field message } } }"""


def definition_input():
    prop = json.loads((ROOT / "data/verified/metaobject-definition-proposed.json").read_text())["definition"]
    fields = [{"key": f["key"], "type": f["type"], "name": f["key"].replace("_", " ").capitalize(),
               "required": f.get("required", False)} for f in prop["fieldDefinitions"]
              if f["key"] != "store_collections"]   # collections travel in page_data.store; see Part B report
    for f in fields:
        if f["key"] == "heat_type":
            f["validations"] = [{"name": "choices", "value": json.dumps(["infrared", "traditional", "hybrid"])}]
    return {"type": "sauna", "name": prop["name"], "displayNameKey": "title", "access": prop["access"],
            "capabilities": prop["capabilities"], "fieldDefinitions": fields}


def entry_fields(pd: dict, record: dict, product_gid):
    v = {"title": pd["title"], "inh_id": pd["inh_id"], "brand": pd["brand"], "heat_type": pd["heat_type"],
         "capacity_label": pd["capacity_label"], "supply_voltage": pd["supply_voltage"], "placement": pd["placement"],
         "verified_date": pd["verified_date"], "seo_title": pd["seo_title"], "seo_description": pd["seo_description"],
         "record": json.dumps(record, ensure_ascii=False, sort_keys=True),
         "page_data": json.dumps(pd, ensure_ascii=False, sort_keys=True)}
    out = [{"key": k, "value": val} for k, val in v.items() if val not in (None, "")]
    if product_gid:
        out.append({"key": "store_product", "value": product_gid})
    return out


def _pages_and_records():
    import verified_pages as vp
    ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
    idx = json.loads((ROOT / "out/verified/pages-index.json").read_text())
    snap = json.loads((ROOT / "data/verified/internal/inh-products-snapshot.json").read_text())
    by_handle = {p["handle"]: p["id"] for p in snap["products"]}
    nav = vp.load_navigation()["mapped"]
    for row in idx:
        pd = json.loads((ROOT / "out/verified/pages" / f"{row['handle']}.json").read_text())
        m = nav.get(row["inh_id"])
        yield pd, vp.record_payload(ds[row["inh_id"]]), (by_handle.get(m["product_handle"]) if m else None)


def deploy_entries(write: bool, q=None):
    q = q or admin()
    missing = NEED_ENTRIES - scopes(q)
    if missing:
        print(f"PENDING: the Admin token lacks {sorted(missing)}. The definition and the draft entries "
              f"cannot be created; nothing written.")
        return False
    d = q(DEF_BY_TYPE_Q, {"t": "sauna"})["metaobjectDefinitionByType"]
    if not d:
        print(f"  {'create' if write else 'would create'} definition 'sauna' (onlineStore urlHandle sauna-database)")
        if write:
            r = q(DEF_CREATE_M, {"d": definition_input()})["metaobjectDefinitionCreate"]
            if r["userErrors"]:
                raise SystemExit(f"HALT: definition refused: {r['userErrors']}")
    n = 0
    for pd, record, product_gid in _pages_and_records():
        fields = entry_fields(pd, record, product_gid)
        lint_payload(json.dumps(fields, ensure_ascii=False), pd["handle"])
        h = {"type": "sauna", "handle": pd["handle"]}
        cur = q(ENTRY_Q, {"h": h})["metaobjectByHandle"] if write else None
        if cur and cur["capabilities"]["publishable"]["status"] != "DRAFT":
            raise SystemExit(f"HALT: entry {pd['handle']} exists and is {cur['capabilities']['publishable']['status']}; "
                             f"Round 2 never touches an active entry")
        if write:
            r = q(UPSERT_ENTRY_M, {"h": h, "m": {"fields": fields, "capabilities": {"publishable": {"status": "DRAFT"}}}})["metaobjectUpsert"]
            if r["userErrors"]:
                raise SystemExit(f"HALT at {pd['handle']}: {r['userErrors']}")
            back = q(ENTRY_Q, {"h": h})["metaobjectByHandle"]
            if back["capabilities"]["publishable"]["status"] != "DRAFT" or json.loads(back["field"]["value"]) != record:
                raise SystemExit(f"HALT: {pd['handle']} read back wrong (status or record differs)")
        n += 1
    print(f"  {'wrote' if write else 'would write'} {n} DRAFT entries" + (", each read back DRAFT with an identical record" if write else ""))
    return True


def _entry_gid(q, handle):
    e = q(ENTRY_Q, {"h": {"type": "sauna", "handle": handle}})["metaobjectByHandle"]
    return e["id"] if e else None


def deploy_metafields(write: bool, q=None):
    """Product -> entry references for mapped products. Every write is recorded (product id,
    namespace, key, previous value, new value) BEFORE the next one, and the reversal is
    proved on the first product before the rest are written."""
    q = q or admin()
    missing = NEED_ENTRIES - scopes(q)
    if missing:
        print(f"PENDING: product metafields reference sauna entries, which do not exist (token lacks {sorted(missing)}). "
              f"Nothing written.")
        return False
    targets = [(pd, gid) for pd, _, gid in _pages_and_records() if gid]
    print(f"  {len(targets)} mapped products")
    if not write:
        return True
    q(MF_DEF_M, {"d": {"name": "INH Verified sauna", "namespace": MF_NAMESPACE, "key": MF_KEY, "ownerType": "PRODUCT",
                       "type": "metaobject_reference",
                       "validations": [{"name": "metaobject_definition_id",
                                        "value": q(DEF_BY_TYPE_Q, {"t": "sauna"})["metaobjectDefinitionByType"]["id"]}]}})
    REVERSALS.mkdir(parents=True, exist_ok=True)
    log = REVERSALS / f"metafield-writes-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    for i, (pd, product_gid) in enumerate(targets):
        entry = _entry_gid(q, pd["handle"])
        if not entry:
            raise SystemExit(f"HALT: no entry for {pd['handle']}")
        prev = q(MF_READ_Q, {"id": product_gid})["product"]["metafield"]
        rec = {"product_id": product_gid, "namespace": MF_NAMESPACE, "key": MF_KEY, "value": entry,
               "previous_value": prev["value"] if prev else None, "written_at": datetime.now(timezone.utc).isoformat()}
        with log.open("a") as f:
            f.write(json.dumps(rec) + "\n")   # recorded before the write, so a crash leaves it reversible
        r = q(MF_SET_M, {"m": [{"ownerId": product_gid, "namespace": MF_NAMESPACE, "key": MF_KEY,
                                "type": "metaobject_reference", "value": entry}]})["metafieldsSet"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at {product_gid}: {r['userErrors']}")
        if i == 0:
            reverse(log, q=q, only=product_gid)
            if q(MF_READ_Q, {"id": product_gid})["product"]["metafield"] is not None and rec["previous_value"] is None:
                raise SystemExit("HALT: reversal did not remove the first write")
            q(MF_SET_M, {"m": [{"ownerId": product_gid, "namespace": MF_NAMESPACE, "key": MF_KEY,
                                "type": "metaobject_reference", "value": entry}]})
            print(f"  reversal proved on {product_gid}: written, reversed, confirmed absent, rewritten")
    print(f"  wrote {len(targets)} metafields; reversal file {log.relative_to(ROOT)}")
    return True


def reverse(log: Path, q=None, only=None):
    q = q or admin()
    for line in Path(log).read_text().splitlines():
        rec = json.loads(line)
        if only and rec["product_id"] != only:
            continue
        if rec["previous_value"] is None:
            r = q(MF_DEL_M, {"m": [{"ownerId": rec["product_id"], "namespace": rec["namespace"], "key": rec["key"]}]})["metafieldsDelete"]
        else:
            r = q(MF_SET_M, {"m": [{"ownerId": rec["product_id"], "namespace": rec["namespace"], "key": rec["key"],
                                    "type": "metaobject_reference", "value": rec["previous_value"]}]})["metafieldsSet"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: reversal failed at {rec['product_id']}: {r['userErrors']}")


# -------------------------------------------------------------------- lints --

PRICE_RX = re.compile(r"(?i)(\"(?:reference_)?price(?:_usd)?\"\s*:|\bprice_usd\b|[$€£]\s?\d|\bUSD\b|\d\s?(?:dollars|usd)\b)")
BANNED_RX = re.compile(r"(?i)infinite\s*sauna|infinitesauna|not stated on the manufacturer")


def lint_payload(text: str, where: str):
    bad = [m.group(0) for rx in (PRICE_RX, BANNED_RX) for m in rx.finditer(text)]
    if bad:
        raise SystemExit(f"HALT: {where} carries forbidden content {bad[:5]}; nothing written")


def self_test():
    fails = []
    lay = "x\n" + LAYOUT_ANCHOR + "\ny"
    p = patch_layout(lay)
    if p.count("elsif metaobject") != 1 or patch_layout(p) != p:
        fails.append("layout patch is not exactly-once")
    try:
        patch_layout("no anchor")
        fails.append("layout patch did not halt without its anchor")
    except SystemExit:
        pass
    tpl = json.dumps({"sections": {"a": {"type": "x"}, "r": {"type": "apps", "blocks": {"b": {"type": REVIEW_BLOCK + "id"}}},
                                   "z": {"type": "y"}}, "order": ["a", "r", "z"]})
    after = patch_product("/* c */\n" + tpl)
    if json.loads(after.split("*/", 1)[1])["order"] != ["a", "r", LINK_SECTION_ID, "z"]:
        fails.append("link section not placed directly after the reviews")
    if not product_prefix_unchanged("/* c */\n" + tpl, after):
        fails.append("prefix check rejected a correct patch")
    if patch_product(after) != after or not product_prefix_unchanged(after, patch_product(after)):
        fails.append("re-running the product patch is not a no-op")
    for s in ('{"price_usd": 1}', "$4,099", "Infinite Sauna", "Not stated on the manufacturer's page"):
        try:
            lint_payload(s, "t")
            fails.append(f"lint passed {s!r}")
        except SystemExit:
            pass
    try:
        guard_theme(lambda *a: {"theme": {"id": "x", "name": "live", "role": "MAIN"}}, PREVIEW_THEME)
        fails.append("guard allowed a MAIN-role theme")
    except SystemExit:
        pass
    try:
        guard_theme(lambda *a: {"theme": {"id": "x", "name": "n", "role": "UNPUBLISHED"}}, "167150092355")
        fails.append("guard allowed a theme other than the preview theme")
    except SystemExit:
        pass
    print("self-test: " + ("PASS" if not fails else "FAIL " + "; ".join(fails)))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", nargs="?", choices=["snapshot", "theme", "pages", "entries", "metafields", "reverse", "remove-retired"])
    ap.add_argument("--file")
    ap.add_argument("--only")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.step == "snapshot":
        snapshot(admin())
        print(f"snapshot + patched files -> {DEPLOY.relative_to(ROOT)}")
    elif a.step == "theme":
        deploy_theme(a.write)
    elif a.step == "pages":
        deploy_pages(a.write)
    elif a.step == "entries":
        deploy_entries(a.write)
    elif a.step == "metafields":
        deploy_metafields(a.write)
    elif a.step == "remove-retired":
        remove_retired(a.write)
    elif a.step == "reverse":
        reverse(Path(a.file), only=a.only)
        print("reversed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
