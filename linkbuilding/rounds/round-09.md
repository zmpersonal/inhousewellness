# Round 9 — Dedup, and test the bank-scope hypothesis

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-09.md` first.

## 1. Cross-edition dedup

HARO repeats queries across its three daily editions — 162 rows, 112 distinct
reply addresses. Dedup on reply address.

Changing the dedup key changes what historical counts mean. Recompute the trend
from stored snapshots so the series is consistent, and state in the report that
pre-Round-9 figures were row counts.

## 2. Dump the evidence — this is the round's real purpose

162 HARO items produced 0 clinical answerable and 14 marginal for Dr.
Alptunaer. HARO produced all four of his proven links. Both cannot be right.

The hypothesis: `claims.json` is scoped to the product (sauna, heat, cold,
recovery) rather than to the expert's competence. The Healthline placement
appears to have been about heart attack risk in younger males — general
cardiology, which the bank cannot match.

Produce `linkbuilding/reports/haro-corpus-review.md`:

- All 14 Alptunaer-marginal items, quoted in full with outlet and the anchor
  that matched
- All 112 distinct HARO queries, one line each: outlet, topic, and the reason
  for rejection
- Group the rejections by subject area

Do NOT change the filter. Do NOT widen the bank. Do NOT tune anything. This
round produces evidence for a human decision about scope — nothing more.

## 3. Report the question plainly

At the end of the corpus review, state: of the 112 distinct HARO queries, how
many are within the general competence of a practising physician, versus how
many are outside any medical scope at all. Give the count.

That number decides whether the bank is mis-scoped or the channel is quiet, and
it is the last open question in this project.

## Acceptance criteria

- [ ] Dedup on reply address; trend recomputed from snapshots
- [ ] All 14 marginals quoted in full
- [ ] All 112 distinct queries listed with rejection reason
- [ ] Physician-competence count reported
- [ ] Filter, bank and anchor lists unchanged
- [ ] Zero drafts, zero sends, mailbox unmodified

## Stop and ask if

- Dedup changes the answerable count by more than 2
- More than 40 of 112 queries fall within general physician competence — that
  is a larger mis-scope than expected and worth confirming before it is acted on
