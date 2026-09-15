"""The discover-mode evidence collector, exercised offline.

Discover run 3 reported robots.txt and homepage reachability for 11 vendors and
nothing else, so there was no product-URL evidence to fill product_url_template
from and all 11 stayed null. This module tests the evidence collector that fixes
that -- against synthetic sitemaps, because no manufacturer host is reachable
from a session (403 on CONNECT). A parser that has only ever run against live
data we cannot see is a parser nobody has checked.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.fetch_manufacturer_specs as M  # noqa: E402

REGISTRY = json.loads((ROOT / "data" / "manufacturer-registry.json").read_text())
DISCOVERY = ROOT / "data" / "facts" / "manufacturer-discovery.json"


# ── what counts as a product URL ─────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/products/catalonia-8p", "/product/fd-kn001",
                                  "/shop/mx-j206-01", "/p/rip-tau",
                                  "/products/thing/"])
def test_product_paths_match(path):
    assert M.PRODUCT_PATH_RX.match(path), path


@pytest.mark.parametrize("path", [
    "/collections/best-infrared-saunas",   # the exact page that once answered a
                                           # product request and put a category
                                           # FAQ into a report as a product spec
    "/blogs/news/how-to-choose",
    "/products",                           # the listing, not an item
    "/products/",
    "/products/cat/sub",                   # two segments deep: not an item page
    "/pages/warranty",
    "/",
])
def test_non_product_paths_are_rejected(path):
    assert not M.PRODUCT_PATH_RX.match(path), path


# ── the evidence collector ───────────────────────────────────────────────────

class StubHost:
    """Stands in for a manufacturer host. `disallow` is a substring test, which
    is enough to prove the robots check is consulted before each sitemap."""

    def __init__(self, sitemaps, pages, disallow=None):
        self.base = "https://vendor.example/"
        self._sitemaps = sitemaps
        self.pages = pages
        self.disallow = disallow
        self.requested = []

        class RP:
            def site_maps(_self):
                return list(sitemaps) or None
        self.rp = RP()

    def allowed(self, url):
        return not (self.disallow and self.disallow in url)

    def wait(self):
        pass


def _install(monkeypatch, host):
    def fake_fetch_bytes(h, url, attempts=3):
        h.requested.append(url)
        if url not in h.pages:
            raise M.urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        body = h.pages[url]
        return (body if isinstance(body, bytes) else body.encode()), url
    monkeypatch.setattr(M, "fetch_bytes", fake_fetch_bytes)


URLSET = """<?xml version="1.0"?><urlset>
 <url><loc>https://vendor.example/products/mx-j206-01-cedar</loc></url>
 <url><loc>https://vendor.example/products/mx-k306-01</loc></url>
 <url><loc>https://vendor.example/collections/all-saunas</loc></url>
 <url><loc>https://vendor.example/blogs/news/emf-explained</loc></url>
 <url><loc>https://vendor.example/pages/warranty</loc></url>
</urlset>"""

INDEX = """<?xml version="1.0"?><sitemapindex>
 <sitemap><loc>https://vendor.example/sitemap_products_1.xml</loc></sitemap>
</sitemapindex>"""


def test_sitemap_index_is_followed_one_level(monkeypatch):
    host = StubHost(["https://vendor.example/sitemap.xml"],
                    {"https://vendor.example/sitemap.xml": INDEX,
                     "https://vendor.example/sitemap_products_1.xml": URLSET})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", set())
    assert len(ev["sitemaps_read"]) == 2
    assert ev["product_urls_seen"] == 2, ev
    assert ev["product_paths"] == {"/products/": 2}
    assert all("/products/" in u for u in ev["sample_product_urls"])


def test_non_product_urls_are_not_counted_as_products(monkeypatch):
    host = StubHost(["https://vendor.example/sitemap.xml"],
                    {"https://vendor.example/sitemap.xml": URLSET})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", set())
    joined = " ".join(ev["sample_product_urls"])
    assert "/collections/" not in joined and "/blogs/" not in joined


def test_our_sku_found_in_their_url_is_reported(monkeypatch):
    """The decisive evidence: a template is only possible if their URLs carry a
    key we hold."""
    host = StubHost(["https://vendor.example/sitemap.xml"],
                    {"https://vendor.example/sitemap.xml": URLSET})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", {"MX-K306-01"})
    assert [m["sku"] for m in ev["sku_matches"]] == ["MX-K306-01"]
    assert ev["sku_matches"][0]["url"].endswith("/products/mx-k306-01")


def test_sku_spacing_variants_are_tried(monkeypatch):
    """Our catalogue holds `MX-M356-01-FS CED` with a space. A vendor URL would
    never contain the space, so the match has to try the obvious renderings."""
    pages = {"https://vendor.example/sitemap.xml":
             '<urlset><url><loc>https://vendor.example/products/mx-m356-01-fs-ced'
             '</loc></url></urlset>'}
    host = StubHost(["https://vendor.example/sitemap.xml"], pages)
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", {"MX-M356-01-FS CED"})
    assert ev["sku_matches"], ev
    assert ev["sku_matches"][0]["as"] == "MX-M356-01-FS-CED"


def test_no_sku_match_is_reported_as_empty_not_guessed(monkeypatch):
    """Products exist, but keyed on something we do not hold. The collector must
    say so plainly — this is the case where NO template is possible."""
    host = StubHost(["https://vendor.example/sitemap.xml"],
                    {"https://vendor.example/sitemap.xml": URLSET})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", {"FD-KN001"})
    assert ev["product_urls_seen"] == 2
    assert ev["sku_matches"] == []


def test_robots_is_consulted_before_each_sitemap(monkeypatch):
    host = StubHost(["https://vendor.example/sitemap.xml"],
                    {"https://vendor.example/sitemap.xml": URLSET},
                    disallow="sitemap.xml")
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", set())
    assert host.requested == [], "a disallowed sitemap was requested anyway"
    assert any("robots disallows" in e for e in ev["sitemap_errors"])


def test_falls_back_to_conventional_locations_and_says_so(monkeypatch):
    host = StubHost([], {"https://vendor.example/sitemap.xml": URLSET})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", set())
    assert ev["sitemap_source"].startswith("conventional")
    assert ev["sitemaps_declared"] == []
    assert ev["product_urls_seen"] == 2
    # exactly two conventional paths tried, never a scan
    assert len(host.requested) <= 2


def test_a_missing_sitemap_is_an_error_not_a_crash(monkeypatch):
    host = StubHost(["https://vendor.example/nope.xml"], {})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", set())
    assert ev["product_urls_seen"] == 0
    assert any("HTTPError" in e for e in ev["sitemap_errors"])


def test_gzipped_sitemaps_decode():
    import gzip
    raw = gzip.compress(URLSET.encode())
    assert "<loc>" in M._decode(raw, "https://vendor.example/sitemap.xml.gz")
    # and a non-.gz url is passed through untouched
    assert "<loc>" in M._decode(URLSET.encode(), "https://vendor.example/s.xml")


def test_homepage_links_are_harvested_from_the_body_already_fetched(monkeypatch):
    html = ('<a href="/products/fd-kn001">A</a>'
            "<a href='https://vendor.example/products/fd-kn002'>B</a>"
            '<a href="/collections/all">C</a><a href="/pages/about">D</a>')
    host = StubHost([], {})
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, html, set())
    assert ev["homepage_product_links"] == [
        "https://vendor.example/products/fd-kn001",
        "https://vendor.example/products/fd-kn002"]


def test_sitemap_count_is_capped(monkeypatch):
    index = "<sitemapindex>" + "".join(
        f"<sitemap><loc>https://vendor.example/s{i}.xml</loc></sitemap>"
        for i in range(50)) + "</sitemapindex>"
    pages = {"https://vendor.example/sitemap.xml": index}
    pages.update({f"https://vendor.example/s{i}.xml": URLSET for i in range(50)})
    host = StubHost(["https://vendor.example/sitemap.xml"], pages)
    _install(monkeypatch, host)
    ev = M.product_url_evidence(host, host.base, "", set())
    assert len(ev["sitemaps_read"]) <= M.MAX_SITEMAPS


# ── the registry's own honesty ───────────────────────────────────────────────

def test_every_template_is_null_until_evidence_supports_one():
    """Run 3's discovery output contains no product-URL evidence for any vendor,
    so every template must still be null. This test is expected to be RELAXED
    per-vendor as evidence arrives — deleting a vendor from here requires
    sample_product_urls and sku_matches in the discovery file."""
    ev_by_vendor = {}
    if DISCOVERY.exists():
        for rec in json.loads(DISCOVERY.read_text())["vendors"]:
            ev_by_vendor[rec["vendor"]] = rec.get("product_url_evidence") or {}
    for vendor, entry in REGISTRY["vendors"].items():
        if entry["product_url_template"] is None:
            continue
        ev = ev_by_vendor.get(vendor, {})
        assert ev.get("sample_product_urls"), (
            f"{vendor}: product_url_template is set but the discovery file holds "
            f"no sample product URL for it — that is a guess")
        assert ev.get("sku_matches"), (
            f"{vendor}: product_url_template is set but no real URL of theirs was "
            f"shown to contain one of our SKUs, so nothing can be substituted")


def test_no_discovered_redirect_is_left_unactioned():
    """A base that redirects to a different host is stale, and run 3 found one:
    www.goldendesignsinc.com -> goldendesigninc.com (no 's').

    Written carefully, because the naive version of this test fails as soon as it
    succeeds. Comparing the registry's base against a COMMITTED discovery record
    goes stale the moment either is legitimately updated — the same shape as
    asserting drift-freedom against a fact baseline. So each record is judged
    against the base it was actually probing:

      the record probed the base we still hold  -> that base must not redirect away
      the record probed a base we have since changed -> the change must have been
                                                        TO the host that answered,
                                                        not to something invented
    """
    if not DISCOVERY.exists():
        pytest.skip("no discovery output yet")
    import urllib.parse as up
    host_of = lambda u: up.urlsplit(u).netloc.removeprefix("www.")  # noqa: E731
    for rec in json.loads(DISCOVERY.read_text())["vendors"]:
        final = rec.get("final_url")
        if not final:
            continue
        vendor = rec["vendor"]
        probed, answered = host_of(rec["base"]), host_of(final)
        current = host_of(REGISTRY["vendors"][vendor]["base"])
        if current == probed:
            assert answered == probed, (
                f"{vendor}: the registry still points at {probed} but it redirects "
                f"to {answered} — update the base, as was done for Golden Designs")
        else:
            assert current == answered, (
                f"{vendor}: the registry base was changed from {probed} to "
                f"{current}, but the host that actually answered was {answered}. A "
                f"correction must go to the host the run reached, not elsewhere.")
