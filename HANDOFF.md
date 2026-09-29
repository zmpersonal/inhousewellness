# HANDOFF

## ⏸ INH Verified — Batch A LIVE (47 model pages), merged; WAITING for Batch B approval (2026-09-29)

`main` includes `verified/go-live`.

- **Live** (verified logged-out on 2026-09-29):
  - the hub (47 rows, "Power supply" column) and the methodology page;
  - 47 model pages: every page for a brand INH sells, plus Salus Solara and Almost Heaven Pinnacle;
  - product links on all 40 mapped products, including leisurecraft-luna (`product.Bundle.json`).
- **Unknown paths** under `/pages/sauna-database/` render noindex, Shopify's self-canonical, and
  "This model page isn't available."
- **Batch B** (84 entries, brands INH does not sell) is **NOT to be activated until the user
  approves.**
  - Handles are in `out/verified/golive/batches.json` "B".
  - Similar models: 65 / 2 / 0 / 17 pages with 3 / 2 / 1 / 0 matches.
  - Procedure:
    1. `activate --handles <B> --write`
    2. `live-check --links`
    3. on any failure: `deactivate --handles <B> --write`
- **Undo:**
  - per step: `restore-step --step-name r4|design --execute --allow-live-theme-id <MAIN>`;
  - whole launch: `rollback --execute --allow-live-theme-id <MAIN>`.
- **Before publishing ANY theme:** `.venv/bin/python scripts/verified_theme_check.py --theme-id <ID>`.
- **Follow-up:** correct the stale layout comment ("no canonical") at the next layout write.
- ⚠️ `inh-seo/scripts/apply/r23j-plain-text.mjs` belongs to another project. Leave it.

---

## INH Verified — unknown-path decision (resolved: Option A) (2026-09-29)

Branch `verified/go-live` (not merged). **Live is unchanged:** the canary state (3 active entries,
the design live).

- **Ready, not deployed:**
  - item 1: product templates `product.json` and `product.Bundle.json` (Luna);
  - item 2: the unknown-path guard, on the preview only;
  - item 3: the series and heat-only similar rule (page data rebuilt locally; entries not updated).
- **Blocked:** Shopify injects a self-canonical when the theme omits one, so "noindex without a
  canonical" is impossible. Options are in the latest report message and in the RUNLOG.
- **After the decision:**
  1. `snapshot-files --step-name r4` with files = layout, the hub section and each product
     template in use;
  2. `update-entries --write`;
  3. `deploy-files --step-name r4 --allow-live-theme-id <MAIN> --write`;
  4. `live-check --links`;
  5. Batch A: `activate` the handles in `out/verified/golive/batches.json` "A", then
     `live-check --links`;
  6. merge if it passes.
- ⚠️ `inh-seo/scripts/apply/r23j-plain-text.mjs` belongs to another project.

---

## INH Verified — design LIVE, Batch A REVERTED (2026-09-29)

Branch `verified/go-live` (NOT merged; the merge was skipped because Step 2 failed). Read
`docs/verified/golive/design-and-batch-a-report.md`.

- **Live** (verified logged-out): the hub, the methodology page and 3 model pages
  (`golden-designs-copenhagen-3-person`, `salus-solara-6-person`,
  `almost-heaven-pinnacle-barrel-4-person`) in the new design, plus the Copenhagen product link.
  128 entries are DRAFT. `data/verified/golive/launch-state.json` agrees.
- **Decision 1, the Bundle template** (recommended A): patch MAIN's own
  `templates/product.Bundle.json` with the link section after `judgeme_reviews_bundle`. Extend
  `verified_theme_check.py` and the CLAUDE.md list to every product template a mapped product
  uses. Then re-run Batch A:
  1. `baseline-products` (already done for these 39);
  2. `activate --handles <out/verified/golive/batches.json A> --write`;
  3. `live-check --links`.
- **Decision 2, the soft 404** at `/pages/sauna-database/<anything>` (recommended: noindex plus
  the hub canonical when the path is not the hub).
- **Decision 3, the similar-models rule:** keep both variants of one model series, or show one per
  series.
- **Batch B** (84) is not to be activated until approved.
- **Design-step undo:** `restore-step --step-name design --execute --allow-live-theme-id <MAIN>`
  restores the 4 files and all entry fields from `data/verified/golive/step-design/`.
- **Whole-launch undo:** `rollback --execute --allow-live-theme-id <MAIN>`.
- **Before publishing ANY theme:**
  `.venv/bin/python scripts/verified_theme_check.py --theme-id <ID>` (CLAUDE.md governance).
- ⚠️ `inh-seo/scripts/apply/r23j-plain-text.mjs` belongs to another project. Leave it.

---

## INH Verified GO-LIVE — canary live, hub report diagnosed (2026-09-29)

Branch `verified/go-live` (not merged; `main` = `8f28eb1`). Read `docs/verified/golive/canary-report.md`.

**Live on inhousewellness.com:**
- `/pages/sauna-database` (hub) and `/pages/sauna-database-methodology`;
- 3 model pages: `golden-designs-copenhagen-3-person`, `salus-solara-6-person` and
  `almost-heaven-pinnacle-barrel-4-person`;
- the Copenhagen product-page link.

128 entries are DRAFT.

- **MAIN** `167150092355` carries 10 new files and 2 patched (+12/-0). The pre-deploy snapshot is
  `data/verified/golive/main-167150092355-snapshot/`.
- **Launch state** (active handles, reversal file, timestamps): `data/verified/golive/launch-state.json`.
- **Tool:** `scripts/verified_golive.py`. Steps: `activate`, `live-check --links`, `live-shots`,
  `verify-entries`, `rollback` (dry run; `--execute --allow-live-theme-id <MAIN>` to run).
- **Next, after approval:** batch A (44 INH-sold entries; 39 product links appear), then batch B
  (84). See the activation plan in the report.
- **Awaiting decision:** the hub "Supply voltage" cell for circuit and option records.
- **2026-09-29 hub report:** it was a theme-preview view in the reporting browser. The live hub
  was verified logged-out (3 of 3 rows). Checks are hardened (`visitor_get`, `hub_rows_problem`,
  `page_update_checked`). **Activation of batches A and B is ON HOLD until the user re-approves.**
- ⚠️ Any theme preview, or publishing any other theme, shows the hub as title and body only. Only
  MAIN holds the INH Verified templates.

- ⚠️ Rollback step 4 has not been run on MAIN. Deleting in-use templates, and JSON re-serialisation
  on recreate, were proved on the preview.
- ⚠️ `inh-seo/scripts/apply/r23j-plain-text.mjs` is another project's uncommitted change. Leave it.

---

## INH Verified Round 3 — Part B delivered and approved (2026-09-28)

Branch `verified/r3-parity` (not merged). Read `docs/verified/round-3-part-b-report.md`.
Evidence: `docs/verified/r3-evidence/`.

**Awaiting your approval:**
- **(1)** approve rows in `docs/verified/round-3-title-review.csv`, then freeze them into
  `handles.json` and `title-overrides.json` the same way Round 2 did;
- **(2)** the amperage wording (`verified_pages.amperage_is_circuit`);
- **(3)** the Curve Dome gap: leave it (recommended).

**Rebuild chain (offline):**
1. `verified_build.py --brands <all 16, out/verified/ALL.sh>`
2. `verified_gaps.py` (offline). Run the gaps and build pair twice, until the hashes converge.
3. `verified_pages.py --build`
4. `verified_pages.py --preliminary docs/verified/round-3-title-review.csv`
5. `verified_render.py`, then `verified_render.py --preliminary [handles…]`
6. `verified_checks.py --nojs`, then `verified_checks.py --preliminary --out out/verified/checks-preliminary.json`

**Rules added this round:**
- **Stated amperage includes draws.** A sheet stating a draw and a circuit is ambiguous; never
  choose one.
- **Headless and page metadata are fallbacks.** They speak only when the plain page is silent
  (`resolve_fallbacks`).
- **Exterior is published only when complete for its shape.**
- `dimensions.exterior` is schema-required.

⚠️ The working tree holds an unrelated change to `inh-seo/scripts/apply/r23j-plain-text.mjs` from
another session. It was NOT committed here.

---

## INH Verified Round 3 — Part A delivered and answered (2026-09-28)

Branch `verified/r3-parity` (from `verified/r2-pages`). Read `docs/verified/round-3-part-a-report.md`
(§6: decisions D-1 to D-5) and `docs/verified/round-3-gap-samples.md`.

- Diagnosis: `scripts/verified_gaps.py` (`--fetch` online, default offline classify, `--samples PATH`),
  output `data/verified/gap-diagnosis.json`, attached to records by the build as `gap_diagnosis`
  (internal; stripped from every payload; the "Not stated on the manufacturer's page" wording is NOT rendered).
- Headless: `verified_fetch.fetch_rendered()` (manifest key `headless:<url>`). From Part B it is a
  FALLBACK only: render when the plain fetch lacks a threshold field AND the brand is known to load specs
  via JS (evidence so far: Leisurecraft only; Clearlight's specs are static). Record the reason. Never
  re-render a cached page. Redwood: plain fetch only (decided).
- Governance done: MAIN resolved at run time (`resolve_main`, `main_refusal`) in every theme writer.
- Part B must not start before D-1..D-5 are answered.

---

## INH Verified Round 2 — Part B delivered (2026-09-28). Nothing is live.

Branch `verified/r2-pages` (not merged). Read `docs/verified/round-2-part-b-report.md` and
`docs/verified/round-2-go-live-checklist.md`. Evidence (screenshots, check JSON) in `docs/verified/r2-evidence/`.

- Preview theme `146278776899` holds the templates (verified by MD5). Hub + methodology pages exist HIDDEN.
- PENDING on token scopes `write_metaobject_definitions`, `write_metaobjects`:
  `.venv/bin/python scripts/verified_deploy.py entries --write` then `metafields --write` (reversal file +
  one-product reversal proof built in). Entries are created DRAFT only; nothing in the script sets ACTIVE.
- Rebuild chain (offline): `verified_build.py --brands <all 16>` → `verified_pages.py --build` →
  `verified_render.py [--shots …]` → `verified_checks.py --nojs [--links]`.
- Frozen: `data/verified/handles.json` (never regenerate; changes go through `handle-redirects.json`),
  `data/verified/title-overrides.json` (overrides may only remove words).
- ⚠️ MAIN is now `167150092355` (Round 23b). CLAUDE.md's `146149867587` is stale — not edited, needs the user.
- Go-live is gated on Round 3 (parity: Almost Heaven, Clearlight, Sun Home, Redwood, Heavenly Heat;
  plus recording option-dependence with evidence).

---

## ✅ INH Verified Round 1 — COMPLETE (2026-09-28).

Branch `verified/r1-data-foundation`, **not merged**. Read
`docs/verified/round-1-final-report.md`. Its §7 is the Round 2 decision list (R2-D1 to R2-D15),
for public metaobject pages at `/pages/sauna-database` and `/pages/sauna/[model]`.

- **Dataset:** `data/verified/saunas.json`: 262 records, 241 published, 21 held by rule.
  - `data/verified/conflicts.json`: lead mismatches and within-source ambiguities.
  - `data/verified/internal/backlog.json`: 26 leads with no fetchable origin.
  - Manufacturer-page inconsistencies (the future public ledger) are in report §4.
- **Rebuild everything (offline, deterministic):**
  `.venv/bin/python scripts/verified_build.py --label final --brands <all 16 lead brands>`.
  Always pass every configured brand; blocked brands have no records but do have backlog
  entries. The list is in `data/verified/sources.json`.
- **Refresh:** `.venv/bin/python scripts/verified_fetch.py --brands …` (online; robots first,
  1 req/2 s, Crawl-delay honoured). Then rebuild and audit the diff against the previous
  committed `saunas.json`: every changed value, every electrical value.
- **Standing rules** (CLAUDE.md: editorial independence, source policy):
  - D1: the lead source is never named.
  - D8: the cost calculator is not in this project.
  - Maxxus and Dynamic rest on the `origin_basis` documents.
- R2-D15: resolved in Round 2 Part A (argument-order-dependent backlog).

---

## ✅ Phase 1 is APPLIED and verified. Nothing is awaiting approval.

113 of 165 active sauna SKUs had their `custom.shipping_details` corrected on
2026-09-15. The stale "Installation labor: $50–$75/hr per installer" line now
returns **0 matches across all 165**; the 52 SKUs outside the approved list are
unchanged; the sentence-survival guard passes on the live values for all five
templates. This was the first write to the live store in this project.

## 🔴 The one thing blocking Round 2's shape

**Heater kW is 31.7% of the 139 matched active SKUs, and tier 1 has never been
fetched.** Manufacturer sites are egress-blocked from agent sessions, so the
fetcher now lives in Actions. It has not run.

Run these two, in this order, from the Actions tab:

1. **`fetch manufacturer specs`** with `mode: discover`.
   Every `product_url_template` in `data/manufacturer-registry.json` is
   deliberately `null` — they could not be tested from a blocked session, and an
   untested template can resolve to a category page and mis-attribute its specs
   to a product. The discover run probes robots.txt and the homepage for each of
   the 11 vendors and commits `data/facts/manufacturer-discovery.json`.
   **Fill the templates in from that file**, then re-run with `mode: fetch`
   (start with `limit: 5`).
2. **`fetch external data`** — refreshes the EIA cache (currently 2026-09-03,
   period 2026-06), both satellite CSVs (2026-09-02), the outdoorsteamsauna
   75-metro feed, and builds `data/zip-to-state.json`.
   Needs `EIA_API_KEY`, `CENSUS_API_KEY`, `FRED_API_KEY` as Actions secrets.

After both: rebuild `cost-tables.json` and the tier-1 coverage number is real.
The merge path is already built and fixture-verified — tier 1 outranks the
metafield, and any disagreement is recorded under `disagrees_with_metafield`
rather than silently resolved.

## State

| Artefact | What |
|---|---|
| `data/cost-tables.json` | 165 rows, 316 KB, schema 1.0.0 |
| `src/power_parse.py` | the guards, ONE definition, imported by every reader |
| `data/manufacturer-registry.json` | 11 vendors; all URL templates null on purpose |
| `data/zip-to-state.json` | **not yet built** — Actions run 2 produces it |

Coverage of the 139 matched active SKUs: rated power **31.7%**, volts 56.1%,
amps 74.8%, dedicated circuit 33.1%. Energy: 51/51 jurisdictions, state
granularity.

## Boundaries that must not be crossed in Round 2

- **No installation or electrician figure** in the dataset or the calculator.
  Electrical cost is reader input (ruling 1); electrician labour is third-party
  and never summed into freight (ruling 3).
- **kW is never derived from volts × amps.** 102 SKUs stay `POWER_NOT_STATED`.
  A null means the calculator declines to compute running cost — correct.
- **An unresolved ZIP renders a coverage gap**, never the national average. EIA's
  `US` row and the 10 census-division aggregates are held in a separate
  non-fallback block for exactly this reason. ZCTAs are not ZIPs: PO-box-only
  ZIPs have no ZCTA and will not resolve.

## Open, reported, not acted on

- An **$80 "Economy"** domestic shipping method is active alongside free
  "Standard", priced above it, unmentioned in the "free curbside, no minimum" copy.
- 29 SKUs state **multiple circuits**; 4 have a **configurable rating**.
- Build Brief v2 says "~15 manufacturers"; the catalogue has **11**.

---

## ⛔ READ FIRST — Round 1 is built; ONE approval is outstanding

**Awaiting your approval: the Phase 1 metafield correction.** 113 of 165 active
sauna SKUs carry a stale "Installation labor: $50–$75/hr per installer" line in
`custom.shipping_details`, contradicting the $1,800-flat product page. The
proposal is committed and **nothing has been written to Shopify**.

- Proposal: `data/shipping-metafield-fix/proposal.json` (before/after per template)
- Affected list: `data/shipping-metafield-fix/affected-handles.txt` (113 handles)
- Generator: `scripts/fix_shipping_metafield.py` (no `--apply` path by design)

**On approval**, the apply is relayed through the Shopify MCP connector
(`metafieldsSet`), resolving handle → id at write time, then verified by
re-running the census probe and confirming it returns zero. This environment
cannot reach admin.shopify.com directly (403 on CONNECT), so the write cannot
originate from a script here.

## Round 1 state

| Artefact | What |
|---|---|
| `data/cost-tables.json` | 165 rows, 311 KB, schema 1.0.0 — the calculator's dataset |
| `data/active-sauna-handles.json` | the 165-SKU census population |
| `scripts/build_cost_tables.py` | rebuilds the table from saved Admin API pulls |
| `scripts/fix_shipping_metafield.py` | Phase 1 proposal generator |

Coverage against the 139 matched active SKUs: rated power **31.7%**, volts 56.1%,
amps 74.8%, dedicated circuit 33.1%. Against all 165 active: power 35.2%,
dedicated circuit 52.1%. Energy: 51/51 jurisdictions.

## 🔴 Blocking for Round 2

1. **Manufacturer websites are unreachable from this environment** (egress 403),
   so source precedence tier 1 was never consulted. Power coverage is 31.7% and
   tier 1 is the stated route to raising it. Needs a machine with open egress or
   a GitHub Actions job.
2. **EIA cache is 2026-09-03, period 2026-06.** `api.eia.gov` is blocked here.
   Refresh before any published number depends on it.
3. **A null rated power means the calculator must decline to compute running
   cost** for that model. That is correct behaviour, and Round 2 must render it
   as an honest gap, never a default.

## Open, reported, not acted on

- An **$80 "Economy" domestic shipping method is active** alongside the free
  "Standard", priced above it, and named nowhere in the "free curbside shipping,
  no minimum" copy.
- 29 SKUs state **multiple circuits** (e.g. 240V stove + 120V lighting); `volts`
  is null with `MULTIPLE_CIRCUITS_STATED` and all readings kept.
- 4 SKUs have a **configurable rating** (6 kW fitted / 8 kW optional).

---

## ✅ The week of 2026-09-12 is SCHEDULED — 15 posts live in Blotato

Scheduled 2026-09-11. 14 Pinterest pins (2/day, 15:00 and 23:00 UTC) plus the
Facebook finding (Tue 16:00 UTC). Every resolved time matched the request.
Submission ids are in `state/scheduled-weeks.json`. Batch cost $0.3728.

The account posts again from **Sat 12 Sep 15:00Z** after nine days silent.

### Next session, in this order

1. **Reconcile last week first** — it gates the new batch:
   `schedule_week.py reconcile --posts <blotato_list_posts output>`
   A `failed` post halts. A post that is simply ABSENT also halts: absence is
   not proof of publication.
2. Then `schedule_week.py plan --start <next Monday> --live` and follow the
   operating procedure in CLAUDE.md.

### Known transport issue — check this before planning

`blotato_create_post` needs a session where the MCP schema is TYPED. When the
schema degrades to `{"type":"object"}` with no properties, the harness sends
`mediaUrls` as a string and every call fails validation. A session restart did
NOT fix it; the week was scheduled by relaying the precomputed arguments from
`out/weeks/<week>/calls.json` through a second session that had the typed
schema. Toggling Blotato in Settings → Connectors is the suspected fix, untested.

`schedule_week.py calls` exists precisely so the arguments can be relayed
without regenerating anything.

## ⛔ READ FIRST — the week of 2026-09-12 is BUILT AND STAGED, NOT SCHEDULED

15 posts (14 Pinterest pins + 1 Facebook finding) are generated, validated,
rendered, uploaded to Blotato and byte-verified. Only the final 15
`blotato_create_post` calls did not happen.

**Why:** in that session the Blotato MCP tools exposed no parameter schema
(`{"type":"object"}` with no properties), so the harness sent every argument as
a string, and Blotato's validator rejected `mediaUrls` with
"Expected array, received string" on every attempt. The same tool published
7 posts with media on 2026-09-02, and the Buffer connector accepted arrays in
the same session — so this is a session-level schema/serialization fault, not
an API change. Nothing was created: `list_posts` and `list_schedules` were both
empty afterwards, and the D5 breadcrumb was cleared on that evidence.

**To finish (no regeneration, no extra model spend):**

```
1  restart the session, or toggle Blotato off/on in Settings -> Connectors
2  confirm the schema is back: blotato_create_post must show typed parameters
3  python3 scripts/schedule_week.py calls --start 2026-09-12
4  make the 15 blotato_create_post calls with those exact arguments
5  python3 scripts/schedule_week.py record --start 2026-09-12 --results <json>
```

The plan and the verified media URLs persist in
`out/weeks/2026-09-12/plan.json`. Slots start Sat 2026-09-12 15:00Z; if that is
past, re-run `plan --start <a future Monday>` instead.


**Last updated:** 2026-09-02, end of Round 5.
**Read first:** `CLAUDE.md` → `docs/autoposter-adjustments-inhousewellness.md` → `RUNLOG.md` → `LEARNINGS.md`.

---

## Round 5 state (supersedes the Round 3 notes below where they conflict)

- **Two pins are LIVE.** Broken-post counter: **day 1, 2 published, 0 broken, 13
  clean days to go** (`state/broken-post-counter.json`).
- Queue: **80 queued**, 35 distinct destination URLs, INH 41.2%, domain and URL
  quotas clean, 0 non-200.
- Batch 02 fully routed: **36 of 36**.
- **25 rows are fact-grounded** via `source_data` rather than an article.
- Caps: domain 35%, **per-URL 4 per 30 days**.
- **147 tests pass.**

### The one thing still unproven
**The automated caption path has never run against a live model.** `.env` does not
exist at repo root. Everything else is wired: `src/model.py`, python-dotenv,
anthropic SDK 1.3.0, Sonnet, SDK default endpoint (shell `ANTHROPIC_BASE_URL` is
ignored deliberately). One line in `.env` unblocks it — see `.env.example`.

### Staged, awaiting review
`out/staged/emf-correction.json` — the EMF correction, the first fact-grounded
post. Validator PASS including the new numeral rule; every figure traced to
`infrared_saunas.csv`.

### 🔴 Strongest Reel candidate in the backlog
The **EMF correction** — "90 models carry an EMF label, 71 say Near Zero EMF,
only 46 state a number, only 34 state the measurement distance." It converts the
brand's best-performing existing argument from an opinion into a statistic, and
it is `compliance: low` (no health claim). Build it after Set 3. **Not built this
round.**

### 🟡 Open: 4 constants still inherit the thin-satellite assumption
`docs/constant-audit-2026-09-02.md`. Highest value: the 1:1 `CLUSTERS` domain map
(842 pages sit on one "cluster" domain) and the 12-URL hand-curated destination
file (supports at most 48 pins network-wide under the per-URL cap).

---

## Where the project is

Rounds 1–3 complete. **Nothing has been published. No cron exists.
`AUTO_PUBLISH = False` in the conductor. The feedback loop is `dry_run=True`.**

The full chain now runs end to end and stages:
D5 gate → select → render (local, 0 credits) → one caption call → validate → stage.

## Verified this round

| Path | State |
|---|---|
| Legacy gate | ✅ no `via: network` post after 2026-09-01; ~26h of silence vs a ~2.4/day baseline |
| Corpus | ✅ **1,908 pages across 11 domains** (was 109, INH only) |
| Queue | ✅ **34 queued / 69 blocked**, 0 non-200, all fields present |
| Destinations | ✅ 12/12 URLs pass both gates; validator allow-list matches the router |
| Media pipeline | ✅ live PUT → `publicUrl` resolved **byte-identical** |
| D5 gate | ✅ simulated post-then-crash halts the next run |
| Staged run | ✅ 4 posts, 0 credits, $0.0148, 4/4 validator pass, published nothing |
| Tests | ✅ **116 passing**; Round 1/2 assertions replay clean |

```bash
.venv/bin/python -m pytest tests/ -q && .venv/bin/python scripts/run_cycle.py --offline
```

## The open decision — INH share is 41.2%, floor is 60%

**This is a ceiling, not a routing bug.** Only 14 of 34 queued rows have any INH
destination scoring ≥0.40; reaching 60% needs ~20. Nothing was redirected to a
weaker INH page to make the number, per the brief's own rule.

Also over: `outdoorsteamsauna.com` at 17.6% against the 15% cap (6 of 34).

Holding the floor by blocking rows would drop the queue from 34 to ~23, below
where Round 2 started. Options are with the user.

## Other open items

- **Only 2 of 34 rows reach an interactive asset.** The queue has no dimension or
  EMF keywords at all. A new keyword batch targeting the assets is the fix.
- **Still-blocked content brief, 69 rows / 45,190 monthly searches:** session
  length (7,880), etiquette/phone/wear (6,590), general cost (5,490), colds
  (5,390), dry vs wet (4,760), build/DIY (4,630), weight loss (4,290).
- **Caption generator has still never run against a live model** — no Anthropic
  key here. The staged run used a deterministic offline stand-in, and its copy is
  explicitly *not* publishable (it is topic-blind: it wrote "sauna renovation cost
  comes down to how the heat reaches you").
- **`firstComment` is not validated for placeholders.** The stand-in emitted
  "Full comparison: PLACEHOLDER" and the validator passed it — it only checks the
  body for URLs. Worth a rule; not changed this round because the brief froze the
  validator.
- Six topical Pinterest boards still do not exist; all rows carry
  `board_is_placeholder: true`.
- Pinterest cannot be scored per post (Buffer free plan = 31-day channel aggregate).
- Blotato holds zero INH history, so the IG/FB analytics feed stays empty until
  the machine posts.
- `animateAiImages` still unmeasured; stays disabled.
- Reels Set 2 still blocked by the health-claim validator — correct behaviour.
- **Not pushed to any remote.** Local git only.

## Credits and tokens

Blotato: **1,550 / 1,750** — zero spent this round, all rendering local.
Model: $0 live. Staged cycle cost $0.0148 with the stand-in; a live cycle is
projected at ~$0.05, about $1.51/month at full cadence.

## What Round 4 looks like

Resolve the INH-share decision, then: wire a live model key and run one real
caption cycle, review the staged output as a human, and only then consider the
controlled first publish. Cadence stays Pinterest 2/day until the queue recovers
above 60 rows — and not by lowering the 0.40 threshold.

---

## Tier 1 manufacturer specs — standing state, 2026-09-15

**Blocked, and not on a matcher failure.** All 11 `product_url_template` values
are still null after discover run 3. The run reached 6 of 11 vendors; 5 fail at
robots.txt (Dynamic Saunas self-signed cert, Dundalk 404, Mande Spa TLS alert,
Kohler timeout, Ripavi unreachable), which is 52 of 139 matched SKUs. No vendor
*disallows* crawling.

**Before `mode: fetch` can ever be right, two things must be settled:**

1. Run `discover` again on the upgraded script. It now collects sitemap-derived
   real product URLs and tests whether any carries one of our SKUs. A template may
   only be filled where the discovery file shows both `sample_product_urls` and
   `sku_matches` — enforced by `tests/test_manufacturer_discovery.py`.
2. Fix the resolution mechanism. `format(handle=handle)` puts our Shopify slug in
   their URL space, and the `model_key` every registry row declares is never read.
   A per-vendor SKU→URL index built from sitemap evidence is the likelier design
   than a format string. **Decide this before requesting a single product page.**

Open for a human: the fetcher skips a host whose robots.txt 404s, which RFC 9309
treats as allow-all. That costs Dundalk (7 SKUs). Deliberate, not a bug.

Also open: `actions/checkout@v4`, `actions/setup-python@v5` and
`actions/upload-artifact@v4` target Node 20 and now raise a deprecation warning on
every run. One line each to bump; left alone so far.

---

## Manuals and model numbers — standing state, 2026-09-15

**The cheap path is real.** 102 of 165 active sauna SKUs carry a manual document
on our own page (`custom.product_documents`, Google Drive embeds — not PDFs).
That reaches Dynamic Saunas, Dundalk, Mande Spa and Ripavi despite their hosts
being unreadable.

**Next action: dispatch `fetch manuals` with `limit: 5`** and read the five
SKU / model / kW / span / page / URL pairs. Nothing scales before that. It cannot
run from a session: drive.google.com is 403 on CONNECT like every vendor host.

**Unknowns the first run settles:** whether the Drive files are PDFs at all
(Drive serves an HTML interstitial for large files), how many need OCR, and
whether the spec-plate tiering fires on real manuals.

**Needs a human — 15 SKUs, bucket 4 at an unreachable vendor.** 13 Dynamic Saunas
(DYN-6203-01, DYN-6440-01 Elite, DYN-6203-02 FS, DYN-6336-03 FS, DYN-6336-02
Elite, DYN-6310-04 Elite, DYN-6006-03 FS, DYN-6206-01 Elite, DYN-6206-01,
DYN-6009-03 FS, DYN-6220-01 Elite, DYN-6210-04 Elite, DYN-6415-03 FS) and 2
Kohler (38440-0FNC-SPS-1 / -2, plus one variant with no SKU). No automated path
reaches these; ask those two vendors for these specific models, not "everything".

**`data/own-page-census.json` is an input to CI and cannot be rebuilt there** —
the Admin API is MCP-only. Re-run `scripts/census_own_pages.py` from a session
whenever the catalogue changes, or `fetch manuals` is reading a stale list.

---

## Manuals — after run 1, 2026-09-15

**The plumbing works end to end.** Drive serves real PDFs from
`drive.usercontent.google.com` with no interstitial and no confirm token; 278
pages, no OCR needed. Content-Type is `application/octet-stream`, never
`application/pdf` — test the `%PDF` magic bytes, never the header.

**But zero rated-power values came out of nine manuals**, and the cause is not yet
established. The next `fetch manuals` run (keep `limit: 5`) now records
`electrical_context`, `chars_extracted` and a raw `text_sample` per PDF, which
settles it: volts and amps present with watts absent means the manuals state a
supply spec and this path will not yield kW; garbled glyphs in the sample means
the miss is ours.

**Do not widen the plausibility band to get numbers out of this.** Run 1's only
readings were 200W / 125W / 300W per-emitter panel wattages on one page. They are
real and precise and none is the unit's rating; the band is what stopped them.

**Still untested on real data:** the spec-plate-over-marketing tiering (no
spec_plate hit in 278 pages) and the recommendation-vs-rating rule (nothing real
rejected). Both are proven only against the constructed PDF in the suite.
