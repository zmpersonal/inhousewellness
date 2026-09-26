/* Round 23c — the 30 "vague coverage" accordions (custom.shipping_details).
 *   node scripts/apply/r23c-vague.mjs [--group V1|V2|V3|V4] [--only <handle>] [--apply]
 *   node scripts/apply/r23c-vague.mjs --self-test
 *   node scripts/apply/r23c-vague.mjs --restore <backup.json> [--apply]
 *
 * "subject to availability in your area" promises coverage nothing establishes. It sits INSIDE the
 * same list item as the Premium Installation offer, so on a component the installation removal takes
 * it along and one rewrite does both. On a sauna the offer stays and the item is rewritten.
 *
 *   C  everything not productType Sauma... not Sauna  -> White Glove kept, installation removed, ZIP ask
 *   D  productType Sauna                              -> both services kept, coverage claim -> ZIP ask
 *
 * D is NOT wired to a live value yet: V3's three saunas ship together with the FAQ answer, because two
 * sources disagreeing about installation is the defect being fixed. --group V3 refuses.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const ONLY = arg('--only'); const GROUP = arg('--group');
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');

const NO_INSTALL = 'We do not offer installation on this product. Any connection work it needs has to '
  + 'meet your local code and pass local inspection, so it should be arranged with a licensed trade in '
  + 'your own area rather than through us.';
const ZIP = 'Send us your ZIP code before you buy and we will confirm it at your address.';
/* White Glove's own wording is PRESERVED, not rewritten. Its product page is sauna-scoped too — 127
   non-saunas offer it — and that is an open ruling, so this pass introduces no new claim about it. */
const C_LONG = `Optional Upgrades: White Glove Service (inside placement) may be available for an additional fee at checkout. ${ZIP} It can add 2 to 5 business days for scheduling and coordination. ${NO_INSTALL}`;
const C_SHORT = `White Glove Delivery may be available for an additional fee. ${ZIP} ${NO_INSTALL}`;

const D_SAUNA = 'Optional Upgrades: White Glove Service (inside placement) and Premium Installation & Assembly '
  + '\u2014 $1,800 flat, all in, with no separate assembly labour bill afterwards. Electrical work is billed by '
  + 'your own licensed electrician, not by InHouse Wellness. ' + 'Send us your ZIP code before you buy and we will '
  + 'confirm both services at your address. Scheduling adds 2 to 5 business days for White Glove, 3 to 10 for '
  + 'installation.';

const D_ZIP = 'Send us your ZIP code before you buy and we will confirm both services at your address.';

const C_GONE = ['subject to availability in your area', 'Premium Installation', 'Installation Services'];
const D_GONE = ['subject to availability in your area'];   // a SAUNA keeps the offer, so this is the only removal

/* CONSUMED, 2026-09-26: V1/V2/V4 were applied and their before-md5s no longer exist, so their guards
   cannot be shown to fail against the estate as it is now. Left in place as the record of what ran. */
const GROUPS = {
  V1: { md5: '960fde3d511c6c9f1cb0f4267b766883', n: 15, item: [8, 1], to: C_LONG,  gone: C_GONE, present: [NO_INSTALL, ZIP], consumed: '2026-09-26' },
  V2: { md5: '8a331df67f298a8105a5b47782a29145', n: 11, item: [8, 1], to: C_LONG,  gone: C_GONE, present: [NO_INSTALL, ZIP], consumed: '2026-09-26' },
  V4: { md5: 'e364aa6229ab13183e4e7860ea9c041c', n: 1,  item: [4, 1], to: C_SHORT, gone: C_GONE, present: [NO_INSTALL, ZIP], consumed: '2026-09-26' },
  V3: { md5: '3b3700ccbe34d51dda3cf9c04ef76568', n: 3,  item: [8, 1], to: D_SAUNA, gone: D_GONE, present: ['$1,800 flat, all in', D_ZIP], sauna: true, consumed: '2026-09-26' },
  /* V5: the em dash in V3's own string breaks the voice guide. Same three saunas, one clause changed. */
  V5: { md5: 'e8046674c845936b088da69c396ea1b7', n: 3,  item: [8, 1], to: D_SAUNA.replace(' \u2014 $1,800 flat, all in,', '. It is $1,800 flat, all in,'), gone: [...D_GONE, '\u2014'], present: ['$1,800 flat, all in', D_ZIP], sauna: true },
};

const render = (n) => { if (n.type === 'text') return n.value || ''; const k = (n.children || []).map(render).join(''); return /paragraph|list-item|heading/.test(n.type) ? k + '\n' : k; };
export const text = (doc) => doc.children.map(render).join('');
export const urls = (doc) => { const o = []; const w = (n) => { if (n.type === 'link' && n.url) o.push(n.url); (n.children || []).forEach(w); }; doc.children.forEach(w); return o.sort(); };
/* replace ONE list item's text, leaving its siblings and every other node alone */
export const replaceItem = (doc, [ni, ii], value) => ({ ...doc, children: doc.children.map((n, i) => (i !== ni ? n
  : { ...n, children: n.children.map((it, k) => (k !== ii ? it : { ...it, children: [{ type: 'text', value }] })) })) });
/* the instance-60 guard, for an item replacement: everything but that one item is byte-identical */
export function onlyThatItem(before, after, [ni, ii], value) {
  if (after.children.length !== before.children.length) return false;
  for (let i = 0; i < before.children.length; i++) {
    if (i === ni) continue;
    if (render(before.children[i]) !== render(after.children[i])) return false;
  }
  const b = before.children[ni].children, a = after.children[ni].children;
  if (a.length !== b.length) return false;
  for (let k = 0; k < b.length; k++) {
    if (k === ii) { if (render(a[k]).trim() !== value.trim()) return false; }
    else if (render(b[k]) !== render(a[k])) return false;
  }
  return true;
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  const P = (t) => ({ type: 'paragraph', children: [{ type: 'text', value: t }] });
  const L = (...xs) => ({ type: 'list', children: xs.map((x) => ({ type: 'list-item', children: [{ type: 'text', value: x }] })) });
  const doc = { type: 'root', children: [P('keep'), L('i0', 'OLD', 'i2'), P('tail')] };
  const after = replaceItem(doc, [1, 1], 'NEW');
  eq('replaces exactly that item', text(after), 'keep\ni0\nNEW\ni2\ntail\n');
  eq('the guard accepts it', onlyThatItem(doc, after, [1, 1], 'NEW'), true);
  eq('replacing the WRONG item is caught', onlyThatItem(doc, replaceItem(doc, [1, 0], 'NEW'), [1, 1], 'NEW'), false);
  eq('replacing in the WRONG node is caught', onlyThatItem(doc, replaceItem({ ...doc, children: [P('keep'), L('i0','OLD','i2'), L('x')] }, [2, 0], 'NEW'), [1, 1], 'NEW'), false);
  eq('a different value than declared is caught', onlyThatItem(doc, replaceItem(doc, [1, 1], 'OTHER'), [1, 1], 'NEW'), false);
  eq('an extra node appended is caught', onlyThatItem(doc, { ...after, children: [...after.children, P('X')] }, [1, 1], 'NEW'), false);
  eq('a dropped sibling item is caught', onlyThatItem(doc, { ...after, children: after.children.map((n,i)=> i!==1?n:{...n, children:n.children.slice(0,2)}) }, [1, 1], 'NEW'), false);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

const readMf = async (id) => (await gql(`query($id:ID!){ product(id:$id){ metafield(namespace:"custom", key:"shipping_details"){ value } } }`, { id })).product.metafield.value;
const writeMf = async (id, value) => {
  const r = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ value } userErrors{ message } } }`,
    { m: [{ ownerId: id, namespace: 'custom', key: 'shipping_details', type: 'rich_text_field', value }] });
  if (r.metafieldsSet.userErrors.length) throw new Error(JSON.stringify(r.metafieldsSet.userErrors));
  return r.metafieldsSet.metafields[0].value;
};
const RESTORE = arg('--restore');
if (RESTORE) {
  const snap = JSON.parse(fs.readFileSync(RESTORE, 'utf8')).filter((s) => !ONLY || s.handle === ONLY);
  let n = 0;
  for (const s of snap) {
    const live = md5(await readMf(s.id));
    if (live === s.md5) { console.log(`  already restored  ${s.handle}`); continue; }
    if (live !== (s.storedMd5 || s.afterMd5)) { console.log(`  REFUSE ${s.handle}: live ${live} is neither the before-state nor what the apply stored — edited since`); n++; continue; }
    if (!APPLY) { console.log(`  would restore     ${s.handle}`); continue; }
    const back = md5(await writeMf(s.id, s.before));
    const ok = back === s.md5;
    console.log(`  ${ok ? 'RESTORED' : 'FAIL    '} ${s.handle}  read-back ${back}${ok ? ' == before-state' : ' != ' + s.md5}`);
    if (!ok) n++; else logChange({ resource: s.id, handle: s.handle, field: 'metafield custom.shipping_details', old: 'Round 23c edit', new: 'restored', note: `restore from ${RESTORE}` });
  }
  process.exit(n ? 1 : 0);
}

let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ id handle status productType metafield(namespace:"custom", key:"shipping_details"){ value } } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);

const plan = []; let fail = 0;
for (const [gid, g] of Object.entries(GROUPS)) {
  if (GROUP && gid !== GROUP) continue;
  if (g.consumed && GROUP !== gid) { console.log(`   SKIP  ${gid}: consumed ${g.consumed} — its before-state no longer exists. Name it with --group to attempt anyway.`); continue; }
  const members = all.filter((p) => p.status === 'ACTIVE' && p.metafield && md5(p.metafield.value) === g.md5);
  if (members.length !== g.n) console.log(`   NOTE ${gid}: ${members.length} carry this value, expected ${g.n}`);
  for (const p of members) {
    if (ONLY && p.handle !== ONLY) continue;
    if (g.sauna && p.productType !== 'Sauna') { console.log(`   FAIL ${gid} ${p.handle}: this spec is for a Sauna, and its productType is "${p.productType}"`); fail++; continue; }
    if (!g.sauna && p.productType === 'Sauna') { console.log(`   FAIL ${gid} ${p.handle}: a Sauna must keep the installation offer`); fail++; continue; }
    const before = JSON.parse(p.metafield.value);
    let after = replaceItem(before, g.item, g.to);
    if (process.argv.includes('--inject-stray')) after = { ...after, children: [...after.children, { type: 'paragraph', children: [{ type: 'text', value: 'INJECTED' }] }] };
    if (process.argv.includes('--inject-link')) {
      /* the EMPTY anchor goes INSIDE the replaced item. Anywhere else and onlyThatItem also catches it,
         so the link guard would never be tested on its own. One test per proof. */
      const [ni, ii] = g.item; const k = [...after.children];
      k[ni] = { ...k[ni], children: k[ni].children.map((it, j) => (j !== ii ? it
        : { ...it, children: [...it.children, { type: 'link', url: 'https://example.com/x', children: [{ type: 'text', value: '' }] }] })) };
      after = { ...after, children: k };
    }
    const t = text(after); const probs = [];
    if (!onlyThatItem(before, after, g.item, g.to)) probs.push('SOMETHING OTHER THAN THAT ONE LIST ITEM CHANGED');
    if (JSON.stringify(urls(before)) !== JSON.stringify(urls(after))) probs.push('LINK SET CHANGED');
    for (const s of g.gone) if (t.includes(s)) probs.push(`GONE: "${s}" still present`);
    for (const s of g.present) { const n = t.split(s).length - 1; if (n !== 1) probs.push(`"${s.slice(0, 30)}…" appears ${n}x, want 1`); }
    if (!/White Glove/.test(t)) probs.push('White Glove was removed — that is a separate open ruling, not this pass');
    if (g.sauna && !/Premium Installation/.test(t)) probs.push('a Sauna lost the installation offer');
    if (probs.length) { fail++; console.log(`   FAIL ${gid} ${p.handle} [${p.productType}]`); probs.forEach((x) => console.log(`        ${x}`)); continue; }
    plan.push({ gid, id: p.id, handle: p.handle, productType: p.productType, before: p.metafield.value, after: JSON.stringify(after) });
  }
}
const tally = {}; plan.forEach((x) => { tally[x.gid] = (tally[x.gid] || 0) + 1; });
console.log(`planned: ${plan.length} products  ${JSON.stringify(tally)}`);
if (fail) { console.log(`\n  FAILED ${fail} — REFUSING, nothing written`); process.exit(1); }
if (!plan.length) { console.log('  nothing to do'); process.exit(0); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = plan.map((p) => ({ gid: p.gid, id: p.id, handle: p.handle, productType: p.productType, md5: md5(p.before), afterMd5: md5(p.after), before: p.before }));
const bpath = backup('r23c-vague' + (ONLY ? '-' + ONLY : GROUP ? '-' + GROUP : ''), snap);
for (const p of plan) {
  const stored = await writeMf(p.id, p.after);
  const s = snap.find((x) => x.handle === p.handle); s.storedMd5 = md5(stored);
  logChange({ script: 'r23c-vague', resource: p.id, handle: p.handle, field: 'metafield custom.shipping_details', old: `${p.gid} before-state`, new: 'coverage claim -> ZIP ask; installation removed', note: `backup ${bpath}` });
  console.log(`  wrote ${p.handle.padEnd(46)} ${p.gid}  stored ${s.storedMd5 === s.afterMd5 ? '= sent' : 'NORMALISED'}`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
