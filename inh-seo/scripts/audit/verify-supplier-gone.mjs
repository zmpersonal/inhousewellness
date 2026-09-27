/* Document-level: is a supplier name gone from the WHOLE rendered page?
 *   node scripts/audit/verify-supplier-gone.mjs <handle>… | --sample | --self-test
 *
 * The row-scoped reader could not see two of 92 edits, because row titles vary by vendor
 * ("Shipping Details", "Fast & Free Shipping") and one product renders a Video row no other has.
 * A reader keyed on a row title is keyed on something that varies. This asks the question the client's
 * ruling actually asks — "no supplier named on the product page" — of the entire document.
 *
 * A name that is the product's OWN manufacturer is legitimate and is not a failure.
 */
import { pathToFileURL } from 'node:url';
import { gql } from '../lib/shopify.js';
import { isOwnManufacturer, DISTRIBUTORS, supplierTerms } from '../lib/vendor-identity.mjs';

/* generated, not listed: the glued and email-domain forms come from vendor-identity.mjs */
const SUPPLIERS = supplierTerms(['Dundalk Leisurecraft']);
/* ── A CROSS-CHECK, NOT THE MEASUREMENT ─────────────────────────────────────────────────────────────
 * THE MEASUREMENT is the field sweep (scripts/audit/supplier-names-all-surfaces.mjs), which reads the
 * metafields directly. THIS is a second instrument with a different blind spot, and its value is exactly
 * what it demonstrated: it found custom.warranty, a field the sweep never listed.
 *
 * IT CANNOT BE THE AUTHORITY. Three false-positive mechanisms appeared on one page:
 *   1. CDN cache serving a pre-edit copy            — preventable, and prevented (the retry below)
 *   2. JSON payloads naming OTHER products' vendors — preventable, and prevented (scripts stripped)
 *   3. the mega-menu listing every brand we sell    — NOT PREVENTABLE. It is correct behaviour, and no
 *      exclusion rule can tell it from a defect without encoding this theme's container structure.
 *
 * THE GENERAL FORM: an outcome check on a rendered page measures every actor on that page, and
 * separating them requires knowing which is which. The more precisely you scope it, the more it measures
 * your model of the theme rather than the outcome. So it is scoped once, honestly, and no further.
 *
 * WHAT IT STRIPS: <script>, <style>, <noscript>, HTML comments, all tags.
 * WHAT IT THEREFORE CANNOT SEE: anything in a script or JSON payload, alt text, title attributes, meta
 *   tags, and anything a widget injects client-side.
 * WHAT IT STILL SEES THAT IS NOT THIS PRODUCT'S COPY: global navigation, brand menus, recommendation
 *   carousels, footer. All legitimate.
 *
 * SO: A FAIL IS A READING QUEUE, NOT A DEFECT. Read the context before believing it. A pass is
 * meaningful; a fail means "a supplier name is somewhere in this page's visible text", which on this
 * storefront is true of every page because the menu names every brand.
 *
 * And neither instrument establishes completeness: the sweep misses fields nobody listed, this misses
 * everything that is not visible text. Both numbers are bounded, not settled. */
export const visibleCopy = (html) => html
  .replace(/<script[\s\S]*?<\/script>/gi, ' ')
  .replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&amp;/g, '&').replace(/&#39;|&rsquo;/g, "'").replace(/&nbsp;/g, ' ')
  .replace(/\s+/g, ' ');

export function offending(html, vendor) {
  html = visibleCopy(html);
  return SUPPLIERS.filter((s) => new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(html))
    .filter((s) => DISTRIBUTORS.some((d) => s.toLowerCase().includes(d.toLowerCase().replace(/\s/g, '')) || s.toLowerCase().includes(d.toLowerCase())) || !isOwnManufacturer(s, vendor))
    .filter((s, i, a) => a.indexOf(s) === i);
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (JSON.stringify(g) !== JSON.stringify(w)) { console.log(`FIXTURE FAIL: ${n} — want ${JSON.stringify(w)} got ${JSON.stringify(g)}`); bad++; } };
  eq('a clean page on a Harvia product', offending('<p>ships curbside via LTL freight</p>', 'Harvia'), []);
  /* the case the first version got wrong, on real markup from the live page */
  eq('another product\'s vendor inside a SCRIPT payload is not this product naming a supplier',
    offending('<p>clean copy</p><script>var x={"title":"Dundalk Leisurecraft Hot Tub","vendor":"Dundalk Leisurecraft"};</script>', 'Delta Faucet Co'), []);
  eq('...but the same name in VISIBLE copy still fails',
    offending('<h2>Why Choose Dundalk Leisurecraft?</h2>', 'Delta Faucet Co'), ['Dundalk Leisurecraft', 'Dundalk']);
  eq('a name in an HTML comment is not visible copy', offending('<!-- Bathing Brands -->', 'Harvia'), []);
  eq('a name in a style block is not visible copy', offending('<style>/* Bathing Brands */</style>', 'Harvia'), []);
  eq('Bathing Brands anywhere is a failure', offending('<p>contact Bathing Brands</p>', 'Harvia'), ['Bathing Brands']);
  eq('the supplier email is a failure', offending('<a>CustomerService@BathingBrands.com</a>', 'Harvia').length > 0, true);
  eq('Dundalk on a Harvia page is a failure', offending('<h2>Why Choose Dundalk Leisurecraft?</h2>', 'Harvia'), ['Dundalk Leisurecraft', 'Dundalk']);
  eq('Dundalk on a DUNDALK page is legitimate', offending('<h2>Why Choose Dundalk Leisurecraft?</h2>', 'Dundalk Leisurecraft'), []);
  eq('and on the other vendor string for that company', offending('<h2>Why Choose Dundalk Leisurecraft?</h2>', 'Leisure Craft'), []);
  return bad;
}
/* CLI GATED. I audited this exact hazard an hour ago and then wrote a new un-gated CLI: importing it to
   reuse visibleCopy ran it, printed usage and exited. Apply the pattern, do not just record it. */
const IS_MAIN = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (IS_MAIN) {
  const bad = selfTest();
  if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
  console.log('self-test: every fixture holds\n');
  if (process.argv.includes('--self-test')) process.exit(0);
}

if (IS_MAIN) await main();
async function main() {
let handles = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (process.argv.includes('--sample')) {
  let cur = null; const all = [];
  do { const d = await gql(`query($c:String){ products(first:250, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ handle status vendor } } }`, { c: cur });
    all.push(...d.products.nodes); cur = d.products.pageInfo.hasNextPage ? d.products.pageInfo.endCursor : null; } while (cur);
  const byV = {}; all.filter((p) => p.status === 'ACTIVE').forEach((p) => { (byV[p.vendor] ||= []).push(p.handle); });
  /* one per vendor in the edited set — the partition, not more samples */
  handles = ['Harvia', 'SaunaLife', 'Thermasol', 'Finnmark Designs', 'Delta Faucet Co', 'Ice Tubs', 'Mr. Steam']
    .map((v) => byV[v]?.[0]).filter(Boolean);
}
if (!handles.length) { console.log('usage: <handle>… or --sample'); process.exit(1); }

let fail = 0; const stale = [];
/* CACHE LAG IS NOT A DEFECT. This repo learned it once in verify-render: the CDN can serve a pre-edit
   copy for a minute. A guard that reports a stale page as a live defect trains people to ignore it, so
   a page that still names a supplier is RETRIED, and only a page that still names one after the retries
   is a finding. A page that never clears is UNREACHABLE — not a pass, and not a defect either. */
const TRIES = 4, WAIT_MS = 15000;
for (const h of handles) {
  const p = (await gql(`query($h:String!){ productByHandle(handle:$h){ vendor } }`, { h })).productByHandle;
  if (!p) { console.log(`  UNREACHABLE ${h}: not found`); fail++; continue; }
  let bad2 = null, tries = 0;
  for (let i = 0; i < TRIES; i++) {
    tries = i + 1;
    const res = await fetch(`https://inhousewellness.com/products/${h}?cb=${Date.now()}`, { headers: { 'User-Agent': 'inh-seo audit', 'Cache-Control': 'no-cache' } });
    if (res.status !== 200) { bad2 = null; console.log(`  UNREACHABLE ${h}: HTTP ${res.status}`); break; }
    bad2 = offending(await res.text(), p.vendor);
    if (!bad2.length) break;
    if (i < TRIES - 1) { console.log(`  RETRY ${tries}/${TRIES} ${h} — still names ${bad2.join(', ')}`); await new Promise((r) => setTimeout(r, WAIT_MS)); }
  }
  if (bad2 === null) { fail++; continue; }
  if (!bad2.length) { console.log(`  ok    ${h.padEnd(42)} [${p.vendor}]${tries > 1 ? `  (cleared after ${tries} fetches)` : ''}`); continue; }
  console.log(`  READ  ${h.padEnd(42)} [${p.vendor}]  names in visible text after ${tries} fetches: ${bad2.join(', ')}`);
  console.log('        ^ a reading queue, not a defect — the mega-menu names every brand we sell. Check the context.');
  fail++;
}
console.log(`\n  ${handles.length - fail}/${handles.length} pages carry no supplier name in visible text. A non-pass is a READING QUEUE — see the header.`);
process.exit(fail ? 1 : 0);
}
