#!/usr/bin/env python3
"""
Source of Sources digest parser.

Structure was confirmed identical across both digests captured on 2026-09-15
(morning and afternoon sends). Each digest carries an `*** INDEX ***` block
followed by N items, each opening `N) SUMMARY:` and carrying ten labelled
fields.

INHERITED RULE 5 — never match on the subject line. SOS subjects vary between
sends ("...Media Queries" vs "...Media Queries - \"24 Hour Ad Sale!\" Edition").
Routing to this parser is by SENDER; nothing here reads the subject.

INHERITED RULE 6 — `IMPORTANT:` appears twice per digest as a non-item field
(house notices, not query data). A naive `^[A-Z ]+:` field regex captures it
and corrupts the field set of whichever item it lands in. It is excluded
explicitly, by name, in FIELD_RE.
"""

import re

SENDER_DOMAINS = ("sourceofsources.com",)

# The ten labelled fields, exactly. Anything else that looks like a field —
# IMPORTANT, ADVERTISEMENT, INDEX — is deliberately NOT in this set.
FIELDS = ("CATEGORY", "NAME", "EMAIL", "MUCK RACK URL", "MEDIA OUTLET",
          "MEDIA WEBSITE", "DEADLINE DATE", "DEADLINE TIME", "TIME ZONE", "QUERY")
# Rule 6: the alternation is closed over FIELDS. IMPORTANT cannot match.
FIELD_RE = re.compile(r"^(%s):[ \t]*(.*)$" % "|".join(re.escape(f) for f in FIELDS), re.M)
# Pseudo-fields that LOOK like labelled fields and must never be captured as
# data. SUMMARY is deliberately NOT here: it is the item header this parser
# sets itself, not something FIELD_RE could leak.
EXCLUDED_PSEUDO_FIELDS = ("IMPORTANT", "INDEX", "AD", "ADVERTISEMENT")

INDEX_RE = re.compile(r"\*{3,}\s*INDEX\s*\*{3,}", re.I)
ITEM_SPLIT_RE = re.compile(r"^(\d+)\)\s+SUMMARY:", re.M)


class SosParseError(Exception):
    pass


def is_sos(from_email):
    return any(from_email.lower().endswith(d) for d in SENDER_DOMAINS)


def looks_like_digest(body_plain):
    """A digest has an INDEX block and at least one numbered SUMMARY item.
    The SOS welcome email has neither — that is how noise is told apart,
    without reading the subject."""
    return bool(INDEX_RE.search(body_plain or "")) and bool(ITEM_SPLIT_RE.search(body_plain or ""))


MAILTO_DUP_RE = re.compile(r"\s*\(mailto:[^)]*\)")
URL_DUP_RE = re.compile(r"\s*\((https?://[^)]*)\)$")


def _clean(v):
    """SOS renders links as 'value (mailto:value)' / 'value (https://value)'
    in the plaintext part. The parenthetical is a duplicate of the value, and
    leaving it in means every downstream consumer has to strip it — including
    anything that tries to actually send to the address."""
    v = re.sub(r"\s+", " ", (v or "")).strip()
    v = MAILTO_DUP_RE.sub("", v)
    v = URL_DUP_RE.sub("", v)
    return v.strip()


def parse(body_plain, source_id=""):
    """Return a list of item dicts, one per query in the digest."""
    if not looks_like_digest(body_plain):
        raise SosParseError("%s: no INDEX block or no numbered items — not a digest" % source_id)

    # Everything after the INDEX block. The index itself repeats each headline
    # and would otherwise double-count.
    after = INDEX_RE.split(body_plain, maxsplit=1)[-1]

    marks = list(ITEM_SPLIT_RE.finditer(after))
    if not marks:
        raise SosParseError("%s: INDEX present but no items after it" % source_id)

    items = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(after)
        block = after[start:end]

        summary = _clean(block[m.end() - start:].split("\n", 1)[0])
        rec = {"item_no": int(m.group(1)), "summary": summary, "source_id": source_id}
        for name, value in FIELD_RE.findall(block):
            key = name.lower().replace(" ", "_")
            if key == "query":
                # QUERY runs to the end of the block, not to end of line.
                qi = block.find("QUERY:")
                rec["query"] = _clean(block[qi + len("QUERY:"):])
            else:
                rec[key] = _clean(value)
        items.append(rec)

    # Rule 6 assertion: no pseudo-field leaked into any record.
    for rec in items:
        for bad in EXCLUDED_PSEUDO_FIELDS:
            k = bad.lower().replace(" ", "_")
            if k in rec:
                raise SosParseError(
                    "%s item %s: pseudo-field %r was captured as data. Rule 6 "
                    "exists because IMPORTANT: appears twice per digest as a "
                    "house notice." % (source_id, rec["item_no"], bad))
    return items


def field_coverage(items):
    """Two different questions, deliberately separated.

    `label` — the field LABEL appeared in the block. This is the structural
    guarantee a parser can rely on.
    `value` — the label carried a non-empty value.

    They differ: SOS emits `MUCK RACK URL:` on every item but leaves it blank
    for roughly a quarter of journalists. Treating a blank value as a parse
    failure would be wrong; treating it as a guaranteed field downstream would
    also be wrong. Round 5 needs to know which fields it can depend on.
    """
    keys = [f.lower().replace(" ", "_") for f in FIELDS]
    return {"label": {k: sum(1 for it in items if k in it) for k in keys},
            "value": {k: sum(1 for it in items if (it.get(k) or "").strip()) for k in keys}}
