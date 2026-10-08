# Round 4 (promote the electrical tool): Part A report. Nothing written.

2026-10-07 · branch `promote/r4-electrical-links` from `main` 97c4562 · generated from read-only Admin pulls and logged-out storefront fetches.

Files: `proposals.csv` (107 rows, one per edit, with an `approve (y/n)` column), `skipped.csv` (every page considered and why it gets nothing), `a2-samples.md`, `a1-inventory.json`, `link-counts.json`, `llms.txt.liquid.draft`.

## A1. Where electrical content lives on product pages (139 priced saunas)

| Storage | Rendered by | Visible on the page | Editable without visual change |
|---|---|---|---|
| `custom.dimentions_specifications` (rich text) | theme `Faq` accordion "Dimensions & Specifications", `metafield_tag` | yes | yes: a link node inside an existing text node |
| `descriptionHtml` | theme `Faq` accordion "Description" (`{{ product.description }}`) | yes | yes: `<a>` around existing words |
| `custom.electrical_requirements` (rich text, 100 products) | **nowhere**: only read as search text by `snippets/product-disclosure.liquid` | **no** | excluded: a link there would never be seen |
| `custom.key_feature`, `why_choose…`, `product_details` | theme accordions | yes | excluded: marketing bullet lists, not electrical sections |

No product uses an app-rendered tab for electrical content. 4 priced handles answer 404 on the storefront (Medical Saunas) and are excluded.

| Brand | Electrical line in the specs | Only in the description | No visible electrical section |
|---|---|---|---|
| Dynamic Saunas | 19 | 17 | 2 |
| Maxxus | 21 | 6 | 7 |
| Golden Designs Inc | 14 | 11 | 6 |
| Scandia | 2 | 0 | 6 |
| Dundalk Leisurecraft | 1 | 0 | 6 |
| SaunaLife | 2 | 0 | 5 |
| Finnmark Designs | 3 | 0 | 0 |
| Mande Spa | 0 | 0 | 3 |
| Kohler | 2 | 0 | 0 |
| Ripavi | 0 | 0 | 2 |

## A2. Product proposals: 57 (one link each)

- **Rule:** the link is an `<a>` around words **already on the page**, inside one text node of the specs' electrical line (preferred) or the description. No text is added, so nothing can rewrap except by link styling.
- **Target:** `/pages/sauna-electrical-requirements?model=<handle>` where the product maps to a live record, otherwise the plain tool.
- **Anchors:** natural phrases from our own copy ("electrical requirements", "dedicated outlet", "120V outlet", "special wiring", …). No phrase is used on more than 8 products, no brand or model name, 23 distinct anchors.
- **Not proposed (82):** 37 have no visible electrical section; 23 have electrical text with no natural phrase to link (no sentence is added to them); 18 were skipped only because every linkable phrase had hit the cap of 8 (raise the cap if you prefer coverage over variety); 4 answer 404.
- Five samples, as stored before and after: `a2-samples.md`.

**Decision for you:** the brief allows "one short plain sentence containing a link", and also forbids any layout shift. An added sentence can add a line and push the page down, so I proposed none on product pages. Approving added sentences would cover more of the 23 + 18.

## A3. Blog articles: 28 proposals

- **Scope:** live sauna and home-installation articles. Cold-plunge, massage and health-science articles are out of scope.
- **Placement:** one link per article, around existing words in a paragraph or list item, never in headings or existing links. 23 relevant articles have no linkable electrical phrase; one already links an electrical page.
- **Targets, most specific first:**
  - the 6 kW or 8 kW answer page where the sentence is about that heater;
  - the dedicated-circuit page only when the paragraph is about infrared;
  - heater sizing where the text is about sizing;
  - otherwise the tool, pre-filled when the article is about one model with a live record (Monaco DYN-6996-01 Elite, Maxxus MX-S106-01).
- No anchor is used on more than 5 articles.

| Article | Target | Anchor |
|---|---|---|
| `/blogs/saunas/best-2-person-sauna-buyers-guide` | `/pages/infrared-sauna-dedicated-circuit` | dedicated outlet |
| `/blogs/saunas/costco-sauna-guide-worth-it` | `/pages/sauna-electrical-requirements` | dedicated circuit |
| `/blogs/saunas/arcadia-barrel-sauna-guide` | `/pages/6-kw-sauna-heater-breaker-size` | 6kW heater |
| `/blogs/saunas/best-infrared-sauna-muscle-recovery` | `/pages/sauna-electrical-requirements` | dedicated circuit |
| `/blogs/saunas/sisu-sauna-review` | `/pages/6-kw-sauna-heater-breaker-size` | 6 kW heater |
| `/blogs/saunas/nurecover-tropic-home-sauna-review` | `/pages/sauna-electrical-requirements` | dedicated circuit |
| `/blogs/saunas/dry-sauna-for-home` | `/pages/6-kw-sauna-heater-breaker-size` | 6 kW heater |
| `/blogs/saunas/sauna-narrow-hallway-doorway-fit-guide` | `/pages/infrared-sauna-dedicated-circuit` | dedicated circuit |
| `/blogs/saunas/finnmark-fd4-vs-almost-heaven-audra` | `/pages/8-kw-sauna-heater-breaker-size` | 8kW heater |
| `/blogs/saunas/small-space-sauna-guide-corner-straight-wall-compact-cabin` | `/pages/infrared-sauna-dedicated-circuit` | dedicated 120V outlet |
| `/blogs/saunas/sunray-roslyn-vs-almost-heaven-madison-which-indoor-sauna-is-right-for-you` | `/pages/6-kw-sauna-heater-breaker-size` | 6kW heater |
| `/blogs/saunas/home-sauna-steam-room-lifetime-operating-costs` | `/pages/6-kw-sauna-heater-breaker-size` | 6kW heater |
| `/blogs/saunas/indoor-vs-outdoor-sauna-guide` | `/pages/6-kw-sauna-heater-breaker-size` | 6 kW heater |
| `/blogs/saunas/heavenly-heat-sauna-review` | `/pages/sauna-electrical-requirements` | dedicated circuit |
| `/blogs/wellness/renovation-sequencing-wellness-installations` | `/pages/sauna-electrical-requirements` | Dedicated outlet |
| `/blogs/wellness/insurance-permits-code-thermal-rooms` | `/pages/sauna-heater-size-calculator` | heater size |
| `/blogs/saunas/golden-designs-saunas-review` | `/pages/8-kw-sauna-heater-breaker-size` | 8 kW stove |
| `/blogs/saunas/dynamic-venice-sauna-review` | `/pages/sauna-electrical-requirements` | Electrical service |
| `/blogs/saunas/maxxus-saunas-review-buyers-guide` | `/pages/sauna-electrical-requirements` | electrical requirement |
| `/blogs/saunas/finnmark-designs-saunas` | `/pages/sauna-electrical-requirements` | 240V circuit |
| `/blogs/saunas/dynamic-saunas-review` | `/pages/sauna-electrical-requirements` | 120V outlet |
| `/blogs/saunas/finnmark-designs-fd-4-review` | `/pages/sauna-electrical-requirements` | electrical work |
| `/blogs/saunas/saunalife-model-g6-review` | `/pages/sauna-heater-size-calculator` | heater sizing |
| `/blogs/saunas/dynamic-saunas-monaco-dyn-6996-01-elite` | `/pages/sauna-electrical-requirements?model=dynamic-monaco-6-person` | electrical requirements |
| `/blogs/saunas/maxxus-mx-s106-01` | `/pages/sauna-electrical-requirements?model=maxxus-s-line-1-person` | dedicated outlet |
| `/blogs/news/best-6-person-sauna` | `/pages/8-kw-sauna-heater-breaker-size` | 8kW stove |
| `/blogs/saunas/almost-heaven-audra-shenandoah` | `/pages/sauna-electrical-requirements` | electrical work |
| `/blogs/saunas/true-total-cost-home-sauna` | `/pages/sauna-electrical-requirements` | 120V circuit |

Each row's full sentence is in `proposals.csv` (`context`).

## A4. Collections: 19 proposals

- **In scope:** sauna and sauna-heater collections only.
- **No proposal:** 42 collections whose only electrical text is the shared delivery boilerplate ("Getting it inside and assembled is $1,800 … electrical work …"). That is not the collection's own words, and linking it would repeat one anchor across dozens of pages.
- **Anchors:** existing words only; no phrase on more than 3 collections.

| Collection | Target | Anchor |
|---|---|---|
| `/collections/sauna` | `/pages/sauna-electrical-requirements` | 240V circuit |
| `/collections/saunas` | `/pages/sauna-electrical-requirements` | dedicated 240V circuit |
| `/collections/harvia-sauna-heaters` | `/pages/sauna-electrical-requirements` | dedicated circuit |
| `/collections/infrared-saunas` | `/pages/infrared-sauna-dedicated-circuit` | standard 120V circuit |
| `/collections/ultra-low-emf` | `/pages/sauna-electrical-requirements` | standard 120V circuit |
| `/collections/far-infrared` | `/pages/infrared-sauna-dedicated-circuit` | standard 120V circuit |
| `/collections/golden-designs` | `/pages/sauna-electrical-requirements` | dedicated 240V circuit |
| `/collections/hybrid` | `/pages/sauna-electrical-requirements` | 240V circuit |
| `/collections/outdoor-saunas` | `/pages/sauna-electrical-requirements` | 240V circuit |
| `/collections/indoor-sauna` | `/pages/sauna-electrical-requirements` | dedicated 240V circuit |
| `/collections/scandia-manufacturing` | `/pages/sauna-electrical-requirements` | 240V supply |
| `/collections/medical-sauna` | `/pages/sauna-electrical-requirements` | 240V supply |
| `/collections/electric-saunas` | `/pages/sauna-electrical-requirements` | dedicated circuit |
| `/collections/huum-sauna-heaters` | `/pages/sauna-electrical-requirements` | 240V supply |
| `/collections/finnmark-designs` | `/pages/infrared-sauna-dedicated-circuit` | standard 120V supply |
| `/collections/6-person-sauna` | `/pages/sauna-electrical-requirements` | standard 120V outlet |
| `/collections/indoor-infrared-sauna` | `/pages/infrared-sauna-dedicated-circuit` | standard 120V household outlet |
| `/collections/3-person-corner-sauna` | `/pages/infrared-sauna-dedicated-circuit` | standard 120V outlet |
| `/collections/2-person-infrared-sauna` | `/pages/infrared-sauna-dedicated-circuit` | standard 120V household outlet |

## A5. Other InHouse Wellness pages

| Page | Existing sentence | Anchor | Target |
|---|---|---|---|
| `/pages/faq-page` | "Premium installation ($1,800) covers everything except electrical work." | electrical work | the tool |
| `/pages/sauna-cost` (page body above the calculator) | "Then the electrician is a separate bill, …" | the electrician | the tool |
| `/pages/sauna-database-methodology` | "A reference of home sauna specifications, with the electrical requirements first." | electrical requirements | the tool |

- **Database hub intro:** already links the tool (added at launch); nothing more.
- **Calculator model step:** the help text "The kW beside a name is the rating its manufacturer publishes" is the natural place ("rating its manufacturer publishes" → the tool). But it lives in **`sections/true-total-cost.liquid`**, a theme file, which this round puts out of scope. **Not proposed unless you allow that one section edit.**
- **Found, not touched:** a published page **`/pages/llms-txt`** holds an older llms-style text (673 products, ~40 manufacturers) as an ordinary indexable page. It is unrelated to the real `/llms.txt` route. Worth unpublishing (your call).

## A6. AI discovery (`/llms.txt`)

- **The brief's premise is out of date.** Shopify serves `/llms.txt` natively, and this store already serves **our own**: `templates/llms.txt.liquid`, live since INH Verified Round 4 (2026-09-29).
  - It currently answers 200 with `content-type: text/markdown; charset=utf-8`.
  - It lists the database hub and methodology, but nothing about the electrical tool or the cost calculator.
- Options considered:
  1. **Edit `templates/llms.txt.liquid` (recommended).** It is the platform's own route: the right content type, no app, no redirect. The file is on the INH Verified must-travel list (CLAUDE.md), so MAIN and the repo change in one commit, written by file with a snapshot first.
  2. **App proxy:** needs a custom app and a server, and `/llms.txt` can't be an app-proxy path (proxies live under `/apps/…`). Rejected.
  3. **Redirect `/llms.txt` to a hosted file:** Shopify won't redirect a path it serves itself, and crawlers expect the file at the root. Rejected.
  4. **A page at `/pages/llms-txt`:** that is what the stray page above is. HTML, the wrong path. Rejected.
- **Content:** draft in `llms.txt.liquid.draft`. It is the current file plus two sections, "Electrical requirements" (the tool, heater sizing, the three answer pages, the electrical methodology) and "Cost" (the calculator), one line each, before "How records are verified". Nothing else changes.
- **Note:** this is a theme template. The round puts templates out of scope, but A6 asks for exactly this, so it needs your explicit yes.

## A7. Satellite sites (list only, no edits)

Candidates from `data/satellite-destinations.json`. All 10 domains are verified to link back. I chose by topic and did not re-read these pages this round.

| Satellite page | Would link to | Suggested descriptive anchor |
|---|---|---|
| besthomeinfraredsauna.com/electrical | `/pages/infrared-sauna-dedicated-circuit` | "what infrared manufacturers say about dedicated circuits" |
| besthomeinfraredsauna.com/best/120v | `/pages/infrared-sauna-dedicated-circuit` | "manufacturer-stated circuit requirements" |
| outdoorsteamsauna.com/heater-sizing | `/pages/sauna-heater-size-calculator` | "manufacturers' own heater sizing charts" |
| tubsandsaunas.com/guides/electrical | `/pages/sauna-electrical-requirements` | "sauna electrical requirements by model" |

- **Risk:** your brief records that the linkbuilding work flagged network links with commercial anchors as high risk. I couldn't find that report in this repo, so I'm restating it from your brief. Links between commonly owned sites are what search engines discount or penalise as a scheme, and a store URL as the target makes it commercial.
- **Recommendation: none this round.** If any: the 4 above, informational pages only, descriptive anchors only, never a product or collection URL. Excluded: infinitesauna.com (banned name in our lint), commercialinfraredsauna.com (a different, commercial audience).

## A8. Quotes that begin mid-word

- **Cause:** `verified_build.snip()` cuts a fixed 60-character window, so a snippet can start inside a word. 34 tool quotes begin at their snippet's first character. Checked against the cached source text:
  - **8 really begin mid-word;**
  - 23 start at a true word boundary ("CARBON MODEL…" is whole for some models and cut for others, so the snippet alone can't decide);
  - 3 come from catalogue JSON and begin "Electrical service:".

| Model | Quote now begins | Source shows | Would begin |
|---|---|---|---|
| dynamic-san-marino-2-person | "UNA – with WiFi…" | "…MODEL SA\|UNA" | "– with WiFi…" (then "with") |
| dynamic-vittoria-2-person | "N MODEL SAUNAS…" | "…CARBO\|N" | "MODEL SAUNAS…" |
| dynamic-vittoria-elite-2-person | "N MODEL SAUNAS…" | "…CARBO\|N" | "MODEL SAUNAS…" |
| golden-designs-reserve-edition-gdi-8260-01 | "ARBON MODEL SAUNA…" | "Manual C\|ARBON" | "MODEL SAUNA…" |
| salus-elite-6-person | "DEL SAUNA FOR…" | "…ARBON MO\|DEL" | "SAUNA FOR…" |
| salus-luxen-4-person | "FRARED MODEL SAUNA…" | "FAR IN\|FRARED" | "MODEL SAUNA…" |
| sun-home-equinox-full-spectrum-2-person | "5°F ELECTRICAL RATED…" | "Up to 16\|5°F" | "ELECTRICAL RATED…" |
| sun-home-solstice-4-person | "ATURE 130–140°F…" | "TEMPER\|ATURE" | "130–140°F…" |

- **Proposed mechanism:** a general rule that changes exactly these 8 and no snippet text.
  - `snip()` records `starts_mid_word` in the evidence (window start > 0 and alphanumeric on both sides of the cut).
  - The quote builder drops the first token only when the quote begins at the snippet's first character and that flag is true. The quote then gets a leading ellipsis, like any other cut.
  - It adds one evidence field to the records concerned: a record-only change (not displayed) that the entry refresh gate already allows as evidence metadata.

## A9. Internal links to the 6 electrical pages (own host only)

| Page | Now | New links proposed | After approval |
|---|---|---|---|
| `/pages/sauna-electrical-requirements` | 173 | +87 | 260 |
| `/pages/sauna-heater-size-calculator` | 2 | +2 | 4 |
| `/pages/6-kw-sauna-heater-breaker-size` | 2 | +6 | 8 |
| `/pages/8-kw-sauna-heater-breaker-size` | 2 | +3 | 5 |
| `/pages/infrared-sauna-dedicated-circuit` | 2 | +9 | 11 |
| `/pages/sauna-electrical-methodology` | 6 | +0 | 6 |

"Now" for the tool: one link on each of 166 live model pages, the hub, and the 6 electrical pages' own links. The two cross-links on the heater page come from the tool section. A first count matched an external site using the same path (thesaunaheater.com); counts are restricted to our own host.

## For Part B (after approval)

- Every proposal states the exact stored text it changes; the write refuses if the stored text differs from what was proposed.
- Both accordions are collapsed by default, so the before/after screenshots will open the accordion holding the edited text, at 1440 and 390 px.
- The theme re-serialises rich text and may normalise description HTML on save. A read-back diff showing anything other than the inserted `<a>` reverts that page and reports it.
