# Social Autoposter

Version: v1.2

Builds a machine that researches → renders → posts on a cadence, unattended. This is a specialization of `build-loop`: its DEFINE ≈ Phase 0, PROVE ≈ Phase 3, DEPLOY/LAUNCH ≈ Phase 7. All meta-rules, tiers, Slack protocol, and the learning loop come from `agent-harness` — read that first.

**Architecture principle that governs every step:** the LLM writes copy and nothing else. Selection, counting, dedup, gating, and posting are CODE — cheap, deterministic, scale-proof. Keep the model surface tiny: one call per cycle, never per-item.

Surfaces: **Code** = Claude Code (default, incl. browser). **Design** = Claude Design (brand + card templates, exported to repo). **Human** = 🔴.

## DEFINE

### 1. Intake brief (Human, 🔴)
Filled before agent involvement, stored in `CLAUDE.md`:
1. **Concept in one sentence** — what it posts and why anyone follows. Content needs a "social job" to spread — pick the mechanism (broadcast: feed→posts, or engagement: reads/reacts), not just the topic.
2. **Niche + audience** — who follows this and what they get.
3. **Platforms + accounts** — which, and whether accounts exist.
4. **Cadence** — a config **map keyed by platform**, never a single scalar and never hardcoded. Give each platform a stated role (search discovery / cold reach / click-driving); different jobs imply different cadences, formats and sizes.
5. **Data source** — feed/API/site, auth needs, update frequency — or "curated bank".
6. **Brand priors** — name candidates, voice (loud/dry/friendly), colors/fonts, hard nos — or "Design to propose".
7. **Tooling status** — Blotato paid plan active? Anthropic key? Private repo?
8. **Cost ceiling** — $/month all-in, plus **cost per post broken out by source** (model tokens, render credits, API credits). Measure before choosing: paid rendering can produce worse, more off-brand output than free local rendering.
8b. **Content-quality floor** — what makes a post in this niche worth publishing, stated concretely enough to become a validator rule in step 11b.
9. **Review period** — how long every post is human-approved before autonomy (default 2 weeks).
10. **Kill-switch criteria** — what re-gates autonomy (e.g., any malformed post, factual error, platform warning).

Done when: brief in `CLAUDE.md`. Blocking TBDs halt RESEARCH.

### 2. Governance files (Code, 🟡)
Land `CLAUDE.md` (harness config block + brief), `RUNLOG.md`, `LEARNINGS.md`, `HANDOFF.md` in a **private repo**. Done when: committed.

## RESEARCH

**Absence is not a value.** Add a narrow lint: no `.get(x)` on a key that can legitimately be missing without an explicit branch. Keep it narrow — a lint with 157 findings is one nobody reads; the useful version had 12, all real.

This is the single most common bug class in builds of this kind — one project hit it **ten times**. A default scoring absent tokens as maximally common; an HTTP 429 read as a dead link, reporting "0.0%"; a lookup on `None` blocking valid rows as "did not return 200"; a cwd-relative cache returning `None` for every value; a loader returning a dict while the caller read the environment; a credential's *presence* treated as its *validity*; a report keyed to local date while timestamps were UTC.

Every one reported itself as a finding about the world rather than a bug. **When a result is surprising, precise and confident — "exactly 0.0%", "no results found", "the file does not exist" — verify the measurement before reporting the finding.** And diagnose your own path before blaming the input.

### 3. Niche research (Code, 🟢)
Research what performs in the niche: formats, hooks, cadence norms. Aim at the intersection of trending ∩ debatable ∩ durable — trending alone decays, durable alone bores. Done when: research brief produced.

### 4. Material bank OR feed spec OR data layer (Code + Human, 🟡)
Assemble the raw reference bank, or spec the data feed (source, auth, update frequency). **Verify every fact and business status** — stale facts read as bot and burn the account's credibility. Done when: material assembled with risky items flagged, or feed spec confirmed.

**Third option — a data layer.** A curated bank exhausts and a feed goes stale. Parsing structured sources into a cached fact layer does neither, and it is what lets a build run indefinitely with no original content.

Parse CSV/JSON endpoints and public APIs into a cache with fetch dates and per-field provenance. Prefer machine-readable endpoints over scraping, and **never use an LLM summarizer to source a number** — it reads prose, writes prose, and silently discards tables. On one build a summarizer reported "no measured numbers" about a page holding a 75-row cost table.

Free no-key public APIs are unusually high-yield: government recall, safety, scholarly, trial and weather data are all open and almost never used as content.

Then write **probes** — deterministic analytical passes over the layer — in five families: disclosure gaps, distributions, concentration, trends, contradictions. Each emits a claim, figures, dataset, fetch date, n, and a notability score. **Findings are single-use** and never recycle, so check the library can sustain the intended cadence before committing to it.

A finding's own claim text is validated copy like any other — a probe can print an ungrounded numeral just as a model can.

## DESIGN

### 5. Brand (Design + Human, 🟡)
Name, voice, visual identity — built in **Claude Design**, reviewed on screen. This is the highest-leverage hour of the build; do NOT automate it and do NOT rush it. Done when: brand kit approved and exported into the repo (assets + a written voice guide the caption function will consume).

### 6. Card templates (Design builds → Code integrates, 🟡)
One HTML template per post type with `{{slots}}`, designed in Claude Design, exported to the repo, wired for rendering by Code. Hard-won constraints:
- Wait for `document.fonts.ready` before screenshotting.
- Auto-fit long text (overflow is the #1 visual failure).
- Native 1080×1080 render — no scaling.
- **Self-host fonts** — CDN fonts fail in CI.
Code loads each template in its browser and screenshots it for the 🟡 REVIEW. Done when: templates render clean with real-length content, human eyeballs approve.

## PROVE — every dependency in isolation, BEFORE building on it

### 7. Confirm tooling — credential preflight (Code checks, Human supplies, 🔴)
Blotato **paid** plan active (API is paid-only), Anthropic key, private repo.

Build `scripts/preflight.py` before anything depends on a credential. It reports every one as **PRESENT / ABSENT / INVALID** — never merely present. For each: print character length (never the value), assert the expected prefix and shape, **make one authenticated live call**, and print the exact error on failure. Print the resolved absolute path of every file read, and run it from a subdirectory as well as the repo root.

**Before reporting a credential missing, the agent verifies its own loader:** resolve paths from `__file__`, never the cwd; confirm the loader populates the environment rather than returning a dict; glob for appended extensions (`.env.txt`); check parent and home directories for a stray copy; search for duplicate keys within the file.

Traps that cost real rounds:
- **`.env.txt`** — GUI editors append `.txt` and the file browser hides it. Add `*.env.txt` to `.gitignore` and have preflight glob for it.
- **Wrong directory** — `>>` run from `~` creates a second `.env` that silently absorbs every edit. Print `pwd`; check `~`.
- **Placeholder values** — never tell the human to edit `.env.example`; always `printf` a fresh `.env`. A placeholder is PRESENT and INVALID.
- **Identity-linked keys** may require an extra header (e.g. workspace id). Handle that 400 with a specific diagnostic, not a generic auth failure.
- **Trailing `=`** in keys — quote the value when appending so padding survives.
- **Spaces in the project path** — audit for unquoted shell interpolation and string-built paths.

Give the human copy-paste commands that append with `>>`, quote the value, and verify with `awk -F= 'NF{print $1": "length($2)" chars"}'` — never `cat`, which prints secrets.

Done when: preflight reports every credential VALID via a live call, and secrets never appear in chat.

### 8. Prove the data source (Code, 🟢)
Tiny script pulls the feed once and prints the result. Done when: source returns clean data, output shown. If it fails: fix or rescope HERE — nothing downstream gets built on an unproven source.

### 8b. Prove the transport, not just the endpoint (Code, 🟢)
A dependency can be *connected* and still unusable. Before building on any tool, assert the **shape** you will actually send:

- If the tool exposes a schema, confirm it is populated. A degraded `{"type":"object"}` with no properties will silently coerce arrays to strings and every call will fail at the last step.
- Make one real call with the exact argument types the build will use, especially arrays and nested objects.
- Record which transport was proven. A session-scoped tool and a REST endpoint are different transports with different failure modes, and proving one says nothing about the other.

Two builds were lost to this: a REST key that authenticated but was rejected by plan tier, and a session whose tool schema came back untyped. Both looked like connectivity problems and neither was.

**When the transport fails, the artefact survives.** If the conductor emits a complete argument set (step 16), a failed batch can be relayed through a different session rather than regenerated. Design for that.

Done when: the exact call shape succeeds, and the proven transport is named in `CLAUDE.md`.

### 9. Prove posting (Code, 🟡)
Media upload → post → **poll status for the real post-id** → capture it. Fail loud on any missing step.

**Prove the path the runner will actually use.** An MCP tool exists only inside an agent session; a cron has none, so a proof through MCP does not transfer. Prove the REST path with a key. If both exist, build one `PostSpec` and assert they produce byte-identical payloads so they cannot drift. The same applies to any data source the cron depends on.

Done when: test post live via the runner's own path, id captured, test post deleted. This proves the whole posting path before any logic exists.

## BUILD-LOGIC

### 10. Selection + dedup (Code, 🟢)
Content selection and never-post-twice via a `seen-ids` state file. Select/count with CODE, not the LLM. Done when: selection correct on test fixtures, including exhaustion behavior (bank empty → halt loudly, don't repeat).

### 11. Caption generation (Code, 🟢)
The ONE place the model writes. One call per cycle. Consumes the voice guide from step 5. Done when: captions match brand voice on fixtures (🟡 spot-check).

## BUILD-OUTPUT

### 11b. Output validator (Code, 🟢) — build this BEFORE any generation logic
A code gate every post must pass before it can be scheduled. Proving that posting *works* (step 9) says nothing about whether the content is *fit to publish*; without this gate a machine publishes its own failure states.

Minimum rules — reject and halt if:
- text is empty, whitespace-only, or under a minimum length
- text matches an error pattern (`Error:|Failed to load|undefined|null|No response`)
- text exceeds the platform limit
- any per-platform required field is missing (for Pinterest: title, description, alt text, destination link)
- media is absent or its URL does not resolve

Then add rules for the niche's own failure modes. A build should expect to need several. Ones earned in practice: a rendered card whose body has no rows; a comparison card with no numeric values; filler headline patterns; **any numeral not present in the source data**; claims beyond their evidence tier; a share statistic without its denominator; a card whose claim and destination disagree.

**On failure: halt. Never publish a degraded version, never skip to keep the run alive.** Retry once at most, then halt.

Test against real historical failures where they exist, not only fixtures.

**The governing principle:** every content-quality problem is fixed by making it a code gate, never by instructing the model. "Be specific" in a prompt decays; "fewer than two numeric cells does not publish" does not. When the model wants a value the rule forbids, **supply the figure in code — never relax the rule.**

Done when: known-bad content is rejected, known-good passes, and the rules are unit-tested.

### 12. Render helper (Code, 🟢)
Fill template + screenshot. **Render at the platform's native aspect, per platform** — a single square size is wrong almost everywhere. Pinterest 2:3 (1000×1500), Instagram feed 4:5 (1080×1350), Stories and Reels 9:16 (1080×1920), Facebook 1080×1350 or 1200×630. Fail loud on wrong dimensions or zero-byte output.

**Auto-fit needs an ordering and a floor.** Concede in this order: headline size → body size **down to but never through a legibility floor** → drop trailing rows. Record what was dropped. Unbounded shrinking produces 8px table cells that pass every test and are unreadable.

**Evaluate at real browse width first** (~236px on Pinterest), full size second. Structure must read as a *shape* where text cannot.

Pin the browser version everywhere. Cards are screenshots; a different engine shapes text and breaks auto-fit lines differently, which makes local-vs-CI comparison meaningless. Self-host fonts — CDN fonts fail in CI — and verify each face actually loads rather than falling back.

Done when: renders real content at every target aspect without collision or overflow, and looks right at thumbnail size.

### 13. Post helper (Code, 🟡 one live test)
Chain upload → post → poll → capture id, reusing **one copy** of the capture logic from step 9. Done when: posts with image + captures id; test post deleted.

## ORCHESTRATE

### 14. Choose the scheduling architecture (Human + Code, 🔴)
**Two options. Pick deliberately — this is the decision that determines how much can go wrong.**

**A. Batch scheduling (default, strongly preferred).** Most posting platforms schedule natively: pass a future `scheduledTime` and the platform publishes from its own infrastructure. One session per week generates and hands over a full week. Nothing else runs. No cron, no runner, no browser on CI, no state persistence across ephemeral machines, no credential reachable by a daemon.

**B. Scheduled runner** (GitHub Actions cron calling the platform daily). Only when the platform has no native scheduling, or content must react to same-day inputs.

Option B has five failure surfaces that A does not: a daemon-reachable credential, browser install on the runner, state surviving ephemeral runners, cron/timezone handling, and the gate that decides when the cron may run. Each is a real cost. **Do not choose B for the feeling of being more automated** — A publishes just as unattended once scheduled.

Done when: the choice is recorded in `CLAUDE.md` with its reasoning.

### 15. State + idempotency (Code, 🟢)
JSON state, **atomic writes**. Absent file = cold start; **corrupt file = HALT** — never silently reinitialize.

**Batch builds need stronger idempotency than daily ones.** A double-fired daily run posts one extra item; a double-fired weekly batch creates a whole duplicate week. Before creating anything, list what the platform already has scheduled and skip any slot already filled.

**Mark content used only once it exists on the platform** — not at plan time. Planning against a working copy is right (a halted plan should leave nothing behind), but that means the real state is only written on confirmation. If that write is missing, the next batch reselects everything and nobody notices, because the run looks clean.

**Stamp used-content with the scheduled publish date, not today**, since cooldowns measure from publication.

Done when: state survives a simulated crash mid-write, and a re-run of a completed batch creates nothing.

### 16. The conductor (Code, 🟢)
Thin runbook chaining the proven scripts: plan → render → upload → validate → schedule → record → reconcile. No new logic in the conductor.

**Every judgement lives in the script, never in the agent.** Where a tool is only reachable from an agent session, the script still computes the full argument set and emits it; the agent relays precomputed arguments and nothing more. This keeps the LLM writing copy only, and it means a batch can be relayed through a different session if the tool fails in this one.

**Dedup across the whole batch, not per item.** Near-duplicate suppression that resets each day will happily put "X vs Y" and "Y vs X" in the same week, which reads as a bot. Filter the pool across the batch window.

**Narrow retries to the rejected items.** Regenerating the whole batch on a validator rejection hands the model fresh chances to break content that already passed — attempt 1 fails on item 3, attempt 2 fails on item 9, and it never converges. Re-request only what failed, and have the parser report *every* bad item rather than raising on the first.

Done when: a full cycle runs end-to-end on fixtures without posting.

### 17. Duplicate-post protection "D5" (Code, 🟢)
Breadcrumb committed **BEFORE** posting; next run halts if it finds one; cleared only after ids are captured. Post-then-crash = duplicate-forever without this. Enforce in CODE, not model prose. Done when: a simulated post-then-crash halts the next run.

## DEPLOY

### 18. Split verification across time (Code, 🟢)
With batch scheduling, posts go live days after they are created, so verification splits:

- **At schedule time:** assert the platform's returned time matches what was requested, and every required per-platform field was accepted.
- **At the next batch:** reconcile the prior window. Every scheduled post is either published with a URL, or failed with a reason. **A failure halts the new batch. So does absence** — an absent post is not proof of publication.

**Reconcile on ids only.** Platforms commonly re-host media on ingest and rewrite the URL. A reasonable-looking media comparison will then report every post in a clean week as broken — a confident, precise, wrong finding that resets the streak. Pin this with a test, not a comment.

Done when: reconciliation correctly classifies published, failed and absent.

### 19. Measurement (Code, 🟢) — wire this during PROVE, not after launch
**Confirm the metric source actually returns data for the platforms being published to, before any content strategy depends on it.**

If a platform's reach cannot be measured, that is 🔴 *before* it is chosen as primary. Reach you cannot measure is reach you cannot improve, and discovering this after launch invalidates the channel choice.

Check that third-party schedulers actually report the platforms they publish to — coverage is often partial, and the gap is rarely advertised. Verify with a real published post rather than documentation.

Weekly: pull reach and saves, join to post id, report into the digest. Done when: a real published post's metrics are retrieved end to end.

## LAUNCH

### 20. Supervised-automatic phase (Machine runs, Human reviews exceptions, 🟡)
Approving every post by hand does not scale — at 2 posts/day a two-week review is 28 approvals, and it is the largest human cost in this SOP.

Run in **halt-on-failure** mode:
- any validator rejection surviving its narrowed retry → halt, schedule nothing, report
- any reconciliation failure or absence → halt, report
- any uncaught exception → halt, report
- it must **never** skip, degrade, or partially schedule to keep running. A short week is worse than no week — it hides the failure.

The human reviews **halts and the digest**, not every post.

Where a build has a low-frequency high-stakes track alongside a high-frequency one, keep the high-stakes track human-reviewed while the other runs unattended.

**The gate to full autonomy is N consecutive clean cycles**, not a calendar period. **Make sure the gate is reachable by the mechanism it gates** — a streak that only advances on published days cannot be reached while publishing is disabled. That circularity turns a supervision policy into a chore.

**Every edit you do make is training data** — fold recurring edits into the voice guide, or better into a validator rule (`RUNLOG.md`; 3+ repeats = a `LEARNINGS.md` candidate).

Done when: the streak target is met with zero broken posts and zero manual interventions.

### 21. Steady state (Human triggers or glances, machine runs)
Under batch scheduling the recurring human step is one trigger per cycle, roughly ten minutes, and only because session-scoped tools need a session. Document that procedure at the top of `CLAUDE.md` and `HANDOFF.md`. Nothing needs to be open between cycles.

Keep non-publishing CI useful regardless: tests, lint, font checks, and data refresh on a schedule, with publishing gated to explicit dispatch.

Keep the kill-switch criteria active; any trigger re-gates to supervised-automatic and resets the streak. The machine may never enable itself, raise its own cadence, add a platform, or modify a validator — those stay human edits. The machine commits to main itself, so **always `git pull` before any manual push**, and never force-push without comparing histories first.

Done when: running on cycle, confirmed healthy, with reconciliation clean.

## Failure paths — quick reference

- Feed proof fails (8) → fix/rescope before anything downstream.
- Posting proof fails (9) → plan/keys/permissions checked before logic work; confirm the runner's path, not just the session's.
- Credential INVALID at preflight (7) → verify the loader and the file path before reporting it missing.
- Validator rejects (11b) → retry once, then halt. Never publish a degraded version.
- Transport shape wrong (8b) → stop; do not retry the calls. Relay the emitted arguments through a working transport instead.
- Corrupt state (15) → HALT + 🔴 BLOCKED to Slack; never silent reinit.
- D5 breadcrumb found (17) → run halts; human clears after investigating.
- Reconciliation finds a failure or an absence (18) → halt the next batch.
- CI red (17+) → 🔴 BLOCKED with the failing step + log excerpt; no retry-spam.
- Kill-switch trigger post-autonomy (20) → auto re-gate to review mode + 🔴 BLOCKED.
- Cost at 80% / 100% of ceiling → flag / STOP (harness rule).

### Changelog
- v1.2: Architecture and transport, from the same build. **Step 14 now makes the scheduling architecture an explicit choice, defaulting to batch scheduling** via the platform's own scheduler — it removes five failure surfaces a daily runner carries (a daemon-reachable credential, a browser on CI, state across ephemeral runners, cron/timezone handling, and the gate deciding when the cron may run), and publishes just as unattended. **Added step 8b, prove the transport not just the endpoint** — two rounds were lost to a REST key rejected by plan tier and a session whose tool schema came back untyped, both of which looked like connectivity. **Added step 19, measurement, wired during PROVE** — one build shipped with its primary channel unmeasurable. **Step 18 splits verification across time** for scheduled posts and reconciles on ids only, since platforms rewrite media URLs on ingest. Also: a data layer with probes as a third content model; the missing-value lint in governance after that bug class appeared ten times; per-platform render aspects with an auto-fit floor and a thumbnail test; batch-strength idempotency; batch-wide dedup; and narrowed retries.
- v1.1: From a full production build. **Added step 11b, the output validator** — the SOP proved that posting worked but never that content was fit to publish; the account this build inherited had published 81 broken posts out of 300 (blank pins averaged 3 impressions against 106 for real ones). **Rewrote step 7 as a credential preflight** reporting PRESENT/ABSENT/INVALID via a live call, after credential problems consumed six rounds — a `.txt` extension hidden by the file browser, appends landing in the home directory, a placeholder left in the file, an identity-linked key needing an extra header. **Replaced per-post review (19) with supervised-automatic operation**, halting on failure and gated on a zero-broken streak rather than a calendar period, and noted the circularity where a streak cannot advance while publishing is disabled. Step 20 now follows from it. Also: cadence is a per-platform map rather than one scalar; step 9 proves the runner's own path rather than a session-only MCP tool; the brief gains a content-quality floor and per-source cost tracking.
- v1.0: Created from the 21-step SOP sheet; routed brand/templates to Claude Design, added intake brief with kill-switch criteria, tiers, failure paths, CI runlog append + Slack webhook reporting, and enforced re-gate on kill-switch.
