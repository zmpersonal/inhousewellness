#!/usr/bin/env python3
"""Database round (electrical coverage), Part A: PROPOSE extractions from cached documents. Read-only.

    .venv/bin/python scripts/electrical_extract_candidates.py [--out docs/verified/r3-electrical/candidates.json]

For every record mapped to a priced INH sauna, reads the manufacturer documents that record already
cites (out/verified/cache; nothing is fetched) and proposes electrical statements: a voltage/amperage
circuit, a breaker, a wire size, a dedicated-circuit requirement. NOTHING here writes a record.

Binding (the round's rule 1): a figure counts only if the document ties it to THIS model.
  ROW      the model's own number precedes the figure in the same line/clause, with no other model
           number between them (label-then-spec, CLAUDE.md "a rating belongs to the model number
           beside it");
  HEADING  the document names no other model number anywhere, and its first page names this model
           (number or model name): a single-model document's heading binds every figure in it;
  ROW_TRAILING  same line, the requirement then a parenthesised model list ("…Required (DYN-6115-05/DYN-6215-05)").
           A decision for the human: adjacency-after can be layout (CLAUDE.md), a parenthesised label is not.
  SHARED_HEADING  the cover (page 1) names this model's number with others ("GDI-8230-01 / GDI-8260-01")
           and states one requirement; held only when no statement in the document gives a listed model
           a DIFFERENT figure (then it is AMBIGUOUS). A decision for the human (Part A, D-binding).
  rejected OTHER_MODEL (another model's number governs the figure), HEATER_TABLE (the clause is about a
           heater sold or bundled separately: "KIP", "HUUM", "Harvia", "kW heaters"), AMBIGUOUS (a
           multi-model document and no model number governs), WARNING (a hazard sentence).
Every candidate's `span` is an exact substring of the page text it cites. No value is normalised:
`value_text` is the matched text itself.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
CACHE = ROOT / "out/verified/cache"
MANIFEST = ROOT / "data/verified/cache-manifest.json"

PATTERNS = {
    "circuit": re.compile(r"(?<![\d.])(1[12]0|2[02][08]|2[34]0)\s*-?\s*(?:V|VAC|volts?)\b\s*[/,]?\s*(?:[-–]\s*)?(\d{2}(?:\.\d)?)\s*-?\s*(?:A|AMPS?|amps?|amperes?)\b", re.I),
    "circuit_ar": re.compile(r"(?<![\d.])(\d{2})\s*-?\s*(?:A|AMPS?|amps?)\s*[/,]\s*(1[12]0|2[02][08]|2[34]0)\s*-?\s*V\b", re.I),
    "breaker": re.compile(r"(?<![\d.])(\d{2})\s*-?\s*(?:A|amps?)\b[^.\n]{0,30}\bbreaker|\bbreaker\b[^.\n]{0,30}?(?<![\d.])(\d{2})\s*-?\s*(?:A|amps?)\b", re.I),
    "wire": re.compile(r"(?<![\d/])(?:#?\s?(\d{1,2})\s*AWG|(\d{1,2})/[23](?:\s*(?:w/g|with ground|wire|cable|\+\s*G)))\b", re.I),
    "dedicated": re.compile(r"\bdedicated\b[^.\n]{0,40}\b(circuit|receptacle|outlet|line)\b", re.I),
}
MODEL_TOKEN = re.compile(r"\b[A-Z]{2,4}-[A-Z0-9]{3,6}(?:-[A-Z0-9]{1,4})*\b")
HEATER = re.compile(r"(?i)\b(KIP|HUUM|Harvia|Cilindro|Virta|Vega|Drop\s*\d|kW\s+heaters|heater\s+models?|SL2|Saunacore|Scandia\s+Ultra)\b")
WARN = re.compile(r"(?i)\b(fatal|death|fire|shock|electrocut\w*|injur\w*|warning|danger|caution)\b")


def own_tokens(r) -> tuple[set[str], list[str]]:
    toks, names = set(), []
    for k in ("model_number", "configuration"):
        v = (r["identity"].get(k) or {}).get("value")
        if v:
            toks.update(t.group(0) for t in MODEL_TOKEN.finditer(str(v).upper()))
    for k in ("model_name",):
        v = (r["identity"].get(k) or {}).get("value")
        if v:
            names.append(re.sub(r"(?i)\b(far ir|infrared|sauna|edition|low emf|full spectrum)\b", "", v).strip(" ,-"))
    return toks, [n for n in names if len(n) >= 4]


def pages_of(path: Path) -> list[str]:
    b = path.read_bytes()
    if b[:4] != b"%PDF":
        t = b.decode("utf-8", "ignore")
        t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
        return [re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", "\n", t))]
    import pypdf
    try:
        return [(p.extract_text() or "") for p in pypdf.PdfReader(io.BytesIO(b)).pages]
    except Exception:
        return []


def product_entry_pages(path: Path, r) -> list[str]:
    import html as _h
    want = {m.group(1) for m in re.finditer(r"/products/([a-z0-9-]+)", json.dumps(r.get("provenance", {})))}
    try:
        cat = json.loads(path.read_text())
    except Exception:
        return []
    for p in cat.get("products", []):
        if p.get("handle") in want:
            body = _h.unescape(re.sub(r"<(?:br|/p|/li|/h\d|/div|/tr)[^>]*>", "\n", p.get("body_html") or "", flags=re.I))
            body = re.sub(r"<[^>]+>", " ", body)
            skus = " ".join(v.get("sku") or "" for v in p.get("variants", []))
            return [f"{p.get('title', '')} {skus}\n" + re.sub(r"[ \t]+", " ", body)]
    return []


def bind(page: str, start: int, doc_tokens: set[str], own: set[str], names: list[str], first_page: str, end: int | None = None):
    """Returns (binding, reason). SAME LINE ONLY: the first version also looked at the previous line and
    bound Dynamic's "120VAC 20AMP … (DYN-6315-05)" to DYN-6215-05, whose own label ended the line above
    (its figure is 15 A). A label group joined by "/", "," or "&" binds every model in it."""
    ls = page.rfind("\n", 0, start) + 1
    le = page.find("\n", start)
    le = len(page) if le < 0 else le
    line = page[ls:le]
    pos = start - ls
    epos = (end - ls) if end is not None else pos
    if HEATER.search(line):
        return "HEATER_TABLE", "the line names a heater line, which binds to the heater, not this cabin"
    before = list(MODEL_TOKEN.finditer(line[:pos]))
    if before:
        group = [before[-1]]
        for t in reversed(before[:-1]):          # walk back through "A/B", "A, B", "A & B"
            if re.fullmatch(r"\s*(?:/|,|&|and|or)\s*", line[t.end():group[0].start()]):
                group.insert(0, t)
            else:
                break
        names_in = [t.group(0) for t in group]
        if set(names_in) & own:
            return "ROW", f"own model number in the label {'/'.join(names_in)} before the figure, same line"
        return "OTHER_MODEL", f"{'/'.join(names_in)} labels the figure; it belongs to that model"
    after = re.match(r"[^()\n]{0,40}?\(\s*((?:[A-Z]{2,4}-[A-Z0-9-]+\s*(?:/|,|&)?\s*)+)\)", line[epos:])
    if after:
        names_in = MODEL_TOKEN.findall(after.group(1))
        if set(names_in) & own:
            return "ROW_TRAILING", f"same line, parenthesised label after the requirement: ({'/'.join(names_in)})"
        return "OTHER_MODEL", f"same-line parenthesised label ({'/'.join(names_in)}) names other models"
    foreign = doc_tokens - own
    cover_own = any(t in first_page for t in own)
    if foreign and cover_own and page is first_page:
        return "SHARED_HEADING", ("the cover names this model among others and states one requirement for all of them "
                                  "(accepted only if no listed model is given a different figure: see differentiated())")
    if not foreign and ((own and cover_own) or any(n.lower() in first_page.lower() for n in names)):
        return "HEADING", "single-model document; its first page names this model"
    if foreign:
        return "AMBIGUOUS", f"multi-model document ({len(foreign)} other model numbers) and no model number governs the figure"
    return "AMBIGUOUS", "the document names no model on its first page"


def candidates_for(r, cached: dict) -> list[dict]:
    own, names = own_tokens(r)
    urls = sorted({u for u in re.findall(r"https?://[^\"\s]+", json.dumps(r.get("provenance", {})) + json.dumps(r["electrical"]))})
    out = []
    for u in urls:
        e = cached.get(u.split("?")[0])
        if not e or not (CACHE / e["cache_file"]).exists():
            continue
        if "products.json" in u:
            # A Shopify catalogue holds many products: read ONLY this record's own product entry (by
            # the product handle its origin page names), as a single-product document. Read whole,
            # the first version let one "Harvia" anywhere in the catalogue mark every statement in it.
            pages = product_entry_pages(CACHE / e["cache_file"], r)
        else:
            pages = pages_of(CACHE / e["cache_file"])
        if not pages:
            continue
        doc_tokens = {t.group(0) for p in pages for t in MODEL_TOKEN.finditer(p)}
        doc_out = []
        for i, pg in enumerate(pages):
            for kind, rx in PATTERNS.items():
                for m in rx.finditer(pg):
                    s, en = m.start(), m.end()
                    span = re.sub(r"\s+", " ", pg[max(0, s - 90):en + 60]).strip()
                    raw = pg[max(0, s - 90):en + 60]
                    b, why = bind(pg, s, doc_tokens, own, names, pages[0], en)
                    if WARN.search(pg[max(0, s - 60):en + 40]) and b in ("ROW", "HEADING"):
                        b, why = "WARNING", "the figure sits in a hazard warning, not a requirement statement"
                    doc_out.append({"kind": "circuit" if kind.startswith("circuit") else kind, "value_text": m.group(0),
                                "span": raw.strip(), "span_flat": span, "doc": u, "page": i + 1 if len(pages) > 1 or u.endswith(".pdf") else None,
                                "fetched_at": e.get("fetched_at"), "binding": b, "why": why})
        differentiated(doc_out)
        out += doc_out
    return out


def differentiated(cands: list[dict]) -> None:
    """A shared cover holds only if no ROW/OTHER_MODEL circuit statement in the same document gives a
    listed model a figure different from the cover's. Mutates bindings in place."""
    per_model = {re.sub(r"\s+", "", c["value_text"]).upper() for c in cands
                 if c["kind"] == "circuit" and c["binding"] in ("ROW", "ROW_TRAILING", "OTHER_MODEL")}
    for c in cands:
        if c["binding"] == "SHARED_HEADING":
            v = re.sub(r"\s+", "", c["value_text"]).upper()
            if per_model and per_model != {v}:
                c["binding"], c["why"] = "AMBIGUOUS", "the cover is shared and another statement gives a listed model a different figure"


def main(argv=None) -> None:
    from electrical_coverage import load
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/verified/r3-electrical/candidates.json"))
    a = ap.parse_args(argv)
    R, H, act, M, cost = load()
    byid = {r["inh_id"]: r for r in R}
    cached = {k.replace("headless:", "").split("?")[0]: e for k, e in json.loads(MANIFEST.read_text())["entries"].items() if e.get("cache_file")}
    priced = [x for x in cost if x["fields"]["price_usd"]["value"] is not None]
    p2r = {v["product_handle"]: k for k, v in M.items()}
    res = []
    for x in priced:
        rid = p2r.get(x["handle"])
        if not rid:
            continue
        r = byid[rid]
        cs = candidates_for(r, cached)
        res.append({"product": x["handle"], "inh_id": rid, "brand": r["identity"]["brand"]["value"],
                    "live": (H.get(rid) or {}).get("handle") in act, "model_tokens": sorted(own_tokens(r)[0]),
                    "candidates": cs})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    n = sum(len(x["candidates"]) for x in res)
    from collections import Counter
    print(f"{len(res)} records, {n} candidate statements")
    print(Counter(c["binding"] for x in res for c in x["candidates"]))
    print(Counter((c["kind"], c["binding"]) for x in res for c in x["candidates"]))


if __name__ == "__main__":
    main()
