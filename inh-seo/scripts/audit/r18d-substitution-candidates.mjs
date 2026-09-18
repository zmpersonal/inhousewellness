/* Round 18d item 8 — competitor links whose DESTINATION is a product we sell. REPORT ONLY.
 * Population: every competitor href unwrapped from ORDINARY articles in rounds 18b/18c/18d, read
 * back from the backups (they are no longer live), plus the 3 held Costco citations.
 * Match: a DISTINCTIVE model token from one of our ACTIVE product titles appears in the URL slug,
 * AND the vendor is corroborated (vendor word in the slug/domain, or a known dealer domain).
 * Candidates are then confirmed by SKU through the Admin API. A title match alone is a candidate,
 * never a verdict (CLAUDE.md: titles are derived copy; DYN-6336-02 was inherited mistitled).
 */
import fs from 'node:fs';
import path from 'node:path';
const P = JSON.parse(fs.readFileSync('data/products.json', 'utf8'));
const A = (Array.isArray(P) ? P : P.products || P.nodes).filter((p) => p.status === 'ACTIVE');
const STOP = new Set('sauna saunas person infrared far full spectrum emf low ultra near zero indoor outdoor cedar hemlock canadian red edition elite traditional heater dynamic maxxus golden designs with and the for inc hybrid barrel corner cabin steam cold plunge chair massage tub bench black white wood kit stove electric kw series premium luxury new model plus pro edition hemlock'.split(' '));
const tok = (s) => s.toLowerCase().normalize('NFKD').replace(/[‐-―]/g, '-').split(/[^a-z0-9]+/).filter(Boolean);
const freq = {};
for (const p of A) for (const t of new Set(tok(p.title))) freq[t] = (freq[t] || 0) + 1;
const model = (p) => [...new Set(tok(p.title))].filter((t) => t.length >= 4 && !STOP.has(t) && !/^\d/.test(t) && freq[t] <= 4);
const VENDOR_WORDS = { 'Dynamic Saunas': ['dynamic'], 'Maxxus': ['maxxus'], 'Golden Designs Inc': ['golden', 'goldendesigns'], 'Medical Saunas': ['medical'], 'Finnmark Designs': ['finnmark'], 'SaunaLife': ['saunalife'], 'SAUNA LIFE': ['saunalife'], 'Harvia': ['harvia'], 'HUUM': ['huum'], 'Huum': ['huum'], 'Narvi': ['narvi'], 'Dundalk Leisurecraft': ['leisurecraft', 'dundalk'], 'Leisure Craft': ['leisurecraft'], 'Scandia': ['scandia'], 'Ice Tubs': ['icetubs'], 'Dreampod': ['dreampod'] };
const DEALERS = { 'goldendesignsaunas.com': ['Dynamic Saunas', 'Maxxus', 'Golden Designs Inc'], 'gdidealers.com': ['Dynamic Saunas', 'Maxxus', 'Golden Designs Inc'], 'dynamicsaunasdirect.com': ['Dynamic Saunas'] };

// ── population, from the backups ──
const hrefs = [];
const BK = 'data/backups';
for (const dir of fs.readdirSync(BK)) for (const f of ['r18-unwrap-t1.json', 'r18c-unwrap-3dmassagechaircom.json', 'r18d-edit.json']) {
  const p = path.join(BK, dir, f); if (!fs.existsSync(p)) continue;
  for (const s of JSON.parse(fs.readFileSync(p, 'utf8'))) {
    if (s.blog === 'institute') continue;
    for (const m of s.before.matchAll(/<a\b[^>]*?href="(https?:\/\/[^"]+)"/gi)) hrefs.push({ article: s.handle, href: m[1], src: f });
  }
}
// keep only competitor hosts (T1 by the cart test or by ruling)
const ct = JSON.parse(fs.readFileSync('data/r18-cart-test.json', 'utf8')).results;
const T1 = new Set(ct.filter((r) => r.tier === 'T1').map((r) => r.d).concat(['lifeprofitness.com', '3dmassagechair.com', 'costco.com', 'rcwilley.com', 'homedepot.com']));
const reg = (h) => { h = h.toLowerCase().replace(/^www\./, ''); const p = h.split('.'); return p.length > 2 && ['com.au', 'co.uk'].includes(p.slice(-2).join('.')) ? p.slice(-3).join('.') : p.slice(-2).join('.'); };
const seen = new Set(); const pop = [];
for (const h of hrefs) { let d; try { d = reg(new URL(h.href).hostname); } catch { continue; } if (!T1.has(d)) continue; const k = h.article + '|' + h.href; if (seen.has(k)) continue; seen.add(k); pop.push({ ...h, domain: d }); }
console.log(`population: ${pop.length} distinct (article, competitor URL) pairs from ${new Set(pop.map((p) => p.article)).size} ordinary articles`);

const cands = [];
for (const h of pop) {
  const slugT = new Set(tok(decodeURIComponent(new URL(h.href).pathname)));
  const domT = tok(h.domain).join('');
  for (const p of A) {
    const hit = model(p).filter((t) => slugT.has(t));
    if (!hit.length) continue;
    const vw = VENDOR_WORDS[p.vendor] || [];
    const vendorOk = vw.some((w) => slugT.has(w) || domT.includes(w)) || (DEALERS[h.domain] || []).includes(p.vendor);
    if (!vendorOk) continue;
    cands.push({ ...h, handle: p.handle, title: p.title, vendor: p.vendor, price: p.priceMin, via: hit.join('+') });
  }
}
fs.writeFileSync('data/r18d-substitution-candidates.json', JSON.stringify(cands, null, 2));
const byHref = {}; for (const c of cands) (byHref[c.article + ' | ' + c.href] ||= []).push(c);
console.log(`candidate destinations: ${Object.keys(byHref).length}\n`);
for (const [k, cs] of Object.entries(byHref)) {
  const [art, url] = k.split(' | ');
  console.log(`  ${art}\n     -> ${url.slice(0, 96)}`);
  for (const c of cs) console.log(`        ~ ours: ${c.handle.padEnd(48)} $${c.price}  [matched on "${c.via}"]`);
}
