/**
 * SEO title and meta description for the 8 blog index pages.
 *
 * All eight had NEITHER. And because theme.liquid's description chain has no
 * `else`, a blog with no `description_tag` renders NO <meta name="description">
 * at all — not a bad one, none. Eight of eight.
 *
 * Blog SEO lives in metafields — `global.title_tag` / `global.description_tag` —
 * the same as Article, because Blog has no `seo` field in API 2026-07.
 *
 * Durable-first per rule 6a-ii: no article counts. A blog index gains and loses
 * articles constantly and a count there is the most fragile figure on the site.
 *
 *   node scripts/apply/blog-seo.mjs            # dry run
 *   node scripts/apply/blog-seo.mjs --apply
 */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange } from '../lib/util.js';

const flags = parseArgs();
banner('blog-seo', flags);

const SEO = {
  saunas: {
    t: 'Sauna Guides: Cost, Wiring, EMF and What Nobody Publishes',
    m: 'Infrared and traditional saunas — what they cost to install and run, what the EMF numbers mean, and the specifications manufacturers do not publish.' },
  'cold-plunge': {
    t: 'Cold Plunge Guides: Chillers, Filtration and Real Costs',
    m: 'Chilled or filled, what a chiller adds to the running cost, filtration that actually works, and what the evidence does and does not show.' },
  wellness: {
    t: 'The Wellness Edit | Home Wellness, Evidence First',
    m: 'Home wellness equipment assessed on what is checkable: temperatures, costs, electrical requirements, and what the research supports.' },
  institute: {
    t: 'Wellness Institute | Research Notes and Evidence Reviews',
    m: 'Longer-form notes on heat, cold and light exposure research — what was measured, in whom, and what the findings do not establish.' },
  fire: {
    t: 'Fire Pits and Outdoor Heat | Safety, Clearances, Setup',
    m: 'Fire pit safety, clearances, local rules and what to check before a backyard install. Practical guidance, not product marketing.' },
  news: {
    t: 'News | InHouse Wellness',
    m: 'Announcements and updates from InHouse Wellness, a US retailer of home saunas, cold plunges and steam rooms.' },
  'media-responses': {
    t: 'Media Responses | InHouse Wellness',
    m: 'Responses to media coverage and public questions about home sauna and cold plunge products.' },
  'home-improvement-reviews': {
    t: 'Home Improvement Reviews | InHouse Wellness',
    m: 'Reviews of home improvement products and installations relevant to home sauna and cold plunge buyers.' },
};

const r = await gql(`query{ blogs(first:50){ nodes{ id handle title
  t: metafield(namespace:"global", key:"title_tag"){ value }
  d: metafield(namespace:"global", key:"description_tag"){ value } } } }`);

const targets = [];
for (const b of r.blogs.nodes) {
  const spec = SEO[b.handle];
  if (!spec) { console.log(`  ? ${b.handle}: no spec — skipped`); continue; }
  const tLen = spec.t.length, mLen = spec.m.length;
  if (tLen >= 60) { console.error(`  ✗ ${b.handle}: title ${tLen} chars, must be under 60`); process.exit(1); }
  if (mLen >= 155) { console.error(`  ✗ ${b.handle}: meta ${mLen} chars, must be under 155`); process.exit(1); }
  /* Copy spec: "Only fill null fields. Do not overwrite an existing meta
     description unless the task says so explicitly." home-improvement-reviews
     already has one — mine is not better enough to justify overwriting a field
     someone wrote deliberately. */
  const overwrite = process.argv.includes('--overwrite');
  const skipMeta = !!b.d?.value && !overwrite;
  console.log(`\n  ${b.handle}`);
  console.log(`    title  ${b.t?.value ? `"${b.t.value}"` : '(none)'}  ->  "${spec.t}"  (${tLen})`);
  console.log(`    meta   ${b.d?.value ? `"${b.d.value.slice(0,40)}…"` : '(none)'}  ->  ${skipMeta ? 'UNCHANGED — already set. Pass --overwrite to replace.' : `"${spec.m.slice(0,60)}…"  (${mLen})`}`);
  targets.push({ b, spec, skipMeta });
}
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('blog-seo-before', targets.map((t) => ({ id: t.b.id, handle: t.b.handle, title_tag: t.b.t?.value ?? null, description_tag: t.b.d?.value ?? null })));

const M = `mutation($metafields:[MetafieldsSetInput!]!){
  metafieldsSet(metafields:$metafields){ metafields{ key } userErrors{ field message } } }`;
let ok = 0;
for (const { b, spec, skipMeta } of targets) {
  const mf = [{ ownerId: b.id, namespace: 'global', key: 'title_tag', type: 'single_line_text_field', value: spec.t }];
  if (!skipMeta) mf.push({ ownerId: b.id, namespace: 'global', key: 'description_tag', type: 'single_line_text_field', value: spec.m });
  const res = await gql(M, { metafields: mf });
  if (res.metafieldsSet.userErrors.length) { console.error(`  FAILED ${b.handle}:`, res.metafieldsSet.userErrors); continue; }
  logChange({ script: 'blog-seo', kind: 'blog', id: b.id, handle: b.handle, field: 'seo metafields',
    before: { title: b.t?.value ?? null, description: b.d?.value ?? null }, after: { title: spec.t, description: spec.m } });
  ok += 1; console.log(`  updated ${b.handle}`);
}
console.log(`\n${ok}/${targets.length} applied.`);
