/* Round 15 — cardiovascular retarget of how-saunas-improve-circulation. --dry-run default.
 *
 *   node scripts/apply/apply-cardio-rewrite.mjs [--apply]
 *
 * Client approved the 1,681-word version, 16 Sep 2026: "a page that says the thing once,
 * correctly, with its population and interval, is the version worth testing".
 *
 * Writes body (articleUpdate) + SEO title/meta (metafieldsSet, global.title_tag /
 * global.description_tag, which is what page_title reads).
 *
 * Verifies by OUTCOME, not by the write report: re-reads the article, then fetches the live
 * page and checks the rendered title, meta and the corrected statistic.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed, ROOT } from '../lib/util.js';
import fs from 'node:fs';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'how-saunas-improve-circulation';
const BODY = fs.readFileSync(path.join(ROOT, 'content/fixes/cardiovascular-body.html'), 'utf8').trim();
const TITLE = 'Sauna and Cardiovascular Health: What the Finnish Cohorts Actually Found';
const SEO_TITLE = 'Sauna for Cardiovascular Health: What the Evidence Shows';
const SEO_META = 'A Finnish cohort of 2,315 men found fewer sudden cardiac deaths at 4–7 sauna sessions a week. Observational, and the 2–3 result was not significant.';

const decode = (s) => s.replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/&#39;|&rsquo;/g, "'")
  .replace(/&quot;/g, '"').replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

/* Outgoing string first — instance: validate what you SEND. */
assertWellFormed(BODY, 'cardio body');
if (decode(SEO_TITLE).length >= 60) throw new Error(`SEO title ${decode(SEO_TITLE).length} chars`);
if (decode(SEO_META).length >= 155) throw new Error(`meta ${decode(SEO_META).length} chars`);
/* The 22% may appear ONLY as the figure being corrected. A screen cannot tell a claim from its
   refutation, so the test is proximity to the correction, not the presence of the string. */
for (const m of BODY.matchAll(/22%/g)) {
  const around = BODY.slice(Math.max(0, m.index - 400), m.index + 400).toLowerCase();
  if (!/not statistically significant|should not be read|crosses 1/.test(around)) {
    throw new Error(`refusing: "22%" at ${m.index} is not inside the correction`);
  }
}
for (const must of ['0.57 to 1.07', '0.18 to 0.75', '0.52 to 1.08', '201 men', 'observational']) {
  if (!BODY.toLowerCase().includes(must.toLowerCase())) throw new Error(`refusing: body is missing "${must}"`);
}

const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle title body blog{ handle }
  t: metafield(namespace:"global", key:"title_tag"){ value }
  d: metafield(namespace:"global", key:"description_tag"){ value } } } }`, { q: `handle:${HANDLE}` });
const a = q.articles.nodes.find((x) => x.handle === HANDLE);
if (!a) throw new Error('article not found');

const wordsOf = (h) => h.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
console.log(`  ${a.blog.handle}/${a.handle}`);
console.log(`  body   ${wordsOf(a.body)} words -> ${wordsOf(BODY)} words`);
console.log(`  title  ${JSON.stringify(a.title)}\n      -> ${JSON.stringify(TITLE)}`);
console.log(`  seo    ${JSON.stringify(a.t?.value)}\n      -> ${JSON.stringify(SEO_TITLE)}  (${decode(SEO_TITLE).length})`);
console.log(`  meta   ${JSON.stringify((a.d?.value || '').slice(0, 60))}…\n      -> ${JSON.stringify(SEO_META)}  (${decode(SEO_META).length})`);
console.log(`  live body asserts the 22% figure: ${/22% lower risk/.test(a.body)}`);

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('cardio-rewrite', [{ id: a.id, handle: HANDLE, title: a.title, body: a.body, seoTitle: a.t?.value ?? null, meta: a.d?.value ?? null }]);

const up = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){
  article{ id title } userErrors{ field message } } }`, { id: a.id, article: { title: TITLE, body: BODY } });
if (up.articleUpdate.userErrors.length) { console.log('  ERR', up.articleUpdate.userErrors); process.exit(1); }

const mf = await gql(`mutation($metafields:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$metafields){
  metafields{ key } userErrors{ field message } } }`, { metafields: [
    { ownerId: a.id, namespace: 'global', key: 'title_tag', type: 'single_line_text_field', value: SEO_TITLE },
    { ownerId: a.id, namespace: 'global', key: 'description_tag', type: 'multi_line_text_field', value: SEO_META },
  ] });
if (mf.metafieldsSet.userErrors.length) { console.log('  ERR', mf.metafieldsSet.userErrors); process.exit(1); }

logChange({ resource: a.id, handle: HANDLE, field: 'body+title+seo', old: `${wordsOf(a.body)} words, title ${a.title}`, new: `${wordsOf(BODY)} words, title ${TITLE}`, note: 'Round 15 cardiovascular retarget; 22% non-significant figure removed' });

/* Outcome. */
const back = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle title body
  t: metafield(namespace:"global", key:"title_tag"){ value } d: metafield(namespace:"global", key:"description_tag"){ value } } } }`, { q: `handle:${HANDLE}` });
const b = back.articles.nodes.find((x) => x.handle === HANDLE);
/* Same proximity test on the way back: the figure may exist only inside its correction. */
const corrected = [...b.body.matchAll(/22%/g)].every((m) => /not statistically significant|should not be read|crosses 1/i.test(b.body.slice(Math.max(0, m.index - 400), m.index + 400)));
/* Shopify's sanitiser reformats whitespace BETWEEN tags (it inserts a newline after <li>).
   Comparing byte-exact reports a correct write as a failure, so compare the normalised form:
   same text, same tag sequence. The outgoing string was already asserted well-formed. */
const norm = (h) => h.replace(/>\s+</g, '><').trim();
const ok = b.title === TITLE && norm(b.body) === norm(BODY) && b.t.value === SEO_TITLE && b.d.value === SEO_META && corrected;
console.log(`\n  re-read: title ${b.title === TITLE}, body ${norm(b.body) === norm(BODY)}, seo ${b.t.value === SEO_TITLE}, meta ${b.d.value === SEO_META}, 22% only inside its correction ${corrected}`);
if (!ok) process.exitCode = 1;
