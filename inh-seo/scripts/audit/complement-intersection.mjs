/* complement-intersection — the records excluded by EVERY substantive review.
 *
 * Every review on this project has honestly named its complement. None has asked
 * what is excluded by all of them. That set is small by construction, which is why
 * it is affordable and why nobody computes it. It is also SELECTED — for records
 * that fit no category any reviewer thought in.
 *
 * "Substantive" means a review that produced a JUDGEMENT or an EDIT about a
 * record's copy. Mechanical pattern screens are deliberately excluded: they cover
 * everything by construction, so including one collapses the intersection to zero
 * and hides the thing this is for. scan-broken-copy covered the three commercial
 * pages the week they broke and told nobody anything about their terms.
 */
import path from 'node:path';
import { readJSON, DATA, REPORTS } from '../lib/util.js';
import fs from 'node:fs';

const P = readJSON(path.join(DATA, 'products.json'));
const C = readJSON(path.join(DATA, 'collections.json'));
const T = readJSON(path.join(DATA, 'content.json'));
const products = Array.isArray(P) ? P : P.products;
const collections = Array.isArray(C) ? C : C.collections;
const articles = T.articles || [];
const pages = T.pages || [];

const plan = readJSON(path.join(DATA, 'collections-plan.json'));
const planRows = Array.isArray(plan) ? plan : plan.rows;
const artReg = readJSON(path.join(DATA, 'article-claim-register.json'));
const artEdits = readJSON(path.join(DATA, 'article-claim-edits.json'));
const prodEdits = readJSON(path.join(DATA, 'product-claim-edits.json'));
const artSeo = readJSON(path.join(DATA, 'article-seo.json'));
const claimReg = readJSON(path.join(DATA, 'claim-review-register.json'));
const residue = readJSON(path.join(DATA, 'residue-batches.json'));

const list = (x) => (Array.isArray(x) ? x : Object.values(x).find(Array.isArray) || []);
const set = (arr) => new Set(arr.filter(Boolean));

/* Each review: what it actually looked at, as handles. */
const REVIEWS = [
  { id: 'collection copy sweep',        covers: set(planRows.filter((r) => ['WRITE','REWRITE','URGENT'].includes(r.action)).map((r) => r.handle)) },
  { id: 'collection SEO titles/metas',  covers: set(collections.filter((c) => (c.seo?.title) || c.seoTitle).map((c) => c.handle)) },
  { id: 'collection scope-out ruling',  covers: set(planRows.filter((r) => /SCOPE-OUT|DEINDEX|KEEP/.test(r.action || '')).map((r) => r.handle)) },
  { id: 'article claim register',       covers: set(list(artReg).map((r) => r.handle)) },
  { id: 'article claim edits',          covers: set(list(artEdits).map((r) => r.handle)) },
  { id: 'article SEO pass',             covers: set(Object.keys(artSeo).filter((k) => !k.startsWith('_'))) },
  { id: 'product claim cuts',           covers: set(list(prodEdits).map((r) => r.handle)) },
  { id: 'product claim vendor review',  covers: set(products.filter((p) => list(claimReg).some((v) => v.vendor === p.vendor)).map((p) => p.handle)) },
  /* NOT the residue batches. Those were mechanical attribute strips with an
     automated equivalence check — they touched 302 products and produced no
     judgement about a single word of copy. Counting them as review is exactly the
     error this script exists to expose. Only batch 4's three live commercial
     pages were actually read. */
  { id: 'batch 4 own-brand read',       covers: set(['installation-assembly', 'extended-your-warranty-3-years', 'white-glove-delivery-service']) },
];

const covered = new Set();
for (const r of REVIEWS) for (const h of r.covers) covered.add(h);

const universe = [
  ...products.map((p) => ({ kind: 'product', handle: p.handle, status: p.status, len: (p.descriptionHtml || '').length, price: p.priceMin })),
  ...collections.map((c) => ({ kind: 'collection', handle: c.handle, status: 'n/a', len: (c.descriptionHtml || '').length })),
  ...articles.map((a) => ({ kind: 'article', handle: a.handle, status: a.published ? 'published' : 'unpublished', len: a.bodyLength || 0 })),
  ...pages.map((p) => ({ kind: 'page', handle: p.handle, status: p.published ? 'published' : 'unpublished', len: (p.body || '').length })),
];

const missed = universe.filter((r) => !covered.has(r.handle));

console.log('\nreview coverage');
for (const r of REVIEWS) console.log(`  ${String(r.covers.size).padStart(4)}  ${r.id}`);
console.log(`  ${String(covered.size).padStart(4)}  UNION of every substantive review`);
console.log(`\nuniverse: ${universe.length} records`);
console.log(`INTERSECTION OF EVERY COMPLEMENT: ${missed.length} records never substantively reviewed\n`);

const by = {};
for (const m of missed) (by[m.kind] = by[m.kind] || []).push(m);
/* Segment it, or a 400-row list is unreadable and gets skipped — which is the
   same failure as not computing it. */
const SCOPEOUT = new Set(planRows.filter((r) => /SCOPE-OUT/.test(r.action || '')).map((r) => r.handle));
const outdoorVendors = new Set(['Primo', 'Broilmaster', 'Cal Flame', 'Cozy Heat']);
const byVendor = new Map(products.map((p) => [p.handle, p.vendor]));
const seg = { 'outdoor cooking (scope-out by ruling)': [], 'accessories, parts and covers': [], 'DRAFT / ARCHIVED': [], 'LIVE and never read': [] };
for (const m of missed) {
  const v = byVendor.get(m.handle);
  if (m.kind === 'product' && outdoorVendors.has(v)) seg['outdoor cooking (scope-out by ruling)'].push(m);
  else if (m.status === 'DRAFT' || m.status === 'ARCHIVED' || m.status === 'unpublished') seg['DRAFT / ARCHIVED'].push(m);
  else if (m.kind === 'product' && /cover|mat|stone|oil|kit|rack|shelf|plate|bracket|hose|thermometer|bucket|ladle|backrest|cushion|headrest|light|filter|chimney|roof|door|bench|accessor/i.test(m.handle)) seg['accessories, parts and covers'].push(m);
  else seg['LIVE and never read'].push(m);
}
console.log('  segmented:');
for (const [k, v] of Object.entries(seg)) console.log(`    ${String(v.length).padStart(4)}  ${k}`);
console.log('\n  === LIVE AND NEVER READ — this is the set to read ===');
for (const r of seg['LIVE and never read'].sort((a, b) => b.len - a.len)) {
  console.log(`      ${r.kind.padEnd(11)} ${String(r.len).padStart(6)}ch  ${r.price != null ? ('$' + r.price).padEnd(10) : ''.padEnd(10)}${r.handle}`);
}

for (const k of Object.keys(by)) {
  console.log(`  ${k} — ${by[k].length}`);
  const notable = by[k].filter((r) => r.status === 'ACTIVE' || r.status === 'published' || r.status === 'n/a');
  for (const r of notable.sort((a, b) => b.len - a.len).slice(0, 30)) {
    console.log(`      ${String(r.len).padStart(6)}ch  ${r.price !== undefined && r.price !== null ? ('$' + String(r.price)).padEnd(10) : ''.padEnd(10)}${r.handle}`);
  }
  const rest = by[k].length - notable.length;
  if (rest > 0) console.log(`      (+${rest} draft/archived/unpublished not listed)`);
}
fs.writeFileSync(path.join(REPORTS, 'complement-intersection.md'),
  `# The intersection of every complement\n\nRun ${new Date().toISOString()}\n\n` +
  REVIEWS.map((r) => `- ${r.covers.size} — ${r.id}`).join('\n') +
  `\n\n**${missed.length} of ${universe.length} records were never substantively reviewed.**\n\n` +
  Object.entries(by).map(([k, v]) => `## ${k} (${v.length})\n\n` + v.map((r) => `- \`${r.handle}\` — ${r.status}, ${r.len} chars${r.price ? `, $${r.price}` : ''}`).join('\n')).join('\n\n'));
