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
  01_source.py run --payload <gmail.json> --connection-id <id> [--date D]
  01_source.py test-samples          # parsers against data/samples/
  01_source.py self-test             # all six rules + filter + idempotency
"""

import argparse, json, os, re, sqlite3, sys
from collections import Counter
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib", "parsers"))
import sos as sos_parser            # noqa: E402
import qwoted as qwoted_parser      # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SAMPLES = os.path.join(DATA, "samples")
DB_PATH = os.path.join(DATA, "links.db")
SCHEMA = os.path.join(DATA, "schema.sql")
REPORT = os.path.join(ROOT, "reports", "source-digest.md")

# Rule 1
EXPECTED_CONNECTION_ID = "029715c5-3a50-8935-b200-6e6eba55ac62"
# Rule 2
EXPECTED_DELIVERED_TO = "media@inhousewellness.com"
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
    """Rule 2 — assert on the response, not the request."""
    if not messages:
        return True
    wrong = [(m.get("id"), delivered_to(m) or "<absent>")
             for m in messages if delivered_to(m) != EXPECTED_DELIVERED_TO]
    if wrong:
        raise SourceError(
            "Rule 2: %d message(s) not Delivered-To %s — the payload came from "
            "the wrong mailbox: %s"
            % (len(wrong), EXPECTED_DELIVERED_TO, wrong[:5]))
    return True


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


def classify(item, claim_topics):
    """Three buckets. Never tuned to produce hits — zero answerable is valid."""
    hay = _hay(item)
    mods = _hits(MODALITY_TERMS, hay)
    outs = _hits(OUTCOME_TERMS, hay)
    adj = _hits(ADJACENT_TERMS, hay)

    if mods and outs:
        return "answerable", mods + outs, (
            "modality %s + outcome %s both present; squarely inside the bank"
            % (mods, outs))
    if mods:
        return "answerable", mods, (
            "modality %s named; the bank covers this directly" % mods)
    if adj or outs:
        return "marginal", adj + outs, (
            "wellness-adjacent (%s) but no sauna/cold/heat modality named; "
            "answering would stretch a claim past its do_not_say"
            % (adj + outs))
    cat = item.get("category") or "uncategorised"
    return "rejected", [], "no claim-bank vocabulary present (category: %s)" % cat


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
        query_truncated INTEGER, gmail_id TEXT, run_date TEXT);
    CREATE INDEX IF NOT EXISTS idx_source_items_bucket ON source_items(bucket);
    CREATE TABLE IF NOT EXISTS source_runs (
        run_date TEXT PRIMARY KEY, messages INTEGER, items INTEGER,
        answerable INTEGER, marginal INTEGER, rejected INTEGER, new_items INTEGER);
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
                query_truncated, gmail_id, run_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["source_key"], cur.lastrowid, r["platform"], r["bucket"], r["reason"],
             1 if r["requires_manual"] else 0, json.dumps(r["matched_terms"]),
             json.dumps(r.get("followed_tags") or []), r.get("respond_url"),
             r.get("journalist_name"), r.get("journalist_email"),
             r.get("muck_rack_url"), r.get("media_website"), r.get("category"),
             r.get("deadline_date"), r.get("deadline_time"), r.get("time_zone"),
             1 if r.get("query_truncated") else 0, r["gmail_id"], run_date))
        new += 1
    return new


# --------------------------------------------------------------------------
# ingest
# --------------------------------------------------------------------------
def ingest(payload, connection_id, labels_queried, run_date):
    assert_connection(connection_id)                      # Rule 1
    assert_label_scope(labels_queried)                    # Rule 4
    messages = payload.get("results") or []
    assert_non_empty(messages, "label scope %s" % (labels_queried,))   # Rule 3
    assert_delivered_to(messages)                         # Rule 2

    claim_topics, _bank = load_claim_topics()
    rows, skipped = [], Counter()

    for m in messages:
        src = route(m)                                    # Rule 5: sender only
        gid = m.get("id")
        body = m.get("body_plain") or ""
        if src == "sos":
            if not sos_parser.looks_like_digest(body):
                skipped["sos_noise"] += 1; continue
            for it in sos_parser.parse(body, source_id=gid):   # Rule 6 inside
                bucket, terms, reason = classify(it, claim_topics)
                rows.append({
                    "source_key": "sos:%s:%d" % (gid, it["item_no"]),
                    "platform": "sos", "gmail_id": gid,
                    "outlet": it.get("media_outlet") or "",
                    "query_text": it.get("query") or it.get("summary") or "",
                    "deadline": " ".join(x for x in (it.get("deadline_date"),
                                                     it.get("deadline_time"),
                                                     it.get("time_zone")) if x),
                    "bucket": bucket, "reason": reason, "matched_terms": terms,
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
                })
        elif src == "qwoted":
            if not qwoted_parser.looks_like_request(body):
                skipped["qwoted_noise"] += 1; continue
            it = qwoted_parser.parse(body, source_id=gid)
            bucket, terms, reason = classify(it, claim_topics)
            rows.append({
                "source_key": "qwoted:%s" % gid,
                "platform": "qwoted", "gmail_id": gid,
                "outlet": it["outlet"], "query_text": it["query"],
                "deadline": it["deadline"],
                "bucket": bucket, "reason": reason, "matched_terms": terms,
                "requires_manual": it["requires_manual"],
                "journalist_name": None, "journalist_email": None,
                "muck_rack_url": None, "media_website": None,
                "category": None, "deadline_date": None,
                "deadline_time": None, "time_zone": None,
                "followed_tags": it["followed_tags"],
                "respond_url": it["respond_url"],
                "summary": it["headline"],
                "query_truncated": it["query_truncated"],
            })
        else:
            skipped["%s_no_parser" % src] += 1

    # Every Qwoted row must be manual. Property of the source, not a setting.
    bad = [r["source_key"] for r in rows
           if r["platform"] == "qwoted" and not r["requires_manual"]]
    if bad:
        raise SourceError("Qwoted rows missing requires_manual: %s" % bad)
    return rows, skipped


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def render_report(conn, rows, skipped, run_date, msg_count):
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


# --------------------------------------------------------------------------
def cmd_run(a):
    with open(a.payload, encoding="utf-8") as fh:
        payload = json.load(fh)
    labels = a.labels.split(",") if a.labels else list(EXPECTED_LABELS)
    run_date = a.date or _date.today().isoformat()
    rows, skipped = ingest(payload, a.connection_id, labels, run_date)

    conn = connect()
    new = persist(conn, rows, run_date)
    counts = Counter(r["bucket"] for r in rows)
    conn.execute("INSERT OR REPLACE INTO source_runs VALUES (?,?,?,?,?,?,?)",
                 (run_date, len(payload.get("results") or []), len(rows),
                  counts["answerable"], counts["marginal"], counts["rejected"], new))
    conn.commit()
    render_report(conn, rows, skipped, run_date, len(payload.get("results") or []))

    print("messages %d | items %d | answerable %d | marginal %d | rejected %d"
          % (len(payload.get("results") or []), len(rows),
             counts["answerable"], counts["marginal"], counts["rejected"]))
    print("new rows inserted: %d (re-run inserts 0)" % new)
    print("report: %s" % os.path.relpath(REPORT, ROOT))
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
            "raw": {"payload": {"headers": {"Delivered-To": EXPECTED_DELIVERED_TO}}}}
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

    print("filter")
    topics = ["heat", "cold"]
    b1 = classify({"summary": "Seeking experts on infrared sauna and blood pressure"}, topics)
    b2 = classify({"summary": "Wellness experts to discuss October Theory"}, topics)
    b3 = classify({"summary": "Looking for mortgage experts on HELOCs",
                   "category": "Business and Finance"}, topics)
    check("modality+outcome -> answerable", b1[0] == "answerable")
    check("wellness w/o modality -> marginal", b2[0] == "marginal")
    check("off-topic -> rejected", b3[0] == "rejected")
    check("rejection carries a reason", bool(b3[2]) and "Business and Finance" in b3[2])
    check("no bucket discards the item", all(x[0] in ("answerable","marginal","rejected")
                                             for x in (b1,b2,b3)))

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
    r.set_defaults(fn=cmd_run)
    sub.add_parser("test-samples").set_defaults(fn=cmd_test_samples)
    sub.add_parser("self-test").set_defaults(fn=cmd_self_test)
    a = ap.parse_args(); sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
