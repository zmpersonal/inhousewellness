/* Round 18g — republish the Osla Edition as SOLD OUT (client: temporarily out of stock).
 *   node scripts/apply/r18g-osla.mjs                    dry run
 *   node scripts/apply/r18g-osla.mjs --apply            apply
 *   node scripts/apply/r18g-osla.mjs --restore <bkp>    restore (dry run unless --apply)
 *
 * ORDER IS THE SAFETY. The policy goes CONTINUE -> DENY *before* the product goes live, so there
 * is no moment at which it is both on the storefront and orderable. Restore runs the reverse:
 * off the storefront first, THEN the policy goes back. At qty 0 with CONTINUE, a live Osla would
 * accept orders for an $8,499 sauna the store cannot ship — the defect this script exists to avoid.
 *
 * No redirect: a redirect outlives the restock and silently diverts traffic from the product.
 * Online Store only — the channel that fixes the 404. Meta and Copilot are not addressable from
 * publications() (CLAUDE.md: the store-level list omits them), so they are reported, not touched.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const RESTORE = process.argv.includes('--restore') ? process.argv[process.argv.indexOf('--restore') + 1] : null;
const HANDLE = 'golden-6-person-sauna';

const pubs = (await gql(`query{ publications(first:20){ nodes{ id name } } }`)).publications.nodes;
const OS = pubs.find((p) => p.name === 'Online Store'); if (!OS) throw new Error('no Online Store publication');

async function state() {
  const p = (await gql(`query($h:String!){ productByHandle(handle:$h){ id status variants(first:10){ nodes{ id inventoryPolicy inventoryQuantity availableForSale inventoryItem{ tracked } } } resourcePublications(first:10){ nodes{ publication{ id } isPublished } } } }`, { h: HANDLE })).productByHandle;
  const os = p.resourcePublications.nodes.some((n) => n.publication.id === OS.id && n.isPublished);
  return { id: p.id, variants: p.variants.nodes, fp: { status: p.status, policy: p.variants.nodes.map((v) => v.inventoryPolicy).join(','), onlineStore: os } };
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const setPolicy = async (s, pol) => { const r = await gql(`mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ message } } }`, { p: s.id, v: s.variants.map((v) => ({ id: v.id, inventoryPolicy: pol })) }); if (r.productVariantsBulkUpdate.userErrors.length) throw new Error(JSON.stringify(r.productVariantsBulkUpdate.userErrors)); };
const setStatus = async (s, st) => { const r = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ message } } }`, { p: { id: s.id, status: st } }); if (r.productUpdate.userErrors.length) throw new Error(JSON.stringify(r.productUpdate.userErrors)); };
const publish = async (s, on) => { const m = on ? 'publishablePublish' : 'publishableUnpublish'; const r = await gql(`mutation($id:ID!,$i:[PublicationInput!]!){ ${m}(id:$id, input:$i){ userErrors{ message } } }`, { id: s.id, i: [{ publicationId: OS.id }] }); if (r[m].userErrors.length) throw new Error(JSON.stringify(r[m].userErrors)); };

const s0 = await state();
console.log('  now   :', JSON.stringify(s0.fp), '| qty', s0.variants.map((v) => v.inventoryQuantity).join(','), '| tracked', s0.variants.map((v) => v.inventoryItem.tracked).join(','), '| availableForSale', s0.variants.map((v) => v.availableForSale).join(','));

if (RESTORE) {
  const b = JSON.parse(fs.readFileSync(RESTORE, 'utf8'));
  if (same(s0.fp, b.before)) { console.log('  already restored'); process.exit(0); }
  if (!same(s0.fp, b.after)) { console.log(`  REFUSE: live ${JSON.stringify(s0.fp)} is neither the before-state nor what the apply set — changed since`); process.exit(1); }
  if (!APPLY) { console.log('  would restore to', JSON.stringify(b.before)); process.exit(0); }
  if (!b.before.onlineStore) await publish(s0, false);        // 1. off the storefront FIRST
  await setStatus(s0, b.before.status);                       // 2. back to draft
  await setPolicy(s0, b.before.policy.split(',')[0]);         // 3. only now the policy
  const s1 = await state();
  const ok = same(s1.fp, b.before);
  console.log(`  ${ok ? 'RESTORED' : 'FAIL'} -> ${JSON.stringify(s1.fp)} ${ok ? '== before-state' : '!= ' + JSON.stringify(b.before)}`);
  logChange({ resource: s0.id, handle: HANDLE, field: 'status/policy/publication', old: JSON.stringify(b.after), new: JSON.stringify(s1.fp), note: 'Round 18g restore' });
  process.exit(ok ? 0 : 1);
}

const target = { status: 'ACTIVE', policy: s0.variants.map(() => 'DENY').join(','), onlineStore: true };
const qtyOk = s0.variants.every((v) => v.inventoryQuantity <= 0 && v.inventoryItem.tracked);
if (!qtyOk) { console.log('  REFUSING: sold-out treatment needs tracked inventory at 0 — this is not that product state'); process.exit(1); }
if (same(s0.fp, target)) { console.log('  already applied'); process.exit(0); }
console.log('  target:', JSON.stringify(target));
if (!APPLY) { console.log('  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const bpath = backup('r18g-osla', { handle: HANDLE, id: s0.id, before: s0.fp, after: target });
await setPolicy(s0, 'DENY');                                   // 1. policy FIRST
let mid = await state();
if (mid.variants.some((v) => v.availableForSale)) { console.log('  ABORT: still available for sale after DENY — not publishing'); process.exit(1); }
await setStatus(s0, 'ACTIVE');                                 // 2. then active
await publish(s0, true);                                       // 3. then the storefront
const s1 = await state();
const ok = same(s1.fp, target) && s1.variants.every((v) => !v.availableForSale);
console.log(`  ${ok ? 'APPLIED' : 'FAIL'} -> ${JSON.stringify(s1.fp)} | availableForSale ${s1.variants.map((v) => v.availableForSale).join(',')}`);   /* fail-ok: process.exit(ok ? 0 : 1) three lines below */
logChange({ resource: s0.id, handle: HANDLE, field: 'status/policy/publication', old: JSON.stringify(s0.fp), new: JSON.stringify(s1.fp), note: `Round 18g — republished sold out; backup ${bpath}` });
console.log('  BACKUP', bpath);
process.exit(ok ? 0 : 1);
