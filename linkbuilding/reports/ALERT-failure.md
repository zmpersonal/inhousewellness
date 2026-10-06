# ❌ 01_source run FAILED — 2026-10-06

**Stage:** preflight

```
COLD-START PREFLIGHT FAILED:
  - links.db is missing. It is a gitignored build artifact — run `python3 pipelines/rebuild.py run` to reconstruct it from committed files. Do NOT proceed: a fresh empty database would reset the 14-day trend counter to zero and look like a quiet week.
  - Connector probe is 1440 min old (limit 30). A probe from an earlier session proves nothing about this one — Routine sessions carry their own OAuth registration. Re-probe.
```

## What this means

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
