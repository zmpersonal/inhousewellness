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

---

## 2026-09-01 — Round 2: Queue remap, zero-cost render path, caption generator

**Objective.** Fix the 🔴 queue blocker by code; route destinations across INH +
satellites on all three platforms; spike a zero-cost local Reel path; build the
batched caption generator; build the self-improvement loop scaffold (collect +
score live, adjust dry-run). No live posting, no cron, no Reels published.

### Legacy path gate (item 7) — passes, but with almost no power yet

Zero posts of ANY kind since 2026-08-25; last `via: network` post remains
2026-08-22. **The gate passes, and it barely means anything: the shutdown was
hours ago.** Confirmation still requires the absence of `via: network` posts with
`sentAt` after 2026-09-01 over several days. Re-run before any scheduling work.

### 1. Queue remap — 24 queued, 79 blocked, zero 404s

Deterministic throughout: IDF-weighted cosine over title+slug+summary, a
rare-token gate, and a subject-compatibility gate. **No model call per row.**

Three bugs found and fixed while building it, each caught by inspecting output
rather than by the code failing:

1. **The blog index was silently under-collecting.** Paginating the `.atom` feeds
   returned 80 articles; the feeds cap at the 30 most recent per blog. Rebuilt on
   the Shopify sitemap: **109 articles**, plus 88 collections and 18 pages.
2. **Unseen tokens were scored as maximally COMMON, not maximally rare.**
   `idf.get(t, 1.0)` gave corpus-absent words the lowest weight, inverting the
   rare-token gate on exactly the queries that most needed blocking. "is it safe
   to take wallet into sauna" matched `are-infrared-saunas-safe` at 0.641
   "strong". Fixed with an IDF table whose `__missing__` returns the max.
3. **Cross-product collisions.** Token similarity cannot separate "is sauna good
   for a cold" from `is-cold-plunge-good-for-women` (0.498) or "how hot should a
   sauna be" from `hot-tub-cold-plunge-combo` (0.433). Added a subject gate:
   a keyword naming a product only matches an article covering that product.

**Threshold 0.40, calibrated by inspection, not tuned to a target count.** Above
it matches are defensible ("home sauna cost" → the operating-costs article at
0.413). Below it they degrade into product reviews standing in for explainers
("infrared vs steam sauna" → `homedics-premium-steam-sauna-review` at 0.375;
"how to use a sauna" → `sauna-alzheimers` at 0.376). Counts across the band:
0.35→45, 0.38→38, **0.40→24**, 0.42→18.

Every queued row now carries `source_article`, `link`, `board_id`, `verified_at`,
`http_status`, `match_score` and `match_confidence`. Sweep: **19 unique URLs, 0
non-200.** Remap re-run is byte-identical (determinism asserted in the sweep).

### The blocked 79 are a content gap, not a matching failure

The blog genuinely has no article for these keywords. Blocked rows carry
**47,180 monthly searches** — more than double the 19,830 the queued rows carry.
Ranked, this is a content brief:

| Missing article | Rows | Monthly volume |
|---|---|---|
| How long should you stay in a sauna | 7 | 10,070 |
| How much does a sauna cost (general) | 18 | 6,020 |
| What to wear / phone / wallet in a sauna | 7 | 6,000 |
| Sauna when you have a cold | 8 | 5,390 |
| Sauna and weight loss | 4 | 4,290 |
| How to build a sauna / DIY | 5 | 4,150 |
| Infrared vs steam / traditional (dedicated) | 9 | 3,820 |
| How hot should a sauna be | 2 | 3,200 |
| How to use a sauna | 2 | 2,190 |

Writing the top four would unblock 40 rows and ~27,500 monthly searches.

### 2. Destination routing — INH 70.8%, all ten satellites verified

All 10 satellites return 200, but **only 4 link to INH from their homepage.**
Six do on inner pages, found via their sitemaps. Destinations therefore point at
the *specific page that links back*, not the homepage:
`outdoorsteamsauna.com/recommended-retailer/`, `saunaimport.com/resources/`,
`homenhealthy.com/home-wellness/`, and so on. 12 destination URLs, all passing
both gates, in `data/satellite-destinations.json`; re-verified by
`scripts/verify_destinations.py` (exit 1 on any failure).

INH share **70.8%** (17/24), floor held.

One design correction: the 8% per-domain cap was firing on a 24-row batch, where
a single post is arithmetically 4.2% and two are 8.3%. The cap is a property of
the rolling 30-day *published* window, so it is now asserted only at
n ≥ 25 and reported as a soft notice below that — the same "don't act on noise"
principle as the loop's 30-post minimum.

### 3. Boards — mapped to the four that exist, all flagged

The six topical boards still do not exist. Every queued row is mapped to the
closest of the four live boards and carries `board_is_placeholder: true`.
18 → The Sauna Shop, 6 → Wellness At Home.

### 4. Zero-cost Reel spike — local wins decisively for anything carrying copy

Playwright story cards → ffmpeg → H.264. Built `reel-3-1` from set-03:
**1080×1920, 30.37s, 360KB, 0 credits, 0 tokens.**

Toolchain note: Playwright's bundled ffmpeg is a stripped build (`--disable-
everything`, VP8/WebM only, no H.264, no MP4 muxer, no xfade). Used the
`imageio-ffmpeg` wheel's full static ffmpeg 7.1 instead — libx264, xfade and
zoompan all present.

Side-by-side against Blotato rendering the same content (30 credits):

| | Local (ffmpeg) | Blotato |
|---|---|---|
| Copy fidelity | exact | **"3 same 180f. completely different heat."** — stray "3", lowercased, "180°F" mangled |
| Palette | locked `#1B1613`/`#E0A03C`/`#E9E5DD` | lime green `#CCFF00` highlight |
| Type | Fraunces 700 + IBM Plex | generic geometric sans |
| Brand device | ticked rule + footer | none |
| Text safety | auto-fit, contained | clipped at frame bottom |
| B-roll | flat cards | genuine AI sauna photography |
| Audio | none | AAC stereo |
| Size / cost | 360KB / 0 credits | 2.5MB / 30 credits |

**The AI photography is genuinely better than a flat card. The copy handling is
disqualifying.** For a brand positioned on measured numbers, publishing
"180f." with a random "3" prepended is worse than no video. Recommendation:
local for Correction, Reality Check and Measured Number (≈85% of the Reel plan);
reserve Blotato for Evidence Read where voiceover adds real value — and even
there, keep on-screen text minimal.

One template change was required and should be reviewed: `statement` hardcoded
`justify-content:flex-start`, which left the 9:16 hook frame ~60% empty — the
most important frame in a Reel. Now size-aware: centred at story, unchanged at
pinterest/ig. No palette, type or brand-device change. All 11 Round 1 fixtures
render byte-identically in dimension terms.

### 5. Caption generator — one batched call, ~$0.008 per post

`src/captions.py`. One call per cycle for all 6 posts. Structural fields (link,
board_id, media) come from the work order; **the model supplies prose only.**
Output is schema-checked, then run through the Round 1 validator, then checked
for cross-platform duplicate text. On failure: one retry with the specific
rejection appended, then halt. No degraded-publish path.

Measured input: **4,240 prompt chars ≈ 1,060 input tokens** for 6 posts.
At ~1,800 output tokens that is **$0.050 per cycle, $0.0084 per published post,
≈$1.51/month** at 6 posts/day. Instrumented in `Usage`, reported per post.

Not yet exercised against a live model — no Anthropic key is present in this
environment. Every deterministic guarantee is tested with a stub: schema
rejection, retry-then-halt, validator rejection, blank text, error strings,
Facebook URL in body, shared cross-platform text.

### 6. Self-improvement loop — collect + score live, adjust dry-run

`src/feedback.py` + `scripts/collect_metrics.py`. Segments by archetype,
platform, destination domain and board; primary reach, secondary saves; rolling
win-rate. Guardrails are the point and are tested individually:

- broken-post rate > 0 **halts the loop entirely**, regardless of reach
- no proposal from a segment under 30 posts
- `ALLOWED_KNOBS` and `FORBIDDEN_KNOBS` are disjoint, and
  `allowed_knobs`/`forbidden_knobs`/`guardrails` are themselves forbidden — the
  loop cannot widen its own permissions
- every proposal writes a dated `LEARNINGS.md` entry with evidence, the metric it
  should move, and a 14-day revert date
- `dry_run=True`: proposals logged, **nothing applied**

Verified against a 136-row fixture: correctly proposed shifting archetype weight
from `comparison` (mean 145) to `correction` (mean 434) and applied nothing.
Fixed one logic bug — the rotation proposal named `inhousewellness.com`, which is
not in the satellite rotation; its share is fixed by the 70% floor the loop
cannot touch.

Real-data limits, recorded honestly: **Buffer's free plan exposes Pinterest as a
channel aggregate over a rolling 31 days only** — 67 posts / 1,003 impressions /
1 save / 2.79% ER for 2026-08-05..09-01. Per-pin reach is not available, so
Pinterest segments cannot be scored per post; `collect` marks this
`granularity: "channel-aggregate"` rather than inventing per-pin numbers. Blotato
still holds zero InHouse Wellness history, so the live run collected 0 joined rows —
correct, not a failure.

### Sweep

94 tests pass (49 Round 1 + 27 caption + 18 loop). Round 1 assertion replay
clean: 11/11 fixtures at unchanged dimensions. 12/12 destination URLs pass.
0 non-200 among queued rows. Remap is deterministic across runs.

### Cost

Blotato: 30 credits for the one comparison render. **1,550 of 1,750 remaining
(11.4% consumed).** Model: $0 spent — the caption path has not run live.
Projected model cost at full cadence: ~$1.51/month.

### Friction

The matcher was written, then rewritten three times, because I kept validating it
on aggregate counts instead of reading the actual pairs. Every one of the three
bugs was invisible in "67 rows matched" and obvious the moment the keyword and
the slug were printed side by side. Printing pairs should have been the first
thing built, not the thing I reached for after the third wrong answer.

---

## 2026-09-01 — Round 2 addendum: queue-depth decision

The 24-row shortfall was put to the user (below the 60-row stop-and-ask line) and
answered: **throttle Pinterest to 2/day and start.**

- `CADENCE["pinterest"]` 4 → 2, with `CADENCE_TARGET` retained at 4 so the
  intended cadence is not lost. Cadence remains config, never hardcoded.
- 24 queued rows at 2/day = **~12 days of runway**, enough to prove the pipe
  end to end and start the 14-day zero-broken-post clock (D2).
- Daily volume is now 4 posts (2 Pinterest + 1 IG + 1 FB), not 6.
- Lift back to 4 only when the content gap closes. Explicitly **not** by lowering
  the match threshold: at 0.35 the extra rows include "infrared vs steam sauna"
  pointing at a Homedics product review and "how to use a sauna" pointing at a
  sauna-and-Alzheimers article. Pins whose destination does not answer the
  keyword are the original failure mode.

The content gap remains the highest-reach item in the backlog: the top four
missing articles unblock 40 rows and ~27,500 monthly searches.
