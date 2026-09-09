/**
 * For every FEATURE-NAMED collection: what share of members actually evidence
 * the feature the collection is named for?
 *
 * A collection named for a feature is a promise. red-light-therapy holds 15
 * units that never mention red light anywhere a buyer can read. That is a
 * merchandising defect, not a copy problem, and copy written over it papers it.
 *
 * Method per CLAUDE.md 6c: product-defining attributes title-only, fitted
 * features title-or-body. Read-only. Fixes nothing.
 */
import path from 'node:path';
import { readJSON, DATA, probeText } from '../lib/util.js';

const products = readJSON(path.join(DATA, 'products.json'));
/* Normalise the Unicode dashes Shopify titles are full of. finnmark-fd-1's
   title reads "Full‑Spectrum" with U+2011 NON-BREAKING HYPHEN, which /full[- ]spectrum/
   does not match — it reported a correctly-filed product as not evidencing the
   feature the collection is named for. The pattern is part of the method (6c),
   and character class is part of the pattern. */
const clean = probeText; // shared: see util.js normalizeText, instance 16
const titleOf = (p) => clean(p.title);
const bodyOf = (p) => clean(String(p.descriptionHtml || '').replace(/<[^>]+>/g, ' '));

const TESTS = [
  ['chromotherapy',        /chromotherap|colou?r therapy/, 'BOTH',  'fitted feature'],
  ['red-light-therapy',    /red light/,                    'BOTH',  'fitted feature'],
  ['full-spectrum',        /full[- ]spectrum/,             'TITLE', 'product-defining'],
  ['hybrid',               /\bhybrid\b/,                   'TITLE', 'product-defining'],
  ['low-emf',              /low emf/,                      'TITLE', 'product-defining'],
  ['ultra-low-emf',        /ultra[- ]?low emf/,            'TITLE', 'product-defining'],
  ['near-zero-emf',        /near[- ]?zero emf/,            'TITLE', 'product-defining'],
  ['ice-tubs',             /ice ?(tub|bath|barrel)|cold ?plunge|plunge/, 'TITLE', 'product-defining'],
  ['steam-showers',        /steam/,                        'TITLE', 'product-defining'],
  ['medical-sauna',        'VENDOR:Medical Saunas',        'VENDOR', 'brand collection'],
];

for (const [handle, re, method, kind] of TESTS) {
  const members = products.filter((p) => p.collections.includes(handle) && p.status === 'ACTIVE');
  if (!members.length) { console.log(`\n${handle}: no ACTIVE members`); continue; }
  const hit = (p) => {
    if (method === 'VENDOR') return p.vendor === String(re).split(':')[1];
    return method === 'TITLE' ? re.test(titleOf(p)) : re.test(`${titleOf(p)} ${bodyOf(p)}`);
  };
  const yes = members.filter(hit);
  const no = members.filter((p) => !hit(p));
  const share = Math.round((100 * yes.length) / members.length);
  const verdict = share === 100 ? 'CLEAN' : share >= 90 ? 'minor' : share >= 70 ? 'REVIEW' : 'MATERIALLY WRONG';
  console.log(`\n${'='.repeat(76)}`);
  console.log(`${handle}  —  ${yes.length}/${members.length} evidence the feature (${share}%)  [${method.toLowerCase()}, ${kind}]  ${verdict}`);
  if (no.length) {
    console.log(`  ${no.length} member(s) do NOT:`);
    no.forEach((p) => {
      const alt = method === 'VENDOR' ? `  vendor="${p.vendor}"`
        : method === 'TITLE' && re.test(bodyOf(p)) ? '  (body mentions it; title does not)' : '';
      console.log(`    ${p.handle.padEnd(48)} $${Number(p.priceMin).toLocaleString().padStart(8)}  ${p.title.slice(0, 46)}${alt}`);
    });
  }
}
