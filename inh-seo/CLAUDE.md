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
### A rule with two clauses gets enforced on the clause that has a screen

**Read this before rule 4, because rule 4 is the case that proved it.**

Rule 4 has two halves. *"Never assert a health benefit"* got a purpose-built
screen with synthetic fixtures and ran across 673 products and 116 articles.
*"Route the evidence to `healthresearchdatabase.com`"* had no check — and **had
never once been executed. Zero of 117 articles, for the life of the project.**

**The rule read as satisfied because its measurable half was.** Every pass asked
*"does this assert something?"* and none asked *"can a reader check it?"*

**Audited across every other multi-clause rule here, 9 September 2026**
(`scripts/audit/two-clause.mjs`). The collection-copy spec has eight clauses and
**exactly one has a guard** — clean HTML, enforced by `cleanHTML` on write and by
`scan-broken-copy`. Word count, first-sentence, the `<h2>`, all four disclosure
clauses and the no-outbound-links rule are **checked by hand, per draft, and by
nothing else.**

**The difference from rule 4 is that they are currently passing** — 56 to 58 of
58 on every clause. So the finding is *unguarded but satisfied*, not *unguarded
and never done*. **That distinction is the whole risk: an unguarded clause is
fine until the person checking by hand changes, and then it fails silently and
the report still says the rule is being followed.**

**Practice: when a rule has two clauses, check that both have a check.** Where one
does not, say so in the report rather than letting the measurable half stand in
for the rule.

**And distinguish the two states, because they carry different risk:**

| | |
|---|---|
| **unguarded and never done** | rule 4's routing clause — zero of 117 articles, for the life of the project |
| **unguarded but satisfied** | the seven copy-spec clauses — 56 to 58 of 58 passing |

The second sounds harmless and is not. **It holds until the person checking by
hand changes, and then it fails silently while the report still says the rule is
being followed.** An unguarded clause has no failure signal; it has a person.

### A route with a limitation attached is worth more than a route

**A bare link implies the destination supports the page.** When routing evidence,
say what the reader will find:

> This page discusses preclinical work — cell culture and animal models — on heat
> shock proteins and neurodegeneration. **Very little of it has been tested in
> humans, and none of it establishes that sauna use affects cognitive aging.** The
> studies are collected at healthresearchdatabase.com.

Without that sentence the link reads as substantiation. With it, the link is an
invitation to check — which is what rule 4's second clause is actually for.

**And an evidence route belongs where a claim is being made. Adding one where
none is implies one.** 19 of the 24 articles with no route are product reviews and
safety guides that brush a physiological term in passing; routing them would
manufacture the claim the route appears to support. **They were read and left
alone, and the report says "1 routed, 19 read" rather than driving 20 to 0** —
which would be the completion-criterion failure this file already has a rule
about.

### And an audit will encode a stricter rule than the rule

Writing that audit, three of its eight clauses failed pages that were correct:

- *"first sentence contains a specific number **or fact**"* — the test checked for
  a digit, and failed **eight** durable-facts rewrites that deliberately open on a
  mechanic instead of a count.
- *"240V **where it applies**"* — the test ran on chimney kits and wood oil, which
  have no electrical requirement. Four correct pages reported as failures.
- *"service fees non-refundable"* — **not a clause at all.** The audit invented it
  from the standard delivery paragraph.

**Same failure as a monolingual probe, moved up a level: reading the spec
carelessly rather than reading the products carelessly.** Quote the rule into the
test as a comment, and check the test against the words rather than against your
memory of them.

4. **Never write a health claim of BENEFIT.** No "detoxifies," "boosts immunity," "burns calories," "reduces inflammation" as an assertion. Link to `healthresearchdatabase.com` for evidence instead. If a claim feels necessary to make the copy work, the copy is wrong.

   **What the rule governs: assertions that use confers a benefit.** Where a
   finding is reported with its source, it must also carry its **population and
   its limitation** — "an observational cohort of Finnish men, which shows
   association rather than cause". The population is usually already in the
   sentence; the limitation usually is not.

   **Two kinds are exempt, and they are the rule working rather than exceptions
   to it** (client ruling, 9 September 2026):

   - **A warning about risk.** "Alcohol before a sauna increases the risk of
     dehydration, arrhythmia and, in extreme cases, death" is the opposite shape
     to a benefit claim. **Hedging it makes it less useful and less safe.**
   - **A correction of a false claim.** "All saunas burn large numbers of
     calories — *Correction:* most immediate weight loss is fluid, not fat."
     **Hedging after the word Correction restores the myth.**

   The exemption is about what the sentence **does**, not what it contains. A
   benefit claim does not become exempt by using the word "risk": the harm named
   must be a harm *of use or misuse* — burns, hypothermia, fainting, arrhythmia,
   dehydration — not a wellness outcome inverted into a risk of abstaining.
   `scripts/audit/health-claim-screen.mjs` encodes this and is the place to
   change it.

   **Where a citation exists but nobody has read the source: describe the source,
   never characterise its contents.** "In the exercise trials reviewed" is
   honest; naming a sample size or a population from a study you have not opened
   is the NEC failure with worse consequences, because it looks like precision.
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

   **A category definition is not a coverage claim.** "Full spectrum means near and mid
   wavelengths on top of far" is what the term means — safe to state, and category knowledge
   under rule 6. "These units deliver all three" is a claim about the products, and at
   **5 of 26** naming all three it is existence-only. Where both are true, state the
   definition and then say plainly that only some units publish the full breakdown. That is
   more useful to a buyer than the claim would have been, because it tells them to check.

6a-ii. **Prefer facts that survive stock movement. Client ruling, 9 September 2026.**

   **Measured, not argued.** The client archived one duplicate product as routine
   housekeeping — thirty seconds in the admin — and it invalidated **19 published
   figures across 7 collection pages**, two of them the highest-traffic
   collections in the estate. Nobody could have predicted which pages a single
   archive would touch.

   **That is the argument for durable facts, not for a faster drift check.**

   | | |
   |---|---|
   | **DURABLE** | tier definitions (*"low EMF means 5–10 mG"*) · universal negatives (*"not one publishes a wavelength"*) · category mechanics (*"a barrel encloses less air"*) · electrical requirements as a **distribution** (*"most run on 120V"*) · price **floors** stated as *"from $X"* |
   | **FRAGILE** | set sizes · exact counts of a feature · price **ceilings** · **"N of M"** constructions |

   **A count is not banned.** It is the most specific thing we can say, and
   specificity is why these pages are good — `low-emf`'s *"5–10 mG — Ask the
   Measuring Distance"* and `red-light-therapy`'s *"Not One Publishes a
   Wavelength"* are the two best titles in the estate precisely because they are
   both specific AND durable.

   **The test: does a durable fact do the same work here?** If yes, the durable
   one wins. If the count is carrying something no durable phrasing can — a real
   price floor, a genuine majority, a coverage rate that is itself the finding —
   it earns its place and stays.

   **Why a ceiling is fragile and a floor is not.** The cheapest unit in a
   collection changes rarely; the dearest changes whenever one premium SKU goes
   out of stock. `far-infrared` and `near-zero-emf` both lost a $14,999 ceiling to
   a single archive. *"From $1,999"* would have survived it.

   **Why "N of M" is the worst shape.** It goes stale when EITHER number moves, so
   it carries double the fragility of a bare count and reads as more precise.
   *"Most run on 120V"* survives every restock that *"55 of the 90"* does not, and
   tells a buyer the same thing.

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

6c. **A count is population + pattern + source, and all three travel with it.**
   `collection-spec.js` is the only sanctioned counter and it **refuses** to emit a count
   without its method — not a warning, a thrown error. Every draft carries a `methods:`
   block in its front matter naming what was counted, with which pattern, from where.

   **Per-feature default:**

   - **Product-defining attributes** that belong in a title — full spectrum, EMF tier,
     barrel, hybrid, wood species → **TITLE-ONLY**. A body match is a cross-sell risk:
     *"unlike our cedar cabins"* counts a hemlock unit as cedar.
   - **Fitted features** a title rarely names — chromotherapy, Bluetooth, red light
     panels, tool-free assembly, chiller → **TITLE-OR-BODY**, and the spec shows both
     counts so the divergence is visible before the number is used.

   **The >20% divergence flag applies to TITLE-ONLY attributes, not to fitted features.**
   Do not "restore" it to all facts — it was tried and it is wrong. Worked example:
   Maxxus chromotherapy is **2 in titles and 28 in listings, and the true answer is 28 of
   28**. Applied literally, the conservative-figure rule advises publishing *2 of 28*,
   which would make the copy actively false. Title-only undercounts fitted features **by
   design** — that is the whole reason they use title-or-body. Divergence only means
   "the method is contestable" where both readings are defensible, and that is the
   title-only case.

   **The pattern is half the method, and it is the half that gets forgotten.** Reviewing
   batch 2, the title-vs-body axis was pinned and the regex was not, so a verification
   pass using `/hemlock/` against drafts built on `/canadian hemlock/` produced four
   confident false alarms. `/hemlock/` and `/canadian hemlock/` are different questions —
   one of them counts a cedar cabin whose listing compares itself to hemlock. One regex
   per concept, defined once in the spec, so drafting and verification cannot diverge.

   **Necessary and not sufficient — amended 9 September 2026.** A shared definition
   stops drafting and verification from *disagreeing*. It does nothing about them
   being **wrong together**, and that failure is invisible in a way divergence is
   not: divergence raises a contradiction, agreement files a clean report. The Sun
   Home citation sweep closed at "0 remaining" because the removal script and the
   audit certifying it both matched round brackets, and the surviving citations were
   in square ones.

   **So every verifier additionally needs a case the implementation was not built
   for**, hand-verified, encoded in the script, failing the run rather than warning.
   `citation-audit.mjs` names the square-bracket article; `stale-references.mjs`
   names the german-sauna anchor; `title-claims.mjs` carries three known-false and
   two known-true fixtures; `health-claim-screen.mjs` carries synthetic fixtures
   including a deliberate trap. **That is the standard, not the exception.**

   `health-claim-screen.mjs` is the model for a different reason worth copying:
   the screen detects by pattern and `cut-product-claims.mjs` acts on **hand-written
   exact strings**. The two ends use different mechanisms, so neither can inherit
   the other's blind spot.

   **Medians: one definition everywhere.** Median of `priceMin` across **ACTIVE members
   only**, from the enumerated connection. Never `productsCount`, never all members.

   **A figure borrowed from another page has a method; it is just someone
   else's.** So it travels the same way. When copy on page A quotes a number
   derived on page B — `indoor-sauna` saying *"55 of 91 units run on a standard
   120V circuit"*, which belongs to `infrared-saunas` — it goes in page A's
   `claims:` block **keyed to the source handle and probe**:

   ```yaml
   claims:
     cites:
       infrared_120v_share: { from: infrared-saunas, probe: names_120v, of: set_size }
   ```

   Without it the figure is unattached and **three guards miss it**:
   `stale-references` carries claims we CORRECTED, not figures we RESTATED;
   `drift-check` re-derives a page's OWN claims and has no notion the prose holds
   another page's number; `seo-field-drift` reads SEO fields only. The 55 has been
   wrong since `infrared-saunas` was rewritten to *"most"* and its set size moved
   to 90.

   A cross-page figure is **a drift problem wearing a string problem's clothes** —
   it has no knowable stale form in advance, so only re-derivation finds it.

6. **Never invent product facts.** Prices, dimensions, wood types, EMF ratings, wattage, and capacity come from `data/products.json` or not at all. If the data isn't there, write around it.
   **General category facts are permitted** where uncontroversial and non-physiological — e.g. that a lower operating temperature means a longer session. What is never permitted is a health or performance claim, which always needs population and limitation. The test: if it describes a *specific product*, it needs the data; if it describes a *physiological effect*, it needs a citation and probably shouldn't be here at all; everything else is ordinary category knowledge and may be written plainly.
7. **Back up before every write batch.** Dump current state to `data/backups/{timestamp}/` first.
8. **A scope decision made on names must be verified against contents — and contents are not enough.** A handle, a title, or a supplied list of handles is a hypothesis about what a collection contains: open it first. (`kohler` and `delta` were scoped out as BBQ; they hold Kohler indoor saunas and Delta steam generators.) This binds hardest on decisions that REMOVE work from scope: a wrong number is visible and invites doubt, an omission shows you nothing.

   **Verifying against contents is necessary but not sufficient.** A collection can be
   *functional* rather than *navigational* — wired into an app, a promotion, a feed, an
   automation or an integration — and **its membership will not tell you that.** `free-bonus`
   was opened, found to hold 64 infrared saunas, and recorded as "an ops bucket, deindex
   stands". It drives a free software bonus, and only the client knew.

   **Before deindexing or unpublishing anything, ask what depends on it.** Apps, promotions,
   automations and integrations are invisible to both the Admin API and the theme. Where a
   dependency cannot be ruled out from here, say so and ask — do not record it as verified.
   Contents tell you what is *in* a collection; they never tell you what it *does*.

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
- **Back up to `data/backups/{ISO timestamp}/` and nowhere else.** This is not a
  filing preference. Ten of the sixteen unlogged mutations wrote a real
  before-state to `data/citation-edit/`, so the integrity cross-check could not
  see them from *either* side — no log row, and no backup where a backup would be
  sought. **Two records are only a cross-check if both land where the check
  looks.** Use `backup(label, payload)` from `scripts/lib/util.js`; it is the only
  sanctioned writer, and a script that hand-rolls its own before-file is a script
  whose writes are invisible to the audit.
- **Run `scripts/audit/changelog-integrity.mjs` after any batch applied outside
  the standard `scripts/apply/` path.** It cross-checks backups, off-convention
  before-files, and the platform's own `updatedAt` against the log. Only the third
  is complete: an audit built on backups cannot see a write that produced no
  backup, which is exactly how the circulation title change stayed invisible.

---

## Operating principles

Three rules earned the hard way on this project. They are not general advice; each one traces
to a specific failure documented in `reports/round-1-summary.md`.

### A canonical asserts that two pages are THE SAME THING

**Topical proximity is not sameness, and the nearest live page is not
automatically the right target.**

Six Sources pages needed canonicals to their parents. **Every one names its parent
in its own opening sentence** — *"Read our synopsis of all this data in our
article on X"* — which is a far better source of truth than similarity, and it is
why this was worth a read per page rather than a match on topic.

**Two of the six name a parent that returns 404.** `sauna-detox` names
`do-saunas-help-detox-your-body`; `red-light-collagen` names
`red-light-therapy-for-collagen`. Neither exists.

**The tempting move is to point them at the nearest live page instead.** For
`sauna-detox` that is `sauna-detox-science-explained` — live, 49,530 characters,
the strongest evidence page in the estate on exactly that subject.

**It is not the article those citations were assembled for.** They were gathered
for a different article making a different argument, and a canonical would tell
Google the two pages are one page. **That manufactures a relationship the content
does not have** — the same move as routing evidence where no claim is made, and
the same failure as a canonical to a 404: an assertion nothing supports.

**Practice: before setting a canonical, establish the parent from what the page
says about itself, not from what it is about.** Where the stated parent is dead,
the fix is a content decision — write the parent, fold the citations in after
reading whether they support the destination, or deindex — and **never a canonical
to the nearest neighbour.**

### themeDuplicate is asynchronous, and the race looks like a bad file

`themeDuplicate` returns a theme id **immediately** and copies the files in the
background. A `themeFilesUpsert` issued straight afterwards hits a partially
copied theme and fails with:

> Section type 'main-blog' does not refer to an existing section file

**That reads as a broken template and it is a race.** A branch snapshotted
mid-copy showed **431 files against MAIN's 558**; minutes later it was 558 and
complete.

**Practice: after `themeDuplicate`, poll the file count against the source theme
before pushing anything.** `scripts/apply/theme-push.mjs` retries on that specific
message and waits, which is the narrower fix — but the count check is the one that
tells you whether the branch is safe to hand anyone as a preview. **A branch that
is short of the live theme is a broken preview, not a draft.**

### An absence in a dump is evidence about the dump

**Sixth instance this session, and the pattern is unambiguous.**

Before reporting that something is missing from the store, **confirm the dump
fetches that field at all.**

| what the dump said | what the store said |
|---|---|
| 118 articles with no meta description | **0** — article SEO lives in metafields the dump does not fetch |
| 8 blogs with no meta | **7** — one had one |
| `compareAtPrice` absent on 673 products | present on 608, via variants the dump does not include |
| `publishedOnline` from `resourcePublicationsCount > 0` | 7 collections reported published that were deindexed |

**A missing field in a dump has two causes and they look identical: the store
does not have it, or the query does not ask for it.** The second is far more
common, and it is the one that produces a confident, wrong, widely-quoted number.

**Practice: when a dump reports zero or null across a whole population, check the
query before checking the store.** A uniform absence is a schema signal, not a
data signal — the same shape as a uniform magnitude being a measurement bug.

### A guard added mid-task must be proved to fire before the run that needs it

*A guard that has never failed has not been tested* applies hardest to a guard
added **in response to a risk you just noticed**, because adding it feels like
handling the risk.

On 9 September a skip-guard was added to `blog-seo.mjs` to stop it overwriting an
existing meta description. The guard's variable and its write were patched; the
patch that changed the **printed line** silently failed to match. The dry run said
plainly that it would overwrite. The run said `8/8 applied`. **Both were read as
success and the meta was overwritten anyway.**

**Practice: after adding a guard, run the case it exists to catch and confirm the
guard SAYS SO in the output.** And **any patch applied by string replacement must
assert its own match** — `assert old in s` — because `str.replace` on a moving
target fails silently by design.

### Verify the OUTCOME, not the write — a match on the wrong element refuses nothing

**The most deceptive failure shape on this project, and every guard we own passes
through it.**

An answer-first pass rewrote the opening paragraph of ten articles. **Three landed
on the SECOND paragraph.** Each of those three has a lede carrying a class —
`<p class="gsg-lede">` — and the extraction matched bare `<p>`, so it offered the
paragraph after the one that mattered.

All three applied. The read-back said *updated*. The diff looked right. The reach
guard reported 0 collateral. **And the compliance measurement still said 16 of
20**, because the figure went into word 90 instead of word 12.

> **A failed match refuses loudly. A match on the wrong element does none of
> that.**

`edit-article-claims` exits non-zero on a `from` that matches zero times, which is
how two of the ten were caught. There is no equivalent signal for a `from` that
matches the wrong thing — it is a successful write to a target nobody checked.

**This generalises well past markup. Any edit verified by "did the write succeed"
rather than "did the outcome change" has this hole**, and every verification in
this repo is the first kind: `assertWellFormed` checks the string sent,
`showDiff` prints the field, `assertReach` proves nothing else moved, the
read-back confirms the value landed. **All four confirm the write. None confirms
the point of it.**

**Practice: for any edit with a measurable outcome, re-run the MEASUREMENT
afterwards, not the read-back.** If the edit exists because a number was wrong,
re-derive the number. If it exists because a check failed, re-run the check. The
apply reports what it did; only the measurement reports whether it worked.

### And exact extraction is the default, because there is no shape to anticipate

Four assumed-markup failures in one session, **and all four were different
shapes**:

| | assumed | actual |
|---|---|---|
| Sources heading | `id="sources"` on the `<h2>` | a generated `id="h.qbgv…"` plus a separate `<a id>` jump target |
| scarcity counter | a placeholder in text | a placeholder in a `data-message` **attribute** |
| Dynamic review opening | a bare `<p>` | `<p style="font-size: 1.05rem; …">` |
| three article ledes | a bare `<p>` | `<p class="gsg-lede">`, `cp-lede`, `rlt-lede` |

**There is no pattern to anticipate, which is the argument for reading rather than
assuming every time.** For any edit inside formatted copy, extract the exact
element from the live body and build the spec from that string. Never write a
`from` by looking at rendered text.

### A command that reports success has told you what it believes, not what is true

Query the state directly. `shopify theme publish` returned no useful output and
`shopify theme list` then showed the *old* theme still live; a second publish reported
success. Whether the first call failed or the list was stale was never determined, because
the answer came from querying theme roles directly instead of trusting either output.

The same failure in other clothing: `menus(first: 25)` returned 25 of 43 menus and called it
success. An order query silently windowed to 60 days by a missing scope returned identical
"90, 180 and 365 day" totals. `publishedOnline` derived from `resourcePublicationsCount > 0`
reported 7 collections as published when they had been deindexed. **None raised an error.**

### When every verdict moves the same direction, test for the mechanism that would produce that pattern regardless of the truth

Reading the 36 flagged article claims reversed **8 of 18 verdicts, every one
toward no-action.** That is also exactly what clearing your own queue looks like,
and the two are indistinguishable from the result alone.

**So the test ran before the verdicts were recorded, not after.** All 12
remaining sentences were re-screened for a qualifier within 520 characters —
**seven qualified automatically**, and the four bare ones were read by hand and
named individually (two inside Myth/Correction blocks, one a modality definition,
one a safety line following *"Critical safety constraint"*). The other half of the
check is the counter-evidence: **the two ASSERTS that survived were real, were
fixed, and were both on articles about medical conditions**, which is where the
exposure was.

**The practice, generalised: a result that is uniform in the direction that suits
you needs a second, mechanical test before you record it — and the test has to be
one that could come back against you.** "I read them all carefully" is not that
test. Counting how many would have survived a rule you did not choose is.

This is the one discipline from the article pass worth carrying into every other:
the register is only worth having if a wrong entry in it is discoverable, and a
verdict sweep that never checks its own direction is a register that agrees with
its author by construction.

### A verification that shares its blind spot with the thing it verifies is not a verification

**The first rule of every guard on this project, and the one that cost the most
to learn.**

We reported 101 Sun Home citations removed, 0 remaining. Five remained, in one
article, cited as `[Sun Home Saunas, 2026]` — **square brackets**. The removal
script matched `\([^()]*?Sun Home[^()]*?\)`. And `citation-audit.mjs`, the
script whose whole job was to confirm the removal, built its pattern the same
way.

**They did not diverge. They agreed, and the agreement was the failure.** Two
different patterns would have produced a contradiction, and a contradiction gets
investigated. Two wrong patterns produce a clean report.

**A verifier must be tested against a case the implementation was not built
for.** Not a case the implementation handles — those pass by construction. The
`citation-audit.mjs` known-positive block naming the square-bracket article is
that test, and it is now **the standard for every audit script in this repo**:

```js
const KNOWN = [ [article, brand, field], … ];   // hand-verified, must be found
if (bad) process.exitCode = 1;                  // fail, do not warn
```

A guard with no encoded known-positive is decoration, and a guard whose
known-positive came from the same place as its pattern is decoration that
agrees with itself.

**And the fixture must be CONSTRUCTED, never a live case.** Both guards written
on 9 September anchored their known-positive to real content — the german-sauna
anchor, the square-bracket citation — passed, and then **failed hours later when
those defects were fixed**, in the same session, by the same author who had just
written the rule above. A live case is the most persuasive fixture available at
the moment you write it, because you have only just verified it by hand. That is
exactly the property that kills it.

**Test of a fixture: can repairing the estate break it?** If yes, the guard is
measuring the estate rather than the code.

### A guard firing on something harmless means your model of harmless is wrong

**Every guard-versus-reality conflict on this project has resolved the same way, and
it is worth stating once rather than rediscovering.** The tempting response to a
guard that blocks correct work is to widen its tolerance. The correct response has
been, every time, to make the guard's model of the world more faithful — and it has
been the same amount of work.

| the guard said | the tempting fix | what was actually wrong |
|---|---|---|
| `theme-branch`: cannot read the live file | allow empty reads | it conflated *absent* with *unreadable*; new files are now **declared** |
| `fix-membership`: reach declared for the whole plan | ignore it | it ignored `--only`; narrowed, not widened |
| span unwrap: WORD SEQUENCE CHANGED | relax the comparison | it replaced **every** tag with a space, modelling inline elements wrongly. Now models the renderer, which is *stricter* |
| empty-span cleanup: TEXT CHANGED | relax the comparison | it consumed adjacent whitespace along with the element. Narrowed to the element only |
| `verify-render`: UNREACHABLE | treat as pass | an unchecked page is not a passed page |

**The tell:** if the fix you are reaching for is "accept a wider range of outcomes",
stop and ask what the guard is measuring and whether that is what you care about.
Twice in one afternoon the answer was that it was measuring a proxy for what a
reader sees, and the proxy was wrong in a direction that made harmless edits look
dangerous. **Both times the faithful model was also the stricter one.**

**And never satisfy a guard by feeding it a value that makes it pass.** That is how
a guard stops meaning anything, and it is indistinguishable in the diff from
fixing it.

### A guard that has never failed has not been tested

`scripts/audit/verify-render.js` was run against the live theme *first*, and confirmed to
fail 3 of 4, before it was trusted to pass against the branch. Two bugs in the checker
surfaced only under that test — one producing a false failure, one a false pass.

Prove a new check catches the thing it exists to catch, using a case you know is broken.
Until then it is decoration.

### Replacing a fragile claim with an equally fragile one is motion, not a fix

Twelve titles were rewritten because their product counts moved with Golden
Designs / Maxxus / Dynamic Saunas stock. The obvious substitute was a capacity
span — until the spans were re-derived and **six of them turned out to be held by
a single volatile-vendor SKU**. `far-infrared`'s "1–8 Person" rests on three
Golden Designs cabins and nothing else.

**Swapping a fragile count for a fragile span would have been motion, not a fix.**
Before replacing a claim you have judged unstable, derive the replacement's own
stability by the same test. A rewrite that feels like progress and changes
nothing about the failure mode is worse than leaving the original, because it
spends the review and closes the ticket.

Volatility is now computed, never asserted: `npm run audit:titles` names every
figure whose holders are all volatile-vendor products, so "this number changed"
and "this number was always going to change" are distinguishable a year from now.

### Prefer the durable weaker claim to the fragile stronger one

"Every max is 140°F" is stronger than "Max 140°F published" and dies the day one
unit publishes 150. "24 Verified, None List nm" is stronger than "Not one
publishes a wavelength" and needs re-counting every restock.

Where two true statements differ in strength, take the one that stays true
longer, **provided it still tells the buyer something**. The test is not
"which is safer" — hedging honest language into vague language fails rule 6a.
It is: *does the weaker form still carry a checkable fact a competitor would not
print?* `low-emf`'s "5–10 mG — Ask the Measuring Distance" and
`red-light-therapy`'s "Not One Publishes a Wavelength" are the two best titles in
the estate on exactly this basis: both are tier definitions or universal
negatives, so neither has a count to go stale, and both still say something no
other sauna retailer will say out loud.

### A proper noun containing a banned term is not a banned claim

`medical-sauna-traditional7` lists *"advanced features like 3D Heat Therapy™,
**Detox Routine™**, and an ultra-efficient heating system"*. **Detox Routine™ is a
registered preset on the control panel.** Removing it misdescribes the product —
a buyer at the unit would find a button we never mentioned.

**The test: is the sentence NAMING a feature or ASSERTING what it does?**

- *"The control panel includes a preset labelled Detox Routine"* — **factual**, it
  describes what is on the unit. Keep.
- *"Use the Detox Routine to eliminate toxins"* — **the claim**. Cut.
- A spec list reading *"Detox Routine™ preset"* is **inventory, not marketing**.
  Leave it.

Same shape as the vendor-name collisions the health-claim screen already handles —
**Medical Saunas** and **Medical Breakthrough** are companies, **Dynamic Cold
Therapy** is a vendor, **red light therapy** and **chromotherapy** are product
categories. A screen matching terms cannot tell a name from an assertion, and the
answer is a read rather than a wider exclusion list.

### A pattern inside a selected set is a hypothesis, not a finding

Three of the four vendors read in full carried an unsourced comparative
performance claim. That read as a supplier convention. Across all 673 products it
is **five, one per vendor** — because the four had been selected for carrying
**health claims**, a different property.

**Before describing a pattern as a convention, a norm or an industry practice,
check it against the population.** A rate inside a set chosen on other criteria
describes the choosing, not the world. This is cheap to check and the failure is
invisible without checking, because the observation itself is correct.

### A completion criterion that can be satisfied by deleting careful writing is worse than none

The product programme closed on **"no term rule 4 names by example remains"** —
checkable, and it worked, because product copy exists to sell.

**It cannot transfer to articles.** An article about sauna research has to say
"detoxification" to discuss whether saunas detoxify. The term is the subject.

The proof is quantitative: a term count flags
`thermal-instruction-templates-pt`, whose own section heading is
**"What we won't promise: 'Speeds healing'"**, among the worst offenders in the
estate — and reaching zero on that article means **deleting the sentences that
refuse the claim**.

**A criterion that is checkable and wrong beats an unchecked one in every process
with a deadline**, because it gets satisfied. That is what makes it worse than no
criterion rather than merely useless.

**The article criterion is read-and-record, not a count.** For every flagged
article the register holds who read it, when, one of three verdicts, and a line of
reasoning:

| verdict | meaning |
|---|---|
| **ASSERTS** | states a physiological effect as fact — fix |
| **REPORTS** | attributes correctly and carries its limitation — no action |
| **NEEDS LIMITATION** | reports a finding, population present, limitation missing |

**"Reviewed" alone is the weaker version and decays into a checkbox.** The
register is the artefact: not a count reaching zero, but a list where every
flagged article has a recorded judgement, and any article without one is the
outstanding work.

### Check the summary against the output above it

Every guard on this project points at the data: freshness asserts, known-positive
validation, fact verification on substituted figures, the outgoing-string check.
**None points at the sentence describing the data**, which is the last thing
written and the only thing the reader sees.

Batch 1 was closed with *"every named term is now zero on this vendor"* four
lines under a check reading `detoxif=11`. Both were in the same message.

**Before writing "complete", "clean", "zero" or "all", re-read the last check
output in the same message. If they disagree, the summary is wrong.**

### A screen selects the unit of work; a full read defines it

Batch 1 of the product-claim cuts was specified from the screen's output. The
screen reports **the sentences it matched**; claims **cluster per product**. Ten
of fourteen products came out improved and not clean, because every description
held claims in the same paragraph that the screen had not surfaced —
`dynamic-3person-sauna` had a four-item benefits list where the screen reported
one sentence.

**A detection tool's output is a list of places to look. It is never a
specification of what to do there.**

This project has now hit that twice, in opposite directions:

| | error |
|---|---|
| **instance 42** | assigned an ARTICLE-level severity from ONE sentence — over-read a single hit |
| **batch 1** | scoped a DOCUMENT edit from sentence matches — under-read the surroundings |

**And once, the full read CANCELLED the work rather than expanding it.** That is
worth naming, because every earlier application of this rule found *more* to do
and it would be easy to assume that is what it always does.

A BACKLOG item read: *"two Reddit threads listed as bibliography sources on a page
about recovery evidence."* Both halves true, conclusion wrong. The bibliography
**already** separates "Primary Research" from "User Experiences" and both threads
sit under the second; the in-text citations **already** frame them as anecdote
three times. **The article's sourcing was better than the audit that flagged it.**

**And the proposed fix would have caused a real defect** — deleting the two
entries would have orphaned three in-text citations, breaking the
citation-has-multiple-representations rule with a fix aimed at citations.

**The finding came from a regex hit on `<li><p>Reddit` with the subheading two
elements above it never read.** Which is the second half of this entry:

> **A backlog item is a claim like any other and it decays the same way.**

A finding written weeks ago, by you, from a partial read, carries no more
authority than any other unverified claim. **Re-establish it before acting on
it** — the ten-minute fix that needs no checking is exactly the one that gets
applied without checking.

**Practice:** the screen chooses which products or articles to open. Opening one
means reading it in full and writing the spec from what is there. And while it is
open, record every other defect found — wrong specs, contradictions with the
title, stale prices, wood errors. The reading is already paid for; the marginal
cost of noting the rest is nothing.

### An absent anchor means two different things

After a deletion runs, its `from` string is gone. A re-run cannot distinguish
**"already applied"** from **"stale spec"** — batch 1's script refused on four
anchors it had itself removed.

**Report them separately and never collapse them.** A deletion whose anchor is
absent is done; a substitution whose anchor is absent is a spec written against
copy that has since changed, and that one must still refuse. Applies to every
deletion script in this repo, not only the product cutter.

### A residue check finds candidates; a person decides

The dangling-colon check flagged *"These panels include:"* and *"The placement of
these heating panels includes:"* — both **pre-existing, both correctly followed
by a list**. A script that auto-removed them would have destroyed two spec
tables.

The check earned its keep **by being read rather than acted on**. Alongside
instance 41: a cut leaves three kinds of residue and only one is machine-visible,
so the machine's job is to point and the person's job is to judge. A residue
sweep that edits on its own findings is a second cut nobody reviewed.

### Copy outlives the mechanism it describes

Three product pages said *"Add this $47 Book FREE"* while charging $2–$5. It was
**not a claim anyone invented.** The guides genuinely were free with purchase;
the programme moved to the SaunaTap app, and a nominal price was added as a
**spam guard**, because $0 products attract bot orders. The sentence was true,
the mechanism changed, and nothing connected the two.

That is a distinct defect class, and worth separating from its neighbours:

| | |
|---|---|
| **free-returns claim** | never true |
| **shipping rates on 36 pages** | true of a different case than the one it was applied to |
| **"$47 Book FREE"** | **true when written; the mechanism moved out from under it** |

**The general shape: a true statement becomes false when the thing it describes
changes, and nothing links the copy to the mechanism.** Identical in structure to
collection counts going stale on restock — which is exactly why `drift-check.mjs`
exists.

**There is no equivalent guard for prose describing a business process.** Delivery
terms, bundle offers, warranty handling, what happens after checkout: all of it is
copy asserting how the business currently works, and none of it is re-derived from
anything. `drift-check` re-derives numbers from `products.json`; nothing re-derives
"this is included free" from whether it is still included free.

**Practice, until a guard exists:** when a business process changes — a
fulfilment route, a bundle, a price model, a delivery app — grep the estate for
the sentences that described the old one. The copy will not tell you it has gone
stale, and unlike a count, nobody will notice it silently.

### A raised standard fossilises its old version in the archive

Three ARCHIVED Dynamic Saunas products held **15 of the 25 health claims in that
vendor's whole catalogue**, including *"helps burn calories"* — a term rule 4
names in its own banned list. The ACTIVE copy from the same vendor is visibly
cleaner.

**The mechanism, and it is not about health claims:** the standard improved, the
live copy was brought up to it, and **the archive kept the old version exactly as
it was.** Nothing in normal operation reads archived copy. And on the volatile
vendors a republish is normal operation — draft and archived products come back
when stock returns.

**So the archive holds the worst copy on the site, and the only route back to the
storefront runs through it.**

**Standing check:** when a copy standard changes, **the archive is in scope**, and
a republish is a re-entry point for everything the standard was raised against.
That applies to every standard this project has raised — health claims, stale
counts, the price-basis rule, the voice guide — not only the one that found it.

### A caught error stays in the batch file

The `dynamic-versailles-elite` substitution originally read *"on a standard 120V
outlet"*. That product publishes no voltage; every other Dynamic product does and
the assumption was carried across. The fact-verification pass caught it before it
shipped.

**The note stays in the batch file rather than being quietly corrected.** A batch
file with no errors in it is indistinguishable from a batch where the check never
ran, and the second is far more common. **A caught error is the evidence the check
works** — the same reason a guard is proved against a known-broken case rather
than trusted because it passed.

### The complements intersect, and that intersection is where the worst defects live

**Read this before the complement rule. Naming complements is the rule; this is what
to do with them once you have several.**

Every review here has honestly named what it excluded. **No review has ever asked
what is excluded by ALL of them.** That set is small by construction — which is
exactly why it is affordable, and exactly why nobody computes it.

**Worked example, 10 September 2026.** Three live pages carry the commercial terms
of this business: `installation-assembly` ($1,800), `extended-your-warranty-3-years`
($597) and `white-glove-delivery-service` ($600). Two of the three carried a serious
defect for months — a page contradicting its own corrected price four sections
later, and a warranty directing claims to a domain the business does not own.

| review | why it missed them |
|---|---|
| the collection sweep | they are **products** |
| the article claim screens | they are **not articles** |
| rule 4's health-claim passes | they carry **no health claims** |

**Three reviews, three honest complements, one intersection nobody looked at.** Each
review was correctly scoped. The defect lived in the only place none of them
reached.

**The qualifier that makes it mean anything: "reviewed" must mean a judgement was
formed.** A screen that touches every record and forms no judgement is **coverage,
not review**, and counting it collapses the intersection to zero.

`scan-broken-copy` reads all 910 records. It ran over `installation-assembly` every
week while that page contradicted its own price, and told nobody, because it was
looking for markup. Counting it as review would have reported this estate as fully
covered and hidden **329 unread live records** behind a number that looked like
completeness.

**So exclude mechanical screens from the coverage set, deliberately and in writing.**
The same test excludes any batch that ran with an automated equivalence check: the
residue strip touched 302 products and produced no judgement about a single word.

**Any process that reports coverage as review will report this estate as complete.**
Measured 10 September 2026: 222 records reviewed, **687 of 910 never**, 329 of those
live. Coverage said 910.

**Practice, operational:** after any set of reviews, compute the records excluded by
**all** of them and read that set. Not sample it — read it. It is small enough that
this is affordable, and its smallness is the reason it feels not worth doing.
`scripts/audit/complement-intersection.mjs` computes it; the reading is a person's.

**And the intersection is not a leftovers pile.** It is selected, by construction,
for records that fit no category any reviewer thought in. Commercial service
products are the example here: not catalogue, not content, and they state what a
customer is charged.

### Every review names its complement, or it is not finished

**Standing practice, client ruling 9 September 2026.** Any review that names its
subject must also name **what it excludes and when that set was last checked.**
"Never" is the most common answer and it is the finding, not a footnote.

This rule has now produced its largest instance three times over:

| review | its subject | its complement | complement last checked |
|---|---|---|---|
| the volatility rewrite | 13 exposed titles | **39 titles that kept their wording** | never — one was false (instance 34) |
| the health-claim screens | metas, collection copy, article titles | **673 product descriptions** | never — 28 ACTIVE products carry claims |
| the collection sweep | 56 collections with copy | 11 outdoor-cooking + `steam-showers` | deliberate for 11; **`steam-showers` was an oversight** |

**Practice:** write the complement into the report, not into your head. A review
that cannot state what it did not look at has not established its own scope, and
the untouched half is where the error is, precisely because every pass over it has
been a pass over something else.

### Correcting a claim at source does not remove it from the site

A claim has more than one physical representation. Fixing the page that makes it
leaves every page that *repeats* it standing, and link text is the worst case
because it asserts the claim **and** promises it about the destination.

`how-saunas-improve-circulation` was retitled on 9 September to stop asserting a
mechanism. `what-is-a-german-sauna` — 23,587 impressions, position 6.2, the
most-seen page in the flagged set — went on carrying *"it helps to understand
**how saunas improve circulation**"* as the anchor text of a link **to the
article we had removed it from**.

This one is ours. The pricing defect was the client's operations moving; the
manufacturer 404s were third parties reorganising. **A rename is a mechanism
change we perform, and it is exactly the kind of edit that feels self-contained.**

Worse: it was predicted. `reports/health-claim-screen.md` said *"it says that only
because it is quoting the article title we are about to change. Fixing the title
fixes it."* Fixing the title did not fix it — and having named the dependency is
what closed it. **A dependency identified and dismissed is worse than one never
noticed, because it has already been through review.**

**Practice: any content edit that changes a claim must sweep for inbound
references to it, before the edit is called done.**
`scripts/audit/stale-references.mjs` is that sweep. Two things about how it is
built are load-bearing:

- **Its register is hand-declared, not derived from `data/changelog.jsonl`** —
  because the changelog has **no row** for the title change that caused this. A
  derived register reproduces the omission.
- **A general anchor-vs-destination overlap check does not catch this class.**
  Run across 361 resolvable internal anchors it flags 30, all benign, and misses
  the german-sauna case: the stale anchor is a paraphrase of the *old* title, so
  it necessarily shares vocabulary with the new one ("circulation"). Only the old
  string finds it.

And renaming one representation of a name does not stale the others: the
`scandia-manufacturing` collection is now *"Scandia Sauna Heaters"*, but
`Scandia Manufacturing` remains the vendor string on 18 products, so copy naming
the supplier is still correct. Instance 36's shape — a brand is not a domain.

### A general heuristic can be structurally blind to the case that motivated it

The stale-anchor problem had an obvious general solution: resolve every internal
link to its destination and flag anchor text with **zero word overlap** against
the destination title. It was built and run. **361 resolvable internal anchors,
30 flagged, all 30 benign** — `"SaunaLife"` → *Sauna Life*, `"Icetubs"` →
*Ice Tubs*, `"ours included"` → *Low EMF Saunas*.

**It does not flag the case it was built for.** *"how saunas improve
circulation"* against *"…What the Circulation Research Actually Shows"* shares
the word **circulation**. Overlap 1, not zero.

And the reason is structural, not a threshold to tune. **A stale anchor is a
paraphrase of the old title, so it necessarily shares vocabulary with the new
one.** Zero-overlap finds renames that change the *subject*. It cannot find
renames that keep the subject and drop the *claim* — which is the only kind this
project produces, because that is what correcting a health claim does.

**The generalisation: a heuristic derived from the general shape of a problem can
be systematically blind to the specific case that motivated it, and it will look
like it works, because it returns results.** Thirty rows is not nothing. Nobody
reading that output would suspect the one row that matters is missing.

**So `scripts/audit/stale-references.mjs` uses a hand-declared register of old
strings, and that is the right answer despite being manual.** The general
solution was built, tested against the known positive, and correctly rejected.
Record it that way — a rejected general solution is evidence, and deleting it
loses the evidence.

Related, and the same week: the integrity probe over `data/changelog.jsonl`
reported **9 unlogged backups**. All nine were the probe reading its own
vocabulary — the payloads say `productHandle`, `slug`, `collection`, or key an
object by a camelCase nickname, while the probe knew only `handle` and `id`. A
third artefact came from stripping `-before.txt` and leaving `-title`. **Eighth
instance of the probe-vocabulary rule, and the first inside an audit OF the audit
trail.** The real number was 1.

### A backfilled log entry must never look contemporaneous

Sixteen mutations were applied without a `logChange()`. They were reconstructed
and appended, and **every reconstructed row carries `reconstructed: true`, the
evidence path it was built from, and `at` taken from the platform's own
`updatedAt`** — never the time of the backfill and never a guess.

**A reconstructed row that reads like an original destroys the only property that
makes a log worth having: that an absence means something.** Two of the sixteen
say `NOT RECOVERABLE — no before-state was written`, because none survives, and
saying so is the entry. `scripts/apply/backfill-changelog.mjs` is idempotent and
keeps a copy of the pre-backfill file alongside.

### A term screen cannot distinguish a claim from its refutation, and the rate is not a target

Four passes, same result: the screen fires hardest on the text that exists to
forbid the thing. 12 "FDA-approved" hits were all debunks, one of them our own
style guidance. 6 of 18 flagged articles are REPORTS, led by
`sauna-detox-science-explained` at **seven hits and zero claims** — it reports a
review calling detox claims "scant and incomplete".

**This is a permanent condition, not a precision problem with a tuning fix.** Any
regex tight enough to exclude the refutations excludes the assertions too; they
are the same words, and the difference lives in the surrounding sentence.

**The output of a term screen is a reading queue, and the finding is what the
reading says.** Never report the hit rate as a defect rate, and never drive it
down — a programme that reached zero here would be deleting the careful writing.
See also the completion-criterion rule.

### A set exempted from a review is where an error survives

The 13 volatility rewrites got a second pass because a rewrite was asked for. The
other **39 kept their wording because nothing prompted a re-read** — and one of
them, `/collections/sauna-heaters`, had been live claiming *"3kW to 50kW"* where
the 3 kW came from a bag of sauna rocks and the 50 kW from a stones-bundling note
about a stove the store does not sell.

Verification catches what it is looking for. **A set left out of a review because
it was not the subject of the review is the most likely place for an error to
survive**, precisely because every pass over it has been a pass over something
else. This is the client's ruling, 8 September 2026, and it generalises past
titles: the untouched half of any batch is the half with no evidence behind it.

**Practice:** when a review is scoped to a subset, say what the *complement* is
and when it was last actually checked. If the answer is "never", that is the
finding.

### A probe encodes OUR vocabulary; the products carry the manufacturer's

`integrated_cooling` was first written as `/chiller/` and returned **0 of 6** on
the Icetubs range. The claim was true — every unit ships with a cooling engine —
and the word "chiller" is ours, not the manufacturer's. Their copy says *cooling
engine*, *integrated engine system*, *18 kW cooling capacity*.

A zero is the signature of a **vocabulary mismatch**, not of a false claim: a
false claim usually returns a wrong number, not no number. A probe built from the
phrase we happened to write will silently miss every product that describes the
same thing in the manufacturer's words, and it will look like the copy is
fabricated rather than like the probe is monolingual.

**Practice:** before trusting a zero or a suspiciously low count, grep the
products for the *concept* — two or three synonyms — and only then decide whether
the copy or the probe is wrong. Sixth instance of a probe right in shape and
wrong in vocabulary (16, 24, 27, 29, 30, 33).

### A brand is not a domain

`www.sunlighten.com` gates its pricing behind a quote request.
`shop-us.sunlighten.com` — the same company — publishes a price on **111 of 111
products**. I probed the first and reported that the brand gates its pricing.

A marketing site and a storefront are different properties with different
disclosure practices. **Checking one tells you nothing about the other**, and
"this company does not publish X" is a claim about every property it owns.

**Practice:** before asserting what a company does or does not publish, enumerate
its properties — `robots.txt`, sitemap index, subdomains — and probe the one that
sells. Two pages on one host is a sample of a host, not of a company. Same shape
as reading a policy page instead of the product a customer buys.

### Name a standard, never assert its content

Where a claim rests on a code or standard we cannot read — NEC, ASTM, NSF, most
of which are paywalled — **name the standard and say what it governs, then send
the reader to the current edition and their local authority.** Do not quote,
paraphrase, or summarise a provision.

> NEC Article 680 covers electrical requirements for pools, spas and hot tubs;
> check the current edition and your local code.

That sentence is true, useful, and requires nothing we have not verified. A
paraphrase of a provision we have not read is an invented product fact wearing a
standards number, and it is worse than no citation because it looks authoritative.
Client ruling, 8 September 2026.

### A range is only a range if both ends are measured the same way

Third instance (17, the volatility re-derivation, and a competitor price band).
A floor taken from entry prices and a ceiling taken from the highest variant
anywhere is not a range; it is two different questions printed with a dash
between them. It made a competitor's median look **$2,299 above ours when it is
$134 below**, and put "several cabins over $30,000" into a draft against a
catalogue containing none.

**When a band or a median crosses two catalogues, state the basis in the copy
itself** — "both figures are entry prices, the cheapest way into each unit, so
they compare like for like". That is `collection-spec.js`'s method-travels-with-
the-count rule applied to published prose, and it is the only version of the rule
a reader can check.

### Validate what you SEND, not what comes back

Removing one bibliography line, a pattern ending `\S*` ate the `</p>` that
followed the URL with no space between them. The outgoing string was 423 open
paragraphs against 422 closed. **Shopify's sanitiser repaired the balance on
save**, so the read-back measured 423/423 and passed — and the page carried an
empty `<li><p></p></li>` that the check could not see.

**A downstream system that repairs your input hides your defect and substitutes
its own artefact.** The read-back is then a report on the repair, not on your
change. Every apply script that verifies by reading back is exposed to this.

**Practice, in order:**

1. **Assert on the outgoing string first** — `assertWellFormed()` in
   `scripts/lib/util.js` checks `<p>`, `<li>`, `<ul>`, `<ol>`, `<h2>`, `<h3>` and
   `<a>` balance and refuses to send unbalanced markup. Call it before every
   body write.
2. **Then read back**, as a second check rather than the only one.
3. When they disagree, **the outgoing string is the evidence about your code**
   and the read-back is evidence about the platform. Both are worth having;
   neither substitutes for the other.

Related regex habit: a greedy class next to markup will take markup. Bound it —
`[^\s<]*`, never `\S*`.

### A citation has more than one physical representation

Removing one leaves the others. This has now appeared three times in three
different forms, and it is one rule rather than three instances:

| form | how it survived |
|---|---|
| **bibliography line** | four articles came back with zero in-text citations and eight live links intact |
| **lead-in phrase** | *"Chest freezer conversions present a clear example:"* left promising an example that had been cut |
| **bare text mention** | the linked Mayo Clinic block was removed; *"an expert-reviewed article from **Mayo Clinic**"* survived in a separate paragraph |

**Any citation removal is a sweep for every form the source appears in:** the
link, the anchor text, the `title` attribute, the bibliography entry, the lead-in
that introduced it, and the **bare mention**.

**The bare mention deserves naming.** It is invisible to a link-based check
(there is no `href`) and to a claim-based one (there is no claim). It is a proper
noun sitting in a sentence, and it carries the same borrowed authority the link
did. Sweep on the SOURCE NAME as well as on the URL.

### A followed redirect answers from a different URL than the one you asked for

`/products/luminar-outdoor-full-spectrum-infrared-sauna` returns HTTP 200 and
serves `/collections/best-infrared-saunas`. Recording the requested URL put a
category page's FAQ into a report as a product page's specification.

**`res.url` is the evidence; the string you passed in is a request.** Compare
them, record the final one, and treat a difference as a different page. This is
the third variant of one family: instance 36 read a marketing host and called it
the brand, the shipping-facts failure read a policy page and called it the
product, instance 39 read a category page and called it a product. Each time the
fetch succeeded and the content was real. **What was wrong was the attribution.**

**Practice:** probes record `requested` and `final`. A coverage claim states which
kind of page it was counted across — product, category, or policy — because
"the brand publishes X" is a different claim from "one of the brand's landing
pages publishes X".

### A probe aimed at a competitor must be validated on THEIR pages first

The probe-vocabulary series (16, 24, 27, 29, 30, 33, 40) produced wrong numbers
in our own copy six times. The seventh was aimed outward: a pattern reported
"0 of 11 Clearlight cabins publish dimensions" when all 11 do, because they write
`46 1/2″` and the regex wanted `46"W x 44"D`.

**A probe encoding our vocabulary is a data quality problem when it is aimed at
our catalogue and a defamation-shaped problem when it is aimed at someone
else's.** A wrong count on our own collection page is correctable. A published
sentence saying a competitor does not disclose something they do disclose is a
false statement of fact about an identifiable business, in copy whose whole value
is that the numbers can be checked.

**Before any claim about a competitor:** find one page you have read yourself
that contains the thing, confirm the probe fires on it, and only then run the
set. A zero or a suspiciously low count is a vocabulary mismatch until proven
otherwise. This is the known-positives rule below, with a higher bar and a
different reason.

### When a set of findings shares an exact magnitude, the magnitude is the bug

`staged-freshness.mjs` first reported **58 staged files differing from live**,
around 50 of them by **exactly +6 or +8 characters**. That would have gone to the
client as an estate-wide emergency.

Markdown keeps a newline between block tags and Shopify stores them stripped, so
collapsing whitespace turns `</p>\n<h2>` into `</p> <h2>` and leaves it differing
from `</p><h2>` **by one character per tag boundary** — six boundaries, +6.
Normalising `>\s+<` to `><` first took 58 findings down to 2.

**A real defect distribution is ragged.** Fifty independent copy errors do not
land on two values. **An exact shared magnitude across a set is a property of the
measurement, not of the things measured** — and the tell is available before any
of them is investigated.

**Practice: sort findings by magnitude before reading them.** If a cluster shares
a value, explain the value first. Related to the probe-vocabulary rule, where the
tell is a zero; here the tell is a repeated constant.

### A comparison against a stale dump reports the state before the last apply

`staged-freshness.mjs` — the audit written to check whether staged copy is fresh —
read `data/collections.json` without `assertFresh` and reported two collections as
still reverted **minutes after they had been restored**.

The guard that exists for writes applies to any read whose purpose is comparison.
Same joke as `drift-check`'s validation block sitting below its own `process.exit`:
**the tool built to catch a class of error contained that error.**

**Practice: any script that compares a live value to a stored one calls
`assertFresh` first**, audit or apply. "Read-only" is not a reason to skip it —
a read-only script that reports the past as the present does more damage than a
write that fails loudly.

### A screen's raw count is a hypothesis; the number worth acting on is the one that survives reading

The health-claim screen returned **58 sentences across 28 articles**. Reading all
38 of the highest tier by hand, roughly half were bibliography lines, debunks, or
sentences about exercise rather than sauna. **Measured precision ~50%**, so the
actionable figure was **~19 assertions across ~15 articles**.

Report **both numbers, with the precision measured rather than asserted**. The raw
count says how much to read; the surviving count says how much to fix. Giving only
the raw count overstates the problem and giving only the tidied one hides the
method.

**And stop tightening the regex once precision is measurable.** Past that point it
is tuning until the output looks right, which is how a guard stops meaning
anything (see the composition-heuristic note in `scripts/lib/probes.mjs`).

### A guard anchored to live content dies when you fix the content

`health-claim-screen.mjs` validated itself against the real opening sentence of
`how-saunas-improve-circulation`. Correcting that sentence deleted the fixture, and
the screen then refused to run — **at exactly the moment it was most needed, to
confirm the fix and catch the rest.**

**Validation fixtures are synthetic.** A constructed positive and several
constructed negatives, living in the script, immune to edits in the estate they
check. The screen now carries one positive and three negatives, including a
correctly-cited study result and a debunk, so a probe that flags either of those
fails its own test.

### Any pattern-matching probe must be validated against known positives

Screen for something you already know is there and confirm the probe finds it. A regex over
59 meta descriptions reported 10 health-claim matches; word stems found 27. It matched
`/reduces? inflammation/` and missed "inflammation reduction". Counting is not evidence that
the count is complete.

## A report is only useful if the work that follows it reads it

**Producing findings faster than they are consumed creates the appearance of
knowing something the project does not act on.**

`reports/article-health-claim-screen.md` recorded, days in advance:

> `saunas/dry-sauna-for-home` — **unpublished**, so no exposure

`reports/c3-scope.md` then scoped that article as a **rescue** — 7,481 words, a
good comparison section, zero GSC impressions — and read the zero as a ranking
problem. A rewrite was planned and performed on a page nobody could reach.

**This is not a judgement failure and it is not instance 53.** There, a dependency
was identified and *dismissed*. Here it was identified, recorded correctly, and
the later work simply never consulted it. **The finding existed and did no work.**

**Practical form, and it is one command:**

```bash
grep -rn "<handle>" reports/ BACKLOG.md
```

**Before scoping work on any page, grep `reports/` for its handle.** It would have
saved a rewrite of an invisible page, and this repo now holds enough reports that
the odds of a relevant one existing are high.

### And the specific trap it exposed

**A zero in GSC has at least three causes, and they demand completely different
work:**

| cause | the work |
|---|---|
| not ranking | rewrite, retarget, or link |
| not indexed | check `robots`, canonical, coverage |
| **not published** | **publish it** |

**Reading it as the first is the expensive assumption, because it is the only one
that justifies a rewrite.** Check publication state before anything else: it is a
single field and it invalidates every other diagnosis.

## The class with no guard: every gate measures the intended change, none measures its REACH

**This is the parent of three separate failures and it should be read before the
instances, not after them.**

| guard | measures | blind to |
|---|---|---|
| `assertWellFormed` | the string you send | every other field in the mutation |
| `showDiff` | the field you named | fields the script did not know it was setting |
| `assertFresh` | the dump's age | which records the write will touch |
| the dry run | the invocation you typed | a different invocation |

**Three regressions on 9 September 2026, all the same class:**

| | intended | actual reach |
|---|---|---|
| dropped `--only` | 1 collection description | **56 collections**, 3 cluster links destroyed |
| partial `seo` object | 5 meta descriptions | **5 metas AND 5 SEO titles nulled** |
| one product archived | routine housekeeping | **19 figures stale across 7 pages** |

**Each was found by accident, and each gate did its job.** The string was
well-formed. The diff printed the field named. The dump was fresh. The dry run
matched what was reviewed *for the command that was reviewed*.

**`assertReach` now exists** — `scripts/lib/reach.mjs`, wired into
`apply-seo-fields.js`, designed in `reports/reach-guard.md`. It captures the
WHOLE record before a batch, diffs every field afterwards, and **throws** on any
change outside the declared handles and fields. `--reach-ok <field>` allows a
named collateral field so a deliberate two-field write stays possible and stays
on the record.

**It runs AFTER the write, and that is deliberate.** Predicting reach would mean
re-implementing the API's semantics, and that prediction would have been wrong
about `seo` in exactly the way the script was. **A guard that models the system it
guards inherits the system's surprises.** It is only acceptable because the
capture doubles as the rollback source.

**Proved against all three known-broken cases plus two controls**
(`scripts/audit/reach-selftest.mjs`), and against the live API
(`reach-liveproof.mjs`, which writes two fields declaring one on the smallest
collection and restores it). For the drift cascade only the WEAK claim is proved
and the test says so: `assertReach` does not catch it at the write, because
archiving a product is a legitimate declared change — what the same capture buys
is that a derived count moves visibly at the moment of the archive.

**Wire it into every remaining apply script before the next batch write.** Still
manual meanwhile, and the question to ask before every write:

> **What else does this touch?** Not "is the change correct" — "what is the set
> of records and fields this mutation can reach, and is that set the one I
> reviewed?"

Concretely: name the handles, name the fields, and after any batch **re-read one
field you did NOT intend to change** on a record you did touch. All three
failures above would have been caught by that one habit.

## HARD RULE — the diff you approve must come from the same command you execute

Argument for argument. A dry run is not a review of *the change*; it is a review
of **that invocation**. Change the invocation and the review is void.

On 9 September a `cold-plunge` correction was dry-run as
`apply-collection-copy.js --only cold-plunge`, the single diff was read, and then
`apply-collection-copy.js --apply` was executed **without `--only`**. It wrote 56
collections. 53 were no-ops. Two reverted three C4 cluster links that had been
wired eight days earlier and verified live.

**The gate was honoured and it protected nothing**, because the reviewed command
and the executed command were different commands.

**Practice:** copy the exact dry-run line and add `--apply` to it. Never retype
it. If the flags differ, dry-run again.

## Staged copy has no freshness guard, and it needs one

`assertFresh` compares DUMPS against `data/changelog.jsonl` and refuses to write
from a stale one. **It has no opinion about `content/`.** The staged markdown in
`content/collections/` is a claim about what a live description says, it goes
stale the moment anyone edits live out of band, and **nothing checks it.**

That is how instance 55 happened: the C4 links were added straight to the live
descriptions, `content/collections/full-spectrum.md` and `low-emf.md` were never
updated, and an apply that "restores the approved copy" silently reverted them.
The two files had been stale for eight days.

**Every apply script that writes from `content/` has this gap** —
`apply-collection-copy.js` today, and `apply-article-seo.js` and
`apply-seo-fields.js` by the same pattern.

**A difference between staged and live is not automatically a defect. There are
three states and only a human can tell them apart:**

| | |
|---|---|
| **PENDING** | staged is newer — an approved edit not yet applied. Apply it. |
| **STALE** | LIVE is newer — applying would REVERT an out-of-band edit. Stop. |
| **UNKNOWN** | both moved, or the change cannot be attributed. Stop. |

`scripts/audit/staged-freshness.mjs` reports the split; the guard that refuses is
still to be written (see BACKLOG). **It must refuse rather than warn** — a warning
in a 56-row apply is a line of output nobody reads, which is exactly how three
links disappeared.

### The smaller the perceived effort, the less scrutiny it attracts

**The ten-minute fix that needs no checking is exactly the one that gets applied
without checking.**

It arrived as a backlog item — a Reddit-citation finding written down once, carried
forward as settled, and due to be applied in ten minutes without reopening the
article. The full read cancelled it: the article already segregates Primary
Research from User Experiences, so there was nothing to fix. The finding had been
wrong since the day it was written, and its smallness is what protected it.

**This generalises past backlog items.** A backlog entry, a one-line fix, a
"trivial" rename, a date bump, a single-string substitution — each is judged cheap,
and the cheapness is read as evidence that it is also safe. The two are unrelated.
Instance 61 was a print-line patch. Instance 62 was two links on one page.

**A backlog item is a claim with an expiry date, not an instruction.** It records
what was true when someone looked. Re-derive it against the current state before
acting, and treat the ten-minute estimate as a reason for suspicion rather than a
reason to skip the check — the estimate was made by the same reading that produced
the finding.

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

## A partial match is the dangerous outcome

Total failure is visible — nothing changed, you investigate. Total success is fine. **A
subset match leaves an inconsistent state that looks deliberate**, with no error raised
anywhere, and reads as intent to whoever finds it later.

This project hit it three times: a delivery-paragraph swap that matched 18 of 34 files and
left 16 pages on old pricing; a SKU naming convention that held for 3 of 4 products and
would have made a correct title wrong; and a find-and-replace that corrected 3 of 4
products and silently no-opped on the fourth because the text was lower case.

**Rules:**

- **Any find-and-replace across a set must report its match count per target. A target
  matching zero is a FAILURE, not a skip** — exit non-zero and make the operator decide.
- **A naming convention, SKU pattern, handle structure or metafield habit is useful for
  finding candidates and never for concluding.** Generate the shortlist from it; confirm
  every row against the authority before acting. A convention that works 75% of the time is
  worse than one that works 0%, because it earns trust before it costs you.
- **Always dry-run a batch edit and read the per-target counts**, not just the summary. A
  run reporting "3 applied" looks like a completed job.

### When a guard exists for the question, run the guard before answering by hand

**Ninth instance of the probe-vocabulary series and the worst of them**, because
every earlier one was a probe missing something with nothing better available.
This one was a hand check getting the answer wrong **while a working guard for the
same question was running and passing.**

I searched a live collection page for two container class names, found them only in
CSS, and reported that no collection page renders its description — a P0
regression, escalated, other work stopped. `verify-render` probes for the first 40
characters of the stored description in the document body. It passes. It has always
passed. It was answering exactly the question I answered wrongly, and it takes one
command.

> **A guard encodes a definition someone thought about. A hand check encodes
> whatever you happened to search for.**

The guard had considered which container, which part of the document, entity
differences, CDN lag and the retry. My hand check considered one class name I had
read in a file five minutes earlier.

**Practice: before answering a question by hand, ask whether a script already
answers it.** `npm run` and `ls scripts/audit/` are the whole check. If a guard
exists, run it first and let a hand check *explain* its result rather than replace
it. Where they disagree, the guard is the evidence about the estate and the hand
check is evidence about your assumptions.

### And a switch in the off position is not evidence that something is off

The same investigation found `enable-saunaBlock: false` gating a description block,
and it read as the smoking gun. **It is `false` in all five published themes,
including the one that fixed the render.** It gates a second, dead path that has
never been on.

**A false lead that looks like a cause is more expensive than no lead**, because it
stops the search. Before treating a disabled feature, a missing file or an empty
setting as the cause of a regression, **check it against a version that worked.**
If it is identical there, it is not the cause, whatever it looks like.

## A guard is written against conditions that will change

Three separate false results came out of one script, `verify-render`, and none of them was
a coding error. Each was an assumption that was true when the guard was written and quietly
stopped being true:

| | What broke | Assumption that expired |
|---|---|---|
| **14** | silent false **pass** | the dump is current |
| **23** | false failure | the page is served the instant the API returns |
| **24** | false failure | the sample is small enough not to be rate-limited |

The sample grew from 10 collections to 56. The dump aged behind an apply. The CDN took a
minute. Nothing failed loudly at any point — the guard just started answering a different
question than the one it was written to answer.

**So: re-prove a guard whenever the thing it checks grows.** New collections, a larger
catalogue, a faster cadence of applies — each is a reason to re-run the proof that the
guard still catches what it exists to catch. "It passed" is not evidence the guard works;
it is evidence it did not object.

**And separate "I could not check" from "this failed."** They demand opposite responses,
and collapsing them is what makes a guard untrustworthy. `verify-render` now reports
UNREACHABLE distinctly from FAIL, and **still exits 1 for both** — an unchecked page is
not a passed page (that was instance 14's whole lesson), but the operator is told which
problem they actually have.

## A pattern approved on one collection is approved in shape, not in wording

The unavailability line was approved on `cold-plunge-cooling-system`, where 9 of 11
products were out of stock and **cheaper than both live units**. Rolling it out meant
re-deriving it from each collection's own facts:

- `dynamic-cold-therapy` — draft band **below** the live floor, so the cheaper-options
  framing is true and was used
- `medical-sauna` and `cold-plunge` — draft band sits **inside** the live band, so the
  same sentence would have been **false**. Both got a breadth statement instead.
- `massage-chairs` — qualified at 47% until the Kahuna archive landed, then **11%**. Dropped.

**Three collections, three different true statements, rather than one sentence applied
three times.** If the facts do not support the shape, the shape does not apply. Re-derive
before every instance, and re-derive from a dump that post-dates your last write.

## And a position, on its own, points at the wrong fix

**The rank-tool rule one level up, and it is the bigger of the two.**

The earlier rule settled *where the number comes from*: GSC, not a third-party
tool. This one is about what a position can and cannot tell you once you have it.

**Two failures, both from the same striking-distance brief:**

| | looked like | actually was |
|---|---|---|
| `low emf infrared sauna`, **position 18.6**, 0 clicks | a snippet problem — good page, poor CTR | **a visibility problem.** Position 18.6 is page two. The collection earns 25 impressions while the query shows 187, so most of those impressions are not even this page. Nothing is clicked because nothing is seen. |
| `infrared sauna for muscle recovery`, **"competition 0.01"** | a winnable term | **10 impressions a month.** The competition figure came from a rank tool; the demand it implies does not exist. |

**A page at 18.6 looks like a snippet problem and is a visibility problem. A term
at competition 0.01 looks winnable and has no demand.**

**Practice: before treating a position as an opportunity, check the impressions
the PAGE actually earns for that term.** Position without volume is a number about
a query nobody makes — and position without page-level impressions is a number
about somebody else's page.

The position test in the snippet rule still holds and this refines it: **page one
is the precondition for a snippet fix, not the whole test.** The page also has to
be the one earning the impressions.

## Third-party rank tools understate position on this site — compare GSC to GSC

Measured 8 September 2026. The round brief quoted positions from Ubersuggest and Semrush.
Against Search Console's own data for the same pages, **all three checkable figures were
wrong in the same direction — better than reported:**

| | Third-party said | GSC says |
|---|---|---|
| `floatation-therapy-tanks` | 98 | **55.1** |
| `thermasol` | 42 | **35.1** |
| `infrared sauna for muscle recovery` | 28 | **18.6** |

`low emf` at 17.6 matched the quoted 16–18, so the tools are not uniformly wrong — they are
**systematically pessimistic on this site**, most severely on the weakest pages.

**The rule: GSC is the source of truth for position, and every measurement compares GSC to
GSC.** A before from one tool and an after from another measures the tool, not the work —
and on these numbers it would have manufactured a 40-place "improvement" on floatation out
of nothing.

Third-party tools stay useful for **volume, CPC and competition**, which GSC does not
provide. They are not authoritative for **position, impressions or CTR** on pages this site
owns. When anyone quotes a Semrush position, this is the reason to re-check it.

### And exclude pages that had nothing to move

A page with zero baseline impressions cannot demonstrate that a change worked. Eleven of
the 52 collections receiving titles have no GSC row at all. They are **excluded from the
checkpoint arithmetic entirely**, not reported alongside — including them drags any
percentage below the truth and hides the effect on the pages that could actually move.

## Verification establishes agreement, not truth

The hardest-won rule on this project, and it cost 36 pages.

`data/shipping-facts.json` was marked `verified_by: client` and
`discrepancies_found: "none — the live policy page matches the client-supplied facts on
every point"`. The check was real and careful. **The fact was still wrong**, because the
source it was verified against was wrong: the shipping policy page described Premium
Installation as a base fee with assembly billed hourly, when the $1,800 is all-in except
electrical.

That wrong figure went into the delivery paragraph on **36 live collection pages**.

**When two sources agree and a third contradicts them, the contradiction is the finding.**
The agreement may only mean one was copied from the other. Two sources are not two
witnesses when one is derived from the other.

### So ask whether they are independent BEFORE treating agreement as evidence

Not after a contradiction shows up. The test is one question — *could either of
these have been copied from the other?* — and it is cheap enough to ask every time.

**Worked example, 10 September 2026, and it reached a client recommendation.** An
archived product cross-sold to a competitor. The competitor's URL named model
**DYN-6336-02**; our catalogue held a product titled *"… Low EMF … (DYN-6336-02)"*.
Two sources, same number, and I called the match decisive.

**Our title had been copied from the manufacturer's own mistitled page.** Their Low
EMF Lugano sits at `/products/new-2019-model-**dyn-6336-01**-…` with a title reading
**(DYN-6336-02)**. They mistyped it; we inherited it. The agreement was one error
seen twice.

**Our SKU field says `DYN-6336-02 Elite` on a different product** — the $3,499
Elite — and that is the right target. It won because **nobody had edited it**, not
because it is inherently more authoritative.

**Practice, in order:**

1. For any product identity claim — model, SKU, variant, trim — **the SKU field is
   primary and the title is derived copy.** Titles are written by hand, get pasted
   between listings, and travel with supplier feeds.
2. Before citing agreement between two sources, name the **path** by which each got
   the value. If you cannot, you have one source and a copy.
3. A tiebreaker field is only a tiebreaker while it stays unedited. Say so when you
   rely on it, so the next person knows what the claim rests on.

This is the verifier-independence rule — *a verification that shares its blind spot
with the thing it verifies is not a verification* — outside a script. Same
mechanism, and harder to see, because two systems agreeing feels like corroboration
in a way that one regex agreeing with itself does not.

### The practical rule: name the primary source

For any commercial figure — price, fee, inclusion, warranty term — identify which source
is **PRIMARY** before trusting it:

- **The product a customer buys is primary.** It is what they see at checkout and what
  they are charged.
- **A policy page describing it is derived.** So is a collection description, a FAQ, an
  email template, and this repo's fact files.
- **Where they disagree, the product wins and the policy is the defect** — fix the derived
  source, and check every other derived source for the same copied error.

And when the primary source contradicts *itself* — as `installation-assembly` did, listing
"Full Assembly & Setup" under What's Included while How Pricing Works billed assembly
hourly — that is not ambiguity to resolve by picking one. **Stop and ask.** Publishing
either reading would have put a price on 36 pages that the store does not honour.

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

---

## Resolved decisions

### MAP / dealer terms — RESOLVED 8 September 2026. We may publish warranty comparisons naming brands we sell.

Open since the Brand Strategy chat. **The client's ruling: approved.** A critical
warranty comparison may name the brands in our own catalogue.

This unblocks the strongest material the project owns.
`data/warranty-facts.json` records the pattern across Harvia, HUUM and Narvi:
**the heating element — the part that actually fails — is excluded or carries the
shortest term at every one of them.** Almost Heaven's own warranty page publishes
the same split (1 year on elements, 5 years on other heating components), which
makes four manufacturers and turns a quirk of three suppliers into a **category
finding**. It is the single most useful thing we can tell a sauna buyer, and no
competitor states it.

The existing constraints in `warranty-facts.json` still bind and are not loosened
by this ruling: three brands only, attribute per brand, never "10+ years", and
where dealers disagree say the terms vary and tell the buyer to confirm.

Unblocks: the Almost Heaven and Sun Home reviews, and the Warranty Decoder later.

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
