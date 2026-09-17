/* Round 15 — two anchors that would misdescribe their destination. --dry-run default.
 *
 *   node scripts/apply/fix-two-anchors.mjs [--apply]
 *
 * Caught BEFORE the destination shipped, which is the first time on this project.
 *
 * biophilic: the link is REMOVED, not repointed. No honest wording of "measurable biophilic
 * outcomes" points at a sauna evidence page, and an anchor that has to be rewritten to survive
 * is a link that should not exist. The sentence itself is untouched.
 *
 * are-infrared-saunas-safe: reworded to drop a steam claim and a populations claim the
 * destination does not carry.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const U = 'https://inhousewellness.com/blogs/saunas/are-saunas-good-for-you';

const EDITS = [
  { handle: 'biophilic-design-measurable-outcomes-evidence',
    from: `For those seeking <a href="${U}">measurable biophilic outcomes</a>, the critical question`,
    to: 'For those seeking measurable biophilic outcomes, the critical question',
    why: 'link removed; sentence unchanged' },
  { handle: 'are-infrared-saunas-safe',
    from: `For a broader comparison of whether<a href="${U}"> </a><a href="${U}">saunas are beneficial for health</a> across different types and populations, our comprehensive overview examines traditional, infrared, and steam options.`,
    to: `For the evidence on whether <a href="${U}">saunas are good for you</a>, including who should avoid them, our overview covers traditional and infrared use.`,
    why: 'drops the steam claim and the populations claim the destination does not carry' },
];

const rows = [];
for (const e of EDITS) {
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${e.handle}` });
  const a = q.articles.nodes.find((x) => x.handle === e.handle);
  if (!a) { console.log(`  MISSING ${e.handle}`); process.exitCode = 1; continue; }
  const n = a.body.split(e.from).length - 1;
  console.log(`  ${e.handle.padEnd(46)} matches=${n} ${n === 1 ? '' : 'FAILURE'}`);
  if (n !== 1) { process.exitCode = 1; continue; }
  const after = a.body.replace(e.from, e.to);
  assertWellFormed(after, e.handle);
  const before = (a.body.split(U).length - 1), now = (after.split(U).length - 1);
  console.log(`     ${e.why}`);
  console.log(`     links to target: ${before} -> ${now}`);
  console.log(`     - ${e.from.replace(/<[^>]+>/g, '').slice(0, 150)}`);
  console.log(`     + ${e.to.replace(/<[^>]+>/g, '').slice(0, 150)}`);
  rows.push({ id: a.id, handle: e.handle, before: a.body, after, expect: now });
}
if (process.exitCode === 1) { console.log('\n  refusing: a target failed its match count'); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('two-anchors', rows.map((r) => ({ id: r.id, handle: r.handle, before: r.before })));
for (const r of rows) {
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`,
    { id: r.id, article: { body: r.after } });
  if (m.articleUpdate.userErrors.length) { console.log(`  ERR ${r.handle}`, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  logChange({ resource: r.id, handle: r.handle, field: 'body', old: 'anchor over-promising the destination', new: r.expect ? 'anchor reworded' : 'link removed', note: 'Round 15 pre-emptive anchor fix' });
}
for (const r of rows) {
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${r.handle}` });
  const b = q.articles.nodes.find((x) => x.handle === r.handle).body;
  const links = b.split(U).length - 1;
  console.log(`  re-read ${r.handle.padEnd(46)} links to target ${links} (expected ${r.expect}) ${links === r.expect ? 'OK' : 'FAIL'}`);
  if (links !== r.expect) process.exitCode = 1;
}
