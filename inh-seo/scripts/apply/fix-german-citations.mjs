/* Round 15 citation pass, article 4 of 5 — what-is-a-german-sauna (23,587 impressions).
 * --dry-run default. Approved 16 Sep 2026. Four corrections, all in the Sources list.
 *
 * All 25 links RESOLVE here; no variant 7, no dead links, zero database-as-source labels.
 * The defects are attribution errors, which is the pattern: where the style names authors the
 * errors are in the attributions; where it names databases they are in the bibliography itself.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'what-is-a-german-sauna';
const EDITS = [
  ['wrong journal — Prog Cardiovasc Dis, not BMC Medicine',
    'Laukkanen et al. — sauna bathing, fitness, and mortality risk (BMC Medicine)</a> (2018)',
    'Laukkanen et al. — combined effect of sauna bathing and cardiorespiratory fitness on sudden cardiac death (Progress in Cardiovascular Diseases)</a> (2018)'],
  ['wrong journal — Temperature (Austin), not Mayo Clinic Proceedings',
    'Laukkanen et al. — a comprehensive review of Finnish sauna (Mayo Clinic Proceedings)</a> (2024)',
    'Laukkanen &amp; Kunutsor — passive heat therapies and healthspan, with a focus on Finnish sauna (Temperature)</a> (2024)'],
  ['reversed authors AND evidence-class inflation: a narrative review called a meta-analysis',
    'Kunutsor et al. — sauna bathing and sudden cardiac death: a meta-analysis</a> (2019)',
    'Laukkanen &amp; Kunutsor — is sauna bathing protective of sudden cardiac death? A review of the evidence (Progress in Cardiovascular Diseases)</a> (2019)'],
  ['wrong author entirely — the RCT is Debray et al.',
    'Mero et al. — Finnish sauna and vascular health in coronary artery disease</a> (2023)',
    'Debray, Gravel, Garceau et al. — Finnish sauna bathing and vascular health of adults with coronary artery disease: a randomized controlled trial (Journal of Applied Physiology)</a> (2023)'],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
let body = a.body, fail = 0;
for (const [l, from, to] of EDITS) {
  const n = body.split(from).length - 1;
  console.log(`  ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${l}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}
if (fail) { console.log(`\n  refusing: ${fail} target(s)`); process.exit(1); }
assertWellFormed(body, HANDLE);
const checks = [['(BMC Medicine)', false], ['a meta-analysis', false], ['Mero et al.', false], ['Debray', true], ['Temperature)', true], ['review of the evidence', true]];
const bad = checks.filter(([k, w]) => body.includes(k) !== w);
console.log(`\n  pre-write: ${checks.length - bad.length}/${checks.length}${bad.length ? ' FAILING ' + bad.map((b) => b[0]).join(', ') : ''}`);
if (bad.length) process.exit(1);
if (!APPLY) { console.log('\n  DRY RUN — nothing written.\n'); process.exit(0); }
backup('german-citations', [{ id: a.id, handle: HANDLE, before: a.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: a.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log(m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: a.id, handle: HANDLE, field: 'body', old: '2 wrong journals, 1 reversed author + inflated study type, 1 wrong author', new: 'four bibliography entries corrected against PubMed', note: 'Round 15 citation pass 4/5' });
const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, want] of checks) { const has = b.includes(k); console.log(`    ${has === want ? 'ok  ' : 'FAIL'} ${String(has).padEnd(5)} ${k}`); if (has !== want) process.exitCode = 1; }
