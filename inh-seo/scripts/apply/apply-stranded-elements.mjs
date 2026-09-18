/* Answer-first openings on five articles. --dry-run default.
 *
 * Anchors are sliced from the LIVE body, never written from rendered text.
 * Refuses on any anchor not matching exactly once. Verifies by re-running the
 * MEASUREMENT afterwards, not by reading the write back.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, readJSON, DATA, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');
const spec = readJSON(path.join(DATA, 'stranded-element-edits.json'));
assertOneWritePerRecord(spec.edits, (e) => e.handle, 'answer-first');

let after = null, arts = [];
for (;;) {
  const r = await gql(`query($a:String){ articles(first:100, after:$a){ pageInfo{hasNextPage endCursor}
    nodes{ id handle title body } } }`, { a: after });
  arts.push(...r.articles.nodes);
  if (!r.articles.pageInfo.hasNextPage) break;
  after = r.articles.pageInfo.endCursor;
}

const jobs = [];
for (const e of spec.edits) {
  const a = arts.find((x) => x.handle === e.handle);
  if (!a) throw new Error(`article not found: ${e.handle}`);
  const n = a.body.split(e.from).length - 1;
  console.log(`  ${n}x  ${e.handle}`);
  if (n !== 1) throw new Error(`${e.handle}: anchor matched ${n} times, expected 1`);
  const body = a.body.replace(e.from, e.to);
  assertWellFormed(body, e.handle, a.body);
  jobs.push({ id: a.id, handle: e.handle, before: a.body, after: body, e });
}

console.log('\n  DIFFS\n');
for (const j of jobs) {
  console.log(`  ── ${j.handle}`);
  console.log(`     - ${j.e.from.slice(0, 150)}`);
  console.log(`     + ${j.e.to.slice(0, 150)}`);
  console.log(`     Δ chars ${j.after.length - j.before.length}`);
}

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const bpath = backup('answer-first', jobs.map((j) => ({ handle: j.handle, id: j.id, body: j.before })));
console.log(`\n  backup -> ${bpath}`);

let ok = 0;
for (const j of jobs) {
  const r = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){
      article{ id } userErrors{ field message } } }`, { id: j.id, article: { body: j.after } });
  if (r.articleUpdate.userErrors.length) { console.log(`  FAIL ${j.handle}: ${JSON.stringify(r.articleUpdate.userErrors)}`); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ resource: j.id, handle: j.handle, type: 'article', field: 'body',
    from: j.e.from, to: j.e.to, note: `answer-first opening: ${j.e.why}`, backup: bpath });
  ok++;
}
console.log(`\n  applied ${ok}/${jobs.length}`);
if (ok !== jobs.length) process.exitCode = 1;
