/* Round 15 — publish the two articles whose handles already carry 37 inbound links.
 * --dry-run default. Client approved both drafts 16 Sep 2026.
 *
 *   node scripts/apply/publish-orphan-articles.mjs [--apply]
 *
 * The handles are not arbitrary: 23 internal links point at are-saunas-good-for-you and 14 at
 * how-often-should-you-use-sauna. Publishing at the original handles is what makes those 37
 * links resolve without editing 71 articles.
 *
 * ⚠ are-saunas-good-for-you has a STORE REDIRECT to "/". A Shopify url redirect can intercept
 * a live resource, so after publishing this script checks whether the URL serves the article
 * or still 301s. We cannot delete the redirect: the token lacks write_online_store_navigation.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed, ROOT } from '../lib/util.js';
import fs from 'node:fs';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');
const BLOG = 'gid://shopify/Blog/90393149507';           // saunas
const AUTHOR = 'Riley Thompson';                          // house convention on this blog
const decode = (s) => s.replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/&#39;|&rsquo;/g, "'")
  .replace(/&quot;/g, '"').replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

const ARTICLES = [
  { handle: 'are-saunas-good-for-you',
    file: 'content/fixes/are-saunas-good-for-you.html',
    title: 'Are Saunas Good for You? What the Evidence Shows, and What It Does Not',
    seoTitle: 'Are Saunas Good for You? What the Evidence Shows',
    meta: 'Mostly yes. The strongest evidence is observational: 4–7 sessions a week in 2,315 Finnish men. Benefit and safety are separate questions.',
    inbound: 23 },
  { handle: 'how-often-should-you-use-sauna',
    file: 'content/fixes/how-often-should-you-use-sauna.html',
    title: 'How Often Should You Use a Sauna? Science-Backed Frequency Guide',
    seoTitle: 'How Often Should You Use a Sauna? What the Studies Show',
    meta: 'Four to seven sessions a week is the only frequency that reached significance in the Finnish cohorts. Sessions over 19 minutes: HR 0.48 (0.31–0.75).',
    inbound: 14 },
];

for (const a of ARTICLES) {
  a.body = fs.readFileSync(path.join(ROOT, a.file), 'utf8').trim();
  assertWellFormed(a.body, a.handle);
  if (decode(a.seoTitle).length >= 60) throw new Error(`${a.handle}: SEO title ${decode(a.seoTitle).length}`);
  if (decode(a.meta).length >= 155) throw new Error(`${a.handle}: meta ${decode(a.meta).length}`);
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle } } }`, { q: `handle:${a.handle}` });
  if (q.articles.nodes.some((x) => x.handle === a.handle)) throw new Error(`${a.handle}: an article already exists`);
  console.log(`  ${a.handle}`);
  console.log(`     H1   ${a.title}`);
  console.log(`     SEO  ${a.seoTitle}  (${decode(a.seoTitle).length})`);
  console.log(`     meta ${a.meta}  (${decode(a.meta).length})`);
  console.log(`     body ${a.body.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length} words, ${a.inbound} inbound links waiting`);
}

if (!APPLY) { console.log('\n  DRY RUN — nothing published. Re-run with --apply.\n'); process.exit(0); }

backup('orphan-articles', ARTICLES.map((a) => ({ handle: a.handle, title: a.title, words: a.body.length })));

for (const a of ARTICLES) {
  const r = await gql(`mutation($article:ArticleCreateInput!){ articleCreate(article:$article){
    article{ id handle title isPublished } userErrors{ field message } } }`, {
      article: { blogId: BLOG, handle: a.handle, title: a.title, body: a.body,
        author: { name: AUTHOR }, isPublished: true, publishDate: new Date().toISOString() },
    });
  if (r.articleCreate.userErrors.length) { console.log(`  ERR ${a.handle}`, r.articleCreate.userErrors); process.exitCode = 1; continue; }
  a.id = r.articleCreate.article.id;
  const mf = await gql(`mutation($metafields:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$metafields){ metafields{ key } userErrors{ field message } } }`, {
    metafields: [
      { ownerId: a.id, namespace: 'global', key: 'title_tag', type: 'single_line_text_field', value: a.seoTitle },
      { ownerId: a.id, namespace: 'global', key: 'description_tag', type: 'multi_line_text_field', value: a.meta },
    ] });
  if (mf.metafieldsSet.userErrors.length) { console.log(`  ERR meta ${a.handle}`, mf.metafieldsSet.userErrors); process.exitCode = 1; }
  logChange({ resource: a.id, handle: a.handle, field: 'article', old: '(did not exist — 404/redirect with inbound links)', new: `${a.title}`, note: `Round 15 orphan article published at original handle; ${a.inbound} inbound links` });
  console.log(`  created ${a.handle}  ${a.id}  published=${r.articleCreate.article.isPublished}`);
}

/* Outcome: does the URL actually serve the article? The redirect question is the whole risk. */
console.log('');
for (const a of ARTICLES) {
  const res = await fetch(`https://inhousewellness.com/blogs/saunas/${a.handle}`, { redirect: 'manual', headers: { 'User-Agent': 'Mozilla/5.0 (compatible; inh-seo-audit)' } });
  if (res.status === 200) {
    const html = await res.text();
    const title = (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '';
    const meta = (html.match(/<meta\s+name="description"\s+content="([^"]*)"/) || [])[1] || '';
    console.log(`  ${a.handle}: 200`);
    console.log(`     title ${JSON.stringify(decode(title.replace(/\s+/g, ' ').trim()))} ${decode(title.replace(/\s+/g, ' ').trim()) === a.seoTitle ? 'MATCH' : 'MISMATCH'}`);
    console.log(`     meta  ${decode(meta) === a.meta ? 'MATCH' : 'MISMATCH'}`);
    if (decode(title.replace(/\s+/g, ' ').trim()) !== a.seoTitle || decode(meta) !== a.meta) process.exitCode = 1;   // guard audit 18i: MISMATCH was print-only
  } else {
    console.log(`  ${a.handle}: ${res.status} -> ${res.headers.get('location')}   ⚠ the store redirect is intercepting the live article`);
    process.exitCode = 1;
  }
}
