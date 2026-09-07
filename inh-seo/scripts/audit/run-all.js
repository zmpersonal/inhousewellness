import { execSync } from 'node:child_process';
const steps = ['dump-collections.js','dump-products.js','dump-content.js','scan-broken-copy.js'];
for (const s of steps) {
  console.log(`\n--- ${s} ---`);
  execSync(`node scripts/audit/${s}`, { stdio: 'inherit' });
}
console.log('\nAudit complete. See data/ and reports/.');
