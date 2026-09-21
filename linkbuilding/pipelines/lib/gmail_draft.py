#!/usr/bin/env python3
"""
Gmail drafts for approved HARO replies.

THE AMENDED MAILBOX RULE, IN ONE LINE: read-only, with one exception — the
pipeline may CREATE a draft. It may never send, delete, archive, label, or
modify any existing message or draft.

That exception is narrow on purpose and is enforced here rather than
remembered. This module names exactly one write action, `gmail_create_draft`,
and a test asserts that no send/delete/archive/label/trash/modify verb appears
anywhere in the file. Everything else it does is read-only.

WHY A DRAFT AND NOT A SEND. The draft lands in a human's mailbox and sits
there until they press the button. Every gate that came before — the
attribution guard, the citation checks, the experience flags, the expert
review — exists so that what reaches a journalist has been looked at by a
person. A send path here would make all of them advisory.
"""

import json, os, re
from html import unescape as _unescape

HERE = os.path.dirname(os.path.abspath(__file__))
# The ONE write action. Named once, so there is a single place to audit.
CREATE_DRAFT_TOOL = "gmail_create_draft"
CREATE_DRAFT_ACTION = "draft_v2"
SELECTED_API = "GoogleMailV2CLIAPI"
# Pinned mailbox. The draft is created in julian@'s Gmail; `timur@` is a
# verified Send-as alias on it (checked 2026-09-21), so From can be set.
CONNECTION_ID = "029715c5-3a50-8935-b200-6e6eba55ac62"
FROM_ADDRESS = "timur@inhousewellness.com"
REPLY_HOST = "helpareporter.com"
_REPLY_RE = re.compile(r"^reply\+[0-9a-f-]{8,}@%s$" % re.escape(REPLY_HOST), re.I)


class GmailDraftError(Exception):
    pass


def assert_haro_reply_address(addr):
    """The recipient is READ from the stored item and never constructed.

    A HARO reply address is a per-query routing mailbox issued by HARO. There
    is no rule that generates one, so a value that does not match the issued
    shape did not come from a digest, and guessing one would send a pitch into
    a void or, worse, to somebody else's query.
    """
    if not addr:
        raise GmailDraftError(
            "no reply address on this item. HARO issues one per query and it "
            "is read from the mail; it is never constructed.")
    if not _REPLY_RE.match(addr.strip()):
        raise GmailDraftError(
            "%r is not a HARO-issued reply address (expected "
            "reply+<uuid>@%s). Refusing to guess a recipient."
            % (addr, REPLY_HOST))
    return True


def build_draft_args(item, draft_text, subject, flag):
    """The exact arguments for one `gmail_create_draft` call.

    Every precondition is checked here rather than at the call site, because
    the call site is an agent following instructions and this is the last
    place code runs before an email exists.
    """
    if (item.get("platform") or "").lower() != "haro":
        raise GmailDraftError(
            "%s is a %s item. Only HARO items get a Gmail draft: Connectively "
            "and Qwoted have no reply address, only an in-platform "
            "click-through, so there is nowhere for an email to go."
            % (item.get("key"), item.get("platform")))
    assert_haro_reply_address(item.get("reply_path"))
    if not (subject or "").strip():
        raise GmailDraftError(
            "no subject. It must be the query's title as it appeared in the "
            "HARO digest, and it is not invented here.")
    if flag and flag in (draft_text or ""):
        raise GmailDraftError(
            "draft still contains %s. A Gmail draft must never carry an "
            "unconfirmed experience flag — it is one keystroke from being "
            "sent." % flag)
    if not (draft_text or "").strip():
        raise GmailDraftError("empty draft body")
    return {
        "selected_api": SELECTED_API,
        "action": CREATE_DRAFT_ACTION,
        "tool_name": CREATE_DRAFT_TOOL,
        "connection_id": CONNECTION_ID,
        "params": {
            "to": [item["reply_path"]],
            "from": FROM_ADDRESS,
            "subject": subject,
            "body": draft_text,
            "body_type": "plain",
            # No attachments, ever. Nothing in this pipeline produces one and
            # a journalist inbox does not want one.
        },
    }


def verify_created(readback, expect_to, expect_subject, credential_line, flag):
    """Read the created draft back and check it is what we asked for.

    Checking the arguments we sent proves only that we sent them — the same
    lesson the mailbox rules already carry about asserting Delivered-To on the
    response rather than the request.
    """
    blob = json.dumps(readback) if not isinstance(readback, str) else readback
    problems = []
    if expect_to not in blob:
        problems.append("recipient %r not found in the created draft" % expect_to)
    if expect_subject not in blob:
        problems.append("subject %r not found" % expect_subject)
    if credential_line not in blob:
        problems.append("the verbatim credential line is not in the body")
    if flag in blob:
        problems.append("the draft CONTAINS %s — it must not" % flag)
    if problems:
        raise GmailDraftError("draft read-back failed:\n  - %s"
                              % "\n  - ".join(problems))
    return True


# --------------------------------------------------------------------------
# detecting the send — read-only on Sent
# --------------------------------------------------------------------------
def sent_query():
    """Gmail search for replies already sent to HARO reply addresses.

    ⚠️ NO WILDCARD IN AN ADDRESS TERM. This used to be
    `to:reply+*@helpareporter.com`, which Gmail does not support: it matched
    NOTHING and returned an empty result for a mailbox that contained the
    send. `detect-sends` would have reported "nothing found" forever, which
    reads exactly like "nothing was sent" — the confident false negative this
    project keeps paying for. Measured against the live mailbox on
    2026-09-21: the wildcard form returned 0 results, the domain form
    returned the real send.

    The address shape is then enforced in `find_sent`, where a regex can
    actually do it, so widening the query does not widen what is recorded.
    """
    return "in:sent to:%s" % REPLY_HOST


# Positive, closed evidence of NON-delivery. HARO mails a notice when a pitch
# is rejected before it reaches the journalist (AI-detection score, for one).
# Without this the send looks clean in Sent and gets counted as a live pitch
# awaiting publication — a wrong outcome attributed to the right text.
UNDELIVERED_MARKERS = (
    "wasn't delivered", "was not delivered", "wasn’t delivered",
    "didn't reach the journalist", "did not reach the journalist",
    "didn’t reach the journalist",
)


def undelivered_query():
    """Gmail search for HARO non-delivery notices. Read-only."""
    return "from:%s in:anywhere" % REPLY_HOST


def find_undelivered(payload):
    """{reply_address: {reason, notified_at, gmail_id}} from HARO notices.

    Requires BOTH a helpareporter.com sender and one of the closed markers
    above, so an ordinary digest mentioning a reply address cannot be read as
    a bounce. Absence of a notice is NOT evidence of delivery — HARO sends no
    positive receipt — so this only ever reports non-delivery it actually saw.
    """
    out = {}
    for m in (payload or {}).get("results") or []:
        frm = ((m.get("from") or {}).get("email") or "").lower()
        if not frm.endswith(REPLY_HOST):
            continue
        body = _sent_body(m) or ""
        low = body.lower()
        if not any(mark in low for mark in UNDELIVERED_MARKERS):
            continue
        for addr in re.findall(r"reply\+[0-9a-f-]{8,}@%s" % re.escape(REPLY_HOST),
                               body, re.I):
            out[addr.lower()] = {
                "reason": _undelivered_reason(body),
                "notified_at": m.get("date"),
                "gmail_id": m.get("id"),
                "subject": m.get("subject")}
    return out


def _undelivered_reason(body):
    """The stated reason, read from the notice. Never inferred."""
    m = re.search(r"(?is)why it wasn.t delivered\s*(.+?)(?:\n\s*\n|how to resend)",
                  body)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def _sent_body(m):
    """The text of a sent message, plain preferred, HTML stripped as a
    fallback. Returns None when neither is present — never "" , which would
    be stored as "an empty email was sent"."""
    body = m.get("body_plain") or m.get("bodyPlain")
    if not body:
        html = m.get("body_html") or m.get("bodyHtml") or m.get("body")
        if html:
            txt = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
            txt = re.sub(r"(?i)<br\s*/?>|</p>", "\n", txt)
            txt = re.sub(r"(?s)<[^>]+>", "", txt)
            body = _unescape(txt)
    body = (body or "").strip()
    return body or None


def find_sent(payload):
    """{reply_address: {sent_at, body, subject, gmail_id}} from a Sent read.

    READ-ONLY. A message in Sent is positive evidence that a human sent it.
    Its ABSENCE is not evidence of anything — the same rule the outcome
    tracker already runs on — so this only ever reports what it found.

    THE BODY IS CARRIED OUT WITH THE TIMESTAMP, deliberately. Outcomes are
    attributed to the text a journalist actually received, and that text is
    not the pipeline's draft: the first real send was hand-edited before it
    went. Reading the address and date but leaving the body behind would make
    every later outcome measure the wrong artifact.
    """
    out = {}
    for m in (payload or {}).get("results") or []:
        hdr = ((m.get("raw") or {}).get("payload") or {}).get("headers") or {}
        to = " ".join(str(v) for v in (hdr.get("To"), m.get("to"),
                                       hdr.get("Delivered-To")) if v)
        for addr in re.findall(r"reply\+[0-9a-f-]{8,}@%s" % re.escape(REPLY_HOST),
                               to, re.I):
            when = m.get("date") or hdr.get("Date")
            key = addr.lower()
            prev = out.get(key)
            # Earliest wins: the first send is the pitch. A later message to
            # the same address is a follow-up, not the thing being measured.
            if prev and not (when and prev.get("sent_at")
                             and when < prev["sent_at"]):
                continue
            out[key] = {"sent_at": when,
                        "body": _sent_body(m),
                        "subject": m.get("subject") or hdr.get("Subject"),
                        "gmail_id": m.get("id")}
    return out
