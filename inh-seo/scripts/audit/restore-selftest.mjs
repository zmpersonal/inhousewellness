import { RESTORE_FIXTURES } from '../lib/restore.mjs';
let bad = 0;
for (const [name, fn, want] of RESTORE_FIXTURES) {
  let got; try { got = await fn(); } catch (e) { got = `threw: ${e.message}`; }
  if (got !== want) { console.log(`FIXTURE FAIL: ${name} — want ${want} got ${got}`); bad++; } else console.log(`  ok  ${name}`);
}
console.log(bad ? `\n${bad} failed` : `\n${RESTORE_FIXTURES.length}/${RESTORE_FIXTURES.length} hold`);
process.exit(bad ? 1 : 0);
