/* Differential verifier. A preview URL answers 302 + sets _shopify_essential; a client that drops
 * that cookie is served MAIN at the URL you asked for, with status 200 — a false pass
 * indistinguishable from a real one. So: demand the 302 AND the cookie, or refuse. */

const THEME = process.argv[2];
const UA = { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36' };

async function fetchPreview(pathname) {
  const url = `https://inhousewellness.com${pathname}${pathname.includes('?') ? '&' : '?'}preview_theme_id=${THEME}`;
  const r1 = await fetch(url, { headers: UA, redirect: 'manual' });
  const setCookie = r1.headers.getSetCookie?.().join('; ') || r1.headers.get('set-cookie') || '';
  if (r1.status !== 302 || !/_shopify_essential/.test(setCookie)) {
    throw new Error(`preview handshake failed for ${pathname}: status ${r1.status}, cookie ${/_shopify_essential/.test(setCookie)}`);
  }
  const cookie = setCookie.split(',').map(s => s.trim().split(';')[0]).filter(Boolean).join('; ');
  const loc = r1.headers.get('location');
  const r2 = await fetch(loc.startsWith('http') ? loc : `https://inhousewellness.com${loc}`, { headers: { ...UA, cookie } });
  return await r2.text();
}

const CASES = [
  ['/', 'HOMEPAGE', [
    ['exactly one <h1>', (h) => (h.match(/<h1[\s>]/g) || []).length === 1],
    ['the h1 is the hero copy', (h) => /<h1[^>]*>\s*Build the Wellness Space/.test(h)],
    ['logo is no longer an h1', (h) => !/<h1 class="my-0 inline-flex/.test(h)],
    ['Organization telephone', (h) => /"telephone": "\+1-512-559-8860"/.test(h)],
    ['Organization aggregateRating', (h) => /"aggregateRating"/.test(h)],
    ['rating 4.82', (h) => /"ratingValue": 4\.82/.test(h)],
    ['reviewCount 1431', (h) => /"reviewCount": 1431/.test(h)],
    ['nav-bar render error GONE', (h) => !/Failed to render section 'mobile-navigation-bar'/.test(h)],
    ['font-awesome link gone', (h) => !/cdnjs\.cloudflare\.com\/ajax\/libs\/font-awesome/.test(h)],
  ]],
  ['/products/maxxus-mx-s106-01', 'PRODUCT (default template, 15 reviews)', [
    ['aggregateRating in served HTML', (h) => /"aggregateRating"/.test(h)],
    ['exactly ONE Product node', (h) => (h.match(/"@type": "Product"/g) || []).length === 1],
    ['ratingValue 4.93', (h) => /"ratingValue": 4\.93/.test(h)],
    ['reviewCount 15', (h) => /"reviewCount": 15/.test(h)],
    ['exactly one <h1>', (h) => (h.match(/<h1[\s>]/g) || []).length === 1],
  ]],
  ['/products/huum-hive-12', 'PRODUCT (Bundle template — the 84 nobody would have checked)', [
    ['page renders', (h) => h.length > 50000],
    ['exactly ONE Product node', (h) => (h.match(/"@type": "Product"/g) || []).length === 1],
    ['no fa- icon classes', (h) => !/class="fa fa-/.test(h)],
  ]],
  /* The handle is featured-experts-consultants, NOT featuredexperts. I derived the URL from the
   * TEMPLATE name and got a 404 with 0 h1s, which read as a regression. A handle comes from the
   * data: pages(first:250){ handle templateSuffix }. Same family as the huum-hive slug guess. */
  ['/pages/featured-experts-consultants', 'PAGE on the featuredexperts template (the two-H1 risk)', [
    /* This page has h1=0 on MAIN *and* on this branch — pre-existing, not a Round 15 regression.
     * Asserting ===1 tested a baseline that never existed. The claim that matters here is the
     * differential: the hero did not become a second h1. Logged for a later round. */
    ['h1 count unchanged from MAIN (0)', (h) => (h.match(/<h1[\s>]/g) || []).length === 0],
    ['hero stayed an h2 here', (h) => /<h2[^>]*>\s*Meet our Experts/.test(h)],
  ]],
];

let bad = 0;
for (const [p, label, checks] of CASES) {
  console.log(`\n  ${label}   ${p}`);
  let html;
  try { html = await fetchPreview(p); } catch (e) { console.log(`    UNREACHABLE — ${e.message}`); bad++; continue; }
  for (const [name, fn] of checks) {
    let pass = false; try { pass = fn(html); } catch {}
    console.log(`    ${pass ? 'ok  ' : 'FAIL'} ${name}`);
    if (!pass) bad++;
  }
}
console.log(bad ? `\n  ${bad} CHECK(S) FAILED` : '\n  all preview checks passed');
process.exitCode = bad ? 1 : 0;
