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
