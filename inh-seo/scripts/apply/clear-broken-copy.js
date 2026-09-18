/**
 * Clears descriptions that are placeholder or leaked-AI text.
 * Deliberately writes an EMPTY string rather than replacement copy —
 * these collections are in the copywriting queue and should not be
 * filled with machine-written text without review.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertFresh } from '../lib/util.js';

const flags = parseArgs();
banner('clear-broken-copy', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/broken-copy.json, data/collections.json');

assertFresh({
  'collections.json': 'npm run audit:collections',
  'broken-copy.json': 'npm run audit:broken',
});

const findings = readJSON(path.join(DATA,'broken-copy.json'))
  .filter(f => f.severity === 'P0' && f.kind === 'collection');

if (!findings.length) { console.log('No P0 collection findings. Run npm run audit:broken first.'); process.exit(0); }

const collections = readJSON(path.join(DATA,'collections.json'));
const byId = new Map(collections.map(c => [c.id, c]));
const seen = new Set();
const targets = [];
for (const f of findings) {
  if (seen.has(f.id)) continue;
  seen.add(f.id);
  const c = byId.get(f.id);
  if (c) targets.push({ ...c, reason: f.pattern });
}

console.log(`${targets.length} collection(s) with P0 broken copy:\n`);
for (const t of targets) showDiff(`${t.handle} (${t.products} products) — ${t.reason}`, t.descriptionHtml, '');

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('clear-broken-before', targets.map(t => ({ id:t.id, handle:t.handle, descriptionHtml:t.descriptionHtml })));

const M = `mutation($input: CollectionInput!){
  collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } }
}`;

for (const t of targets) {
  const r = await gql(M, { input: { id: t.id, descriptionHtml: '' } });
  if (r.collectionUpdate.userErrors.length) { console.error(`  FAILED ${t.handle}`, r.collectionUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ script:'clear-broken-copy', kind:'collection', id:t.id, handle:t.handle,
              field:'descriptionHtml', before:t.descriptionHtml, after:'' });
  console.log(`  cleared ${t.handle}`);
}
console.log('\nThese now need copy. See data/collections-plan.json.');
