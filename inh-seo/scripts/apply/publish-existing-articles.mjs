/**
 * Publishes articles that already exist but have never been published.
 *
 * Separate from publish-article.js, which creates from a markdown file. These
 * three were written, saved, and left with isPublished:false — 152,000
 * characters nobody could read, including the article this project's own claim
 * register singled out as the best writing in the estate.
 *
 * PUBLICATION STATE IS A DECISION, like deindexing. This script publishes only
 * handles named on the command line, never a set.
 *
 *   node scripts/apply/publish-existing-articles.mjs <handle> [<handle>…] [--apply]
 */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange } from '../lib/util.js';
import { captureReach, assertReach, makeFetch, reachAllowFromArgv, mergeCaptures, captureArticleMetafields, ARTICLE_REACH_QUERY } from '../lib/reach.mjs';

const flags = parseArgs();
banner('publish-existing-articles', flags);
const handles = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (!handles.length) { console.error('usage: publish-existing-articles.mjs <handle> [<handle>…] [--apply]'); process.exit(1); }

const fetchFields = makeFetch(gql, ARTICLE_REACH_QUERY, 'articles');
const capture = async () => mergeCaptures(await captureReach(fetchFields), await captureArticleMetafields(gql));

const targets = [];
for (const h of handles) {
  const r = await gql(`query($q:String!){ articles(first:10, query:$q){ nodes{ id handle title isPublished publishedAt
    t: metafield(namespace:"global", key:"title_tag"){ value }
    d: metafield(namespace:"global", key:"description_tag"){ value } } } }`, { q: 'handle:' + h });
  // guard audit 18i: a search hit is not the record — `first:1` + nodes[0] could return a different handle
  const a = r.articles.nodes.find((x) => x.handle === h);
  if (!a) { console.error(`  ✗ ${h}: NOT FOUND`); process.exit(1); }
  if (a.isPublished) { console.log(`  = ${h}: already published, skipping`); continue; }
  console.log(`\n  ${h}`);
  console.log(`    title      : ${a.title}`);
  console.log(`    title_tag  : ${a.t?.value || '(none)'}  (${(a.t?.value || '').length})`);
  console.log(`    meta       : ${(a.d?.value || '(none)').slice(0, 100)}…  (${(a.d?.value || '').length})`);
  targets.push(a);
}
if (!targets.length) { console.log('\nNothing to publish.'); process.exit(0); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('publish-existing-before', targets.map((a) => ({ id: a.id, handle: a.handle, isPublished: a.isPublished, publishedAt: a.publishedAt })));
const before = await capture();

const M = `mutation($id:ID!,$article:ArticleUpdateInput!){
  articleUpdate(id:$id, article:$article){ article{ id handle isPublished publishedAt } userErrors{ field message } } }`;
let ok = 0;
for (const a of targets) {
  const r = await gql(M, { id: a.id, article: { isPublished: true, publishDate: new Date().toISOString() } });
  if (r.articleUpdate.userErrors.length) { console.error(`  FAILED ${a.handle}:`, r.articleUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ script: 'publish-existing-articles', kind: 'article', id: a.id, handle: a.handle, field: 'isPublished',
    before: false, after: true, reason: 'Client ruling 2026-09-09. Article was written and left unpublished; no recorded reason found.' });
  ok += 1;
  console.log(`  published ${a.handle}  (${r.articleUpdate.article.publishedAt})`);
}
console.log(`\n${ok}/${targets.length} published.`);

const after = await capture();
try { assertReach(before, after, { handles: targets.map((a) => a.handle), fields: ['isPublished', 'publishedAt'] }, { allow: reachAllowFromArgv() }); }
catch (e) { console.error(`\n${e.message}`); process.exit(1); }
