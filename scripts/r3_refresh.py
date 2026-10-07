#!/usr/bin/env python3
"""r3 cleanup B (approved 2026-10-07): refresh the entries that were live before this round so the full
entry check reports 0 differences, changing NOTHING a reader sees beyond the approved list.

    .venv/bin/python scripts/r3_refresh.py diff               # read-only gate; exit 1 if it would stop
    .venv/bin/python scripts/r3_refresh.py refresh --write    # gate -> snapshot every entry -> write -> read back
    .venv/bin/python scripts/r3_refresh.py revert [--write]   # restore every field from the snapshot

Allowed differences (anything else on any entry halts before a single write):
- source metadata: fetch and verified dates, hashes, source URLs, the date inside the cite line;
- `gdi-8010-03` (golden-designs-reserve-edition-1-person): the dead manual -> the D8 replacement, and
  the snippet quoted from it;
- `dyn-6315-05` (dynamic-toscana-3-person): identity.configuration empty -> DYN-6315-05.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
BASE = "7ded6fd"                         # the commit the round started from: its handles were the live set
SNAP_DIR = ROOT / "data/verified/r3/refresh-snapshots"
META = re.compile(r"(fetched|verified|observed_at|fetched_at|content_sha256|cache_manifest_sha256|evidence\.|"
                  r"source_url|sources\[\d+\]\.url$|origin_urls|verified_date|cite\.text$)")
EXCEPT = {"dynamic-toscana-3-person": re.compile(r"identity\.configuration"),
          "golden-designs-reserve-edition-1-person": re.compile(r"snippets\[\d+\]\.text$")}
FIELD_META = {"verified_date"}           # top-level entry fields that are dates only
ABSENT = "<absent>"                      # a leaf missing on one side is a difference, never equal to null
# Round 3 launch A1 (approved 2026-10-07, option a): "Similar models" is derived navigation. Its change is
# allowed ONLY on the entries listed in the stop report, and only to exactly the titles listed there.
STOP_REPORT = ROOT / "docs/verified/r3-electrical/cleanup-b-refresh-stopped.md"


def approved_similar() -> dict[str, list[tuple[str, str]]]:
    out = {}
    for line in STOP_REPORT.read_text().splitlines():
        m = re.match(r"\| `([^`]+)` \| (.*) \|$", line)
        if m:
            cell = m.group(2).split("<br><small>")[0]
            out[m.group(1)] = [tuple(x.split(" → ", 1)) for x in cell.split("<br>")]
    return out


def leaves(x, p=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, p + "." + k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, p + f"[{i}]")
    else:
        yield p, x


def allowed(handle: str, path: str, a, b) -> bool:
    if path.endswith("cite.text"):
        d = re.compile(r"\d{4}-\d\d-\d\d")
        return d.sub("D", str(a)) == d.sub("D", str(b))
    if path.startswith("page_data.similar.items[") and handle in SIMILAR:
        return True                      # checked as a whole block against the stop report in plan()
    return bool(META.search(path)) or bool(EXCEPT.get(handle) and EXCEPT[handle].search(path))


SIMILAR = approved_similar()


def live_set() -> set[str]:
    out = subprocess.run(["git", "show", f"{BASE}:data/verified/handles.json"], capture_output=True, text=True, cwd=ROOT).stdout
    return {v["handle"] for v in json.loads(out)["handles"].values()}


def plan(q):
    import verified_deploy as vd
    import verified_golive as vg
    ents = {e["handle"]: e for e in vg.all_entries(q)}
    live = live_set()
    writes, stops = [], []
    for pd, rec, gid in vd._pages_and_records():
        h = pd["handle"]
        if h not in live:
            continue
        cur = {x["key"]: x["value"] for x in ents[h]["fields"]}
        new = {x["key"]: x["value"] for x in vd.entry_fields(pd, rec, gid)}
        bad = []
        for k in sorted(set(cur) | set(new)):
            a, b = cur.get(k), new.get(k)
            if a == b:
                continue
            if k in ("record", "page_data"):
                la, lb = dict(leaves(json.loads(a or "null"))), dict(leaves(json.loads(b or "null")))
                for p in sorted(set(la) | set(lb)):
                    va = la[p] if p in la else ABSENT
                    vb = lb[p] if p in lb else ABSENT
                    if va != vb and not allowed(h, f"{k}{p}", va, vb):
                        bad.append((f"{k}{p}", va, vb))
            elif k not in FIELD_META:
                bad.append((k, a, b))
        if h in SIMILAR:
            was = [x["title"] for x in json.loads(cur["page_data"])["similar"]["items"]]
            now = [x["title"] for x in pd["similar"]["items"]]
            moved = [(a, b) for a, b in zip(was, now) if a != b]
            if moved != SIMILAR[h] or len(was) != len(now):
                bad.append(("page_data.similar", moved, SIMILAR[h]))   # not the change the owner approved
        if bad:
            stops.append((h, bad))
        elif cur != new:
            writes.append((pd, rec, gid, ents[h]))
    return writes, stops


def diff(_write=False) -> int:
    import verified_deploy as vd
    writes, stops = plan(vd.admin())
    print(f"{len(writes)} entries differ only in allowed ways; {len(stops)} carry a displayed change outside the list")
    for h, bad in stops:
        for p, a, b in bad[:6]:
            print(f"  STOP {h}: {p}: {a!r} -> {b!r}")
    return 1 if stops else 0


def refresh(write: bool) -> int:
    import verified_deploy as vd
    q = vd.admin()
    writes, stops = plan(q)
    if stops:
        diff()
        raise SystemExit(f"HALT: {len(stops)} entries would change a displayed value outside the approved list; nothing written")
    print(f"{'would refresh' if not write else 'refreshing'} {len(writes)} entries (status unchanged)")
    if not write:
        return 0
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAP_DIR / f"entries-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    snap.write_text(json.dumps({e["handle"]: {x["key"]: x["value"] for x in e["fields"]} for *_, e in writes},
                               ensure_ascii=False, indent=0) + "\n")       # written BEFORE the first write
    for pd, rec, gid, e in writes:
        h = {"type": "sauna", "handle": pd["handle"]}
        r = q(vd.UPSERT_ENTRY_M, {"h": h, "m": {"fields": vd.entry_fields(pd, rec, gid)}})["metaobjectUpsert"]
        if r["userErrors"]:
            raise SystemExit(f"HALT at {pd['handle']}: {r['userErrors']}; revert with: r3_refresh.py revert --write")
        back = q(vd.ENTRY_Q, {"h": h})["metaobjectByHandle"]
        if back["capabilities"]["publishable"]["status"] != e["capabilities"]["publishable"]["status"] \
                or json.loads(back["field"]["value"]) != rec:
            raise SystemExit(f"HALT: {pd['handle']} read back wrong; revert with: r3_refresh.py revert --write")
    print(f"refreshed {len(writes)} entries, each read back; snapshot {snap.relative_to(ROOT)}")
    return 0


def revert(write: bool) -> int:
    import verified_deploy as vd
    snaps = sorted(SNAP_DIR.glob("entries-*.json"))
    if not snaps:
        print("revert: no refresh snapshot recorded; nothing to do")
        return 0
    data = json.loads(snaps[-1].read_text())
    print(f"{'restoring' if write else 'would restore'} {len(data)} entries from {snaps[-1].relative_to(ROOT)}")
    if write:
        q = vd.admin()
        for handle, fields in data.items():
            r = q(vd.UPSERT_ENTRY_M, {"h": {"type": "sauna", "handle": handle},
                                      "m": {"fields": [{"key": k, "value": v} for k, v in fields.items()]}})["metaobjectUpsert"]
            if r["userErrors"]:
                raise SystemExit(f"HALT at {handle}: {r['userErrors']}")
            back = q(vd.ENTRY_Q, {"h": {"type": "sauna", "handle": handle}})["metaobjectByHandle"]
            if back["field"]["value"] != fields.get("record"):
                raise SystemExit(f"HALT: {handle} did not restore")
        print("restored and read back")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["diff", "refresh", "revert"])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    return {"diff": diff, "refresh": refresh, "revert": revert}[a.step](a.write)


if __name__ == "__main__":
    sys.exit(main())
