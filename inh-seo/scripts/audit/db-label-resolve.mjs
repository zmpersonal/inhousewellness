/* Resolve every scholarly link across the 26 high-label articles. ENUMERATE BY RESOLVING.
 *   node scripts/audit/db-label-resolve.mjs
 * A text check reports these clean by construction — the label names a database, so there is
 * nothing in it to disagree with a destination. Only the href carries a checkable claim.
 */
import fs from 'node:fs';
const big = JSON.parse(fs.readFileSync('data/db-label-big29.json', 'utf8'));

const all = new Map();                       // url -> Set(handles)
for (const a of big) for (const u of a.scholarly) {
  if (!all.has(u)) all.set(u, new Set());
  all.get(u).add(a.handle);
}
console.log(`  ${big.length} articles, ${all.size} DISTINCT scholarly URLs, ${big.reduce((s,r)=>s+r.scholarlyOccurrences,0)} href OCCURRENCES`);

/* how many articles carry labels but NO scholarly link at all */
const none = big.filter((a) => a.scholarlyDistinct === 0);
console.log(`\n  articles with 20+ labels and ZERO scholarly links: ${none.length}`);
for (const a of none) console.log(`     ${String(a.instances).padStart(4)} labels, 0 links   ${a.handle}`);

/* which URLs are shared across articles — a shared paper is one fix applied N times */
const shared = [...all].filter(([, s]) => s.size > 1).sort((a, b) => b[1].size - a[1].size);
console.log(`\n  scholarly URLs appearing in MORE THAN ONE of the ${big.length}: ${shared.length}`);
for (const [u, s] of shared) console.log(`     ${s.size}×  ${u.slice(0, 74)}\n           ${[...s].join(', ').slice(0, 150)}`);

/* PMC5941775 across the WHOLE estate, not just these */
const allRows = JSON.parse(fs.readFileSync('data/db-label-shape.json', 'utf8'));
const p5941775 = allRows.filter((r) => r.scholarly.some((u) => /PMC5941775/i.test(u)));
console.log(`\n  PMC5941775 (Hussain & Cohen, routinely mislabelled) appears in ${p5941775.length} article(s) estate-wide:`);
for (const r of p5941775) console.log(`     ${r.handle}${r.instances ? `  (${r.instances} labels)` : ''}`);

fs.writeFileSync('data/db-scholarly-urls.json', JSON.stringify([...all].map(([u, s]) => ({ url: u, articles: [...s] })), null, 1));
