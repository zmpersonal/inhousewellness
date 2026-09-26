# Round 23b theme branch — the product-to-collection links are removed

**Theme `167150092355` — "Round 23b — product-to-collection links removed". UNPUBLISHED. A human publishes.**

Preview: `https://inhousewellness.com/?preview_theme_id=167150092355`

Branched from the **current MAIN `167149797443`**, which is Round 23's disclosure-removal branch — the
client published it, so this is a second branch rather than an addition to the first.

## What changed

**Two files, one line each.** `{% render 'product-collection-links', product: product %}` removed from
`sections/main-product.liquid` (line 1269) and `sections/bundle-product.liquid` (line 1262), each
replaced by a dated comment. Both were re-pulled from the current MAIN and md5-verified
(`03c5b2c1…`, `bb7013c5…`) before editing.

**`snippets/product-collection-links.liquid` and everything it reads are untouched**, so restoring
this is re-adding one render line.

## Two files cover all three templates

The answer to "check whether it renders on wider-images" is **yes, it does** — `wider-images` renders
the `main-product` section, so there is no third section to touch. Verified on the live pages before
editing: the `inh-product-collections` nav was present with 2 collection links on **all five** probed
products across all three templates, including `saunalife-g3`.

⚠️ My first probe searched for `inh-collection-links` and returned **false on every product**. That
class does not exist; the snippet emits `inh-product-collections` (line 63). A zero across an entire
sample is the signature of a probe-vocabulary mismatch, not of an absent feature.

## This reverses Round 9, as a client decision on appearance

**Recorded so the history stays legible, not as a defect being fixed.** Round 9 was built because:

- **zero of 673 product pages linked to any collection**, and
- **eleven ThermaSol product pages were outranking their own collection page** for the collection's
  own terms.

The links existed to give a decided buyer a route up, and to stop product pages competing with the
collections they belong to. **Removing them re-opens both.** Expect product pages to keep absorbing
collection-level terms; if collection rankings matter later, an internal product→collection route has
to return in some form. The reasoning is preserved in full inside the theme comment itself, so the
next person reads the argument rather than inheriting a bare decision.

## Verified on the preview

| Check | Result |
|---|---|
| `r23b-links-collateral.mjs`, one product per template | **5/5** — nav present on MAIN, absent on the branch, and the rest of the visible text byte-identical |
| mutant: the cut does nothing | fixtures go **red**, so the check is not decoration |

Covered: default (`cal-flame-costa-bbq-island`, `scandia-electric-heater-6kw`), Bundle
(`dynamic-cold-therapy-pvc-barrel-cold-plunge`, `ct-georgian-cabin-sauna`), wider-images
(`saunalife-g3`). Both themes are read through the preview handshake with `assertServedBy`, so a
dropped cookie cannot compare MAIN against MAIN.

## Rollback

Re-add the one render line to each file. The branch is unpublished, so nothing is live until someone
publishes it.
