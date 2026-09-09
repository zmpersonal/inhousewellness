/**
 * drift-check covers collection DESCRIPTIONS. Nothing covers SEO titles and
 * meta descriptions — and the same archive that staled 19 figures in prose
 * staled them in snippets too, where they are what a searcher actually reads.
 *
 * VERY narrow on purpose. A first crude version flagged 35 fields by treating
 * any 1-3 digit number as a possible count: it read "lower 48" as a set size,
 * "2-4 Person" as a set size, and "3 to 5 mG" as a set size. Third over-firing
 * first run in one session. It now matches only two unambiguous shapes:
 *
 *   LEADING SET SIZE   "71 far infrared saunas…"  /  "| 18 From $760"
 *   EXPLICIT BAND      "$1,999 to $14,999"
 *
 * Everything else is left to a human read. A snippet checker that cries wolf on
 * "lower 48" gets ignored, and an ignored guard is worse than none.
 *
 * Read-only.
 *   node scripts/audit/seo-field-drift.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, assertFresh } from '../lib/util.js';

assertFresh({ 'collections.json': 'npm run audit:collections', 'products.json': 'npm run audit:products' });

const collections = readJSON(path.join(DATA, 'collections.json'));
const products = readJSON(path.join(DATA, 'products.json'));
const active = (h) => products.filter((p) => p.collections.includes(h) && p.status === 'ACTIVE');

const rows = [];
for (const c of collections) {
  const A = active(c.handle);
  if (!A.length) continue;
  const n = A.length;
  const prices = A.map((p) => Number(p.priceMin)).filter(Boolean);
  const min = Math.min(...prices), max = Math.max(...prices);

  for (const [field, val] of [['seoTitle', c.seoTitle], ['seoDescription', c.seoDescription]]) {
    if (!val) continue;
    const issues = [];

    /* a number that leads the string, or follows a pipe, and is followed by a
       word — the set-size construction and nothing else */
    /* Two legitimate shapes this must NOT flag, both found on the first run:
         "5 Float Tanks & 4 Cold Plunges"  — a two-part count that sums to 9
         "55 of the 90 infrared saunas"    — a subset, not a set size
       A leading number is only a set-size claim when nothing else in the string
       claims to be one. */
    const twoPart = /^\s*(?:[^|]*\|\s*)?\d{1,3}\s+[A-Za-z][^&]*&\s*\d{1,3}\s+[A-Za-z]/.test(val);
    const subset = /\b\d{1,3}\s+of\s+(?:the\s+)?\d{1,3}\b/.test(val);
    const lead = (twoPart || subset) ? null : val.match(/(?:^|\|\s*)(\d{1,3})\s+[A-Za-z]/);
    if (lead && Number(lead[1]) !== n) issues.push(`set size ${lead[1]} → ${n}`);
    /* A subset construction still needs its DENOMINATOR checked. */
    const sub = val.match(/\b(\d{1,3})\s+of\s+(?:the\s+)?(\d{1,3})\b/);
    if (sub && Number(sub[2]) !== n) issues.push(`subset denominator ${sub[2]} → ${n}`);

    /* an explicit band, both ends */
    const band = val.match(/\$([\d,]+)\s*(?:to|–|-|—)\s*\$([\d,]+)/);
    if (band) {
      const lo = Number(band[1].replace(/,/g, '')), hi = Number(band[2].replace(/,/g, ''));
      /* A price in copy is written in whole dollars. $708.13 shown as "$708"
         and $12,008.95 as "$12,009" are both CORRECT — drift-check already
         carries this rule and the first version of this script did not, so it
         reported five correctly-rounded titles as drifted. */
      const dollarEq = (written, real) => Math.round(real) === written || Math.floor(real) === written;
      if (!dollarEq(lo, min)) issues.push(`band floor $${band[1]} → $${min.toLocaleString('en-US')}`);
      if (!dollarEq(hi, max)) issues.push(`band ceiling $${band[2]} → $${max.toLocaleString('en-US')}`);
    }
    if (issues.length) rows.push({ handle: c.handle, field, value: val, issues });
  }
}

console.log(`${collections.length} collections · SEO fields carrying a stale figure: ${rows.length}\n`);
for (const r of rows) {
  console.log(`  ${r.handle}  [${r.field}]`);
  console.log(`     "${r.value}"`);
  r.issues.forEach((i) => console.log(`     ✗ ${i}`));
}
fs.writeFileSync(path.join(DATA, 'seo-field-drift.json'), JSON.stringify({ _meta: { ran: new Date().toISOString() }, rows }, null, 2));
console.log(`\nwrote data/seo-field-drift.json`);
