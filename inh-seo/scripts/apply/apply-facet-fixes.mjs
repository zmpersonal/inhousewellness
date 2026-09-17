/* B6b — apply one facet-fix pass. --pass mechanical | kw
 *
 * Each pass is its own apply with its own backup and its own review, because
 * they are different kinds of change: pass 1 has no decision in it, pass 2 is a
 * convention decided once for the field.
 *
 * Refuses if any stored `from` no longer matches live, and refuses to write a
 * row whose product title contradicts the value (see HOLD below).
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, readJSON, DATA, assertOneWritePerRecord } from '../lib/util.js';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');
const pass = (process.argv.find((a) => a.startsWith('--pass=')) || '').split('=')[1];
if (!['mechanical', 'kw'].includes(pass)) throw new Error('--pass=mechanical|kw required');

/* HOLD: field says 10KW, title says 9.8kW. A formatting write would leave the
 * contested number looking reviewed. Reported instead — see reports/b6b.md. */
const HOLD = new Set(['wood-burning-sauna-stove-stones-9-8kw']);

const file = pass === 'mechanical' ? 'facet-fix-mechanical.json' : 'facet-fix-kw.json';
const map = readJSON(path.join(DATA, file));
const held = map.rows.filter((r) => HOLD.has(r.handle));
const rows = map.rows.filter((r) => !HOLD.has(r.handle));

/* one write per metafield, not per product: a product can hold two split values */
assertOneWritePerRecord(rows, (r) => r.metafieldId, `facet ${pass}`);

const ids = [...new Set(rows.map((r) => r.productId))];
const live = {};
for (let i = 0; i < ids.length; i += 100) {
  const r = await gql(`query($ids:[ID!]!){ nodes(ids:$ids){ ... on Product { id
    metafields(first:20, namespace:"custom"){ nodes{ id value } } } } }`, { ids: ids.slice(i, i + 100) });
  for (const n of r.nodes) if (n) for (const mf of n.metafields.nodes) live[mf.id] = mf.value;
}
const drift = rows.filter((r) => live[r.metafieldId] !== r.from);
if (drift.length) {
  drift.forEach((r) => console.log(`  DRIFT ${r.handle}.${r.key}: map "${r.from}" vs live "${live[r.metafieldId]}"`));
  throw new Error('mapping is stale — rebuild it');
}

console.log(`  pass: ${pass}`);
console.log(`  freshness: all ${rows.length} rows match live`);
if (held.length) held.forEach((r) => console.log(`  HELD: ${r.handle}.${r.key} "${r.from}" — title contradicts the value`));
console.log(`  writes: ${rows.length}`);

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const bpath = backup(`facet-${pass}`, rows.map((r) => ({ handle: r.handle, key: r.key, metafieldId: r.metafieldId, value: r.from })));
console.log(`  backup -> ${bpath}`);

let ok = 0, fail = 0;
for (const r of rows) {
  const w = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }`,
    { m: [{ ownerId: r.productId, namespace: 'custom', key: r.key, type: 'single_line_text_field', value: r.to }] });
  if (w.metafieldsSet.userErrors.length) { console.log(`  FAIL ${r.handle}.${r.key}: ${JSON.stringify(w.metafieldsSet.userErrors)}`); fail++; continue; }
  logChange({ resource: r.productId, handle: r.handle, type: 'product', field: `metafield custom.${r.key}`,
    from: r.from, to: r.to, note: `B6b facet split, pass ${pass}`, backup: bpath });
  ok++;
}
console.log(`\n  applied ${ok}/${rows.length}   failed ${fail}`);
if (fail) process.exitCode = 1;
