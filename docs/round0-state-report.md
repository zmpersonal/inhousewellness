# Round 0 — Spec table by join, and the storefront state report

**Run:** 2026-09-14 · **Branch:** `claude/happy-ptolemy-ec5gyp` · **Nothing merged, nothing published.**
Governed by `CLAUDE.md` → `docs/autoposter-adjustments-inhousewellness.md`; the
Shopify half additionally by `inh-seo/CLAUDE.md`.

Artefacts committed this round:

| File | What it is |
|---|---|
| `data/spec-table.json` | the versioned spec table, 211 rows, per-field provenance |
| `data/shopify-catalog-snapshot-2026-09-14.json` | the Shopify half of the join, with fetch date |
| `scripts/build_spec_table.py` | the join, re-runnable |
| `scripts/verify_theme_asset_path.py` | the deploy-path probe — **written, guards self-tested, never executed against Shopify** (§5) |

> **`agent-harness` and `build-loop` were not available as loaded skills in this
> session.** This round follows the prompt literally. Reporting is in-session:
> no Slack channel is provisioned (`CLAUDE.md` harness block, still TBD).

---

## 0. Two things to read before the numbers

**The Technical Overview was not attached to this session.** Only Build Brief
v2 came through. Section 6 below reconciles against Build Brief v2, `CLAUDE.md`
and the live repo; disagreements with the Technical Overview specifically could
not be checked, and none are claimed.

**The satellite CSV endpoints are unreachable from this environment.** Both
`infinitesauna.com` and `besthomeinfraredsauna.com` return `403` on CONNECT from
the egress proxy — an organisation policy denial, not a dead host. The join
therefore used the **cached copies already in the repo**, parsed directly from
those CSVs by `scripts/fetch_facts.py` on **2026-09-02**, twelve days stale:

```
data/facts/infinite_saunas.json   190 rows   fetched 2026-09-02T21:16Z
data/facts/bhis_saunas.json        90 rows   fetched 2026-09-02T13:04Z
```

This satisfies "parse the CSV endpoints directly, never via a summarizer" — the
cache *is* a direct CSV parse, with per-source fetch dates. It does not satisfy
"current". **Refresh the two caches before any published number depends on
them.** Every cell in the spec table carries the fetch date it came from, so the
staleness is visible per field rather than assumed away.

---

## 1. Match rate — and why there is no fuzzy matching to disclose

**The brief expected a brand/model string match against the Shopify catalog.
That turned out to be unnecessary.** Both satellite CSVs already carry an
`inhousewellness.com` product URL per row — `inhouse_url` on the infinite feed
(117 of 190 rows), `source_url` on the BHIS feed (84 of 90). The handle in that
URL joins by **exact string equality** to the Shopify product handle.

So the answer to "state the method and the false-positive risk" is:

| | |
|---|---|
| Method | exact equality on the InHouse product handle the satellite row supplies |
| Fuzzy / normalised matching | **none used** |
| False-positive risk | **zero by construction**, not by threshold |

That last claim was tested rather than assumed, because 142/142 resolving is
exactly the shape of result this project has been wrong about before. A negative
control confirms `handle:` is an exact filter, so a dead URL fails to match
rather than matching its neighbour:

```
handle:this-handle-does-not-exist-xyz123   → 0 products
handle:dynamic          (a prefix of ~30)  → 0 products
handle:dynamic-santiago                    → exactly 1
handle:<fake> OR handle:saunalife-g3       → only saunalife-g3
```

**The union of the two feeds claims 142 distinct InHouse handles. All 142 exist
in Shopify.** Neither feed maps two rows onto one handle; the join script exits
rather than guessing if that ever changes.

### The rate that matters

The denominator is not 673 SKUs. The catalog is 672 products across 16 product
types, most of which are accessories, grills and outdoor kitchens. The spec
table's population is `productType: Sauna`.

| Population | Matched | Rate |
|---|---|---|
| All `Sauna` SKUs (211) | 142 | **67.3%** |
| **ACTIVE `Sauna` SKUs (165)** | **139** | **84.2%** |
| Cold Plunge (42), Steam Generator (23), Float Tank (7) | **0** | **0%** |

The 84.2% is the honest headline: of the 69 unmatched Sauna SKUs, **only 26 are
ACTIVE** — the other 43 are DRAFT (31), ARCHIVED (10) or UNLISTED (2), i.e. not
sellable. All 69 are named in `data/spec-table.json` with reason
`NO_SATELLITE_ROW`.

🟡 **Neither CSV covers cold plunge, steam or float at all.** 72 sellable
cabinet-class SKUs have no spec source. If Round 1's calculator is meant to
cover plunges, that is a new data source, not a gap to fill.

### Two census facts worth keeping

- `productsCount` by status returns ACTIVE 480 + DRAFT 169 + ARCHIVED 21 = **670,
  against a total of 672**. The missing two are status `UNLISTED`, a value the
  three-way question did not ask for. Recorded rather than absorbed.
- Product types sum to 672 **exactly**, so the type census is complete.

---

## 2. Field completeness — matched rows only (n = 142)

| Field | Populated | % |
|---|---|---|
| brand · model · type · indoor_outdoor · inh_price_usd | 142 | **100%** |
| msrp_usd | 140 | 98.6% |
| wood | 139 | 97.9% |
| capacity_persons | 138 | 97.2% |
| sku | 136 | 95.8% |
| **volts** | 109 | **76.8%** |
| **amps** | 107 | **75.4%** |
| spectrum | 105 | 73.9% |
| max_temp_f | 98 | 69.0% |
| shipping_weight (Shopify, *not* crate) | 96 | 67.6% |
| emf_label | 84 | 59.2% |
| satellite_weight | 76 | 53.5% |
| circuits_count | 69 | 48.6% |
| assembled width / depth / height | 57 | 40.1% |
| emf_claim | 46 | 32.4% |
| emf_distance | 38 | 26.8% |
| plug_description (prose) | 36 | 25.4% |
| **heater_kw** | 33 | **23.2%** |
| warranty_term_text (prose) | 20 | 14.1% |
| ir_panel_watts | 6 | 4.2% |
| **crate L/W/H · crate_weight · door_width · preheat_minutes · clearances · warranty_doc_url · nema_plug · dedicated_circuit** | **0** | **0%** |

Across the whole table, nulls carry a reason: `NO_SOURCE_CARRIES_FIELD` 2,110 ·
`NO_SATELLITE_ROW` 1,311 · `EMPTY_IN_SOURCE` 1,289 · `NOT_IN_DETAIL_SNAPSHOT`
414 · `SHOPIFY_WEIGHT_ZERO` 46. Nothing is estimated, defaulted or inferred from
a similar model. The missing-value lint passes with 0 findings.

### Three nulls that are deliberate, and would otherwise be confident lies

- **`SHOPIFY_WEIGHT_ZERO` (46 rows).** Shopify reports `0 lb` for 46 matched
  variants. Zero is the untouched default, not a measurement. Left as a number
  it would flow into a freight sum and produce a precise, confident, false
  total — the exact failure shape `lint_missing_values.py` exists for.
- **`nema_plug` = 0%.** The infinite feed's `plug` column reads *"Standard 120V
  outlet"*. That is a description of an outlet, not a NEMA designation.
  Rendering it as `NEMA 5-15` would be inference; the prose is kept beside it as
  `plug_description`.
- **`dedicated_circuit_required` = 0%.** The BHIS `circuits` column is a **count**
  (mostly `1`), not a dedicated-circuit yes/no. Kept as `circuits_count`.

Likewise `preheat_minutes`: the infinite `heater` column *mentions* preheat in
prose ("heats to 180ºF in an hour"), and prose is not a measurement. It is a
candidate for a Round-2-style sourced extraction with verbatim spans, not a
field to regex today.

### Source conflicts — recorded, never resolved silently

9 fields disagree across sources on at least one row. The table keeps every
reading and flags `conflict: true`; no winner is picked. Pairs, not counts:

| Field | Rows | Example |
|---|---|---|
| spectrum | 48 | `dynamic-saunas-heming` — infinite `Far Infrared` vs BHIS `Full Spectrum` |
| **type** | **9** | `santiago-low-emf-sauna` — infinite `hybrid` vs BHIS `infrared` |
| wood | 8 | `dynamic-ultra-low-emf-sauna` — `Canadian Hemlock` vs `Cedar` |
| model | 7 | differing manufacturer part strings |
| **indoor_outdoor** | **3** | `gdi-8260-full-spectrum` — infinite `outdoor` vs BHIS `indoor` |
| **volts** | **1** | `maxxus-3-person-sauna-hemlock` — infinite **240V** vs BHIS **120V** |
| brand | 1 | BHIS records the retailer, not the manufacturer, on one row |
| msrp_usd | 1 | `leisurecraft-tranquility-barrel-sauna` — an 8-variant product; Shopify's `compareAtPrice` is variant 1's, the satellite's is a different variant. Variant-granularity mismatch, not a contradiction |
| max_temp_f | 1 | 140°F vs 151°F |

🔴 **The single `volts` conflict is the most dangerous cell in the table.** 240V
vs 120V on the same SKU is a ~4× swing in the electrical line and a different
answer to "do you need an electrician". One row is enough: a calculator that
picks silently is worse than one that declines.

---

## 3. 🟡 The fields too thin to build on — this is the gate

**This determines whether Round 1's freight line survives.**

| Field | State | Verdict |
|---|---|---|
| crate L × W × H | 0% — no source carries it | **cannot build** |
| crate weight | 0% as crate weight. Shopify ships a *variant shipping weight* at 67.6%, of which 46 rows are a fake `0` | **cannot build as specified** |
| door width required | 0% | **cannot build** |
| clearances | 0% | **cannot build** |
| preheat minutes | 0% as a number | **cannot build** |
| warranty document URL | 0% | **cannot build** (see §4 — metafields change this) |
| heater kW | 23.2% | **too thin to compute running cost catalog-wide** |
| volts / amps | ~76% *and* internally contradicted once | **usable with a disclosed gap, not silently** |

### But the freight line probably does not need crate data at all

**InHouse does not price freight by weight.** The live article
`true-total-cost-home-sauna` (published 2026-09-09) states the delivery terms as
flat tiers, sourced to `data/shipping-facts.json` and marked
`verified_by: client`:

> free to the curb · **$600** inside · **$1,800** inside and assembled · all-in
> **except** electrical · service fees non-refundable

If that is the pricing, the freight line is three constants and a radio button —
and crate dimensions and weight stop being blockers and become *nice to have*
for the "will it fit through my door" question, which already has its own live
article (`sauna-narrow-hallway-doorway-fit-guide`).

⚠️ `data/shipping-facts.json` is **referenced but not present in this repo** —
the SEO project gitignores its `data/` outputs. It needs to be located or
re-derived before Round 1 treats those three numbers as grounded.

---

## 4. 🔴 The finding that most changes Round 1 — the store already holds this data

`custom.total_cost_disclosure` **does not exist**. But the store carries **65
PRODUCT metafield definitions**, and several are populated with exactly the
fields the satellite CSVs are thinnest on.

Population measured on a **stated sample of 50 of the 165 ACTIVE Sauna SKUs**
(first page by title — a sample, not a census; a full pass needs the token path):

| Definition | Type | Populated (n=50) |
|---|---|---|
| `custom.dimentions_specifications` *(sic)* | rich text | **100%** |
| `custom.warranty_details` **or** `custom.warranty` | rich / multi-line | **100%** |
| `custom.shipping_details` | rich text | 90% |
| `custom.estimate` | single line | 88% |
| `custom.electrical_requirements` | rich text | **68%** |
| `custom.width` + `depth` + `height` (all three) | single line | 64% |
| `custom.product_documents` | multi-line | 56% |

Read a value and the significance is obvious:

- **`custom.electrical_requirements`** on `leisurecraft-serenity`:
  *"Voltage: **240V** · Amperage: **30A** · Breaker Requirement: **Dedicated 30A
  breaker** · Wiring: **10/2 wire with ground**"*.
  On `dynamic-saunas-monaco`: *"Requires **two separate dedicated 20 amp
  120-volt outlets**"*.
  That is `volts`, `amps` **and** `dedicated_circuit` — the field the CSVs cannot
  supply at all — already written, per product, in the merchant's own voice.
- **`custom.width/depth/height`** are plain integers (`73`, `73`, `79`). Better
  than the CSVs' 40.1%, though **the unit is not stated anywhere**; inches is an
  assumption and is recorded as one.
- **`custom.warranty_details`** on `leisurecraft-serenity` already contains
  Round 2's whole schema: *5-Year Limited Manufacturer's Warranty*, **parts-only**,
  *labor/shipping not included*, **residential use only**, exclusions, and a
  registration URL. Per brand, as prose, with verbatim spans available.
- **`custom.product_documents`** is a **Google Drive `<iframe>` embed**, not a
  URL field. So it is not `warranty_doc_url` as specified, but it is where
  documents live.

**Consequences for the plan, for the user to rule on:**

1. Round 1's electrical inputs may be better sourced from the store's own
   metafields than from the satellite CSVs. That is the opposite of the brief's
   assumption and worth deciding before building.
2. These are **rich-text prose, not structured data.** Turning them into numbers
   is an extraction job under Round 2's source-span rule — it is not free, and it
   must not be done with a silent regex that drops "two separate".
3. `custom.shipping_details` **already publishes installation labor ranges**
   (*$50–$75/hr per installer*, *$75–$150+/hr for licensed electrical*). Round 1
   proposes deriving that from BLS OEWS wages with a named multiplier. **Two
   different numbers for the same thing on the same store is a credibility
   problem**, and the store's version is already live.

---

## 5. State report

### Storefront

| Item | Finding |
|---|---|
| Live theme | **`Round 12 — drop shop-name suffix from product t…`**, id `146149867587`, role MAIN, updated 2026-09-14. The SEO project's own Round 12 theme is now live. |
| Theme count | **16** (1 MAIN + 15 UNPUBLISHED), including **10** named `SEO Round N` / `Round N`. Shopify's ceiling is 20 — **7 slots left**, and this project's convention is one theme per round. |
| **Online Store 2.0** | ✅ **Yes.** 35 of 37 templates are JSON; 3 section groups (`header-group`, `footer-group`, `overlay-group`). **The tools ship as sections.** |
| Template convention | Alternate page templates already in use — `page.about.json`, `page.compare.json`, `page.faqs.json`, `page.sale.json`, `page.store-location.json`. A `page.sauna-cost.json` is the established pattern, not a new one. |
| Custom sections | `custom-html.liquid`, `custom-liquid.liquid`, `custom-colors.liquid`, `custom-Faq.liquid` — convention is `custom-*.liquid`, casing inconsistent. Theme has **>250 files**. |
| Metafield `custom.total_cost_disclosure` | ❌ **does not exist** (targeted lookup, not inferred from a truncated list). 65 PRODUCT definitions exist — see §4. |
| Structured data | Handled by the **Avada SEO app** (`snippets/avada-seo-other.liquid`, 21 KB; `avada-seo-meta.liquid`) **plus** project-added `snippets/breadcrumbs.liquid` (12 KB) and `meta-tags.liquid`. ⚠️ The tools must **extend** this, not duplicate it — a second `Product` or `BreadcrumbList` block is a real risk. |
| JSON asset ceiling | **No `assets/*.json` exists today** — `cost-tables.json` would be the first. `assets/theme.js` is **180 KB** and `templates/product.json` is **76 KB**, so a few-hundred-KB JSON asset is comfortably inside the practical limit (Shopify's documented cap is 1 MB per non-image theme asset). |
| Shopify plan | **Basic**, USD, `inhousewellness.myshopify.com`. |

#### Page and topic collisions

**Page handles: no collision.** 26 pages exist; none of `sauna-cost`,
`sauna-running-cost`, `sauna-installation-cost`, `sauna-cost-index`,
`sauna-cost-methodology`, `warranty-decoder` is taken.

🟡 **Topic collision: yes, and it is live.**

- **`/blogs/saunas/true-total-cost-home-sauna`** — *"What a Home Sauna Actually
  Costs: Delivery, Electrical and Five Years of Running It"*, **published
  2026-09-09**, targeting the cluster the front matter records as **~6,000–7,000/mo**
  — the same cluster Build Brief v2 §8 assigns to Round 1. Its source is in this
  repo at `inh-seo/content/articles/true-total-cost-home-sauna.md`, `status: approved`.
- It already carries its own methodology: running cost = kW × hours × sessions ×
  the EIA state rate (period 2026-06, US avg 18.34¢/kWh, 13.11¢ Nevada to 52.72¢
  Hawaii), and it states kW coverage as **151 of 481 ACTIVE products (31%)**
  because "the silence is the finding".
- 🔴 **And it records a client ruling that contradicts Round 1 directly:**

  > `installation_cost: NOT PUBLISHED. Reader input, per the client ruling of 9
  > September. A national average would be the NEC failure in another costume.`

  Build Brief v2 §5 specifies installation as a **BLS-OEWS-derived range with a
  named multiplier**. The client has already ruled that installation cost is
  reader input and is not published. **This is a rescope conversation, not a
  rename.**
- Also adjacent and live: `sauna-narrow-hallway-doorway-fit-guide` (the
  `door_width_required` topic) and `best-2-person-sauna-buyers-guide`.

### Repo

| Item | Finding |
|---|---|
| Shopify helper to **reuse, not rebuild** | ✅ `inh-seo/scripts/lib/shopify.js` — Admin GraphQL client with cost-based leaky-bucket throttling, 429/THROTTLED retry, cursor pagination, plus hard-won helpers (`countProducts` enumerates because `productsCount` is cached behind your own write; `publicationsOf` because unpublishing from Online Store leaves other channels live). |
| Theme deploy helpers | ✅ `inh-seo/scripts/apply/theme-branch.mjs`, `theme-push.mjs`. |
| Audit/apply toolchain | ✅ 60+ scripts, all apply scripts dry-run by default, backups + `changelog.jsonl` + idempotency. |
| Theme files in this repo | ❌ **No.** `inh-seo/theme/` is a gitignored Shopify CLI checkout. Theme source is not version-controlled here. |
| Tests | ✅ **270 passed** in 0.73s (`.venv` had to be created; it is gitignored). |
| Custom lint | ✅ `scripts/lint_missing_values.py` — **0 findings**, and it was run against the new spec table. |
| Node | ✅ v22.22.2 available, satisfying `inh-seo`'s `engines: >=22`. |
| Stray file | `inh-seo/node` is a **0-byte file** — almost certainly a stray `> node` redirect. Harmless, worth deleting. |
| Workflow | `.github/workflows/autoposter.yml` has **no Shopify job**. The brief's `push_to_shopify` does not exist yet. |
| `verify_destinations.py` | Reports **0/127**. ⚠️ **This is the environment, not a finding about the sites** — every satellite domain is egress-blocked here, the same whole-host failure shape as L13. Do not read it as 127 dead destinations. |

### 🔴 Path confirmation — NOT completed, and the reason is not just the token

The brief asks for a minutes-long proof: write a small JSON file to an
unpublished theme's assets using only the token from the environment, fetch it
back, remove it. **It did not run.** Two independent blockers:

1. **No credential.** No `.env` exists anywhere in the repo, and there are
   **zero** `SHOPIFY_*` variables in the process environment. Verified by name
   and length only — `find . -name '.env*'` returns only the two `.env.example`
   files.
2. **No route.** Even with a token, this session cannot reach Shopify's Admin
   API: `inhousewellness.myshopify.com` and `admin.shopify.com` both return
   **403 on CONNECT** from the egress proxy. The Shopify MCP connector used for
   everything above works because it travels through a different, allowlisted
   transport — **which is not the transport a cron job will use.**

So a passing connector call here would **not** have been evidence for the
scheduled path, and reporting it as such would have been the confident-false
result this project keeps guarding against.

`scripts/verify_theme_asset_path.py` is written and ready. It takes the token
from the environment, uses plain `urllib` with no connector, refuses when
credentials are missing (exit 2, verified), and **refuses to touch the MAIN
theme**. That live-theme guard never fired against Shopify — transport failed
first — so per this repo's own rule that *a guard that has never failed has not
been tested*, it is exercised offline:

```
$ .venv/bin/python scripts/verify_theme_asset_path.py --self-test
  ok   live theme must be refused
  ok   unpublished theme must pass
  ok   development theme must pass
  ok   missing theme must be refused
self-test: all guards fire as specified
```

**To close this, run it where the cron will live** — GitHub Actions with
`SHOPIFY_ADMIN_TOKEN` as a secret, which is the exact target environment — or
from the machine that ran the SEO project:

```bash
python3 scripts/verify_theme_asset_path.py --theme-id 146147868739   # Round 11, UNPUBLISHED
```

---

## 6. Disagreements between the brief / `CLAUDE.md` and the live repo

The repo wins, but every disagreement is reported rather than quietly adopted.
(The Technical Overview itself was not attached — see §0.)

| # | Document says | Live state | Effect |
|---|---|---|---|
| 1 | "673 SKUs" | **672 products**, 1,470 variants | cosmetic |
| 2 | "the 254 tests" | **270 passing** | cosmetic; brief is stale |
| 3 | v2 §1: "Repo is the autoposter; storefront not deployed from it" → **new Round A** | The repo now contains `inh-seo/`: a full Admin-API toolchain, 114 tracked files, theme push/branch scripts, 10 themes already created through it | **Round A is substantively superseded** — as the prompt anticipated. What remains unproven is only the *unattended, env-token* leg (§5). |
| 4 | "190 models (88 traditional, 77 infrared)" | 190 = 88 traditional + 77 infrared + **25 hybrid**. 88+77 = 165, not 190 | the brief's own arithmetic omits a whole type; **`type` also disagrees between feeds on 9 rows** |
| 5 | Join = Shopify catalog against satellite brand/model | Satellites carry the InHouse URL; the join is an exact handle equality | **better than specified** — no fuzzy matching, no false-positive risk to disclose |
| 6 | "90-model infrared index" (an independent source) | 90 rows, but **84 of 90 are sourced from inhousewellness.com itself** | it is largely a mirror of INH's own catalog, not an independent check on it. Treat "two sources agree" with care. |
| 7 | v2 §7: "`SHOPIFY_ADMIN_TOKEN` … is new" | The SEO project already uses it routinely; it is simply **absent from this environment** | the blocker is provisioning *here*, not creating it |
| 8 | v2 §2: reuse "Playwright pinned at 1.49.1" (macOS-13 reason) | `requirements.txt` documents a **second** reason — render determinism — that applies on Linux/CI too | do not unpin for Linux on the grounds that reason 1 is macOS-only |
| 9 | v2 §5: pipeline job `push_to_shopify` | no Shopify job exists in `.github/workflows/autoposter.yml` | to be built |
| 10 | `CLAUDE.md` governs this repo | Two projects now share one root with **two** `CLAUDE.md` files (`/CLAUDE.md` autoposter, `inh-seo/CLAUDE.md` SEO), and the root one does not mention the SEO work | 🟡 a future session reading only the root file will miss the entire Shopify toolchain |
| 11 | v2 §4 expected gaps: crate dims, warranty URLs, preheat | confirmed exactly — all three are 0% | brief was right |
| 12 | v2 §6: seed the Warranty Decoder from public brand PDFs | `custom.warranty_details` is already populated on ~100% of the sample | 🟡 cheaper first source than PDFs, and it is the store's own published text |

---

## 7. 🟡 Recommendation — where Liquid should live for Rounds 1 and 2

**Admin API upsert from the pipeline, into a per-round unpublished theme. Not a
separate theme checkout under its own version control.**

Why:

1. **The convention already exists and is proven at scale.** Nine themes have
   been deployed this way in the last week, each named for its round, each left
   unpublished until a human publishes. Introducing a second mechanism now means
   two ways to change the storefront and no single answer to "what is live".
2. **The theme is not the source of truth and should not pretend to be.** It is
   a vendor theme (`Hyperspeed`, >250 files) carrying app-injected code from
   Avada SEO and Judge.me. Checking it into git would version thousands of lines
   nobody here owns, and every app update would land as a spurious diff.
3. **The pipeline has to reach the Admin API anyway** to push `cost-tables.json`
   as a theme asset and to write metafields. One credential, one transport, one
   thing to prove — and §5 is exactly that proof, still outstanding.
4. **Rollback already works.** The previous round's theme stays unpublished and
   intact; `inh-seo`'s own note records that theme roles were verified directly
   rather than trusted from `theme publish` output.

Version-control the **inputs**, not the theme: commit the section Liquid under
`sections/` in this repo as the authored source, and have the pipeline upsert it.
That gives reviewable diffs on the code that is actually ours, without pretending
to own the vendor theme.

**One caveat to watch:** 16 of 20 theme slots are used and the convention burns
one per round. Rounds 1 and 2 will take it to 18. Plan to prune.

---

## 8. What is blocked, and on whom

| # | Item | Needs |
|---|---|---|
| 🔴 1 | **Round 1's installation-cost line contradicts a standing client ruling of 9 September** (§5) | a decision from the user before Round 1 starts |
| 🔴 2 | Path confirmation (§5) | `SHOPIFY_ADMIN_TOKEN` in an environment that can reach Shopify — run it in Actions |
| 🟡 3 | `volts` 240 vs 120 on `maxxus-3-person-sauna-hemlock` | one source must win, by checking the product page |
| 🟡 4 | Electrical data: satellite CSVs (76%) vs store metafields (68%, richer, prose) (§4) | a source-of-truth decision before building |
| 🟡 5 | `data/shipping-facts.json` referenced but absent (§3) | locate or re-derive; three published numbers depend on it |
| 🟡 6 | 72 sellable plunge/steam/float SKUs have no spec source (§1) | scope call: does the calculator cover them? |
| 🟡 7 | Satellite caches are 12 days stale and unreachable from here (§0) | refresh from an environment that can reach the two domains |

**Round 1 is not started.**
