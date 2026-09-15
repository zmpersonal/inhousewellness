"""The True Total Cost calculator: its arithmetic, its refusals, and its section.

The arithmetic lives in `assets/inh-cost-core.js` because it has to run in the
customer's browser. It is exercised HERE, through Node, against the same bytes
the theme gets -- rather than reimplemented in Python, which would be a second
definition of the same rules and would drift.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_storefront_assets as BSA          # noqa: E402
from scripts import preview_true_total_cost as PREV         # noqa: E402
from scripts.lint_missing_values import scan_render         # noqa: E402

ASSETS = ROOT / "assets"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not on PATH")


def js(expr):
    """Evaluate an expression with INHCost, the tables and the ZIP table loaded."""
    prog = (
        "const C=require(%s);const T=require(%s);const Z=require(%s);"
        "const out=(%s);console.log(JSON.stringify(out===undefined?null:out));"
        % (json.dumps(str(ASSETS / "inh-cost-core.js")),
           json.dumps(str(ASSETS / "inh-cost-tables.json")),
           json.dumps(str(ASSETS / "inh-zip-state.json")), expr))
    r = subprocess.run([NODE, "-e", prog], capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(r.stderr.strip())
    return json.loads(r.stdout)


def run(overrides, expr="r"):
    """compute() with `overrides` merged over the defaults."""
    return js("(() => {let i=C.defaults(T);Object.assign(i,%s);"
              "const r=C.compute(i,T,Z);return %s;})()"
              % (json.dumps(overrides), expr))


def code_of(name):
    """A JS file with its comments removed.

    A test that greps raw source cannot tell a rule from the sentence explaining
    the rule -- and the explanation is exactly where a forbidden key gets named.
    """
    src = (ASSETS / name).read_text()
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)//.*$", " ", src)


def product_with_kw(kw):
    tables = json.loads((ASSETS / "inh-cost-tables.json").read_text())
    for p in tables["products"]:
        if p["kw"]["v"] == kw:
            return p
    pytest.skip("no catalogue SKU rated %s kW" % kw)


# ── the published methodology, reproduced exactly ───────────────────────────
# inhousewellness.com/blogs/saunas/true-total-cost-home-sauna, published
# 2026-09-09: "kilowatts x hours x sessions per week x your state's rate", three
# 45-minute sessions a week, every week of the year. The article's own worked
# examples are 2.1 kW -> about $45/yr and 8 kW -> about $172/yr at the US
# average. The kWh figure is the part that is ours to get right; the dollar
# figure then follows from whichever state rate applies.
@needs_node
@pytest.mark.parametrize("kw,kwh", [(2.1, 245.7), (8.0, 936.0), (9.0, 1053.0)])
def test_the_published_kwh_arithmetic_round_trips(kw, kwh):
    got = run({"product": {"h": "x", "t": "x", "u": "x",
                           "price": {"v": 1000, "src": "t", "at": "t"},
                           "kw": {"v": kw, "src": "t", "at": "t"},
                           "io": "indoor", "manual": None},
               "zip": "58102", "freightTier": "curbside"},
              "r.lines.find(l=>l.id==='running').kwh_per_year")
    assert got == pytest.approx(kwh, abs=0.05)


@needs_node
def test_the_articles_own_worked_example_is_reproduced():
    """8 kW at the Massachusetts rate. The article publishes $172 at the US
    average (18.34c); MA is 29.61c and the same 936 kWh gives $277.15."""
    line = run({"product": {"h": "x", "t": "x", "u": "x",
                            "price": {"v": 1000, "src": "t", "at": "t"},
                            "kw": {"v": 8.0, "src": "t", "at": "t"},
                            "io": "indoor", "manual": None},
                "zip": "02108", "freightTier": "curbside"},
               "r.lines.find(l=>l.id==='running')")
    assert line["rate_cents"] == 29.61 and line["us_state"] == "MA"
    assert line["amount"] == pytest.approx(936.0 * 0.2961, abs=0.01)


# ── the unknown-kW path, which is the majority state ────────────────────────
@needs_node
def test_an_unrated_model_invites_and_never_estimates():
    p = {"h": "x", "t": "x", "u": "x", "price": {"v": 5000, "src": "t", "at": "t"},
         "kw": {"v": None, "reason": "POWER_NOT_STATED"}, "io": "indoor",
         "manual": "https://example.invalid/m.pdf"}
    line = run({"product": p, "zip": "58102", "freightTier": "curbside"},
               "r.lines.find(l=>l.id==='running')")
    assert line["state"] == "invite"
    assert line["amount"] is None
    assert line["manual"] == "https://example.invalid/m.pdf"


@needs_node
def test_a_reader_supplied_kw_computes_and_is_labelled_as_theirs():
    p = {"h": "x", "t": "x", "u": "x", "price": {"v": 5000, "src": "t", "at": "t"},
         "kw": {"v": None, "reason": "POWER_NOT_STATED"}, "io": "indoor", "manual": None}
    r = run({"product": p, "zip": "58102", "freightTier": "curbside", "readerKw": 6})
    assert r["power"]["state"] == "reader"
    assert "reader-supplied" in r["power"]["source"]
    line = [l for l in r["lines"] if l["id"] == "running"][0]
    assert line["kw_state"] == "reader"
    assert line["amount"] == pytest.approx(6 * 0.75 * 3 * 52 * 0.1412, abs=0.01)


@needs_node
def test_declining_produces_a_partial_total_that_names_its_exclusion():
    p = {"h": "x", "t": "x", "u": "x", "price": {"v": 5000, "src": "t", "at": "t"},
         "kw": {"v": None, "reason": "POWER_NOT_STATED"}, "io": "indoor", "manual": None}
    r = run({"product": p, "zip": "58102", "freightTier": "curbside", "declinedKw": True})
    assert r["complete"] is False
    assert "running" in [e["id"] for e in r["excluded"]]
    assert r["five_year_usd"] == 5000.0          # price only; freight is $0 curbside


@needs_node
def test_a_class_average_is_never_reachable_for_an_unrated_model():
    """The refusal that matters: with no rating and no reader figure, there is
    no code path that produces a number. Every other rated SKU in the catalogue
    could supply a plausible one, and none of them does."""
    p = {"h": "x", "t": "x", "u": "x", "price": {"v": 5000, "src": "t", "at": "t"},
         "kw": {"v": None, "reason": "POWER_NOT_STATED"}, "io": "indoor", "manual": None}
    for extra in ({}, {"declinedKw": True}, {"readerKw": None}):
        args = {"product": p, "zip": "58102", "freightTier": "curbside"}
        args.update(extra)
        line = run(args, "r.lines.find(l=>l.id==='running')")
        assert line["amount"] is None, extra


# ── ZIP resolution: five outcomes, none of them a guess ─────────────────────
@needs_node
@pytest.mark.parametrize("zipcode,status", [
    ("58102", "ok"),            # Fargo, ND
    ("02108", "ok"),            # Boston, MA
    ("99501", "ok"),            # Anchorage, AK
    ("02861", "multi_state"),   # straddles MA / RI
    ("00601", "territory"),     # Puerto Rico: no EIA row
    ("00001", "unresolved"),    # a real ZIP prefix with no ZCTA
    ("1234", "malformed"),
    ("", "malformed"),
])
def test_zip_resolution_outcomes(zipcode, status):
    assert js("C.resolveZip(%s, Z).status" % json.dumps(zipcode)) == status


@needs_node
@pytest.mark.parametrize("zipcode", ["00001", "00601", "02861", "1234", ""])
def test_an_unresolved_zip_never_borrows_the_national_average(zipcode):
    r = run({"product": None, "manualPrice": 5000, "zip": zipcode,
             "freightTier": "curbside"})
    line = [l for l in r["lines"] if l["id"] == "running"][0]
    assert line["amount"] is None
    assert line["state"] in ("zip_gap", "invite")
    # and the one number it must never be
    assert json.dumps(r).find("18.34") == -1


def test_the_national_and_division_aggregates_are_not_in_the_rates_map():
    tables = json.loads((ASSETS / "inh-cost-tables.json").read_text())
    rates = tables["energy"]["rates_cents_per_kwh"]
    ref = tables["energy"]["non_fallback_reference"]["values"]
    assert "US" not in rates and "NEW" not in rates and "PACN" not in rates
    assert ref["US"] == 18.34
    assert len(rates) == 51


def test_no_code_in_the_render_path_reads_the_non_fallback_block():
    """The aggregates ship so the methodology page can PRINT them and say why
    they are unused. If anything in the render path ever reads that key, they
    have stopped being reference and started being a fallback."""
    for name in ("inh-cost-core.js", "inh-true-total-cost.js"):
        assert "non_fallback_reference" not in code_of(name), name


# ── the rulings, asserted as code rather than trusted as prose ──────────────
@needs_node
@pytest.mark.parametrize("tier,usd", [("curbside", 0.0), ("inside_delivery", 600.0),
                                      ("inside_and_assembled", 1800.0)])
def test_freight_is_three_flat_tiers(tier, usd):
    line = run({"product": None, "manualPrice": 1000, "zip": "58102",
                "freightTier": tier}, "r.lines.find(l=>l.id==='freight')")
    assert line["amount"] == usd


@needs_node
def test_a_free_delivery_tier_is_still_shown_as_a_line():
    line = run({"product": None, "manualPrice": 1000, "zip": "58102",
                "freightTier": "curbside"}, "r.lines.find(l=>l.id==='freight')")
    assert line["amount"] == 0.0 and line["state"] == "included"
    assert "included in your price" in line["note"]


@needs_node
def test_installation_is_never_published_only_ever_entered():
    r = run({"product": None, "manualPrice": 1000, "zip": "58102",
             "freightTier": "curbside"})
    e = [l for l in r["lines"] if l["id"] == "electrical"][0]
    assert e["amount"] is None and e["state"] == "omitted"
    r2 = run({"product": None, "manualPrice": 1000, "zip": "58102",
              "freightTier": "curbside", "electricalQuote": 2400})
    e2 = [l for l in r2["lines"] if l["id"] == "electrical"][0]
    assert e2["amount"] == 2400.0 and e2["source"] == "your own figure"


@needs_node
def test_the_1800_tier_never_absorbs_the_electricians_bill():
    """Ruling 3. The two figures are separate lines and both are in the total;
    the delivery line says so in words."""
    r = run({"product": None, "manualPrice": 1000, "zip": "58102",
             "freightTier": "inside_and_assembled", "electricalQuote": 2400})
    freight = [l for l in r["lines"] if l["id"] == "freight"][0]
    assert freight["amount"] == 1800.0
    assert "third-party" in freight["note"]
    assert r["one_off_usd"] == 1000.0 + 1800.0 + 2400.0


def test_nothing_anywhere_derives_kw_from_volts_times_amps():
    """Carried forward and not relitigated. Asserted structurally: the render
    path holds no multiplication of a volts field by an amps field."""
    for name in ("inh-cost-core.js", "inh-true-total-cost.js"):
        src = code_of(name)
        assert not re.search(r"volts[^\n]{0,40}\*[^\n]{0,40}amps", src, re.I), name
        assert not re.search(r"amps[^\n]{0,40}\*[^\n]{0,40}volts", src, re.I), name


# ── a zero is a measurement or an absence, never both ───────────────────────
@needs_node
def test_no_recurring_figure_yields_null_not_zero():
    p = {"h": "x", "t": "x", "u": "x", "price": {"v": 4099, "src": "t", "at": "t"},
         "kw": {"v": None, "reason": "POWER_NOT_STATED"}, "io": "indoor", "manual": None}
    r = run({"product": p, "zip": "58102", "freightTier": "curbside"})
    assert r["per_year_usd"] is None
    assert r["recurring_lines_known"] == 0


@needs_node
def test_a_reader_typed_zero_is_kept_as_a_real_zero():
    p = {"h": "x", "t": "x", "u": "x", "price": {"v": 4099, "src": "t", "at": "t"},
         "kw": {"v": None, "reason": "POWER_NOT_STATED"}, "io": "indoor", "manual": None}
    r = run({"product": p, "zip": "58102", "freightTier": "curbside",
             "maintenancePerYear": 0})
    assert r["per_year_usd"] == 0.0
    assert r["recurring_lines_known"] == 1


# ── determinism ─────────────────────────────────────────────────────────────
@needs_node
def test_the_same_inputs_give_the_same_total_every_time():
    args = {"product": product_with_kw(8.0), "zip": "02108",
            "freightTier": "inside_and_assembled", "sessionsPerWeek": 4,
            "sessionMinutes": 50, "electricalQuote": 2400,
            "foundationCost": 900, "maintenancePerYear": 120}
    totals = {run(args, "r.five_year_usd") for _ in range(3)}
    assert len(totals) == 1
    assert run(args, "r.complete") is True


def test_the_core_holds_no_clock_and_no_network():
    src = code_of("inh-cost-core.js")
    for banned in ("Date.now", "new Date", "fetch(", "Math.random", "localStorage"):
        assert banned not in src, banned


# ── the assets, and the ZIP compression ─────────────────────────────────────
def test_the_asset_builder_passes_its_own_controls():
    assert BSA.self_test() == []


def test_the_committed_assets_match_a_fresh_build():
    """A theme asset nobody rebuilt is a figure nobody checked."""
    fresh = BSA.build_cost_asset()
    on_disk = json.loads((ASSETS / "inh-cost-tables.json").read_text())
    assert fresh["products"] == on_disk["products"]
    assert fresh["coverage"] == on_disk["coverage"]
    fresh_zip, _ = BSA.build_zip_asset()
    assert fresh_zip["ranges"] == json.loads(
        (ASSETS / "inh-zip-state.json").read_text())["ranges"]


def test_coverage_is_reported_as_it_is_not_as_we_wish():
    t = json.loads((ASSETS / "inh-cost-tables.json").read_text())
    c = t["coverage"]
    assert c["priced_skus"] == 139
    assert c["with_rated_power_kw"] + c["without_rated_power"] == c["priced_skus"]
    assert c["with_rated_power_pct"] < 50, "the gap is the headline, not a footnote"


def test_every_product_cell_is_a_value_or_a_reason():
    t = json.loads((ASSETS / "inh-cost-tables.json").read_text())
    for p in t["products"]:
        for name in ("price", "kw", "volts", "amps", "dedicated"):
            cell = p[name]
            assert cell["v"] is not None or cell.get("reason"), (p["h"], name)


def test_a_manual_link_is_only_offered_where_the_pdf_actually_read():
    """5 of the 142 Drive embeds serve a Google sign-in page and one is a dead
    id. Offering a reader a link we know is broken is worse than offering none."""
    t = json.loads((ASSETS / "inh-cost-tables.json").read_text())
    ok = {r["handle"] for r in json.loads(
        (ROOT / "data" / "facts" / "manual_specs.json").read_text())["rows"]
        if r.get("status") == "OK"}
    for p in t["products"]:
        if p["manual"] is not None:
            assert p["h"] in ok, p["h"]


# ── the section ─────────────────────────────────────────────────────────────
def test_the_preview_harness_passes_its_own_controls():
    assert PREV.self_test() == []


def test_the_section_emits_only_the_two_schema_types_that_are_ours():
    """Avada SEO owns Organization, WebSite and Product; breadcrumbs.liquid owns
    BreadcrumbList. A second copy of any of them is the risk Round 0 named."""
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    for owned_elsewhere in ('"@type": "Product"', '"@type": "BreadcrumbList"',
                            '"@type": "Organization",\n        "name": {{ shop',
                            '"@type": "WebSite"'):
        assert owned_elsewhere not in liquid, owned_elsewhere
    assert '"@type": "Dataset"' in liquid
    assert '"@type": "SoftwareApplication"' in liquid


def test_the_section_computes_no_money_in_liquid():
    """Every figure comes from the core. Arithmetic here would be a second
    implementation of the same rules, and they would drift."""
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    for filt in ("| times:", "| plus:", "| minus:", "| divided_by:", "| money"):
        assert filt not in liquid, filt


def test_every_asset_the_section_names_exists():
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    named = set(re.findall(r"\{\{\s*'([\w.-]+)'\s*\|\s*asset_url", liquid))
    assert named, "the section names no assets at all"
    for name in named:
        assert (ASSETS / name).exists(), name


def test_every_page_template_points_at_this_section():
    tpls = sorted((ROOT / "templates").glob("page.sauna-*.json"))
    assert len(tpls) == 4
    for t in tpls:
        doc = json.loads(t.read_text())
        assert doc["sections"]["main"]["type"] == "true-total-cost", t.name
        assert doc["sections"]["main"]["settings"]["last_updated"]


@pytest.mark.parametrize("tpl", sorted((ROOT / "templates").glob("page.sauna-*.json")))
def test_the_number_is_inside_the_first_40_words(tpl):
    s = json.loads(tpl.read_text())["sections"]["main"]["settings"]
    opening = (s["heading"] + " " + s["intro_fact"]).split()
    assert re.search(r"\d", " ".join(opening[:40])), tpl.name


# ── the lint's new rules, fired at input that must and must not trip them ───
def test_the_render_lint_catches_a_literal_default(tmp_path):
    f = tmp_path / "x.js"
    f.write_text("var kw = product.kw || 0;\n")
    hits = scan_render(f)
    assert hits and hits[0][1].startswith("R1")


def test_the_render_lint_catches_an_unguarded_numeric_coercion(tmp_path):
    f = tmp_path / "x.js"
    f.write_text("var q = Number(input.value);\nrender(q);\n")
    hits = scan_render(f)
    assert hits and hits[0][1].startswith("R3")


def test_the_render_lint_accepts_a_guarded_coercion(tmp_path):
    f = tmp_path / "x.js"
    f.write_text("var n = Number(raw);\nif (!isFinite(n)) { return null; }\n")
    assert scan_render(f) == []


def test_the_render_lint_catches_liquids_own_default_filter(tmp_path):
    f = tmp_path / "x.liquid"
    f.write_text("{{ section.settings.kw | default: 0 }}\n")
    hits = scan_render(f)
    assert hits and hits[0][1].startswith("R2")


def test_the_render_lint_does_not_flag_its_own_rationale(tmp_path):
    """The first version flagged the sentence explaining the rule."""
    f = tmp_path / "x.js"
    f.write_text('/* `Number("") === 0` is the bug this guards against. */\n'
                 '// and parseInt("abc") is NaN\n')
    assert scan_render(f) == []


def test_the_render_path_is_actually_in_the_lints_scope():
    from scripts.lint_missing_values import RENDER_SCAN
    scoped = {d for d, _ in RENDER_SCAN}
    assert {"assets", "sections"} <= scoped
    assert scan_render(ASSETS / "inh-cost-core.js") == []
    assert scan_render(ASSETS / "inh-true-total-cost.js") == []
    assert scan_render(ROOT / "sections" / "true-total-cost.liquid") == []


# ── the deploy path ─────────────────────────────────────────────────────────
def test_the_deploy_script_passes_its_own_controls():
    from scripts import deploy_theme_files as D
    assert D.self_test() == []


def test_a_template_is_never_deployed_before_its_section():
    """Shopify refuses `templates/page.sauna-cost.json` into a theme that does
    not yet hold `sections/true-total-cost.liquid`:

        FILE_VALIDATION_ERROR: Section type 'true-total-cost' does not refer to
        an existing section file

    Learned by trying it against the real store on 2026-09-15. In one batch the
    templates are validated before the section lands, so the deploy fails on its
    last four files and leaves a theme holding code and none of the pages.
    """
    from scripts.deploy_theme_files import PASS_1, PASS_2, MANIFEST
    assert not set(PASS_1) & set(PASS_2)
    assert set(PASS_1) | set(PASS_2) == set(MANIFEST)
    assert any(f.startswith("sections/") for f in PASS_1)
    assert not any(f.startswith("templates/") for f in PASS_1)
    assert all(f.startswith("templates/") for f in PASS_2)


def test_the_live_theme_is_refused_by_the_deploy_path_too():
    from scripts.deploy_theme_files import refusal_for
    assert "REFUSED" in refusal_for({"name": "live", "role": "MAIN"}, "1")
    assert refusal_for({"name": "r13", "role": "UNPUBLISHED"}, "1") is None
    assert "FAILED" in refusal_for(None, "1")


def test_the_deploy_workflow_gates_before_it_writes():
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    gates = wf.index("Prove the guards fire")
    sweep = wf.index("Sweep — tests and the missing-value lint")
    write = wf.index("name: Upsert")
    assert gates < write and sweep < write
    assert "secrets.SHOPIFY_ADMIN_TOKEN" in wf
    # inputs travel through env, never interpolated into the shell
    assert "${{ inputs.theme_id }}" in wf
    assert 'python scripts/deploy_theme_files.py --theme-id "$THEME_ID"' in wf
