/* Round 14 theme branch — outcome verification. Read-only.
 *
 *   node scripts/audit/verify-round14.mjs            # reads MAIN (must FAIL before publish)
 *   node scripts/audit/verify-round14.mjs <themeId>  # reads a preview
 *
 * Preview reads use the 302 + _shopify_essential cookie handshake and REFUSE if
 * either is missing: a client that drops the cookie reads MAIN and passes wrongly.
 *
 * Checks, each an outcome on the rendered page:
 *   Q  quoted titles: 0 attribute values cut at a U+0022, on product / collection / home
 *   O  Organization node on the homepage and NOWHERE else; JSON parses; fields as ruled
 *   T  <title>: no raw newline, and whitespace-collapsed decoded title equals MAIN's
 *   C  category cards: alt equals card title, 8 of 8
 *   S  exactly one mobile slider copy
 *   Y  footer year is the current year
 *   G  og:image is https
 */
import fs from 'node:fs';
import path from 'node:path';
import { DATA } from '../lib/util.js';
import { assertServedBy } from '../lib/theme-identity.mjs';

const themeId = (process.argv[2] || '').replace(/\D/g, '');
const UA = 'Mozilla/5.0 (compatible; inh-seo-audit)';
const DQ = String.fromCodePoint(0x22);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchRetry(url, opts) {
  for (let i = 0; i < 6; i++) {
    const r = await fetch(url, opts);
    if (r.status !== 429) return r;
    await sleep(8000);
  }
  throw new Error(`429 persisted: ${url}`);
}
/* 18i: the served theme is asserted on EVERY read and a mismatch is fatal — a run that read the
   wrong theme once has no result worth reporting. MAIN is asserted by ROLE, never by a typed id. */
function identity(html, want, p) {
  try { assertServedBy(html, want, p); } catch (e) { console.error(`\n  REFUSING — ${e.message}`); process.exit(1); }
}
async function getMain(p) {
  const sep = p.includes('?') ? '&' : '?';
  const r = await fetchRetry(`https://inhousewellness.com${p}${sep}cb=${Date.now()}`, { headers: { 'User-Agent': UA } });
  const html = await r.text();
  identity(html, 'main', p);
  return { status: r.status, html };
}
async function getPreview(p) {
  const sep = p.includes('?') ? '&' : '?';
  const first = await fetchRetry(`https://inhousewellness.com${p}${sep}preview_theme_id=${themeId}`, { redirect: 'manual', headers: { 'User-Agent': UA } });
  const jar = (first.headers.getSetCookie?.() || []).map((c) => c.split(';')[0]).join('; ');
  if (first.status !== 302 || !jar) throw new Error(`preview handshake failed on ${p}: ${first.status}`);
  const r = await fetchRetry(new URL(first.headers.get('location'), 'https://inhousewellness.com'), { headers: { 'User-Agent': UA, cookie: jar } });
  const html = await r.text();
  identity(html, themeId, p);
  return { status: r.status, html };
}
const get = themeId ? getPreview : getMain;

const decode = (s) => s.replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');
const titleOf = (html) => (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] ?? null;

const results = [];
const check = (id, name, pass, detail) => { results.push({ id, name, pass, detail }); console.log(`  ${pass ? 'PASS' : 'FAIL'}  ${id}  ${name}  ${detail}`); };

/* ── Q: quoted titles ───────────────────────────────────────────────────── */
const quoted = JSON.parse(fs.readFileSync(path.join(DATA, 'quoted-title-products.json'), 'utf8'));
const heads = quoted.map((p) => ({ handle: p.handle, title: p.title, head: p.title.slice(0, p.title.indexOf(DQ)) }));
function cuts(html) {
  let n = 0; const where = [];
  for (const h of heads) {
    const k = html.split(`="${h.head}"`).length - 1;
    if (k) { n += k; where.push(`${h.handle}×${k}`); }
  }
  return { n, where };
}
const Q_PAGES = [
  ['product default, inch mark 10"', '/products/thermasol-twph1410us'],
  ['product default, quoted name', '/products/dynamic-lugano-infrared-sauna'],
  ['product Bundle, 79"L x 91"D', '/products/saunalife-ee8g'],
  ['collection steam-showers (6 inch-mark ThermaSol)', '/collections/steam-showers'],
  ['collection golden-designs (quoted editions)', '/collections/golden-designs'],
  ['homepage', '/'],
];
const pages = {};
const statuses = {};   // 18i: every page's status travels with its HTML, so later checks can require 200
const load = async (p) => { if (!(p in pages)) { const r = await get(p); pages[p] = r.html; statuses[p] = r.status; } return pages[p]; };
for (const [label, p] of Q_PAGES) {
  const { status, html } = await get(p);
  pages[p] = html; statuses[p] = status;
  const c = cuts(html);
  check('Q', label, status === 200 && c.n === 0, `status ${status}, cut attributes ${c.n}${c.where.length ? ' [' + c.where.slice(0, 4).join(', ') + ']' : ''}`);
}
/* show the full rendering on the inch-mark product */
{
  const t = heads.find((h) => h.handle === 'thermasol-twph1410us');
  const html = pages['/products/thermasol-twph1410us'];
  const esc = t.title.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
  const full = [...html.matchAll(/\s([a-z-]+)="([^"]*)"/g)].filter((m) => m[2] === esc || decode(m[2]) === t.title);
  console.log(`        full-title attributes on thermasol-twph1410us: ${full.length}  ${[...new Set(full.map((m) => m[1]))].join(', ')}`);
}

/* ── O: Organization node ───────────────────────────────────────────────── */
function orgNodes(html) {
  return [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
    .map((m) => { try { return JSON.parse(m[1]); } catch { return { __unparseable: m[1].slice(0, 80) }; } })
    .flatMap((j) => (Array.isArray(j) ? j : [j]))
    .filter((j) => j && (j['@type'] === 'Organization' || j.__unparseable));
}
{
  const nodes = orgNodes(pages['/']);
  const o = nodes.find((n) => n['@type'] === 'Organization');
  const want = {
    name: 'InHouse Wellness', url: 'https://inhousewellness.com/',
    email: 'support@inhousewellness.com', street: '5900 Balcones Drive #20752', zip: '78731',
    sameAs: ['https://www.facebook.com/people/InHouse-Wellness/61569426503966/', 'https://www.instagram.com/inhouse.wellness/',
      'https://www.tiktok.com/@inhousewellness', 'https://www.youtube.com/@InHouseWellness', 'https://www.pinterest.com/inhousewellness/'],
  };
  const ok = o && o.name === want.name && o.url === want.url && o.contactPoint?.email === want.email
    && o.address?.streetAddress === want.street && o.address?.postalCode === want.zip
    && JSON.stringify(o.sameAs) === JSON.stringify(want.sameAs) && /^https:\/\/.+logo_.+\.png/.test(o.logo || '')
    && nodes.length === 1 && !('telephone' in o);
  check('O', 'homepage: exactly one Organization node, fields as ruled', !!ok, o ? `logo ${o.logo}` : `nodes ${nodes.length}`);
  if (o) {
    const urls = [o.url, o.logo, ...o.sameAs];
    for (const u of urls) {
      if (/facebook|instagram|tiktok/.test(u)) { console.log(`        (browser-verified 15 Sep) ${u}`); continue; }
      const r = await fetchRetry(u, { headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/128' } });
      check('O', `resolves ${u}`, r.status === 200, `status ${r.status}`);
    }
  }
}
const O_ABSENT = ['/products/thermasol-twph1410us', '/collections/steam-showers', '/pages/contact', '/blogs/news/best-6-person-sauna', '/blogs/saunas'];
for (const p of O_ABSENT) {
  const html = await load(p);
  /* Organization nested inside VideoObject.publisher is pre-existing and not a top-level node */
  const top = orgNodes(html).length;
  // 18i: an error page has no Organization node either — absence only counts on a page that rendered
  check('O', `absent on ${p}`, statuses[p] === 200 && top === 0, `status ${statuses[p]}, top-level Organization nodes ${top}`);
}

/* ── T: titles ──────────────────────────────────────────────────────────── */
const T_PAGES = ['/', '/products/thermasol-twph1410us', '/products/saunalife-ee8g', '/products/saunalife-g3',
  '/collections/steam-showers', '/collections/golden-designs', '/collections/cold-plunge', '/pages/contact',
  '/blogs/saunas', '/blogs/news/best-6-person-sauna', '/search?q=sauna', '/collections/steam-showers?page=2', '/pages/does-not-exist-r14'];
const DELIBERATE_404 = '/pages/does-not-exist-r14';
for (const p of T_PAGES) {
  const raw = titleOf(await load(p));
  const main = await getMain(p);
  const mainRaw = titleOf(main.html);
  const norm = (s) => decode((s ?? '').replace(/\s+/g, ' ').trim());
  const noNl = raw !== null && !/[\n\r]/.test(raw) && !/ {2}/.test(raw);
  const same = norm(raw) === norm(mainRaw);
  // 18i: both sides must be the page we meant — 200, except the one deliberate 404, which must BE a 404
  const want = p === DELIBERATE_404 ? 404 : 200;
  const statusOk = statuses[p] === want && main.status === want;
  check('T', `title ${p}`, noNl && same && statusOk, `status ${statuses[p]}/${main.status} (want ${want})  raw ${JSON.stringify(raw).slice(0, 70)}  len ${norm(raw).length} (MAIN ${norm(mainRaw).length})`);
}

/* ── C, S, Y, G on the homepage ─────────────────────────────────────────── */
{
  const html = pages['/'];
  const cards = [...html.matchAll(/<div class="category-img">\s*<img src="[^"]+" alt="([^"]*)">\s*<\/div>\s*<div class="category-title">\s*([\s\S]*?)\s*<\/div>/g)];
  const match = cards.filter((c) => decode(c[1]) === decode(c[2].trim())).length;
  check('C', 'category card alt = card title', cards.length === 8 && match === 8, `${match} of ${cards.length}`);
  const sliders = html.split('class="collection_slider_mobile_menu').length - 1;
  check('S', 'one mobile slider copy', sliders === 1, `copies ${sliders}`);
  const yr = String(new Date().getUTCFullYear());
  const foot = (html.match(/<div class="footer__copyright">([\s\S]*?)<\/div>/) || [])[1] || '';
  check('Y', 'footer year current', foot.includes(yr) && !foot.includes('2024'), JSON.stringify(foot.trim()));
  const og = (html.match(/<meta property="og:image" content="([^"]*)"/) || [])[1] || '';
  check('G', 'og:image https', og.startsWith('https://'), og.slice(0, 60));
}

const fail = results.filter((r) => !r.pass).length;
console.log(`\n  ${themeId ? 'PREVIEW ' + themeId : 'MAIN'}: ${results.length - fail} pass, ${fail} fail`);
if (fail) process.exitCode = 1;
