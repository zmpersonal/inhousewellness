/* heavenly-heat-sauna-review — variant 5 on the highest-traffic page of the set (2,049 impressions).
 * --dry-run default.   node scripts/apply/fix-heavenly-hr.mjs [--apply]
 *
 * The article quotes four hazard ratios from Zaccardi et al., "Sauna Bathing and Incident
 * Hypertension: A Prospective Cohort Study", Am J Hypertens 2017 (PMID 28633297), and calls all
 * four "meaningfully lower". Per PubMed:
 *
 *   2-3 sessions/wk, unadjusted      HR 0.76  (95% CI 0.57-1.02)   CROSSES 1 - not significant
 *   4-7 sessions/wk, unadjusted      HR 0.54  (95% CI 0.32-0.91)   significant
 *   2-3 sessions/wk, fully adjusted  HR 0.83  (95% CI 0.59-1.18)   CROSSES 1 - not significant
 *   4-7 sessions/wk, fully adjusted  HR 0.53  (95% CI 0.28-0.98)   significant
 *
 * Two of the four are compatible with no effect. No interval appears anywhere in the article.
 * Same correction as the 22% sudden-cardiac-death figure on how-saunas-improve-circulation.
 *
 * BOTH representations are edited in one pass. The one-claim-many-representations rule has caught
 * this project three times; the FAQ restatement is the second representation here.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'heavenly-heat-sauna-review';

const EDITS = [
  ['BODY — four ratios, two of them non-significant, all called "meaningfully lower"',
   'Cardiovascular and blood pressure effects: Observational cohort research found that more frequent sauna use was associated with meaningfully lower hazard ratios for incident hypertension—0.76 and 0.54 in unadjusted models, and 0.83 and 0.53 in fully adjusted models, for 2–3 versus 4–7 sessions per week (PubMed, 2017). This is associative data from a Finnish population; it does not prove causation.',
   'Cardiovascular and blood pressure effects: A prospective cohort of 1,621 Finnish men found lower incident hypertension at the highest sauna frequency. Against once-weekly use, the fully adjusted hazard ratio was <strong>0.53 (95% CI 0.28–0.98) for 4–7 sessions per week</strong> — statistically significant. At <strong>2–3 sessions per week it was 0.83 (95% CI 0.59–1.18), an interval that crosses 1.0 and is compatible with no effect</strong> (PubMed, 2017). So the association shows up at four or more sessions a week and is not established below that. This is observational data from a Finnish population; it does not prove causation.'],

  ['FAQ — the same claim restated, same two figures, no interval',
   'A prospective Finnish cohort study found fully adjusted hazard ratios of 0.83 and 0.53 for 2–3 versus 4–7 sauna sessions per week, compared to once-weekly use (PubMed, 2017)',
   'A prospective Finnish cohort study found a fully adjusted hazard ratio of 0.53 (95% CI 0.28–0.98) for 4–7 sauna sessions per week against once-weekly use. At 2–3 sessions the figure was 0.83 (95% CI 0.59–1.18), which crosses 1.0 and does not establish a difference (PubMed, 2017)'],
];

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${HANDLE}` });
const art = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!art) throw new Error('not found');
let body = art.body, fail = 0;

for (const [label, from, to] of EDITS) {
  const n = body.split(from).length - 1;
  console.log(`  ${n === 1 ? 'ok  ' : 'FAIL'} ${n}×  ${label}`);
  if (n !== 1) { fail++; continue; }
  body = body.replace(from, to);
}
if (fail) { console.log(`\n  refusing: ${fail} target(s) not matched once`); process.exit(1); }
assertWellFormed(body, HANDLE);

const checks = [
  ['meaningfully lower hazard ratios', false],
  ['0.76 and 0.54', false],
  ['hazard ratios of 0.83 and 0.53', false],
  ['95% CI 0.28–0.98', true],
  ['95% CI 0.59–1.18', true],
  ['compatible with no effect', true],
  ['crosses 1.0 and does not establish a difference', true],
  ['1,621 Finnish men', true],
];
const bad = checks.filter(([k, w]) => body.includes(k) !== w);
const ci = (body.match(/95% CI/g) || []).length;
console.log(`\n  confidence intervals now stated: ${ci} (want 4 — two figures × two representations)`);
console.log(`  pre-write checks: ${checks.length - bad.length}/${checks.length}${bad.length ? '  FAILING: ' + bad.map((b) => b[0]).join(', ') : ''}`);
if (bad.length || ci !== 4) { console.log('  refusing'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('heavenly-hr', [{ id: art.id, handle: HANDLE, before: art.body }]);
const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`, { id: art.id, article: { body } });
if (m.articleUpdate.userErrors.length) { console.log('  ERR', m.articleUpdate.userErrors); process.exit(1); }
logChange({ resource: art.id, handle: HANDLE, field: 'body', old: 'four hazard ratios called "meaningfully lower", two of them non-significant, no confidence intervals, restated in the FAQ', new: 'intervals stated in both representations; the 2-3/week figures named as crossing 1.0; the significant 4-7/week result carries the point; n stated', note: 'variant 5 — non-significant result reported as a finding' });

const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE).body;
console.log('\n  re-read:');
for (const [k, w] of checks) {
  const h = b.includes(k);
  console.log(`    ${h === w ? 'ok  ' : 'FAIL'} ${String(h).padEnd(5)} ${k.slice(0, 48)}`);
  if (h !== w) process.exitCode = 1;
}
console.log(`    95% CI occurrences: ${(b.match(/95% CI/g) || []).length} (want 4)`);
