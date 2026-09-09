---
batch: the 8 ASSERTS from data/article-claim-register.json
status: STAGED — drafted, not applied. Awaiting approval.
read: 2026-09-09, each article opened and read at SECTION scope, not sentence scope
result: 8 flagged -> 1 already fixed, 3 need an edit, 4 verdicts reversed on reading
---

## What the full read changed

The register assigned every verdict from **the sentence the screen returned**.
Reading each one inside its heading and its paragraph reversed four of eight.
One root cause, and it is the error CLAUDE.md already names twice:
*a screen selects the unit of work; a full read defines it.*

| article | register said | after reading | why |
|---|---|---|---|
| `what-is-a-german-sauna` | ASSERTS | **FIXED** | applied 2026-09-09 |
| `sauna-for-arthritis-joint-pain-relief` | ASSERTS | **ASSERTS** | stands, and it is the worst in the set |
| `sauna-for-autoimmune-condition-symptom-relief` | ASSERTS | **ASSERTS** | stands |
| `benefits-of-cold-plunge-and-sauna` | ASSERTS | **NEEDS_LIMITATION** | cited in the next clause; population and limitation missing |
| `are-infrared-saunas-safe` | ASSERTS | **EXEMPT — warning** | sits under *"Infrared Saunas and Medication: A Critical Interaction Guide"*, explaining the mechanism of a risk |
| `heat-shock-proteins-cell-culture-to-humans` | ASSERTS | **EXEMPT — warning** | the answer to *"Is sauna safe if I have heart disease?"*, naming contraindications |
| `chromotherapy-vs-no-chromotherapy-buyers-guide` | ASSERTS | **REPORTS** | the next two sentences give the trials, the non-sauna setting, and *"may offer modest"* |
| `dry-sauna-for-home` | ASSERTS | **REPORTS** | cited, and followed by *"Evidence strength: Moderate. Small trials and short durations limit conclusions."* |

**Two of the four reversals are the by-kind exemption doing exactly what it was
written to do.** The screen fired on a mechanism sentence *inside a safety
warning* — the class the client exempted on 9 September — and the register missed
it because a sentence has no heading.

**This is the argument for read-and-record, not an embarrassment to it.** A count
criterion would have "fixed" all eight and damaged five: two safety warnings
hedged, one careful evidence paragraph gutted, one limitation deleted as
redundant. The register held the judgement, so the error is visible and
correctable. A checkbox would have hidden it.

---

## Draft 1 — `sauna-for-arthritis-joint-pain-relief` (27 impr, pos 17.3)

**The heading first. An assertion in an `<h2>` is the most prominent position on
the page, and it appears twice — the `<h2>` and its table-of-contents entry.**

> **Now:** The Biological Mechanism: How Heat Heals Joints

> **Proposed:** The Proposed Mechanism: Heat, Blood Flow, and Muscle Guarding

The anchor id `#biological-mechanism` and `id="h.t6o27eijoruk"` are unchanged, so
the ToC link keeps working. Only the visible text changes, in both places.

*"Heals" is the whole problem. The section's own third subhead already reads
"(What's Plausible, What's Not Proven in Arthritis)" — the article knows. The
heading contradicts its own contents.*

**And the mechanism sentence.**

> **Now:** Sauna heat causes vasodilation—the widening of blood vessels—and increases heart rate and cardiac output, leading to increased blood flow to skin and muscles. This enhanced circulation helps deliver oxygen and nutrients while removing inflammatory metabolites from joint tissues (Healthline, 2023).

> **Proposed:** Sauna heat raises skin and core temperature, and the physiology literature describes the response as vasodilation — the widening of blood vessels — with a raised heart rate and more blood reaching skin and muscle. Whether that increased flow clears inflammatory metabolites from joint tissue specifically has not been shown in arthritis patients. We collect the research at <a href="https://healthresearchdatabase.com">healthresearchdatabase.com</a> rather than summarising it here.

**A second defect found while reading, and it is worth naming: the source was
Healthline.** A content site was carrying a mechanism claim about synovial tissue
on an article about a medical condition. The rewrite drops it rather than moving
it, because there is nothing to move — the claim it supported is the claim being
withdrawn.

---

## Draft 2 — `sauna-for-autoimmune-condition-symptom-relief` (46 impr, pos 12.1)

> **Now:** Heat exposure causes vasodilation — the widening of blood vessels — which temporarily improves circulation to muscles and joints. This increased blood flow may reduce stiffness and bring more oxygen to inflamed tissue.

> **Proposed:** Heat exposure produces vasodilation — the widening of blood vessels — and the physiology literature describes a temporary increase in circulation to muscles and joints. Whether that translates into less stiffness in an autoimmune condition is what the trials below actually tested, and the research is collected at <a href="https://healthresearchdatabase.com">healthresearchdatabase.com</a>.

*Uncited mechanism on a medical-condition article. The section immediately after
this one is headed "Pain and stiffness: what the trials actually measured" — so
the rewrite points the reader at the article's own strongest section instead of
answering ahead of it. The section intro already says the mechanisms "explain
symptom modulation — not disease modification", which is why this is one clause
rather than a rebuild.*

---

## Draft 3 — `benefits-of-cold-plunge-and-sauna` (137 impr, pos 9.6) — NEEDS_LIMITATION

> **Now:** When you enter a sauna, your core temperature rises. Blood vessels dilate to move heat toward the skin's surface, heart rate increases, and sweating begins. These responses mimic some of the cardiovascular demands of moderate-intensity exercise [Mayo Clinic Proceedings, 2018].

> **Proposed:** When you enter a sauna, your core temperature rises. Blood vessels dilate to move heat toward the skin's surface, heart rate increases, and sweating begins. These responses mimic some of the cardiovascular demands of moderate-intensity exercise [Mayo Clinic Proceedings, 2018] — a comparison drawn from observational cohort work in Finnish populations, which shows association rather than cause.

*The physical description stays exactly as it is: vessels dilating and sweat
starting is what happens in a hot room, and hedging it would fail rule 6a. What
was missing is the limitation on the exercise comparison, which is the part
carrying weight for a buyer.*

**The added clause is the wording already live on
`chromotherapy-vs-no-chromotherapy-buyers-guide` for the same Laukkanen
citation**, applied at 15:08 on 9 September. Using it verbatim is deliberate: one
citation, one limitation, phrased the same way everywhere it appears.

---

## No action, with reasons

**`are-infrared-saunas-safe`** — *"Sauna bathing acutely increases heart rate and
causes blood pressure changes through vasodilation."* Sits under a medication
interaction guide, after a sentence naming dehydration, low blood pressure and
overheating as the risks. **This is the mechanism of a harm of use.** Hedging it
makes the page less safe, which is the exemption in rule 4 exactly.

**`heat-shock-proteins-cell-culture-to-humans`** — *"Sauna increases heart rate
and cardiovascular load similar to moderate exercise."* It is the reason clause
inside the answer to *"Is sauna safe if I have heart disease?"*, next to
*"generally contraindicated in unstable angina, recent heart attack, or severe
valve disease"*. Same exemption.

**`chromotherapy-vs-no-chromotherapy-buyers-guide`** — the flagged sentence is a
buyer-profile line, and the two sentences after it give the trials, say the
studies are *not sauna-specific*, and conclude *"may offer modest psychological
benefits for some users"*. Population, limitation, hedge. REPORTS.

**`dry-sauna-for-home`** — carries `(PMC, 2021)` and is followed two lines later
by *"Evidence strength: Moderate. Small trials and short durations limit
conclusions."* REPORTS. **Still opens for the infrared-vs-traditional rescue**,
where the whole article gets a read; noting here that its claim line needs
nothing.

---

## Logged while reading, not fixed

- **`sauna-for-arthritis-joint-pain-relief` cites Healthline twice** — once for
  the joint-tissue mechanism (removed in draft 1) and once for the infrared
  definition. The second is a definition and survives, but a content site is not
  a source for either.
- **`best-infrared-sauna-muscle-recovery` lists two Reddit threads in its
  bibliography** as sources, alongside the Sunlighten entry cut today.
- **`sauna-for-arthritis-joint-pain-relief` cites `(PMC, 2021)` three times**
  without naming the study. "PMC" is a library, not a citation.
