/* Pull theme files FROM a theme into the local theme/ checkout.
 *   node scripts/apply/theme-pull.mjs <themeId> <file>…
 *
 * WHY THIS EXISTS. theme/ is in .gitignore, so `git checkout -- theme/` silently does nothing —
 * it exits non-zero with "pathspec did not match any file(s) known to git" and leaves the working
 * copy modified. I read that as a revert and re-ran a build over already-built files, which
 * inserted a second aggregateRating block into layout/theme.liquid.
 *
 * The authoritative baseline for an untracked theme checkout is the THEME, not git.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { gql } from '../lib/shopify.js';

const ROOT = path.resolve('.');
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const themeId = args[0].startsWith('gid://') ? args[0] : `gid://shopify/OnlineStoreTheme/${args[0]}`;
const files = args.slice(1);

const t = await gql(`query($id:ID!){ theme(id:$id){ name role } }`, { id: themeId });
console.log(`  source: ${t.theme.name}  role=${t.theme.role}`);

const Q = `query($id:ID!,$names:[String!]){ theme(id:$id){ files(first:25, filenames:$names){
  nodes{ filename checksumMd5 body{ ... on OnlineStoreThemeFileBodyText { content } } } } } }`;

const r = await gql(Q, { id: themeId, names: files });
const got = r.theme.files.nodes;
console.log(`  requested ${files.length}, returned ${got.length}`);
let missing = files.filter((f) => !got.some((g) => g.filename === f));
if (missing.length) { console.log('  MISSING from the theme:', missing.join(', ')); process.exitCode = 1; }

for (const f of got) {
  const content = f.body?.content;
  if (content == null) { console.log(`  ✗ ${f.filename}: no text body returned`); process.exitCode = 1; continue; }
  const p = path.join(ROOT, 'theme', f.filename);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, content);
  const localMd5 = crypto.createHash('md5').update(fs.readFileSync(p)).digest('hex');
  const match = localMd5 === f.checksumMd5;
  console.log(`  ${match ? 'ok  ' : 'FAIL'} ${f.filename.padEnd(44)} local ${localMd5}  theme ${f.checksumMd5}`);
  if (!match) process.exitCode = 1;
}
