# ❌ 01_source run FAILED — 2026-09-23

**Stage:** preflight

```
1a0c58ee46c66b8e: digest declares 13 alert(s) but 10 were parsed. A dropped item is indistinguishable from a quiet day downstream.
```

## What this means

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
