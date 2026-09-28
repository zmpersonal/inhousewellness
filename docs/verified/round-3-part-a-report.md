# INH Verified Round 3 — Part A report: gap diagnosis (then stop)

Branch `verified/r3-parity` (from `verified/r2-pages`). Nothing was written to Shopify or to
any theme. API spend $0: no model calls, and the fetches use no paid API.

Appendix with counts, fix causes and 5 quoted snippets per brand per class:
**`docs/verified/round-3-gap-samples.md`**. The classification lives in
`data/verified/gap-diagnosis.json`, and the build attaches it to each record as `gap_diagnosis`
(104 records). It's internal: it's kept out of every Shopify payload, and the "Not stated on the
manufacturer's page" wording is not rendered.

## 0. Governance (approved) — done

- **MAIN is resolved at run time.** `verify_theme_asset_path.resolve_main()` reads the one theme
  with role MAIN from the Admin API. `main_refusal()` refuses to write to that id unless the
  go-live step names it as the live override.
- **Wired into all three theme writers:** `deploy_theme_files.py`, `rollback_calculator.py` and
  `verified_deploy.py`. Each logs the resolved id (today `167150092355`).
- **CLAUDE.md:** the hard-coded MAIN row is replaced by the rule, with the current id marked
  *informational only*.
- **Tests:** 3 new; every writer is asserted to call the resolver.

## 1. How the diagnosis was done

**Scope.** Every published record that misses the threshold:
- the five brands: Almost Heaven 43, Clearlight 12, Sun Home 15, Redwood 17, Heavenly Heat 8;
- plus Dundalk 2, SaunaLife 6 and Scandia 1, to see which fixes carry over;
- 104 records in total.

**What was read, per record:**
- the product data (Shopify JSON);
- the static page HTML;
- a headless render of the page;
- the page's metadata (the manufacturer's own meta and Open Graph description, JSON-LD);
- every PDF the page links.

**Headless rendering (approved).** It runs under the same policy as plain fetches:
- robots.txt first, including for every same-host subresource;
- every same-host request is spaced at least 2 seconds apart, across processes, with a shared
  gap, so parallel brand fetchers never double the rate on a shared host such as
  `cdn.shopify.com`;
- honest user agent; images, fonts, media and stylesheets are never requested;
- the rendered HTML is cached with its sha256, fetch time and `method: headless`.

**Redwood.** Its pages need about 170 same-host requests, so every render timed out, and per
your decision the plain fetch stands.

**Classes.** A candidate statement must be labelled or a plain sentence on the page, or a
labelled × dimension in a linked document. Anything weaker (link text, a heater brand, drawing
annotations) is NOT_VERIFIED with the snippet quoted as an *unconfirmed candidate*.

**NOT_STATED is stricter still.** It requires that:
- every source was fetched and read;
- no candidate was found, even a weak one;
- the field isn't even named. A "Sizing & Dimensions" heading with no figures in its text is
  NOT_VERIFIED, because the figures may be in an image we don't read.

## 2. Counts (missing fields of below-threshold records)

| Brand | Field | STATED_MISSED | JS_ONLY | OPTION_DEPENDENT | NOT_STATED | NOT_VERIFIED |
|---|---|---|---|---|---|---|
| Almost Heaven | heat type | 27 | 0 | 6 | 0 | 0 |
| | capacity | 2 | 0 | 8 | 0 | 0 |
| | exterior dimensions | 34 | 0 | 8 | 0 | 1 |
| | electrical | 5 | 0 | 35 | 0 | 0 |
| Clearlight | capacity | 8 | 0 | 0 | 1 | 3 |
| | exterior dimensions | 4 | 0 | 0 | 0 | 0 |
| | electrical | 1 | 0 | 0 | 0 | 0 |
| Heavenly Heat | exterior dimensions | 2 | 0 | 0 | 0 | 6 |
| | electrical | 1 | 0 | 0 | 0 | 0 |
| Redwood | heat type | 5 | 0 | 0 | 0 | 4 |
| | exterior dimensions | 16 | 0 | 0 | 0 | 1 |
| | electrical | 0 | 0 | 17 | 0 | 0 |
| Sun Home | exterior dimensions | 15 | 0 | 0 | 0 | 0 |
| Dundalk | heat type / capacity / dims / electrical | 0 / 0 / 0 / 0 | 0 / 2 / 2 / 0 | 0 / 0 / 0 / 2 | 0 | 2 / 0 / 0 / 0 |
| SaunaLife | heat / capacity / dims / electrical | 0 / 6 / 3 / 0 | 0 | 0 | 0 / 0 / 0 / 1 | 6 / 0 / 2 / 5 |
| Scandia | heat / capacity / dims / electrical | 0 | 0 | 0 / 1 / 1 / 1 | 0 | 1 / 0 / 0 / 0 |

- **JS_ONLY appears only on Leisurecraft (Dundalk).** Clearlight's specs are all in its static
  HTML; the extractor just missed them.
- **NOT_STATED is 2 fields in total:**
  - Clearlight's Curve sauna dome, where no capacity is stated anywhere;
  - SaunaLife G11's electrical supply.

## 3. Why values were missed (the fix each needs)

| Cause | Where | Fix |
|---|---|---|
| Fractional inches: "51 3/4″", "86-5/8″" | Almost Heaven 22, Redwood 4 | dimension parser |
| Unicode fractions: "⅞", "80⁵⁄₁₆″" | Almost Heaven 12, Redwood 11, Clearlight 2 | dimension parser |
| Per-axis labels ("Exterior Depth 84.75″ … Width …"), L × W × H order, letters after the inch mark | Sun Home, Heavenly Heat, Redwood, Clearlight, Dundalk | dimension parser |
| "ASSEMBLED EXTERIOR · W × D × H" in per-model spec-sheet PDFs | Sun Home 8 | linked spec sheets bound by model name |
| Multi-model spec tables ("SPEC SOLSTICE 1 SOLSTICE 2 …") | Sun Home 5 | column-to-model assignment |
| "fits / accommodates / holds up to N adults", "Up to N Persons" | Clearlight 6, SaunaLife 6 | capacity extractor |
| Capacity only in the manufacturer's meta description | Clearlight 2 | **decision D-2** |
| "Hardware : 120V, 20 amp dedicated outlet", "120 volts … 8.3 Amps" | Almost Heaven 5, Clearlight 1, Heavenly Heat 1 | electrical extractor |
| "a traditional sauna experience" in the product description | Redwood 5, Almost Heaven 3 | heat type from description |
| Generic "löyly … defines a traditional sauna" copy | Almost Heaven 24 | **decision D-3** |
| Option-dependence detected but never recorded with evidence | Almost Heaven 35 electrical, Redwood 17 ("6kW … with upgrades available: 8kW …"), Dundalk 2 (configurator) | record `electrical.option_dependence` |
| Leisurecraft specs render only with JavaScript | Dundalk 2 | headless fallback (approved) |

## 4. Projection

"Handled" means STATED_MISSED and JS_ONLY values extracted, and electrical option-dependence
recorded with evidence (the Round 2 amendment). Option-dependent capacity, dimensions or heat
type still block a page.

| Brand | Below threshold | Upper bound | Conservative |
|---|---|---|---|
| Almost Heaven | 43 | 28 | 7 |
| Clearlight | 12 | 8 | 7 |
| Heavenly Heat | 8 | 2 | 2 |
| Redwood | 17 | 12 | 12 |
| Sun Home | 15 | 15 | 15 |
| **Five brands** | **95** | **65** | **43** |
| Dundalk, SaunaLife, Scandia | 9 | 0 | 0 |

**What the conservative count leaves out (22 records):**
- 20 Almost Heaven records whose heat type rests only on the generic löyly copy (D-3);
- two corner saunas whose exterior is stated as wall lengths (D-1): Almost Heaven Sutton and
  Clearlight Sanctuary C.

Multi-model tables stay in, because their columns are attributable.

**Dundalk, SaunaLife and Scandia gain fields but no pages:**
- **Dundalk:** the headless fallback and option evidence fix capacity, dimensions and electrical,
  but heat type is only a weak candidate.
- **SaunaLife:** "Up to N Persons" fixes capacity for all 6. Its barrels state L × diameter
  (D-1); electrical and heat type are unverified.
- **Scandia:** the pre-cut kit is sold in many sizes, so capacity, dimensions and heater sizing
  are option-dependent.

## 5. Errors the audit found

Each has a regression test (33 in `tests/test_verified_gaps.py`).

**In my own diagnosis, found by reading every snippet:**
- "can reach **up to 90**.5 degrees" read as a capacity.
- A PEMF mat's "Treatment Area (112 x 37 x 7.2 cm)", "Exterior **Bench** Dimensions", "Canopy
  **Porch** Size" and "**Shipping** Dimensions" read as exterior.
- Assembly-PDF noise: "DET **10a**" and "t r i m 1 5 **A**" read as amps.
- "Each model's exterior dimensions are on its Spec Sheet. **03**" read as a size.
- "Choose a free heater upgrade or shipping on us" (a promotion) read as a heater option.
- A multi-model comparison sheet made two infrared saunas look heater-option-dependent.
- A drawing's "OVERALL DIMENSIONS 13’ 3-1/4” …" read as W × D × H.
- Size-switcher link text and a figure-less "Sizing & Dimensions" heading nearly produced false
  NOT_STATEDs.

**Found in Round 1. All of them withheld values; none published a wrong one:**
- **"Lumber Type (Rustic Red Cedar, Onyx)" was treated as a heat-type option**, because Round 1's
  option matcher accepts any option name containing "Type". That withheld Almost Heaven heat
  types.
- **Escaped PDF links:** links pulled from script-escaped HTML kept `\"`, so real manuals were
  never read (Heavenly Heat, and a set of Almost Heaven manuals). Fixed in the diagnosis fetcher;
  the build's own extractor still has the bug.
- **Our own truncation was read as the source's defect.** The Round 1 cache held 1,039,467 of
  11,490,346 bytes of Heavenly Heat's Eco manual, and the parser's complaint made it look like a
  broken file. It's re-fetched in full. The fetcher now compares the bytes received with the
  declared Content-Length and records a short read as `TRUNCATED_TRANSFER`. Every other cached PDF
  was checked and has its end marker.
- Fractional and Unicode-fraction inches are not parsed. That's the single largest cause of
  missed dimensions.

**Effect on the dataset:** no published value changed. The Eco record's `provenance.origin_urls`
now lists its readable manual, and the Round 2 page data is byte-identical.

## 6. Decisions needed

**D-1. Non-rectangular exteriors.** Four records state their exterior in their own geometry:
- SaunaLife EE6G and EE8G barrels: "63″L x 91″ Diameter";
- Clearlight Sanctuary C: "Back walls: 71 1/4″, Side walls: 38 1/4″, Front wall: 47 1/2″";
- Almost Heaven Sutton: "Back Walls Exterior: 57¹⁄₁₆″W x 80⁵⁄₁₆″H, Side Walls Exterior: …".

Mapping a diameter or wall lengths onto width, depth and height would be derivation.
- **Options:**
  - (a) These don't meet the dimension requirement.
  - (b) Add schema fields for the manufacturer's own geometry (length + diameter; wall lengths),
    shown as stated, and accept them for the threshold.
- **Recommend:** (a) for Round 3 (it's 4 records), and (b) as a later schema round if you want
  them.

**D-2. Page metadata as a source.** Clearlight Retreat and Outdoor 5 state capacity only in the
manufacturer's own meta description ("fits 4-5 people", "5-person"), which is repeated in Open
Graph and JSON-LD.
- **Options:**
  - (a) Accept it as `listed` with the locator "page metadata".
  - (b) Visible body text only.
- **Recommend:** (a), the manufacturer's own words on its own page. It stays withheld if it
  conflicts with anything visible.

**D-3. Almost Heaven heat type.** 24 of 27 candidates are shared copy on each traditional sauna
page ("…creating löyly, the rejuvenating steam that defines a traditional sauna").
- **Options:**
  - (a) Accept it as the product page's statement.
  - (b) Require a product-specific statement.
  - (c) Infer "traditional" from a heater option whose every choice is a sauna heater or stove.
- **Recommend:** (b). It's the conservative 43. (c) is inference, which the project has refused
  so far.

**D-4. Headless fallback list.** Part A found JavaScript-only specs **only on Leisurecraft**.
Clearlight's specs are in its static HTML.
- **Recommend:** the fallback list is Leisurecraft only, and Clearlight is added back only with
  evidence.

**D-5. Round 1 errors that Part B would fix.** None of these changes a published value; each can
only publish values that are withheld today:
- the "Lumber Type" option matcher;
- escaped PDF links in the build;
- fractions and Unicode fractions.

All three would be applied to all brands, so Golden Designs, Maxxus, Salus and Dynamic records
could gain values too. **Recommend:** approve for all brands, with the Part B audit reading every
newly published value as usual. Any change to an already-published value would stop the round.

## 7. Sweep

- **Tests:** 738 passed (701 prior + 37 new).
- **Checks:** the Round 2 value-match check passes on all 67 pages, and the page data is
  byte-identical to Round 2.
- **Build:** jsonschema validation passes; the rebuild is byte-identical from two brand orders
  (`saunas.json` `bccfc7ba…`, conflicts `49f9b398…`, backlog `7de4a8fc…`). The `saunas.json` hash
  moved from Round 2 only by the attached diagnosis and the new manifest hash.
- **Lints:** preflight clean; missing-value lint 0; facts cache and drift clean.
- **Deploy:** self-test PASS.
- **Cost:** API $0.
