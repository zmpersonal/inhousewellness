## Round 18h — the proof held; its runner and its tamper did not

### A proof chain piped through a filter does not halt

`step | grep …` reports grep's exit status, not the step's.
- The Osla restore printed FAIL.
- The pipeline exited 0.
- The next step ran against a product in a state nobody had checked.

**This is the `cmd | tee` rule again (CLAUDE.md, social engine), one repo over.**
Every multi-step proof now runs through a script that checks each exit code and dies on the first failure (`r18h-proof.sh`).
**A proof whose steps cannot stop the next step is a log, not a proof.**

### A tamper test must leave live matching NEITHER recorded state

The "fake a third-party edit" step altered only the recorded `before`.
- Live still equalled the recorded `after`.
- The guard passed, correctly for what it tests.
- The restore then wrote the tampered `before` to the live product and archived the Osla for about 7 seconds.

**The test did not simulate what it claimed to simulate.** An out-of-band edit changes *live*. That only happens in the fixture if both recorded states move away from it. Assert the premise before the step: live ≠ before **and** live ≠ after.

### Meta and Copilot are one-way from this token, and a draft hides its channels

- A Meta unpublish returns no error and does not take. This is the instance-22 shape again, now on a write path. Plan every channel write as add-only unless removal has been proven.
- A DRAFT product reads back with no channels. On activation its old assignments reappear: Osla came back with Copilot, POS and Shop; the Versailles Edition with POS.
- So "the before-state channels" of a drafted product are not knowable until it is active. A restore that believes it knows them will remove channels it never saw.

### A reach check that reads one channel misreports the rest

18g verified the Osla on the Online Store and reported it as "Online Store only". It was on four channels.
The check was correct about the one channel it read, and the report was about all of them.
**Name the scope of the reading in the sentence that carries the result.**

### An injection test must prove it landed

The injected-word test replaced `'Tradeoff:'`, a string that does not exist in the Lugano article.
Nothing was injected, so there was nothing to refuse, and "refused" would have been vacuous.
**The runner caught it by halting.** Injections are now article-agnostic (the first `<p>`, the first `</p>`) and assert that the body changed before handing it to the guard.
**Same rule as a guard that has never failed: a negative test that never delivered its negative has not been run.**

---

## Round 18g — order of operations is the safety, and a GONE check proves the outcome

### When a change passes through a dangerous intermediate state, the ORDER is the guard

Republishing the Osla takes three writes: policy, status, channel. In the wrong order there is a
window in which an $8,499 sauna at zero stock is live **and orderable**. `r18g-osla.mjs` sets the
policy to DENY **first**, asserts `availableForSale` is false, and only then goes live; the restore
runs the exact reverse (off the storefront before the policy returns). **A sequence of individually
correct writes can still pass through a state nobody would approve.** Name the intermediate states.

### A display that tidies a value produces a spec that matches nothing — the count refused it

The Catalonia enumeration printed hrefs with the domain stripped, for readability. The spec was built
from that display, went out relative, and **matched 0 of 9** — the asserted count refused it. Sixth
instance of *an identifier comes from the data, never a display*, and the first where the display was
my own formatting choice made a few minutes earlier.

### A GONE check proves the outcome; it must model what it guards

Per-article *"must be absent afterwards"* strings — `MSRP`, `$14,999`, `identical` — prove the point
of the edit rather than the success of each write. The first version flagged a leftover
`/products/dynamic-garcia` that was an **unrendered editor's HTML comment**, not a link. The guard was
narrowed to the `href`, because what it exists to prove is *no link remains* — **the faithful model
was the narrower one**, and it still refuses a real remaining link.

### And the ambiguous string was the one I was not told to change

`"$3,499 (Low EMF)"` as plain text occurs **once** in the HTML — in the tier line, not the authorised
table row, whose markup is `<strong>$3,499</strong> (Low EMF)`. A text-level match would have edited
the wrong element: **the verify-the-outcome rule's "match on the wrong element refuses nothing".**
Caught by counting the exact string before writing the spec.

### A zero in someone else's system needs the other system's count beside it

Klaviyo shows **0 "Placed Order" events from March to September 2026**. On its own that reads as
"no orders". **Shopify shows orders in August and September.** The pair means the integration stopped
delivering — a different problem with a different fix. A zero is only a measurement when something
independent says what should have been there.

---

## Round 18f — a recommended treatment depends on a field nobody named, and "stale" was three different things

### The fix for a stock-out is only safe if the sell-when-out-of-stock policy is OFF

The client's treatment for a temporarily out-of-stock product — republish at inventory 0 so it renders
sold out at a 200 — is right, and **it would have sold the Osla.** The product is tracked, at qty 0,
with the policy set to **CONTINUE**. Republished as-is it is *available for sale*: an $8,499 sauna the
store cannot supply, orderable. **The policy flip is the part of the fix that makes "sold out" true.**

Same family as `inventory: 0` meaning untracked on the Ripavi: **a quantity means nothing without its
tracking flag and its policy**, and a plan written in terms of quantity inherits that.

### A two-way split met a third case, twice

"Temporarily out of stock → republish; discontinued → 301" covers **3 of the 5**. The other 2 are
**duplicates**: an archived or draft listing whose product is live under another handle. For those the
answer is neither — relink to the live twin, and a redirect is safe because there is no restock to
wait for. **One of the two was found only by normalising SKUs**: `GDI-6880-02-Elite` against
`GDI-6880-02 Elite`. The exact-match query said "no other product". Fifth instance of the normaliser rule.

### Drafting on stock-out is the store's PRACTICE, which makes Osla a class

**Only 1 of 481 active products is actually sold out.** Every other stock-out is either still
orderable or pulled to draft. So the 404 is not an accident to fix once — **every future stock-out does
the same to its inbound links**, and nothing warns the person drafting it that articles point there.

### "Stale price" was three different defects, and only one was a price

| flagged | what it actually was |
|---|---|
| Maxxus Seattle "under $2,000" | a stale price — **fixed**, $2,299, one representation |
| Lugano "$3,499 (Low EMF)" | an **identity conflict**: SKU and link say the $2,699 listing, the price says the $3,499 Elite. Choosing is a product decision — **held** |
| Monaco "~$5,999 MSRP" | a **positioning claim** in five places, plus a street-price range; we charge $6,499, above both. Unverifiable from here — **held** |

**The screen found three places to look. Reading found three different kinds of problem**, and treating
them as one ("correct the price") would have been wrong on two of three.

### A near-empty result for a JS-injected feature needs the interaction that triggers it

"No back-in-stock button" was first measured before any interaction — and this theme defers third-party
scripts until the visitor acts. The absence was re-measured after interaction, **with a positive
control**: Facebook, GTM and DoubleClick all loaded, so deferred scripts did fire, and Klaviyo still
did not. **Without the control, "Klaviyo did not load" could not be told apart from "nothing loaded yet."**

---

## Round 18e — two matching heuristics failed in opposite directions, so the question changed

### Associating a price with a product by position is a heuristic that cannot be tuned right

Sizing site-wide price staleness needed "which price belongs to which product link". Two rules were
tried and **both were wrong, in opposite directions**:

| rule | what it got wrong |
|---|---|
| nearest `$` by distance | gave the Golden Designs Zurich the St. Moritz price that sat *before* its link |
| first `$` after the link | made a stale-looking Venice claim vanish, and gave red-light products their *neighbour's* price |

**The second rule was a tuning of the first to fix the case in front of me** — exactly the move this
file warns turns a guard into something that agrees with its author. It was dropped, not tuned again.

**The question was changed instead:** *does this block quote this product's LIVE price anywhere?*
Yes → fine, whatever order the prose is in. No → a person reads it. That needs no association at all,
and it reduced 122 link/price pairs to **13 to read, of which 3 were genuinely stale** — a 23% read
precision, measured, which is what an honest screen looks like.

### And I reported a correct claim as stale, from the first heuristic

I told the client *"the clearest price at $2,499"* was a stale Venice Elite price. It is correct: that
sentence prices the Venice **Edition** at $2,499 and the **Elite** at $2,699, both matching live. The
heuristic pinned one product's price on the other's link, and I repeated its output as a finding.
**A heuristic's output is a reading queue even when it is one line long.**

### A cross-reference is not a claim about the thing it references

Golden Designs flagged three "stale" prices. **All three prices were right.** Each flagged link was a
cross-reference — *"step up to the 5-person Gargellen"* — sitting in a paragraph that prices a different
product. A link inside a priced paragraph does not inherit the paragraph's price.

### A product that goes to DRAFT takes its inbound links with it, silently

**33 links on published articles point at 5 products that are DRAFT or ARCHIVED, and all 5 return 404.**
The worst is the Osla Edition: 14 links, including a dedicated review article, and it is the
*"Best for most buyers"* pick of the Golden Designs review. Nothing about unpublishing a product warns
that articles link to it. **Same shape as the one-archive-invalidates-19-figures cascade**, reaching
links instead of counts.

### Two of three prices wrong in one table meant the LINKS were wrong too

The Costco guide's comparison table was fixed as authorised. The audit behind it found the Gracia claim
has **four link representations, all to the wrong product** (DYN-6119-03 FS), and the "identical /
same hardware" claim has **about ten prose representations** the softened table now contradicts. Only
the table was authorised; the rest is reported. **A corrected table beside ten uncorrected sentences
is a page that disagrees with itself** — the representations rule, applied to a claim rather than a figure.

### A proof that has never refused is not a proof

The byte-identical-outside-declared-changes check had passed every run in 18c and 18d. This round it was
made to fail on purpose — `--inject-stray` (one undeclared word) and `--inject-link` (one undeclared
link) — and refused both. Both switches refuse to run with `--apply`.

---

## Round 18d — a link's LOCATION decides its job, and checking a premise found a live defect

### Before substituting a link, read which PARAGRAPH it is in

The brief asked to repoint three Costco links — Bellagio, Gracia, San Marino Elite — at our product
pages, on the reading that they sent readers to Costco to buy units we stock. **All three sit in the
"Sources and disclosure" paragraph, in one sentence:** *"Current Costco listings and policies:
Dynamic Bellagio, Dynamic Gracia, San Marino Elite, Backyard Discovery Bennett, and Costco's return
policy (accessed August 2026)."*

**Pointing an item in a list labelled "Current Costco listings" at our own page misattributes the
source** — variant 7 in this file, right citation / wrong destination, created on purpose. And the
conversion the substitution was meant to capture was **already captured**: the body carries a
"Costco vs. InHouse Wellness" section, an "Exact same model" comparison table and repeated "Shop the …
at InHouse Wellness" links for all three units.

**Held, not executed, and reported with options.** Same family as *a source cited as a category
keeps its name*: the job a link does is set by where it sits, and a sources list is not a call to action.

### Checking the premise found a live factual defect the brief did not know about

The comparison table says *"Dynamic Gracia 1–2P · Costco ~$1,799 · InHouse ~$1,899 · Exact same model"*
and links **DYN-6119-03 FS — Full Spectrum, Near Zero EMF, $2,899.** Costco's unit is the 1–2 person
**Low EMF** Gracia. We stock that one too — **DYN-6119-01, $1,999** — and the article does not link it.

**"Gracia" names four different products in our own catalogue** (DYN-6119-01, its DRAFT duplicate,
DYN-6119-01-ELITE at $3,999, DYN-6119-03 FS). A title match cannot tell them apart; only the SKU can.
The table's Bellagio price is also stale ($2,499 quoted, $2,699 live).

**And the Costco side cannot be SKU-confirmed from here** — Costco's product pages return a bot wall to
both curl and the in-app browser. The match is slug-to-title, and it is reported as that.

### A "gone" check must use the whole string

Verifying the LifeTrend rewrite, I asserted the phrase *"current LifeTrend Solitude listing"* was absent
from the rendered page. It was present — in a **different, pre-existing, unlinked** sentence (*"Last
verified August 2026 from Costco's current LifeTrend Solitude listing"*) that the edit never touched.
**A substring shared by two sentences made a correct edit report as a failure.** Root-caused before it
was dismissed; the full original sentence is absent.

### Rewrites get a different proof from unwraps, and both are mechanical

Unwraps: visible text byte-identical. Rewrites: **(1)** the link list after equals the link list before
minus exactly the declared removals — which also proves no link was added — and **(2)** with each
declared sentence masked on both sides, visible text is byte-identical. Held on all six articles.

---

## Round 18c — homepage category detection fails for general retailers BY DESIGN

**Classify marketplaces and big-box chains by DESTINATION URL, never by homepage.**

A general retailer's homepage never names our categories. `costco.com` served its real homepage
— *"Welcome to Costco Wholesale"*, cart 1, price 1, **cats []** — and went to T3 KEEP while
**13 of its 14 links pointed straight at saunas and cold plunges.** That is not a Costco bug. It
is the whole class: Amazon, Walmart, Home Depot, Lowe's, Wayfair, Target, Best Buy, Overstock,
Sam's Club, and any home-improvement or furnishings chain. The homepage is the one page on those
sites guaranteed not to mention a sauna.

**The fix is two legs, and the second is the one a naive version drops:**

1. the linked URL names one of our categories, **and**
2. the linked URL is a **product or listing** page, not content.

`bachmanns.com/sauna-maintenance-guide/` names *sauna* in its slug and is a maintenance guide.
A URL-slug classifier without leg 2 would have removed a legitimate citation. **A slug that names
a category is a candidate, never a verdict** — the third appearance of that rule in one round
(vendor substring, homepage signal, URL slug).

`scripts/lib/linked-url-class.mjs` carries 9 fixtures; the headline one is a general retailer
whose homepage names nothing and whose linked URL is a sauna product, and it **fails the old
homepage rule** (T3 KEEP) — proved by running the old rule against it.

**Measured, not assumed:** of the named big-box set, **zero** links exist anywhere in the estate
to Amazon, Walmart, Lowe's, Wayfair, Target, Best Buy, Overstock, Sam's, eBay, Etsy, Menards.
The class present here is four domains, 18 links, all in ordinary articles.

### Two bugs the fixtures caught in the fix itself

- **The self-test never ran.** `import.meta.url === \`file://${process.argv[1]}\`` never matches
  on a path containing spaces, which this repo's path does. The script printed nothing and exited
  0 — a guard that cannot fail. Compare with `fileURLToPath()`.
- **The normaliser erased the signal it fed.** Rewriting `.` to `-` before the page-type test
  destroyed the `.product.` marker the test looks for. **Normalise the axis you are matching on,
  not the one you are testing against** — category on the normalised slug, page type on the raw path.

### And a fixture keyed to one configuration is not testing the code

The unwrap script's fixtures used `plunge.com`, which is only in the cart-test set. Passing an
explicit `--domains` list made them fail — correctly refusing, for the wrong reason. **A fixture
must exercise the configuration that will actually run**, so it now draws its domain from the
active set.

### A correction I owed the client

Last round I wrote that `realrelaxmall.com` "is T1". **It is REVIEW** — the quote-gated shape, and
its one link is still live in `benefits-of-massage-chairs-for-seniors`. The client's ruling on
3dmassagechair leaned on that sentence. **A classification quoted from memory in a report is a
restatement, and it decays like one** — I should have read the tier from the file.

---

## Round 18 — the cart test, and three shapes it could not see

### Cart + category match with price = 0 is a COMPETITOR SHAPE, not a disqualifier

**Client ruling, 18 September 2026.** `hightechhealth.com` — a named competitor — scored
`cart=5, cats=[sauna, infrared], price=0`. The first rule required a published price
(`cart >= 2 AND price >= 1`), so it went to **T3 KEEP**. It gates pricing behind a quote request:
the Sunlighten shape this repo recorded weeks earlier, when `www.sunlighten.com` hid prices that
`shop-us.sunlighten.com` published.

**A price is evidence of selling. Its absence is not evidence of not selling.** Treating the
missing leg as a disqualifier turned a quote-gated seller into a citation to be protected.

It becomes **T1-CANDIDATE**, not T1: the same shape also matched a sauna research blog
(`saunologia.fi`) and an association (`saunas.org`) whose carts sell books. **Confirm by a read,
never KEEP.** `r18-cart-test.mjs --self-test` carries the fixture and it fails the old rule — proved
by running the old rule against it.

### The known-positive block is what caught it

The client had named seven domains as T1. Checking that all seven landed in T1 was the only reason
the miss surfaced. **A named list from the client is a free set of known positives — run the probe
against it before trusting the probe's output on anything else.**

### A homepage cart test cannot classify a general retailer — known limit, NOT fixed

`costco.com` scored T3 with `cart=1, price=1, cats=[]`. It was **not** a bot wall — I said it was,
then checked the stored title: *"Welcome to Costco Wholesale"*, a real homepage. **A general-
merchandise homepage never names saunas**, so the category leg cannot fire even when our link
points at a sauna listing. The fix is to test the **linked URL**, not the domain root. 14 links in
4 ordinary articles are unresolved because of it. `homedepot.com` (empty 200) is the other shape,
a bot wall, and that one IS now fixtured.

**Correction recorded rather than deleted:** my first explanation of the Costco miss was wrong. I
attributed it to the mechanism I had just fixed, which is the "severity from the shape of a
situation" failure pointed at a diagnosis instead of a finding.

### A manufacturer's domain can defeat a vendor cross-check by one letter

Matching T1 domains against our own 41 vendor strings caught three manufacturers and missed
`goldendesigninc.com` against vendor **"Golden Designs Inc"** — the domain drops the *s*. That was
the one row that mattered: CLAUDE.md already recorded this exact domain being misclassified as a
competitor. **A substring match between a slug and a display name is a candidate generator, never
a verdict** — the same rule as titles checking a mapping rather than deriving one.

### "No prose rewritten" can be an assertion instead of a promise

For an unwrap, the article's **visible text — every tag stripped — must be byte-identical before
and after.** Unwrapping removes tags and nothing else, so any difference is the edit doing
something it was not allowed to do. It ran on all 23 articles and held. Any tag-only edit in this
repo can carry the same invariant.

---

## Round 16 — a set counted one way and priced another

### The count and the range described different populations, in the same clause

`collection-spec.js` already rules that **the method travels with the count**, and the
range rule already says **both ends must be measured the same way**. This is those two
rules meeting in a place neither anticipated: not two catalogues, not two pages, but
**one sentence about one set, where the COUNT came from title matching (95, max $28,649)
and the BAND came from collection membership ($1,999–$16,999)**.

Nothing looked wrong. Both numbers were real, both were about infrared saunas, both were
ACTIVE-only, and the median agreed at $3,699 under either definition — which is precisely
why it survived drafting. **The medians agreeing is what made the mismatch invisible.**

| definition | n | max |
|---|---|---|
| title/type matches "infrared" | 95 | **$28,649** |
| ACTIVE members of `/collections/infrared-saunas` | **90** | $16,999 |

**Practice: when a sentence carries a count AND a range about the same set, state the
definition once and derive both from it.** The check is to re-derive the count from the
population the range came from and see whether it moves. Here it moved by five, and the
ceiling moved by $11,650.

And prefer the definition **the reader can check** — collection membership, because the
link is in the same sentence.

### A re-derivation that strengthens the finding is the argument for re-deriving

The voltage figure went from *288 of 480 (60%)* to *367 of 481 (76%)*. I could not
reproduce the inventory's 121/102 split under any pattern, including one widened with
code-point space classes and NEMA/hardwired synonyms.

**The temptation was to keep 60% because it was already written and already approved.**
The honest number was both different and better: three quarters of the catalogue names no
voltage. **A figure you cannot reproduce is not a figure you own**, whoever derived it.

### Two figures refused rather than published, and one was a documented error

- **Sauna heater kW range.** The dump says 3–50kW. `CLAUDE.md` records *that exact claim*
  as false — the 3 from a bag of sauna rocks, the 50 from a stove the store does not sell.
  I derived it fresh, got the same wrong answer, and was about to print it. **Re-deriving a
  figure does not re-derive whether the figure means anything.** The count survived; the
  range is gone.
- **Steam generator ceiling.** Written as 5–30kW; the true top is a 120kW commercial unit.
  Replaced with a durable floor, "start at 5kW", per 6a-ii.

The first is the one worth remembering: **the guard against it was a sentence in CLAUDE.md,
and the only reason it fired is that I read the file before publishing the range.**

### A post-condition can be wrong in the direction of destroying a true figure

My own guard asserted `"95 active"` reaches zero in the traditional draft. That also
matches **"90 of 95 active heaters"**, which is correct. Had I satisfied the guard by
editing the copy, I would have broken a true sentence to make a check pass — the exact
"never satisfy a guard by feeding it a value that makes it pass" failure, inverted.

**A guard firing on something harmless means the guard's model is wrong. It applies to
guards you wrote ten minutes ago**, and those are the ones you defend hardest.

### Enumerating figures returns more than you estimate — fifth instance

15 occurrences of `480`. I would have guessed five. Four refusals, every one a `from`
string typed from memory: `2.4kW` is `2.4 kW`; `don't` was straight, not curly; `44 of 480`
occurs twice, not three times; and one table row says `44 of our 480`, which no target
covered. **The script refusing is the entry — a partial apply would have left a draft
mixing two denominators and reading as deliberate.**

---


## Round 15 — corrections, and one measurement finding

### CORRECTION 1 — "Claude Code's network cannot reach Shopify directly" is FALSE

Carried into the Round 15 brief as settled fact. It is not. Direct Admin API calls work from the
agent session and were used for **every** write this round — theme duplication, `themeFilesUpsert`,
MD5 read-back, product and metafield enumeration. The token returned 200, not 401.

**The real constraint, misstated as a network limit:** large JSON assets exceed the MCP connector's
payload limit. Different problem, different workaround (the Actions workflow), and it does not apply
to theme file writes. **A constraint that gets restated in briefs stops being checked** — this one
travelled from the Tools project and would have routed a whole round through a workflow it did not
need.

### CORRECTION 2 — shop-level review figures are dynamically sourceable

`shop.metafields.judgeme.all_reviews_rating` = **4.82** and `all_reviews_count` = **1431** both
exist. The homepage Organization node reads them live. **No hardcoding, no staleness caveat**, and
the Round 14 comment claiming telephone was "omitted, not guessed" has been updated rather than left
contradicting the code.

### FINDING — Judge.me groups reviews, so summing product metafields double-counts

| method | total |
|---|---|
| sum of `reviews.rating_count` across all products | **3,491** |
| summed over DISTINCT (rating, count) pairs | **1,383** |
| `shop.metafields.judgeme.all_reviews_count` | **1,431** |

**190 of the 248 rated products share a (rating, count) pair with another product** — 33 products
all read `avg 4.93, n 15`. Judge.me assigns one review to every product in a group.

**Anyone computing a catalogue-wide review total from product metafields will get a number 2.4×
too high.** The shop-level metafield is the only correct source. I nearly reported 3,491 as a
contradiction of the brief's 1,431; it was the wrong unit, not a discrepancy.

### FINDING — Judge.me targets the existing Product node, observed not read

Tested in a real browser on both themes rather than from their docs:

| | raw HTML (no JS) | rendered DOM |
|---|---|---|
| **MAIN** | no `aggregateRating` | Product node **with** `{"ratingValue":4.93,"bestRating":5,"worstRating":1,"reviewCount":15}` |
| **Round 15 preview** | `aggregateRating` present | **identical** — one node, one rating |

Judge.me injects **into the existing node**, with the same shape and the same values. It does not
duplicate the key and does not add a second node. **No resolution was required**, and the values
cannot disagree with the badge because both read the same metafields.

## Round 15b — the gtin defect, and five measurement lessons from finding it

### 🔴 An unquoted identifier discards the ENTIRE node, not the field

```liquid
"gtin12": {{ variant.barcode }},        ->  "gtin12": 019962854569,
```

JSON forbids a leading-zero number literal. A strict parser does not drop the bad key — **it throws
away the whole Product node**: offers, price, availability, and the `aggregateRating` Round 15 had
just added. The rating rendered perfectly and died with the node it sat in.

**Measured: 31 of 478 published products, 24 of them rated and ACTIVE — 13.1% of the ACTIVE rated
set was invisible to a strict parser.**

**Any raw interpolation inside a block that is otherwise correctly filtered is a latent
node-killer.** In that same Offer block, `sku`, `priceValidUntil`, `price`, `priceCurrency` and
`url` all already passed through `| json`. The three gtin lines were the only raw ones — which is
exactly how a defect survives: it hides inside correct code. And `gtin12/13/14` are schema.org
**Text**, so quoting is the right type, not a workaround.

### 🔴 FIXTURE RULE — a validator that samples a clean value proves nothing

**Round 15's `validate-round15-jsonld.mjs` passed six template types and missed this.** It parsed
`/products/maxxus-mx-s106-01`, whose barcode has no leading zero. Six green ticks, 31 broken pages.

**Choose fixtures that can BREAK the property under test**, the way a known-positive is chosen for
a screen. `verify-gtin-fix.mjs` now uses four: a leading-zero barcode, a barcode with non-numeric
characters, a **Bundle-template** product carrying both a leading zero and a rating (the only path
that exercises `bundle-product.liquid`), and a zero-review product to prove the guard still holds.

### `/products.json` omits `barcode` — a zero from the wrong endpoint reads as a clean result

The variant serializer in `/products.json` **has no `barcode` key at all**, while
`/products/<handle>.js` returns it. My first blast-radius run reported **"0 of 478 affected"** and
looked like good news. **It was a property of the endpoint.**

Same family as the dump-absence series, and worse here because zero read as *safe* rather than as
*suspicious*.

### Storefront rate limits: concurrency 2, backoff, and always print the status distribution

Second run, at concurrency 10: **117 of 478 returned** and it reported "2 affected" — a precise
number over a 24% sample. At concurrency 2 with 8s backoff: **478 of 478, absorbing 51 × HTTP 429.**

**Print the HTTP status distribution and an explicit INCOMPLETE warning**, so a shortfall can never
be mistaken for an answer. The scanner now does both.

### U+2011 is a store-wide data characteristic, not a Narvi quirk

`huum-hive` carries barcode `537‑AZ‑128267` — **U+2011 non-breaking hyphens**, the same character
already recorded in Narvi's *"Wood‑Burning"* titles. Confirmed now in **barcodes as well as
titles**, from a different vendor. Treat it as a property of this store's data, and build every
character class from code points.

### SHOPIFY_ADMIN_TOKEN has 401'd twice, both times right after a successful build

Round 13, and again at the end of Round 15 — **both immediately following a session of successful
writes**, with `.env` unchanged at 38 chars each time. **Custom app tokens do not expire on their
own.** Suspect a scope edit or an app reinstall, plausibly from the parallel workstream that shares
these credentials. **If it recurs, check the app's install history before regenerating** — a third
instance is a pattern, not bad luck.
