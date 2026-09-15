# Committed pipeline inputs

These are the raw API payloads every pipeline stage was originally built from.
They live in the repo because `links.db` is a gitignored build artifact and a
Routine-fired session has **no scratchpad** — without these, a cold start can
rebuild nothing.

| File | Source | Feeds |
|---|---|---|
| `overview.json` | Ubersuggest `backlinks_overview`, 2026-09-14 | `00_audit` |
| `backlinks.json` | Ubersuggest `backlinks`, 2026-09-14 (66 rows) | `00_audit` |
| `gap.json` | Ubersuggest `backlink_opportunity`, 2026-09-14 (60 rows) | `03_discover` |
| `serp.json` | Ubersuggest `serp_analysis`, 3 keywords | `03_discover` |
| `mentions.json` | Firecrawl search, unlinked mentions | `03_discover` |

## What is deliberately NOT here: the raw Gmail payloads

The two Gmail pulls are ~640KB and ~700KB of live mailbox content — full
message bodies, journalist names and addresses, and complete query text for
people who did not publish it to us.

Committing a mailbox dump to source control is a different act from committing
SEO data, and it is not needed: `01_source` exports the *derived* rows it
produced to `../source-state.json`, which is what `rebuild.py` restores. That
preserves the 14-day trend counter without putting a mailbox in git.

`data/samples/` holds seven representative raw messages, credential-redacted,
as the parser's ground truth. That is the intended footprint for real mail.
