/* strip-editor-attrs — ATTRIBUTE DELETION ONLY.
 *
 * Removes editor residue attributes from product descriptions. It removes
 * ATTRIBUTES from tags. It never removes, adds or unwraps an element, so it
 * cannot change what a reader sees.
 *
 * That property is not asserted, it is CHECKED: every target must come out with
 * identical visible text and identical tag counts, or the whole batch refuses.
 * Any product whose visible text changes is a defect in this pass by definition —
 * there is no legitimate reason for one.
 *
 * Span unwrapping is a SEPARATE pass. Those spans wrap real copy and that is
 * where a mistake eats a sentence. Do not add it here.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, showDiff, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';

const flags = parseArgs();
banner('strip-editor-attrs', flags);

const batchArg = (() => { const i = process.argv.indexOf('--batch'); return i > -1 ? process.argv[i + 1] : null; })();
if (!batchArg) { console.error('--batch <n> is required. This script never runs across the estate.'); process.exit(1); }
const plan = readJSON(path.join(DATA, 'residue-batches.json'));
const batch = plan.batches.find((b) => b.batch === batchArg);
if (!batch) { console.error(`no batch "${batchArg}"`); process.exit(1); }
console.log(`  batch ${batch.batch}: ${batch.label}`);
console.log(`  products: ${batch.handles.length}\n`);

const ATTRS = [
  / data-start="[^"]*"/g,
  / data-end="[^"]*"/g,
  / data-is-only-node="[^"]*"/g,
  / data-is-last-node="[^"]*"/g,
  / class=""/g,
];

/* What a reader sees, and the document's shape. Both must survive untouched. */
const visible = (h) => h.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const shape = (h) => ['p', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'strong', 'em', 'a', 'img', 'span', 'div', 'table', 'tr', 'td', 'br', 'hr']
  .map((t) => `${t}:${(h.match(new RegExp(`<${t}\\b`, 'gi')) || []).length}`).join(' ');

const Q = `query($q:String!){ products(first:50, query:$q){ nodes{ id handle title descriptionHtml } } }`;
const targets = [];
let hardFail = false;

for (const h of batch.handles) {
  const r = await gql(Q, { q: `handle:${h}` });
  const p = r.products.nodes.find((n) => n.handle === h);
  if (!p) { console.error(`  ✗ ${h}: NOT FOUND live`); hardFail = true; continue; }
  const before = p.descriptionHtml || '';
  let after = before, n = 0;
  for (const re of ATTRS) { const m = before.match(re); if (m) n += m.length; after = after.replace(re, ''); }
  if (n === 0) { console.error(`  ✗ ${h}: ZERO matches — the plan is stale for this handle. Not a skip.`); hardFail = true; continue; }

  /* THE CHECK THIS PASS EXISTS TO PASS */
  if (visible(before) !== visible(after)) {
    console.error(`  ✗ ${h}: VISIBLE TEXT CHANGED — attribute deletion must never do this.`);
    hardFail = true; continue;
  }
  if (shape(before) !== shape(after)) {
    console.error(`  ✗ ${h}: TAG COUNTS CHANGED\n      before ${shape(before)}\n      after  ${shape(after)}`);
    hardFail = true; continue;
  }
  assertWellFormed(after, `${h} description`, before);
  targets.push({ p, before, after, n });
}

console.log(`  ${targets.length} clean, ${batch.handles.length - targets.length} refused\n`);
for (const t of targets.slice(0, 3)) showDiff(t.p.handle, t.before, t.after);
if (targets.length > 3) console.log(`  … ${targets.length - 3} more diffs not shown\n`);

const bytes = targets.reduce((a, t) => a + (t.before.length - t.after.length), 0);
const attrs = targets.reduce((a, t) => a + t.n, 0);
console.log(`  ${attrs} attributes removed, ${bytes} bytes, across ${targets.length} products`);
console.log(`  visible text: unchanged on all ${targets.length}   tag counts: unchanged on all ${targets.length}`);

if (hardFail) { console.error('\nAt least one target failed. NOTHING APPLIED — fix the plan or re-dump.'); process.exit(1); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
assertOneWritePerRecord(targets, (t) => t.p.handle, `strip-editor-attrs batch ${batch.batch}`);
backup(`editor-attrs-batch-${batch.batch}-before`, targets.map((t) => ({ id: t.p.id, handle: t.p.handle, title: t.p.title, descriptionHtml: t.before })));

const M = `mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id handle } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { input: { id: t.p.id, descriptionHtml: t.after } });
  if (r.productUpdate.userErrors.length) { console.error(`  FAILED ${t.p.handle}:`, r.productUpdate.userErrors); continue; }
  logChange({ resource: t.p.id, handle: t.p.handle, field: 'descriptionHtml', before: t.before, after: t.after, note: `batch ${batch.batch}: removed ${t.n} editor residue attributes` });
  ok += 1;
}
console.log(`\n${ok}/${targets.length} updated.`);
