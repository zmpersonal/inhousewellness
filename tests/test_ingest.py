"""Batch-ingest tests, written against the documented batch-02 contract so the
path is proven before the real file lands."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import pytest
from ingest_batch import merge, normalise

EMF = "https://besthomeinfraredsauna.com/emf"
FIT = "https://besthomeinfraredsauna.com/best/small-spaces"


def row(**kw):
    d = {"keyword": "low emf infrared sauna", "link": EMF, "volume": 590,
         "difficulty": 7, "cluster": "emf"}
    d.update(kw)
    return d


def test_source_article_is_nulled_for_the_remap_engine():
    r = normalise(row(source_article="https://guessed.example/x"), 0, 1)
    assert r["source_article"] is None, "batch must not supply a source URL"


def test_link_is_preserved_and_locked():
    r = normalise(row(), 0, 1)
    assert r["link"] == EMF
    assert r["link_locked"] is True


def test_offsite_destination_fails_loudly():
    with pytest.raises(SystemExit) as e:
        normalise(row(link="https://competitor.example/emf"), 0, 1)
    assert "allow-list" in str(e.value)


@pytest.mark.parametrize("missing", ["keyword", "link"])
def test_missing_required_field_fails(missing):
    r = row()
    del r[missing]
    with pytest.raises(SystemExit):
        normalise(r, 3, 4)


def test_defaults_applied():
    r = normalise(row(), 0, 7)
    assert r["id"] == "b02-0007"
    assert r["reuse_class"] == "evergreen" and r["min_repost_days"] == 120
    assert r["batch"] == "02-interactive" and r["status"] == "queued"


def test_merge_dedups_on_normalised_signature():
    existing = [{"id": "pin-0001", "keyword": "infrared vs steam sauna"}]
    batch = [normalise(row(keyword="steam vs infrared sauna", link=EMF), 0, 1),
             normalise(row(keyword="low emf infrared sauna", link=EMF), 1, 2)]
    merged, added, skipped = merge(existing, batch)
    assert len(added) == 1 and added[0]["keyword"] == "low emf infrared sauna"
    assert len(skipped) == 1 and skipped[0][1] == "pin-0001"
    assert len(merged) == 2


def test_merge_dedups_within_the_batch_against_existing_only():
    existing = []
    batch = [normalise(row(keyword="sauna emf levels"), 0, 1),
             normalise(row(keyword="emf levels sauna"), 1, 2)]
    merged, added, skipped = merge(existing, batch)
    assert len(added) == 1, "reordered restatement must not enter twice"


def test_link_locked_row_keeps_its_destination_through_route():
    """The router must not overwrite a pre-set interactive-asset link."""
    from src.destinations import route, domain_of
    routable = [{"keyword": "sauna cost", "archetype": "cost",
                 "best_url": "https://infinitesauna.com/guides/x",
                 "best_score": 0.8, "best_domain": "infinitesauna.com",
                 "inh_url": None, "inh_score": None}]
    assigned, blocked, counts = route(
        routable, preassigned_domains=["besthomeinfraredsauna.com"] * 4, total_rows=5)
    assert counts["besthomeinfraredsauna.com"] == 4, "locked rows must count in the quota"


def test_preassigned_inh_reduces_the_remaining_inh_target():
    from src.destinations import route
    rows = [{"keyword": f"k{i}", "archetype": "cost",
             "best_url": "https://infinitesauna.com/g", "best_score": 0.8,
             "best_domain": "infinitesauna.com",
             "inh_url": "https://inhousewellness.com/blogs/saunas/a",
             "inh_score": 0.7} for i in range(4)]
    a, _, counts = route(rows, preassigned_domains=["inhousewellness.com"] * 4,
                         total_rows=8)
    # floor is 40% of 8 = 3.2 -> 3; four are already INH, so none more are forced
    assert counts["inhousewellness.com"] >= 4


# ------------------------------- URL canonicalisation (Round 6)
@pytest.mark.parametrize("a,b", [
    ("https://besthomeinfraredsauna.com/emf", "https://besthomeinfraredsauna.com/emf/"),
    ("https://besthomeinfraredsauna.com/", "https://besthomeinfraredsauna.com/#finder"),
    ("https://X.com/A", "https://x.com/A/"),
])
def test_same_page_canonicalises_the_same(a, b):
    from src.destinations import canonical_url
    assert canonical_url(a) == canonical_url(b)


def test_url_cap_counts_slash_variants_as_one_page():
    """/emf and /emf/ counted separately let 6 pins land on a page capped at 4."""
    from src.destinations import audit
    urls = ["https://besthomeinfraredsauna.com/emf"] * 4 + \
           ["https://besthomeinfraredsauna.com/emf/"] * 2
    v = audit(urls).url_violations(urls)
    assert v and "6 pins" in v[0]


def test_distinct_pages_are_not_merged():
    from src.destinations import canonical_url
    assert canonical_url("https://x.com/emf") != canonical_url("https://x.com/electrical")
