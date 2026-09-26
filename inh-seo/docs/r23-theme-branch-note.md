# Round 23 theme branch — the product disclosure block is removed

**Theme `167149797443` — "Round 23 — product disclosure block removed". UNPUBLISHED. A human publishes.**

Preview: `https://inhousewellness.com/?preview_theme_id=167149797443`

## What changed

**Two files, one line each.** `sections/main-product.liquid` (line 1270) and
`sections/bundle-product.liquid` (line 1263) each had
`{% render 'product-disclosure', product: product %}` replaced by a dated comment recording the
ruling, the reversibility and the exposure figures below.

**Nothing else is touched.** `snippets/product-disclosure.liquid` stays in the theme and every
metafield it read stays on every product, so restoring the block is re-adding one render line.

**Re-verified against live before editing.** MAIN has moved since Round 22 — it is now
`146318491715` ("Round 15 — server-rendered rating, H1, telephone"), not the `146149867587`
CLAUDE.md records. Both section files were re-pulled from the current MAIN and are
**byte-identical** to what Round 22 measured (`a9d4926e…`, `d657239f…`), so Round 15 did not touch
them and the edit still applies. The edit was then re-derived from the fresh pull and reproduces
the Round 22 md5s exactly (`03c5b2c1…`, `bb7013c5…`).

## Verified on the preview

| Check | Result |
|---|---|
| `verify-disclosure.mjs` against **MAIN** (the control) | **8/8 PASS** — the block is there |
| the same script against **this branch** | **1/8** — every product case reports `block=false`; the one pass is the accessory that must render nothing |
| `r23-disclosure-collateral.mjs`, one product per template | **5/5** — block absent on the branch, present on MAIN, and the rest of the visible text byte-identical |

All three templates in use are covered: default (`cal-flame-costa-bbq-island`,
`scandia-electric-heater-6kw`), Bundle (`dynamic-cold-therapy-pvc-barrel-cold-plunge`,
`ct-georgian-cabin-sauna`) and wider-images (`saunalife-g3`).

## ⚠️ What publishing this removes — the electrical exposure

Measured 2026-09-25 across 345 ACTIVE unit products. Full list:
**`docs/r23-electrical-exposure.csv`** (179 rows, tracked in the repo so it travels with the change).

| Group | Count | What is lost |
|---|---|---|
| **voltage stated ONLY in the block** | **50** | these products publish a supply voltage that appears **nowhere else on their page** |
| combustion — "needs a flue" | 86 | their only statement that no electrical supply is needed |
| nothing published — "ask us" | 40 | their only statement that we do not publish a requirement |
| kW published, no voltage | 3 | their only statement of rated power in this context |

**50 lose their only voltage statement. 129 more lose their only statement of electrical need.**
The client's ruling is that electrical will be stated elsewhere; until it is, that is a real gap and
this note is the record of it.

## Rollback

Re-add the one render line to each file, or push the pre-edit copies. The branch is unpublished, so
nothing is live until someone publishes it.
