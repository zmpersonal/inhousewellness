# Round 7 — Make silent failure impossible

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-07.md` first.

> Yesterday's scheduled run exited 0, reported success, and persisted nothing —
> the push was denied and the container was reclaimed. The repo has since been
> added to the routine's authorized sources. This round makes sure that if it
> recurs, you find out the same day rather than on day 14.

## Scope — build ONLY these

- Push verification and alerting in `01_source`
- Startup connector reachability assertion, including Slack
- Daily heartbeat to `#media`
- HARO sample capture (capture only, no parser)
- Recalibrated decision criteria in `RUNBOOK.md`

No drafter. No HARO parser yet.

## 1. A run that cannot persist has not succeeded

Verify the push landed — confirm the commit exists on the remote, not that
`git push` returned without raising. On failure: exit non-zero and alert.

The trend counter must not increment on a run whose output was never persisted.
If the count can't be trusted, the report says so rather than incrementing.

## 2. Assert Slack at startup

Slack has never executed in a routine session — answerable has been 0 every
run, so the alert path is entirely theoretical and will first fire on the day
it matters.

Assert both connectors reachable at the start of every run: Zapier Gmail
(pinned `connection_id 029715c5`) and Slack `#media` (C0C26J8JX8U). Cloud
routines use a separate OAuth registration from interactive sessions, so a
connector valid in chat can be stale for the routine and fail silently.

Slack unreachable is a failure state: exit non-zero, fall back to the routine's
push/email notification.

## 3. Daily heartbeat

Post to `#media` on the first run of each day only. One line: items ingested,
bucket counts, day N, push status.

At the observed rate an answerable item may be weeks away. A channel silent for
two weeks is indistinguishable from a channel whose posting path is broken. The
heartbeat makes the silence informative.

Answerable items still alert immediately and separately.

## 4. HARO — capture, do not parse

The `media@` HARO account was verified on 15 Sep. Digests should begin arriving.
Every item ingested so far came from SOS and Qwoted only.

When HARO mail appears: write raw samples to `data/samples/`, report the count
and the structure you observe, and **do not write a parser this round**. One
digest is not enough to know whether the format varies between sends — the same
question SOS needed two samples to answer.

Flag HARO items as ingested-but-unparsed in the report so the gap is visible.

## 5. Recalibrate the decision criteria

The four proven links (Jan–Jul 2026) came through a former contractor's own
account, not any account in this mailbox. That is roughly one link per six
weeks, from a pitch volume necessarily higher than four.

Update the `RUNBOOK.md` criteria accordingly:

- The 14-day window starts when HARO digests begin, not from first run
- Zero answerable across SOS and Qwoted alone is not evidence about the channel
  that produced the proven links
- Expected order of magnitude is a handful of answerable items per month, not
  per day. Calibrate the "is this worth keeping" threshold to that.

## Acceptance criteria

- [ ] Push failure exits non-zero and alerts, demonstrated
- [ ] Trend counter does not increment on an unpersisted run
- [ ] Slack reachability asserted at startup, failure demonstrated
- [ ] Daily heartbeat posts, demonstrated in `#media`
- [ ] HARO samples captured if any arrived; no parser written
- [ ] Recalibrated criteria in RUNBOOK.md
- [ ] Zero drafts, zero sends, mailbox unmodified

## Stop and ask if

- Push still fails after the authorization change
- Slack cannot be reached from a routine session — that changes the alerting
  design, not just its configuration
- HARO digest structure varies between the first two samples
