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
- `outdoor-fireplaces` — 6 products, 100% type "Fire Pits", zero "Fireplace". Blocked
  behind the BBQ/outdoor scope decision.
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

**Status:** promoted 6 September 2026 on the client's ruling. `product_type` feeds the
**Google Merchant Center product feed**, where it is a categorisation signal. Inconsistent
values degrade Shopping categorisation and can trigger product disapprovals — so this is
lost revenue, not tidiness. It also blocks any automated membership audit (B5) and any
conversion of the 87 manual collections to smart ones.

**Do this first, before normalising anything:** check Merchant Center for existing
disapprovals and category mismatches, so the size of what is already broken is known rather
than assumed. Normalising the values without that baseline destroys the evidence of what the
inconsistency was costing.

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
