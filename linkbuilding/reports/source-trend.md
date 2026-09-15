# Source trend — cumulative

Rebuilt on every run of `pipelines/01_source.py`. **No drafts, no pitches, nothing sent.**

## Decision criteria — fixed before the data arrived

Stated up front so the conclusion cannot be fitted to whatever turns up.
Assess after **14 days** of accumulation.

| If, after 14 days | Then |
|---|---|
| **>= 1 answerable per week** | `01_source` earns its place. Build the drafter. |
| **Answerable, but all from Qwoted** | Evaluate Qwoted Pro at $149/mo. The free tier's request delay and pitch-credit cap become the binding constraint. |
| **Zero answerable, marginals clustering in one topic** | The gap is in the claim bank, not the pipeline. Extend the bank in that topic. |
| **Zero answerable, marginals scattered** | The niche is quiet. Keep the filter running cheaply and move effort to dealer pages and outreach. |

A fifth outcome is possible and must not be silently folded into the fourth:
if `deadline misses on arrival` is high, the pipeline may be finding real
requests too late rather than not finding them. Check that row before
concluding the niche is quiet.

---

## Where we are

| | |
|---|---|
| Runs recorded | 7 |
| Calendar days covered | 1 of 14 |
| Items ingested | 24 |
| **Answerable (cumulative)** | **0** |
| Marginal (cumulative) | 4 |
| Rejected (cumulative) | 20 |
| Since last answerable | never — no answerable item has been seen |
| Deadline misses on arrival | 0 |

## Per run

| Run date | run_at (UTC) | Msgs | Items | Answerable | Marginal | Rejected | New | Missed |
|---|---|---|---|---|---|---|---|---|
| 2026-09-15 | 2026-09-15T19:36:19 | 13 | 23 | 0 | 4 | 19 | 23 | 0 |
| 2026-09-15 | 2026-09-15T19:36:59 | 14 | 24 | 0 | 4 | 20 | 1 | 0 |
| 2026-09-15 | 2026-09-15T19:37:31 | 14 | 24 | 0 | 4 | 20 | 0 | 0 |
| 2026-09-15 | 2026-09-15T19:38:04 | 14 | 24 | 0 | 4 | 20 | 0 | 0 |
| 2026-09-15 | 2026-09-15T19:53:55 | 14 | 24 | 0 | 4 | 20 | 0 | 0 |
| 2026-09-15 | 2026-09-15T19:55:39 | 14 | 24 | 0 | 4 | 20 | 0 | 0 |
| 2026-09-15 | 2026-09-15T19:57:18 | 14 | 24 | 0 | 4 | 20 | 0 | 0 |

## Items per day by source

| Run date | SOS | Qwoted | Total |
|---|---|---|---|
| 2026-09-15 | 18 | 6 | 24 (running 24) |

## Qwoted — does the free tier bind?

Qwoted's free tier allows **7 pitch credits**. That cap only matters if answerable volume exceeds it. The deciding number is the answerable column, not the received column.

| Run date | Qwoted items received | Of those, answerable |
|---|---|---|
| 2026-09-15 | 6 | 0 |

**Cumulative Qwoted answerable: 0.** Below the 7-credit cap, so the free tier is not yet the constraint.

## Rejection categories, cumulative

This is the dataset that separates *the filter is too tight* from *the niche is genuinely quiet*. If rejections cluster in topics the claim bank covers, the filter is wrong. If they are spread across finance, gift guides and cybersecurity, the niche is quiet.

| Category of rejected item | Count |
|---|---|
| Business and Finance | 5 |
| General | 5 |
| uncategorised | 4 |
| Technology | 3 |
| Travel | 2 |
| Lifestyle and Fitness | 1 |

| Rejection reason | Count |
|---|---|
| no claim-bank vocabulary present | 20 |

