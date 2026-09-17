/* Round 14 theme branch — BUILD ONLY. Writes edited files into theme/ from a fresh
 * snapshot of MAIN. Pushing is theme-branch.mjs, which diffs against MAIN again.
 *
 *   node scripts/apply/build-round14-theme.mjs <main-snapshot-dir>
 *
 * Every string edit asserts EXACTLY ONE match. A zero or a two is a failure.
 * Escaping edits are positional, from scan(), and the result is re-scanned.
 *
 * Scope (client ruling, 15 Sep 2026) — nothing else:
 *   #1 quote escaping   #4 category card alts   #7 dead second slider copy
 *   #8 copyright year   #9 og:image https       #10 title newlines
 *   Organization node on the homepage
 */
import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from '../lib/util.js';
import { scan, dataAxis } from '../audit/attr-escape-scan.mjs';

const MAIN = process.argv[2];
if (!MAIN || !fs.existsSync(path.join(MAIN, 'layout/theme.liquid'))) throw new Error('main snapshot dir required');

const out = new Map();                       // filename -> edited source
const get = (f) => out.get(f) ?? fs.readFileSync(path.join(MAIN, f), 'utf8');
const log = [];

function once(f, from, to, label) {
  const s = get(f);
  const n = s.split(from).length - 1;
  if (n !== 1) throw new Error(`${label}: expected 1 match in ${f}, got ${n}`);
  out.set(f, s.replace(from, () => to));
  log.push(`  ${label.padEnd(26)} ${f}  1 match`);
}

/* ── #1 escaping — positional, end to start ─────────────────────────────── */
const liquidFiles = [];
for (const sub of ['layout', 'sections', 'snippets', 'blocks', 'templates']) {
  const d = path.join(MAIN, sub);
  if (fs.existsSync(d)) for (const f of fs.readdirSync(d)) if (f.endsWith('.liquid')) liquidFiles.push(`${sub}/${f}`);
}
let escTotal = 0, rawBefore = 0;
const escByFile = {};
for (const f of liquidFiles) {
  const src = get(f);
  const all = scan(src);
  rawBefore += all.length;
  const hits = all.filter(dataAxis).sort((a, b) => b.exprStart - a.exprStart);
  if (!hits.length) continue;
  let s = src;
  for (const h of hits) {
    const seg = s.slice(h.exprStart, h.exprEnd);
    if (seg.trim() !== h.expr) throw new Error(`offset drift in ${f} L${h.line}`);
    const trail = seg.match(/\s*$/)[0];
    s = s.slice(0, h.exprStart) + seg.slice(0, seg.length - trail.length) + ' | escape_once' + trail + s.slice(h.exprEnd);
  }
  out.set(f, s);
  escByFile[f] = hits.length;
  escTotal += hits.length;
}
log.push(`  #1 escape_once added      ${escTotal} sites in ${Object.keys(escByFile).length} files`);

/* ── #4 category card alts ──────────────────────────────────────────────── */
once('sections/category-list.liquid',
  `alt="{{ block.settings.image.alt | default: section.settings.heading | escape }}"`,
  `alt="{{ block.settings.title | default: block.settings.image.alt | default: section.settings.heading | escape }}"`,
  '#4 category card alt');

/* ── #7 dead second slider copy ─────────────────────────────────────────── */
once('sections/header.liquid',
  `{% render 'categories-menu-mobile', collection_slider: section.settings.collection_slider %}\n`,
  `{%- comment -%}
  Round 14 #7. A second render of categories-menu-mobile stood here. The first
  copy renders inside horizontal-menu (its L1073), earlier in the DOM, with
  section_st. theme.js reaches the slider with document.querySelector, which
  returns the FIRST match only, so this copy was never used: 27,418 bytes of
  duplicate slider, an empty categories list (no section_st was passed), and a
  second Swiper init. Measured on the live homepage 15 Sep 2026.
{%- endcomment -%}\n`,
  '#7 remove second slider');

/* ── #8 copyright year ──────────────────────────────────────────────────── */
once('sections/footer.liquid',
  `<div class="footer__copyright">{{ section_st.copyright_text }}</div>`,
  `{%- comment -%}
                Round 14 #8. The editor setting reads "© 2024 InHouseWellness". A static
                edit goes stale again every January, so the year is substituted at
                render. Only the literal 2024 is replaced: if the setting is rewritten
                without it, this is a no-op and the editor text renders as typed.
              {%- endcomment -%}
              {%- assign current_year = 'now' | date: '%Y' -%}
              <div class="footer__copyright">{{ section_st.copyright_text | replace: '2024', current_year }}</div>`,
  '#8 copyright year');

/* ── #9 og:image https ──────────────────────────────────────────────────── */
once('snippets/meta-tags.liquid',
  `<meta property="og:image" content="http:{{ page_image | image_url }}">`,
  `<meta property="og:image" content="https:{{ page_image | image_url }}">`,
  '#9 og:image https');

/* ── #10 title newlines ─────────────────────────────────────────────────── */
once('layout/theme.liquid',
  `    <title>\n      {%- if collection -%}`,
  `    {%- comment -%}
      Round 14 #10. Every if/endif block in this chain left a newline in the
      rendered <title> — homepage "…Tubs\\n\\n – inhousewellness\\n", collection
      "…Filled\\n\\n\\n" — on EVERY branch, predating Round 12. Google collapses
      whitespace, so this was cosmetic; the measured decoded lengths do not change.

      The chain is captured and whitespace is collapsed ONCE at output. split: ' '
      is Ruby's awk-style split (any whitespace run, empties dropped), so the join
      is the same collapse the length measurement applies. No branch logic changed.
    {%- endcomment -%}
    {%- capture title_tag_text -%}
      {%- if collection -%}`,
  '#10 title capture open');
once('layout/theme.liquid',
  `      {%- endif -%}\n    </title>`,
  `      {%- endif -%}\n    {%- endcapture %}\n    <title>{{ title_tag_text | split: ' ' | join: ' ' }}</title>`,
  '#10 title capture close');

/* ── Organization node, homepage only ───────────────────────────────────── */
once('layout/theme.liquid',
  `    {% render 'structured-data-extras' %}\n`,
  `    {% render 'structured-data-extras' %}
    {%- comment -%}
      Round 14. Organization node, HOMEPAGE ONLY, tested positively on template.name
      (populated in the layout — the VideoObject block above relies on it).

      Every value is client-confirmed, 15 Sep 2026, and every URL was resolved
      before shipping:
        name / url / logo        the storefront and settings.logo
        contactPoint             support@ is the public contact (help@ is warranty claims only)
        address                  the business location. NOT a returns address, and nothing
                                 about returns belongs in markup. #20752 is the suite on every
                                 PUBLISHED page and on the Facebook page; #21140 survives only
                                 on four unpublished pages; the billing address is not public.
        sameAs                   Facebook page 61569426503966 in its canonical people/ form
                                 (the footer links the same page as profile.php?id=); the other
                                 four from the footer. YouTube is the channel, not its /shorts tab.
      Fields NOT confirmed are omitted, not guessed: telephone, founder, foundingDate.
    {%- endcomment -%}
    {%- if template.name == 'index' -%}
      <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "InHouse Wellness",
          "url": "{{ shop.url }}/",
          {%- if settings.logo != blank %}
          "logo": "https:{{ settings.logo | image_url: width: 600 }}",
          {%- endif %}
          "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": "support@inhousewellness.com"
          },
          "address": {
            "@type": "PostalAddress",
            "streetAddress": "5900 Balcones Drive #20752",
            "addressLocality": "Austin",
            "addressRegion": "TX",
            "postalCode": "78731",
            "addressCountry": "US"
          },
          "sameAs": [
            "https://www.facebook.com/people/InHouse-Wellness/61569426503966/",
            "https://www.instagram.com/inhouse.wellness/",
            "https://www.tiktok.com/@inhousewellness",
            "https://www.youtube.com/@InHouseWellness",
            "https://www.pinterest.com/inhousewellness/"
          ]
        }
      </script>
    {%- endif -%}
`,
  'Organization node');

/* ── Re-scan the OUTPUT, not the plan ───────────────────────────────────── */
let rawAfter = 0, axisAfter = 0;
for (const f of liquidFiles) {
  const h = scan(get(f));
  rawAfter += h.length;
  axisAfter += h.filter(dataAxis).length;
}
log.push(`  re-scan: data-axis unescaped ${axisAfter} (want 0); raw ${rawBefore} -> ${rawAfter} (want -${escTotal})`);
if (axisAfter !== 0 || rawBefore - rawAfter !== escTotal) throw new Error('re-scan failed');

/* ── Write ──────────────────────────────────────────────────────────────── */
for (const [f, s] of out) {
  const p = path.join(ROOT, 'theme', f);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, s);
}
console.log(log.join('\n'));
console.log(`\n  files written to theme/: ${out.size}`);
for (const [f, n] of Object.entries(escByFile).sort((a, b) => b[1] - a[1])) console.log(`     ${String(n).padStart(3)}  ${f}`);
fs.writeFileSync(path.join(ROOT, 'data', 'round14-theme-files.json'), JSON.stringify([...out.keys()].sort(), null, 1));
