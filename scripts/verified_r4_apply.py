#!/usr/bin/env python3
"""Round 4 Part B: apply the APPROVED blog links, with a snapshot, exact read-back and a restore.

    .venv/bin/python scripts/verified_r4_apply.py snapshot            # current bodies -> repo
    .venv/bin/python scripts/verified_r4_apply.py apply [--write]     # approved spans only
    .venv/bin/python scripts/verified_r4_apply.py restore --write     # put every edited body back

Rules: an article is edited only if its body is byte-identical to the body the proposals were
computed on. The new body is the old one with each approved span wrapped in ONE internal link (no
rel), or, for an approved new-sentence hub row, one paragraph appended. The read-back must equal
the expected body byte for byte; otherwise that article is restored and the run halts.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_blog_links as bl  # noqa: E402
import verified_deploy as vd  # noqa: E402

SNAP = ROOT / "data/verified/r4/articles-before"
LOG = ROOT / "data/verified/r4/article-edits.json"
READ_Q = "query($id: ID!) { article(id: $id) { id handle body isPublished blog { handle } } }"
UPDATE_M = """mutation($id: ID!, $a: ArticleUpdateInput!) { articleUpdate(id: $id, article: $a) {
  article { id body } userErrors { field message code } } }"""
HUB_SENTENCE_HTML = ('<p>Electrical requirements and exterior sizes for specific models, each cited to the manufacturer, '
                     'are in the <a href="/pages/sauna-database">Verified Sauna Database</a>.</p>')


def approved_changes():
    """{article_id: [change, ...]} for approved rows, from the proposals and the approval list."""
    props = json.loads((ROOT / "docs/verified/r4/blog-link-proposals.json").read_text())
    ids = set(json.loads((ROOT / "out/verified/r4/approved-ids.json").read_text()))
    hubs = sorted(props["hub_links"], key=lambda h: (h["recommend"] != "yes", h["article"]))
    rows = [(f"M{i}", r) for i, r in enumerate(props["model_links"], 1)] + [(f"H{i}", h) for i, h in enumerate(hubs, 1)]
    out = {}
    for rid, r in rows:
        if rid in ids:
            out.setdefault(r["article_id"], []).append(dict(r, id=rid))
    return out


def expected_body(before, changes):
    body = before
    for c in sorted([c for c in changes if c.get("start") is not None], key=lambda c: -c["start"]):
        body = bl.apply_link(body, c["start"], c["end"], c["target"])
    for c in changes:
        if c.get("start") is None:                        # approved new-sentence hub row
            body = body.rstrip("\n") + ("\n" if body.endswith("\n") else "") + HUB_SENTENCE_HTML + ("\n" if body.endswith("\n") else "")
    return body


def snapshot():
    q = vd.admin()
    proposed = {a["id"]: a for a in json.loads((ROOT / "out/verified/r4/articles.json").read_text())}
    SNAP.mkdir(parents=True, exist_ok=True)
    for aid in approved_changes():
        a = q(READ_Q, {"id": aid})["article"]
        if a["body"] != proposed[aid]["body"]:
            raise SystemExit(f"HALT: {a['handle']} changed since the proposals were made; nothing snapshotted")
        (SNAP / f"{aid.rsplit('/', 1)[1]}.json").write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n")
    print(f"snapshot: {len(approved_changes())} article bodies -> {SNAP.relative_to(ROOT)} (each identical to the proposal source)")


def apply(write):
    from src.health_claims import find_banned_claims
    q = vd.admin()
    changes = approved_changes()
    log = []
    for aid, cs in changes.items():
        before = json.loads((SNAP / f"{aid.rsplit('/', 1)[1]}.json").read_text())
        cur = q(READ_Q, {"id": aid})["article"]
        if cur["body"] != before["body"]:
            raise SystemExit(f"HALT: {before['handle']} changed since the snapshot")
        new = expected_body(before["body"], cs)
        added = [c for c in cs if c.get("start") is None]
        if added and find_banned_claims(bl.visible(HUB_SENTENCE_HTML)):
            raise SystemExit("HALT: the new sentence fails the health gate")
        vd.lint_payload(HUB_SENTENCE_HTML if added else "", "hub sentence")
        print(f"  {'edit' if write else 'would edit'} {before['blog']['handle']}/{before['handle']}: "
              f"{', '.join(c['id'] + ' ' + (c['anchor'] or 'new sentence') + ' -> ' + c['target'] for c in cs)}")
        if not write:
            continue
        r = q(UPDATE_M, {"id": aid, "a": {"body": new}})["articleUpdate"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at {before['handle']}: {r['userErrors']}")
        back = q(READ_Q, {"id": aid})["article"]["body"]
        if back != new:
            q(UPDATE_M, {"id": aid, "a": {"body": before["body"]}})
            restored = q(READ_Q, {"id": aid})["article"]["body"] == before["body"]
            raise SystemExit(f"HALT: {before['handle']} read back differs from the expected body "
                             f"(restored: {restored}); nothing further written")
        log.append({"article_id": aid, "handle": before["handle"], "blog": before["blog"]["handle"],
                    "changes": [{k: c.get(k) for k in ("id", "anchor", "target", "start", "end")} for c in cs],
                    "written_at": datetime.now(timezone.utc).isoformat(), "readback": "byte-identical to expected"})
    if write:
        LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n")
        print(f"edited {len(log)} articles; every read-back byte-identical to the expected body; log {LOG.relative_to(ROOT)}")


def restore(write):
    q = vd.admin()
    for f in sorted(SNAP.glob("*.json")):
        a = json.loads(f.read_text())
        print(f"  {'restore' if write else 'would restore'} {a['blog']['handle']}/{a['handle']}")
        if write:
            q(UPDATE_M, {"id": a["id"], "a": {"body": a["body"]}})
            if q(READ_Q, {"id": a["id"]})["article"]["body"] != a["body"]:
                raise SystemExit(f"HALT: {a['handle']} restore did not read back")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["snapshot", "apply", "restore"])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    {"snapshot": lambda: snapshot(), "apply": lambda: apply(a.write), "restore": lambda: restore(a.write)}[a.step]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
