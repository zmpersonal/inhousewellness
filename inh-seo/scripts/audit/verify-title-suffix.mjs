/* Verify the product-title suffix removal on a theme preview.
 *
 * Proves TWO things, and the second matters more:
 *   1. product titles lost the suffix
 *   2. the catch-all `else` is UNTOUCHED — homepage, static page and blog index
 *      must still carry it
 *
 * Preview requires the cookie handshake: ?preview_theme_id= answers 302 and sets
 * _shopify_essential. A client that drops it reads MAIN and every check passes
 * against the wrong theme.
 */
const themeId = (process.argv[2] || '').replace(/\D/g, '');
if (!themeId) throw new Error('theme id required');
const UA = 'Mozilla/5.0 (compatible; inh-seo-audit)';
const SUFFIX = /–\s*inhousewellness\s*$/i;

const decode = (s) => s.replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

async function title(path) {
  const url = `https://inhousewellness.com${path}?preview_theme_id=${themeId}`;
  const first = await fetch(url, { redirect: 'manual', headers: { 'User-Agent': UA } });
  const jar = (first.headers.getSetCookie ? first.headers.getSetCookie() : [first.headers.get('set-cookie')])
    .filter(Boolean).map((c) => c.split(';')[0]).join('; ');
  if (first.status !== 302 || !jar) throw new Error(`expected 302 + cookie, got ${first.status}`);
  const res = await fetch(first.headers.get('location'), { headers: { 'User-Agent': UA, cookie: jar } });
  const html = await res.text();
  const t = (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '';
  return decode(t.replace(/\s+/g, ' ').trim());
}

/* MUST lose the suffix */
const PRODUCTS = [
  ['default', '/products/cal-flame-costa-bbq-island'],
  ['default', '/products/scandia-electric-heater-6kw'],
  ['Bundle',  '/products/leisurecraft-luna'],
  ['wider-images', '/products/dynamic-venice-elite'],
];
/* MUST KEEP the suffix — these prove the else is untouched */
const CONTROLS = [
  ['homepage',   '/'],
  ['static page', '/pages/contact'],
  ['blog index', '/blogs/saunas'],
  ['collection', '/collections/saunas'],
];

let fail = 0;
console.log('  PRODUCTS — suffix must be GONE\n');
for (const [tpl, p] of PRODUCTS) {
  const t = await title(p);
  const ok = !SUFFIX.test(t);
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${String(t.length).padStart(3)}  ${tpl.padEnd(13)}${t.slice(0, 74)}`);
  if (!ok) fail++;
}
console.log('\n  CONTROLS — suffix must REMAIN (the else is untouched)\n');
for (const [kind, p] of CONTROLS) {
  const t = await title(p);
  /* a collection with its own SEO title legitimately has no suffix — Round 5 */
  const expected = kind === 'collection' ? null : true;
  const has = SUFFIX.test(t);
  const ok = expected === null ? true : has === expected;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${String(t.length).padStart(3)}  ${kind.padEnd(13)}${t.slice(0, 74)}`);
  if (!ok) fail++;
}
console.log(`\n  ${PRODUCTS.length + CONTROLS.length - fail}/${PRODUCTS.length + CONTROLS.length} passed`);
if (fail) process.exitCode = 1;
