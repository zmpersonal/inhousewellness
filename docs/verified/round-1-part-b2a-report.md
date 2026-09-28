# INH Verified — Round 1, Part B2: report at the 7-brand pause

**Status: 🟡 REVIEW. Stopped after 7 brands as instructed. The remaining 7 are not run.**
Branch `verified/r1-data-foundation`. Nothing merged, deployed or put on any website. No theme,
no Shopify write, nothing sent to Infinite Sauna. Anthropic API spend: **$0**. Blotato: 0 credits.

The batch, ordered as instructed (brands INH does not sell first):
- **Not sold by INH:** Almost Heaven, Redwood Outdoors, Sun Home, Clearlight, Heavenly Heat.
- **Sold by INH:** Maxxus, Dynamic Saunas.
- **Also run:** Golden Designs again with its manuals (B1-D2), and Salus with the B1-D3/D8 attachment rules.

Rebuilding from the cache is byte-identical (`saunas.json` sha256 `00d185dd…`, `conflicts.json`
`c6dff8e4…`). The cache manifest holds 469 URLs.

## 1. Per brand

"Changed" = the source states a different value from the lead (the source value is published).
"New" = values the manufacturer states that the lead did not have.

| Brand | Adapter | Leads | Published / backlog | Confirmed | Changed | Not found | Ambiguous (withheld) | New |
|---|---|---|---|---|---|---|---|---|
| Almost Heaven | structured data (per-product JSON; catalogue answers 503) | 59 (2 fetch failures) | **42 / 13** | 115 | 11 | 52 | 31 | 21 |
| Redwood Outdoors | structured data | 18 | **17 / 0** | 49 | 9 | 17 | 19 | 0 |
| Sun Home | structured data + page layout | 15 | **15 / 0** | 86 | 9 | 6 | 6 | 53 |
| Clearlight | page layout (WordPress; `Crawl-delay: 10` honoured) | 12 | **12 / 0** | 28 | 1 | 42 | 1 | 37 |
| Heavenly Heat | structured data + page layout | 8 | **8 / 0** | 34 | 0 | 12 | 0 | 26 |
| Maxxus | structured data + PDF | 27 (4 no page) | **0 / 23** ⏸ pending B2-D1 | 211 | 17 | 5 | 24 | 23 |
| Dynamic Saunas | structured data + PDF | 26 | **0 / 26** ⏸ pending B2-D1 | 250 | 18 | 5 | 8 | 26 |
| Golden Designs (re-run) | structured data + PDF | 28 | **25 / 3** | 195 | 16 | 12 | 71 | 35 |
| Salus (re-run) | structured data + page layout + PDF | 65 | **61 / 4** | 268 | 5 | 0 | 12 | 233 |

**Backlog reasons:**
- **Almost Heaven:** 12 × R3. These are Quick Ship and standard listings of the same name, kept apart per D6.
- **Almost Heaven:** 1 × R5 and 1 × R2 (Grayson: labelled "Hybrid Saunas", but its page names no infrared system).
- **Golden Designs:** Bergen and Salus Aspire II are both **genuine R1 inconsistencies** on the manufacturers' own pages. Each states an "8.0 kw Stove" and a "240V / 30AMP (Stove)" circuit, and 8 kW at 240 V is 33.3 A. The new circuits structure found them.
- **R5** holds the rest: Hanko "2-3 Person" vs "2 person capacity", Forssa, three Salus Governor models, Avila and Barcelona.

**How leads were matched:**
- By the manufacturer's own SKU: all Almost Heaven, Sun Home and Heavenly Heat leads, 17 of 18 Redwood, 25 of 26 Dynamic and 12 of 23 Maxxus.
- By the lead's own manufacturer URL: the rest.
- Clearlight's 12 matched **by name** only (its leads carry retailer URLs and slugs). This is logged per record, and every published Clearlight value describes the manufacturer's page, whatever the lead said.

### Golden Designs: what the manuals changed

| | B1 (no manuals) | B2 (manuals under B1-D2) |
|---|---|---|
| Published / backlog | 26 / 2 | 25 / 3 |
| Manuals attached | 0 | 19 of 22 linked (3 answer 404) |
| `documented` values | 0 | 28 model numbers, 5 supply voltages, 2 amperages |
| Records with labelled circuits | — | 16 |
| R1 failures | 0 | 1 (Bergen, genuine) |

Why published fell by one:
- The Hanko and Forssa capacity conflicts, which one of my own fixes briefly hid, are restored (see §2 item 24).
- Bergen's page states an inconsistency and is held under R1.

## 2. Matcher errors found in the snippet audit, and their fixes

The audit read:
- every "changed by source" value (all brands)
- every electrical value, 322 lines across all 9 brands
- 12 seeded-random confirmed values per brand

Every error below is fixed and has a regression test (`tests/test_verified.py`, 88 tests). **No rule was loosened.** Items 7, 10, 16 and 18 changed an outcome *toward* publication; they're listed separately after the table.

| # | Brand | What it published | What the source said | Fix |
|---|---|---|---|---|
| 1 | Salus | documented capacity **2**, overriding the page | "2 Person Recommended" (the assembly crew) | capacity never comes from a manual; a count beside "recommended / to install" is never seating |
| 2 | Golden Designs | supply **120V/15A** on an 8 kW stove (false R1) | "120VAC 15AMP Outlet Needed For Lights/Radio" | a manual figure labelled for lights, radio or controls is not the supply |
| 3 | Dynamic | Lucca **20A** | "…20AMP Dedicated Circuit Required (DYN-6315-05)", another model's figure | a model in a parenthetical right after a figure labels it (the manual is written spec-then-label) |
| 4 | GD / Maxxus | one amperage | "TWO SEPARATE 120V/15AMP … CIRCUITS", "Dedicated Circuits Required" | the multi-circuit guard now also runs on the manual path, and plural "circuits required" counts |
| 5 | Heavenly Heat | "Dedicated required" | "Dedicated Circuit **Recommended**" | a dedicated circuit needs required/must wording and never "recommend" |
| 6 | Heavenly Heat | circuit purpose "Two Separate Circuits Required Infrared heaters…" | "Infrared heaters and lighting require…" | the purpose is only the load phrase |
| 7 | Heavenly Heat | Combination sauna **held by R2** | "Traditional stone heater requires a hardwired 240V/30A…" + "Infrared heaters…" | R2 now recognises a named "stone heater" |
| 8 | Golden Designs | circuit purpose "Please consult a certified electrician." | an unlabelled parenthetical | a circuit label must name a load |
| 9 | Golden Designs | GDI-8040-03 **15A** from the page | the manual says two separate 15 A circuits | an ambiguous higher tier blocks a simpler lower-tier figure |
| 10 | Maxxus / Dynamic | supply withheld as ambiguous | "120 V/20 AMP … (Not 220/240 V)" | negated voltages are not statements |
| 11 | Dynamic | Bergamo 15A | "15AMP … (2 Person Model)", a different configuration | a configuration parenthetical makes the figure unattributable |
| 12 | Salus | Flora **3.0 A** | "AR-3A", a part label in a drawing | an amperage is never glued to letters, and a bare single-digit "A" is refused |
| 13 | Salus | Elite **20A** | "REQUIRES 2 SEPARATE DEDICATED 120V/20 AMP OUTLETS" | "2 separate" joins the multi-circuit guard, and the window is widened to 40 characters |
| 14 | Salus | "Dedicated required" | "turn OFF the dedicated circuit breaker"; "15AMP Dedicated Circuit **or** 20AMP" | covered by item 5's required-wording rule |
| 15 | Salus | Nordic II **10.2 A** | "Step 10.2A – Install Lower Bench" | a bare "A" counts only beside electrical words |
| 16 | Salus | page values blocked by manual boilerplate | "Information for your electrician: 4.5kW and 6.0kW KIP Heaters…" | a linked document speaks only through pages naming the product's series (your D3 guard, applied literally) |
| 17 | Salus | Luxen 20A, while the same Maxxus wording was withheld | "20AMP Dedicated Circuits Required" | plural rule made consistent across page, linked-document and manual paths |
| 18 | Almost Heaven | heater kW withheld | every heater option names 8kW ("8kW KIP Heater w/ Dials", "8kW KIP Smart Heater + Fenix") | kW is option-independent only when every option names the same kW; voltage and amperage stay withheld |
| 19 | Sun Home | `red_light: true` | "…explore our red light saunas" (cross-sell); "Red light therapy **Not included**" | "not included" is an explicit no, and a cross-sell sentence is ignored |
| 20 | Almost Heaven | wood "Cedar" | "Choose Rustic Cedar…", with Lumber Type = Rustic Cedar / Onyx | option groups: lumber → wood, size → capacity and dimensions, sauna type → heat type |
| 21 | Clearlight | log counted a spectrum as "confirmed" | the record withheld it (heat type unknown) | log outcomes are reconciled against every published field |
| 22 | Almost Heaven | wood "Pine" | "thermally modified Nordic Pine" | species added, so the name isn't truncated |
| 23 | Salus | `red_light: true` | "(Red Light Therapy Feature Starting in 2024 Models)" | a model-year condition makes it ambiguous |
| 24 | **my own fix #1** | hid a real capacity conflict | "Assembled Dimensions (WDH): … 2 person capacity" was discarded for containing "assembl" | only the words right beside the count decide |
| 25 | Almost Heaven | R5 with the reason "2–3" (one value) | the buyer picks a size | a buyer-chosen size withholds capacity; R5 only fires on distinct stated capacities |
| 26 | Maxxus / Dynamic | Avila and Avila **Elite** merged as one model number | SKU "DYN-6103-01", title "(DYN-6103-01 Elite)" | the most specific model string wins, model match is exact, and R3 may use the model number as the configuration |
| 27 | Dynamic | documented "DYN-6103-01" for the Elite record | "Models: DYN-6103-01 / DYN-6103-01 Elite" | a manual's model number must match the page's, suffix included |

Two more, caught while designing the Clearlight adapter before any build:
- Its wood is a buyer choice ("Mahogany / Basswood"), and "Mahogany" was missing from the species list.
- "18.83 Amps" (the draw) was silently skipped beside "20 Amp outlet". Decimal amperages are now captured, so that pair is withheld.

**Four fixes changed an outcome toward publication. Please confirm each (B2-D10).** None accepts weaker evidence; each stops ignoring explicit source text.

| # | What changed | Evidence it now reads |
|---|---|---|
| 7 | R2 recognises a named heater | "Traditional stone heater" |
| 10 | a negated voltage is no longer a statement | "(Not 220/240 V)" |
| 16 | only a linked manual's pages that name the series count | pages naming "Majestic", "Nirvana", etc. |
| 18 | kW publishes when every heater option names the same kW | "8kW" in all four options |

## 3. Electrical coverage on published records

"INH sells" is Golden Designs alone until B2-D1 is decided.

| Field | INH does not sell (155) | INH sells (25) |
|---|---|---|
| supply voltage | 40 (26%) | 10 (40%) |
| stated amperage | 42 (27%) | 8 (32%) |
| breaker amps | 1 (1%) | 0 |
| connection type (named plug / Hardwired) | 17 (11%) | 0 |
| dedicated circuit required | 22 (14%) | 0 |
| GFCI | 0 | 0 |
| labelled circuits | 12 records | 16 records |
| heater kW (traditional / hybrid) | 22 of 47 | 16 of 18 |
| heat type known at all | **97 of 155** | 25 of 25 |
| any `documented` electrical value | 5 | 5 |

The gap is no longer the lead list's INH skew. It comes from how each manufacturer writes its pages:
- **Almost Heaven and Redwood never name a heat type** in their titles or product types, so 58 published records carry no heat type and therefore no heater fields (B2-D2).
- **Almost Heaven and Redwood** publish no electrical values, because heater choices are buyer options.
- **Clearlight** gets supply and plug from every page.

## 4. Blocked or failed sources

| Source | Status | Why |
|---|---|---|
| dynamicsaunas.com | not fetched | TLS: self-signed certificate. Never bypassed |
| maxxussaunas.com | nothing to fetch | a "Launching Soon" placeholder |
| almostheaven.com `/products.json` | 503 | read per product instead |
| 2 Almost Heaven product JSONs | 404 / 503 | `nordik-indoor-saunas`, `quick-ship-audra…` |
| 8 Golden Designs manuals on its Azure storage | 404 | linked from its own pages but gone |
| 4 Salus PDFs | 404 | as in B1 |
| Clearlight spec sheets | not found | "Download Spec Sheet" is on the page, but no PDF link is in the static HTML (B2-D8) |
| Sun Home (33) and Heavenly Heat (7) PDFs | fetched, readable, **0 attached** | they carry no model numbers, and link attachment is approved for Salus only (B2-D3) |
| Golden Designs' Azure storage robots.txt | answers 4xx | fetched under the B1-D2 policy, now in CLAUDE.md under source policy. 5xx and timeouts would still skip |

## 5. Conflicts (`data/verified/conflicts.json`)

- **86 lead mismatches:** Dynamic 18, Maxxus 17, Golden Designs 16, Almost Heaven 11, Redwood 9, Sun Home 9, Salus 5, Clearlight 1. Each carries the source value, the URL and the snippet.
- **334 within-source ambiguities** (withheld). By field: wood 79, model number 54 (mostly Almost Heaven's one-SKU-per-heater-package), stated amperage 52, supply voltage 45, heater kW 31, placement 19, red light 18, capacity 13.
- **0 tier disagreements.** The 27 that appeared mid-audit were error 27 (manual model numbers without their suffix) and are gone.

## 6. Decisions needed before the remaining 7 brands

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **B2-D1** 🔴 | Is goldendesigninc.com the *manufacturer* source for Maxxus and Dynamic? | (a) yes; (b) no, it's a distributor: with none approved, both brands publish nothing; (c) ask Golden Designs to confirm in writing first | **(a).** Its own catalogue sells both brands' SKUs under vendor "Golden Designs Inc (NA)"; their manuals live on Golden Designs' own storage; the About page says it produces "our own line"; Maxxus's site is a placeholder and Dynamic's fails TLS. No page says "our brands Maxxus and Dynamic", so it's your call. On (a): 49 records are computed and waiting, holding for R3/R5 as shown |
| **B2-D2** | Heat type when the title doesn't say it (Almost Heaven, Redwood, some Clearlight) | (a) title or product type only (58 published records have no heat type); (b) also accept the product description when it names exactly one heating system ("The Harvia 8kW electric heater…", "True Wave far infrared heaters") and nothing of the other | **(b).** It's the manufacturer's own statement, and R2 still guards hybrids. It is a new inference class, so it's yours |
| **B2-D3** | Extend link attachment (B1-D3/D8) beyond Salus | (a) Salus only; (b) any brand, same guards (linked from exactly one product page, only pages naming the series, never option-dependent) | **(b).** Sun Home has 33 readable manuals and spec sheets and Heavenly Heat 7, all attaching to nothing now |
| **B2-D4** | "Dedicated Circuits Required" (plural) on a single-model manual | (a) keep withheld: it may mean two circuits; (b) read it as one circuit | **(a)** until a source states the count |
| **B2-D5** | "30-amp" (hyphenated) is not read | (a) leave it: nothing false is published; (b) read it | **(b).** It's explicit text the matcher misses; Sun Home Luminar 5 and Salus heater pages use it |
| **B2-D6** | The two genuine R1 inconsistencies (GD Bergen, Salus Aspire II) | (a) backlog, as now; (b) also tell the manufacturers | **(a) in this round.** Outreach is a separate human decision |
| **B2-D7** | Almost Heaven Quick Ship vs standard (6 pairs held by R3) | stays per D6 / revisit | **Stays.** One pair (Auburn) is known to differ by heater (8 vs 6 kW) |
| **B2-D8** | Clearlight spec sheets | (a) skip; (b) read its "User Manuals & Spec Sheets" owner page for PDF links | **(b)** in the next batch, if robots.txt allows (`Crawl-delay: 10`) |
| **B2-D9** | Next batch (the INH-sold remainder) | Scandia, Dundalk LeisureCraft, SaunaLife, Medical Saunas, Mande Spa, Kohler, Ripavi | **Proceed.** Dundalk's site answers 404 for robots.txt and is not a linked asset host, so under the approved policy it stays skipped and will likely publish nothing |
| **B2-D10** | The four fixes in §2 that changed an outcome toward publication | confirm / revert any | **Confirm.** Each reads explicit source text that had been ignored |

## 7. Gates

| Gate | Result |
|---|---|
| jsonschema validation (schema 0.3.0, with `circuits` + `circuits_required`) | ✅ in the build lint, every record |
| inhousewellness.com rejected as a source; non-allow-listed retailer (ampsrus.com) rejected | ✅ tests |
| Shared Shopify CDN files must carry the brand's own shop path | ✅ test |
| Rebuild from cache byte-identical | ✅ two runs, plus a test |
| Full suite | ✅ **637 passed**, all 595 prior tests included. No prior assertion changed state |
| preflight `--self-test / --static / --imports` | ✅ clean |
| Missing-value lint | ✅ 0 (two new optional-field lines carry `# missing-ok` with reasons) |
| `check_facts_cache` / `check_facts_drift` | ✅ |
| API spend | **$0** |
