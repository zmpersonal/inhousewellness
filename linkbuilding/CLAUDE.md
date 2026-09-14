# InHouse Wellness — Link Building Project

Money site: **inhousewellness.com** (Shopify, home wellness / saunas / cold plunge)

## Baseline as of September 2026

| Metric | Value |
|---|---|
| Domain Authority (Ubersuggest) | 16 |
| Total backlinks | 198 |
| Referring domains (reported) | 68 |
| Referring domains (genuinely earned) | **~20** |
| Top-3 organic positions | 0 |

The gap between 68 and ~20 is the point. Reported referring domains break down as roughly 11 owned or controlled, 6 affiliate, 9 scraper copies of a single Healthline article, 13 junk directories, 4 scraped local aggregators. **All reporting in this project uses the earned number.** Never report the raw figure.

## The four links that matter

| Domain | DR | Target | Anchor |
|---|---|---|---|
| healthline.com | 91 | `/` | inhouse wellness |
| eatthis.com | 83 | `/` | in house wellness |
| womansworld.com | 66 | `/pages/featured-experts-consultants` | timur alptunaer md |
| singlecare.com | 63 | `/pages/featured-experts-consultants` | timur alptunaer md |

All four came from one tactic: a credentialed physician being quoted by health journalists. Nothing else in the profile comes close. Expert sourcing is priority one.

---

## Hard rules

**1. Never propose, contact, or count an owned or affiliate domain.**
Load `data/owned.json` and `data/affiliates.json` at the start of every pipeline. Any candidate matching either list is dropped silently at the discovery stage.

**2. The network is closed.**
Ten owned sites exist. Eight already link to the money site. `arcticsoak.com` and `commercialinfraredsauna.com` are quarantined — do not propose adding them, do not treat their absence as a gap, do not suggest a "natural" reason to link them. If asked to add a network link, say no and explain why. Ten sauna-topic sites pointing at one sauna store is already the maximum defensible density.

**3. Never send.**
Every pipeline drafts. A human sends. This applies to journalist pitches especially: AI-generated or off-topic pitches get ignored or banned, and a ban burns the platform permanently for the expert whose name is attached.

**4. Velocity cap: 8 new earned referring domains per week.**
Hard block, not a warning. In August 2026, four network links landed inside a fortnight — 9th, 12th, 18th, 22nd — two of them using an identical anchor construction with the same trailing arrow glyph. That footprint is the thing this cap exists to prevent repeating.

**5. Anchor distribution, enforced at draft time.**
Brand and naked URL should dominate. Exact-match commercial anchors stay under 10% of new links. Reject any draft whose anchor duplicates the construction of a link placed in the prior 60 days.

**6. Earned links point at content, not collections.**
Collection pages get authority through internal links. External placements go to blog posts, guides, and tools. The existing `/collections/saunas` links from owned properties are the anti-pattern.

**7. Prohibited outright.**
Blog comments, forum signatures, Web 2.0 properties, paid link marketplaces, PBNs, fabricated local addresses for cities not served.

---

## Pipelines

| Stage | Purpose | Status |
|---|---|---|
| `00_audit` | Classify every referring domain: earned / owned / affiliate / syndication / spam. Build disavow candidates. | to build |
| `01_source` | **Priority.** Journalist request monitoring, filtering, scoring, drafting. | to build |
| `02_dealer` | Manufacturer dealer-page applications. Six entities. | to build |
| `03_discover` | Competitor gap, resource pages, roundups, unlinked mentions. | to build |
| `04_qualify` | Score and reject. | to build |
| `05_enrich` | Contact resolution. | to build |
| `06_draft` | Outreach generation. | to build |
| `07_verify` | Weekly liveness, anchor, and rel-attribute check. Velocity guard. | to build |

## 01_source — the free stack

HARO was shut down by Cision in December 2024 and revived by Featured.com in 2025. Current free layer:

- **Source of Sources** — closest free replica of classic HARO, built by its original founder. Volume driver.
- **HARO (revived)** — free newsletter under Featured.com.
- **Qwoted** — free tier, limited pitches per month, with a delay on new requests. Highest request quality.
- **#journorequest** on X and Bluesky — fastest feed, free.
- **Featured** free tier — audit results first; many placements land on Featured's own content network rather than tier-one outlets.

Skip Help a B2B Writer — wrong vertical.

**Speed is the constraint.** Free tiers delay new requests, and first-hour responses win. Run the free stack for 60 days, log hit rate by platform, then decide on Qwoted Pro (~$149/mo) with data rather than by assumption.

**Topic filter:** sauna, heat therapy, cold exposure, cold plunge, recovery, sleep, cardiovascular, metabolic, hydration, longevity. Drop everything outside the expert's competence — most digest volume is noise for this brand.

**Draft format:** ready-to-publish quote first, credentials second, offer of further comment last. Pull positions from the claim bank, never invent a medical position.

---

## Dealer-page targets

Six corporate entities, not eight brands — **Golden Designs is the parent of both Dynamic Saunas and Maxxus Saunas.**

| Entity | Covers | Notes |
|---|---|---|
| Golden Designs | Golden Designs, Dynamic, Maxxus | One application, three brands |
| Harvia | Harvia | Nasdaq Helsinki listed, also owns Almost Heaven and ThermaSol. Formal, gated, slow. Separate motion. |
| Finnmark Designs | Finnmark | |
| Scandia | Scandia | |
| Leisurecraft | Leisurecraft | |
| Ripavi | Ripavi | Verify dealer program exists before building the application |

Zero manufacturer links currently exist. Realistic ceiling 5–7 links.

---

## Open items

- `xwifkv-j0.myshopify.com` — classify (see `data/owned.json`)
- Dr. Alptunaer's review cadence — daily or weekly? Determines whether `01_source` routes to him or to the outreach lead
- `data/identity.json` — canonical NAP not yet captured. Needed before any citation work.
- Several links show paid-insertion anchor patterns (momdaughts.com, lumiluxlimited.com, morpheus8london.com, functionalacademy.org, journalismband.com). Confirm provenance before the audit assigns them to "earned".
