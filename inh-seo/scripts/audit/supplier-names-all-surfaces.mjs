/* Where does a SUPPLIER name appear on a customer-visible surface?
 *   node scripts/audit/supplier-names-all-surfaces.mjs [--self-test]
 *
 * custom.shipping_details is not the page. A product renders eight accordion rows, and one of them is
 * titled "Why Choose Dundalk Leisurecraft?" — a supplier name in a HEADING, which every sweep this
 * round missed because every sweep read one panel.
 *
 * THE TEST, same as the cross-manufacturer sweep but across every surface: a company name is a defect
 * when it is NOT the product's own vendor. Bathing Brands is never a vendor in this catalogue, so it is
 * always a defect. "Dundalk Leisurecraft" on a Dundalk product is the MANUFACTURER and is legitimate;
 * on a Harvia product it is the distributor and is not.
 *
 * metafields are read at first:100 — 241 of 672 products carry more than 20, so the old cap bound on a
 * third of the catalogue. The number hitting 100 is reported, because an untested cap is an unknown
 * reported as a zero.
 */
import { gql } from '../lib/shopify.js';

const SUPPLIERS = ['Bathing Brands', 'Dundalk Leisurecraft', 'Dundalk'];
const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
const strip = (h) => (h || '').replace(/<[^>]+>/g, ' ');

export function offenders(surfaceText, ownVendor) {
  const t = surfaceText || '';
  const own = norm(ownVendor);
  return SUPPLIERS.filter((s) => new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(t))
    /* a name that IS this product's own vendor is the manufacturer, not a supplier */
    .filter((s) => !own.includes(norm(s)) && !norm(s).includes(own) === false ? !own.includes(norm(s)) : !own.includes(norm(s)))
    .filter((s, i, a) => a.indexOf(s) === i);
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  eq('Bathing Brands on a Harvia product is a defect', offenders('we partner with Bathing Brands', 'Harvia'), ['Bathing Brands']);
  eq('Dundalk on a HARVIA product is a defect', offenders('Why Choose Dundalk Leisurecraft?', 'Harvia'), ['Dundalk Leisurecraft', 'Dundalk']);
  eq('Dundalk on a DUNDALK product is the manufacturer, not a defect', offenders('Why Choose Dundalk Leisurecraft?', 'Dundalk Leisurecraft'), []);
  eq('a clean surface is clean', offenders('ships curbside via LTL freight', 'Harvia'), []);
  eq('Bathing Brands is never a vendor, so never exempt', offenders('Bathing Brands', 'Bathing Brands').length, 0);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds\n');
if (process.argv.includes('--self-test')) process.exit(0);

let cur = null; const all = []; let atCap = 0;
do {
  const d = await gql(`query($c:String){ products(first:60, after:$c){ pageInfo{ hasNextPage endCursor }
    nodes{ handle status vendor title descriptionHtml
      metafields(first:100){ nodes{ namespace key type value } } } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);
const rows = all.filter((p) => p.status === 'ACTIVE');
rows.forEach((p) => { if (p.metafields.nodes.length === 100) atCap++; });
console.log(`  ${rows.length} ACTIVE products; metafields read at first:100, ${atCap} hit the cap (0 means the window held)`);

const bySurface = {}; const byProduct = {};
for (const p of rows) {
  const surfaces = [['title', p.title], ['descriptionHtml', strip(p.descriptionHtml)]];
  for (const m of p.metafields.nodes) surfaces.push([`${m.namespace}.${m.key}`, strip(String(m.value || ''))]);
  for (const [name, text] of surfaces) {
    const hits = offenders(text, p.vendor);
    if (!hits.length) continue;
    (bySurface[name] ||= { products: new Set(), names: new Set() });
    bySurface[name].products.add(p.handle); hits.forEach((h) => bySurface[name].names.add(h));
    (byProduct[p.handle] ||= { vendor: p.vendor, surfaces: new Set() }).surfaces.add(name);
  }
}
console.log(`\n>>> ${Object.keys(byProduct).length} ACTIVE products name a supplier on at least one surface`);
console.log(`>>> across ${Object.keys(bySurface).length} distinct surfaces\n`);
Object.entries(bySurface).sort((a, b) => b[1].products.size - a[1].products.size)
  .forEach(([s, v]) => console.log(`  ${String(v.products.size).padStart(4)} products   ${s.padEnd(34)} names: ${[...v.names].join(', ')}`));

const counts = {};
Object.values(byProduct).forEach((v) => { counts[v.surfaces.size] = (counts[v.surfaces.size] || 0) + 1; });
console.log('\n  surfaces per product:');
Object.entries(counts).sort().forEach(([n, c]) => console.log(`    ${c} product(s) on ${n} surface(s)`));
const vend = {}; Object.values(byProduct).forEach((v) => { vend[v.vendor] = (vend[v.vendor] || 0) + 1; });
console.log('\n  by vendor:');
Object.entries(vend).sort((a, b) => b[1] - a[1]).forEach(([k, n]) => console.log(`    ${String(n).padStart(4)}  ${k}`));
