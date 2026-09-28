"""Round 3 Part A: the gap classifier. One test per error the snippet audit found, plus the
honesty rule that a fetch failure is never NOT_STATED."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_build as vb  # noqa: E402
import verified_gaps as vg  # noqa: E402


def src(text, what="page", method="static", status=200, url="https://m.test/p"):
    return (what, url, method, status, text)


def cls(field, *sources, option=None):
    return vg.classify_field(field, option, list(sources), "https://m.test/p")


# ---------------------------------------------------------- false positives --

@pytest.mark.parametrize("field,text", [
    ("capacity", "infrared saunas can reach up to 90.5 degrees Celsius"),
    ("exterior dimensions", "Large Treatment Area (112 x 37 x 7.2 cm) for the mat"),
    ("exterior dimensions", "Exterior Bench Dimensions: 16″W x 13″L x 25″H"),
    ("exterior dimensions", "Canopy Porch Size: 69 ¼″W x 14 ⅝″D x 69 ¼″H"),
    ("exterior dimensions", "Size & Weight Shipping Dimensions: 88\" x 44\" x 41\" Weight: 1544 lbs"),
    ("exterior dimensions", "Each model's exterior dimensions are on its Spec Sheet. 03 Stay Connected"),
    ("electrical", "Details list DET 10a x3 Article. x1 DET 3 A DET 6"),
    ("electrical", "t r i m 1 5 A o n t h e e n d"),
    ("heat type", "the wood was treated with pressurized heat and steam so it lasts longer"),
])
def test_audit_false_positives_are_not_statements(field, text):
    assert [h for h in vg.find(field, text) if h[0] < 2] == [], text


@pytest.mark.parametrize("field,text", [
    ("capacity", "The Sanctuary 2 infrared sauna can fit up to 2 adults"),
    ("capacity", "Sauna Size CT Luna Comfortably Seats 4 People"),
    ("exterior dimensions", "Exterior dimensions: 69⅞″W x 47⅛″D x 77⅝″H"),
    ("exterior dimensions", "Exterior Dimensions Width: 51 3/4″ Depth: 47 3/4″ Height: 77″"),
    ("exterior dimensions", "ASSEMBLED EXTERIOR · W × D × H 50.9″ × 45.9″ × 77.7″"),
    ("exterior dimensions", "Exterior Dimensions 71” L x 72 ¾” W x 76 ½” H"),
    ("exterior dimensions", "Spacious Design 37.4\" W × 37.4\" D × 75\" H."),
    ("electrical", "Hardware : 120V, 20 amp dedicated outlet"),
])
def test_real_statements_are_found(field, text):
    assert any(h[0] < 2 for h in vg.find(field, text)), text


def test_unicode_fractions_are_inches():
    assert any(h[0] < 2 for h in vg.find("exterior dimensions", "Assembled size: 78″W x 94″D x 75 ⅜″H"))


# ------------------------------------------------------------------ options --

def test_a_promotion_is_not_a_heater_option():
    c = cls("electrical", src("Choose a free heater upgrade or shipping on us"))
    assert c["class"] != "OPTION_DEPENDENT"


def test_a_configurator_heater_choice_is_an_option():
    c = cls("electrical", src("Heater Options * Most common 6 KW Electric Heater Wood Heater No Heater Next"))
    assert c["class"] == "OPTION_DEPENDENT"


def test_an_included_heater_with_upgrades_is_option_dependent():
    c = cls("electrical", src("What's Included: 6kW Harvia KIP heater, with upgrades available: 8kW Harvia KIP"))
    assert c["class"] == "OPTION_DEPENDENT"


class P:
    def __init__(self, options):
        self.options = options


def test_lumber_type_is_not_a_heat_type_option():
    """Round 1's `\\btype\\b` matched this and withheld heat types; the diagnosis must not."""
    assert vg.heat_option(P([{"name": "Lumber Type", "values": ["Rustic Red Cedar", "Onyx"]}])) is None


def test_a_lumber_option_that_carries_heat_types_is_a_heat_option():
    o = [{"name": "Lumber Type", "values": ["Traditional & Rustic Red Cedar", "Infrared (Hybrid) & Rustic Red Cedar"]}]
    assert vg.heat_option(P(o)) is not None


# --------------------------------------------------------- honesty classes --

def test_a_fetch_failure_is_never_not_stated():
    c = cls("exterior dimensions", src("nothing here"), src("", status=503))
    assert c["class"] == "NOT_VERIFIED"


def test_a_named_section_without_figures_is_not_verified_not_not_stated():
    c = cls("exterior dimensions", src("Sizing & Dimensions Installation Guide Financing Details"))
    assert c["class"] == "NOT_VERIFIED"


def test_a_size_switcher_in_link_text_is_weak():
    text = vg.main_text('<p>Sanctuary 1</p><a href="/s1">1 Person</a><a href="/s2">2 Person</a>')
    c = cls("capacity", src(text))
    assert c["class"] == "NOT_VERIFIED" and c["strength"] == "weak"


def test_not_stated_needs_every_source_read_and_nothing_named():
    assert cls("capacity", src("A dome you lie in. Plugs into a wall outlet."))["class"] == "NOT_STATED"


def test_js_only_is_reported_only_when_the_static_page_lacks_it():
    c = cls("capacity", src("specs load here"), src("Comfortably Seats 4 People", method="headless"))
    assert c["class"] == "JS_ONLY"


# ------------------------------------------------------------ fetch fixes --

def test_escaped_pdf_links_are_unescaped():
    html = r'{"u":"https:\/\/cdn.shopify.com\/s\/files\/1\/0901\/6334\/7735\/files\/Manual.pdf?v=1\""}'
    src_cfg = {"manufacturer_domains": ["heavenlyheatsaunas.com"], "pdf_hosts": ["cdn.shopify.com/s/files/1/0901/6334/7735/"]}
    links = vg.pdf_links_of(vb, html, "https://heavenlyheatsaunas.com/p", src_cfg)
    assert all(not l.endswith(('\\', '"')) for l in links)


def test_a_short_read_is_recorded_as_our_truncation(monkeypatch):
    import verified_fetch as vf

    class R:
        status = 200
        headers = {"Content-Type": "application/pdf", "Content-Length": "100"}

        def read(self, n):
            return b"%PDF-short"

        def geturl(self):
            return "https://x.test/a.pdf"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(vf.urllib.request, "urlopen", lambda *a, **k: R())
    monkeypatch.setattr(vf, "polite_wait", lambda host: None)
    status, _, body, _ = vf.raw_get("https://x.test/a.pdf")
    assert status == "TRUNCATED_TRANSFER" and body == b""


def test_a_headless_render_obeys_robots_before_opening_a_browser(monkeypatch, tmp_path):
    import urllib.robotparser
    import verified_fetch as vf
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /products/"])
    monkeypatch.setattr(vf, "robots_for", lambda host: ("ok", rp))
    monkeypatch.setattr(vf, "save_manifest", lambda *a, **k: None)

    class NoBrowser:
        def new_context(self, **k):
            raise AssertionError("a disallowed page must never be rendered")

    ent = vf.fetch_rendered("https://m.test/products/x", {"entries": {}}, NoBrowser())
    assert ent["status"] == "ROBOTS_DISALLOWED" and ent["method"] == "headless"


def test_a_multi_model_comparison_sheet_does_not_make_a_record_option_dependent():
    sheet = src("6.0kW KIP 6.0kW KIP 4.5kW KIP 8.0kW KIP Heater Electric Requirements 240V , 30-amp", what="linked document")
    assert cls("electrical", src("Harmony infrared sauna"), sheet)["class"] != "OPTION_DEPENDENT"


def test_a_drawing_annotation_without_axes_is_not_an_exterior_size():
    doc = src("OVERALL DIMENSIONS 32102030 2030 13’ 3-1/4” 10’ 3-1/4” 8’ 10-3/4”", what="linked document")
    assert cls("exterior dimensions", src("A cabin sauna"), doc)["class"] != "STATED_MISSED"
