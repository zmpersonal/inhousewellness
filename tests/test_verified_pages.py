"""Round 2 Part A: the page threshold, the handle rule and the navigation map."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import verified_inh_map as vm  # noqa: E402
import verified_pages as vp  # noqa: E402
import verified_titles as vt  # noqa: E402


def F(value, grade="listed"):
    return {"value": value, "grade": grade}


def rec(**over):
    r = {"inh_id": "sauna/x/m1", "status": "published",
         "identity": {"brand": F("Maxxus"), "model_name": F("Seattle Far IR Sauna"), "model_number": F("MX-J206-01"),
                      "display_title": "Maxxus Seattle Far IR Sauna, 2 Person"},
         "heat_type": F("infrared"), "capacity_min": F(2), "capacity_max": F(2),
         "dimensions": {"assembled": {"width_in": F(47), "depth_in": F(39), "height_in": F(75)},
                        "exterior": F(None, "not_verified")},   # Round 3: required by the schema
         "electrical": {"supply_voltage": F("120V"), "stated_amperage": F(None, "not_verified"),
                        "circuits": [], "heater_kw": F(None, "not_verified")}}
    for k, v in over.items():
        r[k] = v
    return r


def meets(r):
    return next(vp.threshold({"records": [r]}))[1]


def test_a_complete_record_meets_the_threshold():
    assert meets(rec())["meets"]


def test_a_missing_axis_fails_the_dimension_requirement():
    r = rec()
    r["dimensions"]["assembled"]["height_in"] = F(None, "not_verified")
    assert meets(r)["missing"] == ["exterior dimensions"]


def test_claimed_is_not_verified():
    assert meets(rec(heat_type=F("infrared", "claimed")))["missing"] == ["heat type"]


def test_a_labelled_circuit_alone_satisfies_electrical():
    r = rec()
    r["electrical"]["supply_voltage"] = F(None, "not_verified")
    r["electrical"]["circuits"] = [{"purpose": F("Stove")}]
    assert meets(r)["meets"]


def test_a_backlog_record_never_gets_a_page():
    assert list(vp.threshold({"records": [rec(status="backlog")]})) == []


def test_a_range_is_labelled_as_a_range():
    assert meets(rec(capacity_min=F(5), capacity_max=F(6)))["capacity_label"] == "5–6"


# ------------------------------------------------------------------ handles

def test_handle_is_lowercase_without_marketing_or_year():
    r = rec()
    r["identity"]["model_name"] = F("Updated 2026 Sundsvall Traditional Sauna")
    (o,) = vt.propose([(r, "2")])
    assert o["handle"] == "maxxus-sundsvall-2-person"
    assert o["handle"] == o["handle"].lower()


def test_colliding_handles_take_the_manufacturer_edition_token_not_a_counter():
    a, b = rec(), rec()
    b["inh_id"] = "sauna/x/m2"
    b["identity"]["model_number"] = F("MX-J206-01 ZF")
    out = vt.propose([(a, "2"), (b, "2")])
    assert sorted(o["handle"] for o in out) == ["maxxus-seattle-2-person", "maxxus-seattle-zf-2-person"]


def test_an_overlong_handle_is_flagged_not_truncated():
    r = rec()
    r["identity"]["model_name"] = F("Reserve Edition Full Spectrum with Himalayan Salt Bar and Extra Words")
    (o,) = vt.propose([(r, "1")])
    assert len(o["handle"]) > vt.HANDLE_MAX
    assert any("characters" in f for f in o["flags"])


# ---------------------------------------------------------- navigation map

def snap(*products):
    return {"pulled_at": "t", "products": [dict({"status": "ACTIVE", "title": p[0], "collections": []},
                                                handle=p[0], vendor=p[1], skus=p[2]) for p in products]}


def test_an_exact_sku_and_vendor_map():
    nav = vm.build(snap(("maxxus-seattle", "Maxxus", ["MX-J206-01"])), [rec()])
    assert nav["mapped"]["sauna/x/m1"]["product_handle"] == "maxxus-seattle"


def test_a_sku_that_extends_the_model_number_is_reported_not_mapped():
    nav = vm.build(snap(("maxxus-seattle-ced", "Maxxus", ["MX-J206-01 CED"])), [rec()])
    assert nav["mapped"] == {}
    assert "extends" in nav["unmapped"]["sauna/x/m1"]


def test_two_products_with_one_sku_map_nobody():
    nav = vm.build(snap(("a", "Maxxus", ["MX-J206-01"]), ("b", "Maxxus", ["MX-J206-01"])), [rec()])
    assert nav["mapped"] == {} and nav["unmapped"]["sauna/x/m1"].startswith("ambiguous")


def test_another_brands_sku_does_not_map():
    nav = vm.build(snap(("x", "Golden Designs Inc", ["MX-J206-01"])), [rec()])
    assert nav["mapped"] == {}


def test_the_map_stores_no_price():
    nav = vm.build(snap(("maxxus-seattle", "Maxxus", ["MX-J206-01"])), [rec()])
    assert "price" not in json.dumps(nav).lower()
