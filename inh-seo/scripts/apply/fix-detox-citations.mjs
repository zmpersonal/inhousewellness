/* Round 15 citation pass, article 3 of 5 — sauna-benefits-detoxification. --dry-run default.
 * Approved 16 Sep 2026. THE SHUFFLED GENUIS SET: three citations to one author's related papers,
 * each pointing at a different one of the others, with the phthalate PMID one digit from the
 * real BPA paper. Composed, not resolved.
 *
 *   node scripts/apply/fix-detox-citations.mjs [--apply]
 *
 * The one-character anchors in this article are U+00A0, confirmed by code point before writing.
 * Internal links belong to the broken-link pass. The 34 remaining database-as-source labels are
 * a style decision, reported separately, not touched here.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'sauna-benefits-detoxification';
const NB = ' ';
const li = (text, url) => `<li>\n<p>${text} —<a href="${url}">${NB}</a><a href="${url}">${url}</a></p>\n</li>`;
const old = (text, url) => `<li>\n<p>${text} —<a href="${url}">${NB}</a><a href="${url}">${url}</a></p>\n</li>`;

const P = {
  sears: 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3312275/',
  metals: 'https://pubmed.ncbi.nlm.nih.gov/21057782/',
  phthOld: 'https://pubmed.ncbi.nlm.nih.gov/22253638/',
  phth: 'https://pubmed.ncbi.nlm.nih.gov/23213291/',
  bpa: 'https://pubmed.ncbi.nlm.nih.gov/22253637/',
  crinnion: 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5941775/',
  kuan: 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8998800/',
  bmc: 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6262976/',
  ccOld: 'https://www.clevelandclinic.org/health/articles/sauna-benefits',
  cc: 'https://health.clevelandclinic.org/sauna-benefits',
  mayoSaunaOld: 'https://www.mayoclinic.org/healthy-lifestyle/consumer-health/in-depth/sauna/art-20048223',
  mayoSauna: 'https://www.mayoclinic.org/healthy-lifestyle/consumer-health/expert-answers/infrared-sauna/faq-20057954',
  mayoDetox: 'https://www.mayoclinic.org/healthy-lifestyle/consumer-health/in-depth/detox/art-20047622',
};

const EDITS = [
  ['A1 PMC3312275 is Sears, not Genuis',
    old('Genuis SJ et al., "Blood, Urine, and Sweat (BUS) Study," 2012, PMC3312275', P.sears),
    li('Sears ME, Kerr KJ, Bray RI. "Arsenic, Cadmium, Lead, and Mercury in Sweat: A Systematic Review." Journal of Environmental and Public Health, 2012', P.sears)],

  ['A2 21057782 is the METALS BUS study, not BPA',
    old('BPA in sweat study, 2011, PubMed 21057782', P.metals),
    li('Genuis SJ et al. "Blood, urine, and sweat (BUS) study: monitoring and elimination of bioaccumulated toxic elements." Archives of Environmental Contamination and Toxicology, 2011. 20 participants', P.metals)],

  ['A3 phthalates pointed at an ochratoxin paper; one digit from the BPA PMID',
    old('Phthalates in sweat study, 2012, PubMed 22253638', P.phthOld),
    li('Genuis SJ et al. "Human elimination of phthalate compounds: blood, urine, and sweat (BUS) study." ScientificWorldJournal, 2012. 20 participants', P.phth)],

  ['C Crinnion removed — nothing depends on it',
    old('Crinnion W., sauna/sweat review, 2011, PMC5941775', P.crinnion) + '\n',
    ''],

  ['B1 a study described as a review',
    old('Sweat excretion review, 2022, PMC8998800', P.kuan),
    li('Kuan W-H et al. "Excretion of Ni, Pb, Cu, As, and Hg in Sweat under Two Sweating Conditions." International Journal of Environmental Research and Public Health, 2022', P.kuan)],

  ['B2 a cohort described as a review',
    old('Sauna health review, 2018, PMC6262976', P.bmc),
    li('Laukkanen T et al. "Sauna bathing is associated with reduced cardiovascular mortality and improves risk prediction in men and women." BMC Medicine, 2018. Prospective cohort, 1,688 participants', P.bmc)],

  ['E1 Cleveland Clinic dead → live equivalent',
    old('Cleveland Clinic, Sauna benefits', P.ccOld),
    li('Cleveland Clinic. "Sauna Benefits"', P.cc)],

  ['E2 Mayo sauna dead → live equivalent',
    old('Mayo Clinic, Sauna guidance', P.mayoSaunaOld),
    li('Mayo Clinic. "Do infrared saunas have any health benefits?"', P.mayoSauna)],

  ['E3 Mayo detox dead, no equivalent published → removed',
    old('Mayo Clinic, Detox diets/cleansing, 2022', P.mayoDetox) + '\n',
    ''],

  /* in-text: databases named as sources, on the shuffled papers */
  ['D1 in-text: metals + BPA + phthalates sentence',
    'in sweat—"detected," not "flushed out completely" (Genuis et al., 2012; PubMed, 2011; PubMed, 2012)',
    'in sweat—"detected," not "flushed out completely" (Genuis et al., 2011, metals; Genuis et al., 2012, BPA; Genuis et al., 2012, phthalates)'],
  ['D2 in-text: BPA and phthalates detected',
    'have also been detected in sweat in small studies (PubMed, 2011; PubMed, 2012)',
    'have also been detected in sweat in small studies (Genuis et al., 2012, BPA; Genuis et al., 2012, phthalates)'],
  ['D4 in-text: endocrine disruptors sentence — the third PubMed label',
    'as a blanket statement (Genuis et al., 2012; PubMed, 2012)',
    'as a blanket statement (Genuis et al., 2012, BPA; Genuis et al., 2012, phthalates)'],
  ['D3 in-text: metals and plastic chemicals',
    'have been detected in sweat (Genuis et al., 2012; PubMed, 2011)',
    'have been detected in sweat (Genuis et al., 2011, metals; Genuis et al., 2012, BPA)'],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!a) throw new Error('not found');

let body = a.body, fail = 0;
for (const [label, from, to] of EDITS) {
  const n = body.split(from).length - 1;
  console.log(`  ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}
if (fail) { console.log(`\n  refusing: ${fail} target(s) not matched once`); process.exit(1); }

/* add the BPA paper, which had no entry at all */
const ANCHOR = li('Genuis SJ et al. "Human elimination of phthalate compounds: blood, urine, and sweat (BUS) study." ScientificWorldJournal, 2012. 20 participants', P.phth);
if (body.split(ANCHOR).length - 1 !== 1) { console.log('  FAIL anchor for the new BPA entry'); process.exit(1); }
body = body.replace(ANCHOR, ANCHOR + '\n' + li('Genuis SJ et al. "Human excretion of bisphenol A: blood, urine, and sweat (BUS) study." Journal of Environmental and Public Health, 2012. BPA found in sweat in 16 of 20 participants', P.bpa));

/* in-text Crinnion tags: drop the name, keep the co-citations */
const CRIN = [
  ['(Crinnion, 2011; Cleveland Clinic)', '(Cleveland Clinic)'],
  ['(Crinnion, 2011; PMC, 2018; Cleveland Clinic)', '(PMC, 2018; Cleveland Clinic)'],
  ['(Genuis et al., 2012; Crinnion, 2011)', '(Genuis et al., 2011, metals)'],
  ['(Crinnion, 2011; PMC, 2018)', '(PMC, 2018)'],
  ['(Crinnion, 2011)', '(PMC, 2018)'],
  ['(Cleveland Clinic; Crinnion, 2011; PMC, 2018)', '(Cleveland Clinic; PMC, 2018)'],
];
let crinFixed = 0;
for (const [from, to] of CRIN) { const n = body.split(from).length - 1; if (n) { body = body.split(from).join(to); crinFixed += n; } }
const crinLeft = (body.match(/Crinnion/g) || []).length;
console.log(`\n  Crinnion in-text tags rewritten: ${crinFixed}   mentions remaining: ${crinLeft} (want 0)`);
assertWellFormed(body, HANDLE);

const checks = [['22253638', false], ['PMC5941775', false], ['clevelandclinic.org/health/articles', false], ['in-depth/sauna/art-20048223', false], ['in-depth/detox/art-20047622', false],
  ['23213291', true], ['22253637', true], ['Sears ME', true], ['PubMed, 2011', false], ['PubMed, 2012', false]];
const bad = checks.filter(([k, want]) => body.includes(k) !== want);
console.log(`  pre-write checks: ${checks.length - bad.length}/${checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);
if (bad.length || crinLeft) { console.log('  refusing'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('detox-citations', [{ id: a.id, handle: HANDLE, before: a.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: a.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: a.id, handle: HANDLE, field: 'body', old: 'shuffled Genuis citations, Crinnion, 2 loose types, 3 dead externals, 6 database labels', new: 'resolved identifiers, Crinnion dropped, types corrected, 2 replaced 1 removed', note: 'Round 15 citation pass 3/5' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, want] of [...checks, ['Crinnion', false], ['health.clevelandclinic.org/sauna-benefits', true], ['infrared-sauna/faq-20057954', true]]) {
  const has = b.includes(k);
  console.log(`    ${has === want ? 'ok  ' : 'FAIL'} ${String(has).padEnd(5)} ${k}`);
  if (has !== want) process.exitCode = 1;
}
