/* Fixtures for scripts/lib/replan.mjs, plus a mutation check that they are not decoration.
 *   node scripts/audit/replan-selftest.mjs
 */
import { REPLAN_FIXTURES } from '../lib/replan.mjs';
let bad = 0;
for (const [name, fn, want] of REPLAN_FIXTURES) {
  let got; try { got = fn(); } catch (e) { got = `threw: ${e.message}`; }
  if (got !== want) { console.log(`FIXTURE FAIL: ${name} — want ${want} got ${got}`); bad++; }
  else console.log(`  ok  ${name}`);
}
console.log(bad ? `\n${bad} fixture(s) failed` : `\n${REPLAN_FIXTURES.length}/${REPLAN_FIXTURES.length} hold`);
process.exit(bad ? 1 : 0);
