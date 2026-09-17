/* B6b — the facet splits are on custom metafields, not productType.
 *
 * Nine values across four metafields differ from a sibling only by a trailing
 * space, a leading space, a case difference or a zero-width character. Each one
 * shows the customer a duplicate facet option.
 *
 * Builds the fix list to a fixed file. The TARGET is always the majority
 * spelling of the group, never a value invented here.
 */
import { gql } from '../lib/shopify.js';
import { writeJSON, DATA } from '../lib/util.js';
import path from 'node:path';

const KEYS = ['location_', 'wood', 'style', 'capacity_', 'width', 'height', 'depth'];
const sel = KEYS.map((k, i) => `m${i}: metafield(namespace:"custom", key:"${k}"){ id value }`).join('\n');

let after = null, all = [];
for (;;) {
  const r = await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
    nodes{ id handle title status ${sel} } } }`, { a: after });
  all.push(...r.products.nodes);
  if (!r.products.pageInfo.hasNextPage) break;
  after = r.products.pageInfo.endCursor;
}

/* Group values whose normalised form matches. ​ is the zero-width space,
 *   the non-breaking space — both invisible in the admin field. */
const norm = (v) => v.replace(/[\s​ ]+/g, ' ').trim().toLowerCase();
const rows = [];

for (let i = 0; i < KEYS.length; i++) {
  const counts = {}, holders = {};
  for (const p of all) {
    const mf = p[`m${i}`];
    if (!mf || !mf.value) continue;
    counts[mf.value] = (counts[mf.value] || 0) + 1;
    (holders[mf.value] = holders[mf.value] || []).push(p);
  }
  const groups = {};
  for (const v of Object.keys(counts)) (groups[norm(v)] = groups[norm(v)] || []).push(v);

  for (const [, variants] of Object.entries(groups)) {
    if (variants.length < 2) continue;
    /* The target is the most common spelling. Ties break to the shortest, which
     * is the one without the stray character. */
    const target = variants.slice().sort((a, b) => counts[b] - counts[a] || a.length - b.length)[0];
    for (const v of variants) {
      if (v === target) continue;
      for (const p of holders[v]) {
        rows.push({ productId: p.id, handle: p.handle, title: p.title, status: p.status,
                    key: KEYS[i], metafieldId: p[`m${i}`].id, from: v, to: target,
                    reason: v.length !== v.trim().length ? 'whitespace' :
                            /[​ ]/.test(v) ? 'invisible character' : 'case' });
      }
    }
  }
}

writeJSON(path.join(DATA, 'facet-splits.json'), { built: new Date().toISOString(), rows });
const esc = (s) => JSON.stringify(s).replace(/​/g, '\\u200b').replace(/ /g, '\\u00a0');
console.log(`  products scanned: ${all.length}`);
console.log(`  writes needed: ${rows.length}   across ${new Set(rows.map((r) => r.handle)).size} products\n`);
for (const r of rows) {
  console.log(`  custom.${r.key.padEnd(10)} ${esc(r.from).padEnd(14)} -> ${esc(r.to).padEnd(12)}  [${r.status.slice(0, 4)}] ${r.title.slice(0, 42)}`);
}
