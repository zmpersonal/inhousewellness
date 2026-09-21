#!/usr/bin/env python3
"""
backfill_summaries.py — populate source_items.summary for LIVE items only.

WHY THIS EXISTS
  `summary` was added to the schema after most rows were already ingested, so
  every pre-existing item carried NULL. `build_draft_args()` raises on a NULL
  summary rather than inventing a subject line, which is correct and also
  meant no stored item could be drafted. This recovers the real titles from
  the digests still sitting in the mailbox.

THE TWO RULES
  1. NEVER derive a title from query text. A title is read from a header the
     digest actually provides, or the row stays NULL and build_draft_args()
     keeps raising. A plausible-looking subject line invented from the body is
     exactly the failure this project keeps hitting: an absence dressed up as
     a value.
     Consequence: `connectively` is EXCLUDED. Its digest carries no title
     field at all — the parser's `summary` there is a 140-char excerpt of the
     query body, which is an inference, not a reading.
  2. Expired items stay NULL. There is no value in recovering a title for a
     query nobody can answer, and filling them would inflate the count of
     rows that look draftable.

USAGE
  backfill_summaries.py <payload.json> [<payload.json> ...] [--now ISO8601]

  Each payload is a raw `gmail_find_email` result saved to disk. Fetch them
  with the pinned connection (see RUNBOOK) over a window wide enough to cover
  the oldest live deadline, then pass them all in one invocation.

  Afterwards run `01_source.py` state export (or the snippet in the RUNBOOK)
  so `data/source-state.json` carries the summaries and `rebuild.py` restores
  them on a cold start.
"""

import argparse, datetime, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "lib", "parsers"))
DB_PATH = os.path.join(ROOT, "data", "links.db")

import haro                      # noqa: E402
import sos as sos_p              # noqa: E402
import qwoted as qw_p            # noqa: E402

# Platforms whose digest carries a real title header. Anything not listed here
# is skipped rather than guessed at — see rule 1 above.
TITLED_PLATFORMS = ("haro", "sos", "qwoted")


def ingest(path, titles, by_reply, problems):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    for m in doc.get("results") or []:
        gid = m.get("id")
        body = m.get("body_plain") or ""
        frm = (m.get("from") or {}).get("email", "").lower()
        try:
            if haro.is_haro(frm) and haro.looks_like_digest(body):
                for it in haro.parse(body, source_id=gid):
                    titles["haro:%s:%d" % (gid, it["item_no"])] = it["summary"]
                    # HARO reply addresses are per-query and stable across the
                    # morning/afternoon editions that repeat a query, so they
                    # recover a row whose own digest is outside the window.
                    if it.get("journalist_email"):
                        by_reply[it["journalist_email"].lower()] = it["summary"]
            elif sos_p.is_sos(frm) and sos_p.looks_like_digest(body):
                for it in sos_p.parse(body, source_id=gid):
                    titles["sos:%s:%d" % (gid, it["item_no"])] = it.get("summary")
            elif qw_p.is_qwoted(frm) and qw_p.looks_like_request(body):
                it = qw_p.parse(body, source_id=gid)
                titles["qwoted:%s" % gid] = it.get("headline")
        except Exception as e:                                    # noqa: BLE001
            # A parse that fails is reported, never swallowed: a digest the
            # parser cannot read is a parser bug to look at, not a quiet day.
            problems.append((gid, frm, str(e)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("payloads", nargs="+")
    ap.add_argument("--now", default=None,
                    help="ISO8601 cut-off for 'live'; defaults to now, UTC")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    now = (datetime.datetime.fromisoformat(a.now) if a.now
           else datetime.datetime.now(datetime.timezone.utc))
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)

    titles, by_reply, problems = {}, {}, []
    for p in a.payloads:
        ingest(p, titles, by_reply, problems)
    for gid, frm, err in problems:
        print("  PARSE FAILED %s (%s): %s" % (gid, frm, err[:100]))
    print("parsed %d titled items, %d HARO reply addresses, %d digests failed"
          % (len(titles), len(by_reply), len(problems)))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT source_key, platform, journalist_email, deadline_utc, summary "
        "FROM source_items")]
    live = [r for r in rows if r["deadline_utc"]
            and datetime.datetime.fromisoformat(r["deadline_utc"]) > now]

    filled = missing = skipped = 0
    for r in live:
        if r["platform"] not in TITLED_PLATFORMS:
            skipped += 1
            continue
        t = titles.get(r["source_key"])
        if not t and r["journalist_email"]:
            t = by_reply.get(r["journalist_email"].lower())
        if not t:
            missing += 1
            continue
        if not a.dry_run:
            conn.execute("UPDATE source_items SET summary=? WHERE source_key=?",
                         (t, r["source_key"]))
        filled += 1
    if not a.dry_run:
        conn.commit()

    print("\nLIVE items          %d" % len(live))
    print("  summary filled    %d" % filled)
    print("  no digest found   %d  (stay NULL — build_draft_args keeps raising)"
          % missing)
    print("  untitled platform %d  (connectively: no title in the digest)"
          % skipped)

    # Assert the two rules on the database rather than trusting the loop.
    n_exp = conn.execute(
        "SELECT COUNT(*) FROM source_items WHERE summary IS NOT NULL "
        "AND (deadline_utc IS NULL OR deadline_utc <= ?)",
        (now.isoformat(),)).fetchone()[0]
    n_untitled = conn.execute(
        "SELECT COUNT(*) FROM source_items WHERE summary IS NOT NULL "
        "AND platform NOT IN (%s)"
        % ",".join("?" * len(TITLED_PLATFORMS)), TITLED_PLATFORMS).fetchone()[0]
    print("\nASSERT expired rows with a summary      %d (must be 0)" % n_exp)
    print("ASSERT untitled-platform rows w/ summary %d (must be 0)" % n_untitled)
    conn.close()
    if n_exp or n_untitled:
        print("\nBACKFILL VIOLATED ITS OWN RULES — do not commit this database.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
