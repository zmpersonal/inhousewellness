#!/usr/bin/env python3
"""INH Verified Round 2 — render-side checks on the locally rendered pages.

    .venv/bin/python scripts/verified_checks.py            # offline checks (exit 1 on any failure)
    .venv/bin/python scripts/verified_checks.py --links    # + link check (online, polite)
    .venv/bin/python scripts/verified_checks.py --nojs     # + hub row count with JavaScript disabled

Reads the HTML produced by scripts/verified_render.py and compares it with
data/verified/saunas.json INDEPENDENTLY of the page builder: values are resolved from
the dataset by the row's own data-field path, so a builder bug cannot vouch for itself.

  1. value match   every displayed value equals the dataset value at its path, with the
                   same grade and source; every number in the visible text is a number of
                   that value; every gap is a field the dataset does not verify; every
                   verified key/electrical field is shown; H1 is the approved title; the
                   answer sentence and meta description use only numbers the record verifies;
                   hub rows match the dataset; quoted text is a substring of its evidence.
  2. forbidden     no price or currency string, no "Infinite Sauna", no "Not stated on the
                   manufacturer's page", in rendered pages, page data, templates or assets.
  3. health gate   no banned health claim in any rendered page's visible text.
  4. head          title tag, self-referencing canonical, meta description.
  5. schema.org    every JSON-LD type and property exists in the schema.org vocabulary and is
                   used on a type in its domain; no offers, aggregateRating or review.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
RENDER = ROOT / "out/verified/render"
SCHEMA_VOCAB = ROOT / "out/verified/schemaorg-current-https.jsonld"
VOCAB_URL = "https://schema.org/version/latest/schemaorg-current-https.jsonld"
VERIFIED = {"certified", "documented", "listed", "reviewer_measured"}
PRICE_RX = re.compile(r"(?i)(\"(?:reference_)?price(?:_usd)?\"\s*:|\bprice_usd\b|[$€£]\s?\d|\bUSD\b|\d\s?dollars\b)")
BANNED_RX = re.compile(r"(?i)infinite\s*sauna|infinitesauna|not stated on the manufacturer")
NUM_RX = re.compile(r"\d+(?:\.\d+)?")

FACT_RX = re.compile(r'<div class="inhv-fact[^"]*" data-field="([^"]*)" data-state="([^"]*)" data-grade="([^"]*)" '
                     r'data-raw="([^"]*)"(?: data-source="([^"]*)")?>\s*<dt>(.*?)</dt>\s*<dd>\s*<span class="inhv-v">(.*?)</span>', re.S)


def main_of(page_html: str) -> str:
    m = re.search(r'(?s)<main id="MainContent"[^>]*>(.*)</main>', page_html)
    return m.group(1) if m else ""


def visible(fragment: str) -> str:
    t = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", fragment)
    return htmllib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()


def nums(x) -> set:
    if x is None:
        return set()
    if isinstance(x, bool):
        return set()
    if isinstance(x, (int, float)):
        return {float(x)}
    if isinstance(x, (list, tuple)):
        return set().union(*(nums(v) for v in x)) if x else set()
    if isinstance(x, dict):
        return set().union(*(nums(v) for v in x.values())) if x else set()
    return {float(n) for n in NUM_RX.findall(str(x))}


def resolve(r, path):
    """(value, grade, source_url, ok) for a data-field path, read from the record."""
    if path == "capacity":
        a, b = r["capacity_min"], r["capacity_max"]
        return [a["value"], b["value"]], a["grade"], a.get("source_url"), a["value"] is not None and a["grade"] in VERIFIED
    if path == "dimensions.assembled":
        ax = [r["dimensions"]["assembled"][k] for k in ("width_in", "depth_in", "height_in")]
        return [x["value"] for x in ax], ax[0]["grade"], ax[0].get("source_url"), all(x["value"] is not None and x["grade"] in VERIFIED for x in ax)
    m = re.fullmatch(r"electrical\.circuits\[(\d+)\]", path)
    if m:
        c = r["electrical"]["circuits"][int(m.group(1))]
        g = c["voltage"] if c["voltage"]["value"] is not None else c["stated_amperage"]
        return [c["purpose"]["value"], c["voltage"]["value"], c["stated_amperage"]["value"]], g["grade"], g.get("source_url"), True
    f = r
    for part in path.split("."):
        f = f[part]
    return f.get("value"), f.get("grade"), f.get("source_url"), f.get("value") is not None and f.get("grade") in VERIFIED


def check_model(r, title, page_html, pd, errs):
    main = main_of(page_html)
    where = r["inh_id"]
    facts = FACT_RX.findall(main)
    if not facts:
        errs.append(f"{where}: no fact rows found")
    shown_paths = set()
    for path, state, grade, raw, src, label, text in facts:
        raw_v = json.loads(htmllib.unescape(raw))
        text = htmllib.unescape(text)
        src = htmllib.unescape(src) if src else None
        val, dgrade, dsrc, dok = resolve(r, path)
        if state == "value":
            shown_paths.add(path)
            if raw_v != val:
                errs.append(f"{where} {path}: shows {raw_v!r}, dataset {val!r}")
            if grade != dgrade:
                errs.append(f"{where} {path}: grade {grade} vs dataset {dgrade}")
            if src != dsrc:
                errs.append(f"{where} {path}: source {src} vs dataset {dsrc}")
            if not (dok or dgrade == "claimed"):
                errs.append(f"{where} {path}: displayed a value the dataset does not verify")
            extra = nums(text) - nums(val)
            if extra:
                errs.append(f"{where} {path}: text {text!r} carries numbers {sorted(extra)} not in the dataset value")
        elif state == "gap":
            if dok:
                errs.append(f"{where} {path}: shows 'Not verified' but the dataset verifies {val!r}")
            if text != "Not verified":
                errs.append(f"{where} {path}: gap text {text!r}")
        elif state == "not_applicable":
            if dgrade != "not_applicable":
                errs.append(f"{where} {path}: 'Not applicable' but dataset grade {dgrade}")
        elif state == "see_circuits":
            if dok or not r["electrical"]["circuits"]:
                errs.append(f"{where} {path}: 'see circuits' without circuits, or over a verified value")
        elif state == "option":
            if not r["electrical"].get("option_dependence"):
                errs.append(f"{where} {path}: option-dependence shown without recorded evidence")
    for gpath in re.findall(r'<span data-field="([^"]*)" data-state="gap">', main):
        if resolve(r, gpath)[3]:
            errs.append(f"{where} {gpath}: listed as not verified but the dataset verifies it")
    # completeness: every verified key or electrical value is shown
    import verified_pages as _vp
    need = ["heat_type", "capacity", "dimensions.assembled" if _vp.has_rect_dims(r) else "dimensions.exterior"] + \
           [f"electrical.{k}" for k in ("supply_voltage", "stated_amperage", "circuits_required", "connection_type",
                                         "circuit_requirement", "heater_kw")] + \
           [f"electrical.circuits[{i}]" for i in range(len(r["electrical"]["circuits"]))]
    # ...and in the block the brief puts it in: key facts, or the electrical block
    blocks = {}
    for name in ("key-facts", "electrical"):
        m = re.search(r'(?s)<dl class="inhv-facts" data-inhv="%s">(.*?)</dl>' % name, main)
        blocks[name] = {f[0] for f in FACT_RX.findall(m.group(1)) if f[1] == "value"} if m else set()
    for p in need:
        block = "electrical" if p.startswith("electrical.") else "key-facts"
        if resolve(r, p)[3] and p not in blocks[block]:
            errs.append(f"{where} {p}: verified in the dataset but not displayed in the {block} block")
    h1 = re.search(r'<h1 class="inhv-h1">(.*?)</h1>', main)
    if not h1 or htmllib.unescape(h1.group(1)) != title:
        errs.append(f"{where}: H1 is not the approved title")
    allowed = set()
    for p in need + ["dimensions.assembled", "dimensions.exterior"]:
        v, _, _, good = resolve(r, p)
        if good:
            allowed |= nums(v)
    ans = htmllib.unescape(re.search(r'data-inhv="answer">(.*?)</p>', main).group(1))
    extra = nums(ans.replace(title, "")) - allowed
    if extra:
        errs.append(f"{where}: answer sentence carries unverified numbers {sorted(extra)}")
    desc = re.search(r'<meta name="description" content="([^"]*)"', page_html)
    if desc:
        d = htmllib.unescape(desc.group(1))
        extra = nums(d.replace(title, "")) - allowed
        if extra:
            errs.append(f"{where}: meta description carries unverified numbers {sorted(extra)}")
    # quoted source text must be a substring of the evidence it cites
    evid = [re.sub(r"\s+", " ", ev["evidence"]["snippet"]) for ev in iter_evidence(r)]
    for q in re.findall(r"<q>(.*?)</q>", main, re.S):
        t = htmllib.unescape(q).rstrip("…").strip()
        if len(htmllib.unescape(q)) > 160:
            errs.append(f"{where}: quoted text longer than 160 characters")
        if not any(t in e for e in evid):
            errs.append(f"{where}: quoted text not found in the record's evidence: {t[:60]!r}")
    return facts


def iter_evidence(o):
    if isinstance(o, dict):
        if "evidence" in o and isinstance(o["evidence"], dict) and "snippet" in o["evidence"] and o["evidence"]["snippet"]:
            yield o
        for v in o.values():
            yield from iter_evidence(v)
    elif isinstance(o, list):
        for v in o:
            yield from iter_evidence(v)


def check_head(kind, page_html, expect_title, expect_url, errs, where):
    t = re.search(r"<title>(.*?)</title>", page_html, re.S)
    if not t or htmllib.unescape(t.group(1)).strip() != expect_title:
        errs.append(f"{where}: title tag {t.group(1) if t else None!r} != {expect_title!r}")
    c = re.findall(r'<link rel="canonical" href="([^"]*)"', page_html)
    if c != [expect_url]:
        errs.append(f"{where}: canonical {c} != [{expect_url}]")
    d = re.search(r'<meta name="description" content="([^"]*)"', page_html)
    if not d or not d.group(1).strip():
        errs.append(f"{where}: empty meta description")


# ---------------------------------------------------------------- schema.org --

def vocab():
    if not SCHEMA_VOCAB.exists():
        req = urllib.request.Request(VOCAB_URL, headers={"User-Agent": "INH-Verified-check/0.1"})
        SCHEMA_VOCAB.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    g = json.loads(SCHEMA_VOCAB.read_text())["@graph"]
    classes, props, parents = set(), {}, {}
    ids = lambda v: [x["@id"] for x in (v if isinstance(v, list) else [v])] if v else []
    for n in g:
        t = n.get("@type")
        t = t if isinstance(t, list) else [t]
        nid = n["@id"].replace("schema:", "")
        if "rdfs:Class" in t:
            classes.add(nid)
            # A root class has no rdfs:subClassOf: an explicit empty parent list, not a default.
            parents[nid] = [p.replace("schema:", "") for p in ids(n["rdfs:subClassOf"])] if "rdfs:subClassOf" in n else []
        if "rdf:Property" in t:
            # A property with no declared domain is recorded as such (empty set); the check
            # then accepts it on any type, which is what schema.org's missing domain means.
            props[nid] = ({p.replace("schema:", "") for p in ids(n["schema:domainIncludes"])}
                          if "schema:domainIncludes" in n else set())
    return classes, props, parents


def ancestors(c, parents):
    out, stack = set(), [c]
    while stack:
        x = stack.pop()
        if x in out:
            continue
        out.add(x)
        stack += parents.get(x, [])
    return out


def check_jsonld(obj, where, errs, V):
    classes, props, parents = V
    if isinstance(obj, list):
        for o in obj:
            check_jsonld(o, where, errs, V)
        return
    if not isinstance(obj, dict):
        return
    t = obj.get("@type")
    if t is None:
        return
    if t not in classes:
        errs.append(f"{where}: JSON-LD type {t} is not a schema.org class")
        return
    anc = ancestors(t, parents)
    for k, v in obj.items():
        if k.startswith("@"):
            continue
        if k in ("offers", "aggregateRating", "review"):
            errs.append(f"{where}: JSON-LD carries forbidden {k}")
        if k not in props:
            errs.append(f"{where}: {t}.{k} is not a schema.org property")
        elif props[k] and not (props[k] & anc):
            errs.append(f"{where}: {k} is not used on {t} per schema.org domainIncludes")
        check_jsonld(v, where, errs, V)


def jsonlds(page_html):
    return [json.loads(b) for b in re.findall(r'(?s)<script type="application/ld\+json">(.*?)</script>', main_of(page_html))]


# -------------------------------------------------------------------- links --

def check_links(pages_html: dict, errs):
    """Internal new-page links must name frozen handles (they resolve when entries go
    active). Store links and source links are requested: store pages from the live store
    with 429 treated as backoff; source links through the Round 1 fetch policy (robots
    first, 1 request per 2 s per host, honest user agent)."""
    import verified_fetch as vf
    handles = {v["handle"] for v in json.loads((ROOT / "data/verified/handles.json").read_text())["handles"].values()}
    hrefs = set()
    for h in pages_html.values():
        hrefs |= {htmllib.unescape(x) for x in re.findall(r'href="([^"]+)"', main_of(h))}
    report = {"internal_new_pages": 0, "store": {}, "source": {}}
    for u in sorted(hrefs):
        if u.startswith("mailto:") or u.startswith("../assets") or u.startswith("assets/"):
            continue
        if u.startswith("/pages/sauna-database/"):
            report["internal_new_pages"] += 1
            if u.rsplit("/", 1)[1] not in handles:
                errs.append(f"link to a model page with no frozen handle: {u}")
            continue
        if u in ("/", "/pages/sauna-database", "/pages/sauna-database-methodology"):
            continue
        if u.startswith("/"):
            report["store"][u] = status_with_backoff("https://inhousewellness.com" + u)
        else:
            report["source"][u] = source_status(vf, u)
    for u, s in {**report["store"], **report["source"]}.items():
        if s == 404 or (isinstance(s, int) and s >= 400 and s != 429):
            errs.append(f"link {u} answered {s}")
    return report


def status_with_backoff(url):
    for i in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": "INH-Verified-linkcheck/0.1 (+https://inhousewellness.com)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8)
                continue
            return e.code
        except Exception as e:
            return f"error: {type(e).__name__}"
        finally:
            time.sleep(1)
    return 429


def source_status(vf, url):
    from urllib.parse import urlsplit
    host = urlsplit(url).netloc
    kind, rp = vf.robots_for(host)
    if kind == "ok" and not rp.can_fetch(vf.UA, url):
        return "robots-disallowed (not requested)"
    if kind == "unreadable":
        return "robots-unreadable (not requested)"
    vf.polite_wait(host)
    req = urllib.request.Request(url, headers={"User-Agent": vf.UA, "Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"error: {type(e).__name__}"


# ---------------------------------------------------------------------- run --

def run(links=False, nojs=False):
    import verified_pages as vp
    from src.health_claims import find_banned_claims
    ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
    titles = vp.load_titles()
    idx = json.loads((ROOT / "out/verified/pages-index.json").read_text())
    errs, n_facts = [], 0
    pages_html = {}
    V = vocab()
    for row in idx:
        f = RENDER / "model" / f"{row['handle']}.html"
        h = f.read_text()
        pages_html[row["handle"]] = h
        pd = json.loads((ROOT / "out/verified/pages" / f"{row['handle']}.json").read_text())
        n_facts += len(check_model(ds[row["inh_id"]], titles[row["inh_id"]], h, pd, errs))
        check_head("model", h, pd["seo_title"], pd["url"], errs, row["handle"])
        check_jsonld(jsonlds(h), row["handle"], errs, V)
    hub = (RENDER / "hub.html").read_text()
    meth = (RENDER / "methodology.html").read_text()
    pages_html["_hub"], pages_html["_methodology"] = hub, meth
    check_head("page", hub, "Verified Sauna Database – inhousewellness", "https://inhousewellness.com/pages/sauna-database", errs, "hub")
    check_head("page", meth, "How the Sauna Database Is Verified – inhousewellness",
               "https://inhousewellness.com/pages/sauna-database-methodology", errs, "methodology")
    for name, h in (("hub", hub), ("methodology", meth)):
        check_jsonld(jsonlds(h), name, errs, V)
    rows = re.findall(r'(?s)<tr data-heat="([^"]*)" data-cap="([^"]*)" data-brand="([^"]*)" data-inh-id="([^"]*)">(.*?)</tr>', main_of(hub))
    if len(rows) != len(idx) or {r[3] for r in rows} != {i["inh_id"] for i in idx}:
        errs.append(f"hub: {len(rows)} server-rendered rows for {len(idx)} pages")
    for heat, cap, brand, iid, cells in rows:
        r = ds[iid]
        sv = r["electrical"]["supply_voltage"]
        want_sv = sv["value"] if vp.ok(sv) else "Not verified"
        vis = visible(cells)
        if heat != r["heat_type"]["value"] or cap != vp.capacity_label(r) or brand != r["identity"]["brand"]["value"] \
                or titles[iid] not in vis or not vis.endswith(want_sv):
            errs.append(f"hub row {iid} disagrees with the dataset: {vis!r}")
    count = re.search(r'data-inhv="model-count">(\d+)<', hub)
    if not count or int(count.group(1)) != len(idx):
        errs.append("hub count does not equal the number of rows")
    # forbidden content: rendered pages (our part), page data, methodology body, theme sources
    scan = {f"rendered:{k}": main_of(v) + re.search(r"(?s)<head>.*?</head>", v).group(0)[-3000:] for k, v in pages_html.items()}
    for p in (ROOT / "out/verified/pages").glob("*.json"):
        scan[f"page-data:{p.name}"] = p.read_text()
    scan["methodology-body"] = (ROOT / "out/verified/methodology.html").read_text()
    for rel in ["sections/inh-verified-model.liquid", "sections/inh-verified-hub.liquid", "sections/inh-verified-methodology.liquid",
                "sections/inh-verified-product-link.liquid", "snippets/inh-verified-fact.liquid", "assets/inh-verified.css",
                "assets/inh-verified.js", "templates/metaobject/sauna.json", "templates/page.inh-verified-hub.json",
                "templates/page.inh-verified-methodology.json"]:
        scan[f"theme:{rel}"] = (ROOT / rel).read_text()
    for where, text in scan.items():
        for rx, what in ((PRICE_RX, "price/currency"), (BANNED_RX, "banned phrase")):
            m = rx.search(text)
            if m:
                errs.append(f"{where}: {what} {m.group(0)!r}")
    for k, v in pages_html.items():
        bad = find_banned_claims(visible(main_of(v)))
        if bad:
            errs.append(f"{k}: health-claims gate: {bad[:2]}")
    report = {"model_pages": len(idx), "fact_rows_checked": n_facts, "hub_rows": len(rows),
              "texts_scanned_for_forbidden_content": len(scan)}
    if nojs:
        report["hub_rows_visible_with_js_disabled"] = nojs_rows(len(idx), errs)
    if links:
        report["links"] = check_links(pages_html, errs)
    return report, errs


def run_preliminary():
    """Round 3: the same value-match, head, JSON-LD, forbidden-content and health checks over the
    PRELIMINARY pages (proposed titles and handles; nothing final until approved)."""
    import verified_pages as vp
    from src.health_claims import find_banned_claims
    ds = {r["inh_id"]: r for r in vp.load_dataset()["records"]}
    errs, n_facts, n = [], 0, 0
    V = vocab()
    for p in sorted((ROOT / "out/verified/pages-preliminary").glob("*.json")):
        pd = json.loads(p.read_text())
        h = (RENDER / "preliminary" / f"{pd['handle']}.html").read_text()
        n += 1
        n_facts += len(check_model(ds[pd["inh_id"]], pd["title"], h, pd, errs))
        check_head("model", h, pd["seo_title"], pd["url"], errs, pd["handle"])
        check_jsonld(jsonlds(h), pd["handle"], errs, V)
        for text, where in ((main_of(h), f"rendered:{pd['handle']}"), (p.read_text(), f"page-data:{p.name}")):
            for rx, what in ((PRICE_RX, "price/currency"), (BANNED_RX, "banned phrase")):
                m = rx.search(text)
                if m:
                    errs.append(f"{where}: {what} {m.group(0)!r}")
        bad = find_banned_claims(visible(main_of(h)))
        if bad:
            errs.append(f"{pd['handle']}: health-claims gate: {bad[:2]}")
    return {"preliminary_pages": n, "fact_rows_checked": n_facts}, errs


def nojs_rows(expect, errs):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        c = b.new_context(java_script_enabled=False)
        p = c.new_page()
        p.goto((RENDER / "hub.html").resolve().as_uri())
        n = p.locator('[data-inhv="table"] tbody tr:visible').count()
        filt = p.locator('[data-inhv="filters"]').is_visible()
        b.close()
    if n != expect:
        errs.append(f"hub with JavaScript disabled shows {n} rows, expected {expect}")
    if filt:
        errs.append("filter bar visible without JavaScript")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--links", action="store_true")
    ap.add_argument("--nojs", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "out/verified/checks.json"))
    ap.add_argument("--preliminary", action="store_true", help="check the Round 3 preliminary pages instead")
    a = ap.parse_args(argv)
    report, errs = run_preliminary() if a.preliminary else run(a.links, a.nojs)
    report["failures"] = errs
    Path(a.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "links"}, indent=2, default=str)[:3000])
    print("CHECKS:", "PASS" if not errs else f"FAIL ({len(errs)})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
