# RUNLOG

Append-only. One entry per round. Never edited retroactively.

---

## 2026-09-01 — Round 1: Ingest, prove, validate

**Objective.** Ingest the existing bundle and verify it renders; write `CLAUDE.md`;
run the tooling check; measure credit burn; prove the four idea feeds
independently; build the output validator with tests. No generation logic, no
live posting, no cron, no Reels.

**Surface.** Claude Code. No Design work this round (design system is locked).

### What happened vs. plan

Plan followed. Six of seven scope items completed clean. Two findings force a
stop-and-ask before Round 2 (below).

| # | Item | Result |
|---|---|---|
| 1 | Ingest + verify renders | ✅ 11/11 fixtures render at correct dimensions, fonts real |
| 2 | Write `CLAUDE.md` | ✅ committed |
| 3 | Tooling check (C1) | ✅ **not blocked** — Pinterest + Instagram are now authorized |
| 4 | Measure credit burn (A3) | ✅ 5 renders, 170 credits, runway decision below |
| 5 | Prove 4 feeds (Step 8) | ✅ all four respond; two carry caveats |
| 6 | Output validator (C2) | ✅ built + 49 tests, all passing |
| 7 | Stop and report | ✅ this entry |

### Deviations from the plan, and why

- **The adjustments doc's C1 blocker is stale.** It states Blotato has only
  Facebook authorized and that this is 🔴 BLOCKED. Live check shows Pinterest
  (`9630`, `inhousewellness`) and Instagram (`68734`, `inhouse.wellness`) both
  connected, plus TikTok and YouTube. No block was raised; the round continued.
  Corrected in `CLAUDE.md`.
- **The skill's base64 `data:` URI media path (Step 9) does not apply here.**
  `blotato_create_post` takes `mediaUrls` as public URLs. Verified the real path
  is presigned upload → HTTP PUT → `publicUrl`. Recorded in `CLAUDE.md`.
- **Playwright had to be pinned.** Current Playwright refuses to install on this
  host (macOS 13): `Playwright does not support chromium on mac13`. `1.49.1`
  works against the cached `chromium-1148`. Pinned in `requirements.txt`.
- **Did not push to `github.com/zmpersonal/inhousewellness`.** Local git only —
  pushing is outward-facing and was not authorized this round.

### Verification (render-side, not "it builds")

```
python scripts/render.py fixtures/pinterest.json out/   → 6 PNG, all 1000x1500
python scripts/render.py fixtures/instagram.json out/   → 4 PNG 1080x1350, 1 PNG 1080x1920
```
Dimensions read back from the PNG headers, not trusted from the renderer.
Font check inside the page: all 4 faces report `status: loaded`,
`document.fonts.check()` true for Fraunces 700 and IBM Plex 400/600/700,
4 local `.woff2` requests, **0 remote requests, 0 failed requests** — so the
cards are not silently falling back to system type.

```
python -m pytest tests/ -q → 49 passed
```

### Credit burn (adjustment A3)

Measured by reading the balance before and after each render. 1,750 → 1,580.

| # | Template | Output | Credits |
|---|---|---|---|
| 1 | Whiteboard Infographic | 1 static image | 50 |
| 2 | Tutorial Carousel, Minimalist Flat | 7 slides | **0** |
| 3 | When X then Y Text Slideshow | 5-slide MP4, 2 AI images | 30 |
| 4 | Image Slideshow with Text Overlays | 3-slide 9:16 MP4 | 45 |
| 5 | AI Story Video + Brian voiceover, no animation | 3-scene 9:16 MP4 | 45 |
| — | Local Playwright card render | any size PNG | **0** |

**170 credits / $1.02 total.** AI image or voice generation is the only thing
that bills. Layout is free.

Second finding, unprompted but material: **the free paths carry the brand and the
paid ones do not.** The 0-credit Tutorial Carousel accepted `#1B1613` / `#E0A03C`
/ `#E9E5DD` exactly. The 50-credit Whiteboard Infographic produced a photoreal
whiteboard in primary marker colours — accurate, legible, and completely outside
the locked design system. Paying more bought less brand.

**Runway decision: render every static card locally; spend credits only on Reels,
capped at 4/week (≈8.8 weeks).** Every mix routing daily static posts through
Blotato AI templates falls under the 8-week threshold — the all-Blotato mix
lasts about six days. `animateAiImages: true` was NOT measured and must be
measured before it is enabled.

### The four feeds — proven independently

| Feed | Tool | Result |
|---|---|---|
| SEO | Ubersuggest `keyword_overview` | ✅ `infrared vs steam sauna` → vol 1,600, KD 15, CPC $2.25, 13-month seasonality |
| Blog | `blotato_create_source` | ✅ clean summarized content with real figures |
| Pinterest analytics | Buffer `get_aggregated_post_metrics` | ✅ 67 posts / 1,003 impressions / 1 save / 2.79% ER (28d) |
| IG+FB analytics | `blotato_list_top_posts` | ✅ tool returns 200, but **0 InHouse Wellness rows** |

Three caveats worth carrying forward:

1. **The old RSS bug is genuinely fixed by `create_source`.** A dead URL returns
   `Source extraction failed: Could not fetch article - Not Found` as an **error**,
   never a publishable string. The failure path is the one B1 asked for.
2. **`create_source`'s `title` is not trustworthy.** On a real InHouse Wellness
   article it returned `"Visa"`. Use `content` + `referenceUrl` only.
3. **Blotato has no InHouse Wellness history.** `list_top_posts` returned one
   post, from an unrelated Page (`Austin Beefs`) on the same Blotato account. The
   IG/FB analytics feed will only populate once the new machine posts. It is not
   a baseline source. Buffer's free plan caps insights at 31 days, so there is no
   historical Pinterest baseline either.
4. **Seasonality is real and favourable.** `infrared vs steam sauna` runs 880 in
   June–July and 2,900 in Dec–Jan. Restarting Pinterest now is well timed.

### Failures + root cause

- **One validator escape, caught by its own test suite.** "detox heavy metals"
  passed the first `DETOX_MECHANISM` pattern because the rule required
  detox→body-noun adjacency and the sentence read "your body detox heavy metals".
  Root cause: pattern written around one phrasing rather than the claim. Fixed by
  adding `detox|clear|remove|rid…of` to the toxin-object rule. 49/49 after.
  This is exactly why the tests use real published copy rather than invented copy.

### Cost

170 Blotato credits ($1.02) of a 1,750 ceiling — **9.7% consumed**, well under
the 80% flag.

### Friction

The keyword queue was built against a site map that does not exist. 89 of its 103
rows point at a URL that 404s, and the three `/tools/*` destinations were never
built. Discovering that took a URL sweep I had to write myself — nothing in the
bundle recorded which URLs had been verified versus inferred. A `verified_at`
field on each row would have turned a 20-minute investigation into a grep.

---

## 2026-09-01 — Round 1 addendum: blocker decisions

Both 🔴 blockers were put to the user at the end of Round 1 and answered.

**1. Keyword queue (89/103 dead URLs) → remap to live blog URLs.**
Round 2 will sweep the live blog feed, remap each row's `source_article` to its
closest genuine match, and repoint the three dead `/tools/*` destinations at live
collection or blog URLs. Rows with no honest match get `status: blocked` rather
than a guessed URL — withhold beats guess (harness Meta-Rule 6). A `verified_at`
field is added per row so an inferred URL is never again indistinguishable from a
checked one (learning L2).

**2. Legacy `network/customScheduled` path → user shut it down on 2026-09-01.**

Verification state, recorded honestly: both scheduling queues are empty
(`blotato_list_posts` scheduled → 0; Buffer scheduled/sending/draft/error → 0).
**That is not proof the path is off.** The legacy posts arrived in Buffer as
`via: network`, meaning they were published natively and backfilled afterwards —
they never sat in a queue. An empty queue therefore cannot distinguish "shut
down" from "publishes without queueing".

**Baseline for the real check: the most recent `via: network` post is
2026-08-22.** If no `via: network` post appears with a `sentAt` after
2026-09-01, the path is confirmed decommissioned. Round 2 must run that check
before any live posting, and it is a precondition of the D2 zero-broken-posts
clock starting.
