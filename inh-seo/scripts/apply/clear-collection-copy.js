/**
 * Clears collection descriptions to empty, by handle.
 *
 * Distinct from clear-broken-copy.js, which only ever targets P0 findings from
 * the broken-copy scan. This one takes an explicit --only list, because the
 * reason for clearing is editorial rather than mechanical: copy that renders
 * nowhere today but would become visible, and has not been reviewed.
 *
 * Requires --only. It will not clear the whole store by omission.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import {
  readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertFresh,
} from '../lib/util.js';

const flags = parseArgs();
banner('clear-collection-copy', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/collections.json');

assertFresh({ 'collections.json': 'npm run audit:collections' });

if (!flags.only || !flags.only.length) {
  console.error('Refusing to run without --only. Pass the handles explicitly:');
  console.error('  npm run fix:clear-copy -- --only handle-a,handle-b');
  process.exit(1);
}

const collections = readJSON(path.join(DATA, 'collections.json'));
const byHandle = new Map(collections.map((c) => [c.handle, c]));

const targets = [];
const skipped = [];
for (const h of flags.only) {
  const c = byHandle.get(h);
  if (!c) { skipped.push([h, 'no such collection']); continue; }
  if (c.descriptionLength === 0) { skipped.push([h, 'already empty — no-op']); continue; }
  targets.push(c);
}

if (skipped.length) {
  console.log('Skipped:\n');
  for (const [h, why] of skipped) console.log(`  ${h.padEnd(44)} ${why}`);
  console.log('');
}

if (!targets.length) { console.log('Nothing to clear.'); process.exit(0); }

console.log(`${targets.length} description(s) will be cleared to empty:\n`);
for (const c of targets) {
  showDiff(`${c.handle} (${c.products} products, ${c.descriptionLength} chars)`, c.descriptionHtml, '');
  console.log(`      meta description: ${c.seoDescription ? 'present — head unaffected' : 'ABSENT — head falls through to the generic string'}`);
}

console.log(`\n  ${targets.length} of ${flags.only.length} requested. Descriptions are recoverable from the backup below.`);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('clear-collection-copy-before', targets.map((c) => ({
  id: c.id, handle: c.handle, descriptionHtml: c.descriptionHtml, seoDescription: c.seoDescription,
})));

const M = `mutation($input: CollectionInput!){
  collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } }
}`;

let ok = 0;
for (const c of targets) {
  const r = await gql(M, { input: { id: c.id, descriptionHtml: '' } });
  const errs = r.collectionUpdate.userErrors;
  if (errs.length) { console.error(`  FAILED ${c.handle}:`, errs); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({
    script: 'clear-collection-copy', kind: 'collection', id: c.id, handle: c.handle,
    field: 'descriptionHtml', before: c.descriptionHtml, after: '',
  });
  ok += 1;
  console.log(`  cleared ${c.handle}`);
}
console.log(`\n${ok}/${targets.length} cleared. These now need copy — add them to the sweep queue.`);
