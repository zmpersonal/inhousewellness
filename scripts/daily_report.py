#!/usr/bin/env python3
"""Round 12 item 4 — the daily line the machine writes about itself.

Appends one row per run to state/daily-report.jsonl and a human line to
REPORTS.md. Every field is read from state on disk; nothing is passed in by
the caller and nothing is inferred, so a run that publishes nothing reports
zero rather than reporting nothing.

  python3 scripts/daily_report.py --track A [--halt "reason"] [--cost 0.024]

Called by the workflow on ALWAYS, so a halted run still files its line. A run
that dies before reaching this script leaves no row -- and a missing row for a
scheduled day is itself the signal, which is why the row is keyed by date.
"""
import argparse, datetime as dt, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STATE = ROOT / "state"
JSONL = STATE / "daily-report.jsonl"
MD = ROOT / "REPORTS.md"


def _load(name, default):
    p = STATE / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        # A corrupt state file is a HALT condition everywhere else in this
        # system; the reporter must not be the one place that papers over it.
        raise SystemExit(f"HALT: {p} is not valid JSON. Fix by hand.")


def queue_coverage():
    """Share of the live queue that can actually produce a figure.

    Reported because NO_FIGURE blocks a card without one: if coverage falls,
    the queue silently stops being publishable long before it runs dry.
    """
    from src import figures as G
    from src.limits import card_archetype
    q = _load("../data/pinterest-keyword-queue.json", None)
    if q is None:
        qp = ROOT / "data" / "pinterest-keyword-queue.json"
        q = json.loads(qp.read_text()) if qp.exists() else {"items": []}
    live = [r for r in q.get("items", []) if r.get("status") == "queued"]
    if not live:
        return 0, 0, 0.0
    with_fig = 0
    for r in live:
        try:
            payload, _ = G.figures_for({**r, "card_archetype": card_archetype(r.get("archetype"))})
            if payload:
                with_fig += 1
        except Exception:
            pass                      # a row that raises is a row without a figure
    return with_fig, len(live), with_fig / len(live)


def build(track, halt, cost):
    # UTC, deliberately. Every published_at this filters on is UTC, and CI runs
    # in UTC; keying the row by LOCAL date put posts published between UTC
    # midnight and local midnight on the wrong day, which would have quietly
    # misattributed days in the 14-day counter.
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    counter = _load("broken-post-counter.json", {})
    log = _load("published-log.json", [])
    if isinstance(log, dict):
        log = log.get("posts", [])
    today_rows = [r for r in log if str(r.get("published_at", "")).startswith(today)]
    day = counter.get("days", {}).get(today, {})
    n_fig, n_live, cov = queue_coverage()
    return {
        "date": today,
        "track": track,
        "published_today": len(today_rows),
        "published_total": counter.get("total_posts", 0),
        "broken_today": day.get("broken", 0),
        "broken_total": counter.get("total_broken", 0),
        "counter_day": f"{counter.get('streak_days', 0)}/"
                       f"{counter.get('autonomy_gate', {}).get('required_clean_days', 14)}",
        "cost_usd": round(cost, 4),
        "queue_coverage": f"{n_fig}/{n_live} ({cov:.0%})",
        "queue_coverage_pct": round(cov, 4),
        "halt": halt or None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="A")
    ap.add_argument("--halt", default="")
    ap.add_argument("--cost", type=float, default=0.0)
    a = ap.parse_args()

    row = build(a.track, a.halt.strip(), a.cost)
    STATE.mkdir(exist_ok=True)
    with JSONL.open("a") as fh:
        fh.write(json.dumps(row) + "\n")

    line = (f"- **{row['date']}** track {row['track']} — "
            f"published {row['published_today']} "
            f"(total {row['published_total']}), broken {row['broken_today']} "
            f"(total {row['broken_total']}), counter day {row['counter_day']}, "
            f"cost ${row['cost_usd']:.4f}, queue coverage {row['queue_coverage']}")
    if row["halt"]:
        line += f"\n  - 🔴 **HALT** — {row['halt']}"
    if not MD.exists():
        MD.write_text("# Daily reports\n\nOne line per run, appended by "
                      "`scripts/daily_report.py`. Never edited retroactively.\n\n")
    with MD.open("a") as fh:
        fh.write(line + "\n")

    print(line)
    # Coverage below half the queue is a stop-and-ask, not a warning to bury.
    if row["queue_coverage_pct"] < 0.50:
        print(f"\n🔴 BLOCKED: queue coverage {row['queue_coverage']} is below 50%. "
              f"The queue is running out of rows that can carry a figure.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
