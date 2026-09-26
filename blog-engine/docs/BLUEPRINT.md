# InHouse Wellness Blog Engine — Build Blueprint

**Version:** v0.4 draft (Phase 0/1). Review model, keyword source, schema placement and SERP research locked; author, routing, images, north star and cost ceiling still open. Nothing is built yet.
**Runs under:** `agent-harness` (meta-rules, approval tiers, runlog) and `build-loop` (phases). Content spec is the existing `seo-blog-generate` house style, with the German sauna article as the golden reference.

---

## 1. What it does

Each week the engine produces 3–5 new SEO- and AI-answer-optimized articles for inhousewellness.com and takes each one from keyword to a scheduled post on the correct Shopify blog, in the house format: snippet lede, TL;DR box, author/E-E-A-T box, same-window TOC, verified tables, FAQ mirrored in FAQPage schema, `nofollow` sources, and internal links to real collections.

## 2. The governing principle: the model writes, code decides

The model is used for three things only: synthesizing SERP and intent research, drafting the outline brief, and writing article prose (returned as structured JSON, not HTML).

Everything else is deterministic code: which keyword to use, dedup and cannibalization checks, which blog it goes to, which product URLs and specs are allowed, HTML rendering, link attributes, schema, validation, publishing, scheduling, state and reporting.

The reason is that every problem from the manual workflow (doubled URLs, wrong `rel`/`target` attributes, FAQ schema drifting from the on-page FAQ, invented product URLs) becomes impossible by construction instead of something the model has to remember.

## 3. Architecture

```
 keyword bank (repo CSV)  ◄── monthly research round (interactive Claude Code session
        │                      using Ahrefs / Semrush / GSC connectors; also snapshots each keyword's top-10 SERP)
        ▼
 [site index]  code  Shopify Admin API → blogs, articles, products, collections (source of truth)
        ▼
 [select]      code  priority, cooldown, cannibalization vs. existing articles, blog quotas
        ▼
 [SERP teardown] fetch top-ranking pages → coverage matrix, gaps, readability benchmarks (§4.11)
        ▼
 [brief]       LLM → brief.json with measurable "beat criteria" + verified source list
        ▼
 [write]       LLM → article.json (lede, sections, faq[], meta, product slots by Shopify ID)
        ▼
 [render]      code → house-style HTML + JSON-LD (Article, BreadcrumbList, FAQPage from the same faq[])
        ▼
 [validate]    code gate → pass │ one narrowed retry │ HOLD
        ▼
 [self-review] separate Claude reviewer: fact-check vs. sources, beat-the-SERP check,
               readability, YMYL, brand/commercial → revise (max 2 loops) │ HOLD   (§4.12)
        ▼
 [pull request] articles + previews + review reports — workflow auto-merges when every gate passes
        ▼
 [publish]     code → D5 breadcrumb → articleCreate (scheduled publishDate, correct blog, SEO fields, schema metafield) → record IDs
        ▼
 [reconcile]   next run: every scheduled article is live or failed (absence = failure) → weekly digest
        ▼
 [your post-publish review]  digest links + review reports; one-command unpublish/correct (§4.10)
```

**Held articles** don't publish. They're listed at the top of the digest with the reason, and the rest of the batch proceeds because articles are independent. A code error, or more than one held article in a batch, halts the whole run.

**Where it runs.** A private GitHub repo plus GitHub Actions. A weekly `generate` workflow runs Claude Code headless: manual dispatch for the first batch, cron after that. It opens a pull request that is a record rather than an approval step, and the workflow merges it automatically once every gate passes. A `publish` workflow runs on merge. Articles are created with future publish dates, and Shopify's article API supports scheduling with a publish date, so Shopify releases them on the scheduled days and nothing needs to run then.

**Cloudflare: not in v1.** GitHub Actions covers scheduling and the repo covers state. Possible later uses are a webhook receiver or a hosted preview page, and they get added only if a real need appears.

## 4. Components

### 4.1 Keyword bank — `data/keywords.csv`

| Column | Purpose |
|---|---|
| `keyword`, `cluster` | Target phrase and topic cluster (drives blog routing) |
| `intent`, `article_type` | informational / commercial / comparison; guide / best-X / comparison / review |
| `volume`, `difficulty`, `source`, `source_date` | Provenance for every number (withhold beats guess) |
| `priority` | Computed in code from volume, difficulty, commercial value, GSC striking distance |
| `feature_collections` | Collection handles to steer toward (must exist in the site index) |
| `status` | new → queued → drafted → scheduled → published / rejected |

**Refill — DECIDED: monthly interactive session, no new cost.** Once a month you open Claude Code in the repo and run the `/refill-bank` command, about 20–30 minutes. It:

1. Pulls candidates from your connected tools: Ahrefs/Semrush keyword and competitor-gap reports, Search Console "striking distance" queries (positions roughly 8–30 with no dedicated article, via the HYPD connector), and question-style prompts from Promptwatch.
2. Scores and dedupes them in code against the existing bank and the site index, dropping anything an existing article already targets.
3. Assigns cluster, blog, intent and article type by rule, marking uncertain ones for you.
4. Opens a PR adding 15–25 rows. You skim and merge (🟡).

**Sizing:** at 3–5 articles a week, one refill needs to supply 13–22 articles. The weekly run reports weeks of supply left, alerts at 3 weeks, and halts at zero. It never repeats a keyword and never invents one, and a missed refill means a skipped week, not filler.

**Connector check in R3:** Claude Code has to be able to reach the same connectors. They're added as remote MCP servers in the repo's `.mcp.json` and authenticated once in your local session. If any of them can't connect from Claude Code, R3 falls back to running the pull in claude.ai and exporting a CSV into the repo.

### 4.2 Site index (pulled fresh every run)

Pulled via the Admin GraphQL API: all blogs (ID, handle), all articles (title, handle, tags, summary), products (title, handle, vendor, price range, key metafields such as capacity, style and EMF), and collections. Two hard rules follow from it:

- An internal link may only point at a URL that exists in the index.
- A price or spec about an InHouse product may only appear if it is present in the index. The live catalog is the source of truth.

The same index powers cannibalization checks (no new article that competes with an existing one for the same query) and contextual links to related existing posts.

### 4.3 Blog routing (config file, enforced in code)

| Cluster | Blog |
|---|---|
| Saunas: traditional, infrared, barrel, heaters, etiquette, buying guides | `/blogs/saunas` |
| Cold plunge, ice baths, contrast therapy | `/blogs/cold-plunge` |
| Red light, recovery, general wellness | `/blogs/wellness` |
| TBD — confirm what belongs here | `/blogs/fire` |
| TBD — e.g. research-heavy explainers? | `/blogs/institute` |

The breadcrumb schema uses the routed blog, not a hardcoded "Saunas".

### 4.4 Article spec

`spec/house-style.md` is copied into the repo and versioned. It is governance: the machine can't edit it, and changes go through a retro proposal. v1 article types are informational guides (German sauna pattern), best-X roundups and comparisons. Competitor product reviews are deferred to v1.1 because claims about competitors need their own verification path.

### 4.5 Renderer

Templates in Jinja with a unique class prefix per article and the espresso/cream/gold palette. The TOC is generated from section IDs. A link post-processor stamps every `<a>`: TOC anchors get no `target`, internal links get `target="_blank" rel="noopener"`, external links get `target="_blank" rel="nofollow noopener"`. The FAQ HTML and the FAQPage schema are rendered from the same list, so they can't drift.

### 4.6 Validator (built before any generation code)

An article is rejected if any of these fail:

- **Structure:** no `<h1>` in the body; lede, TL;DR, author box, TOC, FAQ, sources and disclaimer all present; every TOC anchor has a matching `id`.
- **Lengths:** lede 40–60 words; SEO title ≤ 60 characters; meta description ~140–160; word count within the range for the article type; FAQ has 8–12 items.
- **Schema:** every JSON-LD block parses; FAQPage matches the on-page FAQ exactly; breadcrumb matches the routed blog.
- **Links:** internal links exist in the site index and carry the right attributes; external links carry `nofollow noopener` and resolve (a 429 counts as *unknown*, never as dead); no raw-URL or "click here" anchor text; no doubled URLs.
- **Truth:** every price or spec numeral about an InHouse product appears in the site index; no fabricated-experience phrases ("we tested", "in our lab", "after 30 days of use") unless a real first-hand note was supplied.
- **Health/YMYL:** health-cluster articles carry the medical disclaimer; "detox" is never asserted as an outcome.
- **Hygiene:** no "As an AI", "In conclusion", TODO, lorem ipsum, `[insert` placeholders; handle doesn't collide with an existing article; primary keyword appears in title, lede and at least one H2.

On failure, only the failing article is retried once. If it fails again, that article is HELD (not published, reported at the top of the digest). A degraded article is never published. The German sauna article becomes the known-good test fixture, and deliberately broken copies of it become the known-bad fixtures.

### 4.7 Publishing

- **Auth:** new Shopify custom apps must now be created in the Dev Dashboard and use client credentials. Tokens are short-lived (reported as 24 hours), so the workflow fetches a fresh one on every run.
- **Scopes:** read products and content, write content (exact scope names confirmed in R2).
- **D5 duplicate protection:** a breadcrumb is committed before `articleCreate`; the next run halts if it finds one; it's cleared only after the article ID is recorded.
- **Per article:** correct `blogId`, handle, title, author, summary, tags, future `publishDate` from the cadence config, SEO title and meta description, featured image (decision D6).

### 4.8 Schema placement — DECIDED: metafield + theme snippet

- The renderer outputs the Article, BreadcrumbList and FAQPage JSON-LD as one JSON array. The publisher writes it to an article metafield (proposed `custom.jsonld`, type JSON) in the same `articleCreate` call.
- A small theme snippet in the article template prints the metafield inside `<script type="application/ld+json">`, only when it exists. Older hand-built posts with inline schema are unaffected.
- The article body contains no `<script>` tags, so later edits in the rich-text editor can't break schema.
- **Theme change is 🔴 human-applied.** Claude Code writes the snippet and a test on a duplicated, unpublished theme, then you publish it. Proven in R2: the rendered page source must contain the schema, and Google's Rich Results Test must parse it.
- **Validator addition:** metafield JSON parses; the FAQPage in it matches the on-page FAQ; the body contains no `<script>`.
- **Dedup watch:** if an SEO app or the theme already emits Article or Breadcrumb schema on blog posts, the snippet emits only what's missing. R2 checks for duplicates.

### 4.9 Measurement

- **Weekly:** Search Console pull for each new URL (indexed?, impressions, clicks, average position at 7 / 28 / 90 days) into the digest.
- **Monthly:** AI visibility check in an interactive session using Promptwatch or Ahrefs Brand Radar. These are session connectors, so this step isn't in CI. It's worth saying plainly that AI citation measurement is still approximate.

### 4.10 Review model — DECIDED: Claude reviews before publish, you review after

No human sits between generation and publishing. The pre-publish quality bar is the code validator (§4.6) plus the in-depth Claude self-review (§4.12). You review live articles after they post.

**One-time launch check (reconciles harness Meta-Rule 8).** The harness requires that nothing goes live unseen. That is met once, at engine launch: in R10 you read the first full batch before the first real publish. After that, articles publish without pre-approval.

**Post-publish review.** Each digest (Slack) lists, per article: live URL, blog, primary keyword, the self-review scorecard, every claim the reviewer softened or removed, and any warnings it passed with. You can use it to triage which articles to read closely.

**Correction path.** `gh workflow run correct -f article=<handle> -f action=unpublish|revise -f note="…"` does one of two things. `unpublish` hides the article immediately. `revise` sends it back through review with your note and republishes it. Every correction is logged in `RUNLOG.md` with a cause category (fact / tone / structure / wrong blog / product / other).

**Corrections become rules.** Any correction you make means a gate missed something. Three corrections in the same category become a new validator or reviewer rule (🟡), not a prompt tweak.

**Kill switch (automatic).** Publishing pauses and you get a 🔴 BLOCKED message if any of these happen:
- a factual or health error you correct
- broken schema or a broken page
- a wrong-blog post or a duplicate
- two or more corrections in a rolling 7 days

Publishing resumes only when you clear it; the machine can't. Scheduled-but-unpublished articles are un-scheduled while paused.

**Ramp.** Weeks 1–3 run at 3 articles/week. The cadence rises toward 5 only if you change it in `CLAUDE.md` after 3 correction-free weeks. The machine never raises its own cadence.

### 4.11 SERP teardown — research what ranks now, then beat it

The goal is for every article to be measurably better than what currently ranks: more complete, more useful information, easier to read, and more current. This stage turns "better" into a checklist the reviewer can verify.

**Inputs.** During the monthly refill, Claude pulls each keyword's live top-10 organic results via the Ahrefs or Semrush SERP tools and stores a snapshot in the bank: URLs, positions, date, and whether an AI Overview or featured snippet appears. The CI run can't reach those connectors, and its web search doesn't reproduce Google's ranking order, so the snapshot is the ranking source of record. When the article is written, the run re-fetches the top 5–8 pages so the content comparison is fresh. A page that can't be fetched is skipped and logged, not guessed at.

**Extraction** (code, with the model only where judgment is needed):

| Measured per competitor page | How |
|---|---|
| Word count, H2/H3 outline, tables, lists, images, FAQ, schema types, last-updated date | code |
| Reading grade, average sentence and paragraph length, wall-of-text sections | code |
| Subtopics covered, questions answered, data points and figures given | LLM, structured output |
| Errors, outdated info, unsupported health claims, thin sections | LLM, each cited to the page |
| Where the answer to the core query appears (first 100 words or buried) | LLM |

**Coverage matrix → beat criteria in brief.json:**

- **Must cover:** every subtopic covered by ≥ 3 of the top 5.
- **Information gain (≥ 3 required):** things no top page offers. Typical sources are InHouse's own catalog data (real specs and price ranges in a comparison table), a decision matrix, cost breakdowns, verified numbers from primary sources, step-by-step procedures, and corrections of errors competitors repeat.
- **Answer-first:** the core query is answered in the lede, and every H2 opens with a 1–2 sentence direct answer. This helps both featured snippets and AI engines, which quote self-contained passages.
- **Readability targets:**
  - reading grade at or below the competitor median, capped at grade 9
  - paragraphs of 4 sentences or fewer
  - no H2 section longer than ~300 words without a table, list or subheading
  - a comparison table wherever competitors compare in prose
- **Length:** set by coverage, not word count. Roughly the median of the top 3, with a hard ceiling of 1.4× so the article doesn't pad to "win".
- **Freshness:** figures dated, and "checked <Month Year>" notes on prices and specs.
- **AI visibility:** from the refill snapshot, the questions AI assistants answer on this topic and the sources they cite. Our article answers those questions in clean, quotable passages.

**Originality check (code):** 8-word shingle overlap between our draft and each fetched competitor page must be under 2%. Structure can be informed by competitors; wording can't be copied.

### 4.12 Claude self-review — in depth, before anything publishes

The reviewer is a separate Claude run with a fresh context and an adversarial brief ("find what's wrong; you are accountable if it ships with an error"). It sees the rendered article, brief.json, the fetched sources and the site index. It never grades its own writing in the same context. It runs five passes and outputs structured findings, never prose opinions.

1. **Fact check.**
   - Every factual sentence is extracted and classified: catalog fact / external fact / health claim / opinion.
   - Catalog facts are checked against the site index, in code.
   - External facts and health claims must map to a specific source the run actually fetched. The reviewer re-reads that passage and marks the claim *supported / partly supported / unsupported*.
   - Health claims additionally require a clinical, government or peer-reviewed source, and correct hedging (association ≠ causation).
   - Any unsupported claim is rewritten to what the source supports, or removed. Never kept.
2. **Beat-the-SERP.** Each beat criterion from §4.11 is checked pass/fail with evidence: which must-cover subtopics are missing, which information-gain items actually landed, and whether readability targets are met (numbers computed in code).
3. **Reader experience.** The reviewer reads as a first-time buyer. Is the core question answered in the first screen? Could someone skim H2s plus tables and get the gist? Is anything confusing, repetitive or filler? Is there any sentence a knowledgeable reader would roll their eyes at?
4. **YMYL and safety.** Contraindications are named and not scary, the disclaimer is present, no dosing- or treatment-style advice, no "detox" or cure language.
5. **Brand and commercial.** The house voice holds, product steering is useful rather than pushy, every product mention is accurate to the index, and competitors are treated fairly.

**Scoring and gate.**
- Hard fails: any unsupported claim remaining, any YMYL violation, any validator rule, or originality over threshold. These block publishing.
- Soft scores (1–10): completeness vs. SERP, information gain, readability, reader experience, brand. The article must average ≥ 8 with none below 7 (thresholds in `CLAUDE.md`, human-edited only).
- **Revision loop:** findings go back to the writer as targeted edits for the affected sections only. The article is re-rendered, re-validated and re-reviewed. Maximum 2 loops, then HOLD.

**Calibration.** Before launch (R9), the reviewer is tested against seeded bad drafts with injected false claims, a missing must-cover subtopic, a wall-of-text section and an overclaimed health benefit. It must catch ≥ 95% of injected issues. The German sauna article is the known-good baseline. Your post-publish corrections are fed back as new seeded cases, so the reviewer is re-tested against every miss.

### 4.13 The article package — every Shopify field, specified

Every article is published as one package. Each field has a rule, and the validator checks every field, not just the body.

| Field | Who produces it | Rule |
|---|---|---|
| Blog | code | From cluster → blog routing (§4.3). |
| Title (the on-page H1) | LLM | Natural and compelling; contains the primary keyword (or its closest natural phrasing); ≤ ~70 characters. Example: "What Is a German Sauna? The Ultimate Guide & Etiquette Checklist". |
| Handle (URL slug) | code | From the primary keyword; lowercase and hyphenated; ≤ 6 words; no dates or stop words; unique in the site index; never changed after publish. |
| SEO title (`global.title_tag`) | LLM | ≤ 60 characters **including** whatever the theme appends (e.g. " – InHouse Wellness", measured in R2); primary keyword first; may differ from the H1. |
| Meta description (`global.description_tag`) | LLM | 140–160 characters; answers the query and gives a reason to click; includes the keyword; no clickbait or all caps. |
| Excerpt / summary | LLM | 1–2 sentences, ~180–300 characters, plain text. Shown on blog listing cards, where it works as a teaser. It must **not** duplicate the meta description or the lede word-for-word (the validator checks similarity). |
| Author | config | Decision D4. The name matches the author box and the Article schema. |
| Tags | code picks, LLM suggests | 3–5 tags from a **controlled vocabulary** in `config/tags.yaml`: one type tag (Guide, Buying Guide, Comparison), 1–2 topic tags, 1 product-category tag. Seeded from tags already on the site. The machine can't invent tags; a suggested new tag goes into the digest for you to approve. (Shopify creates a `/tagged/` page per tag, so a small, fixed vocabulary avoids spawning thin pages; R2 checks whether the theme noindexes them.) |
| Featured image + alt | code | Decision D6. Alt text describes the image and includes the topic naturally; descriptive filename. |
| Publish date | code | The next open cadence slot (Mon/Wed/Fri 7am Central to start). |
| Schema metafield (`custom.jsonld`) | code | Article + BreadcrumbList + FAQPage (§4.8). `dateModified` updates on any revision. |
| Open Graph / social card | theme | Derived by the theme from the SEO title, meta description and image. R2 confirms what the theme actually outputs. |
| Body HTML | code renders LLM content | Structure by article type, below. |

**No paste instructions in the body.** The house-style "paste into Shopify" comment block is dropped because the machine sets every field through the API.

**Body structure by article type.** Sections marked * are conditional.

*Informational guide* (the German sauna pattern):
1. Snippet lede: a direct 40–60 word answer to the query.
2. TL;DR / key-takeaways box (4–6 bullets).
3. Author box with a **"How we researched this"** line: number and types of sources, the date checked, and what was not independently tested.
4. TOC (same-window anchors).
5. H2 sections built from the must-cover subtopics and information-gain items (§4.11). Each opens with a 1–2 sentence direct answer. Tables go wherever something is compared.
6. *Myths / common mistakes.
7. Product bridge section + CTA to verified collections or products, where the topic has a commercial link.
8. FAQ, 8–12 long-tail questions (mirrored in schema).
9. Sources (`nofollow`, descriptive text).
10. *"What we still don't know", for health or science-heavy topics.
11. Disclaimer + "checked <Month Year>".

*Best-X roundup:*
1. Lede.
2. "Our top picks" verdict table (best overall / value / premium / by need), each linking to a verified product.
3. Author box.
4. TOC.
5. How we chose (criteria stated honestly, no fabricated testing).
6. One section per pick: who it's for, verified specs, pros/cons, CTA.
7. Full comparison table.
8. Buying guide ("what to consider").
9. Decision matrix (buy if… / look elsewhere if…).
10. FAQ, sources, disclaimer.

*Comparison (X vs. Y):*
1. Lede that answers "choose X if…, Y if…".
2. Quick-verdict table.
3. Author box.
4. TOC.
5. Side-by-side spec/feature table.
6. One section per deciding factor (cost, results, space, maintenance, safety…).
7. Decision matrix.
8. Recommended InHouse options for each side.
9. FAQ, sources, disclaimer.

### 4.14 The research dossier — what is researched for every article

All research is saved per article as `research/<handle>/dossier.json` and committed alongside the article, so you can audit exactly what any claim was based on.

1. **Keyword record** (from the monthly session): primary keyword, 3–8 secondary/related keywords, volume, difficulty, intent, and the SERP snapshot with top-10 URLs, positions, date, and featured-snippet / AI Overview / People Also Ask presence.
2. **SERP teardown** (§4.11): per competitor page, the outline, length, tables, reading grade, freshness, subtopics, questions answered, data points, and errors or gaps. From these: the coverage matrix and beat criteria.
3. **Question research** (feeds the FAQ and H2s):
   - People Also Ask questions from the snapshot
   - AI-assistant prompts on the topic from Promptwatch, with which sources the AI answers cite
   - Search Console queries already landing on related InHouse pages
   - questions answered by no top page (information-gain candidates)
4. **Source research.** For each must-cover subtopic and each factual claim the outline needs, primary sources are found and fetched. Each saved source records URL, title, publisher, date, the exact supporting passage and a tier:
   - A: clinical, government or peer-reviewed
   - B: manufacturer or official body
   - C: reputable publication
   - D: forums or blogs (usable only for "what people ask", never cited)

   Health claims require tier A. Every claim in the article points to a saved passage, which is what the reviewer's fact check (§4.12) verifies against.
5. **Catalog research** (from the site index):
   - matching products and collections with real specs, price ranges and stock status
   - which of them fit which buyer need
   - 3–6 related existing InHouse articles for contextual internal links
6. **Entity list:** the terms, concepts and named things a complete answer should cover (e.g. Aufguss, textilfrei, Saunameister), used as a topical-completeness check.

**Order of work:** keyword record → SERP teardown → questions → outline → source research against the outline → catalog match → brief.json → write. Sources are gathered against the outline rather than before it, so every section is backed by evidence before any prose is written.

## 5. Guardrails (proposed — 🔴 approval, then locked into CLAUDE.md)

1. **No human pre-approval; Claude reviews in depth before publish, you review after** (§4.10, §4.12). Your one-time read of the first batch in R10 satisfies the harness go-live rule.
2. **Cadence is a ceiling, not a quota.** Google's scaled-content-abuse policy targets pages mass-produced mainly to rank, however they're made. If the bank, validator or reviewer can't yield 3 good articles in a week, fewer ship. A held article is better than a weak one.
3. **Every claim is sourced or removed.** Nothing publishes with an unsupported factual or health claim.
4. **No fabricated experience, testing, credentials or reviews.** The byline is a real person with true credentials or "InHouse Wellness Editorial Team" (decision D4).
5. **The machine never** raises its own cadence, adds a blog, edits the validator, reviewer thresholds or house style, or clears its own kill switch.
6. **Secrets live only in GitHub Actions secrets**, never in chat, code or Slack.
7. **Kill switch:** see §4.10. Publishing pauses automatically, and only you can resume it.

## 6. Intake brief draft (becomes `CLAUDE.md` → Project Brief)

1. **Problem:** InHouse needs a steady flow of high-quality, conversion-aware articles that rank in Google and get cited by AI assistants, without hand-producing each one.
2. **North-star metric:** `TBD-blocking`. For example, "12 new articles indexed with ≥ 500 combined monthly impressions by day 90", or organic sessions/revenue from blog entrances.
3. **Deadline:** `TBD-nonblocking`
4. **Cost ceiling ($/month all-in):** `TBD-blocking`. Covers model usage, any keyword API, and Actions minutes. Cost per article is measured on the first 3 before committing.
5. **Existing assets:**
   - the Shopify store
   - connectors: Ahrefs, Semrush, Ubersuggest, Keyword Tool, HYPD (GSC/GA4), Promptwatch, Slack, Shopify
   - skills: `seo-blog-generate` / `seo-blog-improve`
   - the German sauna article (golden fixture for the renderer, validator and reviewer)
6. **Deploy target:** private GitHub repo + Actions; Shopify production. Tests use unpublished articles that are deleted afterward.
7. **Not in v1:** refreshing old posts, auto-editing old posts to link to new ones, image generation, social distribution, Cloudflare, competitor reviews, translation.
8. **Risk tolerance:** autonomous from launch with post-publish review, 3/week for the first 3 weeks, automatic pause on the kill-switch triggers in §4.10.
9. **Secrets inventory (names only):**
   - `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`
   - `ANTHROPIC_API_KEY` (or a Claude Code OAuth token, to verify in R1)
   - `GSC_SERVICE_ACCOUNT_JSON`, `SLACK_WEBHOOK_URL`
   - optional keyword-API key
10. **Brand priors:** `house-style.md` (espresso/cream/gold, no purple/blue accents, luxury-but-useful voice).

## 7. Build rounds (one objective each)

| Round | Objective | Done when | Tier |
|---|---|---|---|
| R0 | Intake brief answered | No blocking TBDs remain | 🔴 |
| R1a | Orient + land governance: report real repo/environment state (incl. theme-connection and visibility checks), commit the starter kit on a branch | State report reviewed by you; kit on a branch; runlog + handoff written | 🟡 |
| R1b | `preflight.py`: Shopify Dev Dashboard app token, Anthropic, GSC, Slack | Every credential reports VALID via a live call | 🟡 / 🔴 secrets |
| R2 | Prove Shopify: read blogs/articles/products into site index; build the schema theme snippet on a duplicate theme; create one test article with SEO fields, future publish date and the schema metafield; confirm rendering, scheduling and no duplicate schema; delete it | Rich Results Test parses the test page; you publish the snippet (🔴); test article deleted | 🟡 / 🔴 theme |
| R3 | Keyword bank schema + `/refill-bank` command (including SERP snapshots) + connector check + selector with dedup and cannibalization; first real refill | First bank merged with ≥ 4 weeks of supply and a SERP snapshot on every row; selector correct on fixtures, including empty-bank halt | 🟡 |
| R4 | Validator (body **and** every package field in §4.13) + `tags.yaml` seeded from existing tags + unit tests (golden fixture passes, broken fixtures fail) | All rules tested | 🟢 |
| R5 | Renderer: article.json → HTML that reproduces the German sauna structure | Golden render passes validator; screenshot reviewed | 🟡 |
| R6 | Research dossier (§4.14) + SERP teardown + brief: fetch top pages, extraction, coverage matrix, questions, tiered sources, catalog match, beat criteria, originality check | 3 briefs spot-checked against the live SERPs by you | 🟡 |
| R7 | Writer stage → article.json | 3 full articles pass validator and originality; cost per article measured | 🟡 |
| R8 | Self-review stage: 5 passes, scoring, targeted revision loop, HOLD path | Reviewer produces structured findings on the R7 articles; revisions are section-scoped | 🟡 |
| R9 | Reviewer calibration against seeded bad drafts | ≥ 95% of injected issues caught; golden article passes | 🟡 |
| R10 | Conductor + `generate` / `publish` / `correct` workflows: auto-merge on all-gates-pass, D5, scheduled create, reconcile, pause switch — **plus your one-time read of the first real batch** | Simulated crash halts next run; re-run creates nothing; kill switch pauses and un-schedules; you've read batch 1 | 🟡 / 🔴 first batch |
| R11 | Measurement + weekly Slack digest with per-article scorecards and GSC data | Real GSC data returned for a published URL | 🟢 |
| Launch | Cron on at 3/week | Running; cadence increases only by your edit after 3 correction-free weeks | 🔴 |

## 8. Decisions

**Locked (Sept 18, 2026):**

- **D1 Review model:** no human pre-approval; in-depth Claude self-review before publish; you review after, with a one-command correction path and automatic kill switch (§4.10, §4.12).
- **D2 Keyword source:** monthly interactive refill with existing connectors, including SERP snapshots (§4.1, §4.11).
- **D3 Schema placement:** article metafield + theme snippet (§4.8).
- **D7 Health/YMYL:** no separate human gate; covered by the reviewer's fact-check and YMYL passes, with health claims requiring clinical, government or peer-reviewed sources.
- **Competitive research:** every article is built from a SERP teardown with measurable beat criteria (§4.11).

**Open:**

- **D4 Author:** is "Taylor Reed" a real person whose credentials can be stated truthfully? If not, use "InHouse Wellness Editorial Team".
- **D5 Routing:** what belongs in `/blogs/fire` and `/blogs/institute`?
- **D6 Featured images:** reuse product CDN images from the catalog (recommended for v1) vs. Unsplash (connector available). With no pre-publish review, manual upload is off the table.
- **North star + cost ceiling:** both block R1. The extra teardown and review passes add model cost per article, measured in R7–R8.
- **Cadence:** 3 per week (Mon/Wed/Fri, 7am Central) to start; up to 5 by your edit.
