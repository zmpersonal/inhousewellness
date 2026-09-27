/* Round 23g — one product's vendor field.
 *   node scripts/apply/r23g-vendor-fix.mjs [--apply] | --self-test | --restore <backup.json> [--apply]
 *
 * harvia-the-wall-sw60 carries vendor "InHouse Wellness". It is a Harvia heater and its own shipping
 * panel names Harvia throughout. Client ruling 2026-09-27: set it to "Harvia", a string that already
 * exists with 44 ACTIVE products — vendor equals brand, and no new string is invented.
 *
 * The other 8 products with vendor "InHouse Wellness" are genuinely ours (three services, the app, two
 * guides, two own-brand items) and are NOT touched. A hold list that does not print its hits is not a
 * guard, so they are listed by name on every run.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const HANDLE = 'harvia-the-wall-sw60-6-kw-wall-mounted-electric-sauna-heater';
const FROM = 'InHouse Wellness';
const TO = 'Harvia';
const OURS = ['installation-assembly', 'white-glove-delivery-service', 'extended-your-warranty-3-years',
  'saunatap-app-track-sauna-sessions-streaks-insights', 'the-ultimate-sauna-maintenance-care-guide',
  'sauna-session-planner', 'bucket-ladle-sand-timer', 'wellness-advantage'];

/* TO must already exist in the catalogue: vendor equals brand, and a new string splits one */
export function checkTarget(existingVendors, to, from) {
  const p = [];
  if (!existingVendors.includes(to)) p.push(`"${to}" is not an existing vendor string — assigning it would invent a brand`);
  if (to === from) p.push('the target vendor equals the current one, so this is a no-op dressed as a change');
  const near = existingVendors.filter((v) => v !== to && v.toLowerCase().replace(/[^a-z]/g, '') === to.toLowerCase().replace(/[^a-z]/g, ''));
  if (near.length) p.push(`"${to}" collides with ${near.map((v) => `"${v}"`).join(', ')} — picking the wrong one of a pair looks correct and splits the brand`);
  return p;
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  const V = ['Harvia', 'HUUM', 'Huum', 'InHouse Wellness', 'Ice Tubs'];
  eq('the real change passes', checkTarget(V, 'Harvia', 'InHouse Wellness').length, 0);
  eq('an invented vendor is refused', checkTarget(V, 'Harvia Inc', 'InHouse Wellness').length > 0, true);
  eq('a no-op dressed as a change is refused', checkTarget(V, 'Harvia', 'Harvia').length > 0, true);
  eq('a casing collision is refused', checkTarget(V, 'HUUM', 'Ice Tubs').length > 0, true);
  eq('the hold list is not empty', OURS.length, 8);
  eq('the target is not in the hold list', OURS.includes(HANDLE), false);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ id handle status vendor } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);
const vendors = [...new Set(all.filter((p) => p.status === 'ACTIVE').map((p) => p.vendor).filter(Boolean))];
const p = all.find((x) => x.handle === HANDLE);
if (!p) { console.log(`REFUSING: ${HANDLE} not found`); process.exit(1); }
if (p.vendor !== FROM) { console.log(`REFUSING: its vendor is "${p.vendor}", not "${FROM}" — already changed, or the wrong product`); process.exit(1); }

const probs = checkTarget(vendors, TO, FROM);
console.log(`\n  ${HANDLE}`);
console.log(`    vendor: "${FROM}"  ->  "${TO}"   (${all.filter((x) => x.status === 'ACTIVE' && x.vendor === TO).length} ACTIVE products already carry it)`);
console.log(`\n  HELD — genuinely InHouse Wellness products, not touched (${OURS.length}):`);
OURS.forEach((h) => console.log(`    ${h}`));
if (probs.length) { probs.forEach((x) => console.log(`\n  FAIL ${x}`)); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = [{ id: p.id, handle: HANDLE, field: 'vendor', before: FROM }];
const bpath = backup('r23g-vendor-fix', snap);
const r = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ vendor } userErrors{ message } } }`, { p: { id: p.id, vendor: TO } });
if (r.productUpdate.userErrors.length) { console.log(`  FAILED: ${JSON.stringify(r.productUpdate.userErrors)}`); process.exit(1); }
const back = r.productUpdate.product.vendor;
snap[0].stored = back;
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
if (back !== TO) { console.log(`  FAILED: read-back is "${back}", not "${TO}"`); process.exit(1); }
logChange({ script: 'r23g-vendor-fix', resource: p.id, handle: HANDLE, field: 'vendor', old: FROM, new: TO, note: `backup ${bpath}` });
console.log(`\n  WROTE. read-back "${back}"   BACKUP ${bpath}`);
