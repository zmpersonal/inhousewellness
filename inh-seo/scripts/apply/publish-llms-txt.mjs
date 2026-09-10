/* publish-llms-txt — content/llms.txt -> a Shopify page, plus /llms.txt redirect.
 *
 * Shopify serves no arbitrary root files (robots.txt.liquid is the only override,
 * and overriding it to add one comment line risks the whole robots file for no
 * gain). So: a page at /pages/llms-txt holding the text verbatim, and a URL
 * redirect from /llms.txt so the canonical path resolves. Agents following
 * /llms.txt get a 301 to the content.
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { ROOT, parseArgs, banner, backup, logChange } from '../lib/util.js';

const flags = parseArgs();
banner('publish-llms-txt', flags);

const text = fs.readFileSync(path.join(ROOT, 'content', 'llms.txt'), 'utf8');
const HANDLE = 'llms-txt';
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const body = `<pre style="white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px;line-height:1.5">${esc(text)}</pre>`;

const q = await gql(`query($q:String!){ pages(first:5, query:$q){ nodes{ id handle title } } }`, { q: `handle:${HANDLE}` });
const existing = q.pages.nodes.find((n) => n.handle === HANDLE);

const r = await gql(`query{ urlRedirects(first:250, query:"path:/llms.txt"){ nodes{ id path target } } }`);
const redirect = r.urlRedirects.nodes.find((n) => n.path === '/llms.txt');

console.log(`  source      : content/llms.txt  (${text.length} chars, ${text.split('\n').length} lines)`);
console.log(`  page        : ${existing ? `EXISTS ${existing.id}` : 'will be CREATED'}  /pages/${HANDLE}`);
console.log(`  redirect    : ${redirect ? `EXISTS -> ${redirect.target}` : 'will be CREATED'}  /llms.txt -> /pages/${HANDLE}`);
console.log(`\n  first 6 lines:`);
for (const l of text.split('\n').slice(0, 6)) console.log(`    | ${l}`);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

if (existing) backup('llms-page-before', [{ id: existing.id, handle: existing.handle }]);

let pageId = existing?.id;
if (existing) {
  const m = await gql(`mutation($id:ID!,$page:PageUpdateInput!){ pageUpdate(id:$id, page:$page){ page{ id handle } userErrors{ field message } } }`,
    { id: existing.id, page: { title: 'llms.txt', body } });
  if (m.pageUpdate.userErrors.length) { console.error(m.pageUpdate.userErrors); process.exit(1); }
  console.log(`  updated page ${m.pageUpdate.page.handle}`);
} else {
  const m = await gql(`mutation($page:PageCreateInput!){ pageCreate(page:$page){ page{ id handle } userErrors{ field message } } }`,
    { page: { title: 'llms.txt', handle: HANDLE, body, isPublished: true } });
  if (m.pageCreate.userErrors.length) { console.error(m.pageCreate.userErrors); process.exit(1); }
  pageId = m.pageCreate.page.id;
  console.log(`  created page /pages/${m.pageCreate.page.handle}`);
}
logChange({ resource: pageId, handle: HANDLE, field: 'body', before: existing ? '(previous page body)' : '(none)', after: `llms.txt, ${text.length} chars`, note: 'llms.txt published as a page' });

if (!redirect) {
  const m = await gql(`mutation($r:UrlRedirectInput!){ urlRedirectCreate(urlRedirect:$r){ urlRedirect{ id path target } userErrors{ field message } } }`,
    { r: { path: '/llms.txt', target: `/pages/${HANDLE}` } });
  if (m.urlRedirectCreate.userErrors.length) { console.error(m.urlRedirectCreate.userErrors); process.exit(1); }
  console.log(`  created redirect ${m.urlRedirectCreate.urlRedirect.path} -> ${m.urlRedirectCreate.urlRedirect.target}`);
  logChange({ resource: m.urlRedirectCreate.urlRedirect.id, handle: '/llms.txt', field: 'urlRedirect', before: '(none)', after: `/pages/${HANDLE}`, note: 'llms.txt root path' });
} else {
  console.log(`  redirect already present`);
}
