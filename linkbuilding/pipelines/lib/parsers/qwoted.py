#!/usr/bin/env python3
"""
Qwoted single-request parser.

One request per email, not a digest.

WHY EVERY ROW IS `requires_manual: true`
  A Qwoted email carries no journalist name, no journalist email, and no
  mailto — the only reply path is a per-recipient click redirect through
  url1940.qwoted.com. On top of that the query text itself is INCOMPLETE:
  plaintext truncates at ~420 characters with an ellipsis, and the HTML part
  truncates at the identical point (verified 2026-09-15 on all five captured
  requests — the HTML is ~5x larger but that is markup, not content). So the
  email cannot tell you who to contact OR what they fully asked. A human
  clicks through. Nothing here is auto-handleable, and that is a property of
  the source, not a limitation of this parser.

  Plaintext is therefore the parse target: same content as HTML, a fifth of
  the bytes.

INHERITED RULE 5 — routing is by sender, never subject.
"""

import re

SENDER_DOMAINS = ("qwoted.com",)
RESPOND_HOST = "url1940.qwoted.com"

OUTLET_RE = re.compile(r"^From:\s*(.+?)\s*$", re.M)
TAGS_RE = re.compile(r"Because you follow\s+(.+?)\s*$", re.M)
SUBMIT_RE = re.compile(r"^Submit By:\s*(.+?)\s*$", re.M)
RESPOND_RE = re.compile(r"RESPOND TO THIS REPORTER VIA QWOTED:\s*(\S+)", re.I)
HASHTAG_RE = re.compile(r"#(\w+)")
# "in about 24 hours" / "in 7 days" trails the absolute deadline.
RELATIVE_RE = re.compile(r"\s*\(in\s+(?:about\s+)?[^)]+\)\s*$")


class QwotedParseError(Exception):
    pass


def is_qwoted(from_email):
    return any(from_email.lower().endswith(d) for d in SENDER_DOMAINS)


def looks_like_request(body_plain):
    """A real request carries a reply path and a deadline. Welcome and
    verification mail carries neither — that is how noise is separated,
    without reading the subject."""
    t = body_plain or ""
    return bool(RESPOND_RE.search(t)) and bool(SUBMIT_RE.search(t))


def parse(body_plain, source_id="", headline_fallback=""):
    """Return a single item dict, or raise if this is not a request."""
    t = body_plain or ""
    if not looks_like_request(t):
        raise QwotedParseError("%s: no reply path or no deadline — not a request" % source_id)

    outlet = OUTLET_RE.search(t)
    tags_line = TAGS_RE.search(t)
    submit = SUBMIT_RE.search(t)
    respond = RESPOND_RE.search(t)

    quoted = [l.lstrip("> ").rstrip() for l in t.splitlines() if l.strip().startswith(">")]
    query = re.sub(r"\s+", " ", " ".join(quoted)).strip()
    truncated = query.endswith("...") or query.endswith("…")

    # Headline: the line between the outlet and the quoted block.
    headline = ""
    if outlet:
        tail = t[outlet.end():].lstrip("\n")
        for line in tail.splitlines():
            if line.strip() and not line.strip().startswith(">"):
                headline = line.strip()
                break
    if not headline:
        headline = headline_fallback

    deadline_raw = submit.group(1).strip() if submit else ""
    deadline_abs = RELATIVE_RE.sub("", deadline_raw).strip()

    return {
        "source_id": source_id,
        "outlet": outlet.group(1).strip() if outlet else "",
        "headline": headline,
        "query": query,
        "query_truncated": truncated,
        "deadline_raw": deadline_raw,
        "deadline": deadline_abs,
        "followed_tags": HASHTAG_RE.findall(tags_line.group(1)) if tags_line else [],
        "respond_url": respond.group(1) if respond else "",
        # Never auto-handled. See module docstring.
        "requires_manual": True,
        "journalist_name": None,
        "journalist_email": None,
    }
