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

---

## Round 6 — durability and schedule correction — 2026-09-15

**Objective.** Make the pipeline survive a cold Routine-fired session, and fix
a cadence that would have missed same-day deadlines.

**The snapshot audit finding: five required inputs were not in the repo.**
`data/snapshots/` and `data/samples/` were complete for what they cover, but
`links.db` could not be rebuilt from committed files alone. `overview.json`,
`backlinks.json`, `gap.json`, `serp.json` and `mentions.json` existed only in
the scratchpad — the Round 5 recovery worked purely because that session's /tmp
happened to survive. All five are now committed under `data/payloads/` (43KB
total) with a README explaining what feeds what.

**What was deliberately NOT committed: the two raw Gmail payloads** (640KB and
700KB of live mailbox — full bodies, journalist names and addresses, complete
query text). Committing a mailbox dump to source control is a different act
from committing SEO payloads. Instead `01_source` now exports its own derived
rows to `data/source-state.json`, which is what `rebuild.py` restores. That
preserves the 14-day trend counter without putting a mailbox in git.

**`rebuild.py` proven cold.** Scratchpad moved aside entirely, `links.db`
deleted, rebuild run: **delta +0 across all seven classes**, every class
identical to the committed snapshot, 83 target rows, trend restored. The
rebuild re-runs the real pipelines rather than replaying their output, so the
Round 1 acceptance test is exercised on every rebuild and raises if the numbers
move — a rebuild that quietly rewrote the baseline would be worse than none.

**Schedule: 3x daily at 11:37 / 18:37 / 21:37 UTC.** The Routines API accepts a
cron hour list, so one Routine expresses all three. Spacing follows the
observed sends: SOS morning 10:32, SOS afternoon 17:35, plus an evening
catch-all. The old single 13:07 fire would have left afternoon queries ~20
hours; the tightest deadline in the corpus was a Qwoted request arriving 14:38
with a 20:00 deadline.

**Stop-and-ask answered: connectors are NOT API-attachable for this org.**
Tested directly with `connectors: ["Gmail","Slack"]` — returned *"the
connectors parameter is not available for this organization"*. So it is the
claude.ai Routines UI or nothing. The probe errored, so no stray Routine was
created; verified by listing. **The Routine still has `mcp_connections: []` and
every fire will fail until connectors are attached in the UI.**

**Cold-start assertions, all five demonstrated.** Missing `links.db`, missing
`claims.json`, wrong Gmail connection, stale payload, absent payload — each
exits 4 and writes `reports/ALERT-failure.md` plus a Slack body. A successful
run clears them. The reason this is an alert rather than a log line: a pipeline
that stops running produces the same observable as a quiet niche — zero
answerable, every day — and the 14-day decision depends on telling those apart.

**RUNBOOK.md** written for a session with no memory: what runs when and why
those times, how to rebuild, the six inherited rules plus the seventh learned
last round (Slack channel search defaults to public only), the pinned
connection id, the alert routing, and the decision criteria with the context
that the proven channel is live but silent.

**Not built.** No drafter. No HARO or Featured parser — still nothing to test
against. Nothing sent, mailbox unmodified.

### Round 6 amendments — multi-recipient, expert roster, HARO hunt

**Multi-recipient.** Rule 2 now asserts membership in `EXPECTED_RECIPIENTS`
(`media@`, `timur@`, `tripler@`), defined once. Recipient persisted per item.
Sublabels stay keyed on platform — the platform selects the parser, the
recipient is already in the headers.

**HARO hunt — the subscription was never on media@, and never received a
digest.** Searching all addresses, including spam and trash, and Featured's
real sending infrastructure (`mail.helpareporter.com`, `clkmail.`, `send.`,
`rmta.net`) found six messages total:

- 12 Jan 2026 "Your sign up link" -> **julian@inhousewellness.com**
- 13 Jan 2026 "Your HARO **Journalist** Profile Is Ready to Claim" -> julian@
- 21 Jan 2026 "Your sign in link" -> julian@
- 15 Sep 2026 "Welcome to HARO – Please Verify Your Email" -> media@ (unverified)

Two findings. First, the historic subscription is on **julian@, which is NOT
in the new recipient set** — if digests ever arrive there the pipeline will
reject them. Second, and more important: **no HARO query digest has ever
arrived at any address.** The January mail is signup and sign-in only, and the
profile offered was a JOURNALIST profile, not a source profile. If the account
was created on the journalist side it would never receive source queries,
which would explain four proven links from that window with no digest traffic
to show for it. Worth checking before concluding anything about volume.

`timur@` and `tripler@` have zero mail in this mailbox — nothing addressed to
or delivered to either. Either brand-new aliases or separate mailboxes this
connection cannot see; not determinable from here.

**Two-expert roster + retroactive re-score.** `data/experts.json` holds both
experts and the attribution rule. Re-scoring all 24 already-ingested items,
no new ingestion:

| | answerable | marginal | rejected |
|---|---|---|---|
| Alptunaer (cited) | 0 | 4 | — |
| Tripler (experience) | 3 | 3 | — |
| Neither | — | — | 14 |
| **Combined** | **3** | **7** | **14** |

Previous single-roster figure was 0 / 4 / 20.

**So the answer is: partly a single-expert filter, not purely a quiet niche.**
Three items became answerable, all Tripler's, none clinical. The strongest is
a podcast seeking *women solopreneurs with a business they genuinely care
about* — squarely hers. Dr. Alptunaer's count did not move: still zero
answerable in 24 items over 36 hours. The clinical niche remains quiet.

**One self-correction inside the round.** The first Tripler pass produced 4
answerable by matching single generic words — a Pet Age story about the
holiday toll on pet industry *employees*, and a Toronto podcast wanting retail
and tech *leaders* in person. Neither is a business-operations query for a
health coach. Same failure as `spa` inside "Spark Kids" in Round 4, fixed the
same way: specific anchors decide, generic words only support. That tightening
moved Tripler from 4 answerable to 3, and the 3 survive scrutiny.

Clinical attribution audit on the live data: zero violations.

---

## Round 7 — make silent failure impossible — 2026-09-15

**Objective.** A scheduled run had exited 0, reported success and persisted
nothing. Make that detectable the same day rather than on day 14.

**Built.**
- `probe` subcommand — connector reachability from raw results, both connectors
- `verify-push` subcommand — confirms the run is readable out of the remote commit
- daily heartbeat to `#media`, approval-gated alerting, unparsed-platform flag
- 39 new self-test assertions (`self-test` now covers every §1–§4, §6 path)

**Demonstrated, not asserted.**

| Failure | Result |
|---|---|
| Commit that was never pushed | exit 5, alert written |
| State uncommitted (output in no commit) | exit 5, alert written |
| Ref advanced but the commit does not carry the run | exit 5, alert written |
| Branch absent on origin (live remote) | exit 5, alert written |
| Slack `channel_not_found` | probe exit 4, run refuses to start |
| Gmail zero rows / wrong recipient / tool error / prose | probe exit 4 |
| Probe older than 30 min, or future-dated | run refuses to start |
| Real push | verified, 6 of 6 runs found in the remote state file |

**§6 — the alert that should not have fired.** The previous run alerted on 3
answerable items, all matched against Tripler's provisional topic set
(`approved: false`, agent-authored, never reviewed). Nothing could have been
sent from any of them and all 3 would have re-alerted every run. Immediate
alerts now require an approved expert. Both experts are unapproved, so the
correct current state is **zero immediate alerts and one heartbeat a day** —
which is what ran. The stale alert file was removed automatically and the
heartbeat posted to `#media` (`p1789505689944949`).

**§4 — HARO: the finding is that there is nothing to parse.**
Five HARO/Featured messages exist across the whole mailbox and **none is a
query digest**. All five are account lifecycle; captured to `data/samples/`
with auth tokens redacted and nothing else. No parser written, per spec.

🔴 **The `media@` HARO account is NOT verified.** "Welcome to HARO – Please
Verify Your Email" arrived 2026-09-15 18:37 UTC and the link is unclicked. No
digest can arrive until a human clicks it; I did not, as it is an outward-facing
action on a third-party account. Separately, the January signup is on `julian@`
(outside `EXPECTED_RECIPIENTS`) and the profile offered was a **journalist**
profile, which receives no query digests at all.

**§5 — criteria recalibrated.** The 14-day clock starts on the first HARO
digest, not the first run, and has therefore **not started**. All four proven
links came through HARO on a contractor's own account; none came through SOS or
Qwoted, so a zero from those two is not evidence about the channel that earned
every link this site has. Expected rate is a handful of answerable per month —
a day or a week of zeros is not a signal.

**§7 — `PushNotification` diagnosed and working.** `status` is a schema
*const*: `"proactive"` is the only value that validates, so any other value
(including `"normal"`, and omitting it) fails regardless of the message. That
is the whole of the "errors regardless of input" behaviour. Verified live. When
Slack is not confirmed reachable the script now names this fallback explicitly
instead of printing instructions to post to the channel that is down.

**Six runs recorded on 2026-09-15.** Four are development re-runs of the same
payload during this round; all inserted 0 new rows. They are left in the record
rather than deleted — the decision counts verified *days*, not runs, and
pruning the run table to look tidier is the wrong instinct in this project.

**Not built.** No drafter, no HARO parser, no Featured parser. Nothing drafted,
nothing sent, mailbox unmodified.

---

## Round 8 — HARO and Connectively parsers — 2026-09-18

**Objective.** Parse the two platforms that had never sent a digest when
Round 7 ran, and start the 14-day clock on the channel that actually earned
this site's links.

**Precondition checked before building.** Round 7 found zero HARO digests and
an unverified signup. Three days later: **8 HARO query digests** (3/day since
2026-09-15 21:07) and **2 Connectively alert digests**. The verification mail
arrived 18:37 and the first digest followed at 21:07 the same day, so the
signup is verified. Precondition met; neither stop-and-ask fired.

**Built.**
- `pipelines/lib/parsers/haro.py` — tested against **8** digests
- `pipelines/lib/parsers/connectively.py` — tested against **2** digests
- routing, label scope, deadline parsing and ingest wiring for both
- 10 raw digest samples in `data/samples/` (auth tokens redacted, nothing else)
- 38 new self-test assertions

**Format variance — answered explicitly, per platform.**

| | HARO | Connectively |
|---|---|---|
| Digests compared | 8 | 2 |
| Items per digest | 20–21 | 4–7 |
| Structure varies between sends? | **No** | **No** |
| Core fields on 100% of items, every send | `name` `category` `email` `media_outlet` `deadline` `query` | `query` `outlet` `deadline` `respond_url` |
| Optional | `haro_journalist_profile_url` (14–21 of 20–21) | `category`, relay address |
| New fields introduced by any send | none | none |

**Reply paths — classified, never constructed.**
- **HARO: direct.** Every one of 162 items carries `reply+<uuid>@helpareporter.com`,
  a real routing mailbox. 162/162 read out of the mail; `requires_manual: false`.
  This is why HARO produced all four proven links.
- **Connectively: manual.** Q&A items offer only a single-use magic-link auth
  redirect. 0 of 11 Q&A items carry an address. The only addresses seen are
  third-party `send+<id>@tmxmessenger.com` relays on syndicated *opportunity*
  items. `ingest` raises if a Connectively row is ever non-manual without one.

**Two bugs found by testing, not by reading.**
1. `HARO Journalist Profile URL` **wraps** — when the URL is long the label sits
   alone and the value is on the next line, so a same-line capture recorded a
   present field as blank. That is "absence taken as a value" again. Fixed.
2. HARO writes **bare zone abbreviations** (`6:00 PM ET`), ambiguous between
   −5 and −4. Returning `None` would blind `missed_on_arrival` on the only
   channel that matters; hardcoding one would be wrong half the year. Resolved
   by the actual US civil-time rule (2nd Sunday March → 1st Sunday November).
   Not a guess — a definition.

**Featured/Connectively consolidation: RESOLVED, and the answer is keep both.**
Same product, but the sending domains still differ (`featured.com` vs
`connectively.us`) and the spec's own condition was "retire unless the domains
differ". They do. `Media/Featured` stays a route; retiring it would mean a
Featured-domain digest lands nowhere and is counted as nothing.

**The clock started 2026-09-15.** Recorded in `RUNBOOK.md`, in the trend
header, and as `HARO_CLOCK_START` in code. Day 4 of 14.

**HARO's rate, reported separately — and two findings it surfaces.**

| Channel | Rows | Distinct | Answerable rows | Distinct answerable | Rate |
|---|---|---|---|---|---|
| HARO | 162 | 112 | 11 | 9 | 8.0% |
| SOS | 60 | 39 | 6 | 5 | 12.8% |
| Connectively | 11 | 11 | 1 | 1 | 9.1% |
| Qwoted | 9 | 9 | 1 | 1 | 11.1% |

1. **HARO repeats queries across its three daily editions — 31% duplication**
   (162 rows, 112 distinct reply addresses). The dedup key is per-digest and
   cannot see across editions. Rows and distinct requests are now reported side
   by side rather than picking one. Cross-edition dedup was **not** built: out
   of scope, and changing the dedup key changes what every historical count
   means. Proposed for Round 9.
2. **Zero clinical answerables in 162 HARO items.** Dr. Alptunaer drew 14
   *marginal* on HARO and nothing answerable. The single clinical answerable in
   the entire corpus came from **Connectively** (`infrared`, red light therapy).
   All 11 HARO answerable rows are Tripler-provisional and most matched on the
   bare word `founders` — including a Holiday Stocking Stuffers gift guide.
   Same single-generic-anchor failure `employees` produced in Round 6. **The
   filter was not tuned.** Tuning it to move a count is the one thing this
   project forbids, and the anchor list is precisely what Tripler's review
   document already asks her to fix.

**Alerting held correctly.** 19 answerable, all provisional, **zero immediate
alerts**, one heartbeat. The Round 7 gate did its job on a 3.5× larger corpus.

**Not built.** No drafter. No changes to SOS or Qwoted parsing. No filter
tuning. No cross-edition dedup. Nothing drafted, nothing sent, mailbox
unmodified.

**Friction.** The `stable` verdict I wrote first compared "fields present on
every item", which flags an optional field as structural variance the moment
one send happens to populate it fully — it reported `stable: False` on a
corpus that was in fact stable. Measuring the wrong thing confidently is the
recurring shape of this project's near-misses, and the fix was to define the
core field set explicitly rather than infer it.

---

## Round 9 — dedup, and test the bank-scope hypothesis — 2026-09-18

**Objective.** Dedup HARO's cross-edition repeats, then dump the evidence that
decides whether `claims.json` is mis-scoped or HARO is simply quiet.

**1. Dedup — and the key is per platform, which was measured, not assumed.**

"Dedup on reply address" is right for HARO and wrong everywhere else:

| | What the address is | Evidence |
|---|---|---|
| HARO | the **query** (`reply+<uuid>@`) | 162 rows, 112 addresses, **0** addresses carry two different queries |
| SOS | the **person** | 9 addresses carry >1 different query (`paigecerulli@gmail.com`: 4 rows, 4 different queries) |

So HARO keys on the address; SOS keys on (address, query text); Connectively
and Qwoted key on `source_key`. Applying one key to all four would have cut
SOS from 58 real requests to 39 and called it deduplication.

**This corrects a number I published in Round 8.** That round's "Distinct"
column keyed everything on the reply address and reported SOS as 39 distinct /
12.8% answerable. Correct figures: **58 distinct, 10.3%**. HARO's 112 and 9
were right.

Answerable moved 19 rows → 17 distinct (delta 2, HARO 11 → 9). The stop-and-ask
triggers at *more than* 2, so it did not fire.

The trend is recomputed from the stored item rows rather than the historical
per-run counters, and carries a standing banner: every figure before
2026-09-18 was a row count.

**2. The evidence — `reports/haro-corpus-review.md`.**

Of 112 distinct HARO requests:

| Tier | | Count | Share |
|---|---|---|---|
| A | within the general competence of a practising physician | **9** | 8% |
| B | medical, but gated on a specialty the roster does not state | 16 | 14% |
| C | outside any medical scope at all | **87** | 78% |

**The hypothesis is half right, and the half it gets wrong matters more.** The
bank *is* narrower than the expert — widening it from the product to general
medicine takes HARO from 0 reachable to at most 9 over four days, about two a
day, which is the difference between a dead channel and a working one. But 78%
of the corpus is gift guides, road trips, baking pans, Christmas trees and
CISO cybersecurity. HARO is a general press-query newsletter with a health
category, not a medical channel. Fixing the scope gets roughly 2/day. It does
not get 20.

**Tier B cannot be settled here.** 16 requests are squarely medical but need a
named specialty, and `experts.json` records Dr. Alptunaer as `MD` with no
specialty stated. If he is a dermatologist, A becomes 13. That is the cheapest
single fact that would sharpen every number in the report.

**Two concrete defects the corpus exposed — neither fixed, both out of scope.**

1. **The same question, opposite outcomes, decided by one word.** Red light
   therapy for skin arrived on both platforms the same week. Connectively said
   "red or *near-infrared* light" → matched `infrared` → answerable. HARO said
   "*light-based* skin treatments" → matched nothing → rejected. The gate is
   keyed to product vocabulary, not to subject matter.
2. **`infrared` is in the filter and in NO claim in the bank.** The pipeline
   printed *"modality ['infrared'] named; the claim bank covers this directly."*
   It does not: zero of 30 claims mention infrared and zero concern skin. The
   one clinical answerable in the entire corpus is a match on a keyword with
   nothing behind it — it would have been pitched under a physician's name with
   nothing to say. The filter's vocabulary and the bank's contents have drifted
   apart and nothing checks that they agree.

**Method note.** The competence classification is a judgement, not a code gate.
It is committed as `data/haro-corpus-classification.json`, published per item
in the report, and feeds nothing — so a reviewer who counts differently can
disagree on the rows rather than on the total.

**Not changed.** Filter, claim bank, anchor lists, thresholds, experts.json —
all untouched. No drafter. Nothing drafted, nothing sent, mailbox unmodified.

**Friction.** The round's framing ("both cannot be right") assumed the answer
was one of two things. It was three: a genuinely narrow bank, a genuinely
non-medical channel, and an unstated specialty that changes the arithmetic by
7 either way. Reporting the middle tier separately was the only way to avoid
picking one of the two offered answers and sounding certain about it.

---

## Round 10 — close the filter/bank gap — 2026-09-18

**Objective.** Make it impossible for the filter to claim coverage the bank
does not have.

**1. Every clinical term now resolves to a claim, or it cannot match.**

`claims.py` gained `reconcile()` / `assert_no_orphans()` (raises, exit 3 via
`claims.py synonyms`), and `01_source.py` computes its match vocabulary from
the bank at load time instead of declaring it.

The backing rule decided the answer, so it is stated explicitly:

| Source | Backing? | Why |
|---|---|---|
| claim text, hedge, citation titles | yes | what the claim asserts |
| `do_not_say` | **no** | what it FORBIDS |
| `topics` | **no** | an index label, not a statement |

Counting the last two as backing hid 6 orphans.

**11 of 38 candidate terms (29%) are orphaned**, in three classes needing three
different answers — full list in `reports/filter-bank-reconciliation.md`:

- **Covered under another name** (`cold plunge`, `cold-plunge`, `ice bath`,
  `ice baths`). The store's flagship product term appears in the bank **only
  inside `do_not_say`** — matching it would have routed a request to a claim
  whose purpose is to forbid the answer. The bank calls the concept *cold water
  immersion*. Needs one line from the physician, not new evidence. **Not
  self-approved**: deciding a consumer term and a clinical term are synonyms is
  a clinical judgement.
- **Genuinely absent** (`infrared`, `steam room`, `cryotherapy`, `thermal`,
  `longevity`). `longevity` was a *match* term while being, in substance, a
  banned claim — the do_not_say lists forbid "sauna use will extend your life".
- **Index label only** (`hydration`, `dehydration`).

**No claim was added.** The bank is awaiting signature.

**2. Concept matching — and an honest number for it.**

Each claim now carries a synonym set derived from its own text and citation
titles (`data/claim-synonyms.json`, a sidecar so the signature-pending
`claims.json` is untouched).

The raw derivation is 3,156 n-grams including `actual`, `days` and `damages`,
so a form is kept only if it matches text a backed anchor would **miss**. On
that rule the yield is **four concepts**: `cognitive`, `depressive`,
`inflammatory`, `contrast water therapy`. Reporting 263 surface forms would
have been true and useless — `finnish sauna` cannot match text `sauna` misses.

It does **not** reach `light-based skin treatments`. Round 9's near-miss stays
a miss, correctly: no claim mentions light. Widening stops where evidence does.

**3. Verdict changes: exactly one, and it is the point.**

`Red Light Therapy Digest` (Connectively): `answerable/alptunaer` → `rejected`.
Nothing else in 242 rows moved. **Clinical answerable across the whole corpus
is now 0, down from 1** — the second stop-and-ask condition, reported rather
than treated as a failure.

The honest reading: **the clinical filter has never once matched a request the
bank could answer.** The single match was a vocabulary accident, and had the
bank been signed with a drafter in place it would have been pitched under a
physician's name with nothing to say.

(A rescore also corrected 3 rows still carrying verdicts from pre-Round-6
anchor lists — pre-existing drift, not a Round 10 effect.)

**4. `specialty: null` recorded, not guessed.** 16 of 112 HARO requests remain
**unresolvable** — neither reachable nor rejected — until it is filled.

**Four derivation bugs found by measurement, not by reading.** The first orphan
count came out at 39% and would have tripped the stop-and-ask on my own
tokenizer's faults: a blanket minimum word length dropped `brown fat` (three
letters, and the whole concept); hyphen-joined tokens stopped `heat
acclimation` forming its bigram; the stemmer missed `-atory`, so
inflammation/inflammatory did not tie; and a bare prefix test flagged
`depression` as a reversing form of nothing. Corrected, the figure is 29% and
stable.

**Friction.** Three successive orphan counts — 21%, 39%, 29% — all produced
confidently, all from the same data, differing only in how I defined backing
and tokenised. The one that would have escalated to the user was the wrong one.
Measuring the wrong thing precisely remains this project's most reliable
failure mode, and the only defence that worked was refusing to report a number
until the thing producing it had tests.

**Not changed.** No claims added. Anchor lists, thresholds, `claims.json` and
the Tripler topic set all untouched. No drafter. Nothing drafted, nothing sent,
mailbox unmodified.

---

## Round 11 — specialty, and the attribution guard — 2026-09-18

**1. Specialty: Emergency Medicine** (`General Emergency Medicine`), recorded in
`experts.json`. It governs **how he is described, not what he can discuss.**

**Re-resolution of the 16 tier-B items → reachable goes from 9 to 17 of 112.**

| | Count |
|---|---|
| Tier A, general physician competence | 9 |
| Tier B unlocked by the specialty | **8** |
| **Reachable** | **17 of 112 (15%)** |
| Still out — veterinary | 5 |
| Still out — not an expert request at all | 3 |

**A correction to Round 9's breakdown.** It reported the 16 as dermatology (4),
veterinary (4), psychiatry (3) + others. The total was right, the distribution
was not: veterinary is **5**, dermatology 3, psychiatry 2, plus one item gated
on a stated "mental health professional" requirement. The veterinary figure is
the one this round turns on.

**Three of the 16 were never expert requests** and move to tier C: two copies of
a "Future of Fertility" listing that reads as a medical panel for one sentence
and then asks for **gift bags**, and a Famadillo item seeking a plastic-surgery
*practice* to host a writer for a free procedure. Classifying on the opening
clause is how they landed in tier B.

**Reachable is not accepted.** 4 of the 8 name a profession he does not hold
(mental health professional, dermatologist, dentist/dietitian, psychiatrist).
The byline stays correct either way, so it is not an attribution problem — but
the journalist set the requirement and may decline on fit. Flagged per item.

**2. The attribution guard.**

Credential line stored as ONE verbatim literal: `Timur Alptunaer, MD, RN,
EMT-T, FACEP`. Never reconstructed, abbreviated, reordered or expanded.
`assert_pitchable()` requires exact string equality; there is deliberately no
code path that assembles it from parts, because a builder can build it wrong —
drop the RN, reorder the post-nominals, expand FACEP — and each of those
misstates a real person's credentials. Eight wrong forms are tested, including
the plausible ones.

**The guard blocks the description, not the subject.** A pitch about
dermatology is fine; "Dr. Alptunaer, a dermatologist" is not. It matches
descriptor *shapes* — `X-ologist`, `board-certified X`, `specialist in X`, `X
expert`, `professor of X`, `X physician` — within 140 characters of his name,
rather than keeping a list of specialty nouns that would never be complete.
`emergency medicine physician` is the one permitted expansion. Three tests
assert that naming another specialty as the *subject* passes.

`framing` is required on every pitchable item: `published-evidence` (claim
bank, framed as evidence he is interpreting) or `clinical-experience`. Same
credential line either way.

**EMT-T: recorded, not acted on.** Tactical EMT is directly relevant to the
military and sports-performance topics in the experience set. It is stored
under `observations_for_human` with `status: observation_only`, and a test
asserts no filter term was added from it. Nothing widened scope automatically.

**Two bugs caught by the tests.** The permitted descriptor tripped its own
guard — `emergency medicine physician` contains the bigram `medicine
physician`, which is not itself an allowed phrase — fixed by scrubbing what is
permitted before scanning for what is not. And my "no code path assembles the
line" test was matching the wrong-ordering fixtures in its own test file;
replaced with the invariant that actually matters, that code and `experts.json`
agree on one literal.

**Not changed.** No drafter exists yet — the guard is in place *before* one
does, which is the only useful order. Claim bank, anchor lists and thresholds
untouched. Nothing drafted, nothing sent, mailbox unmodified.

---

## Round 12 — the drafter — 2026-09-18

**Objective.** First round that produces something sendable.

**Outcome: 0 drafts, 17 `needs_expert_input`. The round stopped on its own
constraint.** `reports/draft-queue.md`.

**Built and working.** `pipelines/lib/drafter.py` + `01_source.py draft`:
`not_a_query` detection, strict source resolution, draft assembly from approved
material only, the 300-word platform limit, `assert_pitchable()` on every
draft, and the review queue ordered mismatches-first then by deadline. 36 new
assertions.

**The drafter is not broken, and that is tested rather than asserted.** A
covered item produces a real 129-word draft — sourced to `heat-cv-mortality-01`
and `heat-cv-mortality-02`, hedges attached, verbatim credential line,
affiliation, passing `assert_pitchable()`. So a zero on the live corpus is a
fact about the corpus, not about the code.

**Why zero.** Not one of the 17 reachable items names a modality the claim bank
covers. The bank is 30 claims about sauna, heat and cold exposure; the 17 are
kidney transplants, head lice, hyperpigmentation, collagen creams, oral
supplements, obesity endocrinology, emergency medicine, CMS chronic-care
policy, and the psychology of surviving a shooting. Across all 242 corpus rows
Dr. Alptunaer has 23 marginal and **0 answerable**.

**Two premises in the spec are not true of the repo, and both were checked
before building rather than assumed:**

1. *"the claim bank has the expert's general approval"* — `claims.json` still
   reads `approval_status: awaiting_review`. **Not changed.** Flipping the
   physician's own approval field from inside the machine is precisely what
   Round 10 established must never happen.
2. *"the expert's approved experience set"* — **there is no experience set for
   Dr. Alptunaer anywhere in the repo.** `experts.json` gives him
   `evidence_regime: cited` and `claims_source: data/claims.json` and nothing
   else. Tripler has a provisional topic list; it is hers and it is
   `approved: false`. So the drafter's second source of truth does not exist,
   which is most of why the answer is zero.

**A trap this round nearly walked into.** My first coverage probe reported
**16 of 17 covered** — using Round 10's derived concept sets, which contain
generic words. A head-lice piece "matched" a Finnish sauna cohort on the word
`cannot`; hyperpigmentation matched on `improve`. That is exactly the bank
being stretched, and it is what the round's own stop-trigger (>12 clean) exists
to catch. Re-run against the reconciled modality vocabulary the pipeline
actually uses, the honest figure is **0 of 17**.

**A second trap, caught by reading the output.** The first `not_a_query` test
required positive evidence that comment was being requested, and dropped four
real requests for want of a recognised phrase — including *"I want to talk to
experts about how common this is"*, as plain a request as the corpus holds.
Disqualification now requires positive solicitation evidence; an item with no
standard phrasing is passed through flagged, because a human reading one extra
item costs nothing and a silently discarded request costs the thing the project
is for. The three known gift-bag/hosting items are still caught, and all four
false positives are restored — both directions tested.

**Requirement mismatches:** 4 of the 17 name a profession he does not hold.
Flagged, named, and surfaced at the top of the queue. Not papered over.

**Nothing was sent.** Six tests assert `drafter.py` contains no send path at
all — no smtp, no sendmail, no write action, no HTTP post.

**🔴 BLOCKED — see the Slack message.** The round cannot produce drafts from
approved material, and manufacturing them is the one thing it was told not to
do. The decision is the human's.

---

## Round 13 — three regimes — 2026-09-21

**Outcome: 2 drafts, both `verified_at_draft`, both awaiting his review, none
at risk of expiring.** Against Round 12's zero. `reports/draft-queue.md`,
`reports/regime-ceiling.md`.

**1. Experience set.** `data/experience.json` — exactly the five confirmed
topics, `approved: true`, uncited by design. Provenance records a **relayed
confirmation**, `is_signature: false`. The distinction is kept deliberately:
`claims.json` is separately awaiting a real signature and conflating the two
would quietly upgrade one of them.

**2. General medical, verified at draft time.** Five citations retrieved via
the Firecrawl research tools this session, each resolved by `inspect_paper`
with the title stored exactly as returned. The gate raises on an unresolvable
id, a missing title, a missing `verified_at`, or a missing `source_type` — and
an assertion with no citation is **dropped, not softened**, because softening
is how an unsourced claim survives review. Every `verified-guideline` draft
carries `requires_expert_review` as a *precondition of pitchability*, not a
label attached afterwards.

**Verification changed a draft.** My prior was that biotin does not help nails.
The literature says otherwise — small trials do show improvement in brittle
nails (PMID 29057689) — so the draft says that, hedged as the trials warrant,
rather than what I assumed. That is the regime working: it is not a formality
over conclusions already reached.

**The strongest angle came from his actual specialty.** High-dose biotin
interferes with streptavidin-based immunoassays including troponin
(PMID 30582902). An EM physician warning that a nail supplement can distort the
test used to rule out a heart attack is on-specialty, useful, and not
borrowable from a dermatologist.

**3. Regime precedence** is claim bank → experience → verified-at-draft, with
one documented exception: an **evidence question skips the experience set**.
The experience regime is uncited by design and must never be presented as
literature, so "is there real evidence" cannot be answered from it even when
the topic words match.

**§3 caught another one.** `Shawna and LaLa` matched the experience set on
`recovery` and reads as an editorial fitness segment — then asks for "fitness
and wellness brands interested in having their products featured". A product
solicitation. Four new solicitation patterns; 27 of 213 requests are now
`not_a_query`.

**4. Queue** grouped mismatches → awaiting-his-review (soonest deadline first)
→ ready for Julian. **At risk of expiring within 24h: 0** — but only because
these two happened to be 30 and 84 hours out. That count is the number that
decides whether the regime is workable at his response speed.

**5. The ceiling.**

| Regime | Requests | Live |
|---|---|---|
| `claim_bank` | **0** | 0 |
| `experience` | 5 | 2 |
| `verified_at_draft` | 181 | 81 |
| `not_a_query` | 27 | 23 |

**181 is not a reachability figure** and is flagged as such in the report — it
is the fallback bucket and includes travel and gift guides. The meaningful
figure is Round 11's 17 reachable of 112 classified, of which **4 still have a
live deadline**; 40 newer HARO requests are unclassified.

**Option C numbers, stated without argument:** 18 ingest runs, 152 distinct
HARO requests, 213 distinct across all platforms, **0 about sauna, heat or
cold**, 0 covered by the claim bank. Round 9 reported zero against 112; more
than doubling the corpus has not moved it.

**What the regime actually changed:** the constraint, not the coverage. Sources
can now be built per draft, but each costs real citation retrieval and every
one needs his review. Two drafts took five verified citations.

**Still open, surfaced not answered:** which experience topics he speaks to as
an EM physician versus as an informed individual (EMT-T bears on military and
sports performance), and whether he would strike the seven `preliminary`
claims. `approval_status` unchanged.

**Nothing was sent.**

---

## Round 14 — close the loop — 2026-09-21

**Built.** `pipelines/lib/outcomes.py` plus three commands: `sent`, `outcome`,
`outcomes`. 46 new assertions. `reports/outcomes.md`.

**1. Recording sends — a CLI command writing a committed file.** `sends.json`
is the durable store; `sent` and `outcome` are the doors. A hand-edited file
alone was rejected: a trailing comma at the busiest moment loses the only
record of what went out. The commands validate, resolve outlet/regime/platform
from the queue so nothing is retyped, and are idempotent on the item key.

**A sent item drops from the queue and is never re-surfaced.** Demonstrated
end-to-end: recording one send took the corpus from 213 to 212 and the drafts
from 2 to 1.

**The demonstration record was then removed.** `sends.json` is committed
**empty on purpose** — nothing has actually been sent, and leaving a fake send
in it would corrupt the one measurement the file exists to keep.

**2. Outcomes. Statuses are `pending` and `published`; there is no third.** A
pitch nobody answered stays pending indefinitely and is never counted as a
failure. No rate in the report uses sends as the denominator for publication.

**The link is read off the page** — anchors parsed from markup, `rel` recorded
exactly as written. A plain-text mention of the domain is not a link, and a
test says so.

**The page-fetch route does not work in this environment.** The network policy
denies CONNECT to publisher domains — verified against healthline.com and
eatthis.com, both 403 at the proxy. Reported rather than routed around.

So there is a second route, and it works: **`00_audit`'s referring-domain
pull**, which goes through an MCP tool rather than raw HTTP. It confirmed the
eatthis.com link with `rel=follow`. It only ever *upgrades* a record — it can
establish a link, never erase one.

**A failed fetch never sets `linked: false`.** Tested for network-blocked, 403,
429 and 500. "We could not look" and "it is not there" are different facts, and
recording the first as the second would mark real earned links as missing —
the same shape as an empty mailbox read as a quiet niche. A *successful* fetch
finding no link does record `false`, because that one is a real observation.

**3. The headline is now sent / published / linked / time-to-publication**, per
regime and per platform. It replaces answerable-rate, which was always a proxy.
Everything currently reads zero **by absence rather than by result**, and the
report says so in those words.

**A real bug the tests caught.** Re-recording a send without `--at` restamped
it to now — so correcting a typo in the address would have silently corrupted
time-to-publication, the one duration this file measures. The original send
time now survives a re-record; only an explicit `--at` moves it.

**Open item:** the weekly check is not attached to a Routine. `linkbuilding`
had no weekly verify job before this round, so this one is defined rather than
inherited, and `last_checked` is the honest record until it is scheduled.

**Zero sends by the pipeline.** Five tests assert `outcomes.py` has no
transport and only ever GETs.

---

## Round 15 — experience statements are flagged, not removed — 2026-09-21

**The gap.** The drafter writes first-person clinical experience in his voice.
Citations verify literature claims; nothing verifies experience claims, and
they sat in the same paragraph reading identically. A reviewer skimming a draft
with three PMIDs in it would reasonably assume the whole thing had been checked.

**Built.** `experience_statements` as a first-class unit alongside
`assertions`. Each unconfirmed one renders `[CONFIRM: experience]` inline and is
listed separately in the Slack post. `assert_ready_to_send()` raises while any
flag remains. Flags are stripped by `confirm-experience` and nothing else.
*Pitchable* and *ready-to-send* are now deliberately different gates: a flagged
draft may be queued and shown, not sent.

**The restructure found two things worse than the tails.**

1. *"The bigger concern **I see clinically** is contamination rather than
   inertness"* was embedded **inside a cited assertion**. The PMID supports the
   FDA adulteration finding and says nothing about his clinical impression. Split.
2. *"stop it several days before scheduled bloodwork"* sat beside the biotin
   interference citation, which does not state that interval. Now flagged as
   his clinical judgement rather than borrowing the paper's authority.

Health Insiders: 4 experience statements. Mirellé Inspo: 3.

**Dedupe is now on item key AND content hash.** The two drafts already in Slack
showed the experience text unflagged — copying them would have sent exactly
what this change prevents. Keying on the item alone would have meant the
corrected text never reached the channel. A materially changed draft reposts
once, marked REVISED and naming the post it supersedes. Both reposted; re-running
`post-drafts` now reports 0 pending.

**The sentences were not removed.** They make pitches land. The fix is that
they are reviewable.

321 assertions pass.

---

## Round 16 — Gmail drafts for approved HARO replies — 2026-09-21

**The mailbox rule is amended, narrowly.** Read-only, with one exception: the
pipeline may CREATE a draft. Never send, delete, archive, label or modify.
Enforced in `lib/gmail_draft.py`, which names exactly one write action, and
tested by parsing its own AST for every forbidden verb.

**Built.** `gmail-draft` (on demand, because HARO deadlines run under 24h),
`gmail-drafted`, `detect-sends`. 43 new assertions.

**Nothing real was drafted, and that is correct.** Both queued items are
BLOCKED: 4 and 3 experience statements await Dr. Alptunaer's confirmation. I
did not confirm them on his behalf — that is the one thing the flag exists to
prevent.

To verify the path end-to-end I created a clearly-labelled test draft addressed
**internally to julian@, never to a journalist**, and read it back:
`1a0c590c03a41837`, From `timur@inhousewellness.com`, credential line verbatim,
no flag, 0 attachments, label `DRAFT`. The live read-back is committed as
evidence and the test asserts against it. **The pipeline cannot delete it** —
create is the only write it has — so a human should.

**Zapier findings.**
- `gmail_create_draft` (`draft_v2`) was **already enabled**. Nothing was enabled.
- Send Email, Delete, Archive, Add/Remove Label and Reply are ALSO enabled on
  this account. The pipeline cannot reach them, but they exist; disabling is
  the account owner's call since other automations may use them.
- `inspect_zapier_actions` rejects the UUID `connection_id` as NaN. With the
  UUID omitted it silently resolves the enum against the **default**
  connection (support@) — which lists neither timur@ nor julian@. Using the
  numeric id from `reconnect_url` (53367330) resolves against julian@ and
  shows **timur@ IS a Send-as alias**. Reading the first answer as final would
  have reported the alias unavailable, confidently and wrongly.

**From: timur@ works.** No fallback to julian@ was needed.

**A gap this surfaced.** The subject must be the HARO digest title, and
`source_items` never persisted `summary` — it was computed at ingest and
dropped. Added to the schema, to `persist()` and to `rebuild.py`. Existing 311
rows have no summary; `build_draft_args()` raises rather than inventing one,
so no draft can be created for an old item until its title is available.

**Send detection** reads Sent for `reply+*@helpareporter.com` and records the
real send time, replacing the manual `sent --key` step for HARO. Absence from
Sent means nothing was found, never that nothing was sent.

**Two tests I had to fix because they measured prose, not code.** The
forbidden-verb scan matched its own docstring, which lists the verbs in order
to forbid them; and `ast.get_docstring()` normalises indentation, so excluding
docstrings by value never matched. Now it excludes the docstring nodes and
scans the executable surface. Same shape as the Round 11 test that matched its
own fixtures.

---

## Summary backfill — recover the titles for live items — 2026-09-21

*Task, not a round. Closes the gap Round 16 opened.*

**Result.** 168 of 171 live items now carry the real digest title. The three
that do not are Connectively, deliberately — see below. Every live
`answerable` or `marginal` item has a summary, so `build_draft_args()` no
longer raises for anything that is actually draftable.

**The first title recovered, reported before the rest** (Health Insiders,
`reply+554a52ca-…@helpareporter.com`, deadline 22 Sep 18:30 UTC):

> **Expert Insights on Weight Loss Drops and Healthy Weight Management**

from `HARO Queries for September 18, 2026 - Afternoon Edition`, item 16,
journalist Rodgers Panato.

**The bug this exposed, which is the real finding.** The first re-parse
returned a 2,943-character "title" that had swallowed Name, Category, Email,
Media Outlet, Deadline and the entire query body. Cause: the summary was
bounded on the next blank line, `\n\n` — and **live HARO bodies are CRLF**,
where a blank line is `\r\n\r\n`. The eight captured samples were written to
disk with LF, so every whitespace-sensitive rule passed on the fixtures and
broke on real mail. This is the project's recurring failure in a new costume:
the fixture was not a faithful sample of the thing it stood for.

Two fixes: normalise line endings at each parser's entry point, and bound the
summary on the **closed field-label set** rather than on whitespace.

**They are redundant, and I measured that rather than assuming it.** Removing
only the normalisation still passes; removing only the bounding still passes.
So no behavioural test can isolate either one. The guard is therefore the
invariant the bug violated, asserted over the whole captured corpus **in both
line endings**: 324 parses, no summary containing a field label, longest
summary 75 characters. With both fixes reverted that check reports 2,943 and
fails — verified, not assumed.

**Connectively is excluded, and stays NULL.** Its digest carries no title
field at all; the parser's `summary` there is a 140-character excerpt of the
query body. Filling it would be inferring a title from query text, which is
the one thing the task forbade. It costs nothing operationally:
`build_draft_args()` already refuses Connectively items, so all three would
have been skipped anyway.

**Expired items stay NULL** — asserted in the backfill and again in
`self-test`. There is no value in a title for a query nobody can answer, and
filling them would inflate the count of rows that look draftable.

**A second near-miss, caught by accident and then made impossible.** The first
state export would have written 311 items over a committed 333, silently
deleting 22 items and a run: `links.db` is gitignored, and a Routine-fired run
at 18:37 UTC had committed rows this checkout's database had never seen.
`export-state` now refuses to write when the database is missing anything the
committed state already holds, and says how to recover. The guard fires on a
synthetic three-row deletion — tested.

**New.** `pipelines/backfill_summaries.py` (re-runnable, asserts its own two
rules and exits 1 if it violated them) and `01_source.py export-state`
(refresh the state file without re-deciding anything, unlike `rescore`).

**Verified.** `self-test` 379 PASS / 0 FAIL. `test-samples` clean. Cold
`rebuild.py run --force` restores 333 items with 168 summaries and 0 expired
summaries, so the backfill survives a cold start — which was the point of
committing it.
