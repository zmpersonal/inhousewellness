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
sys.path.insert(0, os.path.join(HERE, "lib"))
import relay                        # noqa: E402

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
                   "Media/HARO", "Media/Featured")


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
    if frm.endswith("helpareporter.com"):
        return "haro"
    if frm.endswith("featured.com"):
        return "featured"
    return "unknown"


# --------------------------------------------------------------------------
# Filter against the claim bank
# --------------------------------------------------------------------------
# Terms that name the modality the bank actually covers. Presence of one of
# these is what separates "we have an approved claim" from "this is wellness-
# shaped". Derived from claims.json topics and claim text, not invented.
MODALITY_TERMS = {
    "sauna", "saunas", "infrared", "steam room", "heat therapy", "heat exposure",
    "hyperthermia", "cold plunge", "cold-plunge", "cold water immersion",
    "cold-water immersion", "ice bath", "ice baths", "cryotherapy",
    "contrast therapy", "cold exposure", "thermal", "heat acclimation",
}
# Outcomes the bank speaks to, but only alongside a modality term.
OUTCOME_TERMS = {
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
                "modality %s + outcome %s both present; squarely inside the "
                "claim bank" % (mods, outs), "alptunaer")
    if mods:
        return ("answerable", mods,
                "modality %s named; the claim bank covers this directly" % mods,
                "alptunaer")

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
    clinical = MODALITY_TERMS | OUTCOME_TERMS
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
        else:
            skipped["%s_no_parser" % src] += 1
            if src in ("haro", "featured"):
                unparsed[src] += 1

    # Resolve deadlines to UTC and flag anything already expired when we
    # first saw it. missed_on_arrival is the cadence measurement: it counts
    # requests that were dead before the pipeline ever looked, which is what
    # tells you whether daily is frequent enough.
    for r in rows:
        if r["platform"] == "sos":
            dt = parse_deadline(r.get("deadline_date"), r.get("deadline_time"),
                                r.get("time_zone"))
        else:
            yr = None
            if r.get("_msg_year"):
                yr = datetime.fromtimestamp(r["_msg_year"], timezone.utc).year
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
    L += [DECISION_CRITERIA, "", "---", "",
         "## Where we are", "", "| | |", "|---|---|",
         "| Runs recorded (locally) | %d |" % days,
         "| Runs CONFIRMED on the remote | %d |" % len([r for r in runs if r[1] in verified]),
         "| **Days of evidence (verified)** | **%s of 14** |" % trend_day_number(conn),
         "| Calendar span of local runs | %d day(s) |" % elapsed,
         "| Items ingested | %d |" % sum(tot.values()),
         "| **Answerable (cumulative)** | **%d** |" % tot["answerable"],
         "| Marginal (cumulative) | %d |" % tot["marginal"],
         "| Rejected (cumulative) | %d |" % tot["rejected"],
         "| Since last answerable | %s |" % since_ans,
         "| Deadline misses on arrival | %d |" % sum(1 for i in items if i[5]),
         ""]

    L += ["## Per run", "",
          "`Persisted` is *confirmed readable out of the commit the remote "
          "points at* — not *`git push` returned without an error*. On "
          "2026-09-14 the second was true and the first was false, and the run "
          "reported success.", "",
          "| Run date | run_at (UTC) | Msgs | Items | Answerable | Marginal | Rejected | New | Missed | Persisted |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for rd, rat, msgs, its, a, mg, rj, nw, miss in runs:
        if rat in verified:
            pstat = "\u2705"
        elif rat == newest_at:
            pstat = "\u23F3 pending"
        else:
            pstat = "\u274C NEVER"
        L.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d | %s |"
                 % (rd, (rat or "—")[:19], msgs, its, a, mg, rj, nw, miss or 0, pstat))
    L.append("")
    L += ["The most recent run reads `pending` by design: verification happens "
          "after the commit exists, so `push-log.json` and this table are "
          "committed one run behind. A run that stays `pending` across the "
          "next run is a run that never persisted.", ""]

    L += ["## Items per day by source", "", "| Run date | SOS | Qwoted | Total |",
          "|---|---|---|---|"]
    running = 0
    for rd in sorted({r[0] for r in runs}):
        sd = src_day[rd]; running += sum(sd.values())
        L.append("| %s | %d | %d | %d (running %d) |"
                 % (rd, sd.get("sos", 0), sd.get("qwoted", 0), sum(sd.values()), running))
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
        except (SourceError, sos_parser.SosParseError, qwoted_parser.QwotedParseError):
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
    sub.add_parser("rescore").set_defaults(fn=cmd_rescore)
    sub.add_parser("test-samples").set_defaults(fn=cmd_test_samples)
    sub.add_parser("self-test").set_defaults(fn=cmd_self_test)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
