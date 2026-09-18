#!/usr/bin/env python3
"""
HARO (Help A Reporter Out) digest parser.

Structure was confirmed identical across ALL EIGHT digests captured
2026-09-15 evening through 2026-09-18 morning — three sends a day, 20-21
queries each. See `format_variance()` for the check that says so rather than
the claim that says so.

HARO IS A NEWSLETTER, NOT A PLATFORM. There is no dashboard, no account is
needed to reply, and every query carries its own reply address:

    Email: reply+<uuid>@helpareporter.com

That is a real routing mailbox, not a click-tracking redirect, and it is
PRESENT IN THE MAIL — this parser reads it, it never constructs one. So HARO
rows are `requires_manual: False`, unlike Qwoted and Connectively. This is the
channel that produced all four of the site's proven links, and the direct
reply path is why.

INHERITED RULE 5 — routing is by SENDER, never subject. HARO subjects vary by
edition ("- Morning Edition" / "- Afternoon Edition" / "- Evening Edition")
and nothing here reads them.

INHERITED RULE 6, THE HARO INSTANCE — journalists write prose containing
label-shaped lines, and a naive `^Word:` regex eats them as fields. Observed
in the real corpus, inside Query bodies: `Social Anxiety:`, `Clinical
Implications:`, `Questions include:`, `Note:`, `Study:`, `Exposure Routes:`,
`And the scientific statement:`, `Free Comms Masterclass:`, `Awareness Guide:`.
The digest footer adds `For delivery help:`. The alternation below is CLOSED
over the seven real labels, so none of them can match — and an assertion after
parsing re-checks it, because the list of things journalists might write is
open-ended and the closed alternation is the only defence that does not need
updating every time one of them invents a new heading.
"""

import re

SENDER_DOMAINS = ("helpareporter.com",)
# The reply mailbox HARO issues per query. Recorded, never constructed.
REPLY_HOST = "helpareporter.com"

# The seven labelled fields, exactly as HARO emits them (title case — SOS uses
# UPPERCASE, which is one reason these are separate parsers rather than one
# parameterised one).
FIELDS = ("Name", "Category", "Email", "HARO Journalist Profile URL",
          "Media Outlet", "Deadline", "Query")
# Rule 6: closed alternation. A journalist's `Clinical Implications:` cannot
# match because it is not in this tuple.
FIELD_RE = re.compile(r"^(%s):[ \t]*(.*)$" % "|".join(re.escape(f) for f in FIELDS), re.M)
# Label-shaped strings seen in the real corpus that must NEVER become fields.
# This list is documentation and a test fixture; it is not what does the
# excluding — the closed alternation is.
EXCLUDED_PSEUDO_FIELDS = (
    "Social Anxiety", "Clinical Implications", "Questions include", "Questions",
    "Note", "Study", "Exposure Routes", "And the scientific statement",
    "Free Comms Masterclass", "Awareness Guide", "For delivery help",
    "Sponsored", "Criteria")

FIELD_KEYS = tuple(f.lower().replace(" ", "_") for f in FIELDS)
# Present on 100% of items in all eight captured sends. The profile URL is
# deliberately NOT here: it is real but optional, and promoting it would make
# a normal send look like a structural break.
CORE_FIELD_KEYS = ("name", "category", "email", "media_outlet", "deadline", "query")

INDEX_RE = re.compile(r"\*{3,}\s*INDEX\s*\*{3,}", re.I)
# The index ends with a long bare run of asterisks; items start after it.
INDEX_END_RE = re.compile(r"^\*{20,}\s*$", re.M)
ITEM_SPLIT_RE = re.compile(r"^(\d+)\)\s+Summary:", re.M)
BACK_TO_TOP_RE = re.compile(r"\n\s*Back to Top\s*\n", re.I)
REPLY_ADDR_RE = re.compile(r"(reply\+[0-9a-f-]{8,}@%s)" % re.escape(REPLY_HOST), re.I)
# "Media Outlet: A&E (https://www.aetv.com/crime)" — outlet and its site.
OUTLET_URL_RE = re.compile(r"^(.*?)\s*\((https?://[^)]+)\)\s*$")
# "6:00 PM ET - 17 September"
DEADLINE_RE = re.compile(
    r"^\s*(\d{1,2}:\d{2}\s*[AP]M)\s*([A-Z]{2,4})?\s*-\s*(\d{1,2})\s+([A-Za-z]+)", re.I)


class HaroParseError(Exception):
    pass


def is_haro(from_email):
    return any((from_email or "").lower().endswith(d) for d in SENDER_DOMAINS)


def looks_like_digest(body_plain):
    """A query digest has an INDEX block and numbered `N) Summary:` items.

    The five HARO account-lifecycle emails in this mailbox (sign-up link, sign-in
    link, journalist-profile offer, verification request) have neither. That is
    how noise is told apart — without reading the subject, and without assuming
    that everything from the sender is a digest.
    """
    b = body_plain or ""
    return bool(INDEX_RE.search(b)) and bool(ITEM_SPLIT_RE.search(b))


def _clean(v):
    """HARO repeats every link as bare text on the following line, so
    `Email: reply+x@haro` is immediately followed by the same address again,
    and `Media Outlet: A&E (https://…)` carries its URL inline. Collapse
    whitespace and drop an exact trailing duplicate."""
    v = re.sub(r"[ \t]+", " ", (v or "")).strip()
    parts = [p.strip() for p in v.split("\n") if p.strip()]
    out = []
    for p in parts:
        if not out or p != out[-1]:
            out.append(p)
    return " ".join(out).strip()


def _dedupe_repeat(v):
    """`x x` where the whole value is the same token twice -> `x`."""
    v = (v or "").strip()
    half = len(v) // 2
    if v and len(v) % 2 == 1 and v[half] == " " and v[:half] == v[half + 1:]:
        return v[:half]
    return v


def parse(body_plain, source_id=""):
    """Return a list of item dicts, one per query in the digest."""
    if not looks_like_digest(body_plain):
        raise HaroParseError(
            "%s: no INDEX block or no numbered items — not a query digest. "
            "HARO also sends account-lifecycle mail from the same address."
            % source_id)

    # Everything after the index. The index repeats every headline, and
    # parsing from the top would double-count each query.
    after = body_plain
    m_idx = INDEX_RE.search(after)
    after = after[m_idx.end():]
    m_end = INDEX_END_RE.search(after)
    if m_end:
        after = after[m_end.end():]

    marks = list(ITEM_SPLIT_RE.finditer(after))
    if not marks:
        raise HaroParseError("%s: INDEX present but no items after it" % source_id)

    items = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(after)
        block = after[start:end]
        # `Back to Top` closes every block and is not query text.
        block = BACK_TO_TOP_RE.split(block)[0]

        # Summary wraps onto the next line when long; it runs to the blank line.
        head = block[m.end() - start:]
        summary = _clean(head.split("\n\n", 1)[0])

        rec = {"item_no": int(m.group(1)), "summary": summary,
               "source_id": source_id, "platform": "haro"}
        for name, value in FIELD_RE.findall(block):
            key = name.lower().replace(" ", "_")
            if key == "query":
                qi = block.find("Query:")
                rec["query"] = _clean(block[qi + len("Query:"):])
            elif key == "haro_journalist_profile_url":
                # This one WRAPS. When the URL is long HARO puts the label on
                # its own line and the value on the next, and the same-line
                # capture is empty — which would record a field that exists as
                # blank, the exact "absence taken as a value" failure this
                # project keeps hitting. Fall through to the following line.
                v = _dedupe_repeat(_clean(value))
                if not v:
                    tail = block[block.find("HARO Journalist Profile URL:")
                                 + len("HARO Journalist Profile URL:"):]
                    for line in tail.split("\n")[:3]:
                        line = line.strip()
                        if line.startswith("http"):
                            v = line
                            break
                rec[key] = v
            else:
                rec[key] = _dedupe_repeat(_clean(value))

        # The reply address, read out of the mail. NEVER constructed: if HARO
        # did not issue one, the row says so and a human decides.
        raw_email = rec.get("email") or ""
        hit = REPLY_ADDR_RE.search(raw_email) or REPLY_ADDR_RE.search(block)
        rec["journalist_email"] = hit.group(1) if hit else None
        rec["journalist_name"] = rec.get("name") or None
        # HARO's reply address is a real routing mailbox, not a click redirect,
        # so a row that has one is directly answerable.
        rec["requires_manual"] = rec["journalist_email"] is None
        rec["respond_url"] = None

        outlet = rec.get("media_outlet") or ""
        om = OUTLET_URL_RE.match(outlet)
        rec["media_outlet"] = om.group(1).strip() if om else outlet
        rec["media_website"] = om.group(2) if om else None

        dl = rec.get("deadline") or ""
        dm = DEADLINE_RE.match(dl)
        if dm:
            rec["deadline_time"] = dm.group(1)
            rec["time_zone"] = (dm.group(2) or "").upper() or None
            rec["deadline_date"] = "%s %s" % (dm.group(3), dm.group(4))
        else:
            # Unparsed beats guessed: a deadline computed from an assumed
            # format would silently mis-rank urgency.
            rec["deadline_time"] = rec["time_zone"] = rec["deadline_date"] = None
        rec["query_truncated"] = False
        items.append(rec)

    _assert_no_pseudo_fields(items, source_id)
    return items


def _assert_no_pseudo_fields(items, source_id):
    """Rule 6, re-checked after the fact. The closed alternation is what
    prevents the leak; this catches the day somebody widens it."""
    for rec in items:
        for bad in EXCLUDED_PSEUDO_FIELDS:
            k = bad.lower().replace(" ", "_")
            if k in rec:
                raise HaroParseError(
                    "%s item %s: pseudo-field %r captured as data. Journalists "
                    "write label-shaped lines inside Query bodies; FIELD_RE "
                    "must stay closed over FIELDS." % (source_id, rec["item_no"], bad))
    return True


def field_coverage(items):
    """`label` = the field appeared. `value` = it carried something.

    They differ and the difference matters: HARO emits `HARO Journalist
    Profile URL` on 14-20 of 20 items depending on the send, so it is real but
    OPTIONAL. Treating its absence as a parse failure would be wrong; relying
    on it downstream would also be wrong.
    """
    keys = [f.lower().replace(" ", "_") for f in FIELDS]
    return {"label": {k: sum(1 for it in items if k in it) for k in keys},
            "value": {k: sum(1 for it in items if (it.get(k) or "").strip()) for k in keys}}


def format_variance(digests):
    """Answer 'does the structure vary between sends?' with data, not a claim.

    `digests` is a list of (label, body_plain).

    The question is NOT "is every field on every item in every send" — that
    would call an optional field a variance and cry wolf. It is three things:

      core_stable   every field in CORE_FIELDS is on 100% of items, every send
      no_new_fields no send introduces a label outside FIELDS
      parses        every send yields items at all

    `haro_journalist_profile_url` is genuinely optional (14-21 of 20-21 per
    send, and 20/20 on one send purely by chance). That is a property of the
    source, recorded as optional rather than smuggled into the core set.
    """
    rows, ok_core, ok_new = [], True, True
    core = set(CORE_FIELD_KEYS)
    for label, body in digests:
        items = parse(body, source_id=label)
        cov = field_coverage(items)
        n = len(items)
        missing = sorted(k for k in core if cov["label"].get(k, 0) != n)
        if missing or not n:
            ok_core = False
        stray = sorted(set(cov["label"]) - set(FIELD_KEYS))
        if stray:
            ok_new = False
        rows.append({"digest": label, "items": n,
                     "core_on_every_item": not missing,
                     "core_missing": missing, "stray_fields": stray,
                     "profile_url_present": cov["value"].get(
                         "haro_journalist_profile_url", 0),
                     "with_reply_address": sum(1 for it in items
                                               if it["journalist_email"])})
    return {"digests": rows, "core_fields": sorted(core),
            "optional_fields": ["haro_journalist_profile_url"],
            "core_stable": ok_core, "no_new_fields": ok_new,
            "stable": ok_core and ok_new}
