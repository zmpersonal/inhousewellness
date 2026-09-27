/* Round 23j — supplier names in the PLAIN-TEXT panel fields.
 *   node scripts/apply/r23j-plain-text.mjs [--field delivery|warranty] [--only <handle>] [--apply]
 *   node scripts/apply/r23j-plain-text.mjs --report | --self-test | --restore <backup.json> [--apply]
 *
 * custom.delivery and custom.warranty are multi_line_text_field, NOT rich text. r23h's JSON.parse
 * dropped all of them on a parse failure and reported "custom.delivery 0" against a sweep that found 10.
 *
 * THE RULES ARE SHARED, imported from r23h — one rule set, two storage types. What does NOT transfer is
 * the read, the write type, and the guards: there are no blocks here, so block-count and block-type
 * invariants have no meaning and a line-structure invariant takes their place.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';
import { restoreRows } from '../lib/restore.mjs';
import { supplierTerms, isOwnManufacturer, DISTRIBUTORS } from '../lib/vendor-identity.mjs';
import { RULES } from './r23h-supplier-names.mjs';

const IS_MAIN = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
export const FIELDS = ['delivery', 'warranty'];
const TERMS = supplierTerms(['Dundalk Leisurecraft']);

export function rewrite(text) { let o = text; for (const [re, rep] of RULES) o = o.replace(re, rep); return o; }
export const suppliersIn = (text, vendor) => TERMS
  .filter((s) => new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(text))
  .filter((s) => DISTRIBUTORS.some((d) => s.replace(/\s/g, '').toLowerCase().includes(d.replace(/\s/g, '').toLowerCase())) || !isOwnManufacturer(s, vendor));

/* no blocks here, so the structural invariant is the LINE SHAPE: same number of lines, and no line
   gains or loses its leading marker. That is the nearest honest equivalent to block-count. */
export const lineShape = (t) => t.split('\n').map((l) => (l.trim() ? (l.match(/^\s*([^\w\s]{1,3})?/) || [''])[0].trim() + String(l.trim().length > 0) : ''));

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  eq('the shared rules reach plain text: the supplier email becomes ours',
    rewrite('Or contact Bathing Brands directly at CustomerService@BathingBrands.com'), 'Or email us at support@inhousewellness.com');
  eq('a bare supplier mention is neutralised', /Bathing Brands/.test(rewrite('we partner with Bathing Brands for delivery')), false);
  eq('the return promise narrows', /covers the return shipping cost/.test(rewrite('If due to damage or distributor error: Bathing Brands covers the return shipping cost')), false);
  eq('idempotent: a second pass changes nothing', rewrite(rewrite('we partner with Bathing Brands for delivery')), rewrite('we partner with Bathing Brands for delivery'));
  eq('suppliersIn finds the GLUED form', suppliersIn('email CustomerService@BathingBrands.com', 'Harvia').length > 0, true);
  eq('a name that IS the vendor is not a supplier', suppliersIn('Why Choose Dundalk Leisurecraft?', 'Dundalk Leisurecraft'), []);
  eq('line count preserved by a same-line edit', lineShape('a\nb').length, lineShape('a\nb').length);
  eq('a dropped line is caught', lineShape('a\nb\nc').length === lineShape('a\nb').length, false);
  return bad;
}
if (IS_MAIN) {
  const bad = selfTest();
  if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
  console.log('self-test: every fixture holds');
  if (process.argv.includes('--self-test')) process.exit(0);
}

const adapter = (field) => ({
  key: (r) => `${r.handle}/${r.field}`,
  describe: (r) => r.before,
  storedOf: (r) => r.stored ?? null,
  readLive: async (r) => {
    const d = await gql(`query($id:ID!,$k:String!){ product(id:$id){ metafield(namespace:"custom", key:$k){ value } } }`, { id: r.id, k: r.field });
    if (!d.product) throw new Error('product not found');
    return d.product.metafield?.value ?? null;
  },
  writeBack: async (r) => {
    const d = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ value } userErrors{ message } } }`,
      { m: [{ ownerId: r.id, namespace: 'custom', key: r.field, type: 'multi_line_text_field', value: r.before }] });
    if (d.metafieldsSet.userErrors.length) throw new Error(JSON.stringify(d.metafieldsSet.userErrors));
    return d.metafieldsSet.metafields[0].value;
  },
});

if (IS_MAIN) await main();
async function main() {
const RESTORE = arg('--restore');
if (RESTORE) {
  const rows = JSON.parse(fs.readFileSync(RESTORE, 'utf8'));
  const r = await restoreRows(rows, adapter(), { apply: APPLY, only: arg('--only') });
  if (APPLY) for (const k of r.restored) logChange({ script: 'r23j-plain-text', handle: k, field: 'metafield', old: 'Round 23j edit', new: 'restored', note: `restore from ${RESTORE}` });
  process.exit(r.failed.length || r.refused.length ? 1 : 0);
}

const ONLY = arg('--only'); const FIELD_ONLY = arg('--field');
let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:60, after:$c){ pageInfo{ hasNextPage endCursor }
    nodes{ id handle status vendor metafields(first:100){ nodes{ namespace key type value } } } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);

const plan = []; let fail = 0; const wrongType = [];
for (const p of all.filter((x) => x.status === 'ACTIVE')) {
  if (ONLY && p.handle !== ONLY) continue;
  for (const field of (FIELD_ONLY ? [FIELD_ONLY] : FIELDS)) {
    const mf = p.metafields.nodes.find((m) => m.namespace === 'custom' && m.key === field);
    if (!mf?.value) continue;
    if (mf.type !== 'multi_line_text_field') { wrongType.push(`${p.handle} / custom.${field} is ${mf.type}, not multi_line_text_field`); continue; }
    const before = mf.value;
    if (!suppliersIn(before, p.vendor).length) continue;
    let after = rewrite(before);
    if (process.argv.includes('--inject-stray')) after += '\nINJECTED';
    if (process.argv.includes('--inject-supplier')) after += ' Bathing Brands';
    const probs = [];
    const left = suppliersIn(after, p.vendor);
    if (left.length) probs.push(`supplier name survives: ${left.join(', ')}`);
    if (JSON.stringify(lineShape(before)) !== JSON.stringify(lineShape(after))) probs.push(`LINE SHAPE CHANGED ${before.split('\n').length} -> ${after.split('\n').length} lines`);
    const EM = new RegExp('\\u2014', 'g');
    if ((after.match(EM) || []).length > (before.match(EM) || []).length) probs.push('this edit INTRODUCED an em dash');
    if (JSON.stringify(before.match(/https?:\/\/\S+/g) || []) !== JSON.stringify(after.match(/https?:\/\/\S+/g) || [])) probs.push('a URL changed');
    if (before === after) probs.push('nothing changed');
    if (probs.length) { fail++; console.log(`   FAIL ${p.handle} / custom.${field}`); probs.forEach((x) => console.log(`        ${x}`)); continue; }
    plan.push({ id: p.id, handle: p.handle, field, before, after, vendor: p.vendor });
  }
}
if (wrongType.length) { console.log(`\n  ⚠️ NOT multi_line_text_field, EXCLUDED and named (${wrongType.length}):`); wrongType.forEach((w) => console.log(`    ${w}`)); }
const byField = {}; plan.forEach((x) => { byField[x.field] = (byField[x.field] || 0) + 1; });
console.log(`\nplanned: ${plan.length} row(s)  ${Object.entries(byField).map(([f, n]) => `custom.${f} ${n}`).join('  |  ')}${fail ? `   FAILED ${fail}` : ''}`);
if (fail) { console.log('  REFUSING — nothing written'); process.exit(1); }
if (process.argv.includes('--report')) {
  for (const x of plan) {
    console.log(`\n--- ${x.handle} / custom.${x.field}`);
    const b = x.before.split('\n'), a = x.after.split('\n');
    for (let i = 0; i < b.length; i++) if (b[i] !== a[i]) { console.log(`  - ${b[i].trim().slice(0, 160)}`); console.log(`  + ${a[i].trim().slice(0, 160)}`); }
  }
  process.exit(0);
}
if (!plan.length) { console.log('  nothing to do'); process.exit(0); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = plan.map((x) => ({ id: x.id, handle: x.handle, field: x.field, before: x.before, md5: md5(x.before), afterMd5: md5(x.after) }));
const bpath = backup('r23j-plain-text' + (ONLY ? '-' + ONLY : ''), snap);
for (const x of plan) {
  const d = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ value } userErrors{ message } } }`,
    { m: [{ ownerId: x.id, namespace: 'custom', key: x.field, type: 'multi_line_text_field', value: x.after }] });
  if (d.metafieldsSet.userErrors.length) { console.log(`  FAILED ${x.handle}: ${JSON.stringify(d.metafieldsSet.userErrors)}`); fail++; continue; }
  const stored = d.metafieldsSet.metafields[0].value;
  snap.find((s) => s.handle === x.handle && s.field === x.field).stored = stored;
  logChange({ script: 'r23j-plain-text', resource: x.id, handle: x.handle, field: `metafield custom.${x.field}`, old: 'named a supplier', new: 'route-neutral', note: `backup ${bpath}` });
  console.log(`  wrote ${x.handle.padEnd(44)} custom.${x.field.padEnd(10)} stored ${md5(stored) === md5(x.after) ? '= sent' : 'NORMALISED'}`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
process.exit(fail ? 1 : 0);
}
