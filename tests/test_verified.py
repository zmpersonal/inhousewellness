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
    def __init__(self, text, loc="product body_html", skus=()):
        self.segments, self.skus = [(loc, text)], list(skus)


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
        "_rule_inputs": {"text": "Traditional sauna with Harvia stove", "title": "X", "cap_ambiguous": False, "cap_statements": []},
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
    files = [ROOT / "data/verified/saunas.json", ROOT / "data/verified/conflicts.json"]
    if not all(f.exists() for f in files):
        pytest.skip("dataset not built yet")
    before = [f.read_bytes() for f in files]
    brands = sorted({r["identity"]["brand"]["value"] for r in json.loads(files[0].read_text())["records"]})
    names = [b for b, s in SOURCES["brands"].items() if s["display"] in brands]
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
