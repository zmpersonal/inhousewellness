/* dynamic-venice-sauna-review — DE-LINK, NOT DE-CITE. --dry-run default.
 * Client ruling 16 Sep 2026.
 *
 *   node scripts/apply/fix-venice-retailers.mjs [--apply]
 *
 * THE RULE THIS ARTICLE ESTABLISHES: a competitor cited AS a competitor keeps the NAME and loses
 * the LINK. The name carries the argument, the link carries the sale, and they are separable.
 * 23 of this article's 41 competitor citations exist to tell the reader a number is a SELLER'S
 * claim rather than a measurement — "These are seller claims, not lab results". Stripping those
 * would delete the article's best material to fix a leak that lives entirely in the href.
 *
 * Five of seven competitors are at or below our price (3 undercut by $200, 2 matched on the Elite
 * SKU). The other two are cited for specs we publish. ALL SEVEN lose their links.
 *
 * Every inline tag is handled POSITIONALLY, in document order, asserting a context string. A count
 * that is not exactly 41, or a context that does not match after the edit, refuses the run.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'dynamic-venice-sauna-review';
const P_STD = 'https://inhousewellness.com/products/dynamic-infrared-sauna-venice-edition';
const OURS = '(InHouse Wellness, DYN-6210-01 listing)';
const NAMES = ['Golden Designs', 'Dynamic Saunas Direct', 'Sun Valley Saunas', 'Skyward Medical',
  'Strength & Wellness Supply', 'Zogics', 'Sunflare Saunas'];

/* 41 decisions in document order.
 *  'ours'  — a specification our own listing publishes; cite ourselves instead.
 *  'keep'  — the citation's whole job is that a SELLER said it. Name stays, unchanged.
 *  'drop'  — buyer guidance no source supports; a seller page never established it. */
const TAGS = [
  ['ours', 'snug for two larger adults'],                        //  1 dimensions
  ['ours', 'wall socket" appliance'],                            //  2 120V/15A
  ['keep', 'not independently tested'],                          //  3 seller-reported
  ['keep', 'not a proven medical benefit'],                      //  4 marketing claim
  ['keep', 'benefit for any specific reading'],                  //  5 what the sources do not establish
  ['ours', 'indoor two-person far-infrared sauna'],              //  6 model
  ['ours', 'so read carefully'],                                 //  7 exterior + overhang
  ['ours', 'approximately 43 × 37 × 70 in.'],          //  8 interior
  ['ours', 'arriving in three boxes'],                           //  9 weight
  ['ours', 'six carbon low-EMF panels'],                         // 10 panels
  ['ours', 'a dedicated 120V/15A connection'],                   // 11 electrical
  ['ours', 'and chromotherapy lighting'],                        // 12 materials
  ['keep', 'consistently across product listings'],              // 13 listings agree — about sellers
  ['keep', 'from two different pages'],                          // 14 SKU caution
  ['keep', 'depending on the listing'],                          // 15 sellers place the range
  ['keep', 'treat it as a ballpark'],                            // 16 seller claim, not lab testing
  ['keep', 'measured farther away'],                             // 17 one distributor vs another
  ['ours', 'arriving in multiple boxes'],                        // 18 weight restated
  ['keep', 'a heavy, multi-box shipment'],                       // 19 ask the seller
  ['ours', 'a dedicated 120V/15A outlet or circuit'],            // 20 electrical
  ['ours', 'designed to simplify setup'],                        // 21 clasp-together
  ['keep', 'without full warranty wording'],                     // 22 one retailer page states
  ['keep', 'simplifies a technical concept'],                    // 23 myth correction
  ['keep', 'two-adult use can be snug'],                         // 24 myth correction
  ['keep', 'a quantified figure with proven safety'],            // 25 seller EMF numbers
  ["keep", "but there isn't one"],                          // 26 one seller says 145
  ['keep', 'just sounds frictionless'],                          // 27 myth correction
  ['ours', 'Requires a 120V/15A outlet'],                        // 28 spec bullet
  ['keep', 'ceiling height before buying'],                      // 29 retailers reverse tables
  ['keep', 'not lab results'],                                   // 30 seller claims
  ['keep', 'would be stronger evidence'],                        // 31 independent testing
  ['keep', 'so plan for two people'],                            // 32 "easy assembly" is a seller claim
  ['drop', 'typically means maximum occupancy'],                 // 33 interpretation, no source
  ['drop', 'load with an electrician'],                          // 34 guidance
  ['drop', 'Plan a permanent indoor location'],                  // 35 guidance
  ['keep', 'Confirm the full SKU on your listing'],              // 36 SKU caution
  ['keep', 'Verify materials by SKU'],                           // 37 listings vary
  ['keep', 'mention a red-light feature'],                       // 38 some listings
  ['keep', 'drive your buying decision'],                        // 39 no outcome in these sources
  ['drop', 'delivery method with your seller'],                  // 40 guidance
  ['drop', 'electrical needs, and dealer warranty'],             // 41 guidance
  /* 42-43 sit AFTER the Sources heading, in "What We Still Don't Know". My first
   * enumeration sliced the document at the split point and missed them; this guard's
   * count is what found them. Both are seller-as-seller. */
  ['keep', 'clinical significance in these sources'],            // 42 figures come from sellers
  ['keep', 'over five-plus years is unproven'],                  // 43 no long-term field testing
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!a) throw new Error('article not found');
let body = a.body;
const problems = [];

/* ── 1. inline tags ── */
let i = 0, toOurs = 0, kept = 0, dropped = 0;
/* The separator before a citation is U+0020 in most places and U+00A0 in others — the
 * same non-breaking space that defeated the cold-plunge anchors. Built from code points. */
const TAG_RE = new RegExp('[\\u0020\\u00A0]?\\(([^()]{0,240}?)\\)', 'g');
const nb = (t) => t.replace(new RegExp('\\u00A0', 'g'), ' ');   // normalise for COMPARISON only
body = body.replace(TAG_RE, (whole, inner) => {
  const dec = inner.replace(/&amp;/g, '&');
  if (!NAMES.some((n) => dec.includes(n))) return whole;
  const d = TAGS[i];
  if (!d) { problems.push(`inline tag ${i + 1} has no decision`); i++; return whole; }
  i++;
  if (d[0] === 'keep') { kept++; return whole; }
  if (d[0] === 'ours') { toOurs++; return ' ' + OURS; }
  dropped++; return '';
});
console.log('  INLINE TAGS');
console.log(`    kept  (a competitor cited AS a competitor — name stays): ${kept}`);
console.log(`    ours  (a spec our own listing publishes):                ${toOurs}`);
console.log(`    drop  (buyer guidance no source supports):               ${dropped}`);
console.log(`    seen: ${i} (want ${TAGS.length})`);
if (i !== TAGS.length) problems.push(`inline tag count ${i}, expected ${TAGS.length}`);

for (let k = 0; k < TAGS.length; k++) {
  const [kind, ctx] = TAGS[k];
  const want = kind === 'ours' ? ctx + ' ' + OURS : ctx;
  if (!nb(body).includes(nb(want))) problems.push(`decision ${k + 1} (${kind}) context missing after edit: ${JSON.stringify(ctx.slice(0, 44))}`);
}

/* ── 2. de-link the seven Sources entries — the NAME stays, the href goes ── */
console.log('\n  SOURCES DE-LINK (name kept, link removed)');
const ENTRIES = ['Golden Designs Inc.', 'Dynamic Saunas Direct', 'Sun Valley Saunas',
  'Skyward Medical', 'Strength &amp; Wellness Supply', 'Zogics', 'Sunflare Saunas'];
let delinked = 0;
for (const name of ENTRIES) {
  const re = new RegExp('(<li>\\s*<p>' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[^<]*?)<a href="[^"]+">[^<]*</a><a href="[^"]+">[^<]*</a>');
  const m = body.match(new RegExp(re.source, 'g'));
  const n = m ? m.length : 0;
  console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${name}`);
  if (n !== 1) { problems.push(`sources entry ${name}`); continue; }
  body = body.replace(re, '$1 Product listing, link withheld: this seller is at or below our price, or is cited for a specification we publish.');
  delinked++;
}

assertWellFormed(body, HANDLE);

/* ── 3. pre-write checks ── */
const HOSTS = ['goldendesigninc.com', 'dynamicsaunasdirect.com', 'sunvalleysaunas.com',
  'skywardmedical.com', 'strengthwellnesssupply.com', 'zogics.com', 'sunflaresaunas.com'];
const checks = [
  ...HOSTS.map((h) => [h, false]),
  ['These are seller claims, not lab results', true],
  ['not independently tested', true],
  ['seller EMF numbers, not independent clinical validation', true],
  ['Sun Valley Saunas', true], ['Skyward Medical', true], ['Zogics', true],
  [OURS, true], ['link withheld', true],
];
const bad = checks.filter(([k, want]) => nb(body).includes(nb(k)) !== want);
console.log(`\n  competitor hrefs removed: ${delinked}/7`);
console.log(`  pre-write checks: ${checks.length - bad.length}/${checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);
const extHrefs = (body.match(/href="https?:\/\/(?!inhousewellness\.com)/g) || []).length;
console.log(`  external hrefs remaining: ${extHrefs} (want 18 — the 9 research/health sources, 2 each)`);
if (bad.length || problems.length || delinked !== 7 || extHrefs !== 18) {
  console.log('\n  PROBLEMS:'); [...problems, ...bad.map((b) => `check ${b[0]}`)].forEach((p) => console.log('    -', p));
  console.log('  refusing'); process.exit(1);
}

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('venice-retailers', [{ id: a.id, handle: HANDLE, before: a.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: a.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: a.id, handle: HANDLE, field: 'body', old: '7 competitor product-page links (3 undercutting us by $200, 2 price-matched on the Elite SKU, 2 cited for specs we publish); 41 inline competitor citations', new: 'all 7 de-linked, names kept; 13 spec cites moved to our own listing; 5 unsupported guidance cites dropped; 23 seller-as-seller cites untouched', note: 'de-link not de-cite — client ruling 16 Sep 2026' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, want] of checks) {
  const has = b.includes(k);
  console.log(`    ${has === want ? 'ok  ' : 'FAIL'} ${String(has).padEnd(5)} ${k.slice(0, 56)}`);
  if (has !== want) process.exitCode = 1;
}
console.log(`    external hrefs: ${(b.match(/href="https?:\/\/(?!inhousewellness\.com)/g) || []).length} (want 18)`);
