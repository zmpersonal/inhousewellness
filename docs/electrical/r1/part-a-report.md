# Electrical & Heater Sizing Tool — Round 1, Part A report

2026-10-07 · branch `electrical/r1-tool` (from `main` 3f39831) · **nothing live was changed**

Reproduce every number here, offline:

```bash
.venv/bin/python scripts/electrical_coverage.py --json docs/electrical/r1/coverage.json
```

The output is deterministic: two runs gave an identical MD5. Evidence files sit next to this
report:

- `coverage.json`
- `source-scan-breaker-awg.json`, the breaker and AWG statements in sources we already cache
- `sources-research.md`, the sizing charts, the two satellite sites and the code edition, with
  every URL and page number

---

## 0. The six things that change the build

1. **Wire gauge is not a database field.** No record holds one, so every wire answer the tool
   gives today would be code-based.
2. **Only 2 of 131 live records state a breaker.** 71 more state a *circuit*, for example
   "240V / 30AMP (Stove)" or "120V 20A dedicated". Whether a stated circuit counts as the
   manufacturer's breaker answer decides whether the tool is mostly "manufacturer says" or almost
   entirely "code-based" (D1).
3. **Rule 1 trips on 18 of 18 records, or on none.** It depends on one code reading. At 125%
   (NEC 424, continuous load), every 6 kW model stating 30 A is below a 35 A code minimum, and
   every 8 kW model stating 40 A is below 45 A. At 100% (NEC 422.10, marked rating), none are.
   The heater makers' own tables side with 30 A for 6 kW: HUUM Table 2, cited in Sun Home's
   Nova 3 guide, and Harvia's KIP manual. **This is the first question for the electrician**
   (D2).
4. **The manuals we already hold state breaker and wire that the database never extracted.**
   Sun Home Nova 3 states "Circuit Breaker 30 A … Minimum Wire Size 10 AWG"; the record's
   `breaker_amps` is empty. 66 live records cite a document containing a breaker figure. This
   round may not change database records (D3).
5. **The 30% gate depends on D1.** Of 139 priced INH SKUs, 52 (37.4%) can show a
   manufacturer-stated circuit. **0 (0%) state a breaker**, and 0 can be computed from rated kW,
   because the kW for INH-sold models comes only from our own catalogue, which editorial
   independence bars as evidence (D4).
6. **Only two answer pages qualify: 6 kW (15 models) and 8 kW (14).** 4.5 kW and 10.5 kW have no
   database models; 7.5 kW and 9 kW have one each. Measured US search volume for every per-kW
   breaker query is 0. These pages are for citations and links, not traffic (D6).

---

## 1. Grounding report

### 1.1 Database fields and coverage

Source: `data/verified/saunas.json`, schema 0.3.0, 263 records (236 published, 27 backlog).
**Live:** 131 active entries (`data/verified/golive/launch-state.json`).

| Field | Exists? | Notes |
|---|---|---|
| `heater_kw` | yes | infrared records are `not_applicable`, so there is no infrared wattage field |
| `heater_voltage` | yes | **0 values in all 263** |
| `supply_voltage` | yes | |
| `stated_amperage` | yes | the schema says this is NOT a breaker size; R3 rule `amperage_is_circuit` decides the wording |
| `circuits[]` | yes | each circuit has `voltage`, `stated_amperage`, `purpose` ("Stove", "Control for Lights and Music", "Stove & Full Spectrum") |
| `circuits_required`, `circuit_requirement` | yes | "Dedicated required" is the only value |
| `connection_type` | yes | NEMA 5-15P / 5-20P / 6-15P / 6-20P / L5-30P / L6-20P / L6-30P, or Hardwired |
| `breaker_amps` | yes | 2 live values |
| `gfci` | yes | 2 live values ("Required") |
| **wire gauge** | **NO FIELD** | |

**Coverage, live (n = 131: 54 traditional, 69 infrared, 8 hybrid).** Counts are non-null values.

| Field | ALL | traditional | infrared | hybrid |
|---|---|---|---|---|
| heater_kw | 31 | 23/54 | n/a (69) | 8/8 |
| heater_voltage | 0 | 0 | 0 | 0 |
| supply_voltage | 81 | 4 | 69 | 8 |
| stated_amperage | 71 | 2 | 63 | 6 |
| circuits[] | 15 | 10 | 0 | 5 |
| circuit_requirement (dedicated) | 18 | 4 | 14 | 0 |
| connection_type | 20 | 4 | 16 | 0 |
| breaker_amps | 2 | 0 | 2 | 0 |
| gfci | 2 | 0 | 2 | 0 |
| wire gauge | — | — | — | — |

**By grade, live non-null values:**
- `listed (manufacturer)`: kW 29, supply V 42, amps 42, breaker 1.
- `documented (manufacturer manual)`: kW 2, supply V 39, amps 29, breaker 1, GFCI 2.
- **`listed (distributor)` and `listed (retailer)` do not occur in any electrical field.** The
  database holds no electrical value from a non-manufacturer source.

The published-records table (n = 236) is in `coverage.json` and has the same shape.

**Live heater kW values:** 6.0 (15), 7.5 (1), 8.0 (14), 9.0 (1). All have a 240 V heater circuit
where a voltage is stated.

### 1.2 Manufacturer-stated breaker and wire

| | live (131) | published (236) |
|---|---|---|
| breaker stated (`breaker_amps`) | **2** (Salus Element King 20 A; Sun Home Eclipse 2, 30 A + GFCI) | 3 |
| wire gauge stated | **0** (no field) | 0 |
| circuit stated, no breaker word | 71 | 91 |

**What we already hold but never extracted:**
`scripts/electrical_source_scan.py` re-read all 803 cached sources (1.5 GB) for breaker, AWG and
GFCI statements; the hits are in `source-scan-breaker-awg.json`.
- **Sun Home Nova 3** guide p. 6: 6 kW, 25 A load, 30 A breaker, 10 AWG minimum, hardwired,
  citing HUUM Table 2.
- **Sun Home Nova 6** guide p. 6: 7.5 kW, 31.25 A, 40 A, 8 AWG.
- The Salus, Heavenly and Golden Designs manuals bundle **Harvia heater manuals** with
  breaker and wire tables. These bind to the *heater* model, not the cabin. This is the CLAUDE.md
  rule "A rating belongs to the model number beside it", and it applies directly here.

So "how much of the tool is manufacturer-stated" is today about 2% for breakers and 0% for wire.
After a database extraction round it would be measurably higher, but that round is out of scope
here (D3).

### 1.3 Heater sizing sources (primary documents only)

Full table, URLs and page numbers: `sources-research.md`.

| Chart | Document | Inputs | Glass / wall rule as stated |
|---|---|---|---|
| Harvia | KIP US/UL manual BY05-1516, p. 14 table, p. 16 rules | ft³ / m³ | +1.2 m³ per m² of uninsulated surface, glass included (≈ 3.94 ft³/ft²); log walls × 1.5 |
| HUUM | DROP manual EU v6 2025, p. 4 | m³ | +1 m³ per m² of brick, tile or glass |
| Finnleo (Sauna360) | Designer SL2 72-0130 p. 2; Laava Pro 72-0139 p. 5 | ft³ | none stated |
| Amerec → Helo (Sauna360) | helosauna.com/en-us/faq | shares Finnleo tables | +1 ft³ per ft² of heavy wall or glass |
| Tylö | Sense UB Rev B (2024-08-21) p. 9; Sport USA (2022) p. 3 | ft³; ranges vary with supply voltage | +1 ft³ per ft² of glass |
| Saunacore | brochure, Nov 2022, p. 46 | ft³ ÷ 50 = kW, next size up (maximums only) | none |
| Scandia | product pages only | maximums only | none |

Polar: no manufacturer document found, so it is not used.

**The charts disagree. Worked example: a 6×6×7 ft room (252 ft³), insulated.**
- **Without glass:**
  - Harvia: 6–8 kW
  - HUUM: 6–7.5 kW
  - Finnleo: 6–8 kW
  - Tylö: 6–8.3 kW
  - Saunacore: exactly 6 kW
  - Scandia: 6 kW and up
- **With a 12 ft² glass door:**
  - the glass adds 47 ft³ (Harvia), 39.6 ft³ (HUUM) or 12 ft³ (Helo/Tylö), **a 4× spread**;
  - Harvia moves to 6–9 kW.

This crosses the brief's trigger: Harvia with glass (up to 9 kW) against Saunacore (6 kW) is
more than one standard size apart. Per rule 6 they are shown side by side, never blended (D7).

Harvia also contradicts itself. Its US product page gives the KIP60 as 177–283 ft³; its manual
says 170–300. A retailer-made "Sizing Your Harvia" PDF was found and excluded.

### 1.4 Code reference

- **The current edition is NFPA 70 (NEC) 2026,** issued 2025-08-20. It renumbered articles.
- **Adoption, per NFPA's map as of 2026-08-03:** 6 states on 2026, 20 on 2023, 15 on 2020, 3 on
  2017 and 2 on 2008; AZ, MS and MO adopt locally only.
- **UL 875** (Electric Dry-Bath Heaters, Ed. 10, 2024) is the heater product standard.
- **Unverified, and assigned to the electrician:** whether a sauna heater is sized under
  **424 (fixed space heating, 125% continuous)** or **422 (appliance, marked rating)**, and every
  section number in 2026. No free-access primary text was available. I will not cite section
  numbers from memory.

**Storage plan:** `data/electrical/code-constants.json`. Each table carries `edition`,
`article`, `section`, `table`, `values`, `citation_url`, `retrieved`, and
`electrician_review: {reviewed_by: null, date: null}`. Proposed tables:
- standard OCPD ratings;
- copper conductor ampacity by temperature column (60 °C for NM cable, 75 °C at terminations);
- the small-conductor OCPD limits;
- the continuous-load factor, as **one named constant** whose value D2 decides;
- 120/208/240 V.

Tests enforce that every constant has a citation, that no render path holds a numeral not traced
to the file, and that a constant with `electrician_review.reviewed_by == null` renders a
"pending electrician review" label on the preview.

### 1.5 Overlap with the owned satellite sites (read only, nothing modified)

**infinitesauna.com/electrical**
- What it publishes: a 96-model table of voltage, amperage, plug and kW, refreshed 2026-10-05.
  It has no inputs, breaker, wire, formula or NEC citation.
- Problems: amperage is undefined (draw or breaker?). Several 8 kW units are listed "120V/240V
  40A", and the 120 V half is not credible. Scandia BS64-T is listed at 9 kW on a 30 A plug.

**outdoorsteamsauna.com/heater-sizing**
- What it publishes: a calculator of L×W×H + glass × 3.3 (HUUM's factor). It compares the result
  with three Harvia Cilindro rows, which link to EU 400 V three-phase models. It gives no kW
  recommendation and no electrical output, and uses `Number(x) \|\| 0`, empty-as-zero.

**How INH differs:**
- every value is graded, sourced and dated, and amperage is always labelled draw or circuit;
- breaker and wire are given per circuit, with the manufacturer-first precedence;
- sizing shows every chart side by side with its own glass rule;
- unknown values are designed states, never zero;
- the tool is printable for the electrician.

The satellites stay as they are. Their 8 kW "120V" rows and the 9 kW/30 A row are worth a
separate correction task on those sites (not this round).

### 1.6 URLs and theme slots

- **Themes:** 16 of 20 used, 4 free (read 2026-10-07). MAIN is `167150092355` (resolved at run
  time, informational). Round 13 preview `146278776899` was last updated 2026-09-29.
- **Handles are all free.** These answer 404 today: `/pages/sauna-electrical-requirements`,
  `/pages/sauna-heater-size-calculator`, `/pages/sauna-electrical`, `/pages/sauna-breaker-size`.
- **Legacy paths:** `/tools/panel-check` and `/tools/will-it-fit` both 404, and no redirect
  exists. A Shopify URL redirect fires only on a 404, so both can be redirected. Redirect writes
  need the session connector (`write_online_store_navigation` is not in the Actions token).
  - `panel-check` is referenced by 7 legacy queue rows, all blocked, with unrelated keywords.
  - `will-it-fit` is referenced by one Reels seed.
- **Preview caveat (CLAUDE.md, Round 13):** an unpublished page 404s, with or without
  `?preview_theme_id`. A real preview URL therefore needs the pages to exist PUBLISHED (D8).
- **Pre-existing finding (not this round's to fix):** the live hub and model pages each emit
  **two** `BreadcrumbList` blocks (theme + ours). `/pages/sauna-cost` emits one.

### 1.7 What is reused

| Piece | Reused how |
|---|---|
| model picker | the same `<select>` + 3rem control pattern as `sections/true-total-cost.liquid`, fed from Verified data (the calculator's list is INH SKUs, a different population) |
| provenance | `snippets/inh-verified-fact.liquid` (grade · source · date) |
| missing-value lint | `scripts/lint_missing_values.py` already scans `assets/*.js`, `sections/*.liquid`, `templates/*.liquid`; new files land in those globs, and the file count must rise |
| unknown-kW state | `assets/inh-cost-core.js`'s order of resort: stated → invite → decline-and-say-so, with no fifth branch |
| assertion suite | full `pytest tests/` (859 at last run) plus `verified_checks.py`, the calculator state checks and the metro assertions |
| deploy | `deploy theme files` workflow (two-pass, MD5 read-back), `deploy_pages.py` (visible-text read-back), `verified_theme_check.py` |

---

## 2. Coverage numbers

**Live database (131).** A = breaker stated, B = circuit stated, C = rated kW + voltage stated,
C? = kW stated but voltage not, D = amperage not tied to a circuit, E = nothing.

| | A | B | C | C? | D | E | total |
|---|---|---|---|---|---|---|---|
| INH sells (mapped) | 0 | 39 | 0 | 0 | 0 | 1 | 40 |
| not sold | 2 | 32 | 4 | 9 | 9 | 35 | 91 |
| **total** | **2** | **71** | **4** | **9** | **9** | **36** | 131 |

**What that means:**
- **manufacturer-stated breaker AND wire: 0**;
- breaker only: 2;
- a breaker answer with D1(a): A + B = 73 (55.7%);
- computable from rated kW: 4 (plus 9 more if the reader supplies the voltage);
- cannot answer either: 36 + 9 = 45.

**By heat type:**
- infrared: A 2, B 53, D 9, E 5;
- traditional: B 10, C 4, C? 9, E 31;
- hybrid: B 8.

Traditional is the weak class: 31 of 54 have nothing electrical.

**Priced INH SKUs (139, the cost calculator's population).**

| | count | % |
|---|---|---|
| mapped to a live record, circuit stated (B) | 52 | 37.4% |
| mapped, nothing electrical (E) | 13 | 9.4% |
| **no Verified record at all** | 74 | 53.2% |
| …of which our own catalogue states a kW (not usable as evidence) | 19 + 4 | — |
| breaker stated by the manufacturer | **0** | **0%** |

---

## 3. Proposed static answer pages

Rule: at least 3 live database models, each with its grade and source link.

| Page | Models | Qualifies |
|---|---|---|
| **What Size Breaker Does a 6 kW Sauna Heater Need?** | 15 | ✅ |
| **What Size Breaker Does an 8 kW Sauna Heater Need?** | 14 | ✅ |
| 4.5 kW, 10.5 kW | 0 | ❌ |
| 7.5 kW (Sun Home Nova 6), 9 kW (Sun Home Solaris Custom 6) | 1 each | ❌ |

**6 kW, 15 models:**
- Golden Designs: Soria FS, Sundsvall;
- Salus: Heavenly, Relieve, Renew, Renew II, Renew King, Serenity (B, 240 V); Ally (C?);
- Sun Home: Nova 3, Solaris Custom 4 (C, 240 V);
- Almost Heaven: Charleston, Logan, Sutton, Vienna (C?, voltage not stated).

**8 kW, 14 models:**
- Golden Designs: Copenhagen, Toledo FS;
- Salus: Elevation, Fierce, Grand Renew, Harmony, Restore, Revive II, Solara, Solis (B, 240 V);
  Charisma, Flora, Grand Ally (C?);
- Almost Heaven: Patterson (C?).

Two notes for the decision:
- **Brand concentration.** Salus is 7 of 15 and 11 of 14 rows. The answer sentence must not read
  as a Salus spec.
- **Shared circuits.** 5 of these circuits are "Stove & Full Spectrum". The circuit also feeds
  infrared emitters, so a code minimum computed from heater kW alone would understate the load.
  Those rows show the manufacturer circuit only and never a heater-only computation.

**Optional page type (D6b): one infrared page,** "Does an Infrared Sauna Need a Dedicated
Circuit?" The live counts for it:
- 120 V / 15 A circuit: 38 models;
- 120 V / 20 A: 16 models;
- 240 V circuits: 9 models;
- plug type known: 20 models.

It is grounded in the database's strongest class (infrared, B).

---

## 4. URL handles and redirects

| Artifact | Proposed handle | Alternatives |
|---|---|---|
| A. Tool, two modes | `/pages/sauna-electrical-requirements` (140/mo, KD 10) | `/pages/sauna-heater-size-calculator` (170/mo, KD 20) as a second handle for the sizing mode |
| B. Answer pages | `/pages/6-kw-sauna-heater-breaker-size`, `/pages/8-kw-sauna-heater-breaker-size` | `/pages/sauna-breaker-size-6kw` |
| C. Methodology | `/pages/sauna-electrical-methodology` | — |

Search volumes are US figures from Ubersuggest. Ahrefs Keywords Explorer answered
"Insufficient plan".

**Redirects:**
- **`/tools/panel-check` → the tool, 301.** Create it at go-live, not for the preview, because it
  is a live change. A redirect is inert while the target page is published, so the safe order is
  the Round 13 one.
- **`/tools/will-it-fit` → NOT this tool.** It asks whether a sauna fits a space. Pointing it at
  an electrical tool is the `DESTINATION_MISMATCH` failure. Recommend leaving it 404 or pointing
  it at the hub (D11).

---

## 5. Wireframes (text)

### 5.1 Tool, `/pages/sauna-electrical-requirements`

```
H1  Sauna electrical requirements and heater size
    Last updated 2026-10-xx · Data: InHouse Wellness Verified Sauna Database

[ Electrical ]  [ Heater size ]                 ← two tabs; both work with JS off as anchors

── Electrical ─────────────────────────────────────────────────────────
Step 1  Your sauna
   ( ) Pick a model  [ — pick a sauna — ▾ ]     ← live Verified entries, grouped by brand
   ( ) Enter it yourself:  heater kW [   ]  voltage ( ) 120 ( ) 208 ( ) 240
Step 2  Your home (optional)
   service [120/240 ▾]  main panel [ 100 A ▾ ]  open breaker slots [  ]

RESULT — per circuit, one card each
┌ Circuit 1 · Heater ("Stove")                                         ┐
│ Voltage            240 V                    listed · Salus · 2026-09-28 ↗ │
│ Circuit (stated)   30 A                     listed · Salus · 2026-09-28 ↗ │
│ Heater draw        25.0 A    = 6,000 W ÷ 240 V   (formula ↗)            │
│ Breaker            30 A — as the manufacturer states                     │
│ ░ Code-based minimum, not manufacturer-stated: 35 A  (methodology ↗) ░   │ ← distinct style; only
│ Wire gauge         ░ Code-based minimum: 8 AWG Cu, 75 °C ░ (method ↗)    │   where rule 1 allows
│ Dedicated circuit  Not stated by the manufacturer                        │
│ GFCI               Not stated by the manufacturer                        │
│ Standard outlet?   No — hardwired / not stated                           │
└──────────────────────────────────────────────────────────────────────┘
┌ Circuit 2 · Lights and music · 120 V · 15 A (stated) …                 ┐

Flags (never a verdict)
  · A 100 A main panel with an electric range and dryer is worth a load
    calculation before buying.
One line: Not electrical advice. Local code and the installation manual govern;
a licensed electrician makes the final call.

[ Print the electrician sheet ]
```

**Unknown-kW state** (a C? or E record):

```
│ Heater power   Not stated by the manufacturer                         │
│ ▸ Read it off the heater's spec plate or the manual (p. 6 ↗): [   ] kW │
│ Breaker / wire  Can't be computed without the heater's rated power.   │
│ What is known:  Dedicated circuit required · NEMA L6-30P (manual ↗)   │
```

### 5.2 Heater-size mode

```
Room  length [ ] ft  width [ ] ft  height [ ] ft     → 252 ft³
Glass area [ ] ft²   Walls ( ) insulated ( ) solid log ( ) uninsulated   ( ) indoor ( ) outdoor

By chart — not blended
  Harvia (KIP US manual p.14)     6–8 kW   glass rule: +3.94 ft³/ft² → 299 ft³
  HUUM (DROP manual p.4)          6–7.5 kW glass rule: +3.3 ft³/ft²
  Finnleo (SL2 p.2)               6–8 kW   no glass rule published
  Tylö (Sense UB p.9)             6–8.3 kW glass rule: +1 ft³/ft²
  Saunacore (brochure p.46)       6 kW     ft³ ÷ 50, next size up
  ⚑ These charts differ by more than one heater size for this room.
Database models with a heater in 6–9 kW: [list → Electrical mode, prefilled]
```

An input a chart does not use (for example log walls on Finnleo) shows "This chart does not
adjust for log walls", never a silent pass-through.

### 5.3 Static answer page (6 kW)

```
H1  What Size Breaker Does a 6 kW Sauna Heater Need?
    Last updated 2026-10-xx
Answer (template): "A 6 kW heater at 240 V draws 25.0 A. Of the 15 saunas with a 6 kW heater
in the InHouse Wellness Verified Sauna Database, 8 state a 30 A circuit; 7 state no circuit.
The code-based minimum is [35 A | 25 A — per D2], shown below with its formula."
Table (server-rendered HTML, JS off):
  Model | Heater | Voltage | Circuit stated | Breaker stated | Wire stated | Grade | Source | Verified
Code-based minimum (labelled): formula, constants, edition → methodology
Links: each model page · the tool (prefilled 6 kW / 240 V)
Cite this page: InHouse Wellness Verified Sauna Database, "What Size Breaker…", URL, date.
```

### 5.4 Electrician sheet (print CSS, one page)

```
InHouse Wellness · Electrician sheet · printed 2026-10-xx
Model: Salus Solara 6-person · source page ↗ · manual ↗
Circuit table — every value with grade/source/date, code-based rows marked ░
Home inputs the buyer entered (service, panel, slots) — or "not entered"
Questions to ask your electrician (fixed list, no AI):
  1 Which NEC edition does our jurisdiction enforce?
  2 Is a load calculation needed with our existing appliances?
  3 Does the heater circuit need GFCI protection here?
  4 Wire type inside the sauna walls (the manual specifies 90 °C copper)?
  5 Permit required?
Footer: not electrical advice; manual + local code govern.
```

### 5.5 Methodology page

The page has eight sections:
1. Sources and grades.
2. Precedence (rule 1).
3. The formula for current (I = W ÷ V) and why kW is never derived from V × A.
4. Each code table with edition, article, section and electrician-review status.
5. Wiring-method assumptions (NM cable 60 °C vs conductors 75 °C).
6. Each sizing chart with its document, page and glass rule.
7. Why the charts are not averaged.
8. The unknown states, then last updated.

It states plainly that local code and the manual govern.

---

## 6. Schema plan (extend, never duplicate)

- **Tool:** `WebApplication` (applicationCategory "UtilitiesApplication", `isAccessibleForFree`,
  `isBasedOn` → the Dataset URL).
- **Answer pages:** `FAQPage` with one Q/A whose answer text is the server-rendered template
  sentence, plus a `Dataset` subset (the hub's Dataset as `isPartOf`), with `variableMeasured`
  for heater kW, voltage, circuit amperage and breaker.
- **Methodology:** no new type. `TechArticle` would only be added if nothing else claims it.

Same rule as `true-total-cost.liquid`:
- **no Organization, WebSite, Product or BreadcrumbList** from our sections;
- a guard variable so two copies of a section cannot emit twice;
- a test that counts JSON-LD types on each rendered page.

The existing double BreadcrumbList on the hub and model pages is reported in §1.6 and not
changed.

---

## 7. Measurement baseline

**Prompts to track** (Ahrefs Brand Radar and Promptwatch; both need a human to add them):

1. what size breaker does a 6kw sauna heater need
2. what size breaker for an 8kw sauna heater
3. what wire size for a 6kw sauna heater
4. sauna electrical requirements
5. does an infrared sauna need a dedicated circuit
6. can I plug an infrared sauna into a regular outlet
7. what size sauna heater do I need for a 6x6 sauna
8. sauna heater size calculator
9. do I need a 240v outlet for a sauna
10. how many amps does a home sauna use
11. can my 100 amp panel handle a sauna
12. does a sauna heater need a GFCI
13. sauna heater sizing glass door adjustment

**Search Console queries and pages to watch:**
- queries containing `breaker`, `wire size`, `amp`, `240v`, `electrical`, `dedicated circuit`,
  `heater size`, `kw` together with `sauna`;
- pages `/pages/sauna-electrical-*`, `*-kw-sauna-heater-breaker-size`, and the 131 model pages.

**Baseline status:** NOT captured. No Search Console property is connected to this session
(`search_console_list_sites` returned none), and Ahrefs' plan does not cover Keywords Explorer.

**Volumes (Ubersuggest, US, monthly):**

| Query | Volume | KD |
|---|---|---|
| sauna heater size calculator | 170 | 20 |
| sauna electrical requirements | 140 | 10 |
| infrared sauna electrical requirements | 90 | 12 |
| what size sauna heater do I need | 50 | — |
| sauna heater sizing chart | 40 | — |
| sauna wiring requirements | 20 | — |
| per-kW breaker and wire queries, "sauna breaker size" | 0 | — |

---

## 8. Decisions needed

**D1. What is a "manufacturer-stated" breaker answer?**
- (a) A source-labelled circuit ("240V / 30AMP (Stove)", or an amperage the R3 rule ties to a
  circuit) is shown in the manufacturer's own words as "Circuit (stated)" and wins over code.
  It is never relabelled "breaker".
- (b) Only `breaker_amps` counts.

**Recommend (a).** It is what the source says, and it keeps the tool model-led.

**D2. Continuous load: 125% (Article 424) or 100% (Article 422).**
- (a) Build with 125% as the conservative default and flag all 18 per rule 1.
- (b) Build with 100%.
- (c) Ship no code-based breaker where a manufacturer circuit exists, until the electrician
  answers.

**Recommend (a) for the preview,** with the electrician's answer as review item #1 before
launch. Every heater-maker table seen so far (HUUM Table 2, Harvia KIP) gives 30 A for 6 kW, so
(a) is likely to be corrected, and I'd rather be corrected toward the manufacturer than away
from it.

**D3. The extraction gap.**
- (a) Run an INH Verified round first: add a `wire_gauge` field and extract `breaker_amps` and
  wire from the manuals already cached, under the "rating belongs to the model number beside it"
  binding.
- (b) Build the tool on the database as-is and run that round after.

**Recommend (b).** The tool's precedence makes new values flow in without code changes. The
database round is the bigger lever and deserves its own brief.

**D4. The 30% gate:** with D1(a), 37.4% of priced INH SKUs; with D1(b), 0%.
**Recommend:** lead with the model picker, with manual entry as an equal first-step option, not
behind a link. 53% of priced INH SKUs have no Verified record at all.

**D5. kW stated, voltage not (9 live records).**
- (a) Invite the reader to enter it from the spec plate.
- (b) Show 208 V and 240 V side by side as conditionals.
- (c) Assume 240 V.

**Recommend (a).** (c) is a guess.

**D6. Answer pages.**
- (a) Ship 6 kW and 8 kW only.
- (b) (a) plus the infrared dedicated-circuit page.

**Recommend (b).** The infrared page is better grounded (63 models).

**D7. Sizing disagreement.** Show all charts side by side with a flag when they span more than
one standard size (the brief's rule 6). **Recommend:** yes, and exclude Scandia's open-ended
maximums from the range comparison, because it publishes no minimums.

**D8. Preview mechanics** (unpublished pages 404).
- (a) Create the pages PUBLISHED with `seo.hidden` (noindex, out of the sitemap), with the
  server-rendered content in the page body so MAIN shows real content until the theme's
  template exists.
- (b) Verify locally (Liquid renderer) plus the preview theme for the model-page link only.

**Recommend (a).** It is the only way to meet "load the real preview URL". It is a live write
(🟡), reversible with `deploy_pages.py --pages draft`.

**D9. Preview theme.**
- (a) Reuse `146278776899`. It is stale against MAIN, so its INH Verified files and Round 23b
  changes differ.
- (b) Duplicate MAIN into a fresh preview slot (17 of 20).

**Recommend (b).** Then `verified_theme_check.py` passes on it and the model-page link previews
correctly.

**D10. Handles:** §4. **Recommend** the tool at `sauna-electrical-requirements`, with
`sauna-heater-size-calculator` as a second page using the same section in sizing mode (170/mo is
the larger query).

**D11. `/tools/will-it-fit`:** leave it or point it at the hub. **Recommend** the hub.
`panel-check` → the tool, at go-live.

**D12. Code edition cited.**
- (a) 2023, the most-adopted (20 states), with 2026 cross-references confirmed by the
  electrician.
- (b) 2026 only.

**Recommend (a).** The page names which edition each number comes from.

**D13. Wire-gauge assumption.** Show the code-based minimum for both wiring methods (NM cable at
60 °C, conductors at 75 °C), labelled. Note that heater manuals require 90 °C copper inside the
sauna walls. **Recommend:** both rows. A single row hides an assumption.

**🔴 Human:** arrange the licensed-electrician review. The packet is produced in Part B.

---

*Part A stops here. Nothing is built and nothing live has changed.*
