/* FIXTURES CHOSEN TO BREAK THE PROPERTY — not clean samples.
 * Round 15's validator passed six template types and missed a defect on 31 products because the
 * barcode it happened to sample had no leading zero. Every fixture here carries the awkward value. */
const THEME = process.argv[2];
const UA = { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36' };
async function raw(p) {
  const r1 = await fetch(`https://inhousewellness.com${p}?preview_theme_id=${THEME}`, { headers: UA, redirect: 'manual' });
  const sc = (r1.headers.getSetCookie?.() || []).join('; ');
  if (r1.status !== 302 || !/_shopify_essential/.test(sc)) throw new Error(`no preview handshake (${r1.status})`);
  const cookie = sc.split(',').map((s) => s.trim().split(';')[0]).filter(Boolean).join('; ');
  const loc = r1.headers.get('location');
  return await (await fetch(loc.startsWith('http') ? loc : `https://inhousewellness.com${loc}`, { headers: { ...UA, cookie } })).text();
}
const CASES = [
  ['dynamic-venice-elite',                  'LEADING ZERO — the reported case',        { agg: [4.93, 15], offers: true }],
  ['huum-hive',                             'U+2011 NON-BREAKING HYPHENS in barcode',  { agg: null,       offers: true }],
  ['maxxus-3-person-sauna-hemlock-ultralow','BUNDLE template + leading zero + RATED',  { agg: 'any',      offers: true }],
  ['laguna-q-gpv3100-outdoor-island',       'NO REVIEWS — guard must still hold',      { agg: null,       offers: true }],
];
let bad = 0;
for (const [handle, label, want] of CASES) {
  console.log(`\n  ${label}\n  /products/${handle}`);
  let html; try { html = await raw(`/products/${handle}`); } catch (e) { console.log(`    UNREACHABLE — ${e.message}`); bad++; continue; }
  const blocks = [...html.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1].trim());
  let parsed = [], perr = [];
  for (const b of blocks) { try { parsed.push(JSON.parse(b)); } catch (e) { perr.push(e.message.slice(0, 60)); } }
  const flat = parsed.flatMap((j) => Array.isArray(j) ? j : [j]);
  const prod = flat.find((n) => n['@type'] === 'Product');
  const checks = [
    ['every ld+json block PARSES', perr.length === 0],
    ['exactly one Product node', flat.filter((n) => n['@type'] === 'Product').length === 1],
    ['offers intact', !!prod && Array.isArray(prod.offers) && prod.offers.length > 0],
    ['gtin is a STRING', !prod || !prod.offers ? true : prod.offers.every((o) => ['gtin12','gtin13','gtin14'].every((k) => o[k] === undefined || typeof o[k] === 'string'))],
  ];
  if (want.agg === null) checks.push(['aggregateRating ABSENT (guard)', !prod?.aggregateRating]);
  else if (want.agg === 'any') checks.push(['aggregateRating present', !!prod?.aggregateRating]);
  else checks.push([`aggregateRating ${want.agg[0]}/${want.agg[1]}`, prod?.aggregateRating?.ratingValue === want.agg[0] && prod?.aggregateRating?.reviewCount === want.agg[1]]);
  for (const [n, ok] of checks) { console.log(`    ${ok ? 'ok  ' : 'FAIL'} ${n}`); if (!ok) bad++; }
  if (perr.length) console.log('        parse errors:', perr.join(' | '));
  const g = prod?.offers?.[0] || {};
  const gk = ['gtin12','gtin13','gtin14'].find((k) => g[k] !== undefined);
  if (gk) console.log(`        ${gk} = ${JSON.stringify(g[gk])}   price = ${JSON.stringify(g.price)}`);
  if (prod?.aggregateRating) console.log(`        ${JSON.stringify(prod.aggregateRating)}`);
}
console.log(bad ? `\n  ${bad} CHECK(S) FAILED` : '\n  all checks passed on fixtures chosen to break the property');
process.exitCode = bad ? 1 : 0;
