# ❌ 01_source run FAILED — 2026-09-28

**Stage:** gmail-fetch

```
Zapier MCP timed out (60s) then 'session expired' on 3 consecutive gmail_find_email calls; no payload fetched
```

## What this means

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
