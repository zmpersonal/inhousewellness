/* Round 18e — every InHouse price, model number, product link and "same model" claim in
 * costco-sauna-guide-worth-it, checked against the LIVE catalogue (Admin API, not the dump).
 * READ-ONLY. A claim is only as good as the product it resolves to.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
const r = await gql(`query{ articles(first:5, query:"handle:costco-sauna-guide-worth-it"){ nodes{ handle body } } }`);
const b = r.articles.nodes.find((x) => x.handle === 'costco-sauna-guide-worth-it').body;
const vis = (s) => s.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
const cache = {};
async function prod(h) {
  if (cache[h]) return cache[h];
  const q = await gql(`query($h:String!){ productByHandle(handle:$h){ title status variants(first:10){ nodes{ sku price } } } }`, { h });
  return (cache[h] = q.productByHandle);
}
// the block (cell / li / p) each INH link sits in, and the next cell when the link fills a cell
const links = [...b.matchAll(/<a\b[^>]*href="https:\/\/inhousewellness\.com\/products\/([^"?#]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/g)];
console.log(`A. INH PRODUCT LINKS: ${links.length}\n`);
const rows = [];
for (const m of links) {
  const h = m[1], anchor = vis(m[2]), at = m.index;
  const p = await prod(h);
  const blockStart = Math.max(b.lastIndexOf('<td', at), b.lastIndexOf('<li', at), b.lastIndexOf('<p', at));
  const inCell = b.lastIndexOf('<td', at) === blockStart;
  const blockEnd = b.indexOf(inCell ? '</td>' : b.startsWith('<li', blockStart) ? '</li>' : '</p>', at);
  const block = vis(b.slice(blockStart, blockEnd));
  let nextCell = '';
  if (inCell) { const n0 = b.indexOf('<td', blockEnd); const n1 = b.indexOf('</td>', n0); if (n0 > 0 && n0 < b.indexOf('</tr>', at)) nextCell = vis(b.slice(n0, n1)); }
  const skus = p ? p.variants.nodes.map((v) => v.sku).join(', ') : 'DOES NOT RESOLVE';
  const prices = p ? [...new Set(p.variants.nodes.map((v) => '$' + Number(v.price).toLocaleString('en-US')))].join('/') : '-';
  // does the anchor text describe the product it points at?
  const aT = anchor.toLowerCase(), pT = (p?.title || '').toLowerCase();
  const flags = [];
  if (/1[–-]2/.test(aT) && !/1-2|1–2/.test(pT)) flags.push('anchor says 1–2P, product is not');
  if (/full[- ]spectrum|\bfs\b/.test(pT) && !/full[- ]spectrum/.test(aT) && /gracia/.test(aT)) flags.push('links FULL-SPECTRUM model for a plain Gracia');
  if (p && p.status !== 'ACTIVE') flags.push('product ' + p.status);
  rows.push({ at, h, anchor, skus, prices, flags, block: block.slice(0, 150), nextCell });
  console.log(`  @${String(at).padStart(5)}  [${anchor.slice(0, 44)}]`);
  console.log(`          -> ${h}  ${skus}  live ${prices}${p ? '  "' + p.title.slice(0, 60) + '"' : ''}`);
  if (flags.length) console.log(`          !! ${flags.join('; ')}`);
}
console.log(`\nB. PRICES ATTRIBUTED TO INHOUSE (a $ figure in a sentence naming InHouse, or in the "InHouse price" column)`);
const sents = vis(b).split(/(?<=[.!?])\s+/);
for (const s of sents) if (/InHouse|at InHouse|our price|we charge|InHouse Wellness/i.test(s) && /\$\s?\d/.test(s)) console.log('   · ' + s.slice(0, 220));
const t7 = b.slice(b.lastIndexOf('<table', b.indexOf('Exact same model')), b.indexOf('</table>', b.indexOf('Exact same model')));
for (const tr of t7.matchAll(/<tr>([\s\S]*?)<\/tr>/g)) { const c = [...tr[1].matchAll(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/g)].map((x) => vis(x[1])); if (c[3] && /\$/.test(c[3])) console.log(`   · TABLE 7 "InHouse price" cell: ${c[0]} -> ${c[3]}   relationship: ${c[4]}`); }
console.log(`\nC. MODEL NUMBERS in visible text`);
for (const m of vis(b).matchAll(/\b(?:DYN|MX|GDI|SPE|SCS)-[A-Z0-9-]+\b/g)) console.log('   · ' + m[0]);
console.log(`\nD. SAME-MODEL / IDENTICAL CLAIMS (every representation)`);
for (const s of sents) if (/exact same|same model|identical|same (?:Bellagio|Gracia|San Marino|unit|sauna|hardware)|the identical unit/i.test(s)) console.log('   · ' + s.slice(0, 230));
fs.writeFileSync('data/r18e-costco-guide-audit.json', JSON.stringify(rows, null, 2));
