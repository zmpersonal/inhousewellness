/**
 * Applies collection descriptions from content/collections/{handle}.md
 * Markdown files are written by the drafting step and reviewed by a human
 * BEFORE this runs. A file must contain the line "status: approved" in its
 * front matter or it is skipped.
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach } from '../lib/reach.mjs';
import { readJSON, DATA, CONTENT, parseArgs, banner, backup, logChange, showDiff, cleanHTML, assertFresh, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';

const flags = parseArgs();
banner('apply-collection-copy', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/collections.json');

assertFresh({ 'collections.json': 'npm run audit:collections' });

const dir = path.join(CONTENT,'collections');
if (!fs.existsSync(dir)) { console.log('No content/collections/ directory.'); process.exit(0); }

const collections = readJSON(path.join(DATA,'collections.json'));
const byHandle = new Map(collections.map(c=>[c.handle,c]));

const files = fs.readdirSync(dir).filter(f=>f.endsWith('.md'));
const targets = [];
const skipped = [];

for (const f of files) {
  const handle = f.replace(/\.md$/,'');
  if (flags.only && !flags.only.includes(handle)) continue;
  const raw = fs.readFileSync(path.join(dir,f),'utf8');
  const fm = raw.match(/^---\n([\s\S]*?)\n---\n/);
  const body = fm ? raw.slice(fm[0].length) : raw;
  const approved = fm && /status:\s*approved/i.test(fm[1]);
  const c = byHandle.get(handle);
  if (!c) { skipped.push([handle,'no such collection']); continue; }
  if (!approved) { skipped.push([handle,'not marked "status: approved"']); continue; }
  targets.push({ c, html: cleanHTML(mdToHtml(body)) });
}

function mdToHtml(md) {
  return md.trim()
    .replace(/^### (.+)$/gm,'<h3>$1</h3>')
    .replace(/^## (.+)$/gm,'<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\[(.+?)\]\((.+?)\)/g,'<a href="$2">$1</a>')
    .split(/\n{2,}/)
    .map(b => /^<(h2|h3|ul|ol)/.test(b.trim()) ? b : `<p>${b.trim().replace(/\n/g,' ')}</p>`)
    .join('');
}

if (skipped.length) {
  console.log('Skipped:\n');
  for (const [h,why] of skipped) console.log(`  ${h.padEnd(34)} ${why}`);
  console.log('');
}
if (!targets.length) { console.log('Nothing approved to apply.'); process.exit(0); }

console.log(`${targets.length} approved description(s):\n`);
assertOneWritePerRecord(targets, (t) => t.c.handle, 'apply-collection-copy');

for (const t of targets) {
  const words = t.html.replace(/<[^>]+>/g,' ').trim().split(/\s+/).length;
  const warn = words < 120 || words > 340 ? `  << ${words} words, outside 150-300 target` : `  (${words} words)`;
  showDiff(`${t.c.handle}${warn}`, t.c.descriptionHtml, t.html);
}

/* Instance 38: assert on the OUTGOING string. A clean read-back afterwards
   would be the platform's repair, not this change. */
for (const t of targets) assertWellFormed(t.html, `${t.c.handle} description`, t.c.descriptionHtml);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('collection-copy-before', targets.map(t=>({ id:t.c.id, handle:t.c.handle, descriptionHtml:t.c.descriptionHtml })));

/* REACH GUARD — see reports/reach-guard.md. Captures the WHOLE collection object
   for every record this batch could touch, not the field the plan names. The
   capture doubles as the rollback source. Instance 55 is the reason: an unscoped
   run here reverted three C4 cluster links while 53 rows were byte-identical
   no-ops, and nothing said so. */
const REACH_QUERY = `query($after:String){ collections(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle title descriptionHtml sortOrder templateSuffix seo{ title description } } } }`;
const fetchReach = async () => {
  const out = []; let after = null, more = true;
  while (more) { const r = await gql(REACH_QUERY, { after }); out.push(...r.collections.nodes);
    more = r.collections.pageInfo.hasNextPage; after = r.collections.pageInfo.endCursor; }
  return out;
};
const reachBefore = await captureReach(fetchReach);
const reachDeclared = { handles: targets.map((t) => t.c.handle), fields: ["descriptionHtml"] };
const reachOk = (() => { const i = process.argv.indexOf('--reach-ok'); return i > -1 ? process.argv[i + 1].split(',') : []; })();


const M = `mutation($input: CollectionInput!){
  collectionUpdate(input:$input){ collection{ id handle } userErrors{ field message } }
}`;

for (const t of targets) {
  const r = await gql(M, { input: { id: t.c.id, descriptionHtml: t.html } });
  if (r.collectionUpdate.userErrors.length) { console.error(`  FAILED ${t.c.handle}`, r.collectionUpdate.userErrors); continue; }
  logChange({ script:'apply-collection-copy', kind:'collection', id:t.c.id, handle:t.c.handle,
              field:'descriptionHtml', before:t.c.descriptionHtml, after:t.html });
  console.log(`  applied ${t.c.handle}`);
}

const reachAfter = await captureReach(fetchReach);
try {
  assertReach(reachBefore, reachAfter, reachDeclared, { allow: reachOk });
} catch (e) {
  console.error(`\n${e.message}`);
  console.error('The reach capture holds the full before-state of every collection. Roll back from it.');
  process.exit(1);
}
