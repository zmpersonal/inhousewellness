"""Caption-generator tests. No network: the model is a stub, so every
deterministic guarantee (schema, validation, retry, halt, per-platform copy,
token accounting) is exercised without a live call."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from src.captions import (CaptionError, Usage, build_prompt, generate,
                          parse_response, to_posts)

IMG = ["https://database.blotato.io/storage/v1/object/public/public_media/x.jpg"]
BOARD = "902690387751719051"

ORDERS = [
    {"order_id": "d:pinterest:pin-0019", "platform": "pinterest", "item_id": "pin-0019",
     "keyword": "infrared vs traditional sauna", "archetype": "comparison",
     "evidence_tier": "strong", "source_title": "Best 2 Person Sauna Buyers Guide",
     "link": "https://inhousewellness.com/blogs/saunas/best-2-person-sauna-buyers-guide",
     "link_domain": "inhousewellness.com", "board_id": BOARD, "mediaUrls": list(IMG)},
    {"order_id": "d:instagram:pin-0046", "platform": "instagram", "item_id": "pin-0046",
     "keyword": "sauna vs hot tub", "archetype": "comparison", "evidence_tier": "moderate",
     "source_title": "Hot Tub Cold Plunge Combo",
     "link": "https://inhousewellness.com/blogs/cold-plunge/hot-tub-cold-plunge-combo",
     "link_domain": "inhousewellness.com", "board_id": None, "mediaUrls": list(IMG)},
    {"order_id": "d:facebook:pin-0049", "platform": "facebook", "item_id": "pin-0049",
     "keyword": "red light therapy vs infrared sauna", "archetype": "comparison",
     "evidence_tier": "moderate", "source_title": "Red Light Therapy Sauna Guide",
     "link": "https://inhousewellness.com/blogs/saunas/red-light-therapy-sauna-guide",
     "link_domain": "inhousewellness.com", "board_id": None, "mediaUrls": list(IMG)},
]
BRIEF = [{"order_id": o["order_id"], "platform": o["platform"], "keyword": o["keyword"],
          "archetype": o["archetype"], "evidence_tier": o["evidence_tier"],
          "source_title": o["source_title"], "destination": o["link_domain"]}
         for o in ORDERS]

GOOD = [
    {"order_id": "d:pinterest:pin-0019",
     "title": "Infrared vs Traditional Sauna: What Actually Differs",
     "text": ("Infrared vs traditional sauna comes down to how the heat reaches you, "
              "not the number on the thermostat. Traditional cabins heat the air to "
              "around 180F; infrared panels warm you directly at 120 to 140F. Sweat "
              "starts at 8 to 12 minutes in one and 3 to 5 in the other."),
     "alt_text": "Cedar sauna bench slats beside an infrared heater panel in a home cabin"},
    {"order_id": "d:instagram:pin-0046",
     "text": ("A hot tub and a sauna solve different problems, and most people buy the "
              "wrong one first. One is social and low effort. The other is a 15 minute "
              "commitment you do alone. Worth knowing which you actually want."),
     "slides": ["Different problems", "Hot tub: social, low effort", "Sauna: 15 minutes, alone"]},
    {"order_id": "d:facebook:pin-0049",
     "text": ("Red light therapy and an infrared sauna are not the same tool. One "
              "targets skin and tissue at specific wavelengths; the other raises your "
              "whole-body temperature. Some evidence suggests each may support "
              "recovery, but they are not interchangeable purchases."),
     "first_comment": "Full comparison: https://inhousewellness.com/blogs/saunas/red-light-therapy-sauna-guide"},
]


def stub(payloads, counter=None):
    """Model stub. Yields each payload in turn; records prompts."""
    seq = list(payloads)
    state = {"i": 0, "prompts": []}

    def call(prompt):
        state["prompts"].append(prompt)
        p = seq[min(state["i"], len(seq) - 1)]
        state["i"] += 1
        body = p if isinstance(p, str) else json.dumps(p)
        return body, len(prompt) // 4, len(body) // 4

    call.state = state
    return call


# ------------------------------------------------------------------ happy path
def test_one_batched_call_for_all_posts():
    call = stub([GOOD])
    posts, usage = generate(ORDERS, BRIEF, call)
    assert len(posts) == 3
    assert usage.calls == 1, "must be ONE batched call, not one per post"


def test_prompt_contains_every_order_and_no_article_bodies():
    p = build_prompt(BRIEF)
    for b in BRIEF:
        assert b["order_id"] in p
    assert len(p) < 6000, "brief must stay small -- it is sent every cycle"


def test_token_usage_reported_per_post():
    call = stub([GOOD])
    _, usage = generate(ORDERS, BRIEF, call)
    r = usage.report(3)
    assert "per published post" in r and usage.input_tokens > 0


def test_structural_fields_come_from_code_not_model():
    call = stub([GOOD])
    posts, _ = generate(ORDERS, BRIEF, call)
    pin = next(p for p in posts if p["platform"] == "pinterest")
    assert pin["boardId"] == BOARD
    assert pin["link"] == ORDERS[0]["link"]
    assert pin["mediaUrls"] == IMG


# ------------------------------------------------------------------ schema
@pytest.mark.parametrize("bad,msg", [
    ("not json at all", "not valid JSON"),
    ('{"order_id":"x"}', "expected a JSON array"),
    ('[{"title":"t"}]', "no order_id"),
])
def test_malformed_response_rejected(bad, msg):
    with pytest.raises(CaptionError) as e:
        parse_response(bad, BRIEF)
    assert msg in str(e.value)


def test_missing_order_rejected():
    with pytest.raises(CaptionError) as e:
        parse_response(json.dumps(GOOD[:2]), BRIEF)
    assert "missing copy" in str(e.value)


def test_missing_pinterest_field_rejected():
    broken = json.loads(json.dumps(GOOD))
    del broken[0]["alt_text"]
    with pytest.raises(CaptionError) as e:
        parse_response(json.dumps(broken), BRIEF)
    assert "alt_text" in str(e.value)


def test_json_inside_markdown_fence_is_tolerated():
    fenced = "```json\n" + json.dumps(GOOD) + "\n```"
    assert len(parse_response(fenced, BRIEF)) == 3


# ------------------------------------------------------------------ retry/halt
def test_retries_once_then_succeeds():
    call = stub(["garbage", GOOD])
    posts, usage = generate(ORDERS, BRIEF, call)
    assert len(posts) == 3 and usage.calls == 2
    assert "REJECTED" in call.state["prompts"][1], "retry must state what to fix"


def test_halts_after_second_failure_and_publishes_nothing():
    call = stub(["garbage", "still garbage"])
    with pytest.raises(CaptionError) as e:
        generate(ORDERS, BRIEF, call)
    assert "BLOCKED" in str(e.value) and "Nothing published" in str(e.value)
    assert call.state["i"] == 2, "must not retry forever"


def test_validator_failure_blocks_publication():
    """A schema-valid response that fails the Round 1 validator must not pass."""
    bad = json.loads(json.dumps(GOOD))
    bad[2]["text"] = ("Infrared saunas are clinically proven to cure high blood "
                      "pressure and eliminate joint pain for good, guaranteed.")
    call = stub([bad, bad])
    with pytest.raises(CaptionError) as e:
        generate(ORDERS, BRIEF, call)
    assert "BLOCKED" in str(e.value)


def test_facebook_url_in_body_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[2]["text"] += " Read it at https://inhousewellness.com/blogs/saunas"
    call = stub([bad, bad])
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


def test_blank_caption_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[0]["text"] = "   "
    call = stub([bad, bad])
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


def test_error_string_caption_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[1]["text"] = "Error: No response text"
    call = stub([bad, bad])
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


# ------------------------------------- per-platform copy always (hard rule)
def test_shared_text_across_platforms_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[1]["text"] = bad[2]["text"] = (
        "A hot tub and a sauna solve different problems, and most people buy the "
        "wrong one first. One is social and low effort, the other is a commitment.")
    call = stub([bad, bad])
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


def test_voice_guide_bans_are_stated_in_the_prompt():
    p = build_prompt(BRIEF)
    for banned in ("insane", "game-changer", "secret weapon", "detox"):
        assert banned in p
    assert "first_comment" in p and "hedge" in p.lower()


# ------------------------------------- near-duplicate selection (Round 3)
def test_reordered_keywords_share_a_signature():
    from src.workorders import keyword_signature as sig
    assert sig("infrared vs steam sauna") == sig("infrared sauna vs steam")
    assert sig("infrared vs steam sauna") == sig("steam vs infrared sauna")
    assert sig("hot tub vs sauna") == sig("hot tubs vs saunas")
    assert sig("infrared vs steam sauna") != sig("infrared vs traditional sauna")


def test_cycle_never_selects_two_rows_for_the_same_query():
    """Two near-identical pins on one board reads as spam on a search surface."""
    from src.workorders import keyword_signature, select
    rows = [
        {"id": "a", "keyword": "infrared vs steam sauna", "status": "queued",
         "priority": 900, "reuse_class": "evergreen"},
        {"id": "b", "keyword": "infrared sauna vs steam", "status": "queued",
         "priority": 890, "reuse_class": "evergreen"},
        {"id": "c", "keyword": "steam vs infrared sauna", "status": "queued",
         "priority": 880, "reuse_class": "evergreen"},
        {"id": "d", "keyword": "sauna vs hot tub", "status": "queued",
         "priority": 870, "reuse_class": "evergreen"},
    ]
    chosen = select(rows, {"seen": {}}, cadence={"pinterest": 2}, today="2026-09-02")
    picked = chosen["pinterest"]
    assert len(picked) == 2
    sigs = {keyword_signature(r["keyword"]) for r in picked}
    assert len(sigs) == 2, "picked two rows for the same query"
    assert {r["id"] for r in picked} == {"a", "d"}
