/**
 * Pushes files into an EXISTING unpublished theme branch, retrying while a
 * themeDuplicate job is still copying.
 *
 * themeDuplicate is ASYNCHRONOUS. It returns a theme id immediately and copies
 * files in the background, so an upsert issued straight afterwards can fail with
 * "Section type 'main-blog' does not refer to an existing section file" — the
 * section has not landed yet. That is a race, not a bad file.
 *
 *   node scripts/apply/theme-push.mjs <themeId> <file>… [--apply]
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, logChange, ROOT } from '../lib/util.js';

const flags = parseArgs();
banner('theme-push', flags);
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const themeId = args[0].startsWith('gid://') ? args[0] : `gid://shopify/OnlineStoreTheme/${args[0]}`;
const files = args.slice(1);

const t = await gql(`query($id:ID!){ theme(id:$id){ id name role } }`, { id: themeId });
console.log(`  target: ${t.theme.name}  role=${t.theme.role}`);
if (t.theme.role === 'MAIN') { console.error('  REFUSING — that is the live theme. Hard rule 2.'); process.exit(1); }
if (!flags.apply) { console.log(`  would push: ${files.join(', ')}\n\nDry run. Re-run with --apply.`); process.exit(0); }

const M = `mutation($id:ID!,$files:[OnlineStoreThemeFilesUpsertFileInput!]!){
  themeFilesUpsert(themeId:$id, files:$files){ upsertedThemeFiles{ filename } userErrors{ filename message } } }`;

const pushed = [];
for (const f of files) {
  const body = fs.readFileSync(path.join(ROOT, 'theme', f), 'utf8');
  let done = false;
  for (let attempt = 1; attempt <= 6 && !done; attempt++) {
    const r = await gql(M, { id: themeId, files: [{ filename: f, body: { type: 'TEXT', value: body } }] });
    const errs = r.themeFilesUpsert.userErrors || [];
    if (!errs.length) { done = true; pushed.push(f); console.log(`  pushed ${f}`); break; }
    const racing = errs.some((e) => /does not refer to an existing section file/i.test(e.message));
    if (!racing) { console.error(`  ✗ ${f}:`, errs); break; }   /* fail-ok: `done` stays false, and the !done branch below sets exitCode */
    console.log(`  … ${f}: duplicate still copying (attempt ${attempt}), waiting 10s`);
    await new Promise((r2) => setTimeout(r2, 10000));
  }
  if (!done) { console.error(`  ✗ ${f}: not pushed`); process.exitCode = 1; }   // guard audit 18i: was print-only, exit 0
}
/* Guard audit 18i: MD5 READ-BACK. "userErrors empty" says the write was accepted, not that the bytes landed. */
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
if (pushed.length) {
  const back = await gql(`query($id:ID!,$f:[String!]!){ theme(id:$id){ files(filenames:$f, first:50){ nodes{ filename checksumMd5 } } } }`, { id: themeId, f: pushed });
  for (const f of pushed) {
    const n = back.theme.files.nodes.find((x) => x.filename === f);
    const want = md5(fs.readFileSync(path.join(ROOT, 'theme', f), 'utf8'));
    const ok = n && n.checksumMd5 === want;
    console.log(`  ${ok ? 'md5 ok ' : 'MD5 MISMATCH'} ${f}  ${n ? n.checksumMd5 : '(absent)'}${ok ? '' : ' != ' + want}`);
    if (!ok) process.exitCode = 1;
  }
}
logChange({ script: 'theme-push', kind: 'theme', id: themeId, handle: t.theme.name, field: 'files',
  before: '(unpublished branch)', after: pushed.join(', ') + (pushed.length < files.length ? `  (NOT pushed: ${files.filter((f) => !pushed.includes(f)).join(', ')})` : ''), reason: 'Hard rule 2 — unpublished branch, a human publishes.' });
console.log(`\n  PREVIEW: https://inhousewellness.com/?preview_theme_id=${themeId.split('/').pop()}`);
console.log('  NOT PUBLISHED.');
