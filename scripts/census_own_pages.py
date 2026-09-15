#!/usr/bin/env python3
"""PHASE 1 -- census InHouse's OWN pages. Zero egress to any vendor host.

WHY THIS IS THE CHEAP PATH
Five of eleven manufacturer hosts are unreachable from Actions (discover run 3:
Dynamic Saunas self-signed cert, Dundalk robots 404, Mande Spa TLS alert, Kohler
timeout, Ripavi network unreachable) -- 52 of 139 matched SKUs. If a manual or a
manufacturer model number already sits on OUR product page, we reach those
vendors without ever touching their server for the URL.

WHAT IT LOOKS AT, and it is not just the body
The client described a "Download Manual" PDF link. On this store the manuals are
NOT .pdf hrefs in the body: they are Google Drive iframe embeds in the
`custom.product_documents` metafield. A census that grepped the body for `.pdf`
would have reported ~0% coverage and been precisely, confidently wrong. So this
reads the body AND every metafield value, flattening rich_text_field JSON to
text first.

THE 2x2, not a single rate (client's addition)
  1 manual + model number   -> richest
  2 manual, no model number -> readable now, not mappable to a vendor URL
  3 model number, no manual -> the bucket that decides whether the vendor crawl
                               is worth continuing: a URL can be CONSTRUCTED
                               from evidence rather than guessed
  4 neither                 -> the honest floor

    python3 scripts/census_own_pages.py --pull <admin-pull.json> [--out data/own-page-census.json]
    python3 scripts/census_own_pages.py --self-test
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# One definition of how a rich_text_field becomes text. Redefining it here would
# be a second definition of "what the metafield says" and the two would drift.
from scripts.fix_shipping_metafield import text_of  # noqa: E402

# ── manual references ───────────────────────────────────────────────────────
# Three shapes, because this store uses the third and the brief assumed the first.
PDF_RX = re.compile(r'(?:href|src)="([^"]+\.pdf(?:\?[^"]*)?)"', re.I)
DRIVE_RX = re.compile(r'drive\.google\.com/file/d/([A-Za-z0-9_-]{10,})', re.I)
DRIVE_OPEN_RX = re.compile(r'drive\.google\.com/open\?id=([A-Za-z0-9_-]{10,})', re.I)

# ── manufacturer model number ───────────────────────────────────────────────
# "Model: MX-LS3-01", "Model Number: GDI-6880-02", "Model No. FD-KN001".
# The captured value must LOOK like a part number, which is what keeps
# "Model: 6 persons" and "Model: Heming Edition" out. A bare word is not a model
# number, and accepting one would put prose into a URL key.
# The separator is only optional when a "number / no. / #" word is present, so
# "Model No. FD-KN001" is caught while "This model is our best seller" is not.
MODEL_RX = re.compile(
    r"(?i)\bmodel\s*(?:(?:number|num\.?|no\.?|#)\s*[:\-–]?|[:\-–])\s*"
    # GREEDY, and stopping at the next "Label:" as well as at punctuation or end.
    # These fields pack several facts on one line -- "Model: MX-K406-01 CED
    # Capacity: 4 Person" -- so a non-greedy capture that required terminal
    # punctuation found nothing at all on a flat field, while the same text in a
    # rich_text block (newline-separated) matched. Two answers for one fact
    # depending on the field type is the bug; this is the fix.
    r"([A-Za-z0-9][A-Za-z0-9./\- ]{2,40})"
    # (?-i:...) matters: the pattern is (?i), which would make [A-Z] match a
    # lowercase letter and let the capture stop mid-word -- it produced
    # "MX-K406-01 CED Capac". The next-label terminator must be genuinely
    # capitalised to count.
    r"(?=\s*(?:[<\n,;)]|(?-i:[A-Z][A-Za-z ]{2,20}:)|$))")
# Two letters, not three: "MX-1 is the best sauna" trimmed back to "MX-1 is"
# because "is" slipped under a 3-character floor. No real SKU in this catalogue
# carries an all-lowercase token.
_LOWER_WORD_RX = re.compile(r"^[a-z]{2,}$")
_PARTNO_TOKEN_RX = re.compile(r"^(?=.*\d)[A-Za-z0-9][A-Za-z0-9./\-]*$")
# Units and counting nouns. "Model: 8 kW heater" states a heater size, not a part
# number, and "8 kW" in a URL key would be nonsense.
_UNIT_TOKENS = {"kw", "w", "watt", "watts", "v", "volt", "volts", "a", "amp",
                "amps", "lb", "lbs", "kg", "in", "inch", "inches", "ft", "mm",
                "cm", "person", "persons", "people", "seat", "seats", "hz"}


def looks_like_a_part_number(raw):
    """"6 persons" is not a model number, and accepting one would put prose into
    a URL key. A part number carries a digit, has a token mixing digits with the
    rest, and contains neither a lowercase English word nor a unit -- so
    `MX-M356-01-FS CED` and `GDI-6880-02 Elite` pass while `6 persons`,
    `2 person sauna` and `8 kW heater` do not."""
    if not re.search(r"\d", raw) or not re.search(r"[A-Za-z]", raw):
        return False
    tokens = raw.split()
    if not tokens:
        return False
    if any(t.lower() in _UNIT_TOKENS for t in tokens):
        return False
    if any(_LOWER_WORD_RX.match(t) for t in tokens):
        return False
    return any(_PARTNO_TOKEN_RX.match(t) for t in tokens)


def trim_to_part_number(raw):
    """A greedy capture can run past the model number into the prose after it.
    Drop trailing tokens until what is left is a part number, so `MX-1 is the
    best sauna` still yields `MX-1` instead of being thrown away whole. Returns
    None when nothing survives."""
    tokens = raw.split()
    while tokens:
        candidate = " ".join(tokens)
        if len(candidate) >= 3 and looks_like_a_part_number(candidate):
            return candidate
        tokens.pop()
    return None

# ── shipping weight and box count ───────────────────────────────────────────
WEIGHT_RX = re.compile(
    r"(?i)\b(?:shipping|ship(?:ped)?|gross|package|carton|total)\s*weight\s*"
    r"[:\-–]?\s*(?:approx\.?\s*)?([\d,]+(?:\.\d+)?)\s*(lb|lbs|pound|pounds|kg)\b")
BOXES_RX = re.compile(
    r"(?i)\b(?:ships?|shipped|arrives?|delivered|packed)\s+in\s+(\d{1,2})\s*"
    r"(?:separate\s+)?(?:box|boxes|carton|cartons|crate|crates|package|packages)\b"
    r"|\b(\d{1,2})\s*(?:box|boxes|carton|cartons|crate|crates)\b(?!\s*(?:spring|of\s+tissue))")

SPAN = 90          # characters of verbatim context kept either side of a hit


def flatten_metafield(value, mtype):
    """A metafield value as plain text.

    rich_text_field is a JSON document. Blocks are joined with newlines rather
    than run together, because `text_of` concatenates with no separator and two
    adjacent list items would otherwise read as one sentence -- enough to let a
    regex span a boundary and quote a span that appears nowhere on the page.
    """
    if mtype != "rich_text_field":
        return value or ""
    try:
        doc = json.loads(value)
    except (TypeError, ValueError):
        return value or ""

    out = []

    def walk(node):
        t = node.get("type")
        if t in ("paragraph", "list-item", "heading"):
            out.append(text_of(node))
            return
        for c in node.get("children", []):
            walk(c)

    walk(doc)
    return "\n".join(x for x in out if x)


def sources_of(product):
    """(label, text) for every place a fact could be stated on our own page.

    A metafield with no value is skipped explicitly rather than flattened to "".
    Both read as "nothing found" downstream, but only one of them means the
    merchant left the field empty, and this project does not let an absence
    arrive disguised as a value.
    """
    body = product.get("descriptionHtml")
    yield "body", body if body is not None else ""

    for m in (product.get("metafields") or {}).get("nodes", []):
        value, mtype = m.get("value"), m.get("type")
        if value is None:
            continue                      # the field exists and is empty
        if mtype is None:
            # No type means we cannot know whether it is rich text. Treat it as
            # plain text rather than guessing a JSON document into existence.
            mtype = "single_line_text_field"
        yield "metafield:%s.%s" % (m["namespace"], m["key"]), \
            flatten_metafield(value, mtype)


def span_around(text, match):
    a = max(0, match.start() - SPAN)
    b = min(len(text), match.end() + SPAN)
    return re.sub(r"\s+", " ", text[a:b]).strip()


# WHICH FIELD A REFERENCE SITS IN DECIDES WHAT IT IS.
# Every document reference on this store is a Google Drive embed, and 35 of the
# first 180 found were in `custom.video` -- videos, not manuals. Counting those
# as manuals put coverage at 106/165 when the documents field alone gives 96.
# A precise, confident, wrong number, from the one distinction the field name
# makes for free. Role is assigned from the source, never assumed.
DOC_FIELDS = {"product_documents": "manual_candidate",
              "warranty": "warranty", "warranty_details": "warranty",
              "delivery": "delivery", "shipping_details": "delivery"}
VIDEO_FIELDS = {"video", "videos"}


def _role_for(label):
    key = label.split(".")[-1] if label.startswith("metafield:") else label
    if key in VIDEO_FIELDS:
        return "video"
    return DOC_FIELDS.get(key, "other")


def find_manuals(product):
    out = []
    for label, text in sources_of(product):
        role = _role_for(label)
        for u in PDF_RX.findall(text):
            out.append({"kind": "pdf", "url": u, "source": label, "role": role})
        for fid in DRIVE_RX.findall(text) + DRIVE_OPEN_RX.findall(text):
            out.append({"kind": "google_drive", "file_id": fid, "source": label,
                        "role": role,
                        # Drive's direct-download form. NOT fetched here -- this
                        # census makes no request at all, and whether the file is
                        # a PDF at all is unknown until something fetches it.
                        "url": "https://drive.google.com/uc?export=download&id=" + fid})
    seen, uniq = set(), []
    for d in out:
        k = d.get("url")
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq


def find_model_numbers(product, own_skus):
    out = []
    for label, text in sources_of(product):
        for m in MODEL_RX.finditer(text):
            raw = trim_to_part_number(m.group(1).strip().rstrip(".,;:"))
            if raw is None:
                continue
            out.append({"value": raw, "source": label, "span": span_around(text, m),
                        "matches_our_sku": _norm(raw) in {_norm(s) for s in own_skus}})
    seen, uniq = set(), []
    for d in out:
        if _norm(d["value"]) not in seen:
            seen.add(_norm(d["value"]))
            uniq.append(d)
    return uniq


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def find_shipping(product):
    weights, boxes = [], []
    for label, text in sources_of(product):
        for m in WEIGHT_RX.finditer(text):
            val = float(m.group(1).replace(",", ""))
            unit = m.group(2).lower()
            if unit.startswith("kg"):
                val, unit = round(val * 2.20462, 1), "lb"
            else:
                unit = "lb"
            weights.append({"value": val, "unit": unit, "source": label,
                            "span": span_around(text, m)})
        for m in BOXES_RX.finditer(text):
            n = m.group(1) or m.group(2)
            if not n:
                continue
            boxes.append({"value": int(n), "source": label,
                          "span": span_around(text, m)})
    return weights, boxes


def variant_weight(product):
    """Shopify's own shipping weight. 0 lb is the merchant default, not a
    measurement -- the project's SHOPIFY_WEIGHT_ZERO rule, restated here so this
    census cannot report a 0 as coverage."""
    out = []
    for v in (product.get("variants") or {}).get("nodes", []):
        w = ((v.get("inventoryItem") or {}).get("measurement") or {}).get("weight") or {}
        val = w.get("value")
        if val:                      # 0 and None both fall through, deliberately
            out.append({"sku": v.get("sku"), "value": val, "unit": w.get("unit")})
    return out


def bucket(has_manual, has_model):
    if has_manual and has_model:
        return 1
    if has_manual:
        return 2
    if has_model:
        return 3
    return 4


BUCKET_LABEL = {
    1: "manual + model number",
    2: "manual, no model number",
    3: "model number, no manual  (vendor URL constructible)",
    4: "neither                  (the honest floor)",
}


def census(products):
    rows = []
    for p in products:
        skus = [v.get("sku") for v in (p.get("variants") or {}).get("nodes", [])
                if v.get("sku")]
        manuals = find_manuals(p)
        manual_candidates = [m for m in manuals if m["role"] == "manual_candidate"]
        models = find_model_numbers(p, skus)
        weights, boxes = find_shipping(p)
        rows.append({
            "handle": p["handle"], "title": p.get("title"), "vendor": p.get("vendor"),
            "skus": skus,
            "manuals": manuals,
            "model_numbers": models,
            "shipping_weight_stated": weights,
            "shopify_variant_weight": variant_weight(p),
            "box_count_stated": boxes,
            "manual_candidates": len(manual_candidates),
            "bucket": bucket(bool(manual_candidates), bool(models)),
        })
    return rows


# ── the cross-tabs the client asked for ─────────────────────────────────────

# discover run 3, data/facts/manufacturer-discovery.json: robots.txt unreadable,
# so the crawler skips the host entirely. Not a Disallow -- transport or absence.
UNREACHABLE = {"Dynamic Saunas": "TLS self-signed cert",
               "Dundalk Leisurecraft": "robots.txt 404",
               "Mande Spa": "TLS internal error",
               "Kohler": "read timeout",
               "Ripavi": "network unreachable"}


def analyze(rows, matched_handles):
    """Buckets by vendor, buckets 3/4 against the unreachable vendors, and
    whether Maxxus and Golden Designs share one model-number scheme."""
    out = {}
    by_vendor = {}
    for r in rows:
        v = by_vendor.setdefault(r["vendor"], {"n": 0, "b": {1: 0, 2: 0, 3: 0, 4: 0}})
        v["n"] += 1
        v["b"][r["bucket"]] += 1
    out["by_vendor"] = by_vendor

    out["unreachable_crosstab"] = {
        v: {"reason": why,
            "bucket3": [r["handle"] for r in rows if r["vendor"] == v and r["bucket"] == 3],
            "bucket4": [r["handle"] for r in rows if r["vendor"] == v and r["bucket"] == 4],
            "n": sum(1 for r in rows if r["vendor"] == v)}
        for v, why in UNREACHABLE.items()}

    # The email list: no manual on our page AND no model number AND the vendor's
    # host cannot be read. No automated path reaches these.
    out["needs_a_human"] = sorted(
        ({"vendor": r["vendor"], "handle": r["handle"], "title": r["title"],
          "skus": r["skus"]}
         for r in rows if r["bucket"] == 4 and r["vendor"] in UNREACHABLE),
        key=lambda x: (x["vendor"], x["handle"]))

    # Phase 2: the SKU->URL key, over the matched set
    out["matched"] = {
        "of": len(matched_handles),
        "with_model_number": sum(1 for r in rows if r["handle"] in matched_handles
                                 and r["model_numbers"]),
        "with_manual": sum(1 for r in rows if r["handle"] in matched_handles
                           and r["manuals"]),
    }

    # Maxxus / Golden Designs: one scheme or two?
    def prefixes(vendor, field):
        pre = {}
        for r in rows:
            if r["vendor"] != vendor:
                continue
            vals = r["skus"] if field == "sku" else [m["value"] for m in r["model_numbers"]]
            for s in vals:
                head = re.split(r"[-\s]", s.strip())[0].upper()
                pre[head] = pre.get(head, 0) + 1
        return dict(sorted(pre.items(), key=lambda kv: -kv[1]))

    out["maxxus_golden"] = {
        "Maxxus": {"sku_prefixes": prefixes("Maxxus", "sku"),
                   "model_prefixes": prefixes("Maxxus", "model")},
        "Golden Designs Inc": {"sku_prefixes": prefixes("Golden Designs Inc", "sku"),
                               "model_prefixes": prefixes("Golden Designs Inc", "model")},
    }
    return out


def self_test():
    """Every detector, fired at text that must and must not match."""
    fails = []

    def prod(body="", metafields=()):
        return {"handle": "h", "title": "t", "vendor": "v",
                "descriptionHtml": body,
                "metafields": {"nodes": [{"namespace": "custom", "key": k,
                                          "type": ty, "value": v}
                                         for k, ty, v in metafields]},
                "variants": {"nodes": []}}

    # manuals: all three shapes, and the Drive embed this store actually uses
    m = find_manuals(prod('<a href="https://x.com/manual.pdf">Download Manual</a>'))
    if not (len(m) == 1 and m[0]["kind"] == "pdf"):
        fails.append("did not find a .pdf href")
    m = find_manuals(prod(metafields=[("product_documents", "multi_line_text_field",
        '<iframe src="https://drive.google.com/file/d/1su52vxTv75429hPf7uRz6CaoQRo5wsAB/preview">')]))
    if not (len(m) == 1 and m[0]["kind"] == "google_drive"
            and m[0]["file_id"] == "1su52vxTv75429hPf7uRz6CaoQRo5wsAB"):
        fails.append("did not find a Google Drive embed in a metafield: %r" % m)
    if find_manuals(prod("<p>No documents here.</p>")):
        fails.append("invented a manual where there is none")
    # a Drive embed in the VIDEO field is a video, not a manual
    m = find_manuals(prod(metafields=[
        ("video", "multi_line_text_field",
         '<iframe src="https://drive.google.com/file/d/1AAAAAAAAAAAAAAAAAAA/preview">'),
        ("product_documents", "multi_line_text_field",
         '<iframe src="https://drive.google.com/file/d/1BBBBBBBBBBBBBBBBBBB/preview">')]))
    roles = {x["file_id"]: x["role"] for x in m}
    if roles.get("1AAAAAAAAAAAAAAAAAAA") != "video":
        fails.append("a video embed was not marked as a video: %r" % roles)
    if roles.get("1BBBBBBBBBBBBBBBBBBB") != "manual_candidate":
        fails.append("a product_documents embed was not a manual candidate: %r" % roles)

    # model numbers: a part number yes, prose no
    for text, want in (("Model: MX-LS3-01", "MX-LS3-01"),
                       ("Model Number: GDI-6880-02", "GDI-6880-02"),
                       ("Model No. FD-KN001", "FD-KN001"),
                       ("<li>Model: DYN-6119-01</li>", "DYN-6119-01")):
        got = find_model_numbers(prod(text), [])
        if not got or got[0]["value"] != want:
            fails.append("model %r -> %r, wanted %r" % (text, got, want))
    for text in ("Model: 6 persons", "Model: Heming Edition", "Model: Deluxe",
                 "Model: 2 person sauna", "Model: 8 kW heater",
                 "This model is our best seller", "Model description follows"):
        if find_model_numbers(prod(text), []):
            fails.append("prose accepted as a model number: %r" % text)
    # a real catalogue SKU carrying a space and an all-caps suffix must survive
    got = find_model_numbers(prod("Model: MX-M356-01-FS CED"), [])
    if not got or got[0]["value"] != "MX-M356-01-FS CED":
        fails.append("a spaced real SKU was rejected: %r" % got)
    got = find_model_numbers(prod("Model: MX-K306-01"), ["MX-K306-01"])
    if not got or not got[0]["matches_our_sku"]:
        fails.append("did not notice the model number equals our SKU")

    # shipping weight and boxes
    w, b = find_shipping(prod("Shipping weight: 410 lbs / Ships in 3 boxes."))
    if not (w and w[0]["value"] == 410 and w[0]["unit"] == "lb"):
        fails.append("weight not read: %r" % w)
    if not (b and b[0]["value"] == 3):
        fails.append("box count not read: %r" % b)
    w, _ = find_shipping(prod("Gross weight: 1,234 lbs"))
    if not (w and w[0]["value"] == 1234):
        fails.append("comma-separated weight misread: %r" % w)
    w, _ = find_shipping(prod("Shipping weight: 100 kg"))
    if not (w and abs(w[0]["value"] - 220.5) < 0.2):
        fails.append("kg not converted: %r" % w)

    # a 0 lb Shopify weight is a default, never coverage
    p = prod()
    p["variants"]["nodes"] = [{"sku": "A", "inventoryItem": {"measurement":
                              {"weight": {"value": 0, "unit": "POUNDS"}}}},
                              {"sku": "B", "inventoryItem": {"measurement":
                              {"weight": {"value": 750, "unit": "POUNDS"}}}}]
    vw = variant_weight(p)
    if [x["sku"] for x in vw] != ["B"]:
        fails.append("a 0 lb Shopify weight was counted as a measurement: %r" % vw)

    # rich text: blocks must not run together across a boundary
    doc = json.dumps({"type": "root", "children": [
        {"type": "list", "children": [
            {"type": "list-item", "children": [{"type": "text", "value": "Weight: 410 lbs"}]},
            {"type": "list-item", "children": [{"type": "text", "value": "Model: MX-LS3-01"}]}]}]})
    flat = flatten_metafield(doc, "rich_text_field")
    if "lbsModel" in flat or "\n" not in flat:
        fails.append("rich-text blocks ran together: %r" % flat)

    # buckets
    for args, want in (((True, True), 1), ((True, False), 2),
                       ((False, True), 3), ((False, False), 4)):
        if bucket(*args) != want:
            fails.append("bucket%r != %d" % (args, want))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", help="Admin API pull JSON with products[]")
    ap.add_argument("--out", default="data/own-page-census.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: the census detectors failed their own controls:\n  "
                     + "\n  ".join(fails))
        print("census self-test: every detector fires, and none invents a value")
        return

    if not args.pull:
        ap.error("--pull is required unless --self-test")
    products = json.loads(pathlib.Path(args.pull).read_text())["products"]
    rows = census(products)

    n = len(rows)
    counts = {b: sum(1 for r in rows if r["bucket"] == b) for b in (1, 2, 3, 4)}
    summary = {
        "n": n,
        "manual_candidate_on_our_page": sum(1 for r in rows if r["manual_candidates"]),
        "any_document_reference": sum(1 for r in rows if r["manuals"]),
        "video_only_reference": sum(1 for r in rows if r["manuals"]
                                    and not r["manual_candidates"]),
        "model_number_present": sum(1 for r in rows if r["model_numbers"]),
        "model_number_equals_our_sku": sum(
            1 for r in rows if any(m["matches_our_sku"] for m in r["model_numbers"])),
        "shipping_weight_stated_in_text": sum(1 for r in rows if r["shipping_weight_stated"]),
        "shopify_variant_weight_nonzero": sum(1 for r in rows if r["shopify_variant_weight"]),
        "box_count_stated": sum(1 for r in rows if r["box_count_stated"]),
        "buckets": {str(b): counts[b] for b in (1, 2, 3, 4)},
    }
    doc = {"note": "Phase 1 census of InHouse's own product bodies and metafields. "
                   "No request was made to any host: this reads an Admin API pull "
                   "only. Drive URLs are constructed, never fetched.",
           "source_pull": args.pull, "summary": summary, "rows": rows}
    out = ROOT / args.out
    out.write_text(json.dumps(doc, indent=1) + "\n")

    print(f"census of {n} active sauna SKUs -> {args.out}\n")
    for k in ("manual_candidate_on_our_page", "any_document_reference",
              "video_only_reference", "model_number_present",
              "model_number_equals_our_sku", "shipping_weight_stated_in_text",
              "shopify_variant_weight_nonzero", "box_count_stated"):
        v = summary[k]
        print(f"  {k:34s} {v:>4} / {n}   {100*v/n:5.1f}%")
    print("\n  the 2x2:")
    for b in (1, 2, 3, 4):
        print(f"    {b}. {BUCKET_LABEL[b]:52s} {counts[b]:>4} / {n}   {100*counts[b]/n:5.1f}%")


if __name__ == "__main__":
    main()
