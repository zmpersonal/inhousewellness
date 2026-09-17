
## DEFERRED — jQuery is render-blocking and stays that way (Round 15, deliberate)

`layout/theme.liquid` loads jQuery 3.7.1 synchronously from ajax.googleapis.com. It was **left
alone on purpose**; this is not an oversight for a future round to rediscover.

**Four consumers, found by grep:**

| file | why it matters |
|---|---|
| `assets/custom-mega-menu.js` | site-wide navigation |
| `assets/affirmShopify.js` | **payment widget** |
| `snippets/Bundle.liquid` | **84 ACTIVE products** on `product.Bundle.json` |
| `sections/custom-Faq.liquid` | FAQ accordions |

**Adding `defer` requires converting every parse-time binding in those four to `DOMContentLoaded`,
then regression-testing the mega menu, cart drawer, product sliders and Affirm.** The client's
ruling stands: not worth risking navigation and payments for a render-blocking nit.

**If a future round takes it on**, do those four files first and test Affirm on a real product page
before touching the script tag.
