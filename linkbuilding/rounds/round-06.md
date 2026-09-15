# Round 6 — Durability and schedule correction

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-06.md` first.

> **Why now.** The Routine fires tomorrow in a session with no scratchpad. The
> `links.db` recovery last round depended on scratchpad files that won't be
> there. Fix that before the schedule goes live, not after it fails quietly.

## Scope — build ONLY these

- `linkbuilding/pipelines/rebuild.py`
- `linkbuilding/data/snapshots/` completeness audit
- Schedule correction (below)
- `linkbuilding/RUNBOOK.md`

No drafter. No HARO or Featured parser — still nothing to test against.

## 1. Durable rebuild

`links.db` is gitignored and was fully recreated last round, but only because
scratchpad files survived. A Routine-fired session has none.

Audit what `data/snapshots/` and `data/samples/` actually contain, then make
`rebuild.py` reconstruct `links.db` end to end **from committed files only**.
Prove it: move the scratchpad aside, rebuild, and confirm the Round 1 audit
still reproduces delta +0 across all seven classes.

If any input is missing from the repo, that is the finding — report it and
commit the file rather than working around it.

## 2. Fix the schedule

One fire per day at 13:07 UTC against a source sending up to three times daily
means afternoon queries wait ~20 hours. Deadlines in the current corpus are
same-day.

Move to three runs daily, spaced to follow SOS sends. `source_runs` is already
keyed on `run_at`, so this needs no schema change.

State the times you chose and why. If the Routines API can't express multiple
daily fires, say so — don't simulate it.

## 3. Cold-start assertions

A scheduled session has no conversational context. `01_source` must fail loudly,
not quietly, on: missing `links.db`, missing `claims.json`, an unreachable Gmail
connection, a Slack post failure, or a stale payload.

**A failed run must alert.** A pipeline that silently stops running looks
identical to a quiet niche, and this project is about to spend two weeks
measuring exactly that distinction.

## 4. RUNBOOK.md

Written for a session with no memory of this conversation: what runs when, how
to rebuild from scratch, the six inherited rules, the pinned
`connection_id 029715c5`, `#media` / `C0C26J8JX8U` (private — needs
`slack_search_public_and_private`), and the decision criteria from Round 5.

## Acceptance criteria

- [ ] `rebuild.py` reconstructs `links.db` from committed files with the
      scratchpad moved aside
- [ ] Round 1 audit reproduces delta +0 after rebuild
- [ ] Three daily runs configured, or the limitation reported
- [ ] Every cold-start failure alerts to `#media`, each demonstrated
- [ ] RUNBOOK.md standalone

## Stop and ask if

- A required input isn't in the repo and can't be regenerated
- The Routines API can't do multiple daily fires
- Attaching connectors to a Routine turns out to be API-doable rather than
  UI-only — report it, don't assume either way
