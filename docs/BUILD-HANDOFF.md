# InHouse Wellness — Social Build Handoff

Everything produced so far, and where it lands when the Claude Code project is assembled.
Read alongside `autoposter-adjustments-inhousewellness.md`.

---

## Assets ready to drop in

| File | Goes to | Status |
|---|---|---|
| `inh-cards/tokens.css` | `templates/tokens.css` | Done |
| `inh-cards/cards.html` | `templates/cards.html` | Done — 9 archetypes, 3 sizes |
| `inh-cards/render.py` | `scripts/render.py` | Done — size-aware validator |
| `inh-cards/fonts/` | `templates/fonts/` | Done — 4 woff2, self-hosted |
| `inh-cards/sample.json` | `fixtures/pinterest.json` | Done — render test |
| `inh-cards/ig.json` | `fixtures/instagram.json` | Done — render test |
| `pinterest-keyword-queue.json` | `data/keyword-queue.json` | Done — 103 items, needs URL verification |
| `pinterest-keyword-queue.csv` | — | Human review copy |
| **`reels-seed.json`** | **`data/reels-seed.json`** | **Done — 12 Reels, 4 sets** |

---

## ⚠️ The Reel sets go in at build time

`reels-seed.json` holds 12 Reels across 4 sets, each derived from a post with **measured**
positive engagement in the Buffer history — not invented. Load it as seed content for the
first month of Reel production.

**Build order is specified in the file and matters:**

1. **Set 3 — Same temperature, different heat.** Lowest compliance risk, hits the two
   lowest-difficulty keywords in the queue (`infrared vs steam sauna` KD 2,
   `dry sauna vs wet sauna` KD 4). Learn the format here.
2. **Set 4 — The buying correction.** Highest commercial intent.
3. **Set 2 — Cardiovascular load.** Needs the Golden Designs footage **and** the
   health-claim validator live. Do not build before both exist.
4. **Set 1 — The stress response.** Reel 1-3 carries a required cardiac disclaimer.

**11 of 12 need no footage** — they render free from the existing card system. Only Set 2
and reel-3-2 require the physical unit.

Every `title` field is the frame-zero on-screen text, written to work silently. This
audience watches muted; if the hook needs audio it doesn't exist.

---

## Locked decisions

- **Blotato is the only video tool.** Not Revid, not Opus, not Higgsfield.
- **No AI avatars or synthetic presenters.** Voice-over only (Bill or Brian), animation,
  or real footage. A generated human making health claims to a 40–60 US audience
  evaluating an $8,000 purchase is a credibility liability.
- **No trending audio.** Library must stay evergreen.
- **No brand intro card.** Two seconds of logo spends the entire hook window.
- **Post to Facebook Reels and Instagram Reels**, separate captions per platform.
  FB skews older and is likely the higher-value surface for this buyer.
- **Palette:** `#1B1613` base, `#E9E5DD` type, `#E0A03C` heat, `#6FA8B8` cold.
- **Type:** Fraunces 700 display, IBM Plex Sans 400/600/700 data. Self-hosted.
- **Brand device:** ticked measurement rule, left edge, every card.

---

## Open items

**Blocking:**
- Authorize Pinterest + Instagram in Blotato — currently Facebook only
- Measure credit burn: 5 test renders. 1,750 credits at $6/1,000 remaining.
  This decides the Reel format mix.
- Verify every `source_article` and `link` in the keyword queue resolves.
  Three referenced tools don't exist yet.
- Create the 6 Pinterest boards; pull IDs via `blotato_list_pinterest_boards`

**From the user:**
- Logo — monochrome mark for the 24px footer slot, against the locked palette
- Confirm whether the RSS `network/customScheduled` path is decommissioned
- Check the IG posts showing 3–4 comments on 4–7 reach — likely a pod, and
  if so it's actively suppressing the account

**Still to write:**
- Caption generator: queue row → Pinterest fields + IG carousel payload + FB native copy,
  one call per cycle
- Output validator (adjustment C2) — build before any generation logic
- Health-claim validator (adjustment A2) — gates Set 2

---

## Reminders that cost real reach if forgotten

- **Per-platform copy always.** 207 of 300 historical posts shared caption text.
- **Facebook: link in first comment**, never in the post body.
- **Pinterest pins need title + description + altText + link** or they don't publish.
  75 blank pins averaged 3.0 impressions; pins with text averaged 106.2.
- **Facebook Groups stay manual.** Automating them gets accounts banned.
- **Measure saves and reach, not likes.** Saves are currently zero across all 322 posts.
