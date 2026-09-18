/* Round 18 RESTORE — put article bodies back exactly as they were before r18-unwrap-t1.
 *   node scripts/apply/r18-restore.mjs <backup.json> [--only <handle>] [--apply]
 *
 * Refuses per article if the LIVE body no longer equals what the unwrap stored — that means
 * someone edited it since, and restoring would silently revert their edit (the STALE state).
 * Proves each restore by read-back md5 against the backed-up before-state.
 */
import fs from 'node:fs';
import crypto from 'node:crypto';
import { gql } from '../lib/shopify.js';
import { logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const file = process.argv[2];
const ONLY = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;
if (!file || !fs.existsSync(file)) { console.log('usage: r18-restore.mjs <backup.json> [--only h] [--apply]'); process.exit(1); }
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const snap = JSON.parse(fs.readFileSync(file, 'utf8')).filter((s) => !ONLY || s.handle === ONLY);
if (!snap.length) { console.log('nothing matches'); process.exit(1); }
let bad = 0;
for (const s of snap) {
  const r = await gql(`query($id:ID!){ article(id:$id){ body } }`, { id: s.id });
  const live = md5(r.article.body);
  if (live === s.md5) { console.log(`  already restored  ${s.handle}`); continue; }
  const expect = s.storedMd5 || s.afterMd5;
  if (live !== expect) { console.log(`  REFUSE ${s.handle}: live ${live} is neither the before-state nor what the unwrap stored — edited since`); bad++; continue; }
  if (!APPLY) { console.log(`  would restore      ${s.handle}`); continue; }
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ body } userErrors{ message } } }`, { id: s.id, article: { body: s.before } });
  if (m.articleUpdate.userErrors.length) { console.log('  ERR', s.handle, m.articleUpdate.userErrors); bad++; continue; }
  const back = md5(m.articleUpdate.article.body);
  const ok = back === s.md5;
  console.log(`  ${ok ? 'RESTORED' : 'FAIL    '}  ${s.handle.padEnd(50)} read-back ${back} ${ok ? '== before-state' : '!= before ' + s.md5}`);
  if (!ok) bad++;
  logChange({ resource: s.id, handle: s.handle, field: 'body', old: 'Round 18 unwrapped', new: 'restored to pre-Round-18 body', note: `restore from ${file}` });
}
if (bad) process.exitCode = 1;
if (!APPLY) console.log('\n  DRY RUN — re-run with --apply');
