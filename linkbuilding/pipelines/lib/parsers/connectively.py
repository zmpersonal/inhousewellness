#!/usr/bin/env python3
"""
Connectively alert-digest parser.

CONNECTIVELY AND FEATURED ARE THE SAME PRODUCT. Featured acquired Connectively
in 2025 and in 2026 migrated its own platform onto the Connectively brand. The
SENDING DOMAINS STILL DIFFER, though, and that is what routing keys on:

    connectively.us   -> alert digests (this parser) and onboarding mail
    featured.com      -> auth mail only; has never sent a digest

So `Media/Featured` is kept as a route rather than retired. Deleting it would
mean a Featured-domain digest, if one ever arrives, lands nowhere and is
counted as nothing — and "nothing arrived" is indistinguishable from "we
stopped looking", which is the failure mode this project keeps paying for.

Structure was confirmed identical across both digests captured 2026-09-16 and
2026-09-17. See `format_variance()`.

WHY Q&A ROWS ARE `requires_manual: True`
  Connectively is the PLATFORM product — browse, filter, pitch in-app. Its
  questions carry no journalist name, no journalist address and no mailto. The
  only route is a single-use magic-link:

      https://connectively.us/api/auth/magic-link/verify?token=…&callbackURL=…

  That is an authentication redirect into the web app, not a reply path. A
  human clicks through and pitches in the product. Nothing here constructs an
  address, and no address is inferred from the outlet name.

  OPPORTUNITY rows are the exception and only sometimes: syndicated items
  occasionally carry a third-party relay address (`send+<id>@tmxmessenger.com`,
  a ResponseSource/TMX relay). That address is READ OUT OF THE MAIL when it is
  there. It has never appeared on a Q&A item.

INHERITED RULE 5 — routing is by sender, never subject.
"""

import re

SENDER_DOMAINS = ("connectively.us",)
# Onboarding/marketing comes from community@; digests come from noreply@.
# Both are in-domain, so `looks_like_digest` does the separating, not the
# address — same discipline as HARO, where lifecycle mail shares the sender.
MAGIC_LINK_HOST = "connectively.us/api/auth/magic-link"

SECTION_RE = re.compile(r"^([A-Z][A-Z &]*ALERTS)\s*$", re.M)
# Exactly "Answer by <date>" / "View by <date>" — the item terminator.
# NOT "View All Questions" / "View New Opportunities", which are navigation.
DEADLINE_RE = re.compile(r"^(Answer|View) by\s+(.+?)\s*$")
COUNT_RE = re.compile(r"^(\d+)\s+alerts?$")
CATEGORY_RE = re.compile(r"^[A-Z][A-Z &/]{1,30}$")
EMPTY_SECTION_RE = re.compile(r"^None of the alerts", re.I)
URL_RE = re.compile(r"https?://\S+")
BARE_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")
# callbackURL=%2Fexperts%2Fquestions%2F<slug> — a stable per-question id, which
# is a far better dedup key than a hash of body text that the platform may
# reword between sends.
SLUG_RE = re.compile(r"callbackURL=%2Fexperts%2F(?:questions|opportunities)%2F([A-Za-z0-9\-]+)")


class ConnectivelyParseError(Exception):
    pass


def is_connectively(from_email):
    return any((from_email or "").lower().endswith(d) for d in SENDER_DOMAINS)


def looks_like_digest(body_plain):
    """A digest has the section headers. The four onboarding emails
    ("Welcome to Connectively!", "Create your Profile", "Answer questions, get
    featured", "Monitor Every Press Opportunity") have none of them."""
    b = body_plain or ""
    return bool(SECTION_RE.search(b)) and "ALERTS" in b


def _paras(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _strip_links(s):
    """Query text and its trailing magic-link share a paragraph."""
    return re.sub(r"\s+", " ", URL_RE.sub("", s)).strip()


def parse(body_plain, source_id=""):
    """Return a list of item dicts, one per alert."""
    if not looks_like_digest(body_plain):
        raise ConnectivelyParseError(
            "%s: no ALERTS section headers — not a digest. Connectively also "
            "sends onboarding mail from the same domain." % source_id)

    # Split into sections, keeping each header with its body.
    marks = list(SECTION_RE.finditer(body_plain))
    if not marks:
        raise ConnectivelyParseError("%s: no sections" % source_id)

    items, declared = [], 0
    for i, m in enumerate(marks):
        section = m.group(1).strip()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body_plain)
        paras = _paras(body_plain[m.end():end])

        if any(EMPTY_SECTION_RE.match(p) for p in paras):
            continue          # a section with no matches is not a failure

        category = None
        for j, p in enumerate(paras):
            cm = COUNT_RE.match(p)
            if cm:
                declared += int(cm.group(1))
                continue
            if CATEGORY_RE.match(p) and len(p) < 32:
                category = p.title()
                continue
            dm = DEADLINE_RE.match(p)
            if not dm:
                continue
            # Walk back: [query] [outlet] [Answer by …]
            if j < 2:
                raise ConnectivelyParseError(
                    "%s: '%s' at paragraph %d has no query/outlet before it"
                    % (source_id, p[:40], j))
            outlet = _strip_links(paras[j - 1])
            body = paras[j - 2]

            reply = BARE_EMAIL_RE.search(p) or BARE_EMAIL_RE.search(body)
            slug = SLUG_RE.search(p) or SLUG_RE.search(body)
            link = URL_RE.search(p) or URL_RE.search(body)

            items.append({
                "item_no": len(items) + 1,
                "source_id": source_id,
                "platform": "connectively",
                "section": section,
                "category": category,
                "summary": _strip_links(body)[:140],
                "query": _strip_links(body),
                "outlet": outlet,
                "media_outlet": outlet,
                "deadline": dm.group(2).strip(),
                "deadline_verb": dm.group(1),
                "slug": slug.group(1) if slug else None,
                "respond_url": link.group(0) if link else None,
                # Read, never constructed. A magic-link is an auth redirect, so
                # a row is only directly answerable if a real address is in the
                # mail — which happens on syndicated opportunity items only.
                "journalist_email": reply.group(0) if reply else None,
                "journalist_name": None,
                "requires_manual": reply is None,
                "query_truncated": False,
            })

    # Connectively declares "N alerts" per category. That is a free
    # cross-check on the parse and it is asserted rather than trusted: a
    # silently dropped item would otherwise look exactly like a quiet day.
    if declared and declared != len(items):
        raise ConnectivelyParseError(
            "%s: digest declares %d alert(s) but %d were parsed. A dropped "
            "item is indistinguishable from a quiet day downstream."
            % (source_id, declared, len(items)))
    return items


def field_coverage(items):
    keys = ("section", "category", "summary", "query", "outlet", "deadline",
            "slug", "respond_url", "journalist_email")
    return {"label": {k: sum(1 for it in items if k in it) for k in keys},
            "value": {k: sum(1 for it in items if (it.get(k) or "")) for k in keys}}


def format_variance(digests):
    """Does the structure vary between sends? `digests` is (label, body)."""
    rows, ok_core, ok_sections = True, True, True
    rows = []
    core = ("query", "outlet", "deadline", "respond_url")
    sections_seen = None
    for label, body in digests:
        items = parse(body, source_id=label)
        cov = field_coverage(items)
        n = len(items)
        missing = sorted(k for k in core if cov["value"].get(k, 0) != n)
        if missing:
            ok_core = False
        secs = sorted({it["section"] for it in items})
        if sections_seen is None:
            sections_seen = secs
        elif secs != sections_seen:
            ok_sections = False
        rows.append({"digest": label, "items": n, "sections": secs,
                     "core_missing": missing,
                     "with_reply_address": cov["value"]["journalist_email"],
                     "requires_manual": sum(1 for it in items if it["requires_manual"]),
                     "with_slug": cov["value"]["slug"]})
    return {"digests": rows, "core_fields": list(core),
            "core_stable": ok_core, "sections_stable": ok_sections,
            "stable": ok_core and ok_sections}
