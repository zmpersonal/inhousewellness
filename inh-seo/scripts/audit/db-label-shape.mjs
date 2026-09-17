/* Shape of the database-label round, before any article is opened.
 *   node scripts/audit/db-label-shape.mjs
 *
 * COUNTS ARE OCCURRENCES, not distinct values. That error appeared twice in the citation pass
 * (99 labels read as 99 links; 30 hrefs collapsed to 2 and reported as 1), so every number printed
 * here names its unit.
 *
 * The label pattern is built from the FORMS SEEN, and it is checked against a constructed fixture
 * block so a pattern that stops matching fails the run rather than reporting a clean estate.
 */
import { gql } from '../lib/shopify.js';
import fs from 'node:fs';

/* "(PMC, 2021)", "(PubMed, 2008)", "(NCBI, 2023)", and the same inside a multi-source paren */
const DB = new RegExp('\\b(PMC|PubMed|NCBI|PubMed Central|NIH|Cochrane Library|Medline)\\b\\s*,\\s*(19|20)\\d{2}', 'g');

/* CONSTRUCTED fixtures — repairing the estate cannot break these */
const MUST_MATCH = ['(PMC, 2021)', '(PubMed, 2008)', 'x (NCBI, 2023) y', '(Genuis et al., 2012; PubMed, 2011)', '(Medline, 1999)'];
const MUST_NOT   = ['(Laukkanen et al., 2018)', '(Hussain & Cohen, 2018)', 'PMC5941775', 'see PubMed for more', '(Cleveland Clinic, 2024)'];
let selftest = 0;
for (const f of MUST_MATCH) if (!(f.match(DB) || []).length) { console.log(`  SELFTEST FAIL should match: ${f}`); selftest++; }
for (const f of MUST_NOT)   if ((f.match(DB) || []).length)  { console.log(`  SELFTEST FAIL should not match: ${f}`); selftest++; }
console.log(`  selftest: ${MUST_MATCH.length + MUST_NOT.length - selftest}/${MUST_MATCH.length + MUST_NOT.length}`);
if (selftest) { console.log('  refusing — the pattern does not do what the report will claim'); process.exit(1); }

let after = null, arts = [];
do {
  const q = await gql(`query($a:String){ articles(first:50, after:$a){ pageInfo{hasNextPage endCursor} nodes{ id handle title body isPublished blog{handle} } } }`, { a: after });
  arts.push(...q.articles.nodes);
  after = q.articles.pageInfo.hasNextPage ? q.articles.pageInfo.endCursor : null;
} while (after);

const rows = arts.map((a) => {
  const body = a.body || '';
  const inst = (body.match(DB) || []).length;                       // OCCURRENCES
  const hrefs = [...body.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
  const ext = hrefs.filter((u) => /^https?:/i.test(u) && !/inhousewellness\.com/.test(u));
  const sch = ext.filter((u) => /pubmed|ncbi\.nlm|pmc\.|doi\.org|onlinelibrary|sciencedirect|springer|nature\.com|jamanetwork|bmj|nejm/i.test(u));
  return { handle: a.handle, id: a.id, title: a.title, published: a.isPublished, blog: a.blog.handle,
    instances: inst, hrefOccurrences: ext.length, hrefDistinct: new Set(ext).size,
    scholarlyOccurrences: sch.length, scholarlyDistinct: new Set(sch).size, scholarly: [...new Set(sch)] };
});
fs.writeFileSync('data/db-label-shape.json', JSON.stringify(rows, null, 1));

const withLabels = rows.filter((r) => r.instances > 0);
const big = withLabels.filter((r) => r.instances >= 20).sort((a, b) => b.instances - a.instances);
const totalInst = withLabels.reduce((s, r) => s + r.instances, 0);

console.log(`\n  articles scanned: ${rows.length}`);
console.log(`  articles containing at least one database label: ${withLabels.length}`);
console.log(`  TOTAL LABEL OCCURRENCES (not distinct forms): ${totalInst}`);
console.log(`  articles with 20+ occurrences: ${big.length}`);
console.log(`  unpublished among those ${big.length}: ${big.filter((r) => !r.published).length}`);

const allSch = new Set(); for (const r of big) r.scholarly.forEach((u) => allSch.add(u));
console.log(`\n  across the ${big.length}: scholarly href OCCURRENCES ${big.reduce((s, r) => s + r.scholarlyOccurrences, 0)}, DISTINCT URLs ${allSch.size}`);
console.log(`  external href OCCURRENCES ${big.reduce((s, r) => s + r.hrefOccurrences, 0)}, DISTINCT ${new Set(big.flatMap((r)=>r.scholarly)).size} scholarly of ${new Set(big.flatMap((r)=>[])).size || 'n/a'}`);

console.log(`\n  ${'label'.padStart(5)}  ${'schol'.padStart(5)}  ${'pub'}  handle`);
for (const r of big) console.log(`  ${String(r.instances).padStart(5)}  ${String(r.scholarlyDistinct).padStart(5)}  ${r.published ? ' Y ' : ' n '}  ${r.handle}`);
fs.writeFileSync('data/db-label-big29.json', JSON.stringify(big, null, 1));
