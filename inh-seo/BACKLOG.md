# BACKLOG

Deferred work, with the reasoning for deferring it. Nothing here is a Round 1–3 item.

Ordered by when it should be picked up, not by size.

---

## B1 — Markup residue on 368 products and 26 pages

**Status:** deferred, deliberately. Do not re-raise before 15 November.

**What.** The same ChatGPT-editor residue fixed on collections in Round 1.4 —
`data-start`, `data-end`, `data-is-only-node`, and Tailwind classes like
`class="relative -mx-px"` — is present on:

- **368 products** (232+ ACTIVE), spanning 20+ vendors: Cal Flame,
  Dynamic Cold Therapy, Dreampod, Medical Breakthrough, Dundalk Leisurecraft, Harvia,
  Maxxus, Golden Designs Inc, Ripavi, Scandia, Medical Saunas, Broilmaster, Primo,
  Kahuna Chair, Helios and others. It is a pasting habit, not a single bad import,
  so it will keep recurring until the habit changes.
- **26 pages**, including commercial and trust pages: `sauna-payment-plans`,
  `spa-financing`, `refund-and-return-policy`, `shipping-policy`,
  `terms-and-conditions`, `editorial-guidelines`, `reviews`, `media`.

Detail in `data/broken-copy.json`; run `npm run audit:broken` to refresh.

**Why deferred.** Every one of these is P1: invisible `data-*` and Tailwind residue,
no visible garbage on the page. Both P0s — visible broken text — are collections and
were fixed in Round 1.3. This is technical debt, not a seasonal revenue item, and the
collection copy sweep is worth more before the 15 November deadline.

**When B1 runs, do the 26 pages FIRST.** They are not equivalent to the products. The list
includes `sauna-payment-plans`, `spa-financing`, `refund-and-return-policy`,
`shipping-policy`, `terms-and-conditions`, `editorial-guidelines`, `reviews` and `media` —
policy and financing pages that customers deliberately seek out and read closely before
committing to a $6,000–$15,000 purchase. A buyer checking the return terms is exactly the
buyer who will notice broken markup. The 368 products can follow.

Counts grew from 307 products / 10 pages once the `stray-meta-tag` pattern was added on
6 September 2026; the underlying records are the same plus stray `<meta>` carriers.

**What it needs when picked up.** Its own round. `scripts/apply/strip-markup.js`
currently reads `data/collections.json` and writes via `collectionUpdate`; it cannot
reach products or pages. Extend it — or fork it — to scope over `productUpdate` and
`pageUpdate`, following the same dry-run-default / backup / changelog / idempotent
pattern as every other apply script.

**Read this before running it at scale.** `cleanHTML` unwraps any tag outside its
allow-list. `img`, `figure` and `figcaption` were added to the allow-list on
5 September 2026 precisely because an unwrapped `<img>` is a silently deleted image,
and product descriptions contain images where collection descriptions largely do not.
The `>\s+<` whitespace collapse was removed at the same time — it welded adjacent
inline tags together (`<strong>Cedar</strong> <em>barrel</em>` → `Cedarbarrel`).
Both fixes are in `scripts/lib/util.js` and verified against four cases, all
idempotent. Re-verify before a 307-record run, and read a sample of the diff by hand.

---

## B2 — 320 ACTIVE products with no featured-image alt text

**Status:** deferred. Not in any round.

443 of 673 products have no alt text on the featured image; **320 of those are
ACTIVE**. Alt text is an accessibility requirement before it is an SEO one, and this
is an audience of 40–60 year olds.

Not a copy-generation job that can be batched blindly — alt text describes what is in
the specific image, and `CLAUDE.md` hard rule 6 forbids inventing product facts. The
honest version reads the image or derives from title + vendor + product type in
`data/products.json`, and a human samples the output before it applies.

---

## B3 — Over-length collection SEO titles and meta descriptions

**Status:** deferred, and **will be silently skipped in Round 3.2 unless someone acts.**

- **17 existing SEO titles over 60 characters.** Worst: `medical-sauna` (89),
  `cold-plunge` (88), `frozen` (82), `outdoor-fireplaces` (81), `hot-tubs` (80),
  `red-light-therapy-panel-skin-pain-recovery` (80).
- **10 existing meta descriptions over 155 characters.** Worst: `golden-designs`
  (222), `dynamic-saunas` (179), `cold-plunge` (174), `ripavi` (171).

Two are broken rather than merely long:
- `golden-designs` — "…for Home WellnessGolden Designs", a duplicated brand name from
  a concatenation bug.
- `cal-flame` — trailing zero-width space (U+200B).

**Why this needs a human.** `apply:seo` fills `null` fields only, by design, per
`CLAUDE.md` ("Only fill `null` fields… Do not overwrite an existing meta description
unless the task says so explicitly"). These fields are populated, so the script will
correctly skip all 27. Fixing them requires `--overwrite` and explicit approval.

**Action:** flag all 27 in the Round 3 report so a human decides on `--overwrite`
with the list in front of them. Do not overwrite by default.

> **Not the same as the health-claim metas.** 10 of the 59 admin-set meta descriptions
> contain health-claim language ("detox", "reduce inflammation", "pain relief",
> "therapeutic"), and the Round 2 `theme.liquid` fix makes them render for the first time.
> That is a compliance gate on publishing the branch, not a formatting backlog item. See the
> gate section in `reports/round-2-shipping-claims.md`. Overlap between the two sets is
> incidental.

---

## B4 — Bylines remediation

**Status:** deferred to the E-E-A-T / author-schema work. Open decision in `CLAUDE.md`.

The bylines question is not hypothetical — it is already live and published:

- **Six personas carry all 112 articles:** Taylor Reed, Casey Bennet, Riley Thompson,
  Julian Farley, "InHouse Wellness Research Team", "Editorial Review by InHouse
  Wellness".
- **Dr. Timur Alptunaer appears on zero articles**, despite being quoted in six
  national outlets per `data/press-links.json`.

That is the real credibility asset sitting unused while invented names carry
health-adjacent content to an audience frequently managing blood pressure and cardiac
risk. It also cuts against the brand positioning in `CLAUDE.md` — "the buyer's agent,
not the brand's advocate", "credibility over comfort".

**Blocks:** author schema, E-E-A-T markup, and the Round 2.1 `/pages/press` build,
which will cite outlets that quoted a named doctor the site does not name.

**Needs a decision, not a script:** can Dr. Alptunaer be named as author or reviewer
on health content, and do the six personas stay, get consolidated, or get replaced?
Ask. Do not guess.

---

## B5 — Collection membership quality

**Status:** its own round. Filed 6 September 2026 regardless of survey findings, on the
client's ruling: a buyer filtering to a collection that holds 82% of the range is a
conversion problem, and it sits upstream of the copy, the SEO titles and the internal link
graph. Fixing copy on top of wrong membership is doing the work twice.

**The structural fact.** 87 of 90 collections are **manual** (`smart: false`) — membership
set by hand, with no rule enforcing it. The only three smart collections are
`avada-best-sellers`, `newest-products` and `best-selling-products`, and all three are on
the Round 1.5 DEINDEX/DELETE list. **After Round 1.5, every surviving collection in the
store is hand-maintained.** Nothing prevents the next drift.

**Known instances:**
- `far-infrared` — 20 ACTIVE far-infrared units sit outside it. See
  `reports/far-infrared-membership.md`. Not contaminated, incomplete: 100% of current
  members are correctly filed.
- `hot-tubs` — 7 products, only 3 are type Hot Tub; 3 Cold Plunge, 1 Cold/Hot Plunge. Live,
  published, carries an SEO title and meta. **The only live in-scope instance found.**
- `outdoor-fireplaces` — **RESOLVED 7 September 2026 by reading the products, not the types.**
  All 6 are typed "Fire Pits" but **5 of 6 titles say "Outdoor Fireplace"**. They are
  fireplaces, mis-typed. The collection name was correct; `productType` was wrong. Fold into
  B6.
  **A separate genuine membership error surfaced in the same read:** "Cal Flame FRP906-2 BBQ
  Island – Full-Size Outdoor Kitchen" sits in `outdoor-fireplaces`. It is a BBQ island.
  `productType` could not have found it — it is typed "Fire Pits" like its neighbours.
  Scope-out means no copy is written here, but the membership error stands.
- `cold-plunge-favorites` — 10 products, only 3 Cold Plunge. Resolves itself via 1.5.

**Method note for whoever picks this up.** Scoring membership by whether products mention
the collection's name produces false alarms — `floatation-therapy-tanks` scores 0% because
products say "Float Pod", `massage-chairs` 13% because titles say "Chair" singular.
`productType` is the better signal, but it cannot distinguish a brand collection (`maxxus`,
type "Sauna") or an attribute collection (`chromotherapy`, same) from a miscategorised one.
Any audit needs a human pass. See B6 — the type vocabulary needs cleaning first or this
audit can't be automated at all.

---

## B6 — CLOSED 10 September 2026. **Both stated reasons were false. The work was right anyway.**

**Read this before the entry below, which is preserved as written.**

| stated reason | verdict |
|---|---|
| inconsistent `product_type` triggers Merchant Center disapprovals | **FALSE.** Zero. Killed by the Merchant Center precondition. |
| *"Indoor (85)"* beside *"Indoor(1)"* is the customer-visible symptom | **FALSE ATTRIBUTION.** "Indoor" was never a `productType` value. The facet is `p.m.custom.location_`. See **B6b**. |
| the field was corrupting analysis | **TRUE, and never the headline.** `/collections/delta` published *"five steam generators and two accessories"* — derived from the field, and all seven are generators. |

**Applied:** 53 values to 14, 372 writes, 18 honest blanks. Verified by re-deriving
the measurement, not by reading back the writes.

**The entry passed every review on its summary rather than its evidence.** The
generalisation is in `CLAUDE.md` under *"A summary repeated often enough becomes the
evidence"*. This is the second time the rationale here failed a check nobody had run,
which is why the standing-rationale audit at the foot of this file is not optional.

---
## B6 — `productType` vocabulary is inconsistent — **PROMOTED, revenue not hygiene**

**Status:** promoted 6 September 2026. **RATIONALE CORRECTED 10 September 2026 — the
work stands, the reason it was promoted does not.**

### The original rationale, and why it was wrong

It read: *"`product_type` feeds the Google Merchant Center product feed… Inconsistent
values degrade Shopping categorisation and can trigger product disapprovals — so this
is lost revenue, not tidiness."*

**Checked against Merchant Center, which is what the precondition below exists for:**

| | |
|---|---|
| feed products | 796 |
| eligible | 767 (96%) |
| disapproved | 29 — 28 `landing_page_error`, 2 `shipping_weight_too_high` |
| **category mismatches** | **zero** |
| **`product_type` issues of any kind** | **zero** |

**And `google_product_category` is separately populated and correct** — ThermaSol steam
packages carry *Hardware > Plumbing > … > Electric & Power Showers*. **That is the field
Google categorises on**, which is why inconsistent `product_type` is costing nothing in
the feed.

### The rationale that survives

- **The split facet.** `infrared-saunas` — 103 products, `infrared sauna` at 110,000/mo,
  the most valuable page in the store — shows **"Indoor (85)" and "Indoor(1)" as two
  selectable filter values.** In front of a customer deciding on a $6,000 purchase.
- **Analysis corruption.** 38 infrared saunas typed plain "Sauna", so any count by
  `productType` understates infrared by more than half. `productType` has been wrong on
  `hot-tubs` **three times**, and every count derived from it is suspect.

**Both real. Neither is lost revenue.** Say it that way to the client.

It also blocks any automated membership audit (B5) and any conversion of the 87 manual
collections to smart ones.

### Why the wrong rationale survived four days

**It was written from a plausible mechanism rather than from the data.** Inconsistent
categorisation *can* cause disapprovals — that is true in general and it was never
checked here. It was promoted on that reasoning, repeated in every summary since, and
**nobody opened Merchant Center until the precondition forced it.**

**The precondition worked, and it is the only reason this was caught.** A rationale
that is plausible, general, and unchecked will survive every review that does not
happen to test it — and none of them will, because it sounds like a fact.

**Do this first, before normalising anything:** check Merchant Center for existing
disapprovals and category mismatches, so the size of what is already broken is known rather
than assumed. Normalising the values without that baseline destroys the evidence of what the
inconsistency was costing.

**AMENDED 10 September 2026: 53 distinct values across all 673 products.** The 17 below
is `sauna-heaters` alone — a collection-scoped count that has been quoted as an
estate-wide one.

**And the shape is not what this entry describes.** Only **one** case collision exists
across the whole catalogue — `Sauna` and `SAUNA`, nine products. That is the entire
casing problem. The real issues are **118 products with no value at all** and **33
values holding fewer than three products each**, where someone typed a description
instead of choosing a category. Merging `Sauna` and `SAUNA` is mechanical; collapsing
`Wood-Burning` and `Grill Head` into a taxonomy is a judgement about what the
categories should be. See `reports/producttype-taxonomy.md`.

`sauna-heaters` holds **17 distinct `productType` values across 95 products**: "Sauna
Heater", "Sauna Stove", "Wood Sauna Stove", "Wood-Burning Sauna Stove", "Wood-Burning Sauna
Stove Package", "Wood-Burning Sauna Stove Kit", "Sauna Stove Kit", "Sauna Stove Kits",
"Sauna Stove Package", "Electric Sauna Heater", "Electric Sauna Heater Kit", "Electric Sauna
Heater Package", "Sauna Heater Package", "Wood-Burning Sauna Heater Package",
"Wood-Burning", "Sauna Heater (Homage Row)", "Sauna Accessories".

`sauna-life` carries both `Sauna` and `SAUNA` as separate values. `primo-grills` is 90%
empty type.

Beyond SEO this affects faceted navigation and the Google Shopping feed, where product type
is a matching signal.

### It corrupts analysis, not just facets

**38 infrared saunas inside `/collections/saunas` are typed plain "Sauna".** Any count of
"how many infrared saunas are in X" done by `productType` understates it by more than half.
That error reached a draft for the 40,500/mo page before it was caught.

**Standing rule while this is unfixed: `productType` may be reported, never used to conclude.**
Use collection membership or title text for any claim about what a product is. Every earlier
conclusion in this project that rested on `productType` was re-checked — one was wrong
(`outdoor-fireplaces`), one right, one already withdrawn. See `reports/round-1-summary.md`.

### It is already visible to customers — this is not a hygiene abstraction

Observed in the Round 2 theme preview, 7 September 2026, on the **`infrared-saunas`**
collection — 103 products, `infrared sauna` at 110,000/mo, the single most valuable page in
the store:

> The faceted navigation lists **"Indoor (85)"** and **"Indoor(1)"** as two separate,
> selectable filter values.

Two things are wrong at once, both caused by inconsistent metafield values:

1. **The filter is split.** A customer filtering for indoor saunas picks one of two options
   and silently loses whichever products are behind the other.
2. **The second reads as broken software** — no space before the parenthesis, a count of 1
   sitting beside a count of 85. On a page where someone is deciding whether to spend $6,000
   with an unfamiliar retailer, that is a credibility cost before it is a filtering one.

The same inconsistency that produces 17 `productType` values across 95 sauna heaters, and
`Sauna` beside `SAUNA` in `sauna-life`, is what splits this facet.

**Whoever picks up B6: start here.** It is the cheapest possible demonstration that the
problem is costing something now, and it gives the Merchant Center baseline check a concrete
before-and-after to measure against.

---

## B7 — Product titles omit the keyword they target

**Status:** deferred. Surfaced by the far-infrared membership diff.

Four ACTIVE far infrared saunas do not have "far infrared" in their title, though their body
copy and in one case their own URL handle do:

- `maxxus-chaumont-edition-far-infrared-sauna-corner-unit-4-person-low-emf-red-cedar`
  — titled "Maxxus Chaumont Near Zero EMF Infrared Sauna 4-Person"
- `dynamic-versailles-elite-2-person-infrared-sauna`
- `maxxus-seattle-2-person-sauna`
- `dynamic-infrared-sauna-venice-edition`

`far infrared sauna` runs 6,600/mo at $5.62 CPC. This is a product-title loss independent of
collection membership and is not fixed by moving anything. Likely wider than these four —
worth a sweep of all 482 ACTIVE products against their assigned keywords.

---

## B8 — Unreachable theme demo data

**Status:** deferred. Confirmed harmless 6 September 2026.

The live theme references 8 collections that do not exist in the store. Both call sites are
unreachable, so nothing renders broken today:

- `theme/templates/page.sale.json` → `blazers`, `tops`, `crop-top`, `handbags`, `sweaters`.
  **No page in the store uses the `sale` template suffix**, so this template renders nowhere.
- `theme/sections/overlay-group.json` → `best-seller`, in a `before-you-leave` section
  marked `"disabled": true`. The group is rendered from `theme/layout/theme.liquid:276`, but
  that section is not.

Clean up whenever the theme is next touched. Not urgent, not a live defect.

---

## B9 — Best Sellers collection (was TASKS.md 1.6)

**Status:** dropped for the 2026/27 season on the client's ruling of 7 September 2026.
Revisit after the season, when there is real volume to rank.

**Not dropped because of the API limitation.** Dropped because of what the visible data
shows. Inside the 60 days the Admin API will return without `read_all_orders`:

| | |
|---|---|
| Orders | 3 — 2 PAID, 1 VOIDED |
| Distinct products sold | 3 |
| Units | 22, of which **20 are a single line of cedar duckboard flooring** |
| Range | 2026-07-16 to 2026-08-12 |

Whatever the true annual figure turns out to be, a "Best Sellers" page built on volume of
this shape is a page about duckboard. Publishing it is worse than not having it.

**Do not request `read_all_orders` for this.** That is effort spent sizing a decision already
made. Request it when the collection is actually being built, if it ever is.

**When revisited:** the work is TASKS.md option (a) — a manual collection, membership synced
by a script from units sold over a rolling window, on the standard dry-run / backup /
changelog / idempotent pattern. Choose the window from real volume rather than defaulting to
90 days. The `read_orders` scope is already granted and verified working; only
`read_all_orders` (for history beyond 60 days) would need adding.

`newest-products` remains a separate open decision — becomes "Products", or is unpublished in
favour of the native `/collections/all`.

---

## B10 — `red-light-therapy-panel-skin-pain-recovery`: the health claim is in the URL

**Status:** deferred. Needs a 301 and is not a publish-day decision.

The collection handle itself is:

```
/collections/red-light-therapy-panel-skin-pain-recovery
```

**"skin-pain-recovery" is a health claim at the URL level.** Its meta description was rewritten
on 7 September 2026 to remove "boost skin health, relieve joint pain, and support faster
muscle recovery" — but a compliant meta on a URL that still says `pain-recovery` is half a
fix. The URL appears in the SERP, in the address bar, and in every link anyone builds to it.

**Do not rename the handle as part of the Round 2 branch.** Changing a Shopify collection
handle needs a 301 redirect from the old URL, and doing that alongside a theme publish
conflates two unrelated risks. It is also the highest-CPC page in the red-light cluster
(`red light therapy panel`, 14,800/mo, $5.19) — worth doing carefully, not quickly.

**When it is done:**
- New handle candidate: `red-light-therapy-panels` (plural, matches the keyword, no claim).
- A 301 from the old handle is mandatory. Shopify offers `redirectNewHandle` on
  `CollectionInput`, which creates the redirect automatically — verify it fired rather than
  assuming.
- Only 2 ACTIVE products sit in this collection. Check first whether it should exist at all,
  or fold into `red-light-therapy` (39 products).

**Worth a sweep:** this is the only handle found with claim language in it, but nobody has
audited all 90 handles for the same problem. That check has not been run.

---

## B11 — Product titles run long, and product SEO is a different project

**Status:** logged, not chased. Deliberately out of scope for Rounds 1–3.

Noticed while verifying that the Round 3a title change was correctly scoped to articles: the
product page tested rendered a **109-character** `<title>`. Product titles have never been
measured; that is one observation, not a survey.

**Why it is not being chased now.** 434 product URLs produce **8% of organic clicks** (44 of
548 in the 28 days to 5 September 2026), against 165 blog URLs producing **89%**. The
measured return on a product-title pass is roughly a tenth of the blog work, and it is a
different project with a different shape — 434 machine-generated titles carrying vendor and
model numbers, not 112 editorial ones.

**Before anyone starts it**, apply the standing test in `CLAUDE.md`: pull the positions
first. Product pages average far worse positions than the blog estate, and if they are not on
page one the problem is ranking and a title rewrite is close to wasted. That test is what
justified the Round 3b blog work and what would justify or kill this one.

**Also unmeasured:** product meta descriptions, and whether the theme's shop-name suffix
helps or hurts on a product title that already carries brand and model.

---

## B12 — Article facts drift from catalogue facts, and nothing checks

**Status:** open. **Its own class of problem**, found by accident, and almost certainly not
an isolated case.

### The instance

`/blogs/saunas/dynamic-saunas-review` states the Dynamic line runs **$2,499–$6,499**. Our
`dynamic-saunas` collection sells from **$1,999**.

A brand review page is telling readers the floor price is **$500 higher than we actually
charge**, on a page ranking at position 8.9 with 4,123 impressions in 28 days. It costs
conversions in the most direct way possible: a reader decides the range is above budget and
leaves, on a page we wrote.

**Found only because one number was verified before putting it in a meta description.** It
was not found by any audit, because no audit looks for it.

### Why it is a class, not a bug

112 articles carry prices, model numbers, capacities, wattages, temperature ceilings and EMF
tiers. The catalogue changes — prices move, products are added and archived, the far-infrared
membership fix alone moved 20 products in September 2026. **Nothing reconciles the two.** An
article written accurately in March is silently wrong by September and reads exactly as
confident as it did on the day it was published.

This is the article-level version of the coverage rule in `CLAUDE.md` §6a. That rule stops us
writing an unsupported number today; it does nothing about the ones already published.

### What to build

A script — `scripts/audit/check-article-facts.js` — that does at scale what was done by hand
for one number:

1. Extract every `$N`, `N-person`, `N°F`, `N kW` and named model from each article body.
2. Resolve the products each article discusses (vendor and model strings are in the titles).
3. Compare against `data/products.json`.
4. Report divergences with article, claim, article value, catalogue value.

**Report only.** It must never rewrite article copy — a divergence can mean the article is
stale *or* that it is deliberately describing a third party's pricing. `costco-sauna-guide`
quotes Costco's prices on purpose and dates them; that is correct and must not be flagged as
an error. The check needs to distinguish "our product, wrong price" from "someone else's
product, quoted and dated".

Products we do not sell need no check at all — Sisu, Heavenly Heat and HoMedics reviews were
verified to have no catalogue counterpart, so nothing can drift.

### Priority

Higher than it looks. Blog pages produce **89% of organic clicks**. A wrong price on a
high-ranking review is worse than a missing meta description, because the reader believes it
and acts on it.

---

## B13 — `science-of-temperature-therapy-routines`: a ranking problem, not a snippet one

**Status:** parked deliberately. **Do not rewrite its title or meta — they are already fine.**

767 impressions, **zero clicks**, weighted position **18.7**. Its visible queries sit at
positions **56 to 74**:

| Query | Impressions | Position |
|---|---|---|
| `cold plunge temperature` | 19 | 68.2 |
| `cold plunge temperature and time` | 11 | 74.5 |
| `ideal cold plunge temperature for beginners` | 7 | 73.6 |

**Its SEO title is 61 characters and concrete.** Its meta is 162, fact-led and already in
voice. Neither is the problem — nobody is seeing the page. Rewriting the snippet reaches an
audience that does not exist at position 68.

**If the topic is worth pursuing, it needs a ranking strategy**: the queries are real
(`cold plunge temperature` and its variants), the intent is commercial-adjacent, and the site
already ranks for adjacent cold-plunge terms. That is content depth, internal linking and
possibly a different URL — not a title tweak.

**Whoever picks this up: do not redo the snippet work.** It has been checked and it is not
where the problem is.


---

## B14 — Article snippet hygiene: 77 long metas, 31 long titles, 18 stock openers

**Status:** deferred as a batch. **Position-tested 7 September 2026 and found not to be a
round.** See `reports/snippet-backlog-position-test.md`.

| | Total | Page one | Page one, excluding the dropped german article |
|---|---|---|---|
| Metas over 155 decoded | 77 | 15 (36,180 impr) | **14 (866 impr)** |
| Titles over 60 decoded | 31 | 6 (35,524 impr) | **5 (210 impr)** |
| Stock openers (`Discover` ×14) | 18 | 4 (204 impr) | 4 (204 impr) |

**`saunas/what-is-a-german-sauna` alone is 35,314 of those page-one impressions**, and it was
dropped on intent grounds. Behind it, the entire addressable page-one meta backlog is **866
impressions — 1.9% of the base Round 3b worked on.**

**32 of the 77 over-length metas are on articles with zero impressions in 28 days.**

### How to work it

Opportunistically, when an article is open for another reason. Prioritise by impressions, not
by which rule is broken. The only item that would justify a standalone look is
`cold-plunge/how-long-should-i-cold-plunge` — 390 impressions, position 9.4, **0.00% CTR**.

**Do not batch-rewrite 77 metas.** Most of them are on pages nobody sees, and the ones that
matter were already done in Round 3b.

### Do not re-derive the health-claim count

A screen of the same surface returns **36 flagged articles**. That number is misleading and
acting on it would degrade the site — most flagged articles are evidence pieces whose titles
name a topic and whose metas correctly limit the claim. **One genuine violation was found and
fixed** (plus two bare "health benefits" list items). Read
`reports/article-health-claim-screen.md` before re-running that screen.

---

## B15 — Inventory gaps: high-volume terms with almost nothing to sell

**Status:** open. **An inventory and merchandising decision, not a copy one.** Copy cannot fix
either of these and should not be asked to.

Two collections sit on large search terms with a catalogue that cannot support them:

| Collection | Products | Vol/mo | Price band | GSC impressions |
|---|---|---|---|---|
| `portable-saunas` | **1** | **40,500** | — | **0** |
| `indoor-sauna` | **3** | **8,100** | $11,999–$18,667 | 0 |

**48,600 monthly searches between them, four products, zero impressions.**

### Why this is a pattern and not two coincidences

Both are category terms a buyer would reasonably search — "portable sauna" and "indoor sauna"
are how people describe what they want, not niche modifiers. In both cases the store ranks for
nothing and has nothing to rank with.

`indoor-sauna` is the sharper case: its three products start at **$11,999**, while
`infrared-saunas` holds 55 units on a standard 120V circuit starting at **$1,999** — most of
which are indoor saunas. **The inventory exists; it is filed somewhere else.** So this may be a
merchandising fix rather than a purchasing one: the collection is nearly empty because products
that belong in it were never added.

`portable-saunas` has one product and no equivalent reservoir elsewhere. That one is a
purchasing question.

### What was done in the meantime

The `indoor-sauna` draft states the position honestly — three units, what they are, and a route
to `infrared-saunas` for the sub-$2,000 indoor options. That is the right handling of a thin
collection and it is not a fix.

### The decision to make

For each: **stock it, re-merchandise into it from elsewhere, merge it into a collection with
depth, or unpublish it.** All four are defensible. Writing copy against a term the catalogue
cannot serve is not.

**Check the rest of the 66 for the same shape before deciding** — `npm run sweep:order` flags
any row where volume is high and product count is low. These two were the only ones it caught
at the extreme, but the threshold was set at 3 products and 5,000/mo.

---

## B16 — `/collections/saunas` is not a superset of the sauna catalogue

**Status:** open. **Merchandising, not copy.** The client decides what `/saunas` should contain.

`/collections/saunas` carries the primary keyword **`home sauna`, 40,500/mo** — the broadest
commercial term in the category. Its name and its keyword both promise every sauna in the
store. It does not hold them.

| | ACTIVE | In `/saunas` | **Missing** |
|---|---|---|---|
| `/collections/infrared-saunas` members | 91 | 64 | **27** |
| `/collections/sauna` (traditional) members | 57 | 43 | **14** |
| Everything typed as a sauna | 167 | 112 | **55** |

**55 sauna products are absent from the collection named "Saunas".** A buyer searching
`home sauna`, landing on the page that targets it, sees two thirds of the range.

### Two different numbers, and why the smaller one is misleading

The first draft of this description said "Twenty-six are infrared". That counts products
inside `/saunas` whose **`productType` is literally "Infrared Sauna"**. But 64 of the
collection's members are also in `/infrared-saunas`.

The gap is **BACKLOG B6**: `productType` is applied inconsistently, so 38 infrared saunas
inside `/saunas` are typed plain "Sauna". **Counting by `productType` understates infrared by
more than half.** Use collection membership, not `productType`, for any claim like this until
B6 is fixed.

### Why this matters more than it looks

This is the hub-and-children question from the original audit, finally with numbers behind it.
`/saunas` reads as the category hub — the name, the keyword and the position all say so — but
its membership makes it a sibling of `/infrared-saunas` and `/sauna` rather than their parent.

Three coherent answers, genuinely different strategies:

1. **Make it a real hub.** Add all 167 sauna-typed products. `/saunas` becomes the page that
   ranks for `home sauna` and routes to the type-specific children.
2. **Make it a curated selection** and rename it so the name stops promising completeness.
   The broad term then needs a different home.
3. **Retire it** and point `home sauna` at `/infrared-saunas`, which holds the largest single
   block of stock.

### What was done in the meantime

The `/saunas` draft describes the 116 products actually in the collection and **does not imply
completeness**. It leads on the $1,999–$49,900 spread being two different buying decisions,
which is true of what is there. It needs rewriting under options 1 or 3.

**Do not fix this by editing copy.** The copy is accurate about a collection whose membership
is the problem.

## B17 — `collection-spec.js` temperature range pools unrelated figures

**Do not reach for the temperature figures without reading this.**

`spec.temperature` collects every `°F` value in title and body between 32 and 230 and
reports `min` to `max`. The range is arithmetically correct and **semantically mixed**.

`hot-tubs` reports **34–109°F**:
- `finnmark-soulcold-plunge` genuinely spans that — it is a cold/hot plunge, and 34°F and
  109°F are both real operating temperatures
- the SaunaLife wood-burning hot tubs contribute **40°F**, which is almost certainly an
  ambient or minimum spec rather than anything the tub operates at

So one collection's "range" is two different kinds of number added together.

**Status: left alone deliberately, 8 September 2026.** It is reported with its coverage
(`3/7 publish`), and **no copy has ever used it**. `far-infrared`'s "every published
maximum is 140°F" was written from a manually verified figure, not from this field.

**Before any copy uses a temperature figure from the spec**, separate operating maxima
from ambient/minimum specs — probably by only reading figures adjacent to words like
"max", "up to", "reaches", "operating". Until then treat the field as a prompt to go and
check, not as a fact.

Same class as the `red-light-therapy` and cross-sell findings: a number that is present in
the text but is not about the thing you are counting.

## B18 — `portable-saunas`: 40,500/mo with nothing behind it

**Merchandising, not copy. Retired 8 September 2026, but the demand did not go away.**

`/collections/portable-saunas` targets a term at roughly **40,500 searches a month** — the
highest-volume term touched anywhere in this sweep, by an order of magnitude over
`kohler sauna` at 880.

It holds **one product, ARCHIVED**: "Full-Spectrum Infrared Portable Sauna", $3,899, with
3 units of recorded inventory. The collection has been unpublished because a page with no
sellable product is worse than no page.

**This is a stocking decision, not an SEO one.** No amount of copy fixes an empty
collection. But 40,500/mo against a $3,899 product is the best volume-to-price ratio in
the catalogue, and it is currently earning nothing.

**If a portable sauna is ever stocked again:** republish the collection, write the
description, and treat it as a priority row rather than a tail row. Until then it stays
unpublished and this entry is the record of why.

Same class as the `red-light-therapy` model-year question and the `kahuna-chair` archive —
the sweep can only describe what the catalogue actually sells.

## B19 — `maxxus-3-person-sauna-hemlock-1` has a misleading handle

Its title and description now correctly say **Canadian Red Cedar** (manufacturer-verified,
8 September 2026). The handle still says `hemlock`.

**Deliberately not changed.** A handle change needs a 301, and this is a naming improvement
no customer reads — the handle is not shown on the page and carries no ranking weight worth
a redirect.

Noted so a later audit does not read it as an inconsistency that was missed. If the product
is ever re-slugged for another reason, fix it then.

(`maxxus-3-person-corner-sauna-hemlock` also has `hemlock` in its handle and **is** hemlock,
so it is correct and needs nothing.)

## B20 — EMF manufacturer findings, ready to publish at 90% coverage

`reports/manufacturer-emf-findings.md` holds verified manufacturer data for the three EMF
collection pages — the highest-CPC cluster in the catalogue ($9.15–$30.02).

**The headline finding: roughly a quarter of Golden Designs spec sheets (9 of 39) state two
different EMF measurement distances for the same sauna, in two different rows of the same
table.** Field strength falls off sharply with distance, so an mG figure without its
distance means nothing — and here the manufacturer's own sheet disagrees with itself. No
competitor publishes this.

**Blocked on coverage: 39 of 64 (61%).** Not published, deliberately. These three pages
exist to be the most authoritative EMF content anywhere, and opening with "of the 39 units
whose sheet we could read" hedges the sentence meant to carry the weight.

**Trigger to publish: coverage clears 90% (58 of 64).** The remaining gap is ~10 pages with
no spec table, ~10 ambiguous slugs, 4 absent from the sitemap, 2 non-Golden-Designs. The
no-spec group has at least two distinct causes and one is an extractor bug
(`mx-j206-01-zf` carries the "EMF Levels" label four times and the extractor misses it) —
fixing that alone may move coverage materially and is the cheapest next step.

**Current EMF copy is accurate and stays.** It states the mG tiers from our own listings and
already warns that manufacturers measure at different distances. This research is the
upgrade, not the fix.

---

## B3 follow-up — hand-placed contextual links on the top articles

**Client note, 8 September 2026.** The "Where to go next" block applied to 43
articles ships the routing. It is not the finished asset.

**An inline link inside relevant prose passes more than a footer block**, and
blog pages carry **88.9% of this site's clicks** (487 of 548) against 0.9% for
collections. The 43 articles we touched hold **24,171 impressions** between them
in the 28 days to 2026-09-05.

Do these by hand, highest impressions first, keeping the block as well:

| Article | Impressions | Clicks | Where an inline link belongs |
|---|---|---|---|
| `costco-sauna-guide-worth-it` | 7,379 | 69 | wherever it compares Costco pricing against a real range — `infrared-saunas` |
| `arcadia-barrel-sauna-guide` | 5,103 | 112 | the assembly and siting section — `outdoor-saunas` |
| `dynamic-saunas-review` | 2,237 | 19 | 13 product links already in the prose; the parent belongs beside the first one |
| `santiago-2-person-ultra-low-emf-sauna-review` | 1,601 | 11 | first mention of the category — `infrared-saunas` |
| `low-emf-vs-near-zero-emf-infrared-sauna-guide` | 1,559 | 3 | 3 clicks on 1,559 impressions; the spec comparison paragraph — `far-infrared` |
| `sisu-sauna-review` | 1,304 | 9 | had zero collection links before today |
| `red-light-therapy-sauna-guide` | 1,007 | 7 | — |
| `science-of-temperature-therapy-routines` | 767 | **0** | contrast-protocol section — both `saunas` and `cold-plunge` |

Eight articles, 20,957 impressions, 230 clicks. **Placement is a copy decision:
choose the sentence, choose the anchor phrase, do not let a script do it.** The
whole reason the block exists is that machine-inserting 71 anchors into prose
someone wrote produces duplicate anchor text mid-sentence.

Measure against the same rule as everything else: GSC to GSC, anchor rows
excluded, and not before the 2026-10-13 checkpoint.

---

## Manufacturer-sourced data decays — every competitor finding has a shelf life

**Client note, 8 September 2026.** The instance-39 redirect audit re-fetched all
62 sourced URLs in `data/manufacturer-emf.json`. Zero had redirected, which is
the good result. **Six now return 404** — Golden Designs and Maxxus models
delisted since capture.

That is not a defect in the research. It is what happens to research that rests
on somebody else's website.

**Everything below is a dated artefact, not a standing fact:**

| Artefact | Captured | Rests on |
|---|---|---|
| the 61% EMF coverage figure (39 of 64) | 2026-09-08 | goldendesignsaunas.com product pages, 6 now gone |
| `data/competitor-brands.json` | 2026-09-08 | five competitor sites |
| `data/almost-heaven-catalogue.json` (57 cabins) | 2026-09-08 | almostheaven.com public feed |
| the Sun Home enumeration (0 of 24 product pages) | 2026-09-08 | sunhomesaunas.com, 24 pages + 28 collections |
| both published brand reviews | 2026-09-08 | all of the above |

**Rule: re-verify, never reuse.** If any of this is republished, re-derived, or
quoted in new copy more than roughly three months out, run the enumeration again
rather than reading the file. A competitor can delist a model, move a spec behind
a form, publish a price they previously gated, or fix the thing we criticised —
and our page would still be asserting the old state with a confident number
attached.

**The specific exposure in live copy right now:** the Sun Home review says *"not
one of their 24 product pages shows the EMF figure."* The day they add it to a
product template, that sentence is false and nothing on our side will notice.
Same shape as the volatility work on collection titles, one step further out:
those numbers moved with our own stock, these move with somebody else's website.

**Suggested trigger:** re-run the enumerations before the January peak, and again
before any of this material is reused in a new piece.

---

## Misleading handles — three, all deferred for the same reason

**Client ruling, 9 September 2026.** Each of these needs a 301 for a naming
improvement no customer reads. Deferred individually; **if any one of them ever
changes for another reason, all three go together — three 301s cost the same
attention as one.**

| handle | what it says | what is true | verified |
|---|---|---|---|
| `cold-plunge-immune-system-boost` | the URL asserts a health claim | the article opens by saying *"evidence does not show it 'boosts' immunity"* | 2026-09-09 |
| `maxxus-3-person-sauna-hemlock-1` | hemlock | **Canadian Red Cedar**, in the product title and the body copy | 2026-09-09, `data/products.json` |
| `red-light-therapy-panel-skin-pain-recovery` | asserts pain recovery at URL level | 4 products; the SEO title is now the factual *"Red Light Therapy Panels \| 660nm & 850nm Published"* | 2026-09-09 |

**Why deferred rather than fixed.** In every case the visible copy is already
correct — the product title says Canadian Red Cedar, the article says the evidence
does not support the claim, the collection title states a checkable spec. The
handle is the only wrong part, and it is the part with a redirect cost attached.

**Why they are logged together.** All three are the same shape: a slug written
before the copy was audited, now contradicted by the copy above it. `hemlock-1`
also carries the trailing `-1` of a duplicate that no longer exists.

**Trigger to act:** any planned 301 on any of the three, a platform migration, or
a Search Console report showing one of them drawing impressions on the term it
misstates. Absent one of those, leave them.

---

## A cited source nobody has read

`timing-heat-cold-fatigue-type-recovery-map` cites **PMC9213381 (2022)** for
*"Cold water immersion improves short-term muscular power and soreness after
high-intensity and eccentric exercise."*

**Nobody on this project has opened that paper.** The Tier B limitation added
9 September 2026 says so out loud — *"from the exercise trials reviewed; we have
not read the underlying studies and are not going to characterise their
populations"* — rather than inventing a sample size or a population that looks
like precision.

**Not urgent.** The claim is attributed, scoped and now carries its own
disclosure. **It becomes urgent if it ever goes load-bearing** — quoted in new
copy, used to support a product claim, or lifted into a collection description.
At that point somebody reads the paper first.

**The general rule, now in CLAUDE.md rule 4:** where a citation exists but nobody
has read the source, describe the source and never characterise its contents.
Same discipline as naming NEC Article 680 without quoting a provision. This entry
exists so the one instance we know about is written down rather than remembered.

---

## STANDING CHECK — health claims arrive with supplier copy, so they recur

**Client ruling, 9 September 2026: fix on our side, do not raise it with the
vendors.** That decision has a consequence worth writing down, because it makes
this a permanent check rather than a one-time cleanup.

**The supplier copy is the source.** 28 ACTIVE products carry a health claim and
they concentrate in four vendors:

| vendor | ACTIVE products with a confirmed claim |
|---|---|
| Golden Designs Inc | 10 |
| Dynamic Saunas | 8 |
| Maxxus | 4 |
| Scandia Manufacturing / Finnmark / others | 6 |

Since we are not asking the vendors to change what they send, **every new product
from Golden Designs, Dynamic Saunas, Maxxus and Scandia arrives with the same
copy and the same claims.** Cleaning the current 28 fixes today and nothing else.

### The check

Run `scripts/audit/health-claim-screen.mjs` against a product's description:

- **on creation**, before it goes live, and
- **on republish**, which matters more than it sounds. **Draft is the normal
  state for a product between stock runs on exactly these vendors** — the client's
  own constraint is that counts fluctuate for Golden Designs, Maxxus and Dynamic
  Saunas. A draft product is a published product waiting, and a republish puts
  unscreened supplier copy live without anything resembling a review.

**There is no product-onboarding script in this repo**, so this is a manual step
until one exists. If one is ever built, this belongs in it as a gate rather than
a warning.

### Known probe gaps, not yet fixed

Two misses found while reading the 13 by hand, recorded rather than patched so
the next person does not trust the count blindly:

- `detox\b` does not match **"detoxing"** — `finnmark-fd-4` says *"whether you're
  detoxing after a workout"* and was sorted into the softer tier because of it.
- **"circulation" is not always bodily.** `harvia-m3` says *"efficient air
  circulation"* and fired as a false positive.

Both argue for reading the hits rather than acting on the count, which is the
standing practice anyway.

## Sourcing quality — found during the article claim pass, 9 September 2026

Not health claims. A separate defect class: **citations that cannot be checked.**

- **`sauna-for-arthritis-joint-pain-relief`** — `(PMC, 2021)` used four times as a
  citation. **PMC is a library, not a study.** Same shape as citing "PubMed": it
  names where something lives, not what it says, and a reader cannot follow it.
  Close relative of the NEC rule — naming a standard is honest, characterising its
  contents is not.
- **`sauna-for-arthritis-joint-pain-relief`** — Healthline cited **8 times in-text**
  plus **2 bibliography entries with live outbound links**, on an article about a
  medical condition. A content aggregator is not a source for a claim about
  synovial tissue. Eight is a sourcing standard, not a slip; it needs its own pass.
- ~~`best-infrared-sauna-muscle-recovery` — two Reddit threads listed as bibliography sources.~~ **WITHDRAWN 2026-09-09 — the finding was wrong; see below.**

Also outstanding from the same pass:

- **Three verification scripts share their pattern with what they verify** and have
  no known-positive: `scan-broken-copy.js` (same script specifies AND verifies),
  `drift-check.mjs` (shares `lib/probes.mjs` with the drafting path), and
  `collection-spec.js`. See `reports/verifier-independence.md`. Audited, not fixed —
  each needs a hand-chosen case, and choosing it badly reproduces the problem with a
  fixture attached.
- **`verify-render.js` was proved once, by hand, and the proof is not encoded.**
  CLAUDE.md requires re-proving a guard whenever the thing it checks grows.
- **`changelog-integrity.mjs` has no known-positive** and produced three matcher
  artefacts on its first run.


## Q1 QUEUE — FIRST ITEM: the Recall Checker

**Deferred to Q1 by the client, 9 September 2026. Deferred, not dropped, and the
reasoning is kept here so it is not rediscovered from scratch.**

**Why it keeps its value while the season passes.** It is a **link and
AI-citation asset**, not a seasonal conversion page. `are infrared saunas safe`
runs 1,300/mo, but the reason to build it is that a recall lookup is the kind of
page other sites cite and assistants quote — and at **67 referring domains
against competitors at 31,286 and 56,553**, an asset that earns links is worth
more to this domain than an asset that earns sessions. **Links keep. A January
conversion page that lands in December does not.**

**What is already done, so nobody re-scopes it:**
- CPSC recall data source identified and scoped
- Safety-hub research complete (priority 4 in `CLAUDE.md`)
- `are-infrared-saunas-safe` is live, read during the article claim pass, and
  its medication-interaction section confirmed as an exempt safety warning —
  the hub has a spine already

**What it still needs:** a decision on whether it queries CPSC live or ships a
dated snapshot, and the manufacturer-data-decay rule applies either way — a
recall list is exactly the kind of third-party data that goes stale silently.

**Put it first in Q1.** It is the only remaining item on the priority list that
does not compete with the January peak for its value.

## Apply-script hardening — from instance 55, 9 September 2026

A `--only`-less invocation of `apply-collection-copy.js` reverted three C4
cluster links because the staged `.md` files predated live edits made out of band.

1. **`apply-collection-copy.js` must refuse to run unscoped without `--all`.**
   Its current default is "write every approved file", which in a repo where
   staged copy goes stale is a revert of every out-of-band edit to the set. It
   looks like a no-op because most rows are.
2. **It should diff each staged file against the LIVE description and report
   divergence before writing.** A staged file that differs from live is either an
   intended edit or a stale revert and the script cannot tell which — but it can
   show a human which files are in that state. `assertFresh` guards dumps against
   the changelog and has no opinion about staged copy at all.
3. **The same gap exists in every apply script that writes from `content/`.**
   Check `apply-article-seo.js` and `apply-seo-fields.js` for the same default.

Deliberately not fixed on the day, so the guard is not written to the shape of a
single incident.

## Author schema — BLOCKED on bylines, deferred to the END by client ruling

**Client ruling 9 September 2026: bylines are decided last, after everything
else.** Recorded here so the consequence is visible rather than deferred
silently.

**What stays blocked until then:** `Article` author schema, `Person` markup, and
every E-E-A-T signal that depends on a named author. At **67 referring domains
against competitors at 31,286 and 56,553**, author authority is one of the few
ranking levers this domain has that does not require links, and it is the one
currently switched off.

**The facts that make it a decision rather than a formality:** six personas are
live on articles, and **Dr. Alptunaer is quoted in six national outlets and
appears on none of them.** A byline that cannot be corroborated is worse than no
byline under E-E-A-T; a real expert who is already cited nationally and is absent
from our own pages is unclaimed authority.

**Do not implement author schema against a persona.** If the ruling lands after
15 November, this misses the season, and that is the cost of the deferral rather
than an argument against it.

## URGENT — 19 stale figures in live prose across 7 collections

**Caught by `drift-check` within the hour, 9 September 2026.** Two causes, and
neither is a mistake: the client archived the duplicate Catalonia, and normal
stock movement did the rest.

| collection | stale figures in VISIBLE prose |
|---|---|
| `far-infrared` | set_size 71→70, price_max $14,999→$9,999, needs_240v 7→6, near_zero_tier 17→16, tool_free 40→39, hemlock 56→55 |
| `infrared-saunas` | set_size 91→90, bluetooth 80→79, needs_240v 10→9, hemlock 68→67 |
| `saunas` | set_size 116→115, bluetooth 76→75, capacity_stated 97→96 |
| `near-zero-emf` | price_max $14,999→$9,999, publishes_mg 12→13, tier 21→20 |
| `golden-designs` | chromotherapy 21→22, dedicated_circuit 6→7 |
| `cold-plunge` | draft_count 12→11 |
| `red-light-therapy-panel-…` | red_light 2→3 |

**`infrared-saunas` and `saunas` are two of the three highest-traffic collection
pages in the estate.** Each needs the cold-plunge treatment: re-derive the WHOLE
claim set through `collection-spec.js`, not a number swap, because the cold-plunge
correction found four wrong figures and one unverifiable behind a single flagged
count.

**The `infrared-saunas` meta written today already carries the corrected 90**, so
the meta and the description now disagree until this is done.

### What it argues

**One archive by the client invalidated 19 published figures across 7
collections.** That is the count-in-copy fragility CLAUDE.md already warns about,
measured. Every one of these pages would be immune if its facts were tier
definitions, universal negatives or price bands rather than counts — the
`red-light-therapy` "Not One Publishes a Wavelength" shape.

**Worth putting to the client as a strategy question, not just a fix:** counts
read as precision and cost a re-derivation every time stock moves, on a catalogue
whose stock moves weekly.

## Build `assertStagedFresh` — see reports/staged-freshness.md

Proposed in full, deliberately not built the day of the incident. Refuses rather
than warns, aborts the batch rather than the row, separates STALE from PENDING,
carries `--force-staged` with named handles, and needs a synthetic known-positive.

## 301 the archived Catalonia URL

`/products/catalonia-8p-infrared-sauna` returns **HTTP 404**. It was published
2026-01-20 to 2026-09-09 — nearly eight months of history discarded.

**Redirect to `/products/golden-designs-gdi-6880-02-elite-catalonia`** — same
product, same SKU, in stock. At 67 referring domains this store cannot afford to
throw away a URL when the destination is an exact match. Shopify URL redirects
are an admin function; this needs the client or a `urlRedirectCreate` mutation.

**The general case: 39 more SKUs have an archived twin**, and every archive that
was ever published is the same trade. Check before archiving, not after.

## 28 SEO titles still carry a fragile figure — the metas are done, the titles are not

**The 36-meta batch was written to rule 6a-ii from the start. The titles predate
it**, and 28 of 64 still carry a set size or a price band:

`Sauna Heaters | 95 Electric & Wood` · `Barrel Saunas | 17 Builds From $4,999` ·
`Massage Chairs | 8 Models, $4,000–$10,599` · `Steam Saunas | 15 Traditional
Cabins Reaching 195°F` · `Harvia Sauna Heaters | 36 Models` · and 23 more.

**Not urgent, and not free either.** A title is the strongest snippet signal and
rewriting one resets whatever CTR history it has, so this should NOT be done
before the 13 October checkpoint — changing 28 titles mid-measurement destroys
the before/after the whole round is built on.

**Do it after the checkpoint reads**, and do it selectively: several of these
counts earn their place. `Steam Saunas | 15 Traditional Cabins Reaching 195°F`
carries a category correction (these are cabins, not steam rooms) that the count
does not weaken, and `Harvia | 36 Models, 4.5kW to 40kW` pairs a fragile count
with a durable kW span. **The test is 6a-ii's: does a durable fact do the same
work?** Where the count is the only specific thing in the title, it stays until
something better replaces it.

**The two best titles in the estate remain the model:** `Low EMF Saunas | 5–10 mG
— Ask the Measuring Distance` and `Red Light Therapy Saunas | Not One Publishes a
Wavelength`. Neither has a count and both say something no competitor prints.

## `dynamic-cold-therapy-accesories` — published, 1 product, 0 ACTIVE, no copy

The last in-scope published collection with nothing on it. Its single product is
not ACTIVE, so the page is empty to a customer. Either stock it, or unpublish it
the way `portable-saunas` was — a published page with no sellable product is
worse than no page (BACKLOG B18's reasoning).

## 13 October checkpoint — SCHEDULED items, so they read as planned rather than missed

**Settle window 2026-10-13 to 2026-10-20. Measurement start is the theme publish
timestamp, not the title apply time. GSC to GSC only. The 11 zero-impression
collections are excluded from the arithmetic entirely.**

**Do NOT touch before the checkpoint reads:**

1. **The 28 SEO titles still carrying a set size or a price band.** Rewriting them
   mid-measurement destroys the before/after the whole round is built on. Scheduled
   for immediately after the window closes, and **selectively** — several counts
   earn their place under 6a-ii. `Steam Saunas | 15 Traditional Cabins Reaching
   195°F` carries a category correction that the count **reinforces**: it is the
   fifteen-ness that makes "these are cabins, not steam rooms" land.
2. **`/collections/saunas` is a LINK-GRAPH test at this checkpoint, not a title
   test.** Do not read it as one.

**Read at the checkpoint, and expect the collection copy rewritten to 6a-ii on
9 September to have had only ~4 weeks** — inside the 6-10 week settle range but at
the bottom of it. A flat result on those nine is not evidence the standard failed.

## Cross-page figure references — the gap, and why it needs a `cites:` block rather than a register entry

**`indoor-sauna` says "55 of 91 units run on a standard 120V circuit."** That
figure belongs to `infrared-saunas`, which now says *"most"* and whose set size
is 90. It has been wrong since the rewrite and **three guards missed it**:

- `stale-references.mjs` carries claims we **corrected**. Nobody corrected the 55;
  we stopped saying it somewhere else. Out of scope by construction.
- `drift-check.mjs` re-derives a page's **own** `claims:` block. It has no notion
  that this page's prose holds another page's number.
- `seo-field-drift.mjs` reads SEO fields only.

**Why it cannot simply be added to the stale-references register.** That register
matches known stale STRINGS. A cross-page figure has no knowable stale form in
advance — it is *any* number on page A derived from page B, and enumerating those
is the drift problem, not the string problem.

### The fix: extend the `claims:` front matter with a source handle

```yaml
claims:
  set_size: 3
  cites:
    infrared_120v_share: { from: infrared-saunas, probe: names_120v, of: set_size }
```

`drift-check` already re-derives every entry in `claims:` from
`data/products.json`. The only change is that a `cites:` entry re-derives against
the **named source collection** instead of the current one. **Perhaps 30 lines**,
and it reuses the whole existing mechanism.

**Then a borrowed figure carries a method, which is rule 6c applied across
pages** — a figure with no method cannot be defended, and a figure borrowed from
another page has a method: someone else's.

**Interim practice, recorded in the script:** when copy quotes another page's
number, put it in this page's `claims:` block anyway, keyed to the source handle.
It will not auto-verify yet, but it will be visible to whoever looks.

**Do it with the 42 description rewrites after 13 October** — those rewrites are
where the borrowed figures will be found, and fixing the mechanism while the copy
is open is cheaper than a separate pass.

## Sources-page canonicals — four ready, two blocked on a 404 parent

See `reports/sources-canonicals.md`. Four canonicals ready to apply.

**Two point at parents that DO NOT EXIST and must not be canonicalised:**

- `sauna-detox` names `do-saunas-help-detox-your-body` — **HTTP 404**
- `red-light-collagen` names `red-light-therapy-for-collagen` — **HTTP 404**

Neither stated parent appears anywhere in the current 118-article set, and neither
404 is new damage — both predate this session.

**Do NOT canonicalise either to the topically-nearest live page.**
`sauna-detox-science-explained` looks like the obvious parent for `sauna-detox`
and is not the article those citations were assembled for. Pointing a canonical at
a page the sources do not support manufactures a relationship the content does not
have — the same move as routing evidence where no claim is made.

**The decision is content, not technical:** write the missing parents, fold the
citations into an existing article after reading whether they support it, or
deindex the two sources pages.

## CORRECTED — the "48 products with no meta description" was wrong

**Verified after the Round 6 publish: products were never in the gap.**

`seoDescription` is null on 19 ACTIVE products in the Admin API, and reading that
as "no meta tag" was the error. **Liquid's `page_description` auto-derives from
the product body when the SEO field is empty**, so those products took branch C
of the description chain and always rendered a meta. `stealth-black-mode`, the
test subject, renders *"Make your float tank unique with an all black finish."* —
its own description, not the new fallback.

**Seventh dump-misread instance, and the most consequential: it went into a
BACKLOG entry, a client report, and a comment in the shipped theme file.**

### What the else branch actually covers

Checked live after publish: `/search`, `/cart`, `/404`, and any page or blog with
no `description_tag`. **Those are utility pages that should not rank.**

**So the change is correct and its value is small.** The population it was
justified by does not exist. The real fix for the real gap was writing the **8
blog metas**, which happened the same day and made the blogs take branch C too.

**Not reverted** — a page rendering a generic description is still better than one
rendering none, and search/cart/404 are noindex-adjacent rather than harmful. But
the theme comment overstates it and should be corrected on the next branch.

### The old entry, kept for the record

### ~~48 products with no meta description~~

The theme fallback shipped on the Round 6 branch covers them **generically** —
`shop.description` — which moves them from *no signal* to *a generic signal*.

**It does not replace real metas and it is not meant to.** 48 products still need
descriptions written from their own facts. Count as at 2026-09-09; re-derive
before starting, because it moves with the catalogue.

## `home-improvement-reviews` meta is 162 chars — deliberate, do not "fix"

**Client ruling 2026-09-09: leave it.** An over-length meta on a blog with **zero
articles** and **no GSC rows** is not worth an edit.

Logged here so a future meta-length sweep does not flag it as missed. **If either
empty blog ever gets content, the meta gets rewritten then** — that is the trigger,
not a calendar.

## Method: how to remove an empty blog, if the client ever wants it

Recorded as the method rather than a recommendation, so it is available without
re-deriving.

A blog has **no publication toggle**. `blogDelete` is the only removal and it is
irreversible. The Admin API **cannot see inbound links from other sites**, so
"nothing internal references it" is not "nothing references it".

**Sequence: `urlRedirectCreate` from `/blogs/<handle>` to a real blog → watch 30
days → delete if nothing arrives.** That converts an irreversible action into a
reversible one with a waiting period, and costs nothing.

## Non-finding, closed: 44 parameterised product URLs in GSC

`?currency=USD&country=US&variant=…` rows appear 44 times in Search Console. **The
canonical on each points at the clean URL.** Google reporting variants it crawled,
consolidating correctly.

**No action.** Recorded so nobody spends an afternoon on it. **A URL in Search
Console is evidence Google crawled it, not evidence of a problem.**


## WITHDRAWN — the Reddit citations on `best-infrared-sauna-muscle-recovery`

**Logged as a defect, read properly, and it is not one.** Recorded rather than
deleted, because a withdrawn finding is as useful as a confirmed one and this file
is where someone would otherwise re-find it.

The claim was: *two Reddit threads listed as bibliography sources on a page about
recovery evidence.* Both halves of that are true in isolation and the conclusion
was wrong.

**What the article actually does:**

- **The bibliography is already segregated.** The Sources section has a subheading
  **"Primary Research"** and a separate subheading **"User Experiences"**. Both
  Reddit threads sit under the second one, alongside an LA Times piece.
- **The in-text citations already frame them as anecdote**, three times:
  *"Reddit users describe sleeping better…"*, *"User anecdotes often describe
  reduced pain…"*, *"(Reddit anecdotes, 2024)"*. Not one presents a forum comment
  as evidence.

**And the proposed fix would have caused a real defect.** Deleting the two
bibliography entries would have orphaned three in-text citations — the
citation-has-multiple-representations rule, which this project already has, being
broken by a fix aimed at a citation problem.

**How the wrong finding happened:** it came from a regex hit on `<li><p>Reddit` in
the bibliography, and the subheading two elements above it was never read. **A
screen selects the unit of work; a full read defines it** — third instance, and the
first where the full read cancelled the work entirely rather than expanding it.

**No action. The article's sourcing is better than the audit that flagged it.**

## DECLINED striking-distance terms — reasons recorded so nobody revives them from a rank tool

All three were in the Priority-1 striking-distance list. **Each was declined on
GSC evidence, not on effort.** If a rank tool surfaces them again, this is the
answer.

### `floatation-therapy-tanks` — position 55.1, 209 impressions

**Five SKUs from one manufacturer**, $8,075–$22,325, competing with float-tank
specialists on a five-product range. Position 55 with **1,436 characters of good
copy and a good title** is not a copy problem. **It is catalogue depth.**

**And the winnable terms are already won:** `dreampod home float pro` sits at
**10.1**, `dreampod v2 float pod` at **6.9**. The brand terms rank; the generic
category term does not and will not on five SKUs.

**Same shape as the German sauna ruling** — a term the site is structurally not
going to win, where the honest move is to say so rather than spend the hours.
**Revisit only if the range grows.**

### `infrared sauna for muscle recovery` — position 18.6

**The brief cited "competition 0.01". That is a rank-tool figure and GSC settles
it: the head term draws 10 impressions.** The page earns 452 across everything it
ranks for, at position 13.

Not worthless — the page is worth improving — but **the named term is not the
reason**, and it should never again be picked up as a striking-distance
opportunity on the strength of a competition score.

### `thermasol` — position 35.1, and only half of it is ours to fix

**Two separate problems and the second cannot be fixed by SEO at all.**

1. **Hub structure.** Eleven ThermaSol product pages rank — several on page one,
   at positions 4.2, 5.0 and 9.0 — while `/collections/thermasol` sits at 35. For
   a brand query Google is choosing our product pages over our brand page. That is
   internal linking, not copy.
2. **Catalogue.** All 12 products are $8,360–$13,985 steam **systems**. Someone
   searching the bare brand `thermasol` is frequently after a $200 part or a
   replacement control. **We do not stock the cheap end**, so the bare-brand term
   is capped regardless of what we do to the page.

**Do item 1 with the next internal-linking pass. Item 2 is a merchandising
decision and is not an SEO task.**

## Third-party price data on our pages has a shelf life — and some sources cannot be automated

**General form of the Costco problem.** Where our copy states someone else's
price, that figure decays and we do not control it. Where the source blocks
automated requests, **no guard in this repo can watch it** — the drift check
re-derives from `products.json`, which is our catalogue and not theirs.

**Pages carrying third-party price data:**

| page | impr | whose prices | automatable? |
|---|---|---|---|
| `costco-sauna-guide-worth-it` | **7,379** | Costco — 5 models with item numbers, a $500 promo, an assembly range | **NO — HTTP 403** |
| `lifetrend-cold-plunge-review` | 6,856 | Costco — "$2,999, down from $3,999" | **NO — HTTP 403** |
| `arcadia-barrel-sauna-guide` | 5,103 | Costco — the Arcadia at ~$2,999 | **NO — HTTP 403** |
| the four C4 brand reviews | 0 (new) | Sunlighten, Clearlight, Sun Home, Almost Heaven entry prices | partly — `shop-us.sunlighten.com` publishes 111 of 111; the others gate or vary |
| `msrp-drift.mjs` targets | — | Golden Designs, Scandia, Medical Saunas MSRPs | **YES — products.json feeds, already scripted** |

**So the Costco cluster is the exposure: 19,338 impressions across three pages
carrying prices we cannot verify by script.**

**Practice until something better exists:** a **manual monthly check** against the
Costco item numbers, which are listed in `reports/costco-price-maintenance.md` so
the check takes ten minutes in a browser rather than a re-derivation. **And keep
the dollar figures out of titles and metas** — a stale price in a snippet is seen
by everyone who searches, and in body copy it is seen by readers who reached the
page.

**Same class as the free-returns and $47-value defects:** true when written, false
because the thing it describes changed. The difference is that here we always knew
it would change and the only question is who checks.

---

## The Costco price check is a client task, and its shape is why it takes ten minutes

Verified 2026-09-09. All five Costco item numbers checked by the client against
Costco.com; every price accurate. `reports/costco-price-maintenance.md` carries the
date, the outcome and the next review (2026-10-09).

**The check was manual and took ten minutes.** That is the item worth recording.
The report is a five-row table of item number, price and the ZIP the price was
pulled at, and it is a ten-minute job *because* it is that shape. Anyone tempted
to enrich it — add narrative, fold it into a wider audit, chase automation against
a members-only storefront — should note that they would be spending the property
that makes it get done.

Automating it means scraping a warehouse retailer behind a membership wall with
prices that vary by warehouse. Not proposed.

## Five ACTIVE product pages link out to competing retailers

Found during the 673-product check, not its subject. Full list in
`reports/product-collection-links.md`.

`golden-designs-narvick`, `leisurecraft-luna`, `scandia-barrel-sauna-4-person`,
`golden-designs-6315`, `narvi-inari` — plus ARCHIVED `dynamic-3person-sauna`.
Destinations include goldendesigninc.com, norsesteam.com, nordicasauna.com,
findyourbath.com and vital-hydrotherapy.com. **Three carry `utm_source=chatgpt.com`**,
so they are assistant citation links pasted into product copy with the citation
still attached.

`costco-sauna-guide-worth-it` carries the same goldendesigninc.com link, so this is
not confined to product descriptions.

The no-outbound-links rule was written for collection copy. **Products and articles
were never in its scope** — this is the complement, and the answer to "when was it
last checked" is never. Recommend removal of all six. Not applied.

---

## A dead second render path on every collection page

`sections/main-collection-product.liquid` carries a full collection-description
block — a truncated short version, a hidden full version and a READ MORE toggle —
gated behind `{% if section.settings['enable-saunaBlock'] %}`.

**That setting is `false` in all five published themes**, Round 2 through Round 7.
It has never been on. The description renders from a different section entirely
(`collection_reference_copy`, `div.inh-collection-reference`), which is what Round 2
added and what `verify-render` checks.

**The weight it carries anyway:** the section's CSS block and its READ MORE
JavaScript ship on every collection page regardless of the setting, because they sit
outside the conditional. Roughly 40 lines of dead CSS and 20 of dead JS, on 90
collection pages.

**Not visible, not urgent, real.** Trigger: the next theme branch that touches
`main-collection-product.liquid` for any other reason. Do not make a branch for it
alone.

**AMENDED 10 September 2026 — checked before cutting, and it is NOT dead code.**

| dependency | detail |
|---|---|
| four sibling settings | `quiz_heading`, `quiz_description`, `quiz_button_text`, `quiz_button_link` each carry `"visible_if": "{{ section.settings.enable-saunaBlock }}"` |
| another live section | `sections/image-text-meta.liquid` uses `.sauna-description` and `.sauna-content`, and is referenced by `product.json`, `product.wider-images.json` and `product.Bundle.json` |

**A setting false everywhere is not the same as code nothing references.** Removing
the setting breaks four settings in the theme editor; removing the shared CSS breaks
product pages. Only `.collection-description-short`, `.collection-description-full`
and `.sauna-readmore` are unique to the section, and that is a handful of rules.

**This item is closed as "will not do" rather than deferred**, so it does not come
back as an oversight. Reopen only if `image-text-meta` is removed from the product
templates.

⚠️ **Do not "fix" it by setting `enable-saunaBlock` to true.** That would render the
description twice on every collection page — once from each path — which is a
duplicate-content defect worse than the dead weight.

---

## OPEN QUESTION: does Judge.me inject `aggregateRating` client-side?

**Not closed. Recorded as an open question because closing it wrongly costs more than
leaving it open.**

Checked 10 September across four product pages: Judge.me is installed — 171 `jdgm-`
classes — and emits **no `aggregateRating` anywhere in the server response.** Its own
CSS hides the badge at a zero average, and no sampled product rendered a review count
server-side.

**What could not be checked from here:** whether its JavaScript injects rating markup
after load. A fetch cannot see it and **Google renders JavaScript**, so the
possibility is real.

**Why it matters in both directions.** Round 9 deliberately added no `aggregateRating`.
If Judge.me does inject one client-side and we later add a server-side block, the page
carries two — **the duplicate-rating problem arriving from two directions**, and the
kind of Search Console error nobody traces back to either change.

**To resolve:** render a product page with JavaScript enabled, or read Judge.me's
structured-data setting in its admin. **Trigger:** anyone proposing to add rating
markup to the theme. Do not add it until this is answered.

---

## `product.layout-2.json` — unpatched by decision, and the guard is on the other side

Renders `main-product-layout-2`. **Zero products assigned.** It carries neither the
Round 9 product-to-collection block nor the `itemCondition` / `priceValidUntil` schema
fields.

**Deliberately left unpatched.** Adding untested code to an unused section is a real
risk against a hypothetical one. Ruled 10 September 2026.

**The failure mode:** assign one product to that template and the block and both schema
fields go missing, on that product only, silently.

⚠️ **Do not rely on this entry as the trigger.** The trigger would be "someone assigns
a product to layout-2", and nobody making that change will read this file. **A guard
that fires only when the person causing the failure happens to read the note is not a
guard** — that shape has failed twice this week already.

**The guard belongs on the outcome, not the action:** watch the set of templates in
use and fail when it changes. Proposed in `reports/template-drift-guard.md`, folded
into `verify-render` rather than living as a script someone has to remember. **Not
built.**

Until it exists, this entry is a note and should be treated as one.

---

## Audit every trigger in this file against the fires-where-the-actor-looks test

**Trigger: the 13 October checkpoint.** A date, on the calendar, that someone is
already going to open this file for — which is the point.

Two entries have already failed the test. The editor-residue cleanup was deferred on
"when a product-side cleaner exists" and sat inert for five days until it was
rediscovered and reported as new. `product.layout-2.json` is deferred on "someone
assigns a product to this template", which will be done by a merchant in the Shopify
admin who has never opened this repo.

**Neither failed for lack of diligence.** Both triggers require an actor who will
never read the trigger.

**The pass:** go through every entry here and mark each trigger as **fires where the
actor is looking** or **does not**. For each that does not, one of three outcomes —
build a guard that watches the outcome, do the work, or write down that it is a note
rather than a deferral and stop calling it tracked.

*Watching the outcome is cheaper and survives the person who wrote the note leaving.*

**This entry deliberately states its own trigger and where it fires**, because an item
about triggers that failed its own test would be the wrong way to record it.

---

## B6a — 155 products in no kind collection. **The count is not the finding.**

Found 10 September 2026 while building the productType mapping. Logged now with its
number so it is not rediscovered as new.

**155 products sit in no kind and no accessory collection.** Primo 76, InHouse Wellness
33, Medical Saunas 13, Harvia 6, HUUM 5, Dundalk Leisurecraft 4.

**Checked before treating the number as urgent, per the Dundalk lesson** — where 7 of 25
looked alarming and the missing 18 were floor plates and heat shields:

| | |
|---|---|
| total | **155** |
| DRAFT / ARCHIVED / UNLISTED | **86** |
| ACTIVE | 69 |
| ACTIVE, not an accessory, not a service | **35** |

And most of those 35 are accessories by another name — rotisserie kits, side shelves,
grill cradles, pizza stones, HUUM controllers.

**The genuine gap is roughly twelve products**, and the clearest part of it is **eight
ACTIVE Medical Saunas units in no sauna collection at all**: `medical-4-infrared-sauna`,
`medical-5-infrared-sauna-3-person`, `medical-7-plus-infrared-sauna`, and five
commercial models. Plus two Dundalk barrel saunas and a Harvia stove package.

**155 would have been reported as urgent. Twelve is the number.**

**Trigger:** the accessory-membership fix already queued in
`reports/brand-membership.md` — do these twelve in the same pass, since both are
membership edits against the same collections.

## Found alongside: `shopify-test-product` is in the catalogue

DRAFT, categorised *Furniture > Outdoor Furniture > Outdoor Beds*. Not visible to
customers. **Trigger:** the same membership pass. Delete or leave deliberately, but
decide rather than inherit it.

## The close report restates findings nobody will re-read

**Trigger: the 13 October checkpoint, while the close report is being written.**

The close report is built by restating findings from earlier reports. Under the
restatement rule in `CLAUDE.md` — *each restatement reads as corroboration when it is
the same unverified reading arriving again* — that makes the close the single most
exposed artefact in the project. It is also the one read after everything else is
forgotten, so a wrong line in it is authoritative and permanent.

**B6 is the proof it is not hypothetical.** Its facet symptom was restated in every
summary from the day it was found, by both the client and me, and was wrong the whole
time. Nobody re-read the original because the summary was right there.

**The pass, and it is cheap:** for every figure and finding the close restates, open
the report it came from and check the restatement against the original wording. Where
a claim has been carried through more than two documents, re-derive it instead of
quoting it. Mark each line **re-derived** or **quoted**, so the next reader knows which
is which.

---
## Audit the standing rationales in this file

**Trigger: the 13 October checkpoint**, when this file is open anyway.

B6 was promoted on a rationale that was plausible, general and never checked — that
inconsistent `product_type` triggers Merchant Center disapprovals. It triggers none.
**A rationale that is plausible, general and unchecked survives every review that does
not happen to test it, because it sounds like a fact.**

**The pass:** go through every standing rationale here and mark each as **derived from
data in this repo** or **derived from a mechanism that sounds right**. For the second
kind, either check it or restate the entry on whatever justification does survive.

B6's work survived its rationale being wrong. **The next one may not.**

---

## B6b — the facet split is on custom metafields, not `productType`

**This is B6's headline customer-visible symptom, on the field it actually lives on.**
"Indoor (85)" beside "Indoor(1)" on `/collections/infrared-saunas` is
`p.m.custom.location_`. "Indoor" was never a `productType` value. B6 could not have
fixed it and did not.

**Nine split facets across four metafields, nine products, every one whitespace or case:**

| field | splits |
|---|---|
| `custom.location_` | `Indoor` 156 · `Indoor ` 2 · `Indoor​` 1 (zero-width) |
| `custom.wood` | `Hemlock` 110 · `Hemlock ` 1 · `Hemlock​` 1 (zero-width) |
| `custom.style` | `Cabin` 31 · `Cabin ` 1 |
| `custom.capacity_` | `2 Person`/` 2 Person` · `3 Person`/`3 person` · `6KW`/`6kW` · `9KW`/`9kW` · `12KW`/`12kW` |

**Trigger: any facet or filter work on a collection page, and the 13 October
checkpoint.** Nine records, mechanical, no copy judgement. Full detail in
`reports/producttype-aftermath.md`.

**Do not extend this to `custom.capacity_`'s other 180 values.** That field holds
person counts, kW ratings and free-text cooking-area paragraphs together. It is a
schema problem, not a whitespace one, and it needs a decision before a pass.

**And the general form, which is the part worth keeping:** a customer-visible symptom
was attributed to a field on the strength of it being the field we were working on.
**Before attributing a rendered symptom to a field, read the template or the exposed
filter list and find out which field renders it.**

## `/collections/delta` states a product split that is not true

Live copy: *"five steam generators and two accessories"*. **All seven are steam
generators** — every title says Generator. The split is the old `productType`
breakdown, `Steam Shower 5` + `Sauna Accessories 2`, and it was wrong.

The normalisation removed the wrong field value and left the sentence it produced.
**Correcting a source does not correct what was derived from it** — same shape as
the rename that left the stale anchor standing.

**One sentence. It still goes through the read gate.** Trigger: the next collection
copy pass, or sooner if anyone touches `delta`.

### And the taxonomy has no value for a steam generator

All seven are now `Steam Room`. They are not rooms. The approved 14-value set has
`Sauna Heater` for the sauna equivalent and nothing for the steam one, so the
collection-override rule put them where the collection sits. **The apply followed the
approved mapping; the mapping has a gap.** Client question, not a defect.

---

## B6c — `custom.capacity_` is three fields sharing a name. **CLIENT DECISION.**

**The finding underneath B6b, and bigger than the splits were.** B6b deduplicated
this field from 189 values to 173. That made the list shorter and no more usable.

**173 distinct values, three incompatible kinds:**

| kind | example |
|---|---|
| person counts | `2 Person`, `3 Person` |
| kW ratings | `9 kW`, `16 kW` — 99 values |
| free text | a 163-character cooking-area paragraph listing whole chickens, steaks and racks of ribs |

**This is not a field with dirty values. It is three fields sharing a name**, and it
is exposed as a customer-facing filter on collection pages including
`/collections/infrared-saunas`.

**A facet cannot work in this form.** A shopper filtering by capacity is offered
person counts, kilowatt ratings and a paragraph in one list. No amount of value
cleaning changes that — the field has no single meaning to filter on.

**The obvious shape is `capacity_people` and `capacity_kw` as separate metafields**,
with the free text moved to a description field or dropped. **Deliberately not scoped
further.** It is a schema change touching a live filter, a theme template and 455
populated values, and whether the facet matters enough to justify it is the client's
call, not an engineering tidy-up.

~~**Trigger: any work on collection filters, and the 13 October checkpoint.**~~

> **CLOSED — client ruling, 18 September 2026 (Round 18i): leave `custom.capacity_` as it is.** The overloading is
> deliberate and the faceted navigation depends on it. The analysis limitation it creates is recorded in CLAUDE.md
> (*"custom.capacity_ is overloaded by design"*), so it is handled as a caveat on analysis, not as a defect.

## OPEN — HUUM HIVE: the capacity field contradicts the product title

```
handle      huum-hive
title       Wood-Burning Sauna Stove + Stones – 9.8kW – For 282–635 cu. ft.
capacity_   10 kW
```

**One of the two is wrong and nothing available here says which.** Establishing it
needs the manufacturer's spec. Inventing a figure would be a fabricated product fact.

The B6b kW pass wrote this row — a **format** change, `10KW` to `10 kW`, leaving the
contested number untouched — because a HOLD guard meant to exclude it was keyed on a
handle typed from the title and matched nothing. **The changelog carries an amending
row marked `REVIEWED-NOT-CLEARED`** so the write is not read as the record having
been checked.

Second, separate mismatch on the same record: the handle is `huum-hive` and the title
names a generic wood-burning stove with no brand in it.

**Goes to the client with B6c.**

---

## `natural-sauna-rocks-25lbs` — a bag of rocks that has now corrupted three outputs

**ACTIVE. `productType` is `Sauna Heater`. It is a 25lb bag of rocks.**

```
handle       natural-sauna-rocks-25lbs
productType  Sauna Heater          <- wrong
google cat   Home & Garden > Pool & Spa > Sauna Accessories   <- right, and it was outvoted
collections  sauna-heaters, sauna-accessories, avada-best-sellers, ...
capacity_    null  — the "3kW" lives in the description body
```

**Three separate outputs it has now corrupted:**

1. `/collections/sauna-heaters` published **"3kW to 50kW"**, where the 3 kW came from this
   bag of rocks. Already recorded in `CLAUDE.md` under the exempted-set rule.
2. The productType normalisation typed it **Sauna Heater**, and it survived the review
   because the summary counts looked right.
3. The disclosure-block kW analysis picked it up as a 3kW electric unit — the **lowest**
   value in the whole set, which is what made it visible.

**A number attached to the wrong record does not stay in one report.** It is picked up by
every later pass that trusts the field, and each pass makes it look more established.

**The upstream cause is membership, not type.** The fill classifier's collection-override
rule assigned `Sauna Heater` because the product sits in `sauna-heaters` — the rule working
exactly as specified, on a collection that is wrong. **`google_product_category` already
said Sauna Accessories and the override outranked it.**

That is worth recording against the 33-exceptions finding: those 33 all resolved toward
the collection being right, which is why collections were ranked above the field. **This is
the counter-case, and one counter-case does not overturn 33** — but it does mean the
override needs a check against `google_product_category` rather than an assumption.

**Fix:** remove from `sauna-heaters`, retype to `Sauna Accessories`, then re-derive the
`sauna-heaters` collection copy, which still carries a kW floor derived from it.

**Trigger: the next membership pass, and before any re-derivation of `sauna-heaters`.**

---

## Audit every probe for a typed-glyph character class

**Trigger: before the next probe is written, and at the 13 October checkpoint.**

Three invisible characters defeated three separate probes in one session — U+200B,
U+2011 and U+202F — and a fourth failure was a **checker** whose whitespace class was
built by typing glyphs between brackets and silently lost U+202F.

**Every probe written before 10 September 2026 built its character classes by typing.**
A typed class is unreadable, unreviewable and silently incomplete: nobody can see what is
in it, including its author.

**The pass:** grep `scripts/` for bracketed character classes containing non-ASCII, and
rewrite each as `new RegExp('[\\uXXXX...]')`. Where a literal must be pasted (Liquid has
no escapes), add a comment naming each code point.

## The 8 September policy draft carried an unsourced detail

`reports/shipping-policy-correction.md` asserted the freight carrier *"brings the crate to
the end of your driveway **on a lift gate**"*. **"Lift gate" appears in 0 of 672 product
descriptions and 0 times in `shipping-facts.json`.**

**The draft was accurate on everything checkable** — $600, $1,800, the electrical
exclusion, the non-refundable terms all matched their primary sources two days later — and
it carried one invented product fact through a review that verified the figures.

**Accuracy on the numbers is not the same as being right.** A figure gets checked because
it is obviously checkable; a descriptive clause beside it does not, because it reads as
context rather than as a claim.

Caught by re-reading the draft against its sources before applying, per the staged-decision
rule. **Recorded because the catch was the process working, and because the next draft
will have the same shape.**

---

## B2 — CLOSED 10 September 2026. Alt text at 100% coverage.

2,874 images written across 479 ACTIVE products; 2 held. Verified by re-deriving the
coverage measurement, not by reading the writes back.

| | before | after |
|---|---|---|
| images with no alt | 1,629 (56%) | **0** |
| over 125 chars | 305 | 0 |
| machine-stuffed `-{vendor}-InHouse Wellness` | 1,253 | 0 |
| products with duplicate alt across images | 148 | 0 |

**Held, deliberately:** `dynamic-venice-elite` images 3 and 4 read `venice-front` and
`venice-right`. Hand-written, and they name the view — more than the generator can say.

### The honest limit, and it needs a person not a generator

Alt is derived from the product title plus image position, because we cannot see the
images and rule 6 forbids inventing what is in them. On a product with a long name and
many images that means **a 110-character name repeated nine times with only the index
varying** — `medical-breakthrough-5-massage-chair` is the worst case.

That is better than what it replaced, which was the same 137-character stuffed string
nine times with **nothing** varying. It is not good alt text.

**Real alt text describes what is in each shot: a control panel, a bench detail, a room
setting, a person in the unit.** No generator produces that from a title. **It is a human
looking at 2,884 images**, and it is only worth doing if image search becomes a channel
that matters here.

**Trigger: a decision that image search matters, or an accessibility audit.** Not before —
the current state is compliant and honest, and re-doing it by hand is days of work.

---

## Answer-first pass — CLOSED 10 September 2026. Five rewrites, not 97.

| | |
|---|---|
| articles | 118 |
| first sentence carries a figure | 41 |
| no figure, but the first sentence arrives | 66 |
| **circled before arriving — rewritten** | **5** |
| marginal, left alone | 3 |

**The brief said 97.** That was 117 minus an earlier pass of 20 whose record does not
survive, so the subtraction was unsupported. Enumeration gave 5.

**Ten extractor defects were found and fixed before the count could be trusted, and every
correction moved articles OUT of the queue** — 33, then 39, then 41. A queue whose errors
all inflate it is built on a measurement biased toward work. See `CLAUDE.md`.

**Three of the five stranded a later element** and were repaired in a second pass: a
paragraph reveal, a paragraph payoff, and a heading.

**The screen is renamed.** `answer-first-scan.mjs` now reports `HAS-FIGURE` / `READ-ME`
rather than `COMPLIANT` / `NO-NUMBER`. It detects a digit; it cannot judge answer-first,
and calling it compliance is what made 97 look defensible.

### Known-wrong set of one

`small-space-sauna-guide-corner-straight-wall-configurations` — the extractor reads a
table-of-contents list item. Its real lede sits in a `<div dir="ltr" align="left">` that
the container test does not reach. **Not a rewrite candidate**: the real lede is
answer-first. Recorded because an extractor with a declared blind spot is more trustworthy
than one with a clean count.

## `mindfulness-the-revolutionary-productivity-boost` — unscreened rule-4 claims

**Against its entry in the 329 never-read set.** Two effect claims, both with no
population and no limitation:

> "…mindfulness is not just a wellness trend but **a legitimate productivity hack that can
> enhance focus, reduce stress, and improve overall work performance**."

> "**Research indicates that mindfulness can lower stress levels**, enhance emotional
> regulation, and improve cognitive flexibility."

**Why every screen missed it:** the health-claim probes were built from sauna, cold plunge,
infrared and red light vocabulary. This article says none of those words. It was in scope,
it was scanned, and it came back clean — **a screen's coverage is its word list, not its
record count.**

**Trigger: whoever opens the 329.** Start here, and check what other SUBJECTS the estate
covers that no probe was built for.

## Assistant-paste residue on articles — its own pass, after the copy work

The product estate went 302 to 0. **Articles were never swept.**

| | |
|---|---|
| articles with class-attribute residue | **4** of 118 |
| total class attributes | 1,241 |
| worst | `hot-tub-cold-plunge-combo` 591, `sauna-autophagy` 435, `cold-plunge-brand-we-dont-recommend` 118 |

**The Google Docs finding is the useful half.** 74 articles carry `id="h.xxxxxxx"` heading
anchors. **These are NOT residue** — they are jump targets for in-page links, and stripping
them breaks the links. A sweep that treats them as editor junk would do real damage.

Five more carry `dir="ltr"`, which is inert.

**Trigger: after the copy programme.** Smaller than the product sweep and the same shape.

---

## Four articles carrying an incomplete Review node — the third defect on the same records

**Against their entries in the 329 never-read set.**

`arcadia-barrel-sauna-guide` · `santiago-2-person-ultra-low-emf-sauna-review` ·
`homedics-premium-steam-sauna-review` · `lifetrend-cold-plunge-review`

All four are PUBLISHED and all four hand-write a `Review` node whose `itemReviewed` is a
`Product` with **no `offers`, no `review`, no `aggregateRating`**. That is Search Console's
four critical Product-snippet items, exactly: *"Either offers, review, or aggregateRating
should be specified."*

**Do not add `offers`.** Three of the four review products the store does not sell, and
publishing an offer for a competitor's product would be false. **The likely fix is that
`itemReviewed` should not be a `Product`** — a `Thing` or `ProductModel` carries no offers
requirement — but that is a schema decision on four live articles and it belongs in a
queue, not in a passing pass.

### The reason these are worth reading rather than fixing

**Three separate defects, on overlapping records, none found by looking for it:**

| defect | how it surfaced |
|---|---|
| assistant-pasted markup | a widened residue sweep |
| JSON-LD wrapped in `<p><script>` | the answer-first extractor read schema as prose |
| incomplete `Review` node | Search Console's critical items |

**Each was found by a pass aimed at something else.** That is the argument for reading
these four in full rather than fixing the one defect that has a ticket.

### And the class was ruled out before the instances were found

The theme **cannot** produce this error: its offers array loops over `product.variants`,
every product has at least one variant, so a product page always emits offers. That ruled
out all 673 products before any of the four was identified — a stronger argument than
checking them, because it eliminates the class rather than the instances.

## CHECKPOINT PREDICTION — Product snippet detection, due 13 October 2026

**Baseline, Search Console, 8 September 2026: 92 valid Product snippet URLs.**
390 product URLs earn impressions in the 7 September GSC baseline.

**The differential test, with a control:**

| outcome on 13 Oct | reading |
|---|---|
| materially above 92 | **re-crawl lag.** Detection is working and was behind. No action. |
| flat at ~92 | **detection failure.** Something about ~298 indexed product pages stops Google registering schema. Worth diagnosing. |

**Nothing about product schema changes between now and then**, which is what makes this a
control rather than a hope. Round 11 touches only the Bundle template's review widget.

**Two caveats that bound what the gap is worth:**

- **390 is a FLOOR on indexed products, not a count.** The GSC Pages report lists only URLs
  with impressions; products indexed and earning none do not appear.
- **230 of the 390 earn fewer than 10 impressions each.** Most of the estate ranks thinly
  regardless of schema, so fixing detection on ~298 pages is a smaller prize than the
  number suggests.

---

## Description-chain branches — the four duplicate metas are NOT writable metas

**The instruction "write real metas for the policy pages" described an option that does not
exist.** The investigation changed the item rather than delaying it.

**Six URLs share one meta string.** The homepage (with and without a trailing slash),
`/policies/refund-policy`, `/policies/terms-of-service`, `/policies/shipping-policy`, and
`bucket-ladle-sand-timer`. Semrush grades this as an **error**; a missing meta is only a
**warning**, so the Round 6 fallback moved these pages into a worse bucket by that scoring.

### Why none of them can simply be written

| | |
|---|---|
| **Shopify policy pages have no SEO description field.** | Not in the admin, not via the API. |
| **The token cannot reach legal policies.** | No `read_legal_policies`, no `write_legal_policies`. Same wall as the shipping-policy correction. |
| **All four fall to the Round 6 `else` branch**, which emits `shop.description`. | That branch exists because 8 blog indexes, 4 pages and 48 products previously rendered **no** meta at all. |

**So there are exactly two levers**, and one of them is a trap.

### The scope, if this is built

**Add branches AHEAD of the fallback. Never modify the fallback.**

- `template contains 'policy'` → derive from the policy's own title, giving three distinct
  strings
- `template == 'index'` → a real homepage meta

**Do NOT edit `shop.description` in Settings to fix the homepage.** It is the floor for
**everything without its own meta**, including the 48 products the Round 6 comment names.
Changing it is not a homepage fix; it silently rewrites the fallback everywhere it is
inherited.

**Do NOT edit the `else` branch itself.** It is a catch-all serving blog indexes, static
pages and 48 products alongside these four — the same shape as the title chain's catch-all,
one chain over.

### Corrections to the original framing

- **The shipping-policy meta is INDEPENDENT of the Settings correction.** The meta does not
  come from the document, so nothing here was ever blocked on the client pasting it.
- **`bucket-ladle-sand-timer` needs nothing.** It has no product description to derive from
  and stops being a duplicate the moment the other five diverge.
- **`bbq-grills` and `more` (cluster B) stay duplicated deliberately** — both SCOPE-OUT.

**Clears 8 of the 19 Semrush errors.** Worth doing because six URLs sharing one string is
wrong on its own terms, not for the score.

**Trigger: its own branch, with its own verification. Not bundled with a title change.**

---

## Hand-written schema — the complete enumeration, and why three screens each missed part

**Six nodes across 118 articles and 26 pages. No page carries any.**

| type | record | state |
|---|---|---|
| Review | `arcadia-barrel-sauna-guide` | itemReviewed:Product missing offers/review/rating |
| Review | `santiago-2-person-ultra-low-emf-sauna-review` | same |
| Review | `homedics-premium-steam-sauna-review` | same |
| Review | `lifetrend-cold-plunge-review` | same |
| ItemList | `best-6-person-sauna` | **FIXED** — 11 nodes to 10, images sourced, 1 DRAFT dropped |
| ItemList | `best-outdoor-cold-plunge-tubs` | **FIXED** — 8 nodes, images sourced, none dropped |

### Three screens, three different subsets, and none measured the class

| screen | found | missed |
|---|---|---|
| **Search Console** | the 4 Review nodes | both ItemLists |
| **Semrush** (crawled 100 of ~800) | 1 ItemList | the 4 Reviews and the other ItemList |
| **enumeration** | **all 6** | — |

**Neither tool was wrong.** Semrush reports what it crawled; Search Console reports what
Google chose to surface. **But the union of two partial screens is a FLOOR, not a
measurement.**

> **When two independent screens each return a different subset of one defect class,
> neither is a measurement of the class.** Enumerate it.

**Practical rule: the moment a hand-written artefact of any kind surfaces, enumerate the
class.** Six nodes across 144 records took minutes and was available the day the first
Review node was found, weeks ago.

**`best-outdoor-cold-plunge-tubs` cleared nothing measurable** — Semrush never crawled it
and Search Console never reported it. Fixed anyway: eight Product nodes with no image are
wrong on their own terms.

**The four Review nodes remain open.** Do not add `offers` — three review products the store
does not sell. The likely fix is that `itemReviewed` should not be a `Product`.

## The Round 6 fallback trade — absence fixed, duplication created

**Recorded because we made this trade without knowing we were making it.**

Round 6 added an `else` branch to the description chain because **8 blog indexes, 4 pages
and 48 products rendered no `<meta name="description">` at all**. The branch emits
`shop.description`.

**It worked, and it produced six URLs sharing one identical string.**

| | how it is graded |
|---|---|
| missing meta description | **warning** |
| duplicate meta description | **error** |

**So the fix moved those pages into a worse bucket by that scoring**, while genuinely
improving the 60 that had nothing. Both readings are true.

`bucket-ladle-sand-timer` is one of the two products deliberately left as an honest blank —
**it inherited the fallback rather than staying blank**, which is the mechanism working as
designed and still not what anyone intended.

**The general form: a fallback that fixes absence creates uniformity, and absence and
uniformity are not graded the same.** Before shipping a fallback, ask what the new failure
mode is called and how it scores — it is rarely "no failure".

---

## Review-of-the-review, 15 September 2026 — three records, and the branch plan

### #11's premise was a count that failed enumeration — the seventh

The instruction called `best-6-person-sauna` *"our highest-impression page"*. **GSC baseline
7 Sep: site rank 35, 477 impressions, 2 clicks, position 33.** The top page is
`what-is-a-german-sauna` at 23,587.

~~**The correction changes the answer rather than killing it:** 477 impressions makes a 301
cheap. It is the **only** article on `/blogs/news`, so retiring that blog is the real option.
**Not on the theme branch** — a 301 and a content move.~~

> **REMOVED FROM BACKLOG — client ruling, 18 September 2026 (Round 18i): leave `/blogs/news/best-6-person-sauna`
> where it is.** It is linked from the homepage and improving; the move is not worth a URL change. Struck through
> rather than deleted so the reasoning above stays on the record.

### #10 is NOT ours, stated plainly

The `<title>` newlines render on **every** branch of the title chain — the `else`
(homepage, static pages, blog indexes), the article branch from Round 3a, the collection
branch from Round 5, and the product branch from Round 12. **It predates Round 12.** Had it
been reported against the most recent edit we would have carried it. Google collapses
whitespace in titles, so it is cosmetic.

### #4 found a surface the alt pass never enumerated — the Files library

The 2,884-image alt pass covered **product media**. Theme blocks draw images from the
**Files library**, a separate surface, and nobody enumerated it. Two category-card images
still carry the stuffed `-{vendor}-` suffix the pass removed everywhere else.

**And locating the review's other alt items shows most of them are Files-library DATA, not
theme code:**

| item | where the value lives |
|---|---|
| #2 press logos share one alt | no hardcoded alt in code — file/setting value |
| #3 hero banner empty alt | no hardcoded alt in code — file value |
| #5 icon box `alt="images"` | **no `alt="images"` anywhere in the theme** — so it is a stored value |
| #6 image-cards empty alt | code falls back to `image.alt`, then block title; both empty |

**So those four are probably fixable with `fileUpdate` on the files, with no theme change at
all.** Confirm by enumerating the Files library once the token returns.

### #7 — which copy to remove, decided by DOM order

`header.liquid` line 133 renders `horizontal-menu`, which renders the slider at its own line
1073 — **first in the DOM**. `header.liquid` line 140 renders it again — **second**.
`theme.js` uses `querySelector`, which takes the first. **Remove `header.liquid` line 140.**
Verify the mobile Categories tab on a narrow viewport before handover.

### #8 and #9 locations

- **#8** copyright is `section_st.copyright_text`, a **theme-editor setting**, not code. A
  static year edit goes stale again next January; render the year from the date instead.
- **#9** `snippets/meta-tags.liquid` line 23 hardcodes `http:`. One line.

### Round 14 file-level alts — APPLIED and verified 15 September 2026

16 Files-library alts written by `scripts/apply/apply-file-alts.mjs` (8 press logos, hero,
icon, 6 image cards). Backup `data/backups/2026-09-15T22-25-33-001Z/file-alts.json`.

- **Hold-back guard proved before the run.** Constructed fixtures (empty → write, null →
  write, hand-written → HELD, ours → SAME, filename mismatch → refused). With the HELD branch
  deleted on a scratch copy the self-test failed: `todo=A,B,D held=` — the hand-written alt
  would have been written.
- **Outcome read, not payload:** 16/16 exact via `nodes(ids:)` AND 16/16 via a separate
  `files(query:"filename:…")` search. Re-run: `write 0 already 16 held 0`.
- **Rendered, before/after, with a noise baseline** (two before snapshots, 0 difference):
  homepage exactly 16 alt changes, page text identical. One product per icon template —
  `laguna-q-gpv3100-outdoor-island` (default), `dynamic-cold-therapy-plunge` (Bundle),
  `saunalife-g3` (wider-images, the only product on it) — exactly 1 alt change each (FAQ icon,
  was "Why Choose {vendor}?"), page text identical.
- Card alts name no brand the image cannot be shown to depict; Finnmark heater names are
  transcribed from text printed on the image.

### CLIENT — Healthgrades logo has no feature behind it on record

`data/press-links.json` (client-supplied 3 Sep): **8 articles across 7 outlets** for the
**8 logos** — Healthline has two articles, Healthgrades has none. `_unaccounted` has named it
since that round; `/pages/media` does not mention Healthgrades either.

**If the Healthgrades feature exists, link it like the others. If it does not, the logo comes
off.** A logo row under "We're Featured in…" asserts a feature. Displaying a publication that
has not featured the business is a false claim of endorsement — a different class of problem
from an alt-text gap, and not one an alt can fix. The alt "Healthgrades logo" is accurate about
the image and says nothing about whether the claim is.

### Round 14 theme branch — PUSHED 15 Sep 2026 as `146290704451`, UNPUBLISHED (was: built, not pushed)

`scripts/apply/build-round14-theme.mjs <MAIN snapshot>` → 45 files in `theme/`, listed in
`data/round14-theme-files.json`. `theme-branch.mjs` dry run against live MAIN (Round 13): 45 ±, 0 identical, 0 missing.

- **#1 escaping — 103 sites in 41 files, not 76.** Re-enumerated on MAIN r13 with
  `scripts/audit/attr-escape-scan.mjs` (masks Liquid before finding attribute context; 8
  constructed fixtures). Same data axis as the earlier pass. **Strict superset: 0 of the 76
  missing, 27 added** — multi-line tags the line regex could not see, `arial-label` typos,
  `name`/`value`/`data-option`. `escape_once`, so an already-escaped value is not double-escaped.
  Output re-scanned: 0 unescaped data-axis sites; raw 3153 → 3050, exactly −103.
- **Live baseline for the check (MAIN):** every quoted-title product sampled has 2 product-card
  `aria-label`s cut at the first U+0022. `thermasol-twph1410us` reads "…Package with 10".
  27 ACTIVE products carry U+0022 in the title, 11 as an inch mark; 25 default template,
  2 Bundle, **0 wider-images** (its one product has no quote, so that template cannot be
  checked on a quoted title).

### Found in the Round 14 files — LOGGED, NOT FIXED

1. **#4: 7 of 8 category cards render the FILE alt, not the fallback.** Only
   `saunalife-g3-outdoor.png` fell through to the section heading. Three file alts are
   defective in their own right: `dynamic-ultra-low-emf-far-infrared-sauna-barcelona-elite-edition-833322.jpg`
   and `DYN-6996-01_3x3_4_900x_df7d870a….webp` end in `-Dynamic Saunas-InHouse Wellness`;
   `calflame-bbq-grills-island-for-sale-bbk-401-rl-env-med.jpg` has its own filename as alt.
   Two more end in "image N of M", true on the product page and meaningless on a card. The
   branch puts the card title first; the file alts stay as they are and need their own pass.
2. **Address conflict on unpublished pages.** Four pages (`terms-and-conditions`,
   `refund-and-return-policy`, `privacy-policy`, `shipping-policy` handles, all 404 live) say
   5900 Balcones Drive **#21140**. Every published page, the footer and the Facebook page say
   **#20752**. The Shopify billing address is 2028 E Ben White Blvd, 78741. Anyone republishing
   those pages reintroduces the conflict.
3. **`arial-label` is not an attribute.** 32 uses in 15 files, a typo for `aria-label`, so
   assistive technology ignores them. Escaped in this branch because they break the same way;
   the name itself is untouched.
4. **Mobile menu slider truncates product names to 10 characters** (`product.title | truncate: 10`
   in `categories-menu-mobile.liquid`): cards read "Dynamic...".
5. **Footer copyright brand reads "InHouseWellness"** (editor setting), not "InHouse Wellness".
6. **YouTube footer link points at the `/shorts` tab**, not the channel. The node uses the channel.
7. **TikTok `@inhousewellness` is real but dormant** — 0 followers, 10 likes, 15 Sep 2026. It is in
   `sameAs` because the client listed it.
8. `template.name` (3 sites) cannot carry a quote and was escaped with the rest: the data axis
   matches `.name`. Harmless, and recorded so the count is not read as 103 real risks.

### Round 14 branch — pushed and verified on preview, 15 September 2026

Both decisions confirmed by the client: Balcones **#20752**, and card title wins on all eight.

- MAIN re-checked before push: 45 of 45 files identical to the build snapshot.
- `themeDuplicate` → **polled to 575 / 575** before any upsert (theme-branch.mjs upserts
  immediately, the race recorded in CLAUDE.md; pushed with theme-push.mjs instead).
- Read-back: 45 / 45 byte-identical. That is the write check, not the outcome check.
- **`scripts/audit/verify-round14.mjs`, differential.** MAIN: **5 pass, 24 fail** (the 5 are
  the Organization-absent controls, which pass on MAIN by construction). Preview
  `146290704451`: **33 pass, 0 fail.**
  - Q: cut attributes 0 on thermasol-twph1410us (10"), dynamic-lugano-infrared-sauna,
    saunalife-ee8g (Bundle, 79"L x 91"D), /collections/steam-showers, /collections/golden-designs,
    homepage. MAIN: 32, 32, 32, 42, 72, 30. **The exposure was sitewide, not 2 per page** — the
    quoted Golden Designs titles sit in menus on every page. wider-images is not testable on a
    quoted title (its one product has none) and is not counted as tested.
  - O: one Organization node on the homepage, fields as ruled, no telephone; absent on a
    product, collection, page, article and blog index. URL, logo, YouTube and Pinterest resolve
    by fetch; Facebook, Instagram and TikTok were resolved in a browser the same day.
  - T: 13 page types (home, 3 products across all 3 templates, 3 collections, page, blog index,
    article, search, paginated collection, 404): no raw newline, and the collapsed decoded
    title is identical to MAIN on every one.
  - C 8/8 card alt = card title. S one slider copy. Y "© 2026 InHouseWellness". G og:image https.
- **Mobile Categories tab, preview, 375 px, in a browser** (`Shopify.theme` confirmed the
  preview): tab clicked, "Best sellers" slider displayed, Swiper initialised, 3 slides in view,
  `slideNext` advanced 0 → 1, one instance; categories list 4 items.

### CORRECTION — the 76 → 103 gap was the METHOD, not the code moving

The client's framing was that the scan measured the code at a moment and the code moved.
**Tested before recording, and it did not.** The original line regex re-run on MAIN r13
returns the identical **89 hits (76 after the same filter), zero line keys different** from
the stale local checkout. All 27 additions are sites the first method could not see:

| blind spot of the first scan | examples |
|---|---|
| one line at a time | attributes on tags that span lines |
| a fixed attribute-name list (`alt`, `title`, `aria-label`, `data-*title/name/alt`, `content`, `placeholder`) | `arial-label` ×7, `name`, `value`, `data-option`, `data-value`, `data-label`, `child-menu-name` |

**So it is the probe-vocabulary failure again, in markup:** the attribute list was ours, the
theme's typos and form fields were not in it. Same shape as the escaping count itself — the
earlier count was MINE, and it was a measurement of what its pattern could see.

### Files-library pass — seven category-card image files (logged, not fixed)

Card title now wins in the theme, so these no longer render on the cards. **The alts still
live on the files** and render wherever else the files are used. Before rewriting, check each
for product-media use: alt belongs to the file, and an "image N of M" alt may be correct on its
product page.

| file | current alt | defect |
|---|---|---|
| `calflame-bbq-grills-island-for-sale-bbk-401-rl-env-med.jpg` | the filename | **filename as alt** |
| `dynamic-ultra-low-emf-far-infrared-sauna-barcelona-elite-edition-833322.jpg` | "…Barcelona Elite Edition-Dynamic Saunas-InHouse Wellness" | **keyword-stuffed suffix** |
| `DYN-6996-01_3x3_4_900x_df7d870a-c55d-4fcc-b100-610bea2d534f.webp` | "…Canadian Hemlock-Dynamic Saunas-InHouse Wellness" | **keyword-stuffed suffix** |
| `scandia-4-person-barrel-sauna-kit-traditional-electric-sauna-for-home-wellness-relaxation-472361.webp` | "…, image 4 of 7" | position index off-product |
| `fd-4--trinity-combination-sauna-red-light-therapy-500x500_1.jpg` | "…, image 5 of 9" | position index off-product |
| `luxury-infrared-dynamic-sauna-for-2-low-emf-red-light-therapy-bluetooth-speakers-venice-edition-923915.jpg` | full product title | product title, not the image |
| `dundalk-leisurecraft-the-polar-cold-plunge-tub-premium-cold-plunge-for-recovery-wellness-ct362pp-784985.jpg` | "Dundalk LeisureCraft The Polar Cold Plunge Tub" | product title, not the image |

Same shape as the press logos: Files-library values on a surface the 2,884-image product-media
pass never enumerated.

### AFTER THE CLIENT PUBLISHES — three checks

1. `node scripts/audit/verify-round14.mjs` (no theme id = live). Must read **33 / 0**; it read
   5 / 24 before publish.
2. The Organization checks inside it: homepage only, absent on the five controls.
3. `node scripts/audit/rendered-title-sweep.mjs` on live — rendered over-60 product titles
   must equal the pre-publish baseline below. The field-derived count (317 of 480 ACTIVE
   today, unchanged from Round 12's 317 of 481) never passes through the title chain, so it
   cannot show whether a second chain edit held; only the rendered sweep can.

Client items are in `reports/round-14-client-items.md`: three addresses, #21140 on four
unpublished pages, returns wording, Healthgrades, the inch-mark cut, the branch.

**Rendered title baseline, taken 15 Sep 2026 before publish** (`scripts/audit/rendered-title-sweep.mjs`,
rows in `data/rendered-titles-pre-r14.json`), all 478 ACTIVE published products, 0 unreachable:

| | over 60 | suffix | raw newline | theme confirmed |
|---|---|---|---|---|
| MAIN | **317** | 0 | 478 | — |
| preview `146290704451` | **317** | 0 | **0** | 478 / 478 via `Shopify.theme` |

Per product, the collapsed decoded title is identical on 478 of 478. The newline column is the
differential proving the sweep read two different themes. **Post-publish pass condition: live
reads 317 / 0 suffix / 0 newline.** 317 matches Round 12's prediction and the field-derived count.

### Client rulings, 15 September 2026 (evening)

**1. Healthgrades — CLOSED.** The feature is real; all eight logos stay and the alt stands.
The earlier entry above ("no feature on record") is superseded, not deleted: it records what
was checkable from here, which was that the press file held no URL for it.
**Still open, and it is the original finding:** 7 of 8 logos link to their article and
Healthgrades has none on file. An unlinked logo among linked ones reads as decorative.
Asked the client for the URL; it belongs in `data/press-links.json`, whose `_unaccounted`
block has named it since the first round.

**2. Balcones #20752 is the ONLY address.** Ben White is an old address and is replaced
everywhere it appears; #21140 on the four unpublished pages goes the same way.

**Queued — NOT started. Runs after the publish and the three post-publish checks**, so the
branch does not grow now. Enumerate every occurrence BEFORE changing any, and report by
location:

| location | reachable from here? |
|---|---|
| Shopify billing settings | **no** — client's, and see the flag below |
| pages, products, articles, metafields | yes, Admin API |
| theme: footer, contact sections, any hardcoded string | yes, but a theme edit means a NEW branch |
| policy pages (Settings → Policies) | **no** — client pastes, as with the shipping policy |

⚠ **The billing address is flagged as not cosmetic.** It can feed tax registration, payout
records and invoices, so changing it is the client's call with whoever handles his accounts —
not an SEO edit. Ask first whether Ben White is still the registered address for tax and
payouts; if it is, it stays in Settings and only PUBLISHED addresses change.

**Close condition:** after the sweep, Balcones #20752 is the only address rendering anywhere,
and the Organization node matches it. Both re-derived from rendered pages, not from the dump —
`data/content.json` is a 9 Sep dump and already disagreed with live on which pages carry #21140.

### Address enumeration — done 16 Sep 2026, 4 fixed, 3 client-only, 2 held, 1 comment

`scripts/audit/address-sweep.mjs` (read-only) over 30 pages, 118 articles, 672 products,
94 collections, 561 live-theme files, rendered policy pages, all metaobjects. Patterns built
from code points, with markup/invisible-space tolerance between words, and the street number
matched independently of the street name. **10 must-change occurrences found, enumerated
before any write.**

- **FIXED:** suite #21140 on the four unpublished pages, via `scripts/apply/fix-suite-21140.mjs`
  (dry-run default, exactly-1-match per target, refuses if a page turns out to be published).
  Backup `data/backups/2026-09-16T00-25-12-431Z/`. Re-read after the write: 4/4 read
  `21140:0 20752:1`.
- **CLIENT ONLY — Settings billing address**, flagged as not cosmetic (tax registration,
  payouts, invoices).
- **HELD — `extended-your-warranty-3-years`** states "Business Address: 2028 E. Ben White Blvd.
  **#240-6180**, Austin, TX 78741". Held for two reasons: it is a **fourth** suite variant
  (billing says 240 **6184**, so one is a typo and we cannot tell which), and it is a **warranty
  document**, the same not-cosmetic class as the billing field. **Not on the storefront** — the
  product 404s on Online Store but is **published to Meta and Microsoft Copilot**, so the old
  address is live on those channels.
- **NOT a hit:** `layout/theme.liquid` contains "#21140" inside the Organization comment, which
  describes the situation. Left alone.

**Two API scopes are missing and both are recorded as UNCHECKED, not as clean:**
`read_legal_policies` (policy BODIES — the rendered pages were read instead, and they are clean)
and locations (`read_locations` — a location address is a Settings field we cannot see; the
client should check it).

**Metafield cap tested rather than assumed:** the sweep read 20 metafields per record; re-run
at 100, **241 products exceed 20** and **zero** occurrences were hidden beyond the cap. Pages,
articles and collections top out at 3 metafields.

**Close condition, current state:** Balcones #20752 is the only address rendering on the
storefront (verified live on homepage, contact, about and four policy pages), and the
Organization node carries the same address. **Not yet fully closed:** the warranty product on
Meta/Copilot and the Settings billing address are outstanding, both with the client.

### Warranty claims address — CLOSED 16 Sep 2026

Client ruling: the warranty CLAIMS address is **2028 E Ben White BLVD #240-6184, Austin, TX
78741** — Ben White, not Balcones. The "#20752 everywhere" ruling covers published website
copy; a claims address is not that. Stored value was #240-618**0**, billing says 618**4**, and
the client settled which was the typo.

`scripts/apply/fix-warranty-address.mjs` — one digit, length asserted unchanged, backup
`data/backups/2026-09-16T00-34-52-903Z/`, re-read confirms `#240-6184 ×1, #240-6180 ×0`.
The product is still Online Store-unpublished and live on Meta and Microsoft Copilot, which is
where this address is read.

**So the estate now holds two addresses on purpose:** Balcones #20752 for everything a website
visitor sees, Ben White #240-6184 for warranty claims. Recorded here so a future sweep does not
"fix" the second one back.

### Research-dossier links — SIZED, nothing removed (client: disclosure closed, not urgent)

25 distinct Google Docs, **one per article, none shared**, anchored as "our research dossier".

**First measurement was wrong and the correction is the point.** The plain-text export strips
hyperlinks, so counting URLs in it gave **206 links / 30 PubMed**. The HTML export gives
**6,730 links, 2,671 to primary sources** — a 30× undercount. *An export is a rendering, and a
count taken from it measures the export.* Same family as the dump-absence and cap rules.

**The question that decides it — are the doc's primary sources already in the article?**

| | |
|---|---|
| article primary-source links total | 111 |
| of those, also in the dossier | **108** |
| **articles citing ZERO primary sources of their own** | **6** |

So for 18 articles the dossier is **supplementary** — removing the link costs nothing.

**For 6 it is the only route to the evidence, and removing it would strand the claims:**
`how-saunas-improve-circulation`, `soft-tissue-perfusion-thermal-stress-visual-guide`,
`molecular-targets-longevity-drugs-heat-shock-cellular-stress-pathways`,
`best-2-person-sauna-buyers-guide`, `why-biohacking-matters-for-longevity`,
`bbq-grill-accessories-health-conscious-cooks`. That is the orphaned-citation problem, hit for
the fourth time. **The fix for those six is to cite the studies in the article, then the link is
free to go.** `cold-plunge-maintenance-tips` is a seventh case of its own: its dossier holds no
primary sources at all.

### Keyword ownership — `data/keyword-map.json` HAS NEVER EXISTED

Not on disk and **no git history, on any branch**. CLAUDE.md instructs "check
`data/keyword-map.json` for its assigned primary keyword" before writing collection copy, and
names it the one tracked file in `data/`. **That instruction has never been executable** — the
unguarded-clause failure again, and this time the clause names a file rather than a habit.

**Assignments do exist, in `data/collections-plan.json`:** 72 of 94 collections carry
`primaryKeyword` with volume and CPC. Checked for collisions: **0 duplicates**, so
one-keyword-one-URL holds for collections and IS verifiable — from that file, under another name.

**Articles have no keyword assignment anywhere.** For the three pages this round targets,
nothing records ownership and nothing would catch a collision. Checked by hand instead:
`sauna for cardiovascular health`, `sauna for heart health`, `best sauna for home` and
`sauna vs steam room` — **none collides** with the 72 collection keywords (`home sauna` is
`/collections/saunas`, which is a different term from `best sauna for home`; worth watching).

**Proposal, not done:** rename the file in CLAUDE.md to the one that exists, and add an
`articles` block to it as this round assigns keywords — a guard that watches the outcome rather
than a note whose trigger nobody fires.

### QUEUE — six articles must cite their own sources before any dossier link is removed

Established 16 Sep 2026. Removing a dossier link from an article that cites no primary source
of its own strands its claims — the orphaned-citation failure, fourth instance. **Order is
fixed: cite the studies in the article, THEN the link is free to remove.**

`how-saunas-improve-circulation` · `soft-tissue-perfusion-thermal-stress-visual-guide` ·
`molecular-targets-longevity-drugs-heat-shock-cellular-stress-pathways` ·
`best-2-person-sauna-buyers-guide` · `why-biohacking-matters-for-longevity` ·
`bbq-grill-accessories-health-conscious-cooks`

**`how-saunas-improve-circulation` is one of the six and is being rewritten now**, with its
sources cited in the body. When that ships, its dossier link becomes removable as a side effect
— five left, not six. Nothing is removed as part of the rewrite.

`cold-plunge-maintenance-tips` is a separate case: its dossier holds no primary sources at all,
so there is nothing to cite and nothing stranded.

### 🔴 FOUND WHILE DRAFTING: the internal link graph is substantially broken

Every internal blog link in the estate was resolved, because the cardiovascular draft needed
link targets and two of the first five I chose failed. **67 distinct internal blog URLs are
linked. 40 point at articles that do not exist, and 38 of those are broken:**

| what the URL does | count | link instances |
|---|---|---|
| **301 to the HOMEPAGE** (soft 404 — the link is spent, the reader lands on the shop front) | **25** | — |
| **hard 404** | **13** | — |
| resolves fine despite no matching article (handle differs) | 2 | — |
| **total link instances pointing at broken targets** | | **209** |

Worst: `are-saunas-good-for-you` (23 pages, 301 to homepage), `cold-plunge-benefits-premium-wellness-equipment`
(19 pages, 404), `health-benefits-traditional-sauna-vs-infrared-sauna` (15, homepage),
`how-often-should-you-use-sauna` (14, 404). Rows in `data/broken-internal-links.json`.

**This bears directly on the cardiovascular decision.** The page earns nothing and has one
inbound link; the estate's answer to "link to it" is a link graph where 209 instances go
nowhere. A retarget that ships into this graph is still invisible. **A 301 to the homepage is
the worse half** — nothing 404s, no report complains, and every one of those links is wasted.

**Not fixed, not in this draft.** Proposed as its own pass: decide per target whether the
article should be rewritten, redirected to a real relative, or the links repointed. The two on
`how-saunas-improve-circulation` itself are repointed in the draft to verified live pages.

### Cardiovascular rewrite — DRAFT WRITTEN, nothing applied

`content/fixes/cardiovascular-retarget.md` (decisions) and `content/fixes/cardiovascular-body.html`
(the copy). `assertWellFormed` passes. Every URL in it resolves, checked 16 Sep.

- **All 15 unhedged claim sentences addressed**, not one. Re-screened after writing: 6 effect
  sentences remain, and each is legitimate — an association stated as association, a mechanism
  described as proposed, a safety warning (exempt by kind), a "what we do not know" line, and
  two journal titles inside the Sources list.
- **Every number now carries its population, its interval and its n**, read from the source
  record rather than from our own summary: JAMA IM 2015, BMC Medicine 2018, J Physiol 2016
  (Brunt), Prog Cardiovasc Dis 2018.
- **The second cohort repeats the pattern**, which is the strongest thing on the page: BMC
  Medicine 2018 also fails to reach significance at 2–3 sessions a week after full adjustment,
  HR 0.75 (0.52–1.08).
- **The article now cites its own primary sources**, so it stops being one of the six, and its
  dossier link becomes removable later.
- ⚠ **SCOPE: 4,450 words → 1,681.** Fixing the claims removed the table of contents, the FAQ,
  the comparison tables and the repetition, all of which restated the same evidence. That is a
  bigger change than "fix 15 sentences" and the client decides whether to keep the long form.

### Cardiovascular retarget — APPLIED 16 Sep 2026, live and verified

`scripts/apply/apply-cardio-rewrite.mjs` + `apply-cardio-inlinks.mjs`. Backups
`2026-09-16T12-21-43-284Z` and `2026-09-16T12-23-42-043Z`.

- Body 4,450 → 1,691 words. Title, SEO title (56) and meta (148) applied. Live page checked:
  every interval, the n, "not statistically significant" and the DOI all render.
- **Two guards fired on my own work and both were right to.** (1) A `22%` string check refused
  the body — but the body names the figure only to correct it, so the guard's model was wrong,
  not the copy; it now tests PROXIMITY TO THE CORRECTION and was proved to still refuse a bare
  assertion. (2) The read-back reported `body false`: Shopify's sanitiser inserts a newline
  after `<li>`. Text and tag sequence identical. **Byte-exact read-back on a field the platform
  reformats reports a correct write as a failure** — the comparison is now normalised.
- **Inbound links 1 → 6**, each placed in a sentence the source page already had, with anchor
  text naming what the destination supports. The german-sauna anchor was updated from the old
  title, which is the rename-sweep rule applied to our own rename.
- **The dossier link left with the old body**, because the new one cites its own sources. The
  six-article queue is now FIVE.

### 🔴 THE LINK GRAPH — sized, and it is a round, not an afternoon

**Q1 — the 13 hard 404s.** Not renames: for the two most-linked, no live article covers the
topic under any handle (`are-saunas-good-for-you`, `how-often-should-you-use-sauna` — best
match NONE). Others have partial relatives, e.g. `cold-plunge-benefits-premium-wellness-equipment`
(19 links) → `cold-plunge-benefits-brown-fat-activation` shares 3 of 6 terms. **These are deleted
articles, not moved ones.**

**Q2 — the homepage redirects are DELIBERATE, and the pattern is far bigger than our links.**
All 25 have an **explicit store redirect** to `/`. There is no catch-all involved. Store-wide:

| | |
|---|---|
| URL redirects defined | **364** |
| **targeting the HOMEPAGE** | **208** |
| of those, product URLs | **126** |
| of those, blog URLs | **74** |

**Every retired product and article on this store points at the shop front.** A redirect to an
irrelevant page is treated as a soft 404: the URL's history is discarded, any external link to
it is wasted, and nothing reports an error. This is a store-level decision that predates us and
it dwarfs the internal-link half.

**Q3 — replacement content mostly does not exist.** So the fix is per-target and editorial:
repoint where a real relative exists, otherwise cut the link and read the sentence around it.

**Q4 — concentration: NOT concentrated.** 209 article→URL pairs, **330 raw link instances**,
spread across **71 of 118 articles**. 32 articles carry six or more. Worst: `maxxus-saunas-review-buyers-guide` (10),
`are-infrared-saunas-safe` (8), `soft-tissue-perfusion…` (8), `what-are-the-benefits-of-a-cold-plunge` (8).

**Estimate: a round.** 71 articles needing a read each, plus a client decision on the 208
homepage redirects, which is the bigger and cheaper win. Rows in `data/broken-internal-links.json`.

### Draft-versus-published and the feed — REPORT ONLY, 16 Sep 2026. Nothing proposed, nothing changed.

**First, the premise needs correcting. Drafting does not create the homepage redirects.**
A drafted product's URL simply 404s: `onlineStoreUrl` is null, `publishedAt` is null, no redirect
is involved. Of the **126 product URLs redirecting to the homepage**:

| | |
|---|---|
| no longer in the catalogue **at all** | **114** |
| still present as DRAFT | **7** |
| still present as ARCHIVED | 4 |
| still present as ACTIVE | 1 |

So those 126 redirects are **retired products**, created deliberately as redirects, and they are a
separate question from the drafting habit.

**Second, keeping a product published while it is out of stock WORKS, and our schema is already
correct.** Measured on the two live ACTIVE products whose stock is exhausted:

- `primo-…-grill-head-only` (tracked, policy DENY, 0 on hand): page returns **200**, renders
  "Unavailable", and emits `offers.availability: OutOfStock`.
- `helios-hm5500`: three variant offers, two OutOfStock and one InStock. Correct per-variant
  behaviour, not a conflict. (I first read it as a contradiction and it is not.)

That answers the schema half: **a tracked ACTIVE product at zero emits OutOfStock**, which is
what the feed's availability attribute needs, and the URL keeps working.

**Third, the drafting is NOT mostly stock outages.** Of **169 DRAFT products**:

| | |
|---|---|
| inventory **greater than zero** | **128** |
| inventory zero | 41 |
| tracksInventory | 163 |
| inventoryPolicy CONTINUE | 62 |
| also carrying a homepage redirect | 7 |

Top vendors: Primo 51, InHouse Wellness 30, Dynamic Cold Therapy 13, Medical Saunas 11.
**128 drafts have stock on hand**, so whatever is drafting them, most of it is not an out-of-stock
outage. Either the inventory figures are not trusted, or these are unlaunched or retired lines.
**This needs the client, and it changes the size of the conflict he is being asked to resolve.**

**What I could NOT establish, and who can:**

| question | status |
|---|---|
| Does Simprosys expose an out-of-stock exclusion? | **UNCHECKED** — app config is not API-readable, and `appInstallations` is access-denied on this token. **The client checks this in the app.** |
| Merchant Center feed state / disapprovals | **UNCHECKED** — no Merchant Center account is reachable from here (`accounts: []`) |
| Do the 200 redirected URLs carry search equity? | **UNANSWERABLE from GSC.** All 200 show zero impressions, but a redirected URL cannot appear as a page in GSC because it never serves content. **Zero here measures the instrument, not the equity.** |
| External inbound links to those URLs | **UNCHECKED** — no backlink export in `data/`, and no authenticated backlink tool in this session |

**So the "ads account versus search history" trade-off is not yet established as a real conflict.**
It only exists if Simprosys cannot exclude by availability. The schema and storefront halves
already work. That one app setting decides it, and the client is the only one who can read it.

### MY FRAMING CONFLATED TWO UNRELATED THINGS, and a client ruling was given on it

16 Sep 2026. I reported 126 product URLs redirecting to the homepage, and then reported that
drafting is the client's Merchant Center protection. **I let those sit next to each other, and
the client reasonably read them as one mechanism.** They are not related:

- a drafted product **404s**, with no redirect involved (`onlineStoreUrl` null, `publishedAt` null)
- **114 of the 126** redirected URLs are not in the catalogue at all; only 7 are DRAFT

**He was asked to choose between his ads account and his search history on a conflict that had
not been established.** The storefront and schema halves already do what he wants: a tracked
ACTIVE product at zero stock serves 200, shows "Unavailable", and emits `OutOfStock`.

**Practice, which is the restatement rule pointed at myself:** two findings reported together
assert a relationship whether or not one is claimed. Before putting two counts in one section,
say what connects them, or separate them. A ruling made on a false connection is worse than a
wrong number, because the decision gets made and the error travels inside it.

### QUESTION FOR THE CLIENT — 128 of 169 drafted products show stock on hand

Not a finding. **169 products are DRAFT; 128 of them have inventory greater than zero**, 41 are
at zero. Top vendors: Primo 51, InHouse Wellness 30, Dynamic Cold Therapy 13, Medical Saunas 11.

**Is that stock he has, stock he does not trust, or lines that are not launching?** His answer
decides whether 128 URLs should be live. Nothing is proposed until he answers.

### A redirected URL cannot appear in GSC, so zero there measures the instrument

All 200 homepage-redirected URLs show zero impressions in the 28-day report. **That is not
evidence of no equity.** A redirected URL never serves content, so it cannot be a page row.
Same family as the dump-absence rule and the text-export undercount.

**What would answer it, none of it available in this session:** GSC data from before the
redirects were created, the URL Inspection API, or a backlink export. Recorded so the next
person does not read the zero as a finding.

### The 74 blog URLs — PROPOSALS, nothing applied (16 Sep 2026)

**First, the shape: only 25 of the 74 carry any internal link.** The other 49 redirect to the
homepage with nothing on this site pointing at them, so they are an external-equity question
only, not an internal-link job.

**Method.** The dead page's content is gone, so "read both" means reading the LIVE candidate in
full and reading the ANCHOR TEXT the link promises. The anchor is what the reader was told they
would get, and it is the only surviving evidence of what the dead page did.

**PROPOSED — anchor promise and destination agree**

| dead URL | links | anchor promises | proposed target | why |
|---|---|---|---|---|
| `health-benefits-traditional-sauna-vs-infrared-sauna` | 15 | "traditional vs infrared sauna safety and benefits" | `saunas/infrared-sauna-benefits` | "What an Infrared Sauna Actually Does, and What the Evidence Does and Does Not Show" — opens by contrasting infrared with traditional temperatures and session length. **Partial: infrared-centred rather than a two-way comparison.** |
| `harnessing-the-power-of-contrast-therapy-benefits-and-insights` | 10 | "contrast therapy basics and best practices" | `saunas/contrast-therapy-demystified-human-studies` | same subject, evidence-led, states what CWT does and does not support |
| `the-ultimate-recovery-routine-for-athletes-sauna-and-cold-plunge` | 6 | "Ultimate athlete recovery routine: sauna and cold plunge essentials" | `saunas/benefits-of-cold-plunge-and-sauna` | the complete contrast-therapy guide |
| `optimizing-recovery-mastering-the-sauna-and-cold-plunge-routine` | 4 | "sauna and cold plunge routine guidance" | `saunas/benefits-of-cold-plunge-and-sauna` | same |
| `unlocking-the-power-of-cold-plunge-tubs-a-beginner-s-guide` | 8 | "cold plunge tubs for beginners" | `cold-plunge/at-home-cold-plunge` | setups, benefits and DIY options — a beginner's guide. **Chosen over the buying guides: the anchor promises orientation, not a shortlist.** |
| `health-benefits-of-fire-pits` | 4 | "health benefits of fire pits (with caveats)" | `fire/backyard-fire-pit-benefits-beyond-warmth` | same claim, hedged the same way |
| `how-to-build-a-home-wellness-spa-your-ultimate-guide` | 15 | "how to build a home wellness spa that supports consistency" | `wellness/renovation-sequencing-wellness-installations` | **judgement call.** It answers when to plan thermal spaces in a remodel, which is the buildable half of that promise. Weaker than the rows above. |
| `dynamic-santiago-elite-vs-maxxus-seattle-2-person-sauna-2026` | 3 | "Dynamic Santiago Elite vs Maxxus Seattle comparison" | `saunas/best-2-person-sauna-buyers-guide` | verified it covers **both** Santiago and Maxxus Seattle. The Santiago review scored higher on terms and is single-brand, so it does NOT answer a cross-brand comparison. **A case where the term score picked the wrong page.** |

**NO ADEQUATE RELATIVE — do not redirect, decide editorially**

| dead URL | links | why nothing fits |
|---|---|---|
| `cold-showers-or-ice-baths-which-is-best-for-recovery` | 12 | nothing compares those two modalities; the heat-vs-cold timing map is a different question |
| `transform-your-backyard-into-a-serene-wellness-retreat` | 5 | no live article on outdoor wellness space design |
| `sauna-vs-hot-tub-for-stress-relief` | 3 | no sauna-vs-hot-tub comparison exists |
| `circadian-rhythm-optimization-for-energy` | 3 | **zero term overlap with any live article.** Nothing on this site covers it |
| `10-biggest-benefits-of-using-a-sauna-for-health-and-wellness` | 2 | a benefits listicle with no equivalent; the closest pages are single-topic |

### THE TWO ORPHANS — both are real search terms, and that changes the answer

37 internal links point at content that does not exist. Volume pulled 16 Sep 2026 (Ubersuggest,
global):

| term | volume | CPC | competition | seasonality |
|---|---|---|---|---|
| **are saunas good for you** | **9,900/mo** | $0.27 | 0.60 | 8,100 summer → **14,800 in January** |
| **how often should you use a sauna** | **1,600/mo** | $0.29 | 0.23 | 1,300 → **2,900 in January** |

**Writing them beats removing the links.** 23 internal links already point at
`are-saunas-good-for-you` — a page with 9,900/mo demand, January-peaking into the season this
deadline exists for, and an internal link graph already built for it. The links are the asset;
the article is the missing half. Same for the 14 pointing at the frequency article, which is
also the page the cardiovascular rewrite wanted to cite for dose.

**Recommendation: write both, at the original handles**, so all 37 links resolve without edits.
Client decides. If he declines, the fallback is 37 link removals plus a read of every sentence
around them, which is more work than writing two articles.

### Found while judging: a duplicate pair on fire pit benefits

`fire/backyard-fire-pit-benefits-beyond-warmth` (4,355 words) and `fire/12-fire-benefits`
(3,411 words) are the same article twice, with near-identical opening claims. Outdoor cooking is
scoped out of the SEO programme, so this is logged and not acted on — but a redirect target
should not be chosen without knowing the pair exists.

### The 8 redirects — BUILT AND VERIFIED, BLOCKED ON SCOPE

`scripts/apply/apply-blog-redirects.mjs`. Dry run passes: all 8 sources currently point at "/",
all 8 destinations answer 200. **`--apply` is refused: the token lacks
`write_online_store_navigation`.** Nothing was written; all 8 re-checked afterwards and still
read "/". Either the scope is added to the token, or the client repoints them in
Online Store → Navigation → URL Redirects. The rows, with their qualifications, are in the script.

**Two recorded qualifications, not hidden:** `health-benefits-traditional-sauna-vs-infrared-sauna`
→ `infrared-sauna-benefits` is PARTIAL (destination is infrared-centred, anchor promises a
two-way comparison; move the redirect if a real comparison page is written), and
`how-to-build-a-home-wellness-spa` → `renovation-sequencing-wellness-installations` is the
weakest call, applied because a partial answer beats the homepage.

**A chain was found while fixing the path:** `/blogs/home-wellness/health-benefits-of-fire-pits`
redirects into `/blogs/saunas/health-benefits-of-fire-pits`, which then went to "/". Fixing the
second hop fixes both. **I had also guessed the wrong blog for that path** and the script's
MISSING check caught it before anything was written.

**Another instance of a score picking the wrong page:** for
`dynamic-santiago-elite-vs-maxxus-seattle`, term overlap ranked the single-brand Santiago review
first. Reading found `best-2-person-sauna-buyers-guide`, verified to cover BOTH brands.

### The 5 with no relative — volumes pulled, and two are content candidates

Redirects left as they are, per ruling. Volume 16 Sep 2026 (Ubersuggest, global):

| dead URL | links | term checked | volume | verdict |
|---|---|---|---|---|
| `sauna-vs-hot-tub-for-stress-relief` | 3 | sauna vs hot tub | **1,900/mo**, $0.68, peaks **2,900 in January** | **content candidate** — real demand, nothing on the site answers it |
| `10-biggest-benefits-of-using-a-sauna…` | 2 | sauna benefits | **74,000/mo** | head term, but **cannibalisation risk**: this belongs to `are-saunas-good-for-you`, not a second listicle |
| `cold-showers-or-ice-baths-which-is-best-for-recovery` | 12 | cold shower vs ice bath | 320/mo | **links exceed demand.** Removal job, not a content job |
| `circadian-rhythm-optimization-for-energy` | 3 | circadian rhythm optimization | 260/mo, spiky | off-topic for this catalogue |
| `transform-your-backyard-into-a-serene-wellness-retreat` | 5 | home wellness retreat backyard | **0** | no demand |

### The two orphan articles — DRAFTED, nothing applied

`content/fixes/are-saunas-good-for-you.html` (1,209 words) and
`content/fixes/how-often-should-you-use-sauna.html` (930 words). Both well-formed, both screened:
no unhedged effect claims remain. Every figure carries population, interval and n, read from the
source records (JAMA IM 2015, BMC Medicine 2018, J Physiol 2016, Mayo Clin Proc 2023).

**The anchors were read first and they set the shape.** 19 distinct anchor texts point at
`are-saunas-good-for-you`, and they overwhelmingly promise an EVIDENCE-FIRST overview: "what the
evidence says about sauna benefits" (7×), "evidence-first overview of what sauna use may
support—plus what to watch for", and one that states the article's own thesis: *"benefit and
safety are separate questions"*. The draft answers exactly that. For
`how-often-should-you-use-sauna`, 11 anchors promise a "science-backed frequency guide", so the
draft leads on the frequency the cohorts measured and the duration result nobody quotes.

⚠ **One anchor over-promises and should be reworded when the article ships:** an inbound link
calls the destination *"proven cardiovascular and metabolic benefits"*. The honest article says
the opposite — the strongest result is observational. **That link would misdescribe its own
destination**, which is the stale-anchor rule arriving before the page exists.

### Duplicate article, logged: two versions of the fire pit benefits guide

`fire/backyard-fire-pit-benefits-beyond-warmth` (4,355 words) and `fire/12-fire-benefits`
(3,411 words) cover the same subject with near-identical opening claims. Outdoor cooking is
scoped out for COPY; the scope-out does not cover the fact that two versions of one article are
live and competing. Logged, not acted on.

### The 49 blog redirects with no internal link — external equity only

49 of the 74 have nothing on this site pointing at them, so there is no internal-link work.
Whether they hold external equity is **unanswerable from here**: a redirected URL cannot appear
as a page in GSC, there is no backlink export in `data/`, and no backlink tool is authenticated
in this session. What would answer it: pre-redirect GSC data, the URL Inspection API, or a
backlink export from the client's own tool.

### The first stale anchor caught BEFORE it went stale

Every previous instance of the stale-anchor rule was archaeology: `what-is-a-german-sauna` kept
promising *"how saunas improve circulation"* for days after we removed that claim from the
destination. **This time the destination does not exist yet, so the sweep ran before publication.**

34 anchor instances point at `are-saunas-good-for-you` (19 distinct texts) and 19 at
`how-often-should-you-use-sauna` (11 distinct). **Four need rewording in the same pass, and each
edit is a sentence on another page:**

| page | anchor | why it fails |
|---|---|---|
| `chromotherapy-vs-no-chromotherapy-buyers-guide` | "proven cardiovascular and metabolic benefits" | the article says the opposite: the strongest result is observational. **The host sentence also asserts proof in its own voice** — *"the proven cardiovascular and metabolic benefits that come from sauna heat exposure alone"* — so this is a rule 4 fix on that page, not only an anchor fix |
| `sauna-alzheimers` | "the National Capital Poison Center's **guide to sauna safety**" | **misattribution.** The anchor names an external body and the href points at OUR page. A reader clicking a Poison Control citation lands on us |
| `biophilic-design-measurable-outcomes-evidence` | "measurable biophilic outcomes" | the destination is about sauna evidence and says nothing about biophilic design outcomes |
| `are-infrared-saunas-safe` | "a broader comparison … across different types and populations, our comprehensive overview examines traditional, infrared, **and steam** options" | the draft covers traditional and infrared. **It does not cover steam.** Promising scope the page lacks |

Passing on reading: `sauna-autophagy`'s *"the cardiovascular evidence is where the strongest case
lives"* is exactly what the draft says, and the plain "what the evidence says about sauna
benefits" wording (7 uses) is accurate.

**Practice: when writing a page that inbound links already point at, sweep the anchors BEFORE
publishing.** The links are a specification of what the page must say, and the ones that
over-promise are cheaper to fix now than after Google has seen both.

### Redirect chains — enumerated, 43 of them, nothing had ever looked

All 364 store redirects resolved against each other:

| | |
|---|---|
| **chains (a redirect pointing at another redirect)** | **43** |
| loops | **0** |
| longest | **4 hops** |
| chains ending at the homepage | 6 |

Longest: `/products/bliss-2-sauna-for-two-luxury-wellness` → `bliss-2-sauna-2-persons` →
`bliss-2-sauna-luxury-wellness` → `ellness-bliss-2-infrared-sauna` → `bliss-2-infrared-sauna`.
Most are product-handle churn, one rename stacked on another over years. Note
`ellness-bliss-2-infrared-sauna` — a typo handle preserved as a hop.

**A chain is a different defect from a homepage redirect.** Nothing reports it, each hop loses a
little, and the 6 that end at the homepage inherit both problems. Fixing them means pointing
every hop at the final destination, which is one pass once the scope exists.

### Deliberate non-target: "sauna benefits" (74,000/mo)

`10-biggest-benefits-of-using-a-sauna-for-health-and-wellness` (2 inbound links) is NOT being
rebuilt. That head term belongs to `are-saunas-good-for-you`, and a second benefits listicle
would cannibalise the page we are about to publish. Recorded so nobody reads the 74,000 as a
missed opportunity later.

### Both orphan articles PUBLISHED 16 Sep 2026 — and the redirect did not intercept

`scripts/apply/publish-orphan-articles.mjs`. `are-saunas-good-for-you`
(gid 570067189827, 1,209 words) and `how-often-should-you-use-sauna` (gid 570067222595, 930 words),
both at the handles the links already pointed at.

**The open risk was whether the store redirect would win.** `are-saunas-good-for-you` had a
redirect to "/" and we cannot delete it (no `write_online_store_navigation`). Measured after
publishing: the URL serves **200 with the article**. **A Shopify URL redirect does not intercept
a live resource on this store.** Recorded because it decided whether publishing at that handle
was possible at all, and because the next person will face the same question.

- Rendered head verified on both: `<title>` and `<meta name="description">` MATCH what was set.
- **All 53 inbound link instances across 37 articles now resolve 200.** (37 is distinct source
  articles; 53 is raw href instances. Both counts are real and they are not the same number.)
- Every outbound link verified before publishing. Two DOIs return 403 to a scripted client —
  jamanetwork and Wiley sit behind Cloudflare. Checked in a browser: both resolve to the correct
  publisher article. **A 403 to curl is a bot wall, not a dead link.**

**Enumeration re-run, and the prediction held exactly.** 38 broken → **36**. Pairs at broken
targets 209 → 171, a drop of **38 = 23 + 14 + 1**. The extra 1 is
`health-benefits-traditional-sauna-vs-infrared-sauna` losing a source, because the cardiovascular
rewrite replaced a body that carried that dead link. Fully accounted for, nothing unexplained.

Baseline record: `data/new-pages-no-history.json`. Both pages have **zero baseline impressions by
construction** and must be excluded from before/after arithmetic.

### CORRECTION — the "misattribution" was MY probe, not the article

I reported that `sauna-alzheimers` linked the phrase *"the National Capital Poison Center's guide
to sauna safety"* at our own page. **It does not.** The href is
`https://www.poison.org/articles/are-saunas-good-for-you` — the Poison Control article itself,
correctly attributed, with a `title` attribute naming it.

**My sweep matched the slug ANYWHERE in the href**, and Poison Control's URL ends in the same
slug as our new page. Restricted to internal links, the counts are 33 and 20 instances, and
**2 external links carry that slug in their URL** — both to poison.org.

So the answer to "does the Poison Center publish sauna guidance" is yes, and **the article was
already citing it correctly.** Nothing to fix there.

**Practice, and it is the probe-vocabulary rule in a new costume:** a slug is a substring, not an
identifier. Match the PATH with its origin, never the handle anywhere in a URL. I raised a
misattribution against copy that was right.

### chromotherapy-vs-no-chromotherapy — FULL READ, 6,689 words. Verdicts per sentence.

Second surfacing of this page (first as a stale anchor, now as a rule 4 screen hit) and the
first time anyone has read it. **The screen over-fired, as predicted, and the real defect is not
the one it found.**

**On chromotherapy itself the article is careful and rule 4 compliant.** It says the evidence is
limited, non-sauna-specific and experiential; it carries a "What We Still Don't Know" section
naming six gaps; it refuses the replace-your-medication question outright. **Every "proven" that
appears in a sentence about chromotherapy is the article doing its job.**

**The defect is the CONTRAST TERM: sauna heat is repeatedly described as proven.**

| # | sentence | verdict |
|---|---|---|
| 1 | "Skip chromotherapy if you're budget-conscious or want only **clinically proven heat benefits**" | **ASSERTS** |
| 2 | "heat-only sauna (**proven cardiovascular and relaxation benefits**)" | **ASSERTS** |
| 3 | "…anyone on a tight budget who mainly wants the **proven cardiovascular and metabolic benefits** that come from sauna heat exposure alone" | **ASSERTS** — and this is the anchor pointing at our new page |
| 4 | "If you're drawn to the simplicity and **proven benefits** of traditional sauna bathing" | **ASSERTS** |
| 5 | "**Research shows** that regular dry or infrared sauna sessions **deliver** meaningful health outcomes through heat exposure" | **ASSERTS** |
| 6 | "Evidence: **High for heat benefits**" (decision ruleset) | **ASSERTS** — grades the evidence |
| 7 | "Sauna heat itself has the **strongest and most extensive evidence base** for health benefits" | REPORTS — comparative and defensible |
| 8 | "Strongest body of evidence within sauna literature for cardiovascular and functional outcomes" | REPORTS |
| 9 | "Sauna therapy trials show pain reductions tied to regular heat exposure" | **NEEDS LIMITATION** — no population, no design |
| 10 | "…linking regular dry or infrared sauna bathing to reduced cardiovascular events, improved blood pressure, pain relief, and better functional outcomes" | **NEEDS LIMITATION** |
| 11–19 | chromotherapy-evidence sentences the screen flagged on the word "proven" | REPORTS — the article refusing a claim |

**6 ASSERTS, 2 NEEDS LIMITATION, 11 correct.** The screen's 19 was a reading queue, not a defect
count, exactly as the term-screen rule says.

### 🔴 AND THE CITATION UNDER ALL OF IT IS MISATTRIBUTED — 14 uses

The article cites **"(Laukkanen et al., 2018)" 14 times**, and its Sources list gives that name
to *"Clinical Effects of Regular Dry Sauna Bathing: A Systematic Review"*, PMC5941775.

**That paper is Hussain J and Cohen M, 2018, in *Evidence-Based Complementary and Alternative
Medicine*** (PubMed 29849692, DOI 10.1155/2018/1857413). Laukkanen is not an author.

**And the paper says the opposite of what it is cited for.** Its own abstract: *"Many health
benefits are claimed … however the medical evidence to support these claims is not well
established"*, 40 studies, only 13 randomised, most with fewer than 40 participants, concluding
*"potential health benefits"* and asking for better data.

**So "Evidence: High for heat benefits (Laukkanen et al., 2018)" misnames the authors AND
inverts the finding.** This is variant 3 and variant 5 of the wrong-source family in one
citation, repeated 14 times, on a page nobody had read.

**Not fixed. This is now a rewrite, not an anchor edit**, and it needs the same treatment the
cardiovascular page got.

### Also found in that article — not health claims, logged

1. **Empty citation placeholders shipped live:** `Key Citations: (RLT wavelengths); (chromotherapy vs RLT distinction); Laukkanen et al., 2018` — two parentheses with no source in them.
2. **Lighting vendors cited for safety standards:** Radiant Health Saunas (PDF), China Beauty Lighting, RedDot LED for IEC 60335-2-53, IEC 62471 and photobiological limits, plus Inner Light Sauna for colour guidance. Name the standard, do not source it from a seller.
3. **Frequency guidance conflicts with the article we just published:** it says "20–30 minute sessions, one to four times weekly" and elsewhere "15–30 minutes", citing the misattributed review. Our new frequency page says the significant cohort result sits at four to seven sessions, and the duration result favours over 19 minutes.
4. Dossier link present, so this page stays in the five-article queue.

### 🔴 THE LAUKKANEN ATTRIBUTION IS ESTATE-WIDE, NOT ONE ARTICLE — its own pass

Enumerated across all 118 articles: **171 mentions of Laukkanen in 20 articles**, 21 of them
explicit attributions carrying a URL. Most are correct — the 2015 JAMA IM cohort, the 2018 BMC
Medicine analysis, the 2017 Age and Ageing dementia paper and the 2018 Mayo Clinic Proceedings
review are genuinely his. **His name has become shorthand for sauna research, and that is where
it goes wrong.**

**Verified against PubMed, wrong attributions:**

| where | cited as | what the paper actually is |
|---|---|---|
| `chromotherapy…` (14 inline cites) and `nurecover-tropic…`, `sisu-sauna-review`, `sauna-benefits-detoxification`, `what-is-a-german-sauna` — **10 links to PMC5941775 across 5 articles** | "Laukkanen et al., 2018", and in one case "Mayo Clinic Proceedings" | **Hussain J & Cohen M**, *Evid Based Complement Alternat Med* 2018 (PMID 29849692). Laukkanen is not an author, and the journal is not Mayo Clinic Proceedings |
| `what-is-a-german-sauna` (23,587 impressions) | "Laukkanen et al. — sauna bathing, fitness, and mortality risk (**BMC Medicine**) 2018" → PMID 29551418 | *Progress in Cardiovascular Diseases*. Author right, **journal wrong** |
| `what-is-a-german-sauna` | "Laukkanen et al. — comprehensive review of Finnish sauna (**Mayo Clinic Proceedings**) 2024" → PMID 38577299 | *Temperature (Austin)*. Author right, **journal wrong** |
| `what-is-a-german-sauna` | "Laukkanen et al. — incident hypertension (Am J Hypertension) 2017" → PMID 28633297 | journal right; **first author is Zaccardi**, Laukkanen is fourth and sixth. Loose rather than wrong |
| `thermal-stress-hormetic-window…` | "Laukkanen JA, et al. Sauna bathing and systemic inflammation, *European Journal of Epidemiology*, 2018" | the LINK points at a **KLAFS press release**, a sauna manufacturer, not the paper |
| `dry-sauna-for-home` | a Laukkanen study "explained" | sourced to **saunasupplyco.com**, a retailer blog |

**And the Hussain & Cohen paper says the opposite of what it is cited for.** Its abstract:
*"the medical evidence to support these claims is not well established"*; 40 studies, 13
randomised, most under 40 participants. It is cited on our pages as **"Evidence: High for heat
benefits"**.

**Verdict: this is a pattern, not one bad article.** Five articles carry the wrong-author
citation, two carry wrong journals, two cite a vendor for a paper. `nurecover-tropic-home-sauna-review`
alone carries 59 mentions and 26 inline cites and has never been read.

**Proposed as its own pass, not folded into the chromotherapy rewrite:** read the five, correct
every citation against the source record, and re-check each claim against what that paper found.
Nothing changed yet.

### Two anchors fixed, 16 Sep 2026

`scripts/apply/fix-two-anchors.mjs`. `biophilic-design-measurable-outcomes-evidence`: link
REMOVED, sentence untouched, 1 → 0 links. `are-infrared-saunas-safe`: reworded to drop the steam
claim and the populations claim, 2 → 1 links (it had a stray empty anchor on a space character
as well). Both re-read after writing.

### CITATION PASS — scoped by defect type, 16 Sep 2026. Nothing fixed.

**PMC5941775 appears in 19 articles.** My earlier "5 articles, 10 links" was a count of links,
not of attributions, and the real breakdown has five distinct defects, not one.

**A. WRONG AUTHOR — "Laukkanen" on a paper by Hussain & Cohen**
`chromotherapy…` (2 links, **12 inline claim cites**) and `nurecover-tropic…` (3 links,
**24 inline claim cites**). nurecover also gives the wrong journal, "Mayo Clinic Proceedings".

**B. RIGHT PAPER NAMED, WRONG PAPER LINKED** — a new shape
`benefits-of-cold-plunge-and-sauna` (3 links) cites *"Laukkanen, J.A. et al. Cardiovascular and
Other Health Benefits of Sauna Bathing: A Review of the Evidence, Mayo Clinic Proceedings,
2018"* — which is a real Laukkanen paper, correctly named — **and points the URL at Hussain &
Cohen's paper instead.** Author right, title right, destination wrong.

**C. A DIFFERENT WRONG AUTHOR on the same paper**
`sauna-benefits-detoxification` (4 links) attributes PMC5941775 to *"Crinnion W., sauna/sweat
review, 2011"*. Wrong author and wrong year, and not the Laukkanen error at all.

**D. WRONG JOURNAL, right author** — `what-is-a-german-sauna` (**23,587 impressions**): PMID
29551418 given as *BMC Medicine* (it is *Progress in Cardiovascular Diseases*); PMID 38577299
given as *Mayo Clinic Proceedings* (it is *Temperature (Austin)*).

**E. VENDOR STANDING IN FOR A PAPER** — `thermal-stress-hormetic-window…` cites *Eur J
Epidemiology 2018* and links a **KLAFS press release**; `dry-sauna-for-home` sources a Laukkanen
study to **saunasupplyco.com**.

**F. LOOSE, leave it** — PMID 28633297 cited as "Laukkanen et al." where **Zaccardi** is first
author and Laukkanen is fourth and sixth. Conventional, imprecise, not wrong.

**G. CORRECT, and worth recording so the pass does not "fix" them** — `sisu-sauna-review`,
`what-is-a-german-sauna`, `downdraft-sauna-ventilation-design-patterns` and
`dynamic-saunas-monaco…` all name **Hussain & Cohen** properly. A further 11 articles cite the
paper by title or PMC id with no author named, which is thin but not false.

### The claims resting on the misattribution — several fail on their own terms

36 inline claim cites sit on "(Laukkanen et al., 2018)". Against what Hussain & Cohen actually
report — 40 studies, 13 randomised, most under 40 participants, *"the medical evidence to support
these claims is not well established"*, and explicitly *"further study is also needed to
determine the optimal frequency and duration"*:

| claim | verdict |
|---|---|
| "**Evidence: High** for heat benefits" | **CONTRADICTED.** The review says the opposite |
| "20–30 minute sessions, **one to four times per week**" · "typically 15–30 minutes" · "Most studies and wellness guides suggest moderate session lengths" | **CITED FOR THE THING THE PAPER SAYS IS UNKNOWN.** The review names optimal frequency and duration as an open question |
| "Core sauna health outcomes — reduced blood pressure, improved cardiovascular function — are driven by repeated heat exposure" | partially supported; the review reports most studies found beneficial effects, but heterogeneous and low quality. **NEEDS LIMITATION** |
| "reduced cardiovascular **events**" | **WRONG SOURCE** — that is the Kuopio cohorts, not this review |
| "Sauna therapy trials show **pain reductions**" | supported in kind, **NEEDS LIMITATION** |
| "Sauna heat has the strongest and most extensive evidence base" | defensible as comparative |

**So the fix is not a rename.** Roughly half of these claims change or lose their support once
the citation is corrected.

### ⚠ FLAG TO THE CLIENT NOW — two live pages disagree on frequency

`chromotherapy-vs-no-chromotherapy-buyers-guide` tells a reader **"one to four times weekly"**
and **"15–30 minutes"**, sourced to the misattributed review. `how-often-should-you-use-sauna`,
published today, says the only frequency that reached significance is **four to seven a week**,
and that sessions over 19 minutes carry the stronger duration association.

**A reader can see both today.** When the pass reaches chromotherapy, its frequency line defers
to the published article rather than restating a number.

### Order of work, and the one to be careful with

1. `chromotherapy…` — 12 claim cites, 6 ASSERTS, 2 NEEDS LIMITATION, the empty `Key Citations:`
   placeholders, the vendor-sourced IEC standards, and the frequency deferral.
2. `benefits-of-cold-plunge-and-sauna` — 3 URL swaps, claims likely unaffected.
3. `sauna-benefits-detoxification` — the Crinnion attribution, 7 claim cites.
4. `what-is-a-german-sauna` — 2 journal corrections on the estate's highest-impression page.
5. `nurecover-tropic-home-sauna-review` — **59 mentions, 24 claim cites, never read. A full read,
   not a citation swap**, and the last one for that reason.

Plus E: replace the KLAFS press release and the retailer blog with the papers, or drop the claims.

### Citation pass 1/5 — chromotherapy APPLIED 16 Sep 2026, and my enumeration undercounted TWICE

30 edits in three batches. Backups `2026-09-16T14-59-10-909Z`, `…15-00-02-603Z`, `…15-01-03-129Z`.

| batch | what | proposed | actual |
|---|---|---|---|
| 1 | asserts, doses, placeholders, source entry, attributions | 13 + 6 attributions | **20**, all matched once |
| 2 | vendor-sourced standards | **2** | **9** |
| 3 | a seventh ASSERT, the same claim restated elsewhere | **0** | **1** |

**Both misses are rules this file already carries, and I broke them in the same pass.**

1. **Vendor citations: I proposed 2 and there were 9.** I had counted `IEC 60335-2-53 ×5` and
   `IEC 62471 ×6` in the preflight and then wrote a proposal covering the two sentences I had
   read. **The count was on the screen and the proposal was written from memory of the reading.**
2. **The seventh ASSERT was the same claim in another place** — *"the proven cardiovascular,
   metabolic, and relaxation benefits that come from sauna heat exposure alone"*, a restatement
   of the anchor sentence in a later section. The figure-has-more-than-one-representation rule,
   arriving as a claim rather than a number.

**It was caught because the screen was re-run after the pass rather than trusted once.** That is
the whole value of re-running a measurement instead of reading back the write.

**Verified on the live page:** 0 `(Laukkanen et al., 2018)` cites, Hussain & Cohen named 20 times,
3 body links to the frequency article (the rendered page shows 5, the extra two are theme-rendered
related links), no frequency stated, no empty `Key Citations:` parens, no vendor cited for a
standard, 0 proof-language sentences about heat.

**Group G held.** `sisu-sauna-review`, `downdraft-sauna-ventilation-design-patterns` and
`dynamic-saunas-monaco…` are untouched, with their correct Hussain & Cohen citations intact and
their `updatedAt` unchanged. `what-is-a-german-sauna` shows today's date from the earlier ANCHOR
edit, not from this pass; its Hussain citation is intact.

**Left deliberately:** `Inner Light Sauna, 2024` still appears twice, cited for experiential
colour guidance and for a positioning statement rather than for a standard or a health claim.
That is a weak source, not a false authority. Logged, not changed.

### The shape to watch for in the other four

**An article can be careful about its own subject and careless about the thing it compares
against.** Chromotherapy's own claims were hedged, sourced and limited throughout, and the
contrast term — sauna heat — was treated as settled background: "proven", "Evidence: High",
a dose sourced to a paper that calls dose unknown.

**Check for it in the remaining four:** a review of one product that describes the alternative as
proven is the same defect with a different subject. `nurecover-tropic…` is the obvious candidate,
because its whole argument is a portable steam tent measured against traditional saunas.

### Citation pass 2/5 — `benefits-of-cold-plunge-and-sauna` ENUMERATED. 12 defects, not 3.

**My "3 URL swaps" was the third undercount of the day.** Resolving every link found four wrong
destinations, four dead external citations and four broken internal links. **A text-based read
would have reported this article clean** — every citation string is well formed, correctly
formatted, and names a real paper.

5,367 words, 19 unique links, all resolved 16 Sep 2026.

**VARIANT 7 — right citation, wrong destination (4)**

| cited as | the URL actually is |
|---|---|
| Bleakley C. et al., *Cold-water immersion (cryotherapy) for preventing and treating muscle soreness after exercise*, Cochrane Database, 2015 → PMID **25943635** | **a bacterial genetics paper**: *"A functionally critical single nucleotide polymorphism in the gene encoding the membrane-bound alcohol dehydrogenase found in ethanol oxidation-deficient Gluconobacter thailandicus"*, Gene, 2015 |
| Huttunen P. et al., *Winter swimming improves general well-being*, Eur J Appl Physiol, 2007 → PMID **17993252** | **Shevchuk NA, *Adapted cold shower as a potential treatment for depression*, Medical Hypotheses, 2007.** Wrong author, wrong title, wrong journal — and Medical Hypotheses publishes untested proposals, so it is also the wrong KIND of source |
| Laukkanen J.A. et al., *Cardiovascular and Other Health Benefits of Sauna Bathing*, Mayo Clinic Proceedings, 2018 → **PMC5941775** | Hussain & Cohen's review in a different journal. The named paper is real: **PMID 30077204** |
| Leeder J. et al., *Cold water immersion and recovery from strenuous exercise*, Sports Medicine, 2014 → **PMC4049052** | **Mooventhan A, Nivethitha L, *Scientific Evidence-Based Effects of Hydrotherapy on Various Systems of the Body*, North American Journal of Medical Sciences, 2014** |

**DEAD EXTERNAL CITATIONS (4)** — all 404: Cleveland Clinic contrast-bath, Harvard Health
*Are saunas safe*, CDC cold safety, BBC Future ice baths. Two more (jamanetwork, heart.org) return
403 to a scripted client and are bot walls rather than dead.

**BROKEN INTERNAL LINKS (4)** — `benefits-of-alternating-sauna-and-cold-plunge…` (404),
`cold-plunge-benefits-premium-wellness-equipment` (404), `10-biggest-benefits…` (301 to homepage),
`the-ultimate-recovery-routine…` (301 to homepage). All four are already in the broken-link
enumeration; this article is one of the 71.

**THE COMPARISON-TERM QUESTION: ANSWERED NO.** The shape found on chromotherapy is **not** present
here. All 10 proof-language sentences are refusals — *"has not been independently proven"*,
*"do not interpret this as proof"*, *"plausible but not proven"*, *"Myth: sauna and cold plunge are
proven to extend your lifespan"*. **This article is careful about both of its subjects.** Its
defect is purely in where the links land, which is exactly why variant 7 needed resolving rather
than reading.

Nothing proposed yet.

### Citation pass 2/5 — `benefits-of-cold-plunge-and-sauna` APPLIED 16 Sep 2026

11 edits. Backup `2026-09-16T15-23-07-632Z`. Re-read: all 12 assertions pass — every wrong
identifier gone, every correct one present, the figure and the unsupportable claim gone.

- **Group 1, four identifiers, each resolved through the PubMed API BEFORE being written:**
  Bleakley → PMID 22336838 (Cochrane **2012**, not 2015); Huttunen → PMID 15253480
  (*Int J Circumpolar Health* **2004**, not Eur J Appl Physiol 2007); Leeder → PMID 21947816
  (*Br J Sports Med*, a meta-analysis, not Sports Medicine 2014); Laukkanen Mayo → PMID 30077204.
  **Variant 7 was the visible half: three of the four were wrong in their TEXT as well.**
- **Group 2:** Harvard replaced with the live equivalent from the same publisher, CDC replaced
  with the live Winter Weather page (its 403 was a bot wall, not a death), BBC removed.
- **Šrámek:** the norepinephrine figure now reads 530%, head-out immersion, 14°C, one hour, young
  men, with the sentence that an hour at 14°C is not a two-minute plunge. Source added to the list.
- **Cleveland Clinic:** the diminishing-returns claim cut with its citation. The myth-correction
  structure survives — "the protocols that have been studied run to specific durations … longer
  exposures have not been tested" — which says the useful thing without asserting a consequence.

**TWO GUARDS FIRED AND BOTH WERE RIGHT.**

1. **Every source-list anchor failed to match.** The one-character anchors in this article contain
   **U+00A0, not U+0020**. Printing the code points found it in one command — the rule this file
   already carries. The from-strings are now built with ` `.
2. **The 200–300% figure appeared TWICE.** I fixed the body sentence; the TL;DR carried the same
   claim in different words. The guard refused the write. **This is the restatement rule I
   recorded four hours ago, broken in the next article I touched**, and caught only because the
   script asserts on the outcome rather than the edit.

### FOUR MISSES IN ONE SESSION, ALL MINE, ALL FROM READING MY OWN OUTPUT ONCE

| # | what | how it was caught |
|---|---|---|
| 1 | vendor-sourced standards: proposed 2, found 9 | re-read of the live body after applying |
| 2 | a seventh ASSERT, restated elsewhere | re-running the health-claim screen |
| 3 | "3 URL swaps" for item 2, actually 12 defects | resolving every link instead of reading them |
| 4 | "bibliography-only, nothing rests on these" — I split on "Sources" and hit the **table of contents** | reading the extracted block instead of trusting the split |

**The rule is in the file, it is the rule I quote most, and I broke it four times today while
applying it.** Every catch came from a mechanical re-measurement, never from care.

**PROPOSED, NOT BUILT — a structural check for the class.** A helper that refuses to return a
count derived from a string split without confirming what it split on: it takes the delimiter and
the expected context, asserts the split point is where the caller believes (e.g. that "Sources" is
inside an `<h2>` and is the LAST such occurrence), prints the byte offset and the 80 characters
either side, and throws when the document contains more than one candidate. Same shape as
`assertFresh` and `assertReach`: the guard exists because the discipline demonstrably does not
survive contact with a long session. To be designed properly before it is written.

### 🔴 THE SHUFFLED GENUIS SET — these citations were COMPOSED, not resolved

Item 3 carries three citations to one author's related BUS papers, **each pointing at a different
one of the others**, and the phthalate PMID is **one digit from the real BPA paper**:

| labelled | links to | actually is |
|---|---|---|
| Genuis, *BUS Study*, 2012 | PMC3312275 | Sears, Kerr & Bray, metals-in-sweat systematic review |
| "BPA in sweat, 2011" | PMID 21057782 | Genuis, BUS study of **toxic elements** |
| "Phthalates in sweat, 2012" | PMID 222536**38** | Hope & Hope, **Ochratoxin A and kidney disease** — the real BPA paper is 222536**37** |

**Nobody makes this mistake while reading the sources.** An off-by-one PMID next to two swapped
papers is what assembling a bibliography from memory or from a list looks like. **It explains the
pattern across all five articles better than any individual defect does:** these citations were
composed to look like citations, then attached to URLs afterwards.

**Which is exactly why resolving beats reading.** Every one of these strings is well formed, names a
real paper, and describes it correctly.

### A weak source that supports only claims a stronger source already carries is REDUNDANT

Crinnion, *Altern Med Rev* 2011, is a real paper by a real author, cited 8 times here. Four of those
are refusals already co-cited with Hussain & Cohen; one is a temperature range; one is co-cited with
Genuis. **Removing it strands nothing, and that is the test** — not whether the source is weak, but
whether anything depends on it. A defunct naturopathic journal adding nothing to four refusals is
not worth keeping for form. Dropped rather than corrected.

### Correcting a SOURCE ENTRY can break an inline tag elsewhere in the same article

Fixing Huttunen's source entry (Eur J Appl Physiol 2007 → Int J Circumpolar Health 2004) left a
sentence 2,000 words away reading *"[Cochrane Review, 2015; European Journal of Applied Physiology,
2007]"* — a tag pointing at an entry that no longer existed. **The guard refused the write; no
reading found it.**

**Practice: correcting a source entry requires checking every inline tag that references it, in the
same pass.** This is the one-thing-many-representations rule applied to the RELATIONSHIP rather than
to the thing — the bibliography and the in-text tag are two representations of one citation, and
editing either orphans the other.

### THREE GUARDS FIRED ACROSS TWO ARTICLES TODAY, AND ALL THREE CAUGHT WHAT READING MISSED

1. **U+00A0 vs U+0020** in the source-list anchors — every replacement failed to match. Diagnosed in
   one command by printing code points, because the failure mode is already documented. **Ninth in
   that series, and the cheapest: the early instances cost an afternoon each.**
2. **The 200–300% figure restated in the TL;DR** — the outcome assertion refused the write.
3. **The orphaned Cochrane co-citation** — the stale-tag assertion refused the write.

**Against four misses of mine in the same session, all from reading my own output once.** That is
the argument for building the split-assertion helper rather than writing another rule: the rules
were all present and quoted, and the guards are what actually held.

### Citation pass 3/5 — `sauna-benefits-detoxification` APPLIED 16 Sep 2026

14 edits (13 targets + the BPA entry that never existed), backup `2026-09-16T15-40-15-371Z`,
all 13 re-read assertions pass. The shuffled Genuis set is unshuffled: metals → PMID 21057782,
BPA → 22253637, phthalates → 23213291, and PMC3312275 restored to Sears, Kerr & Bray. Crinnion
dropped (8 in-text tags rewritten to their existing co-citations, 0 mentions left). Two types
corrected. Cleveland Clinic and Mayo replaced with live equivalents; Mayo's detox page removed
because Mayo no longer publishes one.

**A guard refused again mid-pass:** a THIRD "PubMed, 2012" label existed in a sentence I had not
mapped. The pre-write check caught it. Three articles, four guard refusals, zero bad writes.

### 🔴 DATABASE-AS-SOURCE IS THE HOUSE STYLE — 59 of 120 articles, 1,543 instances

Scoped across the estate before anyone decides:

| | |
|---|---|
| articles using "(PMC, 2021)", "(PubMed, 2008)", "(NCBI, 2023)" as a citation | **59 of 120** |
| total instances | **1,543** |
| articles with 20+ | **29** |
| worst | `heat-shock-proteins-neurodegeneration-cognitive-aging` **170**, `heat-cold-pain-modulation` 102, `float-therapy-vs-cryotherapy` 89 |

**And this is the same phenomenon as the shuffled bibliography, seen twice.** A citation style that
names a database rather than an author **is a style you can write without a specific paper in
mind**. "(NCBI, 2023)" attaches to any claim; "Genuis et al., *Blood, Urine and Sweat Study*, 2012"
cannot. **The style made the shuffle possible and made it invisible** — nothing in
"(PubMed, 2011; PubMed, 2012)" tells a reader, or a checker, which papers those are.

**This is a round, not a task.** 1,543 instances, and each one has to be resolved to a real paper
before it can be named — which is the same work as the citation pass, across half the estate. The
client should see the number before it is scheduled.

### GUARD BUILT: `assertSplitPoint` — and it reproduces its founding failure

`scripts/lib/split-assert.mjs`, proved by `scripts/audit/split-assert-selftest.mjs`.

**The founding failure, reproduced on the live article:** splitting `sauna-benefits-detoxification`
on the bare string "Sources" lands at character **1,905** — its table-of-contents entry. The
heading is at **26,285**. My split was **24,380 characters early**, which is why the body looked
free of inline citations and I reported that nothing depended on four dead sources.

The guard refuses an ambiguous split, refuses a context that matches nothing rather than falling
back, refuses an absent delimiter, and accepts ambiguity only when the caller says `pick:'last'`.
It prints the offset and the surrounding text on every call. 9 constructed checks plus the live
case; fixtures are constructed so repairing the estate cannot break the test.

**Written for the same reason as `assertFresh` and `assertReach`: four instances in one session of
the rule being broken by the person quoting it.** A rule its own author breaks four times while
applying it is not a behavioural fix.

### Citation pass 4/5 — `what-is-a-german-sauna` APPLIED 16 Sep 2026

Four bibliography corrections, all matched once, all six re-read checks pass. Backup
`2026-09-16T15-45-29-771Z`. 29551418 → *Prog Cardiovasc Dis*; 38577299 → *Temperature*;
31102597 → Laukkanen & Kunutsor, **a review** not a meta-analysis; 37650138 → **Debray et al.**,
not "Mero et al.".

**MY ESCALATION WAS WRONG AND IT IS RECORDED AS MINE.** I called the Debray citation the most
serious in the project and scoped it as a possible rewrite — before reading the sentence. The
sentence uses the null trial correctly, as a counterpoint restraining the article's own topic. The
fix was a name. Recorded in CLAUDE.md: **a metadata mismatch ranks what to read, not what is wrong.**

**THE NEW GUARD CAUGHT ME ON ITS FIRST PRODUCTION USE.** Checking whether the Debray claim was
restated elsewhere, I split this article on "Sources" — the same mistake as this morning. The guard
refused: 2 candidates. Asserted with context, the heading is at **48,442**; my naive split would
have been at **1,905**. **46,537 characters off**, and the Debray sentence sits inside the closing
section, which is exactly why a naive body-only count showed zero mentions.

A guard written an hour earlier, against a failure from that morning, reproducing its founding case
in production rather than in its test.

### THE STYLE PREDICTS THE FAILURE MODE — useful for the 59 unread articles

| citation style | where the errors are |
|---|---|
| **names authors** (`what-is-a-german-sauna`: 25 links, all resolve, 0 dead, 0 database labels) | **attribution errors** — wrong journal, reversed authors, inflated study type. The links are right; the labels are wrong |
| **names databases** (`sauna-benefits-detoxification`: 40 labels; `benefits-of-cold-plunge-and-sauna`) | **bibliography errors** — shuffled papers, wrong destinations, off-by-one PMIDs. The labels cannot be checked, so the links drift |

**This predicts what the 59 articles carrying 1,543 database labels contain before anyone opens
them:** not sloppy journal names, but citations whose links may point anywhere, because
"(PMC, 2021)" gives a checker nothing to verify against. It also says where to start — the 29
articles with 20+ labels.

### Citation pass 5/5 — `nurecover-tropic-home-sauna-review` APPLIED 16 Sep 2026

Backup `2026-09-16T16-09-18-547Z`. Dry run and apply identical, 14/14 pre-write and 14/14 re-read.

| | |
|---|---|
| competitor names stripped from a paren with other sources | 28 |
| sole-source parens re-sourced to our MX-S106-01 listing | 18 |
| sole-source parens dropped (not a specification) | 4 |
| bibliography entries removed | 3 |
| inline `Laukkanen et al., 2018` → `Hussain & Cohen, 2018` | 58 |

**Measured after, not read back:** 20 hrefs, 9 distinct sources, **zero competitor links**, 5 hrefs
to `/products/maxxus-mx-s106-01`.

**THE CONVERGENCE IS THE FINDING UNDER THE COMMERCIAL ONE.** The client's price ruling (remove a
competitor at or below our price) and the spec test (replace a competitor cited for a spec we
publish) send all three the same way — because **not one specification in that article is published
only by a competitor.** Our listing carries every one and several more precisely:

| the article cited a competitor for | our listing |
|---|---|
| "low-EMF carbon panels" | panels specified **5–10 mG at 2–3 inches** — on no competitor cite |
| "often sold with multi-year warranty" | **5-year limited, named parts, indoor-only** |
| "typically cost several thousand dollars" | the live price, on the page |

**So the article cited competitors for specs we document better.** Four parens were dropped rather
than re-sourced — buyer guidance, psychology and a generic manual instruction that a retail product
page never supported and our listing cannot either.

**STILL OUTSTANDING and deliberately out of this pass:** the ~12 cites Hussain & Cohen cannot
carry — dementia, all-cause mortality, dose-response. Renaming the entry did not make them right.

### ESTATE-WIDE RETAILER CITATIONS — the URL-shape proxy was wrong, the outcome test is right

First sweep matched paths (`/products/`, `/shop/`, `/collections/`) and returned 29 across 13
articles. **It missed `zogics.com`, whose path is `/facility/spa-sauna-equipment/`** — a probe
encoding our idea of what a shop URL looks like. Replaced with an OUTCOME test: a page is a retail
listing if it carries Product/Offer schema or an `og:price`. **496 URLs checked, 30 listings across
9 articles.**

**At or below our price, SKU-matched with dashes AND spaces removed — 6 links, 2 articles:**

| article | competitor | theirs | ours | |
|---|---|---|---|---|
| `dynamic-venice-sauna-review` | dynamicsaunasdirect | $2,299 | $2,499 | **UNDERCUTS $200** |
| `dynamic-venice-sauna-review` | sunvalleysaunas | $2,299 | $2,499 | **UNDERCUTS $200** |
| `dynamic-venice-sauna-review` | strengthwellnesssupply | $2,299 | $2,499 | **UNDERCUTS $200** |
| `dynamic-venice-sauna-review` | skywardmedical | $2,699 | $2,699 | MATCHED |
| `dynamic-venice-sauna-review` | sunflaresaunas | $2,699 | $2,699 | MATCHED |
| `nurecover-tropic…` | havenofheat | $2,299 | $2,299 | MATCHED — **removed** |

⚠️ **Two of my own errors, both caught by their own output.** I retyped five URLs from a truncated
display and got five false 404s — identifiers come from the DATA. And the two MATCHED Venice rows
were reported to the client as "above our price" because I compared an **Elite** SKU against the
plain product. Corrected before it reached a proposal.

⚠️ **The outcome test catches EDITORIAL pages with price widgets** — `businessinsider.com`,
`cnn.com`, `garagegymreviews.com`, `insidehook.com`. Those are not competitors and must not be
treated as such by whoever runs this next.

### `dynamic-venice-sauna-review` APPLIED 16 Sep 2026 — DE-LINK, NOT DE-CITE

Backup `2026-09-16T16-38-42-950Z`. Dry run and apply identical, 15/15 both sides.

**43 inline competitor citations, not 41** — the guard's count found two in *"What We Still Don't
Know"*, past the Sources heading, that my body-only enumeration had missed.

| | |
|---|---|
| kept — a competitor cited AS a competitor | **25** |
| re-sourced to our DYN-6210-01 listing | 13 |
| dropped — guidance no source supports | 5 |
| Sources entries de-linked (name kept) | **7 of 7** |

External hrefs 18, all research and health sources. **Zero competitor links.**

**Two separator characters in one article.** The citation separator is U+0020 in most places and
**U+00A0** in others, and `120V/15A connection` carries one mid-phrase. Four context
assertions failed until the class was rebuilt from code points — the cold-plunge anchor failure
arriving again, in a different article, three weeks later.

### REMAINING FROM THE 30-LISTING SWEEP — 7 articles, 20 listings, unhandled

`dynamic-santiago-ultra-low-emf-sauna-sources` (6) · `homedics-premium-steam-sauna-review` (5) ·
`sisu-sauna-review` (3) · `dynamic-saunas-review` (2) · `top-fire-pits-outdoor-meditation` (2) ·
`golden-designs-osla-edition-review` (1) · `red-light-collagen` (1).

Each needs the same price check and the same per-citation ruling. **Not a bulk job:** Venice and
nurecover needed opposite treatments, and the difference was only visible on a full read.

### STILL OPEN — the ~12 nurecover cites Hussain & Cohen cannot carry

Dementia, all-cause mortality and dose-response are cited to a systematic review of 40 intervention
studies that contains none of them and names the dose as an open question. **Correcting the
bibliography entry did not make those claims right**, and the close report must not imply it did.

### THE THREE GOLDEN DESIGNS DE-LINKS — NOT APPLIED. Both premises failed enumeration.

Instructed 16 Sep 2026 to apply "the same treatment, same reasoning" to three links. Enumerating
first — the standing rule — killed both halves of the premise before anything was written.

**1. `dynamic-santiago-ultra-low-emf-sauna-sources` is UNPUBLISHED.** `isPublished: false`,
`publishedAt: null`, blog `institute`, title **"A) Manus Alignment Snapshot"** — an AI
research-tool working dump, 94,749 characters, not a customer-facing article. **30 goldendesign
hrefs, not 1**; my estate sweep counted DISTINCT URLs and collapsed 30 to 2.

**No reader can reach it, so there is no commercial exposure to fix.** Same shape as the
`dry-sauna-for-home` rewrite: check publication state before diagnosing anything, because it is one
field and it invalidates every other reading.

**2. Golden Designs Inc. is the MANUFACTURER, not a competing retailer.** Our own warranty metafield
says so: *"5 Year Limited Warranty: Golden Designs, Inc. under the Dynamic brand name warranties the
wood, structure, heating elements, and electronics."* Maxxus is *"by Golden Designs"*.

`dynamic-saunas-review` carries **4 links, not 2**, all inside a block headed **"Manufacturer
specifications"** and **"Warranty documentation"**, under *"Sources and verification"*, which states
the review was built from *"Golden Designs product documentation (**the controlling source for
specifications**)"*. Anchor text: *"Golden Designs **manufacturer site** and model specifications"*.
All four carry `rel="nofollow noopener noreferrer"`. The article already discloses that InHouse
Wellness is an authorized Dynamic dealer. One link is the **factory warranty page** — the primary
source for the warranty finding that is the strongest material this project owns.

**And the spec test comes back the other way here.** For Venice and the MX-S106-01 our listings
carry interior dimensions, panel counts, electrical and mG figures. For DYN-6106-01 and DYN-6336-02
our metafields carry **marketing prose** — *"perfect for smaller spaces"*, *"ultimate relaxation"* —
and no dimensional or electrical detail. **The manufacturer publishes specs we do not.** That is the
client's own stated exception: a source cited for something only they publish is a different case.

Direct-sale prices are $3,999 and $6,999 against our $2,299 and $3,499 — **we are 42–50% cheaper**,
so the ruling's mechanism (a seller at or below our price takes the sale) does not engage either.

**Nothing applied. This is a client decision, and it is a different decision from Venice.**

### MERCHANDISING QUESTION FOR THE CLIENT — the Santiago variant gap

Five retailers sell **DYN-6209-02 and DYN-6209-02 Elite**. We stock **DYN-6209-01** ($2,299) and
**DYN-6209-03 FS** ($3,299). **Is the -02 a variant we should carry, or one we deliberately do not?**
If deliberate, the review should say why rather than covering it neutrally. Currently moot for
readers — the page carrying it is unpublished — but it decides what that page becomes if published.

### LOGGED WITH ITS TRIGGER — the Osla comparison

`golden-designs-osla-edition-review` links goldendesigninc at **$9,999** against our
`golden-6-person-sauna` at **$8,499, which is DRAFT**. A live competitor against a draft product is
not a comparison. **TRIGGER: it becomes one the day that product republishes** — and a republish is
normal operation on the volatile vendors. Watch the outcome (the product going ACTIVE), not the
action, because nobody republishing a product will read this file.

### THE THREE-ROW TABLE, with the estate figure on the row that predicts most

**The most transferable thing the citation pass produced.** A style that names databases cannot be
checked by reading, so its links drift unobserved. A style that names authors can be checked, so its
errors land in the labels instead.

| citation style | what a reader can check | where the errors are | estate scope |
|---|---|---|---|
| **names authors** | the attribution, by resolving it | **attribution errors** — wrong journal, reversed authors, inflated study type. Links right, labels wrong | `what-is-a-german-sauna`: 25 links, all resolve, 0 dead |
| **names databases** | **nothing** — "(PMC, 2021)" gives a checker no purchase | **bibliography errors** — shuffled papers, wrong destinations, off-by-one PMIDs | **59 of 120 articles, 1,543 instances.** 29 carry 20+ |
| **names retailers** | the source class, legibly | **commercial errors** — sourcing readable, pointing at people who take the sale | closed: Venice + nurecover were the whole of it |

**The middle row predicts what half the estate contains before anyone opens it:** not sloppy journal
names, but citations whose links may point anywhere, because the label gives a checker nothing to
verify against. Start with the 29 articles carrying 20+ labels. Still a client decision.

### CITATION PASS CLOSED 16 Sep 2026

Five articles plus `dynamic-venice-sauna-review`. 59 edits across items 1–4, a full pass on
nurecover, a de-link pass on Venice. **Four articles left untouched on enumeration** — three Golden
Designs links whose premise failed, and one unpublished working file.

**The clean result, and it is the first of its kind here: the sweep came back SMALLER than the first
article suggested.** 30 retail listings across 9 articles; 17 of the 20 remaining are manufacturers,
non-catalogue products, out-of-scope categories or editorial pages. The commercial exposure was real,
bounded, and is closed.

**Open, carried forward, not implied fixed:** the ~12 nurecover cites Hussain & Cohen cannot carry
(dementia, all-cause mortality, dose-response) — **reattributed is not corrected**. The Santiago -02
variant gap, as a stocking question. The Osla comparison, triggered on that draft republishing. The
two Dynamic listings the manufacturer documents better than we do.

## DATABASE-LABEL ROUND — SHAPE ENUMERATED 16 Sep 2026, nothing touched

### The recorded figure could not be reproduced, and the reason is in this file

| | recorded | re-derived |
|---|---|---|
| articles with database labels | 59 | **53** |
| label occurrences | 1,543 | **1,485** |
| articles with 20+ | 29 | **26** |

Four pattern variants were tried; **none produces 59 / 1,543 / 29.** The original entry recorded a
count **without its pattern**, so the number was never re-derivable — which is rule 6c, *a count is
population + pattern + source and all three travel with it*, broken by an entry in the same file.
`scripts/audit/db-label-shape.mjs` now carries its pattern and 10 constructed fixtures that fail the
run rather than warning.

### Answers to the four questions that decide the size

**1. How many distinct papers?** 136 distinct scholarly URLs across the 26 articles, from 228 href
occurrences — **46 PMIDs, 68 PMC ids, 21 publisher pages with no identifier in the URL.**

**2. How many resolve to something other than what they claim? ZERO so far.** All **46 PMIDs were
resolved through the PubMed API** and every one is a real paper on the subject of the article citing
it. **No shuffle of the Genuis kind exists in the PMID set.**

**3. Is PMC5941775 in more than the five already found? Yes — 18 articles.** And the verdict is the
good one:

| | |
|---|---|
| **MISATTRIBUTED** (says Laukkanen or Mayo Clinic Proceedings) | **0** — the citation pass cleared them |
| correctly attributed to Hussain & Cohen | 2 |
| **cited by title or as "(PMC, 2018)" with no author named** | **16** |

**Sixteen thin citations, none false.** Rule 5 of the method binds: *do not normalise correct
citations.* Naming the authors would be an improvement, not a correction, and it is optional work.

**4. Do any others appear shuffled? No — and the link graph says why.** Only **13 of 136 URLs appear
in more than one article.** 123 are unique to a single article. **These are 26 independently
composed bibliographies, not one bibliography pasted 26 times** — so the round is 26 reads, not one
fix applied 26 times. That is the answer to the sizing question, and it is the expensive one.

### The finding the enumeration did produce — four articles cite nothing resolvable

| labels | scholarly links | article |
|---|---|---|
| **170** | **0** | `heat-shock-proteins-neurodegeneration-cognitive-aging` |
| 83 | 0 | `sauna-for-autoimmune-condition-symptom-relief` |
| 63 | 0 | `biohacking-tools-inflammation-reduction` |
| 25 | 0 | `sauna-wood-species-wet-heat-durability-off-gassing-maintenance` |

**170 database labels and not one resolvable link.** There is nothing to resolve: the citations point
at an institution, not a paper. This is not the shuffled-bibliography failure mode the three-row
table predicted — **it is worse and cheaper to describe.** A shuffled bibliography is wrong and
fixable; this is **unverifiable in principle**, and no amount of link-resolving will touch it. These
four need a decision about what the citations are FOR before anyone edits a word.

### ⚠️ What this enumeration has NOT established

**The 68 PMC ids have not been metadata-matched**, and **no sentence has been read.** Variants 5 and
6 — a null result cited as support, a source cited for the thing it says is unknown — are invisible
to everything done here, and both were found in the last pass only by reading the claim beside the
abstract. **The clean PMID result means the LINKS point at real papers. It says nothing yet about
whether the sentences are true.**

### UNVERIFIABLE 1 of 4 — `heat-shock-proteins-neurodegeneration-cognitive-aging` READ. Outcome 1.

7,346 words, published, 170 labels, **20 hrefs of which 17 are table-of-contents anchors.** Three
real links: `healthresearchdatabase.com`, one internal article, one collection. **Zero scholarly
links in a 7,346-word article on neurodegeneration.**

**But the labels are NOT unfalsifiable.** The Sources section names **10 real sources with PMC ids**,
and the inline "(PMC, 2019)" form is a KEY INTO THAT LIST. All 7 PMC ids were resolved through the
NCBI converter and then PubMed: **every one is a real paper on exactly the right subject.** This is
outcome 1 — real claims, real sources, never linked.

**RULE 4: CLEAN, and better than clean.** The corrected screen finds 13 unhedged effect sentences of
51, and reading them, all are molecular-mechanism definitions, a quoted myth followed by
*Correction:*, or an explicit disclaimer. **Not one asserts a benefit to the reader.** The article
carries the preclinical limitation paragraph almost verbatim from this file's own example, routes to
`healthresearchdatabase.com`, and its myth section corrects *"Sauna use has been proven to prevent
dementia by activating heat shock proteins."* **The article the round most feared is the most careful
one in it.**

⚠️ **My first claim scan said 36 bare sentences. The real number is 13.** `\bmodel\b` does not match
"models", `\banimal\b` does not match "animals". **The match-the-noun-not-the-compound rule, in my own
screen, on the run that would have reported a fabricated rule-4 exposure on a neurodegeneration page.**

**The four real defects, all in the KEY rather than the claims:**

| | |
|---|---|
| **"(PMC, 2005)" is a 2016 paper** | *Stressing Out Hsp90 in Neurotoxic Proteinopathies*, Curr Top Med Chem, **2016** (PMC4995127). Used as 9 parens / 16 tokens. **An 11-year error in the citation key itself** |
| **"(PMC, 2025)" is AMBIGUOUS** | two 2025 PMC sources — PMC11832498 (Front Neurosci, hyperthermia) and PMC11864251 (J Alzheimers Dis Rep, HSP70 in AD). Used 26×. **A reader cannot tell which paper a claim rests on** |
| **a PODCAST cited 9×** | "Psychiatry & Psychotherapy Podcast, 2024", labelled *"Educational Review"*, on a neurodegeneration page |
| **"(PMC, 2023)" is a MOUSE study** | PMC10794279 is wild-type and Ames Dwarf **mice**; the sentence says *"exceptional agers maintain more robust HSP induction"*, which reads human. **Variant 3, wrong population** |

Plus: the Parkinson's entry shortens *"reduces α-synuclein-induced **predegenerative neuronal
dystrophy**"* to *"reduces α-synuclein-induced **toxicity**"* — and that paper explicitly found early
dystrophy **without** overt nigrostriatal neurodegeneration. Variant 4, added by subtraction.

**The fix is small and high-value: link the 10 sources, disambiguate the two 2025 keys, correct 2005
to 2016, name the mouse population, restore the Parkinson's qualifier, and reclassify the podcast.**
Nothing here is a rewrite and nothing is an unpublish.

### 🔴 THE MOST SERIOUS CLAIM DEFECT THIS PROJECT HAS FOUND — and a guard stopped the apply

`heat-shock-proteins-neurodegeneration-cognitive-aging`. **Nothing was written.** The pre-write
check asserted that the phrase "exceptional agers maintain" was gone after the population fix. It
was not: the phrase has **6 representations**, and chasing the others exposed the real defect.

**The article says:**

> *"A 2023 study examining **human postmortem brain tissue** found that normal aging is associated
> with impaired activation of the heat shock axis... **Older adult brains** showed unfavorable
> changes in HSF1 protein levels, DNA binding capacity, and phosphorylation patterns compared to
> younger individuals. In contrast, brains from **'exceptional agers' — older adults who maintained
> superior cognitive function** — showed preserved HSF1 activation signatures more similar to
> younger brains (PMC, 2023)."*

**According to PubMed, PMC10794279 / PMID 37707683 is Trivedi, Knopf, Rakoczy, Manocha, Brown-Borg &
Jurivich, "Disrupted HSF1 regulation in normal and exceptional brain aging", *Biogerontology* 2023.
It assessed "brain stress responses with normally aged wild type and long-lived Dwarf mice."** MeSH
terms: **Mice, Animals.**

| the article asserts | the paper has |
|---|---|
| human postmortem brain tissue | **mouse brain** |
| older adults | **wild-type and Ames Dwarf mice** |
| "exceptional agers … superior cognitive function" | **a genetic longevity model; no cognition measure** |

**This is not a mislabelled citation. The study design, the population and the outcome measure are
all invented**, and no other source in the article's list is a human HSF1-aging study. It is worse
than the Debray case, which was a name in a bibliography — here the SENTENCE is false, on the
estate's neurodegeneration page, and a reader has no way to check it because the citation names a
database.

**Six representations**, which is why a one-sentence fix would have been the partial-match failure:
the glossary entry, the comparison-table row ("Declines with aging; preserved in exceptional
agers"), the body paragraph, the consequence sentence after it, a myth correction, and a key
takeaway.

**Why the enumeration did not catch it and the guard did.** The metadata matched: right subject,
right year, real paper, correct journal. Every check in the citation pass would have passed it.
**Only reading the claim beside the abstract finds a fabricated study design** — variant 3 at full
strength, and the reason the method's rule 4 says to check what a paper actually FOUND.

**This article now needs a claim decision, not a source fix.** The other five fixes are still right
and still ready; they are held because shipping them would leave a corrected bibliography under a
false paragraph, which reads as verified.

### APPLIED 16 Sep 2026 — all six together. Backup `2026-09-16T17-14-40-305Z`

Dry run and apply identical, **18/18 both sides.** 10 source entries linked and attributed from
PubMed metadata · 16 inline `PMC, 2005` → `2016` · 9 PMC links · the podcast reclassified · the
Parkinson's qualifier restored · **all six claim representations rewritten to the mouse study.**

Verified absent on re-read: `exceptional ager` (0), `human postmortem brain tissue` (0),
`older adults who maintained superior cognitive function` (0), `PMC, 2005` (0).

**Held back and reported as a decision, not guessed:** `(PMC, 2025)` keys two different 2025 papers
across 42 occurrences and **17 cannot be assigned by topic.** Either the two papers get distinct
keys and someone reads all 42, or the citations stay ambiguous. **A wrong key is worse than an
ambiguous one**, so nothing was changed.

## THE OTHER THREE "UNVERIFIABLE" ARTICLES — READ. None was unverifiable.

### ⚠️ FIRST, A CORRECTION TO MY OWN SHAPE REPORT

I reported **"4 articles with 20+ labels and ZERO scholarly links"** and called them *"unverifiable in
principle"*. **The probe counted `href` attributes.** Three of the four carry their identifiers as
**plain text** in the Sources list:

| article | hrefs | bare identifiers |
|---|---|---|
| `heat-shock-proteins-neurodegeneration…` | 0 | **10 PMC ids** |
| `sauna-for-autoimmune…` | 0 | **17 full PubMed/PMC URLs** |
| `biohacking-tools-inflammation-reduction` | 0 | **13 identifiers**, written without the `https://` prefix |
| `sauna-wood-species…` | 0 | **18 full URLs** |

**Not one of the four was unverifiable. All four key to named sources with resolvable identifiers.**
They are unclickable, which is a usability defect, and I reported it as an evidence defect.

**A link-based probe measures linking. It cannot measure verifiability**, and calling the gap
"unverifiable in principle" was the strongest claim in the shape report and the wrong one. Same
family as counting hrefs and reporting citations: **the unit was wrong, not the number.**

### `sauna-for-autoimmune-condition-symptom-relief` — 83 labels. CLEAN on the species question.

All 14 PMIDs resolved through PubMed. **Every one is a human study** — MeSH "Humans" on all of them:
RA/AS infrared pilot (18685882), Waon therapy for fibromyalgia (18703857), the sham-controlled
whole-body hyperthermia RCT (37109279), MS heat-sensitivity work (21352533, 21914688), the KIHD
inflammation cohorts (29209938, 29897261). **A claim domain about people, resting on studies about
people.** Its "What We Still Don't Know" names its own limits: *"The RA/AS pilot ran 4 weeks."*

**One defect, and it is variant 4 by substitution.** The source list renders PMID 40202605 as
*"Sauna therapy in rheumatic diseases: mechanisms, potential benefits, and **therapeutic
perspectives**"*. The real subtitle is *"...and **cautions**"*. **The paper's own warning framing was
replaced with a promotional one** — nothing added, one word swapped, and the reader loses the signal
the authors chose to send.

### `biohacking-tools-inflammation-reduction` — 63 labels. CAREFUL, with one species omission.

All 10 PMIDs resolve and are on-subject. The article is unusually disciplined: it reports pooled n
(*"166 (pain) and 212 (long-term function) participants — modest by clinical-trial standards"*),
carries a *"Myth: Red light therapy is universally effective for inflammation"* section, and on the
PEMF stroke work says **"an animal stroke model… but animal findings shouldn't be generalized
directly to consumer use."** Its source list labels that entry **"(animal model)"** unprompted.

**The defect is the OTHER mouse study.** PMID 31136885 is *"Photobiomodulation therapy reduces acute
pain and inflammation **in mice**"*. The source list prints the title **with "in mice" removed**, and
the body says *"A separate study found pain reduction and inflammatory modulation from
photobiomodulation"* — **no species anywhere.** The article flags one animal source and silently
drops the species from the other.

And **"(PubMed, 2019)" is ambiguous** — two 2019 sources, one the mouse study, one a human-and-animal
review. Same key collision as `(PMC, 2025)`.

### `sauna-wood-species-wet-heat-durability` — 25 labels. Not a health problem. A COMMERCIAL one.

Right call to treat it separately: its claims are materials claims, honestly attributed
(*"Vendor guidance commonly estimates"*, *"Industry guidance commonly suggests"*), and its
"What We Still Don't Know" states plainly that vendor lifespan figures *"are not drawn from
standardized testing"*. USDA Forest Products Laboratory is cited 23 times and is the right authority.
**The coverage test passes: 3 ranged numeric claims, all attributed to their source class.**

**But six of its eighteen sources are sauna vendors, and one is HAVEN OF HEAT** — the competitor we
de-linked from `nurecover` this morning for being price-matched to us on the MX-S106-01. It is cited
**7 times**, including for the headline lifespan answer. `peakprimalwellness.com` is cited **10
times — the most-cited source in the article.** Plus `prosaunas.com`, `edenhut.co.uk`,
`hightechhealth.com`, and a Reddit thread.

**The de-link ruling applies here and nobody would have found it from this round's brief**, because
the round was scoped on citation labels and this is the commercial exposure wearing a citation's
clothes. Also: the URLs are bare text, so they are not live links today — **which means this is
cheaper to fix here than it was on Venice.**

⚠️ **Note the citation form: this article uses SQUARE brackets** `[Peak Primal Wellness, 2026]`. The
Sun Home sweep missed square brackets once already. `db-label-shape.mjs` matched on database+year
without requiring a bracket type, so it caught them — but any follow-up pattern must not assume `(`.

### APPLIED — the two title fixes. Backups `2026-09-16T17-22-37-158Z`, `…-579Z`. 7/7 both sides.

`sauna-for-autoimmune`: subtitle restored to **"…and cautions"** with the authors and journal named.
`biohacking-tools`: **"in mice"** restored to the source title, marked **Animal study**, and the body
sentence now opens *"A separate study in mice found…"* with the consumer-device limit stated.

**Reported, not guessed, per the standing ruling:** `(PubMed, 2019)` on biohacking and `(PMC, 2025)`
on the HSF1 article each key two different papers. Assigning occurrences would be a guess.

### 🔴 FOR THE CLIENT — `sauna-wood-species` is sourced on a major competitor's authority

**31 of the article's citation brackets name a sauna vendor.** `peakprimalwellness.com` is cited
**10 times — more than any other source in the article.** `havenofheat.com` **7 times**, including
the headline FAQ answer *"How long does sauna wood last?"*. Then Pro Saunas 7, Eden Hut 6, High Tech
Health 5, and one Reddit thread.

**Peak Primal is one of the two competitors this project has measured itself against all along** —
tens of thousands of referring domains against our 67. **An article whose most-cited source is a
major competitor is sourced on their authority**, and that is a stronger version of the Venice
problem than Venice was, because Venice cited competitors for specs while this cites one for the
article's central question.

**What the vendor citations actually support, and whether we already have a better source:**

| what it supports | count | covered by |
|---|---|---|
| **wood science** — decay resistance, shrinkage, hygroscopicity, thermal-modification mechanism | ~11 | **YES — USDA Forest Products Laboratory (cited 23×) and BioResources, both already in the article, several in the same bracket.** Redundant, the Crinnion shape |
| **odour and comfort** — cedar aroma, hemlock neutrality, aspen skin contact | ~8 | **No published authority.** Genuinely experiential |
| **maintenance practice** — dry-out habits, cleaning, inspection | ~4 | No published authority; ordinary category knowledge |
| **service life in years** — *"10–30 years"*, *"comparable to or exceeding cedar"* | ~8 | **No.** USDA Chapter 14 covers biodeterioration, not sauna service life. The article already labels these *"industry guidance"* and its own limits section says they are *"not drawn from standardized testing"* |

**So the ruling splits, and it is the Venice ruling again:** the ~11 wood-science citations are
**redundant and should be dropped in favour of the USDA source already cited beside them.** The
service-life, odour and maintenance citations are vendors cited **AS industry guidance, which is
what they are** — those keep the name and lose the link, exactly as on Venice.

**And our own catalogue covers part of it.** `custom.wood` is populated on **179 of 672 products**
— Hemlock 112, Cedar 51, Spruce 12, Thermowood 4 — and 110 products name Canadian Hemlock in their
copy. **We can source "which woods are actually sold in home saunas" from our own shelves**, which
no competitor blog can match and which is the positioning exactly.

**Cheaper than Venice: the URLs are bare text, so no link is live today.** The count is the
exposure, not the hyperlinks.

### APPLIED — `sauna-wood-species`, the Venice split. Backup `2026-09-16T17-28-12-377Z`. 12/12 both sides.

**12 dropped** as redundant — re-pointed to the USDA Forest Products Laboratory, the USDA Wood
Handbook or BioResources, all of which were already cited on the page and several in the same
bracket. **18 kept** as vendors cited AS industry guidance or for experiential claims no published
authority covers. **6 competitor URLs removed**, names retained: *"Sauna retailer guidance; link
withheld."*

**The Reddit thread keeps its link**, because it is cited as a user report and labelled as one —
the seller-as-seller case exactly.

**Added, and it is the better find:** *"Of the 672 products in the InHouse Wellness catalogue,
**179 publish a wood species**, and among those 179 the split is **Hemlock 112, Cedar 51, Spruce 12,
Thermowood 4**. That is a distribution across the products that name a species — not across the
whole catalogue, and not across the market."* Coverage rule applied in the sentence: the population
is stated, and the claim does not reach past it. **No competitor blog can produce this number.**

⚠️ **The guard caught my count again: I reported 31 vendor brackets, the script saw 30.** My hand
enumeration included `[Reddit, 2022; PubMed, 2009]` because I had put Reddit in the vendor list for
that run and not for this one. **A count that does not move is the signal** — and the misalignment
would have shifted every decision after position 11 onto the wrong bracket. Caught by the context
assertions, not by re-reading.

## THE HIGHEST-TRAFFIC FIVE OF THE 27 — READ 16 Sep 2026. Reported, nothing proposed.

**Ranked by GSC impressions, not label count, and the ranking inverts the label order almost
completely.** `heat-cold-pain-modulation` carries **102 labels and zero impressions**; the four
largest label counts in the set are all on pages nobody reaches. **12 of 22 have no GSC row at all.**

| impressions | pos | labels | article | verdict |
|---|---|---|---|---|
| **2,049** | 9.5 | 20 | `heavenly-heat-sauna-review` | **VARIANT 5** — one defect, on the page read 15× more than any other |
| 135 | 11.8 | 26 | `benefits-of-massage-chairs-for-seniors` | **VARIANT 6** — a trial PROTOCOL cited as having demonstrated a result |
| 120 | 12.2 | 25 | `bbq-grilling-for-nutrient-preservation` | minor title drift; **outdoor cooking, scoped out 7 Sep** |
| 91 | 16.5 | 72 | `recovery-ladder…` | **clean** — names its case report AS a case report |
| 56 | 7.7 | 27 | `finnmark-designs-fd-4-review` | thin, not false — a paediatric myopia RCT cited for a wavelength |

### 🔴 `heavenly-heat-sauna-review` — variant 5, on the highest-traffic page in the set

> *"…associated with **meaningfully lower hazard ratios** for incident hypertension — 0.76 and 0.54
> in unadjusted models, and 0.83 and 0.53 in fully adjusted models, for 2–3 versus 4–7 sessions per
> week (PubMed, 2017)."*

Per PubMed, PMID 28633297 (Zaccardi et al., *Am J Hypertens* 2017):

| | HR | 95% CI | |
|---|---|---|---|
| 2–3 sessions, unadjusted | 0.76 | **0.57–1.02** | **crosses 1 — not significant** |
| 4–7 sessions, unadjusted | 0.54 | 0.32–0.91 | significant |
| 2–3 sessions, fully adjusted | 0.83 | **0.59–1.18** | **crosses 1 — not significant** |
| 4–7 sessions, fully adjusted | 0.53 | 0.28–0.98 | significant |

**Two of the four figures are non-significant and all four are called "meaningfully lower."** No
confidence interval appears anywhere, and the pair is restated in the FAQ. Same shape as the 22%
sudden-cardiac-death figure corrected in `how-saunas-improve-circulation`.

**And the article is otherwise the most careful in the whole round** — every claim carries its
population and limitation (*"Finnish men, 40–60 years; results may not generalize"*, *"this does not
establish causation"*, *"'Associated with' is not the same as 'causes'"*), manufacturer claims are
flagged as manufacturer claims, and the detox myth is corrected. **Third article in the round whose
prose is more careful than its citation apparatus.**

### 🔴 `benefits-of-massage-chairs-for-seniors` — a PROTOCOL cited as a RESULT

The article says *"A **heat-stone massage trial** for chronic musculoskeletal pain **demonstrated
pain relief and improved tissue response**"*. PMC10466406 is **"Heat-stone massage for patients with
chronic musculoskeletal pain: a PROTOCOL for multicenter randomized controlled trial."** It reports
**no results at all** — it describes a trial that had not yet run.

**Variant 6 at its purest: a source cited for findings it does not contain.** Not a wrong paper, not
a wrong population — the paper has no findings.

**And 3 of its 4 sources are not about massage chairs:** hand massage with a warm hand bath (n=28
elderly women), hot stone massage in hemodialysis patients, and the protocol. **Only PMC12538054 is
a massage-chair trial** — and that one the article handles correctly: *"a single branded device with
a specific stretching protocol. Results cannot automatically be applied to all massage chairs."*

### The species question — asked of every claim, as instructed

**No claim about people rests on animal work in any of the five.** Zero species words appear in any
of the five bodies, which is why the question had to be asked of the SOURCES rather than the prose.
The only animal content in the set is a mouse toxicity model inside the pork-belly HCA paper
(PMC9890326), and **it is not cited in the body at all.**

### `finnmark-designs-fd-4-review` — thin, not false

PMC9587157 is *"650 nm Low-Level Red Light for Myopia Control in **Children**"*, a paediatric
ophthalmology RCT, cited on a sauna review for *"650 nm is a frequently studied red-light
wavelength"*. **That is an existence claim about the wavelength and the paper does support it**, so
it is thin rather than wrong — rule 5 applies. The article is otherwise careful: *"no study tests the
FD-4's three modes as a single therapy"*, *"retailer-reported figures, not independent lab
measurements"*.

## ⛔ CITATION WORK STOPS HERE. The remaining 22 are UNREAD, not clean.

**This distinction is the handover.** An unread article with resolvable citations looks identical to
a verified one in every report this project owns. **Metadata verification cannot catch what the HSF1
paragraph carried** — a fabricated study design under a citation whose identifier, subject, journal,
year and title all check out.

| labels | impressions | article |
|---|---|---|
| 102 | 0 | `heat-cold-pain-modulation-not-elimination` |
| 86 | 0 | `float-therapy-vs-cryotherapy-differences` |
| 81 | 0 | `heat-shock-proteins-cell-culture-to-humans` |
| 69 | 0 | `dry-sauna-for-home` |
| 60 | 0 | `designing-low-cognitive-load-interior-choices…` |
| 45 | 0 | `cold-plunge-benefits-mental-clarity` |
| 41 | 0 | `heat-cold-inflammatory-timeline-musculoskeletal-injuries` |
| 40 | 0 | `contraindications-home-thermal-biohacks-safety-checklist-educators` |
| 39 | 11 | `cold-plunge-buying-mistakes` |
| 37 | 27 | `sauna-for-arthritis-joint-pain-relief` |
| 32 | 0 | `how-float-tanks-improve-sleep-quality` |
| 31 | 20 | `contrast-therapy-demystified-human-studies` |
| 31 | 0 | `massage-chairs-office-workers` |
| 28 | 101 | `sauna-benefits-detoxification` *(citations already fixed, pass 3/5)* |
| 27 | 56 | `finnmark-designs-fd-4-review` *(read)* |
| 26 | 135 | `benefits-of-massage-chairs-for-seniors` *(read)* |
| 25 | 0 | `timing-heat-cold-fatigue-type-recovery-map` |
| 25 | 120 | `bbq-grilling-for-nutrient-preservation` *(read)* |
| 21 | 32 | `chromotherapy-vs-no-chromotherapy…` *(fixed, pass 1/5)* |
| 21 | 0 | `biophilic-design-measurable-outcomes-evidence` |
| 20 | 2,049 | `heavenly-heat-sauna-review` *(read)* |

**`heat-shock-proteins-cell-culture-to-humans` is the one to read first if this resumes** — same
subject and same author-voice as the article that carried the fabricated human framing, 81 labels,
and its title names the exact translation step where that defect lives.

### APPLIED — `heavenly-heat-sauna-review`, variant 5. Backup `2026-09-16T20-13-00-333Z`. 8/8.

Both representations corrected in one pass. The body now reads: *"the fully adjusted hazard ratio
was **0.53 (95% CI 0.28–0.98) for 4–7 sessions per week** — statistically significant. At **2–3
sessions per week it was 0.83 (95% CI 0.59–1.18), an interval that crosses 1.0 and is compatible
with no effect**… the association shows up at four or more sessions a week and is not established
below that."* The FAQ restatement carries the same intervals. **n = 1,621 Finnish men** now stated.
Four `95% CI` occurrences where there were none.

### `benefits-of-massage-chairs-for-seniors` — READ IN FULL. Not a rewrite. Two targeted defects.

**The article is more honest than the first pass suggested.** It names each intervention in the
prose — *"hand massage"*, *"Hot-stone massage… in hemodialysis patients"*, *"chair-based PNF
stretching"* — so it is not passing other interventions off as massage chairs. It carries twelve
myth corrections including *"Massage chairs improve cognitive function and prevent dementia"* and
*"Any massage chair will provide clinically proven benefits"*, and it says of its one real chair
trial: *"a single branded device with a specific stretching protocol. Results cannot automatically
be applied to all massage chairs."* **Fourth article in the round whose prose is more careful than
its citation apparatus.**

**DEFECT 1 — the protocol, cited five times, twice for results it does not contain.** `(PMC, 2023)`
is PMC10466406, *a protocol for* a trial. It reports nothing. It is cited for:

| | |
|---|---|
| *"A heat-stone massage trial… **demonstrated pain relief and improved tissue response**"* | **false — no results exist** |
| *"Heat-assisted massage **improved** chronic musculoskeletal pain"* | **false — same** |
| *"Heat plus massage reduces muscle tension and improves tissue elasticity"* | unsupported by this source |
| *"Massage can reduce arthritis pain and stiffness"* | unsupported by this source |
| an experiment-design prompt in the testing section | harmless |

**DEFECT 2 — one source carrying three outcomes it does not report.** *"Research in older adults
links massage with reduced back pain, better physical function, and improved sleep and relaxation
(PMC, 2019)."* PMC6734672 is hot-stone massage and **sleep quality only**, in **hemodialysis
patients**. Back pain and physical function are not in it, and the population is not "older adults".

**Proposed, not applied:** restate the two false result-claims as a trial in progress or cut them;
narrow defect 2 to sleep, in the population the paper studied. The remaining ~20 cited sentences
rest on sources that say what the article says they say.
