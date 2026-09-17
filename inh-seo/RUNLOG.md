
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
