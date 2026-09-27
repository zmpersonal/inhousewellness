# INH Verified — Round 1, Part B1 report: pilot on two brands

**Status: 🟡 REVIEW. Stopped after the pilot as instructed. The other 14 brands are not run.**
Branch `verified/r1-data-foundation`. Nothing merged, deployed or put on any website. No theme,
no Shopify write, nothing sent to Infinite Sauna. Anthropic API spend: **$0**. Blotato: 0 credits.

Pilot brands: **Golden Designs** (INH sells it) and **Salus**, the brand INH does not sell with the
most records in the lead list (65).

## How it works

1. `scripts/verified_fetch.py` (online) reads robots.txt first on every host, makes at most one
   request every 2 s per host, and identifies itself as
   `INH-Verified-bot/0.1 (+https://inhousewellness.com; …)`. It fetches only the brand's own
   domain from `data/verified/sources.json`. It pulls each manufacturer's product catalogue
   (`/products.json`), so a lead is matched to a manufacturer product **by the SKU the
   manufacturer publishes**, not by the lead's URL. It also pulls the Salus product pages
   (their specs are in labelled panels), the manufacturers' manual and partner pages, and every
   PDF those pages link from the manufacturer's own hosts. The bytes are cached in
   `out/verified/cache/` (gitignored). **The hash manifest is committed:**
   `data/verified/cache-manifest.json`, 163 URLs.
2. `scripts/verified_build.py` (offline) reads only the cache. For each field it asks what the
   source states:
   - exactly one value → **published** with its snippet, locator, fetch time and the fetched
     bytes' sha256. It is labelled *confirmed* (equal to the lead), *changed* (different; the
     source value wins and the mismatch goes into `conflicts.json`) or *source-only* (no lead).
   - two or more values → **withheld**, and the ambiguity is logged.
   - nothing → `not_verified`.

   R1–R5 then run on the **final** values.
3. **Lint in the build:** the jsonschema check on every record, an origin-host allow-list on
   every `source_url`, the banned phrase, no bare values, and no mention of the lead source (D1).
   The build halts on any failure.

Two rebuilds from the cache produced byte-identical `saunas.json` and `conflicts.json`
(sha256 `182ff854…` and `b667a09f…`), and a test enforces this.

## 1. Per-brand results

| | Golden Designs | Salus |
|---|---|---|
| Leads in | 28 | 65 |
| Leads with no manufacturer page | 0 | 0 |
| **Records published** | **26** | **60** |
| Records in backlog | 2 (R5) | 5 (R5) |
| Lead values in | 303 | 286 |
| **Confirmed** | **197** | **266** |
| **Changed by the source** | **14** | **5** |
| **Not found** in the source | 4 | 0 |
| Ambiguous in the source (withheld) | 71 | 12 |
| Not applicable once the source fixed the heat type | 17 | 3 |
| Source-only values (manufacturer states it, the lead had none) | 16 | 224 |
| `documented` values (from a manual) | **0** | **0** |

Coverage of **published** records, meaning values carrying an origin source:

| Field | Golden Designs (26) | Salus (60) |
|---|---|---|
| model number | 26 | 60 |
| heat type · capacity | 26 · 26 | 60 · 60 |
| placement | 18 | 55 |
| wood | 14 | 28 |
| supply voltage | 9 | 18 |
| stated amperage | 9 | 17 |
| breaker amps | 0 | 1 ("install … 20 amp breaker") |
| connection type | 0 | 0 |
| heater kW (traditional + hybrid) | 17 of 19 | 19 of 43 |
| assembled dimensions | 13 | 49 |

**How to read these numbers:**

- **Salus's 266 confirmations mostly come from its product titles.** The leads' capacity, heat
  type, placement and model number were copied from Salus's own titles and SKUs, so confirming
  them is real but carries little information. The informative results are the 224 values Salus
  states that the leads did not have (dimensions, woods, 21 heater ratings, supply) and the 12
  it withholds.
- **All 15 Golden Designs R1 failures from Part A are gone.** The manufacturer's pages state
  240 V, not "120V/240V". For example, Soria's page says `240V / 30AMP` where the lead had
  `120V/240V, 20A`, and Copenhagen's page states 240 V. That is the lead-versus-source design
  doing its job.
- **Golden Designs' 71 ambiguities are mostly one honest pattern.** Its pages give two circuits
  ("240V / 40AMP (Stove) and 120V / 15AMP (Lights and Music)"), so voltage and amperage are
  withheld (B1-D4).
- **Zero `documented` values.** No manufacturer manual could be attached (section 5 and
  B1-D2, B1-D3).

### Matcher errors found by reading the evidence, fixed before this report

None of these was fixed by loosening a rule. Each one had been publishing something the source
did not state:

| What it did | What the source said | Fix |
|---|---|---|
| Copenhagen, Sundsvall, Kuusamo: placement **indoor** | "Indoor or covered exterior use" | Conditional exterior use is ambiguous, so the field is withheld |
| GDI-8040-03: **15 A** | "Dual x 120v/15 AMP" | Two circuits never publish as one amperage |
| Arosa, St. Moritz: wood **"Cedar"** | "Pacific Premium Cedar" | The qualified species is kept whole |
| Salus Stellar With Relax Room: **Hardwired** | a table of heater *options* ("9kw and 10.5kw requires … Hard Wired. The wood burning stoves require no electrical hookup") | An electrical statement from a heater-options passage is configuration-dependent, so it is withheld |
| "GFCI is not required" read as **Required** | negation inside the match | The negation guard now checks inside and after the match |
| Golden Designs build attached **3 Salus PDFs** | a host list that included the shared Shopify CDN | Hosts are per brand, and Shopify files must also carry the brand's own shop path |

Each has a regression test.

## 2. Spot check: 10 confirmed values (seeded random sample, `random.Random(20260927)`)

| # | Record | Field | Value | Source | Snippet |
|---|---|---|---|---|---|
| 1 | Golden Designs Gargellen Hybrid Outdoor Sauna, 5 Person | capacity | 5 | https://goldendesigninc.com/products/golden-designs-gargellen-5-person-hybrid-full-spectrum-ir-or-traditional-stove-outdoor-sauna-canadian-hemlock | “Golden Designs "Gargellen" 5 Person Hybrid (PureTech™ Full Spectrum IR or Traditional Stove) Ou” |
| 2 | Salus Flora Traditional Outdoor Luxury Sauna, 3 Person | capacity | 3 | https://www.salussaunas.com/products/flora | “Flora Traditional Outdoor Luxury Sauna - 3 Person” |
| 3 | Golden Designs Nora Outdoor-Indoor PureTech Hybrid Full Spectrum Sauna, 2 Person | capacity | 2 | https://goldendesigninc.com/products/golden-designs-nora-2-person-outdoor-indoor-puretech™-hybrid-full-spectrum-sauna-gdi-8222-01-canadian-red-cedar-interior | “Golden Designs "Nora" 2 Person Outdoor-Indoor PureTech™ Hybrid Full Spectrum Sauna (GDI-82” |
| 4 | Golden Designs Toledo Hybrid Sauna Full Spectrum and Harvia Traditional Stove, 6 Person | wood_species | Canadian Hemlock | https://goldendesigninc.com/products/golden-designs-2025-toledo-6-per-hybrid-sauna-indoor-full-spectrum-and-harvia-traditional-stove | “he environment in mind, our saunas are made with reforested Canadian Hemlock planks that surpass industry standards, thu” |
| 5 | Golden Designs Far IR Sauna, 6 Person | heat_type | infrared | https://goldendesigninc.com/products/gdi-6996-02-near-zero-emf-far-infrared-sauna | “Golden Designs 6 Person Near Zero EMF Far IR Sauna (GDI-6996-02 Elite)” |
| 6 | Golden Designs Far IR Sauna, 6 Person | placement | indoor | https://goldendesigninc.com/products/gdi-6996-02-near-zero-emf-far-infrared-sauna | “a certified electrician.) Clasp together assembly Roof vent Indoor use only Sauna weight: 750 lbs. Shipping weight: 965 ” |
| 7 | Salus Florence Relax Traditional Outdoor Luxury Sauna, 6 Person | capacity | 6 | https://www.salussaunas.com/products/florence_relax | “Florence Relax Traditional Outdoor Luxury Sauna - 6 Person” |
| 8 | Salus Ally King Traditional Indoor Sauna, 3 Person | heat_type | traditional | https://www.salussaunas.com/products/ally-king-3-person-traditional-indoor-sauna | “Ally King Traditional Indoor Sauna - 3 Person” |
| 9 | Golden Designs Reserve Edition Full Spectrum with Himalayan Salt Bar, 3 Person | placement | indoor | https://goldendesigninc.com/products/new-2023-collection-reserve-edition-gdi-8230-01-full-spectrum-with-himalayan-salt-bar | “Dedicated Outlet) (Please consult a certified electrician.) Indoor Use Only Sauna weight: 505 lbs. Shipping weight: 645 ” |
| 10 | Salus Luxen Far Infrared Indoor Sauna, 4 Person | heat_type | infrared | https://www.salussaunas.com/products/luxen-4-person-near-zero-emf-infrared-sauna | “Luxen Far Infrared Indoor Sauna - 4 Person” |

The random draw landed mostly on title-derived fields, because those make up most confirmations.
For a harder test, look at rows 4, 6 and 9, whose snippets come from body copy.

## 3. Every conflict found (`data/verified/conflicts.json`: 19 lead mismatches, 162 within-source ambiguities, 0 tier disagreements)

#### Lead mismatches — the source value is what is published

| Brand | Product (manufacturer handle) | Field | Lead | Published (source) | Source snippet |
|---|---|---|---|---|---|
| Golden Designs | `2025-reserve-edition-gdi-8010-03-full-spectrum-with-himalaya` | capacity | 1–2 | **1** | 2025 Golden Designs "Reserve Edition" 1 Person Full Spectrum with Himalayan Salt Bar (GDI-8010-03) |
| Golden Designs | `golden-designs-nora-2-person-outdoor-indoor-puretech™-hybrid` | emf_claim | Low | **Near Zero** | s Full Spectrum IR: Total 6 IR Emitters. 2 Carbon PureTech™ Near Zero EMF Heating Panels and 4 Near Infrared Heating Elements All Wea |
| Golden Designs | `golden-designs-2025-soria-3-per-hybrid-sauna-indoor-full-spe` | heat_type | infrared | **hybrid** | 2026 Golden Designs "Soria" 3 Person Hybrid Sauna (Indoor) Full Spectrum and Harvia Traditional Stove ( |
| Golden Designs | `golden-designs-2025-toledo-6-per-hybrid-sauna-indoor-full-sp` | heat_type | infrared | **hybrid** | 2025 Golden Designs "Toledo" 6 Person Hybrid Sauna (Indoor) Full Spectrum and Harvia Traditional Stove ( |
| Golden Designs | `golden-designs-5-person-traditional-flat-roof-outdoor-sauna-` | heat_type | infrared | **traditional** | ***New 2026 Model*** Golden Designs "Vorarlberg" 5 Person Traditional Flat Roof Outdoor Sauna (GDI-8005-01) |
| Golden Designs | `golden-designs-kaskinen-6-person-hybrid-puretech™-full-spect` | heat_type | infrared | **hybrid** | Golden Designs "Kaskinen" 6 Person Barn Hybrid (PureTech™ Full Spectrum IR or Traditional Stove) Outdoor S |
| Golden Designs | `golden-designs-visby-3-person-outdoor-indoor-puretech™-hybri` | heat_type | infrared | **hybrid** | Golden Designs "Visby" 3 Person Outdoor-Indoor PureTech™ Hybrid Full Spectrum Sauna (GDI-8223-01) |
| Golden Designs | `golden-designs-kuusamo-edition-6-person-indoor-traditional-s` | max_temp_f | 195.0 | **190.0** | al Stove: 170-185 is the ideal temperature range, sauna can heat up to 190F Electrical service: 240V / 40AMP (Stove) and 120V / 15AMP ( |
| Golden Designs | `2025-reserve-edition-gdi-8040-03-full-spectrum-with-himalaya` | placement | outdoor | **indoor** | Dedicated Outlet) (Please consult a certified electrician.) Indoor Use Only Sauna weight: 475 lbs. Shipping weight: 560 lbs. S |
| Golden Designs | `new-2023-collection-reserve-edition-gdi-8260-01-full-spectru` | placement | outdoor | **indoor** | Dedicated Outlet) (Please consult a certified electrician.) Indoor Use Only Sauna weight: 640 lbs. Shipping weight: 775 lbs. S |
| Golden Designs | `gdi-6996-02-near-zero-emf-far-infrared-sauna` | spectrum | Full Spectrum | **Far Infrared** | Golden Designs 6 Person Near Zero EMF Far IR Sauna (GDI-6996-02 Elite) |
| Golden Designs | `golden-designs-nora-2-person-outdoor-indoor-puretech™-hybrid` | spectrum | Infrared | **Full Spectrum** | den Designs "Nora" 2 Person Outdoor-Indoor PureTech™ Hybrid Full Spectrum Sauna (GDI-8222-01) |
| Golden Designs | `golden-designs-2025-soria-3-per-hybrid-sauna-indoor-full-spe` | stated_amperage | 20.0 | **30.0** | range, sauna can heat up to 140F Electrical service: 240V / 30AMP (Stove & Full Spectrum) (Please consult a certified electri |
| Golden Designs | `golden-designs-2025-soria-3-per-hybrid-sauna-indoor-full-spe` | supply_voltage | 120V/240V | **240V** | rature range, sauna can heat up to 140F Electrical service: 240V / 30AMP (Stove & Full Spectrum) (Please consult a certified |
| Salus | `grand-renew` | heat_type | traditional | **hybrid** | Grand Renew Hybrid Outdoor Sauna - 6 Person |
| Salus | `harmony-hybrid` | heat_type | traditional | **hybrid** | Harmony Hybrid Indoor Sauna - 6 Person |
| Salus | `renew` | heat_type | traditional | **hybrid** | Renew Hybrid Outdoor Sauna - 2 Person |
| Salus | `renew-king` | heat_type | traditional | **hybrid** | Renew King Hybrid Outdoor Sauna - 3 Person |
| Salus | `serenity-hybrid` | heat_type | traditional | **hybrid** | Serenity Hybrid Indoor Sauna - 3 Person |

#### Tier disagreements

None. No manufacturer document was attached in the pilot, so there was only ever one origin tier.

#### Within-source ambiguities (162): withheld, nothing published

| Brand | Field | Count | Typical reason (first example) |
|---|---|---|---|
| Salus | wood_species | 33 | states Canadian Red Cedar, Cedar, Red Cedar: “2 person capacity 100% Natural Canadian red cedar wood Interior ceiling galaxy star color therapy lighting sy” |
| Golden Designs | stated_amperage | 19 | states 15.0, multiple circuits: “, sauna can heat up to 140F Electrical service: Dual x 120v/15 AMP Non GFCI (Recommend Dedicated Outlet) (Plea” |
| Golden Designs | supply_voltage | 19 | states 120V, multiple circuits: “range, sauna can heat up to 140F Electrical service: Dual x 120v/15 AMP Non GFCI (Recommend Dedicated Outlet) ” |
| Salus | stated_amperage | 15 | states 30.0, 15.0: “range, sauna can heat up to 190F Electrical service: 240V / 30AMP (Stove) and 120V / 15AMP (Control for Lights” |
| Salus | supply_voltage | 15 | states 240V, 120V: “rature range, sauna can heat up to 190F Electrical service: 240V / 30AMP (Stove) and 120V / 15AMP (Control for” |
| Golden Designs | wood_species | 14 | states Canadian Red Cedar, Pacific Premium Clear Cedar, Cedar: “x 78" 3 person capacity 8.0 kw Stove with built in controls Canadian Red Cedar Interior Wood and Pacific Premi” |
| Golden Designs | placement | 10 | states indoor, outdoor (conditional): “Lights and Music) (Please consult a certified electrician.) Indoor or covered exterior use Assembled Weight: 6” |
| Golden Designs | breaker_amps | 5 | states 15.0, multiple circuits: “, sauna can heat up to 140F Electrical service: Dual x 120v/15 AMP Non GFCI (Recommend Dedicated Outlet) (Plea” |
| Golden Designs | max_temp_f | 5 | states 190.0, 140.0: “al Stove: 170-185 is the ideal temperature range, sauna can heat up to 190F Full Spectrum IR: 118-132 is the i” |
| Salus | breaker_amps | 5 | states 50.0, depends on heater option, multiple circuits: “s Heater size: 15kw electrical heater require 240 V and 2 x 50 Amp Breakers- Hard Wired Stove: The wood burnin” |
| Salus | capacity | 5 | states 2, 1–2: “Governor Mini Front Glass Traditional Outdoor Sauna - 2 Person” |
| Salus | placement | 5 | states indoor_outdoor, outdoor: “Aspire II Traditional Indoor/Outdoor Sauna - 6 Person” |
| Salus | connection_type | 3 | states Hardwired, depends on heater option: “kw electrical heater require 240 V and 2 x 50 Amp Breakers- Hard Wired Stove: The wood burning stoves require ” |
| Salus | heater_kw | 3 | states 15.0, depends on heater option: “9" H Shipping Weight: 2205 lbs. Max Capacity : 6 persons Heater size: 15kw electrical heater require 240 V and” |
| Golden Designs | capacity | 2 | states 3–4, 3: “Golden Designs "Forssa" 3-4 Person Traditional Sauna (GDI-7203-01)” |
| Golden Designs | heater_kw | 2 | states 6.0, depends on heater option: “re range, sauna can heat up to 190F Electrical service: 240V / 30AMP (6KW Stove) OR 240V / 40AMP (8KW Stove) a” |
| Salus | spectrum | 2 | states Full Spectrum, Far Infrared: “Ascend Full Spectrum Infrared Indoor Sauna - 2 Person” |

The full list, with every value, locator and snippet, is in `data/verified/conflicts.json`.


## 4. Proposed distributor allow-list (`data/verified/distributors-proposed.json`, not used)

**Proposed list: empty.** I found no distributor that its manufacturer names as authorized on a
page it publishes.

| Candidate | Brands | Status | Evidence |
|---|---|---|---|
| Golden Designs Direct (goldendesigninc.com) | Golden Designs, Maxxus, Dynamic | **Not a distributor**: it is the manufacturer's own store, already a manufacturer source | catalogue `vendor` field |
| Ampsrus (ampsrus.com) | Golden Designs, Maxxus, Dynamic | **Unconfirmed** | Named on no Golden Designs page fetched. Golden Designs' store locator loads its dealer list in the browser from Storemapper (account 15531); the static page names no dealer (B1-D1) |
| Salus dealers | Salus | **None found** | Salus sells direct. `/pages/partnership-program` recruits partners and names none |

## 5. Fetch failures and blocked sources

**Fetched:** 163 URLs, 159 OK. Four HTTP 404s, all Salus-linked PDFs that no longer exist:

- `404` https://cdn.shopify.com/s/files/1/0720/7695/1854/files/Cold_Plunge_Setup_Guide.pdf
- `404` https://cdn.shopify.com/s/files/1/0720/7695/1854/files/Harvia_KIP_Manuals.pdf
- `404` https://cdn.shopify.com/s/files/1/0720/7695/1854/files/Ice_Tub_Manual.pdf
- `404` https://cdn.shopify.com/s/files/1/0720/7695/1854/files/Water_Maintenance_Quick_Guide.pdf

**Not fetched, by rule:**

| Source | Why | Effect |
|---|---|---|
| Golden Designs manuals on `goldendesignstorage.blob.core.windows.net` (236 links from its own product descriptions) | robots.txt returns **HTTP 400**. The project policy is to skip any host whose robots.txt can't be read (CLAUDE.md, the Dundalk note) | **No Golden Designs manual** (B1-D2) |
| Golden Designs links on `www.dropbox.com` (60) | not a manufacturer host | not evidence |
| The manual copies in our own Google Drive (owner `support@inhousewellness.com`) | Google's robots.txt disallows `/uc` and all of `drive.usercontent.google.com`. The Drive connector would relay each 2–8 MB PDF through the conversation, which is not affordable or verifiable | not used (B1-D7) |

**Fetched but not attachable:**
- **Salus: 83 PDFs.** 54 do not name Salus in their text layer. That includes Harvia control
  and chiller manuals (correctly rejected) and genuine Salus owner's manuals whose only brand
  mark is a logo image.
- The 29 that do name Salus, including 5 spec sheets dated September 2026, **identify products
  by series name, never by model number**, so under the model-number rule none attaches (B1-D3).

**Noted, not acted on:** Golden Designs' robots.txt contains instructions addressed to AI agents
(install a shopping skill, use its checkout endpoint). They were treated as page content and
ignored; nothing here buys or checks out.

## 6. Decisions needed before B2

| # | Decision | Options | Recommendation |
|---|---|---|---|
| **B1-D1** | Distributor allow-list | (a) approve it **empty**; (b) let me read Golden Designs' Storemapper dealer list (a third-party widget's data endpoint, account 15531); (c) ask the manufacturers directly | **(a) for B2.** Distributors add no coverage while every value found so far is on the manufacturer's own page. (b) reverse-engineers someone else's widget to get a list whose "authorized" status still isn't stated |
| **B1-D2** 🔴 | Golden Designs' own PDF host serves no robots.txt (HTTP 400) | (a) keep the strict skip: no Golden Designs manuals; (b) for a host the manufacturer itself links from robots-allowed pages, treat a 4xx robots.txt as RFC 9309 does (access allowed), still at 1 request per 2 s; (c) you download the manuals and commit their hashes | **(b), scoped to manufacturer asset hosts only.** It is what the RFC says, the only route to `documented` values for Golden Designs, and CLAUDE.md says this call is yours. Dundalk's 404 case would fall under the same rule |
| **B1-D3** | Documents that name a series, not a model (all Salus spec sheets and manuals) | (a) keep the model-number rule: Salus gets no `documented` values; (b) attach a document only when **the manufacturer's own product page links it**, no other product page links it, and its title names that product; then accept its figures for that record | **(b).** The manufacturer's link is the association, not our guess. The "exactly one product page" condition keeps a multi-model manual from being read as one model's |
| **B1-D4** | Labelled dual circuits ("240V / 40AMP (Stove) and 120V / 15AMP (Lights and Music)") | (a) keep withheld (71 Golden Designs ambiguities, most of them this); (b) when each figure carries an explicit label, map Stove/Heater to `heater_voltage` plus a heater amperage, and Lights/Controls to `supply_voltage` | **(b), labelled figures only.** The schema's `heater_voltage` slot exists for exactly this. An unlabelled pair stays withheld |
| **B1-D5** | "Electrical service: 240V / 30AMP" | (a) `stated_amperage` only, as now; (b) treat it as a breaker size | **(a).** Per D2, it doesn't say breaker. Only "breaker" earns `breaker_amps` (1 Salus record) |
| **B1-D6** | Products sold with a choice of heater (many Salus traditional models) | (a) one record, with option-dependent electrical fields withheld (as now); (b) one record per heater package | **(a) for Round 1, (b) as a Round 2 schema question.** The rule already says one record per configuration, but the source lists options, not packages |
| **B1-D7** | The manual copies in our own Google Drive | (a) don't use them; (b) use them via a download path outside the conversation | **(a).** They are also INH-hosted copies. The manufacturer-hosted originals (B1-D2) are the stronger source under the clause |
| **B1-D8** | Brand check on PDFs (text must name the brand) | (a) keep it: genuine manuals with a logo-only brand are rejected; (b) accept a PDF the manufacturer links from its own product page even without the name in its text | **(b), combined with B1-D3.** The manufacturer's own link carries the authorship, and the text check stays for PDFs found any other way |
| **B1-D9** | Titles with no model name (e.g. "Golden Designs Far IR Sauna, 6 Person") | (a) leave them; (b) a reviewed override table in B2 | **(b).** More regex would be guessing |

## 7. Gates

| Gate | Result |
|---|---|
| Schema validation (`jsonschema` 4.26) on every record | ✅ inside the build lint |
| inhousewellness.com rejected as a `source_url` | ✅ test |
| Retailer domain not on the allow-list rejected (ampsrus.com) | ✅ new test |
| Rebuild from cache byte-identical | ✅ two runs, plus a test |
| Full suite | ✅ **595 passed** (549 before this round, now including the 10 manual-spec tests with `pypdf` installed, plus 46 new). No prior assertion changed state |
| `preflight --self-test / --static / --imports` | ✅ clean (`jsonschema` declared in `requirements.txt`) |
| Missing-value lint | ✅ 0 findings. It found 7 in the new code; each got the lint's own `# missing-ok` marker with a reason, and the lint is unchanged |
| `check_facts_cache` / `check_facts_drift` | ✅ pass / no drift |
| API spend | **$0** |
