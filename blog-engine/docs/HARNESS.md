# Agent Harness

Every project round runs under this harness. It exists because a real project taught these lessons the hard way: assumptions caused every major miss, a green build shipped an invisible bug, and silent guesses cost more than blank states. The harness turns those lessons into standing rules so nobody has to remember them per-session.

Read this whole file at the start of any project session. Then read the project's `CLAUDE.md`, `RUNLOG.md`, and `LEARNINGS.md` (see File Conventions) before doing anything else.

## Surface Routing

Three executors. Route each step to the right one — never improvise a fourth.

| Surface | Owns | Notes |
|---|---|---|
| **Claude Code** | Default for everything: planning, research, all code, orchestration, CI, verification — including **browser-based verification** (loading staging URLs, screenshotting rendered output, checking against brand rules) | Code has a browser. Use it for first-pass visual verification instead of asking the human to eyeball everything. |
| **Claude Design** | Brand kits, visual identity, card/post templates, landing page mockups, any artifact whose primary job is to look right | Design produces the visual artifact; export it (HTML/assets) into the repo, where Claude Code wires it up. Design does not write application logic. |
| **Human** | Everything 🔴 (see Approval Tiers): secrets, DNS, prod-DB migrations, billing, PII/consent, merges, go-live, final aesthetic sign-off | The agent stubs and documents these steps; it never executes them. |

Handoff rule between surfaces: the artifact moves through the **repo**, never through chat. Design exports files → committed on a branch → Code integrates. No pasting rendered HTML into conversation as the source of truth.

## Approval Tiers

Every step in every SOP carries a tier. This is what lets the harness get lighter over time without getting reckless.

- 🔴 **Human-only.** Irreversible or trust-critical: secrets, DNS, production DB migrations, billing, PII/consent, merge to main, go-live, flipping any system to autonomous. The agent prepares, stubs, and documents; the human executes or explicitly approves.
- 🟡 **Human approves until delegated.** Judgment calls: round scoping, feed wiring, template approval, retro-proposed SOP changes. Human approves the first N times (N set in `CLAUDE.md`, default 3); after that the human may downgrade the step to 🟢 by updating `CLAUDE.md`. The agent never self-downgrades.
- 🟢 **Agent proceeds and reports.** Mechanical and reversible: sweeps, assertion replay, runlog entries, research, rendering to a branch. Results appear in the round-end FYI digest.

When in doubt about a step's tier, treat it as one tier stricter and flag the ambiguity in the round digest.

## Meta-Rules

These are non-negotiable. If a task instruction conflicts with a meta-rule, the meta-rule wins and the conflict gets surfaced.

1. **Read before acting.** No build step begins until the agent has read the real environment (repo, data, configs, runlog) and reported its actual state. Reconcile with what exists — do not clobber or rebuild.
2. **One round, one objective.** Each prompt does one thing, with explicit out-of-scope. Big rounds get a mid-point pause for review before they fan out.
3. **Human owns the irreversible.** Secrets, DNS, prod migrations, billing, PII/consent are executed by the human. The agent stubs and documents them.
4. **Secrets never touch chat, code, or Slack.** Keys, tokens, and webhook URLs go into a secret store as SECRET type only (`gh secret set`, env vars). Anything ever pasted into a conversation or channel is burned — revoke it immediately. Slack is a leak surface: a webhook URL posted "for review" is burned.
5. **Gate the data before the feature.** Confirm data exists at the claimed granularity before building on it. Rescope honestly if it doesn't. This is what prevents shipping false precision.
6. **Withhold beats guess.** When certainty isn't available, show nothing (honestly labeled) rather than a plausible wrong value.
7. **Verify what paints, not what compiles.** Proof is a real render/run plus replay of all prior assertions. "It builds" is never "it works."
8. **Agent pre-verifies visually; human owns final sign-off.** The agent uses the browser to load the real staging URL, screenshot rendered states, and check them against brand and honesty rules — attaching screenshots to the review request. The human still walks critical paths end-to-end and gives final aesthetic/go-live approval. Nothing goes live unseen by the human.
9. **Flag, don't assume.** Conflicts with rules, limits, or intent STOP the work and become a human decision — surfaced with options and a recommendation.
10. **Own mistakes out loud.** When the agent (or human) is wrong, correct it explicitly and fix the record, including revising earlier hedges once evidence is in.
11. **Every round ends reviewable.** A diff, rendered states, or a decision list — something the human can actually judge — plus what's done, what's blocked, and what needs a decision.
12. **Every round ends logged.** No round is complete until its `RUNLOG.md` entry is written (see Learning Loop). An unlogged round is an unfinished round.
13. **Leave a handoff.** Each stopping point updates `HANDOFF.md` with enough context that a fresh session continues without re-deriving anything.

## Prompt Skeleton

Use this 10-section skeleton to write each round's task instruction. Every section exists because its absence caused a failure at least once.

| # | Section | What goes here | Why |
|---|---|---|---|
| 1 | Context & grounding | Read the governing docs, `CLAUDE.md`, `RUNLOG.md`, and current repo/data FIRST; report overlaps; reconcile, don't clobber | Every failure traced to acting before reading reality |
| 2 | Objective (one) | A single, specific outcome for this round | Multi-goal rounds sprawl and can't be verified |
| 3 | Out of scope (explicit) | What this round must NOT touch | What you don't say gets built anyway |
| 4 | Constraints | Branch-only; no merge/deploy without approval; cost limits; brand rules; what's 🔴 human-owned | Keeps the agent inside the rails without re-explaining |
| 5 | Honesty gate | No overclaiming, no fake precision, no promising unbuilt features; withhold-not-guess | The single rule that protects credibility |
| 6 | Surface-don't-assume | On any conflict with a rule, data limit, or KPI: STOP and flag with options + a recommendation | Turns silent wrong guesses into decisions the human makes |
| 7 | Verification (render-side) | Prove it WORKS via real run/render in the browser; list the explicit checks | A green build shipped an invisible bug once; only render-side proof caught it |
| 8 | Assertion replay | Re-run the full prior assertion suite; any prior assertion flipping to fail fails this round | Refactors silently regress old guarantees |
| 9 | Full sweep | build + typecheck + content-check + link-check + deploy dry-run + determinism | Catches mechanical regressions before human review |
| 10 | Done & show me | Define done + exactly what to show (diff / screenshots / assertion results), plus what needs a decision | You review outcomes, not process |

## File Conventions

Every project repo carries these files. Create any that are missing at project start (Phase 0 / step 0 of the SOP in use).

- **`CLAUDE.md`** — project config and overrides. Must contain the config block (see `references/templates.md`): Slack channel, cost ceiling, review cadence, per-step-type tier overrides, links to governing docs. Claude Code reads it automatically every session.
- **`RUNLOG.md`** — append-only, agent writes freely, never edited retroactively. One structured entry per round/run (template in `references/templates.md`). For automated systems (cron/CI), the workflow itself appends its entry.
- **`LEARNINGS.md`** — agent-curated candidate patterns distilled from the runlog. Each entry has a status: `candidate` → `validated` → `promoted`. See Learning Loop.
- **`HANDOFF.md`** — the current full-context handoff, overwritten at each stopping point.

The SOP/skill files themselves are **governance**: the agent never edits them without an approved retro proposal (🔴 for meta-rules, 🟡 for step-level changes).

## Learning Loop

Raw learnings go in files; the SOP only changes by approved promotion. Logging lessons directly into an SOP makes it unreadable within twenty runs and violates the governance rule — this three-tier flow keeps the SOP clean while nothing gets lost.

**After every round/run (🟢, mandatory):** append a `RUNLOG.md` entry — date, objective, what happened vs. plan, deviations and why, workarounds used, failures + root cause, time/cost, and one "friction" line: the thing that felt harder than it should have.

**Distillation (🟢, continuous):** when something in the runlog repeats or clearly generalizes, add or update a `LEARNINGS.md` entry as `candidate`, naming the SOP step it affects. Promote to `validated` when seen 2–3 times or explicitly confirmed by the human.

**Retro (🟡, triggered):** run when a learning hits `validated`, when the human says "run a retro," or at the cadence set in `CLAUDE.md`. Procedure:

1. Read `RUNLOG.md` since the last retro.
2. Cluster into: worked / didn't work / workarounds that should become standard.
3. Update `LEARNINGS.md` statuses accordingly.
4. Propose **0–3** concrete SOP/skill diffs, ranked, each citing runlog entries as evidence — exact wording change, which step, why. Never more than 3: an unbounded self-improvement loop generates plausible churn, and every SOP edit risks regressing a load-bearing rule.
5. Post the proposals to Slack as a 🟡 REVIEW.
6. On approval: apply the diff, bump the skill's version line, append a one-line changelog entry inside the skill file, and mark the learning `promoted`.

If a retro finds nothing worth proposing, say so — "no changes proposed" is a valid, honest retro outcome.

## Slack Reporting Protocol

One channel per project (named in `CLAUDE.md`). Three message types, distinguished by prefix. Full message templates in `references/templates.md`.

**🔴 BLOCKED — integral questions only, absolute minimum.** Post only after hitting a genuine surface-don't-assume stop. Required contents: the question, 2–3 options, the agent's recommendation, and what is frozen until answered. Rules that keep volume down:
- Batch: multiple questions in one round → one numbered message.
- Forbidden: anything answerable by reading the repo, runlog, or governing docs. Exhaust "read before acting" first.
- A BLOCKED message without a recommendation is malformed — rewrite it.

**🟡 REVIEW — a gate is ready.** Contents: what's ready, the staging URL, screenshots (taken by the agent's browser), the 2–3 specific things the human should check, and the exact approval needed ("reply `approve merge` or list changes"). Retro proposals arrive as 🟡.

**⚪ FYI — everything else, digest-only.** One message at round end: what was done, sweep results, cost, link to the runlog entry. Never real-time narration — narration buries the 🔴s and trains the human to stop reading the channel.

Boundary rules:
- **No secrets in Slack, ever** (Meta-Rule 4).
- **Slack is for async/unattended contexts** — CI runs, long builds the human has walked away from. When the human is present in the session, ask in-session; posting to Slack while they're right there is theater.
- From Claude Code sessions, post via the Slack tools/MCP. From CI (e.g., the autoposter's cron), post via a Slack webhook stored as a SECRET.

## Version

v1.0 — initial harness (meta-rules updated for browser-enabled verification; learning loop and Slack protocol added).

### Changelog
- v1.0: Created from the project SOP sheet's Meta-Rules + Prompt Skeleton; added surface routing (Code/Design/human), approval tiers, RUNLOG/LEARNINGS/retro loop, Slack BLOCKED/REVIEW/FYI protocol.

---

# Harness Templates

Copy these verbatim when creating project files or posting to Slack. Consistent structure is what makes the runlog machine-readable at retro time and the Slack channel scannable at a glance.

## CLAUDE.md config block

Place this block at the top of every project's `CLAUDE.md`. The harness reads it every session.

```markdown
## Harness Config
- Harness: agent-harness v1.0 (this project runs under it)
- Active SOP skill: [build-loop | social-autoposter] v[x.y]
- Slack channel: #[project-channel]
- Cost ceiling: $[N]/month — flag at 80%, STOP at 100%
- Review cadence: retro every [N] rounds or on any validated learning
- Autonomy: auto_publish=[true|false] (if applicable)
- Tier overrides (step → tier, human-approved only):
  - [e.g., "4.1 round scoping → 🟢 (delegated 2026-XX-XX after 3 clean rounds)"]
- Governing docs: [links/paths]

## Project Brief
[The completed intake brief from the SOP's Phase 0 / DEFINE lives here.]
```

## RUNLOG.md entry

Append-only. One entry per round or automated run. Never edit old entries — corrections go in a new entry (Meta-Rule 10).

```markdown
---
## [YYYY-MM-DD] Round [N] — [one-line objective]
- Surface: [Code | Design | CI | Human]
- Planned vs. happened: [1–3 lines]
- Deviations & why: [or "none"]
- Workarounds used: [or "none"]
- Failures + root cause: [or "none"]
- Time/cost: [duration, tokens/$ if known]
- Friction: [the one thing that felt harder than it should]
- Verification: [sweep result, assertions passed/failed, screenshots path]
```

For CI/cron runs (e.g., autoposter), the workflow appends a compact variant automatically:

```markdown
---
## [ISO timestamp] Auto-run — [posted|staged|halted]
- Item: [content id] | Post id: [id or n/a]
- Render: [ok / retries / dimensions check]
- Anomalies: [or "none"]
```

## LEARNINGS.md entry

```markdown
### L-[NNN]: [short pattern name]
- Status: candidate | validated | promoted
- Affects: [skill + step, e.g., build-loop 5.1]
- Pattern: [what keeps happening / what should change]
- Evidence: [runlog entries: Round 3, Round 7]
- Proposed change: [exact wording, filled at retro time]
```

## Slack messages

### 🔴 BLOCKED
```
🔴 BLOCKED — [project] Round [N]
Frozen: [what cannot proceed]
Q1: [question]
  a) [option] b) [option] c) [option]
  → Recommend: [x] because [one line]
[Q2… if batched]
Reply with choices to unblock.
```

### 🟡 REVIEW
```
🟡 REVIEW — [project] Round [N]: [what's ready]
Staging: [URL]
Screenshots: [attached / path]
Check specifically: 1) [x] 2) [y] 3) [z]
Needed: reply `approve [merge/scope/change]` or list changes.
```

### ⚪ FYI (round digest — one per round, never real-time narration)
```
⚪ FYI — [project] Round [N] complete
Done: [1–2 lines]
Sweep: [pass/fail summary] | Assertions: [n/n]
Cost: [amount] (MTD: [amount] of $[ceiling])
Runlog: [entry link/anchor]
Next: [planned next round or "awaiting decision"]
```

### 🟡 REVIEW (retro proposals)
```
🟡 REVIEW — [project] Retro after Round [N]
Worked: [1–2 lines] | Didn't: [1–2 lines]
Proposals (max 3):
1) [skill step]: [exact change] — evidence: [runlog refs]
2) …
Reply `approve 1,3` / `reject 2` / `discuss`.
```

## HANDOFF.md skeleton

Overwrite at every stopping point.

```markdown
# Handoff — [project] as of [date, round N]
- State: [what exists, what's deployed where]
- In flight: [branch, open PR, unmerged work]
- Blocked on: [decisions/secrets/reviews outstanding]
- Next round: [objective + out-of-scope]
- Gotchas a fresh session must know: [list]
- Files to read first: CLAUDE.md, RUNLOG.md (last [n] entries), LEARNINGS.md
```
