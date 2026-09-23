# Source trend — cumulative

Rebuilt on every run of `pipelines/01_source.py`. **No drafts, no pitches, nothing sent.**

> ### ⚠️ The series changed meaning at Round 9
>
> **Every figure dated before 2026-09-18 was a ROW count.** HARO repeats the same query across its morning, afternoon and evening editions, so rows overstated opportunities by about a third, and the earlier Round 8 figures additionally keyed SOS on the journalist's address — which is the person, not the request, and cut 58 real SOS requests to 39.
>
> From Round 9 the headline is **distinct requests**, keyed per platform, and the whole series below is recomputed from the stored item rows rather than from the historical per-run counters. Row counts are still shown beside it; neither is hidden.

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
| Runs recorded (locally) | 24 |
| Runs CONFIRMED on the remote | 24 |
| **Days of evidence (verified)** | **7 of 14** |
| Calendar span of local runs | 9 day(s) |
| Digest rows ingested | 483 |
| **Distinct requests** | **390** |
| Answerable (rows) | 39 |
| **Answerable (distinct requests)** | **36** |
| Marginal (rows) | 101 |
| Rejected (rows) | 343 |
| Since last answerable | 0 day(s) ago (2026-09-23) |
| Deadline misses on arrival | 80 |

## Per run

`Persisted` is *confirmed readable out of the commit the remote points at* — not *`git push` returned without an error*. On 2026-09-14 the second was true and the first was false, and the run reported success.

`Rows` is digest lines; `Distinct` is separate requests, recomputed per platform. They are shown side by side because collapsing them into one number is what made the earlier series unreadable.

| Run date | run_at (UTC) | Msgs | Rows | Distinct | Ans (rows) | Ans (distinct) | Marginal | Rejected | Missed | Persisted |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-15 | 2026-09-15T20:02:11 | 14 | 24 | 24 | 3 | 3 | 7 | 14 | 1 | ✅ |
| 2026-09-15 | 2026-09-15T20:50:19 | 15 | 24 | 24 | 3 | 3 | 7 | 14 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:51:08 | 15 | 24 | 24 | 3 | 3 | 7 | 14 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:52:43 | 15 | 24 | 24 | 3 | 3 | 7 | 14 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:52:54 | 15 | 24 | 24 | 3 | 3 | 7 | 14 | 2 | ✅ |
| 2026-09-15 | 2026-09-15T20:54:21 | 15 | 24 | 24 | 3 | 3 | 7 | 14 | 2 | ✅ |
| 2026-09-18 | 2026-09-18T15:48:14 | 41 | 242 | 192 | 19 | 13 | 42 | 181 | 76 | ✅ |
| 2026-09-18 | 2026-09-18T15:49:22 | 41 | 242 | 192 | 19 | 13 | 42 | 181 | 76 | ✅ |
| 2026-09-18 | 2026-09-18T16:04:49 | 41 | 242 | 192 | 19 | 13 | 42 | 181 | 77 | ✅ |
| 2026-09-18 | 2026-09-18T16:54:57 | 41 | 242 | 192 | 18 | 13 | 42 | 182 | 77 | ✅ |
| 2026-09-18 | 2026-09-18T18:39:22 | 36 | 260 | 192 | 19 | 13 | 50 | 191 | 79 | ✅ |
| 2026-09-18 | 2026-09-18T21:41:22 | 38 | 280 | 192 | 19 | 13 | 54 | 207 | 91 | ✅ |
| 2026-09-19 | 2026-09-19T11:39:45 | 38 | 280 | 0 | 19 | 0 | 54 | 207 | 111 | ✅ |
| 2026-09-19 | 2026-09-19T18:41:09 | 38 | 280 | 0 | 19 | 0 | 54 | 207 | 111 | ✅ |
| 2026-09-19 | 2026-09-19T21:38:58 | 39 | 280 | 0 | 19 | 0 | 54 | 207 | 111 | ✅ |
| 2026-09-20 | 2026-09-20T11:39:57 | 39 | 280 | 0 | 19 | 0 | 54 | 207 | 119 | ✅ |
| 2026-09-20 | 2026-09-20T18:38:59 | 39 | 280 | 0 | 19 | 0 | 54 | 207 | 123 | ✅ |
| 2026-09-21 | 2026-09-21T11:40:01 | 41 | 300 | 65 | 20 | 8 | 55 | 225 | 151 | ✅ |
| 2026-09-21 | 2026-09-21T18:39:57 | 44 | 322 | 65 | 23 | 8 | 59 | 240 | 154 | ✅ |
| 2026-09-21 | 2026-09-21T21:39:34 | 46 | 345 | 65 | 27 | 8 | 67 | 251 | 164 | ✅ |
| 2026-09-22 | 2026-09-22T11:39:56 | 48 | 379 | 97 | 30 | 11 | 72 | 277 | 179 | ✅ |
| 2026-09-22 | 2026-09-22T18:39:12 | 51 | 418 | 97 | 35 | 11 | 85 | 298 | 193 | ✅ |
| 2026-09-22 | 2026-09-22T21:39:36 | 56 | 444 | 97 | 38 | 11 | 93 | 313 | 195 | ✅ |
| 2026-09-23 | 2026-09-23T11:39:18 | 58 | 472 | 28 | 40 | 2 | 99 | 333 | 227 | ✅ |

The most recent run reads `pending` by design: verification happens after the commit exists, so `push-log.json` and this table are committed one run behind. A run that stays `pending` across the next run is a run that never persisted.

## Answerable rate BY CHANNEL

Reported per channel and never blended. All four proven links (healthline DR91, eatthis DR83, womansworld DR66, singlecare DR63) came through **HARO**; none came through SOS or Qwoted. An average across the four would hide the only channel with a track record.

`Items` counts digest rows. `Distinct` counts separate requests: HARO re-runs the same query across its morning, afternoon and evening editions, so rows overstate opportunities by about a third. Both are shown rather than picking one and hiding the other.

| Channel | Items | Distinct | Answerable | Distinct answerable | Rate (distinct) | Marginal | Rejected | Reply path |
|---|---|---|---|---|---|---|---|---|
| **haro** | 355 | 268 | 27 | **24** | 9.0% | 76 | 252 | direct (`reply+…@helpareporter.com`) |
| **sos** | 102 | 96 | 9 | **9** | 9.4% | 20 | 73 | direct (journalist address in digest) |
| **qwoted** | 15 | 15 | 3 | **3** | 20.0% | 4 | 8 | manual click-through |
| **connectively** | 11 | 11 | 0 | **0** | 0.0% | 1 | 10 | manual (magic-link auth redirect) |

### The 14-day clock

**Starts 2026-09-15 — the first HARO query digest**, not the first run and not the signup date. Days before it measured SOS and Qwoted only, which is two channels that have never produced a link.

| | |
|---|---|
| Clock start (first HARO digest) | 2026-09-15 |
| Day of 14 | **9** |
| HARO digest rows ingested | 355 |
| HARO distinct requests | 268 |
| HARO answerable rows | 27 |
| **HARO distinct answerable requests** | **24** |

## Items per day by source

| Run date | SOS | Qwoted | HARO | Connectively | Total |
|---|---|---|---|---|---|
| 2026-09-15 | 18 | 6 | 0 | 0 | 24 (running 24) |
| 2026-09-18 | 48 | 3 | 205 | 11 | 267 (running 291) |
| 2026-09-19 | 0 | 0 | 0 | 0 | 0 (running 291) |
| 2026-09-20 | 0 | 0 | 0 | 0 | 0 (running 291) |
| 2026-09-21 | 0 | 2 | 63 | 0 | 65 (running 356) |
| 2026-09-22 | 28 | 4 | 67 | 0 | 99 (running 455) |
| 2026-09-23 | 8 | 0 | 20 | 0 | 28 (running 483) |

## Qwoted — does the free tier bind?

Qwoted's free tier allows **7 pitch credits**. That cap only matters if answerable volume exceeds it. The deciding number is the answerable column, not the received column.

| Run date | Qwoted items received | Of those, answerable |
|---|---|---|
| 2026-09-15 | 6 | 1 |
| 2026-09-18 | 3 | 0 |
| 2026-09-19 | 0 | 0 |
| 2026-09-20 | 0 | 0 |
| 2026-09-21 | 2 | 1 |
| 2026-09-22 | 4 | 1 |
| 2026-09-23 | 0 | 0 |

**Cumulative Qwoted answerable: 3.** Below the 7-credit cap, so the free tier is not yet the constraint.

## Rejection categories, cumulative

This is the dataset that separates *the filter is too tight* from *the niche is genuinely quiet*. If rejections cluster in topics the claim bank covers, the filter is wrong. If they are spread across finance, gift guides and cybersecurity, the niche is quiet.

| Category of rejected item | Count |
|---|---|
| General | 70 |
| Business and Finance | 56 |
| Lifestyle and Entertainment | 52 |
| Health and Pharma | 36 |
| Travel | 34 |
| Technology | 20 |
| Gift Bags | 19 |
| Lifestyle and Fitness | 13 |
| Podcasts | 12 |
| Health | 10 |
| uncategorised | 8 |
| Biotech and Healthcare | 6 |
| Public Policy and Government | 3 |
| Education | 3 |
| Beauty and Wellness | 1 |

| Rejection reason | Count |
|---|---|
| no vocabulary for either expert | 343 |

