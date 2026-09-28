"""INH Verified — Round 1 gates.

Every test here runs against a PINNED input or a constructed fixture, never
against re-fetched origin data (CLAUDE.md: never assert a literal value from
refreshed external data). The lead snapshot is pinned by filename and sha256.
"""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import verified_build as vb  # noqa: E402
import verified_import as vi  # noqa: E402

SCHEMA = json.loads((ROOT / "data/verified/schema/inh-verified.schema.json").read_text())
FIELD = Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": "#/$defs/field"})
LEADS = ROOT / "data/verified/internal/leads/infinite-sauna-2026-09-21.json"
LEADS_SHA = "7b3c609cd1080e3d65003af2bc90618e075d2c8fa53437227f51cb4239f3d9f5"


def field(**kw):
    base = {"value": 240, "unit": "V", "grade": "listed", "source_url": "https://goldendesigninc.com/products/x",
            "source_type": "manufacturer", "observed_at": "2026-09-27", "note": None,
            "evidence": {"fetched_at": "2026-09-27T00:00:00+00:00", "content_sha256": "0" * 64,
                         "locator": "body", "snippet": "240V"}}
    base.update(kw)
    return base


def errors(inst):
    return list(FIELD.iter_errors(inst))


# ---------------------------------------------------------------- schema --

def test_the_lead_snapshot_is_the_pinned_one():
    assert hashlib.sha256(LEADS.read_bytes()).hexdigest() == LEADS_SHA


def test_a_valid_listed_field_passes():
    assert errors(field()) == []


def test_inhousewellness_is_never_a_source_url():
    for u in ("https://inhousewellness.com/products/x", "https://www.inhousewellness.com/pages/y"):
        assert errors(field(source_url=u)), u


def test_a_lookalike_domain_is_not_caught_by_the_inh_rule():
    assert errors(field(source_url="https://notinhousewellness.com/x")) == []


def test_listed_requires_a_manufacturer_or_distributor_source_type():
    assert errors(field(source_type="manufacturer_manual"))
    assert errors(field(source_type="none"))


def test_documented_requires_a_manual_or_spec_sheet():
    assert errors(field(grade="documented", source_type="manufacturer"))
    assert errors(field(grade="documented", source_type="manufacturer_manual")) == []


def test_a_graded_value_without_evidence_fails():
    f = field(); del f["evidence"]
    assert errors(f)


def test_not_verified_carries_no_value():
    assert errors(field(grade="not_verified", source_type="none"))
    assert errors({"value": None, "unit": None, "grade": "not_verified", "source_url": None,
                   "source_type": "none", "observed_at": None, "note": None}) == []


def test_no_shared_circuit_value_exists():
    circ = SCHEMA["properties"]["electrical"]["properties"]["circuit_requirement"]
    v = Draft202012Validator({"$defs": SCHEMA["$defs"], **circ})
    assert list(v.iter_errors(field(value="Shared circuit OK", unit=None)))
    assert not list(v.iter_errors(field(value="Dedicated required", unit=None)))


# ------------------------------------------------------------- deciding --

class D:  # a minimal Doc
    def __init__(self, tier="listed"):
        self.tier, self.source_url, self.fetched_at = tier, "https://m.example/p", "2026-09-27T00:00:00+00:00"


def test_decide_confirmed_changed_ambiguous_notfound():
    d = D()
    assert vb.decide([("listed", d, [(8.0, "b", "8 kW")])], 8.0)[0] == "confirmed"
    assert vb.decide([("listed", d, [(6.0, "b", "6 kW")])], 8.0)[0] == "changed"
    assert vb.decide([("listed", d, [(6.0, "b", "6 kW"), (8.0, "b", "8 kW")])], 8.0)[0] == "ambiguous"
    assert vb.decide([], 8.0)[0] == "not_found"
    assert vb.decide([("listed", d, [(6.0, "b", "6 kW")])], None)[0] == "source_only"


def test_a_lead_value_is_never_carried_over():
    outcome, chosen, _ = vb.decide([], 8.0)
    assert chosen is None and outcome == "not_found"


def test_the_higher_tier_wins_and_the_disagreement_is_logged():
    man, page = D("documented"), D("listed")
    out, chosen, notes = vb.decide([("documented", man, [(6.0, "p3", "6kW")]),
                                    ("listed", page, [(8.0, "b", "8 kW")])], 8.0)
    assert chosen[0] == "documented" and chosen[2][0] == 6.0 and out == "changed"
    assert [n[0] for n in notes] == ["tier_disagreement"]


# ------------------------------------------------------------ extractors --

class Seg:
    def __init__(self, text, loc="product body_html", skus=(), kind="data"):
        self.segments, self.skus, self.kind, self.option_note = [(loc, text)], list(skus), kind, None


def test_a_negated_statement_is_not_a_statement():
    assert vb.ex_gfci(Seg("Do NOT use a G.F.I breaker. GFCI is not required.")) == []
    assert vb.ex_circuit(Seg("This unit does not require a dedicated circuit.")) == []
    assert vb.ex_circuit(Seg("A dedicated circuit is not required.")) == []
    assert vb.ex_circuit(Seg("Requires a dedicated 30 amp circuit."))[0][0] == "Dedicated required"


def test_a_recommended_heater_is_not_a_rating():
    assert vb.ex_kw(Seg("An 8 kW electric heater is recommended for optimal performance.")) == []
    assert [s[0] for s in vb.ex_kw(Seg("Harvia 8.0 kW heater included."))] == [8.0]


def test_breaker_amps_needs_the_word_breaker():
    s = Seg("Electrical Service: 240V / 30AMP (Please consult a certified electrician.)")
    assert vb.ex_amps(s, breaker=True) == []
    assert [x[0] for x in vb.ex_amps(s)] == [30.0]
    assert [x[0] for x in vb.ex_amps(Seg("Install on a 40A breaker."), breaker=True)] == [40.0]


def test_dimensions_publish_only_when_the_source_labels_the_order():
    assert vb.ex_dims_assembled(Seg("Exterior dimensions (WDH): 87″ x 75″ x 87″"))[0][0] == (87.0, 75.0, 87.0)
    assert vb.ex_dims_assembled(Seg("Exterior Dimensions : 81” W x 63” D x 85” H"))[0][0] == (81.0, 63.0, 85.0)
    assert vb.ex_dims_assembled(Seg("Exterior dimensions: 84\" x 60\" x 84\"")) == []


def test_capacity_range_and_label():
    assert vb.ex_capacity(Seg("Kuuma 4-6 Person Classic Barrel Sauna"))[0][0] == (4, 6)
    assert vb.ex_capacity(Seg("Max Capacity: 3 persons"))[0][0] == (3, 3)


def test_voltage_multi_statement_is_ambiguous_not_published():
    sts = vb.ex_voltage(Seg("Controls 120V; heater 240V"))
    assert vb.decide([("listed", D(), sts)], None)[0] == "ambiguous"


def test_salus_panels_split_on_titles():
    h = ('<h2 class="disclosure__title x">Specifications</h2><ul><li><strong>Max Capacity:</strong> 3 persons</li></ul>'
         '<h2 class="disclosure__title x">Electrical Requirements</h2><p>8kw heaters require a 40 amp connection</p>')
    panels = dict(vb.salus_panels(h))
    assert "3 persons" in panels["Specifications"] and "40 amp" not in panels["Specifications"]
    assert vb.SPEC_PANEL_RX.search("Specifications") and not vb.SPEC_PANEL_RX.search("Electrical Requirements")


# ------------------------------------------------------------------ rules --

def _record(**over):
    nv = vb.nv
    rec = {
        "inh_id": "sauna/test/x", "status": "published", "withheld_reasons": [],
        "identity": {"brand": field(value="Test"), "model_number": nv(), "model_name": field(value="X"),
                     "configuration": nv(), "display_title": "Test X, 3 Person", "aliases": []},
        "heat_type": field(value="traditional", unit=None), "placement": nv(), "capacity_min": nv(), "capacity_max": nv(),
        "materials": {"wood_species": nv()}, "thermal": {"max_temp_f": nv()},
        "electrical": {k: nv() for k in ("supply_voltage", "heater_voltage", "connection_type", "circuit_requirement",
                                         "breaker_amps", "gfci", "heater_kw", "stated_amperage")},
        "infrared": {k: vb.na() for k in ("spectrum", "emf_claim", "red_light")},
        "_rule_inputs": {"text": "Traditional sauna with Harvia stove", "title": "X", "cap_ambiguous": False, "cap_statements": [], "size_option": None},
    }
    for k, v in over.items():
        rec["electrical"][k] = v
    return rec


def test_r1_fires_on_final_values():
    rec = _record(heater_kw=field(value=8.0, unit="kW"), supply_voltage=field(value="120V", unit=None),
                  stated_amperage=field(value=40.0, unit="A"))
    vb.apply_rules([rec])
    assert rec["status"] == "backlog" and rec["withheld_reasons"][0]["rule"] == "R1_ELECTRICAL"


def test_r1_passes_a_possible_configuration():
    rec = _record(heater_kw=field(value=8.0, unit="kW"), supply_voltage=field(value="240V", unit=None),
                  stated_amperage=field(value=40.0, unit="A"))
    vb.apply_rules([rec])
    assert rec["status"] == "published"


def test_r2_hybrid_without_both_systems_named():
    rec = _record(heater_kw=field(value=6.0, unit="kW"))
    rec["heat_type"] = field(value="hybrid", unit=None)
    rec["_rule_inputs"]["text"] = "Serenity Hybrid Indoor Sauna"
    vb.apply_rules([rec])
    assert any(w["rule"] == "R2_HYBRID" for w in rec["withheld_reasons"])


def test_r3_duplicate_titles_without_a_distinguishing_configuration():
    a, b = _record(heater_kw=field(value=6.0, unit="kW")), _record(heater_kw=field(value=6.0, unit="kW"))
    vb.apply_rules([a, b])
    assert all(any(w["rule"] == "R3_IDENTITY" for w in r["withheld_reasons"]) for r in (a, b))


def test_r3_resolved_by_a_source_stated_heater_package():
    a, b = _record(heater_kw=field(value=6.0, unit="kW")), _record(heater_kw=field(value=8.0, unit="kW"))
    vb.apply_rules([a, b])
    assert {a["identity"]["display_title"], b["identity"]["display_title"]} == {
        "Test X, 3 Person, 6 kW heater", "Test X, 3 Person, 8 kW heater"}


def test_r5_capacity_disagreement_in_the_source():
    rec = _record(heater_kw=field(value=6.0, unit="kW"))
    rec["_rule_inputs"].update(cap_ambiguous=True, cap_statements=[((4, 4), "t", "4 person"), ((3, 3), "b", "3 person")])
    vb.apply_rules([rec])
    assert any(w["rule"] == "R5_CAPACITY" for w in rec["withheld_reasons"])


def test_a_record_with_nothing_verified_is_backlog():
    rec = _record()
    rec["heat_type"] = vb.nv()
    vb.apply_rules([rec])
    assert rec["status"] == "backlog"


# ------------------------------------------------------------------- lint --

SOURCES = json.loads((ROOT / "data/verified/sources.json").read_text())


def _lint_msgs(records, conflicts=()):
    try:
        vb.lint(records, list(conflicts), SOURCES)
    except SystemExit as e:
        return str(e)
    return ""


def _gd_record():
    rec = _record(heater_kw=field(value=6.0, unit="kW"))
    rec["identity"]["brand"] = field(value="Golden Designs", unit=None)
    del rec["_rule_inputs"]
    return rec


def test_a_retailer_domain_not_on_the_allow_list_is_rejected():
    rec = _gd_record()
    rec["electrical"]["heater_kw"] = field(value=6.0, unit="kW", source_url="https://ampsrus.com/products/x")
    assert "ampsrus.com is not an origin host" in _lint_msgs([rec])


def test_the_manufacturers_own_domain_is_accepted_by_the_allow_list():
    assert "not an origin host" not in _lint_msgs([_gd_record()])


def test_the_banned_phrase_fails_the_lint():
    rec = _gd_record()
    rec["electrical"]["connection_type"] = vb.nv("Standard 120V outlet")
    assert "appears in the dataset" in _lint_msgs([rec])


def test_naming_the_lead_source_fails_the_lint():
    rec = _gd_record()
    rec["identity"]["model_name"]["note"] = "via infinitesauna.com"
    assert "D1" in _lint_msgs([rec])


# ------------------------------------------ Part A named records (pinned) --

@pytest.fixture(scope="module")
def dry():
    return vi.run(LEADS)


def _rules_for(dry, model):
    upstream, built, passing, held, quarantine, merges, meta, sha, release = dry
    key = next(r["model_key"] for r in upstream if r["model"] == model)
    return {rule for rule, _ in quarantine.get(key, [])}


@pytest.mark.parametrize("model,rule", [
    ("GDI-7389-02", "R1_ELECTRICAL"),
    ("GDI-8526-01", "R2_HYBRID"), ("GDI-8223-01", "R2_HYBRID"),
    ("SAN05M001", "R2_HYBRID"), ("SAN06M001", "R2_HYBRID"),
    ("SN-BPU-H6K001F", "R3_IDENTITY"), ("SN-BPU-H6K001N", "R3_IDENTITY"),
    ("clearlight-sanctuary-c-full-spectrum-infrared-corner-sauna-4-person", "R5_CAPACITY"),
])
def test_named_lead_records(dry, model, rule):
    assert rule in _rules_for(dry, model)


def test_clearlight_slug_is_never_a_model_number(dry):
    upstream, built, *_ = dry
    for r in upstream:
        if r["brand"] == "Clearlight" and vi.is_slug_model(r["model"]):
            assert built[r["model_key"]]["identity"]["model_number"]["value"] is None


# ------------------------------------------------------------ determinism --

@pytest.mark.skipif(not (ROOT / "out/verified/cache").exists(),
                    reason="origin cache is local-only (gitignored); determinism is checked where it exists")
def test_rebuilding_from_the_cache_is_byte_identical(tmp_path):
    files = [ROOT / "data/verified/saunas.json", ROOT / "data/verified/conflicts.json",
             ROOT / "data/verified/internal/backlog.json"]
    if not all(f.exists() for f in files):
        pytest.skip("dataset not built yet")
    before = [f.read_bytes() for f in files]
    # Every configured brand, including blocked ones: they have no records but do have
    # backlog entries, and a rebuild from a subset would silently drop those.
    names = list(json.loads((ROOT / "data/verified/sources.json").read_text())["brands"])
    subprocess.run([sys.executable, str(ROOT / "scripts/verified_build.py"), "--brands", *names],
                   check=True, capture_output=True)
    assert [f.read_bytes() for f in files] == before


def test_conditional_exterior_use_is_not_indoor_only():
    sts = vb.ex_placement(Seg("Indoor or covered exterior use"))
    assert vb.decide([("listed", D(), sts)], "indoor")[0] == "ambiguous"


def test_dual_circuits_never_publish_as_one_amperage():
    sts = vb.ex_amps(Seg("Electrical service: Dual x 120v/15 AMP Non GFCI"))
    assert vb.decide([("listed", D(), sts)], 15.0)[0] == "ambiguous"


def test_a_qualified_species_is_not_truncated():
    assert [s[0] for s in vb.ex_wood(Seg("Pacific Premium Cedar wood construction"))] == ["Pacific Premium Cedar"]


def test_a_heater_option_table_is_not_a_statement_about_this_model():
    s = Seg("Electrical Requirements 4.5kw and 6kw heaters require a 30 amp connection, 8kw heaters 40-amp, "
            "9kw and 10.5kw requires 220V, 50-amp, Breaker - Hard Wired. The wood burning stoves require no electrical hookup.",
            loc="product page panel 'Specifications'")
    for fn in (vb.option_aware(vb.ex_plug), vb.option_aware(vb.ex_amps), vb.option_aware(vb.ex_kw)):
        assert vb.decide([("listed", D(), fn(s))], None)[0] == "ambiguous"


def test_a_single_included_heater_is_still_a_statement():
    s = Seg("Stainless steel hinge and handle Harvia KIP 6kW Traditional Sauna Stove with Built in Controls")
    assert vb.decide([("listed", D(), vb.option_aware(vb.ex_kw)(s))], None)[0] == "source_only"


def test_titles_drop_year_and_parentheticals():
    name, _ = vi.build_name('2026 Golden Designs "Soria" 3 Person Hybrid Sauna (Indoor) (GDI-8330-01)', "Golden Designs")
    assert name == "Soria Hybrid Sauna"
    name, _ = vi.build_name('***New 2026 Model*** Golden Designs "Arlberg" 3 Person Traditional Outdoor Sauna', "Golden Designs")
    assert name == "Arlberg Traditional Outdoor Sauna"


# ------------------------------------------------------------- B2 additions --

def test_labelled_circuits_publish_as_a_set():
    s = Seg("Electrical service: 240V / 40AMP (Stove) and 120V / 15AMP (Lights and Music)")
    out, chosen, _ = vb.decide([("listed", D(), vb.ex_circuits(s))], None)
    assert out == "source_only"
    assert chosen[2][0] == (("Lights and Music", "120V", 15.0), ("Stove", "240V", 40.0))


def test_prose_labelled_circuits():
    s = Seg("Infrared heaters and lighting require a dedicated 120V/20A circuit (NEMA 5-20). "
            "Traditional stone heater requires a hardwired 240V/30A dedicated circuit.")
    out, chosen, _ = vb.decide([("listed", D(), vb.ex_circuits(s))], None)
    assert out == "source_only" and len(chosen[2][0]) == 2


def test_an_unlabelled_pair_withholds_the_circuits():
    s = Seg("240V / 40AMP (Stove). Also requires 120V / 15AMP.")
    assert vb.decide([("listed", D(), vb.ex_circuits(s))], None)[0] == "ambiguous"


def test_a_stated_count_that_disagrees_withholds_the_circuits():
    s = Seg("Three separate circuits required. 240V / 40AMP (Stove) and 120V / 15AMP (Lights)")
    assert vb.decide([("listed", D(), vb.ex_circuits(s))], None)[0] == "ambiguous"


def test_a_red_light_upgrade_is_not_a_feature():
    s = Seg("Red Light Therapy Upgrade available")
    assert vb.decide([("listed", D(), vb.ex_red_light(s))], None)[0] == "ambiguous"


def test_a_receptacle_is_not_a_plug():
    assert vb.ex_plug(Seg("Outlet NEMA L5-30")) == []
    assert vb.ex_plug(Seg("dedicated 120V/20A circuit (NEMA 5-20)")) == []
    assert vb.ex_plug(Seg("Plug: NEMA 5-20P"))[0][0] == "NEMA 5-20P"


def test_a_decimal_draw_beside_an_outlet_rating_is_two_amperages():
    s = Seg("120 Volts / 2,260 Watts / 18.83 Amps / Plugs into a 120V / 20 Amp outlet.")
    assert vb.decide([("listed", D(), vb.ex_amps(s))], None)[0] == "ambiguous"


def test_per_axis_dimensions_with_fractions():
    s = Seg("Exterior Dimensions\nWidth: 51 3/4″\nDepth: 47 3/4″\nHeight: 77″")
    assert vb.ex_dims_assembled(s)[0][0] == (51.75, 47.75, 77.0)


def test_sibling_selectors_on_a_page_are_not_capacity():
    page = Seg("Eclipse 2\n2-Person 4-Person\nCapacity 2 Person", loc="product page main content", kind="html")
    assert [x[0] for x in vb.ex_capacity(page)] == [(2, 2)]


def test_a_buyer_chosen_heater_package_withholds_electrical():
    p = vb.Product("x", "https://m/x", "X", [], "", "", [{"name": "Heater", "values": ["Electric 8kW", "Wood-burning"]}],
                   [], "https://m/x.json", None)
    assert vb.option_dependent(p)
    s = Seg("The Harvia 8kW electric heater heats to 180F")
    s.option_note = vb.option_dependent(p)
    assert vb.decide([("listed", D(), vb.option_aware(vb.ex_kw)(s))], None)[0] == "ambiguous"


def test_a_shared_cdn_file_needs_the_brands_own_shop_path():
    src = {"manufacturer_domains": ["m.com"], "pdf_hosts": ["cdn.shopify.com"]}
    assert not vb.origin_pdf("https://cdn.shopify.com/s/files/1/1/2/3/files/x.pdf", src)
    src["_shop_prefix"] = "/s/files/1/1/2/3/"
    assert vb.origin_pdf("https://cdn.shopify.com/s/files/1/1/2/3/files/x.pdf", src)
    assert not vb.origin_pdf("https://cdn.shopify.com/s/files/1/9/9/9/files/x.pdf", src)


def test_html_range_and_exclusion():
    src = {"html_start_rx": "^Start$", "html_stop_rx": "^Stop$", "html_exclude": [["^Upsell$", "^Back$"]]}
    h = "<p>Nav</p><p>Start</p><p>Keep 1</p><p>Upsell</p><p>Red Light Towers</p><p>Back</p><p>Keep 2</p><p>Stop</p><p>Footer</p>"
    assert vb.html_range(h, src) == "Keep 1\nBack\nKeep 2"


def test_name_match_needs_a_unique_best_slug():
    prods = {h: vb.Product(h, f"https://m/{h}", "", [], "", "", [], [], "", None)
             for h in ("sanctuary-five-person", "sanctuary-outdoor-five-person", "sanctuary-two-person")}
    lead = {"model_key": "k", "model": "slug", "title": "Clearlight SANCTUARY OUTDOOR 5 (4-5 PERSON)", "source_urls": []}
    matched, none = vb.match_leads({"manufacturer_domains": ["m"], "name_match": True}, [lead], prods)
    assert list(matched) == ["sanctuary-outdoor-five-person"]


def test_an_assembly_crew_is_not_seating_capacity():
    assert vb.ex_capacity(Seg("Recommendation 2 Person Recommended Before beginning installation")) == []
    assert "capacity" not in vb.PDF_FIELDS


def test_manual_spec_then_label_layout_binds_to_the_following_model():
    flat = ("120VAC 15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05) "
            "120VAC 20AMP Dedicated Circuit Required (DYN-6315-05) Carefully")
    ms = list(vb.AMP_RX.finditer(flat))
    assert vb.manual_owner(flat, ms[0]) == "DYN-6115-05|DYN-6215-05"
    assert vb.manual_owner(flat, ms[1]) == "DYN-6315-05"


def test_manual_label_then_spec_layout_still_binds_to_the_preceding_model():
    flat = "GDI-8503-01 - 240VAC 30AMP Circuit Required GDI-8506-01 - 240VAC 40AMP Circuit Required"
    ms = list(vb.AMP_RX.finditer(flat))
    assert vb.manual_owner(flat, ms[0]) == "GDI-8503-01" and vb.manual_owner(flat, ms[1]) == "GDI-8506-01"


def _manual(text):
    class M: pass
    m = M(); m.url = "https://goldendesignstorage.blob.core.windows.net/product/x.pdf"
    m.entry = {"sha256": "0" * 64, "fetched_at": "2026-09-27T00:00:00+00:00"}; m.pages = [(1, text)]
    return m


def test_a_lights_outlet_in_a_manual_is_not_the_supply():
    d = vb.manual_doc(_manual("GDI-8506-01 Owner's Manual 120VAC 15AMP Outlet Needed For Lights/Radio"), {"GDI850601"})
    assert [b for b in d.bound if b[0] in ("supply_voltage", "stated_amperage")] == []


def test_plural_circuits_in_a_manual_is_not_one_amperage():
    d = vb.manual_doc(_manual("MX-K306-01 - 120VAC 20AMP Dedicated Circuits Required"), {"MXK30601"})
    vals = {b[1] for b in d.bound if b[0] == "stated_amperage"}
    assert 20.0 in vals and len(vals) == 2


def test_a_recommended_dedicated_circuit_is_not_required():
    assert vb.ex_circuit(Seg("Dedicated Circuit Recommended. A dedicated 20A circuit is recommended.")) == []
    assert vb.ex_circuit(Seg("disconnect the sauna and turn OFF the dedicated circuit breaker.")) == []
    assert vb.ex_circuit(Seg("120VAC 15AMP Dedicated Circuit Required"))[0][0] == "Dedicated required"


def test_a_parenthetical_that_names_no_load_is_not_a_circuit_label():
    s = Seg("Electrical Service: 240V / 30AMP (Please consult a certified electrician.)")
    assert vb.ex_circuits(s) == []


def test_prose_circuit_purpose_is_only_the_load():
    s = Seg("Two Separate Circuits Required Infrared heaters and lighting require a dedicated 120V/20A circuit. "
            "Traditional stone heater requires a hardwired 240V/30A dedicated circuit.")
    purposes = {c[0] for c in vb.ex_circuits(s)[0][0]}
    assert purposes == {"Infrared heaters and lighting", "Traditional stone heater"}


def test_an_ambiguous_higher_tier_blocks_a_simpler_lower_figure():
    man, page = D("documented"), D("listed")
    out, chosen, _ = vb.decide([("documented", man, [(15.0, "p1", "x"), ("multiple circuits", "p1", "x")]),
                                ("listed", page, [(15.0, "b", "120 V/15 AMP")])], None)
    assert out == "ambiguous" and chosen is None


def test_a_negated_voltage_is_not_a_statement():
    s = Seg("Special Electrical 120 V/20 AMP Non GFCI dedicated receptacle and breaker (Not 220/240 V)")
    assert [x[0] for x in vb.ex_voltage(s)] == ["120V"]


def test_a_drawing_label_is_not_an_amperage():
    assert vb.ex_amps(Seg("AR-2 AR-1 AR-3A WALL B")) == []
    assert [x[0] for x in vb.ex_amps(Seg("120V/15amp"))] == [15.0]


def test_two_separate_outlets_are_not_one_amperage():
    s = Seg("REQUIRES 2 SEPARATE DEDICATED 120V/20 AMP OUTLETS")
    assert vb.decide([("listed", D(), vb.ex_amps(s))], None)[0] == "ambiguous"


def test_a_configuration_parenthetical_in_a_manual_is_not_attributed():
    flat = "DYN-6440-01 manual 120VAC 15AMP Dedicated Circuit Required (2 Person Model) 120VAC 20AMP Required (4 Person Model)"
    ms = list(vb.AMP_RX.finditer(flat))
    assert vb.manual_owner(flat, ms[0]) is None


def test_hybrid_rule_recognises_a_named_stone_heater():
    assert vi.TRAD_TEXT.search("Traditional stone heater requires a hardwired 240V/30A dedicated circuit")


def _opt_product(values):
    return vb.Product("x", "https://m/x", "X", [], "", "", [{"name": "Heater", "values": values}], [], "", None)


def test_uniform_option_kw_is_not_option_dependent_but_supply_still_is():
    p = _opt_product(["8kW KIP Heater w/ Dials", "8kW KIP Smart Heater + Fenix"])
    s = Seg("The Harvia 8kW electric heater heats to 180F. 240V / 40AMP")
    s.option_note, s.option_kw = vb.option_dependent(p), vb.option_uniform_kw(p)
    assert vb.decide([("listed", D(), vb.option_aware(vb.ex_kw, kw_field=True)(s))], None)[0] == "source_only"
    assert vb.decide([("listed", D(), vb.option_aware(vb.ex_amps)(s))], None)[0] == "ambiguous"


def test_mixed_or_wood_options_keep_kw_withheld():
    assert vb.option_uniform_kw(_opt_product(["6kW KIP", "8kW KIP"])) is None
    assert vb.option_uniform_kw(_opt_product(["8kW KIP", "Wood-burning stove"])) is None
    assert vb.option_uniform_kw(_opt_product(["8kW KIP", "Smart controller"])) is None


def test_a_step_number_is_not_an_amperage():
    assert vb.ex_amps(Seg("PAGE 34 Step 10.2A – Install Lower Bench (Wooden Front Wall Model)")) == []
    assert [x[0] for x in vb.ex_amps(Seg("120 Volts 18.83 A draw"))] == [18.83]


def test_series_name_from_the_manufacturer_title():
    assert vb.series_name("Majestic Far Infrared Indoor Sauna - 8 Person") == "majestic"
    assert vb.series_name("Grand Laurel Far Infrared Indoor Sauna - 3 Person") == "grand laurel"
    assert vb.series_name("Nordic II Traditional Outdoor Barrel Sauna - 3 Person") == "nordic ii"


def test_a_linked_manual_speaks_only_through_pages_naming_the_series():
    m = _manual("x")
    m.pages = [(1, "Majestic Hot Yoga 8 Person REQUIRES 240V/30AMP DEDICATED CIRCUIT"),
               (32, "must match the requested voltage (120VAC 15AMP Dedicated Circuit or 120VAC 20AMP Dedicated Circuit)")]
    d = vb.linked_doc(m, None, "Majestic Far Infrared Indoor Sauna - 8 Person")
    assert [loc for loc, _ in d.segments] == ["pdf page 1"]


def test_plural_circuits_on_a_page_or_linked_manual_is_not_one_amperage():
    s = Seg("HEMLOCK WOOD MODEL with CARBON HEATERS 120VAC/20AMP Dedicated Circuits Required Carefully")
    assert vb.decide([("listed", D(), vb.ex_amps(s))], None)[0] == "ambiguous"


def test_red_light_not_included_is_an_explicit_no():
    s = Seg("Red light therapy Not included Wood Eucalyptus")
    assert vb.decide([("listed", D(), vb.ex_red_light(s))], None)[2] == [] and vb.ex_red_light(s)[0][0] is False


def test_a_red_light_cross_sell_is_not_a_feature():
    assert vb.ex_red_light(Seg("If red light therapy is a priority, explore our red light saunas.")) == []


def test_a_buyer_chosen_lumber_type_withholds_wood():
    p = vb.Product("x", "u", "X", [], "", "", [{"name": "Lumber Type", "values": ["Rustic Cedar", "Onyx"]}], [], "", None)
    s = Seg("Choose Rustic Cedar for that classic sauna aroma")
    s.option_notes = {g: vb.option_dependent(p, g) for g in vb.OPTION_GROUPS}
    assert vb.decide([("listed", D(), vb.option_group(vb.ex_wood, "wood")(s))], None)[0] == "ambiguous"


def test_a_model_year_condition_is_not_a_plain_feature():
    s = Seg("Interior chromotherapy lighting system (Red Light Therapy Feature Starting in 2024 Models)")
    assert vb.decide([("listed", D(), vb.ex_red_light(s))], None)[0] == "ambiguous"


def test_nordic_pine_is_not_truncated():
    assert [x[0] for x in vb.ex_wood(Seg("Built from thermally modified Nordic Pine with smooth benches"))] == ["Thermally Modified Nordic Pine"]


def test_a_seating_count_after_assembled_dimensions_is_still_seating():
    s = Seg('SPECIFICATIONS: Assembled Dimensions (WDH): 64" x 48" x 78" 2 person capacity 6.0 kw Stove')
    assert [x[0] for x in vb.ex_capacity(s)] == [(2, 2)]


def test_a_buyer_chosen_size_withholds_capacity_without_r5():
    rec = _record(heater_kw=field(value=6.0, unit="kW"))
    rec["_rule_inputs"].update(cap_ambiguous=True, cap_statements=[((2, 3), "t", "2-3 person")],
                               size_option="the buyer chooses 'Size' (2-3 Person, 4 Person)")
    vb.apply_rules([rec])
    assert not any(w["rule"] == "R5_CAPACITY" for w in rec["withheld_reasons"])
    assert rec["capacity_max"]["grade"] == "not_verified"


def test_a_model_suffix_is_a_different_model():
    s = Seg('Dynamic "Avila" 1-2 Person Ultra Low EMF FAR IR Sauna (DYN-6103-01 Elite)', loc="product 'x' title", skus=["DYN-6103-01"])
    assert [x[0] for x in vb.ex_model(s)] == ["DYN-6103-01 Elite"]
    assert not vb.model_eq("DYN-6103-01", "DYN-6103-01 Elite")


def test_a_manual_model_number_must_match_the_pages_suffix():
    m = _manual("Instruction Manual Models: DYN-6103-01/DYN-6103-01 Elite 120VAC 15AMP")
    d = vb.manual_doc(m, {"DYN610301", "DYN610301ELITE"}, frozenset({"DYN610301ELITE"}))
    assert [b[1] for b in d.bound if b[0] == "model_number"] == ["DYN-6103-01 Elite"]
    d2 = vb.manual_doc(m, {"DYN610301"}, frozenset({"DYN610301"}))
    assert [b[1] for b in d2.bound if b[0] == "model_number"] == ["DYN-6103-01"]


# ----------------------------------------------------------- final batch --

def test_heat_type_from_the_description_names_exactly_one_system():
    s = Seg("Features a corner design. The Harvia 8kW electric heater heats to 180F in an hour.", loc="product 'x' body_html")
    assert [x[0] for x in vb.ex_heat_type(s)] == ["traditional"]


def test_description_naming_both_systems_is_ambiguous():
    s = Seg("A Harvia stove warms the room. Carbon far infrared panels line the walls.", loc="product 'x' body_html")
    assert vb.decide([("listed", D(), vb.ex_heat_type(s))], None)[0] == "ambiguous"


def test_description_heat_type_ignores_cross_sell_option_comparison_and_negation():
    s = Seg("The Harvia 8kW electric heater heats fast. Explore our infrared saunas. Infrared upgrade available. "
            "Unlike infrared cabins, this one uses rocks. No infrared panels.", loc="product 'x' body_html")
    assert [x[0] for x in vb.ex_heat_type(s)] == ["traditional"]


def test_the_title_still_decides_when_it_states_a_type():
    s = Seg("Nordic Traditional Sauna", loc="product 'x' title")
    s.segments.append(("product 'x' body_html", "Carbon infrared panels"))
    assert [x[0] for x in vb.ex_heat_type(s)] == ["traditional"]


def test_hyphenated_amps_are_read_but_drawing_labels_are_not():
    assert [x[0] for x in vb.ex_amps(Seg("Dedicated 240V 30-amp GFCI circuit"))] == [30.0]
    assert vb.ex_amps(Seg("AR-3A WALL B")) == []


def test_slug_model_match():
    prods = {h: vb.Product(h, f"https://m/{h}", "", [], "", "", [], [], "", None)
             for h in ("garden-series-model-g3", "garden-series-model-g2", "ergo-series-model-ee8g", "ergo-series-model-e8g")}
    src = {"manufacturer_domains": ["m"], "slug_model_match": "^[A-Z]{1,3}-"}
    for model, want in (("SL-MODELG3", "garden-series-model-g3"), ("SL-MODELEE8G", "ergo-series-model-ee8g")):
        matched, _ = vb.match_leads(src, [{"model_key": model, "model": model, "title": "", "source_urls": []}], prods)
        assert list(matched) == [want]


def test_slug_model_match_prefers_the_exact_model_over_a_capacity_tie():
    prods = {h: vb.Product(h, f"https://m/{h}", "", [], "", "", [], [], "", None)
             for h in ("traditional-7", "traditional-4", "traditional-8plus")}
    src = {"manufacturer_domains": ["m"], "slug_model_match": "^medical-sauna-", "name_match": True}
    lead = {"model_key": "k", "model": "medical-sauna-traditional7", "title": "Traditional 7 Sauna | 4-Person Hemlock", "source_urls": []}
    matched, _ = vb.match_leads(src, [lead], prods)
    assert list(matched) == ["traditional-7"]


def test_page_title_falls_back_to_og_title_without_the_site_name():
    assert vb.page_title('<meta property="og:title" content="Model G3 - SaunaLife" />') == "Model G3"
    assert vb.page_title('<h1><span>CT Luna Sauna</span></h1>') == "CT Luna Sauna"


def test_an_option_list_after_an_upgrades_header_is_not_the_description():
    s = Seg("What's Included:\n9kW Homecraft Revive , with upgrades available:\n9kW Homecraft Revive with Wi-Fi\n10.5kW Harvia Virta with Wi-Fi",
            loc="product 'x' body_html")
    assert vb.ex_heat_type(s) == []


def test_a_choose_between_heaters_sentence_is_an_option():
    s = Seg("Choose between a Harvia 8kW electric heater or a traditional wood-burning stove.", loc="product 'x' body_html")
    assert vb.ex_heat_type(s) == []


def test_description_fallback_is_off_when_another_document_titles_the_type():
    page = Seg("Blends a traditional stone heater with infrared technology.", loc="product page main content", kind="html")
    page.title_states_type = True
    assert vb.ex_heat_type(page) == []


def test_elect_to_use_is_an_option():
    s = Seg("A second table provides wood storage for those who elect to use a wood-fired sauna stove.", loc="product 'x' body_html")
    assert vb.ex_heat_type(s) == []


def test_spanish_cedar_is_not_truncated():
    assert [x[0] for x in vb.ex_wood(Seg("We cut our Spanish Cedar to your room's specifications"))] == ["Spanish Cedar"]


def test_a_numeric_store_sku_is_not_a_model_number():
    assert vb.ex_model(Seg("Traditional 5", loc="product 'x' title", skus=["37"])) == []
    assert [x[0] for x in vb.ex_model(Seg("x", skus=["CTC22LU"]))] == ["CTC22LU"]


def test_nested_capacity_statements_are_consistent_not_r5():
    rec = _record(heater_kw=field(value=6.0, unit="kW"))
    rec["_rule_inputs"].update(cap_ambiguous=True, cap_statements=[((6, 6), "t", "Olympus 6 Person Sauna"), ((5, 6), "b", "seating 5–6 people")])
    vb.apply_rules([rec])
    assert not any(w["rule"] == "R5_CAPACITY" for w in rec["withheld_reasons"])
    assert rec["capacity_max"]["grade"] == "not_verified" and "consistent" in rec["capacity_max"]["note"]


def test_capacity_outside_a_stated_range_is_r5():
    rec = _record(heater_kw=field(value=6.0, unit="kW"))
    rec["_rule_inputs"].update(cap_ambiguous=True, cap_statements=[((6, 6), "t", "6 Person"), ((5, 5), "b", "Max Capacity: 5 persons")])
    vb.apply_rules([rec])
    assert any(w["rule"] == "R5_CAPACITY" for w in rec["withheld_reasons"])


def test_ideal_for_is_advice_not_capacity():
    s = Seg("Feature: 1-2 Person capacity (Compact Unit - Ideal for 1 Person) Exterior dimensions")
    assert [x[0] for x in vb.ex_capacity(s)] == [(1, 2)]
