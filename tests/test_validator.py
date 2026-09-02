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
