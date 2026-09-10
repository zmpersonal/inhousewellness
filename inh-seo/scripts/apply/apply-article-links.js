/**
 * B3 — adds collection links to blog articles. Never removes anything.
 *
 * Input: data/b3-link-plan.json, which is per-article JUDGEMENT, not a matcher
 * score. Read the plan's _meta before running this.
 *
 * WHAT IT DOES, precisely: appends one "Where to go next" block at the end of
 * the article body. It does NOT rewrite prose to insert contextual anchors.
 *
 * That is a deliberate limit, not a shortcut. A contextual in-body link is the
 * stronger asset, and placing one means choosing a sentence and an anchor
 * phrase — a copy decision. Machine-inserting anchors into 43 live articles is
 * how you end up with "the best [cold plunge](/collections/cold-plunge) for
 * your [cold plunge](/collections/cold-plunge)". The block ships the routing;
 * the top articles can be hand-placed afterwards.
 *
 * Idempotent: the block is fenced by an HTML comment marker and replaced, never
 * duplicated. Running twice changes nothing the second time.
 *
 *   node scripts/apply/apply-article-links.js                # dry run
 *   node scripts/apply/apply-article-links.js --only <h>     # one article
 *   node scripts/apply/apply-article-links.js --apply
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach, makeFetch, reachAllowFromArgv, ARTICLE_REACH_QUERY } from '../lib/reach.mjs';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';

const flags = parseArgs();
banner('apply-article-links', flags);
console.log('  READS FROM: data/b3-link-plan.json');

const MARK_OPEN = '<!-- inh-seo:related-collections -->';
const MARK_CLOSE = '<!-- /inh-seo:related-collections -->';

const plan = readJSON(path.join(DATA, 'b3-link-plan.json'));
const collections = readJSON(path.join(DATA, 'collections.json'));
const byHandle = new Map(collections.map((c) => [c.handle, c]));

/* Anchor text is the SEO title's leading segment — the primary keyword phrase,
   already reviewed. Falls back to the collection title, which on this store is
   sometimes shouty ("FAR Infrared"). */
const anchor = (h) => {
  const c = byHandle.get(h);
  if (!c) return null;
  const lead = (c.seoTitle || '').split('|')[0].trim();
  return lead || c.title;
};

const rows = [
  ...plan.part_1_misdirected_product_links.rows,
  ...plan.part_2_dead_end_articles.rows,
].filter((r) => r.add?.length);

const Q = `query($after:String){
  articles(first:100, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{ id handle title body blog{ handle } }
  }
}`;
const live = [];
let cursor = null;
for (;;) {
  const d = await gql(Q, { after: cursor });
  live.push(...d.articles.nodes);
  if (!d.articles.pageInfo.hasNextPage) break;
  cursor = d.articles.pageInfo.endCursor;
}
const arts = new Map(live.map((a) => [a.handle, a]));

const targets = [], skipped = [];
for (const r of rows) {
  if (flags.only && !flags.only.includes(r.article)) continue;
  const a = arts.get(r.article);
  if (!a) { skipped.push([r.article, 'no such article']); continue; }
  const bad = r.add.filter((h) => !byHandle.has(h));
  if (bad.length) { skipped.push([r.article, `unknown collection: ${bad.join(', ')}`]); continue; }

  const items = r.add.map((h) => `<li><a href="/collections/${h}">${anchor(h)}</a></li>`).join('');
  const block = `${MARK_OPEN}\n<h2>Where to go next</h2>\n<ul>${items}</ul>\n${MARK_CLOSE}`;
  const current = a.body || '';
  const stripped = current.includes(MARK_OPEN)
    ? current.replace(new RegExp(`${MARK_OPEN}[\\s\\S]*?${MARK_CLOSE}`), '').trimEnd()
    : current.trimEnd();
  const next = `${stripped}\n${block}`;
  if (next === current) { skipped.push([r.article, 'already matches — no-op']); continue; }

  /* Never remove a product link (ruling 1). Count them before and after and
     refuse the whole run if the number moves — appending cannot drop one, so a
     difference means the body was mangled, not edited. */
  const count = (s) => (s.match(/href="[^"]*\/products\//gi) || []).length;
  if (count(next) !== count(current)) {
    console.error(`REFUSING — ${r.article}: product links ${count(current)} -> ${count(next)}. Ruling 1 says never remove one.`);
    process.exit(1);
  }
  targets.push({ a, next, current, add: r.add, block });
}

if (skipped.length) {
  console.log('Skipped:\n');
  for (const [h, why] of skipped) console.log(`  ${h.padEnd(56)} ${why}`);
  console.log('');
}
if (!targets.length) { console.log('Nothing to apply.'); process.exit(0); }

console.log(`${targets.length} article(s) to update, ${targets.reduce((n, t) => n + t.add.length, 0)} collection link(s) added, 0 removed:\n`);
assertOneWritePerRecord(targets, (t) => t.a.handle, 'apply-article-links');

for (const t of targets) showDiff(`${t.a.blog.handle}/${t.a.handle}`, '(no related block)', t.block.replace(/\n/g, ' '));

for (const t of targets) assertWellFormed(t.next, `${t.a.handle} body`, t.current);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('article-bodies-before', targets.map((t) => ({ id: t.a.id, handle: t.a.handle, blog: t.a.blog.handle, body: t.current })));

/* REACH GUARD — reports/reach-guard.md. Captures the WHOLE record for every
   article this batch could touch. The capture doubles as the rollback source,
   which is what makes an after-the-fact check acceptable. */
const _fetchReach = makeFetch(gql, ARTICLE_REACH_QUERY, 'articles');
const _reachBefore = await captureReach(_fetchReach);
const _reachDeclared = { handles: targets.map((t) => t.a?.handle ?? t.handle), fields: ['body'] };


const M = `mutation($id:ID!, $body:HTML!){
  articleUpdate(id:$id, article:{ body:$body }) {
    article { id handle }
    userErrors { field message }
  }
}`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { id: t.a.id, body: t.next });
  const errs = r.articleUpdate.userErrors;
  if (errs.length) { console.error(`  FAILED ${t.a.handle}:`, errs); continue; }
  logChange({ script: 'apply-article-links', kind: 'article', id: t.a.id, handle: t.a.handle,
    field: 'body', before: `(${t.current.length} chars, no related block)`, after: `+${t.add.length} collection link(s): ${t.add.join(', ')}` });
  ok += 1;
  console.log(`  updated ${t.a.handle}  (+${t.add.length})`);
}
console.log(`\n${ok}/${targets.length} applied. Verify with a live fetch — the field is not the page (instance 31).`);

const _reachAfter = await captureReach(_fetchReach);
try {
  assertReach(_reachBefore, _reachAfter, _reachDeclared, { allow: reachAllowFromArgv() });
} catch (e) {
  console.error(`\n${e.message}`);
  console.error('The reach capture holds the full before-state. Roll back from it.');
  process.exit(1);
}
