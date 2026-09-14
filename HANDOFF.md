# HANDOFF

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
