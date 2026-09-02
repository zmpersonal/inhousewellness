"""Broken-post counter. The gate on autonomy (adjustment D2).

14 consecutive days at zero broken posts before auto_publish may be considered.
A broken post is any published post that would have failed the validator:
empty/short text, an error or placeholder pattern, a missing Pinterest field, or
a destination that does not resolve.

Any broken post RESETS the streak to zero. The counter is evidence, not a
formality -- the prior baseline was 27%.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "broken-post-counter.json"
REQUIRED_CLEAN_DAYS = 14


def load():
    if not STATE.exists():
        return {"started_on": None, "days": {}, "streak_days": 0, "total_posts": 0,
                "total_broken": 0}
    return json.loads(STATE.read_text())


def save(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    tmp.replace(STATE)


def record(day, published, broken, notes=""):
    """Record one day's outcome. `broken` resets the streak."""
    s = load()
    s["started_on"] = s["started_on"] or day
    s["days"][day] = {"published": published, "broken": broken, "notes": notes}
    s["total_posts"] = sum(d["published"] for d in s["days"].values())
    s["total_broken"] = sum(d["broken"] for d in s["days"].values())

    streak = 0
    for d in sorted(s["days"], reverse=True):
        if s["days"][d]["broken"] == 0:
            streak += 1
        else:
            break
    s["streak_days"] = streak
    s["autonomy_gate"] = {
        "required_clean_days": REQUIRED_CLEAN_DAYS,
        "clean_days_so_far": streak,
        "days_remaining": max(0, REQUIRED_CLEAN_DAYS - streak),
        "eligible": streak >= REQUIRED_CLEAN_DAYS,
    }
    save(s)
    return s


if __name__ == "__main__":
    import sys
    s = record(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]),
               sys.argv[4] if len(sys.argv) > 4 else "")
    g = s["autonomy_gate"]
    print(f"broken-post counter: {s['total_broken']}/{s['total_posts']} broken; "
          f"{g['clean_days_so_far']}/{g['required_clean_days']} clean days, "
          f"{g['days_remaining']} to go")
