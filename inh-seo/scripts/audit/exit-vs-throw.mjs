/* Which shared guards EXIT rather than THROW, and is any of them called inside a fixture-driven probe?
 *   node scripts/audit/exit-vs-throw.mjs [--self-test]
 *
 * r23f hit this: assertWellFormed calls process.exit, so a deliberately-broken fixture killed the run
 * instead of failing a test. Exiting is right for the real outgoing string and wrong inside a probe.
 * A killed run and a failed test look nothing alike, which is why this is worth enumerating.
 */
import fs from 'node:fs';
import path from 'node:path';

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
/* ⚠️ Do NOT try to strip regex literals to decide what is a call. The first version of this audit did,
   to silence one false positive (plan-source.mjs names assertFresh inside a pattern it SEARCHES for),
   and the stripper then ate a REAL call in r18-unwrap-t1.mjs line 124 — trading a visible false
   positive for an invisible false negative. JS cannot be lexed with a regex. The false positive is
   NAMED below instead, with its reason, which is auditable in a way a clever stripper is not. */
const KNOWN_NOT_CALLS = {
  'scripts/audit/plan-source.mjs': 'names assertFresh inside a regex it searches for, never calls it',
  'scripts/audit/exit-vs-throw.mjs': 'names assertWellFormed inside its OWN fixture strings, never calls it',
};

export function fnBody(src, name) {
  const m = src.match(new RegExp(`export function ${name}\\s*\\(`));
  if (!m) return null;
  let i = src.indexOf('{', m.index), d = 0, start = i;
  for (; i < src.length; i++) { if (src[i] === '{') d++; else if (src[i] === '}') { d--; if (!d) return src.slice(start, i + 1); } }
  return null;
}
/* The highest-value finding: a call to an EXITING guard wrapped in try/catch. The author believes the
   failure is handled; it is not, because the process is already gone. Dead code that reads as a guard. */
export const deadCatch = (src, exiters) => exiters.some((n) =>
  new RegExp(`try\\s*\\{[^{}]*\\b${n}\\s*\\([^{}]*\\}\\s*catch`).test(src));
export const classifyFn = (body) => ({ exits: /process\.exit\s*\(/.test(strip(body)), throws: /\bthrow\b/.test(strip(body)) });

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  const src = 'export function a(x) {\n if (x) { process.exit(1); }\n}\nexport function b(x) {\n throw new Error("no");\n}\nexport function c(x) { return 1; }\n';
  eq('a exits', classifyFn(fnBody(src, 'a')), { exits: true, throws: false });
  eq('b throws', classifyFn(fnBody(src, 'b')), { exits: false, throws: true });
  eq('c does neither', classifyFn(fnBody(src, 'c')), { exits: false, throws: false });
  eq('the body stops at its own closing brace', fnBody(src, 'c'), '{ return 1; }');
  eq('a comment mentioning process.exit does not count', classifyFn(fnBody('export function d(){ /* process.exit(1) */ return 1; }', 'd')).exits, false);
  eq('a missing function is null, not a false pass', fnBody(src, 'nope'), null);
  eq('a try/catch around an exiting guard is a DEAD catch', deadCatch("try { assertWellFormed(x); } catch (e) { f.push(e); }", ['assertWellFormed']), true);
  eq('a try/catch around a throwing guard is fine', deadCatch("try { assertOneWritePerRecord(x); } catch (e) {}", ['assertWellFormed']), false);
  eq('an unwrapped call is not a dead catch', deadCatch("assertWellFormed(x);", ['assertWellFormed']), false);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds\n');
if (process.argv.includes('--self-test')) process.exit(0);

const util = fs.readFileSync('scripts/lib/util.js', 'utf8');
const names = [...util.matchAll(/^export function (\w+)/gm)].map((m) => m[1]);
const exiters = [];
console.log('scripts/lib/util.js — how each exported guard reports failure:');
for (const n of names) {
  const b = fnBody(util, n); if (!b) continue;
  const c = classifyFn(b);
  const how = c.exits && c.throws ? 'EXITS and throws' : c.exits ? 'EXITS' : c.throws ? 'throws' : 'returns only';
  console.log(`  ${how.padEnd(16)} ${n}`);
  if (c.exits) exiters.push(n);
}
console.log(`\n${exiters.length} guard(s) exit: ${exiters.join(', ')}`);
console.log('\nwhere an EXITING guard is called from a file that also runs fixtures (--self-test):');
let risky = 0;
for (const dir of ['scripts/apply', 'scripts/audit']) {
  for (const f of fs.readdirSync(dir).filter((x) => /\.(mjs|js)$/.test(x))) {
    const src = fs.readFileSync(path.join(dir, f), 'utf8');
    const hasFixtures = /--self-test|FIXTURE FAIL|function selfTest/.test(src);
    if (!hasFixtures) continue;
    const used = exiters.filter((n) => new RegExp(`\\b${n}\\s*\\(`).test(strip(src)));
    if (!used.length) continue;
    /* only a call reachable FROM the fixtures is the hazard; a call on the real write path is correct */
    const body = strip(src);
    const sel = body.indexOf('function selfTest');
    const inFixtures = sel >= 0 && used.some((n) => body.slice(sel).split('\nconst bad =')[0].includes(`${n}(`));
    const rel = `${dir}/${f}`;
    if (KNOWN_NOT_CALLS[rel]) { console.log(`  n/a     ${rel}  ${KNOWN_NOT_CALLS[rel]}`); continue; }
    const dead = deadCatch(strip(src), used);
    const tag = inFixtures ? 'HAZARD ' : dead ? 'DEAD-CATCH' : 'ok     ';
    console.log(`  ${tag.padEnd(11)} ${rel}  uses ${used.join(', ')}${inFixtures ? '  <-- inside its own fixtures' : dead ? '  <-- try/catch around it never fires: the guard EXITS' : '  (real path only)'}`);
    if (inFixtures || dead) risky++;
  }
}
console.log(`\n  ${risky} file(s) need attention: a fixture-driven call, or a try/catch that can never fire.`);
