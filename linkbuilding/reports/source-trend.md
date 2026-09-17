# Source trend — cumulative

Rebuilt on every run of `pipelines/01_source.py`. **No drafts, no pitches, nothing sent.**

## Decision criteria — fixed before the data arrived

Stated up front so the conclusion cannot be fitted to whatever turns up.

### ⚠️ THE 14-DAY CLOCK HAS NOT STARTED

It starts on **the first HARO query digest**, not on the first run. As of
2026-09-15 no HARO digest has ever arrived at any address in this mailbox:
the only HARO mail is five account-lifecycle messages, the newest an
*unclicked* "Please Verify Your Email" sent to `media@` at 18:37 UTC that day.

This matters because of where the evidence actually comes from. All four
proven links — healthline DR91, eatthis DR83, womansworld DR66, singlecare
DR63 — arrived between 2026-01-20 and 2026-07-02, through HARO, on a
former contractor's own account. **Not one came through SOS or Qwoted.**

So a zero from SOS and Qwoted says nothing whatsoever about the channel that
produced every link this site has earned. Counting those days toward fourteen
would measure two channels that have never produced a link and then draw a
conclusion about a third.

### Expected order of magnitude

One link per six weeks, from a pitch volume necessarily higher than four.
That implies **a handful of answerable items per month** — single digits,
low ones. Not per day, and not per run.

Calibrate accordingly: **zero answerable on any given day is the expected
result and is not a signal.** A week of zeros is not a signal either. The
threshold that would genuinely condemn the pipeline is a *month* of HARO
digests arriving and being filtered to zero.

### Assess after 14 days OF HARO DIGESTS

| If, after 14 days of digests | Then |
|---|---|
| **>= 2 answerable per month** | `01_source` earns its place. Build the drafter. |
| **Answerable, but all from Qwoted** | Evaluate Qwoted Pro at $149/mo. The free tier's request delay and pitch-credit cap become the binding constraint. |
| **Zero answerable, marginals clustering in one topic** | The gap is in the claim bank, not the pipeline. Extend the bank in that topic. |
| **Zero answerable, marginals scattered** | The niche is quiet. Keep the filter running cheaply and move effort to dealer pages and outreach. |

A fifth outcome is possible and must not be silently folded into the fourth:
if `deadline misses on arrival` is high, the pipeline may be finding real
requests too late rather than not finding them. Check that row before
concluding the niche is quiet.

A sixth, currently the live one: **no digests are arriving at all.** That is a
plumbing problem and none of the five rows above apply to it.

---

## Where we are

| | |
|---|---|
| Runs recorded (locally) | 12 |
| Runs CONFIRMED on the remote | 12 |
| **Days of evidence (verified)** | **3 of 14** |
| Calendar span of local runs | 3 day(s) |
| Items ingested | 59 |
| **Answerable (cumulative)** | **7** |
| Marginal (cumulative) | 14 |
| Rejected (cumulative) | 38 |
| Since last answerable | 0 day(s) ago (2026-09-17) |
| Deadline misses on arrival | 3 |

## Per run

`Persisted` is *confirmed readable out of the commit the remote points at* — not *`git push` returned without an error*. On 2026-09-14 the second was true and the first was false, and the run reported success.

| Run date | run_at (UTC) | Msgs | Items | Answerable | Marginal | Rejected | New | Missed | Persisted |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-15 | 2026-09-15T20:02:11 | 14 | 24 | 3 | 7 | 14 | 24 | 1 | ✅ |
| 2026-09-15 | 2026-09-15T20:50:19 | 15 | 24 | 3 | 7 | 14 | 0 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:51:08 | 15 | 24 | 3 | 7 | 14 | 0 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:52:43 | 15 | 24 | 3 | 7 | 14 | 0 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:52:54 | 15 | 24 | 3 | 7 | 14 | 0 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:54:21 | 15 | 24 | 3 | 7 | 14 | 0 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T21:39:38 | 16 | 24 | 3 | 7 | 14 | 0 | 2 | ✅ |
| 2026-09-16 | 2026-09-16T11:39:21 | 18 | 31 | 3 | 9 | 19 | 7 | 4 | ✅ |
| 2026-09-16 | 2026-09-16T18:39:36 | 21 | 41 | 4 | 11 | 26 | 10 | 6 | ✅ |
| 2026-09-16 | 2026-09-16T21:39:40 | 23 | 41 | 4 | 11 | 26 | 0 | 6 | ✅ |
| 2026-09-17 | 2026-09-17T11:39:21 | 26 | 50 | 7 | 13 | 30 | 9 | 8 | ✅ |
| 2026-09-17 | 2026-09-17T18:39:51 | 28 | 59 | 7 | 14 | 38 | 9 | 8 | ✅ |

The most recent run reads `pending` by design: verification happens after the commit exists, so `push-log.json` and this table are committed one run behind. A run that stays `pending` across the next run is a run that never persisted.

## Items per day by source

| Run date | SOS | Qwoted | Total |
|---|---|---|---|
| 2026-09-15 | 18 | 6 | 24 (running 24) |
| 2026-09-16 | 16 | 1 | 17 (running 41) |
| 2026-09-17 | 18 | 0 | 18 (running 59) |

## Qwoted — does the free tier bind?

Qwoted's free tier allows **7 pitch credits**. That cap only matters if answerable volume exceeds it. The deciding number is the answerable column, not the received column.

| Run date | Qwoted items received | Of those, answerable |
|---|---|---|
| 2026-09-15 | 6 | 1 |
| 2026-09-16 | 1 | 0 |
| 2026-09-17 | 0 | 0 |

**Cumulative Qwoted answerable: 1.** Below the 7-credit cap, so the free tier is not yet the constraint.

## Rejection categories, cumulative

This is the dataset that separates *the filter is too tight* from *the niche is genuinely quiet*. If rejections cluster in topics the claim bank covers, the filter is wrong. If they are spread across finance, gift guides and cybersecurity, the niche is quiet.

| Category of rejected item | Count |
|---|---|
| General | 13 |
| Business and Finance | 5 |
| Biotech and Healthcare | 5 |
| uncategorised | 4 |
| Lifestyle and Fitness | 4 |
| Technology | 3 |
| Travel | 3 |
| Public Policy and Government | 1 |

| Rejection reason | Count |
|---|---|
| no vocabulary for either expert | 38 |

