"""The post-fetch data gate, and the committed caches it guards.

This gate used to be a heredoc inside fetch-external-data.yml, where no test
could reach it. It is a file now, so these run.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_facts_cache import FACTS, FLOOR, inspect, scan, self_test  # noqa: E402


def test_gate_controls_fire():
    assert self_test() == []


def test_committed_caches_are_intact():
    """The three aborted Actions runs never reached their commit step, so the
    caches in the repo should be exactly what Round 1 left. This asserts it
    rather than assuming it: every file parses, is dated, and its row_count
    agrees with its contents."""
    _, problems = scan(FACTS)
    assert problems == [], "\n".join(problems)


def test_every_floor_names_a_real_dataset():
    """A floor for a dataset that does not exist is a typo that silently guards
    nothing. scan() reports it; this catches it in the suite."""
    present = {p.stem for p in FACTS.glob("*.json")}
    assert set(FLOOR) <= present, f"floors with no dataset: {sorted(set(FLOOR) - present)}"


def test_floors_sit_below_observed_counts():
    """A floor at or above the current count would halt the next clean refresh."""
    for name, floor in FLOOR.items():
        doc = json.loads((FACTS / f"{name}.json").read_text())
        assert doc["row_count"] > floor, (
            f"{name}: floor {floor} is not below the observed {doc['row_count']}")


def test_row_count_mismatch_is_caught(tmp_path):
    """The specific failure this gate exists for: a truncated write where the
    header still claims the full count."""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"fetched_at": "2026-09-15T00:00:00+00:00",
                             "row_count": 500, "rows": [1, 2, 3]}))
    _, problems = inspect(p)
    assert any("disagree" in s for s in problems)


def test_unreadable_file_is_a_finding_not_a_crash(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{truncated")
    summary, problems = inspect(p)
    assert summary["rows"] is None
    assert any("will not parse" in s for s in problems)


# ── two kinds of artifact live under data/facts/ ─────────────────────────────
# The discover run committed manufacturer-discovery.json, a per-vendor REPORT
# with no rows. The first version of this gate assumed every file here was a row
# dataset and failed with "has no rows list", breaking the Sweep step of BOTH
# fetchers on a file that was perfectly correct. These pin the distinction.

def test_the_discovery_report_is_recognised_and_passes():
    p = FACTS / "manufacturer-discovery.json"
    if not p.exists():
        import pytest as _p
        _p.skip("no discovery run yet")
    summary, problems = inspect(p)
    assert summary["kind"] == "report", summary
    assert problems == [], problems


def test_a_report_needs_no_rows_but_does_need_a_date(tmp_path):
    ok = tmp_path / "r.json"
    ok.write_text(json.dumps({"fetched_at": "2026-09-15T00:00:00+00:00",
                              "vendors": [{"vendor": "X"}]}))
    summary, problems = inspect(ok)
    assert summary["kind"] == "report"
    assert problems == []

    undated = tmp_path / "u.json"
    undated.write_text(json.dumps({"vendors": []}))
    _, problems = inspect(undated)
    assert any("unknowable" in s for s in problems)


def test_half_a_dataset_is_corruption_not_a_report(tmp_path):
    """rows without row_count must not be waved through as a report — that would
    turn a truncated write into a clean result."""
    for doc in ({"fetched_at": "2026-09-15T00:00:00+00:00", "rows": [1, 2]},
                {"fetched_at": "2026-09-15T00:00:00+00:00", "row_count": 2}):
        p = tmp_path / "h.json"
        p.write_text(json.dumps(doc))
        summary, problems = inspect(p)
        assert summary["kind"] == "dataset"
        assert any("carries both or neither" in s for s in problems), problems


def test_a_floored_name_that_carries_no_rows_is_flagged(tmp_path):
    """If a report ever acquired a row floor, one of the two is a mistake."""
    p = tmp_path / "eia_electricity.json"
    p.write_text(json.dumps({"fetched_at": "2026-09-15T00:00:00+00:00", "x": 1}))
    _, problems = inspect(p)
    assert any("floor but carries no rows" in s for s in problems), problems

