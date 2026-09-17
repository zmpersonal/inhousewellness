
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
