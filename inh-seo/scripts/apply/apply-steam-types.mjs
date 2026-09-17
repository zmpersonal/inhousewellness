/* Split productType "Steam Room" into Steam Generator and Steam Accessories.
 *
 * Not one of the 38 products typed "Steam Room" is a steam room. 23 are steam
 * generators (some already mistyped Sauna Heater / Sauna Accessories) and 24
 * are control packages, steamheads, touchscreens and one replacement element.
 *
 * Reads the fixed mapping from data/steam-type-map.json so the list reviewed is
 * the list written. Refuses if the file disagrees with the live field.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, readJSON, DATA, assertOneWritePerRecord } from '../lib/util.js';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');
const TAXONOMY = new Set(['Sauna', 'Sauna Heater', 'Cold Plunge', 'Float Tank',
  'Massage Chair', 'Hot Tub', 'Sauna Accessories', 'Cold Plunge Accessories', 'Grill Accessories',
  'Grill', 'Fire Pit', 'Outdoor Fireplace', 'Outdoor Kitchen', 'Steam Generator', 'Steam Accessories']);

const map = readJSON(path.join(DATA, 'steam-type-map.json'));
assertOneWritePerRecord(map.rows, (r) => r.id, 'steam type split');

for (const r of map.rows) {
  if (!TAXONOMY.has(r.to)) throw new Error(`target "${r.to}" is outside the taxonomy`);
}

/* Confirm the stored `from` still matches live. A mapping built yesterday is a
 * claim about yesterday. */
const ids = map.rows.map((r) => r.id);
const live = {};
for (let i = 0; i < ids.length; i += 100) {
  const r = await gql(`query($ids:[ID!]!){ nodes(ids:$ids){ ... on Product { id productType } } }`, { ids: ids.slice(i, i + 100) });
  for (const n of r.nodes) if (n) live[n.id] = n.productType;
}
const drift = map.rows.filter((r) => live[r.id] !== r.from);
if (drift.length) {
  console.log(`\n  DRIFT — ${drift.length} row(s) no longer match the mapping:`);
  drift.forEach((r) => console.log(`     ${r.handle}  map says "${r.from}", live says "${live[r.id]}"`));
  throw new Error('mapping is stale — rebuild it');
}
console.log(`  freshness: all ${map.rows.length} rows match live\n`);

const counts = {};
map.rows.forEach((r) => { counts[r.to] = (counts[r.to] || 0) + 1; });
for (const [k, n] of Object.entries(counts)) console.log(`  -> ${k.padEnd(20)} ${n}`);
console.log(`  total writes: ${map.rows.length}`);

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const bpath = backup('steam-type-split', map.rows.map((r) => ({ id: r.id, handle: r.handle, productType: r.from })));
console.log(`\n  backup -> ${bpath}`);

let ok = 0, fail = 0;
for (const r of map.rows) {
  const w = await gql(`mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id productType } userErrors{ field message } } }`,
    { input: { id: r.id, productType: r.to } });
  if (w.productUpdate.userErrors.length) { console.log(`  FAIL ${r.handle}: ${JSON.stringify(w.productUpdate.userErrors)}`); fail++; continue; }
  logChange({ resource: r.id, handle: r.handle, type: 'product', field: 'productType', from: r.from, to: r.to, note: 'Steam Room split: no product typed Steam Room was a steam room', backup: bpath });
  ok++;
}
console.log(`\n  applied ${ok}/${map.rows.length}   failed ${fail}`);
if (fail) process.exitCode = 1;
