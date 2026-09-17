## ⏳ TEMPORARY — SKIMLINKS VERIFICATION TAG. REMOVE IT. (Round 17, 17 Sep 2026)

**This tag is not meant to live on the site. It exists only so Skimlinks' signup crawler can
verify domain ownership, and it comes out the moment they confirm.**

| | |
|---|---|
| **Theme** | `146351784003` — "Round 17 — Skimlinks verification tag (TEMPORARY)", **UNPUBLISHED** |
| **File** | `layout/theme.liquid` |
| **Position** | immediately before the single `</body>`, at the end of the file (note: a Hyperspeed rewrite-log `{% comment %}` block sits AFTER `</html>` — leave it alone) |
| **REMOVAL TRIGGER** | **Skimlinks confirms verification.** Nothing else. Not a round boundary, not a theme republish. |

**Delete these three lines and nothing else:**

```
  <!-- SKIMLINKS VERIFICATION — TEMPORARY. Round 17. Remove once
       Skimlinks confirms verification. See HANDOFF.md. -->
  <script type="text/javascript" src="https://s.skimresources.com/js/309479X1797834.skimlinks.js"></script>
  <!-- END SKIMLINKS VERIFICATION -->
```

The markers are exact and unique — `grep -n "SKIMLINKS VERIFICATION" theme/layout/theme.liquid`
finds both ends. The em-dash in the opening marker is **U+2014**; match on `SKIMLINKS VERIFICATION`
rather than retyping the punctuation.

**It was deliberately NOT added to `avadaLightJsExclude` or any Hyperspeed override.** Deferral is
irrelevant to a verifier that reads raw HTML, and a permanent whitelist entry for a temporary tag is
residue that outlives its reason. `avadaLightJsExclude` does not appear in `layout/theme.liquid` at
all and this round did not introduce it.

**After removal:** re-run the curl handshake below and confirm the count is **0**.

```bash
curl -sS -c /tmp/j.txt -o /dev/null "https://inhousewellness.com/?preview_theme_id=<THEME>" && curl -sS -b /tmp/j.txt "https://inhousewellness.com/" | grep -c skimresources
```

⚠️ **A temporary tag with no removal note becomes permanent.** If you are reading this and Skimlinks
verification has already been confirmed, the removal is overdue — do it now rather than filing it.

---


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
