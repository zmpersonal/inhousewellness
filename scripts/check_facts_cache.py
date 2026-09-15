#!/usr/bin/env python3
"""Gate the FETCHED data -- the one check that can only be made after a refresh.

WHY THIS IS A FILE AND NOT A HEREDOC
It used to be ~40 lines of Python embedded in fetch-external-data.yml, which put
the row floors — data — at a call site, and put the logic somewhere pytest, the
missing-value lint and scripts/preflight.py could all not see. A bug in it would
have been found by a run, not by the suite.

WHY IT IS THE ONLY POST-FETCH GATE
Everything else the workflow checks is static: `pytest tests/` reads no file
under data/facts (verified: nothing in tests/ references it) and
lint_missing_values.py scans *.py sources. Neither can observe a refresh, so
neither has any reason to run after one — and when they ran after one, a
missing pytest threw away 13 cleanly refreshed datasets. They now run before
the fetch. What is left here is exactly what needs the new bytes in hand:

  parses          a JSON file that does not load is not a dataset
  fetched_at      present and parseable, or the age is unknowable
  row_count       equals len(rows) -- the count and the contents must agree, or
                  one of them is lying and every downstream number inherits it
  floor           a refresh far smaller than the cache it replaces is a
                  truncated response, not a finding about the world

  python3 scripts/check_facts_cache.py            # gate: non-zero on a problem
  python3 scripts/check_facts_cache.py --report   # print ages, never fail
  python3 scripts/check_facts_cache.py --self-test
"""
import argparse
import datetime
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "facts"

# Floors, set well below the observed row counts: they exist to catch a
# truncated or rate-limited response, not to freeze the data. A source that
# genuinely shrinks past one of these is a finding a human should read, which is
# why it halts instead of warning.
#
#   observed 2026-09-15 (Actions run 3):  eia 5000  infinite 195  bhis 87
#                                         outdoor_cities 75  outdoor_climate 75
FLOOR = {
    "eia_electricity": 4000,
    "infinite_saunas": 150,
    "bhis_saunas": 70,
    "outdoor_cities": 60,
    "outdoor_climate": 60,
}


def inspect(path):
    """One dataset -> (summary dict, list of problems). Never raises: an
    unreadable file is a finding to report, not a traceback to decode."""
    stem = path.stem
    problems = []
    try:
        doc = json.loads(path.read_text())
    except Exception as e:
        return {"name": stem, "rows": None, "age_days": None}, [
            f"{stem}: will not parse as JSON -- {e}"]

    rows = doc.get("rows")
    count = doc.get("row_count")
    age = None
    at = doc.get("fetched_at")
    if not at:
        problems.append(f"{stem}: no fetched_at, so its age is unknowable")
    else:
        try:
            age = (datetime.datetime.now(datetime.timezone.utc)
                   - datetime.datetime.fromisoformat(at)).days
        except ValueError as e:
            problems.append(f"{stem}: fetched_at {at!r} will not parse -- {e}")

    if not isinstance(rows, list):
        problems.append(f"{stem}: has no rows list")
    elif count != len(rows):
        problems.append(f"{stem}: row_count says {count} but rows holds {len(rows)} "
                        f"-- the count and the contents disagree")
    if isinstance(count, int) and stem in FLOOR and count < FLOOR[stem]:
        problems.append(f"{stem}: {count} rows is below its floor of {FLOOR[stem]} "
                        f"-- treating this as a truncated fetch, not a finding "
                        f"about the world")
    return {"name": stem, "rows": count, "age_days": age}, problems


def scan(facts_dir):
    summaries, problems = [], []
    files = sorted(facts_dir.glob("*.json"))
    if not files:
        return [], [f"{facts_dir} holds no datasets -- absence is not a clean result"]
    for p in files:
        s, pr = inspect(p)
        summaries.append(s)
        problems += pr
    missing = sorted(set(FLOOR) - {s["name"] for s in summaries})
    if missing:
        problems.append(f"datasets with a floor but no file: {', '.join(missing)}")
    return summaries, problems


def render(summaries):
    for s in summaries:
        rows = "unreadable" if s["rows"] is None else f"{s['rows']:>6} rows"
        age = "  ?d old" if s["age_days"] is None else f"{s['age_days']:>3}d old"
        print(f"  {s['name']:20s} {rows}  {age}")


def self_test():
    """Each rule, fired at a dataset that breaks it."""
    fails = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cases = {
        "broken.json": "{not json",
        "eia_electricity.json": json.dumps(
            {"fetched_at": now, "row_count": 10, "rows": list(range(10))}),
        "mismatch.json": json.dumps(
            {"fetched_at": now, "row_count": 5, "rows": [1, 2]}),
        "undated.json": json.dumps({"row_count": 1, "rows": [1]}),
    }
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        for name, body in cases.items():
            (d / name).write_text(body)
        _, problems = scan(d)
        blob = " | ".join(problems)
        for needle, what in (("will not parse as JSON", "an unparseable file"),
                             ("below its floor", "a dataset under its floor"),
                             ("disagree", "row_count disagreeing with rows"),
                             ("unknowable", "a missing fetched_at"),
                             ("infinite_saunas", "a floored dataset with no file")):
            if needle not in blob:
                fails.append(f"did not flag {what}")
    with tempfile.TemporaryDirectory() as td:
        _, problems = scan(pathlib.Path(td))
        if not problems:
            fails.append("treated an empty facts directory as clean")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print ages and row counts, exit 0 regardless -- for the "
                         "before-the-refresh snapshot, where a stale or broken "
                         "cache is the thing being replaced, not a reason to halt")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: this gate's own controls did not fire:\n  " + "\n  ".join(fails))
        print("check_facts_cache self-test: every rule fires against a known-bad dataset")
        return

    summaries, problems = scan(FACTS)
    render(summaries)
    if args.report:
        if problems:
            print(f"\n  ({len(problems)} pre-existing problem(s); --report does not gate)")
        return
    if problems:
        sys.exit("\nHALT: the refreshed cache did not survive its checks:\n  "
                 + "\n  ".join(problems))
    print(f"\n{len(summaries)} dataset(s) checked: parse, dated, counts agree, "
          f"all above floor")


if __name__ == "__main__":
    main()
