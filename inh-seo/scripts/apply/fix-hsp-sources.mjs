/* heat-shock-proteins-neurodegeneration-cognitive-aging — link and correct the source list.
 * --dry-run default.   node scripts/apply/fix-hsp-sources.mjs [--apply]
 *
 * OUTCOME 1: real claims, real sources, never linked. Every PMC id in the Sources list was
 * resolved through the NCBI converter and then PubMed; all ten are real papers on the subject.
 * Rule 4 is clean — 13 unhedged effect sentences of 51, none asserting a benefit to the reader.
 *
 * FIVE fixes applied. The sixth is NOT applied and the reason is in the report: "(PMC, 2025)"
 * keys two different 2025 papers, and 17 of its 42 occurrences cannot be assigned to either by
 * topic. An honest blank beats a guess, so the inline key is left alone and reported.
 *
 * Every source line below was checked against PubMed metadata on 16 September 2026.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'heat-shock-proteins-neurodegeneration-cognitive-aging';
const li = (t) => `<li>\n<p>${t}</p>\n</li>`;
const a = (u, t) => `<a href="${u}" rel="nofollow noopener noreferrer" target="_blank">${t}</a>`;
const P = (id) => `https://pmc.ncbi.nlm.nih.gov/articles/${id}/`;

const SOURCES = [
  ["Hyperthermia and targeting heat shock proteins in neurological disorders – Review – 2025 – PMC 11832498",
   `Smadja DM, Abreu MM. "Hyperthermia and targeting heat shock proteins: innovative approaches for neurodegenerative disorders and Long COVID." <em>Frontiers in Neuroscience</em>, 2025. Review. ${a(P("PMC11832498"), "PMC11832498")}`],

  ["Hsp multichaperone complex buffers pathologically modified Tau – Study – 2022 – Nature Communications",
   `Moll A, Ramirez LM, Ninov M, et al. "Hsp multichaperone complex buffers pathologically modified Tau." <em>Nature Communications</em>, 2022. In vitro study of the human Hsp70/Hsp90 machinery. ${a(P("PMC9237115"), "PMC9237115")}`],

  ["Heat Shock Protein 70 reduces α-Synuclein-induced toxicity in a rat model of Parkinson's disease – Study – 2013 – PMC 6493192",
   `Moloney TC, Hyland R, O&#39;Toole D, et al. "Heat shock protein 70 reduces α-synuclein-induced <strong>predegenerative neuronal dystrophy</strong> in the α-synuclein viral gene transfer rat model of Parkinson&#39;s disease." <em>CNS Neuroscience &amp; Therapeutics</em>, 2013. Rats; the study reports early dystrophy <strong>without</strong> overt nigrostriatal neurodegeneration. ${a(P("PMC6493192"), "PMC6493192")}`],

  ["Disrupted HSF1 regulation in normal and exceptional brain aging – Study – 2023 – PMC 10794279",
   `Trivedi R, Knopf B, Rakoczy S, et al. "Disrupted HSF1 regulation in normal and exceptional brain aging." <em>Biogerontology</em>, 2023. <strong>Mice</strong> — normally aged wild-type and long-lived Ames Dwarf. ${a(P("PMC10794279"), "PMC10794279")}`],

  ["Role of a heat shock transcription factor and the heat shock response in synaptic protection – Review – 2021 – PMC 8305005",
   `Zatsepina OG, Evgen&#39;ev MB, Garbuz DG. "Role of a Heat Shock Transcription Factor and the Major Heat Shock Protein Hsp70 in Memory Formation and Neuroprotection." <em>Cells</em>, 2021. Review. ${a(P("PMC8305005"), "PMC8305005")}`],

  ["HSP70 and HSP90 in neurodegenerative diseases – Review – 2019 – PMC 7336893",
   `Gupta A, Bansal A, Hashimoto-Torii K. "HSP70 and HSP90 in neurodegenerative diseases." <em>Neuroscience Letters</em>, 2019. Review. ${a(P("PMC7336893"), "PMC7336893")}`],

  ["Stressing Out Hsp90 in Neurotoxic Proteinopathies – Review – 2005 – PMC 4995127",
   `Inda C, Bolaender A, Wang T, et al. "Stressing Out Hsp90 in Neurotoxic Proteinopathies." <em>Current Topics in Medicinal Chemistry</em>, <strong>2016</strong>. Review. ${a(P("PMC4995127"), "PMC4995127")}`],

  ["Sauna &amp; Heat Exposure's Impact on Mental &amp; Physical Health – Educational Review – 2024 – Psychiatry &amp; Psychotherapy Podcast",
   `Psychiatry &amp; Psychotherapy Podcast. "Sauna &amp; Heat Exposure&#39;s Impact on Mental &amp; Physical Health", 2024. <strong>A podcast episode, not a peer-reviewed review</strong> — cited here for summary and framing only, never as evidence for a claim.`],

  ["Closest horizons of Hsp70 engagement to manage neurodegenerative diseases – Review – 2023 – Frontiers in Molecular Neuroscience",
   `Venediktov AA, Bushueva OY, Kudryavtseva VA, et al. "Closest horizons of Hsp70 engagement to manage neurodegeneration." <em>Frontiers in Molecular Neuroscience</em>, 2023. Review. ${a(P("PMC10546621"), "PMC10546621")}`],

  ["Heat shock protein 70 in Alzheimer's disease and other dementias – Review – 2025 – PMC 11864251",
   `Valle-Medina A, Calzada-Mendoza CC, Ocharan-Hernández ME, et al. "Heat shock protein 70 in Alzheimer&#39;s disease and other dementias: a possible alternative therapeutic." <em>Journal of Alzheimer&#39;s Disease Reports</em>, 2025. Review. ${a(P("PMC11864251"), "PMC11864251")}`],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const art = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!art) throw new Error('not found');
let body = art.body;
let fail = 0;

console.log('  SOURCE ENTRIES — linked and attributed from PubMed metadata');
for (const [from, to] of SOURCES) {
  const old = li(from);
  const n = body.split(old).length - 1;
  console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${from.slice(0, 56)}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(old, li(to));
}

/* the inline key that is simply WRONG. One source that year, so there is no ambiguity here. */
let keyFixed = 0;
for (const [f, t] of [['(PMC, 2005)', '(PMC, 2016)'], ['PMC, 2005;', 'PMC, 2016;'], ['; PMC, 2005', '; PMC, 2016']]) {
  const n = body.split(f).length - 1;
  if (n) { body = body.split(f).join(t); keyFixed += n; }
}
const left2005 = (body.match(/PMC,\s*2005/g) || []).length;
console.log(`\n  inline key "PMC, 2005" → "PMC, 2016": ${keyFixed} rewritten, ${left2005} remaining (want 0)`);

/* ── THE CLAIM. All SIX representations, species IN the sentence, never in a trailing caveat.
 *
 * The article described PMC10794279 as "a 2023 study examining human postmortem brain tissue"
 * comparing "older adults who maintained superior cognitive function". Per PubMed, Trivedi et al.,
 * Biogerontology 2023, assessed "normally aged wild type and long-lived Dwarf mice"; MeSH says
 * Mice, Animals. The design, the population and the outcome measure were all invented.
 *
 * The finding itself is real and stays. What goes is the human framing — and the paper's own term
 * "exceptional agers", which names a mouse genotype and reads as a human cohort in every context
 * this article uses it. A sentence saying "exceptional agers" with "(in mice)" appended can be
 * skimmed back into a claim about people; one that says "Dwarf mice" cannot. */
const CLAIM = [
  ['GLOSSARY entry',
   'Normal brain aging shows impaired HSF1 activation, reducing the capacity to induce protective HSPs under stress, while "exceptional agers" with preserved cognition maintain more robust HSF1 function (PMC, 2023; PMC, 2021).',
   'In mice, normal brain aging shows impaired HSF1 activation, reducing the capacity to induce protective HSPs under stress, while long-lived Dwarf mice retain more robust HSF1 function (PMC, 2023; PMC, 2021). The equivalent comparison has not been made in human brain tissue.'],

  ['COMPARISON-TABLE cell — the one most likely to be read alone',
   'Declines with aging; preserved in exceptional agers',
   'Declines with aging in mice; preserved in long-lived Dwarf mice'],

  ['BODY PARAGRAPH — the fabricated study design',
   'A 2023 study examining human postmortem brain tissue found that normal aging is associated with impaired activation of the heat shock axis, particularly dysregulation of HSF1. Older adult brains showed unfavorable changes in HSF1 protein levels, DNA binding capacity, and phosphorylation patterns compared to younger individuals. In contrast, brains from "exceptional agers"—older adults who maintained superior cognitive function—showed preserved HSF1 activation signatures more similar to younger brains (PMC, 2023).',
   'A 2023 study in mice found that normal aging is associated with impaired activation of the heat shock axis, particularly dysregulation of HSF1. Brains from normally aged wild-type mice showed unfavorable changes in HSF1 protein levels, DNA binding capacity and phosphorylation patterns. Long-lived Ames Dwarf mice — a genetic longevity model, not a cognitively assessed group — showed preserved HSF1 activation signatures by comparison (PMC, 2023). No equivalent study of human brain tissue is cited on this page, and the mouse result does not establish what happens in people.'],

  ['CONSEQUENCE sentence',
   'The preserved stress response in exceptional agers suggests that maintaining robust HSP induction may be a marker—and possibly a mechanism—of cognitive resilience during aging, though causality remains to be fully established (PMC, 2023).',
   'The preserved stress response in long-lived Dwarf mice raises the question of whether robust HSP induction is a marker — or a mechanism — of resilience during aging. Whether any of that applies to human cognitive aging is untested (PMC, 2023).'],

  ['MYTH correction',
   'Correction: Normal aging impairs HSF1 activation, but exceptional agers maintain more robust responses, and physiologic stressors may still induce HSPs. The decline is relative, not absolute.',
   'Correction: in mice, normal aging impairs HSF1 activation while long-lived Dwarf mice retain more robust responses, and physiologic stressors may still induce HSPs. The decline is relative, not absolute. The human version of this question has not been answered.'],

  ['KEY TAKEAWAY',
   'Normal aging impairs HSF1 activation, reducing stress-response capacity in the brain; exceptional agers maintain more robust HSP induction (PMC, 2023).',
   'In mice, normal aging impairs HSF1 activation and reduces stress-response capacity in the brain, while long-lived Dwarf mice retain more robust HSP induction (PMC, 2023). This has not been shown in humans.'],
];
console.log('\n  THE CLAIM — six representations, species in the sentence');
for (const [label, from, to] of CLAIM) {
  const n = body.split(from).length - 1;
  console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}

if (fail) { console.log(`\n  refusing: ${fail} target(s) not matched exactly once`); process.exit(1); }
assertWellFormed(body, HANDLE);

const checks = [
  ['<strong>2016</strong>', true], ['PMC, 2005', false],
  ['predegenerative neuronal dystrophy', true], ['<strong>without</strong> overt nigrostriatal', true],
  ['A podcast episode, not a peer-reviewed review', true],
  /* the term names a mouse genotype and must not survive anywhere in this article */
  ['exceptional ager', false], ['human postmortem brain tissue', false],
  ['older adults who maintained superior cognitive function', false],
  ['Ames Dwarf mice', true], ['Dwarf mice', true], ['not been shown in humans', true],
  ['PMC11832498', true], ['PMC9237115', true], ['PMC10546621', true], ['PMC11864251', true],
  ['Gupta A, Bansal A', true], ['Moll A, Ramirez LM', true], ['Smadja DM', true],
];
const bad = checks.filter(([k, w]) => body.includes(k) !== w);
const hrefs = (body.match(/href="https:\/\/pmc\.ncbi/g) || []).length;
console.log(`\n  PMC links added: ${hrefs} (want 9 — every source but the podcast, which has no paper)`);
console.log(`  pre-write checks: ${checks.length - bad.length}/${checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);
if (bad.length || hrefs !== 9 || left2005) { console.log('  refusing'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('hsp-sources', [{ id: art.id, handle: HANDLE, before: art.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: art.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({
  resource: art.id, handle: HANDLE, field: 'body',
  old: '10 unlinked sources keyed by database+year; "PMC, 2005" naming a 2016 paper; a podcast labelled Educational Review; a mouse study read as human; a Parkinson title dropping its own qualifier',
  new: '9 sources linked and attributed from PubMed metadata; 2005 key corrected to 2016; podcast reclassified; Ames Dwarf mice named; predegenerative neuronal dystrophy restored',
  note: 'database-label round, unverifiable 1 of 4 — 5 of 6 fixes; the (PMC, 2025) ambiguity is reported, not guessed',
});

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, w] of checks) {
  const h = b.includes(k);
  console.log(`    ${h === w ? 'ok  ' : 'FAIL'} ${String(h).padEnd(5)} ${k.slice(0, 48)}`);
  if (h !== w) process.exitCode = 1;
}
console.log(`    PMC links: ${(b.match(/href="https:\/\/pmc\.ncbi/g) || []).length} (want 9)`);
