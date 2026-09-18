/* Round 18c — every general-retailer link, classified by LINKED URL. READ-ONLY. */
import fs from 'node:fs';
import { classifyLinkedUrl, GENERAL_RETAILERS, FIXTURES } from '../lib/linked-url-class.mjs';
for (const [l, f] of FIXTURES) if (!f()) { console.log('FIXTURE FAIL: ' + l); process.exit(1); }
const S = JSON.parse(fs.readFileSync('data/r18c-prestate.json', 'utf8'));
const rows = S.rows.filter((r) => GENERAL_RETAILERS.has(r.domain));
const tally = {};
for (const d of GENERAL_RETAILERS) {
  const rs = rows.filter((r) => r.domain === d);
  if (!rs.length) continue;
  console.log(`\n== ${d}  (institute ${rs.filter((r) => r.blog === 'institute').length} / ordinary ${rs.filter((r) => r.blog !== 'institute').length})`);
  rs.forEach((r, i) => {
    const c = classifyLinkedUrl(r.href);
    tally[c.call] = (tally[c.call] || 0) + 1;
    console.log(`  ${String(i + 1).padStart(2)} ${c.call.padEnd(6)} ${r.article.slice(0, 40).padEnd(40)} ${r.context === 'TABLE CELL' ? 'TABLE ' : '      '}${c.why.padEnd(44)} [${(r.anchorText || '(empty)').slice(0, 42)}]`);
  });
}
console.log('\nTOTAL', rows.length, JSON.stringify(tally));
