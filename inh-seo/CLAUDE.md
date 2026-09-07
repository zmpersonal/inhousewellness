# CLAUDE.md — InHouse Wellness SEO

Governing context for all work in this repo. Read this fully before any task.

---

## What this project is

Fixing and optimising the on-site SEO of **inhousewellness.com**, a Shopify store selling saunas, cold plunges, float tanks, steam rooms, and massage chairs.

**Deadline: 15 November 2026.** The category peaks in January (`infrared sauna cost` runs 1,900/mo in January against 880 in July). Google needs 6–10 weeks to settle a changed page. Anything landing after mid-November misses the season.

**The store:** 673 products · 90 collections · 112 blog articles across 6 blogs · Shopify.

**The constraint:** 67 referring domains against competitors at 31,286 and 56,553. Zero top-3 organic positions despite 520 ranking keywords. On-site work is necessary but not sufficient — it will not produce top-3 rankings alone. The goal here is to stop losing rankings to broken and empty pages.

---

## Hard rules — never violate

1. **Every write script defaults to `--dry-run`.** Writes require an explicit `--apply` flag. No exceptions.
2. **Never write to the live/MAIN theme.** Theme work goes through Shopify CLI on an unpublished branch. A human publishes.
3. **Never delete a collection or product** unless the task explicitly says DELETE and it has zero products. Deindexing means unpublishing from the Online Store channel, which is reversible.
4. **Never write a health claim.** No "detoxifies," "boosts immunity," "burns calories," "reduces inflammation" as an assertion. Link to `healthresearchdatabase.com` for evidence instead. If a claim feels necessary to make the copy work, the copy is wrong.
5. **Never bulk-apply generated copy without a human reviewing a sample.** Generate to `content/` as markdown, stop, wait for approval, then apply.
6a. **Coverage test: check what fraction of the collection actually supports a fact before
   writing it as a collection fact.** A number pulled from `data/products.json` describes the
   products it came from, not the collection, until you have counted.

   **Two claim shapes, two different tests:**

   - An **existence claim** — "from inflatable ice baths to insulated stainless steel",
     "wood-fired and electric", "reaching 195°F" — asserts that something is present in the
     range. It needs **one verified instance**, and for a span, a verified product at each
     end. `cold-plunge`'s cheapest unit *is* an inflatable Dreampod at $760 and its dearest
     *is* a stainless Icetubs at $14,995, so the span is true even though only 4 and 7 of 18
     products carry those words.
   - A **universal claim** — "none run above 140°F", "every unit ships freight" — asserts a
     property of the whole set. It needs **coverage across the whole set**. "None run above
     140°F" was drafted for `far-infrared` on the strength of 28 units that publish a maximum,
     while **43 publish nothing at all**. Silence is not confirmation. It became "Every
     published maximum is 140°F", which is true, is narrower, and is *more* useful — it tells
     a buyer the spec sheets agree and quietly admits some units don't publish one.

   **The near-miss worth remembering:** a draft for `cold-plunge` — the highest-CPC collection
   in the catalogue — said "Chilled models hold 34°F". That figure came from **one product of
   eighteen**. Two of eighteen name any temperature in the 30s or 40s. It read as a class
   property and was a generalisation from n=1.

   **Two of eighteen is not a collection fact.** State the coverage, narrow the claim, or drop
   it. Do not hedge honest language into vague language to make it safe — "up to 195°F" is
   weaker than "reaching 195°F" without being truer.

6b. **Measure length on the decoded string, never the stored one.** Character limits apply to
   what a person sees, and HTML entities are stored long and rendered short. `&amp;` is five
   characters in the metafield and one on the page; `&nbsp;`, `&#39;`, `&ndash;` and
   `&rsquo;` behave the same way.

   Getting this wrong distorts in both directions. Article titles measured raw looked like 3
   of 112 were under 60 characters; decoded, it was 3 before the fix and **76** after, not
   74. A meta measured raw can be reported as over 155 when it renders at 148, or a title
   trimmed to fit can still overflow because the entity was counted as one character in the
   editor and five in the field.

   Decode first, then count:

   ```js
   const decode = (s) => s
     .replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
     .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
     .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');
   ```

   And while decoding, **check whether the entity should be there at all.** Three article
   title metafields carry raw entities that render literally, one of them a leading
   `&nbsp;`. A stored entity in a field that is not HTML is a defect, not an encoding.

6. **Never invent product facts.** Prices, dimensions, wood types, EMF ratings, wattage, and capacity come from `data/products.json` or not at all. If the data isn't there, write around it.
   **General category facts are permitted** where uncontroversial and non-physiological — e.g. that a lower operating temperature means a longer session. What is never permitted is a health or performance claim, which always needs population and limitation. The test: if it describes a *specific product*, it needs the data; if it describes a *physiological effect*, it needs a citation and probably shouldn't be here at all; everything else is ordinary category knowledge and may be written plainly.
7. **Back up before every write batch.** Dump current state to `data/backups/{timestamp}/` first.

---

## Brand positioning

**InHouse Wellness is the buyer's agent, not the brand's advocate.** The differentiator is candour: we publish the measurement, the real cost, and the thing that makes the sale harder.

- We sell 673 SKUs across many manufacturers, so we have no reason to oversell any one of them.
- We state freight, electrical, assembly, and foundation costs up front — the things competitors bury.
- Credibility over comfort. A specific, checkable fact beats a warm adjective every time.

---

## Voice

Write the way a knowledgeable salesperson talks to a customer who is about to spend $6,000 and is nervous about it.

### Do

- **Answer-first.** Put the specific fact in the first sentence.
- Use real numbers: temperatures, dimensions, price bands, wattage, mG readings, session lengths.
- Name the trade-off. Every product has one. Saying it builds more trust than hiding it.
- Short, direct sentences.
- Second person. "You'll need a dedicated 240V circuit," not "a dedicated circuit is required."

### Never

- Manufactured scarcity — "Only 3 Left," "Limited Time," countdown language.
- Wellness dialect — "elevate your wellness journey," "transform your space into a sanctuary," "unlock your body's potential," "the ultimate," "revitalize."
- Health claims without population and limitation.
- Benefit lists with no condition attached.
- Em-dash asides, "not X but Y" constructions, colon-then-reveal sentences.
- Stock openers: "Discover," "Experience," "Transform," "Elevate."

### Calibration

**Bad (this is currently live on the FAR Infrared collection):**
> Discover our premium collection of Far Infrared Saunas, thoughtfully selected to bring the benefits of professional spa therapy into your home. Unlike traditional saunas that primarily heat the surrounding air, far infrared technology gently warms your body from within, creating a comfortable and deeply relaxing experience.

**Good:**
> Far infrared saunas run at 120–140°F, roughly 40 degrees cooler than a traditional room, which is why most people sit in one for 30–45 minutes rather than 15. The 58 models here range from $1,800 to $9,400. Every unit over $4,000 in this collection ships freight and needs a dedicated 240V circuit; the smaller cabins plug into a standard outlet.

The second one is shorter, contains six checkable facts, and tells the customer something that might talk them out of the expensive unit. That's the voice.

---

## Copy specifications

### Collection descriptions

**Link internally only. No outbound links, ever.**

The ten reference domains exist to send authority *to* inhousewellness.com. Linking out from
a commercial collection page reverses that flow on exactly the pages we most need to rank,
and hands a buyer a path away from the purchase. Satellite citations
(`besthomeinfraredsauna.com`, `healthresearchdatabase.com`) belong on **blog content**, not
on commercial pages.

Internal links between collections are the point — a parent routing a decided buyer to a
child, or a child sending someone back up for a wider range. Use them.

A fact that would have carried a citation still stands without one, if it is genuinely useful
to a buyer. "Manufacturers apply EMF tiers inconsistently and measure mG at different
distances" is buyer's-agent information whether or not it links to the index that proves it.
Keep the caution, drop the link — and **do not pad to replace the lost words.**

And do not announce restraint. "We don't publish health claims for these" is defensive
throat-clearing: copy that makes no health claims does not need to say so.

- **150–300 words.** Longer is not better.
- First sentence contains a specific number or fact about this collection.
- At least one `<h2>`.
- At least three facts drawn from the actual products in that collection: price band, capacity range, wood types, EMF tier, wattage.
- Include the disclosure line where it applies: freight type, whether a 240V circuit is needed, assembly requirement, foundation requirement for outdoor units.
- Clean HTML only: `<p>`, `<h2>`, `<h3>`, `<ul>`, `<li>`, `<strong>`, `<a>`. **No** `class`, `style`, `data-*`, or `<meta>` attributes.

### SEO titles
- Under 60 characters.
- Pattern: `{primary keyword} | {differentiator} | InHouse Wellness` — drop the brand if it doesn't fit.
- The primary keyword appears verbatim.

### Meta descriptions
- Under 155 characters. Contains the primary keyword and one concrete number.
- **Only fill `null` fields.** Many existing metas are good. Do not overwrite an existing meta description unless the task says so explicitly.

---

## Keyword ownership

**One keyword, one URL.** The store currently cannibalises itself in several places. Before writing copy for a collection, check `data/keyword-map.json` for its assigned primary keyword. If two collections want the same term, stop and ask.

Known conflicts (resolve before writing):
- **EMF cluster — RESOLVED 7 September 2026. All three stay, as siblings.**
  The earlier plan made `/collections/low-emf` a canonical hub with the other two as children
  linking up to it. **That is dropped.** It assumed the three were one thing split three ways;
  the client's ruling is that they are genuinely different products for different buyers.

  | Collection | Primary keyword |
  |---|---|
  | `/collections/low-emf` | `low emf sauna` |
  | `/collections/ultra-low-emf` | `ultra low emf sauna` |
  | `/collections/near-zero-emf` | `near zero emf sauna` |

  **Each description opens by stating what its tier means in mG**, so the pages are
  distinguishable to a reader and to Google rather than three near-identical pages competing.
  **Cross-link all three as siblings** — each to the other two. Not parent and children.

  Still the highest-CPC cluster in the catalogue ($9.15–$30.02), which is why the
  differentiation has to be real rather than cosmetic.
- **Sauna hierarchy** — `/collections/saunas` (138) vs `/collections/sauna` "Traditional Saunas" (70) vs `/collections/infrared-saunas` (103) vs `/collections/far-infrared` (58) vs `/collections/full-spectrum` (26).
- **`/collections/steam-sauna`** (0 products) conflicts with **`/collections/steam-saunas`** (17 products).
- **`/collections/scandia` vs `/collections/scandia-manufacturing` — NOT duplicates.**
  Checked 7 September 2026 and the merge was cancelled. **Zero product overlap.** `scandia`
  holds 9 cabins and kits, $9,450–$14,800. `scandia-manufacturing` holds 10 heaters,
  $1,300–$6,200 — and draws **189 GSC impressions to `scandia`'s 28**. Merging would have
  buried the collection people actually find.

  Renamed for clarity instead: **"Scandia Saunas"** and **"Scandia Sauna Heaters"**.
  **Titles only — handles unchanged**, because a handle change needs a 301 and
  `scandia-manufacturing` is the one carrying traffic.

  **The lesson generalises: a handle pair that looks like variants of each other is not
  evidence of duplication.** Diff the products before moving anything.


### Satellite deconfliction
The company runs ten reference domains. Do not duplicate content they own:
- **EMF measurement data** → `besthomeinfraredsauna.com` (90-model index, published methodology). INH cites it, never rebuilds it.
- **Health evidence** → `healthresearchdatabase.com` (PubMed-indexed). All health-adjacent claims link here.
- **Climate and running-cost data** → the climate index satellite (NOAA normals, live EIA rates). The True Total Cost tool consumes this rather than rebuilding it.

---

## Repo conventions

```
scripts/lib/shopify.js     Admin API client. Rate-limit aware, retries on 429.
scripts/audit/*            Read-only. Output JSON to data/. Never writes to Shopify.
scripts/apply/*            Writes. --dry-run default, --apply to execute.
data/                      Audit output, backups, keyword map. Gitignored except keyword-map.json.
content/collections/*.md   Generated copy, staged for human review before applying.
theme/                     Shopify CLI checkout. Unpublished branch only.
```

- Every `apply` script prints a diff of old → new before doing anything.
- Every `apply` script writes a backup to `data/backups/{ISO timestamp}/` first.
- Every `apply` script is idempotent. Running it twice changes nothing the second time.
- Log every mutation to `data/changelog.jsonl` with timestamp, resource GID, field, old value, new value.

---

## Operating principles

Three rules earned the hard way on this project. They are not general advice; each one traces
to a specific failure documented in `reports/round-1-summary.md`.

### A command that reports success has told you what it believes, not what is true

Query the state directly. `shopify theme publish` returned no useful output and
`shopify theme list` then showed the *old* theme still live; a second publish reported
success. Whether the first call failed or the list was stale was never determined, because
the answer came from querying theme roles directly instead of trusting either output.

The same failure in other clothing: `menus(first: 25)` returned 25 of 43 menus and called it
success. An order query silently windowed to 60 days by a missing scope returned identical
"90, 180 and 365 day" totals. `publishedOnline` derived from `resourcePublicationsCount > 0`
reported 7 collections as published when they had been deindexed. **None raised an error.**

### A guard that has never failed has not been tested

`scripts/audit/verify-render.js` was run against the live theme *first*, and confirmed to
fail 3 of 4, before it was trusted to pass against the branch. Two bugs in the checker
surfaced only under that test — one producing a false failure, one a false pass.

Prove a new check catches the thing it exists to catch, using a case you know is broken.
Until then it is decoration.

### Any pattern-matching probe must be validated against known positives

Screen for something you already know is there and confirm the probe finds it. A regex over
59 meta descriptions reported 10 health-claim matches; word stems found 27. It matched
`/reduces? inflammation/` and missed "inflammation reduction". Counting is not evidence that
the count is complete.

## When an instruction says "show me" and "apply", the show-me gates the apply

If a request contains both — *"show me all nine before applying anything. Then apply"* — the
review comes first and the apply waits for a separate word. Read it as a gate, not as
permission granted in advance.

The client will say so explicitly when they mean "do both in one pass". Absent that, stop
after showing. The cost of an extra round trip is one message; the cost of applying something
that was meant to be reviewed is a change to a live store that someone has to notice before it
can be undone.

This resolves an actual ambiguity from 7 September 2026, and the ruling is the client's.

## Snippet work: check position before writing anything

A title or meta rewrite lifts CTR **at a fixed position**. On page one that compounds against
traffic already arriving. On page two the ceiling is the ranking, not the snippet, and the
work is close to wasted.

**Standing test: pull the positions first. If the pages are not on page one, the problem is
ranking and a snippet rewrite is the wrong fix.**

This is what justified the Round 3b content pass — all eight target articles sat at weighted
positions 6.2–9.7 with 44,021 impressions converting at 0.77%. It is also why the
`german sauna` cluster was dropped rather than deferred: 153 queries at average position 6.0
running 0.34% is not a snippet problem, it is an audience that has seen the site repeatedly
and does not want it.

## Verification

After any change, prove it worked rather than assuming:
- Re-run the relevant audit script and diff against the previous dump.
- For copy changes: load the live URL and read it as a customer would.
- For deindexing: confirm in Search Console coverage after the next crawl, not immediately.
- For anything touching more than 10 records: verify 3 at random by hand.

---

## Outdoor cooking is out of the SEO programme, in the catalogue

**Decided 7 September 2026. This is a decision, not a gap.**

Eleven collections — `bbq-grills`, `bbq-grills-accesories`, `outdoor-kitchen`, `fire-pits`,
`outdoor-fireplaces`, `broilmaster`, `cal-flame`, `primo-grills`, `cozy-heat`, `kohler`,
`delta` — carry **155 products** and stay **published, sellable and indexed**. Nothing about
them changes on the storefront.

**They do not get collection copy, SEO titles or meta descriptions.** The category draws some
inquiries and little revenue, and it does not earn copywriting hours against a 15 November
deadline that the sauna and cold-plunge estate needs.

**Why this is written down.** Anyone auditing the store later will find eleven published
collections with no descriptions and reasonably conclude the sweep missed them. It did not.
They are marked `SCOPE-OUT` in `data/collections-plan.json` with the same reasoning on each
row. Re-scoping them is a decision to make deliberately, not a gap to close.

A consequence worth knowing: **`/collections/more` is a KEEP.** Its mega-menu dropdown is the
entire BBQ/outdoor set, and since the category stays, so does the nav item and the collection
behind it. It was previously held on the unpublish list pending this decision; that block is
now cleared and no handles are blocked.

## Open decisions — these block work

Do not proceed on the affected task until answered. Ask rather than guessing.

| Question | Blocks |
|---|---|
| Which of the three catalog-wide collections survives (Newest Products / Best Selling Products / AVADA Best Sellers)? | Deindexing task |
| Are BBQ grills, outdoor kitchens, fire pits, and fireplaces in scope? ~155 products across 11 collections. | Whether to write copy for them at all |
| EMF hierarchy — confirm `/collections/low-emf` as hub | EMF collection copy |
| Bylines: real people or personas? | Author schema, E-E-A-T markup |
| Discount theatre: keep, taper, or kill? | Product page copy, and whether the cost tool contradicts the pages it links to |
| MAP / dealer terms — can we publish a critical warranty comparison of brands we sell? | Warranty Decoder, later phase |

---

## Priority order

0. **Theme render fix. P0, above everything.** Collection descriptions do not render as
   visible page content on this storefront, and the meta-description logic is inverted.
   See `reports/URGENT-collection-copy-not-rendering.md`.

   **Do not resequence this below the collection sweep.** The ordering looks wrong and
   someone will try to "fix" it back. The reason it is first:

   - `layout/theme.liquid` contains an `elsif` with an empty body that matches when a
     collection **has** a description. So **writing a description deletes that page's
     `<meta name="description">` tag.** Until it is fixed, every description we write makes
     the page measurably worse, not better.
   - Both render paths for `collection.description` are switched off in
     `templates/collection.json`, so the text is invisible to customers and crawlers
     regardless.

   **The collection sweep is net-negative until this ships.** 81 descriptions would land in
   the admin, reach nobody, and strip the meta tag from 81 pages that currently have one.

   Related pre-existing loss, not caused by this project: because the same `elsif` chain
   matches `template contains 'collection'` before reaching `page_description`, **Shopify's
   own SEO meta description field has never rendered on any collection page. 59 collections
   have one set. None of them have ever appeared in the HTML.**

1. **P0 mechanical fixes.** Broken copy live on commercial pages, junk collections indexed, empty collections published.
2. **Collection sweep.** 81 descriptions, ~40 SEO titles. Biggest seasonal revenue impact.
3. **True Total Cost tool.** ~6,000–7,000/mo cluster, and the link asset.
4. **Safety hub + Recall Checker.** `are infrared saunas safe`, 1,300/mo.
5. **Content and technical.** Comparison pages, brand reviews, schema, internal link graph.

If time runs short, cut from the bottom. Never cut the collection sweep — but never run it
before item 0 either.
