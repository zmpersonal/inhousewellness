#!/usr/bin/env python3
"""Weekly metrics pull -> the ⚪ FYI digest. Code only, no model call.

Pinterest reach and saves come from Buffer: Blotato does not collect Pinterest
analytics, so Buffer is the only source. Instagram and Facebook come from
Blotato. The two feeds are independent -- one failing must not take the other
down.

The MCP calls are made by the agent/CI and handed in as JSON files, so this stays
a pure function of its inputs and is testable offline.

Usage:
  python3 scripts/weekly_metrics.py --buffer buf.json --blotato top.json
"""
import argparse, datetime as dt, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import feedback as FB
from src import health as H

PUBLISHED = ROOT / "state" / "published-log.json"


def load(path, default, label):
    if not path:
        return default, f"{label}: not supplied"
    p = pathlib.Path(path)
    if not p.exists():
        return default, f"{label}: file missing — feed contributes nothing"
    try:
        return json.loads(p.read_text()), f"{label}: ok"
    except json.JSONDecodeError as e:
        # A broken feed is a STATUS, never a publishable value.
        return default, f"{label}: invalid JSON ({e}) — feed skipped"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer")
    ap.add_argument("--blotato")
    ap.add_argument("--broken-rate", type=float, default=0.0)
    a = ap.parse_args()

    buf, buf_status = load(a.buffer, None, "buffer/pinterest")
    blo, blo_status = load(a.blotato, {"items": []}, "blotato/ig+fb")
    published = json.loads(PUBLISHED.read_text()) if PUBLISHED.exists() else []

    c = FB.collect(buf, (blo or {}).get("items", []), published)
    s = FB.score(c)
    counter = H.load()

    print("⚪ FYI — weekly digest")
    print(f"   {buf_status}")
    print(f"   {blo_status}")
    print()
    print(f"   published to date : {len(published)} post(s)")
    print(f"   broken-post rate  : {counter.get('total_broken', 0)}/"
          f"{counter.get('total_posts', 0)}  "
          f"streak {counter.get('streak_days', 0)}/{H.REQUIRED_CLEAN_DAYS} clean days")

    pa = c.get("pinterest_aggregate")
    if pa:
        if pa.get("posts"):
            print(f"   pinterest (channel aggregate, {pa['granularity']}): "
                  f"{pa['posts']} posts, {pa['reach']} impressions, {pa['saves']} saves")
        else:
            # Distinguish "no data yet" from "no posts". Buffer backfills
            # natively-published pins on a daily refresh, and our pins go out
            # through Blotato -- so a zero here shortly after publishing means
            # NOT YET, not NONE.
            pin_rows = [r for r in published if r.get("platform") == "pinterest"]
            print(f"   pinterest: Buffer reports 0 posts in the window while our log "
                  f"has {len(pin_rows)}.")
            print(f"              Buffer backfills natively-published pins on a daily "
                  f"refresh and ours publish via Blotato, so this reads as "
                  f"NOT-YET-BACKFILLED, not as zero reach.")
            print(f"              It becomes a real signal only if it persists past "
                  f"~48h from the first publish.")
    else:
        print("   pinterest: no Buffer data supplied this run")

    print(f"   joined rows       : {len(c['joined'])} "
          f"({len(c['unmatched_our_posts'])} of ours unmatched)")
    print(f"   overall mean reach: {s['overall_mean_reach']} over {s['n_posts']} posts")

    for seg, buckets in s["segments"].items():
        if not buckets:
            continue
        print(f"   {seg}:")
        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1]["mean_reach"]):
            flag = "" if v["enough_data"] else f"  (n<{FB.MIN_SEGMENT_POSTS}, not actionable)"
            print(f"     {k:26s} n={v['n']:4d} mean={v['mean_reach']:8.1f}{flag}")

    try:
        props, applied, notes = FB.propose(s, a.broken_rate, dry_run=True)
    except FB.LoopHalted as e:
        print(f"\n🔴 BLOCKED: {e}")
        return 2
    print(f"\n   loop: {len(props)} proposal(s), {len(applied)} applied (dry_run)")
    for n in notes:
        print(f"     ~ {n}")

    out = ROOT / "state" / f"metrics-{dt.date.today().isoformat()}.json"
    out.write_text(json.dumps({"collected": c, "scored": s,
                               "counter": counter,
                               "feeds": [buf_status, blo_status]},
                              indent=1, default=str))
    print(f"\n   wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
