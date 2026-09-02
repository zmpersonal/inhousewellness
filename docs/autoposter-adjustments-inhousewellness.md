# social-autoposter — Project Adjustments

**Project:** InHouse Wellness (INH) — home saunas, cold plunges, wellness equipment
**Audience:** 40–60 year old Americans, middle to upper-middle class, health-interested
**Platforms:** Pinterest (primary), Facebook, Instagram
**Scope:** Recommendations for this project only. No changes to the skill file itself.

---

## Context: what the existing data says

Analysis of 322 posts published Mar 2025 – Aug 2026 across the three channels:

- **81 of 300 posts (27%) were structurally broken** — 75 Pinterest pins with blank text, 3 Facebook posts reading `Error: No response text`, 1 reading `Failed to load this feed … Status code 503`, 2 empty Instagram posts.
- **39 further Facebook posts were raw article dumps** of 25,000–51,000 characters, averaging ~3 impressions.
- Pinterest pins **with** text averaged 106 impressions; **blank** pins averaged 3.0. Same account, same window.
- **207 of 300 posts shared duplicate caption text** across platforms.
- Total lifetime reach across all three channels: roughly 11,200 impressions.

Every adjustment below traces to one of those findings. The skill's core principle — *the LLM writes copy and nothing else; selection, counting, dedup, gating and posting are CODE* — is exactly right, and is precisely what was missing.

---

## A. Adjustments to DEFINE

### A1. Cadence must be per-platform, not one number (Step 1.4, Step 14)

The skill specifies a single `cadence_days` config value. This project needs three different rhythms, because the platforms have different content half-lives:

```yaml
platforms:
  pinterest: { posts_per_day: 4, role: compounding-search }
  instagram: { posts_per_day: 1, role: cold-reach }
  facebook:  { posts_per_day: 1, role: click-driver }
max_posts_per_day_total: 6
```

Pinterest is a search index where volume compounds; Instagram and Facebook are feeds where volume decays. Treat `cadence` as a map keyed by platform. Keep the skill's rule that it's config, never hardcoded.

Note the prior failure mode this guards against: peak volume hit **13 posts in a single day** during the period when 27% of output was broken.

### A2. Add a health-claims compliance block to the brief — new, and non-optional

Not in the skill, and it is the highest-risk gap for this project. INH sells heat and cold therapy equipment to people who are health-interested and, in this age band, frequently managing blood pressure, cardiac risk, joint pain, or sleep issues.

Ban outright in the voice guide, enforced in code (see C2):

- Disease-treatment or cure claims — blood pressure, cardiovascular disease, depression, insomnia, arthritis
- "Detox" framed as a physiological mechanism
- Weight-loss claims
- Any absolute: "proven," "guaranteed," "eliminates," "cures"
- Any implication of medical advice or substitution for care

Require instead, on any health-adjacent post:
- Hedged framing matching the evidence — "may support," "promising but limited"
- A source when a specific finding is cited
- Contraindication language where the topic warrants it (cold plunge + cardiac risk especially)

The INH blog already does this well — evidence-strength ratings, "what we still don't know" sections. The failure was on social, where published captions included "lifelong detox," "insane benefits," and "your secret weapon." Those are the exact posts that also underperformed.

### A3. Cost ceiling should be denominated in Blotato credits (Step 1.8)

Current balance: **1,750 credits at $6 per 1,000.** Every generated visual burns credits, and per-render cost varies substantially by template — animating AI images is materially more expensive than static slides.

Before setting the ceiling, run five test renders across the templates actually in use and measure. Then express the ceiling as both `$/month` and `credits/month`, with the harness 80%/100% flag-then-stop rule applied to credits, since that's the resource that actually runs out.

### A4. Extend kill-switch criteria (Step 1.10, Step 20)

Add to the re-gate triggers:
- Any post published with empty or under-length text
- Any post text matching an error pattern
- Any Pinterest pin published without title, alt text, or destination link
- Any banned health claim reaching a live post
- Any post exceeding platform character limits

These are the observed failure modes, not hypothetical ones.

---

## B. Adjustments to RESEARCH

### B1. The data source is the INH blog, and it must be summarized, not dumped (Step 4, Step 8)

The blog publishes near-daily and is genuinely strong — ceiling height by tier, what to do when the breaker panel is full, renting vs. 120V infrared, HOA rules for condos, Therasage teardowns. It is the correct feed.

The current implementation polls `inhousewellness.com/blogs/saunas.atom` and publishes the raw `<content>` body. That produced the 39 article dumps and, when the store returned a 503, published the error string itself.

Use `blotato_create_source` instead — it extracts and summarizes a URL and returns clean `title` / `content` / `referenceUrl`. Prove it in isolation at Step 8 with a real blog URL, and confirm the failure path returns a status rather than a publishable string.

### B2. Add an evidence-tier field to every bank item

Each item carries `evidence_tier: strong | moderate | limited`, inherited from the blog post's own rating. The caption function consumes it and matches hedging to tier. This makes A2 enforceable rather than aspirational.

### B3. Niche research should target the four proven pillars (Step 3)

Rather than open-ended format research, validate against what already performed:

| Pillar | Share | Evidence from existing data |
|---|---|---|
| **The Correction** — "X is not the reason to buy Y" | 30% | Top performers across all channels: "$10,000 sauna can be worse than $5,000" (169 FB), "Near-zero EMF is not a reason to buy — transparency is" |
| **The Measured Number** — one figure, shown being measured | 25% | "Same 180°F, completely different heat" — 113 IG reach, 206 FB impressions |
| **The Reality Check** — electrical, space, HOA, delivery | 25% | "I'd love a home sauna but don't want a home improvement project" — 106 reach |
| **The Evidence Read** — what a study found and didn't | 20% | Untested on social; strongest fit for the demographic and lowest compliance risk |

Blog-derived pins outperformed generic wellness pins **5x on mean, 24x on median.** Every post should trace to a blog article. Nothing invented for social.

---

## C. Adjustments to PROVE and BUILD-LOGIC

### C1. Step 7 tooling check has three specific blockers for this project

- **Blotato has only Facebook authorized.** `blotato_list_accounts` returns one account with 12 Facebook Pages and no Pinterest or Instagram. Both must be connected before Step 9 can prove anything.
- **Buffer's free plan caps at 3 channels and 10 scheduled posts.** It cannot carry 4 pins/day. Recommend: post via Blotato, keep Buffer connected for analytics — because **Blotato does not collect Pinterest analytics** and Buffer is the only Pinterest measurement in the stack.
- **Verify the media path.** The skill specifies base64 `data:` URI upload. Blotato's `create_post` takes `mediaUrls` as public URLs, and `blotato_create_presigned_upload_url` exists as a separate path. Confirm which works before building on it.

### C2. Add an output validator before publish — the single most important adjustment (new step, before Step 13)

Enforced in code, in the same architectural slot as the D5 gate and for the same stated reason. A post must **not** publish if any of these hold:

```
text is empty, whitespace-only, or < 50 characters
text matches /Error:|Failed to load|undefined|null|No response/
text exceeds the platform character limit
platform == pinterest AND (title missing OR altText missing OR link missing)
text contains a banned health claim (A2)
mediaUrls is empty or unreachable
```

This gate alone would have blocked all 81 broken posts. On failure: halt, do not publish, emit 🔴 BLOCKED to Slack per the harness protocol. Never publish a degraded version.

### C3. Pinterest needs its own render spec — the 1080×1080 rule doesn't apply (Step 6, Step 12)

The skill mandates *"Native 1080×1080 render — no scaling."* Correct for Instagram and Facebook, wrong for Pinterest, which is vertical-first. Of 296 assets analysed, 47 were square, 5 horizontal, and effectively none were vertical.

Per-platform render targets:

| Platform | Dimensions | Ratio |
|---|---|---|
| Pinterest | 1000 × 1500 | 2:3 |
| Instagram feed | 1080 × 1350 | 4:5 |
| Instagram Reels | 1080 × 1920 | 9:16 |
| Facebook | 1200 × 630 or 1080 × 1080 | — |

Keep every other template constraint as written — `document.fonts.ready`, auto-fit long text, self-hosted fonts. Those are all sound and text overflow is a real risk given the long-form source material.

### C4. Add a Pinterest metadata schema to caption generation (Step 11)

The skill's caption function produces caption text. Pinterest needs a structured object, and the missing fields are the direct cause of the 35x performance gap:

```
title:    40–70 chars (hard cap 100). Keyword front-loaded. No emoji.
          Treat as a page title, not a caption.
text:     150–350 chars. Keyword in first sentence, then the specific
          claim, then one concrete number. Max 3 hashtags, at the end.
altText:  50–125 chars. Literal description of the image.
link:     mandatory, real inhousewellness.com URL. Null → do not publish.
boardId:  from blotato_list_pinterest_boards
```

Worked example:

```
title:   "Sauna Running Costs: What $0.71 Per Session Really Means"
text:    "We measured a 2-person infrared sauna with a plug-in meter across
          30 sessions. Average draw was 1.4 kWh per 45-minute session — about
          $0.71 at the US average rate. Most listings don't publish this."
altText: "Kill-A-Watt meter plugged into a home infrared sauna showing
          kilowatt-hour reading"
link:    "https://inhousewellness.com/tools/sauna-running-cost"
```

### C5. One caption call, per-platform outputs (Step 11)

Preserve the skill's one-call-per-cycle economy, but the call returns a **per-platform object**, not one string reused three times. 207 of 300 posts shared caption text across channels — likely a contributing factor in Pinterest distribution and certainly a waste of the platform differences.

Voice constraints for this demographic, to sit in the voice guide:
- Adult-to-adult register. No hype, no "insane," no emoji stacking.
- Specific numbers over adjectives.
- Contrarian and corrective is the proven register.
- **Hard ban on synthetic human presenters.** Do not use Blotato's AI Selfie or AI Avatar templates. A photoreal fake human making health and trust claims to a 40–60 US audience evaluating an $8,000 purchase from an unfamiliar retailer is a credibility liability, not a shortcut. Text-on-screen with voiceover, animation, or real hands-and-product only.

### C6. Split the material bank; evergreen recycles, timely halts (Step 10)

The skill halts loudly on bank exhaustion. Right for a finite curated bank, wrong for a Pinterest engine where "how to measure your ceiling height for a sauna" is worth republishing every season.

- **Evergreen** — reusable after `min_repost_days` (suggest 120), with a fresh card design and rewritten copy
- **Timely** — product launches, seasonal offers, news; single-use, halts on exhaustion as written

Dedup key is `(platform, item_id)` so one article can legitimately produce a pin, a Reel and an FB post without tripping seen-ids.

### C7. Add a template allow-list (Step 6)

Of Blotato's 30 visual templates, these fit the demographic:

| Pillar | Template |
|---|---|
| The Correction | When X then Y Text Slideshow |
| The Measured Number | AI Story Video with AI Voice (voice: Bill or Brian — no face) |
| The Reality Check | Tutorial Carousel — Minimalist Flat |
| The Evidence Read | Whiteboard or Book Page Infographic |
| Product context | Product Scene Placement |
| Pinterest workhorse | Image Slideshow with Text Overlays |

**Block-list:** Graffiti Mural, Manga Panel, Cave Painting, Egyptian Hieroglyph, Steampunk, Top Secret, Movie Theater, Breaking News, AI Selfie, AI Avatar. Wrong register — they read as gimmicky to this buyer.

Also override every template's default `footerText`. The stock *"Follow me for more helpful content | Repost"* is creator-economy language and reads wrong from a retailer.

---

## D. Adjustments to DEPLOY and LAUNCH

### D1. Add a performance feedback loop (new, after Step 17)

The skill has a CI runlog but no output measurement. Weekly pull:

- **Buffer** `get_aggregated_post_metrics` — the only Pinterest measurement available
- **Blotato** `blotato_list_top_posts` — Instagram and Facebook

Report into the existing Slack ⚪ FYI digest: posts published, broken-post count (target zero), impressions and saves by platform, top 3 posts by pillar. Feed pillar win-rates back into B3's weighting at each retro.

### D2. Track broken-post rate as the primary health metric during review (Step 19)

Not engagement. The prior baseline is 27%. Target is 0%, and it should be the gate on autonomy: **do not flip `auto_publish=true` until 14 consecutive days at zero.**

### D3. Keep Facebook Groups out of the machine (Step 19+)

The strongest untapped channel for this demographic is genuine participation in health-condition and home-renovation Facebook Groups — perimenopause, cardiac health, chronic pain, sleep, home reno. Automating that will get accounts banned and burn reputation permanently.

Keep it a manual daily task outside the machine, and state so explicitly in `CLAUDE.md` so a future agent doesn't helpfully automate it.

### D4. Disable the legacy publish paths before the first controlled run (Step 18)

Two distinct systems are currently publishing:

| Source | Posts | Broken | Raw dumps | Median perf |
|---|---|---|---|---|
| `network / customScheduled` | 263 | 75 | 39 | 4 |
| `buffer / customScheduled` | 31 | 0 | 0 | **14** |
| `buffer / addToQueue` | 6 | **6** | 0 | 5 |

The `addToQueue` path is 6 posts and all 6 are broken — switch it off. The middle row is the August content that worked and is the voice to preserve. Confirm the RSS-driven `network` path is fully decommissioned before Step 18, or the new machine will run alongside the old one.

### D5. Pinterest can restart in ~2–3 weeks, not 90 days

An earlier read attributed the Pinterest collapse to account throttling. The data doesn't support that: blank pins averaged 3.0 impressions and pins with text averaged 106.2 in the same window, and August pins with text still averaged 20.4. **The account was working the entire time — it was being fed pins with no title, description, or link.**

Pinterest's own documentation also notes that Verified Merchant Program suspension may leave approved merchant status, catalog management, and distribution unaffected. The VMP catalog issue is a real store-ops task, but it does not gate organic pinning and runs in parallel.

Restart Pinterest as soon as C3 and C4 are proven.

---

## E. Build sequence

1. Confirm tooling (C1) — authorize Pinterest and Instagram in Blotato; measure credit burn (A3)
2. Build the **output validator (C2) first**, before any generation logic. Highest ROI in the document.
3. Prove `blotato_create_source` on the blog (B1)
4. Pinterest render spec + metadata schema (C3, C4) — Pinterest is the priority channel
5. Full cycle on fixtures, then Step 18 controlled run
6. 14 days at zero broken posts (D2), then flip to autonomous
7. Add Instagram and Facebook once Pinterest is clean

Fixing the pipe comes before making more content. Roughly 40% of everything published in the last 15 months was never capable of performing — that is recoverable reach on content that already exists.
