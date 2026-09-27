/* Does any product's shipping panel name a MANUFACTURER OTHER THAN ITS OWN VENDOR?
 *   node scripts/audit/cross-manufacturer-panels.mjs [--self-test]
 *
 * Six Icetubs products carrying SaunaLife's brand name, distributor, return window and lead time were
 * found by accident while auditing sauna wording. Found-by-accident means nobody has looked, so this
 * looks. READ-ONLY: it reports a count and names the rows. It fixes nothing.
 *
 * Method: the panel text is compared against the product's own `vendor` field and against every OTHER
 * vendor string in the catalogue. A vendor is matched as a WHOLE normalised string, never a token —
 * "Dynamic Cold Therapy" and "Dynamic Saunas" share a word, and a token match would cross them.
 * InHouse Wellness is excluded: we are the retailer and every panel names us legitimately.
 */
import { gql } from '../lib/shopify.js';

const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const render = (n) => { if (n.type === 'text') return n.value || ''; const k = (n.children || []).map(render).join(''); return /paragraph|list-item|heading/.test(n.type) ? k + '\n' : k; };
const OURS = ['inhousewellness', 'inhousewellnesscom'];
/* ⚠️ The first run reported 65, and its two largest groups were the INSTRUMENT, not the estate: the
   catalogue carries TWO VENDOR STRINGS FOR ONE COMPANY, so a "Scandia" panel on a "Scandia
   Manufacturing" product read as cross-manufacturer while being perfectly correct. Resolved by a
   hand-verified equivalence map with a reason each — never by loosening the match, which is what
   produced the collision risk the whole-string rule exists to avoid. */
const SAME_COMPANY = [
  { group: ['dundalkleisurecraft', 'leisurecraft'], why: 'one company, two vendor strings (25 and 1 ACTIVE)' },
  { group: ['scandiamanufacturing', 'scandia'], why: 'one company, two vendor strings (16 and 9 ACTIVE)' },
  { group: ['huum'], why: 'HUUM and Huum are the same string in different case; norm() already merges them' },
  { group: ['calflame', 'calspa'], why: 'Cal Flame and Cal Spa are sibling brands of one manufacturer' },
  { group: ['frozen', 'medicalbreakthrough'], why: 'Frozen is Medical Breakthrough\'s product line' },
];
const sameCompany = (a, b) => a === b || SAME_COMPANY.some((e) => e.group.includes(a) && e.group.includes(b));
/* And a vendor string that is also an ORDINARY PHRASE cannot be matched in prose. "Steam Shower" is a
   vendor on a non-ACTIVE product AND the normal English name for the thing 12 Thermasol panels sell,
   so every one of them read as naming a foreign manufacturer. Named, not pattern-tuned. */
const GENERIC_VENDOR = { steamshower: 'also the ordinary phrase "steam shower"; matches prose, not a brand' };

export function foreignVendors(panelText, ownVendor, allVendors) {
  const t = norm(panelText), own = norm(ownVendor || '');
  return allVendors
    .map(norm).filter((v) => v.length >= 5 && !OURS.includes(v) && !GENERIC_VENDOR[v])
    .filter((v) => !sameCompany(v, own) && t.includes(v))
    .filter((v, i, a) => a.indexOf(v) === i);
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  const V = ['SaunaLife', 'Icetubs', 'Dynamic Cold Therapy', 'Dynamic Saunas', 'Huum', 'InHouse Wellness'];
  eq('the real defect: an Icetubs panel naming SaunaLife', foreignVendors('All SaunaLife products ship curbside', 'Icetubs', V), ['saunalife']);
  eq('a panel naming its OWN vendor is clean', foreignVendors('All SaunaLife products ship curbside', 'SaunaLife', V), []);
  eq('naming InHouse Wellness is never a finding', foreignVendors('At InHouse Wellness we coordinate freight', 'Icetubs', V), []);
  // the case a token match would get wrong, and the reason whole-string matching is used
  eq('Dynamic Saunas text does NOT flag a Dynamic Cold Therapy product', foreignVendors('your Dynamic Saunas cabin', 'Dynamic Saunas', V), []);
  eq('a short vendor is not matched (too collision-prone)', foreignVendors('the huum stove', 'Icetubs', ['Huum']), []);
  // the case the FIRST version got wrong: two vendor strings for one company is not cross-manufacturer
  eq('a Scandia panel on a Scandia Manufacturing product is clean', foreignVendors('All Scandia products ship freight', 'Scandia Manufacturing', ['Scandia', 'Scandia Manufacturing', 'Icetubs']), []);
  eq('a Leisurecraft panel on a Dundalk Leisurecraft product is clean', foreignVendors('Leisurecraft ships curbside', 'Dundalk Leisurecraft', ['Leisure Craft', 'Dundalk Leisurecraft']), []);
  eq('but a genuinely foreign brand is still caught', foreignVendors('All SaunaLife products ship curbside', 'Scandia Manufacturing', ['SaunaLife', 'Scandia Manufacturing']), ['saunalife']);
  eq('an ordinary phrase that is also a vendor string is not a finding', foreignVendors('your new steam shower ships freight', 'Thermasol', ['Steam Shower', 'Thermasol']), []);
  eq('two foreign vendors are both reported', foreignVendors('SaunaLife and Huum ship together', 'Icetubs', ['SaunaLife', 'Huum', 'Icetubs']).length, 1);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds, including the case a token match would get wrong\n');
if (process.argv.includes('--self-test')) process.exit(0);

let cur = null; const all = [];
do {
  const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ handle status vendor productType metafield(namespace:"custom", key:"shipping_details"){ value } } } }`, { c: cur });
  all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null;
} while (cur);
const vendors = [...new Set(all.map((p) => p.vendor).filter(Boolean))];
const rows = all.filter((p) => p.status === 'ACTIVE' && p.metafield?.value);
console.log(`  ${rows.length} ACTIVE products with a shipping panel; ${vendors.length} distinct vendors in the catalogue`);

const findings = [];
for (const p of rows) {
  const t = JSON.parse(p.metafield.value).children.map(render).join('');
  const foreign = foreignVendors(t, p.vendor, vendors);
  if (foreign.length) findings.push({ handle: p.handle, vendor: p.vendor, productType: p.productType, foreign });
}
/* known positive: this row is hand-verified and MUST be found, or the sweep is not working */
const KNOWN = 'icetubs-icebarrel-cold-plunge';
if (!findings.some((f) => f.handle === KNOWN)) { console.log(`\n  REFUSING: the hand-verified row ${KNOWN} was not found. The sweep is not working.`); process.exit(1); }
console.log(`  known positive ${KNOWN} found\n`);

console.log(`>>> panels naming a manufacturer other than their own vendor: ${findings.length}`);
const byPair = {};
findings.forEach((f) => { const k = `${f.vendor}  ->  names ${f.foreign.join(', ')}`; (byPair[k] ||= []).push(f.handle); });
for (const [k, hs] of Object.entries(byPair).sort((a, b) => b[1].length - a[1].length)) {
  console.log(`\n  ${hs.length}x  ${k}`);
  hs.slice(0, 8).forEach((h) => console.log(`        ${h}`));
  if (hs.length > 8) console.log(`        …and ${hs.length - 8} more`);
}
console.log(`\n  ${findings.length} product(s). Reported, not fixed.`);
