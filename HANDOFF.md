# HANDOFF — current state

**Last updated:** 2026-09-01, end of Round 1.
**Read first:** `CLAUDE.md` → `docs/autoposter-adjustments-inhousewellness.md` → `RUNLOG.md`.

---

## Where the project is

Round 1 (ingest / prove / validate) is complete. **Nothing has been posted. No
generation logic exists. No cron exists.** `auto_publish` is false and there is
no code that could flip it.

The bundle is ingested and verified, the validator is built and tested, and all
four idea feeds have been proven to respond independently.

## What is in the repo and working

| Path | State |
|---|---|
| `src/validator.py` | Output validator (adjustment C2). Raises `PostRejected`; no degraded-publish path. |
| `src/health_claims.py` | 20 compiled rules — disease/detox/weight-loss/absolutes/medical-advice/hype, plus hedge and contraindication requirements. |
| `src/limits.py` | Per-platform hard + soft character limits, Pinterest field bounds, allowed link hosts. |
| `tests/test_validator.py` | 49 tests, all passing. Cases are the real published failures. |
| `templates/`, `scripts/render.py` | 9 card archetypes, 3 sizes. Verified rendering at 1000×1500 / 1080×1350 / 1080×1920 with real fonts. |
| `.venv` | Playwright **1.49.1** — pinned for macOS 13. Do not upgrade on this host. |

Run both checks with:
```bash
.venv/bin/python -m pytest tests/ -q && .venv/bin/python scripts/render.py fixtures/pinterest.json out/
```

## Two things block Round 2 — do not build past them

1. **The keyword queue is 86% unpublishable.** 89 of 103 rows point at a
   `source_article` and/or `link` that 404s, including all three `/tools/*`
   destinations, which were never built. Pinterest pins require a working link,
   and the validator enforces it. Full sweep: `out/url-sweep.json`.
2. **The legacy publish path is still live and still publishing broken posts.**
   Buffer shows `via: network` / `customScheduled` posts through 2026-08-22, and
   two Pinterest pins on 2026-08-20 and 2026-08-21 published with `text: " "` —
   the exact blank-pin failure mode, ten days before this round. Running the new
   machine alongside it would double-post and keep the broken-post rate above
   zero, which is the gate on autonomy (D2).

Both are the user's calls. Options and recommendations are in the round report.

## Other open items carried forward

- **Pinterest boards:** only 4 exist (`Social`, `The Sauna Shop`,
  `Wellness At Home`, `Products`). The queue references 6 different board names.
  Either create them or remap `board` on every row.
- **Logo:** still pending from the user. Footer slot is ready in the card system.
- **`animateAiImages: true`** unmeasured — measure before enabling (A3).
- **Off-brand content on the InHouse Wellness surfaces:** a `voltoutpost.com`
  blackout post on the FB page (2026-08-22) and a corporate/workplace-wellness
  pin ("wellness experiences directly into the workplace") that reads as a
  different business from the sauna retailer. Worth a human look.
- **Buffer free plan** caps insights at 31 days — no historical baseline is
  recoverable from it. Blotato has no InHouse Wellness history at all.
- **Not pushed to a remote.** Local git only; `github.com/zmpersonal/inhousewellness`
  has no commits from this session.

## What Round 2 should be, once unblocked

Per the adjustments doc's build sequence (section E), the validator is done, so
next is **the Pinterest render spec + metadata schema (C3, C4)** and the caption
generator — one call per cycle, per-platform outputs, consuming `evidence_tier`
to match hedging to evidence strength. Pinterest first; add IG and FB once
Pinterest is clean.

**Do not build Reels Set 2** — it makes cardiovascular claims. The health-claim
validator now exists, which was its stated gate, but Set 2's seed copy still
fails it (there is a test asserting exactly that). It needs rewriting with
hedges and a cardiac contraindication before it can pass.
