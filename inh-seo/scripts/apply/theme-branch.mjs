/**
 * Pushes theme changes to a NEW UNPUBLISHED theme. Never to MAIN — hard rule 2.
 *
 * Duplicates the live theme, writes the changed files into the copy, and stops.
 * A human publishes.
 *
 *   node scripts/apply/theme-branch.mjs "<branch name>" <file> [<file>…]           # dry run
 *   node scripts/apply/theme-branch.mjs "<branch name>" <file> [<file>…] --apply
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange, ROOT } from '../lib/util.js';

const flags = parseArgs();
banner('theme-branch', flags);
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
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
  if (!live) { console.error(`  ✗ ${f}: could not read live content — refusing to push a file I cannot diff`); process.exit(1); }
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

const upserts = files.map((f) => ({ filename: f, body: { type: 'TEXT', value: fs.readFileSync(path.join(ROOT, 'theme', f), 'utf8') } }));
const up = await gql(`mutation($id:ID!,$files:[OnlineStoreThemeFilesUpsertFileInput!]!){
  themeFilesUpsert(themeId:$id, files:$files){ upsertedThemeFiles{ filename } userErrors{ filename message } } }`,
  { id: branch.id, files: upserts });
if (up.themeFilesUpsert.userErrors?.length) { console.error(up.themeFilesUpsert.userErrors); process.exit(1); }
for (const f of up.themeFilesUpsert.upsertedThemeFiles) console.log(`  pushed ${f.filename}`);
logChange({ script: 'theme-branch', kind: 'theme', id: branch.id, handle: branchName, field: 'files',
  before: `duplicated from ${main.name}`, after: files.join(', '), reason: 'Unpublished branch. A human publishes — hard rule 2.' });

const id = branch.id.split('/').pop();
console.log(`\n  PREVIEW: https://inhousewellness.com/?preview_theme_id=${id}`);
console.log('  NOT PUBLISHED. A human publishes.');
