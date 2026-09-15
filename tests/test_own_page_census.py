"""The Phase 1 census: what our own pages say, and what they do not.

Every detector here decides a coverage number the client reads as a share of
165. A detector that over-counts produces a precise, confident, wrong rate —
which is exactly what happened on the first pass: 35 Google Drive embeds sitting
in `custom.video` were counted as manuals, putting coverage at 106/165 when the
documents field alone gives 102.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.census_own_pages import (  # noqa: E402
    BUCKET_LABEL, UNREACHABLE, bucket, census, find_manuals, find_model_numbers,
    find_shipping, flatten_metafield, looks_like_a_part_number, self_test,
    trim_to_part_number, variant_weight,
)

CENSUS = ROOT / "data" / "own-page-census.json"


def _prod(body="", metafields=(), variants=()):
    return {"handle": "h", "title": "t", "vendor": "v", "descriptionHtml": body,
            "metafields": {"nodes": [{"namespace": "custom", "key": k, "type": ty,
                                      "value": v} for k, ty, v in metafields]},
            "variants": {"nodes": list(variants)}}


def test_census_controls_fire():
    assert self_test() == []


# ── the correction that mattered ─────────────────────────────────────────────

def test_a_drive_embed_in_the_video_field_is_not_a_manual():
    """The over-count. Role comes from the field the reference sits in, never
    from the fact that it is a Drive link."""
    p = _prod(metafields=[
        ("video", "multi_line_text_field",
         '<iframe src="https://drive.google.com/file/d/1VIDEOxxxxxxxxxxxxx/preview">'),
        ("product_documents", "multi_line_text_field",
         '<iframe src="https://drive.google.com/file/d/1DOCxxxxxxxxxxxxxxx/preview">')])
    roles = {m["file_id"]: m["role"] for m in find_manuals(p)}
    assert roles == {"1VIDEOxxxxxxxxxxxxx": "video",
                     "1DOCxxxxxxxxxxxxxxx": "manual_candidate"}
    rows = census([p])
    assert rows[0]["manual_candidates"] == 1
    assert len(rows[0]["manuals"]) == 2, "the video is kept, just not counted"


def test_the_committed_census_never_counts_a_video_as_a_manual():
    if not CENSUS.exists():
        pytest.skip("census not built")
    for r in json.loads(CENSUS.read_text())["rows"]:
        docs = [m for m in r["manuals"] if m["role"] == "manual_candidate"]
        assert r["manual_candidates"] == len(docs)
        for m in r["manuals"]:
            if m["source"].endswith(".video"):
                assert m["role"] == "video", m


# ── model numbers must never be prose ────────────────────────────────────────

@pytest.mark.parametrize("raw,ok", [
    ("MX-LS3-01", True), ("GDI-6880-02", True), ("FD-KN001", True),
    ("CTC88W", True), ("MX-M356-01-FS CED", True), ("38440-0FNC-SPS-1", True),
    ("6 persons", False), ("2 person sauna", False), ("8 kW heater", False),
    ("Heming Edition", False), ("Deluxe", False), ("the best one", False),
])
def test_part_number_discrimination(raw, ok):
    assert looks_like_a_part_number(raw) is ok, raw


def test_one_fact_gets_one_answer_whatever_field_it_sits_in():
    """The same sentence in a flat field and in a rich_text block must yield the
    same model number. It did not: the flat field found nothing, because the
    capture required terminal punctuation and the line packs several labels."""
    flat = "Brand: Maxxus Model: MX-K406-01 CED Capacity: 4 Person"
    rich = json.dumps({"type": "root", "children": [{"type": "list", "children": [
        {"type": "list-item", "children": [{"type": "text", "value": "Brand: Maxxus"}]},
        {"type": "list-item", "children": [{"type": "text", "value": "Model: MX-K406-01 CED"}]},
        {"type": "list-item", "children": [{"type": "text", "value": "Capacity: 4 Person"}]}]}]})
    a = find_model_numbers(_prod(metafields=[("key_feature", "single_line_text_field", flat)]), [])
    b = find_model_numbers(_prod(metafields=[("key_feature", "rich_text_field", rich)]), [])
    assert [x["value"] for x in a] == [x["value"] for x in b] == ["MX-K406-01 CED"]


@pytest.mark.parametrize("raw,want", [
    ("MX-1 is the best sauna", "MX-1"),      # prose trimmed back, hit kept
    ("GDI-6880-02 Elite", "GDI-6880-02 Elite"),   # a real spaced SKU survives whole
    ("MX-M356-01-FS CED", "MX-M356-01-FS CED"),
    ("8 kW heater", None),                    # a heater size is not a part number
    ("6 persons", None),
    ("2 person sauna", None),
    ("Heming Edition", None),
])
def test_trim_back_recovers_a_part_number_without_inventing_one(raw, want):
    assert trim_to_part_number(raw) == want


def test_a_model_number_carries_its_verbatim_span_and_source():
    p = _prod(metafields=[("key_feature", "single_line_text_field",
                           "Brand: Maxxus Model: MX-K406-01 CED Capacity: 4 Person")])
    got = find_model_numbers(p, [])
    assert got[0]["value"] == "MX-K406-01 CED"
    assert got[0]["source"] == "metafield:custom.key_feature"
    assert "MX-K406-01 CED" in got[0]["span"]


def test_a_model_number_matching_our_sku_is_flagged():
    p = _prod(metafields=[("key_feature", "t", "Model: MX-K306-01")])
    assert find_model_numbers(p, ["MX-K306-01"])[0]["matches_our_sku"]
    assert not find_model_numbers(p, ["GDI-9999-99"])[0]["matches_our_sku"]


# ── rich text must not run blocks together ───────────────────────────────────

def test_rich_text_blocks_are_separated():
    doc = json.dumps({"type": "root", "children": [{"type": "list", "children": [
        {"type": "list-item", "children": [{"type": "text", "value": "Weight: 410 lbs"}]},
        {"type": "list-item", "children": [{"type": "text", "value": "Model: MX-LS3-01"}]},
    ]}]})
    flat = flatten_metafield(doc, "rich_text_field")
    assert flat.splitlines() == ["Weight: 410 lbs", "Model: MX-LS3-01"]


def test_a_non_rich_text_value_passes_through():
    assert flatten_metafield("<iframe src='x'>", "multi_line_text_field") == "<iframe src='x'>"


def test_unparseable_rich_text_is_returned_not_crashed():
    assert flatten_metafield("{not json", "rich_text_field") == "{not json"


# ── shipping ─────────────────────────────────────────────────────────────────

def test_weight_and_boxes_from_the_clients_example():
    w, b = find_shipping(_prod("Shipping weight: 410 lbs / Ships in 3 boxes."))
    assert w[0]["value"] == 410 and w[0]["unit"] == "lb"
    assert b[0]["value"] == 3
    assert "410" in w[0]["span"]


def test_a_zero_shopify_weight_is_never_coverage():
    """SHOPIFY_WEIGHT_ZERO: 0 lb is the merchant default a nobody entered, and
    summing it into freight would produce a confident, precise, false number."""
    p = _prod(variants=[
        {"sku": "A", "inventoryItem": {"measurement": {"weight": {"value": 0, "unit": "POUNDS"}}}},
        {"sku": "B", "inventoryItem": {"measurement": {"weight": {"value": None, "unit": "POUNDS"}}}},
        {"sku": "C", "inventoryItem": {"measurement": {"weight": {"value": 750, "unit": "POUNDS"}}}}])
    assert [x["sku"] for x in variant_weight(p)] == ["C"]


# ── buckets ──────────────────────────────────────────────────────────────────

def test_bucket_assignment_is_exhaustive_and_labelled():
    assert {bucket(True, True), bucket(True, False),
            bucket(False, True), bucket(False, False)} == {1, 2, 3, 4}
    assert set(BUCKET_LABEL) == {1, 2, 3, 4}


def test_the_committed_census_buckets_add_up():
    if not CENSUS.exists():
        pytest.skip("census not built")
    d = json.loads(CENSUS.read_text())
    rows, s = d["rows"], d["summary"]
    assert len(rows) == s["n"] == 165
    assert sum(int(v) for v in s["buckets"].values()) == 165
    for r in rows:
        assert r["bucket"] == bucket(bool(r["manual_candidates"]), bool(r["model_numbers"]))


def test_the_unreachable_vendor_list_matches_the_discovery_output():
    """UNREACHABLE is data restated from discover run 3. If the two ever drift,
    the cross-tab is describing a world that no longer exists."""
    disc = ROOT / "data" / "facts" / "manufacturer-discovery.json"
    if not disc.exists():
        pytest.skip("no discovery output")
    actual = {r["vendor"] for r in json.loads(disc.read_text())["vendors"]
              if not r.get("robots_readable")}
    assert set(UNREACHABLE) == actual, (
        "census UNREACHABLE and the discovery output disagree: "
        f"{set(UNREACHABLE) ^ actual}")
