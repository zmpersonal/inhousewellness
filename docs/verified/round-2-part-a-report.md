# INH Verified Round 2 — Part A report (prepare, then stop)

Branch `verified/r2-pages` (from local `main`). Nothing was written to Shopify: no definition, no
entry, no page, no theme file. API spend $0. Tests: **668 passed** (654 prior + 14 new);
preflight clean; missing-value lint 0.

## 1. Merge

**No workflow can be triggered by a merge.** All 11 workflows under `.github/workflows/` trigger
only on `workflow_dispatch` and/or `schedule`. None has `push`, `pull_request`, `workflow_run`,
`release` or `merge_group`. The three scheduled ones (`autoposter`, `autoposter-weekly`,
`linked-product-status`) read none of the files Round 1 added. Round 1 also adds `jsonschema` to
`requirements.txt`, which those jobs install; that is one extra package and no behaviour change.

**Merged locally**, as a fast-forward of `main` to `73ae4a7`. `verified/r2-pages` branches from
there.

**⚠️ Not pushed.** Local `main` was already **8 commits ahead of `origin/main`** before the
merge: Round 23 `inh-seo` work, committed today from another workstream and never pushed.
Pushing `main` would publish those 8 commits along with Round 1. This is decision **D-J**. The
working tree also holds an uncommitted edit to `inh-seo/scripts/apply/r23j-plain-text.mjs` that
isn't mine. I left it untouched.

## 2. R2-D15 — the intermittent test failure: root cause found and fixed

**The pytest cache I cited in Round 1 was wrong. I'm correcting the record.** The three
"last failed" entries in `.pytest_cache` name Blotato tests that were deleted in Round 19
(`bd33e19`). They were stale entries, never the failure.

**The real cause** was that the build wrote `internal/backlog.json` in the order the brands were
passed on the command line:

- The Round 1 sweep built from `out/verified/ALL.sh` (lead-file order), giving a backlog hash of
  `8cffe4ca…`.
- The determinism test rebuilds in `sources.json` order, which gives `1249a59b…`.
- So **the first test run after a sweep always failed, and every later run passed**, because the
  test had already rewritten the file. That is exactly the "1 in 5, never reproduced"
  pattern.

Reproduced on demand: the same 16 brands in two orders gave two backlog hashes.

**Fix.** In `scripts/verified_build.py`, the backlog and the verification log are now sorted by
content, like records and conflicts already were. The determinism test now rebuilds in
**reverse** configuration order, so any future order dependence fails every time rather than
occasionally. Nothing was skipped, marked flaky or deleted.

**Other checks:**
- **Hash seeds:** the build is byte-identical under `PYTHONHASHSEED` 0–5.
- **Content unchanged:** the backlog's content is identical (26 entries, same set); only its order
  changed. It now hashes to `7de4a8fc…` whatever the brand order. `saunas.json` (`4e758a48…`)
  and `conflicts.json` (`49f9b398…`) are unchanged.
- **The Round 1 report was wrong here too.** It gave the backlog hash as `8cffe4ca…`, which was
  never committed; the committed file was `1249a59b…`.

**Second finding, the same class of problem.** 12 back-to-back full runs gave 11 passes and one
failure, and the failure was caused by me. `test_every_third_party_import_is_declared` walks the
**live working tree**, and it caught `verified_titles.py` in the moment before
`verified_pages.py` existed. The suite reads the working tree, and so does the determinism test,
which rewrites the dataset. Any edit during a run, including by the other session that has
uncommitted `inh-seo` work in this same checkout, can flip a result. **Rule for this round:** a
suite run counts as evidence only if nobody is editing the tree during it.

## 3. Shopify metaobject limits, confirmed; proposed definition

Checked against shopify.dev ("Metaobject limits", "Metafield limits", changelog 2025-10-24) and
the Admin API (connector, read-only): the shop is on the **Basic** plan; there are 32 existing
definitions, of which 1 (`sauna_block`) is merchant-created; no `sauna` type exists.

| Limit | Value | Our need |
|---|---|---|
| Fields per definition | 40 | 14 |
| Entries per definition | 1,000,000 | 67 |
| Merchant definitions (Basic) | 128 | +1 |
| JSON field value | **128 KB** (2 MB only for apps grandfathered before 2026-04-01) | largest qualifying record: 19.9 KB |
| Text field | 64 KB | titles and SEO strings |
| Draft entries | **not visible in storefronts** | see D-D, this limit forces a design choice |
| Web pages | `/pages/{urlHandle}/{handle}`, rendered by `templates/metaobject/sauna.json` | |

**Proposed definition:** `data/verified/metaobject-definition-proposed.json`.
- **Type:** `sauna`.
- **Capabilities:** publishable, renderable (SEO title and description) and onlineStore
  (`urlHandle: sauna-database`).
- **14 fields:**
  - title, inh_id, brand, heat_type, capacity_label, supply_voltage, placement, verified_date,
    seo_title, seo_description;
  - **`record`** (JSON: the full record **with `offers` removed**);
  - **`page_data`** (JSON: precomputed render strings, so Liquid never composes a value);
  - `store_product` and `store_collections`, which are navigation only and sit outside
    `record`.
- Nothing in the limits forces a change to R2-D3's design except draft visibility (D-D).

## 4. The threshold: 67 of 241 published records get a page

| Brand | Sold by INH | Published | Get a page |
|---|---|---|---|
| Dynamic Saunas | yes | 26 | **25** |
| Maxxus | yes | 17 | **12** |
| Golden Designs | yes | 27 | **6** |
| Dundalk LeisureCraft | yes | 2 | 0 |
| Medical Saunas | yes | 4 | 0 |
| SaunaLife | yes | 6 | 0 |
| Scandia | yes | 1 | 0 |
| Salus | no | 63 | **24** |
| Almost Heaven | no | 43 | 0 |
| Clearlight | no | 12 | 0 |
| Heavenly Heat | no | 8 | 0 |
| Redwood Outdoors | no | 17 | 0 |
| Sun Home | no | 15 | 0 |
| **Brands INH sells** | | **83** | **43 (52%)** |
| **Brands INH doesn't sell** | | **158** | **24 (15%)** |
| **Total** | | **241** | **67** |

- **"Sold by INH"** is decided per brand from the store's own active products, not from the lead
  file. It agrees with Round 1's split (83 / 158). Mande Spa, Kohler and Ripavi have no
  published records.
- **Why the other 174 fall short** (a record can miss more than one requirement): exterior
  dimensions 124, electrical 117, heat type 51, capacity 40.
- **R2-D6 (widest range)** would change no page count: the 5 records with nested capacity
  statements all miss another requirement.
- **Four brands produce every page.** 43 of the 67 pages (64%) belong to brands INH sells, and
  39 of those map to an INH product. See D-A: this is the result the independence clause exists
  to make look fair.

`scripts/verified_pages.py --threshold` reproduces these numbers; the threshold has one
definition, shared with the page build.

## 5. Review file (one row per record)

**`docs/verified/round-2-title-review.md`** is the version for reading, and
**`round-2-title-review.csv`** has the same 67 rows plus an approve column. Each row gives the
brand, whether INH sells the brand, the INH product it maps to, the proposed title and the
proposed handle.

- **Titles:** the Round 1 display title with marketing and year words removed ("Updated",
  "Luxury", "Nero Zero EMF"). Nothing is added or reworded.
- **Handles:** `brand-model-name[-capacity]`, where the model name is stripped of heat-type,
  placement and generic words. Where two handles collide, the manufacturer's own edition token
  (`elite`, `zf`, `fs`) is appended, never a counter.
- **Flagged for you:**
  - Golden Designs **Reserve Edition** handle is 77 characters, over the 60 limit. I propose
    `golden-designs-reserve-edition-1-person`.
  - Two Maxxus records (`MX-K206-01-ZF HEM`, `MX-M206-01-FS CED`): the manufacturer's title names
    no model, so the handle falls back to the model number.
  - Manufacturer spellings kept as written: "Toulose", "Montilemar", "Llumeneres".
- **Mapping is preliminary.** The local `SHOPIFY_ADMIN_TOKEN` returns **401**, so the mapping
  comes from the Admin API census committed 2026-09-15 (165 active sauna products). That census
  carries no collections. Matching is exact SKU plus vendor, or nothing:
  - Two records whose store SKU only extends the model number (e.g. `MX-S306-01` vs
    `MX-S306-01-FS`) are reported, not mapped.
  - The store has duplicate SKUs (`MX-K306-01 CED` on two products). Any record matching those
    would be withheld as ambiguous.
- Nothing is written to `title-overrides.json` or a handles file until you approve.

## 6. Wireframes (mobile first; text)

Primary reader: 40–60, on a phone. Type follows the store's theme (read from MAIN in Part B).
Base size ≥17px, helper text ≥15px, tap targets ≥48px. The only motion is the source-text
disclosure: 200 ms ease-out, and none under `prefers-reduced-motion`.

**Model page** (`/pages/sauna-database/{handle}`)
```
Breadcrumb: Home › Sauna database › [Title]
H1  [Title]
"[Title] is a 2-person indoor infrared sauna that requires one 120V, 15A circuit."   ← template
Verified 2026-09-27 · How we verify →
── Key facts ─────────────────────────────
Heat type        Infrared                 Listed · source ↗ · 2026-09-27
Capacity         Manufacturer states 5 to 6 people   Listed · source ↗
Exterior (W×D×H) 47 × 39 × 75 in          Listed · source ↗
── Electrical ────────────────────────────
Circuits required  2
  Stove            240V · 30A             Listed · source ↗
  Lights & music   120V · 15A             Listed · source ↗
Supply voltage     Not stated on the manufacturer's page
Stated amperage    Not verified  (one row per field; every value: grade + link + date)
Heater             8 kW                   Documented · manual p.4 ↗
── Ask the seller ────────────────────────   ← one line per missing field, templated
• What amperage does the circuit need?
── Full specifications (table) ───────────
▸ Source text (collapsed; quoted, ≤160 chars, only snippets that pass the health gate)
── Cite this page ────────────────────────
[Title]. InHouse Wellness Verified Sauna Database. URL. Verified 2026-09-27.
Corrections: data@inhousewellness.com
═════════════ visually separated band ════════════
InHouse Wellness store
  See price and availability at InHouse Wellness →   (or: Manufacturer's page ↗ ·
  Browse infrared saunas at InHouse Wellness →)
InHouse Wellness sells some of the brands listed. How records are verified →
```
On a phone, each fact is a two-line row: label and value on top, grade · source · date below.
There is no horizontal table scroll except in the full-specifications table, which gets
a sticky first column. The page shows no price anywhere.

**Hub** (`/pages/sauna-database`)
```
H1  Verified Sauna Database
2–3 sentence intro · "67 models from 4 manufacturers · 174 more records are below the page threshold" · Methodology →
[Filter: heat type ▾] [capacity ▾] [brand ▾]   ← JS-only enhancement; hidden without JS
<table> Brand | Model (link) | Heat type | Capacity | Supply voltage   ← server-rendered, all 67 rows
On phones: rows become stacked cards (CSS only, same DOM)
Disclosure line
```

**Methodology** (`/pages/sauna-database-methodology`)
```
H1  How the Sauna Database is verified
Last updated [date] · Responsible for the data: Daniel Mercer · Corrections: data@inhousewellness.com
1 Source hierarchy (manufacturer page → manufacturer manual/spec sheet → named distributor)
2 Grades — one plain sentence each (certified … not_applicable)
3 Editorial independence — the CLAUDE.md clause, verbatim
4 Two kinds of gap — "Not stated on the manufacturer's page" vs "Not verified"
5 What doesn't get a page — the threshold; 174 below it (by missing field), 21 held by rule
  (identity 18, electrical 2, capacity 1, hybrid 1 — aggregate only), 26 with no reachable
  manufacturer page, 3 manufacturers unreachable
```

## 7. Decisions needed

**D-A. The threshold result is lopsided.** No page for Almost Heaven, Clearlight, Sun Home,
Redwood or Heavenly Heat, and 64% of pages are brands INH sells.
- **Options:**
  - (a) Proceed with 67.
  - (b) Before go-live, run a matcher round on gaps where the value is on the page but was
    withheld:
    - Clearlight capacity is stated ("Premier IS-1 Person", "fits 4-5 people"), and 8 Clearlight
      records miss only capacity.
    - Sun Home is missing dimensions on 15 records, Golden Designs on 14, Heavenly Heat on 7.
  - (c) Change the threshold.
- **Recommend:** (a) for the preview, and (b) before go-live, under the same "read what is stated,
  never loosen" rule.

**D-B. The verification list can't be met as written.** The brief asks for Almost Heaven and
Clearlight model pages, and neither brand has one.
- **Options:**
  - (a) Substitute a second Salus record and a Dynamic record.
  - (b) Wait for D-A(b).
- **Recommend:** (a). The Golden Designs, Maxxus and Salus picks stay, and Salus supplies both
  the labelled-circuit case and the gap case.

**D-C. R2-D7's "Not stated" wording can't be derived from the data yet.** A blank field with
no note means "our extractor found no statement it could attribute". It does not mean "the page
lacks it". The Clearlight pages state capacity, yet the records hold nothing. Printing "Not
stated on the manufacturer's page" there would be false, about a manufacturer.
- **Options:**
  - (a) Add a per-field status to the build. It is "stated_absent" only when a deliberately broad
    mention scan of the fetched text finds nothing; everything else is "not_verified".
  - (b) Show "Not verified" for every gap until (a) exists.
- **Recommend:** (a), with (b) as the rule for any field (a) can't classify.

**D-D. Draft entries can't be previewed.** Shopify doesn't show DRAFT metaobjects on the
storefront, and hidden pages 404 even under `?preview_theme_id=` (recorded in
`scripts/deploy_pages.py`). So the hub, methodology page, model pages and the product link all
fail to render on the preview while entries stay draft, as the brief requires.
- **Options:**
  - (a) Keep entries draft. Verify by rendering the exact theme template files locally against
    the dataset:
    - value match, JS-off table, schema.org, health gate, no price and no "Infinite Sauna" all run
      on that output;
    - Part B also probes one draft URL to confirm Shopify's behaviour empirically;
    - storefront screenshots become the first go-live step.
  - (b) Activate entries while MAIN has no `metaobject/sauna.json` template, so they should 404
    live and render on the preview. This needs your explicit approval, and a probe for sitemap
    exposure first.
  - (c) Publish the hub and methodology pages, which would make them live.
- **Recommend:** (a).

**D-E. The product-page link needs data on the product.** A product can't look up the
metaobject that names it.
- **Options:**
  - (a) Write a product metafield `inh_verified.sauna` (a metaobject reference) on the 39 mapped
    products. It's invisible until a theme renders it, but it is a write to live product data.
  - (b) Loop every entry in Liquid on each product page (67 entries, paginated).
- **Recommend:** (a).

**D-F. The local Admin token returns 401.** This is 🔴, a human step: regenerate
`SHOPIFY_ADMIN_TOKEN` in `.env`.
- **Scopes needed:**
  - `read_products` for the mapping and collections;
  - `write_metaobject_definitions` and `write_metaobjects` for the draft entries;
  - `write_themes` for theme 146278776899;
  - `write_content` for hidden pages.
- The connector can't carry 67 records of about 15–20 KB each: that is the relaying problem
  CLAUDE.md already records.
- Until then the mapping stays preliminary and has no collections.

**D-G. Prices are in the dataset.** `offers[].price_usd` and `reference_price_usd` come from
Round 1. **Recommend:** strip `offers` from every Shopify payload, and add a lint that fails on
any price key or dollar amount in the payload or the rendered HTML.

**D-H. Handles.**
- Accept edition tokens from model numbers (`elite`, `zf`, `fs`) as the collision rule.
- Choose the Reserve Edition handle.
- Accept model-number handles for the two unnamed Maxxus models.

**D-I. Metaobject URL prefix.**
- **Options:** `sauna-database`, giving `/pages/sauna-database/{handle}` (it sits under the hub,
  and the breadcrumb matches), or `saunas`.
- **Recommend:** `sauna-database`, provided the definition can coexist with a page of the same
  handle. If Shopify refuses, I'll use `saunas` and report it.

**D-J. Pushing `main`.** Pushing would also publish 8 unpushed Round 23 commits. Push now, or
leave `main` local?

**D-K. Open item: Daniel Mercer's role.** Until you send it, the name renders alone. Also for
go-live: confirm that `data@inhousewellness.com` receives mail.

**D-L. Title tags.** "[Title]: Verified Specs & Electrical Requirements" runs to 90–130
characters on long titles, so search results will truncate it. No change proposed; noting it
for your review.

**Four ledger records.** All four (Bergen, Aspire II, Grand Governor, Grayson) are in the
backlog, so none gets a page. Part B will add an explicit exclusion and a test that asserts it.

**Design note.** `emil-design-eng` was read. **`frontend-design` isn't available in this
session.** I'm saying so rather than skipping it silently.
