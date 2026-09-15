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

---

## Round 2 — build `03_discover` + `04_qualify` — 2026-09-14

**Objective.** First acquisition round. Produce a ranked worklist of real,
contactable targets.

**Pre-flight (collision).** All 66 `00_audit` rows carried `tactic='audit'`,
`status='live'`. Round 2's tactics are disjoint, so no literal collision was
possible. Took the reserved-tactic option anyway: historical rows migrated to
`audit_historical`, and `00_audit.py` now writes that value, so `audit` is
never written by a working pipeline and a future source named `audit` cannot
silently drop a rediscovered domain. Chose rename over a discriminator column
because a discriminator means altering `schema.sql`, the outreach spine.
Separately, all 66 already-linking domains are excluded from discovery as
opportunities — a logic filter, not an index one.

**Result. 83 discovered → 31 qualified → 52 rejected.** Within the 25–200 band.

| Source | Discovered | Qualified |
|---|---|---|
| gap | 59 | 8 |
| roundup | 16 | 16 |
| resource_page | 0 | 0 |
| mention | 2 | 1 |
| dealer | 6 | 6 |

**Two bugs caught by the round's own stop conditions.**

1. Six dealer rows were being auto-rejected as `below_floor`. The composite
   floor was built for crawled prospects and should never have applied to
   manually seeded human applications. Dealer rows now bypass the floor and
   sit at `queued`.
2. `goldendesigninc.com` was silently dropped by the competitor screen — Golden
   Designs is both a manufacturer we want a dealer page from and an organic
   competitor of the store. The competitor and marketplace screens now apply to
   crawled candidates only; Hard Rule 1 still applies to seeds. Caught by the
   self-test asserting six dealer entities, not by inspection.

**Open stop condition — `template_link_pattern` = 73% of rejections.** Not
overridden. Verified twice against live data instead: `cvillico.com` (DA 63,
0 organic visits, 0 organic keywords, 32,989 backlinks from 652 domains) and
`theforbestimes.com` (DA 56, 0 visits, 0 keywords, 580 domains). Thirty-eight
distinct domains serve the identical path `/all/1298/16.html` or
`/all/1298/17.html`. The rule is correct; its share reflects an input dominated
by one PBN pointed at havenofheat.com. Surfaced for a human decision rather
than silently passed.

**`resource_page` returned zero.** The SERP source produced 16 rows, all
classified `roundup`; no title in three keyword sets matched resource-page
language. Reported rather than papered over by loosening the classifier.

**Organic traffic.** Measured for three ambiguous high-DA candidates only —
one call per domain is 80+ calls at tier1. Where traffic is unknown the
inflated-authority rule does NOT fire and the row is flagged
`traffic not measured`. Rejecting a real publisher on data never fetched is
precisely the confident false positive this project keeps hitting.

**API friction.** `backlink_opportunity` returned `done:false` with an empty
array five times at `limit` 50 and 100, and only produced rows at `limit: 20`.
`sunvalleysaunas.com` never built at all, so the gap source rests on one
competitor. Worth pinning `limit: 20` in any future discovery run and treating
a second competitor as a separate pass.

**Not built.** Pipelines 01, 02, 05, 06, 07. Nobody contacted. No outreach
drafted.

---

## Round 3 — build the claim bank — 2026-09-14

**Objective.** Make Dr. Alptunaer's conditional approval operational: a cited,
structured claim bank that `01_source` can assemble pitches from, and nothing else.

**Built.** `data/claims.json` (30 claims, 47 citations, 26 unique papers),
`pipelines/lib/claims.py` (load / validate / query / drift-check / report),
`reports/claim-bank-review.md` (633 lines, ~4,700 words, ~19 min read).
Also committed `rounds/round-03.md` — the third consecutive spec that never
reached the repo.

**Citation discipline.** Ten literature searches across the topic areas, then
**26 `inspect_paper` calls — one per cited paper.** Nothing was written from
memory and no DOI was constructed. Every stored title is the exact string the
tool returned.

**Tier distribution.** strong 8 (27%), moderate 15 (50%), preliminary 7 (23%).
No tier above 80%; `claims.py stats` emits the stop condition if one ever is.

**Drift check, proven both directions.** Self-test covers 17 integrity
assertions including a deliberately corrupted title. Then run live against the
real bank: 26 ids re-resolved, 47 citation instances passed; corrupting a
single title made it fail on every claim citing that paper, which is the
behaviour that matters — one bad id surfaces everywhere it is used.

**Honesty decisions worth recording.**

- `heat-vascular-limits-01` records the 2023 randomised trial that found sauna
  did NOT improve vascular function in coronary artery disease, alongside the
  positive observational cohort work. A source who volunteers the trial that
  failed is more credible than one who does not.
- `cold-hypertrophy-limits-01` records that cold immersion blunts muscle growth
  — a finding that argues against a product the store sells.
- `safety-pregnancy-01` and `-02` genuinely disagree. Both are in the bank with
  the conservative reading governing both hedges, rather than picking the
  flattering side.
- `journal` is derived from the verified DOI prefix, not returned by
  `inspect_paper`, and says so in the file. `n` is only populated where the
  returned abstract stated it; 0 means not stated and was NOT inferred.
- `pmid:3218894` has no DOI at all. Stored PMID-only; `claims.py` requires one
  resolvable identifier, not both.

**Gaps left open deliberately.** Sauna-specific sleep evidence (the usable
pooled data is warm baths, and the claims say so); cold exposure and immune
function (no human evidence worth a physician's name); detoxification
(supportable only from marketing — excluded and named in do-not-say lists);
product comparisons (no head-to-head trials exist).

**Friction.** `inspect_paper` returns no journal field, so journal had to be
derived from the DOI prefix and flagged as derived. Sample sizes are
inconsistently present in returned abstracts, so most `n` are 0. If Round 4
wants reliable n, `read_paper` would need a pass per citation — roughly 26 more
calls.

**Not built.** `01_source`. No pitches written. Nobody contacted. The bank is
`awaiting_review` and carries no approval until a human signs it.

---

## Round 3a — claim bank data-integrity fixes — 2026-09-14

Two corrections before the bank goes to Dr. Alptunaer, plus one attempted fix
that could not be completed.

**1. `journal` is now null throughout, and `journal_source` is retired.**
Deriving journal from the DOI prefix was unsafe and I should not have shipped
it: prefix `10.1001` covers JAMA, JAMA Internal Medicine and JAMA Cardiology
alike, and the bank asserted two different journals from that one prefix. A
single wrong venue spotted by a clinician would cost confidence in all 47
citations, not just the wrong one. Neither `inspect_paper` nor `read_paper`
returns a journal field for this corpus, so the field is null and the DOI
stands alone. `claims.py` now RAISES if `journal_source` reappears — a value
that needs a provenance caveat should not be displayed at all.

**2. `n: 0` sentinel replaced with null.** Renders as "sample size not stated".
`claims.py` rejects a literal 0, a negative, or a string. A reviewer reading
"0 participants" sees a bug, and Round 4's assembler could have formatted or
filtered on it silently.

**3. ⚠️ Real sample sizes could NOT be retrieved. `read_paper` has no full text
for this bank.** Five probes across `pmid:`, `pmcid:` and `doi:` forms —
including open-access PLOS ONE and PMC papers — all returned
"(no full-text passages available for this paper)". The planned ~26 calls would
have returned nothing, so they were not run.

What this means for the review: **12 of 47 citations carry a sample size**,
taken verbatim from retrieved abstracts (16, 21, 9, 674, 10, 77 and their
reuses). The other 35 read "sample size not stated". Nothing was inferred,
summed from subgroups, or recalled. Notably the anchor citation
(Laukkanen 2015, PMID 25705824) has NO stated n in the retrieved abstract — its
abstract gives three subgroup counts and no total, and summing them assumes the
groups are exhaustive and non-overlapping, which is an inference rather than a
retrieved fact.

The review document now carries a "What this document cannot tell you" section
stating both limits in the clinician's own terms, and directs him to the DOI
where the venue or the cohort size matters to his judgement.

**Verification.** claims.py self-test now 26 assertions (was 17), including the
n=0 sentinel, negative n, string n, retired journal_source, and three rendering
checks proving null never prints as "None" or "0". Live drift check still
passes on all 47 citations. The pre-fix record shape is now actively rejected.

---

## Round 4 — build `01_source` (filter only) — 2026-09-15

**Objective.** Ingest, parse, filter, report. No drafting, no pitching, no
sending. Spec committed to `rounds/round-04.md` and pushed BEFORE any build
work, since three prior rounds had their spec fail to reach the repo.

**Result. 13 messages → 23 items → 0 answerable, 4 marginal, 19 rejected.**
Zero answerable is reported as the result, not treated as a bug. The filter
was tightened during the round, never loosened.

**All six inherited rules asserted in code, 27 self-test assertions passing.**
Rule 1 rejects the support@ connection id and a null id. Rule 2 raises on a
wrong or absent `Delivered-To`. Rule 3 raises on zero rows rather than
reporting an empty inbox. Rule 4 raises if the bare `Media` parent is dropped
from scope. Rule 5 is tested by inspecting `route.__code__` — the compiled
constants, not the source text, because the docstring legitimately contains
the word "subject" and a text scan flagged its own documentation. Rule 6 is
enforced by a closed alternation over the ten real fields plus an explicit
post-parse assertion.

**HTML vs plaintext, answered: the HTML does NOT carry the untruncated query.**
Both parts truncate at the identical point — plaintext ends `"due to the q..."`
and so does the HTML. The HTML is ~5x larger, but that is markup. Three of
five captured Qwoted requests truncate at exactly 420 characters. Plaintext is
the parse target: same content, a fifth of the bytes. This strengthens rather
than weakens `requires_manual` — the email cannot tell you who to contact OR
what they fully asked.

**Three bugs found and fixed, all caught by tests rather than inspection.**

1. `MUCK RACK URL` appeared absent on 5 of 18 SOS items. Investigation showed
   the LABEL is present on all 18 and the VALUE is blank on 5 — a source-side
   fact, not a parse failure. `field_coverage` now reports label-presence and
   value-presence separately, because Round 5 needs to know which fields it
   can depend on. Forcing "all ten fields populated" would have been a false
   guarantee.
2. The filter matched substrings, so `spa` matched inside "**Spa**rk Kids" and
   turned a children's conversation-card deck into a wellness lead. Now
   whole-word matching.
3. The filter's haystack included `category` and `outlet`. The SOS category
   "Lifestyle and Fitness" was matching the term `fitness` and promoting
   unrelated gift-guide requests to `marginal`. A filter that reads the folder
   name instead of the question measures the wrong thing. Haystack is now
   subject matter only.

Fixes 2 and 3 cut marginal from 9 to 4. Both TIGHTEN the filter. The spec
forbids loosening to manufacture hits; tightening against false positives is
the opposite, and necessary for the rejection log to mean anything.

**Also fixed:** SOS plaintext renders links as `value (mailto:value)`. The
duplicate is now stripped at parse time rather than left for every downstream
consumer — including anything that would eventually send to the address.

**The four marginals**, for the record: two Famadillo gift guides that
genuinely contain "self-care"/"wellness" but want product samples, the VICE
"October Theory" request (the only real wellness-adjacent item in the corpus,
and the one produced by the corrected Qwoted tags), and a Parade Pets query
about cats sleeping that matches `sleep` honestly and is still noise.

**Idempotency.** `source_items.source_key` is the primary key
(`sos:<gmail_id>:<item_no>` / `qwoted:<gmail_id>`). Re-running the same
payload inserts 0 rows; verified.

**Not built.** No HARO or Featured parser — neither has sent a request, so
neither could be tested. No drafter. Nothing sent, mailbox unmodified.

**Friction.** The Gmail payload is ~638KB and cannot come back through the
tool channel; it lands in a tool-results file that has to be copied to the
scratchpad before the pipeline can read it. Fine for a manual run, but Round 5
should expect the relay to be a file path, not an inline argument.

---

## Round 5 — scheduling and evidence accumulation — 2026-09-15

**Objective.** Make `01_source` run unattended and accumulate evidence toward
two decisions: keep the pipeline, and buy Qwoted Pro or not. No drafter.

**Built.** `pipelines/lib/relay.py`, deadline parsing and miss tracking,
answerable alerting, `reports/source-trend.md` with the decision criteria
fixed in the header before any data arrived.

**Scheduling: a durable daily Routine, not cron.** `CronCreate` is explicitly
session-only ("gone when this Claude session ends") and this is an ephemeral
container, so it would have been theatre. Routines are account-level and fire
a fresh session with MCP available, which is required because the Gmail call
can only be made from inside an agent session.

**Alerting: Slack #media (C0C26J8JX8U), a PRIVATE channel.** I first reported
that no channel existed. That was wrong: `slack_search_channels` defaults to
public channels only, so a private channel is invisible unless you pass
`channel_types` including `private_channel`. The user supplied the ID. Noted
in code so the next person does not repeat it. The pipeline writes
`reports/ALERT-answerable.md` plus a compact `.slack.txt` body, and DELETES
both when there are no answerable items — a stale alert is worse than none.
Demonstrated with a synthetic item, then removed; both files self-cleared.
Channel verified by posting the round's FYI digest.

**Runs table re-keyed on `run_at`, not `run_date`.** SOS sends up to three
times daily and two Qwoted deadlines in the current corpus expire within 25
minutes of each other. Keying on date would have silently discarded every run
after the first each day — exactly the measurement the round exists to make.

**Deadlines: 23 of 23 parsed, none guessed.** An unrecognised timezone yields
null rather than an assumed offset, because a deadline computed from a guessed
offset mis-ranks urgency invisibly. Misses on arrival: 0 so far.

**⚠️ I deleted `links.db` while rebuilding for this round, which dropped the
Round 1 audit tables and the Round 2 targets.** Recovered by re-running
`00_audit`, `03_discover` and `04_qualify` from the original verified payloads
still in scratch. The audit reproduced with delta +0 in all seven classes, so
nothing was lost — but that was luck of timing, not design. The DB is
gitignored as a build artifact and the snapshot is the real source of truth,
which is the only reason this was recoverable. Round 6 should not assume the
scratchpad survives.

**Pre-flight — the four proven links all post-date the HARO relaunch.**
eatthis 2026-01-20, healthline 2026-02-17, womansworld 2026-03-11, singlecare
2026-07-02. All four fall in the April-2025-or-later Featured-operated era,
none in the Cision era or the Connectively dead zone. The channel that
produced them is live, and the most recent is ten weeks old. That materially
changes how a zero result should be read: this is not a dead channel, it is a
live channel not currently reaching the inbox.

**Not built.** No drafter, no pitches, nothing sent, mailbox unmodified.

**⚠️ The daily Routine was created but CANNOT RUN AS-IS.**
`trig_01JTW5ufQ4xb4fvmS2G2TwSX`, daily 13:07 UTC, first fire 2026-09-16.
The API returned: *"this trigger stores no MCP connectors, so the sessions it
fires will run without connector (mcp__*) tools."* The fired session would
therefore have neither the Zapier Gmail tool nor Slack — it cannot fetch the
payload and cannot alert. The remedy the API names is to attach connectors
from the claude.ai Routines UI. Reported rather than left to fail silently
every morning at 13:07.
