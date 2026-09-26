> **Automation-mode notes (supersede the matching parts below).** This spec was written for the manual "paste into Shopify" workflow. In the blog engine:
> - §1 paste instructions and the header comment block are **not** emitted. Title, handle, SEO title, meta description, excerpt, tags, author, image and publish date are set through the Admin API (BLUEPRINT §4.13).
> - §5 JSON-LD is **not** inlined in the body. It is written to the article metafield `custom.jsonld` and printed by a theme snippet (BLUEPRINT §4.8). The body contains no `<script>`.
> - BreadcrumbList uses the routed blog (`config/routing.yaml`), not a hardcoded "Saunas".
> - §8 "web_fetch" means the pipeline's own HTTP fetcher; product and collection facts come from the Shopify Admin API site index, not page scraping.
> - Article types in v1: informational guide, best-X roundup, comparison. Competitor reviews (§9) are v1.1.
> - This file is governance: the machine never edits it. Changes go through a retro proposal.

# InHouse Wellness — SEO Blog House Style (shared reference)

This is the shared spec both SEO blog skills follow. Read it fully before writing any HTML.

## Table of contents
1. Output format & delivery
2. Link-formatting rules (non-negotiable)
3. Brand facts (reuse verbatim)
4. Luxury palette (scoped CSS)
5. Required schema (JSON-LD)
6. Section toolkit
7. Honesty & YMYL rules
8. Verification workflow
9. Commercial steering
10. HTML skeleton

---

## 1. Output format & delivery
- The deliverable is **one paste-ready HTML file** the user drops into Shopify's **"Show HTML" / `<>` code view** (NOT the rich-text editor). Save it to `/mnt/user-data/outputs/<slug>.html` and share with `present_files`.
- Start the file with an HTML comment block that tells the user exactly what to do in Shopify:
  - **Blog post TITLE** (this becomes the `<h1>` — do not also put an `<h1>` in the body)
  - **SEO title** (≤ ~60 chars, lead with the primary keyword)
  - **Meta description** (~150 chars, useful and accurate)
  - "Paste in the code view", **"Keep the existing URL"**, and a "pricing/specs checked: <Month Year>" note.
- Never put an `<h1>` in the body — Shopify renders the post title as the H1. Body starts at `<h2>`.

## 2. Link-formatting rules (non-negotiable)
- **Table-of-contents anchor links** → native `#anchors`, **same window** (no `target`). Give each linked section a matching `id`.
- **Internal `inhousewellness.com` links** → `target="_blank" rel="noopener"` + **descriptive, SEO-friendly anchor text** (e.g. "Golden Designs St. Moritz 2-person barrel sauna", never "click here" or a raw URL).
- **External links** → `target="_blank" rel="nofollow noopener"` + descriptive anchor text.
- Never print a raw URL as anchor text; never leave a doubled-URL rendering.

## 3. Brand facts (reuse verbatim)
- Publisher: **InHouse Wellness** — Austin, TX (5900 Balcones Drive #20752, Austin, TX 78731). Phone +1 (512) 559-8860. Since 2011. Authorized dealer; free shipping; white-glove available; price-match.
- Logo (for `publisher.logo` in schema): `https://inhousewellness.com/cdn/shop/files/logo_906767b2-2e20-4d0b-af64-005ed2b9a423.png?v=1770888564`
- Brands carried: Finnmark Designs, Golden Designs, Dynamic Saunas, Maxxus, SaunaLife, LeisureCraft, Scandia, Dundalk, Dreampod, Icetubs, Harvia, HUUM, Narvi, ThermaSol, Mr. Steam, Delta, Helios.
- Blog roots for cross-links: `/blogs/saunas`, `/blogs/cold-plunge`, `/blogs/wellness`, `/blogs/fire`, `/blogs/institute`.
- Common collection URLs (verify before relying): `/collections/saunas`, `/collections/infrared-saunas`, `/collections/barrel-saunas`, `/collections/cold-plunge`, `/collections/steam-showers`, `/collections/low-emf`, `/collections/ultra-low-emf`, `/collections/near-zero-emf`, `/collections/full-spectrum`, `/collections/red-light-therapy` (**saunas WITH red light**), `/collections/red-light-therapy-panel-skin-pain-recovery` (**standalone panels**), `/collections/sauna-heaters`, `/collections/sauna-accessories`, `/collections/dynamic-saunas`. A 2-person infrared filter URL that works: `/collections/saunas?filter.p.m.custom.capacity_=2+Person&filter.p.m.custom.style=Infrared`.

## 4. Luxury palette (scoped CSS)
Scope every rule with a **unique class prefix per article** (e.g. `.rlt-`, `.ab-`, `.ds-`) so styles never collide site-wide. Use the espresso/cream/gold system:
- Espresso (headers, avatar, table `th`): `#6b4a2b`
- Deep espresso (CTA background): `#4a3524`; CTA link text champagne `#e9d9bf`
- Cream backgrounds: `#faf7f2` and `#fbf9f5`; borders `#e4dccf`
- Gold accent (callout left border): `#b0894f`
- Even table rows: `#faf7f2`; recommended-cell highlight: `#eef7ee`
- Do NOT use purple/blue accent themes — they read cheap next to the catalog.

## 5. Required schema (JSON-LD)
Emit these `<script type="application/ld+json">` blocks at the top of the file:
- **Article** — headline, description, author, `publisher` (name + logo above), `datePublished`, `dateModified` (today), `mainEntityOfPage` = the live post URL.
- **BreadcrumbList** — Home → Saunas (`/blogs/saunas`) → this post.
- **FAQPage** — mirror the on-page FAQ exactly (plain-text answers, no markup). 8–12 Q&As, favor long-tail buyer questions.
- **Review** — ONLY when the article carries a visible editorial rating. `itemReviewed` = the product/line, `reviewRating` on a 10-point scale, author/publisher = InHouse Wellness.
Keep JSON answers plain (no `"` inside values that break JSON; write "5'10" as "5 foot 10", etc.).

## 6. Section toolkit (pick what the article needs)
- **Snippet-optimized lede** — a direct 40–60 word answer to the core query in the first paragraph.
- **Verdict / TL;DR box** — bordered, near the top; for reviews use "what we like / what gives us pause / recommendation + CTA".
- **Editorial ratings box** — sub-scores + overall on /10, always labeled "InHouse Wellness editorial opinion, not a lab measurement."
- **E-E-A-T author box** — byline + an explicit **"How we reviewed it / how we evaluated it"** line stating sources used and **what was NOT independently tested**.
- **TOC** — native anchors, same-window (see §2).
- **Comparison tables** — verified specs only; highlight the recommended column/cell.
- **Decision matrix** — "Buy if… / Consider something else if…" (green/red cards).
- **Safety section** — compact, caveated (see §7).
- **FAQ** — mirrored 1:1 in FAQPage schema.
- **Sources** — external, `nofollow noopener`, descriptive text; prefer primary/clinical/manufacturer/gov over aggregators; one source per claim.
- **Images** — reuse the article's real Shopify CDN `<img>` URLs when available (with better alt text + `loading="lazy"`); otherwise leave an HTML comment placeholder with a descriptive filename + alt text. Never hotlink competitor images.

## 7. Honesty & YMYL rules
- **Never fabricate**: testing you didn't do, credentials, review counts, wavelengths/irradiance, or specs. If a value isn't verified, say so or omit it.
- State plainly what you **couldn't** verify; label all ratings as opinion.
- **Health topics**: keep claims evidence-based and caveated; avoid "detox" as a proven outcome; add a brief "not medical advice / see a clinician" note; for contraindications name conditions, not scare tactics.
- **Prices/stock change**: present volatile prices as ranges or "recently ~$X", add a dated "checked <Month Year>" note, and tell readers to confirm on the live page.
- **Flag site errors** you find (e.g. a product title that mislabels the wood/features, a collection link that points at the wrong thing) so the user can fix them.

## 8. Verification workflow
- Fetch InHouse product/collection pages with `web_fetch` to get **real names, prices, model numbers, dimensions, EMF/wavelength, warranty**. The `og:price` and title sit at the very top of the markdown; full spec sections sit near the bottom (pages return large nav menus — scan past them).
- **Costco product pages block `web_fetch`** (bot detection) — use `web_search` snippets or a third-party tracker instead, and cite cautiously.
- Cross-check any manufacturer/critique claim against the live page before repeating it. When a critique and the live catalog disagree, the live catalog wins.

## 9. Commercial steering (competitor reviews)
- Stay genuinely useful and fair to the competitor product — that credibility is what converts.
- Frame the upsell as **"X is good/cheap for the money — here's what spending more buys you,"** never trashing the competitor.
- Route to **real, verified InHouse products/collections** by buyer need (value / closest upgrade / more room / premium). Steer AWAY from the competitor SKU without dishonesty.
- For products InHouse can't match (cheap/portable/steam tents), offer the honest adjacent upgrade paths (e.g. entry infrared cabin for the "heat" crowd; permanent steam shower for the "steam" crowd) plus a "shop all" link.

## 10. HTML skeleton
Use this order; delete unused blocks. Replace `PFX` with the article's unique class prefix.

```html
<!-- ============ <ARTICLE NAME> — paste into Shopify "Show HTML" / <> ============
     KEEP EXISTING URL: /blogs/saunas/<slug>
     Shopify TITLE (H1): ...
     SEO title: ...
     Meta description: ...
     Prices/specs checked: <Month Year>
     ============================================================================ -->

<script type="application/ld+json"> { "@context":"https://schema.org","@type":"Article", ... } </script>
<script type="application/ld+json"> { "@context":"https://schema.org","@type":"BreadcrumbList", ... } </script>
<script type="application/ld+json"> { "@context":"https://schema.org","@type":"FAQPage", ... } </script>
<!-- Review block ONLY if a visible rating exists -->

<style>
.PFX-article{max-width:820px;margin:0 auto;line-height:1.65;}
.PFX-article h2{margin-top:2.2em;scroll-margin-top:90px;}
.PFX-verdict{border:2px solid #6b4a2b;border-radius:10px;padding:1.3em 1.5em;margin:1.6em 0;background:#faf7f2;}
.PFX-callout{background:#faf7f2;border-left:4px solid #b0894f;padding:1em 1.2em;border-radius:6px;margin:1.4em 0;}
.PFX-cta{background:#4a3524;color:#fff;border-radius:10px;padding:1.25em 1.5em;margin:1.7em 0;text-align:center;}
.PFX-cta a{color:#e9d9bf;text-decoration:underline;font-weight:600;}
.PFX-author{display:flex;gap:1em;background:#faf7f2;border:1px solid #e4dccf;border-radius:8px;padding:1em 1.3em;margin:1.4em 0;}
.PFX-author .PFX-avatar{flex:0 0 56px;height:56px;width:56px;border-radius:50%;background:#6b4a2b;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;}
.PFX-toc{background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;padding:1.1em 1.4em 1.1em 2.4em;margin:1.6em 0;}
.PFX-article table{width:100%;border-collapse:collapse;margin:1.4em 0;font-size:.92em;}
.PFX-article th,.PFX-article td{border:1px solid #e4dccf;padding:.55em .7em;text-align:left;vertical-align:top;}
.PFX-article th{background:#6b4a2b;color:#fff;}
.PFX-article tbody tr:nth-child(even){background:#faf7f2;}
.PFX-pick{background:#eef7ee !important;font-weight:600;}
.PFX-sources li{margin:.5em 0;font-size:.92em;}
</style>

<div class="PFX-article">
  <p class="PFX-lede">…direct 40–60 word answer…</p>
  <!-- Verdict / TL;DR box -->
  <!-- CTA(s) to real InHouse collections/products -->
  <!-- E-E-A-T author box with "How we reviewed it" -->
  <!-- TOC (native #anchors, same window) -->
  <hr>
  <!-- H2 sections: what-is / comparison table / specs / performance / owners / pros-cons /
       alternatives / decision matrix / safety / FAQ / sources -->
  <p style="font-size:.9em;color:#666;"><em>Specs & pricing reflect listings as of <Month Year> and change; verify before purchase. Ratings are editorial opinion. Not medical advice.</em></p>
</div>
```
