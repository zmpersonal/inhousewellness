/* Restore from any backup this repo wrote, through the one sanctioned path.
 *   node scripts/apply/restore-from-backup.mjs <backup.json> [--only <key>] [--apply]
 *   node scripts/apply/restore-from-backup.mjs --self-test
 *
 * Adapters are chosen by the SHAPE of the rows, not by the filename — a filename list goes stale, and
 * this repo has already had a gate fail because it keyed on one (check_facts_cache).
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { gql } from '../lib/shopify.js';
import { restoreRows } from '../lib/restore.mjs';
import { logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const ONLY = arg('--only');
const J = (o) => JSON.stringify(o);

export function pickShape(row) {
  const k = Object.keys(row || {});
  if (k.includes('seoTitle') && k.includes('seoDescription')) return 'seo-fields';
  if (k.includes('titleTag') && k.includes('descriptionTag')) return 'article-seo';
  if (k.includes('collectionsBefore') && k.includes('productId')) return 'membership';
  if (k.includes('before') && (k.includes('md5') || k.includes('storedMd5'))) return 'body-or-metafield';
  return null;
}

const ADAPTERS = {
  'seo-fields': {
    key: (r) => r.handle,
    describe: (r) => J([r.seoTitle ?? null, r.seoDescription ?? null]),
    storedOf: () => null,                       // this shape predates the stored-value convention
    readLive: async (r) => {
      const t = r.id.includes('/Collection/') ? 'collection' : 'product';
      const d = await gql(`query($id:ID!){ ${t}(id:$id){ seo{ title description } } }`, { id: r.id });
      const n = d[t]; if (!n) throw new Error('record not found');
      return J([n.seo.title || null, n.seo.description || null]);
    },
    writeBack: async (r) => {
      const isC = r.id.includes('/Collection/');
      const m = isC ? 'collectionUpdate' : 'productUpdate';
      /* ProductUpdateInput, not ProductInput: the latter is what crashed r23i-vendor-merge, and this
         branch had never run because every seo-fields backup on disk is a COLLECTION. */
      const inputT = isC ? 'CollectionInput' : 'ProductUpdateInput';
      const d = await gql(`mutation($p:${inputT}!){ ${m}(${isC ? 'input' : 'product'}:$p){ userErrors{ message } } }`,
        { p: { id: r.id, seo: { title: r.seoTitle, description: r.seoDescription } } });
      if (d[m].userErrors.length) throw new Error(J(d[m].userErrors));
      return ADAPTERS['seo-fields'].readLive(r);
    },
  },
  'article-seo': {
    key: (r) => r.handle,
    describe: (r) => J([r.titleTag ?? null, r.descriptionTag ?? null]),
    storedOf: () => null,
    readLive: async (r) => {
      const d = await gql(`query($id:ID!){ node(id:$id){ ... on Article { metafields(first:50){ nodes{ namespace key value } } } } }`, { id: r.id });
      if (!d.node) throw new Error('article not found');
      const get = (kk) => d.node.metafields.nodes.find((m) => m.namespace === 'global' && m.key === kk)?.value ?? null;
      return J([get('title_tag'), get('description_tag')]);
    },
    writeBack: async (r) => {
      const mf = [];
      if (r.titleTag != null) mf.push({ ownerId: r.id, namespace: 'global', key: 'title_tag', type: 'single_line_text_field', value: r.titleTag });
      if (r.descriptionTag != null) mf.push({ ownerId: r.id, namespace: 'global', key: 'description_tag', type: 'single_line_text_field', value: r.descriptionTag });
      if (!mf.length) throw new Error('nothing to write back');
      const d = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ message } } }`, { m: mf });
      if (d.metafieldsSet.userErrors.length) throw new Error(J(d.metafieldsSet.userErrors));
      return ADAPTERS['article-seo'].readLive(r);
    },
  },
  membership: {
    key: (r) => `${r.productHandle}@${r.collection}`,
    describe: (r) => J([...r.collectionsBefore].sort()),
    storedOf: () => null,
    readLive: async (r) => {
      const d = await gql(`query($id:ID!){ product(id:$id){ collections(first:100){ nodes{ handle } } } }`, { id: r.productId });
      if (!d.product) throw new Error('product not found');
      return J(d.product.collections.nodes.map((c) => c.handle).sort());
    },
    writeBack: async () => { throw new Error('membership restore is not wired: re-joining and leaving collections is a multi-mutation change and is left to a person, deliberately'); },
  },
};

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  eq('the seo-fields shape is recognised', pickShape({ id: 'gid://shopify/Collection/1', handle: 'x', seoTitle: 'a', seoDescription: 'b' }), 'seo-fields');
  eq('the article-seo shape is recognised', pickShape({ id: 'gid://shopify/Article/1', handle: 'x', blog: 'y', titleTag: 'a', descriptionTag: 'b' }), 'article-seo');
  eq('the membership shape is recognised', pickShape({ op: 'join', collection: 'c', productId: 'gid://shopify/Product/1', productHandle: 'p', collectionsBefore: [] }), 'membership');
  eq('a metafield/body backup is recognised', pickShape({ id: 'x', handle: 'h', md5: 'm', before: 'v' }), 'body-or-metafield');
  eq('an unknown shape is null, not a wrong guess', pickShape({ foo: 1 }), null);
  // shape, not filename: the same row is recognised whatever the file is called
  eq('recognition does not depend on the filename', pickShape({ id: 'gid://shopify/Product/1', handle: 'x', seoTitle: 'a', seoDescription: 'b' }), 'seo-fields');
  return bad;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const bad = selfTest();
  if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
  console.log('self-test: every fixture holds');
  if (process.argv.includes('--self-test')) process.exit(0);
}

/* ⚠️ THE CLI IS GATED. Importing this module used to RUN it: a proof script imported it to reuse an
   adapter, the usage exit killed that script AFTER it had staged a change and BEFORE it restored it,
   and a collection sat with a placeholder in both SEO fields. A module with a top-level process.exit
   kills its importer, and the failure is silent when it happens after a write. Exporting the adapters
   and gating the CLI means a proof can drive the REAL adapter instead of a copy — and a copy is where
   the ProductInput bug above hid. */
export { ADAPTERS };
const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) { await main(); }
async function main() {
const file = process.argv.slice(2).find((a) => a.endsWith('.json'));
if (!file) { console.log('usage: restore-from-backup.mjs <backup.json> [--only <key>] [--apply]'); process.exit(1); }
const rows = JSON.parse(fs.readFileSync(file, 'utf8'));
const list = Array.isArray(rows) ? rows : [rows];
const shape = pickShape(list[0]);
if (!shape) { console.log(`  REFUSE: unrecognised backup shape, keys ${J(Object.keys(list[0] || {}))}`); process.exit(1); }
if (shape === 'body-or-metafield') { console.log('  This shape is restored by the script that wrote it (it holds md5s and knows its own field). Use that script\'s --restore.'); process.exit(1); }
console.log(`  ${path.basename(file)}: ${list.length} row(s), shape "${shape}"${APPLY ? '' : '   DRY RUN'}\n`);
const r = await restoreRows(list, ADAPTERS[shape], { apply: APPLY, only: ONLY });
console.log(`\n  restored ${r.restored.length}  already ${r.already.length}  refused ${r.refused.length}  failed ${r.failed.length}  skipped ${r.skipped.length}`);
if (APPLY) for (const k of r.restored) logChange({ script: 'restore-from-backup', handle: k, field: shape, old: 'post-apply state', new: 'restored', note: `from ${file}` });
/* A REFUSAL MUST BE DETECTABLE BY EXIT CODE. This exited 0 while printing REFUSE, so a proof runner
   or a CI step would read a refused restore as success — the same shape as the piped `tee` that made a
   printed STOP go green. A refusal is three things: non-zero exit, the guard's own message, and live
   unchanged. Only "already restored" and a completed restore are exit 0. */
process.exit(r.failed.length || r.refused.length ? 1 : 0);
}
