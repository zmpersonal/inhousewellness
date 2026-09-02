# CLAUDE.md — InHouse Wellness social content engine

Governed by, in order: `agent-harness` (meta-rules, tiers, Slack protocol,
learning loop) → `social-autoposter` (the 21-step SOP) → **`docs/autoposter-adjustments-inhousewellness.md`**.

**The adjustments doc overrides the skill wherever they conflict.** It encodes
fixes for 81 structurally broken posts and 15 months of measured failure in the
live account. Where it contradicts the skill, the adjustments win. Where it is
silent, the skill governs.

Read this file, `RUNLOG.md` and `HANDOFF.md` before doing anything.

---

## Harness config block

| Key | Value |
|---|---|
| Slack channel | *TBD-nonblocking — no channel provisioned yet; report in-session* |
| Cost ceiling | **1,750 Blotato credits** ($10.50 at $6/1,000). Flag at 80% (1,400 spent / 350 left), STOP at 100% |
| Review cadence | Every round ends 🟡 REVIEW; retro when a learning hits `validated` |
| 🟡 delegation N | 3 clean rounds before any 🟡 step may be downgraded to 🟢 (agent never self-downgrades) |
| Repo | `github.com/zmpersonal/inhousewellness` (private). **Local git only so far — no remote configured, nothing pushed** |
| Governing docs | `docs/autoposter-adjustments-inhousewellness.md`, `docs/BUILD-HANDOFF.md` |

---

## Project brief

**Concept.** An automated content engine for InHouse Wellness — a US retailer of
home saunas and cold plunges — publishing to Pinterest, Facebook and Instagram.
Ideas come from four independent feeds: SEO keyword research, page analytics,
social performance data, and the company blog. Runs hands-off on a cadence until
explicitly stopped.

**Niche.** Home saunas (infrared and traditional), cold plunge, wellness
equipment. Store: inhousewellness.com (Shopify).

**Audience.** 40–60 year old Americans, middle to upper-middle class,
health-interested. Considered purchase, $3,000–$15,000, months-long research
window, frequently a joint decision between partners. **Not** biohackers, not a
young wellness audience. Write adult-to-adult.

**Social objective: REACH.** Not followers, not likes, not vanity engagement.
North-star metric is **monthly impressions across the three channels.**
Baseline to beat: ~11,200 total impressions across 15 months and 322 posts.
Secondary metric: **saves** — 1 recorded ever, as of 2026-09-01.
Engagement rate is already healthy (7.3% IG, 5.0% FB); **do not optimize for it.**
The bottleneck is distribution, not response.

**Primary health metric during review: broken-post rate.** Prior baseline 27%.
Target 0%. (Adjustment D2.)

---

## Per-platform cadence config (adjustment A1)

Cadence is a **map keyed by platform**, never one number, never hardcoded at a
call site. Peak historical volume was 13 posts in a single day, during the window
when 27% of output was broken.

```yaml
platforms:
  pinterest: { posts_per_day: 4, role: compounding-search }   # primary
  instagram: { posts_per_day: 1, role: cold-reach }
  facebook:  { posts_per_day: 1, role: click-driver }
max_posts_per_day_total: 6
```

### Per-platform render targets (adjustment C3)

The skill's "native 1080×1080, no scaling" rule is **wrong for Pinterest**.

| Platform | Dimensions | Ratio | Verified |
|---|---|---|---|
| Pinterest | 1000 × 1500 | 2:3 | ✅ 2026-09-01 |
| Instagram feed | 1080 × 1350 | 4:5 | ✅ 2026-09-01 |
| Instagram / Facebook Reels | 1080 × 1920 | 9:16 | ✅ 2026-09-01 |
| Facebook feed | 1200 × 630 or 1080 × 1080 | — | not yet exercised |

Every other template constraint stands: wait for `document.fonts.ready`,
auto-fit long text, self-hosted fonts (CDN fonts fail in CI).

---

## Locked decisions — do not relitigate

- **Blotato is the only posting tool.** Not Buffer for posting, not Revid, not
  Opus, not Higgsfield. Buffer stays connected **for Pinterest analytics only**,
  because Blotato does not collect Pinterest metrics and Buffer is the only
  source in the stack.
- **Blotato is the only video tool.**
- **No AI avatars or synthetic human presenters.** Voiceover (Bill or Brian),
  animation, or real footage only. A generated human making health claims to a
  40–60 US audience evaluating an $8,000 purchase from an unfamiliar retailer is
  a credibility liability, not a shortcut.
- **No trending audio.** The library must stay evergreen.
- **No brand intro card.** Two seconds of logo spends the entire hook window.
- **Design system is locked.** Palette `#1B1613` base / `#E9E5DD` type /
  `#E0A03C` heat / `#6FA8B8` cold. Fraunces 700 display, IBM Plex Sans 400/600/700
  data, self-hosted. Ticked measurement rule on the left edge of every card.
  Do not redesign. Logo pending from the user — footer slot is ready.
- **auto_publish = FALSE.** Do not flip until 14 consecutive days at zero broken
  posts (adjustment D2).

---

## Hard rules — each one traces to measured failure

- **Per-platform copy always.** 207 of 300 historical posts shared caption text
  across channels. Never generate one string for multiple platforms. Enforced by
  `validator.assert_no_shared_text`.
- **Pinterest pins need title + description + altText + link + boardId** or they
  do not perform. 75 blank pins averaged 3.0 impressions; pins with text averaged
  106.2 in the same window on the same account.
- **Facebook: link in the first comment**, never in the post body. Enforced by
  the `FB_LINK_IN_BODY` rule.
- **Health claims are code-gated, not prose-guided** (`src/health_claims.py`).
  This audience is frequently managing blood pressure and cardiac risk, and the
  machine is unattended.
- **The LLM writes copy only.** Selection, counting, dedup, gating, rendering and
  posting are CODE. This is the skill's governing principle and the reason the
  previous system failed.
- **Never publish a degraded version.** The validator raises; it has no
  "clean it up and post anyway" path.

### ⛔ Facebook Groups stay manual — never automate (adjustment D3)

The strongest untapped channel for this demographic is genuine participation in
health-condition and home-renovation Facebook Groups — perimenopause, cardiac
health, chronic pain, sleep, home renovation.

**Automating that will get the accounts banned and burn reputation permanently.**
It is a manual daily human task, permanently outside the machine. A future agent
must not helpfully wire it in. This is not a backlog item; it is a prohibition.

---

## Kill-switch criteria (adjustments A4 + D2)

Any of these re-gates the system to `auto_publish=false` automatically, in the
workflow, and emits 🔴 BLOCKED:

1. Any post published with empty or under-length (< 50 char) text
2. Any post text matching an error pattern (`Error:`, `Failed to load`,
   `undefined`, `null`, `No response`, …)
3. Any Pinterest pin published without title, altText, or destination link
4. Any banned health claim reaching a live post
5. Any post exceeding a platform character limit
6. Any factual error or platform warning
7. Blotato credits at 100% of ceiling
8. A D5 duplicate-post breadcrumb found at start of run

Re-gating is enforced in code, not prose. A human clears it after investigating.

---

## Tooling status — verified 2026-09-01

| Item | Status |
|---|---|
| Blotato subscription | ✅ active, plan `starter`, `accounts@inhousewellness.com` |
| Blotato Facebook | ✅ account `49743`, page **InHouse Wellness** `472026422664772` |
| Blotato Pinterest | ✅ account `9630` (`inhousewellness`) — **now authorized** (adjustments doc said missing) |
| Blotato Instagram | ✅ account `68734` (`inhouse.wellness`) — **now authorized** |
| Blotato credits | 1,750 at check-in; 1,620 after the 5 credit-burn test renders |
| Buffer | ✅ org `681037367954398ece80de72`, 3 channels connected (IG, Pinterest, FB) |
| Buffer plan limit | ⚠️ free: 3 channels, 10 scheduled posts, **insights capped at last 31 days** |
| Render environment | ✅ Playwright **1.49.1** in `.venv` (see below) |

### ⚠️ Playwright version is pinned for a reason

This host is macOS 13 (Darwin 22.6). Current Playwright **refuses to install on
mac13** (`Playwright does not support chromium on mac13`). Playwright `1.49.1`
works against the already-cached `chromium-1148`. `requirements.txt` pins it.
Do not upgrade on this host. CI (Linux) may use current Playwright.

### Pinterest boards (live IDs)

| Board | ID |
|---|---|
| Social | `902690387751301590` |
| The Sauna Shop | `902690387751719051` |
| Wellness At Home | `902690387751256709` |
| Products | `902690387751254421` |

The keyword queue references 6 board names that do not exist under these 4.
Board creation is an open item.

### Media path — verified

`blotato_create_post` takes `mediaUrls` as **public URLs**. Locally rendered PNGs
are not public, so the path is:
`blotato_create_presigned_upload_url` → HTTP `PUT` raw bytes → use the returned
`publicUrl` in `mediaUrls`. Base64 `data:` URIs are **not** the path here,
contrary to the skill's step 9. Visuals from `blotato_create_visual` come back as
public URLs already and need no upload.

---

## Credit economics — measured 2026-09-01 (adjustment A3)

Measured empirically by checking the balance before and after each render.
**Local Playwright card renders cost 0 credits** — only Blotato-side generation bills.

| # | Template | Output | Credits | USD |
|---|---|---|---|---|
| 1 | Whiteboard Infographic | 1 static image | 50 | $0.30 |
| 2 | Tutorial Carousel, Minimalist Flat | 7 slides | **0** | $0.00 |
| 3 | When X then Y Text Slideshow | 5-slide MP4, 2 AI images | 30 | $0.18 |
| 4 | Image Slideshow with Text Overlays | 3-slide 9:16 MP4, 3 AI images | 45 | $0.27 |
| 5 | AI Story Video + AI Voice (Brian), no animation | 3-scene 9:16 MP4 + voiceover | 45 | $0.27 |
| — | Local card render (`scripts/render.py`) | any size PNG | **0** | $0.00 |

**Total for the 5 tests: 170 credits ($1.02). 1,580 remaining.**

Two findings that decide the format mix:

1. **AI generation is what bills; layout is free.** Anything that generates an AI
   image or voiceover costs 30–50 credits. Deterministic HTML-template carousels
   cost **0**, and local Playwright card renders cost **0**.
2. **Only the free paths can carry the locked design system.** The Tutorial
   Carousel accepted `#1B1613` / `#E0A03C` / `#E9E5DD` exactly. The 50-credit
   Whiteboard Infographic rendered a photoreal whiteboard in primary colours —
   accurate and legible, but no palette, no type scale, no ticked rule. **Paying
   more buys less brand.**

### Runway, at 1,580 credits

| Mix | Burn | Runway |
|---|---|---|
| All static cards local; Reels 3/week via AI Story Video | 135/wk | **~11.7 weeks** ✅ |
| All static local; Reels 4/week | 180/wk | ~8.8 weeks ✅ |
| All static local; Reels daily | 315/wk | ~5.0 weeks ❌ |
| IG + FB daily via Blotato AI, Pinterest local | 630/wk | ~2.5 weeks ❌ |
| All 6 posts/day via Blotato AI templates | 1,890/wk | **~6 days** ❌ |

**Standing rule: render every static card locally. Spend credits only on Reels,
capped at 4/week.** That is the only mix clearing the 8-week runway threshold.

⚠️ **Unmeasured:** `animateAiImages: true` on the AI Story Video template was not
tested. Adjustment A3 flags animation as materially more expensive. Measure it
before enabling it, not after.

---

## Template allow-list (adjustment C7)

| Pillar | Template | ID |
|---|---|---|
| The Correction | When X then Y Text Slideshow | `/base/v2/images-with-text/c9892c3b-fa75-4ade-821a-a50ff8456230/v1` |
| The Measured Number | AI Story Video with AI Voice (Bill or Brian, **no face**) | `/base/v2/ai-story-video/5903fe43-514d-40ee-a060-0d6628c5f8fd/v1` |
| The Reality Check | Tutorial Carousel — Minimalist Flat | `/base/v2/tutorial-carousel/2491f97b-1b47-4efa-8b96-8c651fa7b3d5/v1` |
| The Evidence Read | Whiteboard Infographic | `ae868019-820d-434c-8fe1-74c9da99129a` |
| The Evidence Read (alt) | Book Page Infographic | `b88c8273-6406-48c6-85e7-096119aefe30` |
| Product context | Product Scene Placement | `f524614b-ba01-448c-967a-ce518c52a700` |
| Pinterest workhorse | Image Slideshow with Text Overlays | `/base/v2/image-slideshow/5903b592-1255-43b4-b9ac-f8ed7cbf6a5f/v1` |

**Block-list** — wrong register, reads gimmicky to this buyer:
Graffiti Mural `3598483b`, Manga Panel `49c61370`, Cave Painting `82ee75b6`,
Egyptian Hieroglyph `a7b0d128`, Steampunk `7b7104f1`, Top Secret `b8707b58`,
Movie Theater `f8f1ebe4`, Breaking News `8800be71`,
**AI Selfie** `/base/v2/ai-selfie-video/…`, **AI Avatar** `/base/v2/ai-avatar-broll/…`.

**Always override `footerText`.** Every template defaults to
*"Follow me for more helpful content | Repost"* — creator-economy language that
reads wrong from a retailer. Use `inhousewellness.com`.

---

## Content pillars (adjustment B3)

| Pillar | Share | Proven by |
|---|---|---|
| The Correction — "X is not the reason to buy Y" | 30% | "$10,000 sauna can be worse than $5,000" (169 FB) |
| The Measured Number — one figure, shown being measured | 25% | "Same 180°F, completely different heat" (113 IG reach, 206 FB) |
| The Reality Check — electrical, space, HOA, delivery | 25% | "I'd love a home sauna but don't want a home improvement project" (106 reach) |
| The Evidence Read — what a study found and didn't | 20% | Untested on social; best demographic fit, lowest compliance risk |

Blog-derived pins outperformed generic wellness pins **5× on mean, 24× on median.**
**Every post traces to a blog article. Nothing is invented for social.**

---

## The four idea feeds — each must fail independently

Failure of one feed must never take down the others.

| Feed | Tool | Status 2026-09-01 |
|---|---|---|
| SEO keywords | Ubersuggest MCP `keyword_overview` / `keyword_suggestions` | ✅ live rows |
| Blog | `blotato_create_source` (`sourceType: article`) | ✅ clean summary; 404 returns an **error**, not a publishable string |
| Pinterest analytics | Buffer `get_aggregated_post_metrics` | ✅ live; 31-day window only |
| IG/FB analytics | Blotato `blotato_list_top_posts` | ✅ tool works, **0 InHouse Wellness rows** (no history in Blotato) |

⚠️ **Do not trust `create_source`'s `title` field.** On a real InHouse Wellness
article it returned `"Visa"`. Use `content` and `referenceUrl`; derive the title
from the keyword queue.

---

## Standing constraint: low-token system

Token cost per published post is a first-class metric, tracked alongside credits.
The skill's governing principle, taken literally: **the LLM writes copy and
nothing else.** Sweeping, matching, routing, dedup, validation and rendering are
deterministic code. If a step can be done without a model call, it must be.

Measured: **one batched call per cycle, ~1,060 input tokens for all 6 posts,
$0.0084 per published post, ≈$1.51/month** at 6 posts/day. One call per post
would be six times that and is forbidden.

## Destination routing (all three platforms)

Destination is a property of every post, not a Pinterest-only field.

| Platform | Where the link lives |
|---|---|
| Pinterest | `link` on the pin — mandatory, validator-enforced |
| Facebook | **first comment**, never the body |
| Instagram | link-in-bio target; captions reference what is currently there |

The satellite network is a **permanent rotation, not a fallback**:
**INH ≥ 70%** of destinations over a rolling 30 days, satellites ~30% round-robin
with a 6-post per-domain cooldown and an 8% per-domain ceiling. Asserted in code
(`src.destinations.audit`); the INH floor fails the build.

**Why the floor:** the Pinterest account is under Verified Merchant Program
review, and an account spraying links across ten related domains is a
recognisable spam pattern.

⚠️ **Satellite homepages mostly do NOT link back to INH** — only 4 of 10 do.
Destinations therefore point at the specific inner page that does (verified
2026-09-01, see `data/satellite-destinations.json`). Re-verify with
`scripts/verify_destinations.py` before any scheduling run; it exits 1 on failure.

The 8% per-domain cap is a property of the rolling 30-day **published** window
and is only asserted at n ≥ 25 — below that a single post is arithmetically over
the cap. Same "don't act on noise" rule as the loop's 30-post minimum.

## Rendering: local first, Blotato only for b-roll

**Never route copy carrying numbers, units or a brand claim through a generative
renderer.** Given exact copy, Blotato returned *"3 same 180f. completely
different heat."* — stray token, lost capitalisation, mangled "180°F" — plus a
lime-green highlight outside the palette. The local path reproduced it exactly at
zero cost.

- Static cards and Reels: **local** (Playwright → ffmpeg), 0 credits, 0 tokens
- Blotato: reserved for Evidence Read where voiceover genuinely adds value, and
  for b-roll behind deterministic text — never for the text itself
- ffmpeg comes from the `imageio-ffmpeg` wheel. Playwright's bundled ffmpeg is a
  stripped VP8/WebM build with no H.264 and no MP4 muxer — unusable for Reels.
- `animateAiImages` stays **disabled** — still unmeasured.

## The self-improvement loop

`src/feedback.py`. Collect and score are live; **adjust runs `dry_run=True`** and
applies nothing.

| May change | May never change |
|---|---|
| archetype mix weighting | the validator, or any gate |
| keyword priority ordering | health-claim rules |
| board assignment | the 70% INH floor |
| posting time of day | brand palette, type, card layouts |
| satellite rotation order | cadence ceilings |

Guardrails, enforced in code and tested individually:
- the loop **cannot widen its own permissions** — `allowed_knobs`,
  `forbidden_knobs` and `guardrails` are themselves in the forbidden set
- **broken-post rate > 0 halts the loop entirely**, regardless of reach
- no proposal from a segment under **30 posts**
- a change that does not move its stated metric within **14 days reverts**
- every adjustment writes a dated `LEARNINGS.md` entry with evidence, the metric,
  and the revert date
- anything outside the allow-list is a 🟡 REVIEW — the loop proposes, never applies

⚠️ **Pinterest cannot be scored per post.** Buffer's free plan exposes a channel
aggregate over a rolling 31 days only, and Blotato does not collect Pinterest
analytics at all. `collect` marks this `granularity: "channel-aggregate"` rather
than inventing per-pin numbers.

## Decisions taken (2026-09-01)

- **Keyword queue:** remap the 89 dead rows to live blog URLs; no guessed URLs —
  a row with no honest match gets `status: blocked`. Add `verified_at` per row.
- **Legacy `network/customScheduled` path:** shut down by the user 2026-09-01.
  ⚠️ **Not yet confirmed.** Those posts were published natively and backfilled
  into Buffer as `via: network`, so they never appeared in a queue — an empty
  queue proves nothing. Confirmation is the absence of any `via: network` post
  with `sentAt` after 2026-09-01. Most recent one: **2026-08-22**.
  Run this check before any live posting; the D2 zero-broken-posts clock does not
  start until it passes.

## Stop and ask the user (surface-don't-assume triggers)

- Credit burn implies under 8 weeks of runway
- Any `source_article` or `link` in the keyword queue 404s
- The legacy `network/customScheduled` RSS path is still live
- Any conflict between this file, the adjustments doc, and the skill

---

## Repo layout

```
CLAUDE.md  RUNLOG.md  LEARNINGS.md  HANDOFF.md
docs/       autoposter-adjustments-inhousewellness.md, BUILD-HANDOFF.md
src/        limits.py  health_claims.py  validator.py      (Round 1)
            remap.py  destinations.py  workorders.py
            captions.py  voice.py  reel.py  feedback.py    (Round 2)
tests/      test_validator.py  test_captions.py  test_feedback.py   (94 tests)
templates/  cards.html (9 archetypes, 3 sizes), tokens.css, fonts/ (4 woff2)
scripts/    render.py  build_blog_index.py  remap_queue.py
            verify_destinations.py  build_reel.py  collect_metrics.py
fixtures/   pinterest.json  instagram.json  feedback/ (loop fixtures)
data/       pinterest-keyword-queue.json (103: 24 queued / 79 blocked)
            blog-index.json (109 articles)  satellite-destinations.json
            reels-seed.json (12 Reels / 4 sets)
state/      posting-state.json, metrics-*.json (gitignored)
out/        renders, reels, spike comparison (gitignored)
```

## Commands

```bash
.venv/bin/python -m pytest tests/ -q
```
```bash
.venv/bin/python scripts/build_blog_index.py && .venv/bin/python scripts/remap_queue.py --write
```
```bash
.venv/bin/python scripts/verify_destinations.py
```
```bash
.venv/bin/python scripts/build_reel.py reel-3-1
```
```bash
.venv/bin/python scripts/collect_metrics.py --buffer fixtures/feedback/buffer-pinterest.json --blotato fixtures/feedback/blotato-top.json --published fixtures/feedback/published-log.json
```
