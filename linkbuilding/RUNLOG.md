# Link Building — RUNLOG

Append-only. One entry per round. Never edited retroactively.

Scoped to `linkbuilding/`. The repo-root `RUNLOG.md` belongs to the blog and
social-autoposter projects; `rounds/round-01.md` forbids writing outside
`linkbuilding/`, so link-building rounds log here rather than polluting it.

---

## Round 1 — build `00_audit` — 2026-09-14

**Objective.** Turn the one-off backlink audit in `reports/audit-baseline.md`
into a re-runnable pipeline that snapshots and diffs. Not to redo the analysis.

**Built.**
- `pipelines/00_audit.py` — classify / snapshot / diff / self-test
- `data/links.db` — 66 rows in `targets`, 66 in `audit_links`, 1 in `audit_runs`
- `data/snapshots/2026-09-14.json` — full per-link pull, archived
- `data/disavow-candidates.txt` — 14 domains, draft only
- `rounds/round-01.md` — the spec itself (see deviations)

**Acceptance test: PASSED, delta +0 in all seven classes.** 17 earned /
10 owned / 6 affiliate / 9 syndication / 14 directory_spam / 4 local_aggregator
/ 6 unresolved. No tolerance consumed. The earned set also matches the report
domain for domain — counts alone would not have proved the rules right.

**What happened vs plan.** The first live run failed the acceptance test at
syndication 18 (+9) and directory_spam 5 (−9), and stopped itself. Two real
bugs, both in rules I had written:

1. `near_identical` compared normalised anchors by character prefix. The
   scraper anchor `inhousewellness.com` normalises to `inhousewellnesscom`,
   which has healthline's `inhouse wellness` → `inhousewellness` as a prefix.
   Nine domain-list scrapers were therefore filed as scraper copies of the
   Healthline article. Fixed by comparing whole tokens and allowing extra
   tokens only when short enough to be a credential (`md`, `phd`).
2. Republication detection searched the whole `url_from`, host included, so
   every domain contained its own brand token and `trustedoptima.site` and
   `trustedoptima.website` were flagged as republications of each other. Fixed
   by searching the path only.

Both were caught by the acceptance test doing its job. The instruction not to
adjust the expected numbers is what forced the diagnosis; had the baseline been
editable, two wrong rules would have shipped looking green.

**Deviations from spec, all documented in code.**
- `unresolved` is evaluated before the heuristic classes, not last. As written
  the taxonomy makes `earned` the default after ruling everything else out,
  which leaves a trailing `unresolved` unreachable — the five paid-pattern
  links would have landed silently in `earned`. An assertion proves no
  carried-forward domain is reachable by any heuristic rule, so the reordering
  changes no count.
- Audit history lives in `audit_runs` / `audit_links`, created by the pipeline.
  `data/schema.sql` has no column for link class and is the outreach spine; it
  was not edited. `targets` is populated in parallel so later pipelines can
  query the live profile.
- The round spec did not exist in the repo or in any git history at the start
  of this round — it lived only as a chat upload. Committed to
  `rounds/round-01.md` so the next round is not blocked the same way. This is
  the same class of failure as the lost September snapshot: real state with
  nothing writing it down.
- Harness requires a RUNLOG entry; spec forbids writing outside
  `linkbuilding/`. Resolved in favour of the boundary — this file.

**Verification.** `self-test` covers the diff against a synthetic prior
snapshot (9 assertions) and the Hard Rule 8 guard (3). Separately, the diff was
proved end to end against a fabricated 2026-09-01 prior: a lost earned domain
surfaced at the top of the output, separated from a lost spam domain, with
anchor and rel changes detected. The fixture was deleted afterwards and the
clean run re-confirmed; `data/snapshots/` holds only the real snapshot.

**Rel attributes.** 45 follow / 21 nofollow from per-link data. The overview
claims 0 follow. All four priority links are follow. `OverviewGuard` raises on
any read of `follow`/`noFollow`, so Hard Rule 8 is enforced by the code rather
than by anyone remembering it.

**Not built, deliberately.** Pipelines 01–07. No outreach. No disavow
submitted. `audit-baseline.md` not rewritten — one section appended.

**Cost.** 2 Ubersuggest calls (`backlinks_overview`, `backlinks`). 0 Blotato
credits — this project does not touch Blotato. No retry needed on the per-link
call; `done: true` first attempt, both times.

**Friction.** Getting the live pull into a file the pipeline could read meant
re-serialising 66 rows by hand, because MCP results exist only in the session
and the script cannot call MCP. That is inherent to the agent-as-executor
split, but it is the slowest part of the round and the most error-prone. A
`--from-stdin` mode would not help; the data still has to be transcribed. Worth
considering whether `00_audit.py` should instead accept a pasted payload once
and cache it under `data/snapshots/raw/`.
