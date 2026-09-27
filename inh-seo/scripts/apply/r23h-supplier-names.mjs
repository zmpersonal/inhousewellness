/* Round 23h — remove every supplier name from the shipping panels, and settle three riders.
 *   node scripts/apply/r23h-supplier-names.mjs --report        every value, before and after
 *   node scripts/apply/r23h-supplier-names.mjs [--only <handle>] [--apply]
 *   node scripts/apply/r23h-supplier-names.mjs --self-test | --restore <backup.json> [--apply]
 *
 * Client ruling 2026-09-27: supplier identity is not a customer-facing fact, and naming one commits us
 * to fulfilling through them. No supplier name survives — not Bathing Brands, not Dundalk.
 *
 * Scope was 43 by my own count and is 117. The 43 counted panels naming a RIVAL VENDOR; the question
 * is panels naming ANY SUPPLIER, and "Bathing Brands" is not a vendor string in this catalogue, so a
 * vendor-based sweep could not see it. 117 products, 12 distinct values, 9 vendors.
 *
 * Rules are ORDERED and most-specific-first: the general terms are substrings of the specific ones
 * ("Dundalk" inside "Dundalk Leisurecraft"), so ordering decides the answer and nothing raises an error.
 */
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const ONLY = arg('--only');
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const EN = '–';

const DAMAGE = 'For items that arrive damaged, contact us before returning anything. Damaged and '
  + 'defective items are handled as exchanges under our refund policy.';
const SUPPORT = 'support@inhousewellness.com';

/* [pattern, replacement, why]. Most specific FIRST. */
export const RULES = [
  // --- the return-shipping promise: three wordings, one replacement (client ruling: narrow, not remove)
  [/If the return is due to shipping damage or a distributor error, Bathing Brands covers return shipping[^.]*\./gi, DAMAGE, 'return promise -> damage/exchange route'],
  [/If due to damage or distributor error:?\s*Bathing Brands covers the return shipping cost\.?/gi, DAMAGE, 'return promise -> damage/exchange route'],
  [/If due to damage or distributor error:?\s*Bathing Brands covers return shipping\.?/gi, DAMAGE, 'return promise -> damage/exchange route'],
  // --- the contact route
  [/(?:Or\s+)?(?:contact|email)\s+Bathing Brands\s+directly\s+at\s+CustomerService@BathingBrands\.com/gi, `Or email us at ${SUPPORT}`, 'supplier contact -> ours'],
  [/CustomerService@BathingBrands\.com/gi, SUPPORT, 'any remaining supplier address'],
  // --- the intro, naming a distributor
  /* bounded on the delimiter, not a lazy quantifier: `[\w .'-]*?` matched a single letter and left the
     rest of the brand name stranded in the sentence. The capture was never used, so it is gone. */
  [/we partner (?:directly )?with Bathing Brands,? the official distributor of [^,.]+,?/gi, "we work directly with the manufacturer's distributor,", 'intro -> route-neutral'],
  [/the manufacturer's distributor, the official distributor of [^,.]+,?/gi, "the manufacturer's distributor,", 'strip a doubled distributor clause'],
  [/we work directly with the exclusive distributor of [^,.]+,?/gi, "we work directly with the manufacturer's distributor,", '"exclusive" implies a fixed route'],
  [/we coordinate directly with Dundalk Leisurecraft/gi, "we coordinate directly with the manufacturer's distributor", 'intro -> route-neutral'],
  // --- the warehouse and the claim route
  [/shipped directly from Dundalk(?:'|’)s warehouse/gi, "shipped directly from the distributor's warehouse", 'warehouse -> route-neutral'],
  [/filing a claim with Dundalk Leisurecraft/gi, 'filing a claim with the manufacturer', 'claim route -> the manufacturer'],
  [/Bathing Brands error/gi, 'a distributor error', 'cost attribution -> route-neutral'],
  // a supplier name in SUBJECT position is not a distributor reference: "Dundalk Leisurecraft orders
  // are made to order" became "the manufacturer's distributor orders are made to order".
  [/\b(?:Dundalk Leisurecraft|Bathing Brands)\s+orders\b/gi, 'Orders for this product', 'supplier in subject position'],
  [/For shipping damage or (?:Bathing Brands|a distributor) error,? return shipping is covered\.?/gi, DAMAGE, 'Finnmark wording of the return promise'],
  [/Email CustomerService@BathingBrands\.com/gi, `Email ${SUPPORT}`, 'RA request address'],
  [/\bBathing Brands\b/g, "the manufacturer's distributor", 'any remaining supplier mention'],
  [/\bDundalk Leisurecraft\b/g, "the manufacturer's distributor", 'any remaining supplier mention'],
  [/\bDundalk\b/g, 'the distributor', 'any remaining supplier mention'],
  // --- lead times keep their figures and gain "typically" (client ruling: route varies per order)
  [/Processing Time:\s*Most ([\w .'-]+?) (?:products|saunas) ship within (\d+[-–]\d+ business days)/gi,
    (m, brand, days) => `Processing Time: ${brand} products typically ship within ${days}`, 'usual-case, not a commitment'],
  [/Standard Products:\s*Typically delivered within/gi, 'Standard Products: Typically delivered within', 'already says typically'],
  [/(Orders|Most [\w .'-]+ orders) (?:are )?(?:delivered|arrive) within (?!up to)/gi, '$1 typically arrive within ', 'usual-case, not a commitment'],
  // --- Group B rides along: generic sauna nouns on non-saunas. Every SaunaLife instance is preserved.
  [/to ensure your sauna is delivered/gi, 'to ensure the item is delivered', 'Group B noun'],
  [/depending on the sauna model and size/gi, 'depending on the model and size', 'Group B noun'],
];

export function rewrite(text) {
  let out = text; const applied = [];
  for (const [re, rep, why] of RULES) {
    const before = out;
    out = out.replace(re, rep);
    if (out !== before) applied.push(why);
  }
  return { out, applied };
}
export const suppliersLeft = (s) => ['Bathing Brands', 'BathingBrands', 'Dundalk'].filter((n) => new RegExp(n, 'i').test(s));

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  eq('the intro loses the supplier and the brand', rewrite('we partner directly with Bathing Brands, the official distributor of SaunaLife, to ensure').out,
    "we work directly with the manufacturer's distributor, to ensure");
  eq('"exclusive distributor" becomes route-neutral', rewrite('we work directly with the exclusive distributor of Finnmark Designs, to ensure').out,
    "we work directly with the manufacturer's distributor, to ensure");
  eq('the claim route names the manufacturer', rewrite('assist you with filing a claim with Dundalk Leisurecraft.').out, 'assist you with filing a claim with the manufacturer.');
  eq('the warehouse is neutral', rewrite("shipped directly from Dundalk's warehouse.").out, "shipped directly from the distributor's warehouse.");
  eq('the return promise narrows', rewrite('If due to damage or distributor error: Bathing Brands covers the return shipping cost').out, DAMAGE);
  eq('the supplier address becomes ours', rewrite('Or contact Bathing Brands directly at CustomerService@BathingBrands.com').out, `Or email us at ${SUPPORT}`);
  eq('a lead time gains "typically" and keeps its figure', rewrite(`Processing Time: Most SaunaLife saunas ship within 7${EN}10 business days`).out,
    `Processing Time: SaunaLife products typically ship within 7${EN}10 business days`);
  eq('SaunaLife survives where it is correct', /SaunaLife/.test(rewrite('All SaunaLife products are delivered via curbside freight').out), true);
  eq('the generic sauna noun goes', rewrite('to ensure your sauna is delivered with care').out, 'to ensure the item is delivered with care');
  eq('no supplier survives a full pass', suppliersLeft(rewrite('Bathing Brands and Dundalk Leisurecraft and Dundalk').out).length, 0);
  eq('the damage sentence carries no em dash', DAMAGE.includes('—'), false);
  // the case the rules were NOT built for: an already-rewritten panel must not be rewritten again
  const once = rewrite('we partner directly with Bathing Brands, the official distributor of SaunaLife, to ensure').out;
  eq('idempotent: a second pass changes nothing', rewrite(once).out, once);
  return bad;
}
/* ⚠️ GATED. Everything below RUNS. Importing this file to reuse RULES executed its self-test, its
   live product query and its plan — and with --apply in the importer's argv it would have WRITTEN.
   Found by triggering it: an import printed "25 products name a supplier" from the importer's process.
   Exports above stay at module level; only the executable tail moves inside main(). */
const IS_MAIN_H = Boolean(process.argv[1]) && pathToFileURL(process.argv[1]).href === import.meta.url;
if (!IS_MAIN_H) { /* imported: nothing below this point runs */ } else { await main(); }

async function main() {
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds, including idempotency\n');
if (process.argv.includes('--self-test')) process.exit(0);

const readMf = async (id) => (await gql(`query($id:ID!){ product(id:$id){ metafield(namespace:"custom", key:"shipping_details"){ value } } }`, { id })).product.metafield.value;
const writeMf = async (id, value) => {
  const r = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ value } userErrors{ message } } }`,
    { m: [{ ownerId: id, namespace: 'custom', key: 'shipping_details', type: 'rich_text_field', value }] });
  if (r.metafieldsSet.userErrors.length) throw new Error(JSON.stringify(r.metafieldsSet.userErrors));
  return r.metafieldsSet.metafields[0].value;
};
/* ⚠️ THIS BRANCH WAS MISSING and 12 products were left edited by a proof run that could not undo its
   own write. A write path without a restore path is not shippable, whatever its guards say. */
const RESTORE_PATH = arg('--restore');
if (RESTORE_PATH) {
  const snap = JSON.parse(fs.readFileSync(RESTORE_PATH, 'utf8')).filter((x) => !ONLY || x.handle === ONLY);
  if (!snap.length) { console.log('  REFUSE: that backup holds no matching row'); process.exit(1); }
  let n = 0;
  for (const x of snap) {
    const live = md5(await readMf(x.id));
    if (live === x.md5) { console.log(`  already restored  ${x.handle}`); continue; }
    if (live !== (x.storedMd5 || x.afterMd5)) { console.log(`  REFUSE ${x.handle}: live ${live} is neither the before-state nor what the apply stored — edited since`); n++; continue; }
    if (!APPLY) { console.log(`  would restore     ${x.handle}`); continue; }
    const back = md5(await writeMf(x.id, x.before));
    const ok = back === x.md5;
    console.log(`  ${ok ? 'RESTORED' : 'FAIL    '} ${x.handle}  read-back ${back}${ok ? ' == before-state' : ' != ' + x.md5}`);
    if (!ok) n++; else logChange({ resource: x.id, handle: x.handle, field: 'metafield custom.shipping_details', old: 'Round 23h edit', new: 'restored', note: `restore from ${RESTORE_PATH}` });
  }
  process.exit(n ? 1 : 0);
}

const render = (n) => { if (n.type === 'text') return n.value || ''; const k = (n.children || []).map(render).join(''); return /paragraph|list-item|heading/.test(n.type) ? k + '\n' : k; };
/* ⚠️ THE SENTENCE IS SPLIT ACROSS TEXT NODES. "we partner with **Bathing Brands**, the official
   distributor of Harvia" is three nodes because the supplier name is bold, so a multi-word pattern
   applied per node CANNOT match it — and the bare fallback fired instead, producing "the manufacturer's
   distributor, the official distributor of Harvia products". Rules therefore run on the JOINED text of
   each BLOCK. A block that changes collapses to one text node, which LOSES inline bold inside that
   block; unchanged blocks keep their formatting. The collapse count is reported: it is a real cost. */
let COLLAPSED = 0;
const BLOCK = /^(paragraph|list-item|heading)$/;
function rewriteBlocks(node) {
  if (BLOCK.test(node.type)) {
    const joined = (node.children || []).map(render).join('');
    const { out } = rewrite(joined);
    if (out === joined) return node;
    COLLAPSED++;
    return { ...node, children: [{ type: 'text', value: out }] };
  }
  return { ...node, children: (node.children || []).map(rewriteBlocks) };
}

let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ id handle status vendor metafield(namespace:"custom", key:"shipping_details"){ value } } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);
const rows = all.filter((p) => p.status === 'ACTIVE' && p.metafield?.value)
  .map((p) => ({ ...p, t: JSON.parse(p.metafield.value).children.map(render).join(''), vm: md5(p.metafield.value) }));
const targets = rows.filter((p) => suppliersLeft(p.t).length);
const byValue = {};
targets.forEach((p) => { (byValue[p.vm] ||= []).push(p); });
console.log(`${targets.length} products name a supplier, across ${Object.keys(byValue).length} distinct panel values\n`);

const plan = []; let fail = 0;
for (const [vm, list] of Object.entries(byValue)) {
  const ex = list[0];
  const doc = JSON.parse(ex.metafield.value);
  const after = { ...doc, children: doc.children.map(rewriteBlocks) };
  let afterDoc = after;
  if (process.argv.includes('--inject-stray')) afterDoc = { ...after, children: [...after.children, { type: 'paragraph', children: [{ type: 'text', value: 'INJECTED' }] }] };
  if (process.argv.includes('--inject-link')) {   // an EMPTY anchor: no visible text, so only the link guard can see it
    const k = [...after.children];
    k[0] = { ...k[0], children: [...(k[0].children || []), { type: 'link', url: 'https://example.com/x', children: [{ type: 'text', value: '' }] }] };
    afterDoc = { ...after, children: k };
  }
  const beforeT = ex.t, afterT = afterDoc.children.map(render).join('');
  const left = suppliersLeft(afterT);
  const probs = [];
  /* THIS EDIT ONLY REWRITES TEXT INSIDE EXISTING BLOCKS. It never adds, removes or retypes a block, so
     the shape of the document is an invariant — and asserting it is what catches a stray node. */
  const shape = (d) => JSON.stringify(d.children.map((n) => [n.type, (n.children || []).length ? n.type : n.type]));
  if (afterDoc.children.length !== doc.children.length) probs.push(`BLOCK COUNT CHANGED ${doc.children.length} -> ${afterDoc.children.length}`);
  else if (JSON.stringify(doc.children.map((n) => n.type)) !== JSON.stringify(afterDoc.children.map((n) => n.type))) probs.push('BLOCK TYPES CHANGED');
  const urls = (d) => { const o = []; const w = (n) => { if (n.type === 'link' && n.url) o.push(n.url); (n.children || []).forEach(w); }; d.children.forEach(w); return o.sort().join('|'); };
  if (urls(doc) !== urls(afterDoc)) probs.push('LINK SET CHANGED');
  if (left.length) probs.push(`supplier name survives: ${left.join(', ')}`);
  /* the client ruled the 153 pre-existing em dashes stay, so this fails only on one THIS edit adds.
     Built from a code point, not a typed glyph, per the character-class rule. */
  const EMDASH = new RegExp('\\u2014', 'g');
  const em = (x) => (x.match(EMDASH) || []).length;
  if (em(afterT) > em(beforeT)) probs.push(`em dashes ${em(beforeT)} -> ${em(afterT)}: this edit INTRODUCED one`);
  if (/exclusive distributor/i.test(afterT)) probs.push('"exclusive distributor" survives — it implies a fixed route');
  if (beforeT === afterT) probs.push('nothing changed');
  if (JSON.stringify([...beforeT.matchAll(/https?:\/\/\S+/g)]) !== JSON.stringify([...afterT.matchAll(/https?:\/\/\S+/g)])) probs.push('a URL changed');
  if (probs.length) { fail++; console.log(`FAIL value ${vm} (${list.length} products, e.g. ${ex.handle})`); probs.forEach((x) => console.log(`     ${x}`)); continue; }
  plan.push({ vm, list, docAfter: afterDoc, beforeT, afterT, applied: rewrite(beforeT).applied });
}
if (process.argv.includes('--report')) {
  for (const v of plan) {
    console.log(`\n${'='.repeat(100)}\nvalue ${v.vm}  ${v.list.length} products  vendors: ${[...new Set(v.list.map((p) => p.vendor))].join(', ')}\n  e.g. ${v.list[0].handle}\n${'='.repeat(100)}`);
    const b = v.beforeT.split('\n'), a = v.afterT.split('\n');
    for (let i = 0; i < Math.max(b.length, a.length); i++) {
      if ((b[i] || '') !== (a[i] || '')) { if (b[i]?.trim()) console.log(`  - ${b[i].trim().slice(0, 165)}`); if (a[i]?.trim()) console.log(`  + ${a[i].trim().slice(0, 165)}`); }
    }
  }
  console.log(`\n${plan.length} values, ${plan.reduce((s, v) => s + v.list.length, 0)} products. ${COLLAPSED} block(s) collapsed to plain text (inline bold lost inside those). REPORT ONLY.`);
  process.exit(fail ? 1 : 0);
}
console.log(`planned: ${plan.length} values, ${plan.reduce((s, v) => s + v.list.length, 0)} products${fail ? `   FAILED ${fail}` : ''}`);
if (fail) { console.log('  REFUSING — nothing written'); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const write = async (id, value) => {
  const r = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ value } userErrors{ message } } }`,
    { m: [{ ownerId: id, namespace: 'custom', key: 'shipping_details', type: 'rich_text_field', value }] });
  if (r.metafieldsSet.userErrors.length) throw new Error(JSON.stringify(r.metafieldsSet.userErrors));
  return r.metafieldsSet.metafields[0].value;
};
const snap = []; const sel = ONLY ? plan.map((v) => ({ ...v, list: v.list.filter((p) => p.handle === ONLY) })).filter((v) => v.list.length) : plan;
for (const v of sel) for (const p of v.list) snap.push({ vm: v.vm, id: p.id, handle: p.handle, md5: md5(p.metafield.value), before: p.metafield.value, afterMd5: md5(JSON.stringify(v.docAfter)) });
const bpath = backup('r23h-supplier-names' + (ONLY ? '-' + ONLY : ''), snap);
for (const v of sel) for (const p of v.list) {
  const stored = await write(p.id, JSON.stringify(v.docAfter));
  const s = snap.find((x) => x.handle === p.handle); s.storedMd5 = md5(stored);
  logChange({ script: 'r23h-supplier-names', resource: p.id, handle: p.handle, field: 'metafield custom.shipping_details', old: 'named a supplier', new: 'route-neutral; typically; damage-exchange clause', note: `backup ${bpath}` });
  console.log(`  wrote ${p.handle.padEnd(48)} ${v.vm.slice(0, 8)}  stored ${s.storedMd5 === s.afterMd5 ? '= sent' : 'NORMALISED'}`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
}
