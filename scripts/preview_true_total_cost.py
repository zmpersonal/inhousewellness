#!/usr/bin/env python3
"""Render the True Total Cost section to a local HTML file, for verification.

WHAT THIS IS, AND WHAT IT IS NOT
Shopify is unreachable from this environment: `inhousewellness.myshopify.com`
and `admin.shopify.com` both answer 403 on CONNECT from the egress proxy, so a
theme preview URL cannot be loaded or screenshotted here. This harness renders
the same section against the same assets so the SIX STATES can be exercised and
photographed. It is NOT a claim about the live theme, and the screenshots it
produces must never be described as the preview URL.

Two things make it worth trusting anyway:

  * `assets/inh-cost-core.js`, `assets/inh-true-total-cost.js`,
    `assets/inh-true-total-cost.css` and the two JSON assets are the SAME BYTES
    the theme gets. The arithmetic and the states are therefore identical; only
    Liquid's own wrapper differs.
  * The renderer handles exactly the Liquid this section uses, and then asserts
    that NO unrendered Liquid remains. If the section grows a construct this
    file does not know, the output carries `{{` or `{%` and the run HALTS. A
    preview that silently drops a tag would be a picture of a page that does not
    exist -- this project's oldest failure shape, in a screenshot.

    python3 scripts/preview_true_total_cost.py
    python3 scripts/preview_true_total_cost.py --self-test
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "preview" / "true-total-cost"

SHOP_NAME = "InHouse Wellness"
ORIGIN = "https://inhousewellness.com"

COMMENT = re.compile(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", re.S)
SCHEMA = re.compile(r"\{%\s*schema\s*%\}.*?\{%\s*endschema\s*%\}", re.S)
LIQUID_TAG = re.compile(r"\{%-?\s*liquid\s.*?-?%\}", re.S)
UNLESS = re.compile(r"\{%-?\s*unless\s+ttc_emit_schema\s*-?%\}(.*?)\{%-?\s*endunless\s*-?%\}", re.S)
ASSIGN = re.compile(r"\{%-?\s*assign[^%]*?-?%\}")
ASSET = re.compile(r"\{\{\s*'([^']+)'\s*\|\s*asset_url\s*\}\}")
ASSET_CSS = re.compile(r"\{\{\s*'([^']+)'\s*\|\s*asset_url\s*\|\s*stylesheet_tag\s*\}\}")
ASSET_JSON_ORIGIN = re.compile(
    r"\{\{\s*'([^']+)'\s*\|\s*asset_url\s*\|\s*prepend:\s*request\.origin\s*\|\s*json\s*\}\}")
SETTING_JSON = re.compile(r"\{\{\s*section\.settings\.(\w+)\s*\|\s*json\s*\}\}")
SETTING = re.compile(r"\{\{\s*section\.settings\.(\w+)\s*\}\}")
SHOP_JSON = re.compile(r"\{\{\s*shop\.name\s*\|\s*json\s*\}\}")
PATH_JSON = re.compile(
    r"\{\{\s*request\.origin\s*\|\s*append:\s*request\.path\s*\|\s*json\s*\}\}")
COLL = re.compile(r"\{\{\s*coll\s*\}\}")
LEFTOVER = re.compile(r"\{\{|\{%")

# The section's own default, restated here ONCE and asserted against the Liquid
# by `self_test`. Two copies of a default that drift apart is how a preview stops
# being a preview.
COLL_DEFAULT = "/collections/saunas"


def render(liquid, settings, page_path, asset_base):
    """The section's Liquid, with exactly the constructs it uses resolved."""
    s = COMMENT.sub("", liquid)
    s = SCHEMA.sub("", s)
    s = LIQUID_TAG.sub("", s)
    s = ASSIGN.sub("", s)
    s = UNLESS.sub(lambda m: m.group(1), s)            # first render emits it
    coll = settings.get("collection_url") or COLL_DEFAULT
    s = COLL.sub(coll, s)
    s = ASSET_JSON_ORIGIN.sub(
        lambda m: json.dumps(ORIGIN + "/cdn/shop/t/1/assets/" + m.group(1)), s)
    s = ASSET_CSS.sub(
        lambda m: '<link rel="stylesheet" href="%s%s">' % (asset_base, m.group(1)), s)
    s = ASSET.sub(lambda m: asset_base + m.group(1), s)
    s = SETTING_JSON.sub(lambda m: json.dumps(settings.get(m.group(1), "")), s)
    s = SETTING.sub(lambda m: settings.get(m.group(1), ""), s)
    s = SHOP_JSON.sub(json.dumps(SHOP_NAME), s)
    s = PATH_JSON.sub(json.dumps(ORIGIN + page_path), s)
    return s


def unrendered(html):
    """Every remaining Liquid delimiter, with a little context. Empty is the
    only acceptable answer; a preview holding a raw tag is not the page."""
    return [html[max(0, m.start() - 40):m.start() + 60].replace("\n", " ")
            for m in LEFTOVER.finditer(html)]


PAGE_SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — local harness, NOT the live theme</title>
<style>body{{margin:0;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,Helvetica,Arial,sans-serif;background:#fbfaf8;color:#1b1613}}
.harness{{background:#1b1613;color:#e9e5dd;font-size:.75rem;padding:.45rem .9rem}}</style>
</head><body>
<p class="harness">LOCAL HARNESS — same section, same assets, not the Shopify preview URL.</p>
{body}
</body></html>
"""


def build():
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for tpl in sorted((ROOT / "templates").glob("page.sauna-*.json")):
        handle = tpl.stem.replace("page.", "")
        settings = json.loads(tpl.read_text())["sections"]["main"]["settings"]
        body = render(liquid, settings, "/pages/" + handle, "../../assets/")
        left = unrendered(body)
        if left:
            sys.exit("HALT: unrendered Liquid in %s:\n  %s"
                     % (handle, "\n  ".join(left[:5])))
        dest = OUT / (handle + ".html")
        dest.write_text(PAGE_SHELL.format(title=settings["heading"], body=body))
        written.append(dest)
    return written


def self_test():
    fails = []
    liquid = (ROOT / "sections" / "true-total-cost.liquid").read_text()
    settings = json.loads((ROOT / "templates" / "page.sauna-cost.json").read_text()
                          )["sections"]["main"]["settings"]
    html = render(liquid, settings, "/pages/sauna-cost", "../../assets/")

    if unrendered(html):
        fails.append("the section still holds Liquid after rendering: %r"
                     % unrendered(html)[:2])
    if "{% schema %}" in html or '"presets"' in html:
        fails.append("the schema block leaked into the rendered page")
    for want in ("data-inh-ttc", "inh-cost-core.js", "inh-zip-state.json",
                 'name="zip"', 'name="decline_kw"', "SoftwareApplication"):
        if want not in html:
            fails.append("rendered page is missing %r" % want)

    # The JSON-LD must PARSE, and must not re-emit a type Avada already owns.
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if len(blocks) != 1:
        fails.append("expected exactly one JSON-LD block, got %d" % len(blocks))
    for b in blocks:
        try:
            doc = json.loads(b)
        except Exception as e:
            fails.append("JSON-LD does not parse: %s" % e)
            continue
        types = {n["@type"] for n in doc["@graph"]}
        if types != {"Dataset", "SoftwareApplication"}:
            fails.append("JSON-LD emits %s; only Dataset and SoftwareApplication "
                         "are ours -- Avada owns the rest" % sorted(types))

    # The default this harness restates must still be the section's default.
    if ("assign coll = '%s'" % COLL_DEFAULT) not in liquid:
        fails.append("the section's collection default has drifted from the "
                     "harness's copy of it (%r)" % COLL_DEFAULT)

    # The unrendered-Liquid guard must actually fire, or it proves nothing.
    if not unrendered("a {{ product.title }} b"):
        fails.append("the unrendered-Liquid guard does not detect an output tag")
    if not unrendered("a {% if x %} b"):
        fails.append("the unrendered-Liquid guard does not detect a logic tag")

    # The number has to be in the first 40 words, and it has to be a NUMBER.
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    first40 = " ".join(text.split(" ")[:40])
    if not re.search(r"\d", first40):
        fails.append("no number in the first 40 words: %r" % first40[:160])
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: the preview harness failed its own controls:\n  "
                     + "\n  ".join(fails))
        print("preview harness self-test: the section renders with no Liquid "
              "left, one JSON-LD block, and only the two types that are ours")
        return
    for p in build():
        print("wrote", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
