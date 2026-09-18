/* B2 — write alt text for 2,882 product images. --dry-run default.
 *
 * A generated value replaces a generated value, never a hand-written one. The
 * builder holds any existing alt that does not match the machine pattern; two
 * survived and both carry view information the generator cannot produce.
 *
 * Batches of 20 through fileUpdate. Reports per-target results: a target that
 * writes zero is a FAILURE, not a skip.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, readJSON, DATA, assertOneWritePerRecord } from '../lib/util.js';
import path from 'node:path';

/* RETIRED by the Round 18i guard audit (2026-09-18): never compares the live alt with the value it replaces — a re-run overwrites alt text edited since the build.
   It ran once and its specs are consumed, so its guards can no longer be demonstrated against the live estate —
   and a guard that cannot be shown to fail is not a guard. To run it again, delete these lines in a reviewed commit. */
console.error('RETIRED (Round 18i guard audit): apply-alt-text.mjs — never compares the live alt with the value it replaces — a re-run overwrites alt text edited since the build.'); process.exit(1);

const APPLY = process.argv.includes('--apply');
const map = readJSON(path.join(DATA, 'alt-text.json'));
const rows = map.rows;

assertOneWritePerRecord(rows, (r) => r.mediaId, 'alt text');

/* Re-assert the build guards here. The builder ran them; a stale file would not. */
const bad = [
  ['over 125 chars', rows.filter((r) => r.alt.length > 125)],
  ['blank', rows.filter((r) => !r.alt.trim())],
  ['JS artefact', rows.filter((r) => /undefined|null|\[object/.test(r.alt))],
  ['dangling word', rows.filter((r) => /\b(and|with|for|the|a|an|in|of|to|or|plus|by|from)\s*,\s*image \d+ of \d+$/i.test(r.alt))],
];
for (const [name, list] of bad) {
  if (list.length) { console.log(`  ${name}: ${list.length}`); throw new Error(`refusing: ${list.length} row(s) ${name}`); }
}
const perProd = {};
for (const r of rows) (perProd[r.productHandle] = perProd[r.productHandle] || []).push(r.alt);
const dupes = Object.entries(perProd).filter(([, a]) => a.length > 1 && new Set(a).size !== a.length);
if (dupes.length) throw new Error(`refusing: ${dupes.length} product(s) with duplicate alt`);

console.log(`  rows: ${rows.length}   FILL ${rows.filter((r) => r.kind === 'FILL').length}   REPLACE ${rows.filter((r) => r.kind === 'REPLACE').length}`);
console.log(`  products: ${new Set(rows.map((r) => r.productHandle)).size}`);
console.log(`  all build guards re-asserted: clean`);

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const bpath = backup('alt-text', rows.map((r) => ({ mediaId: r.mediaId, handle: r.productHandle, pos: r.pos, was: r.was })));
console.log(`  backup -> ${bpath}\n`);

let ok = 0, fail = 0;
for (let i = 0; i < rows.length; i += 20) {
  const batch = rows.slice(i, i + 20);
  const res = await gql(`mutation($files:[FileUpdateInput!]!){ fileUpdate(files:$files){
      files{ id alt } userErrors{ field message code } } }`,
    { files: batch.map((r) => ({ id: r.mediaId, alt: r.alt })) });
  const u = res.fileUpdate;
  if (u.userErrors.length) {
    u.userErrors.forEach((e) => console.log(`  ERR ${e.code || ''} ${e.message}`));
    fail += batch.length;
    continue;
  }
  /* Per-target check: every id sent must come back, and come back with OUR value. */
  const back = new Map(u.files.map((f) => [f.id, f.alt]));
  for (const r of batch) {
    if (!back.has(r.mediaId)) { console.log(`  MISSING ${r.productHandle} pos ${r.pos}`); fail++; continue; }
    if (back.get(r.mediaId) !== r.alt) { console.log(`  MISMATCH ${r.productHandle} pos ${r.pos}`); fail++; continue; }
    ok++;
  }
  if ((i / 20) % 25 === 0) console.log(`  ${ok + fail}/${rows.length}`);
}
logChange({ resource: 'product-media', type: 'batch', field: 'image.altText',
  from: `${rows.filter((r) => r.kind === 'REPLACE').length} machine-stuffed + ${rows.filter((r) => r.kind === 'FILL').length} blank`,
  to: 'title + image position', note: `B2 alt text, ${ok} images, 2 hand-written held`, backup: bpath });
console.log(`\n  applied ${ok}/${rows.length}   failed ${fail}`);
if (fail) process.exitCode = 1;
