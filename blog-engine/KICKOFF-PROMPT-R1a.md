You're starting a new project: the InHouse Wellness Blog Engine. The starter kit is in `blog-engine/` (this folder). This is **Round R1a — Orient + land governance**. It's a read-and-report round with one small commit, not a build round.

## 1. Context & grounding
Read these in full before doing anything else, in this order:
1. `CLAUDE.md`
2. `docs/HARNESS.md` (you run under these meta-rules)
3. `docs/BUILD-LOOP.md`
4. `docs/BLUEPRINT.md`
5. `spec/house-style.md`
6. `HANDOFF.md`
7. `RUNLOG.md`
8. every file in `config/`

Skim `docs/reference/autoposter-playbook.md`; it's reference only. The design was done in a planning session outside this repo, so this round reconciles it with the real repo and machine. Report what exists; don't clobber or restructure anything outside `blog-engine/`.

## 2. Objective (one)
Produce an honest state-of-the-world report for this repo and machine, then commit the starter kit, unchanged, on a new branch.

## 3. Out of scope (do NOT do these)
- Any Shopify, Anthropic, Google or Slack API call, or any use of credentials. Don't create `.env` or ask for secrets.
- Writing pipeline code, `pyproject.toml`, tests or workflows. Creating anything in `.github/`.
- Editing anything outside `blog-engine/`.
- Changing locked decisions, guardrails, `config/*.yaml` values, `spec/` or `docs/`.
- Merging, pushing to the default branch, or force-pushing anything.
- Connecting or authenticating MCP servers. You may list what's already configured.

## 4. Constraints
- Work on branch `be/r1a-orient` created from the current default branch.
- **Repo-safety stop (guardrail 8).** Before any `git push`, determine whether this repo is, or might be, connected to a Shopify theme via Shopify's GitHub integration. Signals include a theme structure at the repo root (`layout/`, `sections/`, `templates/`, `config/settings_schema.json`, `snippets/`, `assets/`, `locales/`) or docs mentioning it.
  - If there's any sign of a theme connection, **do not push**. Report it and give options.
  - If there's no sign, you may push the branch only (never the default branch) after reporting.
- Also report repo visibility (`gh repo view --json visibility,defaultBranchRef,nameWithOwner`). If it's **public**, flag it: research dossiers and configs would be public. Don't push; recommend options.

## 5. Honesty gate
Report what you actually observed, with the command that showed it. If something can't be determined (e.g. the theme connection can't be proven either way from the repo alone), say "unknown" and what would settle it. Don't infer.

## 6. Surface-don't-assume
If anything in the kit conflicts with the real repo or machine, **stop and list it as a decision** with 2–3 options and a recommendation. Examples: a different default branch, an existing `blog-engine/` folder or `CLAUDE.md` elsewhere that would load too, an existing `.github/workflows/` setup, Python unavailable, `gh` unauthenticated. Don't work around it silently.

## 7. Verification
Run and capture output (trim long output) for:
- `git remote -v`
- `git status`
- `git branch --show-current`
- the `gh repo view` command above
- `gh auth status`
- repo root listing (top two levels, ignoring `node_modules`)
- `ls .github/workflows` if present
- `python3 --version`, `uv --version`
- `claude --version`
- `claude mcp list`

Also find any other `CLAUDE.md` files in parent folders or the repo root that Claude Code would also load in this session, and summarize what they'd inject.

## 8. Assertion replay
No prior assertions exist yet. Record "n/a — first round" in the runlog.

## 9. Full sweep
Confirm the kit is intact: every file in `blog-engine/` is present, and each YAML file in `config/` parses (a one-line `python3 -c` with `yaml.safe_load` per file, or report if PyYAML isn't installed). No other sweep this round.

## 10. Done & show me
Done means all of the following:
1. The branch `be/r1a-orient` exists with one commit: "R1a: add blog-engine starter kit" containing the kit exactly as provided, plus your new `RUNLOG.md` entry and your overwritten `HANDOFF.md`.
2. The branch is pushed **only if** the repo-safety and visibility checks passed.
3. A reply to me with these sections:
   - **State report:** repo, branch, visibility, theme-connection verdict with evidence, existing workflows, other CLAUDE.md files, tooling versions, MCP servers configured.
   - **Conflicts & decisions:** numbered, each with options and your recommendation. Include your view on the proposed stack in `CLAUDE.md` and on the open "LLM transport in CI" decision.
   - **Kit review:** anything in the blueprint or configs you think is wrong, risky or underspecified, ranked, with at most 5 items. Propose; don't edit.
   - **What R1b (preflight) will need from the owner:** exact setup steps for the Shopify Dev Dashboard app (scopes you'll need for articles, blogs, products, collections, metafields and themes read), the Anthropic key, the GSC service account, and the Slack webhook. Include how to store each as a GitHub Actions secret and in a local `.env`, **without** ever pasting values into chat.
   - **Push status:** pushed, or not pushed and why.
