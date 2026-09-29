"""Go-live: the hub must render one row per active entry, as a logged-out visitor sees it, and
every page write must keep its template. From the 2026-09-29 hub report (a staff browser on a
preview of an older theme saw the default page template: title and body only)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import verified_deploy as vd  # noqa: E402
import verified_golive as g  # noqa: E402

A, B = "sauna/x/a", "sauna/y/b"


def hub(ids, count=None):
    rows = "".join(f'<tr data-heat="t" data-cap="2" data-brand="X" data-inh-id="{i}"><td>x</td></tr>' for i in ids)
    return f'<strong data-inhv="model-count">{len(ids) if count is None else count}</strong><table>{rows}</table>'


FALLBACK = ('<h1>Verified Sauna Database</h1><div class="rte"><p>This page lists every model in the InHouse '
            'Wellness Verified Sauna Database.</p></div>')


def test_the_default_page_template_fallback_fails():
    assert "not rendered" in g.hub_rows_problem(FALLBACK, [A, B])


def test_fewer_rows_than_active_entries_fails():
    assert "1 rows for 2" in g.hub_rows_problem(hub([A]), [A, B])


def test_the_wrong_rows_fail():
    assert g.hub_rows_problem(hub([A, "sauna/z/c"]), [A, B])


def test_a_count_disagreeing_with_the_rows_fails():
    assert g.hub_rows_problem(hub([A, B], count=131), [A, B])


def test_exactly_the_active_entries_passes():
    assert g.hub_rows_problem(hub([B, A]), [A, B]) is None


def test_a_live_check_refuses_a_preview_url():
    with pytest.raises(SystemExit):
        g.visitor_get("https://inhousewellness.com/pages/sauna-database?preview_theme_id=1")


def test_a_page_write_sets_the_template_and_halts_if_it_does_not_read_back():
    sent = []

    def q(query, v=None):
        if "pageUpdate" in query:
            sent.append(v["p"])
            return {"pageUpdate": {"page": {"id": "p"}, "userErrors": []}}
        return {"page": {"id": "p", "isPublished": True, "templateSuffix": None}}   # Shopify dropped it

    with pytest.raises(SystemExit):
        vd.page_update_checked(q, "p", {"isPublished": True}, "inh-verified-hub")
    assert sent[0]["templateSuffix"] == "inh-verified-hub"


def test_every_page_update_in_the_launch_path_goes_through_the_checked_writer():
    import ast
    for f in ("scripts/verified_golive.py",):
        tree = ast.parse((ROOT / f).read_text())
        raw = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "PAGE_UPDATE_M"]
        assert raw == [], f"{f} calls pageUpdate directly"


# ------------------------------------------- go-live design: mutation tests --
import copy  # noqa: E402
import html as _html  # noqa: E402
import re  # noqa: E402

import verified_checks as vc  # noqa: E402
import verified_pages as vp  # noqa: E402
import verified_render as vr  # noqa: E402

SOLD = "sauna/golden-designs/gdi-7389-02"        # Copenhagen: brand sold, mapped, 2 sources
NOT_SOLD = "sauna/salus/san08m012"               # Solara: brand not sold, one model number


@pytest.fixture(scope="module")
def ds():
    return {r["inh_id"]: r for r in vp.load_dataset()["records"]}


def page(ds, iid, mutate=None):
    pd = vp.page_data(ds[iid], vp.load_handles()[iid], vp.load_titles()[iid], vp.load_navigation())
    if mutate:
        mutate(pd)
    main = vr.render_file(vr.env(), "sections/inh-verified-model.liquid",
                          {"metaobject": {"page_data": {"value": pd}}, "shop": {"url": vp.BASE}})
    return (f'<html><head><title>{_html.escape(pd["seo_title"])}</title></head><body>'
            f'<main id="MainContent" role="main">{main}</main></body></html>'), pd


def errs_for(ds, iid, html_, title):
    errs = []
    vc.check_design(ds[iid], title, html_, errs)
    return errs


@pytest.mark.parametrize("iid", [SOLD, NOT_SOLD])
def test_the_built_pages_pass_the_design_checks(ds, iid):
    h, pd = page(ds, iid)
    assert errs_for(ds, iid, h, pd["title"]) == []


def test_a_marker_pointing_at_the_wrong_source_is_caught(ds):
    h, pd = page(ds, SOLD)
    assert len(pd["sources"]) >= 2
    bad = h.replace('href="#inhv-src-1" data-source-n="1"', 'href="#inhv-src-2" data-source-n="2"', 1)
    assert any("marker" in e for e in errs_for(ds, SOLD, bad, pd["title"]))


def test_a_sources_entry_without_nofollow_is_caught(ds):
    h, pd = page(ds, SOLD)
    assert errs_for(ds, SOLD, h.replace('rel="nofollow noopener"', 'rel="noopener"', 1), pd["title"])


def test_an_inline_source_link_is_caught(ds):
    h, pd = page(ds, SOLD)
    assert errs_for(ds, SOLD, h.replace("</dd>", '<a class="inhv-src" href="https://x.test">x</a></dd>', 1), pd["title"])


def test_the_model_number_in_a_sold_brands_title_is_caught(ds):
    h, pd = page(ds, SOLD, lambda p: p.update(seo_title=f"{p['title']} (GDI-7389-02): Verified Specs & Electrical Requirements"))
    assert any("title tag" in e for e in errs_for(ds, SOLD, h, pd["title"]))


def test_a_missing_model_number_in_a_not_sold_title_is_caught(ds):
    h, pd = page(ds, NOT_SOLD, lambda p: p.update(seo_title=f"{p['title']}: Verified Specs & Electrical Requirements"))
    assert any("title tag" in e for e in errs_for(ds, NOT_SOLD, h, pd["title"]))


def test_a_wrong_mpn_is_caught(ds):
    def m(p):
        p["jsonld"][0]["mpn"] = "WRONG"
    h, pd = page(ds, NOT_SOLD, m)
    assert any("mpn" in e for e in errs_for(ds, NOT_SOLD, h, pd["title"]))


def test_a_top_store_button_on_an_unmapped_model_is_caught(ds):
    def m(p):
        p["store"] = {"sold": True, "product_url": "/products/x", "product_label": "See price", "collections": []}
    h, pd = page(ds, NOT_SOLD, m)
    assert any("top store button" in e for e in errs_for(ds, NOT_SOLD, h, pd["title"]))


def test_a_similar_model_with_another_placement_or_heat_type_is_caught(ds):
    mapped = vp.load_navigation()["mapped"]
    other = next(m["product_handle"] for i, m in mapped.items()
                 if i in ds and ds[i]["heat_type"]["value"] != ds[NOT_SOLD]["heat_type"]["value"])

    def m(p):
        p["similar"]["items"][0] = {"title": "X", "url": f"/products/{other}"}
    h, pd = page(ds, NOT_SOLD, m)
    assert any("does not share" in e for e in errs_for(ds, NOT_SOLD, h, pd["title"]))


def test_a_similar_block_on_a_sold_brand_is_caught(ds):
    def m(p):
        p["similar"] = {"criteria": "c", "items": [], "collection_url": "/c", "collection_label": "l"}
    h, pd = page(ds, SOLD, m)
    assert any("similar-models block on a brand INH sells" in e for e in errs_for(ds, SOLD, h, pd["title"]))


@pytest.mark.parametrize("cell", ["Multiple circuits", "Not verified", "240V"])
def test_a_wrong_hub_power_cell_is_caught(ds, cell):
    r = ds[SOLD]
    right = vc.expected_power(r)
    assert right == "Multiple circuits"
    cells = (f'<td>{r["identity"]["brand"]["value"]}</td><th><a href="/x">{vp.load_titles()[SOLD]}</a></th>'
             f'<td>{r["heat_type"]["value"].capitalize()}</td><td>{vp.capacity_label(r)}</td><td>{cell}</td>')
    assert (vc.hub_row_problems(r, SOLD, cells, vp.load_titles()[SOLD]) == []) == (cell == right)


def test_the_page_builders_hub_power_agrees_with_the_record_on_every_page(ds):
    for pd in (json.loads(p.read_text()) for p in (ROOT / "out/verified/pages").glob("*.json")):
        assert pd["hub_power"] == vc.expected_power(ds[pd["inh_id"]]), pd["handle"]


def test_an_outbound_link_without_rel_is_caught():
    assert vc.external_links_problem('<a href="https://maker.test/p">x</a>') == ["maker.test"]
    assert vc.external_links_problem('<a href="https://maker.test/p" rel="nofollow noopener">x</a>') == []
    assert vc.external_links_problem('<a href="https://inhousewellness.com/x">x</a>') == []


# --------------------------------------------------- theme-publish gate --

def test_the_theme_check_fails_a_theme_without_the_inh_verified_files(monkeypatch):
    import verified_theme_check as tc
    monkeypatch.setattr(vd, "read_files", lambda q, t, names: {})
    probs = tc.file_problems(None, "1", ["templates/product.json", "templates/product.Bundle.json"])
    assert len([p for p in probs if p.startswith("missing")]) == len(g.NEW_FILES) + 2


def test_the_theme_check_passes_a_theme_that_matches_the_repo(monkeypatch):
    import verified_theme_check as tc
    snap = sorted((ROOT / "data/verified/golive").glob("main-*-snapshot"))[0]
    lay = vd.patch_layout((snap / "layout__theme.liquid").read_text())
    prod = vd.patch_product((snap / "templates__product.json").read_text())
    files = {n: {"checksumMd5": vd.md5((ROOT / n).read_bytes()), "body": {"content": (ROOT / n).read_text()}} for n in g.NEW_FILES}
    files["layout/theme.liquid"] = {"checksumMd5": "x", "body": {"content": lay}}
    files["templates/product.json"] = {"checksumMd5": "x", "body": {"content": prod}}
    monkeypatch.setattr(vd, "read_files", lambda q, t, names: files)
    assert tc.file_problems(None, "1", ["templates/product.json"]) == []
    files["templates/product.json"] = {"checksumMd5": "x", "body": {"content": (snap / "templates__product.json").read_text()}}
    assert tc.file_problems(None, "1", ["templates/product.json"]) == [
        "templates/product.json: the link section is not directly after the reviews section"]


def test_the_theme_check_covers_every_product_template_in_use(monkeypatch):
    """The Batch A failure: a mapped product on product.Bundle.json, which had no link section."""
    import verified_theme_check as tc
    snap = sorted((ROOT / "data/verified/golive").glob("main-*-snapshot"))[0]
    files = {n: {"checksumMd5": vd.md5((ROOT / n).read_bytes()), "body": {"content": (ROOT / n).read_text()}} for n in g.NEW_FILES}
    files["layout/theme.liquid"] = {"checksumMd5": "x", "body": {"content": vd.patch_layout((snap / "layout__theme.liquid").read_text())}}
    files["templates/product.json"] = {"checksumMd5": "x", "body": {"content": vd.patch_product((snap / "templates__product.json").read_text())}}
    files["templates/product.Bundle.json"] = {"checksumMd5": "x", "body": {"content": (snap / "templates__product.json").read_text()}}
    monkeypatch.setattr(vd, "read_files", lambda q, t, names: files)
    assert tc.file_problems(None, "1", ["templates/product.json", "templates/product.Bundle.json"]) == [
        "templates/product.Bundle.json: the link section is not directly after the reviews section"]


def test_a_layout_without_the_unknown_path_guard_fails_the_theme_check(monkeypatch):
    import verified_theme_check as tc
    snap = sorted((ROOT / "data/verified/golive").glob("main-*-snapshot"))[0]
    files = {n: {"checksumMd5": vd.md5((ROOT / n).read_bytes()), "body": {"content": (ROOT / n).read_text()}} for n in g.NEW_FILES}
    lay = vd.patch_layout((snap / "layout__theme.liquid").read_text()).replace(vd.UNKNOWN_MARK, "x")
    files["layout/theme.liquid"] = {"checksumMd5": "x", "body": {"content": lay}}
    files["templates/product.json"] = {"checksumMd5": "x", "body": {"content": vd.patch_product((snap / "templates__product.json").read_text())}}
    monkeypatch.setattr(vd, "read_files", lambda q, t, names: files)
    assert tc.file_problems(None, "1", ["templates/product.json"]) == ["layout/theme.liquid lacks the unknown-path guard"]


# ------------------------------------------------ unknown paths: mutation tests --

HUB_URL = "https://inhousewellness.com/pages/sauna-database"
REAL_HUB = (f'<html><head><link rel="canonical" href="{HUB_URL}"></head><body>'
            '<table class="inhv-table" data-inhv="table"><tr data-inh-id="a"></tr></table></body></html>')
UNKNOWN_URL = HUB_URL + "/no-such-model"
UNKNOWN = ('<html><head><meta name="robots" content="noindex">'
           f'<link rel="canonical" href="{UNKNOWN_URL}"></head><body><article data-inhv="unknown-path">'   # Shopify's own
           '<h1>This model page isn&#39;t available.</h1><p><a href="/pages/sauna-database">Browse</a></p></article></body></html>')


def test_the_real_hub_passes():
    assert g.real_hub_problems(REAL_HUB, HUB_URL) == []


@pytest.mark.parametrize("mutation", [
    lambda h: h.replace('<link rel="canonical" href="https://inhousewellness.com/pages/sauna-database">', ""),
    lambda h: h.replace("</head>", '<meta name="robots" content="noindex"></head>'),
    lambda h: h.replace('data-inhv="table"', ""),
])
def test_a_broken_real_hub_is_caught(mutation):
    assert g.real_hub_problems(mutation(REAL_HUB), HUB_URL)


def test_the_unknown_path_render_passes():
    assert g.unknown_path_problems(UNKNOWN, UNKNOWN_URL) == []


@pytest.mark.parametrize("mutation", [
    lambda h: h.replace('<meta name="robots" content="noindex">', ""),                                   # no noindex
    lambda h: h.replace(f'href="{UNKNOWN_URL}"', f'href="{HUB_URL}"'),                                    # canonical elsewhere
    lambda h: h.replace("</head>", f'<link rel="canonical" href="{UNKNOWN_URL}"></head>'),                # two canonicals
    lambda h: h.replace("</body>", '<script type="application/ld+json">{}</script></body>'),            # structured data
    lambda h: h.replace("This model page isn&#39;t available.", "Sauna"),                                # no message
    lambda h: h.replace("</body>", '<table data-inhv="table"><tr data-inh-id="a"></tr></table></body>'),  # the table
])
def test_a_broken_unknown_path_is_caught(mutation):
    assert g.unknown_path_problems(mutation(UNKNOWN), UNKNOWN_URL)


# ------------------------------------------------ similar models: series and criteria --

def test_one_model_per_series_nearest_capacity():
    import verified_pages as _vp
    items = [json.loads(p.read_text()) for p in (ROOT / "out/verified/pages").glob("*.json")]
    recs = {x["inh_id"]: x for x in _vp.load_dataset()["records"]}
    mapped = _vp.load_navigation()["mapped"]
    by_ph = {}
    for i, m in mapped.items():
        if i in recs:
            by_ph.setdefault(m["product_handle"], []).append(recs[i])
    for pd in items:
        if pd["similar"]:
            keys = [_vp.series_key(by_ph[i["url"].split("/")[-1]][0]) for i in pd["similar"]["items"]]
            assert len(set(keys)) == len(keys), pd["handle"]


def test_the_criteria_line_states_exactly_the_criteria_used(ds):
    import verified_pages as _vp
    for p in (ROOT / "out/verified/pages").glob("*.json"):
        pd = json.loads(p.read_text())
        if pd["similar"]:
            want = _vp.CRITERIA_FULL if _vp.ok(ds[pd["inh_id"]]["placement"]) else _vp.CRITERIA_HEAT
            assert pd["similar"]["criteria"] == want, pd["handle"]


def test_a_wrong_criteria_line_is_caught(ds):
    def m(p):
        p["similar"]["criteria"] = "Same heat type, similar capacity"      # Solara's placement IS verified
    h, pd = page(ds, NOT_SOLD, m)
    assert any("criteria line" in e for e in errs_for(ds, NOT_SOLD, h, pd["title"]))


def test_two_variants_of_one_series_are_caught(ds):
    iid = "sauna/sun-home/eclipse2"

    def m(p):
        p["similar"]["items"] = [{"title": "Heming", "url": "/products/dynamic-low-infrared-sauna-heming"},
                                 {"title": "Heming Elite", "url": "/products/dynamic-saunas-heming"}]
    h, pd = page(ds, iid, m)
    assert any("one series" in e for e in errs_for(ds, iid, h, pd["title"]))


def test_the_clock_derived_delivery_date_is_the_only_thing_neutralised():
    a = "<div>Order Now to Receive it By: October 12, 2026 Canadian Red Cedar</div>"
    assert g.norm(a) == g.norm(a.replace("October 12", "October 13"))
    assert g.norm(a) != g.norm(a.replace("Canadian Red Cedar", "Canadian Hemlock"))      # real text still counts
    assert g.norm(a) != g.norm(a.replace("Receive it By", "Ships by"))


def test_similar_links_are_read_from_the_block_only():
    page = ('<a href="/products/elsewhere">x</a><section data-inhv="similar"><ul>'
            '<li><a href="/products/a">A</a></li><li><a href="/products/b">B</a></li></ul></section>')
    assert g.similar_links(page) == ["a", "b"]
    assert g.similar_links("<p>no block</p>") == []


def test_the_staged_sentence_is_gone_from_the_methodology_build():
    assert "published in stages" not in (ROOT / "scripts/verified_pages.py").read_text()


def test_a_page_body_is_compared_as_visible_text_not_bytes():
    """Shopify pretty-prints markup on save; words must still match exactly."""
    sent = "<dl><dt>Listed</dt><dd>The manufacturer&#x27;s page.</dd></dl>"

    def q(query, v=None):
        if "pageUpdate" in query:
            return {"pageUpdate": {"page": {"id": "p"}, "userErrors": []}}
        return {"page": {"id": "p", "templateSuffix": "t", "isPublished": True, "body": body[0]}}

    body = ["<dl>\n<dt>Listed</dt>\n<dd>The manufacturer's page.</dd>\n</dl>"]
    vd.page_update_checked(q, "p", {"body": sent}, "t")                  # reformatted: accepted
    body[0] = "<dl>\n<dt>Listed</dt>\n<dd>The retailer's page.</dd>\n</dl>"
    with pytest.raises(SystemExit):
        vd.page_update_checked(q, "p", {"body": sent}, "t")              # a word changed: halts
