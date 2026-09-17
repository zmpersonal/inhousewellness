/* B6b — build the two facet-fix lists to fixed files.
 *
 * Pass 1 MECHANICAL: a value differing from its sibling only by whitespace or an
 *   invisible character. No decision in any row; the target is the sibling.
 * Pass 2 CONVENTION: kW ratings in custom.capacity_ normalised to "N kW".
 *   Decided ONCE for the field. Majority-per-group is deliberately NOT used —
 *   it yields a field consistent within each group and inconsistent overall,
 *   which is worse than the split because it looks deliberate.
 *
 * Normalisation note: the first version of this collapsed whitespace to a single
 * space, which made "6 kW" and "6kW" different values and hid 11 of the 16 split
 * groups. The normaliser must remove the thing that varies, not tidy it.
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

const KW = /^(\d+(?:\.\d+)?)\s*kw$/i;
/* remove every space and zero-width, then lowercase: the axis that actually varies */
const norm = (v) => v.replace(/[\s​ ]/g, '').toLowerCase();

const mech = [], conv = [];

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
    /* Pass 2 owns every kW value, split or not — a convention applies to the whole field. */
    if (variants.some((v) => KW.test(v))) {
      for (const v of variants) {
        const m = v.match(KW);
        if (!m) continue;
        const target = `${m[1]} kW`;
        if (v === target) continue;
        for (const p of holders[v]) conv.push({ productId: p.id, handle: p.handle, title: p.title,
          status: p.status, key: KEYS[i], metafieldId: p[`m${i}`].id, from: v, to: target });
      }
      continue;
    }
    if (variants.length < 2) continue;
    const target = variants.slice().sort((a, b) => counts[b] - counts[a] || a.length - b.length)[0];
    for (const v of variants) {
      if (v === target) continue;
      for (const p of holders[v]) mech.push({ productId: p.id, handle: p.handle, title: p.title,
        status: p.status, key: KEYS[i], metafieldId: p[`m${i}`].id, from: v, to: target,
        reason: /[​]/.test(v) ? 'zero-width space' : v !== v.trim() ? 'stray space' : 'case' });
    }
  }
}

writeJSON(path.join(DATA, 'facet-fix-mechanical.json'), { built: new Date().toISOString(), rows: mech });
writeJSON(path.join(DATA, 'facet-fix-kw.json'), { built: new Date().toISOString(), convention: 'N kW', rows: conv });
console.log(`  pass 1 MECHANICAL : ${mech.length} writes across ${new Set(mech.map((r) => r.handle)).size} products`);
console.log(`  pass 2 kW         : ${conv.length} writes across ${new Set(conv.map((r) => r.handle)).size} products`);
