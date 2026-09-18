/* sauna-wood-species-wet-heat-durability — the Venice split, applied to vendor citations.
 * --dry-run default.   node scripts/apply/fix-wood-vendors.mjs [--apply]
 *
 * THE RULE, which has now held in three domains:
 *   a source cited AS A CATEGORY OF SOURCE keeps its name and loses its link;
 *   a source cited as an AUTHORITY on something a better source covers is dropped.
 *
 * Here: 12 vendor citations sit on wood science that the USDA Forest Products Laboratory (already
 * cited 23 times) and BioResources cover — several in the SAME bracket. Those are redundant, the
 * Crinnion shape. The rest are vendors cited as industry guidance on service life, odour and
 * maintenance, which is what they are and what the article already calls them.
 *
 * The 31 vendor brackets are handled POSITIONALLY, in document order, with an asserted context.
 * Bracket strings repeat — "[Peak Primal Wellness, 2026]" appears 10 times in four different roles
 * — so a string replace cannot distinguish them.
 *
 * NOTE THE DELIMITER: this article cites in SQUARE brackets throughout.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'sauna-wood-species-wet-heat-durability-off-gassing-maintenance';
const VEND = ['Peak Primal Wellness', 'Haven of Heat', 'Pro Saunas', 'Eden Hut', 'High Tech Health'];
const USDA_FPL = '[USDA Forest Products Laboratory]';
const USDA_WH = '[USDA Wood Handbook]';

/* 31 decisions in document order.
 *  ['usda'|'bior', replacement]  — redundant wood science; the better source is already cited
 *  ['keep']                      — a vendor cited AS industry guidance, or an experiential claim
 *                                  no published authority covers. Name stays. */
const B = [
  ['usda', USDA_FPL, 'than cedar does'],                      //  1 species durability
  ['bior', '[BioResources]', 'harsh humidity cycles'],        //  2 thermal modification, moisture
  ['usda', USDA_WH, 'surface defects over time'],             //  3 glossary: dimensional stability
  ['usda', USDA_WH, 'swelling, shrinking, and movement'],     //  4 glossary: hygroscopicity
  ['usda', USDA_WH, 'under thermal cycling'],                 //  5 cedar shrinkage coefficients
  ['keep', null, 'a meaningful drawback'],                    //  6 cedar aroma — experiential
  ['keep', null, 'overpowering or irritating'],               //  7 hemlock odour — experiential
  ['keep', null, 'is sustained'],                             //  8 aspen comfort — experiential
  ['usda', USDA_FPL, 'dries reliably after every session'],   //  9 aspen durability
  ['bior', '[BioResources]', 'under wet-heat cycling'],       // 10 thermal modification mechanism
  ['keep', null, 'under harsh outdoor conditions'],           // 11 service life — industry guidance
  /* The first-heat-cycle bracket is [Reddit, 2022; PubMed, 2009] and is NOT in this list: Reddit
   * is not one of the five vendors. My hand enumeration counted it as one and reported 31 vendor
   * brackets where the script sees 30 — the count that does not move is the signal. */
  ['keep', null, 'surface residue'],                          // 12 maintenance practice
  ['keep', null, 'approved for sauna use'],                   // 14 maintenance practice
  ['keep', null, 'a universal number to be meaningful'],      // 15 service life — industry guidance
  ['usda', USDA_WH, 'the wood has failed'],                   // 16 cosmetic vs structural
  ['keep', null, 'scent-sensitive users'],                    // 17 cedar extractives — experiential
  ['usda', USDA_FPL, 'chronic moisture exposure'],            // 18 aspen durability myth
  ['keep', null, 'cleaning, and ventilation'],                // 19 maintenance practice
  ['keep', null, 'drying habits, and maintenance'],           // 20 service life — industry guidance
  ['keep', null, 'prefer hemlock or aspen'],                  // 21 scent sensitivity
  ['keep', null, 'a neutral cabin experience'],               // 22 hemlock preference
  ['usda', USDA_FPL, 'on contact surfaces'],                  // 23 aspen decay resistance
  ['keep', null, 'installation, and maintenance habits'],     // 24 service life — industry guidance
  ['keep', null, 'installation type, and care'],              // 25 the 10–30 year headline answer
  ['keep', null, 'natural decay resistance'],                 // 26 TMW vs cedar — industry guidance
  ['keep', null, 'degradation in any species'],               // 27 maintenance practice
  ['keep', null, 'their neutral character'],                  // 28 aromatic wood preference
  ['bior', '[BioResources]', 'without chemical preservatives'], // 29 thermal modification definition
  ['keep', null, 'upgrading for outdoor applications'],       // 30 outdoor vs indoor
  ['usda', USDA_WH, 'across all species'],                    // 31 ventilation and decay
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const art = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!art) throw new Error('not found');
let body = art.body;
const problems = [];

/* ── 1. the split ── */
let i = 0, dropped = 0, kept = 0;
body = body.replace(/\s?\[([^\[\]]{0,160}?)\]/g, (whole, inner) => {
  if (!VEND.some((v) => inner.includes(v))) return whole;
  const d = B[i];
  if (!d) { problems.push(`bracket ${i + 1} has no decision`); i++; return whole; }
  i++;
  if (d[0] === 'keep') { kept++; return whole; }
  dropped++; return ' ' + d[1];
});
console.log('  THE SPLIT');
console.log(`    dropped — redundant, the better source is already cited: ${dropped}`);
console.log(`    kept    — a vendor cited AS industry guidance, or experiential: ${kept}`);
console.log(`    vendor brackets seen: ${i} (want ${B.length})`);
if (i !== B.length) problems.push(`bracket count ${i}, expected ${B.length}`);
for (let k = 0; k < B.length; k++) {
  const [kind, repl, ctx] = B[k];
  const want = kind === 'keep' ? ctx : ctx + ' ' + repl;
  if (!body.includes(want)) problems.push(`decision ${k + 1} (${kind}) context missing: ${JSON.stringify(ctx.slice(0, 40))}`);
}

/* ── 2. de-link the surviving vendor sources — the name carries the argument, the link does not ── */
console.log('\n  SOURCES DE-LINK (name kept, URL removed)');
const ENTRIES = [
  ['Haven of Heat. Thermally Modified Wood vs Cedar Wood for Saunas. 2024. ', 'https://havenofheat.com/blogs/sauna-guides/thermally-modified-wood-vs-cedar-wood-which-is-better-for-your-sauna-and-why'],
  ['Eden Hut. Thermowood vs Cedar. 2026. ', 'https://www.edenhut.co.uk/blog-posts/thermowood-vs-cedar'],
  ['Pro Saunas. Thermally Modified Wood Benefits. 2025. ', 'https://prosaunas.com/thermally-modified-wood-benefit/'],
  ['High Tech Health International. Comparing Sauna Wood Types. 2025. ', 'https://www.hightechhealth.com/sauna-wood/'],
  ['Peak Primal Wellness. Best Wood for a Sauna. 2026. ', 'https://peakprimalwellness.com/blogs/wellness/best-wood-for-sauna'],
  ['Peak Primal Wellness. Cedar Sauna: Why Western Red Cedar Is the Top Choice. 2026. ', 'https://peakprimalwellness.com/blogs/wellness/cedar-sauna'],
];
let delinked = 0;
for (const [label, url] of ENTRIES) {
  const n = body.split(label + url).length - 1;
  console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label.slice(0, 52)}`);
  if (n !== 1) { problems.push(`source entry ${label.slice(0, 30)}`); continue; }
  body = body.replace(label + url, label + 'Sauna retailer guidance; link withheld.');
  delinked++;
}

/* ── 3. our own catalogue, which no competitor blog can produce ── */
const ANCHOR = '<h2 id="h.6pq1fj3pjnub">Comparison Matrix: Durability vs. Maintenance Profiles</h2>';
const anchorPresent = body.includes(ANCHOR);
const ALT = body.match(/<h2[^>]*>Comparison Matrix[^<]*<\/h2>/);
const useAnchor = anchorPresent ? ANCHOR : (ALT ? ALT[0] : null);
if (!useAnchor) problems.push('anchor for the catalogue paragraph not found');
else {
  const para = '<h3>What Is Actually Sold: Our Own Catalogue</h3>\n<p>Published species data is about wood. It says nothing about what home-sauna buyers are actually offered. Of the 672 products in the InHouse Wellness catalogue, <strong>179 publish a wood species</strong>, and among those 179 the split is <strong>Hemlock 112, Cedar 51, Spruce 12, Thermowood 4</strong>. That is a distribution across the products that name a species — not across the whole catalogue, and not across the market. It is worth stating because it shows where the industry has actually settled: hemlock leads on volume while cedar carries the reputation, and thermally modified wood, whatever its engineering case, is still a rounding error on the shelf.</p>\n';
  body = body.replace(useAnchor, para + useAnchor);
}

assertWellFormed(body, HANDLE);

const checks = [
  ['havenofheat.com', false], ['prosaunas.com', false], ['edenhut.co.uk', false],
  ['hightechhealth.com', false], ['peakprimalwellness.com', false],
  ['Sauna retailer guidance; link withheld.', true],
  ['Haven of Heat', true], ['Peak Primal Wellness', true],
  ['179 publish a wood species', true], ['Hemlock 112, Cedar 51, Spruce 12, Thermowood 4', true],
  ['not across the whole catalogue', true],
  ['reddit.com', true],   // the Reddit thread is cited AS a user report and keeps its link
];
const bad = checks.filter(([k, w]) => body.includes(k) !== w);
console.log(`\n  vendor URLs removed: ${delinked}/6`);
console.log(`  pre-write checks: ${checks.length - bad.length}/${checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);   /* fail-ok: bad.length refuses with exit(1) at the gate below */
if (bad.length || problems.length || delinked !== 6) {
  console.log('\n  PROBLEMS:'); [...problems, ...bad.map((b) => `check ${b[0]}`)].forEach((p) => console.log('    -', p));
  console.log('  refusing'); process.exit(1);
}

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('wood-vendors', [{ id: art.id, handle: HANDLE, before: art.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: art.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: art.id, handle: HANDLE, field: 'body', old: '31 vendor citation brackets, 12 of them on wood science the USDA source already covers; 6 competitor URLs live as bare text; no catalogue data', new: '12 redundant vendor citations re-pointed to USDA/BioResources; 19 kept as industry guidance with names and no links; our own 179-product species distribution added with its population stated', note: 'the Venice split applied to vendor citations' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, w] of checks) {
  const h = b.includes(k);
  console.log(`    ${h === w ? 'ok  ' : 'FAIL'} ${String(h).padEnd(5)} ${k.slice(0, 46)}`);
  if (h !== w) process.exitCode = 1;
}
