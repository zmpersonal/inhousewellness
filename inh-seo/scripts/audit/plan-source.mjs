/* Which apply scripts SELECT their targets from a stored dump, and which re-read live?
 *
 * Round 23: a product published between the dry run and the apply was picked up because the
 * splicer re-reads live. A script that plans from a dump would have skipped it and reported clean —
 * the omission is invisible, where an overrun is visible. This names which is which.
 *
 *   node scripts/audit/plan-source.mjs            list every apply script
 *   node scripts/audit/plan-source.mjs --self-test
 *
 * READ-ONLY. Anchors on the AST-ish shape of the calls, not on prose: a comment mentioning
 * assertFresh must not count as calling it (six tests in this repo have made that mistake).
 */
import fs from 'node:fs';
import path from 'node:path';

const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
/* A gql() call is a READ or a WRITE depending on its document. Counting every gql() as a live read
   classes a dump-planned script that merely WRITES over the API as live — which is the distinction
   this audit exists to draw, so it has to be drawn on the document, not on the call. */
const gqlBodies = (code) => [...code.matchAll(/\bgql\s*\(\s*`([\s\S]*?)`/g)].map((m) => m[1]);
export function classify(src) {
  const code = stripComments(src);
  const bodies = gqlBodies(code);
  const WRITE_RX = /metafieldsSet|productUpdate|themeFilesUpsert|collectionUpdate|pageUpdate|pageCreate|articleUpdate|publishablePublish|publishableUnpublish|urlRedirectCreate|themeDuplicate|productSet/;
  const live = bodies.some((b) => !/\bmutation\b/.test(b)) || /\bpaginate\s*\(/.test(code);
  const dump = /readJSON\s*\(/.test(code) || /JSON\.parse\(\s*fs\.readFileSync/.test(code);
  const fresh = /\bassertFresh\s*\(/.test(code);
  const writes = bodies.some((b) => WRITE_RX.test(b)) || WRITE_RX.test(code.replace(/`[\s\S]*?`/g, ''));
  return { live, dump, fresh, writes };
}
export function verdict(c) {
  if (!c.writes) return 'no writes';
  if (c.live && !c.dump) return 'LIVE — a late arrival is picked up';
  if (c.live && c.dump) return c.fresh ? 'mixed, assertFresh present' : 'MIXED, no assertFresh';
  if (c.dump) return c.fresh ? 'DUMP, assertFresh present — a late arrival is still SKIPPED' : 'DUMP, no assertFresh — SKIPS a late arrival silently';
  return 'neither';
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  eq('live selection', verdict(classify('await gql(`q`); await gql(`mutation{metafieldsSet}`)')), 'LIVE — a late arrival is picked up');
  eq('dump selection', verdict(classify('const d=readJSON(p); await gql(`mutation{metafieldsSet}`)')), 'DUMP, no assertFresh — SKIPS a late arrival silently');
  eq('dump + assertFresh', verdict(classify('assertFresh(["x"]); const d=readJSON(p); gql(`mutation{metafieldsSet}`)')), 'DUMP, assertFresh present — a late arrival is still SKIPPED');
  eq('read-only script', verdict(classify('await gql(`query{shop{name}}`)')), 'no writes');
  // the case the implementation was not built for: the words in a COMMENT must not count
  eq('a comment naming assertFresh does not count', classify('/* we call assertFresh( here */ readJSON(p); gql(`metafieldsSet`)').fresh, false);
  eq('a // comment naming readJSON does not count', classify('// readJSON(p)\ngql(`metafieldsSet`)').dump, false);
  eq('a url with // is not a comment', classify('const u="https://x.test"; readJSON(p); gql(`metafieldsSet`)').dump, true);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds, including a comment that must not count\n');
if (process.argv.includes('--self-test')) process.exit(0);

const dir = 'scripts/apply';
const out = [];
for (const f of fs.readdirSync(dir).filter((x) => /\.(mjs|js)$/.test(x)).sort()) {
  const src = fs.readFileSync(path.join(dir, f), 'utf8');
  if (/REFUSING|retired|consumed one-shot/i.test(src.slice(0, 1200)) && /process\.exit\(1\)/.test(src.slice(0, 1500))) { out.push([f, 'retired one-shot']); continue; }
  out.push([f, verdict(classify(src))]);
}
const groups = {};
out.forEach(([f, v]) => { (groups[v] ||= []).push(f); });
for (const v of Object.keys(groups).sort()) {
  console.log(`${v}  (${groups[v].length})`);
  if (/DUMP|MIXED/.test(v)) groups[v].forEach((f) => console.log(`     ${f}`));
}
const risky = out.filter(([, v]) => /^DUMP/.test(v)).length;
console.log(`\n  ${risky} write script(s) select targets from a stored dump and would SKIP a product that arrived after the plan.`);
