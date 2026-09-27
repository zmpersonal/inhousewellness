/* Which apply scripts can UNDO their own write?
 *   node scripts/audit/restore-branch.mjs [--self-test]
 *
 * r23h passed every guard it had and could not undo itself: no --restore branch, so the proof runner's
 * cleanup trap had nothing to call and 12 products were left edited. A trap can only invoke a path that
 * exists. This enumerates the same shape across the repo BEFORE the next write.
 *
 * Anchored on code, not prose: a comment or a string mentioning "restore" does not count.
 */
import fs from 'node:fs';
import path from 'node:path';

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
const WRITE = /metafieldsSet|productUpdate|pageUpdate|articleUpdate|collectionUpdate|themeFilesUpsert|publishablePublish|publishableUnpublish|urlRedirectCreate|productSet/;

export function classify(src) {
  const code = strip(src);
  return {
    writes: WRITE.test(code),
    /* a real restore branch reads --restore AND acts on it */
    readsFlag: /--restore/.test(code),
    /* Capture the IDENTIFIER assigned from --restore and check it gates a branch. The first version
       required the variable to be called RESTORE, which is an assumption about someone else's naming —
       a real restore branch using `const R = arg('--restore')` read as "cannot restore". */
    branches: (() => {
      const m = code.match(/(?:const|let|var)\s+(\w+)\s*=\s*(?:arg|flag)\(\s*['"]--restore['"]\s*\)/)
        || code.match(/(\w+)\s*=\s*process\.argv\[[^\]]*--restore/);
      if (!m) return false;
      return new RegExp(`if\\s*\\(\\s*!?${m[1]}\\b`).test(code);
    })(),
    backsUp: /\bbackup\s*\(/.test(code),
    retired: /REFUSING|consumed one-shot|retired/i.test(src.slice(0, 1500)),
  };
}
export function verdict(c) {
  if (!c.writes) return 'no writes';
  if (c.retired) return 'retired';
  if (c.branches) return 'has a restore branch';
  if (c.backsUp) return 'BACKS UP BUT CANNOT RESTORE — the data exists and no code reads it';
  return 'NO BACKUP AND NO RESTORE';
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  eq('a script with a real restore branch', verdict(classify("const R = arg('--restore'); if (R) { } gql(`mutation{metafieldsSet}`); backup('x',[])")), 'has a restore branch');
  eq('backs up but cannot restore — the r23h shape', verdict(classify("backup('x',[]); gql(`mutation{metafieldsSet}`)")), 'BACKS UP BUT CANNOT RESTORE — the data exists and no code reads it');
  eq('no backup, no restore', verdict(classify('gql(`mutation{productUpdate}`)')), 'NO BACKUP AND NO RESTORE');
  eq('a read-only script', verdict(classify('gql(`query{shop{name}}`)')), 'no writes');
  // the case this audit was NOT built for: prose must not count as a branch
  eq('a restore branch under ANY variable name counts', verdict(classify("const rp = arg('--restore'); if (rp) { } gql(`mutation{metafieldsSet}`); backup('x',[])")), 'has a restore branch');
  eq('reading the flag without branching on it does not count', verdict(classify("const rp = arg('--restore'); gql(`mutation{metafieldsSet}`); backup('x',[])")), 'BACKS UP BUT CANNOT RESTORE — the data exists and no code reads it');
  eq('a COMMENT about restoring does not count', classify('/* restoring is done by --restore elsewhere */ backup("x",[]); gql(`mutation{metafieldsSet}`)').branches, false);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds\n');
if (process.argv.includes('--self-test')) process.exit(0);

const groups = {};
for (const f of fs.readdirSync('scripts/apply').filter((x) => /\.(mjs|js)$/.test(x)).sort()) {
  const v = verdict(classify(fs.readFileSync(path.join('scripts/apply', f), 'utf8')));
  (groups[v] ||= []).push(f);
}
for (const v of Object.keys(groups).sort()) {
  console.log(`${v}  (${groups[v].length})`);
  if (/CANNOT RESTORE|NO BACKUP/.test(v)) groups[v].forEach((f) => console.log(`     ${f}`));
}
const risky = (groups['BACKS UP BUT CANNOT RESTORE — the data exists and no code reads it'] || []).length
  + (groups['NO BACKUP AND NO RESTORE'] || []).length;
console.log(`\n  ${risky} write script(s) cannot undo their own write.`);
