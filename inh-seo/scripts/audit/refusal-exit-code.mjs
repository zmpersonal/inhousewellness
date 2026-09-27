/* Does every script that PRINTS a refusal also RETURN one?
 *   node scripts/audit/refusal-exit-code.mjs [--self-test]
 *
 * A guard has two outputs: what it prints and what it returns. Only the second is read by anything
 * automated. r23i-vendor-merge and restore-from-backup both printed REFUSE and exited 0 — so 24 refused
 * restores were reported to the client as correct behaviour while returning success. Second instance in
 * one round, after `cmd | tee` made a printed STOP go green.
 *
 * Anchored on code: a refusal word inside a COMMENT or a template literal that is never printed does
 * not count, and a script with no refusal vocabulary at all is not a finding.
 */
import fs from 'node:fs';
import path from 'node:path';

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
const WORDS = /\b(REFUS\w*|STOP|BLOCKED|HALT\w*|ABORT\w*)\b/;

export function classify(src) {
  const code = strip(src);
  /* a refusal word inside something being PRINTED */
  const printed = [...code.matchAll(/(?:console\.(?:log|error)|log)\s*\(([\s\S]{0,400}?)\)\s*;/g)]
    .some((m) => WORDS.test(m[1]));
  /* Any process.exit(X) where X is not literally 0 can return non-zero. The first version required a
     bare digit and so missed `process.exit(n ? 1 : 0)` — which is the exact form r23i uses. */
  const exitsNonZero = [...code.matchAll(/process\.exit\s*\(([^)]*)\)/g)].some((m) => m[1].trim() !== '0' && m[1].trim() !== '')
    || /process\.exitCode\s*=\s*[^0\s;]/.test(code);
  const throwsErr = /\bthrow\s+new\s+/.test(code);
  return { printed, exitsNonZero, throwsErr };
}
export function verdict(c) {
  if (!c.printed) return 'prints no refusal';
  if (c.exitsNonZero || c.throwsErr) return 'prints and returns a refusal';
  return 'PRINTS A REFUSAL AND RETURNS 0 — nothing downstream can see it';
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  eq('the real defect', verdict(classify('console.log("  REFUSE x"); process.exit(0);')), 'PRINTS A REFUSAL AND RETURNS 0 — nothing downstream can see it');
  eq('prints and exits non-zero', verdict(classify('console.log("REFUSE x"); process.exit(1);')), 'prints and returns a refusal');
  eq('prints and throws', verdict(classify('console.log("STOP"); throw new Error("no");')), 'prints and returns a refusal');
  eq('exit(0) alone does NOT count as returning a refusal', verdict(classify('console.log("REFUSE"); process.exit(0);')), 'PRINTS A REFUSAL AND RETURNS 0 — nothing downstream can see it');
  eq('a computed exit code counts', verdict(classify('console.log("REFUSE"); process.exit(n ? 1 : 0);')), 'prints and returns a refusal');
  eq('no refusal vocabulary is not a finding', verdict(classify('console.log("wrote 3"); process.exit(0);')), 'prints no refusal');
  // the cases this was NOT built for
  eq('a refusal word in a COMMENT does not count', classify('/* REFUSE is printed elsewhere */ console.log("ok");').printed, false);
  eq('a refusal word in an un-printed string does not count', classify('const msg = "REFUSE"; doNothing(msg);').printed, false);
  eq('exitCode assignment counts as returning', verdict(classify('console.log("REFUSE"); process.exitCode = 1;')), 'prints and returns a refusal');
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds\n');
if (process.argv.includes('--self-test')) process.exit(0);

const groups = {};
for (const dir of ['scripts/apply', 'scripts/audit']) {
  for (const f of fs.readdirSync(dir).filter((x) => /\.(mjs|js)$/.test(x)).sort()) {
    const v = verdict(classify(fs.readFileSync(path.join(dir, f), 'utf8')));
    (groups[v] ||= []).push(`${dir}/${f}`);
  }
}
for (const v of Object.keys(groups).sort()) {
  console.log(`${v}  (${groups[v].length})`);
  if (/RETURNS 0/.test(v)) groups[v].forEach((f) => console.log(`     ${f}`));
}
const n = (groups['PRINTS A REFUSAL AND RETURNS 0 — nothing downstream can see it'] || []).length;
console.log(`\n  ${n} script(s) print a refusal nothing downstream can see.`);
