# HANDOFF — current state

**Last updated:** 2026-09-01, end of Round 2.
**Read first:** `CLAUDE.md` → `docs/autoposter-adjustments-inhousewellness.md` → `RUNLOG.md` → `LEARNINGS.md`.

---

## Where the project is

Rounds 1 and 2 complete. **Nothing has been posted. No cron exists. `auto_publish`
is false and no code can flip it. The self-improvement loop runs `dry_run=True`
and applies nothing.**

The pipeline is built end to end except live posting: queue → work orders →
captions → validator → render. Every stage except caption writing is
deterministic code.

## What works, verified

| Path | State |
|---|---|
| `src/validator.py` + `health_claims.py` | Round 1 gate. Blocks all 5 historical failure modes. |
| `src/remap.py` | Deterministic matcher: IDF cosine + rare-token gate + subject gate. No model call. |
| `src/destinations.py` | Cluster routing, INH ≥70% quota, satellite rotation with cooldown. |
| `src/workorders.py` | Daily selection, dedup `(platform, item_id)`, atomic state, corrupt state HALTS. |
| `src/captions.py` + `voice.py` | One batched call, schema-checked, validator-gated, retry-once-then-halt. |
| `src/reel.py` | Local Reels: Playwright cards → ffmpeg H.264. 0 credits, 0 tokens. |
| `src/feedback.py` | Collect + score live; adjust dry-run with self-protecting guardrails. |
| Tests | **94 passing** (49 validator, 27 caption, 18 loop). |

Sweep is clean: 11/11 Round 1 fixtures at unchanged dimensions, 12/12 destination
URLs pass, 0 non-200 among queued rows, remap deterministic across runs.

```bash
.venv/bin/python -m pytest tests/ -q
```

## The one open decision

**Only 24 of 103 queue rows survived the remap** — below the 60-row
stop-and-ask line. This is not a matcher failure; the blog genuinely has no
article for the other 79. Those rows carry **47,180 monthly searches** against
19,830 for the queued 24.

At 4 pins/day, 24 evergreen rows with a 120-day repost floor sustains roughly
**6 days** before the queue is exhausted. Options were put to the user; the
answer determines Round 3's shape. Ranked content gap is in `RUNLOG.md` —
the top four missing articles unblock 40 rows and ~27,500 monthly searches.

## Other open items

- **Legacy path not truly confirmed yet.** The gate passes (no posts since
  2026-08-25) but the shutdown was hours before the check. Re-run before any
  scheduling: assert no `via: network` post with `sentAt` after 2026-09-01.
- **Six topical Pinterest boards still do not exist.** All queued rows map to the
  closest of the four live boards and carry `board_is_placeholder: true`.
- **One template change needs review:** `statement` is now vertically centred at
  story size (was hardcoded `flex-start`, leaving the Reel hook frame ~60%
  empty). Unchanged at pinterest/ig sizes. No palette, type or brand-device
  change.
- **Caption generator has never run against a live model** — no Anthropic key in
  this environment. All deterministic guarantees are stub-tested.
- **Pinterest cannot be scored per post** — Buffer free plan is a 31-day channel
  aggregate; Blotato collects no Pinterest analytics.
- **Blotato holds zero INH history**, so the IG/FB feed returns nothing until the
  new machine posts.
- `animateAiImages` still unmeasured; stays disabled.
- **Not pushed to any remote.** Local git only.
- **Reels Set 2 remains blocked** — it fails the health-claim validator, which is
  correct. Rewriting it with hedges and a cardiac contraindication is a separate
  task.

## Credits and tokens

Blotato: **1,550 / 1,750 remaining** (200 spent: 170 in Round 1, 30 on the Round 2
comparison render). Model spend to date: **$0**. Projected at full cadence:
**~$1.51/month**.

## What Round 3 looks like

Depends on the queue decision. Once unblocked, the remaining build is: media
pipeline wiring (render → presigned upload → `publicUrl`), the D5 duplicate
breadcrumb gate, the conductor, and then a controlled `auto_publish=false` run
that stages posts without publishing.
