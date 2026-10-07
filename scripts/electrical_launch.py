#!/usr/bin/env python3
"""Electrical tool LAUNCH (Round 3). Every step is a dry run unless --write; MAIN is resolved at run time.

    .venv/bin/python scripts/electrical_launch.py plan                     # MAIN files: current md5 -> new md5
    .venv/bin/python scripts/electrical_launch.py snapshot                 # MAIN's current copies, committed
    .venv/bin/python scripts/electrical_launch.py deploy [--write --allow-live-theme-id <MAIN>]
    .venv/bin/python scripts/electrical_launch.py unhide [--write]         # clear seo.hidden on the 6 pages
    .venv/bin/python scripts/electrical_launch.py rollback [--write --allow-live-theme-id <MAIN>]
    .venv/bin/python scripts/electrical_launch.py teardown-theme [--write] # the PREVIEW theme only; pages stay

`rollback` is the single undo for the whole launch: MAIN's files back to the snapshot (files the launch
created are deleted), the 6 pages hidden again, and the 2 redirects deleted BY THE IDS the redirect step
recorded (never found by searching). Guards (CLAUDE.md): MAIN is never written without
--allow-live-theme-id naming it; the write is gated seconds before on MAIN still equalling the snapshot;
sections and assets land before the templates that name them; every file is read back by MD5.
The two INH Verified sections are written from the REPO copy, which carries the electrical link, so MAIN
keeps equalling the repo (governance: INH Verified must travel with the theme).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import electrical_deploy as ed  # noqa: E402

FILES = ed.PASS_1 + ed.PATCHED + ed.PASS_2           # write order: sections/assets, then templates
LAUNCH = ROOT / "data/electrical/launch"
STATE = ROOT / "data/electrical/launch-state.json"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def lstate() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def lsave(**kw):
    st = lstate()
    st.update(kw)
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")


def main_id():
    import verified_golive as vg
    return vg.resolve_main_logged()[0]


def new_bytes() -> dict[str, bytes]:
    """What MAIN will hold. The repo's INH Verified sections must already carry the link (Part B commits
    them patched); until then the patch is applied to the repo copy so `plan` shows the real result."""
    out = {n: (ROOT / n).read_bytes() for n in ed.PASS_1 + ed.PASS_2}
    out[ed.PATCHED[0]] = ed.patch_model((ROOT / ed.PATCHED[0]).read_text()).encode()
    out[ed.PATCHED[1]] = ed.patch_hub((ROOT / ed.PATCHED[1]).read_text()).encode()
    return out


def plan(_write=False):
    q = ed.admin()
    mid = main_id()
    cur = ed.read_files(q, mid, FILES)
    for n, b in new_bytes().items():
        old = cur.get(n, {}).get("checksumMd5") or "(absent: created)"
        print(f"  {n:45} {old:34} -> {ed.md5(b)}")
    for n in ed.PATCHED:   # governance: MAIN's INH Verified files equal the repo's before we touch them
        if cur[n]["checksumMd5"] != ed.md5((ROOT / n).read_bytes()) and 'data-inhe=' not in (ROOT / n).read_text():
            raise SystemExit(f"HALT: MAIN's {n} differs from the repo copy; fix that first")


def snapshot(_write=False):
    q = ed.admin()
    mid = main_id()
    cur = ed.read_files(q, mid, FILES)
    d = LAUNCH / f"main-{mid}"
    (d / "files").mkdir(parents=True, exist_ok=True)
    man = {"theme_id": mid, "taken_at": now(), "files": {}}
    for n in FILES:
        if n not in cur:
            man["files"][n] = {"absent": True}
            continue
        body = cur[n]["body"]["content"]
        p = d / "files" / n.replace("/", "__")
        p.write_text(body)
        man["files"][n] = {"md5": cur[n]["checksumMd5"], "path": str(p.relative_to(ROOT))}
    (d / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(f"snapshot of MAIN {mid}: {sum(1 for m in man['files'].values() if not m.get('absent'))} files saved, "
          f"{sum(1 for m in man['files'].values() if m.get('absent'))} absent (the launch creates them) -> {d.relative_to(ROOT)}")


def manifest(mid):
    p = LAUNCH / f"main-{mid}" / "manifest.json"
    if not p.exists():
        raise SystemExit(f"HALT: no snapshot of MAIN {mid}; run `snapshot` first")
    return json.loads(p.read_text())


def gate(q, mid, man):
    cur = ed.read_files(q, mid, FILES)
    def changed(n, m):
        if m.get("absent"):
            return n in cur                     # a file the launch creates must still be absent
        return cur.get(n, {}).get("checksumMd5") != m["md5"]
    moved = [n for n, m in man["files"].items() if changed(n, m)]
    if moved:
        raise SystemExit(f"HALT: MAIN changed since the snapshot: {moved}. Nothing written.")


def readback_ok(q, mid, files: dict[str, bytes]):
    back = ed.read_files(q, mid, list(files))
    bad = []
    for n, b in files.items():
        got = back.get(n)
        if got and got.get("checksumMd5") == ed.md5(b):
            continue
        if got and n.endswith(".json"):
            import re
            if json.loads(re.sub(r"/\*.*?\*/", "", got["body"]["content"], flags=re.S)) == json.loads(b):
                continue
        bad.append(n)
    return back, bad


def deploy(write: bool, allow=None):
    import verified_golive as vg
    from verified_deploy import lint_payload
    q = ed.admin()
    mid = main_id()
    man = manifest(mid)
    files = new_bytes()
    lint_payload(b"\n".join(files.values()).decode("utf-8", "replace"), "electrical launch files")
    gate(q, mid, man)
    for n, b in files.items():
        print(f"  {'write' if write else 'would write'}  {n}  {man['files'][n].get('md5', '(absent)')} -> {ed.md5(b)}")
    if not write:
        return
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id must name MAIN ({mid})")
    vg.live_guard(q, mid, allow)
    gate(q, mid, man)                                   # again, seconds before the write
    for batch in (ed.PASS_1 + ed.PATCHED, ed.PASS_2):
        r = q(ed.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": [
            {"filename": n, "body": {"type": "TEXT", "value": files[n].decode()}} for n in batch]})["themeFilesUpsert"]
        if r["userErrors"]:
            raise SystemExit(f"HALT after partial write: {r['userErrors']}. Undo: electrical_launch.py rollback --write "
                             f"--allow-live-theme-id {mid}")
    back, bad = readback_ok(q, mid, files)
    print(f"read-back: {len(files) - len(bad)} of {len(files)} identical {bad or ''}")
    lsave(main_id=mid, files_written_at=now(), files={n: {"old": man["files"][n].get("md5"), "new": back[n]["checksumMd5"]}
                                                      for n in files if n in back})
    if bad:
        raise SystemExit(f"HALT: read-back failed. Undo: electrical_launch.py rollback --write --allow-live-theme-id {mid}")


PAGE_Q = """query($id: ID!) { page(id: $id) { id handle isPublished hidden: metafield(namespace: "seo", key: "hidden") { id value } } }"""
MF_DEL = """mutation($m: [MetafieldIdentifierInput!]!) { metafieldsDelete(metafields: $m) { deletedMetafields { key } userErrors { field message } } }"""
MF_SET = """mutation($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { metafields { key value } userErrors { field message } } }"""


def pages():
    return sorted((h, r["id"]) for h, r in ed.state()["pages"].items())


def unhide(write: bool):
    q = ed.admin()
    for h, pid in pages():
        p = q(PAGE_Q, {"id": pid})["page"]
        if not p or p["handle"] != h or not p["isPublished"]:
            raise SystemExit(f"HALT: {pid} is {p}; expected published page {h}")
        print(f"  {'unhide' if write else 'would unhide'} /pages/{h} (seo.hidden now {(p['hidden'] or {}).get('value')})")
        if write and p["hidden"]:
            r = q(MF_DEL, {"m": [{"ownerId": pid, "namespace": "seo", "key": "hidden"}]})["metafieldsDelete"]
            if r["userErrors"]:
                raise SystemExit(f"HALT at {h}: {r['userErrors']}")
            if q(PAGE_Q, {"id": pid})["page"]["hidden"]:
                raise SystemExit(f"HALT: {h} still hidden after the delete")
    if write:
        lsave(unhidden_at=now())


def rehide(q, write):
    for h, pid in pages():
        print(f"  {'re-hide' if write else 'would re-hide'} /pages/{h}")
        if write:
            r = q(MF_SET, {"m": [{"ownerId": pid, "namespace": "seo", "key": "hidden", "type": "number_integer", "value": "1"}]})["metafieldsSet"]
            if r["userErrors"] or (q(PAGE_Q, {"id": pid})["page"]["hidden"] or {}).get("value") != "1":
                raise SystemExit(f"HALT: {h} not re-hidden: {r['userErrors']}")


def rollback(write: bool, allow=None):
    import verified_golive as vg
    q = ed.admin()
    mid = main_id()
    man = manifest(mid)
    kept = {n: m for n, m in man["files"].items() if not m.get("absent")}
    created = [n for n, m in man["files"].items() if m.get("absent")]
    reds = lstate().get("redirects", {})
    print(f"ROLLBACK on MAIN {mid}{'' if write else ' (dry run)'}:")
    for n in kept:
        print(f"  {'restore' if write else 'would restore'} {n} -> md5 {kept[n]['md5']}")
    for n in created:
        print(f"  {'delete' if write else 'would delete'} {n} (created by the launch)")
    for src, rid in sorted(reds.items()):
        print(f"  {'delete' if write else 'would delete'} redirect {src} ({rid})")
    if not reds:
        print("  redirects: none recorded (the redirect step has not run)")
    if not write:
        rehide(q, False)
        return
    if str(allow) != mid:
        raise SystemExit(f"REFUSED: --allow-live-theme-id must name MAIN ({mid})")
    vg.live_guard(q, mid, allow)
    for src, rid in sorted(reds.items()):
        r = q("mutation($id: ID!) { urlRedirectDelete(id: $id) { deletedUrlRedirectId userErrors { field message } } }",
              {"id": rid})["urlRedirectDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at redirect {src}: {r['userErrors']}")
    rehide(q, True)
    r = q(ed.UPSERT_M, {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": [
        {"filename": n, "body": {"type": "TEXT", "value": (ROOT / m["path"]).read_text()}} for n, m in kept.items()]})["themeFilesUpsert"]
    if r["userErrors"]:
        raise SystemExit(f"HALT: {r['userErrors']}")
    # templates name the sections: delete templates first, then the sections and assets
    order = [n for n in created if n.startswith("templates/")] + [n for n in created if not n.startswith("templates/")]
    present = [n for n in order if n in ed.read_files(q, mid, order)]
    for n in present:
        r = q("""mutation($id: ID!, $files: [String!]!) { themeFilesDelete(themeId: $id, files: $files) {
              deletedThemeFiles { filename } userErrors { filename message } } }""",
              {"id": f"gid://shopify/OnlineStoreTheme/{mid}", "files": [n]})["themeFilesDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT deleting {n}: {r['userErrors']}")
    back = ed.read_files(q, mid, FILES)
    ok = all(back.get(n, {}).get("checksumMd5") == m["md5"] for n, m in kept.items()) and not (set(back) & set(created))
    print(f"rollback read-back: MAIN {'equals the snapshot' if ok else 'MISMATCH'}")
    lsave(rolled_back_at=now(), redirects={})


def teardown_theme(write: bool):
    """After a passing launch: delete the PREVIEW theme only. The 6 pages are live now and are kept;
    `electrical_deploy.py teardown` would delete them too and must not be used after launch."""
    q = ed.admin()
    st = ed.state()
    t = st.get("theme")
    if not t:
        print("no preview theme recorded")
        return
    tt, _ = ed.guard(q, t["id"])
    print(f"  {'delete' if write else 'would delete'} preview theme {t['id']} {tt['name']!r} (role {tt['role']}); pages kept")
    if write:
        r = q("mutation($id: ID!) { themeDelete(id: $id) { deletedThemeId userErrors { field message } } }",
              {"id": f"gid://shopify/OnlineStoreTheme/{t['id']}"})["themeDelete"]
        if r["userErrors"]:
            raise SystemExit(f"HALT: {r['userErrors']}")
        st["theme"] = None
        st["theme_torn_down_at"] = now()
        ed.save(st)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["plan", "snapshot", "deploy", "unhide", "rollback", "teardown-theme"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--allow-live-theme-id")
    a = ap.parse_args(argv)
    if a.step in ("deploy", "rollback"):
        return {"deploy": deploy, "rollback": rollback}[a.step](a.write, a.allow_live_theme_id)
    return {"plan": plan, "snapshot": snapshot, "unhide": unhide, "teardown-theme": teardown_theme}[a.step](a.write)


if __name__ == "__main__":
    main()
