/* Round 18h — move a product to a target {status, policy, channels} in an order that is ALWAYS safe.
 *   node scripts/apply/r18h-sellout.mjs --handle <h> --channels "Online Store,Shop,..." [--apply]
 *   node scripts/apply/r18h-sellout.mjs --restore <backup.json> [--apply]
 *
 * The order, whichever direction the change runs:
 *   1. tighten policy (-> DENY)         never live while orderable-at-zero
 *   2. remove channels                  off the storefront before any status change
 *   3. status                           DRAFT/ACTIVE
 *   4. add channels                     only once the status is right
 *   5. loosen policy (-> CONTINUE)      last, and only ever on a restore to draft
 * After step 1 it asserts availableForSale is false before anything goes live.
 *
 * The backup's `after` is the state READ BACK, not the state requested: Meta and Copilot are
 * visible to this app but CLAUDE.md records an unpublish that silently did not take. A restore keyed
 * to a requested state that never landed would refuse forever.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const APPLY = process.argv.includes('--apply');
const RESTORE = arg('--restore');
const bk = RESTORE ? JSON.parse(fs.readFileSync(RESTORE, 'utf8')) : null;
const HANDLE = RESTORE ? bk.handle : arg('--handle');
const PUB = { 'Online Store': 'gid://shopify/Publication/141724155971', 'Point of Sale': 'gid://shopify/Publication/141724188739', 'Microsoft Copilot': 'gid://shopify/Publication/148560216131', 'Shop': 'gid://shopify/Publication/141724254275', 'Meta': 'gid://shopify/Publication/166471434307' };

async function read() {
  const p = (await gql(`query($h:String!){ productByHandle(handle:$h){ id status variants(first:20){ nodes{ id inventoryPolicy inventoryQuantity availableForSale inventoryItem{ tracked } } } resourcePublications(first:20){ nodes{ isPublished publication{ id name } } } } }`, { h: HANDLE })).productByHandle;
  const ch = p.resourcePublications.nodes.filter((n) => n.isPublished).map((n) => n.publication.name).filter((n) => PUB[n]).sort();
  return { p, fp: { status: p.status, policy: [...new Set(p.variants.nodes.map((v) => v.inventoryPolicy))].join(','), channels: ch } };
}
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const policy = async (p, pol) => { const r = await gql(`mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ message } } }`, { p: p.id, v: p.variants.nodes.map((v) => ({ id: v.id, inventoryPolicy: pol })) }); if (r.productVariantsBulkUpdate.userErrors.length) throw new Error(JSON.stringify(r.productVariantsBulkUpdate.userErrors)); };
const status = async (p, s) => { const r = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ message } } }`, { p: { id: p.id, status: s } }); if (r.productUpdate.userErrors.length) throw new Error(JSON.stringify(r.productUpdate.userErrors)); };
const pub = async (p, names, on) => { if (!names.length) return; const m = on ? 'publishablePublish' : 'publishableUnpublish'; const r = await gql(`mutation($id:ID!,$i:[PublicationInput!]!){ ${m}(id:$id, input:$i){ userErrors{ message } } }`, { id: p.id, i: names.map((n) => ({ publicationId: PUB[n] })) }); if (r[m].userErrors.length) throw new Error(JSON.stringify(r[m].userErrors)); };

async function go(target) {
  let { p, fp } = await read();
  if (target.policy === 'DENY' && fp.policy !== 'DENY') {
    await policy(p, 'DENY'); ({ p, fp } = await read());
    if (p.variants.nodes.some((v) => v.availableForSale)) throw new Error('still available for sale after DENY — stopping before anything goes live');
    console.log('   1 policy -> DENY; availableForSale false on every variant');
  }
  // On APPLY only the convention channels are managed: a channel the client HELD (Point of Sale) is
  // neither added nor removed, whatever it currently is. On RESTORE every channel is managed, so the
  // product returns to its before-state exactly — including anything Shopify added on activation.
  const managed = target.manageAll ? Object.keys(PUB) : target.channels;
  const drop = fp.channels.filter((c) => managed.includes(c) && !target.channels.includes(c));
  if (drop.length) { await pub(p, drop, false); console.log('   2 unpublished:', drop.join(', ')); }
  if (fp.status !== target.status) { await status(p, target.status); console.log('   3 status ->', target.status); }
  const add = target.channels.filter((c) => !fp.channels.includes(c));
  if (add.length) { await pub(p, add, true); console.log('   4 published:', add.join(', ')); }
  if (target.policy === 'CONTINUE' && fp.policy !== 'CONTINUE') { await policy(p, 'CONTINUE'); console.log('   5 policy -> CONTINUE (restore, product already off the storefront)'); }
  return read();
}

const now = await read();
console.log(`  ${HANDLE}\n  now    ${JSON.stringify(now.fp)} | qty ${now.p.variants.nodes.map((v) => v.inventoryQuantity).join(',')} | availableForSale ${now.p.variants.nodes.map((v) => v.availableForSale).join(',')}`);

if (RESTORE) {
  if (eq(now.fp, bk.before)) { console.log('  already restored'); process.exit(0); }
  if (!eq(now.fp, bk.after)) { console.log(`  REFUSE: live is neither the before-state nor what the apply left — changed since`); process.exit(1); }
  if (!APPLY) { console.log('  would restore to', JSON.stringify(bk.before)); process.exit(0); }
  const r = await go({ ...bk.before, manageAll: true });
  const ok = eq(r.fp, bk.before);
  console.log(`  ${ok ? 'RESTORED' : 'FAIL'} -> ${JSON.stringify(r.fp)}${ok ? ' == before-state' : ' != ' + JSON.stringify(bk.before)}`);
  logChange({ resource: r.p.id, handle: HANDLE, field: 'status/policy/channels', old: JSON.stringify(bk.after), new: JSON.stringify(r.fp), note: 'Round 18h restore' });
  process.exit(ok ? 0 : 1);
}
const channels = (arg('--channels') || '').split(',').map((s) => s.trim()).filter(Boolean).sort();
for (const c of channels) if (!PUB[c]) { console.log('  unknown channel', c); process.exit(1); }
const target = { status: 'ACTIVE', policy: 'DENY', channels };
if (!now.p.variants.nodes.every((v) => v.inventoryItem.tracked && v.inventoryQuantity <= 0)) { console.log('  REFUSING: the sold-out treatment needs tracked inventory at 0'); process.exit(1); }
if (now.fp.status === 'ACTIVE' && now.fp.policy === 'DENY' && channels.every((c) => now.fp.channels.includes(c))) { console.log('  already applied'); process.exit(0); }
console.log(`  target ${JSON.stringify(target)}  (Point of Sale HELD: not added, not removed)`);
if (!APPLY) { console.log('  DRY RUN — nothing written.'); process.exit(0); }
const bpath = backup('r18h-' + HANDLE, { handle: HANDLE, before: now.fp, requested: target, after: null });
const r = await go(target);
const b = JSON.parse(fs.readFileSync(bpath, 'utf8')); b.after = r.fp; fs.writeFileSync(bpath, JSON.stringify(b, null, 2));
const landed = r.fp.status === 'ACTIVE' && r.fp.policy === 'DENY' && target.channels.every((c) => r.fp.channels.includes(c)), sold = r.p.variants.nodes.every((v) => !v.availableForSale);
const missing = target.channels.filter((c) => !r.fp.channels.includes(c));
console.log(`  ${landed && sold ? 'APPLIED' : 'PARTIAL'} -> ${JSON.stringify(r.fp)} | availableForSale ${r.p.variants.nodes.map((v) => v.availableForSale).join(',')}${missing.length ? ' | DID NOT LAND: ' + missing.join(', ') : ''}`);
logChange({ resource: r.p.id, handle: HANDLE, field: 'status/policy/channels', old: JSON.stringify(now.fp), new: JSON.stringify(r.fp), note: `Round 18h; backup ${bpath}` });
console.log('  BACKUP', bpath);
process.exit(sold ? 0 : 1);
