/* Round 18e item 5 — SITE-WIDE: articles quoting a specific InHouse price, vs the LIVE price. REPORT ONLY.
 *
 * ASSOCIATION-FREE, deliberately. Two association heuristics were tried and both were wrong in
 * opposite directions: "nearest $" gave Zurich the St. Moritz price sitting before its link;
 * "first $ after the link" made a genuine stale claim (Venice Elite "$2,499" vs $2,699 live)
 * disappear and gave red-light products their NEIGHBOUR's price. Tuning a heuristic until the
 * output looks right is how a guard stops meaning anything.
 *
 * The question asked instead: for a link to product P inside a block (td/th/li/p) that carries
 * any $ figure, does ANY figure in that block contain one of P's LIVE variant prices (±$1)?
 *   yes -> OK (the price is stated correctly somewhere, whatever the prose order)
 *   no  -> READ: a person decides whether the block quotes P's price at all, and if so whether
 *          it is stale. Verdicts are recorded by hand in HAND below, each with its reason.
 * Live prices come from the Admin API at run time — never the dump.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
const vis = (s) => s.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
const MONEY = /~?\$\s?\d{1,3}(?:,\d{3})+(?:\.\d{2})?(?:\s?[–-]\s?\$?\d{1,3}(?:,\d{3})+(?:\.\d{2})?)?|~?\$\s?\d{3,5}(?:\.\d{2})?/g;
const num = (s) => Number(s.replace(/[$,~\s]/g, ''));
const parse = (m) => { const p = m.split(/\s?[–-]\s?/).map(num).filter(Number.isFinite); return p.length === 2 ? [p[0], p[1]] : [p[0], p[0]]; };
const contains = (figs, prices) => figs.some((q) => prices.some((p) => p >= q[0] - 1 && p <= q[1] + 1));
const FIX = [
  ['range parsed', JSON.stringify(parse('$2,299–$2,499')) === '[2299,2499]'],
  ['block quoting the live price anywhere is OK', contains([[4999, 4999], [6999, 6999]], [6999])],
  ['block without the live price is READ', !contains([[2499, 2499]], [2699])],
  ['$1 rounding tolerated', contains([[1999.99, 1999.99]], [1999])],
];
for (const [l, ok] of FIX) if (!ok) { console.log('FIXTURE FAIL ' + l); process.exit(1); }

let cur = null; const arts = [];
while (true) {
  const r = await gql(`query($c:String){ articles(first:250, after:$c){ pageInfo{hasNextPage endCursor} nodes{ handle isPublished body blog{handle} } } }`, { c: cur });
  arts.push(...r.articles.nodes); if (!r.articles.pageInfo.hasNextPage) break; cur = r.articles.pageInfo.endCursor;
}
const pub = arts.filter((a) => a.isPublished);
const cache = {};
async function live(h) {
  if (h in cache) return cache[h];
  const q = await gql(`query($h:String!){ productByHandle(handle:$h){ status title variants(first:50){ nodes{ price } } } }`, { h });
  return (cache[h] = q.productByHandle ? { status: q.productByHandle.status, title: q.productByHandle.title, prices: q.productByHandle.variants.nodes.map((v) => Number(v.price)) } : null);
}
const rows = [];
for (const a of pub) {
  const b = a.body;
  for (const m of b.matchAll(/<a\b[^>]*href="(?:https:\/\/inhousewellness\.com)?\/products\/([^"?#]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/g)) {
    const at = m.index, h = m[1];
    const s = Math.max(b.lastIndexOf('<td', at), b.lastIndexOf('<th', at), b.lastIndexOf('<li', at), b.lastIndexOf('<p', at));
    const tag = b.startsWith('<td', s) ? 'td' : b.startsWith('<th', s) ? 'th' : b.startsWith('<li', s) ? 'li' : 'p';
    let e = b.indexOf(`</${tag}>`, at); if (s < 0 || e < 0) continue;
    // a link that fills a table cell: widen to the whole ROW, where its price column lives
    if (tag === 'td' || tag === 'th') { const r0 = b.lastIndexOf('<tr', at), r1 = b.indexOf('</tr>', at); if (r0 >= 0 && r1 > 0) { e = r1; } }
    const blockStart = (tag === 'td' || tag === 'th') ? b.lastIndexOf('<tr', at) : s;
    const block = b.slice(blockStart, e);
    const figs = [...block.matchAll(MONEY)].map((x) => x[0]);
    if (!figs.length) continue;
    const L = await live(h);
    const ok = L && contains(figs.map(parse), L.prices);
    const lo = L ? Math.min(...L.prices) : null, hi = L ? Math.max(...L.prices) : null;
    rows.push({ article: a.handle, blog: a.blog.handle, handle: h, anchor: vis(m[2]), status: L?.status, live: L ? (lo === hi ? `$${lo.toLocaleString('en-US')}` : `$${lo.toLocaleString('en-US')}–$${hi.toLocaleString('en-US')}`) : 'DOES NOT RESOLVE', figs, verdict: ok ? 'OK' : 'READ', ctx: vis(block) });
  }
}
fs.writeFileSync('data/r18e-price-staleness.json', JSON.stringify(rows, null, 2));
const arts_ = new Set(rows.map((r) => r.article));
console.log(`published articles: ${pub.length}   articles with a product link beside a $ figure: ${arts_.size}   (link/block pairs: ${rows.length})`);
console.log(`  OK   (block states the live price): ${rows.filter((r) => r.verdict === 'OK').length}`);
console.log(`  READ (live price absent from the block): ${rows.filter((r) => r.verdict === 'READ').length}\n`);
for (const r of rows.filter((r) => r.verdict === 'READ'))
  console.log(`  ${r.article.slice(0, 34).padEnd(34)} ${r.handle.slice(0, 44).padEnd(44)} live ${String(r.live).padEnd(14)} ${r.status !== 'ACTIVE' ? '[' + r.status + '] ' : ''}figs ${r.figs.join(' ')}\n      [${r.anchor.slice(0, 50)}] "${r.ctx.slice(0, 300)}"`);
