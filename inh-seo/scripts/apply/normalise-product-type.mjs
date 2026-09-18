/* normalise-product-type — 53 values to 14, plus 100 fills.
 *
 * TWO SOURCES, ONE PRECEDENCE. The value-level map says what a value NAMES.
 * Collection membership overrides it where they disagree, because all 33
 * disagreements resolved the same way: the value was wrong and the collection was
 * right. Thirty-three disagreements pointing one direction is evidence about which
 * source is authoritative, not a set of exceptions.
 *
 * Fills use collection membership, then Shopify's product category. Vendor was
 * dropped entirely — it assigned Grill to pizza stones because the vendor is Primo.
 * A source that produces confident wrong answers is worse than one that abstains.
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, assertOneWritePerRecord } from '../lib/util.js';

const flags = parseArgs();
banner('normalise-product-type', flags);

/* 'Steam Room' was RETIRED 10 September 2026. It was populated on 38 products and
 * described none of them: 23 were steam generators and 24 were controls and parts.
 * A value that names nothing in the catalogue must not survive as a facet option. */
const TAXONOMY = new Set(['Sauna','Sauna Heater','Cold Plunge','Steam Generator','Steam Accessories','Float Tank','Massage Chair','Hot Tub',
  'Sauna Accessories','Cold Plunge Accessories','Grill Accessories','Grill','Fire Pit','Outdoor Fireplace','Outdoor Kitchen']);
const MERGE = readJSON(path.join(DATA, 'producttype-merges.json')).map;
const FILLS = new Map(readJSON(path.join(DATA, 'producttype-fills.json')).map((f) => [f.handle, f.proposed]));
const OPS = new Set(['newest-products','best-selling-products','avada-best-sellers','non-bb','free-bonus','more','frontpage']);
const UNIT = {'Sauna':/^(saunas|sauna|infrared-saunas|far-infrared|full-spectrum|outdoor-saunas|barrel-saunas|indoor-sauna|steam-saunas|low-emf|ultra-low-emf|near-zero-emf)$/,
 'Sauna Heater':/^(sauna-heaters|designer-sauna-heaters|harvia-sauna-heaters|huum-sauna-heaters|scandia-manufacturing)$/,
 'Cold Plunge':/^(cold-plunge|ice-tubs|cold-plunge-cooling-system|leisurecraft-cold-plunge)$/,
 'Steam Generator':/^(steam-showers|thermasol|mr-steam|delta)$/,'Float Tank':/^(floatation-therapy-tanks)$/,
 'Massage Chair':/^(massage-chairs|helios-massage-chair)$/,'Hot Tub':/^(hot-tubs)$/,
 'Grill':/^(bbq-grills|primo-grills|broilmaster)$/,'Outdoor Kitchen':/^(outdoor-kitchen)$/,
 'Fire Pit':/^(fire-pits)$/,'Outdoor Fireplace':/^(outdoor-fireplaces)$/};
const SPEC = ['Float Tank','Hot Tub','Massage Chair','Steam Generator','Cold Plunge','Sauna Heater','Outdoor Fireplace','Fire Pit','Outdoor Kitchen','Grill','Sauna'];

let after = null, more = true; const live = [];
while (more) {
  const r = await gql(`query($after:String){ products(first:250, after:$after){ pageInfo{hasNextPage endCursor}
    nodes{ id handle productType collections(first:40){ nodes{ handle } } } } }`, { after });
  live.push(...r.products.nodes.map((p) => ({ id: p.id, handle: p.handle, productType: p.productType || '',
    collections: p.collections.nodes.map((c) => c.handle) })));
  more = r.products.pageInfo.hasNextPage; after = r.products.pageInfo.endCursor;
}
console.log(`  live products: ${live.length}\n`);

const targets = []; let hardFail = false; const stats = { merged: 0, overridden: 0, filled: 0, blank: 0, unchanged: 0 };
for (const p of live) {
  let want, why;
  if (p.productType.trim()) {
    const mapped = MERGE[p.productType];
    if (!mapped) { console.error(`  ✗ ${p.handle}: value ${JSON.stringify(p.productType)} is not in the merge map`); hardFail = true; continue; }
    want = mapped; why = 'merge';
    const cs = p.collections.filter((c) => !OPS.has(c));
    const units = Object.entries(UNIT).filter(([, re]) => cs.some((c) => re.test(c))).map(([k]) => k);
    if (units.length && !units.includes(mapped)) { want = SPEC.find((k) => units.includes(k)) || units[0]; why = 'collection override'; }
  } else {
    want = FILLS.has(p.handle) ? FILLS.get(p.handle) : '';
    why = want ? 'fill' : 'left blank';
  }
  if (want && !TAXONOMY.has(want)) { console.error(`  ✗ ${p.handle}: target ${JSON.stringify(want)} is not in the taxonomy`); hardFail = true; continue; }
  if (want === p.productType) { stats.unchanged += 1; continue; }
  if (why === 'left blank') { stats.blank += 1; continue; }
  stats[why === 'merge' ? 'merged' : why === 'fill' ? 'filled' : 'overridden'] += 1;
  targets.push({ p, want, why });
}

console.log(`  merges           ${String(stats.merged).padStart(4)}`);
console.log(`  collection overrides ${String(stats.overridden).padStart(0)}`);
console.log(`  fills            ${String(stats.filled).padStart(4)}`);
console.log(`  left blank       ${String(stats.blank).padStart(4)}`);
console.log(`  already correct  ${String(stats.unchanged).padStart(4)}`);
console.log(`  TO WRITE         ${String(targets.length).padStart(4)}\n`);
for (const t of targets.filter((x) => x.why === 'collection override')) console.log(`    override  ${t.p.handle.slice(0,42).padEnd(44)} ${JSON.stringify(t.p.productType)} -> ${t.want}`);

if (hardFail) { console.error('\nAt least one target failed. NOTHING APPLIED.'); process.exit(1); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
assertOneWritePerRecord(targets, (t) => t.p.handle, 'normalise-product-type');
backup('product-type-before', targets.map((t) => ({ id: t.p.id, handle: t.p.handle, productType: t.p.productType })));

const M = `mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { input: { id: t.p.id, productType: t.want } });
  if (r.productUpdate.userErrors.length) { console.error(`  FAILED ${t.p.handle}:`, r.productUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ resource: t.p.id, handle: t.p.handle, field: 'productType', before: t.p.productType, after: t.want, note: t.why });
  ok += 1;
  if (ok % 100 === 0) console.log(`  … ${ok}/${targets.length}`);
}
console.log(`\n${ok}/${targets.length} updated.`);
