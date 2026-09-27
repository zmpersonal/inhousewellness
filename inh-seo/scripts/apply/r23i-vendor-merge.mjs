/* Round 23i — merge a duplicate vendor string into the one the brand already uses.
 *   node scripts/apply/r23i-vendor-merge.mjs [--apply] | --self-test | --restore <backup.json> [--apply]
 *
 * "Leisure Craft" (1 product) and "Dundalk Leisurecraft" (25) are one company. The split made
 * dundalk-leisurecraft-cold-plunge look like it named a foreign supplier on nine surfaces, when every
 * mention is the manufacturer naming itself.
 *
 * This one HAS a restore branch, through scripts/lib/restore.mjs — r23g-vendor-fix.mjs did not, which
 * is why it sits on the person-recoverable list. Vendor equals brand: only strings that already exist.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';
import { restoreRows } from '../lib/restore.mjs';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const FROM = 'Leisure Craft';
const TO = 'Dundalk Leisurecraft';

export function checkMerge(vendors, from, to) {
  const p = [];
  if (!vendors.includes(to)) p.push(`"${to}" is not an existing vendor string — vendor equals brand, and a new string splits one`);
  if (!vendors.includes(from)) p.push(`"${from}" no longer exists — already merged, or the wrong string`);
  if (from === to) p.push('from and to are the same string');
  /* A VARIANT means: ignoring case and spacing, one name is the other or a SHORTENED form of it.
     "Leisure Craft" -> "Dundalk Leisurecraft" is a shortening, not a case variant, and an
     equality test refused it. Containment accepts that and still refuses Cal Flame / Cal Spa,
     which the client ruled are sibling brands rather than one name. */
  const n = (s) => s.toLowerCase().replace(/[^a-z]/g, '');
  const a = n(from), b = n(to);
  if (!(a === b || a.includes(b) || b.includes(a))) {
    p.push(`"${from}" and "${to}" are not the same name ignoring case and spacing, and neither is a shortened form of the other — this tool merges VARIANTS, not different brands`);
  }
  return p;
}

const adapter = {
  key: (r) => r.handle,
  describe: (r) => r.before,
  storedOf: (r) => r.stored ?? null,
  readLive: async (r) => {
    const d = await gql(`query($id:ID!){ product(id:$id){ vendor } }`, { id: r.id });
    if (!d.product) throw new Error('product not found');
    return d.product.vendor;
  },
  writeBack: async (r) => {
    const d = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ vendor } userErrors{ message } } }`, { p: { id: r.id, vendor: r.before } });
    if (d.productUpdate.userErrors.length) throw new Error(JSON.stringify(d.productUpdate.userErrors));
    return d.productUpdate.product.vendor;
  },
};

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  const V = ['Leisure Craft', 'Dundalk Leisurecraft', 'Harvia'];
  eq('the real merge passes', checkMerge(V, FROM, TO).length, 0);
  eq('an invented target is refused', checkMerge(V, FROM, 'Dundalk LeisureCraft Inc').length > 0, true);
  eq('a missing source is refused (already merged)', checkMerge(['Dundalk Leisurecraft'], FROM, TO).length > 0, true);
  eq('merging two DIFFERENT brands is refused', checkMerge(V, 'Harvia', 'Dundalk Leisurecraft').length > 0, true);
  eq('a case/spacing variant is accepted', checkMerge(['HUUM', 'Huum'], 'Huum', 'HUUM').length, 0);
  eq('a SHORTENED form is accepted (the case an equality test refused)', checkMerge(V, 'Leisure Craft', 'Dundalk Leisurecraft').length, 0);
  eq('Scandia -> Scandia Manufacturing is accepted', checkMerge(['Scandia', 'Scandia Manufacturing'], 'Scandia', 'Scandia Manufacturing').length, 0);
  eq('Cal Spa -> Cal Flame is REFUSED: sibling brands, not one name', checkMerge(['Cal Spa', 'Cal Flame'], 'Cal Spa', 'Cal Flame').length > 0, true);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

const RESTORE = arg('--restore');
if (RESTORE) {
  const r = await restoreRows(JSON.parse(fs.readFileSync(RESTORE, 'utf8')), adapter, { apply: APPLY, only: arg('--only') });
  if (APPLY) for (const k of r.restored) logChange({ script: 'r23i-vendor-merge', handle: k, field: 'vendor', old: TO, new: FROM, note: `restore from ${RESTORE}` });
  /* A REFUSAL MUST BE DETECTABLE BY EXIT CODE. This exited 0 while printing REFUSE, so a proof runner
   or a CI step would read a refused restore as success — the same shape as the piped `tee` that made a
   printed STOP go green. A refusal is three things: non-zero exit, the guard's own message, and live
   unchanged. Only "already restored" and a completed restore are exit 0. */
process.exit(r.failed.length || r.refused.length ? 1 : 0);
}

let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ id handle status vendor title } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);
/* all statuses: an ACTIVE-only list hid eight vendor strings, including the two new casing pairs */
const vendors = [...new Set(all.map((p) => p.vendor).filter(Boolean))];
const targets = all.filter((p) => p.vendor === FROM);
const probs = checkMerge(vendors, FROM, TO);
console.log(`\n  "${FROM}" -> "${TO}"   ${targets.length} product(s) across all statuses`);
targets.forEach((p) => console.log(`    ${p.status.padEnd(9)} ${p.handle}\n        ${p.title.slice(0, 96)}`));
console.log(`  "${TO}" currently holds ${all.filter((p) => p.vendor === TO).length} product(s)`);
if (probs.length) { probs.forEach((x) => console.log(`  FAIL ${x}`)); process.exit(1); }
if (!targets.length) { console.log('  nothing to do'); process.exit(0); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = targets.map((p) => ({ id: p.id, handle: p.handle, before: FROM }));
const bpath = backup('r23i-vendor-merge', snap);
let failed = 0;
for (const p of targets) {
  const d = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ vendor } userErrors{ message } } }`, { p: { id: p.id, vendor: TO } });
  if (d.productUpdate.userErrors.length) { console.log(`  FAILED ${p.handle}: ${JSON.stringify(d.productUpdate.userErrors)}`); failed++; continue; }
  const back = d.productUpdate.product.vendor;
  snap.find((x) => x.handle === p.handle).stored = back;
  if (back !== TO) { console.log(`  FAILED ${p.handle}: read-back "${back}"`); failed++; continue; }
  logChange({ script: 'r23i-vendor-merge', resource: p.id, handle: p.handle, field: 'vendor', old: FROM, new: TO, note: `backup ${bpath}` });
  console.log(`  wrote ${p.handle}  vendor now "${back}"`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
process.exit(failed ? 1 : 0);
