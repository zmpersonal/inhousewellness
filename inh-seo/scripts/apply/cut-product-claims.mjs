/**
 * Cuts health claims from product descriptions and substitutes a sourced fact.
 *
 * The edit spec is HAND-WRITTEN per product in data/product-claim-edits.json.
 * Nothing here generates copy: the script matches exact strings, refuses on a
 * miss, and runs the residue checks. Cut by script, substitute by hand.
 *
 * Residue, per instances 41 and 41-at-section-level:
 *   - emptied <li>/<p>            — swept, and only when this edit emptied them
 *   - a heading whose section is gone — declared per product, never inferred
 *   - a lead-in colon pointing at nothing — reported for a human read
 *
 *   node scripts/apply/cut-product-claims.mjs <vendor>            # dry run
 *   node scripts/apply/cut-product-claims.mjs <vendor> --apply
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, assertWellFormed } from '../lib/util.js';

const flags = parseArgs();
const vendor = process.argv[2];
if (!vendor || vendor.startsWith('--')) { console.error('usage: cut-product-claims.mjs <vendor> [--apply]'); process.exit(1); }
banner('cut-product-claims', flags);
console.log(`  READS FROM: data/product-claim-edits.json   VENDOR: ${vendor}`);

const spec = readJSON(path.join(DATA, 'product-claim-edits.json'));
const jobs = spec.edits.filter((e) => e.vendor === vendor);
if (!jobs.length) { console.error(`no edits for vendor "${vendor}"`); process.exit(1); }

const Q = `query($h:String!){ products(first:5, query:$h){ nodes{ id handle title status descriptionHtml } } }`;
const targets = [], misses = [];
for (const j of jobs) {
  const d = await gql(Q, { h: `handle:${j.handle}` });
  const p = d.products.nodes.find((x) => x.handle === j.handle);
  if (!p) { misses.push([j.handle, 'no such product']); continue; }
  let body = p.descriptionHtml || '';
  const notFound = []; let alreadyGone = 0;

  /* whole sections first — a heading whose only purpose was the claim */
  for (const h of j.cutSections || []) {
    const re = new RegExp(`<h[234][^>]*>[\\s\\S]{0,140}?${h.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')}[\\s\\S]*?(?=<h[234]|$)`, 'i');
    if (!re.test(body)) { notFound.push(`section "${h}"`); continue; }
    body = body.replace(re, '');
  }
  /* then exact-string cuts and substitutions */
  for (const [from, to] of j.subs || []) {
    if (to !== '' && body.includes(to)) continue;              // already applied
    /* A DELETION (to === '') leaves nothing to detect. Once applied, its `from`
       is gone and a re-run cannot distinguish "already done" from "stale spec".
       Treat an absent from-string on a deletion as done, and say how many so a
       genuinely stale spec still shows up in the output. */
    if (!body.includes(from)) {
      if (to === '') { alreadyGone += 1; continue; }
      notFound.push(`"${from.slice(0, 46)}…"`); continue;
    }
    body = body.split(from).join(to);
  }

  /* residue: elements this edit emptied */
  const EMPTY = /<(li|p)\b[^>]*>\s*<\/\1>/gi;
  const before = (String(p.descriptionHtml).match(EMPTY) || []).length;
  const after = (body.match(EMPTY) || []).length;
  let swept = 0;
  if (after > before) { swept = after - before; body = body.replace(EMPTY, ''); }

  /* residue a machine cannot judge: a colon pointing at nothing */
  const dangling = [...body.matchAll(/([A-Z][A-Za-z ,'-]{3,60}):\s*(?:<\/[a-z]+>|<[a-z]|$)/g)].map((m) => m[1]);

  if (notFound.length) misses.push([j.handle, notFound.join(' · ')]);
  targets.push({ p, body, j, swept, dangling, alreadyGone, cut: (j.subs || []).length, secs: (j.cutSections || []).length });
}

if (misses.length) {
  console.error(`\nREFUSING — ${misses.length} anchor(s) not found. A hand-written cut that does not match is a stale spec, not a skip:\n`);
  misses.forEach(([h, w]) => console.error(`  ${h}\n     ${w}`));
  process.exit(1);
}

console.log(`\n${targets.length} product(s):\n`);
for (const t of targets) {
  const w = (s) => s.replace(/<[^>]+>/g, ' ').trim().split(/\s+/).length;
  console.log(`  [${t.p.status.slice(0, 4)}] ${t.p.handle.slice(0, 46).padEnd(48)} ${w(t.p.descriptionHtml)} -> ${w(t.body)} words   ${t.cut} sub · ${t.secs} section(s)${t.swept ? ` · swept ${t.swept}` : ''}${t.alreadyGone ? ` · ${t.alreadyGone} already gone` : ''}`);
  if (t.dangling.length) console.log(`        ⚠ colon pointing at nothing, read before applying: ${t.dangling.join(' | ')}`);
  assertWellFormed(t.body, t.p.handle, t.p.descriptionHtml);
}

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
backup(`product-claims-${vendor.replace(/\W+/g, '-')}-before`, targets.map((t) => ({ id: t.p.id, handle: t.p.handle, status: t.p.status, descriptionHtml: t.p.descriptionHtml })));

const M = `mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { input: { id: t.p.id, descriptionHtml: t.body } });
  if (r.productUpdate.userErrors.length) { console.error(`  FAILED ${t.p.handle}:`, r.productUpdate.userErrors); continue; }
  logChange({ script: 'cut-product-claims', kind: 'product', id: t.p.id, handle: t.p.handle, field: 'descriptionHtml',
    before: `${t.p.descriptionHtml.length} chars`, after: `${t.body.length} chars, ${t.cut} substitution(s), ${t.secs} section(s) removed` });
  ok += 1;
  console.log(`  updated ${t.p.handle}`);
}
console.log(`\n${ok}/${targets.length} applied.`);
