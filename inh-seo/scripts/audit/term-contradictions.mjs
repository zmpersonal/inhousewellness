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

const scan = (items, kind, key) => {
  for (const x of items || []) {
    const t = strip(x[key]);
    if (!t) continue;
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

/* KNOWN POSITIVE — synthetic, so repairing the estate cannot break it. */
const FIX = '<p>$1,800, all in. There is no separate assembly labour bill afterwards.</p><p>final labor costs will be billed separately based on actual hours worked</p>';
const t = strip(FIX);
if (!(ALLIN.test(t) && VARIABLE.test(t))) { console.error('\n  SELFTEST FAILED: the known-positive was not flagged'); process.exit(1); }
const CLEAN = '<p>$1,800, all in. Anything beyond this package is quoted hourly.</p>';
console.log(`\n  selftest: known-positive flagged, and the correctly-scoped control ${ALLIN.test(strip(CLEAN)) && VARIABLE.test(strip(CLEAN)) ? 'ALSO FLAGGED (expected — it is a candidate a person clears)' : 'not flagged'}`);
fs.writeFileSync(path.join(REPORTS, 'term-contradictions.md'), `# Within-page term contradictions\n\nRun ${new Date().toISOString()}\n\n${rows.length} candidate documents.\n\n` + rows.map((r) => `- **${r.kind} \`${r.handle}\`** (${r.status})\n` + r.flags.map((f) => `  - ${f}`).join('\n')).join('\n'));
