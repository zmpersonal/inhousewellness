/* Does any script IMPORT a module that exits at import time?
 *   node scripts/audit/cli-import.mjs [--self-test]
 *
 * A module with a top-level process.exit KILLS ITS IMPORTER, and the failure is silent when it lands
 * after a write. That happened here: a proof imported restore-from-backup.mjs to reuse an adapter, the
 * CLI's usage exit terminated the proof AFTER it had staged a change and BEFORE it restored it, and a
 * collection sat with a placeholder in both SEO fields.
 *
 * The fix is to gate the imported module behind an is-main check and export what callers need — not to
 * change the importer, which would leave the hazard for the next caller.
 */
import fs from 'node:fs';
import path from 'node:path';

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ')
  .replace(/`(?:[^`\\]|\\.)*`/g, '``').replace(/'(?:[^'\\]|\\.)*'/g, "''").replace(/"(?:[^"\\]|\\.)*"/g, '""');

/* the brace depth at which each process.exit sits. Depth 0 runs on import. */
export function exitDepths(src) {
  const code = strip(src); const out = []; let d = 0;
  for (let i = 0; i < code.length; i++) {
    if (code[i] === '{') d++;
    else if (code[i] === '}') d--;
    else if (code.startsWith('process.exit', i)) { out.push(d); i += 11; }
  }
  return out;
}
/* An is-main guard has several idiomatic forms. The first version matched `import.meta.url ===` and so
   missed `fileURLToPath(import.meta.url) === process.argv[1]`, reporting a correctly-gated module as a
   finding. Recognising a real guard form is widening the DETECTOR, not loosening the rule. */
export const hasIsMainGuard = (src) => {
  const c = strip(src);
  return /import\.meta\.url\s*===/.test(c)
    || /===\s*import\.meta\.url/.test(c)
    || /fileURLToPath\s*\(\s*import\.meta\.url\s*\)\s*===/.test(c)
    || /require\.main\s*===/.test(c)
    || /pathToFileURL\s*\(\s*process\.argv\[1\]/.test(c);
};
/* And process.exitCode = N does NOT terminate the importer — it only sets the code for a natural exit. */
export const exitCodeOnly = (src) => !/process\.exit\s*\(/.test(strip(src)) && /process\.exitCode\s*=/.test(strip(src));
export const localImports = (src) => [...strip(src).matchAll(/from\s+''|import\s*\(\s*''/g)].length
  ? [...src.matchAll(/(?:from|import\s*\()\s*['"](\.[^'"]+)['"]/g)].map((m) => m[1])
  : [...src.matchAll(/(?:from|import\s*\()\s*['"](\.[^'"]+)['"]/g)].map((m) => m[1]);
/* CERTAIN: an exit at brace depth 0 executes when the module is imported.
   WEAKER: an exit at depth 1+ may be a function body (safe) or a top-level if-block (not). Brace depth
   cannot tell those apart and JS cannot be lexed with a regex — proved earlier this round when a
   regex-literal stripper ate a real call. So the weaker case is reported for a READ rather than
   resolved, and only the certain case is a finding. */
export const runsOnImport = (src) => exitDepths(src).includes(0);
export const mayRunOnImport = (src) => {
  const d = exitDepths(src);
  return d.length > 0 && !d.includes(0) && !hasIsMainGuard(src);
};

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  eq('a top-level exit runs on import', runsOnImport('const x=1; process.exit(1);'), true);
  eq('an exit inside a function does not', runsOnImport('function f(){ process.exit(1); } export default f;'), false);
  eq('an exit inside an is-main guard does not', runsOnImport('if (import.meta.url === pathToFileURL(process.argv[1]).href) { process.exit(0); }'), false);
  eq('an exit in a bare if is NOT certain — it needs a read', runsOnImport('if (bad) { process.exit(2); }'), false);
  eq('...and is reported as the weaker case', mayRunOnImport('if (bad) { process.exit(2); }'), true);
  eq('an is-main guard clears the weaker case too', mayRunOnImport('if (import.meta.url === pathToFileURL(process.argv[1]).href) { process.exit(0); }'), false);
  // the form the first version missed, on a correctly-gated real module
  eq('fileURLToPath(import.meta.url) === argv[1] is recognised', hasIsMainGuard('if (fileURLToPath(import.meta.url) === process.argv[1]) { }'), true);
  eq('exitCode alone does not terminate an importer', exitCodeOnly('process.exitCode = 1;'), true);
  eq('a real exit() is not exitCode-only', exitCodeOnly('process.exit(1);'), false);
  eq('no exit at all', runsOnImport('export const a = 1;'), false);
  eq('depths are counted, not just presence', exitDepths('process.exit(0); function f(){ process.exit(1); }'), [0, 1]);
  // the cases this was NOT built for
  eq('process.exit inside a STRING does not count', exitDepths('const s = "process.exit(1)";'), []);
  eq('process.exit inside a COMMENT does not count', exitDepths('/* process.exit(1) */'), []);
  eq('a relative import is found', localImports("import x from '../lib/util.js';"), ['../lib/util.js']);
  eq('a bare package import is not a local import', localImports("import fs from 'node:fs';"), []);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds\n');
if (process.argv.includes('--self-test')) process.exit(0);

/* NAMED EXEMPTIONS, each with its verdict from a READ. Fifth time this round the answer has been a
   named exemption with a reason rather than a tighter pattern — depth cannot tell a function body from
   a top-level if, and lexing JS with a regex trades a visible false positive for an invisible false
   negative. Both of these are LIBRARIES, not CLIs, and between them they account for essentially every
   row the first version reported: two libraries, one real answer each, times ~90 importers. */
const EXEMPT = {
  'scripts/lib/util.js': 'READ 2026-09-27: all four exits are inside assertFresh / assertWellFormed FUNCTION BODIES. Safe to import.',
  'scripts/lib/shopify.js': 'READ 2026-09-27: GENUINELY EXITS AT IMPORT — a top-level `if (!SHOP || !TOKEN) process.exit(1)`. Accepted: with no credentials nothing can work. ⚠️ BUT SEE THE CONSEQUENCE BELOW.',
};
/* ⚠️ THE CONSEQUENCE, which matters more than the mechanism. ~90 scripts import shopify.js, so a missing
   or refused credential kills each of them AT IMPORT — before any of their own preamble runs. A cleanup
   trap installed at the top of a script IS NOT INSTALLED if .env is missing. The r23h fix depends on
   exactly such a trap: it protects a run that reaches it, and a credential failure is not one of those.
   During the four token failures this round, every script died at import before its guards existed. */

const files = [];
for (const dir of ['scripts/apply', 'scripts/audit', 'scripts/lib']) {
  for (const f of fs.readdirSync(dir).filter((x) => /\.(mjs|js)$/.test(x))) files.push(path.join(dir, f));
}
const src = Object.fromEntries(files.map((f) => [f, fs.readFileSync(f, 'utf8')]));
const exits = Object.fromEntries(files.map((f) => [f, runsOnImport(src[f])]));
const maybe = Object.fromEntries(files.map((f) => [f, mayRunOnImport(src[f])]));
console.log(`  ${files.length} scripts. Modules that EXIT AT IMPORT TIME: ${files.filter((f) => exits[f]).length}\n`);

const findings = [];
for (const f of files) {
  for (const rel of localImports(src[f])) {
    const target = path.normalize(path.join(path.dirname(f), rel));
    if (!src[target]) continue;
    if (EXEMPT[target]) continue;
    if (exits[target]) findings.push([f, target, 'CERTAIN']);
    else if (maybe[target]) findings.push([f, target, 'needs a read']);
  }
}
console.log('  named exemptions, each verdict from a read:');
for (const [k, v] of Object.entries(EXEMPT)) console.log(`    ${k}\n        ${v}`);
console.log();
if (!findings.length) console.log('  0 findings: no script imports an un-exempted module that exits at import time.');
else {
  console.log(`>>> ${findings.length} import(s) of a module that exits at import time:\n`);
  findings.forEach(([a, b, c]) => console.log(`  [${c}] ${a}\n           imports ${b}`));
}
console.log('\n  For reference, the modules that exit at import time (fine when only ever run directly):');
files.filter((f) => exits[f]).slice(0, 12).forEach((f) => console.log(`    ${f}`));
if (files.filter((f) => exits[f]).length > 12) console.log(`    …and ${files.filter((f) => exits[f]).length - 12} more`);
process.exit(findings.length ? 1 : 0);
