/* Address enumeration. Read-only. Client ruling 15 Sep 2026: Balcones #20752 is the only
 * address; Ben White is old and #21140 must go.
 *
 *   node scripts/audit/address-sweep.mjs [--out file]
 *
 * Enumerate BEFORE changing anything, and report by location — some locations are not
 * reachable from the Admin API at all.
 *
 * Patterns are built from CODE POINTS, and the street number is matched WITHOUT the street
 * name: "Ben White" also appears written as "BenWhite" or split across markup, and a suite
 * can be written "#20752", "# 20752", "Ste 20752" or "20752".
 */
import fs from 'node:fs';
import { gql, paginate } from '../lib/shopify.js';

const NB = '[\\s\\u00A0\\u202F\\u2009\\u200B]';       // any space, including the invisibles
const TAGS = '(?:<[^>]*>|' + NB + ')*';               // markup or space between words
const rx = (s, f = 'gi') => new RegExp(s, f);
const PATTERNS = [
  ['BEN_WHITE_STREET', rx('Ben' + TAGS + 'White')],
  ['BEN_WHITE_NUMBER', rx('2028' + TAGS + 'E' + TAGS + 'Ben|\\b2028\\b' + TAGS + 'East')],
  ['ZIP_78741', rx('\\b78741\\b')],
  ['SUITE_21140', rx('\\b21140\\b')],
  ['SUITE_20752', rx('\\b20752\\b')],                  // the KEEP value, counted for coverage
  ['BALCONES', rx('Balcones')],
  ['ZIP_78731', rx('\\b78731\\b')],
];
const CHANGE = new Set(['BEN_WHITE_STREET', 'BEN_WHITE_NUMBER', 'ZIP_78741', 'SUITE_21140']);

const hits = [];
function scan(where, id, field, value, extra = {}) {
  if (typeof value !== 'string' || !value) return;
  for (const [name, re] of PATTERNS) {
    re.lastIndex = 0;
    const n = (value.match(re) || []).length;
    if (!n) continue;
    const m = re.exec(value); re.lastIndex = 0;
    const at = m ? Math.max(0, m.index - 70) : 0;
    hits.push({ where, id, field, pattern: name, count: n, change: CHANGE.has(name),
      context: value.slice(at, at + 200).replace(/\s+/g, ' '), ...extra });
  }
}

/* ── 1. Shop-level: billing address, policies, contact ───────────────────── */
const shop = await gql(`{ shop{ name contactEmail billingAddress{ address1 address2 city provinceCode zip country } } }`);
scan('SETTINGS (client only)', 'shop.billingAddress', 'billingAddress',
  Object.values(shop.shop.billingAddress).filter((v) => typeof v === 'string').join(', '));

/* Policy BODIES need the read_legal_policies scope, which this token does not have
   (confirmed 16 Sep 2026: ACCESS_DENIED). The rendered pages are the available source,
   and they are also what a customer sees. Recorded as a scope limit, not as "no hits". */
const POLICY_URLS = ['/policies/privacy-policy', '/policies/refund-policy', '/policies/terms-of-service',
  '/policies/shipping-policy', '/policies/legal-notice', '/policies/contact-information',
  '/policies/subscription-policy', '/policies/terms-of-sale'];
for (const u of POLICY_URLS) {
  const r = await fetch(`https://inhousewellness.com${u}?cb=${Date.now()}`, { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; inh-seo-audit)' } });
  const html = await r.text();
  if (r.status !== 200) { console.log(`  policy ${u} -> ${r.status} (not present)`); continue; }
  const i = html.indexOf('<main'), j = html.indexOf('</main>');
  scan('POLICY PAGE rendered (client pastes)', u, 'rendered body', i >= 0 && j > i ? html.slice(i, j) : html);
}

/* ── 2. Locations — read_locations not granted (ACCESS_DENIED, 16 Sep 2026).
   Recorded as UNCHECKED, which is not the same as clean. A location address is a
   Settings field the client can see and we cannot. ─────────────────────────── */
let locationsChecked = false;
try {
  const loc = await gql(`{ locations(first:20){ nodes{ id name address{ address1 address2 city zip provinceCode } } } }`);
  locationsChecked = true;
  for (const l of loc.locations.nodes)
    scan('LOCATION (client only)', l.name, l.id, Object.values(l.address).filter((v) => typeof v === 'string').join(', '));
} catch (e) {
  console.log('  LOCATIONS: UNCHECKED — ' + String(e.message).slice(0, 60).replace(/\s+/g, ' '));
}

/* ── 3. Pages, articles, products, collections, blogs ────────────────────── */
const pages = await paginate(`query($first:Int,$after:String){ pages(first:$first, after:$after){ pageInfo{hasNextPage endCursor} nodes{ id handle title body isPublished metafields(first:20){ nodes{ namespace key value } } } } }`, 'pages');
for (const p of pages) {
  scan(p.isPublished ? 'PAGE published' : 'PAGE UNPUBLISHED', p.handle, 'body', p.body, { gid: p.id });
  for (const mf of p.metafields.nodes) scan(p.isPublished ? 'PAGE published' : 'PAGE UNPUBLISHED', p.handle, `metafield ${mf.namespace}.${mf.key}`, mf.value, { gid: p.id });
}
const articles = await paginate(`query($first:Int,$after:String){ articles(first:$first, after:$after){ pageInfo{hasNextPage endCursor} nodes{ id handle title body summary isPublished blog{ handle } metafields(first:20){ nodes{ namespace key value } } } } }`, 'articles');
for (const a of articles) {
  const w = a.isPublished ? 'ARTICLE published' : 'ARTICLE UNPUBLISHED';
  scan(w, `${a.blog.handle}/${a.handle}`, 'body', a.body, { gid: a.id });
  scan(w, `${a.blog.handle}/${a.handle}`, 'summary', a.summary, { gid: a.id });
  for (const mf of a.metafields.nodes) scan(w, `${a.blog.handle}/${a.handle}`, `metafield ${mf.namespace}.${mf.key}`, mf.value, { gid: a.id });
}
const products = await paginate(`query($first:Int,$after:String){ products(first:$first, after:$after){ pageInfo{hasNextPage endCursor} nodes{ id handle title descriptionHtml status seo{ title description } metafields(first:20){ nodes{ namespace key value } } } } }`, 'products', {}, 25);
for (const p of products) {
  scan(`PRODUCT ${p.status}`, p.handle, 'descriptionHtml', p.descriptionHtml, { gid: p.id });
  scan(`PRODUCT ${p.status}`, p.handle, 'seo', [p.seo.title, p.seo.description].filter(Boolean).join(' | '), { gid: p.id });
  for (const mf of p.metafields.nodes) scan(`PRODUCT ${p.status}`, p.handle, `metafield ${mf.namespace}.${mf.key}`, mf.value, { gid: p.id });
}
const collections = await paginate(`query($first:Int,$after:String){ collections(first:$first, after:$after){ pageInfo{hasNextPage endCursor} nodes{ id handle descriptionHtml seo{ title description } metafields(first:20){ nodes{ namespace key value } } } } }`, 'collections', {}, 25);
for (const c of collections) {
  scan('COLLECTION', c.handle, 'descriptionHtml', c.descriptionHtml, { gid: c.id });
  scan('COLLECTION', c.handle, 'seo', [c.seo.title, c.seo.description].filter(Boolean).join(' | '), { gid: c.id });
  for (const mf of c.metafields.nodes) scan('COLLECTION', c.handle, `metafield ${mf.namespace}.${mf.key}`, mf.value, { gid: c.id });
}

/* ── 4. Theme files, live theme ──────────────────────────────────────────── */
const t = await gql(`{ themes(first:1, roles:[MAIN]){ nodes{ id name } } }`);
const themeId = t.themes.nodes[0].id;
let a = null; const names = [];
for (;;) {
  const q = await gql(`query($id:ID!,$a:String){ theme(id:$id){ files(first:250, after:$a){ pageInfo{hasNextPage endCursor} nodes{ filename } } } }`, { id: themeId, a });
  names.push(...q.theme.files.nodes.map((n) => n.filename));
  if (!q.theme.files.pageInfo.hasNextPage) break;
  a = q.theme.files.pageInfo.endCursor;
}
const textFiles = names.filter((n) => /\.(liquid|json|js|css)$/.test(n));
for (let i = 0; i < textFiles.length; i += 50) {
  const q = await gql(`query($id:ID!,$f:[String!]){ theme(id:$id){ files(filenames:$f, first:50){ nodes{ filename body{ ... on OnlineStoreThemeFileBodyText{ content } } } } } }`, { id: themeId, f: textFiles.slice(i, i + 50) });
  for (const n of q.theme.files.nodes) scan(`THEME ${t.themes.nodes[0].name}`, n.filename, 'file', n.body?.content);
}

/* ── 5. Metaobjects ──────────────────────────────────────────────────────── */
const defs = await gql(`{ metaobjectDefinitions(first:50){ nodes{ type } } }`);
for (const d of defs.metaobjectDefinitions.nodes) {
  const mo = await paginate(`query($first:Int,$after:String,$type:String!){ metaobjects(type:$type, first:$first, after:$after){ pageInfo{hasNextPage endCursor} nodes{ id handle fields{ key value } } } }`, 'metaobjects', { type: d.type }, 50);
  for (const o of mo) for (const f of o.fields) scan(`METAOBJECT ${d.type}`, o.handle, f.key, f.value, { gid: o.id });
}

/* ── Report ──────────────────────────────────────────────────────────────── */
const toChange = hits.filter((h) => h.change);
const byWhere = {};
for (const h of toChange) (byWhere[h.where] ??= []).push(h);
console.log(`\n  scanned: ${pages.length} pages, ${articles.length} articles, ${products.length} products, ${collections.length} collections, ${textFiles.length} theme files, policies (rendered), metaobjects; LOCATIONS ${locationsChecked ? 'checked' : 'UNCHECKED — no scope'}`);
console.log(`\n  MUST CHANGE (Ben White / 78741 / #21140): ${toChange.length} occurrences\n`);
for (const [w, list] of Object.entries(byWhere).sort((x, y) => y[1].length - x[1].length)) {
  console.log(`  ${w}  —  ${list.length}`);
  for (const h of list) console.log(`     ${h.id}  [${h.field}]  ${h.pattern}×${h.count}\n        …${h.context.slice(0, 150)}…`);
}
const keep = hits.filter((h) => !h.change);
const keepBy = {};
for (const h of keep) (keepBy[h.pattern] ??= new Set()).add(`${h.where}|${h.id}`);
console.log(`\n  KEEP (Balcones / #20752 / 78731), for coverage:`);
for (const [p, s] of Object.entries(keepBy)) console.log(`     ${p.padEnd(16)} ${s.size} records`);
if (process.argv.includes('--out')) fs.writeFileSync(process.argv[process.argv.indexOf('--out') + 1], JSON.stringify(hits, null, 1));
