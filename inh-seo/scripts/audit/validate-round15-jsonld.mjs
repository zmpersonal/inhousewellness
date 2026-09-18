/* Structural validation of every ld+json block on each CHANGED template type, pre-JavaScript.
 * NOTE: this is NOT Google's Rich Results Test — that has no public API and I did not run it.
 * What this proves: the JSON parses, the node count is right, and the required AggregateRating
 * fields are present and in range. Google's own verdict still needs a human paste into the RRT. */
import { assertServedBy } from '../lib/theme-identity.mjs';
const THEME = process.argv[2];
if (!/^\d+$/.test(THEME || '')) throw new Error('theme id required');
const UA = { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36' };
async function raw(p) {
  const r1 = await fetch(`https://inhousewellness.com${p}?preview_theme_id=${THEME}`, { headers: UA, redirect: 'manual' });
  const sc = (r1.headers.getSetCookie?.() || []).join('; ');
  if (r1.status !== 302 || !/_shopify_essential/.test(sc)) throw new Error(`no preview handshake (${r1.status})`);
  const cookie = sc.split(',').map(s => s.trim().split(';')[0]).filter(Boolean).join('; ');
  const loc = r1.headers.get('location');
  const r2 = await fetch(loc.startsWith('http') ? loc : `https://inhousewellness.com${loc}`, { headers: { ...UA, cookie } });
  const html = await r2.text();
  // 18i: status and served-theme identity
  if (r2.status !== 200) throw new Error(`expected HTTP 200, got ${r2.status}`);
  assertServedBy(html, THEME, p);
  return html;
}
/* 18i: per-target EXPECTATIONS. The old gate was `products.length > 1` (0 Products passed) and
   `aggs.length && !aggOk` (a MISSING rating passed). Each target now states how many Product
   nodes it must carry and whether a rating must be present or absent. */
const TARGETS = [
  ['index',                 '/',                                         { products: 0, rating: true }],
  ['product (default)',     '/products/maxxus-mx-s106-01',               { products: 1, rating: true }],
  ['product (0 reviews)',   '/products/laguna-q-gpv3100-outdoor-island', { products: 1, rating: false }],
  /* huum-hive-12 is on the Bundle template but has ZERO reviews, so it only proves the guard.
   * ct-georgian-cabin-sauna is Bundle WITH a rating — it proves the Bundle path actually emits.
   * 32 of the 84 ACTIVE Bundle products carry a rating. */
  ['product.Bundle (0 rev)','/products/huum-hive-12',                    { products: 1, rating: false }],
  ['product.Bundle (rated)','/products/ct-georgian-cabin-sauna',           { products: 1, rating: true }],
  ['page (featuredexperts)','/pages/featured-experts-consultants',         { products: 0, rating: false }],
];
let bad = 0;
for (const [label, p, want] of TARGETS) {
  let html; try { html = await raw(p); } catch (e) { console.log(`FAIL  ${label}: ${/^WRONG THEME/.test(e.message) ? '' : 'UNREACHABLE — '}${e.message}`); bad++; continue; }
  const blocks = [...html.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1].trim());
  const parsed = [], errs = [];
  for (const b of blocks) { try { parsed.push(JSON.parse(b)); } catch (e) { errs.push(e.message.slice(0, 50)); } }
  const flat = parsed.flatMap((j) => Array.isArray(j) ? j : [j]);
  const products = flat.filter((n) => n['@type'] === 'Product');
  const aggs = flat.filter((n) => n.aggregateRating).map((n) => n.aggregateRating);
  const aggOk = aggs.every((a) => a['@type'] === 'AggregateRating' && typeof a.ratingValue === 'number'
    && a.ratingValue > 0 && a.ratingValue <= a.bestRating && typeof a.reviewCount === 'number' && a.reviewCount > 0);
  const line = `  ${label.padEnd(24)} want Product=${want.products} rating=${want.rating ? 'present' : 'absent'} | blocks=${blocks.length} parse-errors=${errs.length} Product=${products.length} aggregateRating=${aggs.length} valid=${aggs.length ? aggOk : 'n/a'}`;
  const fail = errs.length > 0 || products.length !== want.products
    || (want.rating ? !(aggs.length && aggOk) : aggs.length > 0);
  if (fail) bad++;
  console.log(`${fail ? 'FAIL' : ' ok '}${line}`);
  if (errs.length) console.log('        parse errors:', errs.join(' | '));
  for (const a of aggs) console.log(`        ${JSON.stringify(a)}`);
}
console.log(bad ? `\n  ${bad} FAILURE(S)` : '\n  every target: JSON parses, Product-node count and rating presence as expected, AggregateRating well-formed');
process.exitCode = bad ? 1 : 0;
