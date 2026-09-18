/**
 * Publishes a drafted article from content/articles/*.md to a Shopify blog.
 *
 * The markdown file is front matter + HTML body. The front matter is the record
 * of what was approved and what each figure was derived from; only the body is
 * published. SEO title and meta go to metafields global.title_tag /
 * global.description_tag, because Article has no `seo` field in API 2026-07 —
 * same finding as apply-article-seo.js.
 *
 * Idempotent: if the handle already exists on that blog, the run updates it
 * rather than creating a second article.
 *
 *   node scripts/apply/publish-article.js <slug>            # dry run
 *   node scripts/apply/publish-article.js <slug> --apply
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach, makeFetch, reachAllowFromArgv, mergeCaptures, captureArticleMetafields, ARTICLE_REACH_QUERY } from '../lib/reach.mjs';
import { ROOT, parseArgs, banner, backup, logChange, assertWellFormed } from '../lib/util.js';

const flags = parseArgs();
const slug = process.argv[2];
if (!slug || slug.startsWith('--')) { console.error('usage: publish-article.js <slug> [--apply]'); process.exit(1); }
banner('publish-article', flags);

const file = path.join(ROOT, 'content', 'articles', `${slug}.md`);
console.log(`  READS FROM: ${path.relative(ROOT, file)}`);
const raw = fs.readFileSync(file, 'utf8');
const parts = raw.split(/^---$/m);
const fm = parts[1];
const body = parts.slice(2).join('---').trim();

const field = (k) => (fm.match(new RegExp(`^${k}:\\s*"?(.+?)"?\\s*$`, 'm')) || [])[1];
const blogHandle = field('blog');
const title = field('title');
const seoTitle = field('seo_title');
const meta = field('meta');
const author = field('author') || 'Casey Bennet';

const decode = (s) => (s || '').replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"').replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

for (const [k, v] of Object.entries({ blog: blogHandle, title, seo_title: seoTitle, meta }))
  if (!v) { console.error(`REFUSING — front matter is missing "${k}".`); process.exit(1); }
if (decode(seoTitle).length > 60) { console.error(`REFUSING — seo_title is ${decode(seoTitle).length} decoded (max 60).`); process.exit(1); }
if (decode(meta).length > 155) { console.error(`REFUSING — meta is ${decode(meta).length} decoded (max 155).`); process.exit(1); }
if (!body.length) { console.error('REFUSING — empty body.'); process.exit(1); }

const blogs = await gql('{blogs(first:20){nodes{id handle}}}');
const blog = blogs.blogs.nodes.find((b) => b.handle === blogHandle);
if (!blog) { console.error(`REFUSING — no blog with handle "${blogHandle}".`); process.exit(1); }

/* Does it already exist? Creating a second article on the same handle is how you
   end up with two URLs competing for one keyword. */
const existing = await gql(`query($h:String!){ articles(first:25, query:$h){ nodes{ id handle title body blog{ handle } } } }`, { h: `handle:${slug}` });
/* Guard audit 18i: the lookup matched the handle on ANY blog, so an UPDATE could land on an article in another blog,
   and the backup stored no body — the update path had no recoverable before-state. Handle AND blog now; a same-handle
   article on a different blog refuses; the backup carries the body. */
const sameHandle = existing.articles.nodes.filter((a) => a.handle === slug);
const hit = sameHandle.find((a) => a.blog.handle === blogHandle);
const elsewhere = sameHandle.filter((a) => a.blog.handle !== blogHandle);
if (elsewhere.length) { console.error(`REFUSING — handle "${slug}" already exists on blog(s) ${elsewhere.map((a) => a.blog.handle).join(', ')}; publishing here would create a competing URL.`); process.exit(1); }

console.log(`\n  blog        ${blogHandle}  (${blog.id})`);
console.log(`  handle      ${slug}${hit ? '   [EXISTS — will UPDATE]' : '   [new]'}`);
console.log(`  title       ${title}`);
console.log(`  seo_title   ${seoTitle}  (${decode(seoTitle).length} decoded)`);
console.log(`  meta        ${meta}  (${decode(meta).length} decoded)`);
console.log(`  author      ${author}`);
console.log(`  body        ${body.length} chars, ${body.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length} words`);
const links = [...body.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
console.log(`  links       ${links.join('\n              ')}`);

assertWellFormed(body, `${slug} body`);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('article-publish-before', [{ slug, blog: blogHandle, existing: hit ? { id: hit.id, handle: hit.handle, title: hit.title, body: hit.body } : null }]);

/* REACH GUARD — reports/reach-guard.md. A publish is the widest write in the
   repo: it can create a duplicate on the wrong blog, or update an article it
   was not aiming at. `*` on the field list because a NEW article legitimately
   changes every field it has — what must not move is any OTHER article. */
const _fetchFields = makeFetch(gql, ARTICLE_REACH_QUERY, 'articles');
/* This script calls metafieldsSet as well as articleCreate/articleUpdate, and
   article SEO lives in metafields because Article has no `seo` field. An article
   capture alone would have passed while the SEO title and meta moved — the
   fix-membership defect in a second costume. */
const _fetchReach = async () => _fetchFields();
const _reachBefore = mergeCaptures(await captureReach(_fetchFields), await captureArticleMetafields(gql));
const _reachDeclared = { handles: [slug], fields: ['*'] };


let id;
if (hit) {
  const r = await gql(`mutation($id:ID!, $a:ArticleUpdateInput!){ articleUpdate(id:$id, article:$a){ article{ id handle } userErrors{ field message } } }`,
    { id: hit.id, a: { title, body, author: { name: author } } });
  if (r.articleUpdate.userErrors.length) { console.error(r.articleUpdate.userErrors); process.exit(1); }
  id = r.articleUpdate.article.id;
  console.log(`  updated ${id}`);
} else {
  const r = await gql(`mutation($a:ArticleCreateInput!){ articleCreate(article:$a){ article{ id handle } userErrors{ field message } } }`,
    { a: { blogId: blog.id, title, handle: slug, body, author: { name: author }, isPublished: true } });
  if (r.articleCreate.userErrors.length) { console.error(r.articleCreate.userErrors); process.exit(1); }
  id = r.articleCreate.article.id;
  console.log(`  created ${id}`);
}

const mf = await gql(`mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }`, {
  m: [
    { ownerId: id, namespace: 'global', key: 'title_tag', type: 'single_line_text_field', value: seoTitle },
    { ownerId: id, namespace: 'global', key: 'description_tag', type: 'multi_line_text_field', value: meta },
  ],
});
if (mf.metafieldsSet.userErrors.length) { console.error(mf.metafieldsSet.userErrors); process.exit(1); }
logChange({ script: 'publish-article', kind: 'article', id, handle: slug, field: 'article', before: hit ? '(existing)' : '(none)', after: `${title} — ${body.length} chars` });
console.log(`\nDone. Verify with a live fetch — the field is not the page (instance 31).`);

const _reachAfter = mergeCaptures(await captureReach(_fetchFields), await captureArticleMetafields(gql));
/* A newly created article is absent from the BEFORE capture, which assertReach
   reports as VANISHED-in-reverse. That is expected for a create, so the
   declared handle is excluded from the vanished check by pre-seeding it. */
if (!_reachBefore.has(slug) && _reachAfter.has(slug)) _reachBefore.set(slug, _reachAfter.get(slug));
try {
  assertReach(_reachBefore, _reachAfter, _reachDeclared, { allow: reachAllowFromArgv() });
} catch (e) {
  console.error(`\n${e.message}`);
  console.error('The reach capture holds the full before-state of every article. Roll back from it.');
  process.exit(1);
}
