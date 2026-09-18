/* Round 18 — PRE-STATE SNAPSHOT + structural context for every external link.
 * READ-ONLY. Changes nothing.
 *
 * Population : all live articles from the Admin API (the dump is stale by 2 — Round 17)
 * Pattern    : /<a\b[^>]*href="([^"]+)"/gi over article.body, external hosts only
 * Source     : Shopify Admin API 2026-07, live at run time
 *
 * ALSO answers the two CHECK-FIRST questions, because they decide whether an edit is a
 * content edit at all:
 *   - is the URL inside <script type="application/ld+json"> (a SCHEMA change, and it
 *     interacts with the Round 15 aggregateRating work) rather than body markup?
 *   - is the anchor a button, an image wrapper, or a comparison-table cell rather than
 *     inline prose? Each unwraps differently.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';

const MULTI_SUFFIX = new Set(['com.au','net.au','org.au','edu.au','gov.au','co.uk','org.uk','ac.uk','gov.uk','me.uk','co.nz','org.nz','govt.nz','co.za','co.jp','ne.jp','or.jp','ac.jp','go.jp','com.br','com.mx','com.ar','com.sg','com.my','com.hk','com.tw','com.cn','org.cn','co.in','co.kr','com.tr','co.il','com.pl','com.ua','com.ph','co.th','com.vn','com.co','com.pe','com.ve']);
const reg = (host) => {
  const h = host.toLowerCase().replace(/^www\./, '');
  const p = h.split('.');
  if (p.length <= 2) return h;
  const lastTwo = p.slice(-2).join('.');
  return MULTI_SUFFIX.has(lastTwo) ? p.slice(-3).join('.') : lastTwo;
};

// ── constructed fixtures: region detection must catch cases the body may not contain ──
const regionsOf = (body) => {
  const R = [];
  for (const m of body.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>[\s\S]*?<\/script>/gi)) R.push(['JSON-LD', m.index, m.index + m[0].length]);
  for (const m of body.matchAll(/<table\b[\s\S]*?<\/table>/gi)) R.push(['TABLE', m.index, m.index + m[0].length]);
  for (const m of body.matchAll(/<(?:script|style)\b[^>]*>[\s\S]*?<\/(?:script|style)>/gi)) R.push(['SCRIPT/STYLE', m.index, m.index + m[0].length]);
  return R;
};
const FIX = [
  ['ld+json region found',     regionsOf('<script type="application/ld+json">{"a":1}</script>').some(r => r[0] === 'JSON-LD')],
  ['single-quoted type too',   regionsOf("<script type='application/ld+json'>{}</script>").some(r => r[0] === 'JSON-LD')],
  ['table region found',       regionsOf('<table><tr><td>x</td></tr></table>').some(r => r[0] === 'TABLE')],
  ['plain prose has no region',regionsOf('<p>hello <a href="https://x.com">x</a></p>').length === 0],
];
let bad = 0;
console.log('FIXTURES');
for (const [l, ok] of FIX) { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${l}`); if (!ok) bad++; }
if (bad) { console.log('refusing'); process.exit(1); }

// ── population ──
let cur = null; const arts = [];
while (true) {
  const r = await gql(`query($c:String){ articles(first:250, after:$c){ pageInfo{hasNextPage endCursor} nodes{ id handle title isPublished body blog{handle} } } }`, { c: cur });
  arts.push(...r.articles.nodes);
  if (!r.articles.pageInfo.hasNextPage) break;
  cur = r.articles.pageInfo.endCursor;
}

const rows = [];
const perArticle = {};
for (const a of arts) {
  const body = String(a.body || '');
  const regions = regionsOf(body);
  let ext = 0, int = 0;

  // bare URLs inside JSON-LD (sameAs / offers / url) — NOT <a> tags, invisible to an anchor probe
  for (const [kind, s, e] of regions) {
    if (kind !== 'JSON-LD') continue;
    for (const m of body.slice(s, e).matchAll(/"(https?:\/\/[^"]+)"/g)) {
      let host; try { host = new URL(m[1]).hostname; } catch { continue; }
      const d = reg(host);
      if (d === 'inhousewellness.com') continue;
      rows.push({ article: a.handle, blog: a.blog.handle, domain: d, href: m[1], context: 'JSON-LD (schema, not body markup)', anchorText: null });
      ext++;
    }
  }

  for (const m of body.matchAll(/<a\b([^>]*)href="([^"]+)"([^>]*)>([\s\S]*?)<\/a>/gi)) {
    const [full, pre, href, post, inner] = m;
    const attrs = pre + post;
    const off = m.index;
    if (!/^https?:\/\//i.test(href)) { if (href.startsWith('/')) int++; continue; }
    let host; try { host = new URL(href).hostname; } catch { continue; }
    const d = reg(host);
    if (d === 'inhousewellness.com') { int++; continue; }
    ext++;
    const inRegion = regions.filter(([, s, e]) => off >= s && off < e).map(([k]) => k);
    let context = 'inline prose';
    if (inRegion.includes('JSON-LD')) context = 'JSON-LD (schema, not body markup)';
    else if (/<img\b/i.test(inner)) context = 'IMAGE WRAPPER';
    else if (/class="[^"]*(?:btn|button|cta)/i.test(attrs) || /^\s*<button/i.test(inner)) context = 'BUTTON / CTA';
    else if (inRegion.includes('TABLE')) context = 'TABLE CELL';
    rows.push({ article: a.handle, blog: a.blog.handle, domain: d, href, context, anchorText: inner.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim().slice(0, 90) });
  }
  perArticle[a.handle] = { blog: a.blog.handle, external: ext, internal: int, published: a.isPublished };
}

const domains = [...new Set(rows.map(r => r.domain))];
console.log(`\n══ PRE-STATE SNAPSHOT — ${new Date().toISOString()}`);
console.log(`  articles (live)          : ${arts.length}`);
console.log(`  total EXTERNAL links     : ${rows.length}`);
console.log(`  distinct external domains: ${domains.length}`);
console.log(`  articles carrying one    : ${new Set(rows.map(r => r.article)).size}`);
console.log(`  total INTERNAL links     : ${Object.values(perArticle).reduce((s, v) => s + v.internal, 0)}`);

console.log('\n══ CHECK FIRST — structural context of every external link');
const byCtx = {};
for (const r of rows) (byCtx[r.context] ||= []).push(r);
for (const [k, v] of Object.entries(byCtx).sort((a, b) => b[1].length - a[1].length)) {
  console.log(`  ${String(v.length).padStart(5)}  ${k}`);
  if (k !== 'inline prose') {
    const dd = {}; for (const r of v) (dd[r.domain] ||= new Set()).add(r.article);
    for (const [d, s] of Object.entries(dd).sort((a, b) => b[1].size - a[1].size).slice(0, 12)) console.log(`            ${d}  (${s.size} article(s))`);
  }
}

fs.writeFileSync('data/r18-prestate.json', JSON.stringify({ generatedAt: new Date().toISOString(), articles: arts.length, totalExternal: rows.length, domains: domains.length, perArticle, rows }, null, 2));
fs.writeFileSync('data/r18-domains.txt', domains.sort().join('\n'));
console.log(`\n  -> data/r18-prestate.json  (${rows.length} rows)`);
console.log(`  -> data/r18-domains.txt    (${domains.length} domains, for the cart test)`);
