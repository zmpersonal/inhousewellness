/* create-facet-collections — the four Phase 4 landing pages.
 *
 * Created UNPUBLISHED from the Online Store channel. The copy is generated and a
 * human reads it before it reaches a customer — hard rule 5. Publishing is the
 * human's action, exactly like a theme branch.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, cleanHTML, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';

const flags = parseArgs();
banner('create-facet-collections', flags);
const plan = readJSON(path.join(DATA, 'facet-collections.json')).collections;
const P = readJSON(path.join(DATA, 'products.json'));
const A = (Array.isArray(P) ? P : P.products).filter((x) => x.status === 'ACTIVE');

const t = (p) => p.title || '';
const cap = (p, n) => new RegExp('(^|[^0-9])' + n + '[\\s-]?(person|people|seat)', 'i').test(t(p));
const IR = (p) => /infrared|far ir\b/i.test(t(p)) || p.collections.some((c) => /^(infrared-saunas|far-infrared|full-spectrum)$/.test(c));
const OUTDOOR = (p) => /outdoor|barrel/i.test(t(p)) || p.collections.includes('outdoor-saunas');
const CORNER = (p) => /corner/i.test(t(p));
const SAUNA = (p) => p.collections.some((c) => /^(saunas|sauna|infrared-saunas|far-infrared|full-spectrum|outdoor-saunas|barrel-saunas)$/.test(c));
const RULES = {
  '6-person-sauna': (p) => SAUNA(p) && cap(p, 6),
  'indoor-infrared-sauna': (p) => SAUNA(p) && IR(p) && !OUTDOOR(p),
  '3-person-corner-sauna': (p) => SAUNA(p) && CORNER(p) && cap(p, 3),
  '2-person-infrared-sauna': (p) => SAUNA(p) && IR(p) && cap(p, 2),
};

const existing = await gql(`query{ collections(first:250){ nodes{ id handle } } }`);
const have = new Map(existing.collections.nodes.map((c) => [c.handle, c.id]));

const targets = [];
for (const c of plan) {
  if (have.has(c.handle)) { console.error(`  ✗ ${c.handle}: ALREADY EXISTS ${have.get(c.handle)} — refusing to create a duplicate`); process.exit(1); }
  const members = A.filter(RULES[c.handle]);
  if (!members.length) { console.error(`  ✗ ${c.handle}: zero members — refusing to create an empty collection`); process.exit(1); }
  const html = cleanHTML(c.body);
  assertWellFormed(html, `${c.handle} description`);
  const prices = members.map((m) => m.priceMin).filter(Boolean).sort((a, b) => a - b);
  console.log(`\n  ${c.handle}`);
  console.log(`    title  : ${c.title}`);
  console.log(`    seo    : ${c.seoTitle}  (${c.seoTitle.length})`);
  console.log(`    meta   : ${c.seoDescription}  (${c.seoDescription.length})`);
  console.log(`    members: ${members.length}   floor $${prices[0]}  median $${prices[Math.floor(prices.length / 2)]}`);
  console.log(`    copy   : ${html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().split(' ').length} words`);
  targets.push({ c, html, members });
}
assertOneWritePerRecord(targets, (x) => x.c.handle, 'create-facet-collections');

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
backup('facet-collections-plan', targets.map((x) => ({ handle: x.c.handle, members: x.members.map((m) => m.handle) })));

const pub = await gql(`query{ publications(first:20){ nodes{ id name } } }`);
const online = pub.publications.nodes.find((p) => p.name === 'Online Store');

for (const { c, html, members } of targets) {
  const m = await gql(`mutation($input:CollectionInput!){ collectionCreate(input:$input){ collection{ id handle } userErrors{ field message } } }`, {
    input: { title: c.title, handle: c.handle, descriptionHtml: html, seo: { title: c.seoTitle, description: c.seoDescription }, products: members.map((x) => x.id) },
  });
  if (m.collectionCreate.userErrors.length) { console.error(`  FAILED ${c.handle}:`, m.collectionCreate.userErrors); continue; }
  const id = m.collectionCreate.collection.id;
  if (online) {
    const u = await gql(`mutation($id:ID!,$input:[PublicationInput!]!){ publishableUnpublish(id:$id, input:$input){ userErrors{ field message } } }`, { id, input: [{ publicationId: online.id }] });
    if (u.publishableUnpublish.userErrors.length) console.error(`  ⚠ ${c.handle}: created but could NOT unpublish:`, u.publishableUnpublish.userErrors);
  }
  logChange({ resource: id, handle: c.handle, field: 'collection', before: '(did not exist)', after: `${members.length} products, unpublished`, note: 'Phase 4 facet landing page. UNPUBLISHED — a human publishes after reading the copy.' });
  console.log(`  created ${c.handle}  ${id}  (${members.length} products, UNPUBLISHED)`);
}
