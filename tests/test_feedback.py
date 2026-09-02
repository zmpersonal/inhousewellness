"""Self-improvement loop tests. The guardrails are the point: verify the loop
cannot widen its own permissions, cannot act on noise, and halts on breakage."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from src.feedback import (ALLOWED_KNOBS, FORBIDDEN_KNOBS, LoopHalted,
                          MIN_SEGMENT_POSTS, Proposal, collect, propose, score)


def rows(n, archetype, reach, platform="facebook", domain="inhousewellness.com"):
    return [{"post_id": f"{archetype}-{i}", "platform": platform, "item_id": f"i{i}",
             "archetype": archetype, "board": "The Sauna Shop", "link_domain": domain,
             "external_id": f"e-{archetype}-{i}", "published_at": "2026-08-01"}
            for i in range(n)], reach


def collected(specs):
    joined = []
    for archetype, n, reach in specs:
        for i in range(n):
            joined.append({"post_id": f"{archetype}-{i}", "platform": "facebook",
                           "archetype": archetype, "board": "The Sauna Shop",
                           "link_domain": "inhousewellness.com",
                           "reach": reach, "saves": 1})
    return {"joined": joined, "pinterest_aggregate": None,
            "unmatched_platform_posts": [], "unmatched_our_posts": []}


# ------------------------------------------------------------- guardrails
def test_broken_post_rate_halts_the_loop_regardless_of_reach():
    s = score(collected([("correction", 40, 500), ("evidence_read", 40, 100)]))
    with pytest.raises(LoopHalted) as e:
        propose(s, broken_post_rate=0.01)
    assert "halts" in str(e.value)


def test_no_proposal_below_the_30_post_minimum():
    s = score(collected([("correction", 5, 900), ("evidence_read", 5, 10)]))
    props, applied, notes = propose(s, 0.0)
    assert props == [] and applied == []
    assert any(str(MIN_SEGMENT_POSTS) in n for n in notes)


def test_proposal_made_once_segments_have_enough_data():
    s = score(collected([("correction", 40, 900), ("evidence_read", 40, 100)]))
    props, applied, _ = propose(s, 0.0)
    assert any(p.knob == "archetype_mix" for p in props)


def test_dry_run_applies_nothing():
    s = score(collected([("correction", 40, 900), ("evidence_read", 40, 100)]))
    props, applied, notes = propose(s, 0.0, dry_run=True)
    assert props and applied == []
    assert any("dry_run=True" in n for n in notes)


def test_allow_and_forbid_lists_are_disjoint_and_self_protecting():
    assert not (ALLOWED_KNOBS & FORBIDDEN_KNOBS)
    for meta in ("allowed_knobs", "forbidden_knobs", "guardrails"):
        assert meta in FORBIDDEN_KNOBS, "the loop must not be able to edit its own rules"
        assert meta not in ALLOWED_KNOBS


@pytest.mark.parametrize("knob", sorted(FORBIDDEN_KNOBS))
def test_forbidden_knob_is_never_allowed(knob):
    assert not Proposal(knob, "x", "y", "z").allowed


@pytest.mark.parametrize("knob", sorted(ALLOWED_KNOBS))
def test_allowed_knob_is_allowed(knob):
    assert Proposal(knob, "x", "y", "z").allowed


def test_learnings_entry_states_evidence_metric_and_revert_date():
    e = Proposal("archetype_mix", "shift 5 points", "mean reach 900 vs 100",
                 "monthly impressions").learnings_entry()
    for token in ("archetype_mix", "shift 5 points", "mean reach", "Revert if unmoved by",
                  "monthly impressions"):
        assert token in e


def test_out_of_allowlist_proposal_is_review_not_applied():
    p = Proposal("validator", "loosen the health rules", "reach is low", "impressions")
    assert not p.allowed
    assert "REVIEW" in p.learnings_entry()


# ------------------------------------------------------------- collect/score
def test_collect_reports_unjoinable_rows_rather_than_guessing():
    log = [{"post_id": "p1", "platform": "facebook", "external_id": "ext-1",
            "archetype": "correction", "board": "b", "link_domain": "inhousewellness.com"}]
    top = [{"id": "ext-999", "platform": "facebook",
            "latestMetrics": {"metrics": {"viewsCount": "200"}}}]
    c = collect(None, top, log)
    assert c["joined"] == []
    assert c["unmatched_platform_posts"] == ["ext-999"]
    assert c["unmatched_our_posts"] == ["p1"]


def test_pinterest_is_marked_channel_aggregate_not_per_post():
    log = [{"post_id": "p1", "platform": "pinterest", "external_id": None,
            "archetype": "comparison", "board": "b", "link_domain": "inhousewellness.com"}]
    buf = {"metrics": [{"type": "impressions", "value": 1003},
                       {"type": "saves", "value": 1},
                       {"type": "postCount", "value": 67}]}
    c = collect(buf, [], log)
    agg = c["pinterest_aggregate"]
    assert agg["granularity"] == "channel-aggregate"
    assert agg["reach"] == 1003 and agg["saves"] == 1
    assert "NOT available" in agg["note"]


def test_score_marks_thin_segments_as_not_enough_data():
    s = score(collected([("correction", 3, 100)]))
    assert s["segments"]["archetype"]["correction"]["enough_data"] is False


def test_rotation_proposal_never_names_inh():
    """INH is not in the satellite rotation; its share is fixed by the 70% floor,
    which the loop cannot touch."""
    joined = []
    for dom, reach in (("inhousewellness.com", 900), ("arcticsoak.com", 400),
                       ("saunaimport.com", 100)):
        for i in range(34):
            joined.append({"post_id": f"{dom}-{i}", "platform": "facebook",
                           "archetype": "correction", "board": "b",
                           "link_domain": dom, "reach": reach, "saves": 0})
    s = score({"joined": joined, "pinterest_aggregate": None,
               "unmatched_platform_posts": [], "unmatched_our_posts": []})
    props, _, _ = propose(s, 0.0)
    rot = [p for p in props if p.knob == "satellite_rotation_order"]
    assert rot, "expected a rotation proposal"
    assert all("inhousewellness.com" not in p.change for p in rot)


# ---------------------------------------------------- D5 breadcrumb gate
def test_breadcrumb_absent_is_fine(tmp_path):
    from src.breadcrumb import check
    assert check(tmp_path / "none.json") is None


def test_breadcrumb_present_halts_next_run(tmp_path):
    from src.breadcrumb import DuplicateRisk, check, drop
    b = tmp_path / "crumb.json"
    drop("2026-09-02:pinterest:pin-0001", "pinterest", b)
    with pytest.raises(DuplicateRisk) as e:
        check(b)
    msg = str(e.value)
    assert "HALT" in msg and "pin-0001" in msg and "Never auto-clear" in msg


def test_corrupt_breadcrumb_also_halts(tmp_path):
    from src.breadcrumb import DuplicateRisk, check
    b = tmp_path / "crumb.json"
    b.write_text("{not json")
    with pytest.raises(DuplicateRisk):
        check(b)


def test_simulated_post_then_crash_halts_the_next_run(tmp_path):
    """The exact failure D5 exists for: publish starts, process dies, next run
    must not republish."""
    from src.breadcrumb import DuplicateRisk, check, clear, drop
    b = tmp_path / "crumb.json"
    check(b)                       # clean start
    drop("order-1", "pinterest", b)
    # ... process dies here, before clear() ...
    with pytest.raises(DuplicateRisk):
        check(b)
    clear(b)                       # human clears after investigating
    assert check(b) is None


def test_clear_only_after_capture(tmp_path):
    from src.breadcrumb import check, clear, drop
    b = tmp_path / "crumb.json"
    drop("order-1", "facebook", b)
    clear(b)
    assert check(b) is None
