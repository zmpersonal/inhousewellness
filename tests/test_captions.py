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
     "link_domain": "inhousewellness.com", "board_id": BOARD, "mediaUrls": list(IMG),
     "card_archetype": "comparison"},
    {"order_id": "d:instagram:pin-0046", "platform": "instagram", "item_id": "pin-0046",
     "keyword": "sauna vs hot tub", "archetype": "comparison", "evidence_tier": "moderate",
     "source_title": "Hot Tub Cold Plunge Combo",
     "link": "https://inhousewellness.com/blogs/cold-plunge/hot-tub-cold-plunge-combo",
     "link_domain": "inhousewellness.com", "board_id": None, "mediaUrls": list(IMG),
     "card_archetype": "comparison"},
    {"order_id": "d:facebook:pin-0049", "platform": "facebook", "item_id": "pin-0049",
     "keyword": "red light therapy vs infrared sauna", "archetype": "comparison",
     "evidence_tier": "moderate", "source_title": "Red Light Therapy Sauna Guide",
     "link": "https://inhousewellness.com/blogs/saunas/red-light-therapy-sauna-guide",
     "link_domain": "inhousewellness.com", "board_id": None, "mediaUrls": list(IMG),
     "card_archetype": "comparison"},
]
BRIEF = [{"order_id": o["order_id"], "platform": o["platform"], "keyword": o["keyword"],
          "archetype": o["archetype"], "card_archetype": o["card_archetype"],
          "evidence_tier": o["evidence_tier"],
          "source_title": o["source_title"], "destination": o["link_domain"]}
         for o in ORDERS]

GOOD = [
    {"order_id": "d:pinterest:pin-0019",
     "title": "Infrared vs Traditional Sauna: What Actually Differs",
     "text": ("Infrared vs traditional sauna comes down to how the heat reaches you, "
              "not the number on the thermostat. Traditional cabins heat the air to "
              "around 180F; infrared panels warm you directly at 120 to 140F. Sweat "
              "starts at 8 to 12 minutes in one and 3 to 5 in the other."),
     "alt_text": "Cedar sauna bench slats beside an infrared heater panel in a home cabin",
     "card": {"kicker": "Measured, not claimed",
              "headline": "Infrared and traditional are different heat",
              "a": "Infrared", "b": "Traditional",
              "rows": [["Air temperature", "120 to 140F", "170 to 190F"],
                       ["Humidity", "5 to 15%", "100%"],
                       ["Time to sweat", "8 to 12 min", "3 to 5 min"]]}},
    {"order_id": "d:instagram:pin-0046",
     "text": ("A hot tub and a sauna solve different problems, and most people buy the "
              "wrong one first. One is social and low effort. The other is a 15 minute "
              "commitment you do alone. Worth knowing which you actually want."),
     "slides": ["Different problems", "Hot tub: social, low effort", "Sauna: 15 minutes, alone"],
     "card": {"kicker": "Different problems", "headline": "A hot tub and a sauna are not alternatives",
              "a": "Hot tub", "b": "Sauna",
              "rows": [["Water temperature", "100 to 104F", "170 to 190F"],
                       ["Session length", "20 to 30 min", "15 min"],
                       ["Circuit", "240V / 50 amps", "240V / 30 amps"]]}},
    {"order_id": "d:facebook:pin-0049",
     "text": ("Red light therapy and an infrared sauna are not the same tool. One "
              "targets skin and tissue at specific wavelengths; the other raises your "
              "whole-body temperature. Some evidence suggests each may support "
              "recovery, but they are not interchangeable purchases."),
     "first_comment": "Full comparison",
     "card": {"kicker": "Not the same tool", "headline": "Red light and infrared heat do different jobs",
              "a": "Red light", "b": "Infrared sauna",
              "rows": [["Wavelength", "660 to 850 nm", "5 to 15 micron"],
                       ["Session", "10 to 20 min", "30 to 45 min"],
                       ["Draw", "100 W", "1.7 kW"]]}},
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
    # Ceiling raised 6000 -> 7000 in Round 9 for the headline and figure rules.
    # Measured cost of the increase: ~+430 input tokens per cycle, about
    # +$0.002 -- worth it to stop adjective tables reaching a live card. The
    # guard stays because the prompt ships on every cycle, forever.
    assert len(p) < 7000, "brief must stay small -- it is sent every cycle"


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
    assert "no copy returned" in str(e.value)
    # The failure must name the order, so a retry can re-request just that one.
    assert e.value.order_ids == ["d:facebook:pin-0049"]


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
    from src.captions import MAX_RETRIES
    call = stub(["garbage"] * (MAX_RETRIES + 2))
    with pytest.raises(CaptionError) as e:
        generate(ORDERS, BRIEF, call)
    assert "BLOCKED" in str(e.value) and "Nothing published" in str(e.value)
    # Bounded, not unbounded. The bound moved from 1 retry to MAX_RETRIES when
    # batches grew to 15 posts; the guarantee is that it still stops.
    assert call.state["i"] == MAX_RETRIES + 1, "must not retry forever"


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
    from src.captions import MAX_RETRIES
    call = stub([bad] * (MAX_RETRIES + 1))
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


def test_blank_caption_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[0]["text"] = "   "
    from src.captions import MAX_RETRIES
    call = stub([bad] * (MAX_RETRIES + 1))
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


def test_error_string_caption_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[1]["text"] = "Error: No response text"
    from src.captions import MAX_RETRIES
    call = stub([bad] * (MAX_RETRIES + 1))
    with pytest.raises(CaptionError):
        generate(ORDERS, BRIEF, call)


# ------------------------------------- per-platform copy always (hard rule)
def test_shared_text_across_platforms_blocked():
    bad = json.loads(json.dumps(GOOD))
    bad[1]["text"] = bad[2]["text"] = (
        "A hot tub and a sauna solve different problems, and most people buy the "
        "wrong one first. One is social and low effort, the other is a commitment.")
    from src.captions import MAX_RETRIES
    call = stub([bad] * (MAX_RETRIES + 1))
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
        # archetype "reality_check" maps to checklist, which is exempt from the
        # figure requirement -- this test is about near-duplicate keywords only.
        {"id": "a", "keyword": "infrared vs steam sauna", "status": "queued",
         "priority": 900, "reuse_class": "evergreen", "archetype": "reality_check"},
        {"id": "b", "keyword": "infrared sauna vs steam", "status": "queued",
         "priority": 890, "reuse_class": "evergreen", "archetype": "reality_check"},
        {"id": "c", "keyword": "steam vs infrared sauna", "status": "queued",
         "priority": 880, "reuse_class": "evergreen", "archetype": "reality_check"},
        {"id": "d", "keyword": "sauna vs hot tub", "status": "queued",
         "priority": 870, "reuse_class": "evergreen", "archetype": "reality_check"},
    ]
    chosen = select(rows, {"seen": {}}, cadence={"pinterest": 2}, today="2026-09-02")
    picked = chosen["pinterest"]
    assert len(picked) == 2
    sigs = {keyword_signature(r["keyword"]) for r in picked}
    assert len(sigs) == 2, "picked two rows for the same query"
    assert {r["id"] for r in picked} == {"a", "d"}


# ------------------------------- code owns the FB link (Round 3)
def test_code_appends_the_facebook_link_not_the_model():
    good = json.loads(json.dumps(GOOD))
    good[2]["first_comment"] = "Full comparison"
    posts, _ = generate(ORDERS, BRIEF, stub([good]))
    fb = next(p for p in posts if p["platform"] == "facebook")
    assert fb["firstComment"] == f"Full comparison: {ORDERS[2]['link']}"


def test_model_supplied_url_is_stripped_and_replaced():
    """A model that emits its own URL must not be able to publish it."""
    good = json.loads(json.dumps(GOOD))
    good[2]["first_comment"] = "Read it: https://evil.example.com/phish"
    posts, _ = generate(ORDERS, BRIEF, stub([good]))
    fb = next(p for p in posts if p["platform"] == "facebook")
    assert "evil.example.com" not in fb["firstComment"]
    assert fb["firstComment"].endswith(ORDERS[2]["link"])


# ------------------------------- card body in the schema (Round 7)
def test_missing_card_object_is_rejected():
    """A response with copy but no card renders a ~70% empty image."""
    bad = json.loads(json.dumps(GOOD))
    del bad[0]["card"]
    with pytest.raises(CaptionError) as e:
        parse_response(json.dumps(bad), BRIEF)
    assert "card" in str(e.value) and "70%" in str(e.value)


def test_card_missing_archetype_fields_is_rejected():
    bad = json.loads(json.dumps(GOOD))
    del bad[0]["card"]["rows"]
    with pytest.raises(CaptionError) as e:
        parse_response(json.dumps(bad), BRIEF)
    assert "comparison" in str(e.value) and "rows" in str(e.value)


def test_card_reaches_the_post_as_body():
    posts, _ = generate(ORDERS, BRIEF, stub([GOOD]))
    pin = next(p for p in posts if p["platform"] == "pinterest")
    assert pin["_archetype"] == "comparison"
    assert len(pin["_body"]["rows"]) == 3
    assert pin["_body"]["a"] == "Infrared"


def test_prompt_states_the_card_contract_and_bans_allcaps():
    p = build_prompt(BRIEF)
    assert '"card"' in p and "NEVER ALL-CAPS" in p
    for arch in ("comparison", "cost", "spec", "checklist", "evidence", "correction"):
        assert arch in p


def test_queue_archetypes_map_onto_card_archetypes():
    from src.limits import ARCHETYPE_BODY, card_archetype
    for queue_arch in ("reality_check", "evidence_read", "explainer", "spec_table",
                       "comparison", "cost", "correction"):
        assert card_archetype(queue_arch) in ARCHETYPE_BODY, queue_arch


def test_retry_re_requests_only_the_rejected_posts():
    """A retry must not hand the model a fresh chance to break a good post.

    The first live 14-post batch rejected one card on attempt 1 and a DIFFERENT
    card on attempt 2, because every attempt regenerated all fourteen.
    """
    seen_batches = []

    def call(prompt):
        # Which order_ids did this attempt ask for?
        seen_batches.append([o["order_id"] for o in ORDERS
                             if o["order_id"] in prompt])
        if len(seen_batches) == 1:
            first = json.loads(json.dumps(GOOD))
            # Fails VALIDATION, not parsing: an error pattern in otherwise
            # well-formed copy. A parse failure is about the whole response and
            # correctly retries everything, which is not what this test is for.
            first[0]["text"] = first[0]["text"] + " undefined"
            return json.dumps(first), 10, 10
        failed_id = GOOD[0]["order_id"]
        return json.dumps([c for c in GOOD if c["order_id"] == failed_id]), 10, 10

    posts, usage = generate(ORDERS, BRIEF, call)
    assert len(posts) == len(ORDERS), "every order must come back"
    assert len(seen_batches) == 2, "should have retried once"
    assert len(seen_batches[1]) == 1, (
        f"retry asked for {len(seen_batches[1])} posts; only the rejected one "
        f"should be re-requested")


def test_parse_reports_every_bad_order_not_just_the_first():
    """Raising on the first bad order hid the other thirteen, so a retry could
    only ever fix one post per attempt."""
    bad = json.loads(json.dumps(GOOD))
    bad[0].pop("card")          # pinterest: no card body
    bad[1]["slides"] = []       # instagram: required field emptied
    with pytest.raises(CaptionError) as e:
        parse_response(json.dumps(bad), BRIEF)
    assert len(e.value.order_ids) == 2, e.value.order_ids
