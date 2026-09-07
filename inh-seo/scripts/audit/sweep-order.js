/**
 * Orders the collection sweep into a working sequence.
 *
 * Search volume alone is the wrong sort. A collection with 1 product against a
 * 40,500/mo term is not the same opportunity as one with 47 products against
 * 33,100 — the first cannot convert whatever the copy says.
 *
 * Score = volume signal x inventory signal x traction signal
 *
 *   volume     log-scaled. 110,000 is not 100x better than 1,100.
 *   inventory  saturates around 30 products. Below ~5 it collapses, because a
 *              collection with nothing in it is an inventory problem.
 *   traction   a small bonus for pages already drawing impressions — they are
 *              proven reachable, so copy compounds rather than gambles.
 *
 * Read-only. Prints a sequence and flags rows that are not copy problems at all.
 */
import path from 'node:path';
import fs from 'node:fs';
import { readJSON, DATA } from '../lib/util.js';

const plan = readJSON(path.join(DATA, 'collections-plan.json'));
const live = new Map(readJSON(path.join(DATA, 'collections.json')).map((c) => [c.handle, c]));

/* Parse by column index, not by regex. A greedy [\d,]+ on adjacent numeric
   columns silently returned the Clicks value where Impressions was wanted —
   infrared-saunas read as 1 instead of 73. Split the row and index it. */
const imp = new Map();
const csvLines = fs.readFileSync(path.join(DATA, 'gsc-baseline-2026-09-07', 'Pages.csv'), 'utf8')
  .replace(/^\uFEFF/, '').trim().split(/\r?\n/);
const header = csvLines[0].split(',');
const iUrl = header.indexOf('Top pages');
const iImp = header.indexOf('Impressions');
if (iUrl < 0 || iImp < 0) throw new Error('Pages.csv: expected "Top pages" and "Impressions" columns, got ' + header.join(','));
for (const line of csvLines.slice(1)) {
  const cols = line.split(',');
  const url = cols[iUrl];
  if (!url || !url.includes('/collections/')) continue;
  const h = url.split('#')[0].split('/collections/')[1].replace(/\/$/, '');
  imp.set(h, (imp.get(h) || 0) + Number((cols[iImp] || '0').replace(/[",]/g, '')));
}

const DROP = new Set(['DEINDEX', 'DELETE', 'SCOPE-OUT']);
const rows = [];
for (const p of plan) {
  const c = live.get(p.handle);
  if (!c || !c.publishedOnline || DROP.has(p.action)) continue;
  const vol = p.volume || 0;
  const n = c.products;
  const impressions = imp.get(p.handle) || 0;

  const volS = vol > 0 ? Math.log10(vol + 1) / Math.log10(110001) : 0;
  const invS = n === 0 ? 0 : Math.min(1, Math.log10(n + 1) / Math.log10(31));
  const tracS = 1 + Math.min(0.35, impressions / 600);
  const score = volS * invS * tracS;

  let flag = null;
  if (vol >= 5000 && n <= 3) flag = 'INVENTORY, NOT COPY';
  else if (n === 0) flag = 'EMPTY';
  else if (vol === 0 && impressions === 0) flag = 'no keyword, no traffic';
  else if (n <= 5 && vol >= 1000) flag = 'thin inventory';

  rows.push({ h: p.handle, title: c.title, vol, n, impressions, score, flag,
    needsTitle: !c.seoTitle, needsMeta: !c.seoDescription, needsDesc: c.descriptionLength === 0 });
}
rows.sort((a, b) => b.score - a.score);

const flagged = rows.filter((r) => r.flag === 'INVENTORY, NOT COPY' || r.flag === 'EMPTY');
console.log(`\nSWEEP ORDER — ${rows.length} collections, weighted by volume x inventory x traction\n`);
console.log('  #   score  vol/mo   prod  impr  collection                      needs');
rows.forEach((r, i) => {
  const needs = [r.needsTitle && 'title', r.needsMeta && 'meta', r.needsDesc && 'desc'].filter(Boolean).join('+') || '—';
  console.log(`  ${String(i + 1).padStart(2)}  ${r.score.toFixed(3)}  ${String(r.vol || '-').padStart(6)}  ${String(r.n).padStart(4)}  ${String(r.impressions).padStart(4)}  ${r.h.slice(0, 30).padEnd(31)} ${needs}${r.flag ? '   << ' + r.flag : ''}`);
});

console.log(`\n\nNOT COPY PROBLEMS — ${flagged.length} row(s)\n`);
for (const r of flagged) {
  console.log(`  ${r.h}  —  ${r.n} product${r.n === 1 ? '' : 's'}, ${r.vol.toLocaleString()}/mo, ${r.impressions} impressions`);
  console.log(`     Writing copy here cannot work. There is nothing to sell against the term.`);
  console.log(`     This is an inventory decision: stock it, merge it into a collection that has depth, or unpublish it.\n`);
}
