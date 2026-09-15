"""Drift vs regression in the derived fact layer.

The distinction this file defends: a publisher editing their own index is not a
regression, and a truncated file or a broken parse is not drift. The structural
test in test_validator.py must survive the first and the invariants here must
catch the second -- otherwise the split is just a loosened gate with better
prose.
"""
import json
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import src.facts as F  # noqa: E402
from scripts.check_facts_drift import (  # noqa: E402
    BASELINE, check_invariants, compare, derive, metrics_of, self_test,
)


def test_drift_controls_fire():
    """Every invariant rejects a fact block that breaks it, and the drift/halt
    thresholds behave. Run first, since nothing below is trustworthy otherwise."""
    assert self_test() == []


def test_invariants_pass_on_the_committed_cache():
    facts = derive()
    assert facts, "no cluster derived from the committed cache"
    assert check_invariants(facts, metrics_of(facts)) == []


def test_the_committed_baseline_is_usable_against_the_committed_cache():
    """Deliberately asserts NO DRIFT-FREEDOM, only the absence of a breach.

    The fetcher commits a refreshed cache without touching the baseline -- that
    is the design, so a publisher's edit is acknowledged by a human rather than
    absorbed. Which means a drifted baseline is the NORMAL state between a
    refresh and an --accept, and asserting drift == [] here would fail the suite
    on the run after every refresh: the exact failure this whole change removes,
    rebuilt one layer down. Drift is surfaced by the workflow's drift report.

    What must hold is that the baseline is still usable: it parses, it covers the
    same metrics the code derives, and nothing in it trips a halt.
    """
    assert BASELINE.exists(), "data/facts-baseline.json is missing"
    base = json.loads(BASELINE.read_text())["metrics"]
    assert base, "the baseline holds no metrics"
    _, halts = compare(base, metrics_of(derive()), 0.25)
    assert halts == [], (
        "the committed cache breaches its baseline — this is corruption or a "
        f"schema change, not a publisher edit: {halts}")


# ── the real event: legitimate publisher edits must not fire anything ────────

PRE_REFRESH = {"models_indexed": 90, "models_with_an_emf_label": 90,
               "models_with_a_numeric_emf_claim": 46,
               "models_stating_the_measurement_distance": 34,
               "distinct_label_wordings": 4, "top_labels": [["Near Zero EMF", 71]]}
POST_REFRESH = {"models_indexed": 87, "models_with_an_emf_label": 87,
                "models_with_a_numeric_emf_claim": 43,
                "models_stating_the_measurement_distance": 32,
                "distinct_label_wordings": 4, "top_labels": [["Near Zero EMF", 68]]}


@pytest.mark.parametrize("block,label", [(PRE_REFRESH, "pre-refresh"),
                                         (POST_REFRESH, "post-refresh")])
def test_both_sides_of_the_real_refresh_are_clean(block, label):
    """90/71/46/34 and 87/68/43/32 are both legitimate states of the same source.
    The invariants must be indifferent to which one is current — that
    indifference is the whole point."""
    facts = {"emf": block}
    assert check_invariants(facts, metrics_of(facts)) == [], label


def test_the_real_refresh_reports_as_drift_and_does_not_halt():
    drift, halts = compare(metrics_of({"emf": PRE_REFRESH}),
                           metrics_of({"emf": POST_REFRESH}), 0.25)
    assert halts == [], f"a 3% publisher edit halted: {halts}"
    moved = {p for p, *_ in drift}
    assert "emf.top_labels[0][1]" in moved, (
        "the 71 -> 68 move must appear as a reported finding, not vanish")


# ── regression: corruption the structural test alone would miss ──────────────

@pytest.fixture
def doctored(tmp_path, monkeypatch):
    """A writable copy of the fact cache, with src.facts pointed at it."""
    dest = tmp_path / "facts"
    shutil.copytree(ROOT / "data" / "facts", dest)
    monkeypatch.setattr(F, "CACHE", dest)
    return dest


def _bhis(dest):
    p = dest / "bhis_saunas.json"
    return p, json.loads(p.read_text())


def test_an_emptied_label_column_is_caught(doctored):
    """THE case a shape-only test would miss. Row count intact, every number
    still present and extractable, min<=median<=max fine — but emf_label has
    stopped parsing (renamed column, changed wording). The coverage floor
    catches it without asserting any count."""
    p, d = _bhis(doctored)
    for r in d["rows"]:
        r["emf_label"] = ""
    p.write_text(json.dumps(d))
    facts = derive()
    problems = check_invariants(facts, metrics_of(facts))
    assert any("50% floor" in x for x in problems), problems


def test_a_truncated_cache_is_caught(doctored):
    """Whatever the silent-shrink floor in check_facts_cache.py lets through,
    a large move against the baseline is a breach, not drift."""
    p, d = _bhis(doctored)
    d["rows"] = d["rows"][:5]
    d["row_count"] = 5
    p.write_text(json.dumps(d))
    base = json.loads(BASELINE.read_text())["metrics"]
    _, halts = compare(base, metrics_of(derive()), 0.25)
    assert any("emf.models_indexed" in x for x in halts), halts


def test_a_swapped_dimension_column_is_caught(doctored):
    """A width/depth swap or a unit change leaves the row count untouched and
    every number extractable. An unordered median is what gives it away."""
    p, d = _bhis(doctored)
    for r in d["rows"]:
        if r.get("width") and r.get("depth"):
            r["width"], r["depth"] = "1", r["depth"]
    p.write_text(json.dumps(d))
    facts = derive()
    m = metrics_of(facts)
    assert m.get("fit.width_in.min") is not None
    # the swap itself is not an invariant breach, but it IS a large drift move
    base = json.loads(BASELINE.read_text())["metrics"]
    _, halts = compare(base, m, 0.25)
    assert any("width_in" in x for x in halts), halts


def test_a_cluster_disappearing_halts(doctored):
    """A metric present in the baseline and no longer derived is a schema
    change. Absence is never treated as a value in this project."""
    (doctored / "outdoor_climate.json").unlink()
    base = json.loads(BASELINE.read_text())["metrics"]
    _, halts = compare(base, metrics_of(derive()), 0.25)
    assert any("no longer derived" in x for x in halts), halts


def test_the_structural_grounding_test_survives_a_legitimate_refresh(doctored):
    """The rewritten test_source_data_grounding_round_trips must pass against a
    cache with a different row count. Simulated by dropping three rows, which is
    exactly what the publisher did."""
    p, d = _bhis(doctored)
    d["rows"] = d["rows"][:-3]
    d["row_count"] = len(d["rows"])
    p.write_text(json.dumps(d))
    sd = F.source_data_for({"cluster": "emf", "keyword": "low emf infrared sauna"})
    assert sd and sd["fetched_at"] and sd["url"]
    g = F.grounding_text(sd)
    for field in ("models_indexed", "models_with_an_emf_label"):
        assert field in sd["facts"]
    assert str(sd["facts"]["models_indexed"]) in g
