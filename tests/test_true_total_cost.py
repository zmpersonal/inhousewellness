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
    """ONE template, because Round 3 retired the other three. Four URLs rendering
    the same calculator split link equity four ways across ~67 referring domains
    and read as duplicate content."""
    tpls = sorted((ROOT / "templates").glob("page.sauna-*.json"))
    assert len(tpls) == 1
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
    write = wf.index("name: Upsert")
    for gate in ("Prove the guards fire",
                 "The missing-value lint, across both scopes",
                 "Rebuild the assets and refuse a drifted checkout"):
        assert wf.index(gate) < write, gate
    assert "secrets.SHOPIFY_ADMIN_TOKEN" in wf
    # inputs travel through env, never interpolated into the shell
    assert "${{ inputs.theme_id }}" in wf
    assert 'python scripts/deploy_theme_files.py --theme-id "$THEME_ID"' in wf


def test_the_deploy_job_installs_nothing():
    """The deploy path imports only stdlib, asserted by preflight --stdlib-only.
    A deploy that cannot be broken by a dependency resolving differently on the
    day is worth more than one that also runs pytest. The full suite is a local
    gate on the change; these gates bear on the write."""
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    deploy = wf[wf.index("  deploy:"):wf.index("  verify:")]
    assert "pip install" not in deploy
    assert "playwright" not in deploy


def test_the_shop_and_api_version_are_literals_and_only_the_token_is_secret():
    """A shop domain is in every storefront URL. Holding it in a secret only
    means the deploy fails with 'no credential' when the truth is 'nobody set
    the non-secret'."""
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    assert "SHOPIFY_SHOP: inhousewellness.myshopify.com" in wf
    assert 'SHOPIFY_API_VERSION: "2026-07"' in wf
    assert "secrets.SHOPIFY_SHOP" not in wf
    # Count the INTERPOLATION, not the word. The comment above it in the
    # workflow says "not secrets." and counting prose made this test fail on
    # the sentence explaining the rule -- twice now in this repo.
    assert wf.count("${{ secrets.") == 1


def test_the_theme_id_input_defaults_to_the_round_13_preview_theme():
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    head = wf[wf.index("theme_id:"):wf.index("live:")]
    assert 'default: "146278776899"' in head
    assert "required: true" in head


def test_the_verify_job_drives_the_deployed_url_not_a_local_copy():
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    verify = wf[wf.index("  verify:"):]
    assert "needs: deploy" in verify
    assert "preview_theme_id=${THEME_ID}" in verify
    assert "verify_calculator_states.py" in verify
    assert "--url" in verify
    assert "if: always()" in verify, "screenshots must survive a failure"


def test_a_given_url_is_never_quietly_swapped_for_the_local_harness():
    """A run that says it verified the deployed theme and actually verified a
    file on disk is the worst result this script could produce."""
    import ast
    src = (ROOT / "scripts" / "verify_calculator_states.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "target")
    body = ast.unparse(fn.body[1:])      # [0] is the docstring, which SAYS "fallback"
    assert "if url:" in body and "yield url" in body
    for hedge in ("except", "fallback", "try", "PAGE if"):
        assert hedge not in body, hedge


def test_screenshots_are_stamped_with_what_they_are_pictures_of():
    src = (ROOT / "scripts" / "verify_calculator_states.py").read_text()
    assert 'args.label' in src
    assert 'default="local-harness"' in src


# ── the pages a preview URL actually renders ────────────────────────────────
def test_the_page_deploy_passes_its_own_controls():
    from scripts import deploy_pages as P
    assert P.self_test() == []


def test_every_page_handle_has_a_body_a_title_and_a_matching_template():
    from scripts.deploy_pages import PAGES
    from scripts.deploy_theme_files import MANIFEST
    assert set(PAGES) == {"sauna-cost"}
    for handle, (title, suffix) in PAGES.items():
        assert (ROOT / "content" / "pages" / (handle + ".html")).exists(), handle
        assert title.strip()
        assert "templates/page.%s.json" % suffix in MANIFEST, suffix


def test_the_page_lookup_filters_by_exact_handle_not_by_search():
    """Shopify's page search is full-text: asking for "sauna" returns pages with
    no "sauna" in the handle at all — about-us-page came back on the real store.
    Trusting the search to have filtered would overwrite an unrelated page."""
    import ast
    src = (ROOT / "scripts" / "deploy_pages.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "existing")
    body = ast.unparse(fn.body[1:])
    # ast.unparse normalises quotes, so match on the shape, not the quoting.
    assert "n['handle'] == handle" in body


def test_a_page_is_never_created_without_its_body():
    import ast
    src = (ROOT / "scripts" / "deploy_pages.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "body_of")
    assert "sys.exit" in ast.unparse(fn)


def test_draft_is_the_scripts_default_and_publish_is_asked_for_explicitly():
    """A published page is live on the store immediately, on whatever theme is
    MAIN. That is a decision, so the default declines to make it."""
    src = (ROOT / "scripts" / "deploy_pages.py").read_text()
    assert 'choices=["skip", "draft", "publish"], default="draft"' in src


def test_the_workflow_creates_pages_only_on_a_real_write():
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    step = wf[wf.index("Create or update the page"):]
    assert "if: inputs.live == 'write'" in step
    assert 'deploy_pages.py --pages "$PAGES"' in step
    assert "default: publish" in wf[wf.index("pages:"):wf.index("concurrency:")]


def test_the_workflow_retires_the_duplicates_and_photographs_the_result():
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    retire = wf[wf.index("Retire the three duplicate URLs"):]
    assert "deploy_redirects.py --live" in retire
    assert "if: inputs.live == 'write' && inputs.pages != 'skip'" in retire
    # the pages must be created before they are retired, in that order
    assert wf.index("Create or update the page") < wf.index("Retire the three")
    shots = wf[wf.index("Photograph the deployed page"):]
    assert "--width 1280" in shots and "--width 390" in shots


def test_the_read_back_compares_digests_and_coerces_shopifys_string_size():
    """Deploy run 1 upserted all ten files correctly and then reported every one
    as "SIZE MISMATCH: theme 10147, disk 10147". Shopify returns `size` as
    UnsignedInt64, which JSON-serialises as a STRING, and `"10147" != 10147`.
    A gate firing on correct data, printing two identical numbers as a
    difference — the exact cost CLAUDE.md says such a gate carries.

    The fix is not only the coercion: length was never the right comparison.
    Two files of equal size can differ in every byte, so the digest decides.
    """
    src = (ROOT / "scripts" / "deploy_theme_files.py").read_text()
    assert "hashlib.md5" in src
    assert "int(node[" in src
    assert "checksumMd5" in src
    assert int({"size": "10147"}["size"]) == 10147


def test_a_length_match_is_never_reported_as_byte_identical():
    """When the API returns no digest, the run says what it did and did not
    check rather than calling a length match byte-identical."""
    src = (ROOT / "scripts" / "deploy_theme_files.py").read_text()
    assert "bytes NOT verified" in src
    # The claim is made only alongside a digest comparison. Anchor on the PRINT,
    # not on the word: the comments above it also say "byte-identical", and
    # grepping prose has now failed three tests in this repo.
    idx = src.index('print("  byte-identical')
    window = src[max(0, idx - 400):idx]
    assert "theme_md5 == disk_md5" in window


def test_a_page_is_read_back_by_id_not_by_search():
    """Deploy run 2 created all four pages correctly — published, right suffix —
    and then reported every one as "MISSING after write". The read-back used a
    full-text query for "sauna": a different, weaker lookup than the existence
    check uses, and one a brand-new page may not be indexed for yet. The id
    comes back from the write itself, so there is nothing to search for."""
    src = (ROOT / "scripts" / "deploy_pages.py").read_text()
    assert "query($id: ID!)" in src and "page(id: $id)" in src
    assert 'READ_Q, {"id": written[handle]}' in src
    assert 'READ_Q, {"q"' not in src


def test_the_write_records_the_id_it_got_back():
    import ast
    src = (ROOT / "scripts" / "deploy_pages.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(fn)
    assert "written[handle] = res['page']['id']" in body


# ── Shopify reflows a page body, and that is not corruption ─────────────────
def test_a_page_body_is_compared_on_visible_text_not_bytes():
    """Deploy run 3 wrote the methodology page correctly and reported
    "BODY LENGTH MISMATCH: store 9076, repo 9060". Reading the stored body back
    showed what the 16 bytes were: Shopify PRETTY-PRINTS markup on save. The
    body went in as `<thead><tr><th>Figure</th>` and came back as
    `<thead><tr>\\n<th>Figure</th>\\n`, and `<li><strong>` became `<li>\\n<strong>`.
    Every changed byte is whitespace inside block markup.

    The fix is stricter about what matters, not looser: the reader-facing text
    must be IDENTICAL character for character, where a length check would have
    passed a body with two words swapped.
    """
    from scripts.deploy_pages import visible_text
    sent = "<table><thead><tr><th>Figure</th><th>Read on</th></tr></thead></table>"
    reflowed = ("<table>\n<thead><tr>\n<th>Figure</th>\n<th>Read on</th>\n"
                "</tr></thead>\n</table>")
    assert len(sent) != len(reflowed), "the control must change the byte length"
    assert visible_text(sent) == visible_text(reflowed) == "Figure Read on"


@pytest.mark.parametrize("a,b", [
    ("<p>47 of 139 priced saunas</p>", "<p>48 of 139 priced saunas</p>"),
    ("<p>$1,800 inside and assembled</p>", "<p>$1,300 inside and assembled</p>"),
    ("<p>we do not publish an installation cost</p>",
     "<p>we do publish an installation cost</p>"),
])
def test_a_real_content_change_still_fails_the_comparison(a, b):
    from scripts.deploy_pages import visible_text
    assert visible_text(a) != visible_text(b)


def test_entities_and_missing_bodies_are_normalised_not_guessed():
    from scripts.deploy_pages import visible_text
    assert visible_text("8&nbsp;kW") == "8 kW"
    assert visible_text("<li><strong>90 of 135</strong> state a spec</li>") == \
        "90 of 135 state a spec"
    assert visible_text(None) == ""
    assert visible_text("") == ""


def test_a_mismatch_is_reported_somewhere_a_human_can_act_on():
    """Run 1 printed "10147, disk 10147" as a difference. A mismatch has to say
    WHERE and SHOW BOTH SIDES or nobody can do anything with it."""
    from scripts.deploy_pages import first_difference
    msg = first_difference("the total is $9,413.80 over five years",
                           "the total is $9,413.90 over five years")
    assert "at char" in msg and "repo:" in msg and "store:" in msg


def test_third_party_storefront_noise_is_noted_not_failed():
    """The first run against the DEPLOYED theme passed every one of the six
    states and then failed the job on two lines that have nothing to do with
    this page: a 403 from shop.app/pay/hop and a CSP frame-ancestors refusal
    for shop.app. That is Shop Pay's own widget, on every page of the live
    store. A real storefront is not a test harness.

    The scoping must not soften anything of OURS: a failing request to the
    page's own origin, and a console error naming our origin or no origin at
    all, still fail.
    """
    import ast
    src = (ROOT / "scripts" / "verify_calculator_states.py").read_text()
    tree = ast.parse(src)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert {"note_response", "note_console"} <= names
    body = ast.unparse(tree)
    assert "own_host" in body
    assert "third_party" in body
    # a same-origin failure still goes to fails
    assert "fails if host == own_host else third_party" in body
    # third-party lines are printed, never swallowed
    assert "third-party console/network line(s)" in src


def test_the_verifier_still_fails_on_a_page_error_from_any_origin():
    """A JS exception is the page's own, wherever the script came from."""
    src = (ROOT / "scripts" / "verify_calculator_states.py").read_text()
    assert 'pg.on("pageerror", lambda e: fails.append' in src


# ── Round 3: one page, three redirects, and a redesign that regressed nothing ──
def test_the_redirect_deploy_passes_its_own_controls():
    from scripts import deploy_redirects as R
    assert R.self_test() == []


def test_the_retired_handles_cannot_creep_back_into_the_page_deploy():
    """A PUBLISHED page beats a redirect. If one of the three were re-added to
    deploy_pages.PAGES, the next deploy would republish it and its 301 would
    quietly stop firing — a duplicate back in the index with nothing to show for
    it in any log."""
    from scripts.deploy_redirects import RETIRE, TARGET, handle_of
    from scripts.deploy_pages import PAGES
    assert handle_of(TARGET) in PAGES
    for path in RETIRE:
        assert handle_of(path) not in PAGES, path


def test_the_redirects_are_created_before_any_page_is_unpublished():
    """The order is the whole safety argument, and run 1 got it backwards.

    A redirect only fires on a path that would 404, so unpublishing first is
    tempting. Run 1 did that, the redirect step then died on `Access denied for
    urlRedirects field` — the Actions token has no write_online_store_navigation
    scope — and three live URLs were left 404ing with nothing to catch them.

    A redirect is harmless while its page is still published: inert, waiting.
    Create them first and a failure changes nothing; unpublish second and that
    is what switches them on.
    """
    src = (ROOT / "scripts" / "deploy_redirects.py").read_text()
    body = src[src.index("def main("):]
    assert body.index("redirects:") < body.index("unpublishing the retired pages")


def test_a_missing_scope_halts_before_anything_is_unpublished():
    src = (ROOT / "scripts" / "deploy_redirects.py").read_text()
    body = src[src.index("def main("):]
    denied = body.index("NO SCOPE")
    assert denied < body.index("unpublishing the retired pages")
    assert "NOTHING WAS CHANGED" in body
    assert "write_online_store_navigation" in body


def test_a_redirect_is_proved_by_a_request_not_by_a_mutation_id():
    from scripts.deploy_redirects import check_live, verify_live
    src = (ROOT / "scripts" / "deploy_redirects.py").read_text()
    # main() proves it through verify_live, which is where check_live now lives.
    assert "verify_live(" in src[src.index("def main("):]
    assert callable(check_live) and callable(verify_live)
    # and the verifier must not follow the redirect it is trying to observe
    assert "HTTPRedirectHandler" in src and "return None" in src


def test_the_methodology_is_on_the_page_and_leads_with_the_research():
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    assert 'id="methodology"' in liquid
    method = liquid[liquid.index('id="methodology"'):]
    finding = method[:method.index("The three formulas")]
    for number in ("142", "3,569", "90 of 135", "47 of 139"):
        assert number in finding, number
    # every element the standalone page carried must still be here
    for kept in ("kilowatts × hours per session", "five-year total ÷",
                 "US Energy Information Administration", "2026-09-14", "2026-09-15",
                 "your electrician's quote", "18.34", "43.14",
                 "$4–6, $10–15, $15–25, $20–30 and $30–90"):
        assert kept in method, kept


def test_the_callout_styles_cannot_land_on_a_table_row():
    """`lineRow` builds class="ttc-line ttc-<state>", so an invite row is
    `ttc-invite` — the same name a callout box uses. Unscoped, the callout's
    padding, background and radius rendered inside the table."""
    css = (ROOT / "assets" / "inh-true-total-cost.css").read_text()
    for name in ("ttc-gap", "ttc-invite", "ttc-reader-kw", "ttc-excluded"):
        block = "div.%s" % name
        assert block in css, name
        # the bare class must not carry box styling of its own
        import re as _re
        bare = _re.search(r"(?m)^\.%s\s*\{" % name, css)
        assert bare is None, "%s is styled unscoped" % name


def test_the_type_scale_meets_the_floor_for_this_audience():
    """Base 17px, nothing under 15px. The readers are 40-60 and often on a
    phone; the previous build set body text at 13px and helpers at 11px."""
    css = (ROOT / "assets" / "inh-true-total-cost.css").read_text()
    assert "--fs-base:  1.0625rem" in css       # 17px
    assert "--fs-small: 0.9375rem" in css       # 15px
    import re as _re
    # no rule anywhere may set a size below the 15px floor
    for value in _re.findall(r"font-size:\s*([0-9.]+)rem", css):
        assert float(value) >= 0.9375, value


def test_controls_are_at_least_48px_and_the_native_select_is_replaced():
    css = (ROOT / "assets" / "inh-true-total-cost.css").read_text()
    assert "min-height: 3rem" in css            # 48px
    assert "appearance: none" in css and "-webkit-appearance: none" in css
    assert "background-image: url(\"data:image/svg+xml" in css


def test_every_interactive_thing_has_a_visible_focus_state():
    css = (ROOT / "assets" / "inh-true-total-cost.css").read_text()
    for target in ("input[type=\"text\"]:focus-visible",
                   ".ttc-opt input:focus-visible",
                   ".ttc-decline input:focus-visible",
                   ".ttc a:focus-visible"):
        assert target in css, target


def test_hover_is_gated_and_reduced_motion_is_honoured():
    css = (ROOT / "assets" / "inh-true-total-cost.css").read_text()
    assert "@media (hover: hover) and (pointer: fine)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    # and there is no `transition: all` anywhere
    assert "transition: all" not in css


def test_the_results_region_is_not_animated():
    """It rebuilds on every keystroke. An animation a reader triggers dozens of
    times a session is one that makes the tool feel slow."""
    css = (ROOT / "assets" / "inh-true-total-cost.css").read_text()
    for region in (".ttc-total", ".ttc-lines", "div.ttc-invite", "div.ttc-excluded"):
        block = css[css.index(region):css.index(region) + 420]
        assert "transition" not in block, region
        assert "animation" not in block, region


def test_the_delivery_options_are_cards_not_a_raw_fieldset():
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    assert 'class="ttc-options" role="radiogroup"' in liquid
    assert liquid.count('class="ttc-opt"') == 3
    assert "<legend>How should it arrive?</legend>" not in liquid


def test_the_form_is_grouped_into_four_named_steps():
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    assert liquid.count('class="ttc-step"') == 4
    for n, name in ((1, "The sauna"), (2, "Where it is going"),
                    (3, "How you will use it"), (4, "Your own figures")):
        assert 'ttc-step-n">%d</span> %s' % (n, name) in liquid, name


def test_every_input_the_js_reads_still_exists_under_the_same_name():
    """The redesign moved markup. A renamed `name=` is a silently dead input."""
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    js = (ROOT / "assets" / "inh-true-total-cost.js").read_text()
    for name in ("model", "manual_price", "zip", "io", "circuit", "sessions",
                 "minutes", "reader_kw", "decline_kw", "electrical",
                 "foundation", "maintenance"):
        assert 'name="%s"' % name in liquid, name
        assert '"[name=%s]"' % name in js or "name=%s" % name in js, name
    assert liquid.count("data-freight") == 3
    assert 'data-region="out"' in liquid


def test_the_total_is_rendered_before_the_line_table():
    """The result is the hero. A reader who came for a number should not have to
    scroll past eleven line items to reach it."""
    import ast
    js = (ROOT / "assets" / "inh-true-total-cost.js").read_text()
    body = js[js.index("function render("):js.index("function lineRow(")]
    assert body.index("appendChild(totals(r))") < body.index("appendChild(table)")
    assert body.index("appendChild(totals(r))") < body.index("exclusions(r)")
    assert ast is not None


def test_the_redirects_can_be_proved_without_any_credential():
    """A request to the old path is the evidence, and a reader's browser has no
    token either. It matters here because the Actions token has no navigation
    scope at all — so the one check that can always run is the one that counts."""
    import ast
    src = (ROOT / "scripts" / "deploy_redirects.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "verify_live")
    body = ast.unparse(fn)
    assert "gql(" not in body, "verify_live must not call the Admin API"
    assert "check_live" in body
    wf = (ROOT / ".github" / "workflows" / "deploy-theme.yml").read_text()
    step = wf[wf.index("Prove the three 301s from outside"):]
    assert "--verify-only" in step
    assert "if: inputs.live == 'write'" in step
    assert "pages != 'skip'" not in step.split("run:")[0], \
        "the proof must run even when the page step is skipped"


def test_the_redirect_check_follows_the_chain_a_browser_would():
    """The one-hop version was wrong about all three URLs.
    `inhousewellness.myshopify.com/pages/sauna-running-cost` answers 301 to
    `inhousewellness.com/pages/sauna-running-cost` — Shopify canonicalising the
    DOMAIN, same path — and our redirect fires on the hop after that. Read one
    hop and every page looks like it redirects to itself."""
    import ast
    src = (ROOT / "scripts" / "deploy_redirects.py").read_text()
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "check_live")
    body = ast.unparse(fn)
    assert "MAX_HOPS" in body, "the chain must be walked, and capped"
    assert "urljoin" in body, "a relative Location must resolve against the hop"
    verify = next(n for n in ast.parse(src).body
                  if isinstance(n, ast.FunctionDef) and n.name == "verify_live")
    vbody = ast.unparse(verify)
    # the test is where the path ENDS UP, plus that a redirect happened at all
    assert "urlsplit(final).path" in vbody
    assert "redirected" in vbody
