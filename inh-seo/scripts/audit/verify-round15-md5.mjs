/* MD5 read-back from the THEME against the local file. A successful API response is not
 * verification — this project has had a "byte-identical" report on a file that was never written. */
import fs from 'node:fs'; import path from 'node:path'; import crypto from 'node:crypto';
import { gql } from '../lib/shopify.js';
const themeId = `gid://shopify/OnlineStoreTheme/${process.argv[2]}`;
const files = process.argv.slice(3);
/* The first version declared $n and passed { names: files }. The variable never bound, the
 * filenames filter never applied, the query returned the first 25 files alphabetically, and all
 * seven targets reported "(absent)" against a theme that held them correctly.
 * A FALSE NEGATIVE — the safe direction, but a broken verifier either way. */
const r = await gql(`query($id:ID!,$names:[String!]){ theme(id:$id){ name role files(first:25, filenames:$names){ nodes{ filename checksumMd5 } } } }`, { id: themeId, names: files });
console.log(`  theme: ${r.theme.name}  role=${r.theme.role}\n`);
let bad = 0;
for (const f of files) {
  const remote = r.theme.files.nodes.find((x) => x.filename === f);
  const local = crypto.createHash('md5').update(fs.readFileSync(path.join('theme', f))).digest('hex');
  const ok = remote && remote.checksumMd5 === local;
  if (!ok) bad++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${f.padEnd(44)} local ${local}  theme ${remote?.checksumMd5 ?? '(absent)'}`);
}
console.log(bad ? `\n  ${bad} MISMATCH(ES)` : `\n  all ${files.length} files byte-identical in the theme`);
process.exitCode = bad ? 1 : 0;
