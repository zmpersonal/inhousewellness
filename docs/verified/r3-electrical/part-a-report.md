# Database Round — Electrical Coverage for Priced INH Saunas: Part A report

2026-10-07 · branch `verified/r3-electrical-coverage` (from `325a74b`) · **nothing written to Shopify, no record changed**

Reproduce everything (offline, read-only):

```bash
.venv/bin/python scripts/electrical_extract_candidates.py      # -> docs/verified/r3-electrical/candidates.json (~7 min)
.venv/bin/python scripts/electrical_review_sample.py           # -> review-sample.json (every span read from its document)
```

## 0. What changes the plan

1. **The publish lever is mostly not electrical.**
   - None of the 25 unpublished-but-mapped records meets the threshold.
   - **13 already state a circuit** but lack exterior dimensions.
   - 6 of those 13 have "Exterior (WDH): …" in the manufacturer's own product entry. The build
     missed it (STATED-MISSED).
   - Every one of the 25 also lacks an approved title and a frozen handle. Those are human
     approvals (R2-D1/D2).
2. **Cached manuals add little for records that exist, under strict binding.**
   - 2 not-live records gain a circuit bound to their own model row.
   - 5 more need a binding class you haven't approved: SHARED_HEADING.
3. **The biggest single lever is new records:** 18 of the 74 missing saunas have an
   "Electrical service:" statement in the manufacturer's own product entry, already in our cache.
4. **I found and fixed two errors of my own, and corrected one in Part B's scope file.**
   - The first binder read the previous line's label and bound Dynamic's "120VAC 20AMP"
     to DYN-6215-05; its row says 15 A.
   - Read whole, a multi-product Shopify catalogue let one heater mention mark everything
     HEATER_TABLE, and let other products' sentences count for every record citing it.
   - That same artifact inflated Part B's "83 live records cite a breaker figure":
     - all 13 Redwood hits are heater packages sold separately;
     - the Sun Home "15A breaker" sentence belongs to a cold plunge.
   - Both rules are now same-line and own-entry-only.
5. **No wire gauge or breaker is bound to any priced sauna in our cache.** Every bound breaker or
   wire figure found belongs to non-priced live records (Sun Home Nova 3/6, Salus) or to heater
   packages.

## 1. Scope check (§5)

- **The token in `InHouseWellness/.env`, which every script loads, still lacks all four
  metaobject scopes.**
- **The new token is in `InHouseWellness/tool-electrical/.env`** (modified 2026-10-07 12:04). It
  has `read_metaobjects`, `write_metaobjects`, `read_metaobject_definitions` and
  `write_metaobject_definitions`. **PASS** for this check.
  - Used by loading it into the environment per command. Neither `.env` was edited, and no value
    was read or printed.
- **The new token has 10 scopes (old: 18). Dropped:**
  `read/write_online_store_pages`, `write_online_store_navigation`, `read_online_store_navigation`,
  `read/write_publications`, `read/write_files`, `read/write_product_feeds`, `read_orders`,
  `read_all_orders`.
  - It still reads the hidden electrical pages (via `read_content`).
  - Page **writes** are untested; see D9.
- **The metaobject definition stores the record as JSON** (`record` field), so wire gauge needs
  **no** definition change.

## 2. Counts before any write, and projected coverage

**Today: 38 of 139 priced saunas show a manufacturer-stated circuit (27.3%).**

| Source of improvement | Priced saunas it could add | Conditions |
|---|---|---|
| Extraction from cached manuals, records already live | 0 strict; **+1** with D2 | DYN-6215-05 Lucca Elite: the DB already holds 15 A; the tool's quote builder needs the same trailing-label rule (D2) |
| Extraction, then publishing existing records (25) | **+2** strict | GDI-8040-03, MX-J306-02S: bound rows, then they meet the threshold. Needs titles and handles (D7) |
| …with SHARED_HEADING (D1) | **+5** | GDI-6996-01, GDI-8230-01, GDI-8260-01, GDI-B002-01, GDI-B004-01. The two barrels state a **lighting** circuit only (D4) |
| …with exterior-dimension extraction (D5) | **+6** | GDI-8203/8202/8222/8223/8506/8526: circuits already stated; "Exterior (WDH)" in the manufacturer entry |
| New records from manufacturer product entries (cached) | **up to +18**, ~9 meeting the threshold from the entry alone | Dynamic 11, Golden Designs 5, Maxxus 2 (D6) |
| New records from manuals on **our** product pages | up to ~10 (Maxxus line manuals) | D3; each manual re-read and bound to the SKU's model number |
| The remaining 19 with nothing cached | not estimated | needs online fetches under the source policy (D11) |
| Stay unpublished, reasons known | — | 7 of the 13 (no exterior dims stated anywhere cached); 4 with no bound electrical; Scandia DIY kit missing everything |

**Projected coverage:**

| Scenario | Stated circuit | Share |
|---|---|---|
| Strict (ROW/HEADING only, publish only what meets the threshold, ~9 new records) | ≈ 49 | **≈ 35%** |
| + D2 + D1 (excluding the 2 lighting-only) | ≈ 53 | ≈ 38% |
| + D5 | ≈ 59 | ≈ 42% |
| + D3 | ≈ 69 | ≈ 50% |

- **Every scenario stays under 60% without new online fetches** (D11).
- These are upper bounds until the build runs. New records must pass the unchanged threshold,
  which the build decides.

## 3. Wire gauge: proposed schema change (tested, then reverted)

`docs/verified/r3-electrical/wire-gauge-schema.diff`:
- adds `electrical.wire_gauge` to the schema (required, same `field` shape as every electrical
  field);
- `value` is the **stated text verbatim** ("10 AWG minimum", "#8 copper wire"), never normalised,
  never derived from amperage;
- the build sets it `not_verified` until a reviewed extraction fills it.

Tested on the branch, then reverted (Part A writes no records):

| Check | Result |
|---|---|
| Baseline rebuild with no change | byte-identical to the committed `saunas.json` (the build is deterministic) |
| Rebuild with the field | 263 records; **0 differ** except for the added field |
| Model-page data (`verified_pages --build`) | **byte-identical** with and without the field, so nothing on the live site changes |
| **Tests** | **877 pass** |

**One constraint:** a Part B test asserts no quote in the electrical tool contains a wire size.
Wire gauge stays **data-only** this round unless you approve changing that assertion (D10).

## 4. Review sample: 20 proposed extractions, 6 brands, 5 from line manuals

Spans are copied from the documents by `scripts/electrical_review_sample.py`; a span that does not
match its document fails the script. Coverage effect:
- P01–P05, P07, P10 (via D2): priced records not showing a circuit today.
- P06, P08, P12: new records.
- P09: new record via D3.
- P11: adds a manual source to a live priced record.
- P13–P20: non-priced live records (they improve the tool, not the priced metric).

**Binding notes on the sample:**
- **P13–P16:** my automated check missed the heading binding (the record has no model-number
  token). It was confirmed by reading the guide. The cover reads "Nova Indoor Traditional Sauna
  3-Person" (and 6-Person), the guide names no other model, and the rows sit in that model's own
  spec block beside "Heater Output 6 kW".
- **P17:** stored verbatim as one option-dependent statement, never reduced to one figure.

| # | Brand | Model | Field | Verbatim span | Document | Page | Fetched | Binding | Why it holds |
|---|---|---|---|---|---|---|---|---|---|
| P01 | Golden Designs | GDI-8040-03 (not live) | circuit | “GDI-8040-03 FS – TWO SEPARATE 120V/15AMP DEDICATED CIRCUITS REQUIRED” | [e0317a76-b683-4d0a-b032-31209286b213.p](https://goldendesignstorage.blob.core.windows.net/product/e0317a76-b683-4d0a-b032-31209286b213.pdf) | 1 | 2026-09-28 | ROW · line manual | line manual; the row opens with GDI-8040-03 and the figure follows on the same line. NOTE: this PDF now answers 404 (rule 7); the value was read from the copy fetched 2026-09-27 |
| P02 | Golden Designs | GDI-6996-01 Monaco (not live) | circuit | “DYN-6996-01-Elite / GDI-6996-01 6 Person FAR Infrared Sauna ULTRA LOW/NEAR ZERO EMF INFRARED CARBON MODEL SAUNAS FOR INDOOR USE ONLY REQUIRES 2 SEPARA” | [6159c090-d7c4-4bb8-9b7e-2fd6aabc4f96.p](https://goldendesignstorage.blob.core.windows.net/product/6159c090-d7c4-4bb8-9b7e-2fd6aabc4f96.pdf) | 1 | 2026-09-28 | SHARED_HEADING | the cover names DYN-6996-01-Elite / GDI-6996-01 (one model, two brands) and states one requirement for both; no other statement differs |
| P03 | Golden Designs | GDI-8230-01 (not live) | circuit | “GDI-8230-01 / GDI-8260-01 3 and 6 Person Infrared Saunas Owner’s Manual CARBON MODEL SAUNA SAUNA IS FOR INDOOR USE ONLY Two 120VAC 15AMP Separate Dedi” | [fc9832dc-8cf0-4df4-9cf4-5b31d9efa65d.p](https://goldendesignstorage.blob.core.windows.net/product/fc9832dc-8cf0-4df4-9cf4-5b31d9efa65d.pdf) | 1 | 2026-09-28 | SHARED_HEADING | the cover names GDI-8230-01 / GDI-8260-01 and states one requirement for both |
| P04 | Golden Designs | GDI-8260-01 (not live) | circuit | “GDI-8230-01 / GDI-8260-01 3 and 6 Person Infrared Saunas Owner’s Manual CARBON MODEL SAUNA SAUNA IS FOR INDOOR USE ONLY Two 120VAC 15AMP Separate Dedi” | [fc9832dc-8cf0-4df4-9cf4-5b31d9efa65d.p](https://goldendesignstorage.blob.core.windows.net/product/fc9832dc-8cf0-4df4-9cf4-5b31d9efa65d.pdf) | 1 | 2026-09-28 | SHARED_HEADING | same cover as P03 |
| P05 | Golden Designs | GDI-B002-01 St. Moritz barrel (not live) | circuit | “GDI-B002-01/GDI-B004-01/GDI-B006-01 OWNER’S MANUAL FOR BARREL MODEL SAUNAS REQUIRES 120VAC 15 AMP CIRCUIT (FOR THE LIGHTING)” | [50a61a79-33b5-4845-a40f-7bd2e3a9b37e.p](https://goldendesignstorage.blob.core.windows.net/product/50a61a79-33b5-4845-a40f-7bd2e3a9b37e.pdf) | 1 | 2026-09-28 | SHARED_HEADING | the cover names the three barrel models and one LIGHTING circuit; the heater is not covered by this statement (decision D4) |
| P06 | Golden Designs | golden-designs-6-person-traditional-sauna (new record) | circuit | “Electrical service: 240V / 30AMP (Stove) and 120V / 15AMP (Control for Lights and Music) (Please consult a certified electrician.)” | [golden-designs-bergen-6-person-outdoor](https://goldendesigninc.com/products/golden-designs-bergen-6-person-outdoor-indoor-traditional-sauna-gdi-8206-01-canadian-red-cedar-interior) | — | 2026-09-27 | HEADING | the manufacturer's own product entry for this SKU (exact SKU match); a single-product entry, so its title binds the statement |
| P07 | Maxxus | MX-J306-02S (not live) | circuit | “MX-J306-02S - 120VAC 20AMP Dedicated Circuits Required” | [1f460185-8ba0-41de-8d3e-daa8901dae39.p](https://goldendesignstorage.blob.core.windows.net/product/1f460185-8ba0-41de-8d3e-daa8901dae39.pdf) | 1 | 2026-09-28 | ROW · line manual | line manual; the row is labelled MX-J306-02S on the same line (the MX-J206-02S row above it carries 15AMP) |
| P08 | Maxxus | maxxus-s-line-mx-s306-01-fs (new record) | circuit | “Electrical service: Special Electrical 120 V/20 AMP Non GFCI dedicated receptacle and breaker (Not 220/240 V) (Please consult a certified electrician.” | [new-2024-model-s-edition-mx-s306-01-ma](https://goldendesigninc.com/products/new-2024-model-s-edition-mx-s306-01-maxxus-full-spectrum-infrared-sauna-pacific-cedar) | — | 2026-09-27 | HEADING | manufacturer product entry for this exact SKU |
| P09 | Maxxus | MX-K406-01 CED, maxxus-4-person-sauna-cedar (new record) | circuit | “MX-K306-01/MX-K406-01 - 120VAC 20AMP Dedicated Circuits Required” | [uc?export=download&id=1Dnken6EoldJv5kO](https://drive.google.com/uc?export=download&id=1Dnken6EoldJv5kOHAjMz9DOIeMUO3w3S) | 1 | — | ROW · line manual | line manual; label group MX-K306-01/MX-K406-01 precedes the figure. SOURCE: a manual on OUR product page (Drive), no manufacturer-hosted copy cached (decision D3) |
| P10 | Dynamic | DYN-6215-05 Lucca Elite (live) | circuit | “120VAC 15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05)” | [decfec20-c43b-4bbb-967a-da840e5edfdc.p](https://goldendesignstorage.blob.core.windows.net/product/decfec20-c43b-4bbb-967a-da840e5edfdc.pdf) | 1 | 2026-09-28 | ROW_TRAILING · line manual | line manual, spec-then-label: the parenthesised label follows its own requirement on the same line (decision D2). The DB already holds 15 A for this record; the tool drops the quote |
| P11 | Dynamic | DYN-6115-05 Veneto (live) | circuit | “120VAC 15AMP Dedicated Circuit Required (DYN-6115-05/DYN-6215-05)” | [decfec20-c43b-4bbb-967a-da840e5edfdc.p](https://goldendesignstorage.blob.core.windows.net/product/decfec20-c43b-4bbb-967a-da840e5edfdc.pdf) | 1 | 2026-09-28 | ROW_TRAILING · line manual | same line as P10; adds a documented-grade source to a value now listed from the product page |
| P12 | Dynamic | dynamic-bellagio-3-person (new record; our SKU DYN-6306-02 is a variant of the DYN-6306-01 Bellagio entry) | circuit | “Electrical service: Special Electrical 120 V/20 AMP Non GFCI Dedicated Receptacle and breaker (Not 220/240 V) (Please consult a certified electrician.” | [dyn-6306-01-dynamic-low-emf-far-infrar](https://goldendesigninc.com/products/dyn-6306-01-dynamic-low-emf-far-infrared-sauna-bellagio-edition) | — | 2026-09-27 | HEADING | manufacturer product entry for this exact SKU |
| P13 | Sun Home | Nova 3 (live) | breaker | “Circuit Breaker 30 A (HUUM Table 2)” | [SUN_HOME-NOVA_3-ASSEMBLY_GUIDE-v1.2-20](https://cdn.shopify.com/s/files/1/0570/7418/8481/files/SUN_HOME-NOVA_3-ASSEMBLY_GUIDE-v1.2-2026-09.pdf) | 6 | 2026-09-28 | HEADING | single-model assembly guide; its cover names the Nova 3. The row cites HUUM's table but is printed in the Nova 3's own spec block |
| P14 | Sun Home | Nova 3 (live) | wire_gauge | “Minimum Wire Size 10 AWG minimum (HUUM Table 2)” | [SUN_HOME-NOVA_3-ASSEMBLY_GUIDE-v1.2-20](https://cdn.shopify.com/s/files/1/0570/7418/8481/files/SUN_HOME-NOVA_3-ASSEMBLY_GUIDE-v1.2-2026-09.pdf) | 6 | 2026-09-28 | HEADING | same spec block as P13 |
| P15 | Sun Home | Nova 6 (live) | breaker | “Circuit Breaker 40 A (HUUM Table 2)” | [SUN_HOME-NOVA_6-ASSEMBLY_GUIDE-v1.2-20](https://cdn.shopify.com/s/files/1/0570/7418/8481/files/SUN_HOME-NOVA_6-ASSEMBLY_GUIDE-v1.2-2026-09.pdf) | 6 | 2026-09-28 | HEADING | single-model guide for the Nova 6 |
| P16 | Sun Home | Nova 6 (live) | wire_gauge | “Minimum Wire Size 8 AWG minimum (HUUM Table 2)” | [SUN_HOME-NOVA_6-ASSEMBLY_GUIDE-v1.2-20](https://cdn.shopify.com/s/files/1/0570/7418/8481/files/SUN_HOME-NOVA_6-ASSEMBLY_GUIDE-v1.2-2026-09.pdf) | 6 | 2026-09-28 | HEADING | same spec block as P15 |
| P17 | Almost Heaven | Allegheny cabin 6-person (live; shows no circuit today) | circuit | “8kW/9kW/10.5kW, 240V, 40/45/50-amp requirement, hard-wire connect” | [allegheny-6-person-cabin-sauna](https://almostheaven.com/products/allegheny-6-person-cabin-sauna) | — | 2026-09-28 | HEADING | the model's own product page. OPTION-DEPENDENT: one statement maps three heater options to three circuits in order; stored verbatim as stated, never split into a single number |
| P18 | Almost Heaven | Allegheny cabin 6-person (live) | circuit | “Lighting electrical: 110V, 15-amp service, plug-in connect” | [allegheny-6-person-cabin-sauna](https://almostheaven.com/products/allegheny-6-person-cabin-sauna) | — | 2026-09-28 | HEADING | same page; the lighting circuit is a second, separate statement |
| P19 | Salus | Solara 6-person (live) | breaker | “Traditional Heater: 8kW, requires a 40 amp breaker” | [solara-traditional-outdoor-sauna-6-per](https://www.salussaunas.com/products/solara-traditional-outdoor-sauna-6-person) | — | 2026-09-27 | HEADING | the model's own product page; the 8kW heater is the one this cabin ships with |
| P20 | Salus | Renew II 2-person (live) | breaker | “Traditional Heater: 6kW, requires a 30 amp breaker” | [renew-ii-traditional-indoor-sauna-2-pe](https://www.salussaunas.com/products/renew-ii-traditional-indoor-sauna-2-person) | — | 2026-09-27 | HEADING | the model's own product page |

| # | Brand | Model | Span | Page | Why rejected |
|---|---|---|---|---|---|
| R01 | Dynamic | DYN-6215-05 | “(DYN-6115-05/DYN-6215-05) 120VAC 20AMP Dedicated Circuit Required (DYN-6315-05)” | 1 | OTHER_MODEL: my first binder read the previous line's label and bound 20AMP to DYN-6215-05. The 20AMP row is labelled DYN-6315-05. Fixed: same line only |
| R02 | Salus | Flora 3-person | “8.0kW KIP Heaters • 40-amp double pole breaker • 240 volts • 1 Phase • 8/2 wire” | 26 | HEATER_TABLE: a table for Harvia KIP heaters bundled in the cabin manual; binds to the heater, not the cabin (stays empty; the record links p. 26) |
| R03 | Sun Home | Equinox, Luminar, Solstice, Solaris (10 live records) | “connect to a dedicated 110–120V GFCI circuit with a 15A breaker, then plunge” | — | OTHER PRODUCT: the sentence is in Sun Home's PORTABLE COLD PLUNGE catalogue entry; Part B's scope file attributed it to every Sun Home sauna citing the catalogue |
| R04 | Dynamic | DYN-6996-01 Elite | “1-2 Person FAR Infrared Sauna CARBON MODEL SAUNA FOR INDOOR USE ONLY 120VAC 15AMP Dedicated Circuit Required” | 1 | WRONG DOCUMENT: the cover is a 1-2 person model; the record is a 6-person Monaco. (P02's cover names DYN-6996-01-Elite and is the right document) |
| R05 | Maxxus | MX-K406-01-ZF (ced, hem) | “120V/15AMP DEDICATED CIRCUIT REQUIRED FOR MX-M206-01” | 1 | OTHER_MODEL: the cited line manual covers MX-M206/M306 only; the K406-ZF is not in it. The our-page K406 manual (P09) names MX-K406-01 without -ZF: variant mismatch, left empty |
| R06 | Scandia | barrel sauna kits (6) | “wire gauged between 10 AWG – 4 AWG” | 2 | AMBIGUOUS: a kit manual with no model number, and a RANGE across heater sizes; not a value for any one model |
| R08 | Redwood Outdoors | all 13 live Redwood records | “Requires a 40-amp breaker and #8 copper wire” | — | OTHER PRODUCT: every Redwood breaker/wire statement is in a separately sold HEATER PACKAGE entry of the catalogue, not a sauna. Part B's scope file counted all 13 because they cite the same catalogue: corrected here |
| R07 | Maxxus | every K-series record | “(120VAC 15AMP Dedicated Circuit or 120VAC 20AMP Dedicated Circuit)” | 27 | TEMPLATE either-or sentence in the body; states no requirement for any model |

## 5. The 74 missing priced saunas: sources reachable, by brand

`docs/verified/r3-electrical/missing-74-sources.json`, one row per product.

| Brand | Missing | In a cached manufacturer source | …with "Electrical service" in its own entry | Manual linked from **our** page (PDF read) | Same-size manufacturer copy of that manual cached | Brand in source registry |
|---|---|---|---|---|---|---|
| Golden Designs | 6 | 6 | 5 | 3 (1) | 1 | yes |
| Maxxus | 21 | 16 | 2 | 12 (12) | 5 | yes |
| Dynamic | 13 | 12 | 11 | 2 (0) | 0 | yes |
| Scandia | 7 | 0 | — | 7 (7) | 0 | yes |
| SaunaLife | 7 | 0 | — | 6 (6) | 0 | yes |
| Dundalk Leisurecraft | 6 | 1 | 0 | 6 (6) | 0 | yes (robots 404: allowed under the extended rule) |
| Medical Saunas | 4 | 0 | — | 1 (0) | 0 | yes |
| Finnmark Designs | 3 | 0 | — | 3 (3) | 0 | **no** |
| Mande Spa | 3 | 0 | — | 3 (3) | 0 | yes (TLS alert in Round 1) |
| Kohler | 2 | 0 | — | 0 | 0 | yes (skipped: robots connection closed) |
| Ripavi | 2 | 0 | — | 2 (2) | 0 | yes (unreachable in Round 1) |

- In the recorded electrical passages of the our-page manuals, only **Maxxus** (12) and
  **Golden Designs** (1) show a model-labelled circuit.
- **Scandia's** five state a kit-wide wire range with no model (R06).
- Dundalk, SaunaLife, Finnmark, Mande and Ripavi show none in the recorded passages. Those
  passages are excerpts, so a full re-read in Part B is still needed before calling any of them
  empty.
- 9 of the 74 have no usable SKU in our catalogue, so they cannot be matched exactly.

## 6. Decisions needed

**D1. SHARED_HEADING binding.**
- What it is: a cover that names this model among others and states one requirement for all, with
  no listed model given a different figure anywhere in the document.
- Options:
  - (a) accept (+5);
  - (b) reject.
- **Recommend (a).** Your rule 1 names "heading", and the guard demotes any cover contradicted
  elsewhere.

**D2. ROW_TRAILING binding** ("…Required (DYN-6115-05/DYN-6215-05)", same line).
- Options:
  - (a) accept for extraction **and** let the tool's quote builder apply the same rule, a one-rule
    change to `electrical_build.py` with tests;
  - (b) extraction only;
  - (c) reject.
- **Recommend (a).** Without it, Lucca Elite stays blank in the tool although the database holds
  its 15 A. CLAUDE.md's "adjacency-after is layout" case is an unlabelled figure; this one is a
  parenthesised label.

**D3. Manuals hosted on our own product pages (Google Drive).**
- Options:
  - (a) never;
  - (b) only when byte-identical to a manufacturer-hosted copy, then cite the manufacturer's URL;
  - (c) allow, cited as "manufacturer manual, copy hosted by InHouse Wellness".
- **Recommend (b),** with (c) only on your explicit approval. Editorial independence bars our
  pages as evidence. A byte-identical copy proves the document is the manufacturer's without
  relying on us.

**D4. Lighting-only circuits** (GDI-B002/B004 barrels: "REQUIRES 120VAC 15 AMP CIRCUIT (FOR THE
LIGHTING)").
- **Recommend:** record them and let the tool quote them verbatim, since the quote says what it
  is. Count them separately as "lighting circuit only", **not** in the headline coverage.

**D5. Exterior dimensions for 6 STATED-MISSED records.**
- The question: extract "Exterior (WDH)" from the manufacturer entry under the same verbatim
  rules, so 6 records that already state a circuit can meet the unchanged threshold.
- **Recommend: yes.** It is a database fix, not a threshold change.

**D6. New records from manufacturer product entries** (18). Add the SKUs as build leads, one record
per INH SKU, exact SKU match.
- **Variants:** some match a *variant* inside another product's entry (P12: DYN-6306-02 inside the
  6306-01 Bellagio entry). Each is checked against existing live records so no duplicate model
  page is created.
- **Recommend: yes,** with the duplicate check as a gate.

**D7. Titles and handles.** Anything newly published needs an approved title and a frozen handle
(R2-D1/D2).
- **Recommend:** Part B writes the records, prepares a title-review CSV, and **pauses for your
  approval before any activation.** That is a planned mid-round stop.

**D8. Dead Golden Designs PDFs.** GDI-8040-03's value (P01) and the Reserve Edition manual link come
from `e0317a76…pdf`, which now 404s.
- **Recommend:**
  - look in Golden Designs' current product entry for a replacement PDF;
  - if found with the same statement, re-cite it;
  - if not, keep the value with its original fetch date and sha256, drop the live link, and log
    it (rule 7).

**D9. Token placement and dropped scopes.**
- Please move the new token into `InHouseWellness/.env`, where every script reads it.
- Part B must **update the six hidden pages' bodies** (answer-page counts change). That may need
  `write_online_store_pages`, which the new token dropped.
- Options:
  - (a) restore `write_online_store_pages` now;
  - (b) I attempt the update in Part B and stop if Shopify refuses.
- **Recommend (a).**

**D10. Wire gauge in the tool.**
- Options:
  - (a) data-only this round;
  - (b) display it, which changes a Part B assertion (no wire size in any quote).
- **Recommend (a).** Very few models gain one (none priced), and the assertion change deserves
  its own review.

**D11. Online fetches.**
- For the 19 with nothing cached and the brands known only from our pages: fetch the
  manufacturers' sites under the source policy (robots first, 1 request per 2 s, honest user agent).
- Finnmark needs adding to `data/verified/sources.json`, a registry change you approve.
- **Recommend:** yes for the registered brands. Finnmark only if you approve its domain.

---

*Part A stops here. No record, schema, theme, page or metaobject has been changed.*
