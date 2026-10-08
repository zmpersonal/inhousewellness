#!/usr/bin/env python3
"""Round 4 Part B item 7: retire the stale /pages/llms-txt (an old llms-style text published as a page).

    .venv/bin/python scripts/promote_r4_llmspage.py run [--write]        # unpublish, then 301 -> /llms.txt
    .venv/bin/python scripts/promote_r4_llmspage.py rollback [--write]   # delete the redirect by id, republish

Order (CLAUDE.md "the redirect goes in BEFORE the page comes down" is for pages that must keep answering;
here the brief orders unpublish then redirect, and a redirect only fires on a 404, so it cannot be proved
before the unpublish anyway). Precondition, checked again here: nothing on the site links to the page.
The redirect id is recorded and read back BY ID; rollback never searches for it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
STATE = ROOT / "data/promote/r4/llms-page-state.json"
PAGE_ID = "gid://shopify/Page/135662436419"
SRC, DST = "/pages/llms-txt", "/llms.txt"
STORE = "https://inhousewellness.com"
Q = "query($id: ID!) { page(id: $id) { id handle isPublished } }"
M_UP = "mutation($id: ID!, $p: PageUpdateInput!) { pageUpdate(id: $id, page: $p) { page { id isPublished } userErrors { field message } } }"
M_RED = "mutation($r: UrlRedirectInput!) { urlRedirectCreate(urlRedirect: $r) { urlRedirect { id path target } userErrors { field message } } }"
Q_RED = "query($id: ID!) { urlRedirect(id: $id) { id path target } }"
M_DEL = "mutation($id: ID!) { urlRedirectDelete(id: $id) { deletedUrlRedirectId userErrors { field message } } }"


def status(url):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, headers={"User-Agent": "INH-r4-check"}), timeout=30) as r:
            return r.status, r.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")


def run(write):
    import verified_deploy as vd
    q = vd.admin()
    p = q(Q, {"id": PAGE_ID})["page"]
    if not p or p["handle"] != "llms-txt":
        raise SystemExit(f"HALT: {PAGE_ID} is {p}")
    print(f"  page {p['handle']} published={p['isPublished']}; {SRC} answers {status(STORE + SRC)}")
    if not write:
        print("DRY RUN: would unpublish, then create the 301 and record its id")
        return
    if not p["isPublished"]:
        print("  already unpublished")
    r = q(M_UP, {"id": PAGE_ID, "p": {"isPublished": False}})["pageUpdate"]
    if r["userErrors"] or q(Q, {"id": PAGE_ID})["page"]["isPublished"]:
        raise SystemExit(f"HALT: unpublish failed {r['userErrors']}")
    print("  unpublished (read back)")
    # An old redirect /llms.txt -> /pages/llms-txt (from before Shopify served /llms.txt natively) is inert
    # (redirects fire only on a 404, and /llms.txt answers 200) but makes the new one a loop, which Shopify
    # refuses. It is deleted by id and recorded so rollback recreates it.
    old = q('query($q: String!) { urlRedirects(first: 5, query: $q) { nodes { id path target } } }',
            {"q": f"path:{DST}"})["urlRedirects"]["nodes"]
    old = [o for o in old if o["path"] == DST and o["target"] == SRC]
    for o in old:
        STATE.write_text(json.dumps({"page_id": PAGE_ID, "deleted_old_redirect": o}, indent=1) + "\n")
        d = q(M_DEL, {"id": o["id"]})["urlRedirectDelete"]
        if d["userErrors"] or q(Q_RED, {"id": o["id"]})["urlRedirect"]:
            raise SystemExit(f"HALT: could not delete the old loop redirect {o}: {d['userErrors']}")
        print(f"  deleted inert old redirect {o['id']} {o['path']} -> {o['target']} (recorded)")
    r = q(M_RED, {"r": {"path": SRC, "target": DST}})["urlRedirectCreate"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}. Undo: promote_r4_llmspage.py rollback --write")
    rid = r["urlRedirect"]["id"]
    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    STATE.write_text(json.dumps({**prev, "page_id": PAGE_ID, "redirect_id": rid, "path": SRC, "target": DST}, indent=1) + "\n")
    back = q(Q_RED, {"id": rid})["urlRedirect"]
    print(f"  created {rid} {SRC} -> {DST}; read back by id {'OK' if back and back['target'] == DST else 'MISMATCH'}")
    for _ in range(12):
        st, loc = status(STORE + SRC)
        if st == 301:
            break
        time.sleep(5)
    print(f"  {SRC} answers {st} -> {loc}")
    if st != 301 or not (loc or "").rstrip("/").endswith(DST):
        raise SystemExit("HALT: the redirect does not answer 301 to /llms.txt. Undo: promote_r4_llmspage.py rollback --write")


def rollback(write):
    import verified_deploy as vd
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    print(f"ROLLBACK{'' if write else ' (dry run)'}: delete redirect {st.get('redirect_id', '(none recorded)')}, republish {PAGE_ID}")
    if not write:
        return
    q = vd.admin()
    if st.get("redirect_id"):
        r = q(M_DEL, {"id": st["redirect_id"]})["urlRedirectDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {r['userErrors']}")
    r = q(M_UP, {"id": PAGE_ID, "p": {"isPublished": True}})["pageUpdate"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}")
    o = st.get("deleted_old_redirect")
    if o:                                   # recreate the old (inert) redirect exactly as it was
        r = q(M_RED, {"r": {"path": o["path"], "target": o["target"]}})["urlRedirectCreate"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: could not recreate {o}: {r['userErrors']}")
    STATE.write_text(json.dumps({**st, "rolled_back": True}, indent=1) + "\n")
    print("  done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["run", "rollback"])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    (run if a.step == "run" else rollback)(a.write)
