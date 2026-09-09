/**
 * Does any SKU appear on more than one ACTIVE product?
 *
 * One duplicate was found by ACCIDENT during an MSRP staleness check —
 * GDI-6880-02 Elite, sold as two ACTIVE published products $5,000 apart. Finding
 * it by accident is the evidence that nobody has looked, so this looks.
 *
 * A duplicate costs three ways: the customer can buy the same unit at two
 * prices, Google sees two competing pages for one product, and the two rows can
 * drift apart in EVERY other field — membership, tier, wood, warranty — with
 * nothing tying them together.
 *
 * Read-only.
 *   node scripts/audit/duplicate-skus.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { DATA } from '../lib/util.js';

/* SKUs are typed by humans across suppliers: "GDI-6880-02 Elite" and
   "GDI-6880-02-Elite" are the same part. Comparing raw would have missed the
   one duplicate we already know about. */
const norm = (s) => String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');

let prods = [], after = null, more = true;
while (more) {
  const r = await gql(`query($after:String){ products(first:100, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{ handle title status vendor
      variants(first:20){ nodes{ sku price compareAtPrice } }
      collections(first:40){ nodes{ handle } } } } }`, { after });
  prods.push(...r.products.nodes); more = r.products.pageInfo.hasNextPage; after = r.products.pageInfo.endCursor;
}

const bySku = new Map();
for (const p of prods) for (const v of p.variants.nodes) {
  if (!v.sku) continue;
  const k = norm(v.sku);
  if (!k) continue;
  if (!bySku.has(k)) bySku.set(k, []);
  bySku.get(k).push({ handle: p.handle, title: p.title, status: p.status, vendor: p.vendor,
    sku: v.sku, price: Number(v.price), msrp: v.compareAtPrice ? Number(v.compareAtPrice) : null,
    collections: p.collections.nodes.map((c) => c.handle) });
}

const rows = [];
for (const [k, list] of bySku) {
  const handles = [...new Set(list.map((x) => x.handle))];
  if (handles.length < 2) continue;                      /* one product, many variants — fine */
  const active = list.filter((x) => x.status === 'ACTIVE');
  const activeHandles = [...new Set(active.map((x) => x.handle))];
  rows.push({ sku: k, handles, activeHandles, list });
}

const bothActive = rows.filter((r) => r.activeHandles.length > 1);
const mixed = rows.filter((r) => r.activeHandles.length === 1 && r.handles.length > 1);
const noneActive = rows.filter((r) => r.activeHandles.length === 0);

console.log(`${prods.length} products · ${bySku.size} distinct SKUs\n`);
console.log(`── TWO OR MORE ACTIVE PRODUCTS SHARE A SKU: ${bothActive.length}`);
for (const r of bothActive) {
  console.log(`\n  ${r.sku}`);
  for (const x of r.list.filter((y) => y.status === 'ACTIVE')) {
    console.log(`    $${String(x.price).padStart(9)}  MSRP $${String(x.msrp ?? '-').padStart(8)}  ${x.handle}`);
    console.log(`        "${x.title.slice(0, 76)}"`);
  }
  /* membership divergence is the second cost and is invisible on the page */
  const sets = r.list.filter((y) => y.status === 'ACTIVE').map((y) => new Set(y.collections));
  if (sets.length === 2) {
    const only1 = [...sets[0]].filter((c) => !sets[1].has(c));
    const only2 = [...sets[1]].filter((c) => !sets[0].has(c));
    if (only1.length || only2.length) console.log(`        MEMBERSHIP DIVERGES — first only: ${only1.join(', ') || 'none'} | second only: ${only2.join(', ') || 'none'}`);
  }
}
console.log(`\n── ONE ACTIVE + ARCHIVED/DRAFT TWIN: ${mixed.length}`);
console.log(`   (not customer-facing today, but the archive is the re-entry point — a republish restores the duplicate)`);
for (const r of mixed.slice(0, 25)) {
  const a = r.list.find((x) => x.status === 'ACTIVE');
  const others = r.list.filter((x) => x.status !== 'ACTIVE');
  console.log(`  ${r.sku.padEnd(26)} ACTIVE ${a.handle}  +  ${others.map((o) => `${o.status} ${o.handle}`).join(', ')}`);
}
if (mixed.length > 25) console.log(`  … and ${mixed.length - 25} more`);
console.log(`\n── SKU shared only by non-ACTIVE products: ${noneActive.length} (no customer impact)`);

fs.writeFileSync(path.join(DATA, 'duplicate-skus.json'), JSON.stringify({ _meta: { ran: new Date().toISOString(), method: 'SKU normalised to A-Z0-9 before comparison' }, bothActive, mixed, noneActive }, null, 2));
console.log('\nwrote data/duplicate-skus.json');
