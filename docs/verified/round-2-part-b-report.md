# INH Verified Round 2 — Part B report (preview built; nothing live)

Branch `verified/r2-pages`. API spend $0. Nothing was written to MAIN, and no entry is active.

## What exists now

| Where | What | State |
|---|---|---|
| Preview theme `146278776899` (UNPUBLISHED) | 10 new files (4 sections, 1 snippet, CSS, JS, 3 templates); `layout/theme.liquid` and `templates/product.json` patched | read back byte-identical by MD5 |
| Store pages | `sauna-database` (hub) and `sauna-database-methodology` | **hidden**; body read back identical in visible text |
| Metaobject definition and 67 entries | ready (`verified_deploy.py entries`) | **PENDING**: the token lacks `write_metaobject_definitions` and `write_metaobjects` |
| Product metafields | ready, with a reversal file and a one-product reversal proof (`verified_deploy.py metafields`) | **PENDING**: needs the entries |
| `data/verified/handles.json` | 67 frozen handles (R2-D1); `handle-redirects.json` is empty | committed |
| `data/verified/title-overrides.json` | 67 approved titles | committed |

**Empirically confirmed (D-D).** The hidden hub, the hidden methodology page and a model path all
redirect and then **404** under `?preview_theme_id=146278776899`. So verification renders the
theme's own templates locally (`scripts/verified_render.py`, python-liquid) inside the store's
real header and footer.

## Decisions applied

- **Titles and handles:** all 67 rows approved and frozen.
  - **One deviation, flagged:** the Reserve Edition row's handle as written in the CSV was 77
    characters, which breaks R2-D1's 60-character limit. Your D-H answer adopted my
    recommendation, so the frozen handle is `golden-designs-reserve-edition-1-person`.
  - The freeze step now refuses any handle over 60 characters.
- **R2-D6:** nested capacity statements now publish the widest stated range, cited to the
  statement that states it. That changed 5 records in `saunas.json`; page count is unchanged.
  - Prior assertion changed deliberately: `test_nested_capacity_statements_are_consistent_not_r5`
    asserted the Round 1 placeholder ("which to publish is a Round 2 decision"). It now asserts
    R2-D6. Its "not R5" assertion is unchanged.
- **Title overrides may only remove words.** The build now halts if an approved title adds a word
  the manufacturer-derived title doesn't have.
- **D-C:** every gap reads "Not verified". The words "Not stated on the manufacturer's page" appear
  nowhere; a lint and a test enforce this.
- **D-G:** `offers` is stripped from every payload. A lint over rendered HTML, page data, the
  methodology body and every theme source fails on any price key or currency string.
- **R2-D10:** the "Infinite Sauna" lint now covers templates, page data and rendered output.
- **R2-D8:** quoted source text is capped at 160 characters. A quote is withheld if it contains a
  banned claim or is health-adjacent at all. That's stricter than the minimum; the value and its
  link still show. No quote among the 67 pages was withheld.
- **R2-D12:** the product mapping was rebuilt from the live Admin API (read-only; 672 products).
  - 66 records map; 39 of them have pages.
  - Two records whose store SKU only extends the model number are reported, not mapped.
- **D-K:** `main` pushed after re-confirming that no workflow triggers on push.

## Threshold amendment (option-dependence with evidence)

**Adds 0 pages.** Option-dependence is detected in Round 1 but not recorded with evidence. When a
page offers a heater option, the build turns the field ambiguous, and the record keeps only "the
source states more than one value", with no source URL or snippet. If the page makes no
electrical statement at all, nothing is recorded.

**What's needed (Round 3):** an `electrical.option_dependence` object on the record carrying the
option name and values, `source_url`, `observed_at` and `evidence.snippet`. It must be written
even when the page makes no electrical statement.

**Projection:** 37 Almost Heaven records have a heater or electrical option on the manufacturer's
page. **None** would qualify even with that evidence, because each also lacks verified dimensions
or heat type.

**The template already supports it:** "Depends on the heater option chosen" with its source link,
tested with a fixture. It counts for the threshold only when the source URL and snippet are
present.

## Threshold counts (unchanged: 67)

| Brand | Sold by INH | Published | Page |
|---|---|---|---|
| Dynamic Saunas | yes | 26 | 25 |
| Maxxus | yes | 17 | 12 |
| Golden Designs | yes | 27 | 6 |
| Dundalk LeisureCraft, SaunaLife, Scandia | yes | 9 | 0 |
| Salus | no | 63 | 24 |
| Almost Heaven, Clearlight, Heavenly Heat, Redwood, Sun Home | no | 95 | 0 |
| Medical Saunas | **no** (all its store products are now DRAFT) | 4 | 0 |
| **Sold by INH / not sold** | | **79 / 162** | **43 / 24** |

Medical Saunas moved from "sold" to "not sold": the rule is "an active store product under the
brand", and the live pull shows none.

## Verification (local render of the theme's own templates; 67 model pages, hub, methodology)

| Check | Result |
|---|---|
| **Value match** against `saunas.json`, resolved independently of the page builder | **1,649 fact rows**: value, grade, source and every number in the text match. Also checked: gaps are only where the dataset doesn't verify; every verified key or electrical value appears in its own block; H1 is the approved title; the answer sentence and meta description use only verified numbers; quotes are substrings of their evidence |
| Mutation tests | the check catches a changed value, a hidden verified value and a gap over a verified value (one of these found a real weakness in the check, now fixed) |
| No price, no "Infinite Sauna", no "Not stated…" | 147 texts scanned: rendered pages, page data, methodology body, theme sources. Clean |
| Health-claims gate | clean on every rendered page's visible text |
| Title, canonical, meta description | rendered from the preview theme's own layout. Model title is exactly "[Title]: Verified Specs & Electrical Requirements"; canonicals are self-referencing |
| schema.org | every type and property checked against the current schema.org vocabulary (Product with PropertyValue, BreadcrumbList, Dataset). No offers, aggregateRating or review |
| Hub with JavaScript off | 67 of 67 rows visible; filter bar hidden |
| Links | 98 source links answer 200/206; 52 store links answer 200 (fetched under the Round 1 policy). The 67 internal model links name frozen handles and resolve at activation |
| Product page (real preview, Golden Designs Toledo) | the new section sits directly after the reviews section. Every section above it is identical in the rendered DOM and in `product.json`. It renders 0 px while no entry is active |

## Sweep

- **Tests:** 701 passed (668 prior + 33 new).
- **Checks:** `verified_checks.py` PASS.
- **Missing-value lint:** 0.
- **Preflight:** clean (static and imports).
- **Facts cache and drift:** clean.
- **Deploy:** dry-run clean; self-test PASS, and it now includes an idempotent re-run.
- **Determinism:**
  - dataset: identical from two brand orders (`saunas.json` `293e58a0…`, conflicts `49f9b398…`,
    backlog `7de4a8fc…`);
  - page data: identical across two builds;
  - render: identical across two renders.
- **New dependency:** `python-liquid==1.13.0`, declared in `requirements.txt`.

## Problems found and fixed during the round

1. The hub counted **5 manufacturers instead of 4**. A Liquid `split` of a trailing separator
   behaves differently across engines; the count is now an explicit counter.
2. The **filter bar showed with JavaScript off**: `display: flex` beat `[hidden]`, and would also
   have un-hidden filtered rows on phones.
3. A **calculator test broke** because its `page.sauna-*.json` glob matched my templates. I didn't
   edit that test; I renamed my templates to `page.inh-verified-*.json`. The page URLs are
   unchanged.
4. The **value-match check accepted a verified value shown anywhere**. It now requires the value
   in the key-facts or electrical block.
5. Two **deploy guards fired on correct states**, as CLAUDE.md warns gates can:
   - Shopify's entity normalisation (`&#x27;` stored as `'`);
   - an idempotent product-template re-run.
   Both halted before writing anything. Both now compare the right thing: decoded visible text,
   and "a re-run changes nothing".

## Open items

- **Token scopes (you):** add `write_metaobject_definitions` and `write_metaobjects`. Then run
  `verified_deploy.py entries --write` and `metafields --write`; the second proves the reversal
  on one product before writing the rest.
- **The MAIN theme id in CLAUDE.md is stale.** MAIN is now `167150092355` (Round 23b), not
  `146149867587`. I haven't edited CLAUDE.md; it needs your word.
- **The preview theme is 12 days behind MAIN.** Go-live patches MAIN's own files; it never copies
  from theme 13.
- **`frontend-design` is still unavailable in this session.** `emil-design-eng` was applied:
  - motion is limited to one 200 ms ease-out disclosure marker, with none under reduced motion;
  - tap targets are 48 px; the base size is 17 px.
