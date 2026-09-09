/**
 * Strips literal `{#anchor}` markdown fragments from article bodies.
 *
 * 176 instances across 14 live articles, rendering as visible text — usually
 * inside an <h2>, e.g. "Interactive Calculator: Estimate Your Monthly and
 * Annual Costs {#calculator}". Markdown anchor syntax that was never converted.
 *
 * PURE DELETION with no editorial judgement: `{#slug}` has no legitimate use in
 * stored HTML, and the pattern carries a control proving it stays silent on CSS,
 * hex colours and real `id` attributes.
 *
 * Strips the anchor AND the whitespace before it, so a heading does not end in a
 * stray space. Does NOT touch `id=` attributes — the in-page jump targets are
 * separate markup and removing these does not break them.
 *
 *   node scripts/apply/strip-markdown-anchors.mjs            # dry run
 *   node scripts/apply/strip-markdown-anchors.mjs --apply
 */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange, assertWellFormed } from '../lib/util.js';
import { captureReach, assertReach, makeFetch, reachAllowFromArgv, ARTICLE_REACH_QUERY } from '../lib/reach.mjs';

const flags = parseArgs();
banner('strip-markdown-anchors', flags);

const RE = /\s*\{#[a-z0-9][a-z0-9-]*\}/gi;

const fetchArticles = makeFetch(gql, ARTICLE_REACH_QUERY, 'articles');
const live = await fetchArticles();

const targets = [];
for (const a of live) {
  const body = String(a.body || '');
  const n = (body.match(RE) || []).length;
  if (!n) continue;
  const next = body.replace(RE, '');
  assertWellFormed(next, a.handle, body);
  targets.push({ a, body: next, n });
}

if (!targets.length) { console.log('No literal markdown anchors found.'); process.exit(0); }
console.log(`${targets.length} article(s), ${targets.reduce((s, t) => s + t.n, 0)} instance(s):\n`);
for (const t of targets) {
  const sample = (String(t.a.body).match(/[^<>]{0,60}\{#[a-z0-9-]+\}[^<>]{0,20}/i) || [''])[0].trim();
  console.log(`  ${String(t.n).padStart(3)}  ${t.a.handle}`);
  console.log(`       e.g. "${sample}"`);
}
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('markdown-anchors-before', targets.map((t) => ({ id: t.a.id, handle: t.a.handle, body: t.a.body })));
const reachBefore = await captureReach(fetchArticles);
const declared = { handles: targets.map((t) => t.a.handle), fields: ['body'] };

const M = `mutation($id:ID!,$article:ArticleUpdateInput!){
  articleUpdate(id:$id, article:$article){ article{ id handle } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { id: t.a.id, article: { body: t.body } });
  if (r.articleUpdate.userErrors.length) { console.error(`  FAILED ${t.a.handle}:`, r.articleUpdate.userErrors); continue; }
  logChange({ script: 'strip-markdown-anchors', kind: 'article', id: t.a.id, handle: t.a.handle, field: 'body',
    before: `${t.a.body.length} chars`, after: `${t.body.length} chars, ${t.n} literal anchor(s) removed` });
  ok += 1; console.log(`  cleaned ${t.a.handle}`);
}
console.log(`\n${ok}/${targets.length} applied.`);

const reachAfter = await captureReach(fetchArticles);
try { assertReach(reachBefore, reachAfter, declared, { allow: reachAllowFromArgv() }); }
catch (e) { console.error(`\n${e.message}`); process.exit(1); }
