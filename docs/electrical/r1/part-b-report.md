# Electrical & Heater Sizing Tool — Round 1, Part B report

2026-10-07 · branch `electrical/r1-tool` · **preview built; nothing launched, nothing indexed, MAIN untouched**

Part B §1 replaced Round 1's rules 1 and 2 and D2. The tool shows **manufacturer-stated values only**.
- No code-based breaker, wire gauge or code minimum is computed or published, and no code
  constant exists in the build.
- The one calculation is heater current draw, from a sourced kW and voltage, labelled as
  calculated.
- The code research stays internal: `sources-research.md` Part 3 and `part-a-report.md` §1.4.

## 1. Preview

| | |
|---|---|
| **Preview theme** | **`188725788739`**, "Electrical R1 preview (duplicate of MAIN)". Duplicated from MAIN `167150092355` on 2026-10-07; role UNPUBLISHED; slots 17 of 20. Round 13 (`146278776899`) untouched |
| Enter preview | `https://inhousewellness.com/?preview_theme_id=188725788739` (Shopify sets a cookie and drops the query string; after that the URLs below render in the preview) |
| Tool | `/pages/sauna-electrical-requirements` (try `?model=salus-solara-6-person`) |
| Heater sizing | `/pages/sauna-heater-size-calculator` (try `?len=6&wid=6&hgt=7&glass=12`) |
| Answer pages | `/pages/6-kw-sauna-heater-breaker-size`, `/pages/8-kw-sauna-heater-breaker-size`, `/pages/infrared-sauna-dedicated-circuit` |
| Methodology | `/pages/sauna-electrical-methodology` |
| Model-page link | e.g. `/pages/sauna-database/salus-solara-6-person` ("Check your home's electrical for this model"), **preview theme only** |

**Deploy path, a deviation from Round 1's "existing GitHub Actions workflow only".**
- This session has no `gh` CLI, so it cannot dispatch Actions.
- `deploy-theme.yml` is also hard-wired to the calculator's manifest and redirects.
- Files therefore went through `scripts/electrical_deploy.py`. It reuses the INH Verified session
  path:
  - MAIN resolved at run time and refused;
  - Round 13 refused;
  - UNPUBLISHED only;
  - sections before templates;
  - MD5 read-back.
- **Final read-back: 9 of 9 byte-identical.**

## 2. Pages created live-but-hidden (D8) and the teardown

| Handle | Page id | Template |
|---|---|---|
| sauna-electrical-requirements | `gid://shopify/Page/167399227459` | inh-electrical-tool |
| sauna-heater-size-calculator | `gid://shopify/Page/167399260227` | inh-electrical-tool |
| sauna-electrical-methodology | `gid://shopify/Page/167399292995` | inh-electrical-page |
| 6-kw-sauna-heater-breaker-size | `gid://shopify/Page/167399194691` | inh-electrical-page |
| 8-kw-sauna-heater-breaker-size | `gid://shopify/Page/167399325763` | inh-electrical-page |
| infrared-sauna-dedicated-circuit | `gid://shopify/Page/167399358531` | inh-electrical-page |

How the pages are hidden:
- All six are published with `seo.hidden = 1`.
- **Shopify itself injects `<meta name="robots" content="noindex,nofollow">`** on MAIN's render
  and on the preview. This was proved on one page before the others were created.
- None of the 6 is in the live sitemap (818 URLs read).
- **0 inbound links** from any page, article, menu or MAIN theme file (`check-pages.txt`). The
  first run reported one; it was another store's URL with the same path, and the check now
  requires our own host.
- On MAIN these URLs render through the default page template (title + body).

**Teardown, one command:**

```bash
.venv/bin/python scripts/electrical_deploy.py teardown --write
```

- The dry run is in `teardown-dry-run.txt`. It lists the 6 pages above and theme `188725788739`,
  and nothing else.
- Ids come only from `data/electrical/preview-state.json`.

**Redirects (D11), not created:** `scripts/electrical_redirects_launch.py`. The dry run passes:
- both sources answer 404, which a redirect needs in order to fire;
- both targets answer 200.

## 3. Verification (render-side, real preview URLs)

`scripts/electrical_verify.py`: **23 of 23 PASS**. Results are in `shots/verify-results.json` and
the screenshots in `shots/`.

| § 7 item | Screenshot | Asserted |
|---|---|---|
| model with a stated circuit | `01-stated-circuit-maxxus-seattle.png` | quote "MX-J206-01 120VAC 15AMP Dedicated Circuit Required" verbatim, with grade · source · date |
| one of Part A's 18 | `02-part-a-model-salus-solara.png` | stated circuit, no flag or code note; current draw in its own card, labelled calculated |
| rated kW, no stated circuit | `03-rated-kw-no-circuit-almost-heaven-sutton.png` | "doesn't publish a circuit requirement…", plus draw from the manufacturer's 6 kW and the reader's 240 V, labelled as such |
| no rated kW | `04-no-rated-kw-almost-heaven-allegheny.png` | designed unknown state; nothing computed |
| priced INH sauna, no record | `05-unmapped-inh-product.png` | no coverage claimed; draw only from the reader's figures |
| 120 V plug-in infrared | `06-plug-in-120v-clearlight-premier-2.png` | "Plugs into a standard household outlet." and "NEMA 5-15P", both quoted |
| sizing, 6×6×7 ft + 12 ft² glass | `07-sizing-6x6x7-glass-door.png` | 6 charts listed separately (results below); the glass-allowance sentence |
| 6 kW page, JavaScript off | `08-answer-6kw-js-off.png` (+ the other 3) | all 15 rows readable |
| electrician sheet, print | `09-electrician-sheet-print.png`, `.pdf` | one page: sourced values, labelled draw, questions, no verdict |
| noindex / sitemap / inbound links | `check-pages.txt` | 12 renders noindex; 0 in sitemap; 0 inbound |
| no code value can render | `grep-no-code-values.txt` + `tests/test_electrical.py` | 0 matches; a mutation (`draw * 1.25` injected) was caught, then reverted |
| determinism | verify #10 | identical output twice; the build twice gives no drift |
| teardown dry run | `teardown-dry-run.txt` | 6 pages + 1 theme, nothing else |

**Sizing results** for the 6×6×7 ft room with a 12 ft² glass door. They match Part A's
hand-worked example:

| Chart | Result |
|---|---|
| Harvia | 6–8 kW |
| HUUM | 6–8.5 kW |
| Finnleo | 6–8 kW |
| Tylö | 6–8.3 kW |
| Saunacore | 6 kW |
| Scandia | 6 kW or larger |

**One honest gap in §7:** no live model has BOTH rated kW and its voltage sourced *without* a
circuit statement. The four that have both (Sun Home Nova 3/6, Solaris 4/6) all quote a dedicated
circuit. Case 3 therefore uses Almost Heaven Sutton: 6 kW is sourced, and the reader supplies the
voltage.

**Determinism note:** one verify run failed #10 seconds after a deploy. The 375-character
difference was exactly the block that deploy had removed, so one load had been served the
previous JS from cache. Four further loads were identical, and every later run passed.

### Hand check against manuals (quotes found on the cited page, by text extraction of the cached PDF)

| Model | Manual | Page | What it says | Tool shows |
|---|---|---|---|---|
| Maxxus Seattle (MX-J206-01) | Maxxus line manual (39 pp) | p. 1 | "MX-J206-01 120VAC 15AMP Dedicated Circuit Required" | same, verbatim; the MX-J306-01 row beside it is excluded |
| Sun Home Eclipse 2 | spec sheet p. 1; assembly guide (32 pp) p. 8 | 1, 8 | 120V / 2,820W / 23.5A, NEMA L5-30P; "requires a dedicated, GFCI-protected 120V, 30A circuit…"; GFCI required | all four quoted on those pages |
| Sun Home Nova 3 | assembly guide (39 pp) | pp. 3, 4, 6 | p. 4 "hardwired to a dedicated 240 V circuit"; p. 6 "Heater Load Current 25 A … Circuit Breaker 30 A … 10 AWG" | p. 3/4 quotes; the calculated draw is **25.0 A** (6 kW ÷ 240 V), matching p. 6. The p. 6 breaker and AWG are **not** shown (not in the database), and the row links p. 6 as a known gap |

## 4. Search Console baseline: NOT captured, and what is missing

- **HYPD connector** (the only Search Console tool in this session):
  - `search_console_list_sites` returns `{"sites": []}`;
  - no Google Search Console connection exists on the HYPD account this session uses.
  - **Fix:** connect it under HYPD → Connect → Ad Platforms → Google Search Console, with the
    Google account that owns the `inhousewellness.com` property, either
    `sc-domain:inhousewellness.com` or `https://inhousewellness.com/`.
- **Ahrefs connector:**
  - `management-projects` and `keywords-explorer` both answer "Insufficient plan";
  - its GSC endpoints need a project, and the API plan does not reach projects.
- The `plugin:marketing:ahrefs` connector is listed as needing authentication.
- **Nothing else blocked.** `docs/electrical/r1/baseline-gsc.json` is NOT written; there is no
  data to put in it.

## 5. Coverage after the scope change

**Priced INH saunas (139):**

| Shows | Count |
|---|---|
| manufacturer-stated circuit | **38 (27.3%)** |
| heater current draw only | **0** |
| neither | **101**: 74 have no database record, 25 have a record that is not published live, 2 have a live record that states nothing |

- All 101 get manual entry (kW + voltage → draw only), with the reason in words.
- Part A's 52 counted mapped records whether live or not. The tool can show only live ones.
- **The <30% trigger (Round 1 §7) now fires: 27.3%.** Per D4 the tool already offers manual entry
  as an equal first step. Decision 1 below asks whether that is enough.

**Live database (131):**
- 89 show a stated circuit;
- 42 show neither;
- 22 also show a calculated draw.

## 6. Draft scope for the database round

`database-round-scope.json`, evidence only:

**(a) Live records whose cited documents state breaker or wire values not in the database.**
- 83 records cite a document containing a breaker figure; 5 contain a wire size.
- By brand: Dynamic 25, Sun Home 14, Redwood 13, Salus 13, Maxxus 12, Golden Designs 6.
- Strongest, already on the answer pages as known gaps (`data/electrical/known-gaps.json`):
  - **Sun Home Nova 3:** 30 A, 10 AWG, p. 6;
  - **Sun Home Nova 6:** 40 A, 8 AWG, p. 6;
  - **Salus Flora:** "8.0kW KIP Heaters • 40-amp double pole breaker • 8/2 wire", p. 26. This is a
    heater table, so the binding to Flora's fitted heater needs confirming.
- Many hits are line manuals or bundled Harvia heater manuals. Each figure binds to the model
  number beside it before extraction (CLAUDE.md).

**(b) Priced INH saunas without a live record, by vendor:**

| Vendor | No record | Record not live |
|---|---|---|
| Golden Designs | 6 | 19 |
| Maxxus | 21 | 4 |
| Dynamic | 13 | 1 |
| Scandia | 7 | 1 |
| SaunaLife | 7 | 0 |
| Dundalk | 6 | 0 |
| Medical Saunas | 4 | 0 |
| Finnmark | 3 | 0 |
| Mande Spa | 3 | 0 |
| Kohler | 2 | 0 |
| Ripavi | 2 | 0 |

## 7. Sweep and tests

- **Tests:** 877 pass (859 prior + 18 new). No prior assertion flipped.
- **Lint and preflight:** missing-value lint 0, across 12 render-path files, every new
  template/JS included. Preflight static clean.
- **Build and deploy:** build `--check` shows no drift; all self-tests pass, deploy dry run clean.
- **Content:** the payload gate caught `"price":` in the first schema. `offers` was removed;
  this project publishes no prices on these pages.
- **Links:** 267 checked; 1 real 404, a Golden Designs manual PDF.
  - It is no longer offered as a manual link (`data/electrical/dead-links.json`).
  - The database record is unchanged; that is out of scope.

## 8. Wording changes made for accuracy (yours to confirm)

1. **"Not stated by manufacturer" → "Not stated in the manufacturer sources we've verified".**
   - The plain version is false for Sun Home Nova 3: its manual states 30 A on p. 6, and we have
     not extracted it.
   - The tool's no-circuit line gets the same qualifier: "…doesn't publish a circuit requirement
     for this model in the sources we've verified."
2. **The answer sentence counts what the table shows.** For example: "8 state a 240 V, 30 A
   circuit… 2 more describe a circuit in other words, quoted below; for the other 5…". The first
   version said "no heater circuit amperage" above a row quoting "240V / 30A circuit".
3. **Salus Ally:** the table shows "Amperage stated, not described as a circuit: 'Heater: 6kw, 220V,
   30-amp'" rather than hiding it under "not stated".
4. **The 8 kW page says exactly "11 of the 14 listed models are from Salus."** A further clause I
   drafted about Salus was removed as unapproved brand wording.
5. **The infrared page counts 67, not the brief's 63.** 63 was Part A's count of stated
   amperages; 67 counts every circuit statement shown.
6. **Quotes drop hazard wording** ("…and can cause fatal electric…") and leading warning
   headings. The brand voice forbids fear copy. A quote whose value sits inside a warning is not
   used.

## 9. Decisions still open

1. **30% trigger (27.3%):** keep the model-led tool with equal manual entry (recommended), or lead
   with manual entry until the database round lands.
2. **Token scope:** the Admin token no longer carries `read_metaobjects`, so
   `verified_theme_check.py` fails its preview half on EVERY theme, MAIN included. The files half
   passes on both. Restore the scope before any theme publish.
3. **Launch order:**
   - deploy the model and hub link patches to MAIN through the go-live step (the repo's INH
     Verified files are deliberately unchanged);
   - clear `seo.hidden`;
   - then run the redirects script.
4. **Search Console:** connect the property (§4). The 90-day pull for the Part A §7 queries and the `/pages/sauna-database` + calculator pages is not scripted yet; it is the first step once a connector answers.
5. **The database round brief** (§6).
6. Not touched, as instructed: the duplicate BreadcrumbList on the hub and model pages, and the
   satellite sites.
