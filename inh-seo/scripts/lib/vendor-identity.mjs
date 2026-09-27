/* Which vendor strings are the SAME COMPANY, and is a name in copy this product's own manufacturer?
 *
 * WHY THIS IS A LIBRARY. This map lived inside scripts/audit/cross-manufacturer-panels.mjs, where it
 * cut a finding from 65 to 22. The all-surfaces sweep was written later, did not have it, and so counted
 * a manufacturer naming itself as a supplier defect — 9 surfaces on one product. A rule encoded in one
 * probe is not encoded in the estate, and the second probe had no way to know the first had solved it.
 *
 * Every entry is hand-verified with its reason. Exempting by name with a reason has been the right
 * answer six times this round; loosening the match has not been right once.
 */
export const SAME_COMPANY = [
  { group: ['dundalkleisurecraft', 'leisurecraft', 'dundalk'], why: 'one company. Two vendor strings (merged 2026-09-27) plus the bare "Dundalk" the copy uses — an alias, not a vendor string, and sweeps search for it' },
  { group: ['scandiamanufacturing', 'scandia'], why: 'one company, two vendor strings (16 and 9 ACTIVE)' },
  { group: ['huum'], why: 'HUUM and Huum differ only in case; norm() already merges them' },
  { group: ['mrsteam'], why: 'Mr. Steam and MR. STEAM differ only in case and punctuation' },
  { group: ['saunalife'], why: 'SaunaLife and SAUNA LIFE differ only in case and spacing' },
  { group: ['calflame', 'calspa'], why: 'sibling brands of one manufacturer. NOT merged — the client ruled they are separate lines' },
  { group: ['frozen', 'medicalbreakthrough'], why: "Frozen is Medical Breakthrough's Frozen Series, confirmed by the product's own panel" },
];
/* Distributors, which are never vendor strings in this catalogue, so a vendor-based sweep cannot see
   them. Named here so any probe asking "is this a supplier" has one source. */
export const DISTRIBUTORS = ['Bathing Brands'];
export const OURS = ['inhousewellness', 'inhousewellnesscom'];

/* ── NAME VARIANTS, GENERATED not listed ───────────────────────────────────────────────────────────
 * A sweep searching "Bathing Brands" missed "BathingBrands" — the glued form, which reaches the page
 * through CustomerService@BathingBrands.com. The rewrite rules handled it; the sweep that SIZED the work
 * did not, so custom.warranty_details was reported as 3 products when it was more. Same shape as the
 * SimpleSteam glued compound this project already recorded.
 *
 * Generated rather than listed: spaced, glued and the email-domain form are mechanical transforms of one
 * name, so adding a supplier to the map gives it every form without anyone remembering. ALIASES are the
 * part that cannot be generated — "Dundalk" for "Dundalk Leisurecraft" is a human shortening — so those
 * stay hand-declared, with a reason each. */
export const ALIASES = {
  'Dundalk Leisurecraft': ['Dundalk'],          // the copy's own short form; no vendor is called this
};
export function nameVariants(name) {
  const glued = name.replace(/\s+/g, '');
  const out = new Set([name, glued, `${glued}.com`, `@${glued}`]);
  for (const a of ALIASES[name] || []) { out.add(a); out.add(a.replace(/\s+/g, '')); }
  return [...out];
}
/* every form of every distributor, longest first so a specific match is tried before a substring */
export const supplierTerms = (extra = []) => [...new Set([...DISTRIBUTORS, ...extra].flatMap(nameVariants))]
  .sort((a, b) => b.length - a.length);

export const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
export function sameCompany(a, b) {
  const x = norm(a), y = norm(b);
  if (!x || !y) return false;
  if (x === y) return true;
  return SAME_COMPANY.some((e) => e.group.includes(x) && e.group.includes(y));
}
/* A company name in a product's copy is the MANUFACTURER (legitimate) when it matches the product's own
   vendor, allowing for the same-company variants above. Anything else is a supplier reference. */
export const isOwnManufacturer = (name, ownVendor) => sameCompany(name, ownVendor);

export const VENDOR_IDENTITY_FIXTURES = [
  ['a string is the same company as itself', () => sameCompany('Harvia', 'Harvia'), true],
  ['two vendor strings for one company', () => sameCompany('Leisure Craft', 'Dundalk Leisurecraft'), true],
  ['Scandia and Scandia Manufacturing', () => sameCompany('Scandia', 'Scandia Manufacturing'), true],
  ['case-only variants', () => sameCompany('HUUM', 'Huum'), true],
  ['MR. STEAM and Mr. Steam', () => sameCompany('MR. STEAM', 'Mr. Steam'), true],
  ['SAUNA LIFE and SaunaLife', () => sameCompany('SAUNA LIFE', 'SaunaLife'), true],
  ['different brands are NOT the same company', () => sameCompany('Harvia', 'Dundalk Leisurecraft'), false],
  ['Cal Flame and Cal Spa ARE one company for identity purposes', () => sameCompany('Cal Spa', 'Cal Flame'), true],
  ['an empty vendor is never a match', () => sameCompany('', 'Harvia'), false],
  ['a distributor is not any vendor', () => sameCompany('Bathing Brands', 'Harvia'), false],
  ['isOwnManufacturer: Dundalk on a Dundalk product is legitimate', () => isOwnManufacturer('Dundalk Leisurecraft', 'Leisure Craft'), true],
  ['isOwnManufacturer: Dundalk on a Harvia product is not', () => isOwnManufacturer('Dundalk Leisurecraft', 'Harvia'), false],
  ['variants include the GLUED form — the one the sweep missed', () => nameVariants('Bathing Brands').includes('BathingBrands'), true],
  ['variants include the email-domain form', () => nameVariants('Bathing Brands').includes('BathingBrands.com'), true],
  ['variants include the spaced original', () => nameVariants('Bathing Brands').includes('Bathing Brands'), true],
  ['a hand-declared alias is included', () => nameVariants('Dundalk Leisurecraft').includes('Dundalk'), true],
  ['supplierTerms is sorted longest-first', () => { const t = supplierTerms(); return t[0].length >= t[t.length - 1].length; }, true],
  ['supplierTerms covers the glued form without anyone listing it', () => supplierTerms().includes('BathingBrands'), true],
  ['the bare alias "Dundalk" matches its vendor string', () => sameCompany('Dundalk', 'Dundalk Leisurecraft'), true],
  ['the bare alias does NOT match a different brand', () => sameCompany('Dundalk', 'Harvia'), false],
];
