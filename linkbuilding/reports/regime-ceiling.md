# The ceiling, per regime — Round 13

Generated 2026-09-21 · corpus is now **213 distinct requests** across four platforms (152 of them HARO, from 18 ingest runs since 2026-09-15)

## Drafts produced

| | |
|---|---|
| **Drafts** | **2** |
| — `claim_bank` | 0 |
| — `experience` | 0 |
| — `verified_at_draft` | 2 |
| Requiring his review before they can be called ready | 2 |
| At risk of expiring within 24h | 0 |

Against Round 12's **zero**. Both drafts carry citations retrieved and resolved this session — five of them, each with a PMID or DOI and the exact title as returned.

## Regime assignment across the corpus

| Regime | Requests | Still live |
|---|---|---|
| `claim_bank` | **0** | 0 |
| `experience` | 5 | 2 |
| `verified_at_draft` | 181 | 81 |
| `not_a_query` | 27 | 23 |

⚠️ **181 is not a reachability figure and must not be read as one.** `verified_at_draft` is the *fallback* bucket — everything the other two regimes do not claim lands there, including travel features, gift guides and CISO cybersecurity. It means "no approved source covers this yet", not "he could answer this".

The competence-based figure from Round 11 is still the meaningful one: **17 reachable of the 112 classified**, of which **4 still have a live deadline**. The other 40 HARO requests ingested since then have not been competence-classified.

## The Option C numbers, stated plainly

| | |
|---|---|
| HARO digests ingested | 18 runs, 2026-09-15 → 2026-09-21 |
| Distinct HARO requests | 152 |
| Distinct requests, all platforms | 213 |
| **Requests about sauna, heat or cold** | **0** |
| Requests the claim bank covers | 0 |
| `alptunaer` answerable in the pipeline | 0 |

The 30-claim bank has now matched nothing across 213 requests and 18 ingest runs. Round 9 reported zero against 112; the figure has not moved with more than double the corpus. These are the numbers; the conclusion is the human's.

## What the new regime actually changed

It moved the constraint. Before, nothing could be drafted because no approved source covered any request. Now the sources can be built per draft — but each one costs real citation retrieval, and **every one needs his review before it can be sent**. Two drafts took five verified citations to write.

So the binding question is no longer coverage. It is his response speed against HARO deadlines, which run 24–96 hours. Neither of these two is at risk, but that is because they happened to be 30 and 84 hours out when they were written. **The at-risk count is the number to watch, and it is the thing that decides whether this regime is workable.**

## Still open — two questions for the human

### 1. Which experience topics does he speak to as an EM physician, and which as an informed individual?

Recorded unanswered in `data/experience.json` under `open_question`. It bears hardest on **military performance** and **sports performance**: EMT-T is tactical EMT and is directly relevant to both. The distinction changes how a draft introduces him on those topics, and it has not been guessed at. Nothing in this round widened scope on the strength of EMT-T.

### 2. The seven `preliminary` claims in `claims.json` — any he would rather strike?

Still unanswered from the claim-bank review. They rest on mechanistic, small or single-study evidence — nine participants in one case, cellular markers rather than outcomes in others. The review document groups them so the whole tier can be struck in one decision. **`approval_status` is unchanged at `awaiting_review`.**

Neither question blocked this round, and neither was answered by assuming.
