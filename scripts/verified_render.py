#!/usr/bin/env python3
"""INH Verified — render the theme's OWN Liquid templates locally against real records.

    .venv/bin/python scripts/verified_render.py              # out/verified/render/*.html
    .venv/bin/python scripts/verified_render.py --shots      # + desktop and 390px screenshots

WHY LOCAL (Part A decision D-D). Draft metaobject entries and hidden pages do not render
on the storefront, not even under ?preview_theme_id=. So the pages are verified by
rendering the exact files that deploy to the theme (sections/inh-verified-*.liquid,
snippets/inh-verified-fact.liquid, assets/inh-verified.*) with python-liquid, inside the
store's real header and footer (one live page, fetched read-only, scripts removed). Real
storefront screenshots are the first go-live step.

What the harness supplies, and nothing more:
  * `metaobject.page_data.value`, `metaobjects.sauna.values`, `page`, `shop.url`, and
    `product.metafields.inh_verified.sauna.value` -- the objects Shopify would supply;
  * Shopify's filters these files use: asset_url, stylesheet_tag, json;
  * `{% paginate %}` and `{% schema %}` are Shopify tags python-liquid lacks; the harness
    removes the tag lines and renders their body unchanged.
The <title>, canonical and meta description are rendered from the preview theme's own
layout/theme.liquid head block (patched), so the checks read what the layout would emit.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "out/verified/render"
PAGES = ROOT / "out/verified/pages"
SHELL_SRC = OUT / "shell-source.html"
LAYOUT_SNAPSHOT = ROOT / "out/verified/deploy/theme-146278776899-layout-theme.liquid"
SHOP_URL = "https://inhousewellness.com"
SHELL_URL = SHOP_URL + "/pages/contact"


def env():
    from liquid import Environment, FileSystemLoader

    class Loader(FileSystemLoader):
        """`render 'x'` resolves to snippets/x.liquid, as in a Shopify theme."""
        def get_source(self, environment, template_name):
            name = template_name if "/" in template_name else f"snippets/{template_name}"
            name = name if name.endswith(".liquid") else name + ".liquid"
            src = super().get_source(environment, name)
            return src.__class__(strip_shopify_tags(src.source), src.filename, src.uptodate)

    e = Environment(loader=Loader(str(ROOT)))
    e.add_filter("asset_url", lambda name: f"assets/{name}")
    e.add_filter("stylesheet_tag", lambda url: f'<link href="{url}" rel="stylesheet" type="text/css" media="all" />')
    e.add_filter("json", lambda v: json.dumps(v, ensure_ascii=False))
    return e


def strip_shopify_tags(src: str) -> str:
    src = re.sub(r"(?s)\{%-?\s*schema\s*-?%\}.*?\{%-?\s*endschema\s*-?%\}", "", src)
    src = re.sub(r"\{%-?\s*paginate\b[^%]*-?%\}", "", src)
    return re.sub(r"\{%-?\s*endpaginate\s*-?%\}", "", src)


def render_file(e, rel: str, ctx: dict) -> str:
    return e.from_string(strip_shopify_tags((ROOT / rel).read_text())).render(**ctx)


def entry(p: dict) -> dict:
    """A `sauna` metaobject as Liquid sees it: fields expose `.value`; system.url is the page."""
    f = {k: {"value": p[k]} for k in ("title", "inh_id", "brand", "heat_type", "capacity_label",
                                       "supply_voltage", "placement", "verified_date")}
    f["page_data"] = {"value": p}
    f["system"] = {"url": p["path"], "handle": p["handle"]}
    return f


def head_block(kind: str, title: str, description: str, canonical: str) -> str:
    """The <title>, canonical and meta description, rendered from the theme's own layout."""
    from liquid import Environment
    lay = LAYOUT_SNAPSHOT.read_text()
    t = re.search(r"(?s)<title>.*?</title>", lay).group(0)
    m = re.search(r"(?s)\{%- elsif page_description -%\}\s*(<meta\s+name=\"description\"\s+content=\".*?\"\s*>)", lay).group(1)
    ctx = {"page_title": title, "page_description": description, "shop": {"name": "inhousewellness"},
           "canonical_url": canonical, "paginate": {"current_page": 1}, "current_tags": [],
           "collection": None, "article": None, "product": None, "template": kind}
    if kind == "metaobject":
        ctx["metaobject"] = {"title": title}
    if kind == "page":
        ctx["page"] = {"title": title}
    e = Environment()
    e.add_filter("escape", lambda s: html.escape(str(s), quote=True))
    title_html = re.sub(r"\s+", " ", e.from_string(t).render(**ctx)).replace("<title> ", "<title>").replace(" </title>", "</title>")
    return (f'{title_html}\n<link rel="canonical" href="{canonical}">\n'
            + re.sub(r"\s+", " ", e.from_string(m).render(**ctx)))


def shell() -> str:
    if not SHELL_SRC.exists():
        import urllib.request
        req = urllib.request.Request(SHELL_URL, headers={"User-Agent": "INH-Verified-render/0.1 (+https://inhousewellness.com)"})
        SHELL_SRC.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    s = SHELL_SRC.read_text()
    s = re.sub(r"(?is)<script\b.*?</script>", "", s)
    s = re.sub(r"(?is)<title>.*?</title>|<link[^>]*rel=\"canonical\"[^>]*>|<meta[^>]*name=\"description\"[^>]*>", "", s)
    s = s.replace('href="//', 'href="https://').replace("src=\"//", "src=\"https://")
    return s


def wrap(sh: str, head: str, main: str) -> str:
    out = re.sub(r"(?is)(<main id=\"MainContent\"[^>]*>).*?(</main>)", lambda m: m.group(1) + main + m.group(2), sh, count=1)
    return out.replace("</head>", head + "\n</head>", 1)


def render_all(nav_mapped: dict | None = None) -> dict:
    import verified_pages as vp
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    for a in ("inh-verified.css", "inh-verified.js"):
        shutil.copy(ROOT / "assets" / a, OUT / "assets" / a)
    e = env()
    sh = shell()
    from verified_deploy import page_descriptions
    descs = page_descriptions()
    pages = [json.loads(p.read_text()) for p in sorted(PAGES.glob("*.json"))]
    pages.sort(key=lambda p: (p["brand"], p["title"]))
    written = {}
    shop = {"url": SHOP_URL, "name": "inhousewellness"}
    for p in pages:
        main = render_file(e, "sections/inh-verified-model.liquid",
                           {"metaobject": {"page_data": {"value": p}}, "shop": shop})
        head = head_block("metaobject", p["seo_title"], p["seo_description"], p["url"])
        out = OUT / "model" / f"{p['handle']}.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(wrap(sh, head, main).replace('href="assets/', 'href="../assets/').replace('src="assets/', 'src="../assets/'))
        written[p["handle"]] = out
    hub_main = render_file(e, "sections/inh-verified-hub.liquid",
                           {"metaobjects": {"sauna": {"values": [entry(p) for p in pages]}},
                            "page": {"title": "Verified Sauna Database"}, "shop": shop})
    (OUT / "hub.html").write_text(wrap(sh, head_block("page", "Verified Sauna Database", descs["sauna-database"], SHOP_URL + vp.HUB_PATH), hub_main))
    body = (ROOT / "out/verified/methodology.html").read_text()
    m_main = render_file(e, "sections/inh-verified-methodology.liquid",
                         {"page": {"title": "How the Sauna Database Is Verified", "content": body}, "shop": shop})
    (OUT / "methodology.html").write_text(wrap(sh, head_block("page", "How the Sauna Database Is Verified", descs["sauna-database-methodology"],
                                                                 SHOP_URL + vp.METHOD_PATH), m_main))
    # The product-page line, rendered for a mapped product and for an unmapped one.
    first_sold = next(p for p in pages if p["store"]["sold"])
    link_on = render_file(e, "sections/inh-verified-product-link.liquid",
                          {"product": {"metafields": {"inh_verified": {"sauna": {"value": entry(first_sold)}}}}})
    link_off = render_file(e, "sections/inh-verified-product-link.liquid",
                           {"product": {"metafields": {"inh_verified": {"sauna": {"value": None}}}}})
    (OUT / "product-link-mapped.html").write_text(link_on)
    (OUT / "product-link-unmapped.html").write_text(link_off)
    return {"models": written, "hub": OUT / "hub.html", "methodology": OUT / "methodology.html",
            "link_example": first_sold["handle"]}


def shots(targets: list[tuple[str, Path]], js: bool = True):
    from playwright.sync_api import sync_playwright
    shot_dir = OUT / "shots"
    shot_dir.mkdir(exist_ok=True)
    made = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for label, path in targets:
            for vw, name in ((1280, "desktop"), (390, "mobile")):
                ctx = b.new_context(viewport={"width": vw, "height": 900}, java_script_enabled=js,
                                    device_scale_factor=1)
                pg = ctx.new_page()
                pg.goto(path.resolve().as_uri(), wait_until="load", timeout=90000)
                pg.wait_for_timeout(800)
                main = pg.locator("#MainContent")
                f = shot_dir / f"{label}-{name}{'' if js else '-nojs'}.png"
                main.screenshot(path=str(f))
                made.append(f)
                ctx.close()
        b.close()
    return made


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", nargs="*", default=None, help="handles to photograph (plus hub and methodology)")
    a = ap.parse_args(argv)
    res = render_all()
    print(f"rendered {len(res['models'])} model pages, hub, methodology -> {OUT.relative_to(ROOT)}")
    if a.shots is not None:
        t = [("hub", res["hub"]), ("methodology", res["methodology"])] + \
            [(f"model-{h}", res["models"][h]) for h in a.shots]
        made = shots(t)
        made += shots([("hub", res["hub"])], js=False)
        print("\n".join(str(m.relative_to(ROOT)) for m in made))
    return 0


if __name__ == "__main__":
    sys.exit(main())
