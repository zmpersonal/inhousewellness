/* Blast radius of the unquoted gtin bug, measured from the PUBLIC storefront — no Admin API
 * credential required, which matters because the Admin token is currently 401.
 *
 * /products.json returns PUBLISHED products only. That is the right population: it is exactly
 * what Google and the LLM crawlers can see, so it is what the bug can cost us. Draft and
 * unpublished products are outside the measurement and are named as such. */
import fs from 'node:fs';
const UA = { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36' };
/* products.json DOES NOT CARRY barcode — the key is absent from its variant serializer entirely,
 * while /products/<handle>.js does return it. The first run of this script counted 0 leading-zero
 * barcodes across 478 products, which was a property of the endpoint and not of the store.
 * An absence in a dump is evidence about the dump. Handles come from products.json; barcodes
 * come from the per-product endpoint that actually has them. */
let page = 1, handles = [];
while (page <= 12) {
  const r = await fetch(`https://inhousewellness.com/products.json?limit=250&page=${page}`, { headers: UA });
  if (r.status !== 200) break;
  const j = await r.json();
  if (!j.products?.length) break;
  handles.push(...j.products.map((p) => p.handle)); page++;
}
console.log(`  PUBLISHED products enumerated: ${handles.length}`);
console.log(`  fetching per-product .js for barcodes (products.json omits the field)…`);
/* inhousewellness.com RATE-LIMITS under load. At concurrency 10 only 117 of 478 came back, and
 * measuring "2 affected" over that sample would have been a precise, wrong number.
 * 429 is BACKOFF, never a dead link. Concurrency 2, 8s backoff, 6 attempts — the settings this
 * repo already proved. Status distribution is printed so a shortfall can never look like a result. */
const all = []; let done = 0; const status = {};
const work = async (h) => {
  for (let attempt = 1; attempt <= 6; attempt++) {
    try {
      const r = await fetch(`https://inhousewellness.com/products/${h}.js`, { headers: UA });
      status[r.status] = (status[r.status] || 0) + 1;
      if (r.status === 200) { all.push(await r.json()); break; }
      if (r.status === 429 || r.status >= 500) { await new Promise((z) => setTimeout(z, 8000)); continue; }
      break;
    } catch (e) { status.ERR = (status.ERR || 0) + 1; await new Promise((z) => setTimeout(z, 8000)); }
  }
  if (++done % 100 === 0) console.log(`    …${done}/${handles.length}`);
};
const q = [...handles];
await Promise.all(Array.from({ length: 2 }, async () => { while (q.length) await work(q.pop()); }));
console.log(`  products fetched with variant detail: ${all.length} of ${handles.length}`);
console.log(`  HTTP status distribution: ${JSON.stringify(status)}`);
if (all.length < handles.length) {
  console.log(`  ⚠ INCOMPLETE — ${handles.length - all.length} product(s) never returned 200. Figures below are a FLOOR, not a total.`);
}

/* a gtin is only EMITTED when barcode length is 12, 13 or 14 — the theme's own condition */
const EMITTED = new Set([12, 13, 14]);
let withBarcode = 0, emitted = 0, leadingZero = 0, otherInvalid = 0;
const affected = [];
for (const p of all) {
  for (const v of p.variants || []) {
    const b = (v.barcode ?? '').toString().trim();
    if (!b) continue;
    withBarcode++;
    if (!EMITTED.has(b.length)) continue;
    emitted++;
    if (/^0/.test(b)) { leadingZero++; affected.push({ handle: p.handle, barcode: b }); }
    else if (!/^[0-9]+$/.test(b)) { otherInvalid++; affected.push({ handle: p.handle, barcode: b, why: 'non-numeric, unquoted = invalid JSON' }); }
  }
}
const uniqAffected = [...new Set(affected.map((a) => a.handle))];
console.log(`\n  variants carrying a barcode:                 ${withBarcode}`);
console.log(`  …of length 12/13/14, so a gtin IS emitted:   ${emitted}`);
console.log(`  …starting with 0 — INVALID JSON:            ${leadingZero}`);
console.log(`  …non-numeric, also invalid unquoted:        ${otherInvalid}`);
console.log(`\n  PUBLISHED PRODUCTS WITH A BROKEN Product NODE: ${uniqAffected.length} of ${all.length}`);

/* cross-reference against the rating coverage measured before the token died */
const cov = JSON.parse(fs.readFileSync('data/rating-coverage.json', 'utf8'));
const rated = new Set(cov.filter((r) => r.ok).map((r) => r.handle));
const activeRated = new Set(cov.filter((r) => r.ok && r.status === 'ACTIVE').map((r) => r.handle));
const brokenAndRated = uniqAffected.filter((h) => rated.has(h));
const brokenAndActiveRated = uniqAffected.filter((h) => activeRated.has(h));
console.log(`\n  ── what this cost Round 15 ──`);
console.log(`  products with a usable rating (measured earlier): ${rated.size}   ACTIVE: ${activeRated.size}`);
console.log(`  RATED products whose Product node is invalid:     ${brokenAndRated.length}`);
console.log(`  …and ACTIVE:                                      ${brokenAndActiveRated.length}`);
console.log(`  => ${((brokenAndActiveRated.length / activeRated.size) * 100).toFixed(1)}% of the ACTIVE rated set was invisible to a strict parser`);
fs.writeFileSync('data/gtin-blast-radius.json', JSON.stringify({ published: all.length, emitted, leadingZero, affected: uniqAffected, brokenAndRated, brokenAndActiveRated }, null, 1));
console.log(`\n  first 8 affected: ${uniqAffected.slice(0, 8).join(', ')}`);
