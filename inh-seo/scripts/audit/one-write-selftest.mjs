/* Proof for assertOneWritePerRecord (instance 62).
 * Fixtures are SYNTHETIC. Repairing the estate cannot break this test — which
 * is the standard, after two guards died when their live anchors were fixed. */
import { assertOneWritePerRecord } from '../lib/util.js';

let fail = 0;
const check = (name, fn, shouldThrow) => {
  let threw = null;
  try { fn(); } catch (e) { threw = e; }
  const ok = shouldThrow ? !!threw : !threw;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) fail = 1;
  if (shouldThrow && threw) console.log(threw.message.split('\n').slice(0, 3).map((l) => '        ' + l).join('\n'));
  if (!shouldThrow && threw) console.log('        unexpected: ' + threw.message.split('\n')[0]);
};

console.log('=== assertOneWritePerRecord ===\n');

/* 1. THE KNOWN-BROKEN CASE, reconstructed: the shape that lost the Dundalk
      link. Two writes to one article, each built from the same snapshot. */
check('two writes to one record REFUSE', () => {
  assertOneWritePerRecord(
    [{ h: 'best-outdoor-cold-plunge-tubs', body: 'A' },
     { h: 'sisu-sauna-review', body: 'B' },
     { h: 'best-outdoor-cold-plunge-tubs', body: 'C' }],
    (t) => t.h, 'fixture',
  );
}, true);

/* 2. CONTROL — distinct records must pass, or the guard is just an exception. */
check('distinct records PASS', () => {
  assertOneWritePerRecord(
    [{ h: 'a' }, { h: 'b' }, { h: 'c' }], (t) => t.h, 'fixture',
  );
}, false);

/* 3. CONTROL — the accumulated form, which is what the fix produces. One row
      per record carrying both edits. This MUST pass or the fix is unusable. */
check('accumulated: one row per record PASSES', () => {
  assertOneWritePerRecord(
    [{ h: 'best-outdoor-cold-plunge-tubs', body: 'A+C' }, { h: 'sisu-sauna-review', body: 'B' }],
    (t) => t.h, 'fixture',
  );
}, false);

/* 4. A missing key is not a pass. A keyOf that returns undefined would make
      every row look distinct and the guard would certify a broken batch. */
check('missing record key REFUSES', () => {
  assertOneWritePerRecord([{ h: 'a' }, { nope: 1 }], (t) => t.h, 'fixture');
}, true);

/* 5. Empty batch is fine. */
check('empty batch PASSES', () => {
  assertOneWritePerRecord([], (t) => t.h, 'fixture');
}, false);

console.log(fail ? '\nSELFTEST FAILED' : '\nAll cases behaved as specified.');
process.exit(fail);
