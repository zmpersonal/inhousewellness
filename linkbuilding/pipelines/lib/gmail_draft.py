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
    """Gmail search for replies already sent to HARO reply addresses."""
    return "in:sent to:reply+*@%s" % REPLY_HOST


def find_sent(payload):
    """{reply_address: sent_at} from a Sent-mail read. Read-only.

    A message in Sent is positive evidence that a human sent it. Its ABSENCE
    is not evidence of anything — the same rule the outcome tracker already
    runs on — so this only ever reports what it found.
    """
    out = {}
    for m in (payload or {}).get("results") or []:
        hdr = ((m.get("raw") or {}).get("payload") or {}).get("headers") or {}
        to = " ".join(str(v) for v in (hdr.get("To"), m.get("to"),
                                       hdr.get("Delivered-To")) if v)
        for addr in re.findall(r"reply\+[0-9a-f-]{8,}@%s" % re.escape(REPLY_HOST),
                               to, re.I):
            when = m.get("date") or hdr.get("Date")
            prev = out.get(addr.lower())
            if not prev or (when and when < prev):
                out[addr.lower()] = when
    return out
