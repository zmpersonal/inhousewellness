import { VENDOR_IDENTITY_FIXTURES } from '../lib/vendor-identity.mjs';
let bad = 0;
for (const [n, f, w] of VENDOR_IDENTITY_FIXTURES) {
  let g; try { g = f(); } catch (e) { g = `threw: ${e.message}`; }
  if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } else console.log(`  ok  ${n}`);
}
console.log(bad ? `\n${bad} failed` : `\n${VENDOR_IDENTITY_FIXTURES.length}/${VENDOR_IDENTITY_FIXTURES.length} hold`);
process.exit(bad ? 1 : 0);
