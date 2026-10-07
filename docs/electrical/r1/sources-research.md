# Sauna electrical and heater-sizing tool: primary-source research

Researched 2026-10-07. Everything here was read-only: no forms, no logins, at most one request every 2 s per host. PDFs were downloaded to the scratchpad and read through their text layer with pypdf. "pN" means the PDF's physical page number. Anything not read from a primary document is marked **UNVERIFIED**.

Unit note: 1 m³/m² = 3.28 ft³/ft², and 1.2 m³/m² = 3.94 ft³/ft². Example room: 6×6×7 ft = 252 ft³ = 7.14 m³. Glass door: 2×6 ft = 12 ft² = 1.115 m².

---

## PART 1: Manufacturer heater-sizing charts

### 1. Harvia: KIP (US/UL) manual
- URL: https://pim.harvia.com/rockon-images/CIP/asset/download/3c5b6375-efcf-42bf-86ea-4ff1ab4796a9/6120. This is the manual linked from the harvia.com/en-US KIP60B UL product page (JH60BU1UL).
- Document: "BY05-1516 Harvia KIP Electric sauna heater, Instructions for Installation and Use". Covers models KIP-30/45/60/80-B1 (240 V 1-phase) and -B3 (208 V 3-phase). PDF metadata: created 2026-08-05, modified 2026-08-12. The heater "complies with the standard UL875".
- **Table, p14 (§5.3 Specifications):**

| Model | kW | Room volume min | Room volume max | Floor area min/max | Current (240 V B1 / 208 V B3) | Cable size (B1 / B3) |
|---|---|---|---|---|---|---|
| KIP-30 | 3.0 | 2.4 m³ / 84 ft³ | 3.7 m³ / 130 ft³ | 10 / 20 ft² | 12.5 / 8.3 A | 12/2 / 14/3 |
| KIP-45 | 4.5 | 2.8 m³ / 100 ft³ | 6 m³ / 210 ft³ | 16 / 30 ft² | 18.8 / 12.5 A | 10/2 / 14/3 |
| KIP-60 | 6.0 | 4.8 m³ / 170 ft³ | 8.5 m³ / 300 ft³ | 28 / 40 ft² | 25.0 / 16.7 A | 10/2 / 12/3 |
| KIP-80 | 8.0 | 7.1 m³ / 250 ft³ | 12 m³ / 425 ft³ | 40 / 65 ft² | 33.3 / 22.2 A | 8/2 / 10/3 |

  Minimum room height is 1900 mm / 75" (USA) and 1980 mm / 78" (Canada). Construction guidance (p16): R11 insulation, ceiling no higher than 2300 mm / 90".
- **Adjustment rules, p16 (§6.2):** for uninsulated brick, glass block, glass, concrete and tile walls, "Add 1,2 m³ to the volume of the sauna for each non-insulated wall square meter". The manual's own example: a 10 m³ room with a glass door needs about the output of a 12 m³ room. Log saunas: "multiply the cubic volume of a log sauna by 1.5". The manual gives no imperial version of the glass rule (1.2 m³/m² = 3.94 ft³/ft²).
- Harvia also has a web calculator at https://www.harvia.com/en-US/sauna/saunas/sauna-calculator/. Its inputs are W/H/D (ft), "Made of log", "Glass door", and non-insulated wall area (ft²). The calculator's internal formula was not inspected (**UNVERIFIED**).
- ⚠️ **Harvia contradicts itself.** The harvia.com/en-US product page for EU KIP60 HBK600230S says 177–283 ft³ (KIP45 106–212, KIP80 247–424). Those figures are 5–8 m³, against the US manual's 4.8–8.5 m³. Datasheet: https://pim.harvia.com/media/download/d%252F2%252Fd%252F7%252Fd2d7d07e136d44c8880931e7a06d8d8edatasheet_HBK600230S_en_202505240400.pdf
- Harvia 9 kW: the harvia.com/en-US Cilindro PC90 HPC900400 page gives 9 kW and 283–494 ft³. Its electrical options are 230 V 3~ / 400 V 3N~, so this is **not** a US 240 V single-phase UL model. https://www.harvia.com/en-US/products/HPC900400/cilindro-pc90-90-kw-steel
- Harvia 10.5 kW (US/UL): not located (**UNVERIFIED**).
- **Excluded:** "Sizing Your Harvia 2023" at cdn.shopify.com/s/files/1/0751/2834/0763/... is branded "Get Your Harvia From www.thesaunaheater.com", so it is a retailer document. It says to add "2 cubic feet" per ft² of cold surface, "excluding door". Both points conflict with the Harvia manual.

### 2. Finnleo (Sauna360 US)
- Downloads index: https://www.finnleo.com/downloads
- **Designer SL2, 4.5/6.0/8.0 kW.** https://www.finnleo.com/hubfs/Finnleo%20Downloads/72-0130%20Designer%20SL2%20Heater%2009-23-2020.pdf. The document carries "72-0130 02-08-2022" (314 SKSM 221 F). **Table on p2:**

| Model | kW | Min floor area | Min room (74" wall) | Max room (96" wall) | Amps at 240 V 1-phase | Wire, 240 V 1-phase |
|---|---|---|---|---|---|---|
| Heater 4.5 (1712-45-0207) | 4.5 | 12 ft² | 100 ft³ | 210 ft³ | 18.8 | 2 #10 AWG + GR |
| Heater 6.0 (1712-60-0207) | 6.0 | 21 ft² | 175 ft³ | 310 ft³ | 25 | 2 #10 AWG + GR |
| Heater 8.0 (1712-80-0207) | 8.0 | 31 ft² | 250 ft³ | 425 ft³ | 33.3 | 2 #8 AWG + GR |

  The PDF text layer separates "310" from the 6.0 row. Check it visually before relying on it.
- **Pro/Laava with SL2-C, 10.5/12/14.4 kW.** https://www.finnleo.com/hubfs/Finnleo%20Downloads/72-0139%20314%20SKLE%2084%20A%20Laava%20Pro%20Heater%20with%20SL%202%20Control%2005-05-2021.pdf. The document carries "72-0139 02-08-2022". **Table 1 on p5:** 10.5 kW needs 48 ft² minimum floor area and covers 390 ft³ (78" wall) to 600 ft³ (96"). 12.0 kW covers 510–740 ft³ and 14.4 kW covers 630–950 ft³. At 240 V 1-phase, the 10.5 kW draws 43.8 A on 2 × 30 A breakers and #10 AWG. Single-phase units run on two circuits, "grouped and marked per NEC". These heaters are "ETL approved by Intertek", and wiring must follow "the NEC and local codes".
- Finnleo publishes no 9 kW model in these tables.
- **Glass or uninsulated-wall rule:** none in either Finnleo manual (searched for glass, window and log).

### 3. Amerec, now Helo Sauna (US)
- amerec.com now shows a rebrand to Helo Sauna and hosts only steam products. https://amerec.com/downloads lists no sauna-heater manuals. The Amerec heater line is the shared Sauna360 range: Designer, Pro, Laava.
- **Helo US FAQ:** https://helosauna.com/en-us/faq
  - Volume is calculated as L × W × H, with height capped at 96". The FAQ cites UL-875 for the 8 ft maximum.
  - For heavy walls such as concrete, glass or tile, it says to add one cubic foot to the room volume for every square foot of heavy wall material. That is **1 ft³ per ft²**.
- Helo product pages: Designer-B covers 100–425 ft³. Helo-hosted manuals include Himalaya SL2 and Dual Laava Pro at helosauna.com/hubfs/Helo%20US%20Downloads/... (not parsed).
- Retailer-only Amerec figures (thesaunaheater.com, wcsaunas.com) were excluded.

### 4. HUUM
- **DROP manual (EU edition):** https://huum.eu/wp-content/uploads/2022/05/H1001L02_v6_DROP_User_Manual_EU_2025_PRINT.pdf. File name says v6 2025. **Table 1 on p4 (English):**

| Model | kW | Room (m³) |
|---|---|---|
| DROP 4 | 4.5 | 3–7 |
| DROP 6 | 6 | 5–9 |
| DROP 7 | 7.5 | 7–11 |
| DROP 9 | 8.5 | 8–13 |

  - Rule (p4): for uninsulated brick, tile or glass walls, add 1 m³ per m² of such wall.
  - p11: massive surfaces should be insulated with 50–100 mm of insulation.
  - The German table on p36 mislabels the 7.5 kW row as "DROP 9", a translation error in the manual itself.
- **HUUM web guide:** https://huumsauna.com/sauna-heater-size-calculator-how-to-choose-the-right-power-rating-for-your-sauna/. Published 2025-05-15, modified 2026-01-13.
  - Coefficient k = 1 (metric) or 3.3 (imperial) for "glass, log wall or other non-insulated surface".
  - Heuristic: "1 m³ = 1 kW", or 35 ft³ = 1 kW.
  - The guide counts **log walls as k=1 per area**, whereas Harvia multiplies log-room volume by 1.5.
- A US/UL HUUM manual in ft³ was not located (**UNVERIFIED**).

### 5. Saunacore
- **Product catalogue PDF:** https://saunacore.com/wp-content/uploads/2022/11/Saunacore_Brochure-Updated_Cover.pdf. 64 pages; PDF modified 2022-11-28.
- **"Selecting a Sauna Heater", p46:**
  - Divide the cubic footage by 50 to get kilowatts, then select the next model size exceeding the calculated room cubic feet. Suggested room height is 7 ft maximum.
  - Worked example: 7×5×7 = 245 ft³, ÷ 50 = 4.9 kW, so a 5 kW heater.
  - Approximate maximum room volume (ft³) by kW for SE/SV/ULT/Elite R: 2→100, 3→150, 4→200, 5→250, 6→300, 7.5→375, 9→450, 10.5→525.
  - 240 V 1-phase amps: 8.4, 12.5, 16.7, 20.8, 25.0, 31.3, 37.5, 43.8.
  - Saunacore has **no 4.5 or 8 kW** in this range, publishes **no minimum volume**, and states **no glass rule**.

### 6. Tylö (US)
- **Sense UB Series, Rev B (72-0157, 8/21/24):** https://tylo.com/wp-content/uploads/2025/10/72-0157_Sense_UB_Bliss_Traditional_Manual_Rev_B_08-21-2024.pdf. Table 1 is on p9 (printed page 4):
  - Sense UB 6: 6.0 kW, 16 ft² minimum floor, 135 ft³ (75" wall) to 319 ft³ (96"). 240 V 1-phase, 25 A, 2 #10 AWG + GR.
  - Sense UB 8.3: 8.3 kW, 24 ft², 195–440 ft³. 240 V 34.6 A on 2 #8 AWG; 208 V 1-phase 39.9 A on #6 AWG.
  - Glass note: every square foot of glass adds one cubic foot of volume. That is **1 ft³ per ft²**.
- **Sense UB Mini, Rev C (72-0161, 4/8/26):** https://tylo.com/wp-content/uploads/2026/04/tylo-sense-ub-min-series-bliss-traditional-sauna-heater-instalation-owners-manuals-rev-c-04-08-2026.pdf. Covers the 1.7/2.2 kW 120 V models with the same glass note on p9. Ventilation per UL 875 (p12): for R < 31 ft², V > 9.3 in²; for R > 31 ft², V > 0.3 × R.
- **Sense Sport USA (2900-5240, 2022-06-15):** https://tylo.com/wp-content/uploads/2025/10/2900-5240-Sport-installation-USA_2022-06-15.pdf. Table 1 on p3 gives kW and ft³ ranges by voltage:

| Model | 208 V | 240 V |
|---|---|---|
| SSU 5 | 3.5 kW, 75–105 ft³ | 4.6 kW, 75–220 ft³ |
| SSU 7 | 5.3 kW, 130–175 ft³ | 7.0 kW, 130–320 ft³ |
| SSU 8 | 6.3 kW, 195–285 ft³ | 8.3 kW, 195–440 ft³ |

  This manual has no glass rule. Note that **the volume ranges change with supply voltage**.

### 7. Scandia (US)
- Product pages only. No manual was found on scandiamfg.com; one exists on a retailer host (am-finn.com) and was not used.
  - https://scandiamfg.com/products/electric-ultra-sauna-heater-small-thermostat: 3.0 kW up to 140 ft³; 4.5 kW up to 210 ft³.
  - https://scandiamfg.com/products/scandia-manufacturing-electric-ultra-sauna-heater-medium-6-0kw: 6 kW 294 ft³ max, 7.5 kW 448 ft³ max, 9 kW 616 ft³ max.
- Scandia publishes **no minimum volumes and no glass rule**. Its 9 kW maximum of 616 ft³ is far above Saunacore's 450.

### 8. Polar
- No manufacturer-owned document found. polarsauna.com serves a 123saunas.com favicon and returned no sizing data. **UNVERIFIED / not used.**

### Adjustment-rule comparison (as stated)

| Source | Glass / uninsulated surface | Log walls |
|---|---|---|
| Harvia KIP manual (US) | +1.2 m³ per m² (≈3.94 ft³/ft²); a glass door counts | volume × 1.5 |
| HUUM DROP manual (EU) | +1 m³ per m² (brick, tile, glass) | not stated |
| HUUM web guide | k = 1 (m) / 3.3 (ft) | same k as glass, per area |
| Helo US FAQ (ex-Amerec) | +1 ft³ per ft² of heavy wall | not stated |
| Tylö Sense UB (US) | +1 ft³ per ft² of glass | not stated |
| Finnleo, Saunacore, Scandia, Tylö Sport | none stated | none |
| (retailer) "Sizing Your Harvia" | +2 ft³ per ft², door excluded | not stated |

For the 12 ft² glass door, the volume adders are: Harvia +47 ft³ (1.34 m³), HUUM +39.6 ft³ (1.11 m³), Helo/Tylö +12 ft³. **That is a 4× spread.**

### Worked example: 252 ft³ (7.14 m³) insulated room, then the same room with a 12 ft² glass door

| Chart | No glass | With 12 ft² glass door | kW eligible (no glass → with glass) |
|---|---|---|---|
| Harvia KIP US | 252 ft³ / 7.14 m³: KIP60 (170–300) ✓, KIP80 (250–425) ✓, KIP45 ✗ | 299 ft³ / 8.47 m³: KIP60 ✓ (just under 300 / 8.5), KIP80 ✓ | 6.0–8.0 → 6.0–8.0 |
| Harvia PC90 (EU 400 V page) | 252 < 283 ✗ | 299 ≥ 283 ✓ | 9 kW becomes eligible once glass is added |
| HUUM DROP | 7.14 m³: DROP 4 ✗ (>7), DROP 6 ✓, DROP 7 ✓, DROP 9 ✗ | 8.25 m³: DROP 6 ✓, DROP 7 ✓, DROP 9 ✓ | 6–7.5 → 6–8.5 |
| HUUM web heuristic | 7.1 kW (252 / 35) | 8.3 kW (291.6 / 35) | a point value, not a range |
| Finnleo Designer | 252: 6.0 ✓ (175–310), 8.0 ✓ (250–425) | no rule; with the Helo +1 rule, 264 gives the same result | 6.0–8.0 → 6.0–8.0 |
| Tylö Sense UB | 252: 6.0 ✓ (135–319), 8.3 ✓ (195–440) | 264: same | 6.0–8.3 → 6.0–8.3 |
| Tylö Sport (240 V) | 252: SSU7 7.0 ✓ (130–320), SSU8 8.3 ✓; SSU5 ✗ | no rule | 7.0–8.3 |
| Saunacore | 5.04 kW calculated; 252 > 250, so next size up is **6 kW** (the method gives one value) | no rule | 6 → 6 |
| Scandia | 252 > 210, so 4.5 ✗; 6 kW ✓ (≤294); 7.5/9 kW have no minimum, so they are not excluded | no rule | 6 (to 9, unbounded) |

**Where charts disagree by more than one standard size** (4.5 / 6 / 8 / 9 / 10.5):
- With glass, Harvia's own data admits a 9 kW heater (PC90 ≥ 283 ft³), but Saunacore's method gives exactly 6 kW. That is two steps apart.
- Without glass, Scandia's open-ended maxima would admit 9 kW while Harvia excludes it. Again 6 vs 9.
- Everything else falls within adjacent sizes (6–8). Every chart excludes 4.5 kW for this room: the stated maxima are 210 / 210 / 220 ft³ and 7 m³.
- Not reconciled, per the brief.

---

## PART 2: Infinite Sauna and Outdoor Steam Sauna

### (a) infinitesauna.com/electrical

| Item | Finding |
|---|---|
| What it is | A **database table**, not a calculator. "96 models currently have a documented voltage." Columns: Model, Heat type, Voltage, Amperage, Plug/connection, Heater output |
| Inputs / outputs | No inputs. It outputs no breaker size, no wire gauge and no formula. Unknown values show as "Not verified"; the page says these "are intentionally not inferred from similar models" |
| NEC references | None. Only an advisory to verify manual, breaker, receptacle, conductor and GFCI with the manufacturer and a licensed electrician |
| Models listed | Specific SKUs: Dynamic, Golden Designs, Maxxus, SaunaLife, Sun Home, Scandia BS64-T, Clearlight, Kohler. Each links to /models/<sku>/ |
| Data sources | Model pages show a "Source record". Example: GDI-8506-01 lists inhousewellness.com, goldendesigninc.com and ampsrus.com, with priority "manufacturer documentation, manufacturer page, authorized retailer, then secondary retailer" |
| Structured data | The /electrical/ page has **no JSON-LD**. Model pages carry schema.org `Product` with `offers`, including an InHouse Wellness offer |
| Dates | sitemap `lastmod` 2026-10-05; model page says "refreshed 2026-10-05"; site says "updated weekly". No visible last-updated date on /electrical/ |
| URLs | /electrical/, /guides/120v-vs-240v/, /120v-saunas/, /240v-saunas/, /models/<sku>/, /data/ (CSV/JSON), /methodology/, /llms.txt. robots allows all |

**Numbers that conflict with the manufacturer manuals or with arithmetic:**
- Several traditional 8.0 kW models (GDI-8506-01, -8203-01, -7203-01) are listed as "120V/240V, 40A". An 8 kW load at 120 V would need about 66.7 A. Harvia's US manual gives KIP80 33.3 A at 240 V. The 120 V half of that pairing is not credible.
- The amperage field does not say whether it is current draw or breaker size. For 6 kW models it shows 30A, while the Harvia and Finnleo manuals give 25 A draw. A 30A breaker figure matches neither a 25 A draw nor 125% of it (31.25 A), so the field cannot be read safely either way.
- Scandia BS64-T is listed as 9.0 kW, 220 V, NEMA 10-30R. That is about 40.9 A on a 30 A receptacle configuration, which is internally inconsistent.

### (b) outdoorsteamsauna.com/heater-sizing/

| Item | Finding |
|---|---|
| Inputs | Interior length, width and height (ft); glass / uninsulated surface (ft²) |
| Formula (from /assets/app.js) | `effective = L*W*H + glass*3.3`. The page describes 3.3 as "the imperial form of a 1 m³-per-m² approach" and links HUUM. It then matches the result against a hardcoded `window.HEATERS` list of 3 rows |
| Reference rows | Harvia Cilindro PC70 6.8 kW 212–353 ft³ (harvia.com/**en** HPC700400); PC90 9.0 kW 283–494 ft³ (en-US HPC900400); PC110EE 11.0 kW 318–636 ft³ (en HPC1104EE) |
| Outputs | Effective ft³ plus the matching rows. No kW recommendation, breaker, wire gauge or amps |
| Electrical guide | /guides/electrical/ (TechArticle, `dateModified` 2026-09-16) says kW "is an energy number—not a wiring plan". No NEC citations |
| Cost calculator (/operating-cost/) | `kWh = kW × (warm/60 + session/60 × 0.6)`. The 0.6 session duty factor has no source on the page (**UNVERIFIED**) |
| Schema | JSON-LD `WebApplication` and `SoftwareApplication` (sizing page), `TechArticle` (electrical guide) |
| Dates / version | llms.txt: dataset version 2.0, updated 2026-09-28; NOAA data through 2026-09-23; EIA period 2026-07; sitemap `lastmod` 2026-09-28 |

**Conflicts with Part 1:**
- The 3.3 ft³/ft² adder matches HUUM but **not** Harvia (3.94, and ×1.5 for logs), and is 3.3× the Helo/Tylö rule (1.0).
- All three reference heaters are **EU-voltage Harvia variants**. The PC90 page shows 230 V 3~ / 400 V 3N~. None is a US 240 V single-phase UL model.
- There is no log-wall input.
- Code concern: `Number(x) || 0` turns empty fields into 0, so the result reads "0 ft³". That is the missing-value-as-zero pattern our own lint forbids.

---

## PART 3: Code references (primary sources): INTERNAL REFERENCE ONLY

> Part B §1 (2026-10-07): nothing in this part is published. The tool computes no breaker, wire or code minimum, and no code constant exists in the build.

- **Current NEC edition is 2026, not 2023.** NFPA's "Understanding NFPA 70" page says the 2026 edition superseded 2023 and that the 2029 edition is expected in late 2028. https://www.nfpa.org/education-and-research/electrical/understanding-nfpa-70-national-electrical-code
  - Per NFPA, the Standards Council issued the 2026 edition on 2025-08-20, effective 2025-09-09.
  - NFPA 70 development page: https://www.nfpa.org/codes-and-standards/nfpa-70-standard-development/70. The 2026 edition **reorganized** articles and sections, including new Chapter 2 articles and Chapter 8 losing its stand-alone status.
- **NFPA adoption map:** https://www.nfpa.org/education-and-research/electrical/nec-enforcement-maps. As of 2026-08-03:

| Edition in effect | States |
|---|---|
| 2026 | 6: CO, ME, MA, MN, ND, WY |
| 2023 | 20 |
| 2020 | 15 |
| 2017 | 3 |
| 2008 | 2 |

  Arizona, Mississippi and Missouri adopt locally only. Upcoming changes: Wisconsin moves to 2023 on 2026-09-01; South Carolina moves to 2023 on 2027-01-01. Michigan applies 2014 to one- and two-family dwellings. Indiana applies 2017 to dwellings.
- **UL 875, "Electric Dry-Bath Heaters":** Edition 10, published and ANSI-approved 2024-07-08. https://www.shopulstandards.com/ProductDetail.aspx?UniqueKey=46790
  - Scope: dry-bath heating equipment rated 600 V or less, installed in accordance with NFPA 70 (NEC). Steam-bath heaters are excluded.
  - The Harvia KIP US manual states UL875 compliance.
  - Tylö's ventilation formula and Helo's 96" ceiling cap are both attributed to UL 875.
- **Article 424 vs 422: UNVERIFIED.** No primary or free-access NFPA statement was found that classifies sauna heaters under either article.
  - From memory only, not verified this session: in the 2020/2023 editions, 424.4(B) covers branch-circuit sizing at 125% for fixed electric space heating (424.3(B) in 2017). Section 422.10 covers appliance branch circuits; 422.13 covers storage-type water heaters, so it is not relevant to saunas.
  - Whether the 2026 reorganization renumbered these sections is **UNVERIFIED**.
  - Whether the NEC text uses the word "sauna" anywhere is **UNVERIFIED**.
  - Reading the free-access NEC requires an NFPA login, which this research did not do.
  - The manuals sidestep the question with "per NEC and local codes". Finnleo notes that single-phase 10.5–14.4 kW units use two circuits "grouped and marked per NEC".

## Not done / open
- Harvia US 9 and 10.5 kW (UL) manual tables.
- HUUM US (ft³) manual.
- Polar and Amerec original documents.
- Visual check of the Finnleo 6.0 "310" cell.
- Internals of the Harvia web calculator.
- NEC 2026 section numbers.
