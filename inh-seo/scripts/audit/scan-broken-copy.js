import fs from 'node:fs';
import path from 'node:path';
import { readJSON, writeJSON, DATA, REPORTS, BROKEN_PATTERNS, scanForBroken, contextAround } from '../lib/util.js';

const need = ['collections.json','products.json','content.json'].map(f=>path.join(DATA,f));
for (const f of need) if (!fs.existsSync(f)) {
  console.error(`Missing ${path.basename(f)} — run the dump scripts first (npm run audit).`);
  process.exit(1);
}

const collections = readJSON(need[0]);
const products    = readJSON(need[1]);
const content     = readJSON(need[2]);

const findings = [];
function check(kind, id, handle, field, html) {
  const hits = scanForBroken(html);
  for (const h of hits) {
    const pat = BROKEN_PATTERNS.find(p => p.id === h.id);
    findings.push({
      kind, id, handle, field,
      pattern: h.id, severity: h.severity,
      context: contextAround(html, pat.re),
    });
  }
}

for (const c of collections) check('collection', c.id, c.handle, 'descriptionHtml', c.descriptionHtml);
for (const p of products)    check('product',    p.id, p.handle, 'descriptionHtml', p.descriptionHtml);
for (const a of content.articles) check('article', a.id, a.handle, 'body', a.body);
for (const p of content.pages)    check('page',    p.id, p.handle, 'body', p.body);

writeJSON(path.join(DATA,'broken-copy.json'), findings);

const bySeverity = findings.reduce((m,f)=>((m[f.severity]=(m[f.severity]||0)+1),m),{});
const byPattern  = findings.reduce((m,f)=>((m[f.pattern]=(m[f.pattern]||0)+1),m),{});

const lines = [
  '# Broken copy scan',
  '',
  `Run: ${new Date().toISOString()}`,
  '',
  `**${findings.length} findings** across ${collections.length} collections, ${products.length} products, ${content.articles.length} articles, ${content.pages.length} pages.`,
  '',
  '## By severity',
  ...Object.entries(bySeverity).sort().map(([k,v])=>`- ${k}: ${v}`),
  '',
  '## By pattern',
  ...Object.entries(byPattern).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`- \`${k}\`: ${v}`),
  '',
  '## Findings',
  '',
  '| Severity | Kind | Handle | Pattern | Context |',
  '|---|---|---|---|---|',
  ...findings
    .sort((a,b)=>a.severity.localeCompare(b.severity))
    .map(f=>`| ${f.severity} | ${f.kind} | \`${f.handle}\` | ${f.pattern} | ${(f.context||'').replace(/\|/g,'\\|').slice(0,110)} |`),
];
fs.writeFileSync(path.join(REPORTS,'broken-copy.md'), lines.join('\n'));
console.log(`\n${findings.length} findings — see reports/broken-copy.md`);

/* ---- KNOWN-POSITIVE CHECK ------------------------------------------------
 *
 * This script is BOTH ends of its own loop: clear-broken-copy.js acts on
 * data/broken-copy.json, which is this file's output, and then this file is
 * re-run to confirm the clean. A form outside BROKEN_PATTERNS is never
 * detected, never cleaned, and reported clean — a single point of failure
 * wearing two hats, and strictly worse than the Sun Home case where the
 * removal and the audit at least lived in different scripts.
 *
 * The fixtures below are SYNTHETIC, so repairing the estate cannot break them.
 * The classes they cover were chosen by a HAND READ of live copy, not from the
 * pattern list — reading the list can only ever confirm what it already knows.
 * `framework-class-residue` is the one that matters: 36 Finnmark products
 * carried Material-UI and Emotion classes and the scanner had a Tailwind
 * pattern and nothing else.
 */
import { BROKEN_PATTERNS as BP, scanForBroken as scan } from '../lib/util.js';

const CASES = [
  ['MUI class residue',        '<p class="MuiTypography-root comp-typography css-118mvrh">Standard</p>', 'framework-class-residue'],
  ['Emotion css- hash alone',  '<div class="css-udlkbm"><p>Cover</p></div>',                             'framework-class-residue'],
  ['empty heading',            '<table></table><h2></h2><p>After</p>',                                   'empty-heading'],
  ['empty heading with nbsp',  '<h3>&nbsp;</h3>',                                                        'empty-heading'],
  ['AI citation marker',       '<p>Cedar lasts 15 years:contentReference[oaicite:3]</p>',                'ai-citation-ref'],
  ['editor data attributes',   '<p data-start="742" data-end="762">Text</p>',                            'editor-data-attrs'],
  ['stray meta tag',           '<p><meta charset="utf-8">Experience</p>',                                'stray-meta-tag'],
  ['markdown anchor in a heading', '<h2>Interactive Calculator {#calculator}</h2>',                      'markdown-anchor-literal'],
  ['markdown anchor in prose',     '<p>see the FAQ {#faq} below</p>',                                    'markdown-anchor-literal'],
];
/* Negative controls — every one of these was found in the live estate and read
   by hand as CORRECT. A pattern that fires on them is too wide. */
const CLEAN = [
  ['colon introducing a subheading', '<p>Techniques you can implement:</p><h3>1. Mindful Breathing</h3>'],
  ['jump-target anchor',             '<p><a id="unknowns"></a></p><h2 id="h.x">What We Still Do Not Know</h2>'],
  ['blank cell in a comparison',     '<table><tbody><tr><td><p></p></td><td><p>Yes</p></td></tr></tbody></table>'],
  ['ordinary styled product copy',   '<p style="text-align: center;">Ships freight to the lower 48.</p>'],
  ['a heading that has content',     '<h2 id="h.abc">Delivery</h2>'],
  ['CSS in a style block',           '<style>.a{#fff}</style>'],
  ['a hex colour in an attribute',   '<p style="color:#fff">Text</p>'],
  ['an id attribute, not markdown',  '<h2 id="calculator">Interactive Calculator</h2>'],
];

console.log('\nKNOWN-POSITIVE CHECK (synthetic)');
let bad = 0;
for (const [name, html, want] of CASES) {
  const ids = scan(html).map((x) => x.id);
  const ok = ids.includes(want);
  if (!ok) bad += 1;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name} -> ${want}${ok ? '' : `  (got: ${ids.join(', ') || 'nothing'})`}`);
}
for (const [name, html] of CLEAN) {
  const ids = scan(html).map((x) => x.id);
  const ok = ids.length === 0;
  if (!ok) bad += 1;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  control: ${name} -> silent${ok ? '' : `  (FIRED: ${ids.join(', ')})`}`);
}
console.log(`  ${BP.length} patterns, ${CASES.length} positives, ${CLEAN.length} controls`);
if (bad) { console.error(`\n${bad} fixture(s) failed. This script specifies AND verifies its own work — do not trust its "clean" above.`); process.exit(1); }
