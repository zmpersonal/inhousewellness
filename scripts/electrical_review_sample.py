#!/usr/bin/env python3
"""Database round (electrical coverage), Part A: the 20-item review sample, read from the documents.

    .venv/bin/python scripts/electrical_review_sample.py

Every span is located in the cached document text by a pattern and copied verbatim, never typed:
a sample item whose pattern does not match its document fails loudly. Read-only.
Writes docs/verified/r3-electrical/review-sample.json.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from electrical_extract_candidates import CACHE, MANIFEST, pages_of  # noqa: E402

CACHED = {k.replace("headless:", "").split("?")[0]: e for k, e in json.loads(MANIFEST.read_text())["entries"].items() if e.get("cache_file")}
OURPAGE = {r["handle"]: r for r in json.loads((ROOT / "data/facts/manual_specs.json").read_text())["rows"]}

# (id, brand, model, field, doc-url substring | product-handle, pattern, binding, why, line_or_bundled)
PROPOSALS = [
    ("P01", "Golden Designs", "GDI-8040-03 (not live)", "circuit", "e0317a76-b683-4d0a-b032-31209286b213", r"GDI-8040-03 FS[^\n]{0,80}DEDICATED CIRCUITS\s*REQUIRED",
     "ROW", "line manual; the row opens with GDI-8040-03 and the figure follows on the same line. NOTE: this PDF now answers 404 (rule 7); the value was read from the copy fetched 2026-09-27", True),
    ("P02", "Golden Designs", "GDI-6996-01 Monaco (not live)", "circuit", "6159c090", r"DYN-6996-01-Elite / GDI-6996-01[\s\S]{0,500}?OUTLETS",
     "SHARED_HEADING", "the cover names DYN-6996-01-Elite / GDI-6996-01 (one model, two brands) and states one requirement for both; no other statement differs", False),
    ("P03", "Golden Designs", "GDI-8230-01 (not live)", "circuit", "fc9832dc", r"GDI-8230-01 / GDI-8260-01[\s\S]{0,500}?Circuits Required",
     "SHARED_HEADING", "the cover names GDI-8230-01 / GDI-8260-01 and states one requirement for both", False),
    ("P04", "Golden Designs", "GDI-8260-01 (not live)", "circuit", "fc9832dc", r"GDI-8230-01 / GDI-8260-01[\s\S]{0,500}?Circuits Required",
     "SHARED_HEADING", "same cover as P03", False),
    ("P05", "Golden Designs", "GDI-B002-01 St. Moritz barrel (not live)", "circuit", "50a61a79", r"GDI-B002-01/GDI-B004-01/GDI-B006-01[\s\S]{0,500}?\(FOR THE LIGHTING\)",
     "SHARED_HEADING", "the cover names the three barrel models and one LIGHTING circuit; the heater is not covered by this statement (decision D4)", False),
    ("P06", "Golden Designs", "golden-designs-6-person-traditional-sauna (new record)", "circuit", "product:golden-designs-6-person-traditional-sauna", r"Electrical service:[^\n]{0,160}",
     "HEADING", "the manufacturer's own product entry for this SKU (exact SKU match); a single-product entry, so its title binds the statement", False),
    ("P07", "Maxxus", "MX-J306-02S (not live)", "circuit", "1f460185", r"MX-J306-02S - 120VAC 20AMP Dedicated Circuits Required",
     "ROW", "line manual; the row is labelled MX-J306-02S on the same line (the MX-J206-02S row above it carries 15AMP)", True),
    ("P08", "Maxxus", "maxxus-s-line-mx-s306-01-fs (new record)", "circuit", "product:maxxus-s-line-mx-s306-01-fs", r"Electrical service:[^\n]{0,140}",
     "HEADING", "manufacturer product entry for this exact SKU", False),
    ("P09", "Maxxus", "MX-K406-01 CED, maxxus-4-person-sauna-cedar (new record)", "circuit", "ourpage:maxxus-4-person-sauna-cedar", r"MX-K306-01/MX-K406-01 - 120VAC 20AMP Dedicated Circuits Required",
     "ROW", "line manual; label group MX-K306-01/MX-K406-01 precedes the figure. SOURCE: a manual on OUR product page (Drive), no manufacturer-hosted copy cached (decision D3)", True),
    ("P10", "Dynamic", "DYN-6215-05 Lucca Elite (live)", "circuit", "decfec20", r"120VAC 15AMP Dedicated Circuit Required \(DYN-6115-05/DYN-6215-05\)",
     "ROW_TRAILING", "line manual, spec-then-label: the parenthesised label follows its own requirement on the same line (decision D2). The DB already holds 15 A for this record; the tool drops the quote", True),
    ("P11", "Dynamic", "DYN-6115-05 Veneto (live)", "circuit", "decfec20", r"120VAC 15AMP Dedicated Circuit Required \(DYN-6115-05/DYN-6215-05\)",
     "ROW_TRAILING", "same line as P10; adds a documented-grade source to a value now listed from the product page", True),
    ("P12", "Dynamic", "dynamic-bellagio-3-person (new record; our SKU DYN-6306-02 is a variant of the DYN-6306-01 Bellagio entry)", "circuit", "product:dynamic-bellagio-3-person-indoor-infrared-sauna", r"Electrical service:[^\n]{0,140}",
     "HEADING", "manufacturer product entry for this exact SKU", False),
    ("P13", "Sun Home", "Nova 3 (live)", "breaker", "SUN_HOME-NOVA_3-ASSEMBLY_GUIDE", r"Circuit Breaker 30 A \(HUUM Table 2\)",
     "HEADING", "single-model assembly guide; its cover names the Nova 3. The row cites HUUM's table but is printed in the Nova 3's own spec block", False),
    ("P14", "Sun Home", "Nova 3 (live)", "wire_gauge", "SUN_HOME-NOVA_3-ASSEMBLY_GUIDE", r"Minimum Wire Size 10 AWG minimum \(HUUM Table 2\)",
     "HEADING", "same spec block as P13", False),
    ("P15", "Sun Home", "Nova 6 (live)", "breaker", "SUN_HOME-NOVA_6-ASSEMBLY_GUIDE", r"Circuit Breaker 40 A \(HUUM Table 2\)",
     "HEADING", "single-model guide for the Nova 6", False),
    ("P16", "Sun Home", "Nova 6 (live)", "wire_gauge", "SUN_HOME-NOVA_6-ASSEMBLY_GUIDE", r"Minimum Wire Size 8 AWG minimum \(HUUM Table 2\)",
     "HEADING", "same spec block as P15", False),
    ("P17", "Almost Heaven", "Allegheny cabin 6-person (live; shows no circuit today)", "circuit", "almostheaven.com/products/allegheny-6-person-cabin-sauna",
     r"8kW/9kW/10\.5kW, 240V, 40/45/50-amp requirement, hard-wire connect",
     "HEADING", "the model's own product page. OPTION-DEPENDENT: one statement maps three heater options to three circuits in order; stored verbatim as stated, never split into a single number", False),
    ("P18", "Almost Heaven", "Allegheny cabin 6-person (live)", "circuit", "almostheaven.com/products/allegheny-6-person-cabin-sauna",
     r"Lighting electrical: 110V, 15-amp service, plug-in connect",
     "HEADING", "same page; the lighting circuit is a second, separate statement", False),
    ("P19", "Salus", "Solara 6-person (live)", "breaker", "salussaunas.com/products/solara", r"Traditional Heater: 8kW, requires a 40 amp breaker",
     "HEADING", "the model's own product page; the 8kW heater is the one this cabin ships with", False),
    ("P20", "Salus", "Renew II 2-person (live)", "breaker", "salussaunas.com/products/renew-ii-traditional-indoor-sauna-2-person", r"Traditional Heater: 6kW, requires a 30 amp breaker",
     "HEADING", "the model's own product page", False),
]

REJECTED = [
    ("R01", "Dynamic", "DYN-6215-05", "decfec20", r"\(DYN-6115-05/DYN-6215-05\)\s*\n\s*120VAC 20AMP Dedicated Circuit Required \(DYN-6315-05\)",
     "OTHER_MODEL: my first binder read the previous line's label and bound 20AMP to DYN-6215-05. The 20AMP row is labelled DYN-6315-05. Fixed: same line only"),
    ("R02", "Salus", "Flora 3-person", "Flora_Patio", r"8\.0kW KIP Heaters[\s\S]{0,140}?8/2 wire",
     "HEATER_TABLE: a table for Harvia KIP heaters bundled in the cabin manual; binds to the heater, not the cabin (stays empty; the record links p. 26)"),
    ("R03", "Sun Home", "Equinox, Luminar, Solstice, Solaris (10 live records)", "entry:sunhomesaunas.com:portable-cold-plunge-tub",
     r"connect to a dedicated 110–120V GFCI circuit with a 15A breaker, then plunge",
     "OTHER PRODUCT: the sentence is in Sun Home's PORTABLE COLD PLUNGE catalogue entry; Part B's scope file attributed it to every Sun Home sauna citing the catalogue"),
    ("R04", "Dynamic", "DYN-6996-01 Elite", "08a9a16b", r"1-2 Person FAR Infrared Sauna[\s\S]{0,500}?120VAC 15AMP Dedicated Circuit Required",
     "WRONG DOCUMENT: the cover is a 1-2 person model; the record is a 6-person Monaco. (P02's cover names DYN-6996-01-Elite and is the right document)"),
    ("R05", "Maxxus", "MX-K406-01-ZF (ced, hem)", "18dcad35", r"120V/15AMP DEDICATED CIRCUIT REQUIRED FOR MX-M206-01",
     "OTHER_MODEL: the cited line manual covers MX-M206/M306 only; the K406-ZF is not in it. The our-page K406 manual (P09) names MX-K406-01 without -ZF: variant mismatch, left empty"),
    ("R06", "Scandia", "barrel sauna kits (6)", "ourpage:scandia-electric-barrel-sauna-kit", r"wire gauged between 10 AWG [–-] 4 AWG",
     "AMBIGUOUS: a kit manual with no model number, and a RANGE across heater sizes; not a value for any one model"),
    ("R08", "Redwood Outdoors", "all 13 live Redwood records", "entry:www.redwoodoutdoors.com:harvia-kip-8kw-heater-package",
     r"Requires a 40-amp breaker and #8 copper wire",
     "OTHER PRODUCT: every Redwood breaker/wire statement is in a separately sold HEATER PACKAGE entry of the catalogue, not a sauna. Part B's scope file counted all 13 because they cite the same catalogue: corrected here"),
    ("R07", "Maxxus", "every K-series record", "18dcad35", r"\(120VAC 15AMP Dedicated Circuit or 120VAC 20AMP Dedicated Circuit\)",
     "TEMPLATE either-or sentence in the body; states no requirement for any model"),
]


def doc_text(ref: str) -> tuple[list[str], str, str | None]:
    if ref.startswith("product:"):
        h = ref.split(":", 1)[1]
        snap = {p["handle"]: p for p in json.loads((ROOT / "data/verified/internal/inh-products-snapshot.json").read_text())["products"]}
        skus = {s.upper() for s in snap[h]["skus"]}
        for k, e in CACHED.items():
            if "products.json" not in k:
                continue
            for p in json.loads((CACHE / e["cache_file"]).read_text()).get("products", []):
                if skus & {(v.get("sku") or "").upper() for v in p.get("variants", [])}:
                    body = html.unescape(re.sub(r"<(?:br|/p|/li|/strong)[^>]*>", "\n", p.get("body_html") or "", flags=re.I))
                    return [re.sub(r"<[^>]+>", " ", body)], f"https://goldendesigninc.com/products/{p['handle']}", e.get("fetched_at")
        raise SystemExit(f"no manufacturer entry for {h}")
    if ref.startswith("entry:"):
        # entry:<host>:<product handle> -- ONE product entry of a cached Shopify catalogue
        _, host, h = ref.split(":", 2)
        for k, e in CACHED.items():
            if host in k and "products.json" in k:
                for p in json.loads((CACHE / e["cache_file"]).read_text()).get("products", []):
                    if p.get("handle") == h:
                        body = html.unescape(re.sub(r"<(?:br|/p|/li|/strong|/h\d)[^>]*>", "\n", p.get("body_html") or "", flags=re.I))
                        return [re.sub(r"<[^>]+>", " ", body)], f"https://{host}/products/{h}", e.get("fetched_at")
        raise SystemExit(f"no entry {h} on {host}")
    if ref.startswith("ourpage:"):
        r = OURPAGE[ref.split(":", 1)[1]]
        pages = [""] * (r.get("pages") or 1)
        for x in r.get("electrical_context") or []:
            pages[x["page"] - 1] += "\n" + x["span"]
        return pages, r["pdf_url"] + "  (manual linked from OUR product page)", r.get("fetched_at")
    for k, e in CACHED.items():
        if ref in k:
            pages = pages_of(CACHE / e["cache_file"])
            raw = (CACHE / e["cache_file"]).read_bytes()
            if raw[:4] != b"%PDF":
                # Product text embedded as JSON in the page (escaped HTML): decode it, then strip tags.
                t = raw.decode("utf-8", "ignore")
                t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t).replace("\\/", "/")
                pages = [pages[0] + "\n" + html.unescape(re.sub(r"<[^>]+>", "\n", t))] if pages else pages
            return pages, k, e.get("fetched_at")
    raise SystemExit(f"document not cached: {ref}")


def locate(ref, pattern):
    pages, url, fetched = doc_text(ref)
    rx = re.compile(pattern.replace(" ", r"\s+"))   # PDF text wraps anywhere; the span stays the document's own text
    for i, pg in enumerate(pages):
        m = rx.search(pg)
        if m:
            return {"span": m.group(0), "span_flat": re.sub(r"\s+", " ", m.group(0)).strip(), "document": url,
                    "page": i + 1 if len(pages) > 1 or url.endswith(".pdf") else None, "fetched_at": fetched}
    raise SystemExit(f"pattern not found in {ref}: {pattern}")


def main() -> None:
    out = {"proposed": [], "rejected": []}
    for pid, brand, model, field, ref, pat, binding, why, line in PROPOSALS:
        out["proposed"].append(dict(id=pid, brand=brand, model=model, field=field, binding=binding, why=why,
                                    line_or_bundled_manual=line, **locate(ref, pat)))
    for rid, brand, model, ref, pat, why in REJECTED:
        out["rejected"].append(dict(id=rid, brand=brand, model=model, why=why, **locate(ref, pat)))
    p = ROOT / "docs/verified/r3-electrical/review-sample.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    brands = {x["brand"] for x in out["proposed"]}
    print(f"{len(out['proposed'])} proposed across {len(brands)} brands ({sum(x['line_or_bundled_manual'] for x in out['proposed'])} from line manuals); "
          f"{len(out['rejected'])} rejected -> {p.relative_to(ROOT)}")
    for x in out["proposed"] + out["rejected"]:
        print(f"  {x['id']} p{x['page']} {x['span_flat'][:110]}")


if __name__ == "__main__":
    main()
