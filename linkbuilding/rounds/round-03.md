# Round 3 — Build the claim bank

Load the `agent-harness` skill. Standard round rules apply: tiered approvals,
BLOCKED/REVIEW/FYI reporting, RUNLOG.md entry on completion.

> **What this is.** A structured, cited set of claims about sauna, heat therapy
> and cold exposure that Dr. Timur Alptunaer has approved for attribution in his
> name. `01_source` (Round 4) assembles journalist pitches *only* from this bank.
> A claim not in the bank cannot be pitched.
>
> **Why it exists.** His standing approval is conditional on claims being backed
> by medical science. The bank makes that condition operational and auditable.
> Without it, every pitch is an unreviewed medical assertion published under a
> physician's name.

## Working directory

All work inside `linkbuilding/`. Do not touch anything outside it.
`linkbuilding/CLAUDE.md` governs; Hard Rules 1–8 binding.

## Scope — build ONLY these

- `linkbuilding/data/claims.json`
- `linkbuilding/reports/claim-bank-review.md` (the document he signs off)
- `linkbuilding/pipelines/lib/claims.py` (load, validate, query, drift-check)

Do NOT build `01_source`. Do NOT write pitches. Do NOT contact anyone.

## THE CRITICAL RULE

Every citation must be verified to exist before it enters the bank. Use
`firecrawl_research_search_papers`, `firecrawl_research_inspect_paper`,
`firecrawl_research_read_paper`. Never write a citation from memory. Never
construct a plausible DOI. Never cite a paper you have not retrieved metadata
for.

You have already proven the gate works: `10.1001/jamainternmed.2031.99187`
returns 404 rather than a near-match. Enforce it in code — `claims.py` raises
on any record missing a resolved PMID or DOI.

A hallucinated citation attributed to a named physician in national health
media is worse than producing nothing.

## Claim structure

```json
{
  "id": "heat-cv-mortality-01",
  "claim": "One sentence, quotable, in plain language.",
  "confidence": "strong | moderate | preliminary",
  "evidence_type": "prospective cohort | RCT | meta-analysis | mechanistic | animal",
  "citations": [
    {"pmid": "25705824", "doi": "10.1001/jamainternmed.2014.8187",
     "title": "exact title as returned by inspect_paper",
     "year": 2015, "journal": "...", "n": 0,
     "verified_via": "inspect_paper", "verified_at": "ISO date"}
  ],
  "hedge": "The qualifier that must travel with this claim.",
  "do_not_say": ["Overclaims this must never be stretched into"],
  "topics": ["heat", "cardiovascular"]
}
```

**Drift check.** `claims.py` exposes a revalidate function: re-resolve every
stored ID and compare the returned title against the stored one. Mismatch
raises. This is why the exact title is stored rather than prose with a citation
appended.

## Confidence tiers, applied honestly

- **strong** — multiple human studies, ideally prospective cohort or
  meta-analysis. Statable plainly.
- **moderate** — single good human study, or consistent smaller ones. Must
  carry its hedge.
- **preliminary** — mechanistic, animal, or small/short human work. Framed as
  early evidence, never established.

A bank where everything is `strong` is a bank nobody checked.

## Topic coverage

Heat and cardiovascular outcomes; heat and all-cause mortality; sauna and
sleep; heat shock response; cold exposure and metabolic markers; cold and mood
or alertness; cold and inflammation or recovery; contrast therapy; hydration
and safety; contraindications.

25–40 claims. Breadth over volume — a query about sleep is useless if every
claim is cardiovascular.

**Include contraindications and limits deliberately.** A source who volunteers
who *shouldn't* use a sauna is more credible than one selling only benefits,
and it is the part a physician's name most needs to be attached to.

## Search areas — verify everything

Finnish prospective cohort work on sauna frequency and cardiovascular and
all-cause mortality (Laukkanen 2015, PMID 25705824, already verified — use as
the anchor); sauna and blood pressure or arterial stiffness; cold water
immersion and brown adipose tissue; cold immersion and post-exercise recovery,
including findings that cold *blunts* hypertrophy adaptation — a limits claim
worth having; heat shock protein response to passive heat; whole-body
hyperthermia and depressive symptoms; safety literature including cardiac
events, alcohol interaction, pregnancy.

Where evidence is genuinely contested, record `moderate` or `preliminary` with
the hedge rather than picking the flattering side.

## Prohibited claims

No claim implying treatment, cure, or prevention of a named disease. No weight
loss framed as fat loss rather than fluid. No claim that a product outperforms
a comparator absent a head-to-head study. Nothing drawn from manufacturer
marketing. If a topic can only be supported by marketing copy, leave the gap
and note it.

## The review document

`reports/claim-bank-review.md` is what Dr. Alptunaer reads and signs. Structure
for a clinician's time: claim, confidence, evidence type, citation with journal
and year and sample size, required hedge, and the overclaims it must not be
stretched into. Group by topic. List every `preliminary` claim at the top so he
can reject that tier wholesale.

End with a plain statement of what he is approving: standing attribution of
these specific claims, hedges intact, without per-pitch review.

## Acceptance criteria

- [ ] Everything lives under `linkbuilding/`
- [ ] Every claim carries ≥1 citation verified via `inspect_paper`
- [ ] `claims.py` raises on any claim missing a resolved PMID or DOI
- [ ] Drift check implemented and tested against a deliberately corrupted title
- [ ] Confidence tiers distributed, not uniformly `strong`
- [ ] Contraindications and limits represented, not only benefits
- [ ] Every claim has a `hedge` and ≥1 `do_not_say`
- [ ] ≥6 topic areas covered
- [ ] Review document readable by a clinician in under 20 minutes

## Stop and ask if

- A topic yields no verifiable human evidence — report the gap, do not fill it
  with mechanistic or animal work relabelled `strong`
- More than 80% of claims land in one confidence tier
- You want to soften a `do_not_say` to make a claim more quotable — that is the
  signal to stop and flag it

## Not in this round

`01_source` is Round 4 and depends on this bank plus a week of accumulated
digest samples. The `roundup` tactic split is also Round 4. The five
paid-pattern links remain `unresolved`.
