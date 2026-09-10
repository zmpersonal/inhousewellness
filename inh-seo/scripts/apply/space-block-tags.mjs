/* space-block-tags — insert a newline after each closing block tag in collection
 * descriptions, so that any surface which renders by stripping tags does not glue
 * the last word of one block to the first word of the next.
 *
 * Shopify stores `</p><h2>` with no whitespace. On the storefront that is fine —
 * the theme renders the elements. On every surface that strips tags (the admin's
 * text previews, feeds, extraction) it produces "…gets used.Read the capacity…".
 *
 * This adds whitespace only. It never adds, removes or reorders an element, and
 * the outgoing string is checked to prove it: word sequence identical, tag counts
 * identical, or the batch refuses.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, assertWellFormed, assertOneWritePerRecord, assertFresh } from '../lib/util.js';

const flags = parseArgs();
banner('space-block-tags', flags);
assertFresh({ 'collections.json': 'npm run audit:collections' });

const BLOCK = /<\/(p|h2|h3|h4|ul|ol|li|blockquote)>(?=<)/g;
const words = (h) => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const shape = (h) => ['p','h2','h3','h4','ul','ol','li','strong','em','a','br'].map((t) => `${t}:${(h.match(new RegExp(`<${t}\\b`, 'gi')) || []).length}`).join(' ');

const local = readJSON(path.join(DATA, 'collections.json'));
const candidates = local.filter((c) => (c.descriptionHtml || '').match(BLOCK)).map((c) => c.handle);
console.log(`  collections with glued block boundaries: ${candidates.length}\n`);
if (!candidates.length) { console.log('  nothing to do.'); process.exit(0); }

const r = await gql(`query{ collections(first:250){ nodes{ id handle title descriptionHtml } } }`);
const live = new Map(r.collections.nodes.map((c) => [c.handle, c]));

const targets = [];
let hardFail = false;
for (const h of candidates) {
  const c = live.get(h);
  if (!c) { console.error(`  ✗ ${h}: NOT FOUND live`); hardFail = true; continue; }
  const before = c.descriptionHtml || '';
  const n = (before.match(BLOCK) || []).length;
  if (!n) { console.log(`  = ${h}: already spaced live, dump was stale — skipping`); continue; }
  const after = before.replace(BLOCK, (m) => `${m}\n`);
  if (words(before) !== words(after)) { console.error(`  ✗ ${h}: WORD SEQUENCE CHANGED`); hardFail = true; continue; }
  if (shape(before) !== shape(after)) { console.error(`  ✗ ${h}: TAG COUNTS CHANGED`); hardFail = true; continue; }
  assertWellFormed(after, `${h} description`, before);
  targets.push({ c, before, after, n });
}

const tot = targets.reduce((a, t) => a + t.n, 0);
console.log(`  ${targets.length} collections, ${tot} boundaries to space`);
console.log(`  word sequence: unchanged on all ${targets.length}   tag counts: unchanged on all ${targets.length}`);
for (const t of targets.slice(0, 3)) {
  const b = words(t.before).slice(0, 0);
  const glued = t.before.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').match(/[a-z.]["’]?[A-Z][a-z]+/g) || [];
  console.log(`    ${t.c.handle.padEnd(30)} ${t.n} boundaries   collapse before: ${glued.slice(0, 3).join(', ') || 'none'}`);
}

if (hardFail) { console.error('\nAt least one target failed. NOTHING APPLIED.'); process.exit(1); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
assertOneWritePerRecord(targets, (t) => t.c.handle, 'space-block-tags');
backup('block-tag-spacing-before', targets.map((t) => ({ id: t.c.id, handle: t.c.handle, title: t.c.title, descriptionHtml: t.before })));

const M = `mutation($input:CollectionInput!){ collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const res = await gql(M, { input: { id: t.c.id, descriptionHtml: t.after } });
  if (res.collectionUpdate.userErrors.length) { console.error(`  FAILED ${t.c.handle}:`, res.collectionUpdate.userErrors); continue; }
  logChange({ resource: t.c.id, handle: t.c.handle, field: 'descriptionHtml', before: t.before, after: t.after, note: `spaced ${t.n} block-tag boundaries` });
  ok += 1;
}
console.log(`\n${ok}/${targets.length} updated.`);
