# Constant audit — which constants inherit the thin-satellite assumption

**Date:** 2026-09-02 (Round 5, item 0)
**Trigger:** the 70% INH floor and the 15% per-domain cap were both calibrated
against "the satellites are thin link pages." The full-network sweep found 1,908
indexed pages across the ten domains, disproving it. Both constants then produced
wrong behaviour. This is the sweep for others that inherit the same premise.

**Nothing below is changed unilaterally.** The two decided items are marked; the
rest are 🟡 for the user.

---

## Decided this round

| Constant | Was | Now | Why |
|---|---|---|---|
| `SATELLITE_MAX_SHARE` | 0.15 | **0.35** | The cap measured the wrong thing. A 90-model spec database with published methodology is not a spam destination. |
| `PER_URL_MAX_PINS` | — | **4** / 30 days | The real risk: many pins at one URL, which Pinterest downranks. |

## 🟡 Also inherits the assumption — user's call

### 1. `INH_MIN_SHARE = 0.40` (`src/destinations.py`)
The floor exists for two reasons that have now come apart. The **spam-pattern**
rationale is dead — these are real properties. The **commercial** rationale
survives: INH is the store, and buying-intent traffic belongs there.

Currently non-binding (measured 41.2% against a 40% floor), so it costs nothing
today. But it is calibrated against a premise that no longer holds, and it will
bind again as batch 03+ adds satellite-destined rows.
**Recommendation:** keep the number, rewrite the rationale as commercial-intent
routing rather than spam avoidance, and re-derive it from what fraction of the
queue is genuinely commercial — not from a distrust of satellites.

### 2. `CLUSTERS` — one domain per cluster (`src/destinations.py`)
Each of the 11 clusters maps to exactly one satellite domain. That is a
thin-satellite shape: it assumes each domain is a single-purpose page.
Reality: healthresearchdatabase has **842** pages, infinitesauna 197,
saunasfactorydirect 173, outdoorsteamsauna 138, homenhealthy 136, BHIS 101.
A cluster should map to a *set* of candidate pages ranked by match, which is
what `alt_urls` now does ad hoc inside the router.
**Recommendation:** retire the 1:1 map in favour of corpus matching within a
preferred domain. Highest-value item on this list.

### 3. `data/satellite-destinations.json` — 12 URLs across 10 domains
Built when the only usable page per satellite was the one that linked back to
INH. That constraint was itself a thin-satellite artifact. With a per-URL cap of
4, twelve URLs support at most 48 pins across the whole network.
**Recommendation:** generate destinations from the corpus index rather than a
hand-curated list; keep the file only as the verified-allow-list seed.

### 4. `INTERACTIVE_ASSETS` — 3 assets
Assumed the satellites had a handful of useful pages. The sweep found many more
tools: `arcticsoak.com/calculators/ice/` and `/chiller/`,
`commercialinfraredsauna.com/calculators/roi/`, `tubsandsaunas.com/cost-calculator/`,
`outdoorsteamsauna.com/heater-sizing/`, `infinitesauna.com/compare/`,
`outdoorsteamsauna.com/climate-index/`.
**Recommendation:** expand the asset list; several are stronger save-and-share
candidates than what is routed today.

### 5. `MIN_N_FOR_DOMAIN_CAP` — was hardcoded 25
Derived from the old 8% cap and silently outlived two revisions of it. **Fixed
this round** to compute from the cap (`1/cap + 1`), so it can no longer drift.
Flagged because the failure mode — a derived constant frozen as a literal — is
worth checking for elsewhere.

## Audited and NOT inheriting

`MATCH_THRESHOLD` 0.40, `STRONG_MATCH` 0.62, `RARE_TOKEN_PENALTY` 0.45 —
calibrated on match quality against real pairs, independent of who owns the page.
`MIN_TEXT_CHARS`, `PLATFORM_TEXT_LIMIT/SOFT_MAX`, `PIN_*` bounds — platform facts.
`MIN_SEGMENT_POSTS` 30, `REVERT_AFTER_DAYS` 14, `REQUIRED_CLEAN_DAYS` 14 —
statistical/governance, unrelated.
`MAX_PER_DAY` 6, `MIN_REPOST_DAYS` 120, `MAX_RETRIES` 1, `XFADE` 0.4 — unrelated.
`ALLOWED_LINK_HOSTS` — an allow-list to stop arbitrary offsite links; that
rationale survives independently of how substantive the satellites are.

## Removed as dead code this round

`SatelliteRotator` and `plan_destinations` (56 lines) — round-robin machinery
built to spread links thinly across domains, superseded by `route()`.
`PER_DOMAIN_COOLDOWN_POSTS = 6` went with them; the per-URL cap is the correct
expression of that intent.
