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
// Round 18i: PRODUCT mode. A backup record with kind:'product' restores descriptionHtml; everything else — the guard,
// the no-op, the md5 read-back against the before-state — is the same code path the article restores proved.
async function readLive(s) {
  if (s.kind === 'product') return (await gql(`query($id:ID!){ product(id:$id){ descriptionHtml } }`, { id: s.id })).product.descriptionHtml;
  return (await gql(`query($id:ID!){ article(id:$id){ body } }`, { id: s.id })).article.body;
}
async function writeBack(s) {
  if (s.kind === 'product') {
    const m = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ descriptionHtml } userErrors{ message } } }`, { p: { id: s.id, descriptionHtml: s.before } });
    if (m.productUpdate.userErrors.length) { console.log('  ERR', s.handle, m.productUpdate.userErrors); return null; }
    return m.productUpdate.product.descriptionHtml;
  }
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ body } userErrors{ message } } }`, { id: s.id, article: { body: s.before } });
  if (m.articleUpdate.userErrors.length) { console.log('  ERR', s.handle, m.articleUpdate.userErrors); return null; }
  return m.articleUpdate.article.body;
}
// --premise: read-only. Exit 0 only if LIVE matches NEITHER recorded state for every record — the condition under
// which a refusal proves anything (Round 18i: a tamper that moved one recorded state left live matching the other).
if (process.argv.includes('--premise')) {
  let held = 0;
  for (const s of snap) { const live = md5(await readLive(s));
    const hit = live === s.md5 ? 'the before-state' : live === (s.storedMd5 || s.afterMd5) ? 'the stored after-state' : null;
    console.log(`  ${hit ? 'PREMISE FAILS' : 'premise holds'}  ${s.handle}  live ${live}${hit ? ' matches ' + hit : ''}`); if (!hit) held++; }
  process.exit(held === snap.length ? 0 : 1);
}
let bad = 0;
for (const s of snap) {
  const live = md5(await readLive(s));
  if (live === s.md5) { console.log(`  already restored  ${s.handle}`); continue; }
  const expect = s.storedMd5 || s.afterMd5;
  if (live !== expect) { console.log(`  REFUSE ${s.handle}: live ${live} is neither the before-state nor what the unwrap stored — edited since`); bad++; continue; }
  if (!APPLY) { console.log(`  would restore      ${s.handle}`); continue; }
  const written = await writeBack(s);
  if (written === null) { bad++; continue; }
  const back = md5(written);
  const ok = back === s.md5;
  console.log(`  ${ok ? 'RESTORED' : 'FAIL    '}  ${s.handle.padEnd(50)} read-back ${back} ${ok ? '== before-state' : '!= before ' + s.md5}`);
  if (!ok) bad++;
  logChange({ resource: s.id, handle: s.handle, field: 'body', old: 'Round 18 unwrapped', new: 'restored to pre-Round-18 body', note: `restore from ${file}` });
}
if (bad) process.exitCode = 1;
if (!APPLY) console.log('\n  DRY RUN — re-run with --apply');
