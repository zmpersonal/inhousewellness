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
