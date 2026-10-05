# ❌ 01_source run FAILED — 2026-10-05

**Stage:** connector-probe

```
gmail: Gmail probe returned zero messages. An empty result set is what the WRONG mailbox returns, and what a stale registration returns. It is not proof of reachability. Probe FAILED.
```

## What this means

The run did NOT start: a connector could not be proved reachable. Today has no data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
