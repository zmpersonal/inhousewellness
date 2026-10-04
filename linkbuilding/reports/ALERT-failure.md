:x: *01_source FAILED* — 2026-10-04

*Stage:* fetch (Gmail via Zapier `gmail_find_email`, pinned connection 029715c5…)
*Error:* The Gmail response is too large for the MCP transport. Two attempts each closed the Zapier connection ("message from the server was too large or could not be parsed") before any payload could be staged; one earlier attempt timed out at 60s. The database was rebuilt fine (1067 items, 43 runs restored), so this is purely the fetch.

The run did not complete, so today has NO data. This is not a quiet day — treat the trend line as having a gap. Likely needs a narrower per-sender or date-windowed query (see RUNBOOK "Backfill" for the per-sender pattern).
Runbook: linkbuilding/RUNBOOK.md
