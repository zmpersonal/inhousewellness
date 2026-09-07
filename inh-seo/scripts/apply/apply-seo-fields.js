/**
 * Applies SEO titles and meta descriptions from collections-plan.json.
 * By default only FILLS EMPTY fields — existing metas are not overwritten
 * unless --overwrite is passed.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertFresh } from '../lib/util.js';

const flags = parseArgs();
const overwrite = process.argv.includes('--overwrite');
banner('apply-seo-fields' + (overwrite ? ' --overwrite' : ''), flags);

assertFresh({ 'collections.json': 'npm run audit:collections' });

const plan = readJSON(path.join(DATA,'collections-plan.json'));
const collections = readJSON(path.join(DATA,'collections.json'));
const byHandle = new Map(collections.map(c=>[c.handle,c]));

const targets = [];
for (const p of plan) {
  if (flags.only && !flags.only.includes(p.handle)) continue;
  const c = byHandle.get(p.handle);
  if (!c) continue;
  const seo = {};
  if (p.newSeoTitle && (overwrite || !c.seoTitle)) seo.title = p.newSeoTitle;
  if (p.newMetaDescription && (overwrite || !c.seoDescription)) seo.description = p.newMetaDescription;
  if (Object.keys(seo).length) targets.push({ c, p, seo });
}

if (!targets.length) {
  console.log('Nothing to apply. Fill newSeoTitle / newMetaDescription in collections-plan.json.');
  process.exit(0);
}

const tooLong = targets.filter(t => (t.seo.title||'').length > 60 || (t.seo.description||'').length > 155);
if (tooLong.length) {
  console.log('WARNING — over recommended length:\n');
  for (const t of tooLong) {
    if ((t.seo.title||'').length > 60) console.log(`  ${t.c.handle}: title ${t.seo.title.length} chars (max 60)`);
    if ((t.seo.description||'').length > 155) console.log(`  ${t.c.handle}: meta ${t.seo.description.length} chars (max 155)`);
  }
  console.log('');
}

console.log(`${targets.length} collection(s) to update:\n`);
for (const t of targets) {
  if (t.seo.title) showDiff(`${t.c.handle} — SEO title`, t.c.seoTitle, t.seo.title);
  if (t.seo.description) showDiff(`${t.c.handle} — meta description`, t.c.seoDescription, t.seo.description);
}

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('seo-fields-before', targets.map(t=>({ id:t.c.id, handle:t.c.handle, seoTitle:t.c.seoTitle, seoDescription:t.c.seoDescription })));

const M = `mutation($input: CollectionInput!){
  collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } }
}`;

for (const t of targets) {
  const r = await gql(M, { input: { id: t.c.id, seo: t.seo } });
  if (r.collectionUpdate.userErrors.length) { console.error(`  FAILED ${t.c.handle}`, r.collectionUpdate.userErrors); continue; }
  logChange({ script:'apply-seo-fields', kind:'collection', id:t.c.id, handle:t.c.handle,
              field:'seo', before:{title:t.c.seoTitle, description:t.c.seoDescription}, after:t.seo });
  console.log(`  updated ${t.c.handle}`);
}
