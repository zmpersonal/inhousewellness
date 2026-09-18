/* Round 17 — enumerate EVERY external link across all live articles, grouped by domain.
 * READ-ONLY. Changes nothing.
 *
 * Reads bodies from the LIVE Admin API, not data/content.json: the dump holds 118 articles
 * and the store has 120 (are-saunas-good-for-you, how-often-should-you-use-sauna are newer
 * than the dump). Auditing the dump would have reported a 120-article sweep that read 118.
 *
 * METHOD (a count is population + pattern + source):
 *   population : all articles returned by articles(first:250), any publication state
 *   pattern    : linksOf() — href="…" or href='…' on <a>, over article.body, keeping http(s) hosts
 *                whose registrable domain is not inhousewellness.com
 *   source     : Shopify Admin API 2026-07, live at run time
 *
 * Classification is a RELATIONSHIP and cannot be read off markup (CLAUDE.md: a manufacturer's
 * product page and a competitor's carry identical schema). Domains are bucketed from a
 * hand-declared list; anything unlisted lands in UNCLASSIFIED and must be read by a person.
 */
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { registrableDomain } from '../lib/registrable-domain.mjs';

// hand-declared, each with a reason. Never inferred from markup.
const OWN = new Set(['inhousewellness.com']);
const SATELLITE = new Set([            // our own reference network — not outbound leakage
  'besthomeinfraredsauna.com', 'healthresearchdatabase.com', 'saunasfactorydirect.com',
  'saunaimport.com', 'infinitesauna.com', 'thesaunaheater.com', 'coldplungefactory.com',
  'saunacalculator.com', 'homesaunaclimate.com', 'saunatap.com',
]);
const CITATION = new Set([             // research / standards / government / .edu
  'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov', 'pmc.ncbi.nlm.nih.gov', 'doi.org',
  'nih.gov', 'cdc.gov', 'cpsc.gov', 'fda.gov', 'epa.gov', 'osha.gov', 'census.gov',
  'eia.gov', 'noaa.gov', 'usda.gov', 'fs.usda.gov', 'nfpa.org', 'ul.com', 'iec.ch',
  'nature.com', 'sciencedirect.com', 'springer.com', 'wiley.com', 'jamanetwork.com',
  'nejm.org', 'thelancet.com', 'bmj.com', 'frontiersin.org', 'mdpi.com', 'plos.org',
  'physiology.org', 'ahajournals.org', 'mayoclinic.org', 'hopkinsmedicine.org',
  'clevelandclinic.org', 'harvard.edu', 'health.harvard.edu', 'poison.org',
  'researchgate.net', 'semanticscholar.org', 'scholar.google.com', 'bioresources.com',
]);
const MANUFACTURER = new Set([         // makers of what we sell — documentation sources
  'goldendesigninc.com', 'harvia.com', 'huum.com', 'narvi.fi', 'almostheaven.com',
  'saunalife.com', 'finnmarksauna.com', 'thermasol.com', 'mrsteam.com', 'scandiamfg.com',
  'dundalkleisurecraft.com', 'medicalsaunas.com', 'dreampod.com', 'icetubs.com',
  'maxxussaunas.com', 'dynamicsaunas.com',
]);
const COMPETITOR = new Set([           // retailers selling the same categories we do
  'nurecover.com', 'sunhomesaunas.com', 'clearlight.com', 'sunlighten.com',
  'shop-us.sunlighten.com', 'saunaspace.com', 'plungeoutdoors.com', 'thecoldplunge.com',
  'zogics.com', 'saunaking.com', 'thesaunaheaven.com', 'heavenlyheatsaunas.com',
  'amazon.com', 'costco.com', 'wayfair.com', 'homedepot.com', 'lowes.com', 'walmart.com',
  'skywardmedical.com', 'recoveryforathletes.com', 'northernsaunas.com', 'saunaplace.com',
]);
const COMMUNITY = new Set(['reddit.com', 'old.reddit.com', 'youtube.com', 'youtu.be', 'facebook.com', 'instagram.com', 'x.com', 'twitter.com']);
const EDITORIAL = new Set(['businessinsider.com', 'cnn.com', 'insidehook.com', 'garagegymreviews.com', 'nytimes.com', 'forbes.com', 'menshealth.com', 'health.com', 'webmd.com', 'healthline.com']);

/* Round 18i: the suffix table and the rule now live in ../lib/registrable-domain.mjs, shared with
   r18-prestate. This script keeps its declared multi-label hosts whole (keepWhole) because its
   buckets are declared at that granularity; the lib's own fixtures run on import. */
const DECLARED = (h) => SATELLITE.has(h) || CITATION.has(h) || MANUFACTURER.has(h) || COMPETITOR.has(h) || COMMUNITY.has(h) || EDITORIAL.has(h) || OWN.has(h);
const reg = (host) => registrableDomain(host, DECLARED);
/* Every href on an <a>, either quote style. The first pattern read only href="…", so a
   single-quoted anchor was invisible and its domain never counted. */
const A = /<a\b[^>]*\shref=(?:"([^"]*)"|'([^']*)')/gi;
const linksOf = (body) => [...String(body || '').matchAll(A)].map((m) => (m[1] ?? m[2]).trim());
const bucket = (h) => SATELLITE.has(h) ? 'SATELLITE (ours)' : CITATION.has(h) ? 'CITATION'
  : MANUFACTURER.has(h) ? 'MANUFACTURER' : COMPETITOR.has(h) ? 'COMPETITOR MERCHANT'
  : COMMUNITY.has(h) ? 'COMMUNITY / SOCIAL' : EDITORIAL.has(h) ? 'EDITORIAL'
  : /\.(gov|edu)$/.test(h) ? 'CITATION' : 'UNCLASSIFIED — needs a read';

// ── constructed fixtures (CLAUDE.md 6c): must hold, or the run fails ──
const FIX = [
  ['own host stripped of www',        reg('www.inhousewellness.com') === 'inhousewellness.com'],
  ['subdomain kept when declared',    reg('shop-us.sunlighten.com') === 'shop-us.sunlighten.com'],
  ['ccSLD keeps three labels',        reg('blog.example.co.uk') === 'example.co.uk'],
  ['com.au is a suffix, not a domain',reg('shop.saunas.com.au') === 'saunas.com.au'],
  ['plain subdomain collapses to 2',  reg('blog.example.com') === 'example.com'],
  ['bare 2-label host unchanged',     reg('example.com') === 'example.com'],
  ['.gov falls to CITATION',          bucket('somewhere.gov') === 'CITATION'],
  ['unknown host is not guessed',     bucket('mystery-shop.com') === 'UNCLASSIFIED — needs a read'],
  ['competitor beats the .com rule',  bucket('nurecover.com') === 'COMPETITOR MERCHANT'],
  // 18i: proves each remaining bucket is reachable — a dropped branch otherwise falls to UNCLASSIFIED silently
  ['manufacturer bucket',             bucket('harvia.com') === 'MANUFACTURER'],
  ['satellite bucket',                bucket('besthomeinfraredsauna.com') === 'SATELLITE (ours)'],
  ['editorial bucket',                bucket('webmd.com') === 'EDITORIAL'],
  ['community bucket',                bucket('reddit.com') === 'COMMUNITY / SOCIAL'],
  // 18i: proves www is stripped BEFORE the declared-host check
  ['www + declared subdomain kept',   reg('www.shop-us.sunlighten.com') === 'shop-us.sunlighten.com'],
  // 18i: proves link extraction reads both quote styles and ignores non-anchors
  ['extracts double and single-quoted href', JSON.stringify(linksOf(`<a href="https://a.com/x">a</a> <a class='c' href='https://b.com/y'>b</a> <link href="https://c.com"> <a data-href="https://d.com">d</a>`)) === '["https://a.com/x","https://b.com/y"]'],
];
let bad = 0;
console.log('FIXTURES');
for (const [l, ok] of FIX) { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${l}`); if (!ok) bad++; }
if (bad) { console.log('refusing — fixtures did not hold'); process.exit(1); }

// ── population ──
let cur = null; const arts = [];
while (true) {
  const r = await gql(`query($c:String){ articles(first:250, after:$c){ pageInfo{hasNextPage endCursor} nodes{ handle title isPublished body blog{handle} } } }`, { c: cur });
  arts.push(...r.articles.nodes);
  if (!r.articles.pageInfo.hasNextPage) break;
  cur = r.articles.pageInfo.endCursor;
}
console.log(`\nPOPULATION: ${arts.length} live articles (${arts.filter(a => a.isPublished).length} published)`);

const rows = [];
for (const a of arts) {
  for (const href of linksOf(a.body)) {
    if (!/^https?:\/\//i.test(href)) continue;
    let host; try { host = new URL(href).hostname; } catch { continue; }
    const d = reg(host);
    if (OWN.has(d)) continue;
    rows.push({ article: a.handle, blog: a.blog.handle, published: a.isPublished, domain: d, href });
  }
}
const byDomain = {};
for (const r of rows) (byDomain[r.domain] ||= []).push(r);

const groups = {};
for (const [d, rs] of Object.entries(byDomain)) (groups[bucket(d)] ||= []).push([d, rs]);

const ORDER = ['COMPETITOR MERCHANT', 'UNCLASSIFIED — needs a read', 'MANUFACTURER', 'EDITORIAL', 'COMMUNITY / SOCIAL', 'SATELLITE (ours)', 'CITATION'];
console.log(`\nEXTERNAL LINKS: ${rows.length} across ${Object.keys(byDomain).length} domains in ${new Set(rows.map(r => r.article)).size} articles\n`);
for (const g of ORDER) {
  const gs = (groups[g] || []).sort((x, y) => y[1].length - x[1].length);
  const total = gs.reduce((s, [, rs]) => s + rs.length, 0);
  console.log(`── ${g} — ${total} link(s) across ${gs.length} domain(s)`);
  for (const [d, rs] of gs) {
    const artsIn = [...new Set(rs.map(r => r.article))];
    console.log(`   ${String(rs.length).padStart(3)}  ${d.padEnd(34)} in ${artsIn.length} article(s)`);
    if (g === 'COMPETITOR MERCHANT' || g === 'UNCLASSIFIED — needs a read') {
      for (const h of artsIn.slice(0, 6)) console.log(`         · ${h}`);
      if (artsIn.length > 6) console.log(`         · …${artsIn.length - 6} more`);
    }
  }
  console.log('');
}
fs.writeFileSync('data/r17-outbound-links.json', JSON.stringify({ generatedAt: new Date().toISOString(), population: arts.length, totalExternalLinks: rows.length, rows }, null, 2));
console.log('full row-level detail -> data/r17-outbound-links.json');
