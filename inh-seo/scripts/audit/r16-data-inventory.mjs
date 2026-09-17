/* Phase 2 — what the catalogue can actually support. Every figure is OUR price / OUR metafield.
 * Coverage is reported as "N of M carry it", never as a bare claim. */
import { gql } from '../lib/shopify.js';
import fs from 'node:fs';

let after = null, P = [];
do {
  const q = await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
    nodes{ handle title status vendor descriptionHtml
      cap: metafield(namespace:"custom", key:"capacity_"){ value }
      sty: metafield(namespace:"custom", key:"style"){ value }
      loc: metafield(namespace:"custom", key:"location_"){ value }
      wood: metafield(namespace:"custom", key:"wood"){ value }
      kf: metafield(namespace:"custom", key:"key_feature"){ value }
      dim: metafield(namespace:"custom", key:"dimentions_specifications"){ value }
      variants(first:3){ nodes{ price sku } }
      collections(first:25){ nodes{ handle } } } } }`, { a: after });
  P.push(...q.products.nodes);
  after = q.products.pageInfo.hasNextPage ? q.products.pageInfo.endCursor : null;
} while (after);

const ACTIVE = P.filter((p) => p.status === 'ACTIVE');
const txt = (p) => {
  const bits = [p.descriptionHtml || ''];
  for (const k of ['kf', 'dim']) { const v = p[k]?.value; if (!v) continue;
    try { const j = JSON.parse(v); const o = []; (function w(n){ if(!n) return; if(n.type==='text') o.push(n.value); (n.children||[]).forEach(w); })(j); bits.push(o.join(' ')); }
    catch { bits.push(v); } }
  return bits.join(' ').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/ /g, ' ');
};
const inColl = (p, h) => p.collections.nodes.some((c) => c.handle === h);
const price = (p) => parseFloat(p.variants.nodes[0]?.price ?? 'NaN');
const band = (arr) => { const v = arr.map(price).filter((x) => !Number.isNaN(x)).sort((a, b) => a - b);
  return v.length ? { n: v.length, min: v[0], max: v[v.length - 1], median: v[Math.floor(v.length / 2)] } : { n: 0 }; };

console.log(`products: ${P.length}   ACTIVE: ${ACTIVE.length}\n`);

console.log('── 1. METAFIELD COVERAGE (ACTIVE products) ──');
for (const [k, label] of [['cap','custom.capacity_'],['sty','custom.style'],['loc','custom.location_'],['wood','custom.wood']]) {
  const have = ACTIVE.filter((p) => p[k]?.value);
  const vals = {}; for (const p of have) vals[p[k].value] = (vals[p[k].value] || 0) + 1;
  console.log(`  ${label.padEnd(22)} ${String(have.length).padStart(3)} of ${ACTIVE.length}  (${((have.length/ACTIVE.length)*100).toFixed(0)}%)  values: ${JSON.stringify(vals)}`.slice(0, 210));
}

console.log('\n── 2. PRICE REALITY, our prices, ACTIVE only ──');
const IRcolls = ['infrared-saunas','far-infrared','full-spectrum'];
const ir = ACTIVE.filter((p) => IRcolls.some((c) => inColl(p, c)));
const trad = ACTIVE.filter((p) => inColl(p, 'sauna') && !IRcolls.some((c) => inColl(p, c)));
const steam = ACTIVE.filter((p) => inColl(p, 'steam-saunas') || inColl(p, 'steam-showers'));
for (const [label, set] of [['infrared', ir], ['traditional', trad], ['steam', steam]]) {
  const b = band(set);
  console.log(`  ${label.padEnd(12)} ${String(b.n).padStart(3)} products   $${b.min} – $${b.max}   median $${b.median}`);
}
console.log('\n  infrared by capacity (custom.capacity_):');
const byCap = {};
for (const p of ir) { const c = p.cap?.value || '(not published)'; (byCap[c] ||= []).push(p); }
for (const [c, set] of Object.entries(byCap).sort()) { const b = band(set); console.log(`    ${c.padEnd(18)} ${String(b.n).padStart(3)}  $${b.min} – $${b.max}  median $${b.median}`); }

console.log('\n── 3. EMF TIERS — the citable one ──');
const MG = /(\d+(?:\.\d+)?)\s*(?:to|–|-|—)?\s*(\d+(?:\.\d+)?)?\s*(?:mg|milligauss|milli-gauss)\b/i;
for (const c of ['low-emf','ultra-low-emf','near-zero-emf','far-infrared']) {
  const set = ACTIVE.filter((p) => inColl(p, c));
  const withNum = set.filter((p) => MG.test(txt(p)));
  const brands = [...new Set(withNum.map((p) => p.vendor))];
  const allBrands = [...new Set(set.map((p) => p.vendor))];
  console.log(`  /collections/${c.padEnd(15)} ${String(set.length).padStart(3)} ACTIVE   publish a NUMERIC mG figure: ${String(withNum.length).padStart(3)}  (${((withNum.length/(set.length||1))*100).toFixed(0)}%)`);
  console.log(`      brands in collection (${allBrands.length}): ${allBrands.join(', ').slice(0,110)}`);
  console.log(`      brands that publish a number (${brands.length}): ${brands.join(', ') || '— none —'}`);
}

console.log('\n── 4. ELECTRICAL ──');
const v120 = ACTIVE.filter((p) => /\b120\s*V|120V|110\s*V/i.test(txt(p)));
const v240 = ACTIVE.filter((p) => /\b240\s*V|240V|220\s*V/i.test(txt(p)));
const both = v120.filter((p) => v240.some((q) => q.handle === p.handle));
const neither = ACTIVE.filter((p) => !/\b(120|240|220|110)\s*V/i.test(txt(p)));
console.log(`  names 120V: ${v120.length}   names 240V: ${v240.length}   names both: ${both.length}   names NEITHER: ${neither.length} of ${ACTIVE.length}`);
const heaters = ACTIVE.filter((p) => inColl(p, 'sauna-heaters'));
const kw = heaters.map((p) => { const m = txt(p).match(/(\d+(?:\.\d+)?)\s*kw/i); return m ? parseFloat(m[1]) : null; }).filter(Boolean).sort((a,b)=>a-b);
console.log(`  sauna-heaters: ${heaters.length} ACTIVE, ${kw.length} publish a kW figure — range ${kw[0]}–${kw[kw.length-1]} kW`);

console.log('\n── 5. HEAT-UP TIME AND OPERATING TEMPERATURE ──');
const heatup = ACTIVE.filter((p) => /heat[- ]?up|preheat|warm[- ]?up|reaches? .{0,18}in \d+/i.test(txt(p)));
const temp = ACTIVE.filter((p) => /\d{2,3}\s*°?\s*F\b/i.test(txt(p)));
console.log(`  mention heat-up/preheat time: ${heatup.length} of ${ACTIVE.length}  (${((heatup.length/ACTIVE.length)*100).toFixed(0)}%)`);
console.log(`  publish an operating temperature in °F: ${temp.length} of ${ACTIVE.length}  (${((temp.length/ACTIVE.length)*100).toFixed(0)}%)`);
fs.writeFileSync('data/r16-inventory.json', JSON.stringify({ total: P.length, active: ACTIVE.length }, null, 1));
