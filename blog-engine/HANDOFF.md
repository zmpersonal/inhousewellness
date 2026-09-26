# Handoff — InHouse Wellness Blog Engine as of 2026-09-18 (pre-R1a)
- State: starter kit only (governance docs, blueprint, spec, human-owned configs). No code, no workflows, no secrets, nothing pushed.
- In flight: nothing. The kit sits uncommitted in `blog-engine/` of the owner's local clone.
- Blocked on (not blocking R1a): north star, cost ceiling (blocks R6+), D4 author, D5 routing, D6 images.
- Next round: R1a, Orient + land governance (see KICKOFF prompt). Out of scope: Shopify/API calls, secrets, pipeline code, workflows, merges.
- Gotchas a fresh session must know:
  - GitHub Actions only run from repo-root `.github/workflows/`
  - the repo may be connected to a Shopify theme; confirm before any push
  - new Shopify custom apps use the Dev Dashboard client-credentials grant
- Files to read first: CLAUDE.md, RUNLOG.md (last 3), LEARNINGS.md, docs/BLUEPRINT.md
