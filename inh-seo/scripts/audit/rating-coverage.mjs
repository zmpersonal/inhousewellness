/* Item 1 step 2 — where does the review data live server-side, and on how many products?
 * Counts are OCCURRENCES over the enumerated connection; the unit is named in every line. */
import { gql } from '../lib/shopify.js';
import fs from 'node:fs';
let after = null, prods = [];
do {
  const q = await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
    nodes{ handle status
      r: metafield(namespace:"reviews", key:"rating"){ value }
      c: metafield(namespace:"reviews", key:"rating_count"){ value }
      jb: metafield(namespace:"judgeme", key:"badge"){ value }
    } } }`, { a: after });
  prods.push(...q.products.nodes);
  after = q.products.pageInfo.hasNextPage ? q.products.pageInfo.endCursor : null;
} while (after);

const num = (v) => { if (v == null) return null; try { const j = JSON.parse(v); return parseFloat(j.value ?? j); } catch { return parseFloat(v); } };
let usable = 0, zero = 0, missing = 0, badgeOnly = 0, active = 0, activeUsable = 0;
const rows = [];
for (const p of prods) {
  const rating = num(p.r?.value), count = p.c?.value != null ? parseInt(p.c.value, 10) : null;
  const ok = rating != null && !Number.isNaN(rating) && count != null && count > 0;
  if (p.status === 'ACTIVE') active++;
  if (ok) { usable++; if (p.status === 'ACTIVE') activeUsable++; }
  else if (count === 0) zero++;
  else { missing++; if (p.jb?.value) badgeOnly++; }
  rows.push({ handle: p.handle, status: p.status, rating, count, ok });
}
fs.writeFileSync('data/rating-coverage.json', JSON.stringify(rows, null, 1));
console.log(`products enumerated (occurrences): ${prods.length}   ACTIVE: ${active}`);
console.log(`\nSERVER-SIDE SOURCE: metafields reviews.rating + reviews.rating_count`);
console.log(`  usable (rating present AND count > 0): ${usable}   of which ACTIVE: ${activeUsable}`);
console.log(`  count === 0 (must NEVER emit a rating): ${zero}`);
console.log(`  no usable metafield at all:             ${missing}   (of these, ${badgeOnly} carry a judgeme.badge metafield)`);
const dist = {};
for (const r of rows.filter((x) => x.ok)) { const b = r.count >= 50 ? '50+' : r.count >= 10 ? '10-49' : r.count >= 5 ? '5-9' : '1-4'; dist[b] = (dist[b] || 0) + 1; }
console.log(`  review-count distribution among the usable: ${JSON.stringify(dist)}`);
const tot = rows.filter((x) => x.ok).reduce((s, r) => s + r.count, 0);
const wavg = rows.filter((x) => x.ok).reduce((s, r) => s + r.rating * r.count, 0) / (tot || 1);
console.log(`\n  SHOP-LEVEL from product metafields: ${tot} reviews, weighted mean ${wavg.toFixed(2)}`);
console.log(`  (the prompt states 4.82 from 1,431 — compare before hardcoding anything)`);
