/**
 * Stages the canonical TARGET for four Sources pages as a metafield.
 *
 * IT DOES NOT MAKE THE CANONICAL TAKE EFFECT. `theme.liquid` line 42 renders
 * Shopify's built-in `{{ canonical_url }}`, which always points a page at itself
 * and has no override. A custom canonical needs one line of Liquid that reads
 * this metafield — staged for the NEXT theme branch, not the one currently under
 * review.
 *
 * Writing the data first is deliberate: the metafield is inert until the theme
 * reads it, so it can be reviewed and corrected with zero risk, and the theme
 * change becomes a one-liner with its data already proven.
 *
 *   node scripts/apply/set-canonical-metafields.mjs [--apply]
 */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange } from '../lib/util.js';

const flags = parseArgs();
banner('set-canonical-metafields', flags);

/* Each parent is NAMED IN THE SOURCES PAGE'S OWN OPENING SENTENCE. That is the
   source of truth — not topical similarity. The two pages whose stated parent
   404s are deliberately absent; see reports/sources-canonicals.md. */
const MAP = {
  'float-therapy-sleep-sources': 'how-float-tanks-improve-sleep-quality',
  'firepit-safety': 'fire-pit-safety-tips-backyard-gatherings',
  'plunge-immune-function': 'cold-plunge-immune-system-boost',
  'office-massage-chair-evidence-library': 'massage-chairs-office-workers',
};

const q = `query($q:String!){ articles(first:1, query:$q){ nodes{ id handle isPublished blog{ handle }
  c: metafield(namespace:"custom", key:"canonical_url"){ value } } } }`;

const targets = [];
for (const [child, parent] of Object.entries(MAP)) {
  const a = (await gql(q, { q: 'handle:' + child })).articles.nodes[0];
  const p = (await gql(q, { q: 'handle:' + parent })).articles.nodes[0];
  if (!a) { console.error(`  ✗ ${child}: not found`); process.exit(1); }
  /* refuse to point at a parent that is not live — a canonical to a 404 is
     worse than no canonical */
  if (!p || !p.isPublished) { console.error(`  ✗ ${child}: parent ${parent} is missing or unpublished — REFUSING`); process.exit(1); }
  const url = `https://inhousewellness.com/blogs/${p.blog.handle}/${p.handle}`;
  console.log(`  ${child}`);
  console.log(`     -> ${url}   (parent live: yes)`);
  if (a.c?.value) console.log(`     existing value: ${a.c.value}`);
  targets.push({ a, url });
}
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('canonical-metafields-before', targets.map((t) => ({ id: t.a.id, handle: t.a.handle, canonical: t.a.c?.value ?? null })));
const M = `mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ key } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { m: [{ ownerId: t.a.id, namespace: 'custom', key: 'canonical_url', type: 'url', value: t.url }] });
  if (r.metafieldsSet.userErrors.length) { console.error(`  FAILED ${t.a.handle}:`, r.metafieldsSet.userErrors); continue; }
  logChange({ script: 'set-canonical-metafields', kind: 'article', id: t.a.id, handle: t.a.handle,
    field: 'custom.canonical_url', before: t.a.c?.value ?? null, after: t.url,
    reason: 'Sources page canonicalised to the parent it names in its own opening sentence. INERT until theme.liquid reads it.' });
  ok += 1; console.log(`  set ${t.a.handle}`);
}
/* verify the OUTCOME, not the mutation result */
console.log('');
for (const t of targets) {
  const back = (await gql(q, { q: 'handle:' + t.a.handle })).articles.nodes[0];
  console.log(`  ${back.c?.value === t.url ? 'OK  ' : 'FAIL'} ${t.a.handle}  ${back.c?.value || '(none)'}`);
}
console.log(`\n${ok}/${targets.length} staged. NOT YET IN EFFECT — needs the theme one-liner.`);
