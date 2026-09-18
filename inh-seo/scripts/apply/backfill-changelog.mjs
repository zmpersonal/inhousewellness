/**
 * Backfills the 12 article mutations that were applied without a logChange().
 *
 * EVERY backfilled row carries `reconstructed: true`, the evidence it was built
 * from, and the timestamp Shopify itself recorded. That flag is the whole point.
 * A reconstructed row that reads like a contemporaneous one destroys the only
 * property that makes a log worth having — that its absence means something.
 *
 * `at` is the article's live `updatedAt` from the Admin API, not a guess and not
 * the time of this backfill. `before` is quoted only where a real before-state
 * survives; where none does, the row says so rather than inventing one.
 *
 *   node scripts/apply/backfill-changelog.mjs           # dry run
 *   node scripts/apply/backfill-changelog.mjs --apply
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { DATA, parseArgs, banner } from '../lib/util.js';

/* RETIRED by the Round 18i guard audit (2026-09-18): its idempotency key includes live updatedAt, so a re-run appends duplicate reconstructed rows.
   It ran once and its specs are consumed, so its guards can no longer be demonstrated against the live estate —
   and a guard that cannot be shown to fail is not a guard. To run it again, delete these lines in a reviewed commit. */
console.error('RETIRED (Round 18i guard audit): backfill-changelog.mjs — its idempotency key includes live updatedAt, so a re-run appends duplicate reconstructed rows.'); process.exit(1);

const flags = parseArgs();
banner('backfill-changelog', flags);

const CE = path.join(DATA, 'citation-edit');
/* handle -> [script, evidence file or null, what it was] */
const GAPS = [
  ['arcadia-barrel-sauna-guide', 'arcadia-backlink', path.join(DATA, 'backups/arcadia-backlink/before.json'), 'contextual backlink added to the Arcadia guide'],
  ['almost-heaven-audra-shenandoah', 'c4-cluster', path.join(CE, 'almost-heaven-audra-shenandoah.cluster.before.html'), 'C4 cluster cross-links'],
  ['sun-home-saunas-review', 'c4-cluster', path.join(CE, 'sun-home-saunas-review.cluster.before.html'), 'C4 cluster cross-links'],
  ['clearlight-saunas-review', 'c4-cluster', null, 'C4 cluster cross-links'],
  ['sunlighten-saunas-review', 'c4-cluster', null, 'C4 cluster cross-links'],
  ['plunge-immune-function', 'claimfix', path.join(CE, 'plunge-immune-function.claimfix.before.html'), 'hard-rule-4 correction — "boost immune system functioning"'],
  ['how-saunas-improve-circulation', 'claimfix', path.join(CE, 'how-saunas-improve-circulation.claimfix.before.html'), 'hard-rule-4 correction — the asserted vasodilation mechanism'],
  ['science-of-temperature-therapy-routines', 'tier-b', path.join(CE, 'science-of-temperature-therapy-routines.tierb.before.html'), 'Tier B limitation added to a cited finding'],
  ['thermal-stress-hormetic-window-human-studies', 'tier-b', path.join(CE, 'thermal-stress-hormetic-window-human-studies.tierb.before.html'), 'Tier B limitation added to a cited finding'],
  ['timing-heat-cold-fatigue-type-recovery-map', 'tier-b', path.join(CE, 'timing-heat-cold-fatigue-type-recovery-map.tierb.before.html'), 'Tier B limitation added to a cited finding'],
  ['beyond-sauna-heat-cold-exposures-hsp-map', 'tier-b', path.join(CE, 'beyond-sauna-heat-cold-exposures-hsp-map.tierb.before.html'), 'Tier B limitation added to a cited finding'],
  ['dynamic-saunas-monaco-dyn-6996-01-elite', 'tier-b', path.join(CE, 'dynamic-saunas-monaco-dyn-6996-01-elite.tierb.before.html'), 'Tier B limitation added to a cited finding'],
  ['chromotherapy-vs-no-chromotherapy-buyers-guide', 'tier-b', 'data/content.json@2026-09-09T09:38', 'Tier B limitation — Laukkanen cohort scoped to observational Finnish populations'],
];

/* The title change is not a body edit and has no backup anywhere. Its
   before-state survives only because it was staged as markdown first. */
const TITLE_GAP = {
  handle: 'how-saunas-improve-circulation', field: 'title',
  before: 'The Science of Heat: How Saunas Improve Circulation and Cardiovascular Health',
  after: 'Sauna Temperature, Session Length, and What the Circulation Research Actually Shows',
  evidence: 'content/fixes/how-saunas-improve-circulation.md',
  note: 'THE mutation that caused instance 53. No backup of any kind; recoverable only because the fix was staged as markdown before it was applied.',
};

/* Two collections were removed from the Online Store channel — a deindexing,
   the class hard rule 3 governs — with a backup of their prior publications and
   no log row. The backup keys them by camelCase nickname, which is why the first
   pass of the integrity probe could not match them to anything. */
const COLLECTION_GAPS = [
  ['portable-saunas', 'heaterFloorPlate/portableSaunas backup'],
  ['heater-floor-plate', 'heaterFloorPlate/portableSaunas backup'],
];

let arts = [], after = null, more = true;
while (more) {
  const r = await gql(`query($after:String){ articles(first:100, after:$after){
    pageInfo{ hasNextPage endCursor } nodes{ id handle title body updatedAt } } }`, { after });
  arts.push(...r.articles.nodes); more = r.articles.pageInfo.hasNextPage; after = r.articles.pageInfo.endCursor;
}
const byHandle = new Map(arts.map((a) => [a.handle, a]));

const rows = [];
for (const [handle, script, evidence, what] of GAPS) {
  const a = byHandle.get(handle);
  if (!a) { console.error(`  ✗ ${handle} not found live`); process.exitCode = 1; continue; }   // guard audit 18i
  const haveBefore = evidence && (evidence.startsWith('data/') ? true : fs.existsSync(evidence));
  rows.push({
    at: new Date(a.updatedAt).toISOString(), script, kind: 'article', id: a.id, handle, field: 'body',
    before: haveBefore ? `recoverable — ${evidence.replace(process.cwd() + '/', '')}` : 'NOT RECOVERABLE — no before-state was written',
    after: `${a.body.length} chars`,
    reconstructed: true,
    reconstructed_at: new Date().toISOString(),
    reconstructed_from: haveBefore ? evidence.replace(process.cwd() + '/', '') : 'live updatedAt only',
    what,
  });
}
rows.push({
  at: new Date(byHandle.get(TITLE_GAP.handle).updatedAt).toISOString(),
  script: 'claimfix', kind: 'article', id: byHandle.get(TITLE_GAP.handle).id, handle: TITLE_GAP.handle,
  field: 'title', before: TITLE_GAP.before, after: TITLE_GAP.after,
  reconstructed: true, reconstructed_at: new Date().toISOString(),
  reconstructed_from: TITLE_GAP.evidence, what: TITLE_GAP.note,
});
const colBackup = JSON.parse(fs.readFileSync(path.join(DATA, 'backups/2026-09-08T16-37-06-467Z/backup.json'), 'utf8'));
const collections = JSON.parse(fs.readFileSync(path.join(DATA, 'collections.json'), 'utf8'));
for (const [handle] of COLLECTION_GAPS) {
  const c = collections.find((x) => x.handle === handle);
  const key = handle === 'portable-saunas' ? 'portableSaunas' : 'heaterFloorPlate';
  rows.push({
    at: new Date(c.updatedAt).toISOString(), script: 'collection-deindex', kind: 'collection', id: c.id, handle,
    field: 'publications', before: colBackup[key], after: c.publicationNames,
    reconstructed: true, reconstructed_at: new Date().toISOString(),
    reconstructed_from: 'data/backups/2026-09-08T16-37-06-467Z/backup.json',
    what: 'Removed from the Online Store channel. A DEINDEXING with no log row — the class hard rule 3 governs.',
  });
}

/* Idempotent: never append a reconstructed row that is already present. */
const existing = new Set(fs.readFileSync(path.join(DATA, 'changelog.jsonl'), 'utf8').trim().split('\n')
  .map((l) => JSON.parse(l)).filter((r) => r.reconstructed).map((r) => `${r.handle}|${r.field}|${r.at}`));
const before = rows.length;
for (let i = rows.length - 1; i >= 0; i--) if (existing.has(`${rows[i].handle}|${rows[i].field}|${rows[i].at}`)) rows.splice(i, 1);
if (before !== rows.length) console.log(`  (${before - rows.length} row(s) already backfilled — skipped)\n`);

rows.sort((a, b) => (a.at < b.at ? -1 : 1));

for (const r of rows) {
  console.log(`  ${r.at}  ${r.script.padEnd(14)} ${r.handle}  [${r.field}]`);
  console.log(`      ${r.what}`);
  console.log(`      before: ${String(r.before).slice(0, 100)}`);
}
console.log(`\n${rows.length} reconstructed rows. ${rows.filter(r => String(r.before).startsWith('NOT')).length} with no recoverable before-state.`);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

const target = path.join(DATA, 'changelog.jsonl');
fs.copyFileSync(target, path.join(DATA, `changelog.jsonl.pre-backfill-${Date.now()}`));
fs.appendFileSync(target, rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
console.log(`\nappended ${rows.length} rows to data/changelog.jsonl (copy of the original kept alongside)`);
