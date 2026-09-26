# Build Loop

Version: v1.0

The generic idea→launch loop. Domain-specific playbooks (e.g., `social-autoposter`) specialize this loop; the shared rules live in `agent-harness` — read that skill first, then this one, then the project's `CLAUDE.md`, `RUNLOG.md`, and `HANDOFF.md`.

Surfaces: **Code** = Claude Code (default, includes browser verification). **Design** = Claude Design (visual artifacts, exported into the repo). **Human** = 🔴 steps. Tiers (🔴🟡🟢) are defined in the harness.

## Phase 0 — Idea Intake

The intake brief is filled by the human BEFORE agent involvement. The agent's clarifying questions are only as good as its guesses about what matters; a fixed brief removes the guessing. Store the completed brief in `CLAUDE.md` under Project Brief.

### 0.1 Intake brief (Human, 🔴)
The human answers, in writing:
1. **Problem & who has it** — 1–2 sentences.
2. **North-star metric** — with a number ("50 signups in month 1", not "growth").
3. **Hard deadline** — date or "none".
4. **Cost ceiling** — $/month, all-in (hosting, APIs, model calls). This becomes the enforced ceiling in `CLAUDE.md`.
5. **Existing assets** — repo, domain, data sources, accounts, prior art. Links/paths.
6. **Deploy target** — where this runs (host, platform) and staging vs. prod shape if known.
7. **Explicitly NOT in v1** — the out-of-scope list.
8. **Risk tolerance** — how long in supervised/review mode before any autonomy; which step types may be delegated to 🟢 and after how many clean rounds.
9. **Secrets inventory** — which keys/accounts exist, where they live. Names only — never values (harness Meta-Rule 4).
10. **Brand priors** — voice, colors, hard nos, or "Design to propose".

Done when: brief written into `CLAUDE.md`. If it fails (human can't answer a line): mark the line `TBD-blocking` or `TBD-nonblocking`; any `TBD-blocking` line halts Phase 1.

### 0.2 Gap questions (Code, 🟢)
Agent reads the brief and asks 3–6 questions that fill *gaps in the brief only* — scope edges, success-metric ambiguity, constraint conflicts. Done when: scope + north-star agreed. If answers contradict the brief: update the brief, don't hold two versions.

### 0.3 Reconcile against reality (Code, 🟢)
Agent names what's genuinely new vs. what conflicts with existing plans/data/tools; surfaces the 3–5 decisions that actually change the build. Done when: decision list exists and every item is answered (🟡 per decision). If unresolvable in-session: 🔴 BLOCKED to Slack, batched.

## Phase 1 — Plan

### 1.1 Draft the build outline (Code, 🟡)
Sequenced, phased plan — each phase one prompt-able round (harness Meta-Rule 2) — folding in all brief requirements; flags dependencies and blockers. Human approves/trims/reorders. Done when: written phased plan approved.

### 1.2 Identify gates (Code, 🟡)
Define launch gates (e.g., Gate 1 = content live, Gate 2 = full app) and what blocks each. Done when: gates + blockers documented and confirmed.

### 1.3 Define guardrails (Code, 🔴 approval)
Lock non-negotiables: honesty rules, brand, the cost ceiling from the brief, what's human-owned, verification standard. Done when: guardrail section committed to `CLAUDE.md`. Guardrails are governance — after this point they change only via retro proposal.

## Phase 2 — Orient

### 2.1 Ground in reality (Code, 🟢)
Before building: read the actual repo/environment/data and REPORT current state. Never assume. Done when: honest state-of-the-world report delivered; human has reviewed for surprises. If reality contradicts the plan: back to 1.1 with a diff, not a silent patch.

### 2.2 Land governance (Code, 🟡)
Create/commit `CLAUDE.md` (with harness config block), `RUNLOG.md`, `LEARNINGS.md`, `HANDOFF.md` so every later step runs under the rules. Done when: files in repo on main.

### 2.3 Establish deploy path (Code + Human, 🟡)
Confirm how deploys actually happen (staging vs prod, branch vs auto-deploy); fix if unwired. Done when: a trivial change demonstrably reaches staging. If the path is broken: fixing it becomes the next round's single objective — nothing else builds on an unverified deploy path.

## Phase 3 — De-risk Data

### 3.1 Verify data exists & granularity (Code, 🟢 verify / 🟡 rescope)
For any data-driven feature: confirm the data is real, at the claimed granularity, before building on it (harness Meta-Rule 5). Done when: granularity confirmed with a real pull, or the feature is honestly rescoped (🟡 decision). If the data doesn't exist: the feature does not get built on hope — rescope or cut.

### 3.2 Wire feeds, honesty-first (Code, 🟡 per feed)
Ingest with source + timestamp + stale/error state on every reading; withhold rather than guess; no fake/sample data presented as fact. Done when: feeds live with provenance, approved feed-by-feed.

## Phase 4 — Build (repeat per round)

### 4.1 Build in sequenced rounds (Code, 🟡 scope; work itself 🟢)
One round = one objective + explicit out-of-scope, written with the harness Prompt Skeleton. Work on a branch; nothing merged/deployed without approval. Visual/brand artifacts within a round route to **Design**, exported into the branch. Done when: round scoped, approved, started.

### 4.2 Surface-don't-assume (Code, 🔴 on trigger)
When a step conflicts with a rule/KPI/data limit: STOP, flag with options + recommendation (🔴 BLOCKED if human absent). Done when: conflict resolved before proceeding. Never proceed on a guess — a wrong guess here is the most expensive failure mode in the loop.

### 4.3 Human-owned steps (Human, 🔴)
Secrets, DNS, prod-DB migrations, billing, PII/consent. Agent stubs + documents; human executes. Done when: secret set / migration applied / etc., confirmed.

## Phase 5 — Verify (every round)

### 5.1 Render-side verification (Code w/ browser, 🟢)
Prove it WORKS: load the real build/render in the browser, screenshot rendered states, assert the specific behaviors. A green build is not proof. Done when: behavior proven with artifacts (screenshots, run output) attached to the round. If it fails: round is not done — fix or flag; never hand a failing round to review.

### 5.2 Assertion replay (Code, 🟢)
Re-run the full prior assertion suite against every change. Done when: all prior assertions pass. Any prior assertion flipping to fail **fails this round** — no partial merge.

### 5.3 Full sweep (Code, 🟢)
build + typecheck + content-check + link-check + deploy dry-run + determinism. Done when: sweep clean, results in the round digest.

## Phase 6 — Review & Merge

### 6.1 Pre-verified human review (Code pre-verify 🟢 → Human 🔴)
Agent posts 🟡 REVIEW to Slack (or in-session): staging URL, screenshots from its own browser pass, the 2–3 things to check. Human reviews the actual rendered output and gives visual/UX sign-off — the agent's browser pass reduces the human's work; it does not replace the sign-off (harness Meta-Rule 8). Done when: approved or changes requested.

### 6.2 Honesty gate (Code + Human, 🟡)
Confirm nothing overclaims, no unbuilt feature is promised in copy, no withheld-state reads as an error. Done when: copy matches reality, confirmed.

### 6.3 Merge (Code, 🔴 approval)
Merge to main only after approval; human applies any migration in order. Done when: merged + deployed to staging. Then append the round's `RUNLOG.md` entry and post the ⚪ FYI digest (harness Meta-Rule 12).

## Phase 7 — Launch

### 7.1 Final staging walk-through (Code pre-walk 🟢 → Human 🔴)
Agent walks critical paths in its browser first and reports; human then clicks through the real thing end-to-end (signup, login, notifications — the paths that hurt if broken). Done when: all critical paths verified by the human. If any path fails: launch halts, failure becomes the next round.

### 7.2 Set production secrets (Human, 🔴)
All secrets as SECRET type — never Text, never in chat/code/Slack; revoke anything ever pasted. Done when: secrets set, none exposed.

### 7.3 Cutover (Human, 🔴)
DNS / go-live; clean up old records; leave mail/DNS records intact. Done when: live on the real domain, HTTPS valid. Rollback plan stated BEFORE cutover (what gets reverted, how fast).

### 7.4 Post-launch checks (Code checks 🟢 → Human confirms 🔴)
Verify domain serves, mail still delivers, notifications fire, old site gone. Done when: human confirms launch. Post ⚪ FYI launch digest.

## Phase 8 — Iterate

### 8.1 Write handoff (Code, 🟢)
Update `HANDOFF.md` so a fresh session continues seamlessly. Done when: handoff current.

### 8.2 Log follow-ups (Code, 🟢)
Record deferred items as documented "seams" with reasoning, priority, what unblocks them. Done when: backlog captured; human prioritizes (🟡).

### 8.3 Retro check (Code, 🟡 when triggered)
Check the harness Learning Loop triggers (validated learning, cadence, or human request). Run the retro per the harness procedure if due. Done when: retro run or explicitly not due.

### 8.4 Next round (Human, 🔴)
Human chooses the next priority; loop to Phase 1 (or 4 for an in-plan round). Done when: new cycle started.

## Failure paths — quick reference

- Intake line unanswerable → `TBD`, blocking TBDs halt planning.
- Reality contradicts plan (2.1) → re-plan with a diff, never silently patch.
- Deploy path broken (2.3) → fix becomes the sole next objective.
- Data missing/coarser than claimed (3.1) → rescope or cut; never build on hope.
- Rule conflict mid-build (4.2) → STOP, 🔴 BLOCKED with options + recommendation.
- Assertion regression (5.2) → round fails; no partial merge.
- Cost at 80% of ceiling → flag in FYI; at 100% → STOP all paid actions, 🔴 BLOCKED.
- Critical path fails at 7.1 → launch halts; failure is the next round.

### Changelog
- v1.0: Created from the Phase 0–8 SOP sheet; added intake brief, surface routing (Code/Design/Human), tiers, per-step failure paths, browser pre-verification at 5.1/6.1/7.1, and harness integration (runlog, retro, Slack).
