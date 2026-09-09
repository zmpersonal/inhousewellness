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

const unlogged = [];
const matched = [];
for (const b of backups) {
  if (!b.at) { unlogged.push({ b, reason: 'backup directory has no parseable timestamp' }); continue; }
  const t = b.at.getTime();
  const near = rowsAt.filter((x) => x.t >= t - 60_000 && x.t <= t + WINDOW_MS);
  const byId = near.filter((x) => {
    const h = x.r.handle, id = x.r.id;
    return (h && b.ids.has(h)) || (id && b.ids.has(id));
  });
  const scripts = b.files.flatMap((f) => LABEL_TO_SCRIPT[f] || []);
  const byScriptName = near.filter((x) => scripts.includes(x.r.script));
  if (!near.length) unlogged.push({ b, reason: 'NO changelog row in the window at all', how: 'none' });
  else if (!byId.length && !byScriptName.length) unlogged.push({ b, reason: `${near.length} row(s) in the window, none matched by resource or by writing script`, how: 'none' });
  else matched.push({ b, how: byId.length ? 'resource' : 'script-name-only', rows: byId.length || byScriptName.length });
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
