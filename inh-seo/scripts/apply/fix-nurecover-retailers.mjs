/* Round 15 citation pass, article 5 of 5 — nurecover-tropic-home-sauna-review. --dry-run default.
 * Client ruling 16 Sep 2026: remove competitor links where the competitor is price-matched or
 * cheaper than us. Haven of Heat is $2,299 against our $2,299. The two above our price go too,
 * under the second test: not one spec in this article is published ONLY by a competitor — our
 * own listing carries every one, and several more precisely (5-10 mG at 2-3 inches; a named
 * 5-year warranty where the article said "multi-year").
 *
 *   node scripts/apply/fix-nurecover-retailers.mjs [--apply]
 *
 * SCOPE, and what is deliberately NOT here. This pass does the five things approved:
 * competitor entries out, specs re-sourced to our listing, our product linked in the verdict,
 * the sourcing sentence rewritten, and the bibliography corrected to Hussain & Cohen with its
 * inline tags. It does NOT re-point the ~12 cites that Hussain & Cohen cannot carry (dementia,
 * all-cause mortality, dose-response). Those stay outstanding and are reported as such.
 *
 * The 22 sole-source parens are handled POSITIONALLY, in document order, each asserting a
 * context string that must precede it. A count that is not exactly 22, or a context that does
 * not match, refuses the whole run.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'nurecover-tropic-home-sauna-review';
const PROD = 'https://inhousewellness.com/products/maxxus-mx-s106-01';
const OURS = '(InHouse Wellness, MX-S106-01 listing)';
const COMP = ['Golden Designs Inc., 2024', 'Golden Designs Saunas, 2024', 'Haven of Heat, 2024'];

/* The 22 parens where a competitor is the ONLY source, in document order.
 * 'ours'  — a specification our listing publishes; re-source it.
 * 'drop'  — not a specification. A retail product page never supported it and our listing
 *           cannot either: buyer guidance, psychology, or a generic manual instruction. */
const SOLE = [
  ['ours', 'exterior about 39" × 36" × 75"'],
  ['ours', 'typically 7 panels in the S-Line model'],
  ['ours', 'non-GFCI dedicated circuit'],
  ['ours', 'in many listings'],
  ['ours', 'but then remains permanently installed'],
  ['ours', 'but no plumbing'],
  ['ours', 'permanent indoor installation'],
  ['ours', 'radiant heat from carbon panels'],
  ['ours', 'up to 140°F max'],
  ['ours', 'requires dedicated spot and circuit'],
  ['ours', 'often sold with multi-year warranty'],
  ['drop', 'accommodate a permanent installation'],
  ['drop', 'psychological benefit of a "real" wellness space'],
  ['drop', 'may prefer an infrared cabin like the Maxxus'],
  ['ours', 'can reach 140°F'],
  ['drop', 'for guidance on additives'],
  ['ours', 'audio via Bluetooth or aux'],
  ['ours', 'enhancing comfort and aesthetics'],
  ['ours', 'concerned about electromagnetic exposure'],
  ['ours', 'seamless without external devices'],
  ['ours', 'cabins like the Maxxus'],
  ['ours', 'typically cost several thousand dollars'],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!a) throw new Error('article not found');
let body = a.body;

/* ── 1. text upgrades that must happen BEFORE the paren sweep, because two of them
 *       change the words the sweep's context strings sit next to. Each asserts one match. ── */
const PRE = [
  ['SOURCING SENTENCE — a claim about sourcing this pass is about to make false',
   "Retailer and manufacturer pages provide the clearest specs for the Maxxus model, while third-party Nurecover reviews give more practical specs than the brand's marketing copy",   // apostrophe is U+0027, confirmed by code point
   `The Maxxus specifications here come from <a href="${PROD}">our own listing for the MX-S106-01</a>, which publishes interior and exterior dimensions, the panel count, the operating range and the warranty terms. Where the manufacturer publishes something we do not, it is named as the manufacturer’s figure. Third-party Nurecover reviews give more practical detail than that brand’s marketing copy`],

  ['WARRANTY — "multi-year" replaced with the term our listing names',
   'Solid wood construction, established manufacturer; often sold with multi-year warranty',
   'Solid wood construction, established manufacturer; 5-year limited manufacturer’s warranty on wood, structure, heating elements and electronics, indoor use only'],

  ['LOW EMF — our listing publishes a figure no competitor cite carries',
   'Low-EMF carbon panels appeal to users concerned about electromagnetic exposure',
   'Low-EMF carbon panels appeal to users concerned about electromagnetic exposure; the panels are specified around 5–10 mG at 2–3 inches from the heater surface'],

  ['PRICE — a vague band replaced with a pointer, because a single price goes stale',
   'The Maxxus MX-S106-01 and similar 1-person infrared cabins typically cost several thousand dollars',
   `1-person infrared cabins of this kind run well above a portable tent; current pricing for the MX-S106-01 is on <a href="${PROD}">our product page</a>`],

  ['VERDICT — link the product the recommendation names',
   'the lasting, higher-quality experience, stronger heat, and better build of fixed 1-person infrared saunas like the Maxxus MX-S106-01 offer superior value',
   `the lasting, higher-quality experience, stronger heat, and better build of a fixed 1-person infrared sauna like the <a href="${PROD}">Maxxus MX-S106-01</a> offer superior value`],
];

let fail = 0;
console.log('  PRE-SWEEP EDITS');
for (const [label, from, to] of PRE) {
  const n = body.split(from).length - 1;
  console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}
if (fail) { console.log(`\n  refusing: ${fail} pre-sweep target(s) not matched once`); process.exit(1); }

/* the warranty and price upgrades rewrote two context anchors; the sweep uses the NEW words */
SOLE[10][1] = 'electronics, indoor use only';
SOLE[18][1] = 'from the heater surface';
SOLE[21][1] = 'on <a href="' + PROD + '">our product page</a>';

/* ── 2. the paren sweep ── */
let soleIdx = 0, stripped = 0, resourced = 0, dropped = 0;
const problems = [];
body = body.replace(/ ?\(([^()]{0,240}?)\)/g, (whole, inner) => {
  if (!/Golden Designs|Haven of Heat/.test(inner)) return whole;
  const rest = inner.split(';').map((s) => s.trim()).filter((s) => !COMP.includes(s));
  if (rest.length) { stripped++; return whole.replace(inner, rest.join('; ')); }
  const d = SOLE[soleIdx];
  if (!d) { problems.push(`sole-source paren ${soleIdx + 1} has no decision`); soleIdx++; return whole; }
  soleIdx++;
  if (d[0] === 'ours') { resourced++; return ' ' + OURS; }
  dropped++; return '';
}, );

console.log(`\n  PAREN SWEEP`);
console.log(`    competitor names stripped from a paren with other sources: ${stripped}`);
console.log(`    sole-source parens re-sourced to our listing:              ${resourced}`);
console.log(`    sole-source parens dropped (not a specification):          ${dropped}`);
console.log(`    sole-source parens seen: ${soleIdx} (want ${SOLE.length})`);
if (soleIdx !== SOLE.length) problems.push(`sole-source count ${soleIdx}, expected ${SOLE.length}`);

/* every 'ours'/'drop' decision must have landed next to the context it was written for */
for (let i = 0; i < SOLE.length; i++) {
  const [kind, ctx] = SOLE[i];
  const want = kind === 'ours' ? ctx + ' ' + OURS : ctx;
  if (!body.includes(want)) problems.push(`decision ${i + 1} (${kind}) context not found after edit: ${JSON.stringify(ctx.slice(0, 48))}`);
}

/* ── 3. bibliography: three competitor entries out, our listing in, Laukkanen corrected ── */
const NB = ' ';
const entry = (text, url) => `<li>\n<p>${text}<a href="${url}">${NB}</a><a href="${url}">${url}</a></p>\n</li>`;
const BIB = [
  ['BIB remove Golden Designs Inc. (competitor, $3,999)', /<li>\n<p>Golden Designs Inc\.[\s\S]*?<\/li>\n?/],
  ['BIB remove GoldenDesignSaunas.com (competitor, $2,941)', /<li>\n<p>GoldenDesignSaunas\.com[\s\S]*?<\/li>\n?/],
  ['BIB remove Haven of Heat (competitor, PRICE-MATCHED at $2,299)', /<li>\n<p>Haven of Heat\.[\s\S]*?<\/li>\n?/],
];
for (const [label, re] of BIB) {
  const m = body.match(new RegExp(re.source, 'g'));
  const n = m ? m.length : 0;
  console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
  if (n !== 1) { problems.push(label); continue; }
  body = body.replace(re, '');
}

const LAUK = '<li>\n<p>Laukkanen T et al. "Clinical Effects of Regular Dry Sauna Bathing: A Systematic Review." Mayo Clinic Proceedings. Published 2018-04-23.';
const nL = body.split(LAUK).length - 1;
console.log(`    ${nL === 1 ? 'ok  ' : 'FAIL'} ${nL}×  BIB correct Laukkanen/Mayo → Hussain & Cohen / Evid Based Complement Alternat Med`);
if (nL !== 1) problems.push('Laukkanen bibliography entry');
else body = body.replace(LAUK, '<li>\n<p>Hussain J, Cohen M. "Clinical Effects of Regular Dry Sauna Bathing: A Systematic Review." Evidence-Based Complementary and Alternative Medicine, 2018. 40 studies, 3,855 participants; only 13 randomised and most under 40 participants. The authors conclude the medical evidence for claimed benefits "is not well established".');

/* our listing as a source entry, placed where the first competitor entry was */
const AFTER = body.indexOf('<li>\n<p>Instalab.');
if (AFTER === -1) problems.push('anchor for our own source entry not found');
else {
  const ours = entry('InHouse Wellness. "Maxxus MX-S106-01 S-Line 1-Person Low EMF FAR Infrared Sauna." Product listing: interior and exterior dimensions, seven low-EMF carbon panels specified around 5–10 mG at 2–3 inches, 118–132°F typical with a ~140°F maximum, 120V/15A non-GFCI, and a 5-year limited manufacturer’s warranty.', PROD);
  body = body.slice(0, AFTER) + ours + '\n' + body.slice(AFTER);
}

/* the 58 inline tags travel with the bibliography entry */
const tagsBefore = (body.match(/Laukkanen et al\., 2018/g) || []).length;
body = body.split('Laukkanen et al., 2018').join('Hussain &amp; Cohen, 2018');
console.log(`\n  inline "Laukkanen et al., 2018" tags rewritten: ${tagsBefore}`);

assertWellFormed(body, HANDLE);

/* ── 4. pre-write checks ── */
const checks = [
  ['goldendesigninc.com', false], ['goldendesignsaunas.com', false], ['havenofheat.com', false],
  ['Golden Designs Inc., 2024', false], ['Golden Designs Saunas, 2024', false], ['Haven of Heat, 2024', false],
  ['Laukkanen et al., 2018', false], ['Mayo Clinic Proceedings', false],
  ['Hussain &amp; Cohen, 2018', true], ['Hussain J, Cohen M', true],
  ['products/maxxus-mx-s106-01', true], ['5–10 mG at 2–3 inches', true],
  ['5-year limited manufacturer', true], ['multi-year warranty', false],
];
const bad = checks.filter(([k, want]) => body.includes(k) !== want);
console.log(`  pre-write checks: ${checks.length - bad.length}/${checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);
/* The source entry uses the URL THREE times by this article's own convention: a blank anchor
 * href, the visible-URL anchor href, and the visible URL text. So the faithful expectation is
 * 5 hrefs (3 in prose + 2 in the entry) and 6 string occurrences. Both are asserted; the guard
 * is narrowed to the real convention rather than widened to accept whatever came out. */
const ourHrefs = (body.match(new RegExp('href="' + PROD + '"', 'g')) || []).length;
const ourLinks = body.split(PROD).length - 1;
console.log(`  hrefs to our product page: ${ourHrefs} (want 5: sourcing + price + verdict + 2 in the source entry)`);
console.log(`  total occurrences of the URL: ${ourLinks} (want 6: the 5 hrefs plus the visible URL text)`);
if (ourHrefs !== 5) problems.push(`hrefs to our product ${ourHrefs}, expected 5`);
if (bad.length || problems.length || ourLinks !== 6) {
  console.log('\n  PROBLEMS:'); [...problems, ...bad.map((b) => `check ${b[0]}`)].forEach((p) => console.log('    -', p));
  console.log('  refusing'); process.exit(1);
}

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('nurecover-retailers', [{ id: a.id, handle: HANDLE, before: a.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: a.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: a.id, handle: HANDLE, field: 'body', old: '3 competitor bibliography entries (1 price-matched, 2 above); 50 competitor citation parens; Laukkanen/Mayo Clinic Proceedings on PMC5941775 with 58 inline tags; no link to our own listing', new: 'competitors removed; specs re-sourced to our MX-S106-01 listing; Hussain & Cohen corrected; 4 links to our product', note: 'Round 15 citation pass 5/5 — client price ruling' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, want] of checks) {
  const has = b.includes(k);
  console.log(`    ${has === want ? 'ok  ' : 'FAIL'} ${String(has).padEnd(5)} ${k}`);
  if (has !== want) process.exitCode = 1;
}
console.log(`    hrefs to our product page: ${(b.match(new RegExp('href="' + PROD + '"', 'g')) || []).length} (want 5)   total occurrences: ${b.split(PROD).length - 1} (want 6)`);
