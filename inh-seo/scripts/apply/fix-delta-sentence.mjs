/* Correct the false product split on /collections/delta.
 *
 * The live copy says "five steam generators and two accessories". All seven
 * members are steam generators; the split was derived from productType, where
 * two were mistyped Sauna Accessories. Correcting the field left the sentence.
 *
 * Exact extraction — the `from` string is sliced from the live body, never
 * written from rendered text. Refuses on anything but exactly one match.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange, showDiff, assertWellFormed, ROOT } from '../lib/util.js';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');

const FROM = 'Seven Delta steam components, $2,470 to $12,009, median $4,012. This is a parts collection, not a cabin collection — five steam generators and two accessories, specified to go into a shower enclosure you already have or are building.';
const TO   = 'Seven Delta steam generators, $2,470 to $12,009, median $4,012. This is a parts collection, not a cabin collection — every unit here is the generator alone, 5kW to 30kW, specified to go into a shower enclosure you already have or are building.';

/* Re-derive every figure in TO before writing it. Verify the OUTCOME, not the write. */
async function verifyFacts() {
  const r = await gql(`query{ collections(first:1, query:"handle:delta"){ nodes{ id descriptionHtml
    products(first:50){ nodes{ title status priceRangeV2{minVariantPrice{amount}} } } } } }`);
  const c = r.collections.nodes[0];
  const a = c.products.nodes.filter((p) => p.status === 'ACTIVE');
  const pr = a.map((p) => +p.priceRangeV2.minVariantPrice.amount).sort((x, y) => x - y);
  const med = pr.length % 2 ? pr[(pr.length - 1) / 2] : (pr[pr.length / 2 - 1] + pr[pr.length / 2]) / 2;
  const gens = a.filter((p) => /generator/i.test(p.title)).length;
  const kw = a.map((p) => (p.title.match(/(\d+(?:\.\d+)?)\s*kW/i) || [])[1]).filter(Boolean).map(Number).sort((x, y) => x - y);

  const checks = [
    ['set size is seven',        a.length === 7,                       a.length],
    ['floor rounds to $2,470',   Math.round(pr[0]) === 2470,           pr[0]],
    ['ceiling rounds to $12,009', Math.round(pr[pr.length - 1]) === 12009, pr[pr.length - 1]],
    ['median rounds to $4,012',  Math.round(med) === 4012,             med],
    ['ALL seven are generators', gens === a.length,                    `${gens}/${a.length}`],
    ['all seven publish kW',     kw.length === a.length,               `${kw.length}/${a.length}`],
    ['kW span is 5 to 30',       kw[0] === 5 && kw[kw.length - 1] === 30, `${kw[0]}–${kw[kw.length - 1]}`],
  ];
  let bad = 0;
  for (const [name, ok, got] of checks) {
    console.log(`     ${ok ? 'ok  ' : 'FAIL'}  ${name.padEnd(26)} ${got}`);
    if (!ok) bad++;
  }
  if (bad) throw new Error(`${bad} fact check(s) failed — refusing to write`);
  return c;
}

console.log('\n  FACT VERIFICATION (re-derived now, not trusted from the report)');
const c = await verifyFacts();

const before = c.descriptionHtml;
const n = before.split(FROM).length - 1;
console.log(`\n  anchor matches: ${n}`);
if (n !== 1) throw new Error(`anchor matched ${n} times, expected exactly 1 — refusing`);

const after = before.replace(FROM, TO);
assertWellFormed(after, 'delta description', before);
showDiff('collections/delta', before, after);

/* The staged file carries the identical sentence. Both move or neither does. */
const staged = path.join(ROOT, 'content/collections/delta.md');
const sBefore = fs.readFileSync(staged, 'utf8');
const sn = sBefore.split(FROM).length - 1;
console.log(`  staged file anchor matches: ${sn}`);
if (sn !== 1) throw new Error(`staged anchor matched ${sn} times, expected 1 — refusing`);
const sAfter = sBefore.replace(FROM, TO);

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const bpath = backup('delta-sentence', { collection: { id: c.id, descriptionHtml: before }, staged: sBefore });
console.log(`\n  backup -> ${bpath}`);

const w = await gql(`mutation($input:CollectionInput!){ collectionUpdate(input:$input){ collection{ id } userErrors{ field message } } }`,
  { input: { id: c.id, descriptionHtml: after } });
if (w.collectionUpdate.userErrors.length) throw new Error(JSON.stringify(w.collectionUpdate.userErrors));
fs.writeFileSync(staged, sAfter);

logChange({ resource: c.id, handle: 'delta', type: 'collection', field: 'descriptionHtml',
  from: FROM, to: TO, note: 'false 5/2 product split derived from pre-normalisation productType; all seven are generators', backup: bpath });

console.log('  written: live collection + content/collections/delta.md');
