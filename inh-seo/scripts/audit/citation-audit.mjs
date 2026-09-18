/**
 * Who does our own content cite as the authority?
 *
 * Two shapes, and only one of them is visible to a link crawler:
 *   1. an outbound <a> to another domain
 *   2. an inline text citation — "(Sun Home Saunas, 2026)" — with no link at all
 *
 * The second is the majority and the one that matters editorially: it is the
 * claim's SOURCE, so removing it leaves the claim unsourced. Counting links
 * alone reported 6 where the real figure was 79.
 *
 * Read-only.
 */
import path from 'node:path';
import { readJSON, DATA } from '../lib/util.js';

const arts = readJSON(path.join(DATA, 'content.json')).articles || [];
const raw = (a) => String(a.bodyHtml || a.body || '');
const text = (a) => raw(a).replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ');

/* Retailers that sell what we sell, to the same buyer. NOT the same thing as a
   manufacturer whose products we stock (Harvia, HUUM, Dundalk) — citing your own
   supplier's spec sheet is normal and correct. */
const COMPETING_RETAILER = {
  'Sun Home Saunas': { re: /sun\s?home\s+saunas?/gi, domains: [/sunhomesaunas\.com/i] },
  Sunlighten:        { re: /sunlighten/gi,           domains: [/sunlighten\.com/i] },
  Clearlight:        { re: /clearlight/gi,           domains: [/infraredsauna\.com/i, /clearlightsaunas?\./i] },
  HigherDose:        { re: /higher\s?dose/gi,        domains: [/higherdose\.com/i] },
  'Almost Heaven':   { re: /almost\s+heaven/gi,      domains: [/almostheaven\.com/i] },
  Costco:            { re: /costco/gi,               domains: [/costco\.com/i] },
  'Heavenly Heat':   { re: /heavenly\s+heat/gi,      domains: [/heavenlyheatsaunas\.com/i] },
  'Health Mate':     { re: /health\s?mate/gi,        domains: [/healthmatesauna\.com/i] },
  Therasage:         { re: /therasage/gi,            domains: [/therasage\.com/i] },
  'Sauna Space':     { re: /sauna\s?space/gi,        domains: [/saunaspace\.com/i] },
  'Plunge':          { re: /\bplunge\.com\b/gi,      domains: [/(?<!cold)plunge\.com/i] },
  Redwood:           { re: /redwood\s+outdoors/gi,   domains: [/redwoodoutdoors\.com/i] },
  'Sauna House':     { re: /sauna\s?house/gi,        domains: [/saunahouse\./i] },
};

/* A citation is the source of a claim: "(Brand, 2026)" or "[Brand, 2026]".
   A passing mention in prose is not. The distinction decides whether removing
   the name leaves a claim unsupported.

   THIS PATTERN WAS ROUND-BRACKETS-ONLY and that is how the Sun Home sweep came
   back clean. `sauna-wood-species-…` cites `[Sun Home Saunas, 2026]` five times
   in square brackets, plus a bibliography line with a live URL. The removal
   script and this audit shared the bracket assumption, so the completion check
   confirmed the removal in the only form either of them could see.

   A verification that shares its blind spot with the thing it verifies is not a
   verification. One concept, one pattern, and the pattern has to cover every
   physical representation of the concept — the citation rule at the punctuation
   level. */
const citationRe = (brandRe) => new RegExp(
  `[([]\\s*[^()\\[\\]]*?${brandRe.source}[^()\\[\\]]*?,\\s*\\d{4}\\s*[)\\]]`, 'gi');

/* A bare domain with no href and no bracket is the third form, and it is
   invisible to a link check AND to a citation check. It carries the same
   borrowed authority. */
const bareDomainRe = (domains) => new RegExp(
  domains.map((d) => d.source.replace(/^\(\?<!cold\)/, '')).join('|'), 'gi');

/* The three forms counted for one brand in one document. A function so the fixtures below
   exercise the same code the sweep runs (18i: bare and link counts had no fixture at all). */
function countForms(r, t, cfg) {
  const links = [...r.matchAll(/href="(https?:\/\/[^"]+)"/gi)].map((m) => m[1]);
  const cites = [...t.matchAll(citationRe(cfg.re))].length;
  const mentions = [...t.matchAll(cfg.re)].length;
  const outLinks = links.filter((u) => cfg.domains.some((d) => d.test(u)));
  /* count domain strings that are NOT inside an href — the bare form */
  const hrefText = links.join(' ');
  const allDomain = [...r.matchAll(bareDomainRe(cfg.domains))].length;
  const inHref = [...hrefText.matchAll(bareDomainRe(cfg.domains))].length;
  const bare = Math.max(0, allDomain - inHref);
  return { cites, mentions, bare, outLinks };
}

const rows = [];
for (const a of arts) {
  const t = text(a), r = raw(a);
  for (const [brand, cfg] of Object.entries(COMPETING_RETAILER)) {
    const { cites, mentions, bare, outLinks } = countForms(r, t, cfg);
    if (cites || outLinks.length || bare) rows.push({ article: a.handle, brand, cites, mentions, bare, links: outLinks.length, urls: [...new Set(outLinks)] });
  }
}

rows.sort((x, y) => (y.cites + y.links * 3) - (x.cites + x.links * 3));
const byBrand = {};
for (const r of rows) {
  byBrand[r.brand] ||= { cites: 0, links: 0, articles: new Set() };
  byBrand[r.brand].cites += r.cites; byBrand[r.brand].links += r.links; byBrand[r.brand].bare = (byBrand[r.brand].bare || 0) + r.bare; byBrand[r.brand].articles.add(r.article);
}

console.log(`citation-audit — ${arts.length} articles\n`);
console.log('BY BRAND');
console.log('  brand'.padEnd(24) + 'citations  links   bare  articles');
for (const [b, v] of Object.entries(byBrand).sort((x, y) => (y[1].cites + y[1].links) - (x[1].cites + x[1].links)))
  console.log('  ' + b.padEnd(22) + String(v.cites).padStart(6) + String(v.links).padStart(7) + String(v.bare).padStart(7) + String(v.articles.size).padStart(10));

console.log('\nBY ARTICLE (citation = the claim s source; a link with 0 citations is usually a reference, not an authority)');
console.log('  article'.padEnd(58) + 'brand'.padEnd(18) + 'cites  links   bare');
for (const r of rows) console.log('  ' + r.article.slice(0, 55).padEnd(56) + r.brand.padEnd(18) + String(r.cites).padStart(5) + String(r.links).padStart(7) + String(r.bare).padStart(7));

const totalC = rows.reduce((s, r) => s + r.cites, 0), totalL = rows.reduce((s, r) => s + r.links, 0), totalB = rows.reduce((s, r) => s + r.bare, 0);
console.log(`\n${rows.length} article/brand pairs · ${totalC} citations · ${totalL} outbound links · ${totalB} bare domains · ${new Set(rows.map(r => r.article)).size} distinct articles of ${arts.length}`);

/* Known-positive check — SYNTHETIC, and it has to be.

   The first version named the live article that cited `[Sun Home Saunas, 2026]`
   in square brackets. It passed, those citations were removed the same day, and
   the check then FAILED: the guard died the moment its subject was repaired.
   Same failure as `health-claim-screen.mjs` anchoring to a live sentence.

   These strings are constructed. The square-bracket one is the case the
   implementation was NOT built for — the whole point of the amended rule 6c. */
const FIXTURES = [
  ['(Sun Home Saunas, 2026)', 'Sun Home Saunas', 1, 'round brackets — the form the old pattern matched'],
  ['[Sun Home Saunas, 2026]', 'Sun Home Saunas', 1, 'SQUARE brackets — the form that closed the sweep at a false zero'],
  ['[Clearlight Saunas AU, 2025]', 'Clearlight', 1, 'square brackets, second brand'],
  ['Sun Home Saunas make good cabins.', 'Sun Home Saunas', 0, 'a bare mention is not a citation'],
  ['(Laukkanen et al., 2018)', 'Sun Home Saunas', 0, 'an unrelated citation must not match'],
];
console.log('\nKNOWN-POSITIVE CHECK (synthetic)');
let bad = 0;
for (const [sample, brand, expect, why] of FIXTURES) {
  const n = [...sample.matchAll(citationRe(COMPETING_RETAILER[brand].re))].length;
  const ok = n === expect;
  if (!ok) bad += 1;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${why} — expected ${expect}, got ${n}`);
}
/* 18i: the bare-domain and outbound-link counts, on one constructed document — one bare
   mention, one linked (whose href text must NOT also count as bare), and one unrelated link. */
const FORMS_DOC = '<p>Specs are on sunhomesaunas.com if you want them.</p>'
  + '<p>See <a href="https://www.sunhomesaunas.com/products/x">their page</a> and <a href="https://pubmed.ncbi.nlm.nih.gov/1/">a study</a>.</p>';
const forms = countForms(FORMS_DOC, FORMS_DOC.replace(/<[^>]+>/g, ' '), COMPETING_RETAILER['Sun Home Saunas']);
for (const [label, got, want] of [['bare domain outside an href', forms.bare, 1], ['outbound link to the brand', forms.outLinks.length, 1]]) {
  const ok = got === want;
  if (!ok) bad += 1;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label} — expected ${want}, got ${got}`);
}
if (bad) { console.error(`\n${bad} fixture(s) failed. The pattern has narrowed; do not trust any count above.`); process.exitCode = 1; }
