/**
 * Are the strikethrough MSRPs on our product pages still the manufacturer's
 * current published price?
 *
 * NOT an honesty check. The client's ruling of 9 September 2026 is that
 * strikethrough pricing is a real manufacturer MSRP and a category-standard
 * comparison, and that ruling is accepted. This is the STALENESS question: a
 * figure that was right in 2024 and has since moved is the third defect class —
 * true when written, false because the thing it describes changed.
 *
 * Matching is on SKU where the manufacturer publishes one, and it REFUSES to
 * match on title alone. A title match across two catalogues is a naming
 * convention, and a convention is for finding candidates, never for concluding.
 *
 * Read-only.
 *   node scripts/audit/msrp-drift.mjs
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';

const UA = { 'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36' };

/* Only manufacturers that publish a price to the public. Harvia, HUUM, SaunaLife
   and Dundalk do not expose a fetchable catalogue, so their MSRPs cannot be
   checked from here and are reported as UNCHECKABLE rather than as passing —
   "I could not check" and "this is fine" are different answers. */
const SOURCES = [
  { vendors: ['Golden Designs Inc', 'Dynamic Saunas', 'Maxxus'], url: 'https://goldendesignsaunas.com/products.json?limit=250' },
  { vendors: ['Scandia Manufacturing', 'Scandia'], url: 'https://scandiamfg.com/products.json?limit=250' },
  { vendors: ['Medical Saunas'], url: 'https://medicalsaunas.com/products.json?limit=250' },
];

async function catalogue(url) {
  const all = [];
  for (let page = 1; page <= 6; page++) {
    const res = await fetch(`${url}&page=${page}`, { headers: UA, redirect: 'follow' });
    if (!res.ok) break;
    /* instance 39: the answer belongs to res.url, not to the string we sent */
    if (!res.url.startsWith(new URL(url).origin)) { console.error(`  REDIRECTED off-origin: ${url} -> ${res.url}`); break; }
    const j = await res.json();
    if (!j.products?.length) break;
    all.push(...j.products);
  }
  return all;
}

const norm = (s) => String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');

let ours = [], after = null, more = true;
while (more) {
  const r = await gql(`query($after:String){ products(first:100, after:$after){ pageInfo{hasNextPage endCursor}
    nodes{ handle title vendor status variants(first:10){ nodes{ price compareAtPrice sku } } } } }`, { after });
  ours.push(...r.products.nodes); more = r.products.pageInfo.hasNextPage; after = r.products.pageInfo.endCursor;
}

const rows = [];
for (const p of ours) for (const v of p.variants.nodes) {
  if (v.compareAtPrice && Number(v.compareAtPrice) > Number(v.price)) {
    rows.push({ handle: p.handle, title: p.title, vendor: p.vendor, status: p.status,
      price: Number(v.price), msrp: Number(v.compareAtPrice), sku: v.sku });
  }
}
console.log(`our catalogue: ${ours.length} products, ${rows.length} variants carry a strikethrough MSRP (${new Set(rows.map(r => r.handle)).size} products)\n`);

const results = [];
for (const src of SOURCES) {
  const mfr = await catalogue(src.url);
  const bySku = new Map();
  for (const p of mfr) for (const v of (p.variants || [])) {
    if (v.sku) bySku.set(norm(v.sku), { handle: p.handle, price: Number(v.price), compare: v.compare_at_price ? Number(v.compare_at_price) : null, title: p.title });
  }
  const mine = rows.filter((r) => src.vendors.includes(r.vendor) && r.status === 'ACTIVE');
  const host = new URL(src.url).host;
  console.log(`── ${src.vendors.join(' / ')}  (${host}: ${mfr.length} products, ${bySku.size} SKUs)`);
  let matched = 0;
  for (const r of mine) {
    const m = r.sku ? bySku.get(norm(r.sku)) : null;
    if (!m) continue;
    matched += 1;
    /* CRITICAL: a manufacturer's SELLING price is not their MSRP.
       Scandia publishes 0 compare_at prices across 277 variants, so their list
       price is invisible from here and their selling price says nothing about
       MSRP. Reading it as one produced 8 confident "drifts" on one product.
       Golden Designs publishes a compare_at on 125 of 203 variants, so where
       one exists the comparison is like for like.

       Drift is only asserted where the MANUFACTURER shows their own list price.
       Everything else is UNCHECKABLE — a different answer from "agrees". */
    const mfrList = m.compare && m.compare > m.price ? m.compare : null;
    const delta = mfrList === null ? null : r.msrp - mfrList;
    results.push({ ...r, host, mfrHandle: m.handle, mfrPrice: m.price, mfrList, delta,
      basis: mfrList === null ? 'UNCHECKABLE — manufacturer publishes no list price for this SKU' : 'manufacturer compare_at' });
  }
  console.log(`   our ACTIVE rows: ${mine.length}   matched by SKU: ${matched}   unmatched: ${mine.length - matched}\n`);
}

const checkable = results.filter((r) => r.delta !== null);
const noBasis = results.filter((r) => r.delta === null);
const drift = checkable.filter((r) => Math.abs(r.delta) >= 1);
console.log(`SKU-MATCHED: ${results.length}`);
console.log(`  comparable (manufacturer publishes a list price): ${checkable.length}  ->  agree ${checkable.length - drift.length}, DRIFTED ${drift.length}`);
console.log(`  no basis (manufacturer publishes no list price):   ${noBasis.length}  -> reported as unchecked, not as passing\n`);
for (const r of [...drift].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))) {
  console.log(`  our MSRP $${String(r.msrp).padStart(7)}   mfr list $${String(r.mfrList).padStart(7)}   ${(r.delta > 0 ? 'OURS HIGHER by +' : 'ours lower by ')}${Math.abs(r.delta)}`);
  console.log(`      ${r.handle}  [${r.sku}]  our price $${r.price}, theirs $${r.mfrPrice}`);
}

const UNCHECKABLE = ['Harvia', 'HUUM', 'SaunaLife', 'Dundalk Leisurecraft', 'Dreampod', 'Cozy Heat'];
const un = rows.filter((r) => UNCHECKABLE.includes(r.vendor));
console.log(`\nUNCHECKABLE from here: ${un.length} rows across ${new Set(un.map((r) => r.vendor)).size} vendors — no public catalogue.`);
console.log('  ' + [...new Set(un.map((r) => r.vendor))].join(', '));
console.log('  Reported as unchecked, NOT as passing.');

fs.writeFileSync('data/msrp-drift.json', JSON.stringify({ _meta: { ran: new Date().toISOString(), method: 'SKU match only; title matches refused', sources: SOURCES.map(s => s.url) }, results, uncheckableVendors: [...new Set(un.map(r => r.vendor))] }, null, 2));
console.log('\nwrote data/msrp-drift.json');
