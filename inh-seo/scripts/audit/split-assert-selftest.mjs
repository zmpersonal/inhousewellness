/* Proof that assertSplitPoint catches its OWN founding failure.
 *
 *   node scripts/audit/split-assert-selftest.mjs
 *
 * A guard that cannot reproduce the failure that motivated it has not been tested. The founding
 * failure is real content: sauna-benefits-detoxification contains "Sources" twice — once in its
 * table of contents, once as the section heading — and splitting on the bare string lands on the
 * contents entry, 40,000 characters early.
 *
 * Fixtures are CONSTRUCTED so repairing the estate cannot break this test. 18i: the live
 * confirmation against sauna-benefits-detoxification was removed — it depended on that article
 * still carrying id="sources", so repairing the article would have broken the guard, and it
 * needed Admin API credentials to run at all. Its shape is now a constructed document below.
 */
import { assertSplitPoint, splitAtAssert } from '../lib/split-assert.mjs';

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

// 18i: proves pick:'last' returns the LATER candidate, not merely that it does not throw
check('pick:"last" returns the index of the heading, not the contents entry', () => {
  const i = assertSplitPoint(DOC, 'Sources', { pick: 'last', label: 'last-idx' });
  if (i !== DOC.lastIndexOf('Sources')) throw new Error(`returned ${i}, want ${DOC.lastIndexOf('Sources')}`);
}, false);

/* the split point must actually be the heading, not the contents entry.
   18i: the split itself runs inside check(), so a throw is a reported FAIL, not a crash. */
let head = '', tail = '';
check('split with context "<h2" succeeds', () => { [head, tail] = splitAtAssert(DOC, 'Sources', { context: '<h2', label: 'doc' }); }, false);
check('the body side contains the contents entry (proving we split at the heading)',
  () => { if (!head.includes('<li><p>Sources')) throw new Error('split landed in the wrong place'); }, false);
check('the tail side contains the citation list',
  () => { if (!tail.includes('a citation')) throw new Error('tail is not the bibliography'); }, false);

/* ── the live case's SHAPE, constructed (18i: replaces the live fetch) ──
   A generated heading id plus a separate jump target, "Sources" in the contents list twice
   over, and the heading far down the document — the forms CLAUDE.md records for this article. */
console.log('\nCONSTRUCTED LIVE-SHAPE CASE:');
const LIVE_SHAPE = '<p><a href="#sources">Sources</a></p><ol><li><p>Sources</p></li></ol>'
  + '<p>body</p>'.repeat(3000)
  + '<a id="sources"></a><h2 id="h.qbgv1">Sources</h2><ul><li>ref</li></ul>';
check('bare split on the live-shape document REFUSES', () => assertSplitPoint(LIVE_SHAPE, 'Sources', { label: 'shape-bare' }), true);
let i = -1;
check('context id="sources" + pick:last resolves', () => { i = assertSplitPoint(LIVE_SHAPE, 'Sources', { context: 'id="sources"', pick: 'last', label: 'shape-ctx' }); }, false);
check('the asserted point is the heading, not the first occurrence',
  () => { if (i !== LIVE_SHAPE.lastIndexOf('Sources') || i === LIVE_SHAPE.indexOf('Sources')) throw new Error(`asserted ${i}`); }, false);

console.log(`\n  ${failures ? `${failures} FAILURE(S)` : 'all checks passed'}`);
process.exitCode = failures ? 1 : 0;
