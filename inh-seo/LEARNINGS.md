
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
