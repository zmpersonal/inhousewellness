/**
 * Applies SEO titles and meta descriptions to blog articles.
 *
 * Article SEO does not live on an `seo` field — Article has no such field in
 * API 2026-07. It lives in metafields `global.title_tag` and
 * `global.description_tag`, which is what the theme reads via `page_title`
 * and `page_description`.
 *
 * Input: data/article-seo.json — { "<article-handle>": { t, m } }
 *
 * Lengths are checked on the DECODED string per CLAUDE.md 6b: `&amp;` is five
 * characters stored and one rendered, so a raw count misreports both ways.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import {
  readJSON, DATA, parseArgs, banner, backup, logChange, showDiff,
  assertOneWritePerRecord,
} from '../lib/util.js';

const flags = parseArgs();
banner('apply-article-seo', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/article-seo.json');

const decode = (s) => (s || '')
  .replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

const spec = readJSON(path.join(DATA, 'article-seo.json'));

/* Read current state live. There is no article dump to go stale, so this is
   the read-back rather than a cached file. */
const Q = `query($after:String){
  articles(first:100, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{
      id handle title
      blog{ handle }
      t: metafield(namespace:"global", key:"title_tag"){ id value }
      d: metafield(namespace:"global", key:"description_tag"){ id value }
    }
  }
}`;
const live = [];
let cursor = null;
for (;;) {
  const d = await gql(Q, { after: cursor });
  live.push(...d.articles.nodes);
  if (!d.articles.pageInfo.hasNextPage) break;
  cursor = d.articles.pageInfo.endCursor;
}
const byHandle = new Map(live.map((a) => [a.handle, a]));

const targets = [];
const skipped = [];
for (const [handle, want] of Object.entries(spec)) {
  if (flags.only && !flags.only.includes(handle)) continue;
  const a = byHandle.get(handle);
  if (!a) { skipped.push([handle, 'no such article']); continue; }
  const curT = a.t?.value || null;
  const curD = a.d?.value || null;
  const change = {};
  if (want.t && want.t !== curT) change.t = want.t;
  // Guard audit 18i: this overwrote any existing meta that differed. CLAUDE.md: only fill null fields unless the task
  // says otherwise — so an existing value is left alone unless --overwrite is passed, and the skip is printed.
  const OVERWRITE = process.argv.includes('--overwrite');
  if (want.m && want.m !== curD) { if (curD && !OVERWRITE) skipped.push([handle, 'meta already set — fill-only (pass --overwrite to replace)']); else change.m = want.m; }
  if (!Object.keys(change).length) { skipped.push([handle, 'already matches — no-op']); continue; }
  targets.push({ a, curT, curD, change });
}

if (skipped.length) {
  console.log('Skipped:\n');
  for (const [h, why] of skipped) console.log(`  ${h.padEnd(50)} ${why}`);
  console.log('');
}
if (!targets.length) { console.log('Nothing to apply.'); process.exit(0); }

const over = [];
assertOneWritePerRecord(targets, (t) => t.a.handle, 'apply-article-seo');

for (const t of targets) {
  if (t.change.t && decode(t.change.t).length > 60) over.push(`${t.a.handle}: title ${decode(t.change.t).length} decoded (max 60)`);
  if (t.change.m && decode(t.change.m).length > 155) over.push(`${t.a.handle}: meta ${decode(t.change.m).length} decoded (max 155)`);
}
if (over.length) {
  console.error('REFUSING — over length on the decoded string:\n');   /* fail-ok: process.exit(1) three lines below */
  for (const o of over) console.error(`  ${o}`);
  console.error('\nShorten them or the SERP truncates. Lengths are decoded per CLAUDE.md 6b.');
  process.exit(1);
}

console.log(`${targets.length} article(s) to update:\n`);
for (const t of targets) {
  if (t.change.t) showDiff(`${t.a.blog.handle}/${t.a.handle} — SEO title (${decode(t.change.t).length} decoded)`, t.curT, t.change.t);
  if (t.change.m) showDiff(`${t.a.blog.handle}/${t.a.handle} — meta (${decode(t.change.m).length} decoded)`, t.curD, t.change.m);
}

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('article-seo-before', targets.map((t) => ({
  id: t.a.id, handle: t.a.handle, blog: t.a.blog.handle, titleTag: t.curT, descriptionTag: t.curD,
})));

const M = `mutation($metafields: [MetafieldsSetInput!]!){
  metafieldsSet(metafields: $metafields) {
    metafields { key value }
    userErrors { field message }
  }
}`;

let ok = 0;
for (const t of targets) {
  const metafields = [];
  if (t.change.t) metafields.push({ ownerId: t.a.id, namespace: 'global', key: 'title_tag', type: 'single_line_text_field', value: t.change.t });
  if (t.change.m) metafields.push({ ownerId: t.a.id, namespace: 'global', key: 'description_tag', type: 'multi_line_text_field', value: t.change.m });

  const r = await gql(M, { metafields });
  const errs = r.metafieldsSet.userErrors;
  if (errs.length) { console.error(`  FAILED ${t.a.handle}:`, errs); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */

  if (t.change.t) logChange({ script: 'apply-article-seo', kind: 'article', id: t.a.id, handle: t.a.handle, field: 'global.title_tag', before: t.curT, after: t.change.t });
  if (t.change.m) logChange({ script: 'apply-article-seo', kind: 'article', id: t.a.id, handle: t.a.handle, field: 'global.description_tag', before: t.curD, after: t.change.m });
  ok += 1;
  console.log(`  updated ${t.a.handle}`);
}
console.log(`\n${ok}/${targets.length} applied. Verify with a live fetch — the metafield is not the page.`);
