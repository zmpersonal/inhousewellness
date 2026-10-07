#!/usr/bin/env python3
"""r3-electrical publish (approved 2026-10-07): create, link and activate ONLY the approved rows of
docs/verified/r3-electrical/publish-review.csv. Every live entry is left exactly as it is.

    .venv/bin/python scripts/r3_publish.py publish            # dry run: what would be written
    .venv/bin/python scripts/r3_publish.py publish --write    # DRAFT entries -> product links -> ACTIVE
    .venv/bin/python scripts/r3_publish.py revert             # dry run of the one-command revert
    .venv/bin/python scripts/r3_publish.py revert --write     # entries back to DRAFT, product links removed
    ... --batch cleanup-c                                     # a later batch: its own state file and revert

A batch publishes the approved handles that no EARLIER batch's state file records; each batch's revert
touches only its own handles and links.

Rules:
- an approved handle that already exists as an entry halts the run: this round creates, never updates;
- a product that already carries an `inh_verified.sauna` link halts the run before any write to it;
- every write is read back (entry status and record, metafield value); every metafield write is logged
  with its previous value BEFORE it is made (data/verified/internal/metafield-writes/), which is what
  `revert` reads;
- activation reuses verified_golive.activate, which re-reads every entry's status afterwards.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
REVIEW = ROOT / "docs/verified/r3-electrical/publish-review.csv"
STATE = ROOT / "data/verified/r3/publish-state.json"     # batch "r3" (the first publish run)


def state_path(batch: str) -> Path:
    return STATE if batch == "r3" else STATE.with_name(f"publish-state-{batch}.json")


def earlier_batches(batch: str) -> set[str]:
    done = set()
    for f in sorted(STATE.parent.glob("publish-state*.json")):
        if f != state_path(batch):
            done |= set(json.loads(f.read_text())["handles"])
    return done


def approved(batch: str = "r3") -> list[str]:
    ys = {r["proposed_handle"] for r in csv.DictReader(REVIEW.open()) if r["approve (y/n/edit)"].strip() == "y"}
    return sorted(ys - earlier_batches(batch))


def targets(handles):
    import verified_deploy as vd
    want = set(handles)
    out = [(pd, rec, gid) for pd, rec, gid in vd._pages_and_records() if pd["handle"] in want]
    missing = want - {pd["handle"] for pd, _, _ in out}
    if missing:
        raise SystemExit(f"HALT: approved handles with no page data (run verified_pages.py --build): {sorted(missing)}")
    return out


def publish(write: bool, batch: str = "r3"):
    import verified_deploy as vd
    import verified_golive as vg
    handles = approved(batch)
    rows = targets(handles)
    q = vd.admin()
    # Pre-flight, read-only: nothing is written unless every target is clean.
    for pd, rec, gid in rows:
        vd.lint_payload(json.dumps(vd.entry_fields(pd, rec, gid), ensure_ascii=False), pd["handle"])
        cur = q(vd.ENTRY_Q, {"h": {"type": "sauna", "handle": pd["handle"]}})["metaobjectByHandle"]
        if cur:
            raise SystemExit(f"HALT: entry {pd['handle']} already exists ({cur['capabilities']['publishable']['status']}); "
                             f"this round only creates. Nothing written.")
        if gid:
            mf = q(vd.MF_READ_Q, {"id": gid})["product"]["metafield"]
            if mf:
                raise SystemExit(f"HALT: product {gid} already links {mf['value']} ({pd['handle']}). Nothing written.")
    linked = [(pd, gid) for pd, _, gid in rows if gid]
    print(f"{len(rows)} approved handles; none exists yet; {len(linked)} map to a product with no existing link")
    if not write:
        for pd, _, gid in rows:
            print(f"  would create DRAFT {pd['handle']}" + (f" and link {gid}" if gid else " (no product link)"))
        return
    for pd, rec, gid in rows:
        h = {"type": "sauna", "handle": pd["handle"]}
        r = q(vd.UPSERT_ENTRY_M, {"h": h, "m": {"fields": vd.entry_fields(pd, rec, gid),
                                                "capabilities": {"publishable": {"status": "DRAFT"}}}})["metaobjectUpsert"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at {pd['handle']}: {r['userErrors']}")
        back = q(vd.ENTRY_Q, {"h": h})["metaobjectByHandle"]
        if back["capabilities"]["publishable"]["status"] != "DRAFT" or json.loads(back["field"]["value"]) != rec:
            raise SystemExit(f"HALT: {pd['handle']} read back wrong (status or record differs)")
    print(f"  created {len(rows)} DRAFT entries, each read back DRAFT with an identical record")
    vd.REVERSALS.mkdir(parents=True, exist_ok=True)
    log = vd.REVERSALS / f"metafield-writes-r3-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    for pd, gid in linked:
        entry = vd._entry_gid(q, pd["handle"])
        rec = {"product_id": gid, "namespace": vd.MF_NAMESPACE, "key": vd.MF_KEY, "value": entry, "previous_value": None,
               "handle": pd["handle"], "written_at": datetime.now(timezone.utc).isoformat()}
        with log.open("a") as f:
            f.write(json.dumps(rec) + "\n")          # logged before the write
        r = q(vd.MF_SET_M, {"m": [{"ownerId": gid, "namespace": vd.MF_NAMESPACE, "key": vd.MF_KEY,
                                   "type": "metaobject_reference", "value": entry}]})["metafieldsSet"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at {gid}: {r['userErrors']}")
        if (q(vd.MF_READ_Q, {"id": gid})["product"]["metafield"] or {}).get("value") != entry:
            raise SystemExit(f"HALT: link on {gid} read back wrong")
    print(f"  linked {len(linked)} products, each read back; log {log.relative_to(ROOT)}")
    state_path(batch).write_text(json.dumps({"batch": batch, "handles": handles, "metafield_log": str(log.relative_to(ROOT)),
                                 "published_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}, indent=1) + "\n")
    vg.activate(handles, True)


def revert(write: bool, batch: str = "r3"):
    import verified_deploy as vd
    import verified_golive as vg
    st = json.loads(state_path(batch).read_text())
    log = ROOT / st["metafield_log"]
    n = len(log.read_text().splitlines())
    vg.deactivate(st["handles"], write)
    print(f"  {'removed' if write else 'would remove'} {n} product links logged in {log.relative_to(ROOT)}")
    if write:
        vd.reverse(log)


def snapshot_products():
    """Cleanup A (approved 2026-10-07): read-only visitor copies of the product pages this round linked,
    stored beside the pre-launch baselines so the live check can compare later changes. These were taken
    AFTER linking, so they prove nothing about the moment of linking; the manifest says so."""
    import hashlib
    import verified_golive as vg
    st = json.loads(STATE.read_text())
    gids = {json.loads(l)["product_id"] for l in (ROOT / st["metafield_log"]).read_text().splitlines()}
    snap = json.loads((ROOT / "data/verified/internal/inh-products-snapshot.json").read_text())["products"]
    handles = sorted(p["handle"] for p in snap if p["id"] in gids)
    if len(handles) != len(gids):
        raise SystemExit(f"HALT: {len(gids)} linked products, {len(handles)} resolved to handles")
    d = ROOT / "out/verified/golive/baseline"
    d.mkdir(parents=True, exist_ok=True)
    man = {}
    for ph in handles:
        status, page, seen = vg.visitor_get(f"{vg.STORE}/products/{ph}")
        if status != 200 or seen["theme_role"] != "main" or not vg.link_section(page)[1]:
            raise SystemExit(f"HALT: snapshot {ph}: HTTP {status}, theme {seen['theme_role']}, link {vg.link_section(page)[1]}")
        (d / f"products-{ph}.html").write_text(page)
        man[ph] = {"sha256": hashlib.sha256(page.encode()).hexdigest(), "bytes": len(page.encode()),
                   "theme_id": seen["theme_id"], "taken_at": vg.now()}
    out = ROOT / "data/verified/r3/product-snapshots.json"
    out.write_text(json.dumps({"_comment": snapshot_products.__doc__.split(".")[0] + ". Taken after linking; "
                               "files at out/verified/golive/baseline/products-<handle>.html (local).",
                               "products": man}, indent=1) + "\n")
    print(f"snapshotted {len(man)} linked product pages (visitor, live theme, link rendered); manifest {out.relative_to(ROOT)}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["publish", "revert", "snapshot-products"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--batch", default="r3")
    a = ap.parse_args(argv)
    if a.step == "snapshot-products":
        return snapshot_products()
    (publish if a.step == "publish" else revert)(a.write, a.batch)


if __name__ == "__main__":
    main()
