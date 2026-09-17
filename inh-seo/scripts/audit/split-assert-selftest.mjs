/* Proof that assertSplitPoint catches its OWN founding failure.
 *
 *   node scripts/audit/split-assert-selftest.mjs
 *
 * A guard that cannot reproduce the failure that motivated it has not been tested. The founding
 * failure is real content: sauna-benefits-detoxification contains "Sources" twice — once in its
 * table of contents, once as the section heading — and splitting on the bare string lands on the
 * contents entry, 40,000 characters early.
 *
 * Fixtures are CONSTRUCTED so repairing the estate cannot break this test; the live article is
 * then used as a second, confirmatory case.
 */
import { assertSplitPoint, splitAtAssert } from '../lib/split-assert.mjs';
import { gql } from '../lib/shopify.js';

let failures = 0;
const check = (name, fn, wantThrow) => {
  let threw = null;
  try { fn(); } catch (e) { threw = e.message.split('\n')[0]; }
  const ok = wantThrow ? !!threw : !threw;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${threw ? `  → ${threw.slice(0, 96)}` : ''}`);
  if (!ok) failures++;
};

/* ── constructed fixtures ── */
const DOC = '<ol><li><p>Sources</p></li><li><p>What We Still Don\'t Know</p></li></ol>'
  + 'x'.repeat(4000)
  + '<h2 id="sources">Sources</h2><ul><li>a citation</li></ul>';

console.log('CONSTRUCTED:');
check('the founding failure: bare "Sources" is ambiguous and must REFUSE',
  () => assertSplitPoint(DOC, 'Sources', { label: 'bare' }), true);
check('with context "<h2" it resolves to the heading',
  () => assertSplitPoint(DOC, 'Sources', { context: '<h2', label: 'ctx' }), false);
check('a context that never matches REFUSES rather than falling back',
  () => assertSplitPoint(DOC, 'Sources', { context: '<h9', label: 'bad-ctx' }), true);
check('a delimiter that does not occur REFUSES',
  () => assertSplitPoint(DOC, 'Bibliography', { label: 'absent' }), true);
check('pick:"last" accepts ambiguity deliberately',
  () => assertSplitPoint(DOC, 'Sources', { pick: 'last', label: 'last' }), false);

/* the split point must actually be the heading, not the contents entry */
const [head, tail] = splitAtAssert(DOC, 'Sources', { context: '<h2', label: 'doc' });
check('the body side contains the contents entry (proving we split at the heading)',
  () => { if (!head.includes('<li><p>Sources')) throw new Error('split landed in the wrong place'); }, false);
check('the tail side contains the citation list',
  () => { if (!tail.includes('a citation')) throw new Error('tail is not the bibliography'); }, false);

/* ── the live case that caused it ── */
console.log('\nLIVE CONFIRMATION (sauna-benefits-detoxification):');
const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: 'handle:sauna-benefits-detoxification' });
const body = q.articles.nodes.find((x) => x.handle === 'sauna-benefits-detoxification')?.body;
if (!body) { console.log('  SKIP — article not reachable'); }
else {
  const occurrences = (body.match(/Sources/g) || []).length;
  console.log(`  the live article contains "Sources" ${occurrences}× `);
  check('bare split on the live article REFUSES', () => assertSplitPoint(body, 'Sources', { label: 'live-bare' }), occurrences > 1);
  const i = assertSplitPoint(body, 'Sources', { context: 'id="sources"', pick: 'last', label: 'live-ctx' });
  const naive = body.indexOf('Sources');
  console.log(`  naive split point: ${naive}   asserted: ${i}   difference: ${i - naive} characters`);
  check('the asserted point is NOT the first occurrence', () => { if (i === naive) throw new Error('same as naive'); }, false);
}

console.log(`\n  ${failures ? `${failures} FAILURE(S)` : 'all checks passed'}`);
process.exitCode = failures ? 1 : 0;
