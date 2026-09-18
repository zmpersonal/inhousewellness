/**
 * Pushes theme changes to a NEW UNPUBLISHED theme. Never to MAIN — hard rule 2.
 *
 * Duplicates the live theme, writes the changed files into the copy, and stops.
 * A human publishes.
 *
 *   node scripts/apply/theme-branch.mjs "<branch name>" <file> [<file>…]           # dry run
 *   node scripts/apply/theme-branch.mjs "<branch name>" <file> [<file>…] --apply
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange, ROOT } from '../lib/util.js';

const flags = parseArgs();
banner('theme-branch', flags);
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
/* A file that does not exist live is legitimate — a new snippet has no previous
   version — but it must be DECLARED, not inferred from an empty read. Otherwise
   a typo in a filename looks identical to a new file and pushes a stray. */
const declaredNew = process.argv.filter((x) => x.startsWith('--new=')).map((x) => x.slice(6));
const branchName = args[0];
const files = args.slice(1);
if (!branchName || !files.length) { console.error('usage: theme-branch.mjs "<name>" <file>… [--apply]'); process.exit(1); }

const t = await gql(`query{ themes(first:50){ nodes{ id name role } } }`);
const main = t.themes.nodes.find((x) => x.role === 'MAIN');
if (!main) { console.error('No MAIN theme found.'); process.exit(1); }
console.log(`  live theme : ${main.name}  (${main.id})`);
console.log(`  new branch : "${branchName}"  — UNPUBLISHED, a human publishes\n`);

/* Read the CURRENT live content of each file so the diff is against the store,
   not against whatever the local checkout happens to hold. Instance 14: a local
   file is a belief about the theme. */
for (const f of files) {
  const local = fs.readFileSync(path.join(ROOT, 'theme', f), 'utf8');
  const r = await gql(`query($id:ID!,$fn:[String!]){ theme(id:$id){ files(first:1, filenames:$fn){ nodes{ filename body{ ... on OnlineStoreThemeFileBodyText { content } } } } } }`,
    { id: main.id, fn: [f] });
  const liveNode = r.theme?.files?.nodes?.[0];
  const live = liveNode?.body?.content ?? '';
  if (!live && !declaredNew.includes(f)) {
    console.error(`  ✗ ${f}: not present on the live theme and not declared new.`);
    console.error(`     If it is genuinely new, pass --new=${f}. If it is not, check the filename.`);
    process.exit(1);
  }
  if (!live) { console.log(`  + ${f}: NEW FILE (declared), ${local.length} chars — no live version to diff against`); continue; }
  if (live === local) { console.log(`  = ${f}: identical to live, nothing to push`); continue; }
  console.log(`  ± ${f}   live ${live.length} -> local ${local.length} chars`);
  /* show only the changed region */
  let i = 0; while (i < Math.min(live.length, local.length) && live[i] === local[i]) i++;
  let j = 0; while (j < Math.min(live.length, local.length) - i && live[live.length-1-j] === local[local.length-1-j]) j++;
  console.log(`      - ${JSON.stringify(live.slice(i, live.length - j)).slice(0, 300)}`);
  console.log(`      + ${JSON.stringify(local.slice(i, local.length - j)).slice(0, 700)}`);
}

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

const dup = await gql(`mutation($id:ID!,$name:String){ themeDuplicate(id:$id, name:$name){ newTheme{ id name role } userErrors{ field message } } }`,
  { id: main.id, name: branchName });
if (dup.themeDuplicate.userErrors?.length) { console.error(dup.themeDuplicate.userErrors); process.exit(1); }
const branch = dup.themeDuplicate.newTheme;
console.log(`\n  created ${branch.name}  ${branch.id}  role=${branch.role}`);
if (branch.role === 'MAIN') { console.error('  REFUSING to continue — the duplicate is MAIN.'); process.exit(1); }

/* Guard audit 18i: themeDuplicate returns immediately and copies in the background (CLAUDE.md: a branch snapshotted
   mid-copy held 431 of 558 files). Upserting into a half-copied duplicate races the copy. Poll the file count to
   MAIN's before pushing anything, and refuse after ~5 minutes rather than push into a short branch. */
const countFiles = async (id) => { let n = 0, c = null; do { const r = await gql(`query($id:ID!,$c:String){ theme(id:$id){ files(first:250, after:$c){ nodes{ filename } pageInfo{ hasNextPage endCursor } } } }`, { id, c }); n += r.theme.files.nodes.length; c = r.theme.files.pageInfo.hasNextPage ? r.theme.files.pageInfo.endCursor : null; } while (c); return n; };
const want = await countFiles(main.id);
for (let k = 0; ; k++) { const have = await countFiles(branch.id); console.log(`  copy: ${have}/${want} files`); if (have >= want) break; if (k >= 30) { console.error('  REFUSING — duplicate never reached MAIN\'s file count; it is a broken preview, not a draft.'); process.exit(1); } await new Promise((r) => setTimeout(r, 10000)); }
const upserts = files.map((f) => ({ filename: f, body: { type: 'TEXT', value: fs.readFileSync(path.join(ROOT, 'theme', f), 'utf8') } }));
const up = await gql(`mutation($id:ID!,$files:[OnlineStoreThemeFilesUpsertFileInput!]!){
  themeFilesUpsert(themeId:$id, files:$files){ upsertedThemeFiles{ filename } userErrors{ filename message } } }`,
  { id: branch.id, files: upserts });
if (up.themeFilesUpsert.userErrors?.length) { console.error(up.themeFilesUpsert.userErrors); process.exit(1); }
for (const f of up.themeFilesUpsert.upsertedThemeFiles) console.log(`  pushed ${f.filename}`);
{ // guard audit 18i: MD5 read-back, and every requested file must be among those upserted
  const got = up.themeFilesUpsert.upsertedThemeFiles.map((f) => f.filename);
  const missing = files.filter((f) => !got.includes(f)); if (missing.length) { console.error(`  ✗ not upserted: ${missing.join(', ')}`); process.exitCode = 1; }
  const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
  const back = await gql(`query($id:ID!,$f:[String!]!){ theme(id:$id){ files(filenames:$f, first:50){ nodes{ filename checksumMd5 } } } }`, { id: branch.id, f: files });
  for (const f of files) { const n = back.theme.files.nodes.find((x) => x.filename === f); const w = md5(fs.readFileSync(path.join(ROOT, 'theme', f), 'utf8')); const ok = n && n.checksumMd5 === w; console.log(`  ${ok ? 'md5 ok ' : 'MD5 MISMATCH'} ${f}`); if (!ok) process.exitCode = 1; }
}
logChange({ script: 'theme-branch', kind: 'theme', id: branch.id, handle: branchName, field: 'files',
  before: `duplicated from ${main.name}`, after: files.join(', '), reason: 'Unpublished branch. A human publishes — hard rule 2.' });

const id = branch.id.split('/').pop();
console.log(`\n  PREVIEW: https://inhousewellness.com/?preview_theme_id=${id}`);
console.log('  NOT PUBLISHED. A human publishes.');
