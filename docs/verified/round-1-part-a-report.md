# InHouse Wellness Verified — Round 1, Part A report

**Status: 🟡 REVIEW. Part B is not started and waits on your approval.**
Branch `verified/r1-data-foundation`. Nothing merged, nothing deployed, no theme touched,
no Shopify write, no commit to Infinite Sauna. Anthropic API spend: **$0**.

Input: `data/verified/upstream/infinite-sauna-2026-09-21.json`, release 2026-09-21,
sha256 `7b3c609c…9f5`. Dry run: `python3 scripts/verified_import.py --dry-run`, run twice,
byte-identical report both times.

---

## 1. Grounding answers

### 1.1 How the calculator looks up heater kW today

- The browser reads `assets/inh-cost-tables.json` (139 products, built from
  `data/cost-tables.json` by `scripts/build_cost_tables.py`). Each product has a `kw` object
  `{v, src, at, span, unit}` or `{v: null, reason}`.
- `assets/inh-cost-core.js` `powerState()` uses `product.kw.v` when it is present. Otherwise it
  asks the reader for their spec-plate figure, and if they decline it leaves running cost out.
  It never estimates.
- The kW values come from our own Shopify metafields (`custom.electrical_requirements`, …) and
  from manual PDFs, with Infinite Sauna used only for `type` and `indoor_outdoor`.
  **47 of 139 products have a kW value.**

⚠️ **A finding in the live calculator. I have not acted on it.** Two of those 47 values are
recommendations, not ratings, so they break the project's own rule that *a recommendation is not a
rating*. The manual path has the guard. The metafield path does not:

| Handle | kW shown | Span |
|---|---|---|
| `ct-georgian-cabin-sauna` | 8.0 | "An 8 kW electric heater is **recommended** for optimal performance" |
| `leisurecraft-granby-2-3-person-cabin-sauna` | 6.0 | "a 6 kW electric heater is **recommended** for optimal performance" |

The live calculator therefore prints a running cost for those two cabins based on a heater they
might not have. See decision D8.

### 1.2 What Infinite Sauna actually publishes

`https://infinitesauna.com/data/` lists **291 records across 16 brands**, release 2026-09-21.
The CSV and JSON have the same 291 keys and agree on every field I compared.

| JSON field | Present on | Notes |
|---|---|---|
| `model_key`, `brand`, `model`, `title`, `type`, `placement` | 291 | `model` is sometimes a URL slug (Clearlight, Kohler) or a pipe-joined package (Almost Heaven `cabin\|heater\|LED`) |
| `price`, `reference_price` | 291 | |
| `inhouse_url`, `image`, `data_completeness` | 291 | 114 records have an INH URL |
| `source_urls` | 291 | **record-level list**, 1–9 URLs. None is a manual |
| `retailer_offers[]` | 291 | `{retailer, url, price, reference_price, source_type, checked_at}` |
| `capacity` | 279 | one integer, so ranges are lost |
| `wood` 154 · `spectrum` 133 · `voltage` 97 · `red_light` 91 · `emf` 88 · `amperage` 87 · `heater` 84 · `max_temp` 83 · `heater_kw` 79 · `weight` 76 · `plug` 35 · `warranty` 32 · `exterior_dimensions` 9 · `interior_dimensions` 3 | | strings like `"8.0 kW"` and `"120V/240V"` |

CSV-only columns: `ir_wattage` (empty on all 291) and `retailers` (names joined with `|`).

**Sources are recorded per record only, never per field.** Its methodology page describes a
source hierarchy (A manuals > B manufacturer pages > C authorised retailers > D secondary), but
the data never says which level a given value came from. Of the source URLs, 120 are
inhousewellness.com and none are manuals. So:

- **No imported value can be `documented`.** A manual is never cited.
- **No imported value can name the page it came from.**
- **Every imported factual value is graded `listed`**, the lowest factual grade, with
  `source_type: secondary_dataset_record_level`. The schema rejects any higher grade for that
  source type. Marketing terms are `claimed`. Everything else is `not_verified`.
- **`amperage` does not say whether it is the breaker size or the current draw.** One record
  says `1.2A`, which is clearly a draw. So it does not go into `breaker_amps` (decision D2).
  Rule 1 still holds under either reading: watts ÷ volts above the stated amperage is
  impossible whether that amperage is the breaker or the draw.
- `plug` holds the banned phrase on 33 records. It names no plug, so those import as
  `not_verified` and the phrase appears **0 times** in the output.
  `NEMA10-30R` (Scandia BS64-T) is a **receptacle**, not a plug, so it is `not_verified` too.

**Two facts that bear on "neutral":**

1. **Infinite Sauna is one of our own properties.** It is listed in `linkbuilding/owned.json`
   and in the validator's satellite allow-list, and its own methodology says INH is
   "commercially featured".
2. **Some of the sourcing is circular.** All 114 INH-sold records cite inhousewellness.com, 30
   cite *only* inhousewellness.com, and 13 of the INH-sold records that carry electrical values
   are sourced only from our own pages. INH Verified citing Infinite Sauna, which cites INH, is
   not independent evidence. See D1 and D3.

**Upstream moves fast.** The copy cached in the repo on 2026-09-15 had 195 rows, 25 of them
Hybrid. Six days later there are 291 rows and 8 Hybrid. Every import must pin the file's sha256,
and tests must pin fixtures, never live values (CLAUDE.md: never assert a literal value from
refreshed external data).

### 1.3 Where the dataset should live

| Option | Crawlable per-model page | Theme slot | Versioned and testable | Cost |
|---|---|---|---|---|
| A. Repo JSON built into a theme asset | **No.** Liquid can't loop a JSON asset into server-rendered pages. The browser would have to render it, which crawlers and AI answer engines read poorly | 0 | ✅ | Low |
| B. Shopify metaobjects only | ✅ with the Online Store capability: one template, one URL per entry | 0 new; one template file goes into MAIN | ❌ No diff, no determinism gate. The store becomes the source of truth | Medium |
| **C. Both: repo JSON is the source of truth, a sync step writes metaobjects** | ✅ | **0 new themes** | ✅ The importer, rules, lint and schema all run on the repo copy | Medium |

**Recommendation: C.** This round only produces the repo half. Theme slots don't come into it,
because no new theme is needed. CLAUDE.md records **18 of 20** as of 2026-09-15 and your brief
says 17. I did not re-check live because nothing in this round depends on it. To check before
Round 2: that the Admin token has the metaobject write scopes (the Actions token already lacks
`write_online_store_navigation`), and the per-definition field limits. Storing each graded object
in a JSON-type field should keep us well inside those limits, but that needs confirming.

---

## 2. Proposed schema

`data/verified/schema/inh-verified.schema.json` (JSON Schema 2020-12). The key points:

- **Every factual field is `{value, unit, grade, source_url, source_type, observed_at, note}`**
  and allows no extra keys.
- **The schema enforces as much as it can see:**
  - `not_verified` / `not_applicable` ⇒ `value: null`, and any other grade ⇒ a non-null value,
    a `source_url` and `observed_at`
  - `documented` ⇒ the source is a manual or spec sheet
  - `certified` ⇒ the source is a safety listing
  - `modeled` ⇒ the source is an INH formula and a note is present
  - `secondary_dataset_record_level` ⇒ the grade can be at most `listed`
- **Electrical fields are split as briefed:**
  - `supply_voltage` accepts only `120V` / `240V` / `208–240V`
  - `connection_type` must match `NEMA x-yyP` or `Hardwired`
  - `circuit_requirement` accepts only `Dedicated required`. **There is no shared-circuit value
    anywhere in the schema.** "Not documented" is stored as `not_verified`
  - `gfci` accepts only `Required`
  - `breaker_amps` and `heater_kw` are numbers
  - One proposed addition: `stated_amperage` (D2)
- **Identity:** brand, model number (a slug becomes `not_verified`, "Model number not
  documented"), `package_components`, model name, configuration, `display_title` (derived, no
  ®/™), and `aliases` for merged listings.
- **Other blocks:**
  - `category` is `sauna` | `cold_plunge`. A plug forces `heat_type` to `not_applicable`, and
    `cold_plunge` is a reserved block
  - traditional ⇒ every infrared field is `not_applicable`
  - `emf_claim` can only be `claimed`, `not_verified` or `not_applicable`
- **`warranty`** is a stub (`stub: true` plus the verbatim summary).
- **`offers[]`** has `inh_sells` disclosed on each offer.
- **`provenance`** records the source file sha256 and the upstream key and URLs.

---

## 3. Dry-run import

| | Count |
|---|---|
| Upstream records | **291** |
| After identity resolution | **285** (6 Quick Ship listings merged as offers + aliases) |
| **Passing** | **246** |
| **Quarantined** | **39** |
| R1 electrical plausibility | 15 (2 records also fail R2) |
| R2 hybrid rule | 15 |
| R3 canonical identity | 10 |
| R4 titles | 0 quarantined (rule 4 transforms: 150 suffix drops, 50 EMF claims stripped from titles, 52 case fixes, 11 slug model numbers withheld) |
| R5 capacity | 1 |
| Banned-phrase occurrences in output | **0** |

### Named test records

| Record | Upstream | Outcome |
|---|---|---|
| `GDI-7389-02` Copenhagen | 120V/240V, 40A, 8 kW | **Quarantined R1**: 8 kW at 120V = 66.7 A > 40 A |
| `GDI-8526-01` Kaskinen | Infrared | **Quarantined R2**: the title says Hybrid and names a Harvia stove plus PureTech IR |
| `GDI-8223-01` Visby | Infrared | **Quarantined R2**: the title says Hybrid |
| `SAN05M001` Serenity Hybrid | Traditional | **Quarantined R2**: the title says Hybrid |
| `SAN06M001` Renew Hybrid | Traditional | **Quarantined R2**: the title says Hybrid |
| `SN-BPU-H6K001F` / `…N` | same title, same URL, 6 kW both | **Both quarantined R3**: no distinguishing configuration in the source |
| Clearlight (12) | slug in `model` | 8 slugs withheld as "Model number not documented". `IS-1/2/3` are real model numbers and kept. Titles de-capitalised, ® stripped |
| Clearlight Sanctuary C | title says 4 person, field says 3 | **Quarantined R5** |

R1 also caught a record that fails at 240V too: `GDI-8330-01` Soria, 6 kW at 240V = 25 A > 20 A.
It carries both R1 and R2, and so does `GDI-8005-01` Vorarlberg, which upstream types as Infrared while its source URL calls it a traditional sauna. All 15 R1
failures are Golden Designs records with the Copenhagen pattern (`120V/240V` with a 30/40 A figure).
That looks like a systematic upstream mapping in which two supply options are joined into one
field.

### Quick Ship

Six merged, because no field a source states disagreed. **Auburn's Quick Ship (`MK10002`) lists
8 kW against the standard 6 kW**, so it stays a **separate record** titled `…, 8 kW heater`, per
the rule that a different heater package is a different configuration. Four merges happened
where **both** sides leave heater kW or wood blank. The report lists those as "unknown on both":
absence on both sides is not proof of sameness (D6).

### Full quarantine list

| # | Model | Brand | INH sells | Rule | Reason |
|---|---|---|---|---|---|
| 1 | `AHMAD2PRU\|CLRINDLRG\|AHKIP60PKGUS\|LEDKITLC` | Almost Heaven Saunas |  | R2_HYBRID | upstream type Hybrid, but neither the title nor the heater text names both a traditional heater and an infrared system (title: 'Madison 2-3 Person Indoor Sauna'; spectrum field: 'Infrared'; heater_kw: '6 kW') |
| 2 | `AHRAIN4PRU\|CLRINDLRG\|AHKIP60PKGUS\|LEDKITLC` | Almost Heaven Saunas |  | R2_HYBRID | upstream type Hybrid, but neither the title nor the heater text names both a traditional heater and an infrared system (title: 'Rainelle 4 Person Indoor Sauna'; spectrum field: 'Infrared'; heater_kw: '8 kW') |
| 3 | `BS65-T` | Scandia | yes | R3_IDENTITY | display title 'Scandia Electric Barrel Sauna Kit, 4 Person' shared by 2 records (BS65-T, BS66-T); no distinguishing configuration in the source |
| 4 | `BS66-T` | Scandia | yes | R3_IDENTITY | display title 'Scandia Electric Barrel Sauna Kit, 4 Person' shared by 2 records (BS65-T, BS66-T); no distinguishing configuration in the source |
| 5 | `clearlight-curve-sauna-dome-w-infrared-mat` | Clearlight |  | R2_HYBRID | upstream type Hybrid, but neither the title nor the heater text names both a traditional heater and an infrared system (title: 'Clearlight® Curve Sauna Dome w/ Infrared Mat'; spectrum field: 'Far Infrared'; heater_kw: None) |
| 6 | `clearlight-sanctuary-c-full-spectrum-infrared-corner-sauna-4-person` | Clearlight |  | R5_CAPACITY | title states 4 person, capacity field states 3 |
| 7 | `GDI-7202-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 30A, 6 kW: 6 kW at 120V = 50.0 A > 30 A stated. Impossible as stated; not resolved from a manual in this round |
| 8 | `GDI-7203-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 9 | `GDI-7206-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 10 | `GDI-7289-02` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 30A, 6 kW: 6 kW at 120V = 50.0 A > 30 A stated. Impossible as stated; not resolved from a manual in this round |
| 11 | `GDI-7389-02` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 12 | `GDI-8003-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 13 | `GDI-8005-01` | Golden Designs Inc | yes | R2_HYBRID | upstream type Infrared, but the record carries a heater rating (8.0 kW) and the title never says infrared (title: 'Golden Designs Vorarlberg GDI-8005-01 8.0 kW 5 Person Outdoor Sauna'). Heat type unresolved: needs a manual |
| 14 | `GDI-8005-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 15 | `GDI-8103-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 16 | `GDI-8202-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 30A, 6.0 kW: 6 kW at 120V = 50.0 A > 30 A stated. Impossible as stated; not resolved from a manual in this round |
| 17 | `GDI-8203-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 18 | `GDI-8206-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 19 | `GDI-8223-01` | Golden Designs Inc | yes | R2_HYBRID | upstream type Infrared, but the title says hybrid/combination (title: 'Golden Designs Visby 3 Person Outdoor-Indoor PureTech™ Hybrid Full Spectrum Sauna'; heater: None; heater_kw: '8.0 kW'). Conflict left unresolved: needs a manual |
| 20 | `GDI-8330-01` | Golden Designs Inc | yes | R2_HYBRID | upstream type Infrared, but the title says hybrid/combination (title: 'Golden Designs Soria 3-Person Hybrid Sauna – Full Spectrum Infrared & Harvia Stove'; heater: 'Harvia Stove'; heater_kw: '6 kW'). Conflict left unresolved: needs a manual |
| 21 | `GDI-8330-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 20A, 6 kW: 6 kW at 120V = 50.0 A > 20 A stated; 6 kW at 240V = 25.0 A > 20 A stated. Impossible as stated; not resolved from a manual in this round |
| 22 | `GDI-8360-01` | Golden Designs Inc | yes | R2_HYBRID | upstream type Infrared, but the title says hybrid/combination (title: 'Golden Designs Toledo Per Hybrid Sauna (Indoor). Full Spectrum and Harvia Traditional Stove'; heater: 'Harvia Traditional Stove'; heater_kw: '8 kW'). Conflict left unresolved: needs a manual |
| 23 | `GDI-8506-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 40A, 8.0 kW: 8 kW at 120V = 66.7 A > 40 A stated. Impossible as stated; not resolved from a manual in this round |
| 24 | `GDI-8526-01` | Golden Designs Inc | yes | R2_HYBRID | upstream type Infrared, but the title says hybrid/combination (title: 'Golden Designs Kaskinen 6-Person Hybrid Outdoor Sauna – Canadian Red Cedar Interior'; heater: 'Harvia stove and PureTech™ Full Spectrum infrared heating technology'; heater_kw: '8.0 kW'). Conflict left unresolved: needs a manual |
| 25 | `GDI-B002-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 30A, 6.0 kW: 6 kW at 120V = 50.0 A > 30 A stated. Impossible as stated; not resolved from a manual in this round |
| 26 | `GDI-B004-01` | Golden Designs Inc | yes | R1_ELECTRICAL | upstream states 120V/240V, 30A, 6 kW: 6 kW at 120V = 50.0 A > 30 A stated. Impossible as stated; not resolved from a manual in this round |
| 27 | `HHS-SAU-2P-COMB` | Heavenly Heat Saunas |  | R2_HYBRID | upstream type Hybrid, but neither the title nor the heater text names both a traditional heater and an infrared system (title: '2-Person Combination Sauna'; spectrum field: 'Infrared'; heater_kw: None) |
| 28 | `MX-J306-01` | Maxxus | yes | R3_IDENTITY | display title 'Maxxus Bellevue Far Infrared Sauna, 3 Person' shared by 2 records (MX-J306-01, MX-J306-01-ZF); no distinguishing configuration in the source |
| 29 | `MX-J306-01-ZF` | Maxxus | yes | R3_IDENTITY | display title 'Maxxus Bellevue Far Infrared Sauna, 3 Person' shared by 2 records (MX-J306-01, MX-J306-01-ZF); no distinguishing configuration in the source |
| 30 | `MX-K306-01` | Maxxus | yes | R3_IDENTITY | display title 'Maxxus Far Infrared Sauna, 3 Person' shared by 4 records (MX-K306-01, MX-K306-01 CED, MX-K306-01-ZF CED, MX-K356-01); no distinguishing configuration in the source |
| 31 | `MX-K306-01 CED` | Maxxus | yes | R3_IDENTITY | display title 'Maxxus Far Infrared Sauna, 3 Person' shared by 4 records (MX-K306-01, MX-K306-01 CED, MX-K306-01-ZF CED, MX-K356-01); no distinguishing configuration in the source |
| 32 | `MX-K306-01-ZF CED` | Maxxus | yes | R3_IDENTITY | display title 'Maxxus Far Infrared Sauna, 3 Person' shared by 4 records (MX-K306-01, MX-K306-01 CED, MX-K306-01-ZF CED, MX-K356-01); no distinguishing configuration in the source |
| 33 | `MX-K356-01` | Maxxus | yes | R3_IDENTITY | display title 'Maxxus Far Infrared Sauna, 3 Person' shared by 4 records (MX-K306-01, MX-K306-01 CED, MX-K306-01-ZF CED, MX-K356-01); no distinguishing configuration in the source |
| 34 | `SAN05M001` | Salus Saunas |  | R2_HYBRID | upstream type Traditional, but the title says hybrid/combination (title: 'Serenity Hybrid Indoor Sauna - 3 Person'; heater: None; heater_kw: None). Conflict left unresolved: needs a manual |
| 35 | `SAN05M002` | Salus Saunas |  | R2_HYBRID | upstream type Traditional, but the title says hybrid/combination (title: 'Harmony Hybrid Indoor Sauna - 6 Person'; heater: None; heater_kw: None). Conflict left unresolved: needs a manual |
| 36 | `SAN06M001` | Salus Saunas |  | R2_HYBRID | upstream type Traditional, but the title says hybrid/combination (title: 'Renew Hybrid Outdoor Sauna - 2 Person'; heater: None; heater_kw: None). Conflict left unresolved: needs a manual |
| 37 | `SAN06M003` | Salus Saunas |  | R2_HYBRID | upstream type Traditional, but the title says hybrid/combination (title: 'Renew King Hybrid Outdoor Sauna - 3 Person'; heater: None; heater_kw: None). Conflict left unresolved: needs a manual |
| 38 | `SAN06M004` | Salus Saunas |  | R2_HYBRID | upstream type Traditional, but the title says hybrid/combination (title: 'Grand Renew Hybrid Outdoor Sauna - 6 Person'; heater: None; heater_kw: None). Conflict left unresolved: needs a manual |
| 39 | `SAN06M005` | Salus Saunas |  | R2_HYBRID | upstream type Hybrid, but neither the title nor the heater text names both a traditional heater and an infrared system (title: 'Elevation Hybrid Outdoor Sauna - 6 Person'; spectrum field: 'Full Spectrum'; heater_kw: None) |
| 40 | `SN-BPU-H6K001F` | Redwood Outdoors |  | R3_IDENTITY | display title 'Redwood Outdoors Barrel Outdoor Sauna w/ Porch, 6 Person' shared by 2 records (SN-BPU-H6K001F, SN-BPU-H6K001N); no distinguishing configuration in the source |
| 41 | `SN-BPU-H6K001N` | Redwood Outdoors |  | R3_IDENTITY | display title 'Redwood Outdoors Barrel Outdoor Sauna w/ Porch, 6 Person' shared by 2 records (SN-BPU-H6K001F, SN-BPU-H6K001N); no distinguishing configuration in the source |

**Withheld, not quarantined (11): no capacity in title or field.** The field goes out as
`not_verified`. Almost Heaven Alpina, Everwood, Basic, Country, Family, Hartman, Komfort and
Solace; Scandia `PRECUT-DIY-8X9-ULTRA`; both Kohler C1. See D5.

### Known gaps in the dry run (Part B fixes, none of them loosens a rule)

- Found and fixed during Part A: R1 first skipped records typed Infrared, so `GDI-8330-01`
  Soria showed only R2. R1 now runs on every heat type. That makes the rule stricter, not
  looser. The counts above are from after the fix.
- Dimensions and max temperature strings are not parsed yet (upstream coverage is 9, 3 and 83
  records respectively), so they are `not_verified`.
- The title builder is a heuristic and some titles still carry a model number or an awkward
  name (`Dynamic Saunas Avila DYN-6103-01 Elite`, `Almost Heaven Nordik Indoor Sauna` with no
  capacity). Part B adds a reviewed override table rather than more regex.
- `MX-K306-01`'s upstream sources include both a Hemlock and a Red Cedar page, which means
  Infinite Sauna merged two configurations into one record. The R3 collision already quarantines
  it, but the report should name the actual cause.

---

## 4. Coverage by brand

"Has a value" means any grade. **The `documented` grade is 0% for every brand and every field**,
because no upstream source is a manual. Figures include quarantined records (n = 285).

| Brand | Records | INH sells | Supply voltage | Stated amperage | Connection type | Heater kW (trad/hybrid) | Breaker amps | Documented grade |
|---|---|---|---|---|---|---|---|---|
| Almost Heaven | 53 | 0 | 0% (0) | 0% (0) | 0% (0) | 47% (23) of 49 | 0 | 0 |
| Clearlight | 12 | 0 | 50% (6) | 8% (1) | 0% (0) | 0% (0) of 1 | 0 | 0 |
| Dundalk LeisureCraft | 7 | 7 | 0% (0) | 0% (0) | 0% (0) | 86% (6) of 7 | 0 | 0 |
| Dynamic Saunas | 26 | 26 | 96% (25) | 100% (26) | 0% (0) | n/a of 0 | 0 | 0 |
| Golden Designs | 28 | 28 | 46% (13) | 96% (27) | 0% (0) | 100% (16) of 16 | 0 | 0 |
| Heavenly Heat | 8 | 0 | 0% (0) | 0% (0) | 0% (0) | 0% (0) of 1 | 0 | 0 |
| Kohler | 2 | 2 | 100% (2) | 50% (1) | 50% (1) | 100% (2) of 2 | 0 | 0 |
| Mande Spa | 3 | 3 | 0% (0) | 0% (0) | 0% (0) | 0% (0) of 3 | 0 | 0 |
| Maxxus | 27 | 27 | 67% (18) | 96% (26) | 0% (0) | n/a of 0 | 0 | 0 |
| Medical Saunas | 4 | 4 | 0% (0) | 100% (4) | 0% (0) | 0% (0) of 4 | 0 | 0 |
| Redwood Outdoors | 18 | 0 | 0% (0) | 0% (0) | 0% (0) | 100% (18) of 18 | 0 | 0 |
| Ripavi | 2 | 2 | 0% (0) | 0% (0) | 0% (0) | 0% (0) of 2 | 0 | 0 |
| Salus | 65 | 0 | 0% (0) | 0% (0) | 0% (0) | 0% (0) of 46 | 0 | 0 |
| SaunaLife | 7 | 7 | 14% (1) | 14% (1) | 0% (0) | 14% (1) of 7 | 0 | 0 |
| Scandia | 8 | 8 | 0% (0) | 0% (0) | 0% (0) | 12% (1) of 8 | 0 | 0 |
| Sun Home | 15 | 0 | 20% (3) | 7% (1) | 0% (0) | 50% (2) of 4 | 0 | 0 |

**Yes, coverage skews heavily toward brands InHouse Wellness sells:**

| | INH sells (114) | Not sold by INH (171) |
|---|---|---|
| Supply voltage | **51.8%** | 5.3% |
| Stated amperage | **74.6%** | 1.2% |
| Connection type | 0.9% | 0.0% |
| Heater kW (trad/hybrid) | 53.1% (26/49) | 36.1% (43/119) |
| Breaker amps | 0% | 0% |

The electrical data exists mainly *because* our own product pages carry it. That is the same
circularity as in §1.2. Salus, the largest non-INH brand at 65 records, has **zero** electrical
values of any kind.

## 5. Major US brands absent from the source

**All nine are absent**, and none of them appears anywhere in the JSON: Sunlighten, Finnmark,
Enlighten, Health Mate, JNH Lifestyles, Backyard Discovery, Therasage, Auroom, Thermory. This
is reported only. A reference that leaves out Sunlighten and Health Mate will read as an
INH-catalogue mirror, whatever its methodology says.

---

## 6. Decisions needed

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **D1** 🔴 | Disclose that Infinite Sauna is an owned property | (a) disclose on every INH Verified page and in the dataset metadata; (b) say nothing | **(a).** A "neutral" reference that silently sources from its own satellite breaks the editorial-independence clause you are about to adopt |
| **D2** | How upstream `amperage` is stored | (a) `stated_amperage`, with `breaker_amps` left `not_verified` (as the dry run does); (b) map it into `breaker_amps` at `listed`; (c) drop it | **(a).** The upstream field doesn't say breaker or draw (`1.2A` proves it can be a draw). Rule 1 stays valid either way. Breaker amps come only from a source that says "breaker" |
| **D3** | Grade for imported values | (a) `listed` + `secondary_dataset_record_level` (as the dry run does); (b) add a new grade such as `aggregated`; (c) re-fetch each upstream product page and grade per field only where the value is found on the page | **(a) now, (c) as a later round.** (a) is the lowest factual grade and is marked as record-level. (c) is the only route to a true per-field `listed` with its own `source_url`. For INH-sold records our own metafield spans in `data/cost-tables.json` already give per-field evidence (see D7) |
| **D4** | `120V/240V`, `220V`, `220V/240V` | (a) `not_verified` with the upstream string in the note (as the dry run does); (b) publish the string as-is | **(a).** None of them is a single supply voltage. 29 records affected |
| **D5** | No capacity anywhere (11 records) | (a) withhold the field and publish the record (as the dry run does); (b) quarantine | **(a).** An absence isn't a contradiction. It is listed in the report so you can overrule it |
| **D6** | Quick Ship merges where both sides are blank on heater/wood (4) | (a) merge (as the dry run does); (b) quarantine until a source confirms the package | **(b).** The same model name is not proof of the same package, and Auburn shows packages can differ |
| **D7** | Use our own metafield evidence for INH-sold SKUs | (a) not in Round 1; (b) join `data/cost-tables.json` spans in as per-field `listed` sources | **(b) in Part B, as a second source.** Where the two disagree the record is quarantined with both values. That also resolves some R1 cases (the calculator already holds kW from manuals for several GDI SKUs) |
| **D8** | The two "recommended heater" kW values on the live calculator | (a) a small separate round to add the recommendation guard to the metafield path and rebuild the asset; (b) leave them | **(a).** It is out of scope here, but it is live and wrong in the direction this project exists to prevent |
| **D9** | Validating the dataset against the schema | (a) add `jsonschema` to `requirements.txt` (preflight `--deps` will enforce it); (b) a stdlib validator for our subset | **(a).** A home-grown validator for 2020-12 `if/then` is a new source of false passes |
| **D10** 🔴 | Editorial-independence clause in CLAUDE.md | approve the wording as written / amend | **Approve.** It is not committed. It waits on your 🔴 |

## 7. What Part B will do on approval

1. Build the importer that writes `data/verified/saunas.json` plus `quarantine.json`, with
   pinned-fixture tests for every named record and a deliberately failing fixture per rule.
2. Add the lint: the banned phrase, and any bare value without a grade.
3. Validate against the schema and run the determinism check.
4. Replay the existing suite (the brief says 472; RUNLOG last recorded 536) and both lint scopes.
5. Write the RUNLOG entry and update HANDOFF.
