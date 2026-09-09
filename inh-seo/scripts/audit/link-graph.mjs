/**
 * B3 diagnostic — the current internal link graph, as data.
 * Read-only. Produces data/link-graph.json. Decides nothing.
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, probeText } from '../lib/util.js';

const C = readJSON(path.join(DATA, 'collections.json'));
const P = readJSON(path.join(DATA, 'products.json'));
const content = readJSON(path.join(DATA, 'content.json'));
const arts = content.articles || [];
const pubCols = C.filter(c => c.publishedOnline);
const withCopy = C.filter(c => c.descriptionLength > 0);
const body = a => String(a.bodyHtml || a.body || '');

/* --- edges --- */
const edges = [];
for (const a of arts) {
  const h = body(a);
  for (const m of h.matchAll(/href="[^"]*\/collections\/([a-z0-9-]+)/gi)) edges.push({ from: a.handle, fromTitle: a.title, to: m[1] });
  for (const m of h.matchAll(/href="[^"]*\/products\/([a-z0-9-]+)/gi)) edges.push({ from: a.handle, fromTitle: a.title, to: m[1], kind: 'product' });
}
const colEdges = edges.filter(e => e.kind !== 'product');
const inbound = {};
colEdges.forEach(e => { (inbound[e.to] ||= new Set()).add(e.from); });

/* --- collection→collection links (from the copy we wrote) --- */
const colToCol = {};
for (const c of withCopy) {
  const outs = [...String(c.descriptionHtml).matchAll(/href="\/collections\/([a-z0-9-]+)/g)].map(m => m[1]);
  if (outs.length) colToCol[c.handle] = [...new Set(outs)];
}

/* --- articles linking to nothing commercial --- */
const orphanArts = arts.filter(a => {
  const h = body(a);
  return !/href="[^"]*\/(collections|products)\//i.test(h);
});

/* --- where the 28 unlinked collections could naturally receive links --- */
const unlinked = withCopy.filter(c => !inbound[c.handle]);
const tok = s => new Set(probeText(s).replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(w => w.length > 3));
const STOP = new Set(['sauna','saunas','with','from','your','that','this','best','guide','review','home','wellness','what','how','the','and','for']);
const suggestions = {};
for (const c of unlinked) {
  const ct = [...tok(c.title + ' ' + c.handle.replace(/-/g, ' '))].filter(w => !STOP.has(w));
  if (!ct.length) continue;
  const scored = arts.map(a => {
    const at = tok((a.title || '') + ' ' + body(a).replace(/<[^>]+>/g, ' ').slice(0, 3000));
    const hits = ct.filter(w => at.has(w));
    return { article: a.handle, title: a.title, score: hits.length, matched: hits };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 3);
  if (scored.length) suggestions[c.handle] = scored;
}

const out = {
  _meta: { generated: new Date().toISOString(), purpose: 'B3 diagnostic. Read-only. Shape before rules.' },
  totals: {
    articles: arts.length,
    published_collections: pubCols.length,
    collections_with_copy: withCopy.length,
    article_to_collection_links: colEdges.length,
    article_to_product_links: edges.length - colEdges.length,
    articles_linking_to_any_commercial_page: arts.length - orphanArts.length,
    articles_linking_to_nothing_commercial: orphanArts.length,
    distinct_collections_receiving_links: Object.keys(inbound).length,
    collections_with_copy_and_zero_inbound: unlinked.length,
  },
  inbound_by_collection: Object.fromEntries(Object.entries(inbound).map(([k, v]) => [k, v.size]).sort((a, b) => b[1] - a[1])),
  zero_inbound_with_copy: unlinked.map(c => c.handle),
  collection_to_collection: colToCol,
  articles_linking_to_nothing_commercial: orphanArts.map(a => ({ handle: a.handle, title: a.title })),
  suggested_sources_for_unlinked: suggestions,
};
fs.writeFileSync(path.join(DATA, 'link-graph.json'), JSON.stringify(out, null, 2));

const t = out.totals;
console.log('=== LINK GRAPH, AS IT STANDS ===\n');
console.log(`  articles                                 ${t.articles}`);
console.log(`  published collections                    ${t.published_collections}`);
console.log(`  collections with copy                    ${t.collections_with_copy}\n`);
console.log(`  article -> collection links              ${t.article_to_collection_links}`);
console.log(`  article -> product links                 ${t.article_to_product_links}`);
console.log(`  articles linking to SOMETHING commercial ${t.articles_linking_to_any_commercial_page} of ${t.articles}`);
console.log(`  articles linking to NOTHING commercial   ${t.articles_linking_to_nothing_commercial}\n`);
console.log(`  collections receiving >=1 blog link      ${t.distinct_collections_receiving_links} of ${t.published_collections}`);
console.log(`  collections WITH COPY and zero inbound   ${t.collections_with_copy_and_zero_inbound} of ${t.collections_with_copy}`);
console.log(`  collections linking to other collections ${Object.keys(colToCol).length}\n`);
console.log('  most-linked collections:');
Object.entries(out.inbound_by_collection).slice(0, 8).forEach(([k, v]) => console.log(`    ${k.padEnd(30)} ${v}`));
console.log('\n  sample of natural sources for unlinked collections:');
Object.entries(suggestions).slice(0, 6).forEach(([c, s]) => {
  console.log(`    ${c}`);
  s.slice(0, 2).forEach(x => console.log(`       <- ${String(x.title).slice(0, 62)}  [${x.matched.slice(0,3).join(', ')}]`));
});
console.log(`\n  wrote data/link-graph.json`);
