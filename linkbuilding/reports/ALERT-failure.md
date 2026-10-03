# ❌ 01_source run FAILED — 2026-10-03

**Stage:** gmail-fetch

```
Zapier gmail_find_email (connection 029715c5) failed 3x: one 60s timeout, two 'connection closed: message too large or could not be parsed'. No payload obtained; run not started.
```

## What this means

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
