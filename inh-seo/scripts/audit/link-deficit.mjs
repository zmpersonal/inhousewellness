/**
 * Which collections earn impressions but have few inbound internal links?
 *
 * The EMF result is the reason this exists rather than a guess: `low-emf` had
 * EIGHT inbound articles and the best position (17.6); `ultra-low-emf` had TWO,
 * seven times the impressions, and sat at 47. Nobody predicted that — the brief
 * pointed at low-emf. Diagnose before proposing targets.
 *
 * Read-only.
 *   node scripts/audit/link-deficit.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, assertFresh } from '../lib/util.js';

assertFresh({ 'collections.json': 'npm run audit:collections', 'content.json': 'npm run audit:content' });
const collections = readJSON(path.join(DATA, 'collections.json'));
const articles = (readJSON(path.join(DATA, 'content.json')).articles || []).filter((a) => a.published);

/* GSC page rows, collections only */
const gsc = new Map();
const csv = fs.readFileSync(path.join(DATA, 'gsc-baseline-2026-09-07/Pages.csv'), 'utf8').split('\n').slice(1);
for (const line of csv) {
  const m = line.match(/^"?(https:\/\/inhousewellness\.com\/collections\/([a-z0-9-]+))"?,(\d+),(\d+),/);
  if (!m) continue;
  const g = gsc.get(m[2]) || { impr: 0, clicks: 0 };
  g.impr += Number(m[4]); g.clicks += Number(m[3]);
  gsc.set(m[2], g);
}
/* position, separately — last field */
const pos = new Map();
for (const line of csv) {
  const m = line.match(/^"?https:\/\/inhousewellness\.com\/collections\/([a-z0-9-]+)"?,\d+,\d+,[^,]+,([\d.]+)/);
  if (m && !pos.has(m[1])) pos.set(m[1], Number(m[2]));
}

const rows = [];
for (const c of collections) {
  if (!c.publishedOnline) continue;
  const g = gsc.get(c.handle);
  if (!g || !g.impr) continue;                       /* nothing to move */
  const inA = articles.filter((a) => String(a.body || '').includes(`/collections/${c.handle}`)).length;
  const inC = collections.filter((x) => x.handle !== c.handle && String(x.descriptionHtml || '').includes(`/collections/${c.handle}`)).length;
  rows.push({ handle: c.handle, impr: g.impr, clicks: g.clicks, pos: pos.get(c.handle) ?? null,
    inbound: inA + inC, inA, inC, hasCopy: (c.descriptionLength || 0) > 50 });
}

/* deficit = impressions per inbound link. High = earning attention with no support. */
rows.forEach((r) => { r.deficit = r.impr / (r.inbound + 1); });
rows.sort((a, b) => b.deficit - a.deficit);

console.log(`published collections with GSC impressions: ${rows.length}\n`);
console.log('  impr  pos   in  copy   impr/link  collection');
for (const r of rows.slice(0, 22)) {
  console.log(`  ${String(r.impr).padStart(5)} ${String(r.pos ?? '—').padStart(5)} ${String(r.inbound).padStart(4)}  ${r.hasCopy ? ' Y ' : ' n '}  ${String(Math.round(r.deficit)).padStart(8)}   ${r.handle}`);
}
const noLinks = rows.filter((r) => r.inbound === 0);
console.log(`\n  collections with ZERO inbound links: ${noLinks.length}  (${noLinks.reduce((s, r) => s + r.impr, 0)} impressions between them)`);
fs.writeFileSync(path.join(DATA, 'link-deficit.json'), JSON.stringify({ _meta: { ran: new Date().toISOString(), metric: 'impressions per inbound internal link' }, rows }, null, 2));
