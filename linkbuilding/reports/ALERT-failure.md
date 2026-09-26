# ❌ 01_source run FAILED — 2026-09-26

**Stage:** preflight

```
Connectively rows marked non-manual without a relay address: ['connectively:1a0cfe6fa616cf47:6', 'connectively:1a0cfe6fa616cf47:7']. The magic-link is an auth redirect, not a reply path, and no address may be constructed from the outlet name.
```

## What this means

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap.

## Why this is an alert and not a log line

A pipeline that stops running looks identical to a niche with no relevant requests: zero answerable items, every day. The 14-day decision in `reports/source-trend.md` depends on telling those apart, so a failed run must be visible, and the trend must be read as having a gap rather than a quiet day.

See `linkbuilding/RUNBOOK.md` for recovery.
