---
target: /blogs/saunas/how-saunas-improve-circulation   # rewrite IN PLACE, no new URL
decision: retarget + correct. Not a rescue (0 impressions), not a build (4,450 words already here)
primary_keyword: sauna for cardiovascular health
secondary: sauna for heart health
status: DRAFT — nothing applied
methods:
  evidence: PubMed abstract read directly, 16 Sep 2026 — PMID 25705824, DOI 10.1001/jamainternmed.2014.8187
  route: https://healthresearchdatabase.com/topics/sauna-heat-therapy/ (200, 87 publications / 53 trials)
  claims_screened: scripts/audit/health-claim-screen.mjs fixtures pass; 25 effect sentences, 15 unhedged
---

# Cardiovascular retarget — draft

## The defect that decides the rewrite

The live page says, with no source, no population and no limitation:

> Compared with men who used saunas once weekly, those bathing 2–3 times per week had a
> **22% lower risk of sudden cardiac death**, and those using saunas 4–7 times per week had a
> **63% lower risk**.

**Read against the abstract, the 22% is a non-significant result reported as fact.**
Hazard ratio 0.78, 95% CI **0.57–1.07** — the interval crosses 1. The 4–7 figure is real
(HR 0.37, 95% CI 0.18–0.75) and rests on 201 men and 10 sudden cardiac deaths.

This is variant 4 of the wrong-source family already in CLAUDE.md: right source, right number,
wrong certainty. It is also the single best thing this page can say, because saying it is what
no competitor will do.

## Title and meta

| field | draft | decoded length |
|---|---|---|
| article title (H1) | Sauna and Cardiovascular Health: What One Finnish Cohort Actually Found | 70 |
| SEO title | Sauna for Cardiovascular Health: What the Evidence Shows | 56 |
| meta description | A Finnish cohort of 2,315 men found fewer sudden cardiac deaths at 4–7 sauna sessions a week. Observational, and the 2–3 result was not significant. | 148 |

The SEO title carries `sauna for cardiovascular health` verbatim. `sauna for heart health` is
carried by an H2, not by the title — the page must not depend on one term, and that term ran
5,400 → 74,000 → 40,500 over twelve months.

## Opening — answer-first on the physical fact, then the evidence

> A traditional sauna runs 150–195°F and most sessions last 15–20 minutes. What that does to
> your circulation in the moment is not disputed: vessels widen, heart rate rises, and blood
> pressure falls for a while afterwards.
>
> What it does over years is a different question, and the answer rests mostly on one study.
> Researchers followed **2,315 middle-aged men in Eastern Finland** — aged 42 to 60 at baseline,
> for a median of **20.7 years**. Men who used a sauna **4–7 times a week** had a lower rate of
> sudden cardiac death than men who went once a week: hazard ratio **0.37 (95% CI 0.18–0.75)**,
> which is the "63% lower risk" figure you see quoted everywhere.
>
> The number you see quoted almost as often is **22% lower risk, for 2–3 sessions a week. That
> result was not statistically significant** — hazard ratio 0.78, with a confidence interval of
> 0.57 to 1.07. An interval that crosses 1.0 is consistent with no effect at all.
>
> And the study is **observational**. Nobody was assigned to use a sauna; men who already used
> one four times a week were compared with men who did not. The authors' own conclusion asks for
> further studies "to establish the potential mechanism". Sauna use is **associated** with lower
> cardiovascular mortality in this cohort. It has not been shown to cause it.
>
> **What that means if you are buying a sauna for your heart:** the honest version is that the
> strongest result in the literature comes from men who used one most days of the week, for
> decades, in a country where that is ordinary. The studies are collected at
> [healthresearchdatabase.com](https://healthresearchdatabase.com/topics/sauna-heat-therapy/) —
> 87 publications and 53 trials, indexed by search strategy rather than by how certain the
> evidence is. If a retailer quotes you a percentage without telling you the population it came
> from, that is the question to ask.

## The replacement for the defective passage

> Compared with men who used a sauna once a week, men using one 4–7 times a week had a hazard
> ratio for sudden cardiac death of **0.37 (95% CI 0.18–0.75)** after adjustment for
> cardiovascular risk factors. For 2–3 times a week the hazard ratio was **0.78 (95% CI
> 0.57–1.07)** — a confidence interval crossing 1.0, which means the result is compatible with
> no difference. Population: 2,315 men aged 42–60 in Eastern Finland, recruited 1984–89, median
> follow-up 20.7 years. Design: prospective observational cohort — association, not cause.
> Source: *JAMA Internal Medicine*, 2015.

## Internal links — part of the draft, not a follow-up

One inbound link today, from a page we repaired in Round 3. Five candidates, each with a
sentence already on the page that a link belongs in. **Each page gets read in full before the
edit** — a screen selects the unit of work, a full read defines it.

| source page | impressions | pos | the sentence the link attaches to |
|---|---|---|---|
| `what-is-a-german-sauna` | 23,587 | 6.24 | links already — update the anchor to the new title |
| `costco-sauna-guide-worth-it` | 7,379 | 8.38 | "The clinical literature on sauna safety centers on heat, hydration, and cardiovascular effects—not EMF." |
| `nurecover-tropic-home-sauna-review` | 2,570 | 9.69 | 23 cardiovascular mentions; link from its benefits section |
| `heavenly-heat-sauna-review` | 2,049 | 9.46 | "Health benefits—including possible cardiovascular, blood pressure, sleep, and relaxation effects—are associated with sauna bathing" |
| `santiago-2-person-ultra-low-emf-sauna-review` | 1,601 | 9.09 | "…in large observa[tional studies]" — already hedged correctly, so the link adds the evidence |

Anchor text states the claim the destination actually supports — *"what one Finnish cohort
found"*, never *"saunas improve heart health"*. The stale-anchor rule: a rename is a mechanism
change we perform.

## What this draft does NOT do

- No new URL, no second page competing with 4,450 existing words.
- No change to the sections on mechanism, session structure or safety, beyond the claim fixes.
- The remaining 14 unhedged effect sentences are listed in the screen output and need the same
  read; this draft fixes the one that states a statistic.
- The Google Doc link stays. It is in the queue, not in this edit.
