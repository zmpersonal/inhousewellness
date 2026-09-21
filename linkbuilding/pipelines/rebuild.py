#!/usr/bin/env python3
"""
rebuild.py — reconstruct `links.db` end to end from COMMITTED FILES ONLY.

WHY THIS EXISTS
  `links.db` is gitignored, correctly: it is a build artifact and the snapshot
  is the source of truth. But in Round 5 it was deleted and recovered only
  because scratchpad files happened to survive in the same session. A
  Routine-fired session has no scratchpad at all.

  So a cold start had exactly one recovery path, and that path ran through
  /tmp. This script removes that dependency. Everything it reads is in the
  repository.

WHAT IT REBUILDS, AND FROM WHAT
  audit_links, audit_runs, targets(audit_historical)  <- data/payloads/{overview,backlinks}.json
  targets(gap|roundup|resource_page|mention|dealer)   <- data/payloads/{gap,serp,mentions}.json
  requests, source_items, source_runs                 <- data/source-state.json

  The first two re-run the real pipelines rather than replaying their output,
  so the Round 1 acceptance test (delta +0 across seven classes) is exercised
  again on every rebuild. A rebuild that quietly produced different numbers
  would be worse than no rebuild.

  The third is restored from the pipeline's own exported rows, because the raw
  Gmail payloads are a live mailbox and do not belong in source control.

Usage
  rebuild.py run [--force]      # rebuild links.db
  rebuild.py verify             # check every required input is present
"""

import argparse, json, os, sqlite3, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
PAYLOADS = os.path.join(DATA, "payloads")
DB_PATH = os.path.join(DATA, "links.db")
SCHEMA = os.path.join(DATA, "schema.sql")
STATE = os.path.join(DATA, "source-state.json")

REQUIRED = {
    "data/schema.sql": SCHEMA,
    "data/owned.json": os.path.join(DATA, "owned.json"),
    "data/affiliates.json": os.path.join(DATA, "affiliates.json"),
    "data/claims.json": os.path.join(DATA, "claims.json"),
    "data/payloads/overview.json": os.path.join(PAYLOADS, "overview.json"),
    "data/payloads/backlinks.json": os.path.join(PAYLOADS, "backlinks.json"),
    "data/payloads/gap.json": os.path.join(PAYLOADS, "gap.json"),
    "data/payloads/serp.json": os.path.join(PAYLOADS, "serp.json"),
    "data/payloads/mentions.json": os.path.join(PAYLOADS, "mentions.json"),
}
OPTIONAL = {"data/source-state.json": STATE}

AUDIT_DATE = "2026-09-14"
BASELINE = {"earned": 17, "owned": 10, "affiliate": 6, "syndication": 9,
            "directory_spam": 14, "local_aggregator": 4, "unresolved": 6}


class RebuildError(Exception):
    pass


def verify_inputs():
    missing = [name for name, path in REQUIRED.items() if not os.path.exists(path)]
    if missing:
        raise RebuildError(
            "cannot rebuild — these committed inputs are missing:\n  %s\n"
            "They are required, not optional. Commit them rather than working "
            "around their absence." % "\n  ".join(missing))
    absent_optional = [n for n, p in OPTIONAL.items() if not os.path.exists(p)]
    return absent_optional


def _run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode not in (0,):
        raise RebuildError("step failed (%d): %s\n%s\n%s"
                           % (r.returncode, " ".join(cmd), r.stdout[-2000:], r.stderr[-2000:]))
    return r.stdout


def rebuild_audit():
    out = _run([sys.executable, "pipelines/00_audit.py", "run",
                "--overview", os.path.join(PAYLOADS, "overview.json"),
                "--backlinks", os.path.join(PAYLOADS, "backlinks.json"),
                "--date", AUDIT_DATE])
    # Re-assert the Round 1 acceptance test on the rebuilt database rather than
    # trusting that the script printed something reassuring.
    conn = sqlite3.connect(DB_PATH)
    counts = dict(conn.execute(
        "SELECT link_class, COUNT(*) FROM audit_links GROUP BY 1").fetchall())
    conn.close()
    deltas = {k: counts.get(k, 0) - v for k, v in BASELINE.items()}
    bad = {k: d for k, d in deltas.items() if d != 0}
    if bad:
        raise RebuildError(
            "REBUILD CHANGED THE AUDIT. Classes off baseline: %s\n"
            "A rebuild that produces different numbers is worse than no "
            "rebuild — it would silently rewrite the project's baseline." % bad)
    return counts, deltas, out


def rebuild_discovery():
    _run([sys.executable, "pipelines/03_discover.py", "run",
          "--gap", os.path.join(PAYLOADS, "gap.json"),
          "--serp", os.path.join(PAYLOADS, "serp.json"),
          "--mentions", os.path.join(PAYLOADS, "mentions.json"),
          "--date", AUDIT_DATE])
    # 04_qualify exits 3 on its (expected, investigated) PBN stop condition.
    r = subprocess.run([sys.executable, "pipelines/04_qualify.py", "run",
                        "--date", AUDIT_DATE], cwd=ROOT, capture_output=True, text=True)
    if r.returncode not in (0, 3):
        raise RebuildError("04_qualify failed (%d)\n%s" % (r.returncode, r.stderr[-2000:]))
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM targets WHERE tactic!='audit_historical'").fetchone()[0]
    conn.close()
    return n


def restore_source_state():
    """Restore the 01_source rows. Without this the 14-day trend counter
    resets to zero on a cold start and looks identical to 'found nothing'."""
    if not os.path.exists(STATE):
        return 0, 0
    with open(STATE, encoding="utf-8") as fh:
        doc = json.load(fh)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    # Same DDL 01_source uses; harmless if already present.
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS source_items (
        source_key TEXT PRIMARY KEY, request_id INTEGER, platform TEXT,
        bucket TEXT, reason TEXT, requires_manual INTEGER, matched_terms TEXT,
        followed_tags TEXT, respond_url TEXT, journalist_name TEXT,
        journalist_email TEXT, muck_rack_url TEXT, media_website TEXT,
        category TEXT, deadline_date TEXT, deadline_time TEXT, time_zone TEXT,
        query_truncated INTEGER, gmail_id TEXT, run_date TEXT,
        deadline_utc TEXT, missed_on_arrival INTEGER DEFAULT 0,
        recipient TEXT, matched_expert TEXT, summary TEXT);
    CREATE TABLE IF NOT EXISTS source_runs (
        run_at TEXT PRIMARY KEY, run_date TEXT, messages INTEGER, items INTEGER,
        answerable INTEGER, marginal INTEGER, rejected INTEGER, new_items INTEGER,
        missed_on_arrival INTEGER DEFAULT 0);
    """)
    # Idempotent column migration. CREATE TABLE IF NOT EXISTS leaves an
    # existing table alone, so a database built before a column was added
    # never gains it — and the failure surfaces as "no such column" in the
    # middle of a run rather than at startup.
    for table, col, decl in (("source_items", "summary", "TEXT"),):
        have = {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)}
        if col not in have:
            conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, decl))
            conn.commit()

    def insert(table, rows):
        for row in rows:
            cols = list(row)
            conn.execute("INSERT OR REPLACE INTO %s (%s) VALUES (%s)"
                         % (table, ",".join(cols), ",".join("?" * len(cols))),
                         [row[c] for c in cols])
    insert("requests", doc.get("requests", []))
    insert("source_items", doc.get("source_items", []))
    insert("source_runs", doc.get("source_runs", []))
    conn.commit()
    n_i = conn.execute("SELECT COUNT(*) FROM source_items").fetchone()[0]
    n_r = conn.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0]
    conn.close()
    return n_i, n_r


def cmd_verify(_a):
    absent = verify_inputs()
    print("all %d required inputs present" % len(REQUIRED))
    for n in REQUIRED:
        print("  OK  %s" % n)
    for n in OPTIONAL:
        print("  %s  %s" % ("OK " if n not in absent else "--", n))
    if absent:
        print("\nnote: %s absent — the trend counter will start from this "
              "rebuild rather than carrying forward." % ", ".join(absent))
    return 0


def cmd_run(a):
    absent = verify_inputs()
    if os.path.exists(DB_PATH):
        if not a.force:
            raise RebuildError(
                "%s already exists. Rebuilding would discard whatever is in it. "
                "Pass --force if that is what you want." % DB_PATH)
        os.remove(DB_PATH)

    print("rebuilding from committed files only — no scratchpad is read\n")
    counts, deltas, _ = rebuild_audit()
    print("audit rebuilt:")
    for k in sorted(BASELINE):
        print("  %-18s %3d  (baseline %3d, delta %+d)" % (k, counts.get(k, 0),
                                                          BASELINE[k], deltas[k]))
    print("  ACCEPTANCE: delta +0 across all seven classes")

    n_t = rebuild_discovery()
    print("\ndiscovery rebuilt: %d target rows" % n_t)

    n_i, n_r = restore_source_state()
    if absent:
        print("\nsource state: NOT restored (%s absent)" % ", ".join(absent))
    else:
        print("\nsource state restored: %d items, %d runs" % (n_i, n_r))
    print("\nlinks.db rebuilt at %s" % os.path.relpath(DB_PATH, ROOT))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--force", action="store_true")
    r.set_defaults(fn=cmd_run)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    try:
        sys.exit(a.fn(a))
    except RebuildError as e:
        print("REBUILD FAILED\n%s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
