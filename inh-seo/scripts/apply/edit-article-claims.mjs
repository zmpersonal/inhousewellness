/**
 * Applies the article-side claim corrections in data/article-claim-edits.json.
 *
 * The product-side twin is cut-product-claims.mjs. The difference is ownership:
 * product claims arrived in supplier copy and were mostly cut. Article claims
 * are OURS, and the fix is almost always a rewrite, not a deletion — so this
 * script does exact-string substitution and nothing clever.
 *
 * It reads the LIVE body from the Admin API, not from data/content.json. A dump
 * is a belief about the store; the mutation has to be built on what is there.
 *
 * A `from` that matches ZERO times is a FAILURE, not a skip: exit non-zero and
 * make the operator decide. A partial match across a set is the dangerous
 * outcome — it looks deliberate and raises nothing.
 *
 * Idempotent: a row whose `to` is already present and whose `from` is gone is
 * reported as already-applied, not as a miss.
 *
 *   node scripts/apply/edit-article-claims.mjs                 # dry run, all
 *   node scripts/apply/edit-article-claims.mjs --only <handle>
 *   node scripts/apply/edit-article-claims.mjs --apply
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach, makeFetch, reachAllowFromArgv, ARTICLE_REACH_QUERY } from '../lib/reach.mjs';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';

const flags = parseArgs();
banner('edit-article-claims', flags);
console.log('  READS FROM: data/article-claim-edits.json');

const only = (() => { const i = process.argv.indexOf('--only'); return i > -1 ? process.argv[i + 1] : null; })();
const plan = readJSON(path.join(DATA, 'article-claim-edits.json'));
const rows = plan.edits.filter((e) => !only || e.handle === only);
if (!rows.length) { console.error(only ? `no edit row for ${only}` : 'no edit rows'); process.exit(1); }

const Q = `query($after:String){ articles(first:100, after:$after){
  pageInfo{ hasNextPage endCursor } nodes{ id handle title body } } }`;
const live = new Map();
for (let after = null, more = true; more;) {
  const r = await gql(Q, { after });
  for (const n of r.articles.nodes) live.set(n.handle, n);
  more = r.articles.pageInfo.hasNextPage; after = r.articles.pageInfo.endCursor;
}
console.log(`  live articles: ${live.size}\n`);

/* Two edit rows may name the SAME article. Each row must build on the previous
   row's result, not on the snapshot: reading a.body twice and writing twice makes
   the last write erase the first, and the reach guard cannot see it because body
   is a DECLARED field for that handle. Cost one link, silently, 9 Sep 2026. */
const working = new Map();      // handle -> body as edited so far this run
const targetByHandle = new Map();
let hardFail = false;

for (const e of rows) {
  const a = live.get(e.handle);
  if (!a) { console.error(`✗ ${e.handle}: NOT FOUND live`); hardFail = true; continue; }
  let body = working.has(e.handle) ? working.get(e.handle) : a.body;
  let applied = 0, already = 0;
  console.log(`── ${e.handle}  [${e.verdict}]`);
  console.log(`   ${e.why}\n`);

  for (const s of e.subs) {
    const n = body.split(s.from).length - 1;
    if (n === 0) {
      /* Distinguish "already done" from "never matched". Collapsing them is how
         a re-run reports success over an edit that never landed. */
      /* Guard audit 18i: for a DELETION (to === '') this was always true — every string includes '' — so a stale
         deletion spec read as "already applied". A deletion's absence cannot be told from a stale spec; it must be
         recorded in the plan (supersededBy / appliedAt) or it fails. */
      if (s.to !== '' && body.includes(s.to)) { already += 1; console.log(`   = already applied: "${s.from.slice(0, 60)}…"`); continue; }
      if (s.to === '' && s.appliedAt) { already += 1; console.log(`   = deletion recorded as applied ${s.appliedAt}`); continue; }
      /* A LATER edit can consume an earlier edit's output, so neither `from` nor
         `to` survives verbatim. That is not a stale spec and it is not a silent
         skip: it must be recorded IN THE PLAN, by hand, naming what replaced it.
         Without this the whole-plan run fails forever on a row that is done. */
      if (s.supersededBy) { already += 1; console.log(`   = superseded: ${s.supersededBy}`); continue; }
      console.error(`   ✗ NO MATCH: "${s.from.slice(0, 90)}…"`);
      hardFail = true; continue;
    }
    if (n > 1) console.log(`   ! ${n} occurrences — all will be replaced`);
    body = body.split(s.from).join(s.to);
    applied += n;
    console.log(`   − ${s.from}`);
    console.log(`   + ${s.to}`);
    if (s.note) console.log(`     (${s.note})`);
  }
  console.log('');
  working.set(e.handle, body);
  if (body === a.body) { console.log(`   nothing to change (${already} already applied)\n`); continue; }
  assertWellFormed(body, e.handle, a.body);
  showDiff(e.handle, a.body, body);
  const prev = targetByHandle.get(e.handle);
  targetByHandle.set(e.handle, { a, body, applied: (prev ? prev.applied : 0) + applied });
}

const targets = [...targetByHandle.values()];
if (hardFail) { console.error('\nAt least one `from` matched zero times. Nothing applied. Fix the plan or re-dump.'); process.exit(1); }
if (!targets.length) { console.log('\nNo changes to make.'); process.exit(0); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('article-claims-before', targets.map((t) => ({ id: t.a.id, handle: t.a.handle, title: t.a.title, body: t.a.body })));

/* REACH GUARD — reports/reach-guard.md. Captures the WHOLE record for every
   article this batch could touch. The capture doubles as the rollback source,
   which is what makes an after-the-fact check acceptable. */
const _fetchReach = makeFetch(gql, ARTICLE_REACH_QUERY, 'articles');
const _reachBefore = await captureReach(_fetchReach);
const _reachDeclared = { handles: targets.map((t) => t.a.handle), fields: ['body', 'title'] };


const M = `mutation($id:ID!,$article:ArticleUpdateInput!){
  articleUpdate(id:$id, article:$article){ article{ id handle } userErrors{ field message } } }`;
let ok = 0;
assertOneWritePerRecord(targets, (t) => t.a.handle, 'edit-article-claims');

for (const t of targets) {
  const r = await gql(M, { id: t.a.id, article: { body: t.body } });
  if (r.articleUpdate.userErrors.length) { console.error(`  FAILED ${t.a.handle}:`, r.articleUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ script: 'edit-article-claims', kind: 'article', id: t.a.id, handle: t.a.handle, field: 'body',
    before: `${t.a.body.length} chars`, after: `${t.body.length} chars, ${t.applied} substitution(s)` });
  ok += 1;
  console.log(`  updated ${t.a.handle}`);
}
console.log(`\n${ok}/${targets.length} applied.`);

/* Guard audit 18i: the exit used to sit ABOVE this block, so the reach guard was dead code — the before-capture
   was taken and never compared. The reach check runs first now, and the run's exit waits for it. */
const _reachAfter = await captureReach(_fetchReach);
try {
  assertReach(_reachBefore, _reachAfter, _reachDeclared, { allow: reachAllowFromArgv() });
} catch (e) {
  console.error(`\n${e.message}`);
  console.error('The reach capture holds the full before-state. Roll back from it.');
  process.exit(1);
}
process.exit(ok === targets.length ? 0 : 1);
