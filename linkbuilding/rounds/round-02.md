# Round 2 — Build `03_discover` + `04_qualify`

Load the `agent-harness` skill. Standard round rules apply: tiered approvals,
BLOCKED/REVIEW/FYI reporting, RUNLOG.md entry on completion.

> **This is the first round that produces link opportunities.** Round 1 built
> the baseline. Everything from here is acquisition. Success is a ranked
> worklist of real, contactable targets — not more analysis of existing links.

## Working directory

All work inside `linkbuilding/` in the `inhousewellness` repo. Paths below are
relative to repo root. Do not touch anything outside `linkbuilding/`. The root
`CLAUDE.md` governs other projects; `linkbuilding/CLAUDE.md` wins here.

## Before you write anything

Read `linkbuilding/CLAUDE.md`, `data/owned.json`, `data/affiliates.json`,
`data/schema.sql`, `pipelines/00_audit.py`. Hard Rules 1–8 are binding.

**Hard Rule 1 is the one that matters most this round.** Load `owned.json` and
`affiliates.json` at the top of discovery and drop matches silently. The failure
mode is a pipeline that surfaces your own ten sites as fresh opportunities and
emails your own affiliates.

## Pre-flight check

`targets` has `UNIQUE(domain, tactic)` and `00_audit` already wrote 66 rows to it.

Report what `tactic` and `status` those rows carry **before** writing discovery.
If discovery could reuse any of those tactic values, a rediscovered domain
collides on the index and the opportunity is silently dropped. Either give
historical rows a reserved tactic (`audit_historical`) or add a discriminator.
State which you chose and why.

## Scope — build ONLY these

- `linkbuilding/pipelines/03_discover.py`
- `linkbuilding/pipelines/04_qualify.py`
- `linkbuilding/reports/worklist.md`

Do NOT build 01, 02, 05, 06, 07. Do NOT contact anyone. Do NOT draft outreach.
Discovery and qualification write rows and stop.

## 03_discover — four sources

Ahrefs is still erroring and Semrush has zero API units. Ubersuggest only.
Do not burn the round on either.

**1. Competitor gap.** Build the competitor set with `competitors` against
inhousewellness.com rather than assuming it — then `backlink_opportunity` to
find referring domains linking to competitors but not to you. This is the
highest-yield source in the round. Tactic: `gap`.

**2. Resource pages and roundups.** `serp_analysis` on commercial and
informational queries in the niche (infrared sauna, traditional sauna, cold
plunge, barrel sauna, sauna heater, cold therapy, home recovery). Look for
listicles, buyer guides, and resource pages that already link out to retailers.
Tactics: `roundup`, `resource_page`.

**3. Unlinked mentions.** Pages mentioning "InHouse Wellness" with no link.
Highest conversion rate of any outreach type — the ask is trivial.
Tactic: `mention`.

**4. Dealer pages.** Seed six rows manually, one per corporate entity —
Golden Designs (covers Dynamic and Maxxus), Harvia, Finnmark Designs, Scandia,
Leisurecraft, Ripavi. These are human applications, not crawled opportunities;
they sit in `targets` so they're tracked, not so a pipeline works them.
Tactic: `dealer`. Status: `queued`.

Deduplicate across sources. Write everything as status `new`.

## 04_qualify — score, then reject hard

Most of the value in this round is in what gets thrown away. A pile of 400
unfiltered domains is worse than 40 real ones.

Score per `schema.sql`:

| Component | Range | Basis |
|---|---|---|
| `relevance` | 0–40 | Topical fit: sauna, cold plunge, recovery, wellness, home improvement, outdoor living |
| `authority` | 0–25 | DA and referring domains |
| `traffic_reality` | 0–15 | Organic traffic **relative to** claimed authority |
| `link_likelihood` | 0–20 | Does the page already link out to comparable retailers? |

Auto-reject to `rejected`, recording the reason in `risk_flags`:

- DA >40 with negligible organic traffic
- Spam score >40
- TLDs in `.cfd .sbs .click .website .top`
- Sitewide footer or template link patterns
- Gambling, pharma, adult, or crypto in the outbound neighbourhood
- Any domain in `owned.json` or `affiliates.json`

Survivors become `qualified` with a `composite_score`.

## Output

`reports/worklist.md`: qualified targets ranked by composite score, grouped by
tactic, with domain, DA, the specific page to approach, why it qualified, and
the suggested angle. Include counts discovered vs. qualified vs. rejected per
source, and the top three rejection reasons by volume — if one rule is killing
most of the pile, the rule may be wrong.

## Acceptance criteria

- [ ] Everything created lives under `linkbuilding/`
- [ ] Pre-flight collision question answered and resolved before discovery runs
- [ ] Zero `owned.json` or `affiliates.json` domains reach `qualified` — assert this in code
- [ ] All four discovery sources produce rows, or the empty ones are explained
- [ ] Six dealer rows seeded
- [ ] Every qualified row has a real, specific page to approach — not just a domain
- [ ] Rejection reasons recorded, not just a boolean

## Stop and ask if

- Qualified count is under 25 or over 200 — either the filters are wrong or the
  scoring is
- A single rejection rule accounts for more than half of all rejections
- `competitors` returns a set that doesn't look like actual sauna retailers
- Ubersuggest rate-limits mid-run at tier1 — report how far it got, don't
  silently truncate
- Any discovery source returns zero rows

## Not in this round

`01_source` remains blocked pending the expert's review cadence and a claim
bank. The five paid-pattern links remain `unresolved` pending provenance.
Neither blocks Round 2.
