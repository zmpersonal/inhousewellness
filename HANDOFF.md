# HANDOFF

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
