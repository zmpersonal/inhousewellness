/* Round 15 citation pass, article 1 of 5 — chromotherapy-vs-no-chromotherapy-buyers-guide.
 * --dry-run default. Proposal approved 16 Sep 2026; see content/fixes/chromotherapy-citation-pass.md
 *
 *   node scripts/apply/fix-chromotherapy-citations.mjs [--apply]
 *
 * The article is careful about its own subject and careless about the thing it compares against.
 * Every edit here is about SAUNA HEAT, the contrast term. No chromotherapy claim is touched, and
 * the article's recommendation does not change.
 *
 * The cited paper is Hussain J & Cohen M, "Clinical Effects of Regular Dry Sauna Bathing: A
 * Systematic Review", Evid Based Complement Alternat Med 2018 (PMID 29849692) — NOT Laukkanen,
 * and its own conclusion is that the evidence "is not well established".
 *
 * Every target asserts EXACTLY ONE match. Zero is a FAILURE, not a skip.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'chromotherapy-vs-no-chromotherapy-buyers-guide';
const FREQ = '/blogs/saunas/how-often-should-you-use-sauna';
const L15 = '(Laukkanen et al., 2015)';
const HC = '(Hussain &amp; Cohen, 2018)';
const BOTH = '(Laukkanen et al., 2015; Hussain &amp; Cohen, 2018)';

const EDITS = [
  /* ── the six ASSERTS, all about sauna heat ── */
  ['ASSERT 1', 'want only clinically proven heat benefits',
    'want only the heat benefits, where the evidence is strongest'],
  ['ASSERT 2', 'heat-only sauna (proven cardiovascular and relaxation benefits) serve different purposes',
    'heat-only sauna (the strongest evidence base of the three, and still largely observational) serve different purposes'],
  ['ASSERT 3 (anchor)', '>proven cardiovascular and metabolic benefits</a> that come from sauna heat exposure alone',
    '>cardiovascular associations reported for sauna heat</a> exposure alone'],
  ['ASSERT 4', 'drawn to the simplicity and proven benefits of traditional sauna bathing',
    'drawn to the simplicity of traditional sauna bathing and the evidence behind heat itself'],
  ['ASSERT 5', 'Research shows that regular dry or infrared sauna sessions deliver meaningful health outcomes through heat exposure, independent of chromotherapy (Laukkanen et al., 2018).',
    `Cohort research associates regular sauna use with lower cardiovascular mortality, and what evidence exists for sauna health outcomes concerns heat rather than lighting ${BOTH.slice(0, -1)}).`],
  ['ASSERT 6 / limitation', 'Sauna therapy trials show pain reductions tied to regular heat exposure, not chromotherapy (Laukkanen et al., 2018).',
    `A systematic review of dry sauna bathing reports pain and quality-of-life outcomes across mostly small studies, and attributes them to heat rather than lighting ${HC}.`],

  /* ── contradicted evidence grade ── */
  ['CONTRADICTED', 'to save money — Evidence: High for heat benefits (Laukkanen et al., 2018)',
    `to save money — Evidence: strongest of the three options here, and still mostly observational ${BOTH}`],

  /* ── three doses cited to a paper that calls dose an open question ── */
  ['FREQ 1', 'Session context: Infrared sauna general-use guidance often suggests 20–30 minute sessions, one to four times per week, aligning your color exposure with standard sauna safety limits (Laukkanen et al., 2018).',
    `Session context: your colour exposure is bounded by the session itself, so frequency and duration are the sauna’s question rather than the lighting’s. The evidence on that is covered in <a href="${FREQ}">how often should you use a sauna</a>.`],
  ['FREQ 2', 'Many wellness guides suggest 20–30 minute sessions, one to four times weekly for infrared saunas (Laukkanen et al., 2018).',
    `Session length and frequency follow standard sauna guidance rather than anything specific to the lighting. See <a href="${FREQ}">how often should you use a sauna</a> for what the cohort evidence supports.`],
  ['FREQ 3', 'Most studies and wellness guides suggest moderate session lengths (typically 15–30 minutes) to avoid overheating (Laukkanen et al., 2018).',
    `Session length should follow ordinary sauna guidance, which is set by the heat rather than by the lighting. See <a href="${FREQ}">how often should you use a sauna</a>.`],

  /* ── unfinished work ── */
  ['PLACEHOLDERS', 'Key Citations: (RLT wavelengths); (chromotherapy vs RLT distinction); Laukkanen et al., 2018 (sauna heat evidence)',
    'Key citations: Hussain &amp; Cohen, 2018 (systematic review of dry sauna bathing); Laukkanen et al., 2015 (Finnish cohort)'],

  /* ── standards named, not sourced to lighting vendors ── */
  ['IEC 1', 'Additional certification notes: Sauna manufacturers and third-party lighting suppliers emphasize the importance of ETL, UL, CSA, or IEC 60335-2-53 compliance for fixtures exposed to heat and moisture (Radiant Health Saunas, PDF; China Beauty Lighting, 2025).',
    'Additional certification notes: IEC 60335-2-53 covers electrical safety requirements for sauna heating appliances, and ETL, UL and CSA listings show a product has been tested against the applicable North American standards. Check the current edition, and confirm the listing covers the lighting as installed.'],
  ['IEC 2', 'Some RLT safety standards like IEC 62471 (photobiological safety of lamps) and RoHS (restriction of hazardous substances) also apply to well-designed light therapy devices, highlighting the value of comprehensive testing (RedDot LED, 2025).',
    'IEC 62471 governs the photobiological safety of lamps and lamp systems, and RoHS restricts certain hazardous substances. Both apply to light therapy devices; check the current edition of each.'],

  /* ── source list ── */
  ['SOURCE ENTRY', 'Laukkanen et al. – "Clinical Effects of Regular Dry Sauna Bathing: A Systematic Review" (2018) –',
    'Hussain J, Cohen M – "Clinical Effects of Regular Dry Sauna Bathing: A Systematic Review" – Evidence-Based Complementary and Alternative Medicine, 2018. 40 studies, 13 randomised, most under 40 participants; the authors conclude the evidence is not well established –'],

  /* ── the remaining inline attributions, each to whichever source supports it ── */
  ['ATTRIB 1', 'with or without any lighting features (Laukkanen et al., 2018).', `with or without any lighting features ${HC}.`],
  ['ATTRIB 4', 'clinical trials that did not involve chromotherapy at all (Laukkanen et al., 2018).', `clinical trials that did not involve chromotherapy at all ${BOTH}.`],
  ['ATTRIB 6', 'pain relief, and better functional outcomes (Laukkanen et al., 2018)', `pain relief, and better functional outcomes ${BOTH}`],
  ['ATTRIB 7', 'the feature is optional for health benefits (Laukkanen et al., 2018).', `the feature is optional for health benefits ${L15}.`],
  ['ATTRIB 8', 'driven by heat, not colored light (Laukkanen et al., 2018).', `driven by heat, not colored light ${HC}.`],
  ['ATTRIB 9', 'most extensive evidence base for health benefits (Laukkanen et al., 2018).', `most extensive evidence base for health benefits ${HC}.`],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!a) throw new Error('article not found');

let body = a.body;
let fail = 0;
for (const [label, from, to] of EDITS) {
  const n = body.split(from).length - 1;
  console.log(`  ${n === 1 ? 'ok  ' : 'FAIL'} ${String(n)}×  ${label}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}
if (fail) { console.log(`\n  refusing: ${fail} target(s) did not match exactly once`); process.exit(1); }
assertWellFormed(body, HANDLE);

const left = (body.match(/\(Laukkanen et al\., 2018\)/g) || []).length;
const freqWords = /one to four times (per week|weekly)|typically 15–30 minutes/.test(body);
console.log(`\n  edits: ${EDITS.length}   "(Laukkanen et al., 2018)" remaining: ${left} (want 0)   states a frequency: ${freqWords} (want false)`);
console.log(`  links to the frequency article: ${(body.split(FREQ).length - 1)} (want 3)`);
if (left !== 0 || freqWords) { console.log('  refusing'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('chromotherapy-citations', [{ id: a.id, handle: HANDLE, before: a.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`,
  { id: a.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: a.id, handle: HANDLE, field: 'body', old: '(Laukkanen et al., 2018) ×12 + 6 asserts + 3 doses + placeholders + vendor-sourced standards', new: 'Hussain & Cohen / Laukkanen 2015 as applicable; asserts hedged; doses deferred', note: 'Round 15 citation pass 1/5' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log(`\n  re-read: "(Laukkanen et al., 2018)" ${(b.match(/\(Laukkanen et al\., 2018\)/g) || []).length} (want 0)`);
console.log(`  re-read: frequency links ${(b.split(FREQ).length - 1)} (want 3)`);
console.log(`  re-read: states a frequency ${/one to four times (per week|weekly)|typically 15–30 minutes/.test(b)} (want false)`);
console.log(`  re-read: vendor standard sources ${/Radiant Health Saunas|China Beauty Lighting|RedDot LED/.test(b)} (want false)`);
console.log(`  re-read: empty citation parens ${/Key Citations: \(/.test(b)} (want false)`);
