# InHouse Wellness — Seasonal SEO Action Plan
### Built for execution in Claude Code · 3 September 2026

**The clock:** the category peaks in January and troughs in July. `infrared sauna cost` runs 1,900 in January against 880 in July. `are infrared saunas safe` runs 2,400 against 720. Google needs roughly 6–10 weeks to settle a changed page. **Everything below must be live by 15 November.** That is ten weeks.

---

## What the store audit found

Pulled live from the Shopify Admin API. This changes the priority order — several of these are bugs, not opportunities, and they're on your highest-value pages.

**673 products. 50+ collections. 112 blog articles across 6 blogs.**

### Live bugs on commercial pages

| Issue | Where | Impact |
|---|---|---|
| Collection description is literally `<p>TEST </p>` | **Infrared Saunas** (103 products) | Your single biggest commercial collection has placeholder text as its body copy |
| Leaked AI citation markers in body copy — `:contentReference[oaicite:0]{index=0}` appears three times | **FAR Infrared** (58 products) | Visible garbage on a live page. Reads as unedited AI output to any human and any quality rater |
| 44 of 50 collections have **empty** `descriptionHtml` | Almost everything | Including Saunas (138), Sauna Heater (104), Traditional Saunas (70), Outdoor Saunas (47), Cold Plunge (31) |
| Operational collections published and indexable | **Non BB** (189 products), **More** (52), **Free Bonus Infrared** (64), **Customers Only** (6) | 311 products sitting on thin, meaningless, crawlable pages. "Non BB" is your second-largest collection by product count |
| `seo.title` is null on most high-value collections | Saunas, Infrared Saunas, Sauna Heater, Traditional Saunas, Outdoor Saunas, Low EMF, Ultra Low EMF, Near Zero EMF, Barrel Saunas, Red Light Therapy, Chromotherapy | Title tags fall back to bare collection name. These are free rankings being left on the floor |
| Two blogs with zero articles, published | Media Responses, Home Improvement Reviews | Empty index pages |

### The cannibalisation problem, confirmed

You have **three separate EMF collections**: Low EMF (26 products), Ultra Low EMF (22), Near Zero EMF (24). This is your highest-CPC cluster in the entire catalogue — `low emf sauna` at $9.15, `ultra low emf` at $30.02 — and you're splitting it three ways with no descriptions and no SEO titles on any of them. The earlier research showed these ranking at 16–18. This is why.

Same pattern on saunas: **Saunas (138)** and **Traditional Saunas (70)** and **Infrared Saunas (103)** and **FAR Infrared (58)** and **Full Spectrum (26)** overlap heavily with no hierarchy declared.

### What this means for sequencing

The earlier plan led with building tools. **Fix the store first.** Roughly 40 hours of collection work will move more revenue this season than a calculator will, because the pages already exist, already have products attached, and are currently broken. The tools still matter — they're the link engine — but they ship second.

---

## Setup — do this before any task

### 1. Create the repo

```
inh-seo/
├── CLAUDE.md
├── .env                    # gitignored
├── scripts/
│   ├── lib/shopify.js      # Admin API client, rate-limit aware
│   ├── audit/              # read-only: dump current state to /data
│   └── apply/              # writes, all with --dry-run default
├── data/                   # audit output, CSVs, generated copy for review
├── content/                # markdown source for collection + article copy
└── theme/                  # Shopify CLI theme checkout
```

### 2. Credentials

Shopify admin → Settings → Apps → Develop apps → create a custom app.
Scopes: `read_products`, `write_products`, `read_content`, `write_content`, `read_themes`, `write_themes`, `read_online_store_pages`, `write_online_store_pages`.
Put the Admin API access token in `.env` as `SHOPIFY_ADMIN_TOKEN`, shop domain as `SHOPIFY_SHOP=inhousewellness.myshopify.com`.

*Note:* the Shopify MCP connector blocks writes to the live theme. Theme work has to go through Shopify CLI on an unpublished branch, then publish manually. That's the right workflow anyway.

### 3. Write CLAUDE.md

This is the highest-leverage file in the repo — it stops Claude Code drifting off-brand across fifty collection descriptions. It should contain:

- **Positioning:** buyer's agent, credibility over comfort, "we publish the measurement." Lowest price on the model you choose, no premium tax.
- **Voice rules from the Brand Guide**, including the Never list: no manufactured scarcity, no wellness dialect, no health claim without its population and limitation, no benefit stated without its condition.
- **The keyword map** — which collection owns which query (table below).
- **Copy constraints:** 150–300 words per collection description, answer-first opening (the specific fact in the first sentence), one H2 minimum, no em-dash asides, no "elevate your wellness journey" register.
- **Hard rule:** never write a health claim. Link to healthresearchdatabase.com instead.
- **Verification rule:** every script writes to `data/` first for human review, then applies. `--dry-run` is the default.

### 4. Baseline before touching anything

```
scripts/audit/dump-collections.js     → data/collections-before.json
scripts/audit/dump-products.js        → data/products-before.json
scripts/audit/dump-articles.js        → data/articles-before.json
```

Also start rank tracking now, before any change lands: `costco sauna`, the three EMF terms, `infrared sauna for muscle recovery`, `infrared sauna cost`, `sauna cost`, `how much does a sauna cost`, `sauna installation cost`, `are infrared saunas safe`, `cold plunge tub`.

---

# WEEK 1 — Stop the bleeding

Everything here is a bug fix. No strategy required, no decisions blocked.

### 1.1 Kill the `TEST` and the leaked AI markers
**Claude Code task:** scan every collection `descriptionHtml` for placeholder patterns — `TEST`, `:contentReference`, `oaicite`, `data-start=`, `lorem`, empty `<p>` tags — and report matches to `data/broken-copy.json`.

Then rewrite Infrared Saunas and FAR Infrared properly. These two are 161 products and among your highest-intent pages.

Also strip the `data-start` / `data-end` / `class="relative -mx-px..."` Tailwind residue out of Dynamic Cold Therapy and Full Spectrum — that's pasted-from-ChatGPT markup bloating the HTML.

*Verify:* re-run the scan, zero matches. Load both pages, read them as a customer would.

### 1.2 Deindex the junk collections
**Non BB (189), More (52), Free Bonus Infrared (64), Customers Only (6).**

These are operational groupings, not shopping destinations. Options in order of preference:
1. Unpublish from the Online Store channel — cleanest, removes the URL entirely.
2. If the theme depends on them, add `<meta name="robots" content="noindex,follow">` via a template condition on those handles.

Do not delete them. Products may depend on the membership.

*Verify:* `site:inhousewellness.com/collections/non-bb` returns nothing after recrawl. Check Search Console coverage in two weeks.

### 1.3 Resolve the EMF cannibalisation
**This is the single highest-value fix in the document.** Three collections, 72 products, $9.15–$30.02 CPC, currently splitting authority three ways.

Decide the hierarchy, then implement:

| URL | Role | Target |
|---|---|---|
| `/collections/low-emf` | **Canonical hub.** Full explainer of what EMF means, measurement distances, the three tiers | `low emf sauna`, `low emf infrared sauna`, `lowest emf sauna` |
| `/collections/ultra-low-emf` | Child page, canonical to itself, links up to hub | `ultra low emf sauna` |
| `/collections/near-zero-emf` | Child page, canonical to itself, links up to hub | `near zero emf sauna` |

Each child page opens with a one-line definition of what that tier actually means in mG, links to the besthomeinfraredsauna.com EMF index as the measurement source, then links back to the hub. The hub links down to both children plus the existing `/blogs/saunas/low-emf-vs-near-zero-emf-infrared-sauna-guide` post.

*Do not build a competing EMF index on INH.* The satellite has 90 models with published methodology. Cite it.

*Verify:* the three pages each have a distinct primary keyword in their title tag, and internal links form hub-and-spoke rather than a flat trio.

### 1.4 Fix the homepage bugs
Truncated product titles in the best-sellers grid ("Luxury …", "Dynamic …", "Finnmar…"). Body type to 17px minimum. Both were flagged in the Brand Strategy and are still live.

### 1.5 Link every press logo to its article
AOL, Healthline, Yahoo Health, Men's Journal, Houzz, Healthgrades, Woman's World, Eat This Not That. An unlinked logo row is decorative; a linked one is evidence. Highest trust-per-hour item in this document and it's an afternoon of theme work.

---

# WEEKS 2–4 — The collection sweep

44 collections need descriptions and most need SEO titles. This is the bulk of the seasonal gain and it's exactly the kind of work Claude Code does well: repetitive, structured, verifiable.

### 2.1 Build the keyword map
Before writing a word, assign one primary keyword per collection and put it in `CLAUDE.md`. Starting point from the research:

| Collection | Products | Primary keyword | Vol/mo | CPC |
|---|---|---|---|---|
| Saunas | 138 | `home sauna` | 40,500 | $3.72 |
| Infrared Saunas | 103 | `infrared sauna` | 110,000 | $5.66 |
| Sauna Heater | 104 | `sauna heater` | 12,100 | $4.54 |
| Traditional Saunas | 70 | `traditional sauna` | 9,900 | $5.04 |
| FAR Infrared | 58 | `far infrared sauna` | 6,600 | $5.62 |
| Outdoor Saunas | 47 | `outdoor sauna` | 33,100 | $4.01 |
| Red Light Therapy | 39 | `red light therapy sauna` | 6,600 | $6.56 |
| Cold Plunge | 31 | `cold plunge tub` | 27,100 | **$5.95** |
| Full Spectrum | 26 | `full spectrum infrared sauna` | 6,600 | **$9.76** |
| Low EMF | 26 | `low emf sauna` | 1,300 | **$9.15** |
| Near Zero EMF | 24 | `near zero emf sauna` | — | — |
| Ultra Low EMF | 22 | `ultra low emf sauna` | — | **$30.02** |
| Barrel Saunas | 19 | `barrel sauna` | 22,200 | $2.94 |
| Steam Saunas | 17 | `steam sauna` | 12,100 | $3.38 |
| Hybrid | 14 | `hybrid sauna` | — | — |
| Cold Plunge Cooling System | 11 | `cold plunge chiller` | — | — |
| Indoor Sauna | 4 | `indoor sauna` | 8,100 | $4.39 |
| Cabin Sauna | 3 | `cabin sauna` | — | — |

**Cold Plunge is the standout.** 31 products, no description, no ranking, against a 27,100/mo term at $5.95. It's the biggest single gap in the catalogue.

**One keyword, one collection.** Where two collections want the same term, one wins and the other canonicalises up or targets a modifier.

### 2.2 Generate the descriptions
**Claude Code task:** for each collection, read its products from `data/products-before.json`, generate a 150–300 word description to `content/collections/{handle}.md` for review, then apply via `collectionUpdate`.

Each description needs:
- **Answer-first opening.** A specific fact, not a mood. "Infrared saunas run at 120–140°F rather than the 180°F of a traditional room, which is why sessions run longer." Not "Discover the ultimate in home wellness."
- One H2 minimum, structured for extraction.
- A real spec detail drawn from the actual products in that collection — price range, wood type, EMF tier, capacity.
- The disclosure line where it applies: freight, electrical, assembly, foundation.
- No health claims. Link to healthresearchdatabase.com for evidence.
- No manufactured urgency.

*Review gate:* read ten at random before applying all 44. If the voice is off, fix `CLAUDE.md` and regenerate rather than editing outputs one by one.

### 2.3 SEO titles and meta descriptions
Same batch. Pattern: `{Primary keyword} | {differentiator} | InHouse Wellness`, under 60 characters. Meta description under 155, includes the primary keyword and one concrete number.

The existing meta descriptions are mostly decent — **don't overwrite ones that are already good.** The script should only fill `null` fields unless explicitly told otherwise.

### 2.4 Product-page disclosure block
**Claude Code task:** create a metafield definition `custom.total_cost_disclosure` on products, populate it per product type, and render it on the product template.

Content: freight and delivery type, whether a dedicated 240V circuit is required, assembly requirement, foundation requirement for outdoor units. This is the Brand Strategy commitment and it's also the raw data the True Total Cost tool will consume, so building it now means the tool has a source when you get there.

---

# WEEKS 4–7 — True Total Cost

The one tool with real search demand: ~6,000–7,000/mo across the cost cluster.

### 3.1 Build it
**Page:** `/pages/true-total-cost` (Shopify page) or `/tools/true-total-cost/` if you can route it. Interactive component as a theme section with a JS block, reading product data from the metafields built in 2.4.

**Inputs:** sauna type · size · ZIP · existing 240V panel (yes/no/unknown) · indoor or outdoor · sessions per week.

**Outputs, in order:** purchase price range → freight and delivery → electrical (circuit needed? typical electrician cost in that ZIP) → foundation → assembly → annual running cost at live EIA rates → maintenance → **5-year total cost of ownership and cost per session.**

**Reuse, don't rebuild:** the EIA rate data and 75-metro climate normals already exist on the climate index satellite. Pull from there.

### 3.2 Two supporting pages
- `/pages/sauna-running-cost` → `how much does a sauna cost to run` (110/mo)
- `/pages/sauna-installation-cost` → `sauna installation cost` (480/mo, **$5.78 CPC**, highest in the set)

### 3.3 The requirements that make it citable
Published methodology page · downloadable CSV · visible and machine-readable "last updated" · `Dataset` and `SoftwareApplication` structured data · answer-first paragraph with the number in the first 40 words · a spec table (tables get quoted by AI answers, prose gets paraphrased) · in-content link to the matching collection above the fold.

---

# WEEKS 7–10 — Safety hub, and content

### 4.1 `/pages/sauna-safety` targeting `are infrared saunas safe`
1,300/mo, $2.43 CPC, competition 77. This is the highest-volume education term you can realistically win this season.

The Recall Checker lives **inside** this page, not as its own destination — nobody searches "recall" (~40/mo across every phrasing tested). CPSC data ingested daily, filtered to the relevant categories.

**Accuracy guardrails, non-negotiable:** never output "this product is safe" — output "No recall on record as of [date], based on CPSC data last synced [timestamp]." Always link the CPSC source record. Cover your own catalogue on equal terms; a checker that omits the brands you sell is worthless as credibility and obvious as marketing.

### 4.2 Health-outcome content
`sauna for cardiovascular health` (40,500/mo, competition **4**), `infrared sauna for pain relief` (8,100, competition 32), `sauna for heart health` (5,400, competition 15). Route the evidence through healthresearchdatabase.com rather than making claims on INH.

### 4.3 Comparison hub
One canonical page per pair, every phrasing variant in the H2s, FAQ schema, spec table. `sauna vs steam room` (14,800, fires an AI Overview). `infrared vs traditional sauna` (6,600, **nine phrasings in one bucket** — a page answering one loses).

### 4.4 The five missing brand reviews
Sunlighten (18,100) · Clearlight (12,100) · Sun Home (9,900) · Almost Heaven (9,900) · HigherDose (6,600). All larger than anything currently covered, and this is the asset class the site already ranks with.

### 4.5 Striking distance
- `costco sauna` from position 10 → top 5. 40,500/mo. Refresh with 2026 pricing, internal-link from every sauna post.
- `infrared sauna for muscle recovery` from 28. 6,600/mo at competition 0.01.
- `/collections/floatation-therapy-tanks` — position 98 for a 40,500/mo term, 6 products, no description. Include it in the 2.2 sweep.

---

# TECHNICAL — runs alongside, all Claude Code

**5.1** `llms.txt` at root, listing the tools, methodology pages, and hubs.
**5.2** Structured data audit and fix: `Product` with real availability on all 673, `CollectionPage` on collections, `FAQPage` on comparison pages, `Dataset` on the tools.
**5.3** Internal link graph — script it. Every blog post links to its cluster's tool and collection; every collection links up to the education hub and down to products; no commercial destination more than one click from a tool. Generate the link map to `data/link-graph.json`, review, apply.
**5.4** Static landing pages for the filtered collection URLs currently blocked from crawling. "Indoor infrared sauna" is a real commercial query behind a faceted URL.
**5.5** H1 and meta on the blog index pages. Unpublish or fill the two empty blogs (Media Responses, Home Improvement Reviews).
**5.6** Answer-first rewrite pass on the top 20 blog posts by traffic — the number in the first 40 words.

---

# OFF-SITE — ongoing, not Claude Code

Target **15–25 new referring domains per month.** 67 today; competitors at 31,286 and 56,553. This is the actual ceiling on rankings and no amount of on-site work substitutes for it.

**Point links at the tools and the safety hub, not the collections.** Allocation: 45% tools and `/safety/`, 25% education hubs, 15% collections (branded or naked URL only), 15% homepage. **Zero exact-match commercial anchors to collection pages in V1** — at 67 referring domains that profile is the clearest possible footprint.

**Pitch order for the guest posts and insertions you've started:**
1. The CPSC recall data as a data story — accepted by editors who reject product content, and repeatable every time a new recall lands
2. True Total Cost as a cost story — "the advertised price is X, the real five-year cost is Y"
3. Warranty terms as a consumer-protection story
4. Health-outcome content routed through the research database

**Reference network:** add the recommended-retailer disclosure page to all ten, matching the `outdoorsteamsauna.com/recommended-retailer/` framing. Add tool links where genuinely relevant as those pages get worked on. Cross-link the two fit tools and point external links at one of them, not both.

---

# WHAT NOT TO PUT IN CLAUDE CODE

- **Bulk-publishing generated collection copy without reading a sample.** 44 descriptions in one voice, all slightly wrong, is worse than 44 empty ones.
- **Anything touching the live theme.** Shopify blocks it and it's the right block. Branch, review, publish manually.
- **Health claims.** Hard rule in `CLAUDE.md`.
- **The recall data pipeline running unattended before it's been checked against CPSC by hand.** Get one week of output verified manually first.

---

# THE HONEST VERSION OF THE TIMELINE

Ten weeks to 15 November. Weeks 1–4 are store fixes and the collection sweep — that's the work that will actually move this season, because those pages already exist and already have products. Weeks 4–10 are the tools and content, which are more about next season and about the link engine than about January revenue.

If something has to give, give up the Warranty Decoder. It has ~100 searches a month and its value is conversion and citation, both of which keep. Do not give up the collection sweep.

**The Warranty Decoder is also still blocked** on the MAP and dealer-terms question from the Brand Strategy, which has never been answered. Worth resolving before it reaches the top of the queue.
