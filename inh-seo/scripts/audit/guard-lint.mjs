/* Round 18i — a guard for the GUARDS in scripts/apply/. Three shapes, each found by the guard audit:
 *
 *   R1  a failed write (userErrors) that `continue`s with no failure signal — the run exits 0 and reads as clean.
 *       22 sites across 21 scripts when this was written.
 *   R2  a process.exit() that runs before assertReach(), so the reach guard is dead code (edit-article-claims).
 *   R3  a line that PRINTS a failure (FAIL / FAILED / MISMATCH / REFUS…) with no failure signal on it or the two
 *       lines after — a check that only a reader can see.
 *
 * "Failure signal" = process.exitCode = <non-zero>, process.exit(<non-zero>), throw, or a counter/array that is
 * provably consulted by the final exit. A site that is genuinely fine says so inline:  /* fail-ok: <why> *\/
 *
 *   node scripts/audit/guard-lint.mjs            exit 1 on any finding
 * The lint is itself proved: CONSTRUCTED fixtures must be flagged (and clean ones not) before it will scan.
 */
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const DIR = fileURLToPath(new URL('../apply/', import.meta.url));
const SIGNAL = /process\.exitCode\s*=\s*[1-9]|process\.exit\(\s*[1-9]|process\.exit\(\s*[^)0\s]|\bthrow\b|\b(fail|fails|failed|bad|errors|hardFail|problems|failures)\s*(\+\+|\+=|=\s*true|\.push\()|fail-ok:/;
export function lint(src) {
  const L = src.split('\n'), out = [];
  L.forEach((line, i) => {
    const win = L.slice(i, i + 4).join('\n');
    if (/userErrors(\?)?\.length/.test(line) && /\bcontinue\b/.test(win) && !SIGNAL.test(win.slice(0, win.search(/\bcontinue\b/) + 8)))
      out.push([i + 1, 'R1', 'failed write continues with no failure signal']);
    if (/console\.(log|error)\(.*(\b(FAIL|FAILED|MISMATCH|REFUS)|✗)/.test(line) && !/fail-ok:/.test(line) && !SIGNAL.test(L.slice(Math.max(0, i - 1), i + 3).join('\n')))
      out.push([i + 1, 'R3', 'prints a failure but nothing makes the run fail']);
  });
  const reach = src.search(/\bassertReach\(/);
  if (reach > 0) {
    // a TOP-LEVEL exit (no indentation) before the reach call means the reach call can never run
    const before = src.slice(0, reach).split('\n'); const k = before.findLastIndex((l) => /^process\.exit\(/.test(l));
    if (k >= 0) out.push([k + 1, 'R2', 'top-level process.exit() before assertReach() — the reach guard never runs']);
  }
  return out;
}
// ── the lint's own proof: constructed cases, flagged and not flagged ──
const FIX = [
  ['R1 bare continue',        "if (r.x.userErrors.length) { console.error('FAILED', h); continue; }", ['R1', 'R3']],
  ['R1 with exitCode',        "if (r.x.userErrors.length) { console.error('FAILED', h); process.exitCode = 1; continue; }", []],
  ['R1 counted',              "if (r.x.userErrors.length) { console.error('FAILED', h); fail++; continue; }", []],
  ['R2 dead reach',           "for (const t of T) {}\nprocess.exit(ok ? 0 : 1);\nconst a = 1;\nassertReach(b, a, d);", ['R2']],
  ['R2 exit inside a branch', "if (!APPLY) {\n  process.exit(0);\n}\nassertReach(b, a, d);", []],
  ['R3 printed only',         "console.log(`  MISMATCH ${h}`);\nconst z = 1;", ['R3']],
  ['R3 with a signal',        "console.log(`  MISMATCH ${h}`); process.exitCode = 1;", []],
  ['R3 a ✗ marker counts',    "if (!done) console.error(`  ✗ ${f}: not pushed`);", ['R3']],
  ['R3 marked fail-ok',       "console.log(`  REFUSED as required`); /* fail-ok: expected refusal in a proof */", []],
];
let bad = 0;
for (const [name, src, want] of FIX) { const got = [...new Set(lint(src).map((f) => f[1]))].sort(); if (JSON.stringify(got) !== JSON.stringify(want)) { console.log(`LINT FIXTURE FAIL: ${name} — want [${want}] got [${got}]`); bad++; } }
if (bad) process.exit(2);
console.log(`lint fixtures ${FIX.length}/${FIX.length}`);
if (process.argv.includes('--fixtures-only')) process.exit(0);
let n = 0;
for (const f of fs.readdirSync(DIR).filter((f) => /\.(m?js)$/.test(f) && !f.startsWith('__')).sort()) {
  for (const [line, rule, msg] of lint(fs.readFileSync(path.join(DIR, f), 'utf8'))) { console.log(`  ${rule}  ${f}:${line}  ${msg}`); n++; }
}
console.log(n ? `\n${n} finding(s) — a failure that cannot fail the run is not a guard` : '\nclean: every failed write and printed failure in scripts/apply/ can fail the run');
process.exit(n ? 1 : 0);
