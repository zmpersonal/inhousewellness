# Start here — setting up the Blog Engine in Claude Code

## What's in this kit
```
SETUP-START-HERE.md        ← this file (for you; don't copy into the repo)
KICKOFF-PROMPT-R1a.md      ← paste its contents into Claude Code
blog-engine/               ← copy this whole folder into your repo
  CLAUDE.md                  project rules; Claude Code reads it automatically every session
  HANDOFF.md RUNLOG.md LEARNINGS.md   session memory and learning log
  docs/BLUEPRINT.md          the full design (v0.4)
  docs/HARNESS.md            operating rules (approval tiers, round structure, reporting)
  docs/BUILD-LOOP.md         the phase-by-phase build process
  docs/reference/autoposter-playbook.md   hard-won lessons from a similar automation
  spec/house-style.md        the article spec, with automation-mode notes on top
  config/*.yaml              settings YOU own: cadence, thresholds, routing, models, on/off switch
```

## Before you paste the prompt (about 10 minutes)
1. **Get the latest repo locally.** In your local clone of the InHouse Wellness GitHub repo, run `git checkout <default-branch> && git pull`.
2. **Copy the folder.** Put `blog-engine/` at the **top level** of that clone (next to the repo's other top-level folders). Don't copy `SETUP-START-HERE.md` or the prompt file into the repo.
3. **Check tools:**
   - GitHub CLI: `gh auth status` (if it says you're not logged in, run `gh auth login`)
   - Python: `python3 --version` (3.12 or newer is ideal)
   - uv (the Python package manager the build will use): `uv --version`. If it's missing, install it from astral.sh/uv. Claude Code will flag it either way.
4. **Open Claude Code in the engine folder**, not the repo root: `cd blog-engine && claude`. That way `blog-engine/CLAUDE.md` is loaded as the project rules.
5. **Paste the whole of `KICKOFF-PROMPT-R1a.md`** as your first message.

## Don't do yet
- Don't create any API keys or paste any keys, tokens or passwords into Claude Code or chat. R1a doesn't need them; R1b (next round) will walk you through storing them safely.
- Don't merge anything to your main branch.

## What happens next
Claude Code will report on your repo and machine, commit the kit to a branch called `be/r1a-orient`, and list any conflicts or decisions. Paste its full reply back into the claude.ai chat. I'll turn it into the R1b prompt plus a checklist of anything you need to do first (for example, creating the Shopify Dev Dashboard app).

## Open decisions you can answer anytime (they're not needed for R1a)
1. **North-star metric:** what result in 90 days makes this worth it?
2. **Monthly cost ceiling:** all-in budget for model usage. Needed before the writing stages run.
3. **Author byline:** is "Taylor Reed" a real person with credentials we can state truthfully, or should it be "InHouse Wellness Editorial Team"?
4. **Blog routing:** what topics belong in `/blogs/fire` and `/blogs/institute`?
5. **Featured images:** your own catalog product photos (recommended), Unsplash stock photos, or a mix?
