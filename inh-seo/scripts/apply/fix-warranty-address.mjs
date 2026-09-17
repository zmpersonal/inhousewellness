/* Client ruling 16 Sep 2026: the warranty CLAIMS address is
 *   2028 E Ben White BLVD #240-6184 Austin, TX 78741
 * — Ben White, not Balcones. It is a claims address, not website copy, so the
 * "Balcones #20752 everywhere" ruling does not reach it. The stored value carried
 * #240-618**0**; billing says 240 618**4**. The client settled which is the typo.
 *
 *   node scripts/apply/fix-warranty-address.mjs [--apply]
 *
 * Digit only. Street, punctuation and every other word stay as written, so the
 * rendered address matches the client's string without restyling his page.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'extended-your-warranty-3-years';
const FROM = '#240-6180';
const TO = '#240-6184';

const q = await gql(`query($q:String!){ products(first:3, query:$q){ nodes{ id handle status descriptionHtml resourcePublications(first:10){ nodes{ isPublished publication{ name } } } } } }`, { q: `handle:${HANDLE}` });
const p = q.products.nodes.find((x) => x.handle === HANDLE);
if (!p) throw new Error('product not found');
const n = p.descriptionHtml.split(FROM).length - 1;
console.log(`  ${HANDLE}  status=${p.status}`);
console.log(`  channels: ${p.resourcePublications.nodes.map((x) => `${x.publication.name}=${x.isPublished}`).join(' ')}`);
console.log(`  matches for ${FROM}: ${n}`);
if (n !== 1) { console.log('  FAILURE: expected exactly 1 match'); process.exit(1); }

const after = p.descriptionHtml.split(FROM).join(TO);
const i = p.descriptionHtml.indexOf(FROM);
console.log(`  - ${p.descriptionHtml.slice(i - 46, i + 40).replace(/<[^>]+>/g, '')}`);
console.log(`  + ${after.slice(i - 46, i + 40).replace(/<[^>]+>/g, '')}`);
if (after.length - p.descriptionHtml.length !== 0) { console.log('  FAILURE: length moved; this edit is one digit'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('warranty-address', [{ id: p.id, handle: HANDLE, before: p.descriptionHtml }]);
const m = await gql(`mutation($id:ID!,$html:String!){ productUpdate(product:{ id:$id, descriptionHtml:$html }){ product{ id } userErrors{ field message } } }`,
  { id: p.id, html: after });
if (m.productUpdate.userErrors.length) { console.log('  ERR', m.productUpdate.userErrors); process.exit(1); }
logChange({ resource: p.id, handle: HANDLE, field: 'descriptionHtml', old: FROM, new: TO, note: 'Round 14 — warranty claims address, client ruling 16 Sep 2026' });

/* Outcome, not the write report. */
const back = await gql(`query($q:String!){ products(first:3, query:$q){ nodes{ handle descriptionHtml } } }`, { q: `handle:${HANDLE}` });
const b = back.products.nodes.find((x) => x.handle === HANDLE).descriptionHtml;
console.log(`\n  re-read: ${TO} ×${b.split(TO).length - 1}, ${FROM} ×${b.split(FROM).length - 1}, Balcones ×${b.split('Balcones').length - 1}`);
if (b.includes(FROM) || !b.includes(TO)) process.exitCode = 1;
