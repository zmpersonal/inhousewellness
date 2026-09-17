/* Client ruling 15 Sep 2026: Balcones #20752 is the only address. Replace suite #21140
 * on the four UNPUBLISHED pages that carry it. --dry-run default.
 *
 *   node scripts/apply/fix-suite-21140.mjs [--apply]
 *
 * Scope is the SUITE NUMBER only. Nothing else in these pages changes — not the returns
 * wording, not the parent-company line. Per-target match counts are printed and a target
 * matching zero is a FAILURE, not a skip.
 *
 * The Ben White occurrences are deliberately NOT here: one is in Settings (client only)
 * and one is a warranty product's stated business address, which is the same
 * not-cosmetic question as the billing address.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLES = ['terms-and-conditions', 'refund-and-return-policy', 'privacy-policy', 'shipping-policy'];
const FROM = '21140';
const TO = '20752';

const rows = [];
for (const handle of HANDLES) {
  const q = await gql(`query($q:String!){ pages(first:5, query:$q){ nodes{ id handle title body isPublished } } }`, { q: `handle:${handle}` });
  const p = q.pages.nodes.find((x) => x.handle === handle);
  if (!p) { console.log(`  MISSING  ${handle} — no such page`); process.exitCode = 1; continue; }
  const n = p.body.split(FROM).length - 1;
  console.log(`  ${handle.padEnd(26)} published=${p.isPublished}  matches=${n}`);
  if (n !== 1) { console.log(`     FAILURE: expected exactly 1 match, got ${n}`); process.exitCode = 1; continue; }
  if (p.isPublished) { console.log('     REFUSING: page is published; enumeration said unpublished. Re-read before writing.'); process.exitCode = 1; continue; }
  const after = p.body.split(FROM).join(TO);
  const i = p.body.indexOf(FROM);
  console.log(`     - …${p.body.slice(Math.max(0, i - 60), i + 20).replace(/\s+/g, ' ')}…`);
  console.log(`     + …${after.slice(Math.max(0, i - 60), i + 20).replace(/\s+/g, ' ')}…`);
  rows.push({ id: p.id, handle, before: p.body, after });
}
if (process.exitCode === 1) { console.log('\n  refusing to write: a target failed its match count'); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('suite-21140', rows.map((r) => ({ id: r.id, handle: r.handle, before: r.before })));

for (const r of rows) {
  const m = await gql(`mutation($id:ID!,$body:String!){ pageUpdate(id:$id, page:{ body:$body }){ page{ id } userErrors{ field message } } }`,
    { id: r.id, body: r.after });
  if (m.pageUpdate.userErrors.length) { console.log(`  ERR ${r.handle}`, m.pageUpdate.userErrors); process.exitCode = 1; continue; }
  logChange({ resource: r.id, handle: r.handle, field: 'body', old: `suite ${FROM}`, new: `suite ${TO}`, note: 'Round 14 address ruling — suite number only' });
}

/* Outcome, not the write report: re-read each page. */
let ok = 0;
for (const r of rows) {
  const q = await gql(`query($q:String!){ pages(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${r.handle}` });
  const b = q.pages.nodes.find((x) => x.handle === r.handle).body;
  const good = !b.includes(FROM) && (b.split(TO).length - 1) >= 1;
  console.log(`  re-read ${r.handle.padEnd(26)} ${FROM}:${b.split(FROM).length - 1}  ${TO}:${b.split(TO).length - 1}  ${good ? 'OK' : 'FAIL'}`);
  if (good) ok++; else process.exitCode = 1;
}
console.log(`\n  ${ok} / ${rows.length} pages now carry ${TO} and not ${FROM}`);
