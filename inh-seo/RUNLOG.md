## Round 18e — Option A, the Gracia and Bellagio rows, the orphaned LifeTrend sentence. LIVE.

| change | before | after |
|---|---|---|
| Sources: 3 Dynamic citations | linked to Costco | **unwrapped, names kept, no wording change** |
| Table 7 Bellagio · InHouse price | ~$2,499 | **$2,699** |
| Table 7 Bellagio · relationship | Exact same model | **Same model line** |
| Table 7 Gracia · link | DYN-6119-03 FS ($2,899) | **DYN-6119-01 ($1,999)** |
| Table 7 Gracia · InHouse price | ~$1,899 | **$1,999** |
| Table 7 Gracia · relationship | Exact same model | **Same model line** |
| note under Table 7 | — | *"Same model line" is matched on the model name. Confirm specifications against the current Costco listing before comparing.* |
| LifeTrend | …confirm on the live page before purchase. | …confirm with Costco before purchase. |

**There is no San Marino Elite row in the comparison table.** Its two links resolve to
DYN-6206-01 Elite, which name-matches Costco's listing; no InHouse price is quoted for it anywhere.

**Proof:** link multiset as declared (−4 +1, the Gracia repoint); visible text outside declared changes
byte-identical in both articles; **the proof was made to fail on purpose** with an injected word and an
injected link, and refused both. **Restore sequence** on costco-sauna-guide-worth-it — an article
carrying an earlier round's edit — md5 round-trip, no-op re-run, faked edit refused, then full apply.
Backup: `data/backups/2026-09-18T03-09-09-379Z/r18e-edit.json`.

**Rendered:** Table 7 correct; Gracia row → `/products/1-2-person-infrared-sauna-hemlock-chromotherapy`
(DYN-6119-01, $1,999, available); one Costco link left (return policy); "Exact same model" absent.

**Site-wide:** external 3,630 → **3,627** (Δ3) · internal **1,210** (Gracia swap is one-for-one) ·
institute **2,047** · costco 4 → **1** · 13 withheld unchanged.

**Costco guide audit (report):** 22 InHouse product links; **all 4 Gracia links point at the wrong
product** (1 fixed, 3 remain); ~10 prose representations of "identical / same hardware".

**Site-wide price staleness (report):** 119 published articles · 15 quote a price beside a product link ·
122 link/price pairs · **109 state the live price** · 13 read by hand → **3 genuinely stale**:
Maxxus Seattle "under $2,000" (live $2,299), Lugano DYN-6336-02 "$3,499" (live $2,699), Monaco
"around $5,999 MSRP" (live $6,499). **Not widespread.** The bigger finding: **33 links to 5 DRAFT or
ARCHIVED products, all returning 404.**

---

## Round 18d — 13 competitor links removed, 4 orphaned sentences rewritten, item 1 HELD. LIVE.

**Executed:** Costco ×10 (#1–4, #8, #10–14) · rcwilley.com · homedepot.com · realrelaxmall.com
(reclassified T1 per the quote-gated rule) · 4 minimal rewrites. **Kept:** Costco #9 (return policy),
bachmanns.com ×2. **HELD:** Costco #5–7 — they are source citations, not purchase links (see LEARNINGS).

| article | external before → after | rewrites |
|---|---|---|
| costco-sauna-guide-worth-it | 18 → 13 | 3 |
| arcadia-barrel-sauna-guide | 10 → 8 | — |
| homedics-premium-steam-sauna-review | 13 → 12 | — |
| lifetrend-cold-plunge-review | 13 → 11 | 1 |
| benefits-of-massage-chairs-for-seniors | 21 → 19 | — |
| top-fire-pits-outdoor-meditation | 18 → 17 | — |

**Site-wide:** external 3,643 → **3,630** (Δ13, as declared) · internal **1,210** unchanged (no link
added) · institute **2,047** unchanged · costco 14 → **4** · 13 withheld unchanged · citation spot-check
unchanged.

**Restore proof, per CLAUDE.md, on `lifetrend-cold-plunge-review`** (both rewrite and unwrap paths):
apply → restore md5 `b73b2dd5…` == before → restore again no-op → faked edit REFUSED (exit 1) → full apply.
Backup: `data/backups/2026-09-18T02-42-34-077Z/r18d-edit.json`.

**Rendered:** all six pages as intended; the four new sentences live; the three originals absent.

**Substitution candidates (item 8):** 73 unwrapped competitor destinations in ordinary articles
matched on vendor + model against our ACTIVE catalogue → **3**, all of them the held Costco citations.
One brand-level near-miss: saunamarketplace.com's SaunaLife brand page (no model named).

**Found while checking item 1 — a live defect:** the Costco guide's comparison table calls the Gracia
at InHouse "Exact same model" at ~$1,899 and links DYN-6119-03 FS at $2,899. The matching unit is
DYN-6119-01 at $1,999, which we stock and the article does not link.

---

## Round 18c — 3dmassagechair unwrapped; general retailers classified by linked URL. 1 LIVE EDIT.

**Executed:** decision 1 only — the single ordinary-article `3dmassagechair.com` link in
`massage-chairs-office-workers`. **Costco and the general-retailer class are REPORTED, not cut**:
the brief asked to see destinations before cutting, and the DONE list confirms one removal.

| | R18 start | R18c start | now |
|---|---|---|---|
| external | 3,730 | 3,644 | **3,643** (Δ1) |
| internal | 1,210 | 1,210 | **1,210** |
| institute external (control) | 2,047 | 2,047 | **2,047** |
| 3dmassagechair.com | 9 | 9 | **8** (all institute) |
| costco.com | 14 | 14 | **14** (untouched) |
| 13 withheld | — | — | **all unchanged** |

**Restore proof, full sequence, on the real target:** apply → restore (md5 `3830ddba…` ==
before-state) → restore again (no-op) → faked third-party edit **REFUSED** (exit 1) → re-apply.
**And the stacked-round guard:** the 18b restore on this article now REFUSES, so the two rounds
can only be undone in reverse order.
Backup: `data/backups/2026-09-18T02-34-23-655Z/r18c-unwrap-3dmassagechaircom.json`.

**Rendered:** 0 `3dmassagechair.com` hrefs on the live page; the URL survives as plain text.

**General retailers — 4 domains, 18 links, all ordinary, 0 institute:**
costco.com 14 (13 REMOVE / 1 KEEP) · homedepot.com 1 (CALL — fire pit) · rcwilley.com 1
(REMOVE — massage recliners) · bachmanns.com 2 (KEEP — maintenance guide).

**Counts in the brief:** `costco-sauna-guide-worth-it` holds **9** Costco links, not 4.

**Friction:** the classifier's own self-test silently never ran (spaces in the repo path), and
its normaliser erased the `.product.` marker. Both caught by fixtures, neither by reading.

---

## Round 18b — T1 competitor links unwrapped in 23 ordinary articles. LIVE.

**This is a live content edit, not a theme change.** Article bodies have no preview theme; the
brief's "live content edit across 24 articles" acknowledged that, and the proven restore path is
the safety net. MAIN theme untouched.

**Institute blog excluded entirely** (client ruling: the section is being removed) — **6 articles,
not 5**: `plunge-immune-function` carries 1 T1 link beyond the five Sources pages. So the edit set
is **23 articles / 84 links**, not 24 / 85, **plus 2** `lifeprofitness.com` links hand-classified T1
this round = **86 anchors**.

| article | external before | after | T1 unwrapped |
|---|---|---|---|
| `are-infrared-saunas-safe` | 49 | **33** | 16 |
| `dry-sauna-for-home` | 39 | **29** | 10 |
| `best-inflatable-cold-plunge-tubs` | 12 | **4** | 8 |
| `cold-plunge-maintenance-tips` | 15 | **8** | 7 |
| `home-sauna-steam-room-lifetime-operating-costs` | 34 | **28** | 6 |
| `cold-plunge-buyers-checklist` | 26 | **20** | 6 |
| `hidden-failure-points-diy-sauna-steam-projects` | 22 | **18** | 4 |
| `red-light-therapy-sauna-guide` | 8 | **5** | 3 |
| `best-infrared-sauna-muscle-recovery` | 25 | **22** | 3 |
| `sisu-sauna-review` | 10 | **7** | 3 |
| `massage-chairs-office-workers` | 19 | **16** | 3 |
| `benefits-of-massage-chairs-for-seniors` | 23 | **21** | 2 |
| `sauna-detox-science-explained` | 16 | **14** | 2 |
| `polar-monkeys-cold-plunge-review` | 20 | **18** | 2 |
| `downdraft-sauna-ventilation-design-patterns` | 24 | **22** | 2 |
| `maxxus-saunas-review-buyers-guide` | 24 | **22** | 2 |
| `costco-sauna-guide-worth-it` | 19 | **18** | 1 |
| `top-fire-pits-outdoor-meditation` | 19 | **18** | 1 |
| `thermal-stress-hormetic-window-human-studies` | 24 | **23** | 1 |
| `how-float-tanks-improve-sleep-quality` | 18 | **17** | 1 |
| `what-is-a-german-sauna` | 19 | **18** | 1 |
| `lifetrend-cold-plunge-review` | 10 | **9** | 1 |
| `golden-designs-saunas-review` | 17 | **16** | 1 |

**Site-wide:** external 3,730 → **3,644** (Δ86, exactly as planned) · internal 1,210 → **1,210** ·
institute 2,047 → **2,047** (control held) · 13 withheld domains **all unchanged**.

**Verified from the RENDERED storefront article**, not the API: 23/23 zero T1, withheld counts
equal, none redirected. Visible text byte-identical on all 23 — no prose touched.

**Restore — proven before the full apply, on a real article:** applied to
`lifetrend-cold-plunge-review`, restored, read-back md5 `dd130bc4…` **== before-state**, a second
restore was a no-op, and a faked out-of-band edit made the restore **refuse** (exit 1). Then the
full apply ran. Backup: `data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json`.

```bash
node scripts/apply/r18-restore.mjs data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json            # dry run
node scripts/apply/r18-restore.mjs data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json --apply    # all 23
node scripts/apply/r18-restore.mjs data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json --only <handle> --apply
```

**Out of scope, flagged, untouched:** `costco.com` 14 links in 4 ordinary articles (probe
false-negative — see LEARNINGS); `3dmassagechair.com` 1 link (Real Relax's content blog, no
cart — a relationship call); 50 bot-blocked domains stay REVIEW.

**Friction:** three of the brief's counts (24, 85, "six withheld" naming seven) disagreed with the
data. None changed the work; each would have, had I edited to the stated number.

---

## Round 18 — outbound competitor classification. NOTHING EDITED. Gated on your approval.

**Read as a show-me gate: the brief says "EXECUTE (after the T1 list is approved)". No article
was touched, no theme created.**

### PRE-STATE SNAPSHOT — 2026-09-18, live Admin API (data/r18-prestate.json)

| | |
|---|---|
| live articles | **120** |
| total external links | **3,730** |
| distinct external domains | **398** |
| articles carrying ≥1 external link | **102** |
| total internal links | **1,210** |

3,730 vs Round 17's 3,664 = exactly the **66 bare URLs inside JSON-LD**, which an `<a href>`
probe cannot see.

| context | links |
|---|---|
| inline prose | 3,368 |
| **TABLE CELL** | **296** |
| JSON-LD | 66 |
| button / CTA | **0** |
| image wrapper | **0** |

### CLASSIFICATION

| tier | domains | links |
|---|---|---|
| **T1 REMOVE** | **54** | **356** |
| T2 keep (adjacent) | 27 | 111 |
| T3 keep (non-commercial) | 204 | 1,210 |
| MANUFACTURER — withheld | 6 | 37 |
| REVIEW — not classified | 62 | 211 |

**102 links were pulled OUT of the probe's T1 before it was shown.** The probe put
`goldendesigninc.com` (26 links) in T1; it is the MANUFACTURER that warrants the Dynamic and
Maxxus units we sell, and CLAUDE.md already records that exact domain being misclassified as a
competitor once before. Also withheld: `globalwellnessinstitute.org` (40, industry body),
`ndnr.com` (10, journal), `medicalsaunas.com`, `dream-pod.com`, `almostheaven.com`, `homedics.com`.

### Concentration

**Five `institute`-blog Sources pages carry 271 of the 356 T1 links (76%).**
`dynamic-santiago-ultra-low-emf-sauna-sources` alone carries 140, of which 28 are table cells.

### Two probe failures caught by their own guards

1. **Known-positive block.** `hightechhealth.com` — which you named as T1 — scored
   `cart=5, cats=[sauna,infrared], price=0` and my rule required a price, so it fell to T3.
   It is a **quote-gated seller**, the Sunlighten shape CLAUDE.md already documents. My
   fixtures did not include that class.
2. **Vendor cross-check near-miss.** Matching T1 domains against our own 41 vendor strings
   caught `dream-pod.com`, `dynamicsaunasdirect.com` and `medicalsaunas.com` and **missed
   `goldendesigninc.com`** — the domain drops the `s` in "Designs", so the substring test
   failed on the single most important row.

---

## Round 17 — Skimlinks verification tag. NOT PUBLISHED.

**Theme `146351784003` — "Round 17 — Skimlinks verification tag (TEMPORARY)", UNPUBLISHED.**
Preview: https://inhousewellness.com/?preview_theme_id=146351784003
Theme slots: **13 of 20 used, 7 free** at start; 14 of 20 used, 6 free after.

| item | outcome |
|---|---|
| tag before `</body>` in `layout/theme.liquid` | ✅ 1 occurrence, markers both ends |
| MD5 read-back | ✅ `7bf6856331e4f44d1a2021e7cf3b7846` byte-identical |
| raw served HTML (curl, no JS) | ✅ present on home, article, product, collection, page |
| differential vs MAIN | ✅ preview 1, MAIN 0 |
| `avadaLightJsExclude` | ✅ not added; string absent from the file entirely |
| MAIN contaminated? | ✅ no — md5 unchanged at `6022499a30fa37837cd114a35d61151a` |
| outbound-link audit | report only, nothing changed |

**🔴 THE PROMPT'S MAIN ID WAS STALE, AND IT WAS NOT A HARMLESS ERROR.** The brief said MAIN is
`146290704451`. **MAIN is `146318491715`** — the Round 15 theme, which the client published after
Round 15 closed. `146290704451` is Round 14 and is now UNPUBLISHED. Duplicating the id as given
would have branched from a theme that predates Round 15, and **publishing that branch would have
silently reverted the server-rendered `aggregateRating` and the gtin quoting fix.** Caught by
querying theme roles instead of trusting the id. `theme-branch.mjs` resolves MAIN by role, so the
tooling was already immune; the reasoning was not.

**And the client's article count was right where my dump was wrong.** The brief said 120 articles;
`data/content.json` holds 118. The live store has **120** — `are-saunas-good-for-you` and
`how-often-should-you-use-sauna` postdate the dump. The audit was re-pointed at the live API. The
usual direction of this rule is reversed: here the artefact was stale and the instruction was current.

**Friction:** `themeDuplicate` took ~4 minutes to copy 575 files and reported 36 at first poll.
Curling the preview before it completed would have tested a half-built theme.

---

## Round 16 — two comparison drafts. NOTHING PUBLISHED.

`content/drafts/infrared-vs-traditional-sauna.html` (37,341 chars)
`content/drafts/infrared-vs-steam-sauna.html` (36,385 chars)

Draft only. No article created, no Admin API write, no theme touched. Anthropic spend $0.

| phase | outcome |
|---|---|
| Cannibalisation audit | 1 real overlap: `dry-sauna-for-home` holds its own "Infrared vs Traditional" section. Trim is a **publishing precondition**, not done this round |
| Data inventory | accepted; then **re-derived and nine figures moved** — see LEARNINGS |
| Drafts | written, swept, committed `3f19ce3` |
| GSC for `dry-sauna-for-home` | **BLOCKED — unobtainable from here.** Open on the client's side |

**Verification, all re-run after the final edit:**
`r16-verify-drafts.mjs` (8 constructed fixtures, structure, links, FAQ 1:1, anchors) ·
`r16-claims-vs-data.mjs` (17 figures re-derived; all match) ·
the repo's own `health-claim-screen.mjs` imported and run over both drafts: **0 assertions,
0 property claims.** 31 internal links resolved against real data; none retyped.

**Friction:** the correction script refused four times, every refusal caused by a `from`
string typed from memory rather than extracted. Extracting first would have cost one command.

---


## Round 15 — server-rendered aggregateRating, H1, telephone, nav-bar. NOT PUBLISHED.

**Theme `146318491715` — "Round 15 — server-rendered rating, H1, telephone, nav-bar", UNPUBLISHED.**
Preview: https://inhousewellness.com/?preview_theme_id=146318491715
Free slots at start: **8 of 20** (the client had deleted superseded round themes).

**7 files, all MD5-verified byte-identical in the theme.** 14/14 post-build checks, 19/19 rendered
preview checks, 6/6 template types structurally valid.

| item | outcome |
|---|---|
| `aggregateRating` server-side | **3 sections**, not 1 — see below |
| Organization `telephone` | on the node and the ContactPoint, E.164 |
| Organization `aggregateRating` | **4.82 / 1431, read live from shop metafields** |
| homepage H1 | logo → `div`, hero → `h1`, both guarded to `index` |
| nav-bar render error | gone; the redundant direct call removed |
| Font Awesome | link removed, two icons inlined as SVG |
| jQuery | **deliberately left** — see HANDOFF.md |

### Two enumerations changed the scope, both toward more work

**THREE sections emit the Product node** — `main-product`, `bundle-product`, `main-product-layout-2`.
**84 ACTIVE products sit on `product.Bundle.json`, 32 of them with ratings.** Editing only
`main-product.liquid` would have shipped the rating to 396 products and silently missed 84. That is
the Round 9 template-partition failure, and the validation now covers both Bundle branches — one
rated (`ct-georgian-cabin-sauna`, 4.6/5) and one not (`huum-hive-12`, guard holds).

**`image-with-text-overlay` renders on `index` AND on the featuredexperts template**, which has a
live page at `/pages/featured-experts-consultants`. An unguarded `h2`→`h1` would have put a second
H1 there. The promotion is guarded to `index`; verified the hero stayed an `h2` on that page.

### Four errors of mine, all caught before the client saw them

1. **`git checkout -- theme/` reverts NOTHING** — `theme/` is gitignored, the command exits
   non-zero, and I read a failed revert as a successful one. Re-running the build then inserted a
   **second `aggregateRating` block** into `layout/theme.liquid`, because that edit re-emits its own
   anchor. `scripts/apply/theme-pull.mjs` now restores from MAIN with MD5 proof, and the build
   carries an **idempotency guard proved to refuse a second run**.
2. **`{%- comment -%}` inside a `{%- liquid -%}` block is a syntax error.** Shopify refused the file
   rather than accepting it — the push failing was the correct outcome.
3. **My MD5 verifier declared `$n` and passed `names`.** The filter never bound, the query returned
   the first 25 files alphabetically, and all 7 targets reported "(absent)" against a theme that
   held them correctly. **A false negative — the safe direction, but a broken verifier.**
4. **I derived a page URL from a template name** and got a 404 with 0 H1s, which read as a
   regression. The handle is `featured-experts-consultants`. Identifiers come from the data.

### And the duplicate was still copying when I first pushed

`themeDuplicate` is asynchronous. At first push the branch held **175 files against MAIN's 575** and
was still growing. Polled to 575/575, then re-pushed and verified. **A branch short of the live
theme is a broken preview, not a draft** — and a file pushed into a still-copying duplicate can be
overwritten by the copy.

### Not done, and not claimed

- **Google's Rich Results Test was NOT run.** It has no public API. What was run is structural
  validation: JSON parses, one Product node per page, `AggregateRating` well-formed and in range,
  on all six template types. **Google's verdict needs a human paste.**
- **Search Console was not read.** The "33 valid Review URLs, zero invalid" figure could not be
  re-derived from here, so it is carried as the client's number, not confirmed.
- **Hyperspeed caches aggressively.** After the client publishes, a cache rebuild is likely needed
  before the changes are visible on the live domain.

## Round 15b — gtin quoting. Theme 146318491715, still UNPUBLISHED.

Client's Rich Results check found a pre-existing bug that nullified Round 15 on 31 products.
9 edits across the 3 Product emitters, 3 files MD5-verified byte-identical.

**Blast radius, measured 478/478 from the public storefront:** 270 products emit a gtin; **30 have
a leading-zero barcode and 1 is non-numeric**; **31 published products had their whole Product node
discarded**; **24 of those were rated and ACTIVE — 13.1% of the ACTIVE rated set.**

**Verified on fixtures chosen to break the property**, not clean samples:

| fixture | why it was chosen | result |
|---|---|---|
| `dynamic-venice-elite` | leading-zero barcode, the reported case | parses · `gtin12` `"019962854569"` **as a string** · aggregateRating **4.93/15** · offers intact at 2699 |
| `huum-hive` | **U+2011** non-breaking hyphens | parses · `gtin13` `"537‑AZ‑128267"` |
| `maxxus-3-person-sauna-hemlock-ultralow` | **the only Bundle-template product that is both affected and rated** | parses · aggregateRating **4.5/20** |
| `laguna-q-gpv3100-outdoor-island` | no reviews | aggregateRating **absent** — guard holds |

Round 15's work confirmed intact: **aggregateRating exactly once in all three emitters, raw gtin
zero, quoted three** — read back from the theme, not from local files. All 19 rendered preview
checks and all 6 template-type validations still pass.

**Themes: 13.** The 12 that existed before this round plus `146318491715`. MAIN is unchanged at
`146290704451`. **Nothing was created that I did not create.** (The t/NN in asset paths is
Shopify's creation counter, not a theme count — client's correction, noted.)
