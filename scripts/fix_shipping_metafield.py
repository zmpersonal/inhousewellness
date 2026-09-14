#!/usr/bin/env python3
"""Propose the correction to `custom.shipping_details` on active sauna SKUs.

THE DEFECT
`installation-assembly` (the $1,800 "Premium Installation Service" product) says
in its own body: "$1,800, all in ... There is no separate assembly labour bill
afterwards." The same store's `custom.shipping_details` metafield, on sauna
product pages, describes that same service as hourly: "Installation labor:
$50-$75/hr per installer". A buyer reading the sauna page and the service page
gets two different answers to what installation costs.

Round 1 client ruling 3 settles which is correct: $1,800 covers InHouse's
delivery and assembly only, as a flat fee. Electrician labour is separate,
third-party, and is never summed into it. So the metafield line is the stale one.

THIS SCRIPT DOES NOT WRITE. It is dry-run only by design -- there is no --apply
flag, because the apply path for this correction is the MCP relay (see below),
not this process. It emits a reviewable proposal and the exact per-handle
before/after. inh-seo hard rule 1 ("every write script defaults to --dry-run")
is honoured by having no write path here at all.

WHY THERE IS NO --apply HERE
This environment cannot reach admin.shopify.com (403 on CONNECT, organisation
egress policy), so a credentialed write cannot originate from this process. The
write is relayed through the Shopify MCP connector by the agent, using the
payloads this script emits -- the same "script computes, agent relays" split
scripts/schedule_week.py already uses, which keeps the judgement in code.

IDS ARE RESOLVED AT WRITE TIME, NOT HERE. The proposal is keyed by product
handle. Baking product ids into a proposal that a human may approve hours later
means writing against ids captured before the review; resolving handle -> id in
the same call that writes removes that window.

FIVE DISTINCT TEMPLATES, NOT ONE FIND-REPLACE
The 113 affected SKUs carry 5 distinct metafield values in 2 structural shapes:
  A  a rich-text `list` whose items carry the offending sentences  (99 SKUs)
  B  a single flat `paragraph` with the sentences inline           (14 SKUs)
and the wording differs between them ("Installation labor:" vs "Additional
labor costs apply:"). A single blind string replacement would silently miss the
variants -- which is how the original sweep missed this field in the first place.
Each shape gets its own transform, and every output is re-probed.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
# data/, not out/: out/ is gitignored, and a proposal that will be reviewed
# and then executed against a live store has to be in version history.
OUT = ROOT / "data" / "shipping-metafield-fix"

# The probe that found the defect. Reused here to prove the fix removes it.
RATE_RX = re.compile(r"\$\s?50\s?[–—-]\s?\$?75\s?/?\s?hr", re.I)
CONTROL = "$50–$75/hr per installer"

# The replacement copy. Wording tracks the `installation-assembly` product body
# verbatim where it can, so the two pages say the same thing in the same words.
FLAT_FEE = ("$1,800 flat, all in — inside delivery, placement in the room of your "
            "choice, unboxing and full assembly. There is no separate assembly "
            "labour bill afterwards.")
ELECTRICIAN = ("Electrical work is billed by your own licensed electrician, not by "
               "InHouse Wellness. Local rates typically run $75–$150+/hr.")

# Shape B: the exact sentences to replace, per template. Written out in full
# rather than pattern-matched, so a near-miss fails loudly instead of quietly
# rewriting the wrong span.
B_REPLACEMENTS = [
    ("Installation labor: $50–$75/hr per installer (varies by region); "
     "$75–$150+/hr for any licensed electrical work.",
     FLAT_FEE + " " + ELECTRICIAN),
]


def text_of(node):
    if node.get("type") == "text":
        return node.get("value", "")
    return "".join(text_of(c) for c in node.get("children", []))


def li(text, bold_prefix=None):
    """Build a rich-text list item. bold_prefix, when given, is emitted bold."""
    kids = []
    if bold_prefix is not None:
        kids.append({"type": "text", "value": bold_prefix, "bold": True})
        rest = text[len(bold_prefix):]
        if rest:
            kids.append({"type": "text", "value": rest})
    else:
        kids.append({"type": "text", "value": text})
    return {"type": "list-item", "children": kids}


def transform_shape_a(doc):
    """List shape: drop the 'labor:' label item and the $50-$75 item, and
    re-label the electrician item as third-party."""
    changed = False
    for block in doc["children"]:
        if block.get("type") != "list":
            continue
        items = block["children"]
        texts = [text_of(i) for i in items]
        # Locate the offending pair by meaning, not by index.
        lab = [n for n, t in enumerate(texts)
               if re.fullmatch(r"(Installation labor:|Additional labor costs apply:)", t.strip())]
        rate = [n for n, t in enumerate(texts) if RATE_RX.search(t)]
        elec = [n for n, t in enumerate(texts)
                if re.search(r"\$\s?75\s?[–—-]\s?\$?150", t) and not RATE_RX.search(t)]
        if not rate:
            continue
        drop = set(lab) | set(rate)
        new_items = []
        for n, item in enumerate(items):
            if n in drop:
                continue
            if n in elec:
                new_items.append(li(ELECTRICIAN, "Electrical work is billed by your own "
                                                 "licensed electrician, not by InHouse Wellness."))
                continue
            new_items.append(item)
        # The flat fee replaces the removed pair, in the position they occupied.
        at = min(drop)
        offset = sum(1 for n in drop if n < at)
        new_items.insert(at - offset, li(FLAT_FEE, "$1,800 flat, all in"))
        block["children"] = new_items
        changed = True
    return changed


def transform_shape_b(doc):
    """Flat-paragraph shape: replace the sentence inside whichever text node
    carries it. Only exact, full-sentence matches are accepted."""
    changed = False

    def walk(node):
        nonlocal changed
        if node.get("type") == "text":
            v = node.get("value", "")
            for old, new in B_REPLACEMENTS:
                if old in v:
                    node["value"] = v.replace(old, new)
                    changed = True
            return
        for c in node.get("children", []):
            walk(c)

    walk(doc)
    return changed


def surviving_sentence_check(before_text, after_text):
    """Every sentence in the original must still be present afterwards, EXCEPT the
    ones this fix is supposed to remove. Returns the list of wrongly-lost sentences.

    This guard exists because it caught a real bug. One template (x1) packs the
    whole Premium Installation section into a SINGLE list item with ' u2022 '
    separators. The list transform saw a list item matching the rate probe and
    dropped the item -- taking 'Includes White Glove Service...', 'Electrical work
    not included...' and the scheduling line with it. The output passed the rate
    probe (the defect was gone) and was still wrong. A probe that only asks 'is
    the bad thing gone' cannot see content it silently deleted.
    """
    allowed_to_vanish = re.compile(
        r"installation labor|additional labor costs apply|\$\s?50\s?[–—-]"
        r"|per installer|for any licensed electrical|for licensed electricians", re.I)
    split = lambda s: [p.strip() for p in re.split(r"(?<=[.!?])\s+|•", s) if p.strip()]
    after_norm = re.sub(r"\s+", " ", after_text)
    lost = []
    for sent in split(before_text):
        if allowed_to_vanish.search(sent):
            continue
        core = re.sub(r"\s+", " ", sent)
        if core not in after_norm:
            lost.append(sent)
    return lost


def propose(value):
    """Return (new_value, shape) or (None, reason).

    Shape B is tried FIRST. It replaces one exact, full sentence, so it cannot
    take neighbouring content with it. Shape A edits whole list items and is the
    blunter of the two, so it only runs when the precise transform found nothing.
    """
    doc = json.loads(value)
    if transform_shape_b(doc):
        return json.dumps(doc, ensure_ascii=False, separators=(",", ":")), "B-sentence"
    doc = json.loads(value)
    if transform_shape_a(doc):
        return json.dumps(doc, ensure_ascii=False, separators=(",", ":")), "A-list"
    return None, "NO_TRANSFORM_MATCHED"


def main():
    assert RATE_RX.search(CONTROL), "PROBE BROKEN: control string does not match"
    src = pathlib.Path(sys.argv[1])
    templates = json.loads(src.read_text())

    OUT.mkdir(parents=True, exist_ok=True)
    proposal = {
        "generated_at": "2026-09-14",
        "status": "PROPOSED - NOT APPLIED",
        "ruling": "Round 1 ruling 3: $1,800 covers InHouse delivery and assembly only, "
                  "flat. Electrician labour is separate, third-party, never summed in.",
        "metafield": {"namespace": "custom", "key": "shipping_details", "type": "rich_text_field"},
        "apply_path": "Shopify MCP metafieldsSet, handle resolved to id at write time",
        "templates": [],
    }
    total = 0
    for sha, rec in templates.items():
        new, shape = propose(rec["value"])
        if new is None:
            sys.exit(f"HALT: template {sha} matched no transform ({shape}). "
                     f"Refusing to emit a partial proposal.")
        # The fix must remove the defect...
        if RATE_RX.search(new):
            sys.exit(f"HALT: template {sha} still matches the rate probe after transform.")
        # ...and must not take anything else with it.
        before_t, after_t = text_of(json.loads(rec["value"])), text_of(json.loads(new))
        lost = surviving_sentence_check(before_t, after_t)
        if lost:
            sys.exit(f"HALT: template {sha} ({shape}) silently dropped {len(lost)} "
                     f"sentence(s) it should have kept:\n  " + "\n  ".join(repr(s) for s in lost))
        proposal["templates"].append({
            "sha_before": sha,
            "shape": shape,
            "sku_count": len(rec["handles"]),
            "handles": sorted(rec["handles"]),
            "before_text": before_t,
            "after_text": after_t,
            "before_value": rec["value"],
            "after_value": new,
        })
        total += len(rec["handles"])

    proposal["affected_sku_count"] = total
    (OUT / "proposal.json").write_text(json.dumps(proposal, indent=1, ensure_ascii=False) + "\n")

    print(f"PROPOSAL (not applied) -> {(OUT / 'proposal.json').relative_to(ROOT)}")
    print(f"  templates: {len(proposal['templates'])}   SKUs affected: {total}")
    for t in proposal["templates"]:
        print(f"    {t['sha_before']}  {t['shape']:12s}  x{t['sku_count']}")
    print("  rate probe on every proposed value: 0 matches")


if __name__ == "__main__":
    main()
