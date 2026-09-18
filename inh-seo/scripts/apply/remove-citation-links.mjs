/* remove-citation-links — remove assistant citation pills INCLUDING their anchors.
 *
 * The pill wraps the anchor, so removing the markup and removing the link are the
 * same edit. Doing them in two passes would be two writes to one record, which is
 * instance 62. One clean edit per product.
 *
 * Uses a balanced-span walk, not a lazy regex: the anchors contain nested <span>
 * elements, and `[\s\S]*?</span></span>` would terminate on the first inner pair
 * and leave a broken fragment behind.
 */
import { gql } from '../lib/shopify.js';
import {
  parseArgs, banner, backup, logChange, showDiff,
  assertWellFormed, assertOneWritePerRecord,
} from '../lib/util.js';

const flags = parseArgs();
banner('remove-citation-links', flags);

const only = (() => { const i = process.argv.indexOf('--only'); return i > -1 ? process.argv[i + 1].split(',') : null; })();
if (!only) { console.error('--only <handle,…> is required.'); process.exit(1); }

const OPEN = /<span class=""(?:\s+data-state="closed")?>\s*<span\b[^>]*(?:animate-\[show_150ms_ease-in\]|webpage-citation-pill)[^>]*>/;

/* Walk forward from `from` counting span opens and closes; return the index just
   past the close that balances the first open. Returns -1 if never balanced. */
function endOfSpan(html, from) {
  const tag = /<\/?span\b[^>]*>/g;
  tag.lastIndex = from;
  let depth = 0, m;
  while ((m = tag.exec(html))) {
    depth += m[0].startsWith('</') ? -1 : 1;
    if (depth === 0) return m.index + m[0].length;
  }
  return -1;
}

function stripPills(html) {
  let out = html, removed = [], guard = 0;
  for (;;) {
    if (guard++ > 200) throw new Error('runaway pill removal — aborting');
    const m = out.match(OPEN);
    if (!m) break;
    const start = m.index;
    const end = endOfSpan(out, start);
    if (end === -1) throw new Error('unbalanced pill markup — refusing to guess');
    const el = out.slice(start, end);
    removed.push(el);
    /* Collapse a doubled space left where the pill sat mid-sentence. */
    out = (out.slice(0, start) + out.slice(end)).replace(/ {2,}/g, ' ');
  }
  return { out, removed };
}

const Q = `query($q:String!){ products(first:5, query:$q){ nodes{ id handle title descriptionHtml } } }`;
const targets = [];
let hardFail = false;

for (const h of only) {
  const r = await gql(Q, { q: `handle:${h}` });
  const p = r.products.nodes.find((n) => n.handle === h);
  if (!p) { console.error(`  ✗ ${h}: NOT FOUND live`); hardFail = true; continue; }
  const before = p.descriptionHtml || '';
  const { out: after, removed } = stripPills(before);
  if (!removed.length) { console.error(`  ✗ ${h}: ZERO pills — nothing to remove. Not a skip.`); hardFail = true; continue; }

  const hrefsBefore = [...before.matchAll(/href="([^"]+)"/gi)].map((x) => x[1]);
  const hrefsAfter = [...after.matchAll(/href="([^"]+)"/gi)].map((x) => x[1]);
  const gone = hrefsBefore.filter((u) => !hrefsAfter.includes(u));

  console.log(`\n  ${h}`);
  console.log(`    pills removed : ${removed.length}`);
  console.log(`    hrefs         : ${hrefsBefore.length} → ${hrefsAfter.length}`);
  for (const u of gone) console.log(`      − ${u.slice(0, 110)}`);
  if (hrefsAfter.length) for (const u of hrefsAfter) console.log(`      = KEPT ${u.slice(0, 110)}`);
  assertWellFormed(after, `${h} description`, before);
  targets.push({ p, before, after, n: removed.length, gone });
}

if (hardFail) { console.error('\nAt least one target failed. Nothing applied.'); process.exit(1); }
assertOneWritePerRecord(targets, (t) => t.p.handle, 'remove-citation-links');
for (const t of targets) showDiff(t.p.handle, t.before, t.after);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('citation-links-before', targets.map((t) => ({ id: t.p.id, handle: t.p.handle, title: t.p.title, descriptionHtml: t.before })));

const M = `mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id handle } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { input: { id: t.p.id, descriptionHtml: t.after } });
  if (r.productUpdate.userErrors.length) { console.error(`  FAILED ${t.p.handle}:`, r.productUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ resource: t.p.id, handle: t.p.handle, field: 'descriptionHtml', before: t.before, after: t.after, note: `removed ${t.n} citation pill(s); links dropped: ${t.gone.join(' | ')}` });
  console.log(`  updated ${t.p.handle}`);
  ok += 1;
}
console.log(`\n${ok}/${targets.length} updated.`);
