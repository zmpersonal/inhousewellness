/* Rendered <title> sweep over every ACTIVE, published product. Read-only.
 *
 *   node scripts/audit/rendered-title-sweep.mjs [themeId] [--out file]
 *
 * Measures what the title CHAIN produces, which a field-derived count cannot:
 * whitespace collapsed, entities decoded, suffix included if the chain adds one.
 * Preview reads use the 302 + cookie handshake and refuse without it.
 * UNREACHABLE is reported separately from a measurement and fails the run.
 */
import fs from 'node:fs';
import { paginate } from '../lib/shopify.js';

const themeId = (process.argv.slice(2).find((a) => /^\d+$/.test(a)) || '');
const outIdx = process.argv.indexOf('--out');
const UA = 'Mozilla/5.0 (compatible; inh-seo-audit)';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const decode = (s) => s.replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

async function f(url, opts) {
  for (let i = 0; i < 6; i++) { const r = await fetch(url, opts); if (r.status !== 429) return r; await sleep(8000); }
  return null;
}
let jar = '';
async function page(handle) {
  const p = `/products/${handle}`;
  if (!themeId) { const r = await f(`https://inhousewellness.com${p}`, { headers: { 'User-Agent': UA } }); return r && { status: r.status, html: await r.text() }; }
  if (!jar) {
    const first = await f(`https://inhousewellness.com${p}?preview_theme_id=${themeId}`, { redirect: 'manual', headers: { 'User-Agent': UA } });
    jar = (first?.headers.getSetCookie?.() || []).map((c) => c.split(';')[0]).join('; ');
    if (!first || first.status !== 302 || !jar) throw new Error('preview handshake failed');
  }
  const r = await f(`https://inhousewellness.com${p}`, { headers: { 'User-Agent': UA, cookie: jar } });
  return r && { status: r.status, html: await r.text() };
}

const all = (await paginate(`query($first:Int,$after:String){ products(first:$first, after:$after, query:"status:active"){ pageInfo{hasNextPage endCursor} nodes{ handle onlineStoreUrl } } }`, 'products'))
  .filter((p) => p.onlineStoreUrl).map((p) => p.handle);
const rows = []; let i = 0;
async function worker() {
  while (i < all.length) {
    const h = all[i++];
    const r = await page(h);
    if (!r || r.status !== 200) { rows.push({ h, unreachable: r ? r.status : '429' }); continue; }
    const raw = (r.html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] ?? '';
    const t = decode(raw.replace(/\s+/g, ' ').trim());
    const theme = (r.html.match(/Shopify\.theme = (\{[^;]*\})/) || [])[1] || '';
    rows.push({ h, len: t.length, t, rawNewline: /[\n\r]/.test(raw), suffix: /–\s*inhousewellness$/i.test(t), themeOk: !themeId || theme.includes(themeId) });
  }
}
await Promise.all([worker(), worker()]);
const ok = rows.filter((r) => !r.unreachable);
const out = {
  theme: themeId || 'MAIN', at: new Date().toISOString(), products: all.length, measured: ok.length,
  unreachable: rows.filter((r) => r.unreachable).length,
  over60: ok.filter((r) => r.len > 60).length,
  withSuffix: ok.filter((r) => r.suffix).length,
  rawNewline: ok.filter((r) => r.rawNewline).length,
  wrongTheme: ok.filter((r) => !r.themeOk).length,
};
console.log(JSON.stringify(out, null, 1));
if (outIdx > 0) fs.writeFileSync(process.argv[outIdx + 1], JSON.stringify({ ...out, rows }, null, 1));
if (out.unreachable || out.wrongTheme) process.exitCode = 1;
