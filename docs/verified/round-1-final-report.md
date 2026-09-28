# INH Verified — Round 1 final report

**Status: Round 1 complete. Stopped as instructed.** Branch `verified/r1-data-foundation`.
Nothing merged, deployed or put on any website. No theme, no Shopify write, nothing sent to
Infinite Sauna. **Anthropic API spend: $0.** Blotato: 0 credits.

**The final dataset** (`data/verified/saunas.json`):
- **262 records, 241 published, 21 in backlog by rule.** A further 26 leads have no fetchable origin page and sit in the internal backlog.
- Every published value carries its `source_url`, fetch time, the fetched bytes' sha256 and a snippet or PDF page.
- Rebuilding from the cache is byte-identical: `saunas.json` `4e758a48…`, `conflicts.json` `49f9b398…`, `internal/backlog.json` `8cffe4ca…`.

## Decisions applied in this batch

| Decision | What was done |
|---|---|
| **B2-D1** Maxxus and Dynamic | Public proof found in Golden Designs' own manuals: *"This limited warranty applies to products manufactured or distributed by Golden Designs, Inc. under the **Maxxus** brand name…"* (p. 37, sha256 `74e59585…`), and the same sentence for **Dynamic** (p. 24, sha256 `0ddfe0de…`). Recorded in CLAUDE.md (source policy) and on every affected record as `provenance.origin_basis`. Both brands released |
| Robots 4xx on a manufacturer's main site | Allowed per RFC 9309 at 1 request / 2 s, Crawl-delay honoured. 5xx, timeouts and closed connections are still skipped. CLAUDE.md updated. (leisurecraft.com now answers 200 anyway) |
| **B2-D2** heat type from the description | Only the product's own description, only when exactly one heating system is named. Cross-sell, option, "choose/elect to", comparison and negated sentences are excluded, and it never overrides a title |
| **B2-D3** link attachment for all brands | Applied with the Salus guards, plus one ordering rule found in the audit: a document that names the brand's own model numbers goes through model binding (Round 15); link attachment only covers documents naming none |
| **B2-D5** "30-amp" | Read. The hyphen is allowed only before a spelled-out unit, so "AR-3A" stays a drawing label |
| **B2-D10** | All four fixes kept |
| **B2-D4 / D6 / D7 / D9** | Adopted as recommended |
| **B2-D8** Clearlight spec sheets | Tried. `/owner-resources/` was fetched and has **no PDF links in its static HTML** (they load in the browser), so nothing attaches without a new rule. Flagged, not loosened |

## 1. Per brand, all 16

| Brand | INH sells | Adapter | Leads | Published / backlog | Confirmed | Changed | Not found | Ambiguous (withheld) | New | Manuals attached |
|---|---|---|---|---|---|---|---|---|---|---|
| Almost Heaven | no | structured data | 59 (2 fetch failures) | 43 / 12 | 128 | 11 | 36 | 39 | 21 | 0 |
| Clearlight | no | page layout | 12 | 12 / 0 | 35 | 3 | 39 | 1 | 37 | 0 |
| Heavenly Heat | no | structured data + page layout + PDF | 8 | 8 / 0 | 34 | 0 | 12 | 0 | 26 | 7 |
| Redwood Outdoors | no | structured data | 18 | 17 / 0 | 57 | 9 | 9 | 19 | 0 | 0 |
| Salus | no | structured data + page layout + PDF | 65 | 63 / 2 | 268 | 5 | 0 | 12 | 234 | 40 |
| Sun Home | no | structured data + page layout + PDF | 15 | 15 / 0 | 86 | 9 | 6 | 6 | 52 | 28 |
| Golden Designs | yes | structured data + PDF | 28 | 27 / 1 | 195 | 16 | 12 | 71 | 35 | 19 |
| Maxxus | yes | structured data + PDF | 27 (4 no page) | 17 / 6 | 211 | 17 | 5 | 24 | 23 | 28 |
| Dynamic Saunas | yes | structured data + PDF | 26 | 26 / 0 | 252 | 20 | 5 | 4 | 26 | 25 |
| Scandia | yes | structured data | 8 (7 no page) | 1 / 0 | 1 | 1 | 2 | 1 | 0 | 0 |
| Medical Saunas | yes | structured data | 4 | 4 / 0 | 4 | 0 | 22 | 0 | 0 | 0 |
| SaunaLife | yes | page layout + PDF | 7 (1 no page) | 6 / 0 | 10 | 0 | 23 | 6 | 2 | 7 |
| Dundalk LeisureCraft | yes | page layout | 7 (5 no page) | 2 / 0 | 1 | 1 | 11 | 0 | 0 | 0 |
| Mande Spa | yes | **blocked** (TLS) | 3 | 0 / 0 | — | — | — | — | — | — |
| Kohler | yes | **blocked** (robots unreadable) | 2 | 0 / 0 | — | — | — | — | — | — |
| Ripavi | yes | **blocked** (timeouts) | 2 | 0 / 0 | — | — | — | — | — | — |

**Notes on the new brands:**
- **Scandia's** barrel-sauna kits (BS64-T to BS68-T) aren't on Scandia's own site, which lists pre-cut room kits, heaters and accessories.
- **Medical Saunas'** descriptions are marketing copy ("backed by over 48 doctors…") with almost no specs. Its numeric store SKUs ("37", "5335") are not taken as model numbers.
- **Leisurecraft** renders its specs in the browser. Only the title and the visible SKU are in the page, and only 3 CT models print a SKU.
- **SaunaLife** states specs in text. Wood is a mix (Thermo-Pine staves, Thermo-Aspen benches, spruce cradles), so it's withheld. Heaters are sold separately.

## 2. Matcher errors found in this batch, and fixes

Every one has a regression test (`tests/test_verified.py`, 105 tests). No rule was loosened.

| # | Brand | What it published | What the source said | Fix |
|---|---|---|---|---|
| 1 | Redwood (Grove) | heat type traditional | "…with upgrades available: / 9kW Homecraft Revive with Wi-Fi", an option-list item | list lines after an options header are excluded |
| 2 | Almost Heaven (Appalachia, Kuuma, Magnus, Timberline) | heat type | "**Choose** between a Harvia 8kW electric heater … or a … wood-burning" | "choose / choice / select" are option words |
| 3 | Salus hybrids ×6, Heavenly Heat Combination | heat type **lost** (ambiguous) | titled "Hybrid" / "Combination" in the data document, but the rendered page (no title) fell through to the description rule | the description is a fallback only when no document for the product states a type in its title |
| 4 | Golden Designs, Kaskinen | documented model numbers and electrical fell back to page grade | link attachment took over from model binding on line manuals | documents naming the brand's own model numbers go through model binding |
| 5 | SaunaLife (all 6) | held by R4 (no name) | the pages have no `<h1>`; the name is in `og:title` ("Model G3 - SaunaLife") | title falls back to og:title, then `<title>`, without the site name |
| 6 | Medical Saunas | 2 of 4 matched ("Traditional 7 … 4-Person" tied with `traditional-4`) | the lead slug `medical-sauna-traditional7` pins the product | model-in-URL matching; the manufacturer's test pages (`-new`, "testing", "-beta") are excluded |
| 7 | SaunaLife G11 | heat type traditional | "…for those who **elect to use** a wood-fired sauna stove" | "elect to / for those who / if you prefer" are option words |
| 8 | Scandia | wood "Cedar" | "We cut our **Spanish Cedar**…" | species added (Spanish, Eastern White, Northern White, Alaskan Yellow Cedar; Western Hemlock) |
| 9 | Medical Saunas | model number "37", "5335" | store item ids, not part numbers | a purely numeric SKU is not a model number |
| 10 | Dynamic Avila / Barcelona ×4 | **held by R5** for "1 vs 1–2" | "1-2 Person capacity (Compact Unit - **Ideal for 1 Person**)" | a count after "ideal for / best for / perfect for" is advice, not capacity |
| 11 | Almost Heaven Olympus, GD Hanko / Forssa, Salus Governor Mini ×2 | **held by R5** | "6 Person" vs "seating 5–6"; "2-3 Person" vs "2 person capacity" | R5 as your Part A rule defines it: a value **outside** another stated range. Nested statements withhold the capacity field with a note; the record is not quarantined |
| 12 | Scandia pre-cut kit | held by R5 | "Sizes 1-3 People From: … 4-8 People From: …" | a capacity in a "Sizes…" passage counts as size dependence |
| 13 | test harness | the determinism test rebuilt only brands with records, which silently rewrote the backlog without the blocked brands | — | the test rebuilds every configured brand and asserts on the backlog file too |

**Items 3, 5, 6, 10, 11 and 12 moved outcomes toward publication. Please confirm them.**
- 3 and 5 restore values that one of my own changes had wrongly removed.
- 10 and 11 stop R5 firing on statements your own rule defines as consistent.
- 11 and 12 withhold the capacity field rather than publishing either statement.
- **The choice of which consistent capacity to publish is left to you (R2-D6).**

**Values that changed because of the decisions** (audited line by line against the committed B2 dataset):
- **B2-D1:** 43 Maxxus and Dynamic records released. Values unchanged from the B2 audit.
- **B2-D2:** heat type added to 16 records (Almost Heaven 8, Redwood 8) and 3 Clearlight Premier records. Each snippet was read, and the option-sentence cases in errors 1, 2 and 7 were removed.
- **B2-D5:**
  - Salus Ally gained 30 A ("Heater: 6kw, 220V, 30-amp").
  - Sun Home Luminar 5's 30 A is now withheld. Its description also cites a sibling's "240V 20-amp" circuit.
- **B2-D3:** Sun Home (28), Heavenly Heat (7) and SaunaLife (7) documents attached. They produced no value that differed from the page and no documented value, because their pages name the series only in images or the figures are option tables.

## 3. Electrical coverage on published records

| Field | INH does not sell (158) | INH sells (83) |
|---|---|---|
| supply voltage | 40 (25%) | 47 (57%) |
| stated amperage | 42 (27%) | 45 (54%) |
| breaker amps | 1 (1%) | 0 |
| connection type (named plug / Hardwired) | 17 (11%) | 0 |
| dedicated circuit required | 22 (14%) | 0 |
| GFCI | 0 | 0 |
| labelled circuits | 12 records | 18 records |
| heater kW (traditional / hybrid) | 25 of 63 | 18 of 24 |
| heat type known | 116 of 158 | 74 of 83 |
| any `documented` electrical value | 5 | 23 |

**Parity is not there, and the cause is now the manufacturers, not the lead list:**
- **Golden Designs' family** (Golden Designs, Maxxus, Dynamic) states supply and amperage on nearly every page and publishes manuals the rules can bind to its model numbers. That is most of the "INH sells" column.
- **Among brands INH does not sell,** Clearlight and Sun Home state plugs and circuits; Almost Heaven and Redwood state almost nothing electrical, because heaters are buyer options.
- **Three brands INH sells** (Mande Spa, Kohler, Ripavi) publish nothing because their sites can't be reached.

## 4. Manufacturer-page inconsistencies (for the public conflict ledger)

Each is two statements on the **same manufacturer page** that cannot both be true, or a label the page itself doesn't support.

| # | Record | Rule | What the manufacturer's page states (verbatim) | Source |
|---|---|---|---|---|
| 1 | Golden Designs Bergen, 6 Person (GDI-8206-01) | R1 | "…6 person capacity **8.0 kw Stove**…" and "Electrical service: **240V / 30AMP (Stove)** and 120V / 15AMP (Control for Lights and Music)". 8 kW at 240 V = 33.3 A > 30 A | goldendesigninc.com/products/golden-designs-bergen… |
| 2 | Salus Aspire II, 6 Person | R1 | "…6 person capacity **8.0 kw Stove**…" and "Electrical service: **240V / 30AMP (Stove)** and 120V / 15AMP (Control for Lights and Music)" | salussaunas.com/products/aspire-ii-traditional-… |
| 3 | Salus Grand Governor | R5 | title "Grand Governor Traditional Outdoor Sauna - **6 Person**" vs specifications "**Max Capacity: 5** persons" | salussaunas.com/products/grand-governor |
| 4 | Almost Heaven Grayson, 4 Person | R2 | product type "**Hybrid Saunas**"; the page names no infrared system (its description names a Harvia 8kW heater) | almostheaven.com/products/grayson-4-person-indoor-sauna-copy |

Snippets, content hashes and fetch times for each are in `data/verified/saunas.json` (evidence) and `data/verified/conflicts.json`.

Three kinds of within-page difference were deliberately **not** put in this ledger, because they aren't contradictions:
- nested capacities such as "6 Person" and "seating 5–6";
- option tables;
- sibling-model mentions.

## 5. Blocked or failed sources

| Source | Why | Effect |
|---|---|---|
| mandespa.com | TLS handshake fails (`tlsv1 alert internal error`). Never bypassed | Mande Spa: 3 leads, nothing published |
| www.kohler.com | closes the connection on robots.txt (HTTP/1.1 and HTTP/2): unreadable, so skipped | Kohler: 2 leads |
| ripavi.com | times out (20 s) on robots.txt and every page | Ripavi: 2 leads |
| dynamicsaunas.com | self-signed certificate. Never bypassed | none: Dynamic is published from goldendesigninc.com (B2-D1) |
| maxxussaunas.com | "Launching Soon" placeholder | none, as above |
| almostheaven.com `/products.json` | 503 | read per product; 2 product JSONs failed (404 `nordik-indoor-saunas`, 503 `quick-ship-audra…`) |
| leisurecraft.com | specs render in the browser | only title and SKU verifiable |
| infraredsauna.com spec sheets and owner resources | PDF links load in the browser | no Clearlight documents |
| 8 Golden Designs manuals on Azure, 4 Salus PDFs | 404 | linked by the manufacturer but gone |

## 6. The full backlog

**Records held by rule (21, in `saunas.json` with `status: backlog`)**

| Rule | Count | Records |
|---|---|---|
| R3 identity | 18 | 12 Almost Heaven: six Quick Ship and standard pairs (Auburn, Blackwater Cube, Blackwater Mini-Cube, Grayson, Hillsboro, Salem), kept apart per D6. 6 Maxxus: "Far IR Sauna, 3 Person" ×4 and "Full Spectrum IR Sauna, 3 Person" ×2; one page in each group states no model number, so no distinguishing configuration exists |
| R1 electrical | 2 | Golden Designs Bergen, Salus Aspire II (§4) |
| R5 capacity | 1 | Salus Grand Governor (§4) |
| R2 hybrid | 1 | Almost Heaven Grayson (§4; also counted under R3) |

**Leads with no fetchable origin (26, in `data/verified/internal/backlog.json`)**

| Reason | Brand: leads |
|---|---|
| no page on the manufacturer's own site | **Scandia 7** (BS64-T to BS68-T, PRECUT-DIY-3X4-ULTRA, PRECUT-DIY-8X9-ULTRA) · **Dundalk 5** (CTC2245W, CTC22W, CTC2345, CTC66W, CTC88W) · **Maxxus 4** (MX-K306-01 CED, MX-K356-01 CED, MX-K406-01, MX-S206-01-ELITE) · **Almost Heaven 2** (FAMILY-S package, MK10005) · **SaunaLife 1** (SL-MODELG6-L-1) |
| origin site not fetchable | **Mande Spa 3** (MW12, MW16, MW20: TLS) · **Kohler 2** (robots unreadable) · **Ripavi 2** (timeouts) |

## 7. Round 2 decision list: public pages on metaobjects

Target: the hub at `/pages/sauna-database`, model pages at `/pages/sauna/[model]`. Shopify serves
metaobject web pages at `/pages/<type-handle>/<entry-handle>`, so a metaobject type with handle
`sauna` gives exactly that URL shape. **Things in the dataset or schema that would make Round 2
hard, each with a recommendation:**

| # | Issue | Why it matters | Recommendation |
|---|---|---|---|
| **R2-D1** | **Page handles.** `inh_id` slugs come from model numbers or manufacturer handles; 4 exceed 40 characters (e.g. `new-2023-model-maxxus-3-person-full-spectrum-infrared-sauna-canadian-red-cedar`). Almost Heaven's model numbers are pipe-joined package SKUs, and ids changed this round (Medical Saunas moved from store ids to handles) | a URL is permanent; an id that moves breaks links and splits ranking signals | freeze a separate `handle` field, `brand-model-name[-capacity]`, stored in the repo and never regenerated. Add a redirect table for any handle that changes |
| **R2-D2** | **Display titles are uneven** ("Scandia Diy PreCut Sauna Kit", "Golden Designs Far IR Sauna, 6 Person", "SaunaLife G3") | the title is the page's H1 and its title tag | fill `title-overrides.json` (B1-D9) from the manufacturers' own names, human-reviewed, **before** any page is built |
| **R2-D3** | **Record shape vs metaobject fields.** Records have up to 32 graded paths, and each is an object with evidence (median 10.8 KB, max 20.6 KB) | metaobject definitions cap the number of fields, and JSON fields have size limits | a few scalar fields for listing and filtering (brand, title, heat type, capacity, supply, kW, status) plus the full record in one JSON field, rendered by the template. Confirm the current Shopify limits against the Admin API first; don't assume them |
| **R2-D4** | **Backlog records have no public page** (21 by rule, 26 leads without origin) | a hub showing only published models could read as a curated catalogue | hub lists published models only, with a methodology page that states the backlog counts and reasons in aggregate. No page per backlog record |
| **R2-D5** | **The conflict ledger** (§4) names manufacturers | it is public criticism, even though it quotes their own pages | publish verbatim snippets with links and dates, plus a standing correction contact. Decide whether to notify the three manufacturers first (B2-D6 said not in Round 1) |
| **R2-D6** | **Consistent capacity statements** ("6 Person" and "seating 5–6") are withheld on 5 records | one missing number looks like a data gap | options: publish the widest stated range, or the title figure, or keep withheld. Recommend the widest stated range, labelled as the manufacturer's range |
| **R2-D7** | **Coverage parity** (§3): three brands INH sells publish nothing, and Almost Heaven and Redwood carry little electrical data | the Transparency Index depends on comparable coverage | show per-brand coverage openly ("the manufacturer does not state it") rather than hide thin brands. Human outreach to Mande Spa, Kohler and Ripavi for reachable spec sources |
| **R2-D8** | **Evidence snippets quote manufacturer marketing.** 3 records' snippets contain health wording ("detox", "cardiovascular") | CLAUDE.md gates health claims in code; snippets on a public page are content we publish | run every rendered snippet through `src/health_claims.py`. Show snippets as collapsed "source text" with quotation marks and a length cap |
| **R2-D9** | **`listed` vs `documented` vs `claimed`** need plain-language labels | readers and AI answer engines will quote them | methodology page defines each grade in one sentence, and every value shows its grade and source link |
| **R2-D10** | **D1: Infinite Sauna must not appear** on pages or in the methodology | the lead list is internal | describe it as "an internal lead list; nothing is published from it". Extend the build's D1 lint to the page templates |
| **R2-D11** | **Freshness.** Values are dated 2026-09-27 and 28; prices and specs move | a stale page is a wrong page | a scheduled re-fetch and re-verify (Actions has the egress), with `observed_at` shown. Changes on refresh go to a human before they publish, like `check_facts_drift --accept` |
| **R2-D12** | **Offers.** Only single-variant manufacturer-direct prices are recorded; INH offers are not in the dataset | the clause allows featuring a retailer, never changing a record | add INH as an offer from the Shopify Admin API, marked `inh_sells: true`, and keep it out of every verified field |
| **R2-D13** | **The metaobject template is a theme file in MAIN** | a live-theme write | follow the Round 18 path: snapshot first, `--allow-live-theme-id`, two-pass deploy, a walked rollback |
| **R2-D14** | **Structured data** | Product markup invites review and price rich results | mark up only verified fields (brand, model, name). No `aggregateRating`, and no `offers` unless R2-D12 lands |
| **R2-D15** | **The intermittent test failure below** | a flaky gate trains people to rerun until green | investigate `tests/test_blotato_rest.py` under load before Round 2 depends on the suite |

## 8. Gates

| Gate | Result |
|---|---|
| jsonschema (schema 0.3.0, plus `provenance.origin_basis`) on every record | ✅ in the build lint |
| inhousewellness.com rejected as a source; non-allow-listed retailer rejected; shared CDN needs the brand's shop path | ✅ tests |
| Rebuild from cache byte-identical, including the backlog | ✅ twice, plus a test |
| Full suite | ✅ **654 passed** in each of the last three full runs. All 637 prior tests are included; no prior assertion changed state |
| ⚠️ Intermittent failure | **One of five full runs reported "1 failed"** and was not reproduced in three full reruns or three targeted reruns. Pytest's cache points at pre-existing tests in `tests/test_blotato_rest.py` (the Blotato publish-poll tests), outside this round's code. Unresolved: R2-D15 |
| preflight `--self-test / --static / --imports` | ✅ clean |
| Missing-value lint | ✅ 0 |
| `check_facts_cache` / `check_facts_drift` | ✅ |
| API spend | **$0** |
