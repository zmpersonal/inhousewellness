/* Round 18 — THE CART TEST. Fetch each unclassified domain's homepage and decide whether it
 * sells physical product direct to consumer, and if so whether it sells OUR categories.
 * READ-ONLY against third parties: one GET per domain, polite concurrency, real UA.
 *
 * A probe aimed at someone else's site must be validated on THEIR pages first, and a zero or
 * a failure is a VOCABULARY or NETWORK result — never evidence of a fact about the business.
 * So: anything that does not fetch, or fetches ambiguously, goes to REVIEW. Never to T1.
 * Removing a citation on the strength of a failed request would be the defamation-shaped
 * version of the probe-vocabulary bug.
 */
import fs from 'node:fs';

const KNOWN_CITATION = /(\.gov|\.edu|\.mil)$|^(pubmed|pmc|ncbi|doi|nih|cdc|who|nature|sciencedirect|springer|wiley|jamanetwork|nejm|thelancet|bmj|frontiersin|mdpi|plos|physiology|ahajournals|clinicaltrials|researchgate|semanticscholar|scholar\.google|cochrane)/;
const OURS = new Set(['besthomeinfraredsauna.com','healthresearchdatabase.com','saunasfactorydirect.com','saunaimport.com','infinitesauna.com','thesaunaheater.com','coldplungefactory.com','saunacalculator.com','homesaunaclimate.com','saunatap.com','inhousewellness.com']);

const domains = fs.readFileSync('data/r18-domains.txt', 'utf8').trim().split('\n')
  .filter((d) => !OURS.has(d) && !KNOWN_CITATION.test(d));
console.log(`domains to cart-test: ${domains.length}`);

// ── signals ──
const CART = [/add[\s-]?to[\s-]?cart/i, /\/cart\b/i, /add-to-cart/i, /checkout/i, /shopify/i, /woocommerce/i, /bigcommerce/i, /\bmy[\s-]?(?:cart|bag|basket)\b/i, /\bbuy now\b/i, /product-form/i, /snipcart|ecwid|squarespace-commerce/i];
const PRICE = [/\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?/, /"price"\s*:/i, /itemprop=["']price/i, /class="[^"]*price/i];
// our categories — match the NOUN, not the compound (CLAUDE.md), stems allow inflection
const CAT = [
  ['sauna',        /\bsaunas?\b/i],
  ['infrared',     /\binfra[\s-]?red\b/i],
  ['cold plunge',  /\bcold[\s-]?plunge|\bice[\s-]?bath|\bplunge tub/i],
  ['chiller',      /\bchiller|\bcooling (?:engine|unit|system)\b/i],
  ['steam',        /\bsteam (?:room|shower|generator|sauna)\b/i],
  ['massage chair',/\bmassage chairs?\b/i],
  ['hot tub',      /\bhot tubs?\b|\bspas? (?:for sale|dealer)\b/i],
];

// ── constructed fixtures: must hold before any network call ──
const scoreOf = (html) => ({
  cart: CART.filter((r) => r.test(html)).length,
  price: PRICE.filter((r) => r.test(html)).length,
  cats: CAT.filter(([, r]) => r.test(html)).map(([n]) => n),
});
const FIX = [
  ['shopify cart detected',      scoreOf('<form action="/cart/add">Add to Cart</form>').cart >= 2],
  ['price detected',             scoreOf('<span class="price">$1,299.00</span>').price >= 2],
  ['sauna category detected',    scoreOf('Our Saunas are great').cats.includes('sauna')],
  ['saunas plural matches',      scoreOf('infrared saunas').cats.includes('sauna')],
  ['a journal page is not a shop', scoreOf('<h1>Effects of sauna bathing</h1><p>Abstract</p>').cart === 0],
  ['blog mentioning price only', scoreOf('<p>it cost $5,000</p>').cart === 0],
];
let bad = 0;
console.log('\nFIXTURES');
for (const [l, ok] of FIX) { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${l}`); if (!ok) bad++; }
if (bad) { console.log('refusing — fixtures did not hold'); process.exit(1); }

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36';
async function probe(d) {
  for (const scheme of ['https://', 'https://www.']) {
    try {
      const ctl = new AbortController();
      const to = setTimeout(() => ctl.abort(), 14000);
      const res = await fetch(scheme + d, { redirect: 'follow', signal: ctl.signal, headers: { 'user-agent': UA, accept: 'text/html' } });
      clearTimeout(to);
      if (!res.ok) { if (scheme.endsWith('www.')) return { d, status: res.status, err: `HTTP ${res.status}` }; continue; }
      const html = (await res.text()).slice(0, 400000);
      const s = scoreOf(html);
      return { d, status: res.status, finalUrl: res.url, ...s, title: (html.match(/<title[^>]*>([\s\S]{0,120}?)<\/title>/i) || [, ''])[1].replace(/\s+/g, ' ').trim() };
    } catch (e) { if (scheme.endsWith('www.')) return { d, err: e.name === 'AbortError' ? 'timeout' : e.message.slice(0, 60) }; }
  }
  return { d, err: 'unreachable' };
}

const out = [];
const CONC = 5;
let idx = 0, done = 0;
await Promise.all(Array.from({ length: CONC }, async () => {
  while (idx < domains.length) {
    const d = domains[idx++];
    out.push(await probe(d));
    if (++done % 40 === 0) console.log(`  …${done}/${domains.length}`);
    await new Promise((r) => setTimeout(r, 120));
  }
}));

for (const r of out) {
  if (r.err) { r.tier = 'REVIEW'; r.why = `could not fetch (${r.err}) — a failed request is not evidence`; continue; }
  const sells = r.cart >= 2 && r.price >= 1;
  const maybe = r.cart === 1 && r.price >= 2;
  if (sells && r.cats.length) { r.tier = 'T1'; r.why = `sells DTC (cart ${r.cart}, price ${r.price}) and carries: ${r.cats.join(', ')}`; }
  else if (sells) { r.tier = 'T2'; r.why = `sells DTC but no category of ours detected`; }
  else if (maybe) { r.tier = 'REVIEW'; r.why = `ambiguous commerce signal (cart ${r.cart}, price ${r.price})${r.cats.length ? '; mentions ' + r.cats.join(', ') : ''}`; }
  else if (r.cats.length && r.cart === 0) { r.tier = 'T3'; r.why = `no commerce signal; editorial/reference mentioning ${r.cats.join(', ')}`; }
  else { r.tier = 'T3'; r.why = 'no commerce signal'; }
}
fs.writeFileSync('data/r18-cart-test.json', JSON.stringify({ generatedAt: new Date().toISOString(), probed: out.length, results: out }, null, 2));
const t = {}; for (const r of out) t[r.tier] = (t[r.tier] || 0) + 1;
console.log('\nTIERS:', JSON.stringify(t));
console.log('-> data/r18-cart-test.json');
