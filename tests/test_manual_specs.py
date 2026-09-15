"""The manual extractor, exercised against a real PDF built here.

No manual is reachable from a session: every one is a Google Drive embed and
drive.google.com answers 403 on CONNECT from the agent proxy. So the PDF path is
proven against a text-layer PDF constructed in this file — page numbers, spans,
both guards and the tiering — rather than against a live file nobody can see.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.extract_manual_specs import (  # noqa: E402
    drive_download_url, pages_of, readings_from, self_test,
)


def make_pdf(page_texts):
    """A minimal, valid, text-layer PDF — one page per string, with a correct
    xref table so this tests the reader and not pypdf's damaged-file recovery."""
    objs, kids = [], []
    font_num = 3 + 2 * len(page_texts)
    for i, txt in enumerate(page_texts):
        page_num = 3 + 2 * i
        content_num = page_num + 1
        kids.append("%d 0 R" % page_num)
        safe = txt.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream = "BT /F1 12 Tf 72 720 Td (%s) Tj ET" % safe
        objs.append((page_num,
                     "<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                     "/Contents %d 0 R/Resources<</Font<</F1 %d 0 R>>>>>>"
                     % (content_num, font_num)))
        objs.append((content_num,
                     "<</Length %d>>\nstream\n%s\nendstream" % (len(stream), stream)))
    objs.append((font_num, "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"))
    objs.insert(0, (2, "<</Type/Pages/Kids[%s]/Count %d>>"
                    % (" ".join(kids), len(page_texts))))
    objs.insert(0, (1, "<</Type/Catalog/Pages 2 0 R>>"))
    objs.sort()

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num, body in objs:
        offsets[num] = len(out)
        out += ("%d 0 obj %s endobj\n" % (num, body)).encode("latin-1")
    xref_at = len(out)
    n = max(offsets) + 1
    out += ("xref\n0 %d\n" % n).encode()
    out += b"0000000000 65535 f \n"
    for i in range(1, n):
        out += ("%010d 00000 n \n" % offsets.get(i, 0)).encode()
    out += ("trailer <</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n"
            % (n, xref_at)).encode()
    return bytes(out)


def test_extractor_controls_fire():
    """Both guards, the plausibility band, the recommendation rule and the
    tiering, each against input that must and must not yield a rating."""
    assert self_test() == []


def test_a_real_pdf_round_trips_with_page_numbers():
    raw = make_pdf(["Welcome to your sauna. Enjoy the gentle warmth.",
                    "SPECIFICATIONS  Rated power: 4.5 kW   Model No. MX-LS3-01"])
    assert raw.startswith(b"%PDF")
    pages = pages_of(raw)
    assert [p for p, _ in pages] == [1, 2], pages
    acc, rej = readings_from(pages, "https://example/m.pdf")
    assert len(acc) == 1, acc
    assert acc[0]["kw"] == 4.5
    assert acc[0]["page"] == 2, "the page number must be the page a human turns to"
    assert acc[0]["tier"] == "spec_plate"
    assert "4.5 kW" in acc[0]["span"]
    assert acc[0]["source_url"] == "https://example/m.pdf"


def test_the_1800_watt_bug_cannot_recur_through_a_pdf():
    """The parser that read '1,800 watts' as 800 W produced 0.8 kW saunas. It is
    imported, not restated, so it cannot drift away from this."""
    acc, _ = readings_from(pages_of(make_pdf(["RATING 1,800 watts"])), "u")
    assert acc and acc[0]["kw"] == 1.8


def test_an_implausible_value_is_recorded_not_dropped():
    acc, rej = readings_from(pages_of(make_pdf(["Standby draw 200 W"])), "u")
    assert acc == []
    assert rej and "plausibility band" in rej[0]["rejected_because"]
    assert rej[0]["page"] == 1 and "200 W" in rej[0]["span"]


def test_a_recommended_heater_is_never_read_as_a_rating():
    """The Dundalk case, verbatim from its registry note: 'an 8 kW electric
    heater is recommended' says what to buy, not what this unit draws."""
    acc, rej = readings_from(pages_of(make_pdf([
        "An 8 kW electric heater is recommended for optimal performance."])), "u")
    assert acc == []
    assert rej and "recommendation" in rej[0]["rejected_because"]


def test_a_spec_plate_outranks_marketing_copy():
    acc, _ = readings_from(pages_of(make_pdf([
        "Feel the 3 kW of gentle radiant heat wrap around you.",
        "ELECTRICAL DATA - rated 7.5 kW"])), "u")
    assert acc[0]["kw"] == 7.5 and acc[0]["tier"] == "spec_plate"
    assert acc[1]["kw"] == 3.0 and acc[1]["tier"] == "body_copy"


def test_a_scan_has_no_text_layer_and_is_not_guessed_at():
    """A PDF with no text layer must yield nothing, so the caller records
    NEEDS_OCR instead of inventing a rating."""
    assert pages_of(make_pdf([" "])) == []


def test_drive_download_url_shape():
    assert drive_download_url("1abcDEF") == \
        "https://drive.google.com/uc?export=download&id=1abcDEF"


@pytest.mark.parametrize("head", [b"<!DOCTYPE html>", b"\x00\x00\x00 ftypmp4"])
def test_non_pdf_bytes_are_detectable(head):
    """Drive serves an HTML interstitial for large files, and a video is not a
    manual. The caller checks the %PDF magic; this pins that they differ."""
    assert not head.startswith(b"%PDF")


# ── a zero must carry its own evidence ───────────────────────────────────────
# Run 1 read 9 real PDFs, 278 pages, no OCR needed, and found not one rated
# power. "The manuals do not state it" and "we could not read what they state"
# are different facts, and a bare zero cannot tell them apart.

from scripts.extract_manual_specs import electrical_context  # noqa: E402


def test_a_manual_stating_only_volts_and_amps_is_visibly_that():
    """The likely real case: infrared manuals give a supply spec, not a total
    wattage. The diagnostic must show volts and amps present and watts absent,
    so the zero reads as the manual's silence rather than ours."""
    pages = pages_of(make_pdf(["Installation", "Power Supply: 120V 15A dedicated circuit"]))
    acc, rej = readings_from(pages, "u")
    assert acc == [] and rej == []
    spans, npages, sample, chars = electrical_context(pages)
    terms = {s["term"] for s in spans}
    assert {"power", "supply", "circuit"} <= terms
    assert "watt" not in terms and "kw" not in terms
    assert npages == 1 and chars > 0
    assert sample["page"] == 2 and "120V" in sample["text"]


def test_garbled_extraction_is_visible_in_the_sample():
    """If a custom font encoding turns '1800W' into spaced glyphs, no regex
    matches and the result looks identical to a manual that says nothing. The
    raw sample is what tells them apart."""
    pages = pages_of(make_pdf(["Rated power 1 8 0 0 W supply"]))
    acc, _ = readings_from(pages, "u")
    assert acc == [], "spaced glyphs must not be parsed into a rating"
    _, _, sample, _ = electrical_context(pages)
    assert "1 8 0 0 W" in sample["text"], "the evidence of mangling must survive"


def test_the_diagnostic_never_becomes_a_reading():
    """Context is recorded beside readings, never promoted into one."""
    pages = pages_of(make_pdf(["Electrical rating information follows on page 2"]))
    acc, rej = readings_from(pages, "u")
    assert acc == [] and rej == []
    spans, _, _, _ = electrical_context(pages)
    assert spans and all("kw" not in s for s in spans[0])


def test_per_panel_wattages_are_rejected_not_summed():
    """The real run's only findings: 200W bench, 125W floor, 300W wall emitters
    on page 36 of the Monaco manual. Each is a real, precise number and none is
    the unit's rating. The band refused all three; summing them would have been
    derivation, which this project forbids."""
    pages = pages_of(make_pdf([
        "As the bench heat emitter and floor heat emitter (200W/125W each) are of "
        "much less wattage than the wall heat emitters (300W each), they will not "
        "get nearly as hot."]))
    acc, rej = readings_from(pages, "u")
    assert acc == [], "a per-emitter wattage must never become the unit's rating"
    assert {round(r["kw"], 3) for r in rej} == {0.2, 0.125, 0.3}
    assert all("plausibility band" in r["rejected_because"] for r in rej)


# ── the deliberate sample, and checking against what we already hold ──────────

from scripts.extract_manual_specs import compare_to_our_value, load_sample  # noqa: E402


def test_the_sample_is_five_eligible_handles_with_reasons():
    sample = load_sample()
    assert len(sample) == 5
    census = {r["handle"] for r in
              json.loads((ROOT / "data" / "own-page-census.json").read_text())["rows"]}
    for handle, meta in sample:
        assert handle in census, f"{handle} is not an active sauna SKU"
        assert meta["why"].strip(), f"{handle} has no recorded reason"
        assert meta["manual_candidates"] > 0, f"{handle} has no manual to read"


def test_the_sample_spreads_across_vendors_not_yet_read():
    """Run 1 covered Dundalk, Dynamic Saunas, Maxxus and Golden Designs. None of
    them may appear again, or the sample answers the same question twice."""
    already = {"Dundalk Leisurecraft", "Dynamic Saunas", "Maxxus", "Golden Designs Inc"}
    vendors = {meta["vendor"] for _, meta in load_sample()}
    assert not (vendors & already), f"re-sampling a vendor run 1 already read: {vendors & already}"
    assert len(vendors) >= 2, vendors


def test_the_sample_includes_traditional_electric_not_only_infrared():
    """A traditional electric heater is the case most likely to carry a stated
    kW. A sample of only infrared cabins would repeat run 1's blind spot."""
    types = [meta["type"] for _, meta in load_sample()]
    assert sum(1 for t in types if "traditional" in t) >= 3, types


def test_most_of_the_sample_has_a_known_kw_to_check_against():
    known = [meta["our_metafield_kw"] for _, meta in load_sample()
             if meta["our_metafield_kw"] is not None]
    assert len(known) >= 3, "a blind sample cannot corroborate anything"
    assert len(set(known)) == len(known), "duplicate magnitudes test less"


def test_no_externally_heated_or_wood_fired_sku_is_sampled():
    """SaunaLife ships every cabin without a heater and G3 offers a wood-fired
    option, so none of its 8 manual-bearing SKUs may be read. The reason is
    recorded in the sample file so the exclusion cannot be quietly undone."""
    doc = json.loads((ROOT / "data" / "manual-sample.json").read_text())
    excluded = doc["vendors_that_could_not_be_sampled"]
    assert "SaunaLife" in excluded and "heater" in excluded["SaunaLife"]
    assert "Medical Saunas" in excluded
    assert not any(meta["vendor"] in excluded for _, meta in load_sample())


@pytest.mark.parametrize("our,readings,want", [
    (9.0, [{"kw": 9.0, "page": 1, "span": "s", "tier": "spec_plate"}], "AGREES"),
    (9.0, [{"kw": 6.0, "page": 1, "span": "s", "tier": "body_copy"}], "DISAGREES"),
    (9.0, [], "NO_MANUAL_READING"),
    (None, [], "NO_VALUE_OF_OURS"),
    (None, [{"kw": 4.5, "page": 2, "span": "s", "tier": "spec_plate"}], "NO_VALUE_OF_OURS"),
])
def test_comparison_records_and_never_resolves(our, readings, want):
    c = compare_to_our_value(our, readings)
    assert c["verdict"] == want
    if want == "DISAGREES":
        assert c["our_kw"] == 9.0 and c["manual_kw"] == 6.0 and c["manual_span"] == "s"


def test_a_disagreement_is_never_averaged_or_overwritten():
    c = compare_to_our_value(9.0, [{"kw": 6.0, "page": 1, "span": "s", "tier": "body_copy"}])
    assert 7.5 not in c.values(), "the two values must never be averaged"
    assert c["our_kw"] == 9.0, "our value must survive the comparison intact"
