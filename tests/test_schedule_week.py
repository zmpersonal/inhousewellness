"""Round 14 — weekly batch scheduling.

The architecture moved from a daily cron to one human-triggered session a week
that hands Blotato seven days of posts with future timestamps. These tests pin
the parts that decide whether a week is correct before anything is scheduled.
"""
import datetime as dt
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import schedule_week as SW
from src import workorders as WO

MON = dt.date(2026, 9, 14)          # a Monday


def test_a_week_is_fourteen_pins_and_one_finding():
    slots = SW.week_slots(MON)
    assert sum(1 for p, _ in slots if p == "pinterest") == 14
    assert sum(1 for p, _ in slots if p == "facebook") == 1


def test_the_two_daily_pins_are_not_back_to_back():
    """The legacy account hit 13 posts in one day during its worst period."""
    slots = SW.week_slots(MON)
    by_day = {}
    for p, when in slots:
        if p == "pinterest":
            by_day.setdefault(when.date(), []).append(when)
    for day, times in by_day.items():
        assert len(times) == 2
        gap = abs((times[1] - times[0]).total_seconds()) / 3600
        assert gap >= 6, f"{day}: pins only {gap}h apart"


def test_the_finding_lands_on_tuesday():
    fb = [w for p, w in SW.week_slots(MON) if p == "facebook"]
    assert len(fb) == 1 and fb[0].weekday() == 1


def test_every_slot_is_utc():
    assert all(w.tzinfo == dt.timezone.utc for _, w in SW.week_slots(MON))


def test_local_label_names_both_us_timezones():
    label = SW.local_label(SW._utc(MON, "15:00"))
    assert "Z" in label and "ET" in label and "PT" in label


def test_week_wide_dedup_prevents_near_duplicate_keywords():
    """The selector suppresses near-duplicates within ONE call, which is right
    for a day and wrong for a batch: the first real week drew both
    "dry sauna vs wet sauna" AND "wet sauna vs dry sauna"."""
    rows = json.loads((ROOT / "data" / "pinterest-keyword-queue.json").read_text())["items"]
    state = {"seen": {}, "published": []}
    sigs, picked = set(), []
    for i in range(7):
        day = (MON + dt.timedelta(days=i)).isoformat()
        pool = [r for r in rows if WO.keyword_signature(r.get("keyword")) not in sigs]
        chosen = WO.select(pool, state, {"pinterest": 2}, day)
        for r in chosen["pinterest"]:
            sigs.add(WO.keyword_signature(r.get("keyword")))
            picked.append(r["id"])
            state["seen"][WO.dedup_key("pinterest", r["id"])] = day
    assert len(picked) == 14
    assert len(set(picked)) == 14, "a row was scheduled twice in one week"
    assert len(sigs) == 14, "two near-duplicate keywords in the same week"


# ---------------------------------------------------------------- reconcile
def _state_with(tmp_path, items):
    s = {"weeks": {"2026-09-12": {"items": items}}}
    (tmp_path / "scheduled-weeks.json").write_text(json.dumps(s))
    return tmp_path / "scheduled-weeks.json"


def _run_reconcile(monkeypatch, tmp_path, items, rows):
    monkeypatch.setattr(SW, "STATE", _state_with(tmp_path, items))
    posts = tmp_path / "posts.json"
    posts.write_text(json.dumps(rows))
    args = type("A", (), {"posts": str(posts), "start": None})()
    return SW.cmd_reconcile(args)


def test_reconcile_passes_a_clean_week(monkeypatch, tmp_path):
    items = {"o1": {"submission_id": "s1", "platform": "pinterest", "keyword": "k"}}
    rows = [{"id": "s1", "status": "published", "postUrl": "https://pin/1"}]
    assert _run_reconcile(monkeypatch, tmp_path, items, rows) == 0


def test_reconcile_halts_on_a_failed_post(monkeypatch, tmp_path):
    items = {"o1": {"submission_id": "s1", "platform": "pinterest", "keyword": "k"}}
    rows = [{"id": "s1", "status": "failed", "errorMessage": "board not found"}]
    assert _run_reconcile(monkeypatch, tmp_path, items, rows) == 2


def test_a_missing_post_is_not_counted_as_published(monkeypatch, tmp_path):
    """Absence is not proof of publication. Letting a missing row pass would
    advance the 14-day clean-week counter on posts nobody confirmed."""
    items = {"o1": {"submission_id": "s1", "platform": "pinterest", "keyword": "k"}}
    assert _run_reconcile(monkeypatch, tmp_path, items, []) == 2


def test_calls_refuse_a_pin_missing_any_mandatory_field(tmp_path, monkeypatch):
    """75 blank pins averaged 3.0 impressions against 106.2 for pins with text."""
    plan = {"week_start": "2026-09-12", "items": [{
        "order_id": "o1", "platform": "pinterest", "keyword": "k",
        "scheduled_time": "2026-09-12T15:00:00Z", "local": "",
        "media_local": "x.png", "public_url": "https://m/x.png",
        "post": {"text": "t", "title": "T", "altText": "A", "link": "https://l",
                 "boardId": None}}]}
    d = tmp_path / "2026-09-12"
    d.mkdir()
    (d / "plan.json").write_text(json.dumps(plan))
    monkeypatch.setattr(SW, "WEEK_DIR", tmp_path)
    with pytest.raises(SystemExit, match="missing boardId"):
        SW.cmd_calls(type("A", (), {"start": "2026-09-12"})())


def test_a_record_with_no_submission_id_is_flagged_as_the_d5_case(monkeypatch, tmp_path):
    """str(None) would look up the key "None" and report it as merely
    unaccounted-for. A post whose id was never captured may be live."""
    items = {"o1": {"submission_id": None, "platform": "pinterest", "keyword": "k"}}
    assert _run_reconcile(monkeypatch, tmp_path, items, []) == 2


def test_reconcile_matches_on_submission_id_not_media_url():
    """Blotato re-hosts media on ingest and rewrites the URL. Comparing media
    would fail on every post and report a clean week as entirely broken."""
    import inspect
    src = inspect.getsource(SW.cmd_reconcile)
    assert "public_url" not in src and "mediaUrls" not in src, (
        "reconcile must not compare media URLs — Blotato rewrites them")


def test_record_marks_scheduled_rows_used_and_retires_the_finding(monkeypatch, tmp_path):
    """A scheduled post is a used row. `plan` selects against a working copy, so
    the real state is only written once the posts exist in Blotato — without
    this, next week reselects the same fourteen keywords."""
    plan = {"week_start": "2026-09-12", "usd": 0.1, "items": [
        {"order_id": "o1", "platform": "pinterest", "item_id": "pin-0001",
         "keyword": "k", "scheduled_time": "2026-09-12T15:00:00Z", "local": "",
         "media_local": "x.png", "public_url": "https://m/x.png",
         "post": {"link": "https://l"}},
        {"order_id": "f1", "platform": "facebook", "item_id": "f1",
         "keyword": "c", "scheduled_time": "2026-09-15T16:00:00Z", "local": "",
         "media_local": "y.png", "public_url": "https://m/y.png",
         "finding_id": "trend:made_up", "finding_claim": "claim",
         "post": {"link": "https://l"}}]}
    d = tmp_path / "2026-09-12"
    d.mkdir()
    (d / "plan.json").write_text(json.dumps(plan))
    results = tmp_path / "r.json"
    results.write_text(json.dumps([
        {"order_id": "o1", "postSubmissionId": "s1", "scheduledTime": "2026-09-12T15:00:00.000Z"},
        {"order_id": "f1", "postSubmissionId": "s2", "scheduledTime": "2026-09-15T16:00:00.000Z"}]))

    monkeypatch.setattr(SW, "WEEK_DIR", tmp_path)
    monkeypatch.setattr(SW, "STATE", tmp_path / "weeks.json")
    monkeypatch.setattr(WO, "STATE_PATH", tmp_path / "posting.json")
    from src import probes as P
    monkeypatch.setattr(P, "LEDGER", tmp_path / "ledger.json")

    rc = SW.cmd_record(type("A", (), {"start": "2026-09-12",
                                      "results": str(results)})())
    assert rc == 0
    seen = json.loads((tmp_path / "posting.json").read_text())["seen"]
    # Marked with the PUBLISH date, which is what the evergreen cooldown measures.
    assert seen["pinterest:pin-0001"] == "2026-09-12"
    assert "trend:made_up" in P.published_ids()


def test_record_does_not_half_mark_state_when_something_went_wrong(monkeypatch, tmp_path):
    """A resolved time that disagrees with the request halts. Marking rows used
    on a half-failed batch would silently retire content that never shipped."""
    plan = {"week_start": "2026-09-12", "usd": 0.1, "items": [
        {"order_id": "o1", "platform": "pinterest", "item_id": "pin-0001",
         "keyword": "k", "scheduled_time": "2026-09-12T15:00:00Z", "local": "",
         "media_local": "x.png", "public_url": "https://m/x.png",
         "post": {"link": "https://l"}}]}
    d = tmp_path / "2026-09-12"
    d.mkdir()
    (d / "plan.json").write_text(json.dumps(plan))
    results = tmp_path / "r.json"
    results.write_text(json.dumps([{"order_id": "o1", "postSubmissionId": "s1",
                                    "scheduledTime": "2026-09-12T09:00:00.000Z"}]))
    monkeypatch.setattr(SW, "WEEK_DIR", tmp_path)
    monkeypatch.setattr(SW, "STATE", tmp_path / "weeks.json")
    monkeypatch.setattr(WO, "STATE_PATH", tmp_path / "posting.json")

    assert SW.cmd_record(type("A", (), {"start": "2026-09-12",
                                        "results": str(results)})()) == 2
    assert not (tmp_path / "posting.json").exists(), "state written despite a mismatch"
