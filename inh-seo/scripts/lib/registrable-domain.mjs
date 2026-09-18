/* Registrable domain of a host — ONE implementation, shared by r17-outbound-links and
 * r18-prestate. Round 18i: r18-prestate carried a copy of r17's reg() with no fixtures of its
 * own, so a fix to one would silently not reach the other.
 *
 * Public suffixes with a second label. Taking the last TWO labels of "saunas.com.au" yields
 * "com.au", which is a SUFFIX, not a domain. Where the last two labels are a suffix, take three.
 *
 * `keepWhole(h)` (optional) lets a caller keep a hand-declared multi-label host intact —
 * r17 keeps shop-us.sunlighten.com and pubmed.ncbi.nlm.nih.gov whole because its buckets are
 * declared at that granularity. r18-prestate passes nothing and gets the plain rule.
 *
 * The fixtures run at IMPORT, so every importer is guarded without having to remember to call
 * anything: a broken rule throws before a single domain is counted.
 *   node scripts/lib/registrable-domain.mjs     # runs the fixtures and prints them
 */
import { fileURLToPath } from 'node:url';

export const MULTI_SUFFIX = new Set([
  'com.au','net.au','org.au','edu.au','gov.au','co.uk','org.uk','ac.uk','gov.uk','me.uk',
  'co.nz','org.nz','govt.nz','co.za','co.jp','ne.jp','or.jp','ac.jp','go.jp','com.br',
  'com.mx','com.ar','com.sg','com.my','com.hk','com.tw','com.cn','org.cn','co.in','co.kr',
  'com.tr','co.il','com.pl','com.ua','com.ph','co.th','com.vn','com.co','com.pe','com.ve',
]);

export function registrableDomain(host, keepWhole = null) {
  const h = String(host).toLowerCase().replace(/^www\./, '');
  if (keepWhole && keepWhole(h)) return h;
  const p = h.split('.');
  if (p.length <= 2) return h;
  const lastTwo = p.slice(-2).join('.');
  return MULTI_SUFFIX.has(lastTwo) ? p.slice(-3).join('.') : lastTwo;
}

// 18i: constructed fixtures — they guard every importer, because they run on import
const KEEP = (h) => h === 'shop-us.sunlighten.com';
export const REGISTRABLE_FIXTURES = [
  ['www stripped',                        registrableDomain('www.example.com') === 'example.com'],
  ['upper case folded',                   registrableDomain('WWW.Example.COM') === 'example.com'],
  ['co.uk keeps three labels',            registrableDomain('shop.example.co.uk') === 'example.co.uk'],
  ['www + co.uk',                         registrableDomain('www.example.co.uk') === 'example.co.uk'],
  ['bare co.uk domain unchanged',         registrableDomain('example.co.uk') === 'example.co.uk'],
  ['com.au is a suffix, not a domain',    registrableDomain('a.b.saunas.com.au') === 'saunas.com.au'],
  ['plain subdomain collapses to 2',      registrableDomain('blog.example.com') === 'example.com'],
  ['deep subdomain collapses to 2',       registrableDomain('pubmed.ncbi.nlm.nih.gov') === 'nih.gov'],
  ['keepWhole keeps a declared host',     registrableDomain('shop-us.sunlighten.com', KEEP) === 'shop-us.sunlighten.com'],
  ['keepWhole sees the www-stripped host',registrableDomain('www.shop-us.sunlighten.com', KEEP) === 'shop-us.sunlighten.com'],
  ['without keepWhole it collapses',      registrableDomain('shop-us.sunlighten.com') === 'sunlighten.com'],
];
const failed = REGISTRABLE_FIXTURES.filter(([, ok]) => !ok).map(([l]) => l);
if (failed.length) throw new Error(`registrable-domain fixtures FAILED: ${failed.join('; ')}`);
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  for (const [l] of REGISTRABLE_FIXTURES) console.log(`  ok   ${l}`);
}
