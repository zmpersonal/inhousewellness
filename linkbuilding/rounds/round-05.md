# Round 5 — Scheduling and evidence accumulation

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-05.md`
first.

> **Scope.** Make `01_source` run unattended and accumulate evidence. NO
> drafter. Four marginal items and zero answerable is not enough signal to
> build against, and the claim bank is still `awaiting_review`.
>
> This round exists so that in two weeks you have a defensible answer to: is
> `01_source` worth keeping, and is Qwoted Pro at $149/month worth buying.

## Scope — build ONLY these

- Scheduled execution of `01_source` (daily)
- `linkbuilding/reports/source-trend.md` — cumulative across runs
- Alerting on `answerable` items
- `linkbuilding/pipelines/lib/relay.py` — the file-path payload handling

Do NOT build a drafter. Do NOT write pitches. Do NOT send anything.

## Relay

The Gmail payload is ~638KB and cannot return through the tool channel — it
lands in a tool-results file that must be copied to the scratchpad. Encode
this properly in `relay.py` rather than leaving it as a manual step, and make
it fail loudly if the file is missing rather than silently processing nothing.

## Scheduling

Run daily. SOS sends up to three times a day and deadlines are often same-day,
so a run that fires after a deadline passes is wasted. Record `run_at` on every
execution and surface any item whose deadline expired between runs — that is
the measurement that tells you whether daily is frequent enough.

Idempotency is already proven; keep the test.

## Alerting

An `answerable` item is the event this whole pipeline exists for and it may
happen once a fortnight. It must not sit unread in a report.

Alert on `answerable` only. Marginal goes in the daily report. Rejected goes
to the log. Use Slack if available; state what you used.

## The trend report

`reports/source-trend.md`, cumulative and rebuilt each run:

- Items ingested per day by source, running total
- Bucket counts per day and cumulative
- Rejection categories ranked, cumulative — this is the dataset that answers
  whether the niche is quiet or the filter is wrong
- Days elapsed, and days since the last `answerable`
- Qwoted specifically: items received per day, and how many were answerable.
  Seven pitch credits is only a constraint if answerable volume exceeds it.
  Report the number that decides it.
- Deadline-miss count: items whose deadline passed before a run saw them

## Decision criteria — write these into the report header

After 14 days of accumulation:

- **≥1 answerable per week** — `01_source` earns its place; build the drafter
- **Answerable but all Qwoted** — evaluate Qwoted Pro; the free tier's delay
  and credit cap are then the binding constraint
- **Zero answerable, marginals clustering in one topic** — the claim bank has
  a gap worth filling, not the pipeline
- **Zero answerable, marginals scattered** — the niche is quiet; keep the
  filter running cheaply and put effort into dealer pages and outreach instead

State these up front so the conclusion is settled before the data arrives.

## Acceptance criteria

- [ ] Daily run configured and demonstrated
- [ ] `relay.py` handles the file path and fails loudly on a missing file
- [ ] Alerting fires on `answerable`, demonstrated with a synthetic item that
      is then removed
- [ ] Trend report renders cumulatively across at least two runs
- [ ] Deadline-miss tracking implemented
- [ ] Decision criteria in the report header
- [ ] Idempotency test still passing
- [ ] Zero drafts, zero sends, mailbox unmodified

## Stop and ask if

- Scheduling isn't available in this environment — say so, don't simulate it
- A run returns zero rows where rows are expected (Rule 3)
- You want to loosen the filter to produce an answerable count
