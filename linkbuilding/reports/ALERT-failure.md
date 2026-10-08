# ❌ 01_source run FAILED — 2026-10-08

**Stage:** preflight

```
COLD-START PREFLIGHT FAILED:
  - Connector probe is 2037 min old (limit 30). A probe from an earlier session proves nothing about this one — Routine sessions carry their own OAuth registration. Re-probe.
```

## What this means

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
