"""Validator tests built from the REAL failure cases in the 322-post history.

Every rejection test below corresponds to something that actually published.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from src.validator import (PostRejected, assert_no_shared_text,
                           assert_publishable, validate)

BOARD = "902690387751719051"          # "The Sauna Shop", real board id
IMG = ["https://database.blotato.io/storage/v1/object/public/public_media/x.jpg"]


def good_pin(**over):
    p = {
        "id": "pin-0014", "platform": "pinterest",
        "title": "Sauna Running Costs: What $0.71 Per Session Really Means",
        "text": ("Sauna running cost is the number most listings leave out. We measured a "
                 "2-person infrared sauna on a plug-in meter across 30 sessions. Average "
                 "draw was 1.4 kWh per 45-minute session, about $0.71 at the US average rate."),
        "altText": "Plug-in electricity meter connected to a home infrared sauna showing a kilowatt-hour reading",
        "link": "https://inhousewellness.com/blogs/saunas",
        "boardId": BOARD, "mediaUrls": list(IMG),
    }
    p.update(over)
    return p


def good_ig(**over):
    p = {"id": "ig-01", "platform": "instagram",
         "text": ("Almost every sauna cabin reaches 180F. What differs is how the heat gets "
                  "to you, and that changes how the same number feels on your skin."),
         "mediaUrls": list(IMG)}
    p.update(over)
    return p


def good_fb(**over):
    p = {"id": "fb-01", "platform": "facebook",
         "text": ("The $10,000 sauna can be the worse one. Buyers compare maximum temperature; "
                  "what decides it is heater type, wood thickness, and who honours the warranty "
                  "in year three."),
         "mediaUrls": list(IMG), "firstComment": "Full guide: https://inhousewellness.com/blogs/saunas"}
    p.update(over)
    return p


def codes(post, **kw):
    return validate(post, **kw).codes()


# ---------------------------------------------------------------- happy path
def test_good_pin_passes():
    assert validate(good_pin()).ok, validate(good_pin()).summary()


def test_good_ig_and_fb_pass():
    assert validate(good_ig()).ok
    assert validate(good_fb()).ok


# ------------------------------------------------- REAL failure case 1: blank
@pytest.mark.parametrize("blank", ["", "   ", "\n\t ", None])
def test_blank_pinterest_text_rejected(blank):
    """75 Pinterest pins published with blank text; they averaged 3.0 impressions
    against 106.2 for pins with text."""
    assert "TEXT_EMPTY" in codes(good_pin(text=blank))


def test_blank_pin_raises_not_returns():
    with pytest.raises(PostRejected):
        assert_publishable(good_pin(text=""))


# ------------------------------------------- REAL failure case 2: error strings
@pytest.mark.parametrize("err", [
    "Error: No response text",
    "Failed to load this feed. Please check the URL. Status code 503",
    "undefined",
    "null",
    "No response text was returned by the model at all, please retry later.",
    "[object Object] was rendered into the caption slot for this post today.",
])
def test_error_strings_rejected(err):
    """3 Facebook posts published 'Error: No response text'; 1 published the
    503 feed error verbatim."""
    c = codes(good_fb(text=err))
    assert "TEXT_ERROR_PATTERN" in c or "TEXT_TOO_SHORT" in c, c


def test_error_string_flagged_even_when_long_enough():
    long_err = "Error: No response text. " * 5
    assert "TEXT_ERROR_PATTERN" in codes(good_fb(text=long_err))


# ------------------------------------------ REAL failure case 3: article dumps
def test_25000_char_article_dump_rejected():
    """39 Facebook posts were raw 25,000-51,000 char article dumps averaging
    ~3 impressions."""
    dump = ("A sauna is an enclosed room designed to be heated to high temperature. " * 380)
    assert len(dump) > 25_000
    c = codes(good_fb(text=dump))
    assert "TEXT_OVER_SOFT_LIMIT" in c or "TEXT_OVER_PLATFORM_LIMIT" in c


def test_51000_char_dump_breaks_hard_limit_free_platform():
    dump = "x" * 51_000
    assert "TEXT_OVER_PLATFORM_LIMIT" in codes(good_pin(text=dump))


def test_text_just_under_soft_limit_passes():
    body = "Measured sauna facts. " * 15          # ~330 chars
    assert validate(good_pin(text=body)).ok


# --------------------------------------------------- short text (< 50 chars)
def test_under_50_chars_rejected():
    assert "TEXT_TOO_SHORT" in codes(good_pin(text="Sauna facts."))


# ------------------------------------ REAL failure case 4: Pinterest metadata
@pytest.mark.parametrize("field,code", [
    ("title", "PIN_TITLE_MISSING"),
    ("altText", "PIN_ALT_MISSING"),
    ("link", "PIN_LINK_MISSING"),
    ("boardId", "PIN_BOARD_MISSING"),
])
def test_missing_pinterest_field_rejected(field, code):
    assert code in codes(good_pin(**{field: ""}))
    assert code in codes(good_pin(**{field: None}))


def test_pin_title_emoji_rejected():
    assert "PIN_TITLE_EMOJI" in codes(
        good_pin(title="Sauna Running Costs: What $0.71 Per Session Means 🔥🧖"))


def test_pin_title_over_100_rejected():
    assert "PIN_TITLE_TOO_LONG" in codes(good_pin(title="Sauna running costs " * 8))


def test_pin_alt_out_of_range_rejected():
    assert "PIN_ALT_LENGTH" in codes(good_pin(altText="A sauna."))
    assert "PIN_ALT_LENGTH" in codes(good_pin(altText="A sauna cabin. " * 20))


def test_offsite_link_rejected():
    assert "PIN_LINK_OFFSITE" in codes(good_pin(link="https://amazon.com/dp/B01"))


def test_404_link_rejected_when_checker_supplied():
    """89 of 103 keyword-queue rows currently point at a URL that 404s."""
    dead = {"https://inhousewellness.com/tools/sauna-match"}
    checker = lambda u: u not in dead
    c = codes(good_pin(link="https://inhousewellness.com/tools/sauna-match"),
              link_checker=checker)
    assert "PIN_LINK_UNREACHABLE" in c


# --------------------------------------------------------------- media
def test_empty_media_rejected():
    assert "MEDIA_EMPTY" in codes(good_pin(mediaUrls=[]))
    assert "MEDIA_EMPTY" in codes(good_pin(mediaUrls=None))


def test_relative_or_data_media_url_rejected():
    assert "MEDIA_INVALID_URL" in codes(good_pin(mediaUrls=["out/pin-0014.png"]))


def test_unreachable_media_rejected_when_checker_supplied():
    assert "MEDIA_UNREACHABLE" in codes(good_pin(), media_checker=lambda u: False)


# ------------------------------------------- health claims (adjustment A2)
@pytest.mark.parametrize("text,code", [
    ("Regular sauna use lowers your blood pressure and reverses heart disease for good.",
     "HEALTH_DISEASE_TREATMENT"),
    ("Infrared heat helps your body detox heavy metals through the skin every session.",
     "HEALTH_DETOX_MECHANISM"),
    ("A lifelong detox starts with fifteen minutes a day in the cabin at home.",
     "HEALTH_DETOX_MECHANISM"),
    ("Burn 600 calories per session and lose weight without stepping into a gym.",
     "HEALTH_WEIGHT_LOSS"),
    ("Clinically proven to eliminate joint pain in ninety percent of users, guaranteed.",
     "HEALTH_ABSOLUTE_CLAIM"),
    ("Use the sauna instead of your blood pressure medication and feel the difference.",
     "HEALTH_MEDICAL_ADVICE"),
    ("The insane benefits of daily heat are your secret weapon this winter season.",
     "HEALTH_HYPE_REGISTER"),
])
def test_banned_health_claims_rejected(text, code):
    assert code in codes(good_fb(text=text)), codes(good_fb(text=text))


def test_health_adjacent_without_hedge_rejected():
    t = ("Sauna use improves cardiovascular function and circulation across the "
         "whole body when you use the cabin four times a week.")
    assert "HEALTH_UNHEDGED" in codes(good_fb(text=t))


def test_health_adjacent_with_hedge_passes():
    t = ("Regular sauna use may support cardiovascular health. The evidence is "
         "promising but limited, and most of it comes from Finnish cohort studies "
         "rather than randomised trials.")
    assert validate(good_fb(text=t)).ok, validate(good_fb(text=t)).summary()


def test_cold_plunge_needs_contraindication():
    t = ("A cold plunge at 50F triggers a sharp gasp reflex. The response may ease "
         "with repeated exposure, though evidence is limited on how quickly.")
    assert "HEALTH_NO_CONTRAINDICATION" in codes(good_fb(text=t))


def test_cold_plunge_with_contraindication_passes():
    t = ("A cold plunge at 50F triggers a sharp gasp reflex and a spike in heart rate. "
         "The response may ease with repeated exposure. If you have a heart condition "
         "or high blood pressure, talk to your doctor before cold water immersion.")
    r = validate(good_fb(text=t))
    assert r.ok, r.summary()


def test_set2_cardiovascular_reel_copy_is_gated():
    """The Reels seed Set 2 makes cardiovascular claims and must not pass
    until it is hedged. This is the gate the handoff calls for."""
    t = ("Sauna bathing puts a cardiovascular load on the body similar to moderate "
         "exercise. It lowers blood pressure and cuts cardiac risk substantially.")
    assert not validate(good_fb(text=t)).ok


# ------------------------------------- facebook link placement (hard rule)
def test_facebook_link_in_body_rejected():
    """Facebook: link in first comment, never in the post body."""
    t = ("The $10,000 sauna can be the worse one. Read the full buying breakdown at "
         "https://inhousewellness.com/blogs/saunas before you commit to a cabin.")
    assert "FB_LINK_IN_BODY" in codes(good_fb(text=t))


def test_facebook_link_in_first_comment_passes():
    assert validate(good_fb()).ok


# ---------------------------------- per-platform copy always (hard rule)
def test_shared_text_across_platforms_rejected():
    """207 of 300 historical posts shared caption text across channels."""
    shared = ("Almost every sauna cabin reaches 180F. What differs is how the heat "
              "gets to you, and that changes how the same number feels on your skin.")
    with pytest.raises(PostRejected):
        assert_no_shared_text([good_ig(text=shared), good_fb(text=shared)])


def test_distinct_text_across_platforms_passes():
    assert_no_shared_text([good_ig(), good_fb(), good_pin()])


# ---------------------------------------------------------- platform guard
def test_unknown_platform_rejected():
    assert "PLATFORM_UNSUPPORTED" in codes(good_pin(platform="tiktok"))
    assert "PLATFORM_UNSUPPORTED" in codes(good_pin(platform=""))


# ------------------------------------------------ no partial / degraded pass
def test_multiple_failures_all_reported():
    r = validate({"platform": "pinterest", "text": "", "mediaUrls": []})
    for expected in ("TEXT_EMPTY", "MEDIA_EMPTY", "PIN_TITLE_MISSING",
                     "PIN_ALT_MISSING", "PIN_LINK_MISSING", "PIN_BOARD_MISSING"):
        assert expected in r.codes(), r.summary()


def test_result_summary_is_actionable():
    r = validate(good_pin(text=""))
    assert "REJECTED" in r.summary() and "pin-0014" in r.summary()


# ------------------------------- satellite destinations (Round 3)
def test_verified_satellite_link_allowed():
    """The satellite network is a sanctioned destination set: every domain was
    verified to return 200 and to link back to INH."""
    p = good_pin(link="https://besthomeinfraredsauna.com/emf")
    assert validate(p).ok, validate(p).summary()


def test_unknown_host_still_rejected():
    """Extending the allow-list must not turn the gate off."""
    for bad in ("https://amazon.com/dp/B01", "https://example.com/",
                "https://saunas-factory-direct.com/", "https://evil.co/inh"):
        assert "PIN_LINK_OFFSITE" in codes(good_pin(link=bad)), bad


def test_allow_list_matches_the_router_domain_list():
    from src.destinations import SATELLITES
    from src.limits import ALLOWED_LINK_HOSTS
    for d in SATELLITES:
        assert d in ALLOWED_LINK_HOSTS, f"{d} routed but not allowed by the validator"


# ------------------------------- placeholder / template artifacts (Round 3)
@pytest.mark.parametrize("junk", [
    "Full comparison: PLACEHOLDER", "TODO: add the link", "TBD",
    "See {{link}} for details", "lorem ipsum dolor sit amet",
    "Read more at YOUR_URL_HERE", "FIXME before publishing", "<insert link>"])
def test_placeholder_in_first_comment_rejected(junk):
    """The first staged run emitted 'Full comparison: PLACEHOLDER' and it passed:
    the error check only ever ran against the post body."""
    assert "SECONDARY_ERROR_PATTERN" in codes(good_fb(firstComment=junk)), junk


def test_placeholder_in_carousel_slides_rejected():
    p = good_ig(_slides=["Real slide", "TODO write this one", "Another"])
    assert "SECONDARY_ERROR_PATTERN" in codes(p)


def test_placeholder_in_pin_title_and_alt_rejected():
    assert "SECONDARY_ERROR_PATTERN" in codes(
        good_pin(title="Sauna Running Costs: PLACEHOLDER Per Session Really"))
    assert "SECONDARY_ERROR_PATTERN" in codes(
        good_pin(altText="TODO describe the image showing a plug-in meter and cabin"))


def test_clean_secondary_fields_still_pass():
    assert validate(good_fb()).ok
    assert validate(good_ig(_slides=["Different problems", "Hot tub: social"])).ok
    assert validate(good_pin()).ok


def test_body_error_check_unchanged():
    """The original body rule must keep firing -- this is additive."""
    assert "TEXT_ERROR_PATTERN" in codes(good_fb(text="Error: No response text. " * 5))


# ------------------------------- numeric grounding (Round 5, item 2)
GROUND = ("90 models 71 near zero 46 numeric 34 distance "
          "width 38 46 52 depth 36 41 48 height 68 75 78.6")


def test_grounded_numerals_pass():
    p = good_pin(text=("Sauna dimensions vary more than buyers expect. Across 90 indexed "
                       "models the 2-person cabins run 38 to 52 inches wide, median 46, "
                       "and 68 to 78.6 inches tall. Measure ceiling clearance, not just "
                       "the cabin."))
    r = validate(p, grounding=GROUND)
    assert r.ok, r.summary()


def test_invented_numeral_rejected():
    """The exact failure source_article existed to prevent."""
    p = good_pin(text=("Sauna dimensions vary. Across 90 indexed models the 2-person "
                       "cabins run 38 to 52 inches wide and weigh precisely 412 pounds "
                       "each, which is the number nobody publishes anywhere at all."))
    r = validate(p, grounding=GROUND)
    assert "UNGROUNDED_NUMERAL" in r.codes()
    assert "412" in r.summary()


def test_extrapolated_numeral_rejected():
    p = good_pin(text=("Across 90 indexed models the median 2-person cabin is 46 inches "
                       "wide, so a four-person cabin must be 92 inches wide, which is a "
                       "figure we simply doubled rather than measured anywhere."))
    assert "UNGROUNDED_NUMERAL" in validate(p, grounding=GROUND).codes()


def test_ungrounded_numeral_in_title_and_alt_rejected():
    assert "UNGROUNDED_NUMERAL" in validate(
        good_pin(title="Sauna Dimensions: The 777 Inch Cabin Nobody Mentions"),
        grounding=GROUND).codes()
    assert "UNGROUNDED_NUMERAL" in validate(
        good_pin(altText="A cedar sauna cabin measured at 999 inches wide on a tape"),
        grounding=GROUND).codes()


def test_grounding_absent_means_rule_not_applied():
    """Rows with no grounding are already blocked upstream; the validator must
    stay backward compatible."""
    assert validate(good_pin()).ok


def test_small_ordinals_are_not_treated_as_claims():
    p = good_pin(text=("Sauna dimensions come down to 3 numbers most buyers skip. Across "
                       "90 indexed models the 2-person cabins run 38 to 52 inches wide, "
                       "median 46 inches across the bench."))
    assert validate(p, grounding=GROUND).ok


def test_source_data_grounding_round_trips():
    """Shape, provenance and extractability -- deliberately NOT literal values.

    This test used to assert that "90", "71", "46" and "34" appear in the EMF
    grounding text. On 2026-09-15 the besthomeinfraredsauna index was
    republished: 90 models became 87 (two Dynamic models retired, one duplicate
    record resolved), so 71 "Near Zero EMF" labels became 68. The source was
    right, the refresh was right, and this test failed -- in the Sweep step of a
    manufacturer crawl that has nothing to do with EMF labels.

    A test that pins a literal value from refreshed third-party data WILL fail on
    some future refresh. So what is asserted here is what the CODE must do:
    resolve the cluster, carry its provenance, and emit every number it was given
    in a form the grounding extractor can reach. Content change is watched by
    scripts/check_facts_drift.py, which reports drift and halts only on an
    invariant breach (a subset larger than its source set, an unordered median, a
    collapsed count). Failures there name the moved metric instead of blocking a
    crawl.
    """
    import re as _re
    import src.facts as F
    sd = F.source_data_for({"cluster": "emf", "keyword": "low emf infrared sauna"})

    # provenance: without these the numbers are unattributable, whatever they are
    assert sd, "the emf cluster resolved to nothing"
    assert sd["fetched_at"], "no fetched_at — an undated figure cannot be cited"
    assert sd["url"], "no source url"

    g = F.grounding_text(sd)

    # every number the block contains must be reachable in the grounding text.
    # This is the real regression risk: Round 6 shipped numbers that lived only
    # in key names, and UNGROUNDED_NUMERAL rejected the model for citing them.
    for num in _walk_expected_numbers(sd["facts"]):
        assert num in g, (
            f"{num!r} is in the emf fact block but not extractable from the "
            f"grounding text — a caption citing it would be wrongly rejected")

    # the block is not empty of quantities, whatever they happen to be today
    assert len(_re.findall(r"\d+", g)) >= 4, (
        f"the emf grounding text carries fewer than 4 numbers: {g!r}")

    # the counts this cluster is for, present as keys and internally consistent.
    # Names are ours, so asserting them is asserting our own contract, not the
    # publisher's data.
    f = sd["facts"]
    for field in ("models_indexed", "models_with_an_emf_label",
                  "models_with_a_numeric_emf_claim",
                  "models_stating_the_measurement_distance"):
        assert field in f, f"the emf block no longer reports {field}"
    assert f["models_indexed"] > 0
    assert f["models_with_an_emf_label"] <= f["models_indexed"]
    assert f["models_stating_the_measurement_distance"] <= f["models_with_a_numeric_emf_claim"]


def _walk_expected_numbers(obj, out=None):
    """Numeric leaf values, as the strings a caption would quote."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_expected_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk_expected_numbers(v, out)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, int):
        out.append(str(obj))
    return out


# ------------- facts presentation must be extractable (Round 6, live finding)
def test_every_fact_number_is_reachable_by_the_grounding_extractor():
    """UNGROUNDED_NUMERAL fired on live output because 120 and 240 lived in KEY
    NAMES (models_120v, voltage_breakdown.120) and the extractor walks values.
    The model was rejected for correctly citing the block it was given.

    Any number a caption may quote must be extractable, or the rule punishes
    correct behaviour and pushes the model into vaguer copy.
    """
    import re as _re
    import src.facts as F
    for row in ({"cluster": "electrical", "keyword": "sauna electrical requirements"},
                {"cluster": "emf", "keyword": "low emf infrared sauna"},
                {"cluster": "fit", "keyword": "2 person sauna dimensions"}):
        sd = F.source_data_for(row)
        assert sd, row
        g = F.grounding_text(sd)
        # every numeral appearing in a KEY name must also be reachable as a value
        for key_num in _re.findall(r"\d+", " ".join(_flatten_keys(sd["facts"]))):
            assert key_num in g, (
                f"{row['cluster']}: {key_num!r} appears in a fact KEY but is not "
                f"extractable — a caption citing it would be wrongly rejected")


def _flatten_keys(obj, out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            _flatten_keys(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flatten_keys(v, out)
    return out


# --------------- EMPTY_BODY, against the three live-cycle assets (Round 7)
def _live(arch, **body):
    """Card fixture. A headline is required on every card, so supply a default
    unless the test is explicitly about its absence (pass headline=None)."""
    p = good_pin()
    p["_archetype"] = arch
    body.setdefault("headline", "71 of 90 need no electrician")
    if body.get("headline") is None:
        body.pop("headline")
    p["_body"] = body
    return p


def test_the_three_live_cycle_cards_all_fail_empty_body():
    """The live cycle produced cards that were ~70% empty: kicker, headline,
    standfirst, nothing. The comparison card had no comparison; the EMF card
    dropped the 90/46/34/4 statistic entirely. All three must now fail."""
    for arch in ("comparison", "correction", "spec"):
        r = validate(_live(arch, headline=None))
        assert "EMPTY_BODY" in r.codes(), f"{arch} card with no body passed"


def test_headline_only_card_is_rejected_for_every_archetype():
    from src.limits import ARCHETYPE_BODY
    for arch in ARCHETYPE_BODY:
        assert "EMPTY_BODY" in validate(_live(arch, headline=None)).codes(), arch


def test_filled_comparison_passes():
    r = validate(_live("comparison", a="Infrared", b="Steam room", rows=[
        ["Air temperature", "130 to 150F", "110 to 115F"],
        ["Humidity", "5 to 15%", "100%"],
        ["Heat-up time", "15 min", "35 to 45 min"]]))
    assert r.ok, r.summary()


def test_too_few_rows_rejected():
    r = validate(_live("comparison", a="A", b="B",
                       rows=[["Air temp", "130F", "110F"]]))
    assert "EMPTY_BODY" in r.codes() and "at least" in r.summary()


def test_wrong_row_width_rejected():
    r = validate(_live("comparison", a="A", b="B",
                       rows=[["Air temp", "130F"], ["Humidity", "5%"], ["Time", "15m"]]))
    assert "EMPTY_BODY" in r.codes()


def test_empty_cell_rejected():
    r = validate(_live("comparison", a="A", b="B", rows=[
        ["Air temp", "130F", "110F"], ["Humidity", "5%", ""], ["Time", "15m", "35m"]]))
    assert "EMPTY_BODY" in r.codes() and "empty cell" in r.summary()


def test_filled_correction_passes():
    r = validate(_live("correction", xLabel="What buyers compare",
                       yLabel="What actually decides it",
                       x=["Maximum temperature", "Panel count"],
                       y=["Heater type and wattage", "Who honours the warranty"]))
    assert r.ok, r.summary()


def test_body_numerals_are_grounded_too():
    """A figure smuggled into a table cell must face the same rule as body text."""
    r = validate(_live("spec", rows=[["Width", "46 in"], ["Depth", "41 in"],
                                     ["Weight", "999 lb"]]),
                 grounding="46 41 90 71")
    assert "UNGROUNDED_NUMERAL" in r.codes() and "999" in r.summary()


# ------------------------------- FINDING_UNSOURCED (Round 8)
def _finding_post(**over):
    p = {"id": "find-1", "platform": "facebook",
         "text": ("Of 90 indexed infrared saunas, 71 run from a standard 120V outlet. "
                  "Source: bhis_saunas, fetched 2026-09-02."),
         "mediaUrls": list(IMG),
         "firstComment": "Full index: https://besthomeinfraredsauna.com/",
         "_is_finding": True, "_dataset_name": "bhis_saunas", "_fetch_date": "2026-09-02",
         "_archetype": "chart",
         "_body": {"headline": "71 of 90 need no electrician",
                   "chart": {"type": "dot", "total": 90, "filled": 71}}}
    p.update(over)
    return p


def test_sourced_finding_passes():
    r = validate(_finding_post())
    assert r.ok, r.summary()


def test_finding_without_dataset_name_rejected():
    p = _finding_post(text="Of 90 indexed infrared saunas, 71 run from a standard outlet, fetched 2026-09-02.")
    assert "FINDING_UNSOURCED" in validate(p).codes()


def test_finding_without_fetch_date_rejected():
    p = _finding_post(text="Of 90 indexed saunas, 71 run from a standard outlet. Source: bhis_saunas.")
    assert "FINDING_UNSOURCED" in validate(p).codes()


def test_finding_with_no_source_metadata_at_all_rejected():
    p = _finding_post(_dataset_name="", _fetch_date="")
    r = validate(p)
    assert "FINDING_UNSOURCED" in r.codes() and "no dataset name" in r.summary()


def test_non_finding_posts_are_unaffected():
    assert validate(good_fb()).ok


def test_chart_card_needs_a_chart_object():
    p = _finding_post(_body={})
    assert "EMPTY_BODY" in validate(p).codes()


# ------------------------------- NO_FIGURE, against the two LIVE cards (Round 9)
LIVE_CARD_1 = {"a": "Infrared", "b": "Steam", "rows": [
    ["Heat source", "Direct radiant heaters", "Steam generator"],
    ["Room sealing", "Not required", "Fully sealed room"],
    ["Water hookup", "Not needed", "Floor drain needed"],
    ["Ceiling", "Flexible", "Fixed low ceiling"]]}

LIVE_CARD_2 = {"a": "Dry sauna", "b": "Wet sauna", "rows": [
    ["Humidity", "Low", "High"],
    ["Wood wear", "Lower", "Higher"],
    ["Maintenance", "Occasional", "Regular"],
    ["Wood species tolerance", "Flexible", "Limited"]]}

APPROVED_REFERENCE = {"a": "Infrared", "b": "Steam room", "rows": [
    ["Air temperature", "130 to 150°F", "110 to 115°F"],
    ["Humidity", "5 to 15%", "100%"],
    ["Heat-up time", "15 min", "35 to 45 min"],
    ["Circuit", "240V · 20 amps", "240V · 30 amps"]]}


def test_both_live_cards_fail_no_figure():
    """The two cards that actually published contain no numbers at all."""
    for body in (LIVE_CARD_1, LIVE_CARD_2):
        r = validate(_live("comparison", **body))
        assert "NO_FIGURE" in r.codes(), r.summary()


def test_lower_higher_is_reported_as_a_non_value():
    r = validate(_live("comparison", **LIVE_CARD_2))
    assert "Lower" in r.summary() or "Higher" in r.summary()


def test_the_approved_reference_card_passes():
    r = validate(_live("comparison", **APPROVED_REFERENCE))
    assert r.ok, r.summary()


@pytest.mark.parametrize("cell,ok", [
    ("130 to 150°F", True), ("5 to 15%", True), ("240V · 20 amps", True),
    ("$1,999", True), ("15 min", True), ("1.4 kWh", True),
    ("Lower", False), ("Higher", False), ("Flexible", False), ("Limited", False),
    ("Occasional", False), ("Not required", False), ("Fully sealed room", False),
    ("Steam generator", False), ("", False)])
def test_figure_detection(cell, ok):
    from src.validator import is_figure
    assert is_figure(cell) is ok, cell


def test_one_figure_is_not_enough():
    r = validate(_live("comparison", a="A", b="B", rows=[
        ["Air temperature", "130°F", "Higher"],
        ["Humidity", "Low", "High"],
        ["Wear", "Lower", "Higher"]]))
    assert "NO_FIGURE" in r.codes()


def test_cost_card_figure_counts():
    r = validate(_live("cost", figure="$0.71", unit="per 45-minute session", rows=[
        ["Draw per session", "1.4 kWh"], ["Sessions per week", "4"],
        ["Monthly", "$12.30"]]))
    assert r.ok, r.summary()


@pytest.mark.parametrize("arch", ["checklist", "evidence"])
def test_qualitative_archetypes_are_exempt(arch):
    body = ({"items": ["Shower before you enter", "Sit on your towel",
                       "Leave the phone in the locker"]} if arch == "checklist"
            else {"claim": "Does a sauna help you lose weight?",
                  "finding": "Not meaningfully; the weight is water and it returns.",
                  "strength": "limited", "source": "Reviewed against published trials."})
    assert "NO_FIGURE" not in validate(_live(arch, **body)).codes()


# ------------------------------- WEAK_HEADLINE (Round 9)
@pytest.mark.parametrize("head", [
    "Infrared vs steam: the build differences that matter",
    "Sauna wiring: what you need to know",
    "Infrared vs Steam Sauna: What Actually Differs",
    "Home saunas: a complete guide",
    "Everything about sauna humidity"])
def test_topic_label_headlines_rejected(head):
    p = _live("comparison", headline=head, **APPROVED_REFERENCE)
    assert "WEAK_HEADLINE" in validate(p).codes(), head


@pytest.mark.parametrize("head", [
    "Same 180F. Completely different heat.",
    "The $10,000 sauna can be the worse one.",
    "71 of 90 need no electrician.",
    "Steam needs a floor drain. Infrared needs an outlet."])
def test_claim_headlines_pass(head):
    p = _live("comparison", headline=head, **APPROVED_REFERENCE)
    assert "WEAK_HEADLINE" not in validate(p).codes(), head


def test_the_live_card_headline_is_rejected():
    """The headline that actually published was a topic label."""
    p = _live("comparison", headline="Infrared vs Steam Sauna: What Actually Differs",
              **APPROVED_REFERENCE)
    assert "WEAK_HEADLINE" in validate(p).codes()


def test_everything_shown_to_the_model_is_grounded():
    """Round 6's key-name bug recurring: numbers reach the prompt via note/basis
    and the walker never saw them, so correct citation was rejected."""
    import src.facts as F
    sd = F.source_data_for({"cluster": "cost", "keyword": "home sauna cost"})
    assert sd and sd.get("note"), "cost facts carry a basis/note line"
    g = F.grounding_text(sd)
    import re as _re
    for n in _re.findall(r"\d{3,4}", sd["note"]):
        assert n in g, f"{n!r} is shown to the model but is not grounded"


def test_figures_payload_is_grounded():
    import src.facts as F
    payload = {"rows": [["Amp draw", "15 to 20 amps", "15 to 30 amps"]]}
    import json as _json
    g = F.grounding_text(None, extra=_json.dumps(payload))
    assert "15" in g and "20" in g and "30" in g


def test_every_archetype_requires_a_headline():
    """A cost card shipped with headline: None because the check was per
    archetype and no archetype listed it."""
    from src.limits import ARCHETYPE_BODY
    bodies = {
        "comparison": APPROVED_REFERENCE,
        "cost": {"figure": "$0.71", "unit": "per session",
                 "rows": [["Draw", "1.4 kWh"], ["Weekly", "4"], ["Monthly", "$12.30"]]},
        "spec": {"rows": [["Width", "46 in"], ["Depth", "41 in"], ["Height", "75 in"]]},
        "checklist": {"items": ["a", "b", "c"]},
        "evidence": {"claim": "c", "finding": "f", "strength": "limited", "source": "s"},
        "chart": {"chart": {"type": "dot", "total": 90, "filled": 71}},
    }
    for arch, body in bodies.items():
        assert arch in ARCHETYPE_BODY
        r = validate(_live(arch, headline=None, **body))   # explicitly no headline
        assert "EMPTY_BODY" in r.codes(), f"{arch} passed without a headline"
        r2 = validate(_live(arch, headline="71 of 90 need no electrician", **body))
        assert "EMPTY_BODY" not in r2.codes(), f"{arch}: {r2.summary()}"


# ------------------------------- DENOMINATOR_MISSING (Round 11)
def _share_finding(**over):
    p = _finding_post()
    p.update({"_finding_kind": "concentration",
              "_figures": {"top": "China", "count": 84, "total": 154, "share": 0.545},
              "_baseline": None, "_population_is_the_subject": False})
    p.update(over)
    return p


def test_the_china_finding_is_blocked():
    """China manufactures most US home saunas, so 55% of recalls may be BELOW
    expectation. Published bare it reads as nationality, not safety."""
    r = validate(_share_finding())
    assert "DENOMINATOR_MISSING" in r.codes(), r.summary()


def test_share_with_a_sourced_baseline_passes():
    r = validate(_share_finding(_baseline={"value": 0.78,
                                           "source": "US import share, 2025"}))
    assert "DENOMINATOR_MISSING" not in r.codes(), r.summary()


def test_baseline_without_a_source_is_not_enough():
    assert "DENOMINATOR_MISSING" in validate(
        _share_finding(_baseline={"value": 0.78})).codes()


def test_population_as_subject_passes():
    """'56% of the indexed studies are observational' describes the population
    itself and implies no outside comparison."""
    r = validate(_share_finding(_population_is_the_subject=True))
    assert "DENOMINATOR_MISSING" not in r.codes(), r.summary()


def test_non_share_findings_are_unaffected():
    """58 recalls since 2015, and fire leading 129 of 231 filings, have no
    denominator problem."""
    p = _finding_post()
    p.update({"_finding_kind": "disclosure",
              "_figures": {"recalls": 58, "first_year": "2015"}})
    assert "DENOMINATOR_MISSING" not in validate(p).codes()


def test_the_probe_library_no_longer_offers_the_origin_finding():
    import src.probes as P
    from src.validator import check_denominator
    for f in P.publishable(P.run_all()):
        post = {"_is_finding": True, "_finding_kind": f.get("kind"),
                "_figures": f.get("figures"), "_baseline": f.get("baseline"),
                "_population_is_the_subject": f.get("population_is_the_subject")}
        if not check_denominator(post).ok:
            assert "country" in f["id"] or "origin" in f["id"], (
                f"unexpected finding blocked: {f['claim']}")


# ------------------------------- DESTINATION_MISMATCH (Round 12)
def _dest(claim_terms, dest_terms, **over):
    p = _live("comparison", **APPROVED_REFERENCE)
    p["_figure_terms"] = claim_terms
    p["_destination_terms"] = dest_terms
    p.update(over)
    return p


def test_the_real_defect_is_caught():
    """The pre-publish catch: a price/temperature claim pointing at a
    wood-durability article. Every figure was real; NO_FIGURE and
    UNGROUNDED_NUMERAL both passed it."""
    p = _dest("Infrared Traditional",
              "Sauna Wood Species in Wet Heat: Durability, Off-Gassing and "
              "Maintenance Over 10 Years")
    assert "DESTINATION_MISMATCH" in validate(p).codes(), validate(p).summary()


def test_agreeing_destination_passes():
    p = _dest("Infrared Traditional", "Outdoor Steam Sauna vs Traditional Sauna")
    assert "DESTINATION_MISMATCH" not in validate(p).codes()


def test_generic_sauna_overlap_is_not_agreement():
    """Everything here is about saunas; overlap on that word means nothing."""
    from src.validator import _topic_terms
    assert "sauna" not in _topic_terms("Best home sauna guide 2026")


def test_missing_terms_do_not_guess():
    assert "DESTINATION_MISMATCH" not in validate(_dest(None, "anything")).codes()
    assert "DESTINATION_MISMATCH" not in validate(_dest("anything", None)).codes()


def test_partial_overlap_is_left_alone():
    """Blocking on a guess would be worse than the defect."""
    p = _dest("Infrared Traditional", "Infrared sauna buying guide")
    assert "DESTINATION_MISMATCH" not in validate(p).codes()


def test_measurement_labels_are_not_the_subject():
    """The rule compares WHAT IS MEASURED, never the measurement names.

    Comparing row labels ("Amp draw", "Price, median") against destination
    titles flagged 68% of the queue -- measurement vocabulary and subject
    vocabulary do not intersect, so the rule fired on correct pairings.
    Work orders now pass the compared entities instead; this test pins that
    the two vocabularies really are disjoint, so the mistake stays fixed."""
    from src.validator import _topic_terms
    labels = _topic_terms("Models indexed Max temperature Amp draw Price median Weight")
    title = _topic_terms("Outdoor Steam Sauna vs Traditional Sauna")
    assert not (labels & title)


def test_only_comparisons_are_judged():
    """spec/cost/article payloads carry no subject, so the rule declines."""
    import src.workorders  # noqa: F401  -- documents where terms are built
    for payload in ({"models": 45}, {"figure": "$2.46", "unit": "median cost"},
                    {"article_figures": ["a", "b"]}):
        terms = " ".join(str(payload.get(k) or "") for k in ("a", "b")).strip() or None
        assert terms is None
