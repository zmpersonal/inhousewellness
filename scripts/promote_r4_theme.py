#!/usr/bin/env python3
"""Round 4 Part B: the three MAIN theme files this round changes, written by file (never a theme publish).

    .venv/bin/python scripts/promote_r4_theme.py snapshot
    .venv/bin/python scripts/promote_r4_theme.py deploy --files <f> [<f> ...] [--write --allow-live-theme-id <MAIN>]
    .venv/bin/python scripts/promote_r4_theme.py rollback [--write --allow-live-theme-id <MAIN>]

Files: sections/true-total-cost.liquid (one help-text link), assets/inh-electrical-data.json (A8 rebuild),
templates/llms.txt.liquid (two added sections; on the INH Verified must-travel list, so MAIN and the repo
change together). The repo copy is what is written; MAIN must still equal the snapshot seconds before the
write; every file is read back by MD5; rollback restores the snapshot of every file this round wrote.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
FILES = ["sections/true-total-cost.liquid", "assets/inh-electrical-data.json", "templates/llms.txt.liquid"]
DIR = ROOT / "data/promote/r4"
STATE = DIR / "theme-state.json"


FILES_Q = """query($id: ID!, $f: [String!]) { theme(id: $id) { files(first: 50, filenames: $f) {
  nodes { filename checksumMd5 size body { ... on OnlineStoreThemeFileBodyText { content }
                                           ... on OnlineStoreThemeFileBodyBase64 { contentBase64 }
                                           ... on OnlineStoreThemeFileBodyUrl { url } } } } } }"""


def read_files(q, mid, names):
    """Like verified_deploy.read_files, but a large asset served as base64 is decoded to bytes too."""
    import base64
    nodes = q(FILES_Q, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "f": names})["theme"]["files"]["nodes"]
    out = {}
    for n in nodes:
        b = n["body"]
        if "content" in b:
            n["bytes"] = b["content"].encode()
        elif "contentBase64" in b:
            n["bytes"] = base64.b64decode(b["contentBase64"])
        else:                                   # a large file is served by URL; its MD5 is checked by the caller
            import urllib.request
            n["bytes"] = urllib.request.urlopen(b["url"], timeout=60).read()
        out[n["filename"]] = n
    return out


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main_id():
    import verified_golive as vg
    return vg.resolve_main_logged()[0]


def snapshot(_w=False, files=None, allow=None):
    import verified_deploy as vd
    q = vd.admin()
    mid = main_id()
    cur = read_files(q, mid, FILES)
    d = DIR / f"main-{mid}"
    d.mkdir(parents=True, exist_ok=True)
    man = {"theme_id": mid, "taken_at": now(), "files": {}}
    for n in FILES:
        p = d / n.replace("/", "__")
        p.write_bytes(cur[n]["bytes"])
        man["files"][n] = {"md5": cur[n]["checksumMd5"], "path": str(p.relative_to(ROOT))}
        if md5(p.read_bytes()) != cur[n]["checksumMd5"]:
            raise SystemExit(f"HALT: {n} body does not match its own MD5")
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(f"snapshot of MAIN {mid}: {len(FILES)} files -> {d.relative_to(ROOT)}")


def manifest(mid):
    return json.loads((DIR / f"main-{mid}" / "manifest.json").read_text())


def deploy(write=False, files=None, allow=None):
    import verified_deploy as vd
    import verified_golive as vg
    q = vd.admin()
    mid = main_id()
    man = manifest(mid)
    files = files or []
    if not files or set(files) - set(FILES):
        raise SystemExit(f"HALT: --files must name some of {FILES}")
    cur = read_files(q, mid, files)
    st = json.loads(STATE.read_text()) if STATE.exists() else {"written": {}}
    for n in files:
        expect = st["written"].get(n, {}).get("new") or man["files"][n]["md5"]
        if cur[n]["checksumMd5"] != expect:
            raise SystemExit(f"HALT: MAIN's {n} is {cur[n]['checksumMd5']}, expected {expect}. Nothing written.")
    body = {n: (ROOT / n).read_bytes() for n in files}
    # The INH Verified payload lint (no prices, no banned names) applies to INH Verified files. The cost
    # calculator states dollar figures by design and is gated by the missing-value lint instead.
    verified = [n for n in files if n != "sections/true-total-cost.liquid"]
    if verified:
        vd.lint_payload(b"\n".join(body[n] for n in verified).decode("utf-8", "replace"), "round 4 INH Verified files")
    for n in files:
        print(f"  {'write' if write else 'would write'} {n}  {cur[n]['checksumMd5']} -> {md5(body[n])}")
    if not write:
        return
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id must name MAIN ({mid})")
    vg.live_guard(q, mid, allow)
    r = q(vd.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": [
        {"filename": n, "body": {"type": "TEXT", "value": body[n].decode()}} for n in files]})["themeFilesUpsert"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}. Undo: promote_r4_theme.py rollback --write --allow-live-theme-id {mid}")
    back = read_files(q, mid, files)
    bad = [n for n in files if back[n]["checksumMd5"] != md5(body[n])]
    for n in files:
        st["written"][n] = {"old": man["files"][n]["md5"], "new": back[n]["checksumMd5"], "at": now()}
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")
    print(f"read-back: {len(files) - len(bad)} of {len(files)} byte-identical by MD5 {bad or ''}")
    if bad:
        raise SystemExit(f"HALT: read-back failed. Undo: promote_r4_theme.py rollback --write --allow-live-theme-id {mid}")


def rollback(write=False, files=None, allow=None):
    import verified_deploy as vd
    import verified_golive as vg
    mid = main_id()
    man = manifest(mid)
    st = json.loads(STATE.read_text()) if STATE.exists() else {"written": {}}
    todo = sorted(st["written"])
    print(f"ROLLBACK on MAIN {mid}{'' if write else ' (dry run)'}: {todo or 'nothing written yet'}")
    for n in todo:
        print(f"  {'restore' if write else 'would restore'} {n} -> {man['files'][n]['md5']}")
    if not write or not todo:
        return
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id must name MAIN ({mid})")
    q = vd.admin()
    vg.live_guard(q, mid, allow)
    r = q(vd.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": [
        {"filename": n, "body": {"type": "TEXT", "value": (ROOT / man["files"][n]["path"]).read_text()}} for n in todo]})["themeFilesUpsert"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}")
    back = read_files(q, mid, todo)
    ok = all(back[n]["checksumMd5"] == man["files"][n]["md5"] for n in todo)
    print(f"rollback read-back: {'MAIN equals the snapshot' if ok else 'MISMATCH'}; then `git revert` the repo commit")
    if ok:
        st["written"] = {}
        st["rolled_back_at"] = now()
        STATE.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["snapshot", "deploy", "rollback"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--allow-live-theme-id")
    a = ap.parse_args(argv)
    {"snapshot": snapshot, "deploy": deploy, "rollback": rollback}[a.step](a.write, a.files, a.allow_live_theme_id)


if __name__ == "__main__":
    main()
