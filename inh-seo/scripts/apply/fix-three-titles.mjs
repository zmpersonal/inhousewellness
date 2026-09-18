/* Database-label round — the three small fixes. --dry-run default.
 *   node scripts/apply/fix-three-titles.mjs [--apply]
 *
 * Both edits are VARIANT 4 BY SUBTRACTION OR SUBSTITUTION: nothing was added, nothing was
 * misattributed, and a word carrying the source's own meaning was changed or dropped.
 *
 * 1. sauna-for-autoimmune — PMID 40202605 is "Sauna therapy in rheumatic diseases: mechanisms,
 *    potential benefits, and CAUTIONS" (Rheumatol Int 2025). The source list renders the subtitle
 *    as "therapeutic perspectives". The paper's own warning framing, replaced with a promotional
 *    one, in a source list, on an autoimmune page.
 *
 * 2. biohacking-tools — PMID 31136885 is "Photobiomodulation therapy reduces acute pain and
 *    inflammation IN MICE" (J Photochem Photobiol B 2019; MeSH Animals, Mice). The source list
 *    prints the title with "in mice" removed and the body names no species. The same article
 *    labels its PEMF stroke source "(animal model)" unprompted — it flags one and drops the other.
 *
 * NOT FIXED, reported instead: "(PubMed, 2019)" here and "(PMC, 2025)" on the HSF1 article each
 * key two different papers. Assigning occurrences would be a guess. A wrong key is worse than an
 * ambiguous one.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');

const WORK = [
  {
    handle: 'sauna-for-autoimmune-condition-symptom-relief',
    edits: [
      ['SUBTITLE — "cautions" restored, per PubMed 40202605',
       'Sauna therapy in rheumatic diseases: mechanisms, potential benefits, and therapeutic perspectives. PubMed, 2025.',
       'Sauna therapy in rheumatic diseases: mechanisms, potential benefits, and cautions. Fedorchenko Y et al., Rheumatology International, 2025. Review. PubMed, 2025.'],
    ],
    checks: [['and cautions. Fedorchenko', true], ['therapeutic perspectives', false], ['40202605', true]],
  },
  {
    handle: 'biohacking-tools-inflammation-reduction',
    edits: [
      ['SOURCE LIST — "in mice" restored to the title',
       'PubMed — "Photobiomodulation therapy reduces acute pain and inflammation," 2019. pubmed.ncbi.nlm.nih.gov/31136885.',
       'PubMed — Pigatto GR et al., "Photobiomodulation therapy reduces acute pain and inflammation <strong>in mice</strong>," J Photochem Photobiol B, 2019. <strong>Animal study.</strong> pubmed.ncbi.nlm.nih.gov/31136885.'],

      ['BODY — the species named in the sentence, not appended to it',
       'A separate study found pain reduction and inflammatory modulation from photobiomodulation, but effects varied by protocol and condition treated (PubMed, 2019).',
       'A separate study in mice found pain reduction and inflammatory modulation from photobiomodulation, with effects varying by protocol (PubMed, 2019). As with the PEMF animal work below, a mouse result does not establish what a consumer device does for a person.'],
    ],
    checks: [['inflammation <strong>in mice</strong>', true], ['<strong>Animal study.</strong>', true],
             ['A separate study in mice found', true], ['does not establish what a consumer device does', true]],
  },
];

let anyFail = 0;
const staged = [];

for (const w of WORK) {
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${w.handle}` });
  const art = q.articles.nodes.find((x) => x.handle === w.handle);
  if (!art) { console.log(`  FAIL article not found: ${w.handle}`); anyFail++; continue; }   /* fail-ok: anyFail refuses with exit(1) before any write */
  let body = art.body;
  console.log(`\n  ${w.handle}`);
  let fail = 0;
  for (const [label, from, to] of w.edits) {
    const n = body.split(from).length - 1;
    console.log(`    ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
    if (n !== 1) { fail++; continue; }
    body = body.replace(from, to);
  }
  if (fail) { anyFail += fail; continue; }
  assertWellFormed(body, w.handle);
  const bad = w.checks.filter(([k, want]) => body.includes(k) !== want);
  console.log(`    pre-write checks: ${w.checks.length - bad.length}/${w.checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);   /* fail-ok: anyFail refuses with exit(1) before any write */
  if (bad.length) { anyFail += bad.length; continue; }
  staged.push({ ...w, id: art.id, before: art.body, body });
}

if (anyFail) { console.log(`\n  refusing: ${anyFail} problem(s)`); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

for (const s of staged) {
  backup(`three-titles-${s.handle}`, [{ id: s.id, handle: s.handle, before: s.before }]);
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: s.id, article: { body: s.body } });
  if (m.articleUpdate.userErrors.length) { console.log('  ERR', s.handle, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  logChange({ resource: s.id, handle: s.handle, field: 'body', old: 'source title altered from the published record', new: 'published title and species restored from PubMed metadata', note: 'database-label round — variant 4 by substitution/subtraction' });
}

console.log('\n  re-read:');
for (const s of staged) {
  const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${s.handle}` });
  const b = back.articles.nodes.find((x) => x.handle === s.handle).body;
  console.log(`    ${s.handle}`);
  for (const [k, want] of s.checks) {
    const has = b.includes(k);
    console.log(`      ${has === want ? 'ok  ' : 'FAIL'} ${String(has).padEnd(5)} ${k.slice(0, 48)}`);
    if (has !== want) process.exitCode = 1;
  }
}
