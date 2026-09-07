/**
 * Applies collection descriptions from content/collections/{handle}.md
 * Markdown files are written by the drafting step and reviewed by a human
 * BEFORE this runs. A file must contain the line "status: approved" in its
 * front matter or it is skipped.
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { readJSON, DATA, CONTENT, parseArgs, banner, backup, logChange, showDiff, cleanHTML, assertFresh } from '../lib/util.js';

const flags = parseArgs();
banner('apply-collection-copy', flags);

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
for (const t of targets) {
  const words = t.html.replace(/<[^>]+>/g,' ').trim().split(/\s+/).length;
  const warn = words < 120 || words > 340 ? `  << ${words} words, outside 150-300 target` : `  (${words} words)`;
  showDiff(`${t.c.handle}${warn}`, t.c.descriptionHtml, t.html);
}

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('collection-copy-before', targets.map(t=>({ id:t.c.id, handle:t.c.handle, descriptionHtml:t.c.descriptionHtml })));

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
