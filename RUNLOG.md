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

---

## 2026-09-02 — Round 3: Full-network corpus, media pipeline, staged run

**Objective.** Re-sweep the corpus across all 11 domains, re-run the remap, move
the destination floor to 60%, route the interactive assets, build the media
pipeline, add the D5 gate and conductor, and produce a staged run. No publishing.

### 1. Legacy gate — PASSES, and this time it means something

Zero Buffer posts of any kind since 2026-08-22; no `via: network` post after
2026-09-01. Round 2's check ran ~1 hour after shutdown and proved almost
nothing; this one ran **~26 hours after**, against a prior Pinterest baseline of
~2.4 posts/day. Silence over that span is real evidence.

### 2. The content gap was largely my error, not the network's

Round 2 reported "the blog genuinely has no article for these keywords." **I had
only swept inhousewellness.com.** The ten satellites are substantive content
properties, and sweeping them changes the conclusion.

| | Round 2 | Round 3 |
|---|---|---|
| Corpus | 109 pages (INH only) | **1,908 pages, 11 domains** |
| Queued | 24 | **34** |
| Blocked | 79 | 69 |

Scorer, threshold (0.40), subject gate and IDF handling **unchanged** — they were
correct and are untouched.

Two indexer bugs found and fixed:

1. **Shopify sub-sitemaps carry query strings.**
   `sitemap_collections_1.xml?from=…&to=…` does not end in `.xml`, so the suffix
   check skipped it and **all 37 INH collection pages were missing** — the exact
   commercial-intent destinations the floor depends on. Now matched by path.
2. **429 was being read as a dead link.** The URL verifier treated rate-limiting
   as failure, which blocked every INH row simultaneously and reported an INH
   destination share of **0.0%** — a completely false finding about the corpus.
   Now backs off (8s × 6, concurrency 2) and retries. After the fix: 0 non-200.

Per-domain corpus: healthresearchdatabase 842, infinitesauna 197,
saunasfactorydirect 173, inhousewellness 155, outdoorsteamsauna 138,
homenhealthy 136, besthomeinfraredsauna 101, arcticsoak 93,
commercialinfraredsauna 58, saunaimport 10, tubsandsaunas 5.

### 3. Destination floor 60% — NOT MET, and it is a ceiling not a choice

Floor moved to 60% with a 15% per-satellite cap, and `route()` now fills the INH
quota first, preferring the best INH match.

**Achieved INH share: 41.2% (14/34).** This is the maximum available, not a
routing preference: only 14 of the 34 queued rows have *any* INH destination
scoring ≥0.40. Reaching 60% would need ~20. The remaining rows' honest
destinations are satellite pages that actually answer the keyword.

Per the brief's own rule — *match quality outranks the ratio, block rather than
degrade* — nothing was redirected to a weaker INH page to make the number.
Second violation: `outdoorsteamsauna.com` at 17.6% against the 15% cap.

Both are 🔴 stop-and-ask conditions and are reported unresolved.

### 4. Interactive assets — routed, but the queue barely reaches them

Located and verified: `besthomeinfraredsauna.com/emf`,
`besthomeinfraredsauna.com/best/small-spaces`,
`healthresearchdatabase.com/healthspan`.

Destination is now resolved **per platform**: the Healthspan Habits Score carries
a challenge-a-friend share mechanic, and sharing is native on IG and FB but not
on Pinterest, so the asset wins on the feeds while the row's normal destination
wins on Pinterest.

One rule was wrong: the Healthspan rule required evidence-read archetype **and**
a health keyword, and matched nothing. The brief lists them as two signals for
the same asset; changed to OR.

Honest result: **only 2 of 34 queued rows are asset-eligible.** The queue is
almost entirely "X vs Y" and cost keywords — it contains no dimension or EMF
keywords at all. The assets are well-targeted; the *keyword queue* does not reach
them. That is an argument for a new keyword batch, not for loosening routing.
Among blocked rows, 9 more (8,110 vol) would route to the Healthspan score.

### 5. Media pipeline — proven end to end

`blotato_create_presigned_upload_url` → HTTP PUT raw bytes → `publicUrl`.
Verified live: PUT returned 200 with `{"Key": …}`, and the public URL resolved
`HTTP/2 200, content-type: image/png, content-length: 86302` — **byte-identical
to the local file.**

`src/media.py` verifies the public URL resolves *before* handing it to
`create_post`, rather than relying on the validator to catch it later, and treats
a byte-count mismatch as corruption rather than success.

### 6. D5 gate, conductor, staged run

`src/breadcrumb.py`: written before a publish attempt, cleared only after the id
is captured, **never auto-cleared**. A simulated post-then-crash halts the next
run (tested).

`scripts/run_cycle.py` chains: D5 gate → select → render (local, 0 credits) →
one caption call → validate → stage. `AUTO_PUBLISH = False`; the breadcrumb is
only dropped on a real publish attempt, which this mode never makes.

**Staged run: 4 posts, 0 credits, $0.0148, 4/4 validator pass, published
nothing.** Full output in `out/staged/<date>/staged.json`.

### Two defects the staged output exposed

Staging is doing exactly what it is for — these were invisible until real output
existed.

1. **Two Pinterest pins for the same query.** "infrared vs steam sauna" and
   "infrared sauna vs steam" are the same search reordered, and both were
   selected for the same day and board. Exact-text dedup cannot catch it because
   the captions differ. Fixed at **selection**: rows now carry a normalised
   keyword signature and one cycle never takes two rows with the same signature.
2. **`ALLOWED_LINK_HOSTS` was still INH-only** — a Round 1 constant written
   before satellites were destinations, so every satellite pin was rejected
   `PIN_LINK_OFFSITE`. Extended to the 10 verified domains. This is the gate's
   **data**, not its logic: an unknown host still fails, and a test asserts the
   router's domain list and the validator's allow-list cannot drift apart.

### Sweep

116 tests pass (was 94). Round 1/2 assertion replay clean: 11/11 fixtures at
unchanged dimensions, the Reel still builds at 1080×1920. Queue: 34 queued,
0 non-200, no missing fields. 12/12 destination URLs pass.

### Cost

Blotato: **0 credits this round** — all rendering local. 1,550 of 1,750 remain
(11.4% consumed, unchanged). Model: $0.0148 for the staged cycle, and that was
the offline stand-in; a live cycle is projected at ~$0.05.

### Friction

I hammered inhousewellness.com hard enough during the corpus build to get
rate-limited, then spent three remap runs watching the INH share swing between
0% and 41% before recognising the 429s as my own doing rather than a property of
the data. A politeness budget in the crawler — and treating 429 as backoff from
the start — would have saved all of it.

---

## 2026-09-02 — Round 3 addendum: floor decision + placeholder rule

Both open questions answered by the user and applied.

**1. INH floor 60% → 40%.** 41.2% was the measured ceiling, not a routing
preference. Re-raise as INH-side content grows; that remains the durable fix.

Applying it surfaced a related bug: **the per-satellite cap was computed before
URL verification**, so a domain inside the cap at n=40 (6 = 15.0%) was outside it
at n=34 (6 = 17.6%). Enforcement now runs *after* verification and **iterates to
a fixpoint**, because dropping a row shrinks the denominator and can put a domain
back over. Offenders are dropped lowest-volume-first — never redirected to a
weaker match.

Result: **29 queued, INH 48.3%, no satellite above 13.8%, QUOTA ok, 0 non-200.**
Five rows were dropped to hold the cap; that trade was the point of the rule.

**2. Placeholder rule added.** `ERROR_PATTERN` now also catches PLACEHOLDER,
TODO, TBD, FIXME, XXX, lorem ipsum, `{{...}}`, `<insert ...>` and `YOUR_*`, and
— the actual gap — it now runs over `firstComment`, carousel `slides`, and
Pinterest `title`/`altText`, not the post body alone. It caught the staged
"Full comparison: PLACEHOLDER" on the next run.

That prompted a better fix upstream: **the model no longer supplies the Facebook
link at all.** It writes a lead-in phrase and CODE appends the destination URL,
stripping any URL the model emits. A model can now no longer fabricate, mistype
or omit a link. Tested with a model that tries to emit a phishing URL — it is
stripped and replaced.

130 tests pass. Assertion replay clean.

---

## 2026-09-02 — Round 4: live model blocked; batch 02 absent; copy staged for review

**Objective.** Legacy gate, ingest keyword batch 02, run the first live caption
cycle, then stop at the human gate. Publish only on explicit approval.

### 1. Legacy gate — PASSES (third check)

- `via: network` posts after 2026-09-01: **0**
- Posts of any kind since 2026-08-23: **0**
- Last Buffer post of any kind: 2026-08-22, **10d 12h ago**
- Time since the confirmed shutdown: **1d 3h** — not the ~3 days the brief
  assumed. The stronger evidence is the 10½-day gap in posting of any kind
  against a prior ~2.4 posts/day Pinterest rate.

### 2. 🔴 BLOCKED — batch 02 does not exist

`data/keyword-batch-02-interactive.json` is not in the repo, not elsewhere under
`Claude Master`, and not in `~/Downloads`. Nothing was ingested and **no keyword
was invented to stand in for it.**

The ingest path was built and tested against the documented contract so it runs
the moment the file lands (`scripts/ingest_batch.py`, 10 tests):

- `source_article` is nulled on ingest and resolved by the existing remap engine
  at the unchanged 0.40 threshold; failures block
- `link` is preserved and the row marked `link_locked`, so the router cannot
  overwrite a pre-set interactive asset with a generic corpus match
- a destination outside the verified allow-list **fails loudly** rather than
  being accepted
- merge dedups against the existing queue on the normalised keyword signature
- `route()` now accepts `preassigned_domains`, so locked rows bypass routing but
  still count toward the INH floor and the per-domain caps

Queue is unchanged: **29 queued, INH 48.3%, quota ok, 0 non-200.** Interactive
routing stays at 2 of 29 — batch 02 is exactly what would move it.

### 3. 🔴 BLOCKED — no API key, so the live cycle did not run

There is no `ANTHROPIC_API_KEY` in the environment. `ANTHROPIC_BASE_URL` is set
and the Claude Code session variables are present, but no key a standalone script
can use. **The automated caption path has still never run against a live model.**

Rather than deliver nothing, the four work orders were written as real copy
**in-session** and staged through the identical chain — same validator, same
render, same staging. `scripts/run_cycle.py --copy-file` was added for this and
is reusable for any human-supplied copy.

This gives the human the quality review item 3 exists for. It does **not** prove
the automated path works, and the RUNLOG should not later be read as if it did.

Copy was grounded in the real sources via `blotato_create_source`, not invented.
That surfaced a finding: **the satellite pages yield almost no extractable
content.** `outdoorsteamsauna.com/guides/steam-vs-sauna` returned "No concrete
measured numbers are provided"; `infinitesauna.com/guides/infrared-vs-traditional`
returned only "120V vs 240V". The INH articles extracted richly (240V dedicated
circuit, 4.5–9 kW drawing 19–38 amps, humidity under 60%, 40 psf floor load;
German sauna etiquette with 10–15 minute rounds and the Aufguss). Satellite pages
are almost certainly JS-rendered data tables the scraper cannot read. **Captions
routed to satellite sources will be markedly less specific than INH-sourced ones**,
which cuts against the "specific numbers over adjectives" voice rule.

Staged: 4 posts, **4/4 validator pass, 0 credits, $0.0201, $0.0050 per post** —
just inside the $0.05 ceiling, and that figure is for supplied copy.

### One pipeline fix the staged output forced

Cards were rendering *before* captions existed, so they showed the bare keyword
as a headline and the SEO article title as a subhead — the frame said nothing
specific. The cycle now runs **caption → render**, and the card carries the
approved copy: headline from the pin title, supporting line from the caption's
own first sentence. "Sauna Renovation Cost: The Circuit Decides the Budget /
Most traditional heaters need a dedicated 240V circuit, and a 4.5 to 9 kW unit
draws 19 to 38 amps."

Known limitation, not changed: `statement` cards are top-aligned at Pinterest
size, leaving the lower ~60% empty. The richer archetypes (`cost`, `comparison`,
`spec`) fill the frame properly but need structured rows the caption call does
not yet return. Worth a Round 5 change to the caption schema; not changed
unilaterally here.

### 4. Not reached — no publish

Item 4 is gated on human approval of item 3, and item 3 is itself blocked on the
missing key. **Nothing was published. The broken-post counter has not started.**

### 5. Loop unchanged

`dry_run=True`. Nothing published means nothing to collect; the 30-posts-per-
segment minimum is nowhere near met.

### Sweep

140 tests pass (was 130). Queue integrity, destination verification and the
Round 1–3 assertion replay all clean. Blotato credits unchanged at 1,550.

### Friction

Two of the round's three inputs did not exist, and both failures were silent
until I looked — the brief described the batch file and the API key as present.
Checking preconditions before planning the round would have turned two dead ends
into one question asked up front.

---

## 2026-09-02 — Round 4 (continued): batch 02, fact layer, FIRST LIVE PUBLISH

### Correction to Round 4's satellite finding

Round 4 concluded the satellites yield almost no extractable facts and are
"almost certainly JS-rendered." **That was wrong, and the wrong thing was
blamed.** `blotato_create_source` is an LLM summarizer, not a scraper: it read
prose, wrote prose, and truthfully reported that *its own output* contained no
numbers. The data was published as CSV and JSON the whole time.

`create_source` is now restricted to prose context only. **It must never source
a number.**

### 1. Batch 02 ingested — 36 added, 5 surviving

51 rows, clusters exactly as briefed (emf 25 / fit 19 / electrical 7, 8,530
volume). 15 skipped on ingest as near-duplicates **within the batch itself**
("low emf sauna" / "sauna low emf" / "low emf saunas" are one query reordered).

| | before | after |
|---|---|---|
| queued | 29 | **35** |
| interactive-asset routing | **0 of 29** | **5 of 35** |
| INH share | 48.3% | **40.0%** (floor held, quota ok) |

Of the 36 merged batch rows, **5 queued and 31 blocked**, for two different reasons:

- **17 blocked below the 0.40 threshold.** No page in the 11-domain corpus
  answers "2 person sauna dimensions" or "sauna electrical requirements" — the
  BHIS *destinations* exist (`/#finder`, `/electrical/`) but no *source article*
  does. Scorer, threshold, subject gate and IDF untouched, as instructed.
- **14 blocked by the 15% per-domain cap.** See the conflict below.

### 🔴 The 15% cap and batch 02 are structurally incompatible

Batch 02 points **all 51 rows at one domain** by design. The cap allows
`int(35 × 0.15) = 5`. Even with a perfect matcher, at most 5 batch rows can ever
route. The cap was written when satellites were generic rotation targets, for
spam-pattern risk under VMP review; batch 02 deliberately concentrates on one
domain's owned assets. Both rules are reasonable and they cannot both hold.
Left unresolved and reported — this is the user's call, not a bug to patch.

### 2. Structured fact layer — built, and it is better than scraping

`scripts/fetch_facts.py` + `src/facts.py`. Five datasets cached with a fetch date:

| dataset | rows |
|---|---|
| `besthomeinfraredsauna.com/data/infrared_saunas.csv` | 90 models |
| `outdoorsteamsauna.com/data/outdoor-sauna-index.csv` | 75 metros |
| `outdoorsteamsauna.com/data/cities.json` | 75 |
| `healthresearchdatabase.com/data/studies.csv` | 583 |
| `healthresearchdatabase.com/data/topics.json` | 9 |

Exact numbers, zero tokens, no hallucination risk, deterministic. One dataset
failing does not take down the others.

The EMF cluster now has its correction, straight from the data: **all 90 models
carry an EMF label, 71 of them "Near Zero EMF" — but only 46 state a number and
only 34 state the measurement distance.** A field claim without a distance is not
comparable. That is the highest-value fact the network holds and it was sitting
in a CSV.

Also live: 71 of 90 models are 120V vs 4 at 240V; 2-person cabins run 38–52 in
wide (median 46) and 68–78.6 in tall (median 75); a 9 kW session costs $1.88 in
New Orleans and $7.35 in Honolulu, median $2.46 across 75 metros.

### 3. 🔴 Live caption cycle BLOCKED — `.env` does not exist

`src/model.py` is wired: python-dotenv, Sonnet, and it deliberately ignores any
shell `ANTHROPIC_BASE_URL` in favour of the SDK default endpoint. `python-dotenv`
and `anthropic` are installed. `.gitignore` now covers `.env` / `.env.*`, and
`.env.example` shows the one line required.

But there is **no `.env` at repo root**, and no `ANTHROPIC_API_KEY` anywhere in
the environment. **The automated caption path still has never run against a live
model.** Item 3 is not done.

### 4. ⚪ FIRST LIVE PUBLISH — 2 Pinterest pins

The legacy-path gate was removed from the cycle per instruction.

| | pin |
|---|---|
| **Infrared vs Steam Sauna: The Difference Is Humidity** | https://www.pinterest.com/pin/902690319088917799 |
| **Sauna Renovation Cost: The Circuit Decides the Budget** | https://www.pinterest.com/pin/902690319088917812 |

Board: **The Sauna Shop** — the six topical boards still do not exist, so both
fell back to the closest existing board and are flagged, not blocked.

Sequence, exactly as designed: media uploaded and each `publicUrl` verified
byte-identical → payloads re-validated against the **real** media URLs → D5
breadcrumb dropped **before** each publish → published → breadcrumb cleared only
**after** the id was captured → `published-log.json` updated.

**These two were written in-session and human-approved. They were NOT generated.
They prove the publish path, not the generator.**

Verification — stated precisely:
- ✅ both pins exist, `status: published`, pin URLs return 200
- ✅ full description present on both, read back from `list_posts` (not blank)
- ✅ both destination links return 200
- ✅ media present on both
- ⚠️ **title and altText were submitted and accepted but not independently read
  back.** Neither Blotato endpoint echoes them, and Pinterest blocks automated
  page fetches, which is not something to work around. Confirm by eye in the
  Pinterest UI.

### Broken-post counter STARTED

`src/health.py`. **Day 1 = 2026-09-02: 2 published, 0 broken. 1 of 14 clean days,
13 to go.** Any broken post resets the streak to zero.

### 5. Loop unchanged

`dry_run=True`. Two published posts is nowhere near the 30-per-segment minimum.

### Sweep

140 tests pass. Queue integrity clean, 0 non-200 among queued rows, quota ok.
Blotato credits unchanged at 1,550 — all rendering local.

### Friction

The 15% cap is the second rule this project has hit that was correct when written
and wrong once the facts changed, after the 70% INH floor. Both were calibrated
against an assumption about the satellites that the full sweep disproved. Worth
re-reading the other constants for the same failure mode.

---

## 2026-09-02 — Round 5: recalibrate the constants, fact-grounding

### 0. Constant audit — 4 more inherit the thin-satellite assumption

Full write-up in `docs/constant-audit-2026-09-02.md`. Flagged 🟡, not changed:
`INH_MIN_SHARE` (the spam rationale is dead, the commercial one survives), the
1:1 `CLUSTERS` domain map (842 pages on one "cluster" domain), the 12-URL
hand-curated destination file, and the 3-asset interactive list (the sweep found
calculators on five domains).

One was fixed outright: `MIN_N_FOR_DOMAIN_CAP` was hardcoded 25, derived from the
*8%* cap and silently outliving two revisions of it. Now computed from the cap.

Removed 56 lines of dead rotation code (`SatelliteRotator`, `plan_destinations`,
`PER_DOMAIN_COOLDOWN_POSTS`) — thin-satellite machinery superseded by `route()`.

### 1. Domain cap → URL cap

`SATELLITE_MAX_SHARE` 0.15 → **0.35**; new `PER_URL_MAX_PINS = 4` per rolling 30
days, enforced after verification and iterating to a fixpoint alongside the
domain cap.

`link_locked` changed from a router bypass to a **first choice**. That is the
whole point: the URL cap can now push a batch-02 row off `/emf/` and onto a
deeper page on the same domain. Rows carry `alt_urls` — up to 8 same-domain
candidates above threshold — so falling through means a deeper page, not a block.

Result: **35 distinct destination URLs for 80 rows, max 4 per URL, no violations.**
Batch 02 spread onto model pages, `/collections/far-infrared`,
`/best/small-spaces` and the EMF index instead of stacking on one URL.

### 2. Structured facts can ground a row

A row now qualifies if `source_article` **or** `source_data` resolves.
`source_data` names the dataset, the selector, the fetch date and the exact
figures. New validator rule `UNGROUNDED_NUMERAL` rejects any numeral in caption
copy — text, title, altText, firstComment, slides — that appears in neither the
source article nor the source_data facts. Bare 0–10 are exempt as structural.

Tested with the real failure it exists to prevent: an invented weight ("412
pounds") and an extrapolated one (doubling a median to guess a 4-person width)
are both rejected; grounded figures pass.

**All 17 previously-blocked rows released.** Batch 02 went from 5 of 36 queued to
**36 of 36**.

| | before | after |
|---|---|---|
| queued | 35 | **80** |
| batch-02 queued | 5 | **36 of 36** |
| distinct destination URLs | ~17 | **35** |
| fact-grounded rows | 0 | **25** |
| INH share | 40.0% | 41.2% (floor held, quota ok) |
| interactive assets routed | 5 | 6 across all three assets |

One bug found and fixed en route: fact-grounded rows have no `source_article` by
design, and the verifier was calling `status.get(None)`, then blocking all 25 as
"URL did not return 200". That was a bug reported as a finding — the fix is to
verify only URLs that actually exist.

### 3. 🔴 Live caption cycle still BLOCKED — `.env` absent

Diagnostic run in full: repo root correct, `.env.example` present, `.gitignore`
covers `.env`, `python-dotenv` installed, `anthropic` SDK 1.3.0 installed, model
configured `claude-sonnet-5`, shell `ANTHROPIC_BASE_URL` present and **ignored by
design**. The only missing piece is the file:

```
.env exists : False
ANTHROPIC_API_KEY in shell env : False
```

Not stubbed, per instruction. **The automated caption path has still never run
against a live model.** It is the last unproven link in the system.

### 4. ⚪ EMF correction staged — first fact-grounded post

Grounded entirely in `infrared_saunas.csv` (fetched 2026-09-02), validator PASS
including the new numeral rule. Every figure traced: 90, 71, 46, 34.

> **Low EMF Infrared Sauna: 90 Models, 34 Real Numbers**
> Low EMF infrared sauna claims are almost universal and almost never comparable.
> Across 90 indexed models, all 90 carry an EMF label and 71 say "Near Zero EMF" —
> but only 46 state an actual number, and only 34 say at what distance it was
> measured. A reading without a distance tells you nothing.

Rendered with the `correction` archetype: the claims column struck through
against the published column. Fills the frame properly, unlike the `statement`
cards. Staged at `out/staged/emf-correction.json`, **not published**.

Written in-session and fact-grounded — **not model-generated.**

### 5. Loop unchanged

`dry_run=True`. Two published posts against a 30-per-segment minimum.

### Sweep

**147 tests pass** (was 140). Queue: 80 queued, 0 non-200, domain and URL quotas
clean. Broken-post counter unchanged at day 1, 0 broken. Blotato credits 1,550.

### Friction

The `status.get(None)` bug produced a precise, plausible, entirely wrong finding —
"25 rows blocked, source_article did not return 200" — for the third time this
project (after the 429s and the IDF default). All three had the same shape: a
missing-value path silently taking the failure branch. Worth a standing check on
any code that treats absence and failure as the same thing.

---

## 2026-09-02 — Round 6: constants applied, missing-value rule enforced

### 0. The missing-value pattern is now a lint, and it found more

`scripts/lint_missing_values.py`. A broad "flag every one-arg `.get()`" rule
produced **157 findings**, almost all already guarded — a lint nobody reads is
worse than none. Narrowed to the two shapes that actually caused the bugs:
a `.get()` result passed unguarded into another call (`str(status.get(url))`),
and a `.get()` whose **key** is itself an unguarded `.get()`. Helpers verified to
handle `None` as their first act are whitelisted; the guard exists, one level
down. Result: 39 → **12 real findings, all fixed, lint now clean at 0.**

The sweep found **two new instances**, taking the count to six:

5. **The API key was present but a placeholder.** `load_key` checked presence,
   not usability, so `sk-ant-your-key-here` loaded perfectly and failed at the API
   with a 401. Now shape-checked at load: prefix and length, with a specific
   diagnostic naming what it found.
6. **Every cached fact silently returned `None` when run from `scripts/`.**
   `CACHE = pathlib.Path("data/facts")` is cwd-relative — the same shape as
   `load_dotenv()` searching the cwd instead of the repo root. All state and data
   paths are now anchored to the repo root via `__file__`.

**Space-in-path audit: clean.** No `shell=True` anywhere; `subprocess.run` in
`reel.py` passes an argument list, not a string; every module imports and runs
correctly from a subdirectory. The f-string "hits" were message text, not paths.

### 1. All four constant fixes applied

**`CLUSTERS` retired to a preference weight.** Matching now searches all 11
domains and adds `CLUSTER_PREFERENCE_BONUS = 0.06` when a page is on the
cluster's preferred domain — a tiebreak, never a gate, so a weak match on the
"right" domain can't beat a strong match elsewhere.

**Destinations generated, not curated** (`scripts/generate_destinations.py`):
**12 hand-curated URLs → 127 verified**, capacity **48 → 508 pins**.

Two corrections were needed to get there, both the same shape as everything else
this project keeps hitting:

- The link-back gate was **per-URL** when its purpose — proving a satellite is
  legitimately connected to INH — is a **per-domain** property. Applied per-URL it
  excluded `besthomeinfraredsauna.com/emf/` and `/electrical/`, the batch-02
  destinations the user pre-set and approved. Now: a domain qualifies if any page
  links back; thereafter any 200 page on it is usable. 🟡 **This is a gate change
  and is flagged as such.**
- The first run then reported "BHIS and healthresearchdatabase: no verified
  destination survived." That was **sampling**, not fact — the shallow-page sample
  missed `/retailers/inhouse-wellness/` at depth 4. Added a bounded deeper probe;
  both domains qualify. Absence of evidence in a sample is not evidence of absence.

**`INH_MIN_SHARE` kept at 0.40, rationale rewritten** — recorded in `LEARNINGS.md`
so it is not relitigated on the dead spam-pattern argument.

**`INTERACTIVE_ASSETS` 3 → 12**: EMF index, electrical checker, home-fit finder,
120V list, three ArcticSoak calculators, climate index, heater sizing, commercial
ROI, hot-tub cost calculator, Healthspan score.

### Result

| | before | after |
|---|---|---|
| queued | 80 | **90** |
| distinct destination URLs | 35 | 39 |
| network URL capacity | 48 pins | **508 pins** |
| fact-grounded rows | 25 | **28** |
| rows landing on an interactive asset | 6 | **13 (14%)** |
| INH share | 41.2% | 41.1% (floor held) |
| destination domains spanned | 6 | 7 |

Retiring `CLUSTERS` **did not** drop queue size or INH share — the stop-and-ask
condition did not trigger.

One more bug found by checking the output rather than trusting it: the asset
report showed **6 pins on the EMF index against a cap of 4**. `/emf` and `/emf/`
were counted as different URLs. Added `canonical_url()` — strips trailing slash,
lowercases the host, drops the fragment (so `/#finder` and `/` are one page) —
and routed all cap accounting through it. Cap now holds.

### 2. 🔴 Live caption cycle STILL BLOCKED — the key is a placeholder

The `.env.txt` diagnosis was right and that problem is fixed: `.env` exists, is
plain ASCII, 39 bytes, and `ANTHROPIC_API_KEY` reads from the repo root.

But the value is **`sk-ant-your-key-here`** — 20 characters, the placeholder from
`.env.example`. Confirmed against the API:

```
401 authentication_error: API key is invalid.
```

`load_dotenv` was already anchored to the repo root via `Path(__file__).parents[1]`,
so that suspicion is ruled out — it was never reading the cwd. Not stubbed, per
instruction. **The automated caption path has still never run against a live
model.** One real key unblocks it.

### 3. Not reached — gated on item 2, then on human approval.

### 4. Metrics pull wired

`scripts/weekly_metrics.py`. Buffer for Pinterest (the only source), Blotato for
IG/FB, feeds independent, joined to `post_id`, output as the ⚪ FYI digest.

Run against real data: Buffer reports **0 posts** for 2026-09-01..02 while our log
has 2. The digest says so explicitly rather than printing "0 impressions" — our
pins publish through Blotato and Buffer backfills natively-published pins on a
daily refresh, so this reads as **not-yet-backfilled**. It becomes a real signal
only if it persists past ~48h. That distinction is exactly the missing-value rule
applied to a report.

### 5. Loop unchanged — `dry_run=True`, 2 posts against a 30-per-segment minimum.

### Sweep

**152 tests pass** (was 147). Missing-value lint clean. Queue 90 queued, 0
non-200, domain and URL caps clean. Broken-post counter unchanged: day 1, 0
broken. Blotato credits 1,550.

---

## 2026-09-02 — Round 6 (continued): live cycle blocked on a workspace id

### The key is real. The blocker moved.

The placeholder is gone. `.env` holds a 108-character `sk-ant-api03-…` key and
**the shape check passes.** The key also **authenticates** — no 401.

It fails at a different, more specific point:

```
400 invalid_request_error: anthropic-workspace-id is required when
authenticating with an identity-linked API key; send the id of the workspace
this request acts in.
```

This is an **identity-linked key** — issued against a user rather than a
workspace — so every request must name the workspace it acts in. The value is not
discoverable without a working auth path, so it has to come from the user:
console.anthropic.com → Settings → Workspaces, an id beginning `wrkspc_`.

Support is wired: `src/model.py` reads `ANTHROPIC_WORKSPACE_ID` from the same
`.env` and sends it as the `anthropic-workspace-id` default header when present.
`.env.example` now documents it, and tells the reader to paste the key directly
rather than edit the example — which is how the placeholder reached `.env`.

**One line in `.env` unblocks the cycle:**
```
ANTHROPIC_WORKSPACE_ID=wrkspc_...
```

### Everything downstream of the call is now wired and proven

So that only the model call itself remains untested:

- **Work orders carry `source_data` into the brief.** The brief now includes a
  `facts` block with the exact figures for fact-grounded rows.
- **A `NUMBERS` section was added to the prompt**, stating that every numeral must
  come from that block verbatim — no rounding, converting, averaging,
  extrapolating or combining, and no numerals at all on posts without facts.
  This is what makes `UNGROUNDED_NUMERAL` satisfiable rather than a trap. If the
  rule still fires on live output, it is a signal about how the facts are
  presented, not a reason to loosen the rule.
- **Each post is validated against its OWN grounding** inside `captions.generate`,
  not a shared blob.
- Today's 4 work orders include **2 fact-grounded posts** (the 120V/240V split and
  the EMF claims index), so the rule will be exercised against live output.

Dry run through the full chain with the stand-in: brief 2,072 chars, **4/4
validator pass**, caption → render → stage, 0 credits. Projected live cost
**$0.0042 per post**, inside the $0.05 ceiling.

### 🟡 Small-n artifact worth a decision

The per-cycle audit reports quota violations on a **4-post day** — INH 25% against
the 40% floor, BHIS 50% against the 35% cap. Both caps are defined over a rolling
**30-day** window, and 4 posts cannot express either ratio. `MIN_N_FOR_DOMAIN_CAP`
is now 4 (derived from the 35% cap), so it asserts where it previously would not.
The queue-level audit over 90 rows is clean. Not changed unilaterally — the caps
are decided constants. Options: apply the daily audit as a notice rather than a
violation, or raise the minimum-n for the per-cycle check specifically.

---

## 2026-09-02 — Round 6 (final): cycle audit fixed; live call blocked on the workspace id

### Per-cycle quota audit is now a notice — approved change applied

`MIN_N_FOR_CYCLE_AUDIT = 30`, set as a **literal**, deliberately not derived from
the cap. Deriving `MIN_N_FOR_DOMAIN_CAP` from the cap value is exactly how it
silently drifted 25 → 4 across two revisions; this one is set on its own terms.

Below the threshold the cycle reports the ratios without asserting on them:

```
[quota] cycle ratios (informational, n=4 < 30): INH 25% (1/4), besthomeinfraredsauna.com 50%
```

At n=4 the only achievable INH shares are 0/25/50/75/100%, so a 40% floor is
unreachable by construction and a clean daily run would have halted on
arithmetic — blocking cadence permanently. The 90-row queue-level audit remains
the enforcing check and is clean. Three tests cover it, including one asserting
the threshold is literal rather than derived.

### 🔴 Auth: the key works, the workspace id is not in the file

Reporting measurement, not assumption — I diagnosed my own loader first, as
instructed.

**What passes:** key loads, 108 chars, `sk-ant-api03-…`, shape check PASS. The
key **authenticates** — no 401.

**Exact error, unchanged from the previous attempt:**
```
400 invalid_request_error: anthropic-workspace-id is required when
authenticating with an identity-linked API key; send the id of the workspace
this request acts in.
```

**Loader diagnostics — all clean:**
- path resolves to `<repo>/.env` via `Path(__file__).resolve().parents[1]`, not the cwd
- no BOM, no CRLF, no quoting on the value
- `dotenv_values()` parses the file and returns exactly one key

**File measurement:** `.env` is **127 bytes** = `ANTHROPIC_API_KEY=` (18) + key
(108) + newline (1). That accounts for every byte; there is no room for a second
line. `dotenv_values` sees one key: `ANTHROPIC_API_KEY`.

**Repo-wide search:** `ANTHROPIC_WORKSPACE_ID` appears only in `.env.example`
(the template I wrote) and this runlog. No `wrkspc_` value exists anywhere on
disk, and there is no second `.env` in the repo, its parent, or `~/Downloads`.

The header wiring is already in place and is not the problem: `make_caller`
sends `anthropic-workspace-id` as a default header whenever
`load_workspace_id()` returns a value. It returns `None` because the variable is
absent from the file.

**One line unblocks the cycle:**
```
ANTHROPIC_WORKSPACE_ID=wrkspc_...
```
from console.anthropic.com → Settings → Workspaces. Appending it (rather than
replacing the file) preserves the working key line.

### Everything else is ready

155 tests pass. Full chain verified with the stand-in this run: 4 work orders,
**2 of them fact-grounded**, brief 1,282 input tokens, **4/4 validator pass**,
caption → render → stage, 0 credits, **$0.0042 per post** projected. Nothing
published.

---

## 2026-09-02 — Round 6 (final): FIRST LIVE CAPTION CYCLE

Auth resolved. The stray `~/.env` was the cause; the byte-count measurement was
correct throughout. `.env` now 182 bytes, two keys, and the wired
`anthropic-workspace-id` header satisfied the 400 on the first try.

**The automated caption path has now run against a live model.** It was the last
unproven link in the system.

```
[caption] live model: claude-sonnet-5
[caption] tokens in 2,079 / out 1,510 over 1 call = $0.0481; $0.0120 per post
[render]  4 cards from approved copy, local, 0 credits
[validate] 4/4 pass
```

One batched call, no retries, **$0.0120 per post** against a $0.05 ceiling.
Nothing published.

### Three real failures on the way, each fixed at the right layer

**1. Truncation misreported as schema drift.** The first live call returned
`response is not valid JSON`. It was not malformed — it was **incomplete**.
Sonnet 5 spent **3,237 of a 4,000-token budget on extended thinking**, hit
`max_tokens`, and truncated the array mid-object. `stop_reason` was available and
ignored, so a truncated string reached the parser and the reader would have gone
hunting for a schema bug that did not exist. Raised `MAX_TOKENS` to 16,000 and
made `stop_reason == "max_tokens"` an explicit error naming the real cause.
**This is the missing-value pattern again** — a known failure state silently
taking the wrong branch.

**2. Cost 7× over ceiling, from thinking tokens.** With thinking on, the cycle
cost **$0.3537 — $0.0884 per post**. Caption writing is a short, heavily
constrained transformation of a structured brief and the output is validated in
code either way, so the reasoning budget bought little. Disabled by default
(`THINKING = {"type": "disabled"}`, flip to `None` to re-enable and measure).
Cost fell to **$0.0120 per post, a 7.4× reduction**, with no loss of quality —
the disabled-thinking copy is the better of the two.

**3. 🟡 `UNGROUNDED_NUMERAL` fired on live output — and it was our bug, not the
model's.** Reported rather than patched, per instruction.

Offending numerals: **`120` and `240`**. Prompt section that should have
prevented it: the `facts` block in `brief_for_model`, governed by the `NUMBERS`
rule in `src/captions.py`.

The model cited 120V and 240V **correctly, from the block it was given**. But the
figures lived in *key names* — `models_120v`, `voltage_breakdown: {"120": 71}` —
and `grounding_text` walks **values only**, so the extractor could not see them.
The rule rejected correct behaviour.

Worse, it had already **degraded the copy**: in the earlier thinking-on run the
model dodged the rejection by writing *"71 run on the lower-amp setup"* instead of
*"71 run on 120V"* — vaguer copy, produced to satisfy a false positive, on a brand
positioned on published measurements.

Fixed at the presentation layer, not by loosening the rule: `electrical_facts`
now emits `by_voltage: [{volts: 120, models: 71, amps_min: 15.0, ...}]`, so every
quotable number is a value. A test now asserts that **any numeral appearing in a
fact key is also reachable by the grounding extractor**, across all three
clusters. The live copy immediately improved to *"71 run on 120V and pull between
15.0 and 20.0 amps."*

**4. `source_data` staleness.** The fix above appeared not to work because
`source_data` is cached on each queue row at remap time, so 61 rows still carried
the old key-based shape. A stale block silently mismatches the grounding check and
rejects correct copy. Refreshed; noted in `remap_queue.py`.

### Live output quality

Adult-to-adult throughout, specific numbers over adjectives, corrective register,
no hype, no emoji stacking, no engagement bait. Both fact-grounded posts cite only
figures from their block.

The Facebook EMF post is the strongest thing the system has produced: it turns the
brand's best-performing argument into a statistic (90 labelled, 46 numeric, 34
with a stated distance, 4 distinct wordings), explains *why* distance matters,
and — unprompted — carries the correct hedge and a cardiac/pregnancy
contraindication. The health-claim gate was satisfied by the copy itself, not by
a retry.

One validator catch worth noting: an intermediate attempt was rejected
`HEALTH_UNHEDGED` on the dry-vs-wet pin. The gate is working on live output.

### Sweep

**156 tests pass.** Missing-value lint clean. Nothing published; broken-post
counter unchanged at day 1, 0 broken. Blotato credits 1,550.

---

## 2026-09-02 — Round 7: empty-card defect fixed, Band direction ported

### 1. 🔴 The empty-card defect — fixed

The live cycle rendered a kicker, a headline and a standfirst, then nothing. The
comparison card had no comparison. The EMF card — the strongest copy this system
has produced — dropped the 90/46/34/4 statistic entirely. This was the Round 5
deferral coming due.

**The caption schema now returns the card body**, per archetype:
`comparison` (a/b + rows of [label, aVal, bVal]), `cost` (figure, unit, rows),
`spec` (rows), `checklist` (items), `evidence` (claim, finding, strength,
source), `correction` (xLabel/yLabel + x[]/y[]). Queue archetypes map onto card
archetypes through `ARCHETYPE_ALIAS`, so `reality_check` renders as a checklist
and `evidence_read` as evidence.

**`EMPTY_BODY` added.** It rejects a card missing its archetype's required
fields, with fewer than 3 rows, with a wrong-width row, or with an empty cell.
Tested against the three assets from the live cycle — **all three fail**, as
required. Body cells are also now scanned by `UNGROUNDED_NUMERAL`, so a figure
smuggled into a table cell faces the same rule as body text.

### 2. Band direction ported

`templates/cards.html` rebuilt as direction 1a. Photograph across the top third
bled to three edges; charred ground below carrying the body at full width; the
headline in a solid ink capsule overlapping the seam so type never sits on the
image. Legacy template kept at `templates/cards-legacy.html`.

Design-system tokens adopted from the bundle (`templates/ds/`) in place of the
hand-rolled `tokens.css`. The four woff2 files are **byte-identical** to ours, so
there is no font risk. `--flag: #9B2C24` is now available for warnings and
contraindications only.

Both violated rules fixed: kickers pass through `sentence()` so
`CORRECTION` / `REALITY CHECK` become `Correction` / `Reality check`, and the
17px body floor is enforced in code.

The ticked measurement rule is preserved — the design notes call it out as the
thing no lifestyle pin has.

### Two render defects found by looking at the output

**Autofit was shrinking body type to ~8px** chasing a fit, straight through the
17px floor. Rewritten to concede in order: headline first, then body type **down
to but never through** the floor, then drop trailing rows — and it records
`rowsDropped` and `minBodyPx` on each card so the next run is checkable. The
validator's 3-row minimum holds the lower bound, so a card that cannot show
enough rows fails rather than rendering a stub. Final run: **0 rows dropped,
minimum body type 40px.**

**The note was being clipped and the autofit could not see it.** With
`justify-content:center` a flex column overflows equally in both directions and
`scrollHeight` can equal `clientHeight` — so the fit check passed while the note
was cut off the bottom. Body is now top-aligned with the note pinned to the
bottom, which makes overflow measurable.

### 3. 🔴 Unsplash is not connected

Verified against the connector registry: **no Unsplash tool is installed**, and
no image search of any kind. Reported rather than shipping a card with no band.

`src/photos.py` carries the sourcing contract for when one is: Unsplash first,
then the user's Golden Designs footage, **never manufacturer product
photography** (indexed on dozens of dealer sites, no uniqueness signal). It holds
a per-cluster shot brief, the design constraints (low-key, warm light in one
band, no people under 40, no towel-on-shoulder or meditation clichés), a local
cache with attribution and a 30-day no-repeat rule.

Until then the band renders the design bundle's own labelled photo well, stating
the shot it holds — *"Photo: infrared cabin and steam room in the same house, one
frame."* That is the design's treatment for this state: a card that names the
image it is missing, not one pretending it has one.

### 4. Cycle re-run, cards filled

**One batched call, 4/4 validator pass, $0.0161 per post**, 0 credits. Nothing
published.

Assets rendered at full size and at **236px**, the real Pinterest browse width,
plus a contact sheet on a pale ground. At 236px the dark ground and the
heat/cold accent columns hold against pale lifestyle pins, and the table
structure reads even where the cell text does not — which is what stops a scroll.

An intermediate attempt was rejected `HEALTH_UNHEDGED` on the EMF post; the
retry hedged and passed. The health gate is working on live output.

### Sweep

**169 tests pass** (was 156). Missing-value lint clean. Six legacy fixtures still
render at 1000×1500 through the Band template.

---

## 2026-09-02 — Round 8: zero-input operation, two tracks, supervised publish

### 0. Updated design adopted — "Plate"

The attached plate bundle is a genuinely different structure, not a repaint: the
timber runs the **full card** and a raised plate floats over it carrying the
headline, the table and the footer, with the kicker in its own capsule above.
Ground moves to a cooler, darker `#131416`. Extracted by rendering the bundle in
Playwright and reading the computed geometry, then ported into `cards.html`.

The design tokens embedded in the bundle are **identical** to the ones adopted in
Round 7, so nothing else changed.

### 1. Procedural band — the photo dependency is dead

The timber is now generated locally: tone, grain, one warm light band positioned
under the plate's top edge, and two hairline seams. Slat pitch, plank offset,
grain contrast, band position, height and lean all vary **deterministically from
the row id**, so consecutive cards differ. No text, no "placeholder" label.

Three consecutive cards rendered side by side to confirm the variation reads as
designed rather than repetitive.

**Real photography drops into the same `.well` at `inset:0` with no layout
change** — exactly the drop-in upgrade the brief asked for. Nothing depends on it.

### 2. Track B — the weekly finding

`src/probes.py`. Deterministic passes over the cached fact layer; **no model call
in the probe**. Seven families: disclosure gap, distribution, concentration,
trend, contradiction, climate, evidence quality. Each finding emits claim,
figures, dataset, fetch date, n and a notability score, and carries the chart
spec the card renders.

**Findings are single use.** `state/published-findings.json` is the ledger; a
corrupt ledger HALTS rather than silently resetting, because that is how a
finding gets republished.

First pass produced 9 above the floor — under the 10 the brief set as the
stop-and-ask. Rather than lower the floor I checked my own probes and found the
cause: I had guessed field names (`country`, `topic`) that do not exist on
`hrd_studies`, whose real axes are `design`, `journal`, `topics`, `year`. Fixing
the guesses and adding climate and evidence-quality families took it to **17
findings, 15 above the floor** — roughly 15 weeks of Track B from today's data
alone, before any refresh. The library was narrow because I wrote it narrow.

**Top 10 reported before any post was built from them** (full list in the round
report). One probe failing does not take down the library — `climate_probes`
raised a tuple-sort error on the first run, was reported, and the other six
still returned.

### 3. Chart band

Three types, all rendered locally from exact probe output: **dot** for disclosure
gaps (the block of `--flag` IS the finding), **range** for distributions,
**bar** for concentration and trend. No legends needing colour discrimination, no
multi-series lines, values inline so no axis is needed.

Checked at **236px**: all three carry their point as a shape. The bar's dominant
category, the dot plot's red tail and the range's span all read at browse size.

### 4. Destination

A finding links to the site holding its data, bypassing the router and exempt
from the per-URL cap — a finding is a one-off. Facebook only; the link goes in
the **first comment**, and any URL the model emits is stripped before the code
appends the real one.

### 5. `FINDING_UNSOURCED`

Rejects a finding that does not name its dataset AND its fetch date in the source
line. A weekly finding published without them is indistinguishable from an
opinion and cannot be checked by the reader. `EMPTY_BODY` extended to the new
`chart` archetype.

### 6. Cron wired, DISABLED

`.github/workflows/autoposter.yml`. Track A daily, Track B Tuesdays, both
`schedule` lines commented out; `workflow_dispatch` only. It gates on the
broken-post counter before doing anything, runs the sweep and the lint, refreshes
the fact layer, and appends its runlog entry on every outcome.

**Enabling it is a human edit.** Nothing in the codebase can flip it.

### The supervised cycle — 3 posts, published for real

Reported before publishing, then verified after.

| Track | Post | URL |
|---|---|---|
| A | Infrared vs Steam Sauna: What Actually Differs | https://www.pinterest.com/pin/902690319088929405 |
| A | Dry Sauna vs Wet Sauna: The Wood Question | https://www.pinterest.com/pin/902690319088929420 |
| B | Session cost by metro, $1.88 to $7.35 | https://facebook.com/472026422664772_122182409852647550 |

D5 breadcrumb dropped before each publish and cleared only after the id was
captured. All three read back from the platform with full text and media; all
three destination links return 200.

**The validator earned its place twice on live output this round.** Track A
attempt 1 was rejected `TEXT_OVER_SOFT_LIMIT` (422 and 399 chars against a 350
ceiling) and the retry fixed it. Track B attempt 1 was rejected for
`HEALTH_UNHEDGED` and two `UNGROUNDED_NUMERAL`s — and those two were **my prompt
leaking numerals**: the model had reused "$3,000-$15,000" from my own audience
description. Fixed at the prompt, which now spells quantities in words and says
so; Track B then passed first time.

### Cost, split by track

| | posts/week | tokens (this run) | cost |
|---|---|---|---|
| Track A (Pinterest) | 14 | 2,599 in / 2,063 out | ~$0.016/post |
| Track B (Facebook) | 1 | 833 in / 483 out | $0.0162/post |

Track B runs a longer brief per post but is one post against fourteen, so it is
**~7% of weekly model spend**. Weekly total lands near $0.24. Well inside the
ceiling, and the split is where the brief wanted it.

### Counter

**5 published, 0 broken, day 1 of 14.** 13 clean days before the cron may be
enabled.

### Sweep

**175 tests pass** (was 169). Missing-value lint clean.

---

## 2026-09-02 — Round 9: make the cards say something

The two live Pinterest cards were correct and empty of content: "Low / High",
"Lower / Higher", "Occasional / Regular", "Flexible / Limited". Not one number
between them, from a brand whose position is publishing measurements other
sellers will not.

### 1. `NO_FIGURE`

Rejects any `comparison`, `cost` or `spec` card with fewer than two cells
carrying a real value — number, range, unit, percentage, temperature, currency.
A comparative adjective is not a value: a cell made only of words from
`COMPARATIVE_WORDS` (lower, higher, flexible, limited, occasional, required…)
does not count. `checklist` and `evidence` are exempt; they are legitimately
qualitative.

**Both live cards fail it.** The approved reference card (130–150°F vs
110–115°F, 5–15% vs 100%, 240V/20 amps) passes. 12 parametrised cases pin the
figure/adjective boundary.

### 2. Feeding the generator numbers

`NO_FIGURE` is only fair if the brief carries figures, so `src/figures.py`
supplies them in order:

1. **the fact layer**, where it covers BOTH sides — 120V vs 240V models (71 vs 4,
   amp ranges, median price), 2-person spec (38–52 in wide, 68–78.6 in tall),
   metro cost ($1.88–$7.35, 13.1–52.7 c/kWh)
2. **figures extracted from the source article**, cached offline by
   `scripts/cache_article_figures.py` — a plain fetch, not a summarizer, because
   a summarizer reads prose and drops the tables (learning L19)
3. **nothing → the row blocks** rather than generating an adjective table

Coverage across the 90-row queue: **32% exempt, 54% with figures, 13% blocked** —
well under the 50% stop-and-ask. The article cache moved blocked from 31% to 13%.
The 12 still blocked are all infrared-vs-steam/traditional, where the satellite
guide pages are JS-rendered and yield nothing. That is a real content signal:
the network has no measured infrared-vs-steam comparison anywhere.

A gap this exposed: figure availability was being checked AFTER selection, so a
blocked row silently shortened the day — a 2-pin day published 1. It is now a
selection criterion, and the selector backfills.

### 3. Headlines that claim

Prompt rewritten: a headline says something the reader would not already assume,
or contradicts something they would. `WEAK_HEADLINE` rejects the filler patterns
outright, including the one that actually published — *"Infrared vs Steam Sauna:
What Actually Differs."*

Before and after, same pipeline:

| live | new |
|---|---|
| Infrared vs Steam Sauna: What Actually Differs | **Cedar lasts 15 to 25 years, but only in dry heat** |
| Dry Sauna vs Wet Sauna: The Wood Question | **71 of 90 saunas plug into a normal wall outlet** |
| | **90 models claim low EMF, only 34 say from how far** |
| | **Same 9 kW sauna costs $1.88 to $7.35 per session** |

### 4. Timber reworked

The first version was a flat vertical gradient — muddy, no depth, reading as a
placeholder despite being deliberate. Now: discrete slats with **tonal variance
between them** (each its own hue and lightness), irregular grain hairlines
*within* each slat at varying opacity and rake, a **soft warm falloff** instead of
a hard band, and a vignette so the plate sits on something. Still seeded per row
id.

Five consecutive cards rendered at 236px: the slat structure reads, all five
differ, and it no longer looks like a gradient artifact. Honest assessment: it
reads as a deliberate material, not as photography — which is what it is.

### Two bugs the round surfaced

**The Round 6 key-name bug recurred, in a new place.** "NOAA 1991-2020 normals"
reached the model through `facts_note`, the model cited it correctly, and
`UNGROUNDED_NUMERAL` rejected it because `grounding_text` walked only `facts`
values. Fixed by the general rule this time: **anything SHOWN to the model as
source material is IN the grounding** — notes, basis lines and the figures
payload. A test asserts every numeral in a fact note is reachable.

**A card shipped with `headline: None`.** The headline was only ever checked
archetype by archetype and no archetype listed it. It is now required on every
card, with a test that walks all six archetypes.

### Cycle

One call, **4/4 validator pass, $0.0178 per post**, 0 credits. Nothing published.
Before/after rendered side by side at full size and at 236px.

### Sweep

**210 tests pass** (was 175). Missing-value lint clean.

---

## 2026-09-02 — Round 10: more data sources, more contrast

### 0. 🔴 The black-and-white cards are not here

Searched the repo, full git history, `~/Downloads` and the whole `Claude Master`
tree. **No black-and-white card designs exist anywhere, and none were added to
the schedule.** The only design uploads received were the Round 7 zip (three
directions, all dark) and the Round 8 plate bundle (dark). Nothing was silently
dropped — they never arrived.

One near-miss worth naming: `~/Downloads/logo-1200-628.png`, dated 2026-09-02
10:53, never sent in a message. It is the **monochrome InHouse Wellness mark** —
black house outline and wordmark on white — which matches the logo request open
in `HANDOFF.md` since Round 1 ("monochrome mark for the 24px footer slot"). Cards
currently draw a generic house SVG instead. **Not adopted unilaterally**: it is a
brand asset and it is not what this round asked for.

### 1. Free public APIs — four connected, no keys needed

| source | rows | note |
|---|---|---|
| **CPSC recalls** | **196** | sauna, heater, infrared, hot tub. Nobody in the category publishes this. |
| OpenAlex | 194 | scholarly volume by year, two topics |
| ClinicalTrials.gov | 263 | what is being studied now |
| openFDA device events | 97 | adverse-event counts by device name |

Licences recorded per source in `fetch_facts.py`: all US federal public domain or
CC0, all permitting redistribution of derived figures with the attribution the
card's source line already carries. No stop-and-ask.

Three probe families added — recalls, trials, scholarly volume. **Findings above
the floor: 15 → 19**, five of them from the new sources:

- 58 sauna, heater and related recalls filed with CPSC since 2015
- Fire is the most common hazard across 231 filings — 129 of them
- China accounts for 84 of 154 recalled units by manufacturing country, 55%
- The median heat-therapy trial enrols 39.5 people; the largest enrols 3,257
- 51 of 263 registered trials are still running or recruiting

**Needing a key, listed together for one pass:** EIA (`api.eia.gov`, electricity
rates and history), Census (`api.census.gov`, housing stock — home size, basement
share, new build), FRED (`fred.stlouisfed.org`, electricity price and
home-improvement spend over time).

### 2. The infrared-vs-steam gap is closed — 12 blocked rows → 2

No compilation was needed. `infinitesauna.com/data/saunas.csv` already publishes
**190 models: 88 Traditional, 77 Infrared, 25 Hybrid**, with heater kW, voltage,
amperage, capacity, price, max temperature, weight and wood. It was the
traditional side the infrared-only index was missing, sitting behind a URL.

The network now holds a measured infrared-versus-traditional comparison:
140°F against 180–200°F, 15–30 amps against 1.2–50, $4,499 against $8,245
median, 250–920 lb against 475–1,763 lb.

**Queue coverage: 66% with figures, 2% blocked** (was 54% / 13%). The two
survivors are `sunlighten vs clearlight sauna` and `sauna costs`.

### 3. Contrast — 1.34:1 → **1.69:1 measured**

The plate and timber were two dark browns one step apart, so at browse width the
card read as a single mass.

- timber base `#3A2D1E` → **`#4A3826`**, warm falloff raised from .10–.17 to
  .20–.30 alpha, slat lightness lifted — it reads as lit wood, not shadow
- plate `#1B1613` → **`#161009`**, deeper and cooler, with an outer shadow
- **hairline top edge** `#2A2018`, one step lighter than the plate, so the seam
  is a deliberate line rather than a gradient
- **accent presence raised**: column fields .10 → .22/.20 alpha with a 3px
  leading edge in `--heat-dark`/`--cold-dark`; cost values and spec figures now
  carry the heat accent

Measured plate-to-timber at the seam: **1.69:1**, against a 1.60 target. Five
cards shown at 236px in a simulated column against pale lifestyle pins, before
and after: the tinted columns read as shapes where the text does not, which is
the whole point at browse size.

### 4. Re-run

Track A: one call, **4/4 pass, $0.0175 per post**. Track B: **$0.0142**, PASS.
Nothing published.

One validator catch worth recording. The model wrote "3,746" and "60" — the
price gap and the temperature gap — by doing **arithmetic on grounded figures**,
which `UNGROUNDED_NUMERAL` correctly rejects. The rule was not touched. Instead
the derivation moved into code: `infrared_vs_traditional` now emits
`temp_gap_low_f: 40`, `temp_gap_high_f: 60`, `price_gap_usd: 3746`,
`price_multiple: 1.8` as grounded facts the model may quote verbatim. Same
pattern as Round 9 — **supply the figure, never relax the rule** — and the
headline it wanted became legal: *"180 to 200F traditional vs 140F infrared,
$3,746 apart."*

### Sweep

**210 tests pass.** Missing-value lint clean. 10 datasets cached.

---

## 2026-09-02 — Round 11: DENOMINATOR_MISSING, the logo, and day 1 published

### 1. `DENOMINATOR_MISSING` — built before anything shipped

Any share finding must declare one of two things, and the probe author has to
choose; there is no silent default:

- **`baseline`** — the population share it is compared against, WITH a source
- **`population_is_the_subject`** — an explicit assertion that the finding
  describes the indexed population itself and implies no outside comparison

**The China finding is blocked**, as required. It is not emitted at all now, with
the reason recorded at the probe: China manufactures the large majority of home
saunas sold in the US, so 55% of recalls may well be *below* expectation, and the
bare share reads as nationality rather than consumer safety. If an import-share
source is added later, supply it as `baseline` and the finding becomes publishable.

The rule initially over-blocked — four findings, 21%. Three of those describe the
indexed population itself ("79% of indexed models run on 120V", "30% of indexed
studies are randomised", "Dynamic is 41% of the index") and were correctly
reclassified. One of my edits had also silently failed to apply.

**Final: 1 finding blocked, 5% of the list**, well under the one-third
stop-and-ask. Both other CPSC findings survive — 58 recalls since 2015 (rank 4),
and fire leading 129 of 231 filings. Findings above the floor: **18**.

### 2. Logo adopted

The supplied `logo-1200-628.png` is an integrated lockup: the house **encloses**
the wordmark, so the two do not separate by cropping, and the whole lockup is
illegible at 24px. Cropping was tried and produced a fragment.

**What I did:** redrew the house geometry as a stroked SVG path — apex, left
wall, baseline extending right under the name, rounded joins — matching the
supplied mark, and kept "InHouse Wellness" as live Fraunces beside it. It is
resolution-independent, crisp at 24px, and replaces the generic house SVG that
was there. Verified at 300px and at 32×24px against `#161009`.

### 3. Keyed APIs — wired, skipping

EIA, Census and FRED fetchers are built with endpoints, row normalisers, licence
notes and cache contract. All three **skip cleanly** and name themselves, because
no key is in `.env`:

```
EIA_API_KEY      api.eia.gov            electricity rates including historical trend
CENSUS_API_KEY   api.census.gov         housing stock: home size, detached share, new build
FRED_API_KEY     fred.stlouisfed.org    electricity price and home-improvement spend over time
```

10 of 13 datasets cached. Adding a key to `.env` is all that is needed.

### 4. ⚪ PUBLISHED — day 1 of the clock

| pin | |
|---|---|
| **Infrared vs Steam Sauna: 77 vs 88 Models Compared** | https://www.pinterest.com/pin/902690319088930991 |
| **Dry vs Wet Sauna: What Wood Actually Survives 10 Years** | https://www.pinterest.com/pin/902690319088931001 |

Both carry figures from the new traditional dataset: 40–60°F hotter, $3,746 more
at the median, 1.2–50 amps; near 100% humidity, cedar at 15–25 years. D5
breadcrumb dropped before each publish and cleared only after the id was
captured. Both read back from the platform with full text and media; both
destination links return 200.

**One relevance defect caught before publishing.** The first run produced a pin
headlined *"Traditional units cost $3,746 more than infrared"* pointing at a
wood-durability article — my figures regex matched bare "dry vs wet" to the
infrared-vs-traditional builder, so the card claimed a price finding while the
link answered a different question. A reader clicking that is a wasted click.
Tightened so the builder requires infrared to be named on one side; "dry vs wet"
now draws its own article figures and the card and destination agree.

Cost: **$0.0372 per post** (one retry on a health hedge), inside the ceiling.

**Counter: 7 published, 0 broken, day 1 of 14, 13 to go.**

### 5. Weekly metrics

Buffer still reports 0 Pinterest posts against our 7. The digest states that as
**not-yet-backfilled** rather than as zero reach — our pins publish through
Blotato and Buffer backfills natively-published pins on a daily refresh. The
earliest pins are now ~7 hours old. **If this still reads zero past 48 hours it
stops being a backfill lag and becomes a real signal**, and the Pinterest
measurement path needs re-examining. Loop stays `dry_run: true`.

### 6. Cron

Still disabled. Both `schedule` lines commented; `workflow_dispatch` only.

### ⚠️ On "run it again each day"

Only today's cycle could run — a session cannot advance the calendar. **The
counter moves one day per real day of publishing**, so reaching the 14-day gate
needs 13 more days of runs. The publishing path is proven end to end and is one
command: `python scripts/run_cycle.py --live` plus the publish step.

### Sweep

**216 tests pass** (was 210). Missing-value lint clean.


## 2026-09-02T22:12Z — Round 12

**Objective:** Buffer backfill check, `DESTINATION_MISMATCH`, Track A cron,
daily reporting, three API keys.

**What happened vs plan:**
- Buffer backfill: NOT concluded — only ~9h elapsed of the 48h the brief set.
  Evidence is one-sided though: Buffer backfilled a Blotato-published FACEBOOK
  post within 1.6h, while six Pinterest pins up to 9h old do not appear and
  Buffer's newest Pinterest row is still 2026-08-22 (the legacy system's).
  Definitive re-check 2026-09-04. Pinterest API fallback scoped, not built.
- `DESTINATION_MISMATCH` built and wired. First implementation compared figure
  ROW LABELS ("Amp draw", "Price, median") to destination titles and flagged
  68% of the queue — measurement vocabulary and subject vocabulary do not
  intersect, so it fired on correct pairings. Corrected to compare the entities
  the figures measure (`a`/`b` of the comparison payload). Final: 2 blocked of
  12 judged (17% of judged, 2% of the 90-row queue), both true positives.
- Cron NOT enabled. Blocked on a dependency, not on the counter: neither
  run_cycle.py nor run_finding.py can publish. Both stage and stop; `--publish`
  prints a notice. All 7 posts to date were published by hand through the
  Blotato MCP, which a GitHub runner cannot reach.
- Daily reporting built (`scripts/daily_report.py` → `state/daily-report.jsonl`
  + `REPORTS.md`), wired to run on `always()` so a halted run still files why.
- Three API keys: all absent. Skipped cleanly, no probes added.

**Failures + root cause:** the 68% false-positive rate was my own design error —
I compared the wrong two vocabularies. Caught by measuring against the real
queue instead of trusting the rule, which is why the brief asked for the rate.

**Friction:** "enable the cron" turned out to depend on a publish path nobody
had built, because every publish so far went through a human-only tool surface.
That gap was invisible from the workflow file, which reads as if it publishes.

**Cost:** $0 — no model calls this round.


## 2026-09-03T00:33Z — Round 12 (continued): the three keyed datasets

**Objective:** fetch, cache and add probes for EIA, Census and FRED.

**What happened vs plan:**
- All three keys present. My previous "all three absent" report was wrong:
  `load_env()` RETURNS a dict, it does not populate `os.environ`, and I read
  `os.environ` after calling it. The .env file was correct throughout.
- 13/13 datasets now cached. EIA 5,000 rows, Census 52, FRED 138.
- Three probe families added, four findings, all above the 0.45 floor:
  electricity state spread (8 kW hour: $1.05 Nevada vs $4.22 Hawaii, 4.0x),
  median-vs-mean placement, decade trend (+43% since 2015), detached-housing
  spread (61% national, 10% DC to 74% Idaho). Library: 25 findings, 23
  publishable.
- Buffer Pinterest backfill: still zero at 11.4h. 48h threshold falls
  2026-09-04T13:07Z. Not concluded, not declared broken.

**Failures + root cause:**
- The trend probe printed "43%" while its figures carried only the unrounded
  42.8 — UNGROUNDED_NUMERAL committed by the probe rather than the model.
  Caught by asserting every numeral in a probe's own claim is groundable, now
  a permanent test.
- The documented legacy-path test is wrong and would now false-positive: it
  keys on `via: network`, which is also what our own backfilled posts look
  like. Corrected in CLAUDE.md. Substantive conclusion unchanged — the legacy
  path is confirmed dead (newest legacy Pinterest post 2026-08-22).

**Friction:** I reported the keys absent last round on a broken check of my own,
after being told explicitly not to assume the file was wrong. The check itself
was the thing to verify first, and this time it was.

**Cost:** $0 — no model calls. No Blotato credits.


## 2026-09-03T01:13Z — Round 13

**Objective:** the REST publish path, the GitHub push, and a runnable workflow.

**What happened vs plan:**
- `src/blotato.py` built against Blotato's documented v2 API. Presigned upload
  reuses `src.media` rather than owning a second copy. Publish polls to a
  terminal state; an unresolved submission raises rather than reporting success.
  `verify_published` reads the post back. 20 tests, including the REST/MCP
  parity assertion the brief required.
- `run_cycle.py --publish` wired with the D5 breadcrumb down before each
  attempt and halt-on-first-failure. `--platforms` added: Track A is
  Pinterest-only, and without the filter the cadence map also yielded Instagram
  orders, which are out of scope and have no configured account.
- Loaders now read the environment first and `.env` second, so CI works with no
  file present.
- `scripts/check_fonts.py` proves the four woff2 faces load and do not fall
  back. Verified in both directions.
- Pushed to GitHub. Remote held ONE unrelated commit (a manual upload of 16 seed
  files). Merged with `--allow-unrelated-histories` rather than force-pushing,
  which would have discarded it. 14 of 16 files were byte-identical; the two
  that differed had evolved locally over Rounds 2-11 and local won those.
- Git history audited for secrets: **clean.** Only `.env.example` was ever
  committed, and the ten regex hits were documentation prose (`sk-ant-api03-`
  with nothing after it), not key material. No rotation needed.

**Failures + root cause:**
- `BLOTATO_API_KEY` returns 401 on every documented endpoint and header variant.
  Blotato's docs name stripped `=` padding as the usual cause, and the key is
  47 chars = a `blt_` prefix plus 43 base64 chars, where base64 wants a multiple
  of 4. That hypothesis was testable, so I tested it: appending one, two and
  three `=` all still returned 401. Reported as refuted rather than as the cause.
- My first font checker used `set_content()`, which has no base URL, so the
  relative `fonts/` paths could not resolve and every face fell back — the
  checker would have failed against a perfectly good template. Fixed to
  `goto(file://)` exactly as `render.py` does. It then reported every face
  "unloaded" because a @font-face is fetched lazily and `document.fonts.ready`
  resolves without loading unused faces; fixed by forcing an explicit load.

**Friction:** two of my three diagnostic tools were wrong before the thing they
measured was. Checking the checker first is becoming the reliable move.

**Cost:** $0.0402 for one live 2-post cycle ($0.0201/post — higher per post than
the $0.0120 measured at 6 posts, because fixed prompt overhead amortises worse
over a smaller batch). No Blotato credits.

## 2026-09-03T01:20Z — CI run 1
- outcome: success
- trigger: workflow_dispatch, track A, publish false

## 2026-09-11T14:48Z — Round 14

**Objective:** replace the daily-cron architecture with weekly batch scheduling,
and schedule a week live.

**What happened vs plan:**
- `scripts/schedule_week.py` built: plan / presign / upload / calls / record /
  reconcile. All judgement is in the script; the agent only relays precomputed
  MCP arguments, so "the LLM writes copy and nothing else" still holds.
- Slots: Pinterest 15:00 and 23:00 UTC daily (8h apart, not back to back),
  Facebook Tuesday 16:00 UTC. Local equivalents in the workflow and CLAUDE.md.
- A full week planned LIVE: 14 pins + 1 finding, 14/14 validated, all 1000x1500,
  15 media uploaded and byte-verified. Batch cost $0.3728, under the $1.00 ceiling.
- Cron retired but not deleted: the workflow now runs NON-PUBLISHING maintenance
  weekly (tests, lint, fonts, fact refresh), and the publishing steps are gated
  to workflow_dispatch only. The header records exactly what would re-enable it.
- **Scheduling did not happen.** See the failure below.

**Failures + root cause:**
- The first 14-post batch failed because captions retried ALL fourteen on every
  attempt: attempt 1 rejected one card, attempt 2 rejected a DIFFERENT one. Fixed
  so a retry re-requests only the rejected orders, and `parse_response` now
  reports every bad order rather than raising on the first. The retry prompt also
  had to state the expected array length, because naming the failures made the
  model return copy for only those posts. With that, the live batch converged:
  11 rejected, then 1, then clean.
- **BLOCKER:** the Blotato MCP tools exposed no parameter schema this session, so
  the harness serialised `mediaUrls` as a string and Blotato's validator refused
  it. Six attempts, three formattings. Not an API change: the same tool published
  with media on 2026-09-02, and Buffer accepted arrays in this very session.

**Friction:** two consecutive rounds have been blocked by the transport to
Blotato rather than by anything this system does. The content pipeline has been
ready both times.

**Cost:** $0.3728 (one 14-post batch + the finding). No Blotato credits.


## 2026-09-11T15:11Z — Round 14 completed

**Outcome:** the week of 2026-09-12 is scheduled. 15 posts, every resolved
`scheduledTime` matching the request, verified against the plan by `record`.

- The MCP schema never recovered in this session, so the 15 call argument sets
  were written to `out/weeks/2026-09-12/calls.json` and relayed through a
  session that had the typed schema. No regeneration, no extra model spend.
- `record` gained two things it was missing, both found by checking state rather
  than trusting the happy path: a scheduled post now marks its queue row used,
  and the finding is retired in the ledger. `plan` selects against a working
  copy, so before this the real posting-state had ZERO seen entries and next
  week would have reselected the same fourteen keywords and the same finding.
  Verified: next week's selection now overlaps this week's by none.
- Recorded that Blotato RE-HOSTS media and rewrites the URL. `reconcile` matches
  on submission id only, with a test asserting it never compares media URLs —
  that comparison would fail on all fifteen and report a clean week as broken.

**Friction:** the two gaps in `record` were invisible from a passing run. Both
only showed up by reading the state files afterwards and asking what next week
would do.

**Cost:** $0 this session. Round total $0.3728.

## 2026-09-14T11:14Z — CI run 2
- outcome: success
- trigger: schedule, track A, publish false

## 2026-09-14T21:15Z — Round 0 (Shopify build brief v2): spec table by join + state report

**Objective:** one versioned spec table assembled by joining existing sources,
plus an honest state report on the storefront. No feature code, no Liquid.

**What happened vs plan:**
- **The join needed no fuzzy matching at all.** The brief expected a brand/model
  string match against 673 SKUs. Both satellite CSVs already carry an
  inhousewellness.com product URL per row (`inhouse_url`, `source_url`), so the
  join is exact equality on the product handle. 142 distinct claimed handles,
  **142 resolve**. False-positive risk is zero by construction, not by threshold.
- That 142/142 is the shape of result this project has been wrong about before,
  so it was tested, not reported: `handle:<nonexistent>` returns nothing and the
  bare prefix `handle:dynamic` returns nothing, proving `handle:` is an exact
  filter and a dead URL fails rather than matching its neighbour.
- Match rate against the population that matters: **139 of 165 ACTIVE Sauna SKUs
  = 84.2%** (67.3% across all 211 including drafts and archives). Of the 69
  unmatched, only 26 are ACTIVE.
- `data/spec-table.json` built, 211 rows, every field either a value with source
  and fetch date or a null with a reason code. Missing-value lint: 0 findings.
- 270 tests pass (the brief says 254 — stale).

**Failures + root cause:**
- My first spec table reported a `model` conflict on all 142 rows. The bug was
  mine: I listed the Shopify product TITLE as a candidate reading of the model
  NUMBER. Two different quantities compared as one, so "conflict" fired
  everywhere and the count said nothing. Title moved to its own field; real
  conflicts fell to 9 fields, and each was then printed as a pair rather than a
  count (L7) to confirm it was a genuine source disagreement.
- The **satellite CSV endpoints are egress-blocked here** (403 on CONNECT), so
  the join ran on the repo's 2026-09-02 caches — a direct CSV parse, but twelve
  days stale. Flagged per field rather than silently accepted.
- `verify_destinations.py` reports 0/127. That is the environment, not the
  sites: every satellite domain is blocked. Reading it as 127 dead destinations
  would be L13 again, a whole-host failure read as evidence about the world.

**🔴 Two findings that change the plan, both for the user:**
1. **`/blogs/saunas/true-total-cost-home-sauna` is LIVE** (published 2026-09-09)
   on the same ~6,000–7,000/mo cluster Round 1 is for — and its front matter
   records a **client ruling of 9 September that installation cost is NOT
   published**, reader input only. Build Brief v2 §5 specifies a BLS-derived
   installation range. That is a rescope, not a rename.
2. **The store already holds the data the CSVs are thinnest on.**
   `custom.total_cost_disclosure` does not exist, but 65 PRODUCT metafield
   definitions do, and `custom.electrical_requirements` (68% of a stated
   50-SKU sample) reads "Voltage: 240V · Amperage: 30A · Dedicated 30A breaker".
   `custom.warranty_details` (~100%) already contains Round 2's whole schema.
   Prose, not structured — but a better first source than the satellites.

**Path confirmation: NOT completed, and not only for want of a token.** No
`.env` exists and there are zero `SHOPIFY_*` vars here; *and* the Admin API hosts
are themselves 403 on CONNECT. The Shopify MCP connector works over a different,
allowlisted transport — so a passing connector call would not have been evidence
for the cron path, and saying otherwise would have been the confident-false
result. `scripts/verify_theme_asset_path.py` is written, refuses on missing
credentials (verified) and refuses to touch the MAIN theme. That live-theme guard
never fired against Shopify, so per this repo's own rule it is exercised offline
via `--self-test`: 4/4 cases pass.

**Friction:** the most valuable half of this round came from checking the
*shape* of the sources rather than running the specified join — the URL column
that removed the matching problem, the `0 lb` weights that would have become a
freight number, and the metafields that make the satellite CSVs the second-best
source rather than the only one.

**Cost:** $0 model spend beyond this session. No Blotato credits. No writes to
Shopify — every call was a read.

**Round 1 NOT started.** Full report: `docs/round0-state-report.md`.

## 2026-09-14T22:05Z — Pre-round task: Actions workflow + freight tiers

**Objective:** two small things. Make the path verification runnable where the
cron actually lives, and find the real source of the three freight tiers. No
feature code, no Shopify writes.

**Task 1 — `.github/workflows/verify-theme-path.yml`.**
- Read `scripts/verify_theme_asset_path.py` first rather than assuming its
  interface. It reads `SHOPIFY_SHOP`, `SHOPIFY_ADMIN_TOKEN` and optionally
  `SHOPIFY_API_VERSION` (default `2026-07`).
- **Nothing is installed, and the workflow proves it rather than asserting it.**
  The script imports only argparse/json/os/pathlib/sys/urllib — all stdlib — so
  the `--self-test` step runs on a bare `setup-python` interpreter with no pip
  install at all. If a third-party import ever creeps in, that step fails on
  ModuleNotFoundError instead of being silently carried by `requirements.txt`.
  Deliberately does NOT install requirements.txt, which pulls Playwright.
- `workflow_dispatch` only. No `schedule`, no `push`: the probe writes to a
  theme on a live commercial store's account, so it runs when a human asks or
  not at all. `permissions: contents: read` — it commits nothing.
- Safety in layers: self-test runs BEFORE any credential is used; the default
  theme id is `146147868739` (Round 11), re-verified UNPUBLISHED this session
  against MAIN `146149867587`; and the script refuses `role == MAIN` regardless
  of what id is passed.
- The token is confirmed by LENGTH only and never interpolated into a shell
  string. Both branches of that step were exercised locally: present -> prints
  `len=`, missing -> halts non-zero.
- Store domain is set literally, not as a secret — it is public on every page —
  so **`SHOPIFY_ADMIN_TOKEN` is the only thing a human must provision.**

**Task 2 — the freight tiers are sourced, and they are not prose.**
`data/shipping-facts.json` is still absent. Rather than reconstruct it from the
article, the figures were re-sourced from the live store, and all three are
things a customer can actually transact:
- **free curbside** — delivery profile "General profile" (default), Domestic
  zone, method `Standard`, $0.00, active
- **$600 inside delivery** — product `white-glove-delivery-service`, ACTIVE
- **$1,800 inside and assembled** — product `installation-assembly`, ACTIVE
Written to `data/freight-tiers.json` with per-figure source and fetch date.
This mattered because `inh-seo/CLAUDE.md` records that `shipping-facts.json` was
marked `verified_by: client, discrepancies_found: none` **and was still wrong**,
because the page it was verified against was wrong — and that error reached 36
live collection pages. An article and a policy page are not two witnesses when
one is derived from the other.

**Findings + root cause:**
- 🔴 **The $1,800 contradiction is not fixed — it moved.** The product body now
  reads "$1,800, all in ... There is no separate assembly labour bill
  afterwards", matching the CLEAN fixture in `term-contradictions.mjs`. But the
  `custom.shipping_details` metafield on sauna pages still describes "Premium
  Installation & Assembly (Optional)" with "Installation labor: $50–$75/hr per
  installer". Same contradiction, different field. The sweep covers product
  bodies and collection copy, **not metafield values** — the
  intersection-of-complements failure `inh-seo/CLAUDE.md` already names. Seen
  byte-identical on 2 of 3 sauna products read, so it is a shared template, not
  one stale row. **Spread not measured; 2-of-3 is a sample, not a rate.**
- 🟡 An **$80 "Economy" domestic shipping method is active** alongside the free
  "Standard", priced above it, and is named nowhere in the copy that says
  "free curbside shipping, no minimum". Reported, not resolved.
- Installer/electrician hourly ranges are kept in a **separate** block from
  InHouse's own charges and are never summed with them. The $50–$75/hr installer
  range is recorded as AMBIGUOUS rather than classified, because it sits under a
  heading naming InHouse's own service.

**My own error, corrected:** the Round 0 report claimed "the missing-value lint
passes with 0 findings" and that it "was run against the new spec table". It was
not — the lint ran early in that session, before `build_spec_table.py` existed,
and was never re-run. Against the finished script it produced **30 findings**.
All 30 were the `.get()`-into-helper shape on `blank()`, `num()` and
`handle_of()`; each was then *proved* None-safe (and proved not to swallow `0`)
before being added to the linter's `NONE_SAFE` set, and the linter was
re-checked against a deliberately-broken canary to confirm it still fires. Lint
is clean at 0. **No spec-table value changed** — the error was in the reporting,
not the data. Both claims are annotated in place in the Round 0 report rather
than quietly rewritten.

**Sweep before commit:** 270 tests pass; missing-value lint 0 findings.

**Cost:** $0 model spend beyond this session. No Blotato credits. No writes to
Shopify — every call was a read.

**Round 1 NOT started.**

## 2026-09-14T23:40Z — Round 1: True Total Cost, the data layer

**Objective:** a complete, lint-clean cost dataset for active sauna SKUs, with
per-field provenance. No calculator, no sections, no pages.

`agent-harness` and `build-loop` WERE available this session and were loaded
(they were not in Round 0). Reporting is in-session; no Slack channel exists.

**🔴 Environment constraint that reshaped Phase 2 before it started.** Every
external host this round needed is blocked by the organisation egress policy
(403 on CONNECT): all ~7 manufacturer domains, `api.eia.gov`, the
`outdoorsteamsauna.com` 75-metro feed, and both satellite CSVs. So source
precedence tier 1 — manufacturer websites, the client's stated most-accurate
source — **could not be consulted at all**. Tiers 2-4 were worked in full. The
EIA layer is the committed 2026-09-03 cache (period 2026-06); staleness is
recorded per field rather than refreshed.

**Phase 1 — census, not sample.** All 165 ACTIVE sauna SKUs scanned, coverage
asserted against the population before any rate was computed.
- **113 of 165 (68.5%)** carry the stale installer-labour line, across **5
  distinct metafield values** in 2 structural shapes. Round 0's "2 of 3" is
  replaced by a rate.
- The contamination is confined to exactly one key. `custom.delivery` (108
  present), `custom.product_details` (161), `custom.why_inhouse_wellness` (148)
  and `custom.return_policy` (0): **zero hits**, censused across all 165.
- Product bodies and all 94 collection descriptions: clean. Collection copy
  already states the tiers correctly.
- **Why the earlier sweep missed it, demonstrated rather than asserted:**
  Shopify's product search indexes bodies but NOT metafields. 113 products carry
  "installer" in a metafield and `products(query:"installer")` returns 6. That is
  the intersection-of-complements gap `inh-seo/CLAUDE.md` names, with a number
  on it.

**Failures + root cause — three real bugs, all caught by looking at pairs
rather than counts, and all of the same family:**
1. **My first transform mangled a template.** One of the 5 packs the whole
   section into a single list item; the list transform dropped the item and took
   three unrelated sentences with it. **The rate probe PASSED that output** — the
   defect was gone and content had silently vanished. Fixed by trying the precise
   sentence transform first, and by adding a sentence-survival guard that is
   itself proved against the known-bad transform.
2. **"1,800 watts" parsed as 800 W.** The wattage regex had no thousands
   separator, so three SKUs became 0.8, 0.75 and 0.2 kW. Every structural check
   passed. A 0.2 kW sauna would have gone straight into the running-cost line —
   the one number the competing SERP already gets wrong. Fixed, and a
   plausibility band (0.8-30 kW) now refuses the class rather than the instance.
3. **29 false "volts conflicts".** A cabin stating "240V/30A (stove)" and
   "120V/15A (lighting)" has two circuits, not a contradiction. Recorded as
   `MULTIPLE_CIRCUITS_STATED` with all readings kept; picking the larger silently
   would have asserted a spec nobody stated. Likewise "6 kW fitted, 8 kW optional"
   is `RATING_DEPENDS_ON_CONFIGURATION`, not a conflict for a human to adjudicate.

**The maxxus conflict is resolved, and ruling 5 did it.** `maxxus-3-person-sauna-hemlock`:
`custom.electrical_requirements` states "Power Supply: 120V / 20AMP dedicated
circuit ... operates at 1,900 watts". Metafields outrank satellite CSVs, so
**120V stands** — BHIS was right, the infinite feed's 240V is wrong — and the
same span yields 1.9 kW and a dedicated-circuit flag. No manufacturer site was
needed.

**Phase 3.** `data/cost-tables.json`: 165 rows, 311 KB, schema 1.0.0. Freight as
three flat constants. Energy at state granularity, **51 of 51 jurisdictions**.
EIA's 10 census-division aggregates and its national row are stored in a
separate, explicitly non-fallback block — leaving `US` among the states is how an
uncovered ZIP quietly becomes a national average. **No installation or
electrician figure appears anywhere in the file**, per rulings 1 and 3.

**Lint, run at the END this time.** Round 0's correction was that a lint run
before the code existed proves nothing. So the scan scope was verified to
actually include the new scripts (43 files, all four named), a canary violation
was planted to confirm the lint still fires, then removed. 0 findings. 270 tests
pass.

**Friction:** the MCP tool saving oversized results to disk turned a census that
looked unaffordable into a cheap one — every scan ran over files rather than
through context. It is also what made "census, not sample" the easy option
rather than the expensive one.

**Cost:** $0 Anthropic spend — this round made no model API calls; all extraction
is deterministic code. No Blotato credits. **No writes to Shopify: every call was
a read.** Phase 1 awaits approval.

**Round 2 NOT started.**

## 2026-09-15T01:30Z — Round 1b: apply the fix, move the fetchers to Actions

**Objective:** apply the approved metafield correction, and move every external
fetch into the environment that can actually reach the internet.

`agent-harness` and `build-loop` loaded. Egress re-checked at round start:
`api.eia.gov` and the manufacturer hosts still 403 on CONNECT. No external fetch
was attempted from this session.

**Phase 1 — applied. 113 SKUs, first write to a live commercial store.**
- Pre-write state captured for all 165 ACTIVE sauna SKUs, and every one of the
  113 verified against the approved proposal by content hash BEFORE writing.
  **Zero drift** — all 113 still carried exactly the value that was reviewed.
  Product ids were resolved at write time, never taken from the proposal.
- A **single-product pilot** went first and was hash-checked against the approved
  value before the remaining 112. It matched byte for byte. Only then did the
  batches run.
- Sent as aliased mutations with the value as one GraphQL variable: the 4.4 KB
  payload travels once per call instead of 25 times, which cut the transcription
  surface from ~110 KB to ~8 KB per batch. 8 calls, **zero `userErrors`**.
- Verification, as separate read calls from the ones that wrote:
  1. stale line across all 165 → **0 matches** (probe re-checked against its
     known-positive control first, so the zero means something);
  2. 113/113 byte-identical to the approved value;
  3. the 52 SKUs NOT on the approved list → **0 changed**;
  4. the sentence-survival guard re-run on the **live post-write values**, not on
     the proposal → 0 lost sentences on all five templates.

**Phase 2/3 — fetchers written, not run.**
- `src/power_parse.py`: the guards now have ONE definition, imported by both the
  builder and the new fetcher. The brief asked that any new source run through
  the comma-aware wattage parser and the 0.8–30 kW band; importing rather than
  copying makes that structural instead of a promise. It carries its own
  known-positive self-test and asserts the band rejects exactly the values the
  comma bug produced (0.2, 0.75 kW).
- Refactoring the builder onto it was proved value-neutral: rebuilt output is
  identical except one additive `source_url` key, and every `rated_power_kw`
  value is unchanged.
- `fetch-manufacturer-specs.yml` + `scripts/fetch_manufacturer_specs.py`:
  robots.txt honoured per host (an unreadable robots.txt is treated as "don't",
  not as permission), one request at a time with a delay, Retry-After honoured,
  and a User-Agent that says who we are and how to be excluded. 429/5xx are
  backoff, never "no data".
- `fetch-external-data.yml` reuses the existing `scripts/fetch_facts.py` rather
  than adding a second fetcher — it already parses all 13 datasets, including
  both satellite CSVs and the outdoorsteamsauna 75-metro feed, directly from
  their endpoints. Added `--only` with a guard that makes an unknown name an
  error, plus a post-refresh floor check so a truncated response fails loudly
  instead of shrinking a dataset into a "finding".
- `scripts/fetch_zip_state.py`: Census ZCTA→county relationship file, column
  indices read from the header rather than assumed by position.

**Failures + root cause — four, all caught by checking rather than assuming:**
1. My refactor left `DED_REQ_RX` undefined and the build raised. The diff I ran
   immediately after reported "byte-identical" — **because the file had never
   been rewritten**. Absence read as success, in my own verification step. Fixed,
   and the re-check now asserts the file was regenerated before comparing it.
2. The fetcher read vendor from `cost-tables.json`, which has no `brand` field.
   It returned `None` for all 165 and would have produced a clean-looking run
   that fetched nothing. Vendor now comes from the committed snapshot.
3. `fetch_facts.py` had no `--only` flag, so the workflow I wrote would have
   failed on first use. Added — and the guard I added with it then rejected
   `eia_electricity`, a real dataset, because my `known` set missed the third
   source dict. The guard caught my own bug.
4. My merge fixture asserted a disagreement would be recorded for a SKU whose
   metafield states no kW at all. The code was right and the fixture wrong;
   re-tested against a SKU that does have one, and the pair is recorded.

**🟡 Every `product_url_template` in the manufacturer registry is null, deliberately.**
They were written from a session that cannot fetch a single manufacturer page. A
URL template that has never been tested is a guess, and a guessed template does
not fail safely — `inh-seo/CLAUDE.md` records a followed redirect answering from
a category page while the requested URL was a product page, putting a category
FAQ into a report as a product spec. So the fetcher skips null templates and
records `NEEDS_URL_TEMPLATE`, and the workflow has a `discover` mode that probes
robots.txt and the homepage per vendor from Actions and commits the evidence.
**Fill the templates from that run, not from memory.**

**Also reported:** the brief says "~15 manufacturers"; the catalogue has **11**
behind the 139 matched active SKUs. Reported rather than rounded to the brief.

**Cost:** $0 Anthropic spend — no model API calls; all parsing is deterministic
code. The only Shopify writes were the 113 approved metafield updates.

**Round 2 NOT started.**

## 2026-09-15 — Actions runner parity, and gates moved ahead of the network work

**Trigger.** `fetch external data` run 3 failed on `No module named pytest`
after a fully successful refresh: 13/13 datasets in 17s, shrink floors cleared,
missing-value lint 0 findings, ZIP table built (33,505 single-state ZCTAs). The
commit step was skipped, so three runs produced no persisted data.

**Diagnosis — one class, three instances.** Runs 1–2 failed on absent scripts
(`fetch_zip_state.py`, `power_parse.py` were on a branch, the workflow on main);
run 3 on an absent package. In every case something present on the dev host was
absent on the runner, and the absence surfaced at the point of use rather than
at the start. Root cause of run 3 specifically: `autoposter.yml` carried
`pip install python-dotenv anthropic imageio-ffmpeg` as a second, hand-written
line, so the complete dependency list lived inside one workflow rather than in
`requirements.txt` — and the two fetchers, which install from the manifest,
could not inherit it.

**Fixed.**
- `requirements.txt` now declares `python-dotenv`, `anthropic`, `imageio-ffmpeg`
  (unpinned, exactly as autoposter installed them — a move, not a version
  change). The hand-written pip line is gone; every workflow installs `-r
  requirements.txt` and nothing else.
- `scripts/preflight.py` (new, stdlib-only, with `--self-test`): `--deps` walks
  the AST of `src/`, `scripts/`, `tests/` and fails on any third-party import
  the manifest does not declare; `--workflow-paths` asserts every `.py` a
  workflow names exists in the checkout; `--stdlib-only` asserts by AST that the
  outward-reaching scripts import stdlib + local only; `--imports` proves the
  install delivered. Runs in all three installing workflows and in the suite.
- The "bare interpreter proves no third-party deps" step was environmental and
  stopped holding the moment this job needed pytest. Kept (it still runs before
  any install) but now backed by the AST assertion, which does not depend on
  what the runner happens to have.

**Step order — gates partitioned by what they depend on.** Verified that
`lint_missing_values.py` scans `*.py` only and that the suite's sole reader of
`data/facts` asserts the *committed* caches are intact. Neither can observe a
refresh, so both moved ahead of the fetch; `scripts/check_facts_cache.py` is the
only post-fetch gate. Commit was NOT moved ahead of the test gate — that would
land data from a tree the run believes is broken. Reasoning recorded in
CLAUDE.md and at the top of the workflow.

**Gate strengthened, not weakened.** The shrink check was ~40 lines of Python
inside the YAML — data at a call site, logic no test could see. Now
`scripts/check_facts_cache.py`, which additionally asserts each dataset parses,
carries a `fetched_at`, and that `row_count` equals `len(rows)`. Fetched data
uploads as an artifact under `if: always()`, so a halt no longer destroys it.

**Also fixed in the audit.** Dispatch inputs were interpolated straight into
`run:` blocks (`${{ }}` is textual substitution — a shell-metacharacter input
would execute); they travel through `env` now. `git add … 2>/dev/null || true`
in the manufacturer workflow silenced real failures as well as expected absence;
each path is now added only if it exists.

**Cache integrity after three aborted runs: clean.** No `inh-fetcher[bot]`
commit exists in any branch, so nothing was ever pushed. All 13 committed
datasets parse, are dated 2026-09-02/03, `row_count == len(rows)`, and are
byte-identical to HEAD. `data/zip-to-state.json` has never been tracked — it is
an output of the first successful run. Now asserted by
`tests/test_facts_cache_gate.py` rather than checked by hand once.

**Open, not fixed — needs a decision.** `autoposter.yml` runs
`scripts/fetch_facts.py` on its weekly schedule but commits only `state/`,
`REPORTS.md`, `RUNLOG.md`. Its fact-layer refresh is therefore discarded on
every run, which is the same shape as the bug above. Left alone because it
changes what a scheduled job commits.

**Verification.** 285 tests pass (was 270). `preflight --self-test`,
`--static`, `--imports` clean; `check_facts_cache --self-test` and the gate
itself clean; missing-value lint 0 findings; all four workflow YAMLs parse and
their triggers are unchanged.

## 2026-09-15 — the EMF grounding test: diagnosed as source change, not regression

**Trigger.** `fetch manufacturer specs` run 2 failed at Sweep: 284 passed, 1
failed — `test_source_data_grounding_round_trips`, asserting `"71"` appears in
the EMF grounding text. `fetch external data` run 5 had committed refreshed
satellite caches minutes earlier (`e5e1498`).

**Verdict: (a) the source legitimately changed.** Five independent lines of
evidence, from the git history of the cache either side of `e5e1498`:

1. **`last_checked` advanced on all 87 surviving rows**, `2026-08-31` →
   `2026-09-14`. That is the publisher's own freshness stamp, a column inside the
   CSV. A truncated or mis-parsed fetch can drop or garble a value; it cannot
   advance one. This is positive proof of republication.
2. **The removals are interior.** Rows vanished at indices 7, 11 and 50 of 90;
   the last five rows are byte-identical and order is preserved throughout
   (`AFTER == BEFORE minus the three rows` exactly). Truncation removes a
   contiguous suffix.
3. **The parser cannot selectively drop rows.** `fetch_facts.fetch()` is
   `list(csv.DictReader(io.StringIO(body)))` over the whole response — no dedup,
   no filtering. `row_count` *is* the CSV's data-line count. (The `seen` dedup in
   `fetch_facts` is in `fetch_api`, a different path.)
4. **The duplicate resolution was editorial.** 90 → 87 is −3, but only 2 slugs
   disappeared; the third was `gdi-6880-02-elite`, which had **two conflicting
   records** — SKU `GDI-6880-02 Elite` vs `GDI-6880-02-Elite`, price $9,999 vs
   $14,999, MSRP $14,999 vs $19,500, different `source_url`, one with dimensions
   and one without. The publisher fixed a real data-quality problem.
5. **Control: the other satellite gained rows** (`infinite_saunas` 190 → 195) on
   the same `csv.DictReader` path, and `outdoor_cities`/`outdoor_climate` held at
   75. Nothing is systematically dropping rows.

Arithmetic closes exactly: `Near Zero EMF` 71 → 68, and the three removed rows
were all labelled `Near Zero EMF` (2 Dynamic + 1 deduped copy). Every invariant
in the new drift checker passes against the refreshed data.

Direct verification against the live CSV is not possible from this session —
`besthomeinfraredsauna.com` still answers **403 on CONNECT** — but the
`last_checked` column makes the source's own intent unambiguous without it.

**The structural fix.** `test_source_data_grounding_round_trips` was the ONLY
test in the suite pinning literals from refreshed external data (line 656 derives
its numbers from `sd["note"]`; line 664 uses a hand-built payload). It now
asserts shape, provenance, extractability and internal consistency — never a
value. Content is watched by `scripts/check_facts_drift.py`, post-fetch, which
reports every moved metric to the run summary and exits 0, halting only on
something no publisher edit can produce. Full rationale and the stated tradeoff
are in CLAUDE.md.

Proven, not asserted: `tests/test_facts_drift.py` (11 tests) shows both
90/71/46/34 and 87/68/43/32 pass the invariants, that the real refresh reports as
drift with `emf.top_labels[0][1] 71 -> 68` named, and that four corruption classes
still halt — an emptied label column (row count intact, every number still
extractable: the case a shape-only test would miss), a truncated cache, a swapped
dimension column, and a cluster disappearing. The workflow step's shell was
extracted and executed under `bash -e` for both outcomes.

**A trap caught in my own design.** The first version of the baseline test
asserted `drift == []`. Since the fetcher commits a refreshed cache without
touching the baseline, that test would have failed on the run *after* every
refresh — the original bug rebuilt one layer down. It asserts breach-freedom
only, and CLAUDE.md now forbids asserting drift-freedom anywhere.

**Nothing partial was committed, and the pre-fetch ordering did its job.**
Run 2's job steps: Sweep failed at step 7; **Discover, Fetch, Rebuild and Commit
all show `skipped`**, and the `if: always()` artifact step ran and found nothing.
Zero outbound requests reached any of the eleven manufacturer hosts — under the
old ordering the crawl would have completed and then been discarded. No
`manufacturer specs:` commit exists on any branch and neither
`manufacturer_specs.json` nor `manufacturer-discovery.json` is tracked or on
disk. The external-data commit was atomic: all 13 datasets, all stamped
`2026-09-15T02:54`, in one commit.

**Verification.** 296 tests pass (was 285). `check_facts_drift --self-test`
clean; invariants clean against the committed cache; no drift against the
committed baseline; `check_facts_cache` clean; preflight `--static` clean; the
workflow YAML parses with triggers unchanged.

## 2026-09-15 — discover run 3: 11 vendors probed, 0 templates fillable

**The run.** `fetch manufacturer specs`, mode `discover`, succeeded on main
(`81e1ab3`), 1m38s, committed `d3e27ce`. Pre-crawl gates all green: power_parse
self-test, preflight `--static`/`--imports`, 296 tests, lint 0 findings.

**Reachable (6 of 11)** — robots.txt readable and allowing `/`, homepage 200:
Maxxus, Golden Designs Inc, Scandia, SaunaLife, Medical Saunas, Finnmark Designs.

**Unreachable (5 of 11)**, all failing at robots.txt so the crawler will skip them:
Dynamic Saunas (38 SKUs — TLS `CERTIFICATE_VERIFY_FAILED`, self-signed cert),
Dundalk Leisurecraft (7 — robots.txt 404), Mande Spa (3 — `TLSV1_ALERT_INTERNAL_ERROR`),
Kohler (2 — read timeout), Ripavi (2 — `Errno 101 Network is unreachable`).
That is 52 of 139 matched SKUs behind a host we cannot read, Dynamic Saunas alone
being the largest vendor in the catalogue.

**No vendor disallows crawling.** All 5 failures are transport or absence, not a
`Disallow`. Kohler's registry note predicted a strict robots.txt; it timed out
instead, so that prediction is still untested.

**Warning annotation (1):** `Node.js 20 is deprecated. The following actions
target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4,
actions/setup-python@v5, actions/upload-artifact@v4.` Flagged in the previous
round's audit and deliberately not changed then; it is now a live annotation and
will eventually be a hard failure. Not bumped here either — it was outside this
round's ask.

**Product-URL evidence found: none, for any vendor.** Discover as written requests
`/robots.txt` and `/` only. The sole URL information in the output is `final_url`
after redirect, which points at a homepage. **All 11 templates stay null.**

**Two deeper faults the run exposed, both recorded, neither fixed:**
1. `product_url_template.format(handle=handle)` substitutes OUR Shopify handle
   into THEIR URL space — `arosa-4p-barrel-sauna`,
   `1-2-person-infrared-sauna-hemlock-chromotherapy`,
   `hand-finished-precut-sauna-kit`. Even a correct path shape would request
   pages that cannot exist.
2. Every registry row declares `model_key` (`sku` × 9, `title` × 1) and
   `scripts/fetch_manufacturer_specs.py` never reads it — verified by grep.

**One registry error corrected from evidence.** `Golden Designs Inc` base was
`www.goldendesignsinc.com`; the run's own `final_url` shows it redirects to
`goldendesigninc.com` (no `s`). Corrected, with the evidence recorded in
`base_evidence`. A test now asserts no discovered redirect is left unactioned —
and it is written so that fixing one does not make the test fail, by judging each
record against the base it was actually probing rather than against the current
registry. The naive form of that assertion goes stale the moment it succeeds, the
same shape as asserting drift-freedom against a fact baseline.

**Discover upgraded so the next run can settle it.** It now harvests: `Sitemap:`
directives already in the robots.txt we fetched (free), those sitemaps with one
level of sitemap-index following and a robots check before each request, product
links from the homepage body we already had and used to discard, and — decisively
— whether any REAL product URL of theirs contains one of OUR SKUs (trying the
space/hyphen renderings, since our catalogue holds `MX-M356-01-FS CED`). Capped at
6 sitemaps and 8 MB per vendor; still stdlib-only, asserted by
`preflight --stdlib-only`. 25 offline tests against synthetic sitemaps, because no
manufacturer host is reachable from a session (verified again: HTTP 000, CONNECT
refused, for maxxussaunas.com, goldendesigninc.com and saunalife.com).

**A live breakage on main, found and fixed.** The discover run committed
`data/facts/manufacturer-discovery.json`, a per-vendor report with no `rows`.
`scripts/check_facts_cache.py` assumed every file under `data/facts/` was a row
dataset and failed with *"has no rows list"* — so `pytest` in the **Sweep step of
both fetchers** was broken on a correct file. Run 3 itself passed because the file
did not exist at checkout; the next run of either workflow would have failed. The
gate now decides dataset-vs-report by shape rather than by a filename list, and
treats one of `rows`/`row_count` without the other as corruption. Third instance
of the same lesson after the EMF literal and the drift baseline: a gate that fires
on correct data costs more than the gate is worth.

**STOPPED before `mode: fetch`, as instructed.** No product page was requested.

**Verification.** 325 tests pass (was 296). preflight `--static` clean,
`check_facts_cache --self-test` and the gate clean (13 datasets + 1 report),
`check_facts_drift` clean, lint 0 findings, `python3 src/power_parse.py` clean on
a bare interpreter.

## 2026-09-15 — Phases 1 & 2 done, Phase 3 built and blocked on egress

**Phase 1 — census of our own pages, zero egress to any vendor.** Pulled all 165
active `productType: Sauna` products via the Shopify MCP connector (4 pages,
`descriptionHtml` + up to 50 metafields + variant weights; no product hit the
metafield cap). Handle set matches `cost-tables.json` exactly, 165/165.

**The brief's premise was wrong, and checking it was the whole value of Phase 1.**
There is not one `.pdf` href on the store. Every document reference is a Google
Drive `iframe` in `custom.product_documents`. A census grepping the body for
`.pdf` would have reported ~0% coverage.

**Coverage, all 165:** manual candidate 102 (61.8%) · any document reference 106
· video-only 4 · model number 32 (19.4%) · model number equal to our SKU 16 ·
shipping weight in text 78 (47.3%) · non-zero Shopify variant weight 103 (62.4%)
· box count 70 (42.4%).

**The 2×2:** 1) manual + model 13 (7.9%) · 2) manual only 89 (53.9%) ·
3) model only 19 (11.5%) · 4) neither 44 (26.7%).

**A correction I made to my own first number.** The first pass reported 106
manuals. 35 of the 180 Drive embeds sat in `custom.video` — videos. Role now
comes from the source field, and the honest figure is 102. Medical Saunas moved
13→0 in bucket 2 as a result: all four of its "manuals" were videos.

**Cross-tab, buckets 3 and 4 at the 5 unreachable vendors** (53 SKUs): Dynamic
Saunas b3=3 b4=13, Kohler b4=2, and Dundalk / Mande / Ripavi **zero in both** —
every one of their 12 SKUs already carries a manual on our page. **The email list
is 15 SKUs: 13 Dynamic + 2 Kohler**, listed with SKUs in the report. 26 of the 39
Dynamic SKUs are reachable through our own pages despite their host being dead.

**Phase 2 — the SKU→URL key.** Of 139 matched SKUs, **26 (18.7%)** now carry a
manufacturer model number and 94 (67.6%) a manual. 16 of the 32 model numbers
equal one of our own SKUs exactly.

**Maxxus and Golden Designs do NOT share a scheme in our data.** Maxxus `MX-`
34/34 SKUs and 9/9 model numbers; Golden Designs `GDI-` 37 of 38 SKUs and 7/7
model numbers, plus a single `DYN-` SKU. Cross-branding runs the other way. The
screenshot's claim is about their *site*, which our catalogue cannot settle — but
the upgraded discover tests our SKUs against their sitemap and answers it free.

**Three parser bugs found and fixed while building, each pinned by a test:**
`(?i)` made the `[A-Z]` next-label terminator match lowercase, producing the
capture `MX-K406-01 CED Capac`; a three-character floor on lowercase words let
`is` through, so `MX-1 is the best sauna` trimmed to `MX-1 is`; and a capture
requiring terminal punctuation found a model number in a rich-text block but not
in a flat field — one fact with two answers depending on storage format.

**The project's own lint caught my code**: `flatten_metafield(m.get("value"), …)`
consumed a `None` silently. Fixed with an explicit branch, not a `# missing-ok`.

**Phase 3 — built, self-tested, NOT run.** `scripts/extract_manual_specs.py`
imports both guards from `src/power_parse.py` and adds two rules: a
*recommendation* is never a rating (the Dundalk "8 kW recommended" case), and a
spec plate outranks marketing copy. Every reading carries kW, basis, tier, page
number, verbatim span and URL; implausible values are recorded as rejected, never
dropped or clamped. Proven against a text-layer PDF constructed in
`tests/test_manual_specs.py` — page numbers, spans, the 1,800 W case, the 200 W
band rejection, the recommendation rule and the tier ordering.

⛔ **No real pair exists yet.** `drive.google.com` answers 403 on CONNECT from a
session, exactly like every manufacturer host. The extractor was run at
`--limit 2` and recorded four honest `FETCH_FAILED` rows; that artifact was
deleted rather than committed. `.github/workflows/fetch-manuals.yml` runs it on a
runner, `limit: 5` by default, gates before the fetch. **Dispatch that to get the
five pairs. Nothing scales until they are read.**

**Verification.** 368 tests pass (was 325). preflight `--static`/`--imports`
clean, both new self-tests clean, cache gate clean, drift clean, lint 0 findings,
`power_parse` clean on a bare interpreter, all five workflow YAMLs parse with
triggers unchanged.

## 2026-09-15 — `fetch manuals` run 1: 9 real PDFs, 278 pages, zero ratings

**The run.** limit 5 → 5 products, 9 manual candidates, all fetched. Status OK on
all nine. **Zero accepted readings. Three rejected, all on one product.**

**What Drive served.** All nine redirected from `drive.google.com/uc?export=download`
to **`drive.usercontent.google.com/download`** and returned the bytes directly. No
HTML interstitial, no confirm-token round trip on any file. Content-Type was
`application/octet-stream` on all nine — **Drive never declared `application/pdf`**,
so a content-type test would have rejected every real manual. The `%PDF` magic-byte
check is what passed them, which is the right test and was already in place.

**OCR: zero.** Every one of the 278 pages carried a text layer.

**Tiering: did not fire.** All three readings were `body_copy`; not one
`spec_plate` hit across 278 pages. The tier ordering is still untested on real
data — it is proven only against the constructed PDF in the suite.

**The recommendation rule rejected nothing real.** All three rejections were the
plausibility band. That rule is also still untested outside the suite, even though
the case it exists for is live in our own metafields (Dundalk's "an 8 kW electric
heater is recommended").

**The three rejections are the band earning its place.** Page 36 of the Monaco
manual: *"the bench heat emitter and floor heat emitter (200W/125W each) are of
much less wattage than the wall heat emitters (300W each)"*. Three real, precise,
correctly-parsed numbers — 0.2, 0.125 and 0.3 kW — and not one of them is the
unit's rating. Summing them would have been derivation, which is forbidden. Now
pinned by `test_per_panel_wattages_are_rejected_not_summed` using that exact
sentence.

**The zero is not yet attributable, and that is the finding.** The parser was
re-checked against twelve common rating forms (`Total power: 1800W`,
`Rated Power 1,800 W`, `POWER 1.8 kW`, `3.0KW`, a newline between number and unit,
…) and catches all of them; it returns nothing for `Power Supply 120V 15A`. So the
likely reading is that these manuals state a **supply spec, not a total wattage**.
But "the manual does not state it" and "we could not read what it states" are
different facts and a bare zero cannot tell them apart — this project's oldest
failure shape.

**Fix: a zero now carries its own evidence.** `electrical_context()` records, for
every PDF, the spans around power vocabulary (volt/amp/watt/kW/power/rated/
breaker/circuit/supply/consumption) whether or not anything parsed, plus
`chars_extracted` and a raw `text_sample` from the page with the densest
vocabulary. A manual that says `120V 15A` and no wattage now shows volts and amps
with watts absent; pypdf mangling glyphs into `1 8 0 0 W` shows up in the sample.
No gate was loosened and no band widened — evidence is recorded beside a reading,
never promoted into one.

**Not scaled.** `limit` stays 5. The next dispatch answers whether the silence is
the manuals' or ours.

**Verification.** 372 tests pass (was 368), including four new ones pinning this
run's actual findings. preflight `--static`/`--imports` clean, both self-tests
clean, cache gate clean (14 datasets + 1 report), drift clean, lint 0 findings.

## 2026-09-15 — manuals run 2: deliberate sample. Answer is a SPLIT, and one real bug

**The sample** (`data/manual-sample.json`, reasons recorded per SKU): Scandia ×3,
Finnmark ×2, three of them with a kW already in our metafields (9.0, 4.5, 1.9).
11 PDFs, 11/11 OK, **0 needing OCR**, 179,148 characters extracted.

**Two target vendors could not be sampled, and that is itself a finding.**
Medical Saunas: 13 SKUs, **zero** manual candidates (its four Drive embeds are all
in `custom.video`). SaunaLife: 8 SKUs carry a manual and **every one ships without
a heater** — `e8g` "Weight (less heater)", `ee6g` "Shipping Weight (without
heater)", `ee8g`/`e8g` "Select Your Heater" as a separate product, `g6` "plug it
into your heater system", `g3` explicitly "you select the heater (electric **or
wood-fired**)". The brief's "no externally heated" excludes all 8 — and that is
also why run 1's Dundalk cabin was a poor probe.

**ANSWER: (a) for one document shape, and the parser is NOT at fault.**

- **Scandia barrel kit, 16pp, 15,102 chars, 3 pages of electrical vocabulary:**
  `volt`, `power`, `electrical` — and **no `watt`, no `kw`, no `rated`**. What it
  states: *"make sure you have 220v single phase available and a NEMA 10-30R wall
  plug, the electrical wiring has to be done with a wire gauged between 10 AWG –
  4 AWG"*, and page 10 shows `125/250 V … LEVITON 30 A 10-30`. That is a **supply
  spec**. Our metafields say 9.0 kW for this SKU; the manual cannot corroborate
  it, and 220 × 30 is breaker capacity, not draw.
- **Scandia PreCut kit, 9pp:** *"ELECTRICAL NOTES — For heater, controls and light
  installation — refer to the…"*. It defers to a separate heater document by
  design.
- **Finnmark Trinity, 29pp: wattage IS stated and was read correctly.** Page 22:
  *"Trinity™= 15a 120v **1750 watts** • Harvia™ Vega Compact = 20a 120v **1900
  watts**"* → 1.75 kW and 1.9 kW, both parsed.

So it is not (a) globally and not (b) at all: **assembly/installation guides carry
a supply spec; line-wide FAQ manuals carry wattage.** The manual path yields kW
for the second shape only.

**A REAL BUG, found by the sample it was designed to expose.** FD-4's metafield
says **1.9 kW** and the manual line says **1900 watts** — an exact match. The
first comparison reported **DISAGREES**, because it compared only `readings[0]`
(the 1750 W) and never looked at the 1900 W sitting beside it on the same line.
A confident, precise, wrong verdict from reading one of two numbers. Fixed:
`compare_to_our_value` now considers every reading, and lists them all for
attribution. Corrected verdicts: **FD-4 AGREES** (1.9 corroborated),
**FD-5 NO_MATCHING_READING** (its 4.5 kW is the XL's steam heater; the FAQ lists
the Trinity infrared draw and a Harvia heater, neither of which is it).

"DISAGREES" is retired as a verdict. **All four manuals in this sample are shared
between two SKUs** — one Finnmark PDF serves FD-4 and FD-5, one Scandia PDF serves
two barrel kits — so an absent rating usually means the document covers another
variant, not that two sources contradict. `manual_shared_with` now records it.

**The lint caught a second bug in the same code:** `annotate_shared` grouped every
row with no Drive id under a `None` key, which would have reported id-less rows as
sharing one another. Now `manual_shared_with: null` with a reason, not `[]`.

**Tiering still has not fired.** Both readings are `body_copy`; no `spec_plate`
hit in 447 pages across two runs. The recommendation rule has still rejected
nothing real.

**Nothing relaxed.** The 0.8–30 kW band, never-derive-from-volts×amps, magic-byte
PDF detection and context-beside-a-reading all unchanged. `--recompare` recomputes
verdicts from readings already on disk, so fixing a verdict never costs a vendor
another fetch.

**Not scaled.** limit stays 5. 390 tests pass (was 383).

## 2026-09-15 — full manual extraction, 102 candidates. Four false ratings caught.

**Run 4 did not scale.** It passed `limit=102` and read FIVE products: `--sample`
truncates to `data/manual-sample.json`'s length and a larger `--limit` silently
meant nothing. Fixed three ways — scope is explicit (`--all` | `--sample`, neither
defaults, both halts), a limit beyond the supply HALTS instead of capping, and the
run prints its product-list source and counts before fetching, with an explicit
NOTE when selected ≠ available. fontTools/pypdf loggers dropped below ERROR.

**Run 5 crashed and committed nothing.** ~140 of 142 manuals read, then
`PdfStreamError` escaped an unguarded `pages_of()`. Now `PDF_UNREADABLE` with the
error; one bad file never discards a run.

**FOUR FALSE RATINGS, caught by auditing every accepted reading before publishing.
Two had already reached cost-tables.json as tier-1 values overriding correct data:**

| SKU | false | read from | overrode |
|---|---|---|---|
| leisurecraft-serenity | 2.245 kW | the SKU `CTC2245W` | correct metafield 6.0 |
| leisurecraft-tranquility | 2.345 kW | `CTC2345W` | correct metafield 6.0/8.0 |
| saunalife-g6 | 1.0 kW | the LIGHTING circuit | — |
| saunalife-g6 | 11.0 kW | `240V max. 11kW/46A, four wires 10AWG` — what the wiring supports, on a cabin that ships without a heater | — |

All four sit inside the 0.8–30 kW band. Four fixes in the shared guards:
`(?<![A-Za-z0-9])` so a wattage is never a part number's tail; `option` /
`selection required` (Dundalk's Luna parts list is a menu of heaters);
`W_EXCLUDE` applied to `read_kw` as well as `read_watts` (it guarded only watts,
so "6KW per panel" was rejected in watts and accepted in kW); and `AWG` / `wires`
/ `cable`, because a wire-gauge table states circuit capacity, never draw — the
prose form of the rule that already forbids deriving from volts × amps.
`power_parse.self_test()` had only known-POSITIVE controls and had never been
shown to refuse anything; it now carries six real strings that must not parse.

**FINAL, run 8 — 142 PDFs, 102 products, 3,487 pages, 3.77M chars.**

- **Coverage of 139 matched SKUs: 44 → 47 (31.7% → 33.8%, +3).** Of all 165:
  58 → 61. Sources: metafields 33, body/title 17, satellite 8, **manual 3**.
- **Nulls (104):** POWER_NOT_STATED 53 · MANUAL_SUPPLY_SPEC_ONLY 47 ·
  RATING_DEPENDS_ON_CONFIGURATION 2 · MANUAL_AMBIGUOUS 1 · POWER_CONFLICT 1.
- **The document-shape split is the finding:** FAQ-style yielding a rating 10
  PDFs (7.0%); **assembly-guide, supply spec only 88 (62.0%)**; no electrical
  content 34 (23.9%); unreadable 10 (7.0%). The 88 guides are not silent —
  `power` ×766, `electrical` ×359, `supply` ×303, `circuit` ×163, `voltage` ×125,
  `breaker` ×68, `rated` ×18. They state what to wire, not what the unit draws.
- **Verdicts:** 1 AGREES, 1 DISAGREES, 1 no-value-of-ours. The disagreement:
  `dynamic-low-infrared-sauna-heming`, manual "Total power:1650W" vs our own
  "approximately 1,750 watts". Both values, both spans, recorded; unresolved.
- **needs_ocr: 1** (`kaarina-6-person-sauna`). Not OCR'd. Also 5 NOT_A_PDF
  (Drive served text/html), 3 PDF_UNREADABLE (truncated, all SaunaLife), 1 404.
- **spec_plate has still never fired.** All 24 readings are `body_copy`, across
  ~7,000 pages over two full passes.
- **The recommendation rule has still rejected nothing real.** Its 4 hits in run 6
  were all the `CTC2245W` artifact; with the fix, zero.
- **Band rejections: 45 across 13 products**, values {0.125 ×17, 0.2 ×15, 0.3 ×13}
  — every one a per-emitter panel wattage. On Dynamic's dimension table the band
  rejected the panel figures while accepting the real total (1650 W) from the
  same line.

**Precedence rebuilt:** manual > page > metafield > body > satellite. One
correction: the first version emitted MANUAL_AMBIGUOUS / MANUAL_SUPPLY_SPEC_ONLY
as VALUES, suppressing figures we already publish and dropping coverage 58 → 55.
**A higher tier that states nothing must not nullify a lower one** — precedence
orders values, not silence. The manual now supplies a value or steps aside,
leaving `manual_evidence` on whatever wins.

398 tests pass, lint 0 findings against the finished artifacts.

---

## Round 15 — a rating belongs to the model number beside it (2026-09-15)

**The bug the client found.** Run 8's readings were attributed to whichever SKU
we fetched the PDF *for*, not to the model the document names. Three products
carried false ratings:

| SKU | run 8 read | correct | why |
|---|---|---|---|
| `GDI-8503-01` savonlinna | **6.0 AND 8.0 kW** | 6.0 | one cover line, two models |
| `GDI-8526-01` kaskinen | **6.0 AND 8.0 kW** | **8.0** | our SKU is the 40 A / 8 kW one |
| `CTC22LU` luna | **6.0 kW ×5** | none | a HUUM/Harvia price list |

⚠️ **The brief said "same on GDI-8526-01", meaning 6.0. The span says 8.0.** On the
Kaskinen cover `GDI-8523-01` carries the 6 kW and `GDI-8526-01` — our SKU — carries
the 8 kW. The rule follows the document; `tests/test_manual_specs.py` pins it.

**The rule.** A rating is governed by the model number that most recently
**precedes** it in its span. Not the nearest: on that cover the nearest token to
the 6 kW is `GDI-8506-01`, nine characters *after* it, and binding to it gives
exactly the wrong answer. Variant tables and price lists are written
label-then-spec. A rating with **no** model before it is UNBOUND and the other
guards decide as before, which is what keeps Dynamic's `Total power:1650W
DYN-6225-02` — our model is adjacent but follows the figure, and adjacency-after
is a layout, not a claim.

Where the governing model is not ours the reading is **rejected** with
`belongs_to_model`, never left in `readings` as a second candidate. The reason
distinguishes two different facts: our model **on the same page** bound to a
different rating (a variant table) from our model **nowhere on the page** (a
foreign catalogue). Where a model governs a rating and we hold no identifier at
all, it is rejected as unverifiable.

**We truncated three manuals and filed it as the publisher's defect.** Run 9's
three `PDF_UNREADABLE` SaunaLife rows were all **exactly 30,000,000 bytes** — our
own `read()` cap. Not damaged: cut off by us, the stump handed to pypdf, its
complaint written down as a fact about the file. Cap is now 120 MB, read with one
byte to spare so exceeding it is detectable, and an over-cap file is `TOO_LARGE`,
named, never parsed. Run 10 read all three: 24 + 29 + 29 pages, 0 ratings (those
cabins ship without a heater).

### Run 10 — 142 PDFs, 3,569 pages, 3.8 M characters

- **Status:** OK 135 · NOT_A_PDF 5 · NEEDS_OCR 1 · FETCH_FAILED 1 · **PDF_UNREADABLE 0**
- **Readings:** 17 accepted across 9 products; 52 rejected — 45 band (per-emitter
  panel wattages), **7 model-bound to another product**.
- **2 readings are bound to our own model number** (`GDI-8503-01` → 6.0,
  `GDI-8526-01` → 8.0). That is the strongest provenance this path has produced.
- **spec_plate has still never fired** — all 17 accepted readings are `body_copy`,
  now across ~10,500 pages over three full passes.
- **Where ratings actually come from:** 6 of 9 from ONE FAQ page (p22) inside an
  assembly manual; 2 from an assembly-guide **cover warning**; 2 from a dimension
  drawing. **Zero from a spec table.**
- **90 of 135 (66.7%) state a supply spec and no rating**; 36 (26.7%) carry no
  electrical vocabulary at all; 9 yield a rating.

### Verdicts against what OUR OWN pages state

The census now records `rated_power_stated` (64 of 165 SKUs), because in `--all`
scope the extractor had nothing to compare against and wrote `NO_VALUE_OF_OURS`
on 132 rows — "we hold no rating" when the truth was "this scope never looked".

AGREES 4 · NO_MATCHING_READING 4 · NO_MANUAL_READING 42 · NO_VALUE_OF_OURS 85.

🔴 **The finding worth acting on:** `savonlinna-3-person-sauna`. Our title names
`GDI-8503-01`; Golden Designs' own manual binds `GDI-8503-01` to a **6 kW heater
on a 30 A circuit**, and `GDI-8506-01` to the 8 kW. Our metafield says "Harvia
**8 kW** stove". Tier 1 wins (6.0) and the disagreement is recorded with both
spans. This looks like the sibling model's spec on our page — a merchandising fix,
not a parser one.

### Cost tables rebuilt

Coverage of the 139 priced SKUs: **47 (33.8%) before → 47 (33.8%) after.** The
binding removed false values rather than adding true ones, and where it removed a
tier-1 value a lower tier stepped back in with the same number and honest
provenance (`leisurecraft-luna` 6.0 kW: was `manufacturer_manual` from the price
list, now `product_body`). Nulls: POWER_NOT_STATED 53→51, MANUAL_SUPPLY_SPEC_ONLY
47→49 — two products moved from "nobody said" to "we read the manual and it gives
a supply spec".

### The non-OK PDFs — retry or lost

| n | status | verdict |
|---|---|---|
| 5 | NOT_A_PDF | **Lost, and it is our fault.** All five were Google **sign-in** pages: the Drive files are not shared publicly. Retrying cannot help. Two of the five share one file id, so it is 4 files. Fix is on our product pages. |
| 1 | FETCH_FAILED 404 | **Lost.** The Drive id embedded on `maxxus-bellevue-3-person…` resolves to nothing — a broken embed of ours. |
| 1 | NEEDS_OCR | `kaarina-6-person-sauna`, 8.2 MB scan, no text layer. Recoverable only by OCR, which is out of scope by ruling. |
| 3 | PDF_UNREADABLE | **Recovered.** They were our truncation, not their corruption. |

414 tests pass, lint 0 findings, preflight clean.

---

## Round 16 — True Total Cost: the calculator (2026-09-15)

**Objective: a working ZIP- and model-aware calculator, with the unknown-kW path
as a designed state.** Built. Verified in six states. **Not deployed** — the
blocker is named in full below, and it is transport, not code.

### The unknown-kW path, designed first

92 of 139 priced SKUs (66.2%) publish no rated power, so that is the state the
core is written around. Order of resort: catalogue rating → compute · no rating →
**invite** the reader to read it off their own spec plate, with a link to the
manual where we have a working one · reader declines → compute everything else
and name the exclusion in the total, in the per-session line and in a list. No
fifth branch, and a test asserts no combination of inputs reaches a number
without a rating.

### What was built

| | |
|---|---|
| `assets/inh-cost-core.js` | the arithmetic. No clock, no network, no randomness, not one `\|\| 0` on a money path |
| `assets/inh-true-total-cost.js` / `.css` | renders states, decides nothing |
| `assets/inh-cost-tables.json` | 160 KB · 139 priced SKUs · every cell a value with provenance or null **with the reason** |
| `assets/inh-zip-state.json` | 202 KB · 33,505 ZCTAs as 10,659 ranges |
| `sections/true-total-cost.liquid` | no arithmetic in Liquid; Dataset + SoftwareApplication only |
| 4 page templates + 4 page bodies | `sauna-cost`, `-running-cost`, `-installation-cost`, `-cost-methodology` |

### Verification — six states, all passing

Screenshots in `out/true-total-cost/` (gitignored, per the repo's render
convention). Known kW computes · unknown kW invites and renders no figure ·
reader kW computes and is labelled reader-supplied · declining yields a partial
total with an explicit exclusion list · an unresolvable ZIP renders a gap and
everything not depending on the rate is still computed · three identical runs
give one total. Plus a seventh the screenshots forced (below).

**Published arithmetic reproduced exactly.** 8 kW × 0.75 h × 3/wk × 52 = **936
kWh**, which is the article's own worked example; $132.16 in ND, $277.15 in MA,
$171.66 at the US average — the article's "about $172".

🔴 **The three per-session figures in the brief do not come from our
methodology and cannot be reproduced by it.** Fargo $2.44, Boston $4.61,
Anchorage $4.70 at 9 kW are `metrics.session_cost_9kw` in
`data/facts/outdoor_cities.json`, fetched from **outdoorsteamsauna.com**. Our
formula gives **$0.95 / $2.00 / $1.90**. Their implied session lengths are 1.92,
1.73 and 1.85 hours — not one number — and **Anchorage (28.21¢) costs MORE per
session than Boston (29.61¢)**, which no rate-proportional model can produce. A
climate term is in there and this repo holds no source for it. Fitted across all
75 cities the implied hours run 1.55 h (frost-free) to 1.92 h (Fargo), roughly
linear in January minimum temperature, residual ±0.12 h — close enough to see
the shape, nowhere near close enough to adopt. **Not reverse-engineered, not
copied.** Instead session length is a reader input defaulting to the 45 minutes
our own article publishes, so a reader who preheats for an hour reaches the same
range by stating their own fact.

### Two bugs the screenshots found

- **`$0.00 a year`, at 2.4rem, while both recurring lines were excluded.** A zero
  standing in for two figures nobody holds. `per_year_usd` is now `null` when
  nothing recurring is known; a reader who *types* zero still gets a real zero.
- **The missing-value lint could not see one line of what a customer reads.** It
  now scans `assets/*.js`, `sections/*.liquid`, `templates/*.liquid` for `||`/`??`
  literal defaults, Liquid's `default:` with a number, and numeric coercions with
  no finiteness check nearby — `Number("")` is `0`, which turns an empty quote box
  into a free electrician. Three rules, each fired at input that must and must not
  trip it. Its first version flagged its own rationale; comment lines are skipped.

### ZIP resolution coverage

| | |
|---|---|
| resolvable single-state ZCTAs | **33,505** |
| straddle a state line → two rates, deliberately not resolved | 137 |
| US territories → no EIA row | 149 |
| PO-box and single-building ZIPs | absent from the Census source by construction; they render a gap |

Range compression proved lossless against all 33,505 keys **and** proved not to
swallow the gaps between them.

### 🔴 Deployment — blocked, and it is transport

Theme **`Round 13 — True Total Cost calculator`**, id `146278776899`, created
**UNPUBLISHED** by duplicating MAIN. **Theme slots: 17 of 20.**

Nothing was written into it, for two independent reasons:

1. **`workflow_dispatch` only surfaces workflows on the DEFAULT branch.**
   `.github/workflows/deploy-theme.yml` sits on the round branch with its
   scripts, per the same-commit rule, and is therefore not dispatchable until
   the branch merges. Pushing the workflow to `main` alone would be the exact
   thing `CLAUDE.md` forbids.
2. **The two JSON assets cannot travel the MCP connector.** 214 KB + 269 KB
   base64. Relaying that through an agent's own output is neither affordable nor
   verifiable, and a theme holding the code without the data renders the
   "cost tables did not load" state — a preview not worth taking.

Shopify remains **403 on CONNECT** from this environment, so no preview URL could
be loaded or screenshotted either. The screenshots are of the local harness,
which loads the byte-identical JS, CSS and JSON. **They are not the preview URL
and are not described as it.**

**To finish it, from anywhere with the token:**

```bash
python3 scripts/deploy_theme_files.py --theme-id 146278776899 --live
```

### One real finding, bought by probing the live store

Upserting a template into a theme that does not yet hold its section is refused:
`FILE_VALIDATION_ERROR: Section type 'true-total-cost' does not refer to an
existing section file`. In one batch the templates validate before the section
lands, so the deploy fails on its last four files. The script now upserts in two
passes, halts if the first errors rather than compounding it, and reads every
file back and compares sizes before claiming anything.

### Numbers

472 tests (414 → 472) · lint **0 findings across both scopes**, 3 rendering-path
files now in scope · preflight clean · **Anthropic spend on the calculator: $0** —
every figure is deterministic code, no model call is in the path.
