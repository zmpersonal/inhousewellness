/* strip-assistant-markup — remove EMPTY assistant citation-pill markup from
 * product descriptions.
 *
 * Scope is deliberately narrow. It removes only spans that are immediately
 * closed and therefore contain nothing:
 *
 *     <span … animate-[show_150ms_ease-in]"></span>
 *     <span data-testid="webpage-citation-pill" …></span>
 *
 * A span wrapping an <a> cannot match `></span>`, so a live link is
 * structurally out of reach of this script. That is the point: the link
 * decision is the client's and is not entangled with removing dead markup.
 *
 * It does NOT touch data-start / data-end, which sit on 292 further products
 * and are a separate, larger scope decision. See reports/assistant-pasted-copy.md.
 */
import { gql } from '../lib/shopify.js';
import {
  parseArgs, banner, backup, logChange, showDiff,
  assertWellFormed, assertOneWritePerRecord,
} from '../lib/util.js';

const flags = parseArgs();
banner('strip-assistant-markup', flags);
/* No assertFresh here, deliberately. That guard protects scripts that write FROM
   a dump; this one queries the live product and edits what it gets back, so a
   stale dump cannot reach the write. Calling it with the right argument shape
   just to satisfy the checklist would be decoration. */

const only = (() => { const i = process.argv.indexOf('--only'); return i > -1 ? process.argv[i + 1].split(',') : null; })();
if (!only) { console.error('--only <handle,handle,…> is required. This script never runs across the catalogue by default.'); process.exit(1); }

const Q = `query($q:String!){ products(first:50, query:$q){ nodes{ id handle title descriptionHtml } } }`;
const live = new Map();
for (const h of only) {
  const r = await gql(Q, { q: `handle:${h}` });
  for (const n of r.products.nodes) if (only.includes(n.handle)) live.set(n.handle, n);
}
console.log(`  live products fetched: ${live.size} of ${only.length}\n`);

/* Stage 1: the empty pill itself. Stage 2: a wrapper left empty by stage 1.
   Ordered, because stage 2 only becomes true after stage 1 runs. */
const EMPTY_PILL = /<span\b[^>]*(?:animate-\[show_150ms_ease-in\]|webpage-citation-pill)[^>]*><\/span>/g;
const EMPTY_WRAP = /<span class=""(?:\s+data-state="closed")?><\/span>/g;

const targets = [];
let hardFail = false;
for (const h of only) {
  const p = live.get(h);
  if (!p) { console.error(`  ✗ ${h}: NOT FOUND live`); hardFail = true; continue; }
  const before = p.descriptionHtml || '';
  const n1 = (before.match(EMPTY_PILL) || []).length;
  if (n1 === 0) { console.error(`  ✗ ${h}: ZERO matches — nothing to strip. Not a skip.`); hardFail = true; continue; }
  let after = before.replace(EMPTY_PILL, '');
  const n2 = (after.match(EMPTY_WRAP) || []).length;
  after = after.replace(EMPTY_WRAP, '');
  console.log(`  ${h}: ${n1} empty pill(s), ${n2} emptied wrapper(s) — ${before.length} → ${after.length} chars`);
  assertWellFormed(after, `${h} description`, before);
  targets.push({ p, before, after, n1, n2 });
}

if (hardFail) { console.error('\nAt least one target failed. Nothing applied.'); process.exit(1); }
assertOneWritePerRecord(targets, (t) => t.p.handle, 'strip-assistant-markup');

for (const t of targets) showDiff(t.p.handle, t.before, t.after);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('assistant-markup-before', targets.map((t) => ({ id: t.p.id, handle: t.p.handle, title: t.p.title, descriptionHtml: t.before })));

const M = `mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id handle } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { input: { id: t.p.id, descriptionHtml: t.after } });
  if (r.productUpdate.userErrors.length) { console.error(`  FAILED ${t.p.handle}:`, r.productUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ resource: t.p.id, handle: t.p.handle, field: 'descriptionHtml', before: t.before, after: t.after, note: `stripped ${t.n1} empty assistant citation pill(s)` });
  console.log(`  updated ${t.p.handle}`);
  ok += 1;
}
console.log(`\n${ok}/${targets.length} updated.`);
