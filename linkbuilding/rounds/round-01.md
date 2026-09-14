# Round 1 — Build `00_audit`

Load the `agent-harness` skill. Standard round rules apply: tiered approvals,
BLOCKED/REVIEW/FYI reporting, RUNLOG.md entry on completion.

> **Scope note.** The audit *analysis* is already done — `reports/audit-baseline.md`
> exists and is correct (17 earned confirmed, 23 ceiling). This round does NOT
> redo it. This round turns that one-off analysis into a re-runnable pipeline.
> The September snapshot was lost because nothing was writing it down; that is
> the problem this round closes.

## Working directory

**All work happens inside `linkbuilding/` in the `inhousewellness` repo.**
Every path below is relative to the repo root.

Do not create, modify, or delete anything outside `linkbuilding/`. The root
`CLAUDE.md` governs the blog and social-autoposter projects and does not apply
here. Where the two conflict, `linkbuilding/CLAUDE.md` wins — stop and ask.

## Before you write anything

Read: `linkbuilding/CLAUDE.md`, `linkbuilding/data/owned.json`,
`linkbuilding/data/affiliates.json`, `linkbuilding/data/schema.sql`, and
`linkbuilding/reports/audit-baseline.md`.

Hard Rules 1–8 are binding.

## Objective

Produce a pipeline that reproduces the existing audit from live data, stores it,
and can be re-run monthly to diff against prior runs.

## Scope — build ONLY these

- `linkbuilding/pipelines/00_audit.py`
- `linkbuilding/data/links.db` (initialise from `data/schema.sql`, populate)
- `linkbuilding/data/snapshots/YYYY-MM-DD.json` (raw pull, archived)
- `linkbuilding/data/disavow-candidates.txt`

Do NOT build pipelines 01–07. Do NOT start outreach. Do NOT rewrite
`audit-baseline.md` — append a "reproduced by pipeline" line to it instead.

## Acceptance test

`00_audit.py` run against live Ubersuggest data must reproduce the classification
already in `audit-baseline.md`: **17 earned, 10 owned/controlled, 6 affiliate,
9 syndication, 14 spam, 4 local aggregator, 6 unresolved.**

Tolerance is ±1 in any class, to allow for genuine drift since the manual pass.
A larger divergence means the rules are encoded wrong — stop and report the diff
rather than adjusting the expected numbers to match the output.

## Classification taxonomy

Encode as rules, evaluated in this order. First match wins.

| Class | Rule |
|---|---|
| `owned` | Matches `data/owned.json` |
| `affiliate` | Matches `data/affiliates.json` |
| `syndication` | Republished copy of an article also appearing on a legitimate source. Known case: the Healthline heart-attack-risk piece. Match on shared target URL + near-identical anchor. |
| `directory_spam` | Spam score >40, or TLD in `.cfd .sbs .click .website .top`, or zero organic traffic with outbound-heavy profile. |
| `local_aggregator` | Scraped listings never submitted to (`blushlocal.net`, `poicircle.com`, `ratelivo.com`, `redsavia.com`). |
| `earned` | Independent editorial. Default only after ruling out everything above. |
| `unresolved` | Cannot classify confidently. Never guess. |

## Snapshot and diff

Every run writes `data/snapshots/YYYY-MM-DD.json` containing the full per-link
pull. On any run after the first, emit a diff against the most recent prior
snapshot: domains gained, domains lost, class changes, anchor changes,
rel-attribute changes.

Lost `earned` domains are the highest-signal event this pipeline can detect
against a 17-domain base. Surface them at the top of the diff.

## Rel attributes

Per Hard Rule 8, `backlinks_overview` reports `follow: 0 / noFollow: 66` and
this is false. Derive rel from the per-link `nofollow` field only. Assert this
in code — if the overview split is ever consulted, fail loudly.

## Carried-forward flags

Do not resolve these. Persist them as `unresolved` in `links.db` and keep them
in the report:

1. `xwifkv-j0.myshopify.com` — leaked template anchor, ownership unknown.
2. The five paid-insertion-shaped links, three of which point at the same
   red-light-therapy article with mid-sentence phrase anchors. Provenance is a
   human question. If confirmed clean, earned rises to 22.

## Disavow file

Draft only. Never submit to Google Search Console.

`directory_spam` only. Exclude `syndication` — scraper copies of a legitimate
article are normal and harmless. State in the file header that disavowal is
usually unnecessary absent a manual action, and that this exists as a prepared
artifact, not a recommended action.

## Acceptance criteria

- [ ] Everything created lives under `linkbuilding/`
- [ ] `00_audit.py` reproduces the baseline classification within ±1 per class
- [ ] `links.db` populated and queryable
- [ ] Snapshot written to `data/snapshots/`
- [ ] Diff logic implemented and tested against a synthetic prior snapshot
- [ ] Rel attributes derived from per-link data only, asserted in code
- [ ] Both carried-forward flags persisted as `unresolved`

## Stop and ask if

- Any class diverges from the baseline by more than ±1
- Ubersuggest returns fewer than 60 referring domains
- A classification rule produces a result you would have to guess on
- Encoding a rule requires changing what `audit-baseline.md` already concluded
