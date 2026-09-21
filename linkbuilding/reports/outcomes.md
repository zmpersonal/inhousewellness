# Outcomes — sent, published, linked

**This replaces answerable-rate as the headline.** Answerable was always a proxy for this: a guess about what a journalist might use. These are what they did.

Generated 2026-09-21T21:31:00+00:00

| | |
|---|---|
| Pitches sent (by a human) | **1** |
| — of which never reached the journalist | 1 |
| Reached the journalist, or unknown | **0** |
| Published | **0** |
| Pending | 1 |
| Carrying a link to inhousewellness.com | **0** |
| — follow | 0 |
| — nofollow | 0 |
| Median send → publication | no publication timed yet |

> ⚠️ **1 pitch(es) never reached the journalist.** A pitch that was not delivered is not a pitch that failed, and it does not belong in the denominator of any rate below — it measures a delivery problem, not the drafting. Non-delivery is only ever recorded from a notice that was actually read; the absence of one is never taken as proof of arrival.

> **`pending` is not a failure and is never counted as one.** A pitch nobody answered stays pending indefinitely. Publication is never inferred from silence, so no rate below treats these as rejections — the denominator for a publication rate is *confirmed outcomes*, not *sends*.

## By regime

| Regime | Sent | Published | Linked | Pending |
|---|---|---|---|---|
| `verified_at_draft` | 1 | 0 | 0 | 1 |

## By platform

| Platform | Sent | Published | Linked | Pending |
|---|---|---|---|---|
| `haro` | 1 | 0 | 0 | 1 |

## The record

| Item | Outlet | Sent | Delivered | Status | Body vs draft | Link | rel |
|---|---|---|---|---|---|---|---|
| `reply+554a52ca-1344-40d1-a750-a5e1` | Health Insiders | 2026-09-21T20:56 | **NO** | pending | **edited** (23% same) | — | — |

### Why the sent body is stored

Outcomes are attributed to the text the journalist actually received, not to the pipeline's draft. The first real send was hand-edited before it went out and shares only 23% of its wording with the queued version — crediting a published link to the untouched draft would measure the wrong artifact. Both bodies are kept in `data/sends.json`; the diff between them is the best available signal on how the drafter should change.

### Non-delivery: Health Insiders

> The journalist has chosen to receive only pitches written by a person, so every submission to this query runs through AI detection. Yours scored above the cutoff they set.

Notified 2026-09-21T21:06:04+00:00.

## Cadence

`01_source.py outcomes` is the weekly check. **It is not attached to a Routine yet** — `linkbuilding` had no weekly verify job before this round, so this one is defined rather than inherited. Until it is scheduled or run by hand, `last_checked` is the honest record of when anything was actually looked at.

