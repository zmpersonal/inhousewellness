"""The manual extractor, exercised against a real PDF built here.

No manual is reachable from a session: every one is a Google Drive embed and
drive.google.com answers 403 on CONNECT from the agent proxy. So the PDF path is
proven against a text-layer PDF constructed in this file — page numbers, spans,
both guards and the tiering — rather than against a live file nobody can see.
"""
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
