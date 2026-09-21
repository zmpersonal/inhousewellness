#!/usr/bin/env python3
"""
01_source — ingest journalist requests, parse, filter against the claim bank,
report. It does NOT draft, pitch, or send, and it never touches the mailbox.

WHY FILTER-ONLY. The claim bank is `awaiting_review` and the measured
relevance rate is zero of 23 over the first 36 hours. A drafter built against
that would fire about once a fortnight, using claims no clinician has signed.
So this round stops at the worklist.

THE SIX INHERITED RULES (data/samples/README.md) ARE ASSERTED, NOT ASSUMED.
Each earned its place from the 2026-09-14 run that reported an empty inbox
which was really a wrong-mailbox read:

  1. connection_id 029715c5 pinned on every Gmail call. The Zapier default is
     support@, all five connections are still listed, and omitting the id
     reads the wrong mailbox.
  2. Delivered-To asserted on the RESPONSE. Checking the request you sent
     proves nothing.
  3. Zero rows where rows are expected RAISES. An empty result from the wrong
     mailbox is a success, not an error, and looks exactly like an empty inbox.
  4. The bare `Media` parent label is in scope. Media/Featured exists but is
     empty; Featured's mail landed on the parent.
  5. Routing is by SENDER, never subject. SOS subjects vary between sends.
  6. IMPORTANT: is excluded from SOS field extraction — it appears twice per
     digest as a house notice.

The agent relays the Gmail payload; MCP exists only inside an agent session.
This script does all parsing, filtering, dedup and reporting. No model call
decides a bucket.

Usage
  01_source.py probe --gmail <raw> --slack <raw>   # FIRST. both connectors.
  01_source.py run --payload <gmail.json> --connection-id <id> [--date D]
  ... commit, push, then ...
  01_source.py verify-push           # the run is not done until this passes
  01_source.py rescore               # re-classify stored rows in place
  01_source.py test-samples          # parsers against data/samples/
  01_source.py self-test             # all six rules + filter + idempotency

Exit codes: 0 ok · 3 stop condition · 4 run failed · 5 push not verified
"""

import argparse, json, os, re, sqlite3, subprocess, sys
from collections import Counter, defaultdict
from datetime import date as _date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib", "parsers"))
import sos as sos_parser            # noqa: E402
import qwoted as qwoted_parser      # noqa: E402
import haro as haro_parser          # noqa: E402
import connectively as cx_parser    # noqa: E402
sys.path.insert(0, os.path.join(HERE, "lib"))
import relay                        # noqa: E402
import claims as claims_lib        # noqa: E402
import drafter                     # noqa: E402
import outcomes                    # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SAMPLES = os.path.join(DATA, "samples")
DB_PATH = os.path.join(DATA, "links.db")
SCHEMA = os.path.join(DATA, "schema.sql")
REPORT = os.path.join(ROOT, "reports", "source-digest.md")
TREND = os.path.join(ROOT, "reports", "source-trend.md")
ALERT = os.path.join(ROOT, "reports", "ALERT-answerable.md")
# Derived rows, committed. links.db is a gitignored build artifact and a
# Routine-fired session has no scratchpad, so without this the 14-day trend
# counter silently resets to zero on any cold start — which would look exactly
# like "the pipeline found nothing", the one thing this project is measuring.
STATE = os.path.join(DATA, "source-state.json")
FAIL_ALERT = os.path.join(ROOT, "reports", "ALERT-failure.md")

# --- Round 7: nothing about this run may fail quietly ---------------------
# Evidence that both connectors answered a real call THIS session, written by
# `probe` from raw tool results. A cloud Routine uses a separate OAuth
# registration from an interactive session, so a connector that works in chat
# can be stale for the Routine and return an empty set rather than an error.
PROBE = os.path.join(DATA, "connector-probe.json")
PROBE_MAX_AGE_S = 1800
# Append-only record of which runs were confirmed present ON THE REMOTE.
# The trend counter is computed from this, not from "git push returned 0".
PUSH_LOG = os.path.join(DATA, "push-log.json")
# Source keys already alerted on, so a standing item cannot re-alert daily.
ALERTED = os.path.join(DATA, "alerted-items.json")
HEARTBEAT = os.path.join(ROOT, "reports", "heartbeat.slack.txt")
GIT_BRANCH = "claude/sleepy-edison-83ovwt"
# Path of STATE as git sees it, i.e. from the repository root, not from ROOT.
STATE_IN_REPO = "linkbuilding/data/source-state.json"

# Rule 1
EXPECTED_CONNECTION_ID = "029715c5-3a50-8935-b200-6e6eba55ac62"
# Rule 2 — THE recipient set, defined once. Three addresses feed this
# pipeline; the recipient identifies which expert a query is for and is
# persisted on every item. Delivery to anything else is still a connection
# signal and still raises.
EXPECTED_RECIPIENTS = frozenset({
    "media@inhousewellness.com",
    "timur@inhousewellness.com",
    "tripler@inhousewellness.com",
})
EXPERTS_PATH_REL = "data/experts.json"
# Rule 4
EXPECTED_LABELS = ("Media", "Media/Qwoted", "Media/SourceOfSources",
                   "Media/HARO", "Media/Featured", "Media/Connectively")
# Round 8. The first HARO QUERY digest, not the first run and not the signup.
# All four proven links came through HARO, so this is the date the 14-day
# window actually starts; SOS and Qwoted days before it measured two channels
# that have never produced a link.
HARO_CLOCK_START = "2026-09-15"


class SourceError(Exception):
    pass


# --------------------------------------------------------------------------
# Rules 1-4: ingest-side assertions
# --------------------------------------------------------------------------
def assert_connection(connection_id):
    """Rule 1."""
    if connection_id != EXPECTED_CONNECTION_ID:
        raise SourceError(
            "Rule 1: connection_id is %r, expected %r (julian@inhousewellness.com). "
            "The Zapier default is support@inhousewellness.com and returns an "
            "empty result set rather than an error."
            % (connection_id, EXPECTED_CONNECTION_ID))
    return True


def delivered_to(msg):
    return ((msg.get("raw") or {}).get("payload", {})
            .get("headers", {}).get("Delivered-To", ""))


def assert_delivered_to(messages):
    """Rule 2 — assert on the response, not the request.

    Membership in EXPECTED_RECIPIENTS, not equality with one address. Anything
    outside the set means the payload came from a mailbox this pipeline does
    not own, which is a connection fault, not data.
    """
    if not messages:
        return True
    wrong = [(m.get("id"), delivered_to(m) or "<absent>")
             for m in messages if delivered_to(m) not in EXPECTED_RECIPIENTS]
    if wrong:
        raise SourceError(
            "Rule 2: %d message(s) delivered outside the expected recipient "
            "set %s — the payload came from the wrong mailbox: %s"
            % (len(wrong), sorted(EXPECTED_RECIPIENTS), wrong[:5]))
    return True


def load_experts():
    with open(os.path.join(DATA, "experts.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    return {e["id"]: e for e in doc["experts"]}


def assert_non_empty(messages, query_desc):
    """Rule 3 — zero where rows are expected is a connection signal."""
    if not messages:
        raise SourceError(
            "Rule 3: zero rows for %r. This mailbox is known to contain "
            "Media/* mail, so zero means the connection or query is wrong, "
            "NOT that the inbox is empty. Re-check connection_id before "
            "reporting nothing to ingest." % query_desc)
    return True


def assert_label_scope(labels_queried):
    """Rule 4 — the bare Media parent must be in scope."""
    if "Media" not in labels_queried:
        raise SourceError(
            "Rule 4: bare 'Media' label missing from query scope %r. "
            "Media/Featured exists but is empty; Featured's mail, the SOS "
            "welcome and the Qwoted confirmation all landed on the parent."
            % (labels_queried,))
    return True


# --------------------------------------------------------------------------
# Rule 5: routing by sender
# --------------------------------------------------------------------------
def route(msg):
    """Rule 5 — sender only. This function never reads msg['subject']."""
    frm = ((msg.get("from") or {}).get("email") or "").lower()
    if sos_parser.is_sos(frm):
        return "sos"
    if qwoted_parser.is_qwoted(frm):
        return "qwoted"
    if haro_parser.is_haro(frm):
        return "haro"
    if cx_parser.is_connectively(frm):
        return "connectively"
    # featured.com has never sent a digest — only auth mail — but the route is
    # kept because Featured and Connectively are the same product on two
    # domains. Deleting it would mean a Featured-domain digest lands nowhere
    # and is counted as nothing, and "nothing arrived" reads identically to
    # "we stopped looking".
    if frm.endswith("featured.com"):
        return "featured"
    return "unknown"


# --------------------------------------------------------------------------
# Filter against the claim bank
# --------------------------------------------------------------------------
# Terms that name the modality the bank actually covers. Presence of one of
# these is what separates "we have an approved claim" from "this is wellness-
# shaped". Derived from claims.json topics and claim text, not invented.
# ==========================================================================
# Round 10 — the clinical vocabulary is DERIVED FROM the bank, not declared
# ==========================================================================
# The two sets below are CANDIDATES, not the match vocabulary. Every one is
# reconciled against claims.json at load time and a term with no backing claim
# is dropped before it can match anything.
#
# Round 9 caught the pipeline printing "modality ['infrared'] named; the claim
# bank covers this directly" for a term in zero of 30 claims. Two lists
# maintained by different hands will always drift; the only fix that holds is
# for one to be computed from the other.
CANDIDATE_MODALITY_TERMS = {
    "sauna", "saunas", "infrared", "steam room", "heat therapy", "heat exposure",
    "hyperthermia", "cold plunge", "cold-plunge", "cold water immersion",
    "cold-water immersion", "ice bath", "ice baths", "cryotherapy",
    "contrast therapy", "cold exposure", "thermal", "heat acclimation",
}
# Outcomes the bank speaks to, but only alongside a modality term.
CANDIDATE_OUTCOME_TERMS = {
    "cardiovascular", "blood pressure", "heart", "mortality", "longevity",
    "sleep", "insomnia", "recovery", "muscle soreness", "hypertrophy",
    "inflammation", "metabolic", "brown fat", "dementia", "cognition",
    "mood", "depression", "hydration", "dehydration", "pregnancy",
}
# Wellness-adjacent vocabulary with no approved claim behind it. A hit here
# WITHOUT a modality term is marginal at best.
ADJACENT_TERMS = {
    "wellness", "biohacking", "recovery routine", "self-care", "mindfulness",
    "fitness", "home gym", "spa", "hot tub", "longevity",
}


def _backed_vocabulary():
    """(modality, outcome, orphans, table) — resolved against the live bank.

    Every surviving term carries the claim ids that back it, so a match can
    say WHICH claim it rests on instead of asserting that one exists.
    """
    doc = claims_lib.load(os.path.join(DATA, "claims.json"))
    mod = claims_lib.expand_terms(CANDIDATE_MODALITY_TERMS, doc)
    out = claims_lib.expand_terms(CANDIDATE_OUTCOME_TERMS, doc)
    _t, orph = claims_lib.reconcile(
        CANDIDATE_MODALITY_TERMS | CANDIDATE_OUTCOME_TERMS, doc)
    return mod, out, orph, _t


MODALITY_BACKED, OUTCOME_BACKED, ORPHANED_TERMS, RECONCILIATION = _backed_vocabulary()
# What actually matches. Orphans are absent by construction, so an item whose
# only clinical vocabulary is orphaned falls through to `rejected` — it cannot
# reach `answerable` by a route that no claim supports.
MODALITY_TERMS = set(MODALITY_BACKED)
OUTCOME_TERMS = set(OUTCOME_BACKED)
# Attribution is checked against the CANDIDATE set on purpose: a term dropped
# for having no claim is still clinical vocabulary, and must still never be
# attributed to the health coach.
CLINICAL_VOCABULARY = CANDIDATE_MODALITY_TERMS | CANDIDATE_OUTCOME_TERMS


def backing_for(terms):
    """Claim ids behind a set of matched terms, for the reason string."""
    ids = []
    for t in terms:
        for cid in (MODALITY_BACKED.get(t) or OUTCOME_BACKED.get(t)
                    or {}).get("claims", []):
            if cid not in ids:
                ids.append(cid)
    return ids


def _hay(item):
    """Subject matter ONLY.

    `category` and `outlet` are deliberately excluded. They are taxonomy and
    brand names, not what the journalist is asking about: the SOS category
    "Lifestyle and Fitness" was matching the term `fitness` and pushing
    unrelated gift-guide requests into `marginal`. A filter that reads the
    folder name instead of the question is measuring the wrong thing.
    """
    parts = [item.get("summary"), item.get("headline"), item.get("query")]
    return " ".join(str(p) for p in parts if p).lower()


def _hits(terms, hay):
    """Whole-word matching. Plain substring search put `spa` inside "Spark
    Kids" and turned a children's card deck into a wellness lead."""
    out = []
    for t in terms:
        if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(t), hay):
            out.append(t)
    return sorted(out)


# Tripler's provisional territory. Experience-based, no citations, and NOT a
# claims.json equivalent — see data/experts.json for why the regimes are kept
# apart. Nothing is pitched from these; they exist to measure whether a
# second expert changes the relevance rate at all.
# ANCHORS are specific enough to identify a query as genuinely hers. SUPPORT
# terms are words that appear in any article about any workplace.
#
# The first pass used the support words as anchors and produced four
# "answerable" items including a Pet Age story about the holiday toll on pet
# industry EMPLOYEES and a Toronto podcast wanting retail and tech LEADERS in
# person. Neither is a business-operations query for a health coach. This is
# the same single-generic-word failure that put "spa" inside "Spark Kids" in
# Round 4, and it is fixed the same way: require a specific anchor, and let
# the generic words support rather than decide.
TRIPLER_ANCHOR = {
    "business operations", "org design", "organizational design",
    "team design", "hiring and retention", "employee retention",
    "founder", "founders", "solopreneur", "solopreneurs",
    "small business", "small businesses", "scaling a business",
    "health coach", "health coaching", "behaviour change", "behavior change",
    "habit formation", "workplace wellbeing", "workplace well-being",
    "women in business", "organizational behavior", "organisational behaviour",
}
TRIPLER_SUPPORT = {
    "operations", "leadership", "management", "workplace", "employee",
    "employees", "productivity", "burnout", "hiring", "retention",
    "entrepreneur", "scaling", "habit", "habits", "wellbeing", "well-being",
    "accountability", "lifestyle change", "functional health",
}


def classify(item, claim_topics, experts=None):
    """Three buckets, per expert. Never tuned to produce hits — zero
    answerable is valid.

    Returns (bucket, matched_terms, reason, matched_expert). `matched_expert`
    is None on rejection. An item answerable by neither expert stays rejected.
    """
    hay = _hay(item)
    mods = _hits(MODALITY_TERMS, hay)
    outs = _hits(OUTCOME_TERMS, hay)
    adj = _hits(ADJACENT_TERMS, hay)
    t_anchor = _hits(TRIPLER_ANCHOR, hay)
    t_support = _hits(TRIPLER_SUPPORT, hay)

    # --- clinical first: only the physician may answer from the claim bank
    if mods and outs:
        return ("answerable", mods + outs,
                "modality %s + outcome %s both present; backed by %s"
                % (mods, outs, backing_for(mods + outs)), "alptunaer")
    if mods:
        return ("answerable", mods,
                "modality %s named; backed by %s"
                % (mods, backing_for(mods)), "alptunaer")

    # --- Tripler: her own territory, experience-based, no citation needed
    if t_anchor:
        return ("answerable", t_anchor + t_support,
                "business/coaching anchor %s present; experience-based, no "
                "citation required (PROVISIONAL topic set, approved: false)"
                % t_anchor, "tripler")
    if t_support and not (adj or outs):
        return ("marginal", t_support,
                "generic workplace vocabulary %s with no specific business or "
                "coaching anchor — the words appear, the query is not hers"
                % t_support, "tripler")

    # --- wellness-shaped but unanchored
    if adj or outs:
        return ("marginal", adj + outs + t_support,
                "wellness-adjacent (%s) but no sauna/cold/heat modality named; "
                "answering would stretch a claim past its do_not_say"
                % (adj + outs), "alptunaer")
    cat = item.get("category") or "uncategorised"
    return ("rejected", [], "no vocabulary for either expert (category: %s)" % cat,
            None)


def assert_clinical_attribution(rows):
    """HARD RULE. Anything matched on claim-bank vocabulary belongs to the
    physician and to nobody else.

    A certified health coach quoted on cardiovascular mortality literature is
    a scope-of-practice failure and a credibility failure at once, and
    'functional health' is exactly the boundary where that mistake gets made.
    This raises rather than warns.
    """
    clinical = CLINICAL_VOCABULARY | MODALITY_TERMS | OUTCOME_TERMS
    bad = []
    for r in rows:
        terms = set(r.get("matched_terms") or [])
        if terms & clinical and r.get("matched_expert") not in (None, "alptunaer"):
            bad.append((r.get("source_key"), r.get("matched_expert"),
                        sorted(terms & clinical)))
    if bad:
        raise SourceError(
            "CLINICAL ATTRIBUTION VIOLATED — claim-bank vocabulary routed to a "
            "non-physician: %s\nEvery claim in claims.json is attributable to "
            "Dr. Alptunaer ONLY." % bad)
    return True


# --------------------------------------------------------------------------
# Attribution guard — the BYLINE, not the topic
# --------------------------------------------------------------------------
# His stated condition, precisely: his name must never appear attached to a
# specialty he does not hold.
#
# THIS IS NOT A TOPIC FILTER, AND CONFUSING THE TWO WOULD THROW AWAY MOST OF
# WHAT HE CAN DO. He is willing to speak outside his clinical practice. A
# pitch about dermatology is fine. "Dr. Alptunaer, a dermatologist" is not,
# and neither is anything a journalist could reasonably compress into that —
# "skin expert", "sleep specialist", "specialist in X" for any X.
#
# So the guard reads the DESCRIPTION around his name and never the subject
# matter of the query.
CREDENTIAL_LINE = "Timur Alptunaer, MD, RN, EMT-T, FACEP"
# The one expansion allowed where a role descriptor is genuinely needed.
PERMITTED_ROLE_DESCRIPTOR = "emergency medicine physician"

# Surface forms of his name that a descriptor could attach to.
_NAME_RE = re.compile(r"\b(?:dr\.?\s+)?(?:timur\s+)?alptunaer\b", re.I)
# How far a descriptor can sit from the name and still read as describing him.
_WINDOW = 140

# Descriptor SHAPES, not a list of specialties. A blocklist of specialty nouns
# would be endless and would miss the next one; these patterns catch the shape
# of a credential claim whatever noun fills it.
_DESCRIPTOR_PATTERNS = [
    (re.compile(r"\b[a-z]+(?:ologist|ologists|iatrist|iatrists|iatrician|"
                r"iatricians|ontist|ontists|urgeon|urgeons)\b", re.I),
     "specialty noun"),
    (re.compile(r"\bboard[-\s]certified\s+[a-z]+", re.I), "board-certified X"),
    (re.compile(r"\bspecial(?:ist|ising|izing|ises|izes)\s+in\s+[a-z]+", re.I),
     "specialist in X"),
    (re.compile(r"\b[a-z]+\s+special(?:ist|ists)\b", re.I), "X specialist"),
    (re.compile(r"\b[a-z]+\s+expert\b", re.I), "X expert"),
    (re.compile(r"\bexpert\s+in\s+[a-z]+", re.I), "expert in X"),
    (re.compile(r"\b[a-z]+\s+consultant\b", re.I), "X consultant"),
    (re.compile(r"\bprofessor\s+of\s+[a-z]+", re.I), "professor of X"),
    (re.compile(r"\b(?:chief|head|director)\s+of\s+[a-z]+", re.I), "head of X"),
    (re.compile(r"\b[a-z]+\s+doctor\b", re.I), "X doctor"),
    (re.compile(r"\b[a-z]+\s+physician\b", re.I), "X physician"),
]
# What may sit beside his name. Anything else matching a descriptor shape is a
# misrepresentation, including an accurate-sounding one.
_ALLOWED_DESCRIPTORS = {
    PERMITTED_ROLE_DESCRIPTOR,
    "emergency medicine physicians",
    "emergency physician",              # the same role, no other specialty
    "emergency physicians",
}


class AttributionError(SourceError):
    pass


def _windows_around_name(text):
    for m in _NAME_RE.finditer(text or ""):
        yield (text[max(0, m.start() - _WINDOW): m.end() + _WINDOW], m.start())


def assert_attribution_safe(text, where=""):
    """RAISE if any descriptor other than the permitted role sits near his name.

    Runs on GENERATED text — pitch bodies, subject lines, bios. It does not
    look at the journalist's query: what they are writing about is their
    business, how he is labelled is his.
    """
    if not text:
        return True
    low = text.lower()
    # The credential line itself is exempt: it is the one string that may
    # accompany him, and it contains commas and post-nominals that would
    # otherwise trip nothing but are worth stating explicitly.
    scrubbed = low.replace(CREDENTIAL_LINE.lower(), " ")
    # Remove what IS permitted before looking for what is not. Testing each
    # match against an allow-set fails on overlap: "emergency medicine
    # physician" contains the bigram "medicine physician", which is not itself
    # an allowed phrase, so the permitted descriptor tripped its own guard.
    for allowed in sorted(_ALLOWED_DESCRIPTORS, key=len, reverse=True):
        scrubbed = scrubbed.replace(allowed, " ")
    bad = []
    for window, _pos in _windows_around_name(scrubbed):
        for pattern, shape in _DESCRIPTOR_PATTERNS:
            for hit in pattern.finditer(window):
                phrase = " ".join(hit.group(0).split())
                bad.append((shape, phrase))
    if bad:
        raise AttributionError(
            "ATTRIBUTION VIOLATION%s — a descriptor other than %r appears beside "
            "his name: %s\n\nHis condition is that his name never appear attached "
            "to a specialty he does not hold. The SUBJECT is not the problem and "
            "must not be changed to fix this; the DESCRIPTION is. Use the "
            "credential line %r, or the role descriptor %r, and nothing else."
            % (" in %s" % where if where else "", PERMITTED_ROLE_DESCRIPTOR,
               sorted(set(bad)), CREDENTIAL_LINE, PERMITTED_ROLE_DESCRIPTOR))
    return True


def assert_pitchable(item):
    """An item cannot be marked pitchable without the credential line, EXACT.

    Exact string equality, deliberately: no normalisation, no reassembly from
    parts, no 'close enough'. There is no code path anywhere that builds this
    string from components, because a builder is a thing that can build it
    wrong — reorder the post-nominals, drop the RN, expand FACEP — and every
    one of those is a misrepresentation of a real person's credentials.
    """
    if not item.get("pitchable"):
        return True
    line = item.get("credential_line")
    if line != CREDENTIAL_LINE:
        raise AttributionError(
            "%s is marked pitchable with credential_line %r, which is not the "
            "verbatim string %r. It is stored as one literal in experts.json and "
            "is never reconstructed."
            % (item.get("source_key", "item"), line, CREDENTIAL_LINE))
    framing = item.get("framing")
    if framing not in ("published-evidence", "clinical-experience",
                       "verified-guideline"):
        raise AttributionError(
            "%s is pitchable but framing is %r. Claim bank -> published "
            "evidence he is INTERPRETING; experience set -> clinical or "
            "personal experience; general medical -> a guideline or source "
            "verified at draft time. All three carry the same credential line."
            % (item.get("source_key"), framing))
    # Round 13. A verified-at-draft draft rests on citations retrieved by the
    # machine minutes earlier, not on anything he has signed. It may be
    # written and queued; it may not be called ready to send until he has
    # looked at it. The flag is a precondition of pitchability, not a label
    # attached afterwards, because a label can be forgotten.
    if framing == "verified-guideline" and not item.get("requires_expert_review"):
        raise AttributionError(
            "%s is a verified-at-draft pitch and must carry "
            "requires_expert_review=True. Its citations were resolved by the "
            "machine at draft time; nothing in it has passed the expert."
            % item.get("source_key"))
    for field in ("pitch_text", "subject_line", "bio"):
        if item.get(field):
            assert_attribution_safe(item[field], where="%s.%s"
                                    % (item.get("source_key", "item"), field))
    return True


def mark_pitchable(item, framing, requires_expert_review=None):
    """The ONLY way an item becomes pitchable. Attaches the literal and checks."""
    item = dict(item)
    item["pitchable"] = True
    item["credential_line"] = CREDENTIAL_LINE
    item["framing"] = framing
    if requires_expert_review is None:
        requires_expert_review = framing == "verified-guideline"
    item["requires_expert_review"] = bool(requires_expert_review)
    assert_pitchable(item)
    return item


def load_claim_topics():
    p = os.path.join(DATA, "claims.json")
    with open(p, encoding="utf-8") as fh:
        bank = json.load(fh)
    status = bank.get("approval_status")
    # Stop condition: the round is defined against an unapproved bank.
    if status != "awaiting_review":
        raise SourceError(
            "claim bank approval_status is %r, not 'awaiting_review'. Round 4 "
            "was scoped against an unapproved bank; if it has been signed, the "
            "filter thresholds and the no-drafter decision both need revisiting."
            % status)
    return sorted({t for c in bank["claims"] for t in c["topics"]}), bank


# --------------------------------------------------------------------------
# deadlines
# --------------------------------------------------------------------------
# Offsets for the zone spellings actually observed in SOS and Qwoted mail.
# An unrecognised zone yields None rather than a guess: a deadline computed
# from an assumed offset would silently mis-rank urgency.
TZ_OFFSETS = {
    "pacific standard time": -8, "pacific daylight time": -7, "pst": -8, "pdt": -7,
    "mountain standard time": -7, "mountain daylight time": -6, "mst": -7, "mdt": -6,
    "central standard time": -6, "central daylight time": -5, "cst": -6, "cdt": -5,
    "eastern standard time": -5, "eastern daylight time": -4, "est": -5, "edt": -4,
    "utc": 0, "gmt": 0,
}
_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?", re.I)


def _offset(zone):
    z = (zone or "").strip().lower()
    return TZ_OFFSETS.get(z)


def parse_deadline(date_s, time_s, zone_s):
    """SOS shape: ('2026-09-16', '9:30 pm', 'Pacific Standard Time')."""
    if not date_s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_s.strip())
    if not m:
        return None
    off = _offset(zone_s)
    if off is None:
        return None
    hh, mm = 23, 59                      # no time given: end of the stated day
    t = _TIME_RE.search(time_s or "")
    if t:
        hh = int(t.group(1)) % 12
        mm = int(t.group(2) or 0)
        if t.group(3).lower() == "p":
            hh += 12
    y, mo, d = (int(x) for x in m.groups())
    try:
        naive = datetime(y, mo, d, hh, mm)
    except ValueError:
        return None
    return naive.replace(tzinfo=timezone(timedelta(hours=off))).astimezone(timezone.utc)


_QW_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{1,2}):(\d{2})\s*([AP])M\s+([A-Z]{2,4})", re.I)
_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August",
     "September","October","November","December"], 1)}


def parse_qwoted_deadline(s, year_hint=None):
    """Qwoted shape: '15 September 3:00PM CDT'. No year in the string, so the
    year is taken from the message date rather than assumed to be now."""
    if not s:
        return None
    m = _QW_RE.search(s)
    if not m:
        return None
    day, mon, hh, mm, ap, zone = m.groups()
    mo = _MONTHS.get(mon.lower())
    off = _offset(zone)
    if mo is None or off is None:
        return None
    hh = int(hh) % 12
    if ap.lower() == "p":
        hh += 12
    y = year_hint or datetime.now(timezone.utc).year
    try:
        naive = datetime(y, mo, int(day), hh, int(mm))
    except ValueError:
        return None
    return naive.replace(tzinfo=timezone(timedelta(hours=off))).astimezone(timezone.utc)


# HARO writes BARE zone abbreviations — "6:00 PM ET", not "EST" or "EDT".
# Bare ET is ambiguous between -5 and -4, and the project rule is that a
# guessed offset is worse than none: it would silently mis-rank urgency by an
# hour, which is enough to call a live request dead.
#
# But returning None for every HARO deadline would blind `missed_on_arrival`
# on the ONLY channel that has ever produced a link. So the ambiguity is
# resolved the one way that is not a guess: by the actual US civil-time rule.
# DST runs from the second Sunday in March to the first Sunday in November.
_BARE_US_ZONES = {"et": (-5, -4), "ct": (-6, -5), "mt": (-7, -6), "pt": (-8, -7)}


def _nth_weekday(year, month, weekday, n):
    """n-th `weekday` (0=Mon) of a month."""
    d = _date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _us_dst_active(d):
    """US DST: 2nd Sunday in March -> 1st Sunday in November."""
    start = _nth_weekday(d.year, 3, 6, 2)
    end = _nth_weekday(d.year, 11, 6, 1)
    return start <= d < end


def _offset_for(zone, on_date):
    """Offset for a zone spelling, resolving bare US abbreviations by date."""
    z = (zone or "").strip().lower()
    if z in _BARE_US_ZONES and on_date is not None:
        std, dst = _BARE_US_ZONES[z]
        return dst if _us_dst_active(on_date) else std
    return _offset(zone)


_HARO_DL_RE = re.compile(r"(\d{1,2}):(\d{2})\s*([AP])M\s+([A-Z]{2,4})\s*-\s*(\d{1,2})\s+([A-Za-z]+)", re.I)


def parse_haro_deadline(s, year_hint=None):
    """HARO shape: '6:00 PM ET - 17 September'. Time first, then the day, and
    no year — so the year comes from the message date, never from now()."""
    if not s:
        return None
    m = _HARO_DL_RE.search(s)
    if not m:
        return None
    hh, mm, ap, zone, day, mon = m.groups()
    mo = _MONTHS.get(mon.lower())
    if mo is None:
        return None
    y = year_hint or datetime.now(timezone.utc).year
    try:
        on = _date(y, mo, int(day))
    except ValueError:
        return None
    off = _offset_for(zone, on)
    if off is None:
        return None
    hh = int(hh) % 12
    if ap.lower() == "p":
        hh += 12
    try:
        naive = datetime(y, mo, int(day), hh, int(mm))
    except ValueError:
        return None
    return naive.replace(tzinfo=timezone(timedelta(hours=off))).astimezone(timezone.utc)


_CX_DL_RE = re.compile(r"([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?", re.I)
_MONTHS_ABBR = {m[:3].lower(): i for m, i in _MONTHS.items()}


def parse_connectively_deadline(s, year_hint=None):
    """Connectively shape: 'Sep 18th'. NO TIME AND NO ZONE ARE GIVEN.

    End of the stated day in UTC is used, and that is a deliberate choice worth
    naming: assuming a US zone would make a deadline look up to 8 hours
    tighter or looser than it is. UTC end-of-day is the latest defensible
    reading, so `missed_on_arrival` stays conservative — it will never call a
    live request dead.
    """
    if not s:
        return None
    m = _CX_DL_RE.search(s)
    if not m:
        return None
    mon, day = m.groups()
    mo = _MONTHS.get(mon.lower()) or _MONTHS_ABBR.get(mon[:3].lower())
    if mo is None:
        return None
    y = year_hint or datetime.now(timezone.utc).year
    try:
        return datetime(y, mo, int(day), 23, 59, tzinfo=timezone.utc)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def connect():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS source_items (
        source_key   TEXT PRIMARY KEY,
        request_id   INTEGER REFERENCES requests(id),
        platform     TEXT, bucket TEXT, reason TEXT,
        requires_manual INTEGER, matched_terms TEXT, followed_tags TEXT,
        respond_url  TEXT, journalist_name TEXT, journalist_email TEXT,
        muck_rack_url TEXT, media_website TEXT, category TEXT,
        deadline_date TEXT, deadline_time TEXT, time_zone TEXT,
        query_truncated INTEGER, gmail_id TEXT, run_date TEXT,
        deadline_utc TEXT, missed_on_arrival INTEGER DEFAULT 0,
        recipient TEXT, matched_expert TEXT);
    CREATE INDEX IF NOT EXISTS idx_source_items_bucket ON source_items(bucket);
    -- Keyed on run_at, not run_date: SOS sends up to three times a day with
    -- same-day deadlines, so more than one run per day is expected and every
    -- execution must be recorded. run_date is kept for daily grouping.
    CREATE TABLE IF NOT EXISTS source_runs (
        run_at TEXT PRIMARY KEY, run_date TEXT, messages INTEGER, items INTEGER,
        answerable INTEGER, marginal INTEGER, rejected INTEGER, new_items INTEGER,
        missed_on_arrival INTEGER DEFAULT 0);
    """)
    return conn


def persist(conn, rows, run_date):
    """Idempotent: source_key is the primary key, so a re-run of the same
    messages inserts nothing."""
    new = 0
    for r in rows:
        exists = conn.execute("SELECT 1 FROM source_items WHERE source_key=?",
                              (r["source_key"],)).fetchone()
        if exists:
            continue
        cur = conn.execute("""
            INSERT INTO requests (platform, outlet, query_text, deadline,
                                  ingested_at, topic_match, status)
            VALUES (?,?,?,?,?,?,?)""",
            (r["platform"], r["outlet"], r["query_text"], r["deadline"],
             run_date, json.dumps(r["matched_terms"]),
             "filtered_out" if r["bucket"] == "rejected" else "new"))
        conn.execute("""
            INSERT INTO source_items (
                source_key, request_id, platform, bucket, reason,
                requires_manual, matched_terms, followed_tags, respond_url,
                journalist_name, journalist_email, muck_rack_url, media_website,
                category, deadline_date, deadline_time, time_zone,
                query_truncated, gmail_id, run_date, deadline_utc,
                missed_on_arrival, recipient, matched_expert)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["source_key"], cur.lastrowid, r["platform"], r["bucket"], r["reason"],
             1 if r["requires_manual"] else 0, json.dumps(r["matched_terms"]),
             json.dumps(r.get("followed_tags") or []), r.get("respond_url"),
             r.get("journalist_name"), r.get("journalist_email"),
             r.get("muck_rack_url"), r.get("media_website"), r.get("category"),
             r.get("deadline_date"), r.get("deadline_time"), r.get("time_zone"),
             1 if r.get("query_truncated") else 0, r["gmail_id"], run_date,
             r.get("deadline_utc"), 1 if r.get("missed_on_arrival") else 0,
             r.get("recipient"), r.get("matched_expert")))
        new += 1
    return new


# --------------------------------------------------------------------------
# ingest
# --------------------------------------------------------------------------
def ingest(payload, connection_id, labels_queried, run_date, run_at=None):
    assert_connection(connection_id)                      # Rule 1
    assert_label_scope(labels_queried)                    # Rule 4
    messages = payload.get("results") or []
    assert_non_empty(messages, "label scope %s" % (labels_queried,))   # Rule 3
    assert_delivered_to(messages)                         # Rule 2

    claim_topics, _bank = load_claim_topics()
    experts = load_experts()
    run_at = run_at or datetime.now(timezone.utc)
    rows, skipped = [], Counter()
    # Round 7 §4. A message from a real platform we have no parser for is not
    # noise and must not be filed as noise: it is evidence that arrived and
    # was not read. HARO is the case in point — the four proven links came
    # through that channel, so a HARO digest silently counted as "skipped"
    # would be the single most expensive missing value in this project.
    unparsed = Counter()

    for m in messages:
        src = route(m)                                    # Rule 5: sender only
        gid = m.get("id")
        body = m.get("body_plain") or ""
        if src == "sos":
            if not sos_parser.looks_like_digest(body):
                skipped["sos_noise"] += 1; continue
            for it in sos_parser.parse(body, source_id=gid):   # Rule 6 inside
                bucket, terms, reason, who = classify(it, claim_topics, experts)
                rows.append({
                    "source_key": "sos:%s:%d" % (gid, it["item_no"]),
                    "platform": "sos", "gmail_id": gid,
                    "outlet": it.get("media_outlet") or "",
                    "query_text": it.get("query") or it.get("summary") or "",
                    "deadline": " ".join(x for x in (it.get("deadline_date"),
                                                     it.get("deadline_time"),
                                                     it.get("time_zone")) if x),
                    "bucket": bucket, "reason": reason, "matched_terms": terms,
                    "matched_expert": who, "recipient": delivered_to(m),
                    "requires_manual": False,
                    "journalist_name": it.get("name"),
                    "journalist_email": it.get("email"),
                    "muck_rack_url": it.get("muck_rack_url"),
                    "media_website": it.get("media_website"),
                    "category": it.get("category"),
                    "deadline_date": it.get("deadline_date"),
                    "deadline_time": it.get("deadline_time"),
                    "time_zone": it.get("time_zone"),
                    "summary": it.get("summary"),
                    "query_truncated": False,
                    "deadline_utc": None,
                })
        elif src == "qwoted":
            if not qwoted_parser.looks_like_request(body):
                skipped["qwoted_noise"] += 1; continue
            it = qwoted_parser.parse(body, source_id=gid)
            bucket, terms, reason, who = classify(it, claim_topics, experts)
            rows.append({
                "source_key": "qwoted:%s" % gid,
                "platform": "qwoted", "gmail_id": gid,
                "outlet": it["outlet"], "query_text": it["query"],
                "deadline": it["deadline"],
                "bucket": bucket, "reason": reason, "matched_terms": terms,
                "matched_expert": who, "recipient": delivered_to(m),
                "requires_manual": it["requires_manual"],
                "journalist_name": None, "journalist_email": None,
                "muck_rack_url": None, "media_website": None,
                "category": None, "deadline_date": None,
                "deadline_time": None, "time_zone": None,
                "followed_tags": it["followed_tags"],
                "respond_url": it["respond_url"],
                "summary": it["headline"],
                "query_truncated": it["query_truncated"],
                "deadline_utc": None,
                "_msg_year": int((m.get("raw") or {}).get("internalDate", "0")[:10] or 0),
            })
        elif src == "haro":
            # HARO also sends account-lifecycle mail from the same address, so
            # the digest test decides, not the sender and not the subject.
            if not haro_parser.looks_like_digest(body):
                skipped["haro_noise"] += 1; continue
            for it in haro_parser.parse(body, source_id=gid):
                bucket, terms, reason, who = classify(it, claim_topics, experts)
                rows.append({
                    "source_key": "haro:%s:%d" % (gid, it["item_no"]),
                    "platform": "haro", "gmail_id": gid,
                    "outlet": it.get("media_outlet") or "",
                    "query_text": it.get("query") or it.get("summary") or "",
                    "deadline": it.get("deadline") or "",
                    "bucket": bucket, "reason": reason, "matched_terms": terms,
                    "matched_expert": who, "recipient": delivered_to(m),
                    # HARO issues a real reply mailbox per query, read out of
                    # the mail. This is the only channel with a direct path.
                    "requires_manual": it["requires_manual"],
                    "journalist_name": it.get("journalist_name"),
                    "journalist_email": it.get("journalist_email"),
                    "muck_rack_url": it.get("haro_journalist_profile_url") or None,
                    "media_website": it.get("media_website"),
                    "category": it.get("category"),
                    "deadline_date": it.get("deadline_date"),
                    "deadline_time": it.get("deadline_time"),
                    "time_zone": it.get("time_zone"),
                    "summary": it.get("summary"),
                    "query_truncated": False,
                    "deadline_utc": None,
                    "_msg_year": int((m.get("raw") or {}).get("internalDate", "0")[:10] or 0),
                })
        elif src == "connectively":
            if not cx_parser.looks_like_digest(body):
                skipped["connectively_noise"] += 1; continue
            for it in cx_parser.parse(body, source_id=gid):
                bucket, terms, reason, who = classify(it, claim_topics, experts)
                rows.append({
                    # The platform's own per-question slug is the dedup key
                    # where it exists: it survives a reworded digest, which a
                    # text hash would not.
                    "source_key": "connectively:%s:%s"
                                  % (gid, it.get("slug") or it["item_no"]),
                    "platform": "connectively", "gmail_id": gid,
                    "outlet": it.get("outlet") or "",
                    "query_text": it.get("query") or "",
                    "deadline": it.get("deadline") or "",
                    "bucket": bucket, "reason": reason, "matched_terms": terms,
                    "matched_expert": who, "recipient": delivered_to(m),
                    "requires_manual": it["requires_manual"],
                    "journalist_name": None,
                    "journalist_email": it.get("journalist_email"),
                    "muck_rack_url": None, "media_website": None,
                    "category": it.get("category"),
                    "deadline_date": None, "deadline_time": None,
                    "time_zone": None,
                    "respond_url": it.get("respond_url"),
                    "summary": it.get("summary"),
                    "query_truncated": False,
                    "deadline_utc": None,
                    "_msg_year": int((m.get("raw") or {}).get("internalDate", "0")[:10] or 0),
                })
        else:
            skipped["%s_no_parser" % src] += 1
            if src == "featured":
                unparsed[src] += 1

    # Resolve deadlines to UTC and flag anything already expired when we
    # first saw it. missed_on_arrival is the cadence measurement: it counts
    # requests that were dead before the pipeline ever looked, which is what
    # tells you whether daily is frequent enough.
    for r in rows:
        yr = None
        if r.get("_msg_year"):
            yr = datetime.fromtimestamp(r["_msg_year"], timezone.utc).year
        if r["platform"] == "sos":
            dt = parse_deadline(r.get("deadline_date"), r.get("deadline_time"),
                                r.get("time_zone"))
        elif r["platform"] == "haro":
            dt = parse_haro_deadline(r.get("deadline"), yr)
        elif r["platform"] == "connectively":
            dt = parse_connectively_deadline(r.get("deadline"), yr)
        else:
            dt = parse_qwoted_deadline(r.get("deadline"), yr)
        r["deadline_utc"] = dt.isoformat() if dt else None
        r["missed_on_arrival"] = bool(dt and dt < run_at)
        r.pop("_msg_year", None)

    assert_clinical_attribution(rows)   # HARD RULE, raises

    # Every Qwoted row must be manual. Property of the source, not a setting.
    bad = [r["source_key"] for r in rows
           if r["platform"] == "qwoted" and not r["requires_manual"]]
    if bad:
        raise SourceError("Qwoted rows missing requires_manual: %s" % bad)
    # A Connectively Q&A row's only route is a single-use magic link, which is
    # an auth redirect and not a reply path. If one is ever marked answerable
    # directly, something constructed an address — raise rather than pitch it.
    bad = [r["source_key"] for r in rows
           if r["platform"] == "connectively" and not r["requires_manual"]
           and "tmxmessenger" not in (r.get("journalist_email") or "")]
    if bad:
        raise SourceError(
            "Connectively rows marked non-manual without a relay address: %s. "
            "The magic-link is an auth redirect, not a reply path, and no "
            "address may be constructed from the outlet name." % bad)
    return rows, skipped, unparsed


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def render_report(conn, rows, skipped, run_date, msg_count, unparsed=None):
    counts = Counter(r["bucket"] for r in rows)
    cum = conn.execute("""SELECT COUNT(*),
        SUM(bucket='answerable'), SUM(bucket='marginal'), SUM(bucket='rejected')
        FROM source_items""").fetchone()
    runs = conn.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0]

    L = ["# Source digest — %s" % run_date, "",
         "Generated by `pipelines/01_source.py`. **Nothing has been drafted, "
         "pitched or sent. The mailbox was not modified.**", ""]
    L += ["| | |", "|---|---|",
          "| Messages ingested | %d |" % msg_count,
          "| Items parsed | %d |" % len(rows),
          "| **Answerable** | **%d** |" % counts["answerable"],
          "| Marginal | %d |" % counts["marginal"],
          "| Rejected | %d |" % counts["rejected"], ""]
    # Round 7 §4 — the gap is a line in the report, not a silent skip counter.
    if unparsed:
        L += ["## \u26A0\uFE0F Ingested but UNPARSED", "",
              "These arrived and were **not read**. No parser exists for them, "
              "so their contents were never filtered and they cannot appear in "
              "any bucket. This is a known gap, deliberately left open: one "
              "digest is not enough to know whether the format varies between "
              "sends, and SOS needed two samples to answer that same question.",
              "", "| Platform | Messages | Parser |", "|---|---|---|"]
        for k, v in sorted(unparsed.items()):
            L.append("| %s | %d | **none written** |" % (k, v))
        L.append("")

    by_src = Counter(r["platform"] for r in rows)
    L += ["## Items by source", "", "| Source | Items | Answerable | Marginal | Rejected |",
          "|---|---|---|---|---|"]
    for s in sorted(by_src):
        sr = [r for r in rows if r["platform"] == s]
        c = Counter(r["bucket"] for r in sr)
        L.append("| `%s` | %d | %d | %d | %d |"
                 % (s, len(sr), c["answerable"], c["marginal"], c["rejected"]))
    L.append("")
    if skipped:
        L += ["Skipped (no parser, or platform noise): %s"
              % ", ".join("%s=%d" % kv for kv in sorted(skipped.items())), ""]

    for bucket, heading in (("answerable", "Answerable"), ("marginal", "Marginal")):
        got = [r for r in rows if r["bucket"] == bucket]
        L += ["---", "", "## %s — %d" % (heading, len(got)), ""]
        if not got:
            L += ["None this run.", ""]
            continue
        for r in got:
            L += ["### %s — %s" % (r["outlet"] or "(no outlet)", r.get("summary") or ""),
                  "",
                  "- **Platform:** `%s`" % r["platform"],
                  "- **Deadline:** %s" % (r["deadline"] or "not stated"),
                  "- **Why:** %s" % r["reason"]]
            if r["platform"] == "qwoted":
                L += ["- **Reply path:** %s" % (r.get("respond_url") or "—"),
                      "- ⚠️ **Requires manual handling.** No journalist name or "
                      "email in the email, and the query text is truncated "
                      "(both plaintext and HTML). A human must click through.",
                      "- **Followed tags:** %s" % ", ".join("#" + t for t in (r.get("followed_tags") or [])) ]
            else:
                L += ["- **Journalist:** %s <%s>" % (r.get("journalist_name") or "?",
                                                     r.get("journalist_email") or "?"),
                      "- **Outlet site:** %s" % (r.get("media_website") or "—")]
            L += ["", "> %s" % (r["query_text"] or "")[:900], ""]

    L += ["---", "", "## Rejections — %d, logged not discarded" % counts["rejected"], "",
          "At the current rate the rejections are the dataset. They are how you "
          "tell a filter that is too tight from a niche that is genuinely quiet.", ""]
    rc = Counter(r["reason"].split("(")[0].strip() for r in rows if r["bucket"] == "rejected")
    cats = Counter((r.get("category") or "uncategorised") for r in rows if r["bucket"] == "rejected")
    L += ["| Rejection reason | Count |", "|---|---|"]
    for reason, n in rc.most_common():
        L.append("| %s | %d |" % (reason, n))
    L += ["", "| Category of rejected item | Count |", "|---|---|"]
    for c, n in cats.most_common(12):
        L.append("| %s | %d |" % (c, n))
    L += ["", "<details><summary>All rejected items</summary>", ""]
    for r in [x for x in rows if x["bucket"] == "rejected"]:
        L.append("- `%s` **%s** — %s" % (r["platform"], r["outlet"] or "?",
                                         (r.get("summary") or "")[:90]))
    L += ["", "</details>", ""]

    L += ["---", "", "## Cumulative across all runs", "",
          "| | |", "|---|---|",
          "| Runs | %d |" % runs,
          "| Items | %d |" % (cum[0] or 0),
          "| Answerable | %d |" % (cum[1] or 0),
          "| Marginal | %d |" % (cum[2] or 0),
          "| Rejected | %d |" % (cum[3] or 0), ""]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")




def export_state(conn):
    """Write the derived rows to a committed JSON so a cold start can restore
    them. Deliberately NOT the raw Gmail payload: this is the pipeline's own
    output, not a mailbox dump."""
    items = [dict(r) for r in conn.execute("SELECT * FROM source_items")]
    runs = [dict(r) for r in conn.execute("SELECT * FROM source_runs")]
    reqs = [dict(r) for r in conn.execute(
        "SELECT * FROM requests WHERE id IN (SELECT request_id FROM source_items)")]
    doc = {"_comment": "Derived output of 01_source, committed so links.db can "
                       "be rebuilt on a cold start. Not raw mail.",
           "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "requests": reqs, "source_items": items, "source_runs": runs}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return len(items), len(runs)



# --------------------------------------------------------------------------
# cold start
# --------------------------------------------------------------------------
# A scheduled session has no conversational context and nobody watching. Every
# precondition is checked BEFORE any work, and every failure alerts.
#
# The reason this matters more than usual here: a pipeline that silently stops
# running produces exactly the same observable as a quiet niche — zero
# answerable items, day after day. This project is about to spend two weeks
# measuring that precise distinction, so a silent failure would not just lose
# a day, it would corrupt the conclusion.
def preflight(require_connectors=True):
    """`require_connectors=False` only for commands that make no connector
    call at all (rescore). Anything that reads the mailbox or needs to be
    able to alert asserts both."""
    problems = []
    if not os.path.exists(DB_PATH):
        problems.append(
            "links.db is missing. It is a gitignored build artifact — run "
            "`python3 pipelines/rebuild.py run` to reconstruct it from "
            "committed files. Do NOT proceed: a fresh empty database would "
            "reset the 14-day trend counter to zero and look like a quiet week.")
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            have = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            conn.close()
            missing = {"requests", "targets"} - have
            if missing:
                problems.append("links.db exists but is missing tables %s — "
                                "run pipelines/rebuild.py" % sorted(missing))
        except sqlite3.Error as e:
            problems.append("links.db is unreadable (%s) — run pipelines/rebuild.py" % e)
    claims_path = os.path.join(DATA, "claims.json")
    if not os.path.exists(claims_path):
        problems.append(
            "claims.json is missing. The filter has nothing to classify "
            "against; every item would fall through to 'rejected' and the run "
            "would report a confident, meaningless zero.")
    if not os.path.exists(SCHEMA):
        problems.append("schema.sql is missing — the database cannot be created.")
    # Round 7 §2 — both connectors, asserted from real calls, before any work.
    if require_connectors:
        try:
            assert_connectors()
        except SourceError as e:
            problems.append(str(e))
    if problems:
        raise SourceError("COLD-START PREFLIGHT FAILED:\n  - %s"
                          % "\n  - ".join(problems))
    return True


def delivery_instruction(path):
    """Where to send an alert, decided by whether Slack is actually up."""
    slack_ok = True
    try:
        with open(PROBE, encoding="utf-8") as fh:
            slack_ok = bool((json.load(fh).get("slack") or {}).get("ok"))
    except (OSError, ValueError, KeyError):
        slack_ok = False        # no probe, no evidence Slack works
    if slack_ok:
        return ("*** POST TO SLACK #media (%s) — body in %s.slack.txt ***"
                % (SLACK_ALERT_CHANNEL, os.path.relpath(path, ROOT)))
    return ("*** SLACK IS NOT CONFIRMED REACHABLE — do NOT rely on posting "
            "there. Send the fallback instead: PushNotification with "
            "status=\"proactive\" (the only value its schema accepts), "
            "message under 200 chars. Detail is in %s ***"
            % os.path.relpath(path, ROOT))


def emit_failure_alert(stage, err, run_date):
    """Write the failure alert. A failed run is itself an event that must
    reach #media — silence is indistinguishable from a quiet niche."""
    # The consequence differs by stage and saying the wrong one is its own
    # missing-value failure: a push-verification failure means the run DID
    # complete and its output is stranded, which needs a different response
    # from a run that never produced anything.
    if stage == "push-verification":
        consequence = ("The run completed but its output is NOT on the remote. "
                       "When this container is reclaimed the data is gone. The "
                       "trend counter will not count this run and the report "
                       "will show it as a gap, not a quiet day.")
    elif stage == "connector-probe":
        consequence = ("The run did NOT start: a connector could not be proved "
                       "reachable. Today has no data. This is not a quiet day "
                       "\u2014 treat the trend line as having a gap.")
    else:
        consequence = ("The run did not complete, so today has NO data. This "
                       "is not a quiet day \u2014 treat the trend line as "
                       "having a gap.")
    body = (":x: *01_source FAILED* \u2014 %s\n\n"
            "*Stage:* %s\n"
            "*Error:* %s\n\n%s\n"
            "Runbook: linkbuilding/RUNBOOK.md"
            % (run_date, stage, str(err)[:1500], consequence))
    md = ["# \u274C 01_source run FAILED — %s" % run_date, "",
          "**Stage:** %s" % stage, "", "```", str(err)[:4000], "```", "",
          "## What this means", "", consequence, "",
          "## Why this is an alert and not a log line", "",
          "A pipeline that stops running looks identical to a niche with no "
          "relevant requests: zero answerable items, every day. The 14-day "
          "decision in `reports/source-trend.md` depends on telling those "
          "apart, so a failed run must be visible, and the trend must be read "
          "as having a gap rather than a quiet day.", "",
          "See `linkbuilding/RUNBOOK.md` for recovery."]
    os.makedirs(os.path.dirname(FAIL_ALERT), exist_ok=True)
    with open(FAIL_ALERT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    with open(FAIL_ALERT + ".slack.txt", "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    return FAIL_ALERT


# --------------------------------------------------------------------------
# alerting
# --------------------------------------------------------------------------
# ALERT DELIVERY: Slack #media (C0C26J8JX8U), a PRIVATE channel.
#
# An earlier search for it returned nothing because slack_search_channels
# defaults to public channels only — pass channel_types including
# private_channel, or the channel is invisible. Recorded here so the next
# person does not repeat it and conclude no channel exists.
#
# This function writes the alert BODY; the agent session posts it, because
# Slack is an MCP tool and MCP exists only inside a session. The file is the
# durable artifact and the audit trail; the Slack post is the notification.
SLACK_ALERT_CHANNEL = "C0C26J8JX8U"     # #media (private)


# --- Round 7 §6: alerting is gated on APPROVAL, not on the bucket ----------
# The 2026-09-15 run alerted on three answerable items, all matched against
# Tripler's provisional topic set — agent-authored, `approved: false`, never
# reviewed by her. Nothing could be sent from any of them. Those same three
# would have alerted on every subsequent run until the corpus changed, which
# teaches the channel to be ignored before a real item ever arrives.
#
# So an immediate alert requires an APPROVED expert behind the match. A
# provisional match is real signal and is kept — it just goes in the daily
# heartbeat instead of interrupting anyone. A quiet channel with a pulse is
# the design.


def approved_experts(experts, bank):
    """The experts whose matches may raise an immediate alert.

    Currently EMPTY by design: the claim bank is `awaiting_review` and
    Tripler's topic set is `approved: false`. This reads the real status
    rather than hardcoding zero, so the day either is signed the alerting
    starts working with no code change.
    """
    ok = set()
    if (bank or {}).get("approval_status") == "approved":
        ok.add("alptunaer")
    for eid, e in (experts or {}).items():
        if e.get("approved") is True or e.get("approval_status") == "approved":
            ok.add(eid)
    return ok


def load_alerted():
    if not os.path.exists(ALERTED):
        return {}
    with open(ALERTED, encoding="utf-8") as fh:
        return json.load(fh).get("alerted", {})


def record_alerted(keys, run_date):
    seen = load_alerted()
    for k in keys:
        seen.setdefault(k, run_date)
    os.makedirs(os.path.dirname(ALERTED), exist_ok=True)
    with open(ALERTED, "w", encoding="utf-8") as fh:
        json.dump({"_comment": "source_keys already alerted on, and the run "
                               "date they first alerted. A standing item must "
                               "not re-alert every run.",
                   "alerted": seen}, fh, indent=2)
        fh.write("\n")
    return seen


def split_hits(rows, approved):
    """(immediate, provisional) — answerable rows, split on approval and
    deduped against everything already alerted."""
    hits = [r for r in rows if r["bucket"] == "answerable"]
    already = load_alerted()
    immediate, provisional = [], []
    for r in hits:
        if r.get("matched_expert") in approved:
            if r["source_key"] not in already:
                immediate.append(r)
        else:
            provisional.append(r)
    return immediate, provisional


def slack_alert_body(hits, run_date):
    """Compact plain-text body for Slack. Kept separate from the markdown
    file: Slack truncates and nobody reads a wall of query text in a channel."""
    if not hits:
        return None
    lines = [":rotating_light: *%d ANSWERABLE journalist request(s)* — run %s"
             % (len(hits), run_date), ""]
    for r in hits:
        lines.append("*%s* — %s" % (r["outlet"] or "(no outlet)", r.get("summary") or ""))
        lines.append("  deadline: %s" % (r["deadline"] or "not stated"))
        lines.append("  matched: %s" % ", ".join(r["matched_terms"]))
        lines.append("  expert: %s" % (r.get("matched_expert") or "?"))
        if r["platform"] == "qwoted":
            lines.append("  reply: %s (manual click-through, no journalist contact in email)"
                         % (r.get("respond_url") or "—"))
        else:
            lines.append("  journalist: %s <%s>" % (r.get("journalist_name") or "?",
                                                    r.get("journalist_email") or "?"))
        lines.append("")
    lines.append("Full detail: linkbuilding/reports/ALERT-answerable.md")
    return "\n".join(lines)


def emit_alert(rows, run_date, run_at, approved):
    """Write the immediate-alert artifacts. Returns (path, immediate,
    provisional); path is None when nothing warrants interrupting anyone."""
    immediate, provisional = split_hits(rows, approved)
    if not immediate:
        for stale in (ALERT, ALERT + ".slack.txt"):
            if os.path.exists(stale):
                os.remove(stale)     # a stale alert is worse than none
        return None, immediate, provisional
    L = ["# \U0001F6A8 ANSWERABLE JOURNALIST REQUEST — %d" % len(immediate), "",
         "Run %s (%s). **This is the event the pipeline exists for.**" % (run_date, run_at),
         "", "Matched against an APPROVED expert. Provisional matches do not "
         "appear here; they are counted in the daily heartbeat.", ""]
    for r in immediate:
        L += ["---", "", "## %s — %s" % (r["outlet"] or "(no outlet)", r.get("summary") or ""),
              "", "- **Platform:** `%s`" % r["platform"],
              "- **Expert:** %s" % (r.get("matched_expert") or "?"),
              "- **Deadline:** %s" % (r["deadline"] or "not stated"),
              "- **Deadline (UTC):** %s" % (r.get("deadline_utc") or "unparsed"),
              "- **Matched:** %s" % ", ".join(r["matched_terms"]),
              "- **Why:** %s" % r["reason"]]
        if r["platform"] == "qwoted":
            L += ["- **Reply path:** %s" % (r.get("respond_url") or "—"),
                  "- ⚠️ Requires manual click-through; no journalist contact in the email."]
        else:
            L += ["- **Journalist:** %s <%s>" % (r.get("journalist_name") or "?",
                                                 r.get("journalist_email") or "?")]
        L += ["", "> %s" % (r["query_text"] or "")[:1200], ""]
    os.makedirs(os.path.dirname(ALERT), exist_ok=True)
    with open(ALERT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    body = slack_alert_body(immediate, run_date)
    if body:
        with open(ALERT + ".slack.txt", "w", encoding="utf-8") as fh:
            fh.write(body + "\n")
    record_alerted([r["source_key"] for r in immediate], run_date)
    return ALERT, immediate, provisional


# --- Round 7 §3: the daily heartbeat --------------------------------------
# At the observed rate an answerable item may be weeks away. A channel that
# is silent for two weeks is indistinguishable from a channel whose posting
# path is broken — which is the same missing-value failure this project keeps
# hitting, one layer up. One line a day makes the silence informative.


def is_first_run_of_day(conn, run_date):
    """Asked BEFORE this run is inserted, so it means 'no earlier run today'."""
    return conn.execute("SELECT COUNT(*) FROM source_runs WHERE run_date=?",
                        (run_date,)).fetchone()[0] == 0


def push_status_line():
    log = load_push_log()
    if not log:
        return "no run has been confirmed on the remote yet"
    last = max(log, key=lambda e: e["run_at"])
    return "last confirmed on remote: %s (%s)" % (last["run_date"], last["commit"][:8])


def emit_heartbeat(rows, counts, run_date, provisional, unparsed, day_n):
    """One line to #media. Written to a file; the session posts it."""
    parts = [":heartbeat: *01_source* %s — day %s · %d items · %d answerable / "
             "%d marginal / %d rejected"
             % (run_date, day_n, len(rows), counts["answerable"],
                counts["marginal"], counts["rejected"])]
    if provisional:
        parts.append("%d answerable held as PROVISIONAL (unapproved expert) — "
                     "no alert raised: %s"
                     % (len(provisional),
                        "; ".join((r.get("outlet") or "?") for r in provisional[:4])))
    if unparsed:
        tot = sum(unparsed.values())
        parts.append(":warning: %d message(s) ingested but UNPARSED (%s) — no "
                     "parser written yet, so their contents are not filtered"
                     % (tot, ", ".join("%s ×%d" % (k, v)
                                       for k, v in sorted(unparsed.items()))))
    parts.append("push: %s" % push_status_line())
    body = "\n".join(parts)
    os.makedirs(os.path.dirname(HEARTBEAT), exist_ok=True)
    with open(HEARTBEAT, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    return HEARTBEAT


# --------------------------------------------------------------------------
# Round 7 §2 — connector reachability, asserted before any work
# --------------------------------------------------------------------------
# WHY THIS IS EVIDENCE AND NOT A FLAG. The 2026-09-14 failure was a run that
# read `is_stale: false` off a connection listing and proceeded to read the
# wrong mailbox. A self-reported health flag is not reachability. So `probe`
# takes the RAW result of an actual call to each connector and decides for
# itself; the agent relays, the code judges. A stale OAuth registration
# returns an error or an empty set, and both fail here.
#
# Slack matters as much as Gmail and has never once executed in a Routine
# session: answerable has been zero every run, so the alert path is entirely
# theoretical and would first fire on the day it mattered. Slack unreachable
# is therefore a FAILURE STATE, not a degraded mode — the run exits non-zero
# and the fallback is a PushNotification (see RUNBOOK; verified 2026-09-15).


def _load_json_file(path, what):
    if not os.path.exists(path):
        raise SourceError("%s not found at %s" % (what, path))
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    try:
        return json.loads(txt), txt
    except json.JSONDecodeError as e:
        raise SourceError("%s at %s is not JSON (%s). A tool error is often "
                          "returned as prose; that is a failed probe, not a "
                          "parse problem." % (what, path, e))


def judge_gmail_probe(raw_text):
    """Decide from the RAW gmail_find_email result whether the pinned mailbox
    actually answered. Returns a dict; raises on anything short of proof."""
    try:
        doc = json.loads(raw_text)
    except json.JSONDecodeError:
        raise SourceError("Gmail probe result is not JSON — the tool most "
                          "likely returned an error string. Probe FAILED.")
    if isinstance(doc, dict) and doc.get("isError"):
        raise SourceError("Gmail probe returned isError: %s"
                          % str(doc.get("error"))[:400])
    msgs = (doc.get("results") if isinstance(doc, dict) else None) or []
    if not msgs:
        # Rule 3, applied to the probe itself.
        raise SourceError(
            "Gmail probe returned zero messages. An empty result set is what "
            "the WRONG mailbox returns, and what a stale registration returns. "
            "It is not proof of reachability. Probe FAILED.")
    seen = {delivered_to(m) for m in msgs} - {None}
    good = seen & EXPECTED_RECIPIENTS
    if not good:
        raise SourceError(
            "Gmail probe answered, but Delivered-To was %s — none of them in "
            "EXPECTED_RECIPIENTS %s. Reachable is not the same as the right "
            "mailbox. Probe FAILED." % (sorted(seen), sorted(EXPECTED_RECIPIENTS)))
    return {"ok": True, "messages": len(msgs), "recipients": sorted(good)}


def judge_slack_probe(raw_text):
    """Decide from the RAW slack_read_channel result whether #media answered."""
    if not raw_text.strip():
        raise SourceError("Slack probe result is empty. Probe FAILED.")
    low = raw_text.lower()
    for bad in ("channel_not_found", "not_in_channel", "invalid_auth",
                "token_revoked", "account_inactive", "missing_scope"):
        if bad in low:
            raise SourceError("Slack probe returned `%s`. #media (%s) is not "
                              "reachable from this session. Probe FAILED."
                              % (bad, SLACK_ALERT_CHANNEL))
    try:
        doc = json.loads(raw_text)
        if isinstance(doc, dict) and doc.get("isError"):
            raise SourceError("Slack probe returned isError: %s"
                              % str(doc.get("error"))[:400])
    except json.JSONDecodeError:
        pass          # the Slack tool may return prose; the id check decides
    if SLACK_ALERT_CHANNEL not in raw_text:
        raise SourceError(
            "Slack probe result does not contain the channel id %s. A reply "
            "about some other channel is not proof that #media is reachable, "
            "and #media is where every alert goes. Probe FAILED."
            % SLACK_ALERT_CHANNEL)
    return {"ok": True, "channel": SLACK_ALERT_CHANNEL}


def assert_connectors(now=None):
    """Called from preflight. Requires a FRESH, PASSING probe for both."""
    now = now or datetime.now(timezone.utc)
    if not os.path.exists(PROBE):
        raise SourceError(
            "No connector probe. Run `01_source.py probe --gmail <raw> "
            "--slack <raw>` with the raw results of a real gmail_find_email "
            "call (connection %s) and a real slack_read_channel call on "
            "#media (%s) BEFORE running. Without it the run cannot tell a "
            "quiet niche from a dead connector."
            % (EXPECTED_CONNECTION_ID, SLACK_ALERT_CHANNEL))
    doc, _ = _load_json_file(PROBE, "connector probe")
    age = (now - datetime.fromisoformat(doc["probed_at"])).total_seconds()
    if age > PROBE_MAX_AGE_S:
        raise SourceError(
            "Connector probe is %.0f min old (limit %.0f). A probe from an "
            "earlier session proves nothing about this one — Routine sessions "
            "carry their own OAuth registration. Re-probe."
            % (age / 60.0, PROBE_MAX_AGE_S / 60.0))
    if age < -120:
        raise SourceError("Connector probe is dated %s, in the future. "
                          "Refusing to trust it." % doc["probed_at"])
    for name in ("gmail", "slack"):
        if not (doc.get(name) or {}).get("ok"):
            raise SourceError("Connector probe says %s is NOT ok: %s"
                              % (name, (doc.get(name) or {}).get("error")))
    return doc


def cmd_probe(a):
    """Validate raw connector results and write the probe. Exits non-zero if
    either connector fails, BEFORE any ingestion is attempted."""
    now = datetime.now(timezone.utc)
    out = {"probed_at": now.isoformat(timespec="seconds"),
           "connection_id": EXPECTED_CONNECTION_ID,
           "slack_channel": SLACK_ALERT_CHANNEL}
    failures = []
    for name, path, judge in (("gmail", a.gmail, judge_gmail_probe),
                              ("slack", a.slack, judge_slack_probe)):
        try:
            with open(path, encoding="utf-8") as fh:
                out[name] = judge(fh.read())
        except (OSError, SourceError) as e:
            out[name] = {"ok": False, "error": str(e)[:1000]}
            failures.append("%s: %s" % (name, e))
    os.makedirs(os.path.dirname(PROBE), exist_ok=True)
    with open(PROBE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2); fh.write("\n")
    for name in ("gmail", "slack"):
        print("  %-6s %s" % (name, "OK" if out[name].get("ok") else
                             "FAILED — " + out[name].get("error", "")[:200]))
    if failures:
        path = emit_failure_alert("connector-probe",
                                  SourceError("; ".join(failures)),
                                  _date.today().isoformat())
        print("\n*** CONNECTOR PROBE FAILED — the run must not proceed ***",
              file=sys.stderr)
        if not out["slack"].get("ok"):
            print("*** SLACK IS DOWN: do NOT try to post the alert there. "
                  "Send the fallback PushNotification instead (RUNBOOK "
                  "§ Alerting). ***", file=sys.stderr)
        else:
            print("*** POST TO SLACK #media (%s) — body in %s.slack.txt ***"
                  % (SLACK_ALERT_CHANNEL, os.path.relpath(path, ROOT)),
                  file=sys.stderr)
        return 4
    print("\nprobe OK — both connectors answered a real call at %s"
          % out["probed_at"])
    return 0


# --------------------------------------------------------------------------
# Round 7 §1 — a run that cannot persist has not succeeded
# --------------------------------------------------------------------------
# On 2026-09-14 a scheduled run exited 0, printed a clean summary, and
# persisted nothing: the push was denied and the container was reclaimed. The
# run reported success because `git push` raising was the only thing it knew
# how to notice, and it never got that far.
#
# So this does not check that a push command returned. It checks that THIS
# RUN'S OUTPUT is readable out of the commit the REMOTE is pointing at. The
# distinction is the whole point: a ref that moved, a commit that exists
# locally, and a push that printed no error are all satisfiable while the
# run's rows are still only in a container about to be deleted.


def _git(repo, *args):
    out = subprocess.run(("git",) + args, cwd=repo, capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise SourceError("git %s failed: %s"
                          % (" ".join(args), (out.stderr or out.stdout).strip()[:500]))
    return out.stdout.strip()


def load_push_log():
    if not os.path.exists(PUSH_LOG):
        return []
    with open(PUSH_LOG, encoding="utf-8") as fh:
        return json.load(fh).get("verified", [])


def verified_run_ats():
    return {e["run_at"] for e in load_push_log()}


def local_runs():
    """Every run in the committed state file, newest last."""
    doc, _ = _load_json_file(STATE, "source-state.json")
    runs = doc.get("source_runs") or []
    if not runs:
        raise SourceError("source-state.json holds no runs — nothing to verify.")
    return sorted(runs, key=lambda r: r["run_at"])


def latest_local_run():
    """(run_at, run_date) of the newest run in the committed state file."""
    newest = local_runs()[-1]
    return newest["run_at"], newest["run_date"]


def verify_push(branch=None, repo=None, fetch=True):
    """Raise unless this run's output is present in the commit the remote
    branch points at. Returns the verification record."""
    branch = branch or GIT_BRANCH
    repo = repo or os.path.dirname(ROOT)
    run_at, run_date = latest_local_run()

    dirty = _git(repo, "status", "--porcelain", "--", STATE_IN_REPO)
    if dirty:
        raise SourceError(
            "%s has uncommitted changes (%s). The run's output is in the "
            "working tree, not in any commit, so it cannot be on the remote. "
            "Commit before verifying." % (STATE_IN_REPO, dirty.strip()))

    ls = _git(repo, "ls-remote", "origin", "refs/heads/" + branch)
    if not ls:
        raise SourceError("origin has no branch %r. Nothing was pushed." % branch)
    remote_sha = ls.split()[0]
    if fetch:
        _git(repo, "fetch", "origin", branch)

    local = _git(repo, "rev-parse", "HEAD")
    anc = subprocess.run(("git", "merge-base", "--is-ancestor", local, remote_sha),
                         cwd=repo, capture_output=True, text=True)
    if anc.returncode != 0:
        raise SourceError(
            "Local HEAD %s is NOT contained in the remote head %s. The commit "
            "exists here and nowhere else; when this container is reclaimed "
            "the run is gone." % (local[:12], remote_sha[:12]))

    # The check that actually matters: read the state file OUT OF the remote
    # commit and confirm this run is in it. A ref can advance on a commit that
    # does not carry the run.
    try:
        blob = _git(repo, "show", "%s:%s" % (remote_sha, STATE_IN_REPO))
    except SourceError as e:
        raise SourceError("%s is not present in the remote commit %s (%s). "
                          "The push landed but carried no state."
                          % (STATE_IN_REPO, remote_sha[:12], e))
    try:
        remote_doc = json.loads(blob)
    except json.JSONDecodeError as e:
        raise SourceError("state file in remote commit %s is not valid JSON "
                          "(%s)" % (remote_sha[:12], e))
    on_remote = {r["run_at"] for r in (remote_doc.get("source_runs") or [])}
    if run_at not in on_remote:
        raise SourceError(
            "Run %s (%s) is NOT in the state file on the remote. The remote "
            "commit %s carries %d run(s), newest %s. This run has not been "
            "persisted — do not count it."
            % (run_at, run_date, remote_sha[:12], len(on_remote),
               max(on_remote) if on_remote else "none"))
    # Confirm EVERY local run against the same remote blob, not just the
    # newest. A run is verified by being present on the remote, and the log
    # not yet existing when it ran is a fact about the log, not about the run.
    # Checking only the newest would report every earlier run as NEVER
    # PERSISTED — a false alarm, which is the failure mode a banner this loud
    # can least afford.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return [{"run_at": r["run_at"], "run_date": r["run_date"],
             "commit": remote_sha, "branch": branch, "verified_at": now}
            for r in local_runs() if r["run_at"] in on_remote]


def cmd_verify_push(a):
    try:
        recs = verify_push(branch=a.branch, repo=a.repo)
    except SourceError as e:
        path = emit_failure_alert("push-verification", e, _date.today().isoformat())
        print("\n*** PUSH VERIFICATION FAILED — %s ***" % e, file=sys.stderr)
        print("*** This run's output is NOT on the remote. The trend counter "
              "will NOT count it, and the trend report will show a gap. ***",
              file=sys.stderr)
        print(delivery_instruction(path), file=sys.stderr)
        return 5
    log = load_push_log()
    have = {e["run_at"] for e in log}
    for rec in recs:
        if rec["run_at"] not in have:
            log.append(rec); have.add(rec["run_at"])
    log.sort(key=lambda e: e["run_at"])
    newest = recs[-1]
    os.makedirs(os.path.dirname(PUSH_LOG), exist_ok=True)
    with open(PUSH_LOG, "w", encoding="utf-8") as fh:
        json.dump({"_comment": "Runs CONFIRMED present in the state file on "
                               "the remote. render_trend counts these and only "
                               "these. Written by `01_source.py verify-push`.",
                   "verified": log}, fh, indent=2)
        fh.write("\n")
    # The trend is re-rendered so the run it just confirmed stops reading as
    # pending. Both files are committed by the NEXT push, one run behind —
    # that lag is deliberate and stated in the report rather than hidden.
    if os.path.exists(DB_PATH):
        conn = connect(); render_trend(conn); conn.close()
    print("push verified: run %s is readable from %s on origin/%s"
          % (newest["run_at"], newest["commit"][:12], newest["branch"]))
    print("%d of %d local run(s) found in the remote state file."
          % (len(recs), len(local_runs())))
    print("%d run(s) confirmed persisted. Commit %s and %s."
          % (len(log), os.path.relpath(PUSH_LOG, ROOT),
             os.path.relpath(TREND, ROOT)))
    return 0


# --------------------------------------------------------------------------
# trend report
# --------------------------------------------------------------------------
DECISION_CRITERIA = """## Decision criteria — fixed before the data arrived

Stated up front so the conclusion cannot be fitted to whatever turns up.

### \u26A0\uFE0F THE 14-DAY CLOCK HAS NOT STARTED

It starts on **the first HARO query digest**, not on the first run. As of
2026-09-15 no HARO digest has ever arrived at any address in this mailbox:
the only HARO mail is five account-lifecycle messages, the newest an
*unclicked* "Please Verify Your Email" sent to `media@` at 18:37 UTC that day.

This matters because of where the evidence actually comes from. All four
proven links \u2014 healthline DR91, eatthis DR83, womansworld DR66, singlecare
DR63 \u2014 arrived between 2026-01-20 and 2026-07-02, through HARO, on a
former contractor's own account. **Not one came through SOS or Qwoted.**

So a zero from SOS and Qwoted says nothing whatsoever about the channel that
produced every link this site has earned. Counting those days toward fourteen
would measure two channels that have never produced a link and then draw a
conclusion about a third.

### Expected order of magnitude

One link per six weeks, from a pitch volume necessarily higher than four.
That implies **a handful of answerable items per month** \u2014 single digits,
low ones. Not per day, and not per run.

Calibrate accordingly: **zero answerable on any given day is the expected
result and is not a signal.** A week of zeros is not a signal either. The
threshold that would genuinely condemn the pipeline is a *month* of HARO
digests arriving and being filtered to zero.

### Assess after 14 days OF HARO DIGESTS

| If, after 14 days of digests | Then |
|---|---|
| **>= 2 answerable per month** | `01_source` earns its place. Build the drafter. |
| **Answerable, but all from Qwoted** | Evaluate Qwoted Pro at $149/mo. The free tier's request delay and pitch-credit cap become the binding constraint. |
| **Zero answerable, marginals clustering in one topic** | The gap is in the claim bank, not the pipeline. Extend the bank in that topic. |
| **Zero answerable, marginals scattered** | The niche is quiet. Keep the filter running cheaply and move effort to dealer pages and outreach. |

A fifth outcome is possible and must not be silently folded into the fourth:
if `deadline misses on arrival` is high, the pipeline may be finding real
requests too late rather than not finding them. Check that row before
concluding the niche is quiet.

A sixth, currently the live one: **no digests are arriving at all.** That is a
plumbing problem and none of the five rows above apply to it."""


# --------------------------------------------------------------------------
# Round 9 — request identity, per platform
# --------------------------------------------------------------------------
# "Dedup on reply address" is right for HARO and WRONG everywhere else, and
# the difference was measured rather than assumed:
#
#   HARO  `reply+<uuid>@helpareporter.com` is a per-QUERY token. Across 162
#         rows / 112 addresses, ZERO addresses carry two different queries.
#         The uuid identifies the request, so the address is the identity.
#
#   SOS   `EMAIL:` is the journalist's real address — the PERSON, not the
#         request. 9 addresses carry more than one different query
#         (paigecerulli@gmail.com: 4 rows, 4 genuinely different queries).
#         Deduping on it would silently merge distinct requests. SOS does also
#         repeat a query across sends, so identity is (address, query text).
#
#   Connectively / Qwoted  one row per request already; source_key holds the
#         platform's own per-question slug where there is one.
#
# Collapsing all four onto one key would have cut SOS from 58 real requests to
# 39 and called it deduplication.
DEDUP_SQL = """
    CASE s.platform
      WHEN 'haro' THEN s.journalist_email
      WHEN 'sos'  THEN COALESCE(s.journalist_email,'') || '|' || substr(r.query_text,1,160)
      ELSE s.source_key
    END"""


def request_key(platform, journalist_email, query_text, source_key):
    """Python mirror of DEDUP_SQL. A test asserts the two agree."""
    if platform == "haro":
        return journalist_email or source_key
    if platform == "sos":
        return "%s|%s" % (journalist_email or "", (query_text or "")[:160])
    return source_key


def distinct_counts(conn):
    """(per_platform_totals, per_platform_bucket, per_rundate) — all distinct
    REQUESTS, recomputed from the stored item rows rather than read off the
    historical per-run counters, which were row counts."""
    rows = conn.execute("""SELECT s.platform, s.bucket, s.run_date, %s AS k
        FROM source_items s JOIN requests r ON r.id = s.request_id""" % DEDUP_SQL)
    tot, per_bucket, per_day = defaultdict(set), defaultdict(set), defaultdict(set)
    day_bucket = defaultdict(set)
    for plat, bucket, rd, k in rows:
        tot[plat].add(k)
        per_bucket[(plat, bucket)].add(k)
        per_day[(rd, plat)].add(k)
        day_bucket[(rd, bucket)].add(k)
    return ({p: len(v) for p, v in tot.items()},
            {k: len(v) for k, v in per_bucket.items()},
            {k: len(v) for k, v in per_day.items()},
            {k: len(v) for k, v in day_bucket.items()})


def trend_day_number(conn):
    """Days of accumulation we can actually stand behind: distinct run_dates
    CONFIRMED on the remote. Rendered as 'N (+1 pending)' when the current
    run has not been verified yet, never silently as N+1."""
    verified = verified_run_ats()
    rows = conn.execute("SELECT DISTINCT run_date, run_at FROM source_runs").fetchall()
    ok = {rd for rd, ra in rows if ra in verified}
    pending = {rd for rd, ra in rows if ra not in verified} - ok
    return "%d%s" % (len(ok), " (+%d pending verification)" % len(pending)
                     if pending else "")


def render_trend(conn):
    runs = conn.execute("""SELECT run_date, run_at, messages, items, answerable,
        marginal, rejected, new_items, missed_on_arrival
        FROM source_runs ORDER BY run_at""").fetchall()
    items = conn.execute("""SELECT run_date, platform, bucket, reason, category,
        missed_on_arrival, deadline_utc FROM source_items""").fetchall()
    # Round 9: distinct REQUESTS, keyed per platform (see DEDUP_SQL). The
    # previous version keyed everything on the reply address, which is correct
    # for HARO and wrong for SOS.
    distinct_tot, distinct, distinct_day, distinct_day_bucket = distinct_counts(conn)

    tot = Counter(); per_day = defaultdict(Counter); src_day = defaultdict(Counter)
    reasons = Counter(); cats = Counter(); qwoted_day = Counter(); qwoted_ans = Counter()
    for rd, plat, bucket, reason, cat, missed, _dl in items:
        tot[bucket] += 1
        per_day[rd][bucket] += 1
        src_day[rd][plat] += 1
        if bucket == "rejected":
            reasons[(reason or "").split("(")[0].strip()] += 1
            cats[cat or "uncategorised"] += 1
        if plat == "qwoted":
            qwoted_day[rd] += 1
            if bucket == "answerable":
                qwoted_ans[rd] += 1

    days = len(runs)
    first = runs[0][0] if runs else None
    last_ans = conn.execute("""SELECT MAX(run_date) FROM source_items
                               WHERE bucket='answerable'""").fetchone()[0]
    elapsed = 0
    if first:
        elapsed = (_date.fromisoformat(runs[-1][0]) - _date.fromisoformat(first)).days + 1
    since_ans = "never — no answerable item has been seen"
    if last_ans:
        since_ans = "%d day(s) ago (%s)" % (
            (_date.fromisoformat(runs[-1][0]) - _date.fromisoformat(last_ans)).days, last_ans)

    # --- Round 7 §1: a run whose output never reached the remote is not a
    # day of evidence, and must not quietly advance the counter.
    verified = verified_run_ats()
    newest_at = runs[-1][1] if runs else None
    unverified = [r for r in runs if r[1] not in verified]
    stale_unverified = [r for r in unverified if r[1] != newest_at]
    verified_days = len({r[0] for r in runs if r[1] in verified})

    L = ["# Source trend — cumulative", "",
         "Rebuilt on every run of `pipelines/01_source.py`. "
         "**No drafts, no pitches, nothing sent.**", ""]
    if stale_unverified:
        L += ["> ## \u26A0\uFE0F THE COUNTER BELOW IS NOT TRUSTWORTHY", ">",
              "> %d run(s) produced output that was never confirmed on the "
              "remote. A run that could not persist did not happen, as far as "
              "any later session can tell: its container was reclaimed and its "
              "rows went with it." % len(stale_unverified), ">",
              "> " + ", ".join("`%s` (%s)" % (r[1], r[0]) for r in stale_unverified),
              ">",
              "> **Do not read the 14-day window as continuous.** These are "
              "gaps, not quiet days, and the distinction is the entire point "
              "of the measurement. Re-run `verify-push`; if it still fails, "
              "the pipeline is not persisting and nothing downstream of this "
              "line means anything.", ""]
    L += ["> ### \u26A0\uFE0F The series changed meaning at Round 9", ">",
          "> **Every figure dated before 2026-09-18 was a ROW count.** HARO "
          "repeats the same query across its morning, afternoon and evening "
          "editions, so rows overstated opportunities by about a third, and "
          "the earlier Round 8 figures additionally keyed SOS on the "
          "journalist's address — which is the person, not the request, and "
          "cut 58 real SOS requests to 39.", ">",
          "> From Round 9 the headline is **distinct requests**, keyed per "
          "platform, and the whole series below is recomputed from the stored "
          "item rows rather than from the historical per-run counters. Row "
          "counts are still shown beside it; neither is hidden.", "",
          DECISION_CRITERIA, "", "---", "",
         "## Where we are", "", "| | |", "|---|---|",
         "| Runs recorded (locally) | %d |" % days,
         "| Runs CONFIRMED on the remote | %d |" % len([r for r in runs if r[1] in verified]),
         "| **Days of evidence (verified)** | **%s of 14** |" % trend_day_number(conn),
         "| Calendar span of local runs | %d day(s) |" % elapsed,
         "| Digest rows ingested | %d |" % sum(tot.values()),
         "| **Distinct requests** | **%d** |" % sum(distinct_tot.values()),
         "| Answerable (rows) | %d |" % tot["answerable"],
         "| **Answerable (distinct requests)** | **%d** |"
         % sum(n for (_p, b), n in distinct.items() if b == "answerable"),
         "| Marginal (rows) | %d |" % tot["marginal"],
         "| Rejected (rows) | %d |" % tot["rejected"],
         "| Since last answerable | %s |" % since_ans,
         "| Deadline misses on arrival | %d |" % sum(1 for i in items if i[5]),
         ""]

    L += ["## Per run", "",
          "`Persisted` is *confirmed readable out of the commit the remote "
          "points at* — not *`git push` returned without an error*. On "
          "2026-09-14 the second was true and the first was false, and the run "
          "reported success.", "",
          "`Rows` is digest lines; `Distinct` is separate requests, recomputed "
          "per platform. They are shown side by side because collapsing them "
          "into one number is what made the earlier series unreadable.", "",
          "| Run date | run_at (UTC) | Msgs | Rows | Distinct | Ans (rows) | Ans (distinct) | Marginal | Rejected | Missed | Persisted |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for rd, rat, msgs, its, a, mg, rj, nw, miss in runs:
        if rat in verified:
            pstat = "\u2705"
        elif rat == newest_at:
            pstat = "\u23F3 pending"
        else:
            pstat = "\u274C NEVER"
        L.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d | %d | %s |"
                 % (rd, (rat or "—")[:19], msgs, its,
                    sum(n for (d, _p), n in distinct_day.items() if d == rd),
                    a, distinct_day_bucket.get((rd, "answerable"), 0),
                    mg, rj, miss or 0, pstat))
    L.append("")
    L += ["The most recent run reads `pending` by design: verification happens "
          "after the commit exists, so `push-log.json` and this table are "
          "committed one run behind. A run that stays `pending` across the "
          "next run is a run that never persisted.", ""]

    # --- Round 8: per channel, never averaged -----------------------------
    # All four proven links came through HARO and none through SOS or Qwoted.
    # A blended answerable rate hides the only signal that has ever mattered
    # here, so the channels are never summed into one number.
    per_plat = defaultdict(Counter)
    for rd, plat, bucket, _reason, _cat, _missed, _dl in items:
        per_plat[plat][bucket] += 1
        per_plat[plat]["total"] += 1
    plats = sorted(per_plat, key=lambda k: -per_plat[k]["total"])
    L += ["## Answerable rate BY CHANNEL", "",
          "Reported per channel and never blended. All four proven links "
          "(healthline DR91, eatthis DR83, womansworld DR66, singlecare DR63) "
          "came through **HARO**; none came through SOS or Qwoted. An average "
          "across the four would hide the only channel with a track record.", "",
          "`Items` counts digest rows. `Distinct` counts separate requests: "
          "HARO re-runs the same query across its morning, afternoon and "
          "evening editions, so rows overstate opportunities by about a third. "
          "Both are shown rather than picking one and hiding the other.", "",
          "| Channel | Items | Distinct | Answerable | Distinct answerable | Rate (distinct) | Marginal | Rejected | Reply path |",
          "|---|---|---|---|---|---|---|---|---|"]
    reply_path = {"haro": "direct (`reply+…@helpareporter.com`)",
                  "sos": "direct (journalist address in digest)",
                  "qwoted": "manual click-through",
                  "connectively": "manual (magic-link auth redirect)",
                  "featured": "n/a — never sent a digest"}
    for plat in plats:
        c = per_plat[plat]
        dt = distinct_tot.get(plat, c["total"])
        da = distinct.get((plat, "answerable"), c["answerable"])
        rate = (100.0 * da / dt) if dt else 0.0
        L.append("| **%s** | %d | %d | %d | **%d** | %.1f%% | %d | %d | %s |"
                 % (plat, c["total"], dt, c["answerable"], da, rate,
                    c["marginal"], c["rejected"], reply_path.get(plat, "?")))
    L += ["", "### The 14-day clock", "",
          "**Starts %s — the first HARO query digest**, not the first run and "
          "not the signup date. Days before it measured SOS and Qwoted only, "
          "which is two channels that have never produced a link."
          % HARO_CLOCK_START, ""]
    if per_plat["haro"]["total"]:
        elapsed_haro = (_date.fromisoformat(runs[-1][0])
                        - _date.fromisoformat(HARO_CLOCK_START)).days + 1
        L += ["| | |", "|---|---|",
              "| Clock start (first HARO digest) | %s |" % HARO_CLOCK_START,
              "| Day of 14 | **%d** |" % elapsed_haro,
              "| HARO digest rows ingested | %d |" % per_plat["haro"]["total"],
              "| HARO distinct requests | %d |" % distinct_tot.get("haro", 0),
              "| HARO answerable rows | %d |" % per_plat["haro"]["answerable"],
              "| **HARO distinct answerable requests** | **%d** |"
              % distinct.get(("haro", "answerable"), 0), ""]
    else:
        L += ["No HARO items ingested yet — the clock has not started.", ""]

    L += ["## Items per day by source", "",
          "| Run date | SOS | Qwoted | HARO | Connectively | Total |",
          "|---|---|---|---|---|---|"]
    running = 0
    for rd in sorted({r[0] for r in runs}):
        sd = src_day[rd]; running += sum(sd.values())
        L.append("| %s | %d | %d | %d | %d | %d (running %d) |"
                 % (rd, sd.get("sos", 0), sd.get("qwoted", 0), sd.get("haro", 0),
                    sd.get("connectively", 0), sum(sd.values()), running))
    L.append("")

    L += ["## Qwoted — does the free tier bind?", "",
          "Qwoted's free tier allows **7 pitch credits**. That cap only matters "
          "if answerable volume exceeds it. The deciding number is the "
          "answerable column, not the received column.", "",
          "| Run date | Qwoted items received | Of those, answerable |", "|---|---|---|"]
    for rd in sorted({r[0] for r in runs}):
        L.append("| %s | %d | %d |" % (rd, qwoted_day.get(rd, 0), qwoted_ans.get(rd, 0)))
    tot_qa = sum(qwoted_ans.values())
    L += ["", "**Cumulative Qwoted answerable: %d.** %s" % (
        tot_qa,
        "Below the 7-credit cap, so the free tier is not yet the constraint."
        if tot_qa <= 7 else
        "Above the 7-credit cap — the free tier is now the binding constraint "
        "and Qwoted Pro becomes a real question."), ""]

    L += ["## Rejection categories, cumulative", "",
          "This is the dataset that separates *the filter is too tight* from "
          "*the niche is genuinely quiet*. If rejections cluster in topics the "
          "claim bank covers, the filter is wrong. If they are spread across "
          "finance, gift guides and cybersecurity, the niche is quiet.", "",
          "| Category of rejected item | Count |", "|---|---|"]
    for c, n in cats.most_common(15):
        L.append("| %s | %d |" % (c, n))
    L += ["", "| Rejection reason | Count |", "|---|---|"]
    for r, n in reasons.most_common(10):
        L.append("| %s | %d |" % (r, n))
    L.append("")

    os.makedirs(os.path.dirname(TREND), exist_ok=True)
    with open(TREND, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


# --------------------------------------------------------------------------
def cmd_run(a):
    run_date = a.date or _date.today().isoformat()
    stage = "preflight"
    try:
        return _run_inner(a, run_date)
    except Exception as e:                       # noqa: BLE001 - must catch all
        path = emit_failure_alert(stage, e, run_date)
        print("\n*** RUN FAILED — %s ***" % e, file=sys.stderr)
        # Telling someone to post to Slack when the reason the run failed IS
        # that Slack is unreachable would leave the failure silent, which is
        # the one outcome this round exists to prevent.
        print(delivery_instruction(path), file=sys.stderr)
        return 4


def _run_inner(a, run_date):
    preflight()                      # includes the connector probe (§2)
    # a successful run clears any previous failure alert
    for stale in (FAIL_ALERT, FAIL_ALERT + ".slack.txt"):
        if os.path.exists(stale):
            os.remove(stale)
    # relay.resolve raises on missing / truncated / stale / malformed files.
    # There is deliberately no fallback to an empty payload.
    payload = relay.resolve(a.payload)
    labels = a.labels.split(",") if a.labels else list(EXPECTED_LABELS)
    run_at = datetime.now(timezone.utc)
    print(relay.describe(payload))
    rows, skipped, unparsed = ingest(payload, a.connection_id, labels,
                                     run_date, run_at)

    conn = connect()
    first_today = is_first_run_of_day(conn, run_date)      # ask BEFORE insert
    new = persist(conn, rows, run_date)
    counts = Counter(r["bucket"] for r in rows)
    missed = sum(1 for r in rows if r.get("missed_on_arrival"))
    conn.execute("INSERT OR REPLACE INTO source_runs VALUES (?,?,?,?,?,?,?,?,?)",
                 (run_at.isoformat(timespec="seconds"), run_date,
                  len(payload.get("results") or []), len(rows),
                  counts["answerable"], counts["marginal"], counts["rejected"],
                  new, missed))
    conn.commit()
    conn.row_factory = sqlite3.Row
    n_items, n_runs = export_state(conn)
    conn.row_factory = None
    render_report(conn, rows, skipped, run_date, len(payload.get("results") or []),
                  unparsed)
    render_trend(conn)

    _topics, bank = load_claim_topics()
    approved = approved_experts(load_experts(), bank)
    alert_path, immediate, provisional = emit_alert(
        rows, run_date, run_at.isoformat(timespec="seconds"), approved)

    # --force-heartbeat exists for the day the heartbeat itself is added or
    # recovered: "first run of the day" is the right rule and would otherwise
    # make the first heartbeat wait until tomorrow. It never suppresses one.
    hb_path = None
    if first_today or getattr(a, "force_heartbeat", False):
        hb_path = emit_heartbeat(rows, counts, run_date, provisional, unparsed,
                                 day_n=trend_day_number(conn))

    print("messages %d | items %d | answerable %d | marginal %d | rejected %d"
          % (len(payload.get("results") or []), len(rows),
             counts["answerable"], counts["marginal"], counts["rejected"]))
    print("new rows inserted: %d (re-run inserts 0)" % new)
    print("deadline misses on arrival: %d" % missed)
    if unparsed:
        print("INGESTED BUT UNPARSED: %s — no parser written; contents NOT filtered"
              % dict(unparsed))
    print("report: %s" % os.path.relpath(REPORT, ROOT))
    print("trend:  %s" % os.path.relpath(TREND, ROOT))
    print("state:  %s (%d items, %d runs) — commit this"
          % (os.path.relpath(STATE, ROOT), n_items, n_runs))
    if alert_path:
        print("\n*** ALERT: %d ANSWERABLE ITEM(S), APPROVED EXPERT — %s ***"
              % (len(immediate), os.path.relpath(alert_path, ROOT)))
        print("*** POST TO SLACK #media (%s) — body in %s.slack.txt ***"
              % (SLACK_ALERT_CHANNEL, os.path.relpath(alert_path, ROOT)))
    else:
        print("alert:  none (%d answerable, %d of them provisional and held)"
              % (counts["answerable"], len(provisional)))
    if hb_path:
        print("*** HEARTBEAT (first run today) — POST %s TO SLACK #media (%s) ***"
              % (os.path.relpath(hb_path, ROOT), SLACK_ALERT_CHANNEL))
    else:
        print("heartbeat: already sent today, not repeating")
    conn.close()
    # §1. The run is NOT finished here. Commit, push, then:
    #     01_source.py verify-push
    # Until that passes, this run has produced nothing durable and the trend
    # report says so.
    print("\nNEXT: commit + push, then `01_source.py verify-push`. "
          "An unverified run is not counted.")
    return 0


# --------------------------------------------------------------------------
# Round 12 — the drafter
# --------------------------------------------------------------------------
DRAFT_QUEUE = os.path.join(ROOT, "reports", "draft-queue.md")
# Machine-readable twin of the queue, so `sent` can look up an item's
# outlet/regime/platform without the human retyping them.
DRAFT_QUEUE_STATE = os.path.join(DATA, "draft-queue-state.json")
CORPUS_CLASSIFICATION = os.path.join(DATA, "haro-corpus-classification.json")


def _reachable_items(conn):
    """Reachable corpus rows, joined to what the pipeline stored about them."""
    with open(CORPUS_CLASSIFICATION, encoding="utf-8") as fh:
        rows = json.load(fh)
    reach = [r for r in rows if r.get("reachable")]
    conn.row_factory = sqlite3.Row
    live = {}
    for r in conn.execute("""SELECT s.journalist_email k, s.source_key, s.platform,
            s.requires_manual, s.deadline_utc, r.deadline, r.outlet, r.query_text
            FROM source_items s JOIN requests r ON r.id=s.request_id
            WHERE s.platform='haro'"""):
        live.setdefault(r["k"], dict(r))
    conn.row_factory = None
    out = []
    for r in reach:
        extra = live.get(r.get("k")) or {}
        out.append({**r, **{k: v for k, v in extra.items() if v is not None}})
    return out


def cmd_draft(a):
    """Build the review queue across all three regimes. Sends nothing."""
    preflight(require_connectors=False)
    _topics, bank = load_claim_topics()
    experts = load_experts()
    experience = drafter.load_experience(os.path.join(DATA, "experience.json"))
    cits = json.load(open(os.path.join(DATA, "draft-citations.json"),
                          encoding="utf-8"))["citations"]
    authored = {d["item_key"]: d for d in json.load(
        open(os.path.join(DATA, "drafts.json"), encoding="utf-8"))["drafts"]}

    conn = connect()
    conn.row_factory = sqlite3.Row
    seen, items = set(), []
    for r in conn.execute("""SELECT s.journalist_email k, s.source_key, s.platform,
            s.requires_manual, s.deadline_utc, s.respond_url,
            r.outlet, r.deadline, r.query_text
            FROM source_items s JOIN requests r ON r.id=s.request_id"""):
        key = r["k"] or r["source_key"]
        if key in seen:
            continue
        seen.add(key)
        items.append(dict(r, key=key))
    conn.close()

    # Round 14. A sent item leaves the queue and is never re-surfaced. This
    # is the drop, and it happens BEFORE assessment so a sent item cannot be
    # re-drafted, re-alerted or re-counted.
    sent_keys = {s["key"] for s in outcomes.load(SENDS)["sends"]}
    dropped = [it for it in items if it["key"] in sent_keys]
    items = [it for it in items if it["key"] not in sent_keys]

    recs = []
    for it in items:
        rec = _assess(it, bank, experts, experience, cits, authored)
        recs.append(rec)
    drafted = [r for r in recs if r["draft"]]
    for r in drafted:
        assert_pitchable(mark_pitchable(
            {"source_key": r["key"], "pitch_text": r["draft"]}, r["framing"],
            requires_expert_review=r["requires_expert_review"]))

    render_draft_queue_v2(recs)
    # The machine-readable twin, so `sent` can resolve an item's outlet,
    # regime and platform without the human retyping any of it.
    with open(DRAFT_QUEUE_STATE, "w", encoding="utf-8") as fh:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "records": [{k: v for k, v in r.items() if k != "draft"}
                               for r in recs]}, fh, indent=1)
    per = Counter(r["regime"] for r in drafted)
    if dropped:
        print("already sent, dropped from the queue: %d" % len(dropped))
    print("corpus distinct requests : %d" % len(recs))
    print("DRAFTED                  : %d" % len(drafted))
    for reg in drafter.REGIMES:
        print("   %-18s     : %d" % (reg, per.get(reg, 0)))
    print("requires_expert_review   : %d" % sum(1 for r in drafted if r["requires_expert_review"]))
    print("at risk of expiring (<24h): %d" % sum(1 for r in drafted if r["at_risk"]))
    print("not_a_query              : %d" % sum(1 for r in recs if r["not_a_query"]))
    print("\nNOTHING WAS SENT.")
    return 0


def _hours_left(deadline_utc, now=None):
    if not deadline_utc:
        return None
    now = now or datetime.now(timezone.utc)
    return (datetime.fromisoformat(deadline_utc) - now).total_seconds() / 3600.0


def _assess(it, bank, experts, experience, cits, authored):
    """One corpus item -> one queue record. Regime precedence lives here."""
    text = it.get("query_text") or ""
    hrs = _hours_left(it.get("deadline_utc"))
    rec = {"key": it["key"], "outlet": it.get("outlet"), "platform": it.get("platform"),
           "deadline": it.get("deadline"), "deadline_utc": it.get("deadline_utc"),
           "hours_left": hrs, "expired": hrs is not None and hrs <= 0,
           "reply_path": it.get("k"), "requires_manual": bool(it.get("requires_manual")),
           "regime": None, "framing": None, "draft": None,
           "source_claim_ids": [], "source_experience_topics": [],
           "source_citation_ids": [], "requires_expert_review": False,
           "at_risk": False, "not_a_query": False, "needs_expert_input": False,
           "requirement_mismatch": False, "reason": ""}

    ok, why = drafter.classify_query(text)
    if not ok:
        rec["not_a_query"] = True; rec["reason"] = why
        return rec

    # Precedence: claim bank -> experience -> verified_at_draft.
    claim_ids = drafter.covering_claims(text, bank, MODALITY_TERMS, OUTCOME_TERMS)
    if claim_ids:
        rec.update(regime="claim_bank", framing="published-evidence",
                   source_claim_ids=claim_ids)
    else:
        topics = drafter.experience_topics_for(text, experience)
        if topics and not drafter.needs_citation(text):
            rec.update(regime="experience", framing="clinical-experience",
                       source_experience_topics=topics)
        else:
            rec.update(regime="verified_at_draft", framing="verified-guideline",
                       source_experience_topics=topics)

    d = authored.get(it["key"])
    if not d:
        rec["needs_expert_input"] = True
        rec["reason"] = ("no draft authored for this item. Under the "
                         "verified-at-draft regime every factual assertion "
                         "needs a citation retrieved and resolved at draft "
                         "time; none has been for this one."
                         if rec["regime"] == "verified_at_draft" else
                         "no approved source covers this item.")
        return rec

    drafter.assert_assertions_verified(d["assertions"], cits)
    body = " ".join(x for x in (d.get("opening"),
                                drafter.render_verified_body(d["assertions"], cits),
                                d.get("experience_tail")) if x)
    rec["draft"] = drafter.assemble(body, experts["alptunaer"]["credential_line"])
    rec["regime"] = d["regime"]; rec["framing"] = d["framing"]
    rec["source_citation_ids"] = sorted({i for x in d["assertions"]
                                         for i in x["citation_ids"]})
    rec["source_experience_topics"] = d.get("experience_topics") or []
    rec["requirement_mismatch"] = bool(d.get("requirement_mismatch"))
    # The slow step is HIS review, not ours. Every verified-at-draft item
    # needs it and cannot be marked ready-to-send without it.
    rec["requires_expert_review"] = d["regime"] == "verified_at_draft"
    rec["at_risk"] = bool(rec["requires_expert_review"] and hrs is not None
                          and 0 < hrs < 24)
    return rec


def render_draft_queue_v2(recs):
    drafted = [r for r in recs if r["draft"]]
    mism = [r for r in drafted if r["requirement_mismatch"]]
    review = sorted([r for r in drafted if r["requires_expert_review"]
                     and not r["requirement_mismatch"]],
                    key=lambda r: r["hours_left"] if r["hours_left"] is not None else 1e9)
    ready = [r for r in drafted if not r["requires_expert_review"]
             and not r["requirement_mismatch"]]
    at_risk = [r for r in drafted if r["at_risk"]]

    L = ["# Draft queue", "", "Round 13 · %d distinct requests · **%d drafts**"
         % (len(recs), len(drafted)), "",
         "**Nothing here has been sent.**", "",
         "| | |", "|---|---|",
         "| Drafts | %d |" % len(drafted),
         "| — requirement mismatch | %d |" % len(mism),
         "| — awaiting HIS review | %d |" % len(review),
         "| — ready for Julian | %d |" % len(ready),
         "| **At risk of expiring (<24h, needs his review)** | **%d** |" % len(at_risk),
         "| not_a_query | %d |" % sum(1 for r in recs if r["not_a_query"]), ""]

    def block(r):
        out = ["### %s — `%s`" % (r["outlet"] or "?", r["regime"]), ""]
        if r["requirement_mismatch"]:
            out += ["> ⚠️ **Requirement mismatch.** The journalist asked "
                    "for a profession he does not hold. The credential line is "
                    "correct either way; the human decides whether to send.", ""]
        hrs = r["hours_left"]
        out += ["| | |", "|---|---|",
                "| Deadline | %s |" % (r["deadline"] or "not stated"),
                "| Hours left | %s |" % ("expired" if r["expired"] else
                                         ("%.0f" % hrs if hrs is not None else "unknown")),
                "| Reply path | %s |" % ("`%s` (read from the mail)" % r["reply_path"]
                                         if r["reply_path"] else
                                         "**manual** — copy-paste in-platform, no reply path"),
                "| Regime | `%s` |" % r["regime"],
                "| Framing | `%s` |" % r["framing"],
                "| Citations (verified at draft time) | %s |"
                % (", ".join("`%s`" % c for c in r["source_citation_ids"]) or "—"),
                "| Claim ids | %s |" % (", ".join(r["source_claim_ids"]) or "—"),
                "| Experience topics | %s |" % (", ".join(r["source_experience_topics"]) or "—"),
                "| Expert review required | %s |" % ("**YES**" if r["requires_expert_review"] else "no"),
                "", "```", r["draft"], "```", ""]
        return out

    if mism:
        L += ["---", "", "## 1 · Requirement mismatches", ""]
        for r in mism: L += block(r)
    L += ["---", "", "## 2 · Awaiting Dr. Alptunaer's review — soonest deadline first", ""]
    if at_risk:
        L += ["> 🔴 **%d draft(s) expire within 24 hours.** Expert review "
              "is the slow step, so these are the ones the regime puts at risk."
              % len(at_risk), ""]
    for r in review: L += block(r)
    if not review: L += ["_None._", ""]
    L += ["---", "", "## 3 · Ready for Julian's review", ""]
    for r in ready: L += block(r)
    if not ready: L += ["_None. No live item is covered by the claim bank or "
                        "answerable from the experience set alone._", ""]
    os.makedirs(os.path.dirname(DRAFT_QUEUE), exist_ok=True)
    with open(DRAFT_QUEUE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return DRAFT_QUEUE



# --------------------------------------------------------------------------
# Round 14 — close the loop
# --------------------------------------------------------------------------
# THE MECHANISM IS A CLI COMMAND WRITING A COMMITTED FILE, and the choice is
# deliberate. `data/sends.json` is the durable record — tracked, diffable,
# survives a reclaimed container — but a human hand-editing JSON at speed
# introduces a trailing comma at exactly the moment they are busiest, and a
# corrupt sends file loses the only copy of what went out. So the file is the
# store and `sent` / `outcome` are the doors: they validate, they are
# idempotent on the item key, and the file stays readable if anyone does want
# to correct it by hand.
SENDS = os.path.join(DATA, "sends.json")
OUTCOMES_REPORT = os.path.join(ROOT, "reports", "outcomes.md")


def cmd_sent(a):
    """Record that a HUMAN sent a pitch. The pipeline never sends."""
    doc = outcomes.load(SENDS)
    meta = {}
    if os.path.exists(DRAFT_QUEUE_STATE):
        with open(DRAFT_QUEUE_STATE, encoding="utf-8") as fh:
            meta = {r["key"]: r for r in json.load(fh).get("records", [])}
    m = meta.get(a.key, {})
    rec, created = outcomes.record_send(
        doc, a.key, a.sent_from, a.at, outlet=m.get("outlet"),
        regime=m.get("regime"), platform=m.get("platform"), note=a.note)
    outcomes.save(doc, SENDS)
    print("%s: %s" % ("recorded" if created else "updated", rec["key"]))
    print("  outlet   : %s" % (rec["outlet"] or "(unknown — not in the queue)"))
    print("  regime   : %s" % (rec["regime"] or "unknown"))
    print("  sent from: %s" % rec["sent_from"])
    print("  sent at  : %s" % rec["sent_at"])
    print("  status   : %s (a pitch nobody answered stays pending)" % rec["status"])
    print("\nIt will not appear in the draft queue again.")
    print("Commit %s." % os.path.relpath(SENDS, ROOT))
    return 0


def cmd_outcome(a):
    """Record a published URL a human saw. The LINK is still read off the page."""
    doc = outcomes.load(SENDS)
    rec = outcomes.record_published_url(doc, a.key, a.url, a.at)
    outcomes.check_one(rec)
    outcomes.save(doc, SENDS)
    print("published: %s" % rec["published_url"])
    print("  linked : %s" % rec.get("linked"))
    print("  rel    : %s" % (rec.get("rel") or "(none)"))
    print("  note   : %s" % rec.get("check_note"))
    return 0


def cmd_outcomes(a):
    """WEEKLY. Re-check every recorded published URL for the link and its rel.

    NOTE ON CADENCE: there was no weekly verify job in `linkbuilding` before
    this round — `00_audit` exists but nothing schedules it. This command is
    the weekly job; it is not yet attached to a Routine, and that is an open
    item rather than something quietly assumed to be running.
    """
    doc = outcomes.load(SENDS)
    if not doc["sends"]:
        print("no sends recorded yet — nothing to check.")
        render_outcomes(doc)
        return 0
    conn = connect(); conn.row_factory = sqlite3.Row
    audit_rows = [dict(r) for r in conn.execute("SELECT * FROM audit_links")]
    conn.close()
    for rec in doc["sends"]:
        outcomes.check_one(rec)
        # Second route to the same fact. Where this environment cannot reach a
        # publisher page, the backlink audit still can — it only ever upgrades
        # a record, so a working page fetch is never overwritten by it.
        if not rec.get("linked"):
            outcomes.check_via_backlink_audit(rec, audit_rows)
        print("%-44s %-10s %s" % (rec["key"][:44], rec["status"],
                                  rec.get("check_note") or ""))
    outcomes.save(doc, SENDS)
    render_outcomes(doc)
    print("\nreport: %s" % os.path.relpath(OUTCOMES_REPORT, ROOT))
    return 0


def render_outcomes(doc):
    s = outcomes.summarise(doc)
    times = sorted(s["times"])
    med = times[len(times) // 2] if times else None
    L = ["# Outcomes — sent, published, linked", "",
         "**This replaces answerable-rate as the headline.** Answerable was "
         "always a proxy for this: a guess about what a journalist might use. "
         "These are what they did.", "",
         "Generated %s" % datetime.now(timezone.utc).isoformat(timespec="seconds"), "",
         "| | |", "|---|---|",
         "| Pitches sent (by a human) | **%d** |" % s["sent"],
         "| Published | **%d** |" % s["published"],
         "| Pending | %d |" % s["pending"],
         "| Carrying a link to inhousewellness.com | **%d** |" % s["linked"],
         "| — follow | %d |" % s["follow"],
         "| — nofollow | %d |" % s["nofollow"],
         "| Median send → publication | %s |"
         % ("%.0f hours" % med if med is not None else "no publication timed yet"), ""]
    if s["pending"]:
        L += ["> **`pending` is not a failure and is never counted as one.** "
              "A pitch nobody answered stays pending indefinitely. Publication "
              "is never inferred from silence, so no rate below treats these "
              "as rejections — the denominator for a publication rate is "
              "*confirmed outcomes*, not *sends*.", ""]
    if not s["sent"]:
        L += ["## Nothing sent yet", "",
              "No pitch has been recorded as sent, so every number above is "
              "zero by absence rather than by result. The first `01_source.py "
              "sent` call starts the series.", ""]
    for dim, title in (("per_regime", "By regime"), ("per_platform", "By platform")):
        L += ["## %s" % title, "", "| %s | Sent | Published | Linked | Pending |"
              % title.split()[-1].title(), "|---|---|---|---|---|"]
        for k, v in sorted(s[dim].items()):
            L.append("| `%s` | %d | %d | %d | %d |"
                     % (k, v["sent"], v["published"], v["linked"], v["pending"]))
        if not s[dim]:
            L.append("| _none_ | 0 | 0 | 0 | 0 |")
        L.append("")
    L += ["## The record", "",
          "| Item | Outlet | Sent | From | Status | Link | rel |",
          "|---|---|---|---|---|---|---|"]
    for r in doc["sends"]:
        L.append("| `%s` | %s | %s | %s | %s | %s | %s |"
                 % (r["key"][:34], r.get("outlet") or "?", (r.get("sent_at") or "")[:16],
                    r.get("sent_from") or "?", r["status"],
                    "yes" if r.get("linked") else ("no" if r.get("linked") is False else "—"),
                    r.get("rel") or "—"))
    if not doc["sends"]:
        L.append("| _no sends recorded_ | | | | | | |")
    L += ["", "## Cadence", "",
          "`01_source.py outcomes` is the weekly check. **It is not attached "
          "to a Routine yet** — `linkbuilding` had no weekly verify job before "
          "this round, so this one is defined rather than inherited. Until it "
          "is scheduled or run by hand, `last_checked` is the honest record of "
          "when anything was actually looked at.", ""]
    os.makedirs(os.path.dirname(OUTCOMES_REPORT), exist_ok=True)
    with open(OUTCOMES_REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return OUTCOMES_REPORT


# --------------------------------------------------------------------------
# Post every new draft to #media, in full
# --------------------------------------------------------------------------
# The draft text itself goes to Slack, not a link to the file. A link means
# opening a repo to copy a paragraph, and the person doing that is usually on
# a phone with a four-hour deadline. Slack is where the copy-paste happens, so
# the copy lives in Slack.
#
# Posting is deduped on ITEM KEY and recorded in a committed file. A draft is
# posted exactly once: re-posting the same pitch every time the queue
# regenerates is how a channel becomes noise, and this one already has a
# standing rule about that.
POSTED = os.path.join(DATA, "posted-drafts.json")


def load_posted():
    if not os.path.exists(POSTED):
        return {"_comment": "Item keys already posted to #media, so a draft is "
                            "never posted twice. Dedupe is on the item key, "
                            "which is stable across queue regenerations.",
                "posted": {}}
    with open(POSTED, encoding="utf-8") as fh:
        return json.load(fh)


def record_posted(key, ts=None, link=None):
    doc = load_posted()
    doc["posted"][key] = {"posted_at": datetime.now(timezone.utc)
                          .isoformat(timespec="seconds"),
                          "message_ts": ts, "message_link": link}
    with open(POSTED, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
    return doc


_TOKEN_RE = re.compile(r"(token=)[A-Za-z0-9_\-]+", re.I)
_URL_IN_FIELD_RE = re.compile(r"https?://\S+")


def _scrub(value):
    """Never put a credential in a channel.

    Connectively's deadline line carries a single-use magic-link token, and it
    reached this renderer through the parser. That is fixed at the source, but
    the scrub stays: a Slack post is public to everyone in the channel and
    forever, and defence in depth costs one regex.
    """
    v = _TOKEN_RE.sub(r"\1<REDACTED>", str(value or ""))
    return " ".join(_URL_IN_FIELD_RE.sub("", v).split())


def slack_draft_body(rec, cits):
    """One draft, in full, formatted to be copied straight out of Slack."""
    by_id = {c["id"]: c for c in cits}
    hrs = rec.get("hours_left")
    when = ("**EXPIRED**" if rec.get("expired") else
            "%.0f hours left" % hrs if hrs is not None else "no deadline stated")
    reply = (rec["reply_path"] if rec.get("reply_path")
             else "submit via Connectively — no reply address")
    lines = [":memo: *New draft — %s*" % (rec.get("outlet") or "(no outlet)"), ""]
    if rec.get("requirement_mismatch"):
        lines += [":warning: *Requirement mismatch.* The journalist asked for a "
                  "profession he does not hold. The credential line is correct "
                  "either way — you decide whether to send.", ""]
    lines += ["*Outlet:* %s" % (rec.get("outlet") or "?"),
              "*Deadline:* %s  (%s)" % (_scrub(rec.get("deadline")) or "not stated", when),
              "*Platform:* `%s`" % (rec.get("platform") or "?"),
              "*Reply path:* %s" % reply,
              "*Regime:* `%s`  ·  *Framing:* `%s`" % (rec.get("regime"), rec.get("framing")),
              "*Requires Dr. Alptunaer's review:* %s"
              % ("*YES* — do not send before he has seen it"
                 if rec.get("requires_expert_review") else "no"), ""]
    if rec.get("source_citation_ids"):
        lines.append("*Citations (verified at draft time):*")
        for cid in rec["source_citation_ids"]:
            c = by_id.get(cid, {})
            ident = ("PMID %s" % c["pmid"] if c.get("pmid")
                     else "doi:%s" % c.get("doi"))
            lines.append("• %s — %s _(%s)_" % (ident, c.get("title", cid),
                                               c.get("source_type", "?")))
        lines.append("")
    if rec.get("source_claim_ids"):
        lines += ["*Claim ids:* %s" % ", ".join("`%s`" % c for c in rec["source_claim_ids"]), ""]
    if rec.get("source_experience_topics"):
        lines += ["*Experience topics:* %s" % ", ".join(rec["source_experience_topics"]), ""]
    lines += ["*The draft — copy from here:*", "```", rec["draft"], "```", "",
              "_Item key_ `%s`" % rec["key"]]
    return "\n".join(lines)


def cmd_post_drafts(a):
    """Emit the Slack body for every draft not yet posted. Dedupes on key.

    Slack is an MCP tool and MCP exists only inside an agent session, so this
    writes the bodies and the session posts them — the same relay the alerting
    path already uses.
    """
    if not os.path.exists(DRAFT_QUEUE_STATE):
        raise SourceError("no queue state; run `01_source.py draft` first")
    with open(DRAFT_QUEUE_STATE, encoding="utf-8") as fh:
        recs = json.load(fh)["records"]
    with open(os.path.join(DATA, "drafts.json"), encoding="utf-8") as fh:
        bodies = {d["item_key"]: d for d in json.load(fh)["drafts"]}
    cits = json.load(open(os.path.join(DATA, "draft-citations.json"),
                          encoding="utf-8"))["citations"]
    experts = load_experts()
    already = set(load_posted()["posted"])

    pending = []
    for r in recs:
        d = bodies.get(r["key"])
        if not d or r["key"] in already:
            continue
        body = " ".join(x for x in (d.get("opening"),
                        drafter.render_verified_body(d["assertions"], cits),
                        d.get("experience_tail")) if x)
        r = dict(r, draft=drafter.assemble(
            body, experts["alptunaer"]["credential_line"]))
        pending.append(r)

    outdir = os.path.join(ROOT, "reports", "draft-posts")
    os.makedirs(outdir, exist_ok=True)
    for r in pending:
        safe = re.sub(r"[^A-Za-z0-9]+", "-", r["key"])[:60]
        path = os.path.join(outdir, "%s.slack.txt" % safe)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(slack_draft_body(r, cits) + "\n")
        print("PENDING  %-28s %s" % ((r.get("outlet") or "?")[:28],
                                     os.path.relpath(path, ROOT)))
    print("\n%d draft(s) already posted, %d pending" % (len(already), len(pending)))
    if pending:
        print("Post each body to Slack #media (%s), then record it:" % SLACK_ALERT_CHANNEL)
        print("  01_source.py posted --key <item key> --ts <message_ts> --link <url>")
    return 0


def cmd_posted(a):
    """Record that a draft was posted, so it is never posted again."""
    record_posted(a.key, a.ts, a.link)
    print("recorded as posted: %s" % a.key)
    print("Commit %s." % os.path.relpath(POSTED, ROOT))
    return 0


def cmd_rescore(a):
    """Re-classify every already-ingested item in place. No new ingestion.

    `persist` only inserts rows whose source_key is new, which is what makes
    re-runs idempotent — but it also means a change to the filter or the
    expert roster never reaches rows already stored. This does.
    """
    preflight(require_connectors=False)   # reads no mailbox, posts nothing
    claim_topics, _ = load_claim_topics()
    experts = load_experts()
    conn = connect()
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        """SELECT s.source_key, s.platform, s.bucket, s.matched_expert,
                  s.category, r.outlet, r.query_text, r.id AS rid
           FROM source_items s JOIN requests r ON r.id = s.request_id""")]
    before = Counter((r["bucket"], r["matched_expert"]) for r in rows)

    updated, changed = [], 0
    for r in rows:
        item = {"summary": r["outlet"], "headline": r["outlet"],
                "query": r["query_text"], "category": r["category"],
                "outlet": r["outlet"]}
        bucket, terms, reason, who = classify(item, claim_topics, experts)
        updated.append({"source_key": r["source_key"], "matched_terms": terms,
                        "matched_expert": who})
        if (bucket, who) != (r["bucket"], r["matched_expert"]):
            changed += 1
        conn.execute("""UPDATE source_items SET bucket=?, reason=?,
                        matched_terms=?, matched_expert=? WHERE source_key=?""",
                     (bucket, reason, json.dumps(terms), who, r["source_key"]))
        conn.execute("UPDATE requests SET topic_match=?, status=? WHERE id=?",
                     (json.dumps(terms),
                      "filtered_out" if bucket == "rejected" else "new", r["rid"]))
    assert_clinical_attribution(updated)      # HARD RULE, raises
    conn.commit()

    after = Counter()
    for b, w in conn.execute("SELECT bucket, matched_expert FROM source_items"):
        after[(b, w)] += 1
    export_state(conn)
    conn.row_factory = None
    render_trend(conn)
    print("re-scored %d items; %d changed bucket or expert" % (len(rows), changed))
    print("\nper expert:")
    for who in ("alptunaer", "tripler", None):
        label = who or "(neither)"
        a = after.get(("answerable", who), 0)
        m = after.get(("marginal", who), 0)
        j = after.get(("rejected", who), 0)
        print("  %-12s answerable %-3d marginal %-3d rejected %-3d" % (label, a, m, j))
    tot = Counter(b for b, _ in after.elements())
    print("\ncombined: answerable %d | marginal %d | rejected %d"
          % (tot["answerable"], tot["marginal"], tot["rejected"]))
    conn.close()
    return 0


def cmd_test_samples(_a):
    ok = True
    for name in ("sos-2026-09-15-morning.txt", "sos-2026-09-15-afternoon.txt"):
        raw = open(os.path.join(SAMPLES, name), encoding="utf-8").read()
        body = raw.split("----- BODY (text/plain) -----")[1] \
                  .split("----- BODY (text/html) -----")[0]
        items = sos_parser.parse(body, source_id=name)
        cov = sos_parser.field_coverage(items)
        n = len(items)
        labels_ok = all(v == n for v in cov["label"].values())
        sparse = {k: v for k, v in cov["value"].items() if v != n}
        print("%-34s items=%d  all ten field LABELS on every item: %s"
              % (name, n, labels_ok))
        if sparse:
            print("   labels present but value blank on some items: %s"
                  % {k: "%d/%d" % (v, n) for k, v in sparse.items()})
        if n != 9:
            print("   STOP CONDITION: expected 9 items, got %d" % n); ok = False
        if not labels_ok:
            print("   STOP: missing LABELS: %s"
                  % {k: v for k, v in cov["label"].items() if v != n}); ok = False
    for name in ("qwoted-request-2026-09-15-vice.txt",):
        raw = open(os.path.join(SAMPLES, name), encoding="utf-8").read()
        body = raw.split("----- BODY (text/plain) -----")[1] \
                  .split("----- BODY (text/html) -----")[0]
        it = qwoted_parser.parse(body, source_id=name)
        print("%-34s outlet=%r tags=%s manual=%s"
              % (name, it["outlet"], it["followed_tags"], it["requires_manual"]))
        if not it["requires_manual"]:
            print("   FAIL: requires_manual not set"); ok = False
    return 0 if ok else 1


def cmd_self_test(_a):
    fails = []

    def check(n, c):
        print("  %s %s" % ("PASS" if c else "FAIL", n))
        if not c:
            fails.append(n)

    def raises(fn):
        try:
            fn(); return False
        except (SourceError, sos_parser.SosParseError,
                qwoted_parser.QwotedParseError, haro_parser.HaroParseError,
                cx_parser.ConnectivelyParseError, claims_lib.ClaimBankError,
                drafter.DraftError, outcomes.OutcomeError):
            return True

    good = {"id": "m1", "from": {"email": "peter@sourceofsources.com"},
            "raw": {"payload": {"headers": {"Delivered-To": "media@inhousewellness.com"}}}}
    wrong = {"id": "m2", "from": {"email": "x@y.com"},
             "raw": {"payload": {"headers": {"Delivered-To": "support@inhousewellness.com"}}}}

    print("Rule 1 — connection pinned")
    check("correct id accepted", assert_connection(EXPECTED_CONNECTION_ID))
    check("support@ default id rejected", raises(lambda: assert_connection("02db007d-ef2f-8770-8175-3537c461ff4c")))
    check("omitted id rejected", raises(lambda: assert_connection(None)))

    print("Rule 2 — Delivered-To asserted on the response")
    check("correct mailbox accepted", assert_delivered_to([good]))
    check("wrong mailbox raises", raises(lambda: assert_delivered_to([wrong])))
    check("absent header raises", raises(lambda: assert_delivered_to([{"id": "m3", "raw": {}}])))

    print("Rule 3 — zero rows raises")
    check("zero rows raises", raises(lambda: assert_non_empty([], "label:Media/Qwoted")))
    check("rows pass", assert_non_empty([good], "x"))

    print("Rule 4 — bare Media parent in scope")
    check("full scope accepted", assert_label_scope(list(EXPECTED_LABELS)))
    check("missing bare Media raises", raises(lambda: assert_label_scope(["Media/Qwoted", "Media/HARO"])))

    print("Rule 5 — routing by sender, never subject")
    subj_trap = {"id": "m4", "from": {"email": "peter@sourceofsources.com"},
                 "subject": "[Qwoted] totally misleading subject"}
    check("sender wins over misleading subject", route(subj_trap) == "sos")
    check("subject-only match impossible",
          route({"id": "m5", "from": {"email": "nobody@example.com"},
                 "subject": "[SOS] Tuesday Morning Media Queries"}) == "unknown")
    check("varied SOS subject still routes", route(good) == "sos")
    # Inspect the COMPILED function, not its source text: the docstring
    # legitimately contains the word "subject", and a text scan would flag it.
    # co_consts holds the string literals the body actually uses for lookups.
    consts = tuple(c for c in route.__code__.co_consts if isinstance(c, str))
    check("route() never looks up 'subject'",
          "subject" not in consts and "subject" not in route.__code__.co_names)

    print("Rule 6 — IMPORTANT excluded from SOS fields")
    digest = ("*** INDEX ***\n1) Thing (#item0)\n****\n"
              "1) SUMMARY: Thing\nCATEGORY: General\nNAME: A B\nEMAIL: a@b.com\n"
              "MUCK RACK URL: https://muckrack.com/a\nMEDIA OUTLET: Outlet\n"
              "MEDIA WEBSITE: https://o.com\nDEADLINE DATE: 2026-09-20\n"
              "DEADLINE TIME: 5:00 pm\nTIME ZONE: PST\n"
              "IMPORTANT: house notice that must not become a field\n"
              "QUERY: the actual query text\n")
    items = sos_parser.parse(digest, "t")
    check("one item parsed", len(items) == 1)
    check("IMPORTANT not captured as a field", "important" not in items[0])
    check("ten real fields captured", all(
        items[0].get(f.lower().replace(" ", "_")) for f in sos_parser.FIELDS))

    print("filter + two-expert roster")
    topics = ["heat", "cold"]
    b1 = classify({"summary": "Seeking experts on infrared sauna and blood pressure"}, topics)
    b2 = classify({"summary": "Wellness experts to discuss October Theory"}, topics)
    b3 = classify({"summary": "Looking for mortgage experts on HELOCs",
                   "category": "Business and Finance"}, topics)
    b4 = classify({"summary": "Seeking founders on hiring and retention at small business"}, topics)
    b5 = classify({"summary": "Experts on habit formation and behaviour change"}, topics)
    b6 = classify({"summary": "The toll the holiday season takes on pet industry employees"}, topics)
    check("modality+outcome -> answerable/alptunaer",
          b1[0] == "answerable" and b1[3] == "alptunaer")
    check("wellness w/o modality -> marginal", b2[0] == "marginal")
    check("off-topic -> rejected", b3[0] == "rejected")
    check("rejected has no expert", b3[3] is None)
    check("business ops -> answerable/tripler",
          b4[0] == "answerable" and b4[3] == "tripler")
    check("named coaching anchor -> answerable/tripler",
          b5[0] == "answerable" and b5[3] == "tripler")
    # The anchor/support split exists because this exact item was promoted to
    # answerable on the first pass by the bare word "employees".
    check("generic workplace word alone -> marginal, not answerable",
          b6[0] == "marginal" and b6[3] == "tripler")
    check("rejection carries a reason", bool(b3[2]) and "Business and Finance" in b3[2])
    check("no bucket discards the item", all(x[0] in ("answerable","marginal","rejected")
                                             for x in (b1,b2,b3,b4,b5,b6)))

    print("HARD RULE — clinical attribution")
    check("clinical terms on alptunaer pass",
          assert_clinical_attribution([{"source_key":"a","matched_terms":["sauna"],
                                        "matched_expert":"alptunaer"}]))
    check("clinical terms on tripler RAISE",
          raises(lambda: assert_clinical_attribution(
              [{"source_key":"b","matched_terms":["sauna","cardiovascular"],
                "matched_expert":"tripler"}])))
    check("business terms on tripler pass",
          assert_clinical_attribution([{"source_key":"c","matched_terms":["hiring"],
                                        "matched_expert":"tripler"}]))
    check("experts.json loads two experts", len(load_experts()) == 2)
    check("tripler is unapproved", load_experts()["tripler"]["approved"] is False)
    check("tripler has no claims source", load_experts()["tripler"]["claims_source"] is None)

    print("Rule 2 — recipient SET, not a single address")
    for addr in EXPECTED_RECIPIENTS:
        check("accepts %s" % addr, assert_delivered_to(
            [{"id":"x","raw":{"payload":{"headers":{"Delivered-To":addr}}}}]))
    check("rejects julian@ (not in the set)", raises(lambda: assert_delivered_to(
        [{"id":"x","raw":{"payload":{"headers":{"Delivered-To":"julian@inhousewellness.com"}}}}])))
    check("rejects support@", raises(lambda: assert_delivered_to(
        [{"id":"x","raw":{"payload":{"headers":{"Delivered-To":"support@inhousewellness.com"}}}}])))

    print("claim bank gate")
    check("bank is awaiting_review", load_claim_topics()[1]["approval_status"] == "awaiting_review")

    print("qwoted manual flag")
    q = ("Because you follow #Mindfulness\nFrom: VICE.com\nHeadline here\n"
         " > body text\nSubmit By: 15 September 3:00PM CDT (in about 5 hours)\n"
         "RESPOND TO THIS REPORTER VIA QWOTED: http://url1940.qwoted.com/ls/click?x=1\n")
    qi = qwoted_parser.parse(q, "t")
    check("requires_manual always true", qi["requires_manual"] is True)
    check("no journalist name", qi["journalist_name"] is None)
    check("relative time stripped from deadline", qi["deadline"] == "15 September 3:00PM CDT")
    check("followed tags captured", qi["followed_tags"] == ["Mindfulness"])
    check("welcome mail is not a request",
          raises(lambda: qwoted_parser.parse("Welcome to Qwoted! Get started.", "t")))

    # ------------------------------------------------------------------
    # Round 7 — silent failure must be impossible
    # ------------------------------------------------------------------
    import tempfile, shutil
    global PROBE, PUSH_LOG, ALERTED, HEARTBEAT
    tmp = tempfile.mkdtemp(prefix="r7-selftest-")
    _save = (PROBE, PUSH_LOG, ALERTED, HEARTBEAT)
    PROBE = os.path.join(tmp, "probe.json")
    PUSH_LOG = os.path.join(tmp, "push-log.json")
    ALERTED = os.path.join(tmp, "alerted.json")
    HEARTBEAT = os.path.join(tmp, "hb.txt")
    try:
        print("§2 — connector probe judges RAW results, never a flag")
        ok_gmail = json.dumps({"results": [
            {"id": "g1", "raw": {"payload": {"headers": {
                "Delivered-To": "media@inhousewellness.com"}}}}]})
        check("real gmail result passes", judge_gmail_probe(ok_gmail)["ok"])
        # The exact 2026-09-14 failure: the wrong mailbox answers with zero
        # rows and no error. That must not read as reachable.
        check("EMPTY gmail result FAILS (wrong mailbox looks like this)",
              raises(lambda: judge_gmail_probe('{"results": []}')))
        check("gmail tool error FAILS",
              raises(lambda: judge_gmail_probe('{"isError": true, "error": "auth"}')))
        check("gmail prose (not JSON) FAILS",
              raises(lambda: judge_gmail_probe("Error: connection expired")))
        check("gmail to the WRONG recipient FAILS", raises(
            lambda: judge_gmail_probe(json.dumps({"results": [
                {"id": "g", "raw": {"payload": {"headers": {
                    "Delivered-To": "support@inhousewellness.com"}}}}]}))))
        check("real slack result passes",
              judge_slack_probe('{"messages":"Channel: #media (%s)\\nhi"}'
                                % SLACK_ALERT_CHANNEL)["ok"])
        check("slack channel_not_found FAILS",
              raises(lambda: judge_slack_probe('{"error":"channel_not_found"}')))
        check("slack invalid_auth FAILS",
              raises(lambda: judge_slack_probe('{"error":"invalid_auth"}')))
        check("slack reply about ANOTHER channel FAILS",
              raises(lambda: judge_slack_probe('{"messages":"Channel: #general (C999)"}')))
        check("empty slack result FAILS", raises(lambda: judge_slack_probe("   ")))

        print("§2 — the probe must be fresh and present")
        check("missing probe raises", raises(assert_connectors))
        now = datetime.now(timezone.utc)
        def _write_probe(age_s, gmail_ok=True, slack_ok=True):
            with open(PROBE, "w") as fh:
                json.dump({"probed_at": (now - timedelta(seconds=age_s))
                                        .isoformat(timespec="seconds"),
                           "gmail": {"ok": gmail_ok, "error": "x"},
                           "slack": {"ok": slack_ok, "error": "x"}}, fh)
        _write_probe(60);  check("fresh passing probe accepted", assert_connectors())
        _write_probe(PROBE_MAX_AGE_S + 60)
        check("stale probe raises (a chat probe proves nothing about a Routine)",
              raises(assert_connectors))
        _write_probe(60, slack_ok=False)
        check("SLACK DOWN is a failure state, not a degraded mode",
              raises(assert_connectors))
        _write_probe(60, gmail_ok=False)
        check("gmail down raises", raises(assert_connectors))
        _write_probe(-3600)
        check("future-dated probe raises", raises(assert_connectors))
        os.remove(PROBE)
        check("preflight WITH connectors required raises when unprobed",
              raises(lambda: preflight(require_connectors=True)))

        print("§1 — push verification checks the REMOTE, not the exit code")
        repo = tempfile.mkdtemp(prefix="r7-repo-")
        def git(*a, cwd=repo):
            return subprocess.run(("git",) + a, cwd=cwd, capture_output=True,
                                  text=True, check=True).stdout.strip()
        bare = os.path.join(repo, "origin.git")
        git("init", "--bare", "-q", bare, cwd=tempfile.gettempdir())
        work = os.path.join(repo, "w"); os.makedirs(work)
        git("init", "-q", "-b", "main", cwd=work)
        git("remote", "add", "origin", bare, cwd=work)
        git("config", "user.email", "t@t", cwd=work)
        git("config", "user.name", "t", cwd=work)
        os.makedirs(os.path.join(work, os.path.dirname(STATE_IN_REPO)))
        statefile = os.path.join(work, STATE_IN_REPO)
        def write_state(run_at):
            with open(statefile, "w") as fh:
                json.dump({"source_runs": [{"run_at": run_at,
                                            "run_date": run_at[:10]}]}, fh)
        global STATE
        _state_save = STATE; STATE = statefile
        write_state("2026-09-15T20:00:00+00:00")
        git("add", "-A", cwd=work); git("commit", "-qm", "run1", cwd=work)

        # Committed but NOT pushed: the exact 2026-09-14 shape.
        check("commit that was never pushed FAILS verification",
              raises(lambda: verify_push(branch="main", repo=work, fetch=False)))
        git("push", "-q", "origin", "main", cwd=work)
        recs = verify_push(branch="main", repo=work, fetch=False)
        check("pushed run verifies",
              [r["run_at"] for r in recs] == ["2026-09-15T20:00:00+00:00"])

        # A later run whose state is only in the working tree.
        write_state("2026-09-16T20:00:00+00:00")
        check("uncommitted state FAILS (output is in no commit at all)",
              raises(lambda: verify_push(branch="main", repo=work, fetch=False)))
        # Committed and pushed, but the commit does not carry the run: a ref
        # that advanced is not evidence that anything was persisted.
        git("stash", "-q", cwd=work)
        with open(os.path.join(work, "unrelated.txt"), "w") as fh:
            fh.write("x")
        git("add", "-A", cwd=work); git("commit", "-qm", "unrelated", cwd=work)
        git("push", "-q", "origin", "main", cwd=work)
        git("stash", "pop", "-q", cwd=work)
        git("add", "-A", cwd=work); git("commit", "-qm", "run2-local-only", cwd=work)
        check("ref advanced but run absent from remote state FAILS",
              raises(lambda: verify_push(branch="main", repo=work, fetch=False)))
        STATE = _state_save

        print("§1 — the counter does not advance on an unpersisted run")
        with open(PUSH_LOG, "w") as fh:
            json.dump({"verified": [{"run_at": "2026-09-15T20:00:00+00:00",
                                     "run_date": "2026-09-15",
                                     "commit": "deadbeef"}]}, fh)
        check("verified_run_ats reads the log",
              verified_run_ats() == {"2026-09-15T20:00:00+00:00"})
        os.remove(PUSH_LOG)
        check("no push log -> nothing counts as verified", verified_run_ats() == set())

        print("§6 — alerting is gated on APPROVAL")
        experts = load_experts()
        _topics, bank = load_claim_topics()
        approved = approved_experts(experts, bank)
        check("claim bank awaiting_review -> alptunaer NOT approved",
              "alptunaer" not in approved)
        check("tripler approved:false -> NOT approved", "tripler" not in approved)
        check("so the approved set is empty today", approved == set())
        prov_rows = [{"source_key": "k1", "bucket": "answerable",
                      "matched_expert": "tripler", "outlet": "Business Insight",
                      "platform": "sos", "deadline": None, "matched_terms": ["founders"],
                      "reason": "r", "query_text": "q", "summary": "s"}]
        imm, prov = split_hits(prov_rows, approved)
        check("provisional match raises NO immediate alert", imm == [])
        check("provisional match is still counted, not discarded", len(prov) == 1)
        path, imm, prov = emit_alert(prov_rows, "2026-09-15", "t", approved)
        check("no alert file written for a provisional-only run", path is None)
        # and with an approved expert it must still fire
        imm2, prov2 = split_hits(prov_rows, {"tripler"})
        check("same row alerts once the expert IS approved", len(imm2) == 1)
        record_alerted(["k1"], "2026-09-15")
        imm3, _ = split_hits(prov_rows, {"tripler"})
        check("already-alerted item does NOT re-alert", imm3 == [])

        print("§3 — daily heartbeat")
        hb = emit_heartbeat(prov_rows, Counter({"answerable": 1, "marginal": 2,
                                                "rejected": 9}),
                            "2026-09-15", prov_rows, Counter({"haro": 2}), "3")
        body = open(hb, encoding="utf-8").read()
        check("heartbeat names the day", "day 3" in body)
        check("heartbeat carries bucket counts",
              "1 answerable" in body and "2 marginal" in body and "9 rejected" in body)
        check("heartbeat reports held provisional items", "PROVISIONAL" in body)
        check("heartbeat reports the unparsed gap",
              "UNPARSED" in body and "haro" in body)
        check("heartbeat reports push status", "push:" in body)

        print("§4 — HARO is ingested-but-unparsed, never 'skipped'")
        check("haro routes by sender",
              route({"id": "h", "from": {"email": "haro@helpareporter.com"}}) == "haro")
        check("featured routes by sender",
              route({"id": "f", "from": {"email": "x@featured.com"}}) == "featured")
    finally:
        PROBE, PUSH_LOG, ALERTED, HEARTBEAT = _save
        shutil.rmtree(tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # Round 8 — HARO and Connectively
    # ------------------------------------------------------------------
    import glob as _glob

    def _bodies(pat):
        out = []
        for f in sorted(_glob.glob(os.path.join(SAMPLES, pat))):
            raw = open(f, encoding="utf-8").read()
            out.append((os.path.basename(f),
                        raw.split("----- BODY (text/plain) -----", 1)[1]))
        return out

    print("Rule 5 — the two new platforms route by SENDER")
    check("haro routes by sender", route(
        {"id": "h", "from": {"email": "haro@helpareporter.com"}}) == "haro")
    check("connectively routes by sender", route(
        {"id": "c", "from": {"email": "noreply@connectively.us"}}) == "connectively")
    check("featured keeps its own route (different sending domain)", route(
        {"id": "f", "from": {"email": "noreply@featured.com"}}) == "featured")
    check("a misleading subject cannot route to haro", route(
        {"id": "x", "from": {"email": "nobody@example.com"},
         "subject": "HARO Queries for September 18, 2026"}) == "unknown")

    haro_d = _bodies("haro-haro-queries-*.txt")
    cx_d = _bodies("connectively-connectively-alerts-*.txt")

    print("HARO — %d captured digests" % len(haro_d))
    check("at least two digests to compare", len(haro_d) >= 2)
    hv = haro_parser.format_variance(haro_d)
    check("structure does NOT vary between sends", hv["stable"])
    check("core fields on every item of every send", hv["core_stable"])
    check("no send introduces a field outside FIELDS", hv["no_new_fields"])
    hitems = [it for _n, b in haro_d for it in haro_parser.parse(b, _n)]
    check("every item has a DIRECT reply address",
          all(it["journalist_email"] for it in hitems))
    check("every reply address was READ, not constructed",
          all(it["journalist_email"] in _raw for it, _raw in
              ((it, b) for _n, b in haro_d for it in haro_parser.parse(b, _n))))
    check("no HARO row requires manual click-through",
          not any(it["requires_manual"] for it in hitems))
    check("profile URL is optional, not missing",
          0 < sum(1 for it in hitems if it.get("haro_journalist_profile_url"))
          < len(hitems))
    # Rule 6, HARO instance: journalists write label-shaped lines in prose.
    check("journalist prose headings are NOT captured as fields",
          not any(k in it for it in hitems for k in
                  ("clinical_implications", "questions_include", "note",
                   "social_anxiety", "for_delivery_help")))
    trap = ("********* INDEX ***********\n1) Thing (X)\n****************************\n"
            "1) Summary: Thing\n\nName: A B\n\nCategory: Health\n\n"
            "Email: reply+abcdef12-0000-0000-0000-000000000000@helpareporter.com\n\n"
            "Media Outlet: Outlet (https://o.com)\n\nDeadline: 6:00 PM ET - 17 September\n\n"
            "Query:\n\nreal text. Clinical Implications: not a field. Note: also not.\n\n"
            "Back to Top\n")
    ti = haro_parser.parse(trap, "trap")
    check("trap digest parses to one item", len(ti) == 1)
    check("trap: prose heading stayed inside the query",
          "Clinical Implications:" in ti[0]["query"] and "note" not in ti[0])
    check("trap: outlet split from its URL",
          ti[0]["media_outlet"] == "Outlet" and ti[0]["media_website"] == "https://o.com")
    check("lifecycle mail is not a digest", raises(
        lambda: haro_parser.parse("Thanks for signing up for HARO!", "welcome")))
    # HARO writes BARE zones ("ET"), ambiguous between -5 and -4. Resolved by
    # the US civil-time rule, not by picking one and hoping.
    dl = parse_haro_deadline("6:00 PM ET - 17 September", 2026)
    check("bare ET in September resolves as EDT (-4) -> 22:00 UTC",
          dl is not None and dl.hour == 22 and dl.day == 17)
    dl_w = parse_haro_deadline("6:00 PM ET - 17 December", 2026)
    check("bare ET in December resolves as EST (-5) -> 23:00 UTC",
          dl_w is not None and dl_w.hour == 23)
    dl_p = parse_haro_deadline("9:00 AM PT - 1 July", 2026)
    check("bare PT in July resolves as PDT (-7) -> 16:00 UTC",
          dl_p is not None and dl_p.hour == 16)
    check("explicit EST still honoured",
          parse_haro_deadline("6:00 PM EST - 17 December", 2026).hour == 23)
    check("unknown zone yields None, never a guess",
          parse_haro_deadline("6:00 PM XYZ - 17 September", 2026) is None)

    print("Connectively — %d captured digests" % len(cx_d))
    check("at least two digests to compare", len(cx_d) >= 2)
    cv = cx_parser.format_variance(cx_d)
    check("structure does NOT vary between sends", cv["stable"])
    check("section set identical across sends", cv["sections_stable"])
    citems = [it for _n, b in cx_d for it in cx_parser.parse(b, _n)]
    check("Q&A rows are ALL requires_manual (magic-link is not a reply path)",
          all(it["requires_manual"] for it in citems
              if it["section"].startswith("Q&A")))
    check("no Q&A row carries an email address",
          not any(it["journalist_email"] for it in citems
                  if it["section"].startswith("Q&A")))
    check("relay addresses on opportunity rows were READ, not constructed",
          all(it["journalist_email"] in b for _n, b in cx_d
              for it in cx_parser.parse(b, _n) if it["journalist_email"]))
    check("navigation links are not parsed as items",
          not any("View All Questions" in (it["query"] or "") for it in citems))
    check("empty section yields no items, and is not an error",
          all("bylined" not in (it["section"] or "").lower() for it in citems))
    # The digest declares "N alerts" per category; a dropped item must raise.
    broken = cx_d[0][1].replace("Answer by", "Answered by", 1)
    check("a dropped item RAISES rather than reading as a quiet day",
          raises(lambda: cx_parser.parse(broken, "broken")))
    check("onboarding mail is not a digest", raises(
        lambda: cx_parser.parse("Welcome to Connectively! Create your profile.", "w")))
    cdl = parse_connectively_deadline("Sep 18th", 2026)
    check("Connectively deadline resolves (UTC end of day, not a guessed zone)",
          cdl is not None and (cdl.hour, cdl.minute) == (23, 59))

    print("Round 8 — the clock")
    check("clock start is the first HARO digest", HARO_CLOCK_START == "2026-09-15")
    check("Media/Connectively is in label scope",
          "Media/Connectively" in EXPECTED_LABELS)
    check("Media/Featured is NOT retired (separate sending domain)",
          "Media/Featured" in EXPECTED_LABELS)

    print("Round 9 — request identity is per platform")
    # The SQL and the Python must not drift; the trend uses one and any future
    # caller will reach for the other.
    _c = connect()
    sql_rows = list(_c.execute("""SELECT s.platform, s.journalist_email,
        r.query_text, s.source_key, %s AS k FROM source_items s
        JOIN requests r ON r.id = s.request_id""" % DEDUP_SQL))
    check("DEDUP_SQL and request_key() agree on every stored row",
          all(request_key(p, e, q, sk) == k for p, e, q, sk, k in sql_rows))
    # HARO: reply+<uuid> is the QUERY id. Proven, not assumed.
    haro_keys = defaultdict(set)
    for p, e, q, sk, k in sql_rows:
        if p == "haro":
            haro_keys[k].add((q or "")[:120])
    check("HARO: no reply address carries two different queries",
          all(len(v) == 1 for v in haro_keys.values()))
    check("HARO dedup collapses rows", len(haro_keys) < sum(
        1 for p, *_ in sql_rows if p == "haro"))
    # SOS: the address is the PERSON. Deduping on it alone would merge real
    # requests — this is the check that stops a future refactor doing that.
    sos_by_addr = defaultdict(set)
    for p, e, q, sk, k in sql_rows:
        if p == "sos" and e:
            sos_by_addr[e].add((q or "")[:120])
    check("SOS: some journalists DO send multiple different queries",
          any(len(v) > 1 for v in sos_by_addr.values()))
    check("SOS identity keeps those separate",
          len({k for p, _e, _q, _sk, k in sql_rows if p == "sos"})
          >= len(sos_by_addr))
    check("request_key never returns None",
          all(request_key(p, e, q, sk) is not None for p, e, q, sk, _k in sql_rows))
    check("a HARO row with no reply address falls back to source_key",
          request_key("haro", None, "q", "haro:g:1") == "haro:g:1")
    _c.close()

    print("Round 10 — every clinical term resolves to a claim")
    _doc = claims_lib.load(os.path.join(DATA, "claims.json"))
    check("orphans are DROPPED from the match vocabulary",
          not (set(ORPHANED_TERMS) & (MODALITY_TERMS | OUTCOME_TERMS)))
    check("infrared no longer matches", "infrared" not in MODALITY_TERMS)
    check("every surviving modality term names its claims",
          all(v["claims"] for v in MODALITY_BACKED.values()))
    check("every surviving outcome term names its claims",
          all(v["claims"] for v in OUTCOME_BACKED.values()))
    check("claims.py RAISES on an orphaned vocabulary", raises(
        lambda: claims_lib.assert_no_orphans(CANDIDATE_MODALITY_TERMS, _doc)))
    check("and passes once only backed terms are asked about",
          bool(claims_lib.assert_no_orphans(set(MODALITY_TERMS), _doc)))
    # The Round 9 bug, as a test.
    check("an item whose ONLY clinical term is an orphan is REJECTED",
          classify({"summary": "red or near-infrared light for skin health"},
                   [], None)[0] == "rejected")
    check("a backed modality still reaches answerable",
          classify({"summary": "sauna use and blood pressure"},
                   [], None)[0] == "answerable")
    check("the reason names claim ids, not a promise",
          "backed by" in classify({"summary": "sauna and blood pressure"},
                                  [], None)[2])

    print("Round 10 — backing rules")
    # do_not_say is what a claim FORBIDS. Backing on it would route an item to
    # the claim that exists to stop that sentence being said.
    check("`cold plunge` is an orphan (do_not_say only)",
          "cold plunge" in ORPHANED_TERMS)
    check("and the reconciliation says WHY",
          bool(RECONCILIATION["cold plunge"]["do_not_say_only"]))
    check("`hydration` is an orphan (topic label only)",
          "hydration" in ORPHANED_TERMS
          and bool(RECONCILIATION["hydration"]["topic_label_only"]))
    check("a reversing prefix does not inherit backing",
          "dehydration" in ORPHANED_TERMS)
    check("but `depression` is NOT blocked by its leading 'de'",
          "depression" not in ORPHANED_TERMS)

    print("Round 10 — concept derivation")
    _c = [c for c in _doc["claims"] if c["id"] == "heat-cognition-01"][0]
    check("morphological tie: cognition <- cognitive",
          claims_lib.backing_claims("cognition", _doc)[1] == "morphological")
    check("inflammation <- inflammatory",
          claims_lib.backing_claims("inflammation", _doc)[0] == ["heat-shock-02"])
    check("hyphen and space are the same separator",
          claims_lib._canon("cold-water immersion") == "cold water immersion")
    check("a short content word survives derivation ('brown fat')",
          claims_lib.backing_claims("brown fat", _doc)[0])
    check("hyphen-joined compounds still form their bigram ('heat acclimation')",
          claims_lib.backing_claims("heat acclimation", _doc)[0])
    check("derivation invents nothing: no claim reaches 'light'",
          not claims_lib.backing_claims("light-based skin treatment", _doc)[0])
    check("redundant supersets are pruned",
          "finnish sauna" not in MODALITY_TERMS)
    check("non-redundant morphological forms are kept",
          "cognitive" in OUTCOME_TERMS and "depressive" in OUTCOME_TERMS)

    print("Round 10 — attribution still covers dropped terms")
    check("an orphaned clinical term on tripler STILL raises", raises(
        lambda: assert_clinical_attribution(
            [{"source_key": "x", "matched_terms": ["infrared"],
              "matched_expert": "tripler"}])))

    print("Round 11 — the specialty gap is FILLED")
    _ex = load_experts()
    check("specialty recorded", _ex["alptunaer"]["specialty"] == "Emergency Medicine")
    check("subspecialty recorded",
          _ex["alptunaer"]["subspecialty"] == "General Emergency Medicine")
    check("specialty governs DESCRIPTION, not eligibility",
          "how he is DESCRIBED" in _ex["alptunaer"]["attribution"]["scope_vs_eligibility"])
    check("tripler's specialty stays null", _ex["tripler"]["specialty"] is None)

    print("Attribution guard — the BYLINE, not the topic")
    check("credential line is the verbatim literal",
          CREDENTIAL_LINE == "Timur Alptunaer, MD, RN, EMT-T, FACEP")
    check("it is stored in experts.json, not built in code",
          load_experts()["alptunaer"]["credential_line"] == CREDENTIAL_LINE)
    # The invariant that matters is not "the substring is absent" — this test
    # file quotes wrong orderings on purpose as fixtures. It is that code and
    # data agree on one literal and every deviation is caught below.
    check("code and experts.json agree on one literal",
          CREDENTIAL_LINE == load_experts()["alptunaer"]["credential_line"]
          == load_experts()["alptunaer"]["attribution"]["required_credential_line"])

    print("  blocks the DESCRIPTION")
    for bad in ("Dr. Alptunaer, a dermatologist, explains why",
                "We spoke to Alptunaer, a board-certified dermatologist.",
                "Timur Alptunaer is a sleep specialist.",
                "Alptunaer, a skin expert, said",
                "Dr. Alptunaer specialises in dermatology",
                "Alptunaer, professor of cardiology",
                "Alptunaer, chief of surgery",
                "quote from Alptunaer, a psychiatrist",
                "Alptunaer, an expert in nutrition",
                "Alptunaer, a wellness consultant",
                "Dr. Alptunaer, a sports doctor"):
        check("blocks %r" % bad[:44], raises(lambda b=bad: assert_attribution_safe(b)))

    print("  permits the credential line and the one role descriptor")
    for ok in ("Timur Alptunaer, MD, RN, EMT-T, FACEP, on what the study found",
               "Dr. Alptunaer, an emergency medicine physician, notes",
               "Alptunaer is an emergency physician.",
               "Timur Alptunaer, MD, RN, EMT-T, FACEP"):
        check("permits %r" % ok[:44], assert_attribution_safe(ok))

    print("  does NOT filter the subject matter")
    # The whole point: he may speak about dermatology. He may not be CALLED a
    # dermatologist. A guard that blocked the topic would throw away most of
    # what he can do.
    check("a dermatology SUBJECT is fine", assert_attribution_safe(
        "Timur Alptunaer, MD, RN, EMT-T, FACEP, on treating hyperpigmentation "
        "and what the dermatology literature actually shows"))
    check("a psychiatry SUBJECT is fine", assert_attribution_safe(
        "Timur Alptunaer, MD, RN, EMT-T, FACEP, on how trauma survivors present"))
    check("naming another specialty NOT beside him is fine",
          assert_attribution_safe("Dermatologists disagree about this. "
                                  + "x" * 200 +
                                  " Timur Alptunaer, MD, RN, EMT-T, FACEP, adds"))

    print("  pitchable requires the EXACT literal")
    base = {"source_key": "k", "pitchable": True, "framing": "published-evidence"}
    check("exact line passes",
          assert_pitchable(dict(base, credential_line=CREDENTIAL_LINE)))
    for wrong in ("Timur Alptunaer, MD",
                  "Timur Alptunaer, MD, RN, EMT-T, FACEP.",
                  "Timur Alptunaer MD RN EMT-T FACEP",
                  "Timur Alptunaer, MD, RN, FACEP, EMT-T",
                  "Dr. Timur Alptunaer, MD, RN, EMT-T, FACEP",
                  "Timur Alptunaer, MD, RN, EMT-T, Fellow of the American "
                  "College of Emergency Physicians", None, ""):
        check("rejects %r" % (str(wrong)[:40]), raises(
            lambda w=wrong: assert_pitchable(dict(base, credential_line=w))))
    check("un-pitchable items are not gated",
          assert_pitchable({"source_key": "k", "pitchable": False}))

    print("  framing is required and named")
    check("published-evidence accepted", assert_pitchable(
        dict(base, credential_line=CREDENTIAL_LINE, framing="published-evidence")))
    check("clinical-experience accepted", assert_pitchable(
        dict(base, credential_line=CREDENTIAL_LINE, framing="clinical-experience")))
    check("missing framing raises", raises(lambda: assert_pitchable(
        {"source_key": "k", "pitchable": True, "credential_line": CREDENTIAL_LINE})))
    check("invented framing raises", raises(lambda: assert_pitchable(
        dict(base, credential_line=CREDENTIAL_LINE, framing="whatever"))))

    print("  mark_pitchable is the only door, and it checks")
    m = mark_pitchable({"source_key": "k"}, "clinical-experience")
    check("attaches the literal unmodified", m["credential_line"] == CREDENTIAL_LINE)
    check("body text is guarded on the way through", raises(
        lambda: mark_pitchable({"source_key": "k",
                                "pitch_text": "Alptunaer, a dermatologist, says"},
                               "published-evidence")))

    print("  EMT-T is recorded, NOT acted on")
    _obs = load_experts()["alptunaer"].get("observations_for_human") or []
    check("observation is recorded", any(o["id"] == "emt-t-scope" for o in _obs))
    check("and is observation_only",
          all(o["status"] == "observation_only" for o in _obs))
    check("no filter term was added from it",
          not any("tactical" in t or "military" in t
                  for t in (CANDIDATE_MODALITY_TERMS | CANDIDATE_OUTCOME_TERMS)))

    print("Round 12 — the drafter")
    _bank = load_claim_topics()[1]
    _ex = load_experts()
    _MOD = set(MODALITY_TERMS)
    _writer = lambda i, c, e: drafter.default_body_writer(i, c, e, _bank)
    covered = {"source_key": "t:1", "outlet": "Demo", "platform": "haro",
               "journalist_email": "reply+demo@helpareporter.com",
               "query_text": ("Seeking a physician to comment on whether regular "
                              "sauna use is associated with cardiovascular "
                              "mortality and what the evidence supports.")}
    d = drafter.build(covered, _bank, _ex, _MOD, set(), body_writer=_writer)
    check("a COVERED item drafts — so a zero elsewhere is the corpus, not the code",
          bool(d["draft"]))
    check("the draft enumerates its source claim ids", bool(d["source_claim_ids"]))
    check("framing is published-evidence when claims are the source",
          d["framing"] == "published-evidence")
    check("the draft carries the verbatim credential line",
          CREDENTIAL_LINE in d["draft"])
    check("and the InHouse Wellness affiliation",
          "inhousewellness.com" in d["draft"])
    check("under the 300-word platform limit", len(d["draft"].split()) < 300)
    check("the draft passes assert_pitchable", assert_pitchable(mark_pitchable(
        {"source_key": "t:1", "pitch_text": d["draft"]}, d["framing"])))
    check("the hedge travels with the claim",
          "does not establish" in d["draft"] or "has not been replicated" in d["draft"])

    print("  a failing draft is BLOCKED")
    check("wrong credential line blocks it", raises(lambda: assert_pitchable(
        {"source_key": "t", "pitchable": True, "framing": "published-evidence",
         "credential_line": "Timur Alptunaer, MD"})))
    check("a specialty descriptor in the body blocks it", raises(
        lambda: mark_pitchable({"source_key": "t",
            "pitch_text": "Alptunaer, a dermatologist, notes " + CREDENTIAL_LINE},
            "published-evidence")))
    check("over the word limit raises",
          raises(lambda: drafter.assemble("word " * 320, CREDENTIAL_LINE)))
    check("a claim id not in the bank raises", raises(
        lambda: drafter.default_body_writer({}, ["no-such-claim"], [], _bank)))

    print("  needs_expert_input instead of improvising")
    uncovered = {"source_key": "t:2", "outlet": "Demo",
                 "query_text": ("Seeking a dermatologist to comment on treating "
                                "hyperpigmentation in darker skin tones.")}
    u = drafter.build(uncovered, _bank, _ex, _MOD, set(), body_writer=_writer)
    check("no approved source -> needs_expert_input", u["needs_expert_input"])
    check("and NO draft text is produced", u["draft"] is None)
    check("and it says why", "no approved source covers this" in u["reason"])
    check("no experience set exists to fall back on",
          not _ex["alptunaer"].get("experience_set"))

    print("  not_a_query — tested against the three known items")
    _rows = json.load(open(CORPUS_CLASSIFICATION, encoding="utf-8"))
    for idx, why in ((37, "gift bag"), (38, "gift bag"), (56, "host")):
        ok, reason = drafter.classify_query(_rows[idx]["query_text"])
        check("[%d] %s caught as not_a_query" % (idx, _rows[idx]["outlet"][:18]),
              not ok and why in reason)
    # The first version demanded positive comment vocabulary and dropped four
    # real requests. Absence of expected phrasing is not evidence of absence.
    for idx in (52, 61, 69, 72):
        ok, _r = drafter.classify_query(_rows[idx]["query_text"])
        check("[%d] %s is NOT dropped for want of a phrase"
              % (idx, _rows[idx]["outlet"][:18]), ok)
    check("'I want to talk to experts' reads as a query",
          drafter.classify_query("I want to talk to experts about how common this is")[0])

    print("  requirement mismatches are flagged, not papered over")
    mm = drafter.build({"source_key": "t:3", "outlet": "D",
                        "query_text": "Seeking comment. This opp is for a dermatologist.",
                        "journalist_restriction": "asks for dermatologists"},
                       _bank, _ex, _MOD, set(), body_writer=_writer)
    check("mismatch flagged", mm["requirement_mismatch"])
    check("and the requested profession is named",
          "dermatolog" in (mm["requested_profession"] or ""))

    print("  the drafter cannot send")
    _src = open(os.path.join(HERE, "lib", "drafter.py"), encoding="utf-8").read()
    for forbidden in ("smtp", "sendmail", "gmail_send", "execute_zapier_write",
                      "requests.post", "urlopen"):
        check("drafter.py contains no %r" % forbidden, forbidden not in _src.lower())

    print("Round 13 — three regimes")
    _exp = drafter.load_experience(os.path.join(DATA, "experience.json"))
    _cits = json.load(open(os.path.join(DATA, "draft-citations.json"),
                           encoding="utf-8"))["citations"]
    _drafts = json.load(open(os.path.join(DATA, "drafts.json"),
                             encoding="utf-8"))["drafts"]
    check("experience set is approved", _exp["approved"] is True)
    check("exactly the five confirmed topics",
          _exp["topics"] == ["exercise", "diet", "recovery",
                             "sports performance", "military performance"])
    check("provenance recorded", _exp["provenance"]["relayed_by"] == "Julian")
    check("and it is NOT described as a signature",
          _exp["provenance"]["is_signature"] is False)
    check("experience regime is uncited by design",
          "never_cited" in _exp["constraints"])
    check("the capacity question is recorded as unanswered",
          _exp["open_question"]["status"] == "unanswered")

    print("  a citation must RESOLVE")
    ok_cit = {"id": "c", "title": "T", "pmid": "33976376", "source_type": "study",
              "verified_at": "2026-09-21", "retrieved_via": "inspect_paper"}
    check("resolved PMID passes", drafter.assert_citation_resolved(ok_cit))
    check("resolved DOI passes", drafter.assert_citation_resolved(
        dict(ok_cit, pmid=None, doi="10.1038/s41366-021-00839-w")))
    for bad, why in ((dict(ok_cit, pmid="abc", doi=None), "unresolvable id"),
                     (dict(ok_cit, title=""), "no title"),
                     (dict(ok_cit, verified_at=None), "not verified at draft time"),
                     (dict(ok_cit, source_type=None), "no source_type"),
                     (dict(ok_cit, source_type="vibes"), "bad source_type")):
        check("blocks: %s" % why, raises(
            lambda b=bad: drafter.assert_citation_resolved(b)))
    check("every stored citation passes the gate",
          all(drafter.assert_citation_resolved(c) for c in _cits))
    check("source_type recorded on all of them",
          all(c["source_type"] in ("guideline", "study") for c in _cits))

    print("  an unsourced assertion is DROPPED, not softened")
    check("assertion with no citation raises", raises(
        lambda: drafter.assert_assertions_verified(
            [{"text": "Red light therapy rebuilds collagen.", "citation_ids": []}],
            _cits)))
    check("assertion citing an unknown id raises", raises(
        lambda: drafter.assert_assertions_verified(
            [{"text": "x", "citation_ids": ["no-such-citation"]}], _cits)))
    check("every authored assertion is verified",
          all(drafter.assert_assertions_verified(d["assertions"], _cits)
              for d in _drafts))

    print("  verified-at-draft cannot be ready-to-send without expert review")
    check("marking it pitchable sets the flag",
          mark_pitchable({"source_key": "k"}, "verified-guideline")["requires_expert_review"])
    check("clearing the flag blocks it", raises(lambda: assert_pitchable(
        {"source_key": "k", "pitchable": True, "framing": "verified-guideline",
         "credential_line": CREDENTIAL_LINE, "requires_expert_review": False})))
    check("experience drafts do NOT require it",
          not mark_pitchable({"source_key": "k"}, "clinical-experience")["requires_expert_review"])

    print("  regime precedence")
    check("an EVIDENCE question skips the experience set",
          drafter.needs_citation("Is there real evidence this works?"))
    check("a practice question does not",
          not drafter.needs_citation("What do you tell patients in clinic?"))
    check("experience topics match on subject",
          drafter.experience_topics_for("questions about diet and exercise", _exp)
          == ["exercise", "diet"])
    check("all three framings are accepted by the guard",
          all(mark_pitchable({"source_key": "k"}, f)["framing"] == f
              for f in ("published-evidence", "clinical-experience",
                        "verified-guideline")))

    print("  §3 again — a product solicitation that opens like an editorial ask")
    check("'brands interested in having their products featured' is not_a_query",
          not drafter.classify_query(
              "We are working on an At Home Fitness segment and are looking to "
              "connect with fitness and wellness brands interested in having "
              "their products featured.")[0])

    print("  the attribution guard holds across every draft")
    for d in _drafts:
        body = " ".join(x for x in (d.get("opening"),
                        drafter.render_verified_body(d["assertions"], _cits),
                        d.get("experience_tail")) if x)
        txt = drafter.assemble(body, CREDENTIAL_LINE)
        check("%s: guard passes" % d["outlet"][:20], assert_attribution_safe(txt))
        check("%s: verbatim credential line" % d["outlet"][:20], CREDENTIAL_LINE in txt)
        check("%s: under 300 words" % d["outlet"][:20], len(txt.split()) < 300)
        check("%s: every assertion carries an id" % d["outlet"][:20],
              all(a["citation_ids"] for a in d["assertions"]))

    print("Round 14 — close the loop")
    import tempfile as _tf
    _tmp = os.path.join(_tf.mkdtemp(prefix="r14-"), "sends.json")
    d = outcomes.load(_tmp)
    check("an empty record loads", d["sends"] == [])
    rec, created = outcomes.record_send(d, "k1", "media@inhousewellness.com",
                                        "2026-09-21T10:00:00+00:00",
                                        outlet="Demo", regime="verified_at_draft",
                                        platform="haro")
    check("a send is recorded", created and rec["key"] == "k1")
    check("and starts PENDING, not failed", rec["status"] == "pending")
    _r2, created2 = outcomes.record_send(d, "k1", "julian@inhousewellness.com")
    check("re-recording updates rather than duplicating",
          not created2 and len(d["sends"]) == 1)
    check("the correction lands", _r2["sent_from"] == "julian@inhousewellness.com")
    # Found by this test failing: a re-record without --at was restamping the
    # send to now, quietly corrupting the one duration the file measures.
    check("but the ORIGINAL send time survives a re-record",
          _r2["sent_at"] == "2026-09-21T10:00:00+00:00")
    check("an explicit --at does move it",
          outcomes.record_send(d, "k1", "a@b.com",
                               "2026-09-20T09:00:00+00:00")[0]["sent_at"]
          == "2026-09-20T09:00:00+00:00")
    outcomes.record_send(d, "k1", "media@inhousewellness.com",
                         "2026-09-21T10:00:00+00:00")
    check("a send needs the address it went from", raises(
        lambda: outcomes.record_send(d, "k2", "")))
    check("a bare name is not an address", raises(
        lambda: outcomes.record_send(d, "k2", "julian")))
    check("a malformed timestamp raises", raises(
        lambda: outcomes.record_send(d, "k3", "a@b.com", "last tuesday")))

    print("  silence is never publication, and never failure")
    s0 = outcomes.summarise(d)
    check("pending counted as pending", s0["pending"] == 1 and s0["published"] == 0)
    outcomes.check_one(d["sends"][0], fetcher=lambda u, timeout=25: (200, ""))
    check("no published URL -> stays pending", d["sends"][0]["status"] == "pending")
    check("and says why", "Silence is not evidence"
          in d["sends"][0].get("check_note", ""))
    check("no status other than pending/published exists",
          outcomes.STATUSES == ("pending", "published"))

    print("  the link is READ OFF THE PAGE")
    page = ('<a href="https://inhousewellness.com/x" rel="nofollow noopener">IHW</a>'
            '<a href="https://example.com/">other</a>'
            ' inhousewellness.com in plain text is not a link')
    links = outcomes.find_links(page)
    check("finds the anchor", len(links) == 1)
    check("records rel exactly as written", links[0]["rel"] == "nofollow noopener")
    check("flags nofollow", links[0]["nofollow"])
    check("a plain-text brand mention is NOT a link",
          not outcomes.find_links("we love inhousewellness.com very much"))
    check("an anchor with no href is ignored",
          not outcomes.find_links('<a name="x">inhousewellness.com</a>'))

    print("  a failed fetch must never read as an absent link")
    live = {"published_url": "https://pub.example/a", "linked": True, "rel": "follow"}
    outcomes.check_one(live, fetcher=lambda u, timeout=25: (None, "NETWORK-ERROR: blocked"))
    check("blocked fetch leaves linked=True untouched", live["linked"] is True)
    check("and records that it could not look",
          live["check_source"] == "page-fetch-failed")
    for code in (403, 429, 500):
        r = {"published_url": "https://p/x", "linked": True}
        outcomes.check_one(r, fetcher=lambda u, timeout=25, c=code: (c, ""))
        check("HTTP %d does not clear the link" % code, r["linked"] is True)
    r200 = {"published_url": "https://p/x"}
    outcomes.check_one(r200, fetcher=lambda u, timeout=25: (200, "<p>no link</p>"))
    check("a SUCCESSFUL fetch with no link does record linked=false",
          r200["linked"] is False)

    print("  the backlink audit is the second route")
    rows = [{"url_from": "https://www.eatthis.com/seated-balance-exercises-after-65/",
             "url_to": "https://inhousewellness.com/", "rel_attr": "follow",
             "run_date": "2026-09-14"}]
    rb = {"published_url": "https://www.eatthis.com/seated-balance-exercises-after-65/"}
    outcomes.check_via_backlink_audit(rb, rows)
    check("audit confirms a link the fetch could not", rb["linked"] is True)
    check("with its rel", rb["rel"] == "follow" and rb["follow"] is True)
    check("and says where the fact came from", rb["check_source"] == "backlink-audit")
    absent = {"published_url": "https://nowhere.example/x", "linked": None}
    outcomes.check_via_backlink_audit(absent, rows)
    check("audit silence does NOT set linked=false", absent["linked"] is None)

    print("  outcome recording and the maths")
    outcomes.record_published_url(d, "k1", "https://pub.example/story",
                                  "2026-09-23T10:00:00+00:00")
    check("status becomes published", d["sends"][0]["status"] == "published")
    check("time to publication computed",
          outcomes.hours_to_publication(d["sends"][0]) == 48.0)
    check("recording an outcome for an unsent key raises", raises(
        lambda: outcomes.record_published_url(d, "never-sent", "https://x/y")))
    check("a published_url must be a URL", raises(
        lambda: outcomes.record_published_url(d, "k1", "not a url")))
    s1 = outcomes.summarise(d)
    check("per-regime breakdown present",
          s1["per_regime"]["verified_at_draft"]["published"] == 1)
    check("per-platform breakdown present",
          s1["per_platform"]["haro"]["sent"] == 1)

    print("  the committed record is empty and honest")
    real = outcomes.load(SENDS)
    check("no send is recorded yet", real["sends"] == [])
    check("and the file says so on purpose", "EMPTY ON PURPOSE" in real["_comment"])
    check("the mechanism is stated in the file", "CLI" in real.get("mechanism", ""))

    print("  the pipeline still cannot send")
    _osrc = open(os.path.join(HERE, "lib", "outcomes.py"), encoding="utf-8").read()
    for forbidden in ("smtp", "sendmail", "gmail_send", "execute_zapier_write"):
        check("outcomes.py contains no %r" % forbidden, forbidden not in _osrc.lower())
    check("it only ever GETs", "urlopen" in _osrc and "data=" not in _osrc)

    print()
    if fails:
        print("SELF-TEST FAILED: %d" % len(fails)); return 1
    print("SELF-TEST PASSED"); return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--payload", required=True)
    r.add_argument("--connection-id", required=True)
    r.add_argument("--labels")
    r.add_argument("--date")
    r.add_argument("--force-heartbeat", action="store_true",
                   help="post the heartbeat even if one already went out today")
    r.set_defaults(fn=cmd_run)
    pr = sub.add_parser("probe", help="assert both connectors from raw results")
    pr.add_argument("--gmail", required=True,
                    help="file holding the RAW gmail_find_email result")
    pr.add_argument("--slack", required=True,
                    help="file holding the RAW slack_read_channel result for #media")
    pr.set_defaults(fn=cmd_probe)
    vp = sub.add_parser("verify-push",
                        help="confirm this run's output is on the remote")
    vp.add_argument("--branch", default=GIT_BRANCH)
    vp.add_argument("--repo", default=None)
    vp.set_defaults(fn=cmd_verify_push)
    sub.add_parser("draft").set_defaults(fn=cmd_draft)
    sn = sub.add_parser("sent", help="record that a HUMAN sent a pitch")
    sn.add_argument("--key", required=True)
    sn.add_argument("--from", dest="sent_from", required=True,
                    help="the address or platform it was actually sent from")
    sn.add_argument("--at", default=None, help="ISO timestamp; defaults to now")
    sn.add_argument("--note", default=None)
    sn.set_defaults(fn=cmd_sent)
    oc = sub.add_parser("outcome", help="record a published URL")
    oc.add_argument("--key", required=True)
    oc.add_argument("--url", required=True)
    oc.add_argument("--at", default=None, help="ISO publication timestamp")
    oc.set_defaults(fn=cmd_outcome)
    sub.add_parser("outcomes", help="WEEKLY: re-check published URLs").set_defaults(fn=cmd_outcomes)
    sub.add_parser("post-drafts", help="emit Slack bodies for unposted drafts").set_defaults(fn=cmd_post_drafts)
    pd = sub.add_parser("posted", help="record that a draft was posted")
    pd.add_argument("--key", required=True)
    pd.add_argument("--ts", default=None)
    pd.add_argument("--link", default=None)
    pd.set_defaults(fn=cmd_posted)
    sub.add_parser("rescore").set_defaults(fn=cmd_rescore)
    sub.add_parser("test-samples").set_defaults(fn=cmd_test_samples)
    sub.add_parser("self-test").set_defaults(fn=cmd_self_test)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
