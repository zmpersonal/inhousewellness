"""Round 4 (Discovery): blog-link rules and the comment-only layout fix."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_blog_links as bl  # noqa: E402
import verified_deploy as vd  # noqa: E402

PAGES = [
    {"handle": "maxxus-seattle-2-person", "url": "/pages/sauna-database/maxxus-seattle-2-person", "title": "Maxxus Seattle Far IR Sauna, 2 Person",
     "brand": "Maxxus", "series": "seattle", "variants": frozenset(), "model_numbers": ["MX-J206-01"]},
    {"handle": "maxxus-seattle-zf-2-person", "url": "/pages/sauna-database/maxxus-seattle-zf-2-person", "title": "Maxxus Seattle ZF, 2 Person",
     "brand": "Maxxus", "series": "seattle", "variants": frozenset({"zf"}), "model_numbers": []},
    {"handle": "gd-toledo", "url": "/pages/sauna-database/gd-toledo", "title": "Golden Designs Toledo Hybrid Sauna Full Spectrum",
     "brand": "Golden Designs", "series": "toledo", "variants": frozenset({"fs"}), "model_numbers": []},
    {"handle": "dyn-venice-a", "url": "/a", "title": "Dynamic Saunas Venice, 2 Person", "brand": "Dynamic Saunas", "series": "venice",
     "variants": frozenset(), "model_numbers": []},
    {"handle": "dyn-venice-b", "url": "/b", "title": "Dynamic Saunas Venice Far IR Sauna, 2 Person", "brand": "Dynamic Saunas",
     "series": "venice", "variants": frozenset(), "model_numbers": []},
]
PATS = bl.mention_patterns(PAGES)


def art(body, blog="saunas", handle="a"):
    return {"id": "x", "handle": handle, "blog": {"handle": blog}, "body": body}


def test_the_only_edit_is_one_wrapped_span():
    body = "<p>The Maxxus Seattle is compact. The Maxxus Seattle again.</p>"
    props, _ = bl.model_proposals(art(body), PAGES, PATS)
    assert len(props) == 1
    new = bl.apply_link(body, props[0]["start"], props[0]["end"], props[0]["target"])
    assert new.replace('<a href="/pages/sauna-database/maxxus-seattle-2-person">', "").replace("</a>", "", 1) == body
    assert new.count("<a ") == 1


@pytest.mark.parametrize("body", [
    "<h2>Maxxus Seattle review</h2>",
    '<p><a href="/products/x">Maxxus Seattle</a></p>',
    '<div class="product-card"><p>Maxxus Seattle</p></div>',
    '<p><button>Maxxus Seattle</button></p>',
    '<p><img alt="Maxxus Seattle" src="x.jpg"></p>',
    "<p>Maxxus Seattle review video. 2024. https://www.youtube.com/watch?v=x</p>",
])
def test_ineligible_places_are_never_linked(body):
    assert bl.model_proposals(art(body), PAGES, PATS)[0] == []


def test_a_variant_token_picks_the_variant_page_and_joins_the_anchor():
    props, _ = bl.model_proposals(art("<p>Consider the Maxxus Seattle ZF for EMF.</p>"), PAGES, PATS)
    assert props[0]["target"].endswith("maxxus-seattle-zf-2-person") and props[0]["anchor"] == "Maxxus Seattle ZF"


def test_a_series_with_one_page_resolves_though_its_name_carries_full_spectrum():
    props, _ = bl.model_proposals(art("<p>Choose the Golden Designs Toledo for hybrid heat.</p>"), PAGES, PATS)
    assert props[0]["target"].endswith("gd-toledo")


def test_two_pages_the_mention_could_mean_are_ambiguous_and_not_linked():
    props, amb = bl.model_proposals(art("<p>The Dynamic Venice is popular.</p>"), PAGES, PATS)
    assert props == [] and amb and len(amb[0]["candidates"]) == 2


def test_a_variant_the_database_has_no_page_for_is_not_linked():
    pages = [p for p in PAGES if p["handle"] != "maxxus-seattle-zf-2-person"]
    props, _ = bl.model_proposals(art("<p>The Maxxus Seattle ZF is quiet.</p>"), pages, bl.mention_patterns(pages))
    assert props == []


def test_at_most_three_links_per_article():
    pages = [dict(PAGES[0], handle=f"m{i}", url=f"/m{i}", series=s) for i, s in enumerate(["aa", "bb", "cc", "dd"])]
    body = "<p>" + " ".join(f"Maxxus {s} is here." for s in ["aa", "bb", "cc", "dd"]) + "</p>"
    assert len(bl.model_proposals(art(body), pages, bl.mention_patterns(pages))[0]) == 3


def test_the_comment_fix_changes_only_a_comment():
    snap = sorted((ROOT / "data/verified/golive").glob("main-*-snapshot"))[0]
    base = (snap / "layout__theme.liquid").read_text()
    stale = vd.patch_layout(base).replace(vd.FIXED_UNKNOWN_COMMENT, vd.STALE_UNKNOWN_COMMENT)
    fixed = vd.fix_unknown_comment(stale)
    assert vd.FIXED_UNKNOWN_COMMENT in fixed and vd.STALE_UNKNOWN_COMMENT not in fixed
    assert vd.strip_liquid_comments(fixed) == vd.strip_liquid_comments(stale)
    assert vd.fix_unknown_comment(fixed) == fixed


def test_the_comment_fix_halts_if_it_would_touch_code():
    stale = "{%- comment -%}\n" + vd.STALE_UNKNOWN_COMMENT + "{%- endcomment -%}\n"
    bad = stale + vd.STALE_UNKNOWN_COMMENT      # a second copy outside any comment
    with pytest.raises(SystemExit):
        vd.fix_unknown_comment(bad)
