# Round 13 — Three regimes

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-13.md` first.

> Dr. Alptunaer has confirmed two things: the five experience topics are
> correct, and he is willing to be cited on anything medical provided the claim
> is accurate with modern medical advice. The second is broader than the claim
> bank and needs its own enforcement. Nothing here relaxes verification — it
> moves it to draft time.

## 1. Experience set — approved, with provenance

`experience.json` for Alptunaer. Topics exactly: exercise, diet, recovery,
sports performance, military performance. No additions, no inferred anchors.

`approved: true`, `evidentiary_regime: experience`, and record provenance:
confirmed by the expert, relayed by Julian, with the date. Do not describe this
as a signature.

Uncited by design. Must never be presented as literature.

## 2. General medical — verified at draft time

New regime, `evidentiary_regime: verified_at_draft`.

His condition is accuracy with modern medical advice. The drafter's own
knowledge cannot satisfy that — enforce it:

- Every factual medical assertion in a draft carries a citation retrieved and
  verified via the Firecrawl research tools **at draft time**, same gate as
  `claims.json`: resolved PMID or DOI, exact returned title stored
- Prefer current clinical guidelines and consensus statements — CDC, AHA, ACEP,
  USPSTF, specialty society guidance — over individual studies. Record which
- **No verified citation, no assertion.** Drop the sentence rather than
  soften it into something unsourced
- Every draft in this regime is marked `requires_expert_review: true` and cannot
  be marked ready-to-send without it

Where only a general clinical perspective is possible with no specific factual
claim, say so and flag the item — do not pad it with unsourced generalities.

## 3. Drafting across all three

Source precedence: claim bank → experience set → general medical. Record which
regime and which ids every draft used.

The attribution guard applies unchanged to all three. Credential line verbatim.
`framing` required: `published-evidence`, `clinical-experience`, or
`verified-guideline`.

Requirement mismatches from Round 12 (the 4 items requesting a profession he
doesn't hold) stay flagged and surface first.

## 4. Review queue with deadlines

`reports/draft-queue.md`, grouped:

1. Requirement mismatches
2. `requires_expert_review` — with deadline and hours remaining. Anything
   expiring within 24 hours at the top, because expert review is the slow step
3. Ready for Julian's review — claim bank and experience-set drafts

Report how many drafts the review requirement puts at risk of expiring. That
number tells you whether this regime is workable at his response speed.

## 5. The ceiling, per regime

Rescore the full corpus. Report reachable and drafted counts per regime, and
the combined total against Round 12's zero.

Then state the Option C numbers alongside: 8 digests, 112 distinct requests,
zero about sauna, heat or cold. Give the numbers; do not argue a conclusion.

## Still open — ask, do not block

Two questions unanswered. Surface both in the report for the human:

- Which experience topics does he speak to as an EM physician versus as an
  informed individual? EMT-T bears on military and performance.
- The seven preliminary claims in `claims.json`: any he'd rather strike?

`claims.json` `approval_status` stays unchanged.

## Acceptance criteria

- [ ] Experience set approved with honest provenance
- [ ] General-medical drafts carry verified citations per assertion; a draft
      with an unverified assertion is blocked, tested
- [ ] Every general-medical draft requires expert review; tested
- [ ] Attribution guard passes on every draft across all three regimes
- [ ] Queue grouped and deadline-sorted; at-risk count reported
- [ ] Per-regime ceiling reported
- [ ] Zero sends

## Stop and ask if

- More than 12 drafts produced — check against the 16-of-17 failure first
- A draft can only be written by asserting something no citation supports
- A guideline found at draft time contradicts a claim in `claims.json`
