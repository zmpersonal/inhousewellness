# Work order

Execute in order. **Stop at each gate and report** — do not run ahead.

Deadline: **15 November 2026.** The category peaks in January and Google needs 6–10 weeks to settle a changed page. Anything landing after mid-November misses the season.

---

## Round 1 — Audit and P0 fixes

### 1.1 Verify the environment
```bash
node -v          # must be v22.x
npm install
```
Confirm `.env` has a token. Run `npm run audit:collections` — if it returns 90 collections, the connection works.

### 1.2 Full audit (read-only)
```bash
npm run audit
```
Then write `reports/audit-summary.md` covering:
- Collections: how many with no description, no SEO title, zero products
- Products: how many missing SEO title, missing featured image alt text, thin descriptions
- Content: empty blogs, articles with no summary
- Broken copy: findings by severity and pattern

**Flag anything the pre-built `data/collections-plan.json` doesn't already account for.** That file was generated from an audit on 3 September 2026 — the store may have changed. Report drift rather than silently working from stale data.

**GATE — stop here. Wait for review before any write.**

### 1.3 Clear broken copy
```bash
npm run fix:broken
```
Expected targets:
- `infrared-saunas` (103 products) — description is `<p>TEST </p>`
- `far-infrared` (58 products) — `:contentReference[oaicite:0]{index=0}` appears three times

This writes an **empty** description deliberately. Both collections are in the copywriting queue; do not fill them with generated text.

Show the diff, get approval, then `-- --apply`.

### 1.4 Strip markup residue
```bash
npm run fix:markup
```
Expected: `dynamic-cold-therapy`, `full-spectrum`, `steam-showers`, `red-light-therapy-panel-skin-pain-recovery`. Run against whatever the scan actually found, not just this list.

Show the diff, get approval, then `-- --apply`.

### 1.5 Unpublish junk collections
```bash
npm run fix:unpublish
```
The script checks navigation menus and skips referenced handles. **Also grep the theme** — the Admin API can't see section settings reliably. The script prints the grep commands to run.

Targets (from `collections-plan.json`):

*Zero products, published:* `steam-sauna` `dynamic-cold` `sauna-bestseller` `sauna-generator` `sauna-best-seller`

*Operational, 311 products total:* `non-bb` (189) `more` (52) `free-bonus` (64) `customers-only` (6) `cold-plunge-favorites` (10) `digital-downloads` (3)

*App-generated:* `avada-best-sellers` (664) — **check the AVADA app doesn't break first**

`customers-only` may be gated by a customer-tag app. Check before unpublishing.

Show the list, get approval, then `-- --apply`.

### 1.6 Best Sellers, top 20
Client decision: keep `best-selling-products`, capped at 20 products.

Shopify collections have no product cap, so this needs one of:

**(a) Manual collection, script-maintained.** Query the top 20 by units sold over a rolling 90 days (`read_orders` scope), then set collection membership. Genuinely 20 products on the page, best for SEO. Needs a scheduled re-run.

**(b) Theme render limit.** Leave the collection as-is and cap the template at 20 with pagination removed. Simpler, but the collection still *contains* 673 and paginated URLs may remain crawlable.

Recommend (a). Build `scripts/apply/sync-best-sellers.js` following the same dry-run/backup/changelog pattern as the others. **Ask before building** — confirm the client wants the ongoing sync.

Separately: `newest-products` is marked `DECIDE`. Shopify already provides `/collections/all` for free, so a catch-all collection may be redundant. Grep the theme for references before recommending.

**GATE — stop. Report what changed, then wait.**

---

## Round 2 — Theme fixes

Pull the theme to `theme/` on an **unpublished branch**. Never write to the live theme.

```bash
shopify theme pull --store inhousewellness.myshopify.com
```

### 2.1 Press logo row
Wire from `data/press-links.json`. Eight outlets, eight logos.

Two complications, both noted in that file:
- **Healthline has two articles.** One logo can't link to both.
- **Healthgrades has a logo but no URL.** Either it gets sourced or the logo comes out.

**Recommended approach:** build `/pages/press` listing all eight with your own summaries, link every logo to that page, and link out from there. Solves both problems, keeps the link equity on-site, and creates a page that can rank. Propose this before building the direct-link version.

### 2.2 Homepage bugs
- Truncated titles in the best-sellers grid: "Luxury …", "Dynamic …", "Finnmar…"
- Body copy to 17px minimum sitewide (audience is 40–60)

### 2.3 Blog index pages
Add H1 and meta description to the four blog index pages. Unpublish or fill the two empty blogs — `media-responses` and `home-improvement-reviews`, both zero articles.

Push the branch and report what to review. **A human publishes.**

**GATE — stop.**

---

## Round 3 — Collection copy

Blocked until `data/worksheet.csv` exists (the client-filled sheet, exported from the Collections tab).

### 3.1 Import
```bash
npm run import:plan
```

### 3.2 SEO titles and metas
```bash
npm run apply:seo
```
Fills empty fields only. Many existing metas are decent — don't overwrite without `--overwrite` and explicit approval. The script warns on titles over 60 chars and metas over 155.

### 3.3 Draft descriptions
For every collection with action `WRITE`, `REWRITE`, or `URGENT`, build a spec from `data/products.json` — the real price band, capacity range, wood types, EMF tier, vendors in that collection — then draft 150–300 words per `CLAUDE.md` voice rules to `content/collections/{handle}.md`.

Front matter:
```yaml
---
handle: cold-plunge
keyword: cold plunge tub
status: draft
---
```

**Draft ten first and stop.** If the voice is wrong across ten, it's wrong across eighty — fix `CLAUDE.md` and regenerate rather than editing outputs one at a time.

A human changes `status: draft` to `status: approved`. `apply:copy` skips anything not approved.

### 3.4 Apply
```bash
npm run apply:copy
```

---

## Priority collections

If time runs short, these come first — highest product count against real search volume.

| Handle | Products | Keyword | Vol/mo | CPC |
|---|---|---|---|---|
| `infrared-saunas` | 103 | infrared sauna | 110,000 | $5.66 |
| `saunas` | 138 | home sauna | 40,500 | $3.72 |
| `outdoor-saunas` | 47 | outdoor sauna | 33,100 | $4.01 |
| `cold-plunge` | 31 | cold plunge tub | 27,100 | **$5.95** |
| `barrel-saunas` | 19 | barrel sauna | 22,200 | $2.94 |
| `sauna-heaters` | 104 | sauna heater | 12,100 | $4.54 |
| `steam-saunas` | 17 | steam sauna | 12,100 | $3.38 |
| `sauna` | 70 | traditional sauna | 9,900 | $5.04 |
| `indoor-sauna` | 4 | indoor sauna | 8,100 | $4.39 |
| `far-infrared` | 58 | far infrared sauna | 6,600 | $5.62 |
| `full-spectrum` | 26 | full spectrum infrared sauna | 6,600 | **$9.76** |
| `red-light-therapy` | 39 | red light therapy sauna | 6,600 | $6.56 |

**Cold Plunge is the biggest single gap** — 31 products, no description, no ranking, against a 27,100/mo term at the second-highest CPC in the catalogue.

---

## Blocked — do not proceed without an answer

| Question | Blocks |
|---|---|
| EMF hierarchy: is `/collections/low-emf` the hub, with ultra-low and near-zero as children? | Copy for those three. Highest-CPC cluster in the store ($9.15–$30.02), currently split three ways. |
| Are BBQ grills, outdoor kitchens, fire pits, fireplaces in scope? 11 collections, ~155 products, all marked `SCOPE?` | Whether to write copy for them at all |
| `newest-products` — becomes "Products", or unpublish in favour of `/collections/all`? | 1.6 |
| Duplicate pairs: `scandia` / `scandia-manufacturing`, `chimneys` / `chimney-option` | Merge decisions |
| Bylines — likely resolved. Dr. Timur Alptunaer is quoted in six national outlets per `press-links.json`. Confirm he can be named as author or reviewer on health content. | Author schema, E-E-A-T |

Ask. Don't guess.
