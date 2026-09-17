/* Round 17 — insert the Skimlinks SITE VERIFICATION tag before </body> in layout/theme.liquid.
 *
 * TEMPORARY. Wrapped in explicit markers so removal is unambiguous. See HANDOFF.md.
 *
 * Deliberately NOT added to avadaLightJsExclude or any Hyperspeed override: deferral is
 * irrelevant to a verifier that reads raw HTML, and a permanent whitelist entry for a
 * temporary tag is exactly the kind of residue that outlives its reason.
 *
 *   node scripts/apply/r17-skimlinks-tag.mjs [--apply]
 */
import fs from 'node:fs';

const APPLY = process.argv.includes('--apply');
const F = 'theme/layout/theme.liquid';

const OPEN  = '<!-- SKIMLINKS VERIFICATION — TEMPORARY. Round 17. Remove once\n       Skimlinks confirms verification. See HANDOFF.md. -->';
const TAG   = '<script type="text/javascript" src="https://s.skimresources.com/js/309479X1797834.skimlinks.js"></script>';
const CLOSE = '<!-- END SKIMLINKS VERIFICATION -->';
const BLOCK = `  ${OPEN}\n  ${TAG}\n  ${CLOSE}\n`;

let s = fs.readFileSync(F, 'utf8');

// idempotency: a second run must change nothing (repo convention)
if (s.includes('SKIMLINKS VERIFICATION')) {
  console.log('  already present — refusing to insert a second copy.');
  console.log(`  skimresources occurrences: ${(s.match(/skimresources/g) || []).length}`);
  process.exit(0);
}

const BODY = /<\/body>/i;
const n = (s.match(/<\/body>/gi) || []).length;
console.log(`  </body> occurrences: ${n}`);
if (n !== 1) { console.log('  REFUSING: expected exactly 1'); process.exit(1); }

/* Anchor on the EXACT existing string including its indent, so the file grows by
   precisely BLOCK.length. Anchoring on bare </body> and re-adding an indent grew
   it by BLOCK.length + 2 and the length check caught it. */
const ANCHOR = '\n  </body>';
const a = (s.match(/\n {2}<\/body>/g) || []).length;
console.log(`  exact anchor "\\n  </body>" occurrences: ${a}`);
if (a !== 1) { console.log('  REFUSING: anchor did not match exactly once'); process.exit(1); }

const out = s.replace(ANCHOR, `\n${BLOCK}  </body>`);

// post-conditions on the OUTGOING string (validate what you send, not what comes back)
const checks = [
  ['tag present',                 out.includes(TAG)],
  ['open marker present',         out.includes('SKIMLINKS VERIFICATION — TEMPORARY')],
  ['close marker present',        out.includes(CLOSE)],
  ['tag sits BEFORE </body>',     out.indexOf(TAG) < out.search(BODY)],
  ['exactly one </body> still',   (out.match(/<\/body>/gi) || []).length === 1],
  ['exactly one </html> still',   (out.match(/<\/html>/gi) || []).length === 1],
  ['exactly one script tag',      (out.match(/skimresources/g) || []).length === 1],
  ['no avadaLightJsExclude',      !out.includes('avadaLightJsExclude')],
  ['Hyperspeed comment intact',   out.trimEnd().endsWith('{% endcomment %}')],
  ['only grew by the block',      out.length === s.length + BLOCK.length],
];
let bad = 0;
for (const [label, ok] of checks) { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${label}`); if (!ok) bad++; }
if (bad) { console.log(`\n  REFUSING: ${bad} check(s) failed`); process.exit(1); }

console.log('\n  --- inserted block ---');
console.log(BLOCK.replace(/^/gm, '  | '));

if (!APPLY) { console.log('  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }
fs.writeFileSync(F, out);
console.log(`  written: ${F}  (${s.length} -> ${out.length} bytes)\n`);
