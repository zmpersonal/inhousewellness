/**
 * CHANGELOG INTEGRITY — is the audit trail complete?
 *
 * data/changelog.jsonl is the artefact anyone reconstructing this work would
 * rely on. Its completeness is therefore a fact about the project, and
 * "mostly complete" is the answer that causes harm, because it gets trusted.
 *
 * The method is a cross-check between two independent records of the same
 * events. Every apply script is supposed to do BOTH of these:
 *
 *   backup(...)     -> data/backups/{ISO}/   (state, timestamped)
 *   logChange(...)  -> data/changelog.jsonl  (intent, timestamped)
 *
 * A backup with no changelog row in its window is a WRITE THAT WAS NOT LOGGED.
 * A changelog row with no backup near it is a LOG WITH NO RECOVERY POINT.
 * Neither record is authoritative; the disagreement is the finding.
 *
 * Read-only.
 *
 *   node scripts/audit/changelog-integrity.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { DATA } from '../lib/util.js';

const WINDOW_MS = 45 * 60 * 1000; /* generous: a batch of 90 collections takes minutes */

const rows = fs.readFileSync(path.join(DATA, 'changelog.jsonl'), 'utf8')
  .trim().split('\n').map((l) => JSON.parse(l));

const dirToDate = (name) => {
  const m = name.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})-(\d{3})Z$/);
  return m ? new Date(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}.${m[7]}Z`) : null;
};

/* Walk any shape and collect the identifiers it carries. Backup payloads are
   not a schema — each script wrote whatever key it happened to have, and the
   FIRST version of this probe encoded only `handle` and `id`. It reported 9
   unlogged backups. All nine were the probe reading its own vocabulary: the
   payloads say `productHandle`, `slug`, `collection`, or use a camelCase
   nickname as an object key. Eighth instance of the probe-vocabulary rule, and
   the first one inside an audit OF the audit trail. */
const ID_KEYS = /^(handle|productHandle|collectionHandle|slug|collection|articleHandle)$/;
function idsIn(node, out = new Set()) {
  if (node == null) return out;
  if (Array.isArray(node)) { for (const n of node) idsIn(n, out); return out; }
  if (typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (ID_KEYS.test(k) && typeof v === 'string') out.add(v);
      if (k === 'id' && typeof v === 'string' && v.startsWith('gid://')) out.add(v);
      idsIn(v, out);
    }
    return out;
  }
  return out;
}

/* Some payloads carry NO resolvable identifier at all — emf-membership keys its
   object by nickname (`sanMarino`), a publications backup by `heaterFloorPlate`.
   Those can only be matched by which script wrote them, so the filename is a
   second, weaker key. Weaker because a filename is a convention, and a
   convention is for finding candidates, never for concluding. */
const LABEL_TO_SCRIPT = {
  'membership-before.json': ['fix-membership'],
  'emf-membership-before.json': ['emf-membership'],
  'article-publish-before.json': ['publish-article'],
  'article-bodies-before.json': ['apply-article-links', 'resource-citations'],
  'article-claims-before.json': ['edit-article-claims'],
  'collection-copy-before.json': ['apply-collection-copy'],
  'seo-fields-before.json': ['apply-seo-fields'],
  'article-seo-before.json': ['apply-article-seo'],
  'decisions-before.json': ['decisions-2026-09-07'],
  'clear-broken-before.json': ['clear-broken-copy'],
  'strip-markup-before.json': ['strip-markup'],
  'unpublish-before.json': ['unpublish-collections'],
  'clear-collection-copy-before.json': ['clear-collection-copy'],
  'product-claims-Dynamic-Saunas-before.json': ['cut-product-claims'],
};

const backupsDir = path.join(DATA, 'backups');
const backups = [];
for (const name of fs.readdirSync(backupsDir)) {
  const full = path.join(backupsDir, name);
  if (!fs.statSync(full).isDirectory()) continue;
  const at = dirToDate(name);
  const files = fs.readdirSync(full);
  const ids = new Set();
  for (const f of files) {
    if (f.endsWith('.json')) {
      try { idsIn(JSON.parse(fs.readFileSync(path.join(full, f), 'utf8')), ids); } catch { /* unreadable */ }
    } else {
      /* html/txt backups are named for their target, sometimes with the FIELD
         appended: `<handle>-title-before.txt`, `<handle>-body-before.txt`.
         Stripping only `-before` left `…-title` and reported four logged wood
         corrections as unlogged. Third matcher artefact in this one script. */
      ids.add(f.replace(/-(title|body|description)?-?(before|after)\.(html|txt)$/, '').replace(/\.(html|txt)$/, ''));
    }
  }
  backups.push({ name, at, files, ids, label: files.join(', ') });
}
backups.sort((a, b) => (a.at?.getTime() || 0) - (b.at?.getTime() || 0));

const rowsAt = rows.map((r) => ({ r, t: new Date(r.at).getTime() }));

/* One backup against the log, as a pure function so constructed fixtures can hold it to account. */
function classify(b, rowsAt) {
  if (!b.at) return { logged: false, reason: 'backup directory has no parseable timestamp', how: 'none' };
  const t = b.at.getTime();
  const near = rowsAt.filter((x) => x.t >= t - 60_000 && x.t <= t + WINDOW_MS);
  const byId = near.filter((x) => {
    const h = x.r.handle, id = x.r.id;
    return (h && b.ids.has(h)) || (id && b.ids.has(id));
  });
  const scripts = b.files.flatMap((f) => LABEL_TO_SCRIPT[f] || []);
  const byScriptName = near.filter((x) => scripts.includes(x.r.script));
  if (!near.length) return { logged: false, reason: 'NO changelog row in the window at all', how: 'none' };
  if (!byId.length && !byScriptName.length) return { logged: false, reason: `${near.length} row(s) in the window, none matched by resource or by writing script`, how: 'none' };
  return { logged: true, how: byId.length ? 'resource' : 'script-name-only', rows: byId.length || byScriptName.length };
}

// 18i: constructed fixtures — a logged write matches, an unlogged one is reported, in every shape
{
  const T0 = Date.parse('2026-01-01T00:00:00Z');
  const bk = (ids, files = ['x-before.json'], at = new Date(T0)) => ({ at, ids: new Set(ids), files });
  const row = (min, r) => ({ r, t: T0 + min * 60_000 });
  const FIX = [
    ['same handle 5 min later is logged',        classify(bk(['h1']), [row(5, { handle: 'h1' })]).logged === true],
    ['same handle 2 hours later is NOT logged',  classify(bk(['h1']), [row(120, { handle: 'h1' })]).logged === false],
    ['other handle, no script: NOT logged',      classify(bk(['h1']), [row(5, { handle: 'h2' })]).logged === false],
    ['writing script via the label is logged',   classify(bk([], ['seo-fields-before.json']), [row(5, { script: 'apply-seo-fields' })]).how === 'script-name-only'],
    ['no timestamp is NOT logged',               classify(bk(['h1'], ['x.json'], null), [row(5, { handle: 'h1' })]).logged === false],
  ];
  const bad = FIX.filter(([, ok]) => !ok);
  for (const [l] of bad) console.error(`  FIXTURE FAIL ${l}`);
  if (bad.length) { console.error('refusing — changelog-integrity fixtures did not hold'); process.exit(1); }
}

const unlogged = [];
const matched = [];
for (const b of backups) {
  const c = classify(b, rowsAt);
  if (c.logged) matched.push({ b, how: c.how, rows: c.rows });
  else unlogged.push({ b, reason: c.reason, how: 'none' });
}

/* the reverse: a logged mutation with no recovery point near it */
const noBackup = [];
for (const x of rowsAt) {
  const has = backups.some((b) => {
    if (!b.at) return false;
    const inWindow = x.t >= b.at.getTime() - 60_000 && x.t <= b.at.getTime() + WINDOW_MS;
    if (!inWindow) return false;
    if ((x.r.handle && b.ids.has(x.r.handle)) || (x.r.id && b.ids.has(x.r.id))) return true;
    return b.files.some((f) => (LABEL_TO_SCRIPT[f] || []).includes(x.r.script));
  });
  if (!has) noBackup.push(x.r);
}

console.log(`changelog rows : ${rows.length}`);
console.log(`backup dirs    : ${backups.length}`);
console.log(`window         : −1 min to +${WINDOW_MS / 60000} min around each backup\n`);

console.log(`matched by resource : ${matched.filter(m=>m.how==='resource').length}`);
console.log(`matched by script only: ${matched.filter(m=>m.how!=='resource').length}\n`);
console.log(`── BACKUPS WITH NO MATCHING CHANGELOG ROW: ${unlogged.length} of ${backups.length}`);
for (const u of unlogged) console.log(`   ${u.b.name}  [${u.b.label}]  ${u.b.ids.size} resource(s)\n      ${u.reason}`);

const byScript = {};
for (const r of noBackup) { const k = r.script || '(no script field)'; byScript[k] = (byScript[k] || 0) + 1; }
console.log(`\n── CHANGELOG ROWS WITH NO BACKUP NEARBY: ${noBackup.length} of ${rows.length}`);
for (const [k, v] of Object.entries(byScript).sort((a, b) => b[1] - a[1])) console.log(`   ${String(v).padStart(4)}  ${k}`);

fs.writeFileSync(path.join(DATA, 'changelog-integrity.json'), JSON.stringify({
  _meta: { ran: new Date().toISOString(), windowMinutes: WINDOW_MS / 60000, rows: rows.length, backups: backups.length },
  backupsWithoutLog: unlogged.map((u) => ({ backup: u.b.name, files: u.b.files, resources: [...u.b.ids].slice(0, 40), reason: u.reason })),
  logRowsWithoutBackup: noBackup,
}, null, 2));
console.log('\nwrote data/changelog-integrity.json');

/* Round 18i: WARN-ONLY no longer. The six unlogged backups found on 18 September 2026 are accepted
   EXPLICITLY, by directory name, as the baseline — each was already reported and none is a new
   write. Any OTHER unlogged backup fails the run: an unlogged write is the finding this exists for.
   Adding a name here is a decision; do it with a reason, never to get a green run. */
const ACCEPTED_UNLOGGED = new Map([
  ['arcadia-backlink',          'baseline 2026-09-18: directory name carries no timestamp'],
  ['2026-09-08T16-37-06-467Z',  'baseline 2026-09-18: backup.json, no resolvable identifier'],
  ['2026-09-10T17-17-50-026Z',  'baseline 2026-09-18: delta-sentence.json'],
  ['2026-09-10T18-22-57-451Z',  'baseline 2026-09-18: alt-text.json (479 media ids)'],
  ['2026-09-15T22-25-33-001Z',  'baseline 2026-09-18: file-alts.json'],
  ['2026-09-16T13-47-31-924Z',  'baseline 2026-09-18: blog-redirects.json'],
]);
const newUnlogged = unlogged.filter((u) => !ACCEPTED_UNLOGGED.has(u.b.name));
const staleAccept = [...ACCEPTED_UNLOGGED.keys()].filter((n) => !unlogged.some((u) => u.b.name === n));
console.log(`\naccepted unlogged (baseline): ${unlogged.length - newUnlogged.length} of ${ACCEPTED_UNLOGGED.size} listed`);
if (staleAccept.length) console.log(`  note: accepted but no longer unlogged: ${staleAccept.join(', ')}`);
if (newUnlogged.length) {
  console.error(`\nFAIL — ${newUnlogged.length} unlogged backup(s) NOT on the accepted list:`);
  for (const u of newUnlogged) console.error(`   ${u.b.name}  [${u.b.label}]  ${u.reason}`);
  process.exitCode = 1;
}
