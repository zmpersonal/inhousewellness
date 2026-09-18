/* Round 18i — the shared write guards in scripts/lib/util.js, proved against CONSTRUCTED cases.
 *   node scripts/audit/util-guards-selftest.mjs            (tests the repo's util.js)
 *   UTIL=/path/to/util.js node scripts/audit/util-guards-selftest.mjs   (tests another copy — used to show
 *                                                            the OLD util.js FAILS this test, i.e. it bites)
 * Every guard gets cases it must REFUSE and cases it must ACCEPT. A guard is only proved if both hold: a
 * guard that refuses everything is as useless as one that refuses nothing. Guards that call process.exit
 * run in a child process so the exit code is the evidence.
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path';
import { fileURLToPath } from 'node:url';
const UTIL = process.env.UTIL || fileURLToPath(new URL('../lib/util.js', import.meta.url));
let bad = 0;
const check = (name, ok, detail = '') => { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? '  — ' + detail : ''}`); if (!ok) bad++; };
/* A REFUSAL is a non-zero exit AND the guard's own message. A crash (a missing import, a syntax error) also
   exits non-zero, and counting it as a refusal is exactly the vacuous pass this file exists to prevent — the
   first draft of this test did that. So each result is REFUSED, ACCEPTED, or CRASHED, and CRASHED fails. */
const verdict = (r, msg) => r.status === 0 ? 'ACCEPTED' : (msg.test((r.stderr || '') + (r.stdout || '')) ? 'REFUSED' : 'CRASHED: ' + ((r.stderr || '').split('\n').find((l) => /Error/.test(l)) || '').slice(0, 90));
const wf = (html, before) => verdict(spawnSync(process.execPath, ['--input-type=module', '-e',
  `import { assertWellFormed } from ${JSON.stringify(UTIL)}; assertWellFormed(${JSON.stringify(html)}, 'fixture', ${before === undefined ? 'null' : JSON.stringify(before)});`], { encoding: 'utf8' }), /REFUSING — fixture is not well formed/);

console.log('assertWellFormed');
const cases = [
  // [name, html, before, must refuse?]
  ['balanced paragraph is accepted',                          '<p>a</p><p>b</p>', undefined, false],
  ['a missing </p> is refused',                               '<p>a<p>b</p>', undefined, true],
  ['PRE-EXISTING imbalance, unchanged by the edit: accepted',  '<p>a<p>b</p><p>new</p>', '<p>a<p>b</p>', false],
  ['PRE-EXISTING imbalance made WORSE: refused',               '<p>a<p>b', '<p>a<p>b</p>', true],
  ['a stripped </span> is refused',                           '<span>x', undefined, true],
  ['a stripped </td> is refused',                             '<table><tr><td>x</tr></table>', undefined, true],
  ['a stripped </h4> is refused',                             '<h4>x', undefined, true],
  ['a stripped </div> is refused',                            '<div><p>x</p>', undefined, true],
  ['mis-nesting introduced is refused',                       '<ul><li><p>a</li></p></ul>', '<ul><li><p>a</p></li></ul>', true],
  ['mis-nesting already present, unchanged: accepted',        '<ul><li><p>a</li></p></ul><p>b</p>', '<ul><li><p>a</li></p></ul>', false],
  ['<br>, <img>, <iframe> are not mistaken for b / i',        '<p>a<br>b<img src="x"><iframe src="y"></iframe></p>', undefined, false],
  ['<thead>/<tbody> balanced is accepted',                    '<table><thead><tr><th>a</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table>', undefined, false],
  ['a new empty <p> is refused',                              '<p>a</p><p></p>', '<p>a</p>', true],
];
for (const [name, html, before, refuse] of cases) { const v = wf(html, before); check(name, v === (refuse ? 'REFUSED' : 'ACCEPTED'), v); }

console.log('assertFresh / lastMutationAt');
// Run against a throwaway ROOT: copy util.js into a temp tree so DATA points at fixtures, never the real log.
// The tree sits INSIDE the repo so util.js's own imports (cheerio) still resolve — outside it, every case
// crashed, and a crash is not a verdict.
const REPO = fileURLToPath(new URL('../..', import.meta.url));
const fresh = (log) => {
  const d = fs.mkdtempSync(path.join(REPO, '.selftest-fresh-')); fs.mkdirSync(path.join(d, 'scripts', 'lib'), { recursive: true }); fs.mkdirSync(path.join(d, 'data'));
  fs.copyFileSync(UTIL, path.join(d, 'scripts', 'lib', 'util.js'));
  if (log !== null) fs.writeFileSync(path.join(d, 'data', 'changelog.jsonl'), log);
  fs.writeFileSync(path.join(d, 'data', 'dump.json'), '{}');                       // mtime = now
  const r = spawnSync(process.execPath, ['--input-type=module', '-e', `import { assertFresh } from ${JSON.stringify(path.join(d, 'scripts', 'lib', 'util.js'))}; assertFresh({ 'dump.json': 'npm run dump' });`], { encoding: 'utf8' });
  fs.rmSync(d, { recursive: true, force: true }); return verdict(r, /ABORTED|unparseable line/);
};
const past = JSON.stringify({ at: '2020-01-01T00:00:00Z' }), future = JSON.stringify({ at: '2999-01-01T00:00:00Z' });
check('dump newer than the last write is accepted',        fresh(past + '\n') === 'ACCEPTED');
check('dump older than the last write is refused',          fresh(future + '\n') === 'REFUSED');
check('MISSING changelog is refused, not read as fresh',    fresh(null) === 'REFUSED');
check('EMPTY changelog is refused, not read as fresh',      fresh('') === 'REFUSED');
check('a CORRUPT line hiding the newest write is refused',  fresh(past + '\n{not json\n') === 'REFUSED');

console.log('assertNoLinkLoss');
const nl = (b, a, allowed = []) => verdict(spawnSync(process.execPath, ['--input-type=module', '-e',
  `import { assertNoLinkLoss } from ${JSON.stringify(UTIL)}; assertNoLinkLoss(${JSON.stringify(b)}, ${JSON.stringify(a)}, 'fixture', ${JSON.stringify(allowed)});`], { encoding: 'utf8' }), /REFUSING — fixture: this write would REMOVE/);
const LIVE55 = '<p>See <a href="/collections/low-emf">low EMF</a> and <a href="/collections/ultra-low-emf">ultra</a>.</p>';
check('instance 55: staged copy drops two live links — refused', nl(LIVE55, '<p>See low EMF and ultra.</p>') === 'REFUSED');
check('one of two identical links dropped — refused (multiset)', nl('<a href="/x">a</a><a href="/x">b</a>', '<a href="/x">a</a>') === 'REFUSED');
check('links kept, prose changed — accepted',                   nl(LIVE55, '<p>Compare <a href="/collections/low-emf">low EMF</a> with <a href="/collections/ultra-low-emf">ultra low</a>.</p>') === 'ACCEPTED');
check('a named, intended removal — accepted',                   nl(LIVE55, '<p>See <a href="/collections/low-emf">low EMF</a>.</p>', ['/collections/ultra-low-emf']) === 'ACCEPTED');
check('a link ADDED — accepted',                                nl('<p>x</p>', '<p><a href="/y">x</a></p>') === 'ACCEPTED');

console.log('assertOneWritePerRecord');
const { assertOneWritePerRecord } = await import(UTIL);
const throws = (f) => { try { f(); return false; } catch { return true; } };
check('two writes to one record are refused',  throws(() => assertOneWritePerRecord([{ k: 'a' }, { k: 'a' }], (t) => t.k)));
check('a write with no key is refused',        throws(() => assertOneWritePerRecord([{ k: '' }], (t) => t.k)));
check('distinct records are accepted',         !throws(() => assertOneWritePerRecord([{ k: 'a' }, { k: 'b' }], (t) => t.k)));

console.log(bad ? `\n${bad} FAILED` : '\nall util guards refuse what they must and accept what they must');
process.exit(bad ? 1 : 0);
