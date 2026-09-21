#!/usr/bin/env python3
"""
The loop: sent -> published -> linked.

Everything before this round measured proxies. `answerable` was a guess about
what a journalist might use; this measures what they actually did.

THREE RULES SHAPE THIS FILE.

1. THE PIPELINE NEVER SENDS. A human sends, then records it here. There is no
   transport in this module and a test asserts there is none.

2. SILENCE IS NOT A RESULT. A pitch nobody answered is `pending`, forever if
   need be. It never becomes `not_published`, because "we did not see it" and
   "it did not happen" are different facts and this project has already paid
   for confusing them twice — an empty mailbox read as a quiet niche, a
   missing push log read as a lost run.

3. A LINK IS READ OFF THE PAGE. Not inferred from the pitch being used, not
   assumed from a mention of the brand. The anchor must be in the HTML, and
   its `rel` is recorded as found — a nofollow is a real outcome and is worth
   knowing about, not something to round up.
"""

import difflib
import html as _html
import json, os, re, ssl, urllib.error, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TARGET_HOST = "inhousewellness.com"
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
UA = "InHouseWellness-LinkCheck/1.0 (+https://inhousewellness.com)"

STATUSES = ("pending", "published")


class OutcomeError(Exception):
    pass


# --------------------------------------------------------------------------
# the record
# --------------------------------------------------------------------------
def load(path):
    if not os.path.exists(path):
        return {"_comment": "Sends recorded by a human. The pipeline never "
                            "writes a send here; it only records one that "
                            "already happened.",
                "sends": []}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(doc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def _norm_body(text):
    """Collapse whitespace for COMPARISON only. Never for storage.

    A reflowed paragraph and a rewritten one are different facts, and a mail
    client rewraps lines on its own. Comparing raw text would report every
    send as diverged and the signal would be worthless within a week.
    """
    return re.sub(r"\s+", " ", (text or "")).strip()


def body_divergence(drafted, sent):
    """How the body that WENT OUT differs from the one the pipeline queued.

    Outcomes belong to what was sent, not to what was drafted — the human
    edits before pressing send, and attributing a published link to the
    pipeline's untouched draft would credit the wrong text. Both bodies are
    kept; this only describes the gap between them.

    `diverged` is None, never False, when there is no queued draft to compare
    against. "We did not find a draft" and "the draft matched" are different
    facts, and this project has already paid for merging that pair twice.
    """
    if not sent:
        raise OutcomeError("no sent body to compare — record what went out, "
                           "or record nothing")
    if not drafted:
        return {"diverged": None, "similarity": None, "diff": None,
                "drafted_chars": None, "sent_chars": len(sent),
                "note": "no queued draft on file for this item; the sent "
                        "body is stored on its own rather than compared "
                        "against nothing"}
    a, b = _norm_body(drafted), _norm_body(sent)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    diff = "\n".join(difflib.unified_diff(
        (drafted or "").splitlines(), (sent or "").splitlines(),
        fromfile="queued-draft", tofile="sent", lineterm=""))
    return {"diverged": a != b, "similarity": round(ratio, 4),
            "diff": diff if a != b else None,
            "drafted_chars": len(drafted), "sent_chars": len(sent)}


def record_send(doc, key, sent_from, sent_at=None, outlet=None, regime=None,
                platform=None, note=None, sent_body=None, drafted_body=None):
    """Mark an item sent. Idempotent on key: re-recording updates, never
    duplicates, because a double entry would inflate the denominator.

    `sent_body` is the text READ BACK FROM SENT MAIL — what the journalist
    actually received. It is the artifact outcomes attribute to. `drafted_body`
    is what the pipeline had queued, kept alongside it so the gap between the
    two can be measured over time; that gap is the best available signal on
    how the drafter should change.
    """
    if not key or not sent_from:
        raise OutcomeError("a send needs both an item key and the address it "
                           "was sent from")
    if "@" not in sent_from and not sent_from.startswith("http"):
        raise OutcomeError("sent_from %r is neither an address nor a platform "
                           "URL. Record where it actually went." % sent_from)
    explicit_time = sent_at is not None
    sent_at = sent_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        datetime.fromisoformat(sent_at)
    except ValueError:
        raise OutcomeError("sent_at %r is not an ISO timestamp" % sent_at)
    for s in doc["sends"]:
        if s["key"] == key:
            # THE ORIGINAL SEND TIME SURVIVES A RE-RECORD. Correcting a typo in
            # the address must not silently restamp the send to now — that
            # would quietly corrupt time-to-publication, which is the one
            # duration this file exists to measure. Only an explicit --at
            # moves it.
            s["sent_from"] = sent_from
            if explicit_time:
                s["sent_at"] = sent_at
            if note:
                s["note"] = note
            if sent_body:
                _attach_bodies(s, sent_body, drafted_body)
            return s, False
    rec = {"key": key, "outlet": outlet, "platform": platform, "regime": regime,
           "sent_from": sent_from, "sent_at": sent_at,
           "status": "pending", "published_url": None, "published_at": None,
           "linked": None, "rel": None, "last_checked": None, "note": note,
           "sent_body": None, "drafted_body": None, "divergence": None,
           # TRI-STATE, and None is the honest default. A platform that sends
           # no delivery receipt cannot prove arrival, so `delivered` is only
           # ever set False by a non-delivery notice actually read. It is
           # never set True by the absence of one.
           "delivered": None, "delivery": None}
    if sent_body:
        _attach_bodies(rec, sent_body, drafted_body)
    doc["sends"].append(rec)
    return rec, True


def _attach_bodies(rec, sent_body, drafted_body):
    """Store what went out, what was queued, and the gap. Append-only on the
    sent body.

    A sent message does not change. So a second read that returns DIFFERENT
    text is not a correction to apply — it means the wrong message was
    matched, or the read was truncated. Overwriting would destroy the only
    copy of what was actually sent, so the first capture stands and the
    conflict is recorded next to it for a human to look at.
    """
    prior = rec.get("sent_body")
    if prior and _norm_body(prior) != _norm_body(sent_body):
        rec.setdefault("sent_body_conflicts", []).append(
            {"seen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "body": sent_body})
        return rec
    rec["sent_body"] = sent_body
    if drafted_body and not rec.get("drafted_body"):
        rec["drafted_body"] = drafted_body
    rec["divergence"] = body_divergence(rec.get("drafted_body"), sent_body)
    return rec


def record_delivery_failure(doc, key, reason=None, notified_at=None,
                            source_id=None):
    """A notice said this pitch never reached the journalist.

    This is the difference between "nobody used it" and "nobody saw it", and
    counting the second as the first would quietly poison every hit-rate this
    file computes — the pitch would sit in the denominator as a fair try that
    failed, when it was never delivered at all.

    Only a notice sets this. There is no path that infers non-delivery from
    silence, and none that infers delivery from the absence of a notice.
    """
    for s in doc["sends"]:
        if s["key"] == key:
            s["delivered"] = False
            s["delivery"] = {"reason": reason, "notified_at": notified_at,
                             "source_id": source_id}
            return s
    raise OutcomeError(
        "no send recorded for %r, so there is nothing to mark undelivered. "
        "Record the send first — a bounce without a send is a read error, "
        "not a result." % key)


def record_published_url(doc, key, url, published_at=None):
    """A human saw it go live. The LINK is still verified from the page."""
    for s in doc["sends"]:
        if s["key"] == key:
            if not url.startswith("http"):
                raise OutcomeError("published_url must be a URL: %r" % url)
            s["published_url"] = url
            s["published_at"] = published_at
            s["status"] = "published"
            return s
    raise OutcomeError("no send recorded for key %r. Record the send before "
                       "its outcome." % key)


# --------------------------------------------------------------------------
# reading the link off the page
# --------------------------------------------------------------------------
_ANCHOR_RE = re.compile(r"<a\b([^>]*)>", re.I | re.S)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
_REL_RE = re.compile(r"""rel\s*=\s*["']([^"']*)["']""", re.I)


def find_links(page_html, host=TARGET_HOST):
    """Every anchor pointing at `host`, with its rel exactly as written.

    Parsed from the markup rather than a text search for the domain, because
    a brand name in body copy is not a link and counting it as one would be
    the same wishful arithmetic the audit found in the legacy backlink data.
    """
    out = []
    for attrs in _ANCHOR_RE.findall(page_html or ""):
        m = _HREF_RE.search(attrs)
        if not m:
            continue
        href = _html.unescape(m.group(1)).strip()
        if host not in href.lower():
            continue
        rel = _REL_RE.search(attrs)
        rel_val = " ".join((rel.group(1) if rel else "").lower().split())
        out.append({"href": href, "rel": rel_val or None,
                    "nofollow": "nofollow" in rel_val,
                    "sponsored": "sponsored" in rel_val,
                    "ugc": "ugc" in rel_val})
    return out


def fetch(url, timeout=25):
    """Fetch a page. Returns (status, html). Never raises on HTTP status —
    the caller needs to tell 404 from 429 from a network failure, and a 429 is
    backoff rather than a dead page."""
    ctx = ssl.create_default_context(
        cafile=CA_BUNDLE if os.path.exists(CA_BUNDLE) else None)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:                       # noqa: BLE001
        return None, "NETWORK-ERROR: %s" % e


def check_one(rec, fetcher=fetch, now=None):
    """Verify one published URL. Mutates and returns the record.

    A fetch failure does NOT clear a previously found link and does NOT mark
    anything unpublished. It records that the check could not be made.
    """
    now = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    if not rec.get("published_url"):
        rec["last_checked"] = now
        rec["check_note"] = ("no published URL recorded — stays pending. "
                             "Silence is not evidence of non-publication.")
        return rec
    status, body = fetcher(rec["published_url"])
    rec["last_checked"] = now
    rec["http_status"] = status
    if status != 200:
        # A FAILED FETCH IS NOT AN ABSENT LINK. `linked` is left exactly as it
        # was — never set to False — because "we could not look" and "it is not
        # there" are different facts, and recording the first as the second
        # would mark real earned links as missing. Same rule as silence not
        # meaning unpublished, one level down.
        blocked = status is None and "NETWORK-ERROR" in (body or "")
        rec["check_source"] = "page-fetch-failed"
        rec["check_note"] = (
            "fetch could not be made (%s); link state UNCHANGED, not set to "
            "false. %s" % (
                "network/proxy blocked" if blocked else "HTTP %s" % status,
                "This environment's network policy denies CONNECT to "
                "publisher domains, so page-level checking must run elsewhere "
                "— see the backlink-audit cross-check."
                if blocked else
                "429 is backoff, not a dead page." if status == 429 else
                "Re-check next cycle."))
        return rec
    links = find_links(body)
    rec["linked"] = bool(links)
    rec["rel"] = links[0]["rel"] if links else None
    rec["link_hrefs"] = [l["href"] for l in links]
    rec["follow"] = bool(links) and not any(l["nofollow"] for l in links)
    rec["check_source"] = "page-fetch"
    rec["check_note"] = ("%d link(s) to %s found in the page markup"
                         % (len(links), TARGET_HOST) if links else
                         "page fetched, no link to %s in the markup" % TARGET_HOST)
    return rec


def check_via_backlink_audit(rec, audit_rows):
    """Second route to the same fact, and the one that works here.

    `00_audit` already pulls every referring domain for inhousewellness.com,
    including the `rel` attribute, through an MCP tool rather than raw HTTP.
    Where this environment cannot fetch a publisher page, the audit can still
    say whether the link exists — so the loop is not blocked on a network
    policy, it just closes on a slower cadence.

    Only ever UPGRADES a record: it can establish a link, never erase one.
    """
    url = (rec.get("published_url") or "").lower()
    if not url:
        return rec
    for row in audit_rows:
        frm = (row.get("url_from") or "").lower()
        if not frm:
            continue
        if frm.rstrip("/") == url.rstrip("/"):
            rec["linked"] = True
            rec["rel"] = row.get("rel_attr")
            rec["follow"] = (row.get("rel_attr") or "").lower() != "nofollow"
            rec["link_hrefs"] = [row.get("url_to")]
            rec["check_source"] = "backlink-audit"
            rec["check_note"] = ("link confirmed by the backlink audit "
                                 "(%s), rel=%s" % (row.get("run_date"),
                                                   row.get("rel_attr")))
            return rec
    return rec


def hours_to_publication(rec):
    if not (rec.get("sent_at") and rec.get("published_at")):
        return None
    try:
        a = datetime.fromisoformat(rec["sent_at"])
        b = datetime.fromisoformat(rec["published_at"])
    except ValueError:
        return None
    return (b - a).total_seconds() / 3600.0


def summarise(doc):
    """Counts that never treat `pending` as a failure."""
    sends = doc.get("sends") or []
    # A pitch that never reached the journalist is not a pitch that failed.
    # Leaving it in the denominator would report the drafter as performing
    # worse than it did, on a delivery problem it cannot influence.
    undelivered = [s for s in sends if s.get("delivered") is False]
    out = {"sent": len(sends), "undelivered": len(undelivered),
           "delivered_or_unknown": len(sends) - len(undelivered),
           "pending": 0, "published": 0, "linked": 0,
           "follow": 0, "nofollow": 0, "per_regime": {}, "per_platform": {},
           "times": []}
    for s in sends:
        for dim, key in (("per_regime", s.get("regime") or "unknown"),
                         ("per_platform", s.get("platform") or "unknown")):
            d = out[dim].setdefault(key, {"sent": 0, "published": 0,
                                          "linked": 0, "pending": 0})
            d["sent"] += 1
        pub = s.get("status") == "published"
        out["published" if pub else "pending"] += 1
        for dim, key in (("per_regime", s.get("regime") or "unknown"),
                         ("per_platform", s.get("platform") or "unknown")):
            out[dim][key]["published" if pub else "pending"] += 1
        if s.get("linked"):
            out["linked"] += 1
            for dim, key in (("per_regime", s.get("regime") or "unknown"),
                             ("per_platform", s.get("platform") or "unknown")):
                out[dim][key]["linked"] += 1
            if s.get("follow"):
                out["follow"] += 1
            else:
                out["nofollow"] += 1
        h = hours_to_publication(s)
        if h is not None:
            out["times"].append(h)
    return out
