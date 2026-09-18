/* Round 18 — verify from the RENDERED storefront article, not the API.
 * Politeness: concurrency 2, HTTP 429 is backoff (8s x6), never a failure.
 * A page that cannot be fetched is UNREACHABLE, reported apart from FAIL, and still exits 1.
 */
import fs from 'node:fs';
const B = process.argv[2];
const snap = JSON.parse(fs.readFileSync(B, 'utf8'));
const ct = JSON.parse(fs.readFileSync('data/r18-cart-test.json', 'utf8')).results;
const T1 = new Set(ct.filter((r) => r.tier === 'T1').map((r) => r.d)); T1.add('lifeprofitness.com');
const WITHHELD = ['goldendesigninc.com','medicalsaunas.com','dream-pod.com','almostheaven.com','homedics.com','homedics.com.au','globalwellnessinstitute.org','ndnr.com','peakprimalwellness.com','saunasociety.org','drdferguson.com','fisiologiadelejercicio.com','soeberginstitute.com'];
const MULTI = new Set(['com.au','net.au','org.au','co.uk','co.nz','co.za']);
const reg = (h) => { h = h.toLowerCase().replace(/^www\./, ''); const p = h.split('.'); if (p.length <= 2) return h; const l2 = p.slice(-2).join('.'); return MULTI.has(l2) ? p.slice(-3).join('.') : l2; };
const count = (html) => { const c = { t1: 0, wh: 0 }; for (const m of html.matchAll(/<a\b[^>]*?href="(https?:\/\/[^"]+)"/gi)) { let d; try { d = reg(new URL(m[1]).hostname); } catch { continue; } if (T1.has(d)) c.t1++; if (WITHHELD.includes(d)) c.wh++; } return c; };
const whBefore = (body) => count(body).wh;

async function get(url) {
  for (let i = 0; i < 7; i++) {
    const r = await fetch(url, { headers: { 'user-agent': 'Mozilla/5.0 (compatible; INH-verify/1.0)' } });
    if (r.status === 429) { await new Promise((z) => setTimeout(z, 8000)); continue; }
    return { status: r.status, final: r.url, html: await r.text() };
  }
  return { status: 429 };
}
const rows = []; let i = 0;
await Promise.all([0, 1].map(async () => {
  while (i < snap.length) {
    const s = snap[i++];
    const url = `https://inhousewellness.com/blogs/${s.blog}/${s.handle}`;
    let r = await get(url), c = r.html ? count(r.html) : null, tries = 0;
    while (c && c.t1 > 0 && tries++ < 3) { await new Promise((z) => setTimeout(z, 20000)); r = await get(url + '?cb=' + Date.now()); c = count(r.html); } // CDN lag
    rows.push({ s, r, c, whB: whBefore(s.before) });
  }
}));
let fail = 0, unreach = 0;
console.log('article                                              T1 before  rendered T1  withheld before/rendered');
for (const { s, r, c, whB } of rows.sort((a, b) => b.s.counts.t1 - a.s.counts.t1)) {
  if (!c || r.status !== 200) { unreach++; console.log(`  UNREACHABLE ${s.handle} status=${r.status}`); continue; }
  const redirected = !r.final.includes(s.handle);
  const ok = c.t1 === 0 && c.wh === whB && !redirected;
  if (!ok) fail++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${s.handle.padEnd(50)} ${String(s.counts.t1).padStart(5)}  ${String(c.t1).padStart(10)}   ${String(whB).padStart(6)} / ${c.wh}${redirected ? '  REDIRECTED to ' + r.final : ''}`);
}
console.log(`\n  ${rows.length - fail - unreach} ok, ${fail} FAIL, ${unreach} UNREACHABLE`);
process.exitCode = fail || unreach ? 1 : 0;
