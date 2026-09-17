/* Round 15 citation pass, article 2 of 5 — benefits-of-cold-plunge-and-sauna. --dry-run default.
 * Approved 16 Sep 2026: groups 1 and 2, plus the Šrámek correction and the Cleveland Clinic cut.
 *
 *   node scripts/apply/fix-coldplunge-citations.mjs [--apply]
 *
 * VARIANT 7 was the visible half. Three of the four wrong destinations ALSO carry wrong text:
 * wrong year on Bleakley, wrong author/title/journal on Huttunen, wrong journal/year on Leeder.
 *
 * Every replacement identifier was resolved through the PubMed API before it was written here,
 * not after. The Šrámek DOI was resolved over HTTP as well (Springer, 200).
 *
 * Internal links are NOT touched: they belong to the broken-link pass.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'benefits-of-cold-plunge-and-sauna';
const NB = '\u00A0';   // the one-char anchors in this article use U+00A0, not U+0020
const li = (text, url) => `<li>\n<p>${text}<a href="${url}">${NB}</a><a href="${url}">${url}</a></p>\n</li>`;

const EDITS = [
  ['G1 Bleakley — wrong year AND wrong paper',
    '<li>\n<p>Bleakley, C. et al. "Cold-water immersion (cryotherapy) for preventing and treating muscle soreness after exercise." Cochrane Database of Systematic Reviews, 2015.<a href="https://pubmed.ncbi.nlm.nih.gov/25943635/">\u00A0</a><a href="https://pubmed.ncbi.nlm.nih.gov/25943635/">https://pubmed.ncbi.nlm.nih.gov/25943635/</a></p>\n</li>',
    li('Bleakley, C. et al. "Cold-water immersion (cryotherapy) for preventing and treating muscle soreness after exercise." Cochrane Database of Systematic Reviews, 2012. 17 small trials, 366 participants, study quality low.', 'https://pubmed.ncbi.nlm.nih.gov/22336838/')],

  ['G1 Huttunen — wrong author, title, journal, year',
    '<li>\n<p>Huttunen, P. et al. "Winter swimming improves general well-being." European Journal of Applied Physiology, 2007.<a href="https://pubmed.ncbi.nlm.nih.gov/17993252/">\u00A0</a><a href="https://pubmed.ncbi.nlm.nih.gov/17993252/">https://pubmed.ncbi.nlm.nih.gov/17993252/</a></p>\n</li>',
    li('Huttunen, P., Kokko, L., Ylijukuri, V. "Winter swimming improves general well-being." International Journal of Circumpolar Health, 2004. Mood questionnaires before and after a four-month winter swimming season.', 'https://pubmed.ncbi.nlm.nih.gov/15253480/')],

  ['G1 Leeder — wrong journal and year',
    '<li>\n<p>Leeder, J. et al. "Cold water immersion and recovery from strenuous exercise." Sports Medicine, 2014.<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4049052/">\u00A0</a><a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4049052/">https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4049052/</a></p>\n</li>',
    li('Leeder, J. et al. "Cold water immersion and recovery from strenuous exercise: a meta-analysis." British Journal of Sports Medicine, 2012.', 'https://pubmed.ncbi.nlm.nih.gov/21947816/')],

  ['G1 Laukkanen Mayo — text correct, URL wrong',
    '<li>\n<p>Laukkanen, J.A. et al. "Cardiovascular and Other Health Benefits of Sauna Bathing: A Review of the Evidence." Mayo Clinic Proceedings, 2018.<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5941775/">\u00A0</a><a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5941775/">https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5941775/</a></p>\n</li>',
    li('Laukkanen, J.A., Laukkanen, T., Kunutsor, S.K. "Cardiovascular and Other Health Benefits of Sauna Bathing: A Review of the Evidence." Mayo Clinic Proceedings, 2018.', 'https://pubmed.ncbi.nlm.nih.gov/30077204/')],

  ['G2 Harvard — dead link, live equivalent from the same publisher',
    '<li>\n<p>Harvard Health Publishing. "Are saunas safe?" 2018.<a href="https://www.health.harvard.edu/blog/are-saunas-safe-2018070514150">\u00A0</a><a href="https://www.health.harvard.edu/blog/are-saunas-safe-2018070514150">https://www.health.harvard.edu/blog/are-saunas-safe-2018070514150</a></p>\n</li>',
    li('Harvard Health Publishing. "Sauna health benefits: Are saunas healthy or harmful?"', 'https://www.health.harvard.edu/staying-healthy/saunas-and-your-health')],

  ['G2 CDC — dead link, live equivalent from the same agency',
    '<li>\n<p>Centers for Disease Control and Prevention. Cold Safety Guidance.<a href="https://www.cdc.gov/disasters/winter/staysafe/coldsafety.html">\u00A0</a><a href="https://www.cdc.gov/disasters/winter/staysafe/coldsafety.html">https://www.cdc.gov/disasters/winter/staysafe/coldsafety.html</a></p>\n</li>',
    li('Centers for Disease Control and Prevention. "Winter Weather: Before, During, and After."', 'https://www.cdc.gov/winter-weather/about/index.html')],

  ['G2 BBC — dead, nothing rests on it, removed',
    '<li>\n<p>BBC Future. "Are ice baths good for you?" 2023.<a href="https://www.bbc.com/future/article/20231219-are-ice-baths-good-for-you">\u00A0</a><a href="https://www.bbc.com/future/article/20231219-are-ice-baths-good-for-you">https://www.bbc.com/future/article/20231219-are-ice-baths-good-for-you</a></p>\n</li>',
    ''],

  /* the quantitative claim: right subject, wrong source, wrong number */
  ['ŠRÁMEK — the figure with its conditions',
    'One study found cold exposure increased norepinephrine by roughly 200–300% [European Journal of Applied Physiology, 2007].',
    'In one controlled study, an hour of head-out immersion at 14°C raised plasma noradrenaline by 530% in young men, against no change at thermoneutral temperature [Šrámek et al., European Journal of Applied Physiology, 2000]. An hour at 14°C is not a two-minute plunge, and the size of the response depends on how cold the water is and how long you stay in it.'],

  /* the SAME figure restated in the TL;DR — found by the guard, not by the enumeration */
  ['ŠRÁMEK — the TL;DR restatement of the same figure',
    'Cold exposure may increase norepinephrine by roughly 200–300%, contributing to alertness and mood effects [European Journal of Applied Physiology, 2007]',
    'Cold exposure raises noradrenaline sharply, by 530% in one controlled study of head-out immersion at 14°C for an hour [Šrámek et al., 2000]'],

  /* the myth-correction keeps its structure; the unsupportable consequence goes */
  ['CLEVELAND CLINIC — claim cut with its citation, correction preserved',
    'Beyond the studied protocol ranges, you encounter diminishing returns and increased risk — including hypothermia (cold) and heat exhaustion (sauna) [Cleveland Clinic, 2022].',
    'The protocols that have been studied run to specific durations — sauna sessions of roughly 10 to 20 minutes, cold immersion of a few minutes — and longer exposures have not been tested. Prolonged heat and cold carry their own hazards, hypothermia and heat exhaustion among them.'],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!a) throw new Error('article not found');

let body = a.body, fail = 0;
for (const [label, from, to] of EDITS) {
  const n = body.split(from).length - 1;
  console.log(`  ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}
if (fail) { console.log(`\n  refusing: ${fail} target(s) not matched once`); process.exit(1); }

/* add Šrámek to the source list, next to the paper it replaces as an authority */
const HUTT = 'https://pubmed.ncbi.nlm.nih.gov/15253480/</a></p>\n</li>';
if (body.split(HUTT).length - 1 !== 1) { console.log('  FAIL anchor for the Šrámek source entry'); process.exit(1); }
body = body.replace(HUTT, HUTT + '\n' + li('Šrámek, P. et al. "Human physiological responses to immersion into water of different temperatures." European Journal of Applied Physiology, 2000. Head-out immersion, one hour, young men; noradrenaline +530% at 14°C.', 'https://pubmed.ncbi.nlm.nih.gov/10751106/'));
assertWellFormed(body, HANDLE);

const dead = ['25943635', '17993252', 'PMC4049052', 'PMC5941775', 'are-saunas-safe-2018070514150', 'disasters/winter', 'bbc.com'];
const still = dead.filter((d) => body.includes(d));
console.log(`\n  edits: ${EDITS.length} + 1 source added   dead identifiers remaining: ${still.length ? still.join(', ') : 'none'}`);
console.log(`  "200–300%" present: ${body.includes('200–300%')} (want false)   Šrámek cited: ${body.includes('Šrámek')} (want true)`);
if (still.length || body.includes('200–300%')) { console.log('  refusing'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('coldplunge-citations', [{ id: a.id, handle: HANDLE, before: a.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: a.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: a.id, handle: HANDLE, field: 'body', old: '4 wrong destinations, 3 wrong citation texts, 3 dead externals, 1 unsupportable claim', new: 'identifiers resolved via PubMed; Harvard and CDC replaced; BBC removed; Šrámek with conditions; diminishing-returns claim cut', note: 'Round 15 citation pass 2/5' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, want] of [['25943635', false], ['17993252', false], ['PMC4049052', false], ['PMC5941775', false], ['22336838', true], ['15253480', true], ['21947816', true], ['30077204', true], ['10751106', true], ['200–300%', false], ['diminishing returns', false], ['bbc.com', false]]) {
  const has = b.includes(k);
  console.log(`    ${has === want ? 'ok  ' : 'FAIL'} ${String(has).padEnd(5)} ${k}`);
  if (has !== want) process.exitCode = 1;
}
