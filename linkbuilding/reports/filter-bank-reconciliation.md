# Filter/bank reconciliation — the orphaned terms

Round 10 · generated from `data/claims.json` + `data/claim-synonyms.json`

## What this is

Round 9 caught the pipeline printing *"modality ['infrared'] named; the claim bank covers this directly"* for a term appearing in **zero of 30 claims**. The filter's term lists and the bank were maintained by different hands and nothing reconciled them.

Every clinical match term now resolves to at least one claim id or it does not match at all. **11 of 38 candidate terms (29%) have no backing claim and have been removed from the filter.** They are listed here in full; none was removed silently.

**No claim was added to the bank.** It is a reviewed artifact awaiting Dr. Alptunaer's signature, and writing into it outside his process is exactly what would make the signature meaningless. These are gaps for him to fill or decline.

## :rotating_light: The headline consequence

**Clinical answerable across the entire corpus is now 0, down from 1.**

The single clinical answerable ever recorded — a Connectively request about red light therapy for skin — matched on `infrared`, and `infrared` has no claim behind it. Removing the orphan removed the match. Nothing else in 242 rows changed verdict.

That is a real finding, not a regression. The honest reading: **the clinical filter has never once matched a request the bank could actually answer.** The one that looked like a match was a vocabulary accident, and had the bank been signed and a drafter existed it would have been pitched under a physician's name with nothing to say.

## The orphans

Three different problems, needing three different answers.

### 1. The concept is covered — under a different name  (needs one line from him, not new evidence)

| Term | Why it is an orphan | The bank's own term |
|---|---|---|
| `cold plunge` | appears ONLY inside `do_not_say` on `cold-glucose-01` and `cold-timing-01` | `cold water immersion` (4 claims) |
| `cold-plunge` | same concept, hyphenated | `cold water immersion` |
| `ice bath` | appears ONLY inside `do_not_say` on `cold-recovery-01` | `cold water immersion` |
| `ice baths` | same | `cold water immersion` |

**This is the most alarming class and the cheapest to fix.** `cold plunge` is the store's flagship product category, and the only place those words appear in the bank is a list of sentences that must never be said. Matching on it would have routed a request to a claim whose purpose is to forbid the answer. The bank does cover the concept — it calls it *cold water immersion* — so this needs a synonym confirmation, not a new study.

It was **not** self-approved. Deciding that a consumer term and a clinical term mean the same thing is a clinical judgement, and this round does not make clinical judgements.

### 2. The concept is genuinely absent  (needs evidence, or a decision to decline)

| Term | Status |
|---|---|
| `infrared` | no claim mentions infrared; no claim concerns skin, light or photobiomodulation |
| `steam room` | the sauna claims are about dry/Finnish sauna; steam is a different modality |
| `cryotherapy` | whole-body cryotherapy is not cold-water immersion; no claim covers it |
| `thermal` | generic; would match `thermal imaging` and `thermal printer` as readily as heat |
| `longevity` | absent from every claim, and the do_not_say lists explicitly forbid "sauna use will extend your life" |

`longevity` deserves its own line: it was a *match* term while being, in substance, a banned claim. The bank supports **mortality** findings in one Finnish cohort and forbids translating them into life extension.

### 3. Backed only by an index label  (the label is real, the claim text is not)

| Term | Status |
|---|---|
| `hydration` | a `topics` label on `hydration-01` and `hydration-02`, but neither claim's text mentions hydration |
| `dehydration` | absent entirely; and a claim about staying hydrated would not back a query about dehydration — the opposite state |

## What still matches, and on whose authority

Every surviving term carries its claim ids, so a match now says which claim it rests on instead of asserting that one exists. The reason string changed from *"the claim bank covers this directly"* to *"backed by ['heat-cv-mortality-01', …]"*.

| Term | Backed by | How |
|---|---|---|
| `blood pressure` | `heat-bp-01`, `heat-vascular-01`, `heat-vascular-limits-01`, `safety-alcohol-01` +1 | exact |
| `brown fat` | `cold-bat-01`, `cold-glucose-01` | exact |
| `cardiovascular` | `heat-cv-mortality-01`, `heat-cv-mortality-02`, `heat-allcause-01` | exact |
| `cognition` | `heat-cognition-01` | morphological |
| `cold exposure` | `cold-bat-01`, `cold-glucose-01` | exact |
| `cold water immersion` | `cold-mood-01`, `cold-affect-01`, `cold-recovery-01`, `cold-hypertrophy-limits-01` +2 | exact |
| `cold-water immersion` | `cold-mood-01`, `cold-affect-01`, `cold-recovery-01`, `cold-hypertrophy-limits-01` +2 | exact |
| `contrast therapy` | `contrast-therapy-01` | exact |
| `dementia` | `heat-cognition-01` | exact |
| `depression` | `heat-mood-01` | morphological |
| `heart` | `safety-contraindications-01`, `safety-stable-cad-01` | exact |
| `heat acclimation` | `heat-shock-01` | exact |
| `heat exposure` | `heat-vascular-01`, `heat-shock-01`, `safety-pregnancy-01` | exact |
| `heat therapy` | `heat-vascular-01`, `heat-vascular-limits-01` | exact |
| `hyperthermia` | `heat-mood-01`, `safety-pregnancy-01`, `safety-pregnancy-02` | exact |
| `hypertrophy` | `cold-hypertrophy-limits-01`, `cold-timing-01` | exact |
| `inflammation` | `heat-shock-02` | morphological |
| `insomnia` | `sleep-slowwave-01` | exact |
| `metabolic` | `heat-shock-02`, `cold-bat-01`, `cold-glucose-01` | exact |
| `mood` | `cold-mood-01` | exact |
| `mortality` | `heat-cv-mortality-01`, `heat-cv-mortality-02`, `heat-allcause-01`, `heat-vascular-limits-01` | exact |
| `muscle soreness` | `cold-recovery-01`, `contrast-therapy-01` | exact |
| `pregnancy` | `safety-pregnancy-01`, `safety-pregnancy-02` | exact |
| `recovery` | `cold-recovery-01`, `cold-hypertrophy-limits-01`, `contrast-therapy-01` | exact |
| `sauna` | `heat-cv-mortality-01`, `heat-cv-mortality-02`, `heat-allcause-01`, `heat-bp-01` +14 | exact |
| `saunas` | `heat-cv-mortality-01`, `heat-cv-mortality-02`, `heat-allcause-01`, `heat-bp-01` +14 | exact |
| `sleep` | `sleep-passive-heating-01`, `sleep-slowwave-01` | exact |

## Concept matching — what it actually bought

Each claim now carries a synonym set derived from its own text and citation titles (`data/claim-synonyms.json`). The raw derivation is large and noisy — 3,156 n-grams including `actual`, `days` and `damages` — so a form is kept only when it would match text that a backed anchor would **miss**.

On that rule the yield is **four concepts**, not two hundred:

| New surface form | Reaches | Via claim |
|---|---|---|
| `cognitive`, `cognitive decline` | queries saying *cognitive*, never *cognition* | `heat-cognition-01` |
| `depressive`, `depressive symptoms`, `major depressive disorder` | queries saying *depressive* | `heat-mood-01` |
| `inflammatory` | queries saying *inflammatory* | `heat-shock-02` |
| `contrast water therapy` | the bank's own phrasing | `contrast-therapy-01` |

Reporting this as 263 surface forms would have been true and useless: `finnish sauna` cannot match text that `sauna` does not already match. The number that means anything is four.

**It does not reach `light-based skin treatments`.** Round 9's near-miss stays a miss, and it should: no claim in the bank mentions light. Concept matching widens to the edge of the evidence and stops there.

## The specialty gap

`data/experts.json` now carries `specialty: null` for Dr. Alptunaer, with a note. It is **not guessed**.

Round 9 found **16 of 112** HARO requests that are squarely medical but call for a named specialty: dermatology (4), veterinary (4), psychiatry or behavioural neurology (3), reproductive medicine (2), transplant surgery, plastic surgery, dentistry. Until the field is filled those 16 are **unresolvable** — neither reachable nor rejected. Filling it is the cheapest single action available to this project.
