#!/usr/bin/env python3
"""Weekly metrics collection. Code only -- no model call.

Pinterest reach/saves come from Buffer (the only source: Blotato does not
collect Pinterest analytics). Instagram and Facebook come from Blotato.
Both feeds are fetched independently: one failing must not take down the other.

This script writes state/metrics-<date>.json. The MCP calls are made by the
agent/CI and passed in as JSON files, so this stays a pure function of its input
and is testable offline.

Usage:
  python3 scripts/collect_metrics.py --buffer buffer.json --blotato top.json \
      --published state/published-log.json
"""
import argparse, datetime as dt, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src import feedback as FB


def load(path, default):
    if not path:
        return default
    p = pathlib.Path(path)
    if not p.exists():
        print(f"  ! {path} missing — that feed contributes nothing this run", file=sys.stderr)
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        # A broken feed is a STATUS, never a publishable value.
        print(f"  ! {path} is not valid JSON ({e}) — feed skipped", file=sys.stderr)
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer")
    ap.add_argument("--blotato")
    ap.add_argument("--published", default="state/published-log.json")
    ap.add_argument("--broken-rate", type=float, default=0.0)
    ap.add_argument("--apply", action="store_true",
                    help="disable dry_run (NOT permitted in Round 2)")
    a = ap.parse_args()

    buffer_metrics = load(a.buffer, None)
    blotato_top = (load(a.blotato, {}) or {}).get("items", [])
    published = load(a.published, [])

    c = FB.collect(buffer_metrics, blotato_top, published)
    s = FB.score(c)

    print(f"collected {len(c['joined'])} joined rows "
          f"({len(c['unmatched_our_posts'])} of ours unmatched, "
          f"{len(c['unmatched_platform_posts'])} platform rows unmatched)")
    if c["pinterest_aggregate"]:
        pa = c["pinterest_aggregate"]
        print(f"pinterest (channel aggregate): {pa['posts']} posts, "
              f"{pa['reach']} impressions, {pa['saves']} saves")
    print(f"overall mean reach: {s['overall_mean_reach']} over {s['n_posts']} posts\n")

    for seg, buckets in s["segments"].items():
        if not buckets:
            continue
        print(f"  {seg}:")
        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1]["mean_reach"]):
            flag = "" if v["enough_data"] else f"  (n<{FB.MIN_SEGMENT_POSTS}, not actionable)"
            print(f"    {k:28s} n={v['n']:4d} mean={v['mean_reach']:8.1f} "
                  f"win={v['win_rate']:.2f}{flag}")

    try:
        props, applied, notes = FB.propose(s, a.broken_rate, dry_run=not a.apply)
    except FB.LoopHalted as e:
        print(f"\nBLOCKED: {e}")
        return 2

    print(f"\nproposals: {len(props)} | applied: {len(applied)}")
    for p in props:
        print(f"   [{'allow' if p.allowed else 'REVIEW'}] {p.knob}: {p.change}")
    for n in notes:
        print(f"   ~ {n}")

    out = pathlib.Path(f"state/metrics-{dt.date.today().isoformat()}.json")
    out.parent.mkdir(exist_ok=True)
    json.dump({"collected": c, "scored": s,
               "proposals": [vars(p) for p in props], "applied": len(applied)},
              open(out, "w"), indent=1, default=str)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
