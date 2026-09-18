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
| Runs recorded (locally) | 8 |
| Runs CONFIRMED on the remote | 8 |
| **Days of evidence (verified)** | **2 of 14** |
| Calendar span of local runs | 4 day(s) |
| Items ingested | 242 |
| **Answerable (cumulative)** | **19** |
| Marginal (cumulative) | 42 |
| Rejected (cumulative) | 181 |
| Since last answerable | 0 day(s) ago (2026-09-18) |
| Deadline misses on arrival | 68 |

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
| 2026-09-18 | 2026-09-18T15:48:14 | 41 | 242 | 19 | 42 | 181 | 218 | 76 | ✅ |
| 2026-09-18 | 2026-09-18T15:49:22 | 41 | 242 | 19 | 42 | 181 | 0 | 76 | ✅ |

The most recent run reads `pending` by design: verification happens after the commit exists, so `push-log.json` and this table are committed one run behind. A run that stays `pending` across the next run is a run that never persisted.

## Answerable rate BY CHANNEL

Reported per channel and never blended. All four proven links (healthline DR91, eatthis DR83, womansworld DR66, singlecare DR63) came through **HARO**; none came through SOS or Qwoted. An average across the four would hide the only channel with a track record.

`Items` counts digest rows. `Distinct` counts separate requests: HARO re-runs the same query across its morning, afternoon and evening editions, so rows overstate opportunities by about a third. Both are shown rather than picking one and hiding the other.

| Channel | Items | Distinct | Answerable | Distinct answerable | Rate (distinct) | Marginal | Rejected | Reply path |
|---|---|---|---|---|---|---|---|---|
| **haro** | 162 | 112 | 11 | **9** | 8.0% | 25 | 126 | direct (`reply+…@helpareporter.com`) |
| **sos** | 60 | 39 | 6 | **5** | 12.8% | 14 | 40 | direct (journalist address in digest) |
| **connectively** | 11 | 11 | 1 | **1** | 9.1% | 1 | 9 | manual (magic-link auth redirect) |
| **qwoted** | 9 | 9 | 1 | **1** | 11.1% | 2 | 6 | manual click-through |

### The 14-day clock

**Starts 2026-09-15 — the first HARO query digest**, not the first run and not the signup date. Days before it measured SOS and Qwoted only, which is two channels that have never produced a link.

| | |
|---|---|
| Clock start (first HARO digest) | 2026-09-15 |
| Day of 14 | **4** |
| HARO digest rows ingested | 162 |
| HARO distinct requests | 112 |
| HARO answerable rows | 11 |
| **HARO distinct answerable requests** | **9** |

## Items per day by source

| Run date | SOS | Qwoted | HARO | Connectively | Total |
|---|---|---|---|---|---|
| 2026-09-15 | 18 | 6 | 0 | 0 | 24 (running 24) |
| 2026-09-18 | 42 | 3 | 162 | 11 | 218 (running 242) |

## Qwoted — does the free tier bind?

Qwoted's free tier allows **7 pitch credits**. That cap only matters if answerable volume exceeds it. The deciding number is the answerable column, not the received column.

| Run date | Qwoted items received | Of those, answerable |
|---|---|---|
| 2026-09-15 | 6 | 1 |
| 2026-09-18 | 3 | 0 |

**Cumulative Qwoted answerable: 1.** Below the 7-credit cap, so the free tier is not yet the constraint.

## Rejection categories, cumulative

This is the dataset that separates *the filter is too tight* from *the niche is genuinely quiet*. If rejections cluster in topics the claim bank covers, the filter is wrong. If they are spread across finance, gift guides and cybersecurity, the niche is quiet.

| Category of rejected item | Count |
|---|---|
| General | 45 |
| Business and Finance | 24 |
| Health and Pharma | 21 |
| Lifestyle and Entertainment | 21 |
| Travel | 16 |
| Technology | 11 |
| Gift Bags | 11 |
| Health | 9 |
| uncategorised | 6 |
| Podcasts | 6 |
| Lifestyle and Fitness | 5 |
| Biotech and Healthcare | 5 |
| Public Policy and Government | 1 |

| Rejection reason | Count |
|---|---|
| no vocabulary for either expert | 181 |

