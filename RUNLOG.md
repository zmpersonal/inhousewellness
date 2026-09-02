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
