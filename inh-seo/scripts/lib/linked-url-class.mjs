/* Classify a link by its DESTINATION URL, not by the destination site's homepage.
 *
 * WHY (Round 18c): a general retailer's homepage never names our categories, so a homepage
 * category test is blind to the whole class BY DESIGN. costco.com served its real homepage
 * ("Welcome to Costco Wholesale", cart 1, price 1, cats []) and went to T3 KEEP while 13 of
 * its 14 links pointed straight at saunas and cold plunges. Marketplaces and big-box chains
 * are classified per link, from the URL, never from the root.
 *
 * TWO LEGS, BOTH REQUIRED FOR REMOVE:
 *   1. the URL names one of our categories, and
 *   2. the URL is a PRODUCT or LISTING page, not content.
 * Leg 2 exists because bachmanns.com/sauna-maintenance-guide/ names "sauna" and is a guide.
 * A slug that names a category is a candidate, never a verdict.
 */
export const GENERAL_RETAILERS = new Set([   // hand-declared, each a retailer of goods across categories
  'costco.com', 'homedepot.com', 'rcwilley.com', 'bachmanns.com',
  'amazon.com', 'walmart.com', 'lowes.com', 'wayfair.com', 'target.com', 'bestbuy.com',
  'overstock.com', 'samsclub.com', 'ebay.com', 'etsy.com', 'menards.com', 'bjs.com',
]);
const CORE = [
  ['sauna', /\bsaunas?\b/], ['cold plunge', /\bcold[- ]?plunge|\bice[- ]?bath|\bplunge[- ]?tub/],
  ['massage chair', /\bmassage[- ]?(?:chair|recliner)s?\b|\bzero[- ]gravity[- ]massage/],
  ['hot tub', /\bhot[- ]?tubs?\b|\bhot[- ]soak/], ['chiller', /\bchillers?\b/],
  ['steam', /\bsteam[- ](?:room|shower|generator|sauna)/],
];
const OUTDOOR = [['fire pit', /\bfire[- ]?pits?\b/]];    // carried, but scoped out of SEO — a client call
const CONTENT = /\/(?:blogs?|news|research|articles?|learn|guides?|how-to|explorer|magazine|ideas|cost)\/|-guide\b|\/answers?\//;
const PRODUCT = /\.product\.|\/p\/|\/dp\/|\/ip\/|\/s\?keyword=|\/search\?|\/c\/|\/collections?\//;

export function classifyLinkedUrl(href) {
  let u; try { u = new URL(href); } catch { return { call: 'REVIEW', why: 'unparseable URL' }; }
  const raw = decodeURIComponent(u.pathname + u.search).toLowerCase();
  // category words on a NORMALISED slug; page type on the RAW path. Normalising '.' to '-'
  // first erased the '.product.' marker the page-type test looks for — the fixture caught it.
  const slug = raw.replace(/[_+.]/g, '-');
  const hit = CORE.find(([, r]) => r.test(slug.replace(/-/g, ' ')) || r.test(slug));
  const out = OUTDOOR.find(([, r]) => r.test(slug.replace(/-/g, ' ')));
  const content = CONTENT.test(raw);
  const product = PRODUCT.test(raw);
  if (/^customerservice\.|^help\.|^support\./.test(u.hostname)) return { call: 'KEEP', why: 'customer-service / policy page' };
  if (hit && product && !content) return { call: 'REMOVE', why: `${hit[0]} ${slug.includes('keyword') || slug.includes('search') ? 'listing' : 'product'} page` };
  if (hit && content) return { call: 'KEEP', why: `names ${hit[0]} but is a content page, not a product` };
  if (out && product) return { call: 'CALL', why: `${out[0]} product — a category we sell but scoped out of SEO` };
  if (hit) return { call: 'REVIEW', why: `names ${hit[0]}; page type unclear` };
  return { call: 'KEEP', why: product ? 'product page outside our categories' : 'not a product of ours' };
}

// the HOMEPAGE rule this replaces, kept only so the fixture can prove it fails. 18i: it is called by
// nothing but that fixture, so the fixture documents the regression and guards no live code path.
export const oldHomepageRule = (r) => (r.cart >= 2 && r.price >= 1 && r.cats.length) ? 'T1' : (r.cart >= 2 && r.price >= 1) ? 'T2' : 'T3';

export const FIXTURES = [
  ['GENERAL RETAILER: homepage names no category, linked URL is a sauna product -> REMOVE',
    () => classifyLinkedUrl('https://www.costco.com/p/-/dynamic-bellagio-3-person-low-emf-far-infrared-sauna/100370044').call === 'REMOVE'],
  ['...and the OLD homepage rule keeps that same retailer (T3) — the regression this catches',
    () => oldHomepageRule({ title: 'Welcome to Costco Wholesale', cart: 1, price: 1, cats: [] }) === 'T3'],
  ['category word in a GUIDE url is KEEP, not REMOVE (bachmanns shape)',
    () => classifyLinkedUrl('https://bachmanns.com/sauna-maintenance-guide/').call === 'KEEP'],
  ['.product. style url with a cold plunge -> REMOVE',
    () => classifyLinkedUrl('https://www.costco.com/lifetrend-cold-plunge-hot-soak-tub.product.123.html').call === 'REMOVE'],
  ['sauna SEARCH listing -> REMOVE',   () => classifyLinkedUrl('https://www.costco.com/s?keyword=sauna').call === 'REMOVE'],
  ['return-policy page -> KEEP',       () => classifyLinkedUrl('https://customerservice.costco.com/app/answers/list/p/2166').call === 'KEEP'],
  ['massage recliner product -> REMOVE', () => classifyLinkedUrl('https://www.rcwilley.com/dp/OV-zero-gravity-massage-recliners').call === 'REMOVE'],
  ['fire pit product -> CALL, not auto', () => classifyLinkedUrl('https://www.homedepot.com/p/reviews/Breeo-X-Series-19-Smokeless-Fire-Pit').call === 'CALL'],
  ['unrelated product -> KEEP',        () => classifyLinkedUrl('https://www.costco.com/p/-/kirkland-paper-towels/1').call === 'KEEP'],
  // 18i: proves the !content leg — a product-shaped path (/c/) that is a guide stays KEEP
  ['guide under a /c/ path -> KEEP',   () => classifyLinkedUrl('https://www.homedepot.com/c/sauna-buying-guide').call === 'KEEP'],
  // 18i: proves the product leg and the REVIEW branch — a category slug of unclear page type is REVIEW, never REMOVE or KEEP
  ['unclear page type -> REVIEW',      () => classifyLinkedUrl('https://www.costco.com/sauna-deals').call === 'REVIEW'],
  ['unclear page type (.html) -> REVIEW', () => classifyLinkedUrl('https://www.costco.com/sauna-buying-tips.html').call === 'REVIEW'],
  // 18i: proves the customer-service rule — this path is product-shaped (/p/) and names sauna, so only that rule keeps it
  ['customer-service host, product-shaped path -> KEEP', () => classifyLinkedUrl('https://customerservice.costco.com/p/sauna-return-policy').call === 'KEEP'],
  ['customer-service answers page -> KEEP', () => classifyLinkedUrl('https://customerservice.costco.com/app/answers/sauna-return').call === 'KEEP'],
  // 18i: proves the unparseable branch lands on REVIEW, the safe side
  ['unparseable URL -> REVIEW',        () => classifyLinkedUrl('not a url').call === 'REVIEW'],
  // 18i: one product URL per category regex no other fixture exercises
  ['hot tub product -> REMOVE',        () => classifyLinkedUrl('https://www.homedepot.com/p/4-Person-Hot-Tub/123').call === 'REMOVE'],
  ['chiller product -> REMOVE',        () => classifyLinkedUrl('https://www.amazon.com/dp/1hp-water-chiller').call === 'REMOVE'],
  ['steam generator product -> REMOVE', () => classifyLinkedUrl('https://www.lowes.com/p/steam-generator-9kw/555').call === 'REMOVE'],
];
import { fileURLToPath } from 'node:url';
// compare PATHS: the repo path contains spaces, and a raw file:// comparison silently never matched
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let bad = 0;
  for (const [l, f] of FIXTURES) { const ok = f(); console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${l}`); if (!ok) bad++; }
  process.exitCode = bad ? 1 : 0;
}
