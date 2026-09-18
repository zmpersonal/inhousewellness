/* Round 16 — re-derive EVERY figure that appears in the two comparison drafts.
 *
 * WHY: the Phase-2 inventory produced an infrared count (95) by matching titles and a price
 * range ($1,999-$16,999) from collection membership, and I wrote both into one sentence.
 * That is the "a range is only a range if both ends are measured the same way" failure.
 * Everything here comes from ONE definition: ACTIVE members of the named collection.
 *
 * Median = median of priceMin across ACTIVE members only (CLAUDE.md 6c).
 */
import fs from 'node:fs';

const P = JSON.parse(fs.readFileSync('data/products.json', 'utf8'));
const ALL = Array.isArray(P) ? P : (P.products || P.nodes);
const A = ALL.filter((p) => (p.status || '').toUpperCase() === 'ACTIVE');
const N = A.length;
const inC = (p, h) => (p.collections || []).some((c) => (c.handle || c) === h);
const txt = (p) => `${p.title || ''} ${p.descriptionHtml || ''}`;
const money = (n) => '$' + n.toLocaleString('en-US');

// space class built from CODE POINTS, never typed glyphs (CLAUDE.md)
const SP = '[\\u0020\\u00A0\\u202F\\u2009\\u200B]*';

function stats(arr) {
  const v = arr.map((p) => +p.priceMin).filter(Number.isFinite).sort((a, b) => a - b);
  if (!v.length) return null;
  return { n: arr.length, min: v[0], max: v[v.length - 1], med: v[Math.floor(v.length / 2)] };
}
const line = (label, s) => console.log(`  ${label.padEnd(26)} n=${String(s.n).padStart(3)}  ${money(s.min)} – ${money(s.max)}  median ${money(s.med)}`);

console.log(`POPULATION: ${ALL.length} products, ${N} ACTIVE\n`);

console.log('PRICE BANDS (ACTIVE members of the collection)');
line('infrared-saunas', stats(A.filter((p) => inC(p, 'infrared-saunas'))));
line('sauna (Traditional)', stats(A.filter((p) => inC(p, 'sauna'))));
line('steam-saunas + showers', stats(A.filter((p) => inC(p, 'steam-saunas') || inC(p, 'steam-showers'))));
line('  steam-saunas', stats(A.filter((p) => inC(p, 'steam-saunas'))));
line('  steam-showers', stats(A.filter((p) => inC(p, 'steam-showers'))));

console.log('\nINFRARED BY CAPACITY (person-count stated in the title)');
const IR = A.filter((p) => inC(p, 'infrared-saunas'));
const CAP = /(\d+)[\s\u00A0\u2011-]?person/i;   // 18i: code points (NBSP, non-breaking hyphen), not typed glyphs
const cap = {};
for (const p of IR) { const m = (p.title || '').match(CAP); if (m) (cap[+m[1]] ||= []).push(+p.priceMin); }
let capTot = 0;
for (const k of Object.keys(cap).sort((a, b) => a - b)) {
  const v = cap[k].sort((a, b) => a - b); capTot += v.length;
  console.log(`  ${k}-person`.padEnd(28) + `n=${String(v.length).padStart(3)}  ${money(v[0])} – ${money(v[v.length - 1])}  median ${money(v[Math.floor(v.length / 2)])}`);
}
console.log(`  → ${capTot} of ${IR.length} infrared cabins state a person-count in the title`);

console.log(`\nCOVERAGE (denominator = all ${N} ACTIVE)`);   // 18i: derived, was the literal 481
const cov = (label, re) => {
  const hit = A.filter((p) => re.test(txt(p)));
  console.log(`  ${label.padEnd(34)} ${String(hit.length).padStart(3)} of ${N}  (${Math.round(hit.length / N * 100)}%)`);
  return hit;
};
const v120 = cov('names 120V', new RegExp(`\\b120${SP}v`, 'i'));
const v240 = cov('names 240V or 220V', new RegExp(`\\b(?:240|220)${SP}v`, 'i'));
cov('publishes a heat-up / preheat time', /heat(?:s)?[-\s]?up|pre[-\s]?heat|reaches?\s+\d+\s*°?\s*F\s+in/i);
cov('states any temperature in °F', /\d{2,3}\s*°?\s*F\b/i);
const S = new Set(v120), T = new Set(v240);
const both = A.filter((p) => S.has(p) && T.has(p)).length;
const none = A.filter((p) => !S.has(p) && !T.has(p)).length;
console.log(`  ${'names BOTH voltages'.padEnd(34)} ${String(both).padStart(3)} of ${N}`);
console.log(`  ${'names NEITHER — the finding'.padEnd(34)} ${String(none).padStart(3)} of ${N}  (${Math.round(none / N * 100)}%)`);

const HS = A.filter((p) => inC(p, 'sauna-heaters'));
const kw = HS.filter((p) => /\d+(?:\.\d+)?\s*kW/i.test(txt(p)));
console.log(`\nSAUNA HEATERS: ${kw.length} of ${HS.length} ACTIVE publish a kW rating`);
console.log('  (range deliberately NOT published — CLAUDE.md records "3kW to 50kW" as false:');
console.log('   the 3 came from a bag of sauna rocks, the 50 from a stove the store does not sell)');

console.log('\nCOMBINATION UNITS');
for (const h of ['finnmark-fd-4', 'finnmark-fd-5-trinity-xl', 'finnmark-fd-3', 'finnmark-fd-2']) {
  const p = ALL.find((x) => x.handle === h);
  console.log(`  ${(p ? p.status : 'MISSING').padEnd(8)} ${money(+p.priceMin).padStart(8)}  ${h}`);
}

console.log('\nUNIVERSAL NEGATIVE');
/** Rows naming steam whose TITLE names an enclosure. The live set is empty, so without a fixture
 *  this check could be dead and still print ✓ (18i). */
const steamEnclosures = (rows) => rows
  .filter((p) => /steam/i.test(`${p.title} ${p.productType}`))
  .filter((p) => /\b(room|enclosure|cabin|cabinet|booth)\b/i.test(p.title || ''));
// 18i: proves the check can fire — a constructed enclosure row must be found, a generator must not
const ENCL_FX = [
  { title: 'Modular Steam Room Enclosure 4x6', productType: 'Steam Accessories' },
  { title: 'Delta SimpleSteam 12kW Generator', productType: 'Steam Generator' },
];
const fxHit = steamEnclosures(ENCL_FX);
if (fxHit.length !== 1 || fxHit[0] !== ENCL_FX[0]) {
  console.log(`  ✗ SELF-TEST: the enclosure check found ${fxHit.length} of the 1 constructed enclosure — the negative below is not trustworthy`);
  process.exit(1);
}
const steamish = A.filter((p) => /steam/i.test(`${p.title} ${p.productType}`));
const enclosure = steamEnclosures(A);
console.log(`  ACTIVE products naming steam: ${steamish.length}; of those, titles naming an ENCLOSURE: ${enclosure.length}`);
if (enclosure.length !== 0) { console.log('  ✗ the universal negative NO LONGER HOLDS — the steam article must be edited'); process.exitCode = 1; }
else console.log('  ✓ "not one active product is a steam enclosure" holds');
