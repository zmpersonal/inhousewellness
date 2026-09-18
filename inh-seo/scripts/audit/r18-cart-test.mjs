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
  // 18i: proves the two categories no fixture reached
  ['cold plunge category detected', scoreOf('<h2>Ice Baths &amp; Cold-Plunge Tubs</h2>').cats.includes('cold plunge')],
  ['hot tub category detected',   scoreOf('<a>Hot Tubs</a>').cats.includes('hot tub')],
];
let bad = 0;
console.log('\nFIXTURES');
for (const [l, ok] of FIX) { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${l}`); if (!ok) bad++; }
if (bad) { console.log('refusing — fixtures did not hold'); process.exit(1); }

/* THE TIER RULE, as a pure function so fixtures can hold it to account.
 *
 * Round 18 fix: a QUOTE-GATED seller publishes no price. hightechhealth.com scored
 * cart=5, cats=[sauna,infrared], price=0 and the first rule (cart>=2 AND price>=1) sent it
 * to T3 KEEP — the Sunlighten shape CLAUDE.md already recorded. Cart + category + no price
 * is a COMPETITOR SHAPE, not a disqualifier. It is not T1 on its own, because the same shape
 * also matched a sauna research blog (saunologia.fi) and an association (saunas.org) whose
 * cart sells books — so it becomes T1-CANDIDATE: confirm by a read, never KEEP.
 *
 * And a 200 that is a bot wall is not "no commerce" — homedepot.com returned 200 with an
 * EMPTY title and no content, and went to T3 KEEP. Routing only non-200 failures to REVIEW
 * let it through.
 *
 * ⚠ KNOWN LIMIT, NOT FIXED — costco.com is a DIFFERENT failure and no fixture here covers it.
 * It served its real homepage ("Welcome to Costco Wholesale", cart 1, price 1, cats []). A
 * general-merchandise retailer's HOMEPAGE never names saunas, so a homepage cart test cannot
 * see the category even when our link points straight at a sauna listing. The fix is to test
 * the LINKED URL, not the domain root. Until then, a general retailer can land in T3 wrongly.
 */
const WALL = /just a moment|access denied|attention required|are you a robot|captcha|pardon our interruption|request unsuccessful/i;
function tierOf(r) {
  if (r.err) return { tier: 'REVIEW', why: `could not fetch (${r.err}) — a failed request is not evidence` };
  if (!r.title || WALL.test(r.title)) return { tier: 'REVIEW', why: 'HTTP 200 but the page looks like a bot wall — not evidence of no commerce' };
  const priced = r.cart >= 2 && r.price >= 1;
  const gated = r.cart >= 4 && r.price === 0;
  if (priced && r.cats.length) return { tier: 'T1', why: `sells DTC (cart ${r.cart}, price ${r.price}) and carries: ${r.cats.join(', ')}` };
  if (gated && r.cats.length) return { tier: 'T1-CANDIDATE', why: `COMPETITOR SHAPE, pricing gated (cart ${r.cart}, price 0) and carries: ${r.cats.join(', ')} — confirm by a read` };
  if (priced || gated) return { tier: 'T2', why: 'sells DTC but no category of ours detected' };
  if (r.cart === 1 && r.price >= 2) return { tier: 'REVIEW', why: 'ambiguous commerce signal' };
  return { tier: 'T3', why: r.cats.length ? `no commerce signal; mentions ${r.cats.join(', ')}` : 'no commerce signal' };
}
const TFIX = [
  ['QUOTE-GATED seller is never KEEP (hightechhealth shape)', tierOf({ title: 'Saunas', cart: 5, price: 0, cats: ['sauna', 'infrared'] }).tier === 'T1-CANDIDATE'],
  ['priced seller of our category is T1',                     tierOf({ title: 'Shop', cart: 4, price: 2, cats: ['cold plunge'] }).tier === 'T1'],
  ['priced seller of something else is T2',                   tierOf({ title: 'Skincare', cart: 4, price: 2, cats: [] }).tier === 'T2'],
  ['200 bot wall is REVIEW, not T3 (homedepot shape)',           tierOf({ title: 'Access Denied', cart: 0, price: 0, cats: [] }).tier === 'REVIEW'],
  ['empty title is REVIEW, not T3',                           tierOf({ title: '', cart: 0, price: 0, cats: [] }).tier === 'REVIEW'],
  // 18i: the bare {err} case also passed via the empty-title branch; assert the REASON, and that an
  // error beats an otherwise-T1 page
  ['fetch error is REVIEW, never T1',                         tierOf({ err: 'HTTP 403' }).tier === 'REVIEW' && /could not fetch \(HTTP 403\)/.test(tierOf({ err: 'HTTP 403' }).why)],
  ['fetch error beats a T1-shaped page',                      tierOf({ err: 'HTTP 403', title: 'Shop', cart: 4, price: 2, cats: ['sauna'] }).tier === 'REVIEW'],
  // 18i: proves the Cloudflare interstitial title is a wall even with commerce-shaped numbers
  ["'Just a moment...' is a bot wall",                         tierOf({ title: 'Just a moment...', cart: 4, price: 2, cats: ['sauna'] }).tier === 'REVIEW'],
  // 18i: proves the ambiguous-commerce branch exists (it otherwise falls to T3 KEEP)
  ['cart 1 + price 2 is REVIEW, not T3',                      tierOf({ title: 'Store', cart: 1, price: 2, cats: [] }).tier === 'REVIEW'],
  ['journal with no cart is T3',                              tierOf({ title: 'Journal', cart: 0, price: 0, cats: ['sauna'] }).tier === 'T3'],
];
for (const [l, ok] of TFIX) { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${l}`); if (!ok) bad++; }
if (bad) { console.log('refusing — tier fixtures did not hold'); process.exit(1); }
if (process.argv.includes('--self-test')) { console.log('self-test only, no network'); process.exit(0); }

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

for (const r of out) Object.assign(r, tierOf(r));
fs.writeFileSync('data/r18-cart-test.json', JSON.stringify({ generatedAt: new Date().toISOString(), probed: out.length, results: out }, null, 2));
const t = {}; for (const r of out) t[r.tier] = (t[r.tier] || 0) + 1;
console.log('\nTIERS:', JSON.stringify(t));
console.log('-> data/r18-cart-test.json');
