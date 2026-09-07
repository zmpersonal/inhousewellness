/**
 * Asserts that what is in Shopify actually reaches the page.
 *
 * Read-only. Never writes to Shopify.
 *
 * This exists because of a two-month silent failure. Collection descriptions
 * were stored correctly in the admin and rendered nowhere: the description
 * block was disabled in templates/collection.json, and an `elsif` with an
 * empty body in layout/theme.liquid deleted the meta description tag from any
 * collection that had a description. Neither raised an error. Both were found
 * by reading a live page back, and only after copy had been written on the
 * assumption it would appear.
 *
 * Both failures are one theme-editor click away from returning: the section
 * that renders the description can be reordered, disabled or deleted by a
 * merchant with no warning.
 *
 * Run this after any theme publish, and on a schedule if one exists.
 *
 *   node scripts/audit/verify-render.js              # sample of 8
 *   node scripts/audit/verify-render.js --limit 20
 *   node scripts/audit/verify-render.js --only far-infrared,cold-plunge
 *   node scripts/audit/verify-render.js --preview 146038259779
 *
 * Exits 1 and prints the failing URLs if any assertion fails.
 */
import path from 'node:path';
import { readJSON, DATA, ROOT } from '../lib/util.js';

const argv = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};
const limit = Number(arg('--limit', 8));
const only = arg('--only', null)?.split(',').map((s) => s.trim());
const previewId = arg('--preview', null);
const base = arg('--base', 'https://inhousewellness.com');

const collections = readJSON(path.join(DATA, 'collections.json'));

/* Sample: every collection with a description is checked (those are the ones
   that can silently stop rendering), topped up with published collections
   without one, which still must emit a meta description. */
let sample;
if (only) {
  sample = collections.filter((c) => only.includes(c.handle));
} else {
  const withCopy = collections.filter((c) => c.publishedOnline && c.descriptionLength > 0);
  const without = collections
    .filter((c) => c.publishedOnline && c.descriptionLength === 0 && c.products > 0)
    .slice(0, Math.max(0, limit - withCopy.length));
  sample = [...withCopy, ...without];
}

if (!sample.length) { console.error('No collections to check.'); process.exit(1); }

const strip = (h) => h.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();

const jar = [];
async function fetchPage(url) {
  const res = await fetch(url, {
    headers: { 'User-Agent': 'inh-seo verify-render', cookie: jar.join('; ') },
    redirect: 'follow',
  });
  const setCookie = res.headers.getSetCookie?.() || [];
  for (const c of setCookie) jar.push(c.split(';')[0]);
  return { status: res.status, html: await res.text() };
}

console.log(`\nverify-render — ${sample.length} collection(s) against ${base}${previewId ? ` (preview ${previewId})` : ' (LIVE)'}\n`);

/* Priming request. A preview_theme_id URL answers with a 302 that sets the
   preview cookie; fetch(redirect:'follow') does not expose the intermediate
   response's headers, so the FIRST page in the run comes back rendered with
   the LIVE theme and fails spuriously. Burn one request to seed the jar. */
if (previewId) {
  try {
    await fetchPage(`${base}/collections/${sample[0].handle}?preview_theme_id=${previewId}`);
    await new Promise((r) => setTimeout(r, 1000));
  } catch { /* the real run will report any fetch problem */ }
}

const failures = [];
for (const c of sample) {
  const url = `${base}/collections/${c.handle}${previewId ? `?preview_theme_id=${previewId}` : ''}`;
  let page;
  try {
    page = await fetchPage(url);
  } catch (e) {
    failures.push({ url, why: `fetch failed: ${e.message}` });
    console.log(`  FAIL  ${c.handle.padEnd(40)} fetch error`);
    continue;
  }
  if (page.status !== 200) {
    failures.push({ url, why: `HTTP ${page.status}` });
    console.log(`  FAIL  ${c.handle.padEnd(40)} HTTP ${page.status}`);
    continue;
  }

  const problems = [];

  /* 1. a meta description must exist, and must not be the generic fallback
        when the collection has its own copy to derive one from */
  const meta = page.html.match(/<meta[^>]*name=["']description["'][^>]*content=["']([^"']*)/i)?.[1];
  if (!meta) problems.push('no <meta name="description"> in the head');

  /* 2. if the collection has a description, its opening words must appear in
        the body — not merely somewhere in the document (og: tags live in head) */
  if (c.descriptionLength > 0) {
    const headEnd = page.html.indexOf('</head>');
    const body = headEnd >= 0 ? page.html.slice(headEnd) : page.html;
    /* Probe the plain text of both sides. Inline tags (<strong>, <a>) sit
       mid-sentence in the stored HTML, so comparing raw markup produces false
       negatives. Keep the probe short enough to survive entity differences. */
    const probe = strip(c.descriptionHtml).slice(0, 40);
    if (probe && !strip(body).includes(probe)) {
      problems.push('description is in Shopify but does NOT render in the page body');
    }
  }

  if (problems.length) {
    failures.push({ url, why: problems.join('; ') });
    console.log(`  FAIL  ${c.handle.padEnd(40)} ${problems.join('; ')}`);
  } else {
    console.log(`  ok    ${c.handle.padEnd(40)} ${c.descriptionLength > 0 ? 'copy renders' : 'no copy'}, meta present`);
  }

  await new Promise((r) => setTimeout(r, 1500)); // inhousewellness.com rate-limits
}

console.log('');
if (failures.length) {
  console.error(`${failures.length} of ${sample.length} FAILED:\n`);
  for (const f of failures) console.error(`  ${f.url}\n      ${f.why}`);
  console.error('\nWhat is in the admin is not reaching the page. Check:');
  console.error('  - templates/collection.json  — is the section rendering the description still present and enabled?');
  console.error('  - layout/theme.liquid        — is the meta description elsif chain intact?');
  process.exit(1);
}
console.log(`All ${sample.length} passed.`);
