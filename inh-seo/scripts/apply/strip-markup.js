import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, cleanHTML, assertFresh } from '../lib/util.js';

const flags = parseArgs();
banner('strip-markup', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/collections.json');

assertFresh({ 'collections.json': 'npm run audit:collections' });

const collections = readJSON(path.join(DATA,'collections.json'));
const targets = collections
  .filter(c => c.descriptionHtml)
  .map(c => ({ ...c, cleaned: cleanHTML(c.descriptionHtml) }))
  .filter(c => c.cleaned !== c.descriptionHtml)
  .filter(c => !flags.only || flags.only.includes(c.handle));

if (!targets.length) { console.log('Nothing to clean.'); process.exit(0); }

console.log(`${targets.length} collection(s) have markup residue:\n`);
for (const t of targets) {
  showDiff(`${t.handle} (${t.products} products)`, t.descriptionHtml, t.cleaned);
}

if (!flags.apply) {
  console.log(`\nDry run. Re-run with --apply to write these ${targets.length} changes.`);
  process.exit(0);
}

/* Guard audit 18i: this writes cleanHTML(DUMP value). assertFresh cannot see an admin or other-session edit, so a
   live description edited since the dump would be silently reverted (instance 55's shape). Re-read live first and
   refuse any target whose live value is not the dumped one. */
const LIVEQ = `query($id:ID!){ collection(id:$id){ descriptionHtml } }`;
const drifted = [];
for (const t of targets) { const l = (await gql(LIVEQ, { id: t.id })).collection?.descriptionHtml; if (l !== t.descriptionHtml) drifted.push(t.handle); }
if (drifted.length) { console.error(`REFUSING — live differs from the dump for: ${drifted.join(', ')}. Re-dump; writing would revert an edit.`); process.exit(1); }
backup('strip-markup-before', targets.map(t => ({ id: t.id, handle: t.handle, descriptionHtml: t.descriptionHtml })));

const M = `mutation($input: CollectionInput!){
  collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } }
}`;

for (const t of targets) {
  const r = await gql(M, { input: { id: t.id, descriptionHtml: t.cleaned } });
  const errs = r.collectionUpdate.userErrors;
  if (errs.length) { console.error(`  FAILED ${t.handle}:`, errs); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ script:'strip-markup', kind:'collection', id:t.id, handle:t.handle,
              field:'descriptionHtml', before:t.descriptionHtml, after:t.cleaned });
  console.log(`  cleaned ${t.handle}`);
}
console.log('\nDone. Re-run npm run audit:collections to verify.');
