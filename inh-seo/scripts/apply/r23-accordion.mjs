/* Round 23 — the Shipping Details accordion (custom.shipping_details, rich_text_field).
 *   node scripts/apply/r23-accordion.mjs [--group G1..G5] [--only <handle>] [--apply]
 *   node scripts/apply/r23-accordion.mjs --self-test
 *   node scripts/apply/r23-accordion.mjs --restore <backup.json> [--apply]
 *
 * SCOPE, client ruling 25 September 2026: INSTALLATION IS SAUNAS ONLY. The primary source —
 * the installation-assembly product a customer actually buys — says "your sauna" throughout and
 * names nothing else. So treatment is decided by productType, never by the metafield value:
 *
 *   A  productType Sauna, stale installation text   -> SPLICE to the corrected text
 *   B  productType Sauna, correct text + stale lead-in -> DELETE the lead-in item
 *   C  everything else                               -> REMOVE the installation offer and say so
 *
 * C's line is fuel-neutral on purpose. "Your licensed electrician" is FALSE on at least 24 of the
 * 72 non-units by fuel (20 wood-fired, 4 gas): a wood stove needs a flue and clearances, a gas
 * heater needs a gas fitter. The line borrows the installation page's own compliance reason,
 * which is true of electric, gas and wood alike, and names no trade we cannot know.
 *
 * Every product is gated on the EXACT md5 of its current value AND its productType, and the write
 * is refused unless the text OUTSIDE the edited region is byte-identical afterwards (instance 60:
 * a successful write to the wrong element reports clean).
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const ONLY = arg('--only');
const GROUP = arg('--group');
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const ND = '–';                                   // en dash, by code point — it is in "$50–$75"

const NO_INSTALL = 'We do not offer installation on this product. Any connection work it needs has to '
  + 'meet your local code and pass local inspection, so it should be arranged with a licensed trade in '
  + 'your own area rather than through us.';
const LINE = () => ({ type: 'paragraph', children: [{ type: 'text', value: NO_INSTALL }] });

const SOURCE = { handle: 'dynamic-saunas-monaco', md5: '7add8aaab4d143105e27e9b4af0f8b1b', span: [6, 10] };

/* correct = what a SAUNA gets.  noInstall = what everything else gets. */
const GROUPS = {
  G1: { md5: 'e19d24eec292e7a6aeec01edac51d0e5', n: 24, correct: { span: [6, 11] }, noInstall: { span: [9, 11] } },
  G2: { md5: 'd3e1a4169a9bc196cb2df20ca7509b0e', n: 16, correct: { span: [8, 13] }, noInstall: { span: [11, 13] } },
  G3: { md5: '0445afbbc776fbf74b08007b1aa3917c', n: 7,  correct: { span: [6, 10] }, noInstall: { span: [8, 10] } },
  G4: { md5: '6f10b11d401b8e77556c190f41de45cd', n: 31, correct: { span: [9, 11] }, noInstall: { dropItem: [10, 1] } },
  G5: { md5: '471938b2875cd518fa80cf936e5ae14a', n: 9,  correct: { deleteItem: [12, 1] }, noInstall: null },
};
const GONE_CORRECT = [`$50${ND}$75`, 'May involve electrical work', 'Electrical work may be required',
  'May include electrical work depending on the product', 'base fee at checkout covers delivery'];
const PRESENT_CORRECT = ['$1,800 flat, all in', 'There is no separate assembly labour bill afterwards'];
const GONE_NOINSTALL = ['Premium Installation', `$50${ND}$75`, 'Additional labor costs', 'Installation labor',
  'base fee at checkout covers delivery', '$1,800'];

/* ── pure transforms ──────────────────────────────────────────────────────────────────────────── */
const render = (n) => { if (n.type === 'text') return n.value || ''; const k = (n.children || []).map(render).join(''); return /paragraph|list-item|heading/.test(n.type) ? k + '\n' : k; };
export const text = (doc) => doc.children.map(render).join('');
export const urls = (doc) => { const o = []; const w = (n) => { if (n.type === 'link' && n.url) o.push(n.url); (n.children || []).forEach(w); }; doc.children.forEach(w); return o.sort(); };

export const spliceDoc = (doc, [s, e], rep) => ({ ...doc, children: [...doc.children.slice(0, s), ...rep, ...doc.children.slice(e)] });
export const deleteItem = (doc, [ni, ii]) => ({ ...doc, children: doc.children.map((n, i) => (i !== ni ? n : { ...n, children: n.children.filter((_, k) => k !== ii) })) });
/* drop a list ITEM and put the standalone line after the list it came from */
export const dropItemAddLine = (doc, [ni, ii], line) => {
  const list = doc.children[ni];
  return spliceDoc(doc, [ni, ni + 1], [{ ...list, children: list.children.filter((_, k) => k !== ii) }, line]);
};

/* the instance-60 guard: text OUTSIDE the edited region must be byte-identical */
export function outsideUnchanged(before, after, region) {
  if (region.deleteItem || region.dropItem) {
    const [ni, ii] = region.deleteItem || region.dropItem;
    const same = (a, b) => text({ children: a }) === text({ children: b });
    if (!same(before.children.slice(0, ni), after.children.slice(0, ni))) return false;
    const tailLen = before.children.length - ni - 1;
    if (!same(before.children.slice(ni + 1), after.children.slice(after.children.length - tailLen))) return false;
    // and inside the edited list: the surviving items must be EXACTLY before's items minus index ii
    const want = before.children[ni].children.filter((_, k) => k !== ii).map((n) => render(n));
    const got = (after.children[ni].children || []).map((n) => render(n));
    return JSON.stringify(want) === JSON.stringify(got);
  }
  const [s, e] = region.span;
  const pre = text({ children: before.children.slice(0, s) });
  const post = text({ children: before.children.slice(e) });
  const aPre = text({ children: after.children.slice(0, s) });
  const aPost = text({ children: after.children.slice(after.children.length - (before.children.length - e)) });
  return pre === aPre && post === aPost;
}

function selfTest() {
  let bad = 0;
  const eq = (name, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want)) { console.log(`FIXTURE FAIL: ${name} — want ${JSON.stringify(want)} got ${JSON.stringify(got)}`); bad++; } };
  const P = (t) => ({ type: 'paragraph', children: [{ type: 'text', value: t }] });
  const L = (...xs) => ({ type: 'list', children: xs.map((x) => ({ type: 'list-item', children: [{ type: 'text', value: x }] })) });
  const doc = { type: 'root', children: [P('keep-a'), P('OLD-1'), P('OLD-2'), P('keep-b')] };
  const reg = { span: [1, 3] };
  const after = spliceDoc(doc, reg.span, [P('NEW')]);
  eq('splice replaces exactly the span', text(after), 'keep-a\nNEW\nkeep-b\n');
  eq('outside text unchanged -> true', outsideUnchanged(doc, after, reg), true);
  eq('a splice at the WRONG anchor is caught', outsideUnchanged(doc, spliceDoc(doc, [0, 2], [P('NEW')]), reg), false);
  eq('a splice that grows the doc is still checked', outsideUnchanged(doc, spliceDoc(doc, reg.span, [P('N1'), P('N2')]), reg), true);
  const d2 = { type: 'root', children: [P('keep'), L('i0', 'i1')] };
  eq('deleteItem removes only that item', text(deleteItem(d2, [1, 1])), 'keep\ni0\n');
  eq('deleteItem outside check -> true', outsideUnchanged(d2, deleteItem(d2, [1, 1]), { deleteItem: [1, 1] }), true);
  eq('deleting the WRONG item is caught', outsideUnchanged(d2, deleteItem(d2, [1, 0]), { deleteItem: [1, 1] }), false);
  const d3 = { type: 'root', children: [P('keep'), L('white glove', 'premium install'), P('tail')] };
  const dropped = dropItemAddLine(d3, [1, 1], P('LINE'));
  eq('dropItemAddLine keeps item 0 and appends the line', text(dropped), 'keep\nwhite glove\nLINE\ntail\n');
  eq('dropItemAddLine leaves the rest alone', outsideUnchanged(d3, dropped, { dropItem: [1, 1] }), true);
  eq('dropping the WRONG item is caught', outsideUnchanged(d3, dropItemAddLine(d3, [1, 0], P('LINE')), { dropItem: [1, 1] }), false);
  eq('urls sorted', urls({ children: [{ type: 'link', url: '/b', children: [] }, { type: 'link', url: '/a', children: [] }] }), ['/a', '/b']);
  return bad;
}

const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

/* ── restore ──────────────────────────────────────────────────────────────────────────────────── */
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
    if (!ok) n++; else logChange({ resource: s.id, handle: s.handle, field: 'metafield custom.shipping_details', old: 'Round 23 edit', new: 'restored', note: `restore from ${RESTORE}` });
  }
  process.exit(n ? 1 : 0);
}

/* ── plan ─────────────────────────────────────────────────────────────────────────────────────── */
const src = (await gql(`query($h:String!){ productByHandle(handle:$h){ metafield(namespace:"custom", key:"shipping_details"){ value } } }`, { h: SOURCE.handle })).productByHandle.metafield.value;
if (md5(src) !== SOURCE.md5) { console.log(`REFUSING: replacement source ${SOURCE.handle} is ${md5(src)}, expected ${SOURCE.md5}`); process.exit(1); }
const REPLACEMENT = JSON.parse(src).children.slice(...SOURCE.span);
console.log(`replacement: ${REPLACEMENT.length} nodes from ${SOURCE.handle} (md5 verified)\n`);

let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ id handle status productType metafield(namespace:"custom", key:"shipping_details"){ value } } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);

const plan = []; let fail = 0;
for (const [gid, g] of Object.entries(GROUPS)) {
  if (GROUP && gid !== GROUP) continue;
  const members = all.filter((p) => p.status === 'ACTIVE' && p.metafield && md5(p.metafield.value) === g.md5);
  if (members.length !== g.n) console.log(`   NOTE ${gid}: ${members.length} carry this value, expected ${g.n}`);
  for (const p of members) {
    if (ONLY && p.handle !== ONLY) continue;
    const sauna = p.productType === 'Sauna';
    const region = sauna ? g.correct : g.noInstall;
    if (!region) { console.log(`   FAIL ${gid} ${p.handle}: productType "${p.productType}" has no treatment for this value`); fail++; continue; }
    const kind = sauna ? (region.deleteItem ? 'B' : 'A') : 'C';
    const before = JSON.parse(p.metafield.value);
    let after = kind === 'B' ? deleteItem(before, region.deleteItem)
      : kind === 'A' ? spliceDoc(before, region.span, REPLACEMENT)
      : region.dropItem ? dropItemAddLine(before, region.dropItem, LINE())
      : spliceDoc(before, region.span, [LINE()]);
    if (process.argv.includes('--inject-stray')) after = { ...after, children: [...after.children, { type: 'paragraph', children: [{ type: 'text', value: 'INJECTED' }] }] };
    if (process.argv.includes('--inject-link')) {
      const kids = [...after.children];
      kids[0] = { ...kids[0], children: [...kids[0].children, { type: 'link', url: 'https://example.com/x', children: [{ type: 'text', value: '' }] }] };
      after = { ...after, children: kids };
    }
    const t = text(after); const bad2 = [];
    if (!outsideUnchanged(before, after, region)) bad2.push('TEXT OUTSIDE THE EDITED REGION CHANGED');
    if (JSON.stringify(urls(before)) !== JSON.stringify(urls(after))) bad2.push('LINK SET CHANGED');
    if (kind === 'C') {
      for (const s of GONE_NOINSTALL) if (t.includes(s)) bad2.push(`GONE: "${s}" still present`);
      const n = t.split(NO_INSTALL).length - 1; if (n !== 1) bad2.push(`the no-installation line appears ${n}x, want 1`);
      if (!/White Glove/.test(t)) bad2.push('White Glove was removed — it is delivery, not installation, and must survive');
    } else {
      for (const s of GONE_CORRECT) if (t.includes(s)) bad2.push(`GONE: "${s}" still present`);
      for (const s of PRESENT_CORRECT) { const n = t.split(s).length - 1; if (n !== 1) bad2.push(`PRESENT: "${s.slice(0, 28)}…" appears ${n}x, want 1`); }
      if (t.includes(NO_INSTALL)) bad2.push('a sauna received the no-installation line');
    }
    if (bad2.length) { fail++; console.log(`   FAIL ${gid}/${kind} ${p.handle} [${p.productType}]`); bad2.forEach((x) => console.log(`        ${x}`)); continue; }
    plan.push({ gid, kind, id: p.id, handle: p.handle, productType: p.productType, before: p.metafield.value, after: JSON.stringify(after) });
  }
}
const tally = {}; plan.forEach((x) => { const k = `${x.kind} (${x.gid})`; tally[k] = (tally[k] || 0) + 1; });
console.log(`planned: ${plan.length} products`);
Object.entries(tally).sort().forEach(([k, v]) => console.log(`    ${String(v).padStart(3)}  ${k}`));
if (fail) { console.log(`\n  FAILED ${fail} — REFUSING, nothing written`); process.exit(1); }
if (!plan.length) { console.log('  nothing to do'); process.exit(0); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = plan.map((p) => ({ gid: p.gid, kind: p.kind, id: p.id, handle: p.handle, productType: p.productType, md5: md5(p.before), afterMd5: md5(p.after), before: p.before }));
const bpath = backup('r23-accordion' + (ONLY ? '-' + ONLY : GROUP ? '-' + GROUP : ''), snap);
for (const p of plan) {
  const stored = await writeMf(p.id, p.after);
  const s = snap.find((x) => x.handle === p.handle); s.storedMd5 = md5(stored);
  logChange({ script: 'r23-accordion', resource: p.id, handle: p.handle, field: 'metafield custom.shipping_details', old: `${p.gid} before-state`, new: `treatment ${p.kind}`, note: `backup ${bpath}` });
  console.log(`  wrote ${p.handle.padEnd(46)} ${p.gid}/${p.kind}  stored ${s.storedMd5 === s.afterMd5 ? '= sent' : 'NORMALISED'}`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
