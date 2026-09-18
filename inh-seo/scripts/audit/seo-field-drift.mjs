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

/* The field rule, as a pure function so constructed fixtures can hold it to account. */
function issuesOf(val, n, min, max) {
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
  return issues;
}

/* 18i: constructed fixtures — each shape must fire, each known-legitimate shape must stay silent */
const SFD_FIX = [
  ['leading set size that moved fires',     issuesOf('71 Far Infrared Saunas | From $1,999', 70, 1999, 9000).some((i) => i.startsWith('set size 71'))],
  ['set size after a pipe fires',           issuesOf('Cold Plunges | 18 From $760', 17, 760, 9000).some((i) => i.startsWith('set size 18'))],
  ['band ceiling that moved fires',         issuesOf('Saunas from $1,999 to $14,999', 40, 1999, 12000).some((i) => i.startsWith('band ceiling'))],
  ['subset denominator that moved fires',   issuesOf('55 of the 90 run on 120V', 91, 1, 2).some((i) => i.startsWith('subset denominator 90'))],
  ['correct set size is silent',            issuesOf('71 Far Infrared Saunas', 71, 1, 2).length === 0],
  ['"lower 48" is not a set size',          issuesOf('Free freight to the lower 48', 12, 1, 2).length === 0],
  ['two-part count is not a set size',      issuesOf('5 Float Tanks & 4 Cold Plunges', 9, 1, 2).length === 0],
  ['whole-dollar rounding is not drift',    issuesOf('$708 to $12,009', 5, 708.13, 12008.95).length === 0],
];
const sfdBad = SFD_FIX.filter(([, ok]) => !ok);
for (const [l] of sfdBad) console.error(`  FIXTURE FAIL ${l}`);
if (sfdBad.length) { console.error('refusing — seo-field-drift fixtures did not hold'); process.exit(1); }

const rows = [];
for (const c of collections) {
  const A = active(c.handle);
  if (!A.length) continue;
  const n = A.length;
  const prices = A.map((p) => Number(p.priceMin)).filter(Boolean);
  const min = Math.min(...prices), max = Math.max(...prices);

  for (const [field, val] of [['seoTitle', c.seoTitle], ['seoDescription', c.seoDescription]]) {
    if (!val) continue;
    const issues = issuesOf(val, n, min, max);
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
/* Round 18i: WARN-ONLY no longer. A stale figure in a snippet is a finding, and a finding that
   exits 0 is a line nobody reads. */
process.exitCode = rows.length ? 1 : 0;
