/* Add featured-image URLs to hand-written ItemList Product nodes. --dry-run default.
 *
 * Two articles carry hand-written ItemList schema whose Product entries have no
 * `image`, which is a required field. Images are SOURCED from each product's own
 * featuredMedia — never chosen, never invented.
 *
 * A node whose product is not purchasable is DROPPED rather than illustrated:
 * schema advertising an offer for a draft product is worse than a missing image.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertOneWritePerRecord } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const TARGETS = ['best-6-person-sauna', 'best-outdoor-cold-plunge-tubs'];
assertOneWritePerRecord(TARGETS.map((h) => ({ h })), (x) => x.h, 'itemlist images');

let after = null, arts = [];
for (;;) {
  const r = await gql(`query($a:String){ articles(first:100, after:$a){ pageInfo{hasNextPage endCursor} nodes{ id handle body } } }`, { a: after });
  arts.push(...r.articles.nodes);
  if (!r.articles.pageInfo.hasNextPage) break;
  after = r.articles.pageInfo.endCursor;
}

const jobs = [];
for (const handle of TARGETS) {
  const a = arts.find((x) => x.handle === handle);
  if (!a) throw new Error(`article not found: ${handle}`);

  const blocks = [...a.body.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)];
  const target = blocks.find((m) => /"ItemList"/.test(m[1]));
  if (!target) throw new Error(`${handle}: no ItemList block`);

  const raw = target[1].trim();
  const j = JSON.parse(raw);
  const kept = [];
  const dropped = [];

  for (const el of j.itemListElement) {
    const it = el.item || el;
    if (it['@type'] !== 'Product') { kept.push(el); continue; }
    const m = String(it.url || '').match(/\/products\/([a-z0-9-]+)/i);
    if (!m) { dropped.push([it.name, 'no product URL']); continue; }
    const r = await gql(`query($q:String!){ products(first:1, query:$q){ nodes{ handle status featuredMedia{ ... on MediaImage { image{ url } } } } } }`, { q: 'handle:' + m[1] });
    const p = r.products.nodes[0];
    if (!p) { dropped.push([it.name, 'not in catalogue']); continue; }
    if (p.status !== 'ACTIVE') { dropped.push([it.name, `status ${p.status} — not purchasable`]); continue; }
    const img = p.featuredMedia && p.featuredMedia.image && p.featuredMedia.image.url;
    if (!img) { dropped.push([it.name, 'no featured image']); continue; }
    it.image = img.split('?')[0];
    kept.push(el);
  }

  /* renumber positions if the schema uses them */
  kept.forEach((el, i) => { if (el.position !== undefined) el.position = i + 1; });
  j.itemListElement = kept;

  const out = JSON.stringify(j, null, 2);
  const n = a.body.split(raw).length - 1;
  if (n !== 1) throw new Error(`${handle}: ItemList block matched ${n} times`);
  const body = a.body.replace(raw, out);

  console.log(`  ── ${handle}`);
  console.log(`     nodes ${j.itemListElement.length} kept, ${dropped.length} dropped`);
  dropped.forEach(([n2, why]) => console.log(`        DROPPED  ${String(n2).slice(0, 46)}  (${why})`));
  console.log(`     every kept Product now has an image: ${kept.filter((e) => (e.item || e)['@type'] === 'Product').every((e) => (e.item || e).image)}`);
  jobs.push({ id: a.id, handle, before: a.body, after: body });
}

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const bpath = backup('itemlist-images', jobs.map((j) => ({ handle: j.handle, id: j.id, body: j.before })));
console.log(`\n  backup -> ${bpath.split('/').slice(-2).join('/')}`);
let ok = 0;
for (const j of jobs) {
  const r = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: j.id, article: { body: j.after } });
  if (r.articleUpdate.userErrors.length) { console.log(`  FAIL ${j.handle}: ${JSON.stringify(r.articleUpdate.userErrors)}`); continue; }
  logChange({ resource: j.id, handle: j.handle, type: 'article', field: 'body(ItemList schema)', from: 'Product nodes with no image', to: 'featured image URLs sourced from each product', note: 'Semrush error 1 / hand-written ItemList', backup: bpath });
  ok++;
}
console.log(`\n  applied ${ok}/${jobs.length}`);
