/**
 * Applies SEO titles and meta descriptions from collections-plan.json.
 * By default only FILLS EMPTY fields — existing metas are not overwritten
 * unless --overwrite is passed.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach } from '../lib/reach.mjs';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertFresh } from '../lib/util.js';

const flags = parseArgs();
const overwrite = process.argv.includes('--overwrite');
banner('apply-seo-fields' + (overwrite ? ' --overwrite' : ''), flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/collections-plan.json, data/collections.json');

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
  /* Shopify treats `seo` as a WHOLE OBJECT: sending { description } with no
     title sets the title to NULL. Writing metas to five collections that already
     had titles deleted all five, and showDiff printed only the description —
     a diff that shows one change while the mutation makes two.
     Always carry the field we are not changing. */
  if (seo.description !== undefined && seo.title === undefined && c.seoTitle) seo.title = c.seoTitle;
  if (seo.title !== undefined && seo.description === undefined && c.seoDescription) seo.description = c.seoDescription;
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

/* REACH GUARD. Captures the WHOLE collection object for every record this batch
   could touch — not the fields the plan names. The capture doubles as the
   rollback source, which is what makes an after-the-fact check acceptable.
   See reports/reach-guard.md and scripts/audit/reach-selftest.mjs. */
const REACH_QUERY = `query($after:String){ collections(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle title descriptionHtml sortOrder templateSuffix seo{ title description } } } }`;
const fetchReach = async () => {
  const out = []; let after = null, more = true;
  while (more) { const r = await gql(REACH_QUERY, { after }); out.push(...r.collections.nodes);
    more = r.collections.pageInfo.hasNextPage; after = r.collections.pageInfo.endCursor; }
  return out;
};
const reachBefore = await captureReach(fetchReach);
/* The declaration is written by the AUTHOR, so it records what they believed —
   which is exactly the step all three regressions skipped. */
const declaredFields = [];
if (targets.some(t => t.seo.title !== undefined)) declaredFields.push('seo.title');
if (targets.some(t => t.seo.description !== undefined)) declaredFields.push('seo.description');
const declared = { handles: targets.map(t => t.c.handle), fields: declaredFields };
const reachOk = (() => { const i = process.argv.indexOf('--reach-ok'); return i > -1 ? process.argv[i+1].split(',') : []; })();

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

const reachAfter = await captureReach(fetchReach);
try {
  assertReach(reachBefore, reachAfter, declared, { allow: reachOk });
} catch (e) {
  console.error(`\n${e.message}`);
  console.error('ROLLBACK SOURCE: data/backups/ holds the declared fields, and the reach capture holds the rest.');
  console.error('Nothing has been rolled back automatically — read the collateral above and decide.');
  process.exit(1);
}
