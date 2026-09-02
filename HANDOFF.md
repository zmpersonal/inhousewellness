# HANDOFF — current state

**Last updated:** 2026-09-02, end of Round 3.
**Read first:** `CLAUDE.md` → `docs/autoposter-adjustments-inhousewellness.md` → `RUNLOG.md` → `LEARNINGS.md`.

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
