/* Round 15 — build the theme files locally. No writes to Shopify; theme-push does that.
 *   node scripts/apply/build-round15-theme.mjs
 *
 * Every edit asserts EXACTLY ONE match. A target matching zero is a FAILURE, not a skip.
 *
 * TWO ENUMERATION FINDINGS changed the scope of this build, both in the direction of MORE files:
 *
 *  1. THREE sections emit the Product node, not one — main-product, bundle-product and
 *     main-product-layout-2. 84 ACTIVE products sit on product.Bundle.json. Editing only
 *     main-product.liquid would have shipped aggregateRating to 396 products and missed 84.
 *     That is the Round 9 template-partition failure exactly.
 *
 *  2. image-with-text-overlay renders on index.json AND page.featuredexperts.json. That page
 *     already has an H1 from page-default. An unguarded h2->h1 promotion would ship TWO H1s to a
 *     live page. The promotion is therefore guarded to index, mirroring snippets/logo.liquid.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.cwd().endsWith('/theme') ? '..' : '.');
const T = (f) => path.join(ROOT, 'theme', f);
let failures = 0;
const touched = new Set();

/* IDEMPOTENCY GUARD — added after this script bit me.
 *
 * theme/ is gitignored, so `git checkout -- theme/` exits non-zero and reverts NOTHING. I read a
 * failed revert as a successful one and re-ran the build over already-built files. Twelve edits
 * correctly refused (their anchors were gone) but ONE did not: the shop-level aggregateRating
 * insert re-emits its own anchor `"sameAs": [`, so it matched a second time and inserted a SECOND
 * aggregateRating block into layout/theme.liquid — a duplicate key in a live JSON-LD node.
 *
 * "Every apply script is idempotent. Running it twice changes nothing the second time" is a repo
 * convention and this script broke it. A refusal is the honest second-run behaviour; a silent
 * second insert is not. Restore the baseline with:
 *   node scripts/apply/theme-pull.mjs 146290704451 <files…>
 */
const MARKERS = [
  ['layout/theme.liquid', 'all_reviews_count'],
  ['snippets/Bundle.liquid', 'stroke-linejoin'],
  ['sections/main-product.liquid', '"aggregateRating"'],
];
const dirty = MARKERS.filter(([f, m]) => fs.readFileSync(T(f), 'utf8').includes(m));
if (dirty.length) {
  console.log('  REFUSING — Round 15 markers already present, so this is a second run:');
  dirty.forEach(([f, m]) => console.log(`    ${f} already contains ${JSON.stringify(m)}`));
  console.log('  Restore from MAIN first: node scripts/apply/theme-pull.mjs 146290704451 <files…>');
  process.exit(1);
}

function once(file, from, to, label) {
  const p = T(file);
  const s = fs.readFileSync(p, 'utf8');
  const n = s.split(from).length - 1;
  const ok = n === 1;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${n}×  ${file.padEnd(42)} ${label}`);
  if (!ok) { failures++; return; }
  fs.writeFileSync(p, s.replace(from, to));
  touched.add(file);
}

/* ────────────────────────────── ITEM 1a — product aggregateRating ────────────────────────────── */
const BRAND_ANCHOR = `      "brand": {
        "@type": "Brand",
        "name": {{ product.vendor | json }}
      },
      "offers": [`;

/* Guarded so the 424 zero-review products emit NO aggregateRating key at all — not a zero, not an
 * empty object. The theme has never read these metafields, so the accessor is written defensively:
 * .value.rating for a rating-type metafield, falling back to .value if it is a plain number. */
const AGG = `      "brand": {
        "@type": "Brand",
        "name": {{ product.vendor | json }}
      },
      {%- liquid
        assign jm_mf = product.metafields.reviews.rating
        assign jm_count = product.metafields.reviews.rating_count.value | plus: 0
        assign jm_value = jm_mf.value.rating | default: jm_mf.value
        assign jm_best = jm_mf.value.scale_max | default: 5
        assign jm_worst = jm_mf.value.scale_min | default: 1
      -%}
      {%- if jm_count > 0 and jm_value != blank %}
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": {{ jm_value }},
        "bestRating": {{ jm_best }},
        "worstRating": {{ jm_worst }},
        "reviewCount": {{ jm_count }}
      },
      {%- endif %}
      "offers": [`;

console.log('ITEM 1a — aggregateRating inside the EXISTING Product node, all three emitters');
for (const f of ['sections/main-product.liquid', 'sections/bundle-product.liquid', 'sections/main-product-layout-2.liquid']) {
  once(f, BRAND_ANCHOR, AGG, 'guarded aggregateRating');
}

/* ────────────────────────── ITEM 1b + 2 — Organization node on the homepage ────────────────────── */
console.log('\nITEM 1b + 2 — Organization: telephone, and shop-level aggregateRating');
once('layout/theme.liquid',
  `          "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": "support@inhousewellness.com"
          },`,
  `          "telephone": "+1-512-559-8860",
          "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": "support@inhousewellness.com",
            "telephone": "+1-512-559-8860"
          },`,
  'telephone on Organization and ContactPoint');

once('layout/theme.liquid',
  `          "sameAs": [`,
  `          {%- liquid
            assign shop_rating = shop.metafields.judgeme.all_reviews_rating.value | plus: 0.0
            assign shop_reviews = shop.metafields.judgeme.all_reviews_count.value | plus: 0
          -%}
          {%- if shop_reviews > 0 and shop_rating > 0 %}
          "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": {{ shop_rating }},
            "bestRating": 5,
            "worstRating": 1,
            "reviewCount": {{ shop_reviews }}
          },
          {%- endif %}
          "sameAs": [`,
  'shop-level aggregateRating, sourced dynamically');

/* The Round 14 comment says telephone was "omitted, not guessed". It is confirmed now. */
once('layout/theme.liquid',
  `      Fields NOT confirmed are omitted, not guessed: telephone, founder, foundingDate.`,
  `      Fields NOT confirmed are omitted, not guessed: founder, foundingDate.
      Round 15: telephone confirmed from the footer and added. aggregateRating is sourced from
      shop.metafields.judgeme.all_reviews_rating / all_reviews_count — never hardcoded, so it
      cannot go stale.`,
  'comment updated to match reality');

/* ─────────────────────────────── ITEM 3 — the homepage H1 ─────────────────────────────── */
console.log('\nITEM 3 — H1: logo demoted on index only, hero promoted on index only');
once('snippets/logo.liquid',
  `{% if request.page_type == 'index' %}
  <h1 class="my-0 inline-flex align-center">
{%- endif -%}`,
  `{% if request.page_type == 'index' %}
  <div class="my-0 inline-flex align-center">
{%- endif -%}`,
  'logo h1 -> div (opening)');

once('snippets/logo.liquid',
  `{% if request.page_type == 'index' %}
  </h1>
{%- endif -%}`,
  `{% if request.page_type == 'index' %}
  </div>
{%- endif -%}`,
  'logo h1 -> div (closing)');

/* GUARDED to index. This section also renders on page.featuredexperts, which already has an H1
 * from page-default — an unguarded promotion would put two H1s on that page. */
once('sections/image-with-text-overlay.liquid',
  `              {%- when 'heading' -%}
                <h2
                  class="sec__content-heading {{ anim_class }} heading-letter-spacing mt-0 {{ mb_custom }} {{ uppercase }} {{ fs_custom }} {{ font_weight }}"
                  style="font-size:{{ fs }}px;--space-bottom:{{ sb }};"
                  {{ block.shopify_attributes }}
                >
                  {{- block_st.heading -}}
                </h2>`,
  `              {%- when 'heading' -%}
                {%- comment -%}
                  Round 15: this is the homepage H1. Promoted on index ONLY — the same section
                  renders on page.featuredexperts, which already has an H1 from page-default,
                  so an unguarded promotion would put two H1s on that page.
                {%- endcomment -%}
                {%- if request.page_type == 'index' -%}
                <h1
                  class="sec__content-heading {{ anim_class }} heading-letter-spacing mt-0 {{ mb_custom }} {{ uppercase }} {{ fs_custom }} {{ font_weight }}"
                  style="font-size:{{ fs }}px;--space-bottom:{{ sb }};"
                  {{ block.shopify_attributes }}
                >
                  {{- block_st.heading -}}
                </h1>
                {%- else -%}
                <h2
                  class="sec__content-heading {{ anim_class }} heading-letter-spacing mt-0 {{ mb_custom }} {{ uppercase }} {{ fs_custom }} {{ font_weight }}"
                  style="font-size:{{ fs }}px;--space-bottom:{{ sb }};"
                  {{ block.shopify_attributes }}
                >
                  {{- block_st.heading -}}
                </h2>
                {%- endif -%}`,
  'hero h2 -> h1, index only');

/* ─────────────────── ITEM 4 — the redundant mobile-navigation-bar call ─────────────────── */
console.log('\nITEM 4 — remove the redundant direct section call');
once('layout/theme.liquid',
  `      sections 'overlay-group'
      section 'mobile-navigation-bar'
      section 'product-quickview'`,
  /* Inside a {%- liquid -%} block, tags are BARE and comments use a leading #.
   * A {%- comment -%} block here is a Liquid syntax error, and Shopify refused the file:
   *   "Liquid syntax error (line 459): Unknown tag '      {%- comment '"
   * The push failing is the correct outcome — the API rejected broken Liquid rather than
   * accepting it, which is exactly why every file is verified rather than assumed. */
  `      sections 'overlay-group'
      # Round 15: the direct "section 'mobile-navigation-bar'" call was removed here. That section
      # declares enabled_on groups ["custom.overlay"], so invoking it outside the group rendered
      # "Failed to render section ... does not support the 'index' template type" into the HTML.
      # overlay-group above already renders it and is called unconditionally on every template,
      # so nothing is lost.
      section 'product-quickview'`,
  'delete the direct call, keep the group');

/* ─────────────────────── FONT AWESOME — Bundle is NOT dead: 84 ACTIVE ─────────────────────── */
console.log('\nFONT AWESOME — inline the two icons, then drop the stylesheet');
once('snippets/Bundle.liquid',
  `<i class="fa fa-search-plus" aria-hidden="true"></i>`,
  `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>`,
  'fa-search-plus -> inline SVG');

once('snippets/Bundle.liquid',
  `<i class="fa fa-check" aria-hidden="true"></i>`,
  `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
  'fa-check -> inline SVG');

once('layout/theme.liquid',
  `    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css">\n`,
  '',
  'remove the render-blocking Font Awesome link');

/* ─────────────────────────────────────── report ─────────────────────────────────────── */
console.log(`\n  files changed: ${touched.size}`);
[...touched].sort().forEach((f) => console.log(`    ${f}`));
if (failures) { console.log(`\n  REFUSING — ${failures} target(s) did not match exactly once. Nothing is safe to push.`); process.exit(1); }

/* re-scan the OUTCOME, not the write */
console.log('\n  post-build verification:');
const themeLiquid = fs.readFileSync(T('layout/theme.liquid'), 'utf8');
const checks = [
  ['layout/theme.liquid', 'font-awesome link gone', !/cdnjs\.cloudflare\.com\/ajax\/libs\/font-awesome/.test(themeLiquid)],
  /* NARROWED, not widened: the first version of this check matched the explanatory COMMENT that
   * replaced the call and reported a failure on correct output. A Liquid call sits alone on its
   * own line inside the {%- liquid -%} block; prose does not. */
  ['layout/theme.liquid', 'direct nav-bar call gone', !/^\s*section 'mobile-navigation-bar'\s*$/m.test(themeLiquid)],
  ['layout/theme.liquid', 'nav-bar named once, in the comment only', (themeLiquid.match(/mobile-navigation-bar/g) || []).length === 1],
  ['layout/theme.liquid', 'overlay-group still called', /sections 'overlay-group'/.test(themeLiquid)],
  ['layout/theme.liquid', 'telephone ×2', (themeLiquid.match(/\+1-512-559-8860/g) || []).length === 2],
  ['layout/theme.liquid', 'shop aggregateRating present', /all_reviews_count/.test(themeLiquid)],
  ['snippets/logo.liquid', 'no <h1 in logo', !/<h1/.test(fs.readFileSync(T('snippets/logo.liquid'), 'utf8'))],
  ['snippets/Bundle.liquid', 'no fa- classes left', !/class="fa fa-/.test(fs.readFileSync(T('snippets/Bundle.liquid'), 'utf8'))],
];
for (const f of ['sections/main-product.liquid', 'sections/bundle-product.liquid', 'sections/main-product-layout-2.liquid']) {
  const s = fs.readFileSync(T(f), 'utf8');
  checks.push([f, 'exactly one aggregateRating', (s.match(/"aggregateRating"/g) || []).length === 1]);
  checks.push([f, 'exactly one Product node', (s.match(/"@type": "Product"/g) || []).length === 1]);
}
let bad = 0;
for (const [f, label, pass] of checks) { console.log(`    ${pass ? 'ok  ' : 'FAIL'} ${f.padEnd(42)} ${label}`); if (!pass) bad++; }
console.log(bad ? `\n  ${bad} verification(s) FAILED` : '\n  all post-build checks passed');
process.exitCode = bad ? 1 : 0;
