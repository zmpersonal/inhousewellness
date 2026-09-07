import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, cleanHTML, assertFresh } from '../lib/util.js';

const flags = parseArgs();
banner('strip-markup', flags);

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

backup('strip-markup-before', targets.map(t => ({ id: t.id, handle: t.handle, descriptionHtml: t.descriptionHtml })));

const M = `mutation($input: CollectionInput!){
  collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } }
}`;

for (const t of targets) {
  const r = await gql(M, { input: { id: t.id, descriptionHtml: t.cleaned } });
  const errs = r.collectionUpdate.userErrors;
  if (errs.length) { console.error(`  FAILED ${t.handle}:`, errs); continue; }
  logChange({ script:'strip-markup', kind:'collection', id:t.id, handle:t.handle,
              field:'descriptionHtml', before:t.descriptionHtml, after:t.cleaned });
  console.log(`  cleaned ${t.handle}`);
}
console.log('\nDone. Re-run npm run audit:collections to verify.');
