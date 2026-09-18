/* term-contradictions — WITHIN-page disagreement on a price, fee or delivery term.
 *
 * The shipping-facts failure taught us to check a term ACROSS sources. The $1,800
 * installation page taught us the other half: we corrected the section that stated
 * the price and left a section four below it asserting the opposite billing model.
 * A term has more than one representation inside a single document too.
 *
 * This finds candidates. A person decides — a page can legitimately say "all in"
 * about one service and "hourly" about a different one, which the installation page
 * does correctly two sections above the bullet that was wrong.
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, REPORTS } from '../lib/util.js';

const strip = (h) => String(h || '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();

/* Two opposed families. A document asserting both is a candidate, not a defect. */
const ALLIN = /\ball[- ]in\b|no separate .{0,30}(bill|charge|fee)|included in the (price|checkout)|nothing further to pay|no additional (charge|fee|cost)/i;
const VARIABLE = /billed separately|actual hours worked|quoted hourly|\bhourly rate\b|billed at cost|additional fee|charged separately|extra charge/i;
const FREEISH = /free shipping|no minimum|shipping is free|free delivery/i;
const CHARGED = /shipping (fee|charge|cost) of|\$\d[\d,]* (shipping|delivery)|delivery fee/i;

const rows = [];
const money = (t) => [...new Set((t.match(/\$\s?\d[\d,]*(?:\.\d{2})?/g) || []).map((m) => m.replace(/\s/g, '')))];

/* Round 18i: the flag logic, ONE function used by the scan AND the self-test. The self-test used
   to re-implement the all-in check inline, so it proved a copy of the rule, not the rule. */
function flagsOf(t) {
  const flags = [];
  if (ALLIN.test(t) && VARIABLE.test(t)) flags.push('all-in AND variable billing');
  if (FREEISH.test(t) && CHARGED.test(t)) flags.push('free shipping AND a shipping charge');
  /* the same fee word carrying two different amounts */
  for (const w of ['installation', 'assembly', 'white-glove', 'white glove', 'delivery', 'warranty']) {
    const near = [...t.matchAll(new RegExp(`(?:\\$\\s?\\d[\\d,]*)(?:[^.]{0,60}?)${w}|${w}(?:[^.]{0,60}?)(?:\\$\\s?\\d[\\d,]*)`, 'gi'))]
      .map((m) => (m[0].match(/\$\s?\d[\d,]*/) || [''])[0].replace(/\s/g, ''));
    const uniq = [...new Set(near.filter(Boolean))];
    if (uniq.length > 1) flags.push(`"${w}" stated at ${uniq.join(' and ')}`);
  }
  return flags;
}

/* KNOWN POSITIVES — synthetic, so repairing the estate cannot break them. Run BEFORE the scan and
   before the report is written: a failing self-test must not leave a fresh report behind. */
const SELF = [
  ['all-in AND variable billing', '<p>$1,800, all in. There is no separate assembly labour bill afterwards.</p><p>final labor costs will be billed separately based on actual hours worked</p>', 'all-in AND variable billing'],
  // 18i: proves the shipping pair fires
  ['free shipping AND a charge',  '<p>Free shipping on every order.</p><p>A $149 delivery fee applies to Alaska.</p>', 'free shipping AND a shipping charge'],
  // 18i: proves one fee word at two amounts fires
  ['one fee at two amounts',      '<p>White-glove delivery is $600.</p><p>Our white-glove crew charges $900 for stairs.</p>', '"white-glove" stated at $600 and $900'],
];
let selfBad = 0;
for (const [label, html, want] of SELF) if (!flagsOf(strip(html)).includes(want)) { console.error(`  SELFTEST FAILED: ${label} — expected "${want}", got [${flagsOf(strip(html)).join('; ')}]`); selfBad++; }
// 18i: one fee at ONE amount stated twice is not a contradiction
if (flagsOf(strip('<p>Installation is $1,800.</p><p>The $1,800 installation includes assembly.</p>')).some((f) => f.startsWith('"installation"'))) { console.error('  SELFTEST FAILED: the same amount stated twice was flagged'); selfBad++; }
if (selfBad) { console.error('  refusing — term-contradictions self-test failed'); process.exit(1); }

const scan = (items, kind, key) => {
  for (const x of items || []) {
    const t = strip(x[key]);
    if (!t) continue;
    const flags = flagsOf(t);
    if (flags.length) rows.push({ kind, handle: x.handle, status: x.status || (x.published ? 'published' : 'unpublished'), flags, money: money(t) });
  }
};

const P = readJSON(path.join(DATA, 'products.json'));
const C = readJSON(path.join(DATA, 'collections.json'));
const T = readJSON(path.join(DATA, 'content.json'));
scan(Array.isArray(P) ? P : P.products, 'product', 'descriptionHtml');
scan(Array.isArray(C) ? C : C.collections, 'collection', 'descriptionHtml');
scan(T.articles, 'article', 'body');
scan(T.pages, 'page', 'body');

console.log(`\nterm-contradictions — ${rows.length} candidate document(s)\n`);
for (const r of rows) {
  console.log(`  [${r.kind}] ${r.handle}  (${r.status})`);
  for (const f of r.flags) console.log(`      · ${f}`);
}
if (!rows.length) console.log('  none.');

const CLEAN = '<p>$1,800, all in. Anything beyond this package is quoted hourly.</p>';
console.log(`\n  selftest: ${SELF.length} known-positives flagged, and the correctly-scoped control ${flagsOf(strip(CLEAN)).includes('all-in AND variable billing') ? 'ALSO FLAGGED (expected — it is a candidate a person clears)' : 'not flagged'}`);
fs.writeFileSync(path.join(REPORTS, 'term-contradictions.md'), `# Within-page term contradictions\n\nRun ${new Date().toISOString()}\n\n${rows.length} candidate documents.\n\n` + rows.map((r) => `- **${r.kind} \`${r.handle}\`** (${r.status})\n` + r.flags.map((f) => `  - ${f}`).join('\n')).join('\n'));
