"""Round 3 Part B: one regression test per matcher error the snippet audit found, and one per
decision (D-1 exterior shapes, D-2 page metadata, D-3 heater options, D-4 headless, D-5 fixes)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_build as vb  # noqa: E402
import verified_pages as vp  # noqa: E402


class Seg:
    def __init__(self, text, loc="product body_html", kind="data", method="static"):
        self.segments, self.skus, self.kind, self.option_note = [(loc, text)], [], kind, None
        self.method = method


class P:
    def __init__(self, options=(), handle="x"):
        self.options, self.handle = list(options), handle


def vals(out):
    return [v for v, _, _ in out]


def ext(text):
    return [v for v in vals(vb.ex_exterior(Seg(text))) if v != "depends on the buyer's choice"]


# ------------------------------------------------------------- D-5(c) inches --

@pytest.mark.parametrize("s,inches", [
    ("51 3/4", 51.75), ("86-5/8", 86.625), ("75 ⅜", 75.375), ("80⁵⁄₁₆", 80.3125), ("77", 77.0), ("50.9", 50.9)])
def test_fractions_and_unicode_fractions_are_inches(s, inches):
    assert vb.to_inches(s) == pytest.approx(inches)


# --------------------------------------------------------- D-5(a) Lumber Type --

def test_lumber_type_does_not_make_heat_type_option_dependent():
    """Round 1's bare `type` matched 'Lumber Type' and withheld every heat type on the product."""
    assert not vb.option_dependent(P([{"name": "Lumber Type", "values": ["Rustic Red Cedar", "Onyx"]}]), "type")


def test_a_type_option_naming_two_heat_types_is_option_dependent():
    o = [{"name": "Lumber Type", "values": ["Traditional & Rustic Red Cedar", "Infrared (Hybrid) & Rustic Red Cedar"]}]
    assert vb.option_dependent(P(o), "type")


# ------------------------------------------------------ D-5(b) escaped links --

def test_escaped_pdf_links_are_unescaped_and_untrailed():
    html = r'{"u":"https:\/\/cdn.shopify.com\/s\/files\/1\/0901\/6334\/7735\/files\/Manual.pdf?v=1\""}'
    src = {"manufacturer_domains": ["heavenlyheatsaunas.com"], "pdf_hosts": ["cdn.shopify.com"],
           "_shop_prefix": "/s/files/1/0901/6334/7735/"}
    links = vb.page_pdf_links(html, "https://heavenlyheatsaunas.com/p", src)
    assert links == {"https://cdn.shopify.com/s/files/1/0901/6334/7735/files/Manual.pdf?v=1"}


def test_a_shopify_cdn_pdf_needs_the_shop_prefix_the_build_injects():
    """The lint once read the raw brand config, which has no `_shop_prefix`, and so refused the
    Sun Home spec sheets the build had used. Without the prefix no CDN PDF is an origin PDF."""
    u = "https://cdn.shopify.com/s/files/1/0901/6334/7735/files/Manual.pdf"
    raw = {"manufacturer_domains": ["x.test"], "pdf_hosts": ["cdn.shopify.com"]}
    assert not vb.origin_pdf(u, raw)
    assert vb.origin_pdf(u, dict(raw, _shop_prefix="/s/files/1/0901/6334/7735/"))
    assert not vb.origin_pdf(u, dict(raw, _shop_prefix="/s/files/1/9999/"))


# ------------------------------------------------------- series name for docs --

def test_trademark_marks_do_not_fold_into_the_series_name():
    name = vb.series_name("Eclipse™ Red Light Full Spectrum Sauna")
    assert name.startswith("eclipse") and "tm" not in name.split()[0]


# ---------------------------------------------------------- D-1 exterior forms --

def test_rectangular_exterior_with_fractions():
    (shape, parts, q), = ext("Exterior Dimensions Width: 51 3/4″ Depth: 47 3/4″ Height: 77″")
    assert shape == "rectangular" and [p[1] for p in parts] == pytest.approx([51.75, 47.75, 77.0]) and not q


def test_exterior_values_render_exactly_as_stated():
    (shape, parts, _), = ext("Exterior dimensions: 69⅞″W x 47⅛″D x 77⅝″H")
    assert [p[2] for p in parts] == ["69⅞", "47⅛", "77⅝"]
    assert vp.exterior_text(vb.ext_value(ext("Exterior dimensions: 69⅞″W x 47⅛″D x 77⅝″H")[0])).count("⅞″") == 1


@pytest.mark.parametrize("text", [
    "Exterior Bench Dimensions: 16″W x 13″L x 25″H",
    "Assembled Weight: 900 lbs Crate Dimensions: 88\" x 44\" x 41\"",
    "Exterior Door Dimensions: 24″W x 72″H x 2″D",
])
def test_a_part_or_crate_size_is_not_the_exterior(text):
    assert ext(text) == []


def test_a_roof_size_carries_its_qualifier():
    out = ext("Exterior Dimensions Roof: 83 1/2″ L x 66 1/4″ W x 82 1/2″ H")
    assert out and out[0][2] == "roof"
    assert vp.exterior_text(vb.ext_value(out[0])).startswith("At the roof: ")


def test_a_barrel_needs_diameter_and_length():
    out = ext('Exterior dimensions - 63"L x 91"Diameter Interior dimensions - 55"L x 83"Diameter')
    assert out and out[0][0] == "barrel" and {p[0].lower() for p in out[0][1]} == {"length", "diameter"}


def test_a_barrel_without_its_length_is_not_an_exterior():
    assert ext('Exterior dimensions - 91"Diameter') == []


def test_a_corner_unit_needs_every_wall_and_the_height():
    out = ext("Exterior Dimensions Back walls: 71 1/4″ Side walls: 38 1/4″ Front wall: 47 1/2″ Height: 77″")
    assert out and out[0][0] == "corner"


def test_two_axis_exterior_is_not_complete():
    assert ext("Exterior Dimensions: 69″W x 47″D") == []


# ---------------------------------------------------------------- capacity --

@pytest.mark.parametrize("text,n,upto", [
    ("The Sanctuary 2 infrared sauna can fit up to 2 adults", 2, True),
    ("Sauna Size CT Luna Comfortably Seats 4 People", 4, False),
    ("accommodates up to four people", 4, True),
])
def test_capacity_phrases(text, n, upto):
    out = vb.ex_capacity(Seg(text))
    assert out and out[0][0] == (n, n) and (vb.UP_TO_MARK in out[0][1]) == upto


def test_a_temperature_up_to_is_not_capacity():
    assert vb.ex_capacity(Seg("infrared saunas can reach up to 90.5 degrees Celsius")) == []


# ------------------------------------------------ D-2 metadata vs the page --

class D:
    def __init__(self, kind="data", method="static"):
        self.kind, self.method = kind, method


def test_metadata_is_a_fallback_only():
    page, meta = D(), D("meta")
    out = vb.resolve_fallbacks("capacity", [("listed", page, [((4, 4), "p", "s")]), ("listed", meta, [((4, 4), "m", "s")])])
    assert [sts for _, d, sts in out if d is meta] == [[]]


def test_nested_metadata_does_not_contradict_the_page():
    page, meta = D(), D("meta")
    out = vb.resolve_fallbacks("capacity", [("listed", page, [((2, 4), "p", "s")]), ("listed", meta, [((4, 4), "m", "s")])])
    assert sum(len(sts) for _, _, sts in out) == 1


def test_contradicting_metadata_is_kept_beside_the_page_so_capacity_is_unsettled():
    page, meta = D(), D("meta")
    out = vb.resolve_fallbacks("capacity", [("listed", page, [((4, 4), "p", "s")]), ("listed", meta, [((5, 5), "m", "s")])])
    assert sorted(v for _, _, sts in out for v, _, _ in sts) == [(4, 4), (5, 5)]


def test_metadata_speaks_when_the_page_is_silent():
    page, meta = D(), D("meta")
    out = vb.resolve_fallbacks("capacity", [("listed", page, []), ("listed", meta, [((5, 5), "m", "s")])])
    assert [v for _, _, sts in out for v, _, _ in sts] == [(5, 5)]


# ------------------------------------------------------------ D-4 headless --

def test_a_headless_render_never_displaces_the_plain_page():
    page, hl = D(), D("html", "headless")
    out = vb.resolve_fallbacks("heater_kw", [("listed", page, [(6.0, "p", "s")]), ("listed", hl, [(8.0, "h", "s")])])
    assert [v for _, _, sts in out for v, _, _ in sts] == [6.0]


def test_the_description_rule_does_not_read_a_headless_configurator():
    doc = Seg("Includes a Harvia KIP electric heater and a wood-burning stove option.", loc="main content",
              kind="html", method="headless")
    assert vb.ex_heat_type_description(doc) == []


# ---------------------------------------------------------------- amperage --

@pytest.mark.parametrize("text", [
    "A standard 15 amp household outlet is not sufficient",
    "Do not use a 15 amp extension cord",
    "plugs into a 15 amp standard household outlet",
])
def test_negations_prohibitions_and_household_outlets_are_not_the_units_amperage(text):
    assert vb.ex_amps(Seg(text)) == []


def test_a_draw_is_still_a_stated_amperage():
    """Reverted in Part B: skipping draws flipped the Round 1 assertion. Draw beside circuit is ambiguous."""
    assert 23.5 in vals(vb.ex_amps(Seg("RATED ELECTRICAL 120V / 2,820W / 23.5A")))


def test_a_circuit_amperage_is_still_read():
    assert 20.0 in vals(vb.ex_amps(Seg("Hardware : 120V, 20 amp dedicated outlet")))


# ---------------------------------------------------------------- GFCI --

def test_a_conditional_gfci_sentence_is_not_a_requirement():
    assert vb.ex_gfci(Seg("Where your local electrical code requires GFCI protection for this circuit, ask your electrician")) == []
    assert vb.ex_gfci(Seg("GFCI protection is required.")) != []


# ------------------------------------------------------------- D-3 heaters --

def test_heater_choices_from_the_upgrade_sentence():
    doc = Seg("What's Included: 6kW Harvia KIP heater, with upgrades available: 8kW Harvia KIP, 9kW Harvia Virta")
    items, _, d, _, n = vb.heater_items(P(), [doc])
    assert n == 3 and d is doc and vb.heater_items_heat(items) == "traditional"


def test_heater_choices_from_a_configurator_exclude_no_heater():
    doc = Seg("Heater Options * Most common 6 KW Electric Heater Wood Heater No Heater Next", kind="html")
    items, _, _, _, n = vb.heater_items(P(), [doc])
    assert n == 3 and "no heater" not in items and vb.heater_items_heat(items) == "traditional"


def test_one_infrared_option_withholds_heat_type():
    assert vb.heater_items_heat(["6kW Harvia KIP electric heater", "infrared heater panel"]) is None


def test_a_promotion_is_not_a_heater_choice():
    assert vb.heater_items(P(), [Seg("Choose a free heater upgrade or shipping on us")]) is None


# ------------------------------------------------------------------ wood --

def test_a_generic_wood_name_does_not_merge_two_different_woods():
    assert vb.woods_all_nest({"cedar", "red cedar", "canadian red cedar"})
    assert not vb.woods_all_nest({"cedar", "red cedar", "white cedar"})


# ------------------------------------------------------------ page wording --

def fld(v, snippet=""):
    return {"value": v, "grade": "listed", "evidence": {"snippet": snippet}}


def test_a_stated_draw_is_never_called_a_circuit():
    f = fld(13.9, "Electrical Components 240 Volts 3,330 Watts 13.9 Amps Plugs into a 240V outlet")
    assert not vp.amperage_is_circuit(f)


@pytest.mark.parametrize("snippet", [
    "REQUIRES 240V/30AMP DEDICATED CIRCUIT/ RECEPTACLE REQUIRED",
    "Hardware : 120V, 20 amp dedicated outlet",
])
def test_a_circuit_amperage_keeps_circuit_wording(snippet):
    v = 30 if "30" in snippet else 20
    assert vp.amperage_is_circuit(fld(v, snippet))


@pytest.mark.parametrize("word,art", [("infrared", "an"), ("indoor", "an"), ("8-person", "an"), ("11-person", "an"),
                                      ("traditional", "a"), ("4-person", "a"), ("1-person", "a"), ("6", "a")])
def test_articles(word, art):
    assert vp.article(word) == art


# ------------------------------------------------------ option-row collapse --

def test_an_all_option_dependent_record_renders_one_cited_electrical_row():
    """Shape, not literals: every record whose electrical values all depend on the heater renders
    ONE row naming the option, cited, and never six identical rows."""
    keys = ("circuits_required", "supply_voltage", "stated_amperage", "connection_type", "circuit_requirement", "heater_kw")
    hits = [r for r in vp.load_dataset()["records"] if vp.option_dependence(r) and not r["electrical"]["circuits"]
            and not any(vp.ok(r["electrical"][k]) for k in keys)]
    assert hits, "no option-dependent record to exercise"
    for r in hits:
        rows = vp.electrical_rows(r)
        assert len(rows) == 1 and rows[0]["field"] == "electrical.option_dependence" and rows[0]["state"] == "option"
        assert r["electrical"]["option_dependence"]["source_url"] and r["electrical"]["option_dependence"]["evidence"]["snippet"]


def test_a_metric_twin_after_each_axis_does_not_hide_the_exterior():
    out = ext('Dimensions: 91.3"W (231.9 cm) x 62.8"D (159.5 cm) x 84.7"H (215.1 cm) '
              'Exterior Dimensions: 95.3"W (242.1 cm) x 86.6"D (220 cm) x 92.1"H (233.9 cm) Specifications')
    assert len(out) == 1 and [p[1] for p in out[0][1]] == pytest.approx([95.3, 86.6, 92.1])
