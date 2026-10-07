"""Round 2 Part B: page data, the theme templates rendered locally, the checks that guard
them, and the deploy script's guards. No network: records come from saunas.json."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_checks as vc  # noqa: E402
import verified_deploy as vd  # noqa: E402
import verified_pages as vp  # noqa: E402
import verified_render as vr  # noqa: E402

TOLEDO = "sauna/golden-designs/gdi-8360-01"


@pytest.fixture(scope="module")
def ds():
    return {r["inh_id"]: r for r in vp.load_dataset()["records"]}


@pytest.fixture(scope="module")
def nav():
    return vp.load_navigation()


def render_model(pd):
    e = vr.env()
    main = vr.render_file(e, "sections/inh-verified-model.liquid", {"metaobject": {"page_data": {"value": pd}},
                                                                     "shop": {"url": vp.BASE}})
    return f'<html><head></head><body><main id="MainContent" role="main">{main}</main></body></html>'


def pd_for(ds, nav, iid):
    handles, titles = vp.load_handles(), vp.load_titles()
    return vp.page_data(ds[iid], handles[iid], titles[iid], nav)


# ------------------------------------------------------------ page data --

def test_page_data_never_carries_a_price_or_banned_wording(ds, nav):
    for r, h, t, _ in vp.page_records({"records": list(ds.values())}):
        s = json.dumps(vp.page_data(r, h, t, nav), ensure_ascii=False)
        assert not vc.PRICE_RX.search(s), h
        assert not vc.BANNED_RX.search(s), h


def test_every_gap_reads_not_verified(ds, nav):
    pd = pd_for(ds, nav, TOLEDO)
    gaps = [r for r in pd["key_facts"] + pd["electrical"] if r["state"] == "gap"]
    assert gaps and all(r["text"] == "Not verified" for r in gaps)


def test_the_record_payload_drops_offers(ds):
    assert "offers" not in vp.record_payload(ds[TOLEDO])


def test_ledger_records_never_get_a_page(ds):
    ids = {r["inh_id"] for r, *_ in vp.page_records({"records": list(ds.values())})}
    assert not ids & vp.LEDGER_IDS
    forced = copy.deepcopy(ds["sauna/golden-designs/gdi-8206-01"])
    forced["status"] = "published"
    assert not next(vp.threshold({"records": [forced]}))[1]["meets"]


def test_page_count_is_the_threshold_count(ds):
    """Every record meeting the threshold either has a page (approved title, frozen handle) or is a
    row awaiting approval in the Round 3 review CSV. Nothing meets the threshold unaccounted for.
    (Round 2 asserted pages == meets; Round 3 adds records whose titles are not yet approved.)"""
    import csv
    d = {"records": list(ds.values())}
    meets = {r["inh_id"] for r, t in vp.threshold(d) if t["meets"]}
    paged = {r["inh_id"] for r, *_ in vp.page_records(d)}
    pending = set()
    # Round 3's review file, and every later round's publish review (r3-electrical: publish-review.csv).
    for csv_path in (ROOT / "docs/verified/round-3-title-review.csv", ROOT / "docs/verified/r3-electrical/publish-review.csv"):
        if csv_path.exists():
            pending |= {row["inh_id"] for row in csv.DictReader(open(csv_path))}
    assert paged <= meets
    assert meets - paged == pending - paged
    assert vp.threshold_report(d)["totals"]["meets"] == len(meets)


# ------------------------------------------------- rendered templates + checks --

def test_a_real_record_renders_and_passes_the_value_match(ds, nav):
    pd = pd_for(ds, nav, TOLEDO)
    html = render_model(pd)
    errs = []
    vc.check_model(ds[TOLEDO], pd["title"], html, pd, errs)
    assert errs == []
    assert "Circuit: Stove &amp; Full Spectrum" in html


def test_the_value_match_catches_a_changed_value(ds, nav):
    pd = pd_for(ds, nav, TOLEDO)
    html = render_model(pd).replace("240V · 40 A", "240V · 30 A", 1)
    errs = []
    vc.check_model(ds[TOLEDO], pd["title"], html, pd, errs)
    assert any("numbers" in e for e in errs)


def test_the_value_match_catches_a_hidden_verified_value(ds, nav):
    pd = pd_for(ds, nav, TOLEDO)
    pd["electrical"] = [r for r in pd["electrical"] if r["field"] != "electrical.heater_kw"]
    errs = []
    vc.check_model(ds[TOLEDO], pd["title"], render_model(pd), pd, errs)
    assert any("not displayed" in e for e in errs)


def test_the_value_match_catches_a_gap_over_a_verified_value(ds, nav):
    pd = pd_for(ds, nav, TOLEDO)
    row = next(r for r in pd["key_facts"] if r["field"] == "heat_type")
    row.update(state="gap", text="Not verified")
    errs = []
    vc.check_model(ds[TOLEDO], pd["title"], render_model(pd), pd, errs)
    assert any("verifies" in e for e in errs)


def test_option_dependence_renders_with_its_source_and_counts_for_the_threshold(ds, nav):
    """No record carries recorded option-dependence yet; the template must still render it
    so a Round 3 record needs no template work."""
    r = copy.deepcopy(ds[TOLEDO])
    for k in ("supply_voltage", "stated_amperage", "heater_kw", "circuits_required"):
        r["electrical"][k] = {"value": None, "grade": "not_verified", "source_url": None, "note": None}
    r["electrical"]["circuits"] = []
    assert not vp.has_electrical(r)
    r["electrical"]["option_dependence"] = {"value": "heater option", "grade": "listed", "observed_at": "2026-09-28",
                                            "source_url": "https://example-manufacturer.test/p",
                                            "evidence": {"snippet": "Choose between a Harvia 8kW electric heater or a wood stove"}}
    assert vp.has_electrical(r)
    rows = vp.electrical_rows(r)
    opt = [x for x in rows if x["state"] == "option"]
    assert opt and all(x["text"] == "Depends on the heater option chosen" and x["source_url"] for x in opt)
    pd = vp.page_data(r, "fixture", "Fixture Sauna", nav)
    html = render_model(pd)
    assert "Depends on the heater option chosen" in html and "example-manufacturer.test" in html


def test_option_dependence_without_evidence_does_not_count(ds):
    r = copy.deepcopy(ds[TOLEDO])
    r["electrical"]["option_dependence"] = {"value": "heater option", "source_url": None, "evidence": {}}
    assert vp.option_dependence(r) is None


def test_hub_table_is_server_rendered_for_every_entry(ds, nav):
    pages = [vp.page_data(r, h, t, nav) for r, h, t, _ in vp.page_records({"records": list(ds.values())})]
    e = vr.env()
    html = vr.render_file(e, "sections/inh-verified-hub.liquid",
                          {"metaobjects": {"sauna": {"values": [vr.entry(p) for p in pages]}},
                           "page": {"title": "Verified Sauna Database"}, "shop": {"url": vp.BASE}})
    assert html.count("<tr data-heat=") == len(pages)
    assert f'data-inhv="brand-count">{len({p["brand"] for p in pages})}<' in html
    assert 'data-inhv="filters" hidden' in html


def test_product_link_renders_only_for_a_mapped_entry(ds, nav):
    e = vr.env()
    pd = pd_for(ds, nav, TOLEDO)
    on = vr.render_file(e, "sections/inh-verified-product-link.liquid",
                        {"product": {"metafields": {"inh_verified": {"sauna": {"value": vr.entry(pd)}}}}})
    off = vr.render_file(e, "sections/inh-verified-product-link.liquid",
                         {"product": {"metafields": {"inh_verified": {"sauna": {"value": None}}}}})
    assert "Verified specs &amp; electrical requirements →" in on and pd["path"] in on
    assert off.strip() == ""


def test_schema_vocabulary_check_rejects_offers_and_unknown_properties():
    V = ({"Product", "Thing", "Brand"}, {"name": {"Thing"}, "offers": {"Product"}, "brand": {"Product"}},
         {"Product": ["Thing"], "Brand": ["Thing"]})
    errs = []
    vc.check_jsonld({"@type": "Product", "name": "x", "offers": {}, "madeUp": 1}, "t", errs, V)
    assert any("offers" in e for e in errs) and any("madeUp" in e for e in errs)


# --------------------------------------------------------------- deploy --

def test_deploy_self_test_passes():
    assert vd.self_test() == 0


class FakeAdmin:
    def __init__(self, scopes, existing_status=None):
        self.scopes, self.existing, self.calls = scopes, existing_status, []

    def __call__(self, query, v=None):
        self.calls.append(query.split("(")[0].split("{")[0].strip())
        if "currentAppInstallation" in query:
            return {"currentAppInstallation": {"accessScopes": [{"handle": s} for s in self.scopes]}}
        if "metaobjectDefinitionByType" in query:
            return {"metaobjectDefinitionByType": {"id": "gid://d/1", "type": "sauna", "capabilities": {}}}
        if "metaobjectByHandle" in query:
            if self.existing is None:
                return {"metaobjectByHandle": None}
            return {"metaobjectByHandle": {"id": "gid://m/1", "handle": v["h"]["handle"],
                                           "capabilities": {"publishable": {"status": self.existing}}, "field": {"value": "{}"}}}
        raise AssertionError("unexpected write: " + query[:60])


def test_entries_step_writes_nothing_without_scopes():
    q = FakeAdmin(["read_products"])
    assert vd.deploy_entries(True, q=q) is False
    assert not any("mutation" in c for c in q.calls)


def test_entries_step_never_touches_an_active_entry():
    q = FakeAdmin(["write_metaobject_definitions", "write_metaobjects"], existing_status="ACTIVE")
    with pytest.raises(SystemExit):
        vd.deploy_entries(True, q=q)


def test_entry_payloads_carry_no_price(ds, nav):
    pd = pd_for(ds, nav, TOLEDO)
    s = json.dumps(vd.entry_fields(pd, vp.record_payload(ds[TOLEDO]), "gid://shopify/Product/1"), ensure_ascii=False)
    assert not vc.PRICE_RX.search(s)


THEME_SOURCES = ["sections/inh-verified-model.liquid", "sections/inh-verified-hub.liquid",
                 "sections/inh-verified-methodology.liquid", "sections/inh-verified-product-link.liquid",
                 "snippets/inh-verified-fact.liquid", "assets/inh-verified.css", "assets/inh-verified.js",
                 "templates/metaobject/sauna.json", "templates/page.inh-verified-hub.json",
                 "templates/page.inh-verified-methodology.json"]


@pytest.mark.parametrize("rel", THEME_SOURCES)
def test_theme_sources_carry_no_price_no_lead_source_and_no_absence_wording(rel):
    """D1 extended to templates (R2-D10), D-G for prices, D-C for the gap wording."""
    text = (ROOT / rel).read_text()
    assert not vc.PRICE_RX.search(text)
    assert not vc.BANNED_RX.search(text)


@pytest.mark.parametrize("rel", THEME_SOURCES[:5])
def test_templates_type_no_spec_value(rel):
    """Pages render entirely from the dataset: no unit-bearing number is typed into a template."""
    import re
    text = (ROOT / rel).read_text()
    assert not re.search(r"(?i)\b\d+(?:\.\d+)?\s?(?:v|kw|a|amps?|in|inches|°f|people|person)\b", text)


# ----------------------------------------------- Round 3 governance: MAIN at run time --

def test_main_is_refused_by_resolved_id_even_if_the_role_field_disagrees():
    from verify_theme_asset_path import main_refusal
    assert main_refusal("167150092355", "167150092355") is not None
    assert main_refusal("167150092355", "146278776899") is None
    assert main_refusal("167150092355", "167150092355", "167150092355") is None   # the go-live override, named
    assert main_refusal("167150092355", "167150092355", "146278776899") is not None


def test_resolve_main_refuses_unless_exactly_one_main(monkeypatch):
    import verify_theme_asset_path as g
    monkeypatch.setattr(g, "gql", lambda *a: {"themes": {"nodes": []}})
    with pytest.raises(SystemExit):
        g.resolve_main("s", "t")
    monkeypatch.setattr(g, "gql", lambda *a: {"themes": {"nodes": [{"id": "gid://shopify/OnlineStoreTheme/9", "name": "n", "role": "MAIN"}]}})
    assert g.resolve_main("s", "t") == ("9", "n")


def test_every_theme_writer_resolves_main_at_run_time():
    for rel in ("scripts/deploy_theme_files.py", "scripts/rollback_calculator.py", "scripts/verified_deploy.py"):
        src = (ROOT / rel).read_text()
        assert "resolve_main(" in src and "main_refusal(" in src, rel
        assert "resolved at run time" in src, rel


def test_the_gap_diagnosis_never_leaves_the_repo(ds):
    """Round 3: the diagnosis quotes raw page text, prices included, and is not rendered yet."""
    with_diag = [r for r in ds.values() if "gap_diagnosis" in r]
    assert with_diag, "the dataset should carry the Round 3 diagnosis"
    for r in with_diag:
        p = json.dumps(vp.record_payload(r), ensure_ascii=False)
        assert "gap_diagnosis" not in p and not vc.PRICE_RX.search(p)


def test_d12_per_circuit_figure_never_reads_as_one_circuit(ds):
    """r3 D12: a figure stated for EACH of several circuits. The first live render said "requires a
    120V, 20 A circuit" for a unit needing two; the answer sentence and the fact rows must carry it."""
    d12 = [r for r in ds.values() if vp.per_circuit(r["electrical"]["stated_amperage"])]
    assert d12
    for r in d12:
        s = vp.answer_sentence(r, "T")
        assert " A circuit." not in s and "requires a " not in s, s
        assert "separate" in s or "per circuit" in s, s
        rows = {x["field"]: x for x in vp.electrical_rows(r)}
        assert rows["electrical.stated_amperage"]["note"].startswith("per circuit"), r["inh_id"]
    monaco = ds["sauna/dynamic-saunas/dyn-6996-01-elite"]
    assert vp.answer_sentence(monaco, "T").endswith("requires two separate 120V, 20 A outlets.")


def test_rule_c_short_title_and_handle(ds):
    """Cleanup C: brand + short model name + model number, under 60, generated by rule (never by hand)."""
    import verified_titles as vt
    t, h, f = vt.short_title_and_handle(ds["sauna/golden-designs/gdi-8230-01"], "3")
    assert (h, t, f) == ("golden-designs-reserve-edition-gdi-8230-01", "Golden Designs Reserve Edition GDI-8230-01, 3 Person", [])
    t, h, f = vt.short_title_and_handle(ds["sauna/golden-designs/gdi-6996-02-elite"], "6")
    assert h == "golden-designs-gdi-6996-02-elite" and not f      # "Far IR Sauna" leaves no short name
    frozen = json.loads(vt.HANDLES.read_text())["handles"]
    for i in ("sauna/golden-designs/gdi-8040-03", "sauna/golden-designs/gdi-8260-01", "sauna/maxxus/mx-k406-01-hemlock"):
        _, h, f = vt.short_title_and_handle(ds[i], None)
        assert len(h) <= 60 and not f and frozen[i]["handle"] == h
