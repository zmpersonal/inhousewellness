# InHouse Wellness Blog Engine

Automated pipeline that researches, writes, self-reviews and publishes 3–5 SEO/AI-search-optimized articles per week to inhousewellness.com (Shopify), on the correct blog, in the house format.

## Harness Config
- Harness: agent-harness v1.0 (`docs/HARNESS.md`). This project runs under it; read it at the start of every session.
- Active SOP: build-loop v1.0 (`docs/BUILD-LOOP.md`). Batch/validator/idempotency lessons are borrowed from `docs/reference/autoposter-playbook.md` (reference only; it's written for social posting).
- Slack channel: `#blog-engine` (TBD-nonblocking: confirm the channel exists; CI posts via the `SLACK_WEBHOOK_URL` secret).
- Cost ceiling: **TBD-blocking for R6 onward** (no paid model calls in CI until set). Flag at 80%, STOP at 100%.
- Review cadence: retro every 4 rounds, or on any validated learning.
- Autonomy: `publishing_enabled` lives in `config/control.yaml`. **The machine may set it to `false` (kill switch) but never to `true`.**
- Tier overrides (human-approved only): none yet.
- Governing docs:
  - `docs/BLUEPRINT.md`: the full design; section numbers are cited as §x.y.
  - `spec/house-style.md`: the article spec.
  - `docs/HARNESS.md` and `docs/BUILD-LOOP.md`: process.

## Session start (every time)
1. Read this file, then `HANDOFF.md`, then the last 3 entries of `RUNLOG.md`, then `LEARNINGS.md`.
2. Read the BLUEPRINT sections relevant to the current round.
3. Report actual state before changing anything (Meta-Rule 1).
4. End every round with a `RUNLOG.md` entry and an overwritten `HANDOFF.md` (Meta-Rules 12–13).

## Project Brief (intake, build-loop Phase 0)
1. **Problem:** InHouse needs a steady flow of high-quality, conversion-aware articles that rank in Google and get cited by AI assistants, without hand-producing each one.
2. **North-star metric:** TBD-blocking for launch. The owner will set it (e.g. indexed articles + impressions/clicks by day 90, or blog-entrance revenue).
3. **Deadline:** none stated.
4. **Cost ceiling:** TBD-blocking for R6+. See Harness Config.
5. **Existing assets:**
   - Shopify store inhousewellness.com
   - this GitHub repo
   - owner's claude.ai connectors (Ahrefs, Semrush, Ubersuggest, Keyword Tool, HYPD for GSC/GA4, Promptwatch, Slack, Shopify)
   - the published article `/blogs/saunas/what-is-a-german-sauna` (golden reference)
6. **Deploy target:**
   - this repo; the engine lives in `blog-engine/`
   - GitHub Actions workflows **must** live at the repo root `.github/workflows/`, using `working-directory: blog-engine`
   - Shopify production; tests use unpublished articles that are deleted afterward
7. **Not in v1:**
   - refreshing old posts, or editing old posts to add links
   - image generation
   - social distribution
   - Cloudflare
   - competitor product reviews
   - translation
8. **Risk tolerance:**
   - no human pre-approval; Claude reviews before publish, the owner reviews after (BLUEPRINT §4.10)
   - the owner reads the first real batch once before launch
   - 3/week for the first 3 weeks; cadence rises only by the owner's edit
9. **Secrets inventory (names only; values never in chat, code, logs or Slack):**
   - `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`: Dev Dashboard custom app, client-credentials grant, short-lived tokens fetched per run
   - `ANTHROPIC_API_KEY`
   - `GSC_SERVICE_ACCOUNT_JSON`
   - `SLACK_WEBHOOK_URL`
10. **Brand priors:** `spec/house-style.md` (espresso/cream/gold palette, no purple/blue accents, useful-first luxury voice).

## Locked decisions
| # | Decision | Where |
|---|---|---|
| D1 | No human pre-approval. Code validator + in-depth separate-context Claude review gate every article. Owner reviews post-publish; one-command correct/unpublish; automatic kill switch. | §4.10, §4.12 |
| D2 | Keywords come from a monthly interactive `/refill-bank` session using the owner's connectors, which also snapshots each keyword's top-10 SERP. CI never calls keyword tools. | §4.1, §4.11 |
| D3 | JSON-LD in article metafield `custom.jsonld`, printed by a theme snippet. No `<script>` in article bodies. | §4.8 |
| D7 | Health/YMYL: no separate human gate; tier-A sources are required for health claims. | §4.12, §4.14 |
| — | Every article is built from a SERP teardown with measurable beat criteria and a saved research dossier. | §4.11, §4.14 |

## Open decisions (ask the owner; don't assume)
- **D4 Author byline:** is "Taylor Reed" a real person with statable credentials, or should the byline be "InHouse Wellness Editorial Team"? Blocks R5.
- **D5 Routing:** what belongs in `/blogs/fire` and `/blogs/institute`? Blocks R3.
- **D6 Featured images:** catalog product images (recommended) vs. Unsplash vs. a mix. Blocks R10.
- **LLM transport in CI:** Anthropic Python SDK called from the pipeline scripts (proposed; keeps the model surface small and structured), vs. Claude Code headless. Confirm in R1b.

## Guardrails (locked; change only via approved retro)
1. **The model writes; code decides.** Selection, routing, URLs, specs, rendering, link attributes, schema, validation, publishing, scheduling and state are deterministic code. Fix quality problems with code gates, never with prompt wording alone.
2. **Cadence is a ceiling, not a quota.** Fewer articles beat weak ones. A HELD article never publishes in degraded form.
3. **Every claim is sourced or removed.** Nothing about InHouse products appears unless it's in the Shopify site index.
4. **No fabricated experience, testing, credentials, reviews or ratings.**
5. **Human-only:**
   - secrets
   - theme publishing
   - merges to the default branch during the build phase
   - setting `publishing_enabled: true`
   - raising cadence
   - editing `config/thresholds.yaml`, `config/control.yaml` (except the kill-switch direction), `spec/`, `docs/HARNESS.md`, `docs/BUILD-LOOP.md`
6. **Secrets only in GitHub Actions secrets or a local `.env`** (gitignored). Credential checks print name + length + PRESENT/ABSENT/INVALID, never values.
7. **Withhold beats guess.** A surprising, precise, confident result ("0 results", "exactly 0.0%", "file does not exist") gets its measurement verified before it's reported.
8. **Repo safety:** before any push, confirm this repo is not auto-deploying a Shopify theme from the branch being pushed to.

## Stack & conventions (proposed; confirm or amend in R1a)
- **Language:** Python 3.12, managed with `uv`.
- **Libraries:** `httpx`, `pydantic` v2 (every stage's input/output is a model), `jinja2`, `pyyaml`, `selectolax` or `beautifulsoup4`, `textstat`, `pytest`.
- **Layout (target):**
  ```
  blog-engine/
    engine/        stages: site_index, select, teardown, research, brief, write, render, validate, review, publish, reconcile, digest
    templates/     jinja templates per article type
    config/        routing, cadence, thresholds, models, control, tags (human-owned unless noted)
    data/          keywords.csv, state.json (atomic writes; corrupt = HALT)
    research/<handle>/  dossier.json, brief.json, article.json, review.json, rendered.html
    tests/         fixtures/golden (German sauna), fixtures/bad (seeded failures)
    scripts/       preflight.py, one-off proofs
    .claude/commands/  refill-bank.md (built in R3)
  ```
- **Git:** one branch per round, `be/r<N>-<slug>`. Small, labelled commits. No force-push.
- **Timezone:** America/Chicago for schedules; store UTC timestamps.
- **Shopify:** GraphQL Admin API, pinned version in `config/shopify.yaml`.

## Round status
| Round | Objective | Status |
|---|---|---|
| Planning | Blueprint v0.4 (done in claude.ai, Sept 18 2026) | done |
| R1a | Orient + land governance | **next** |
| R1b | Preflight | pending |
| R2–R11, Launch | See BLUEPRINT §7 | pending |
