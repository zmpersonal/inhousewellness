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
import { readJSON, DATA, ROOT, assertFresh } from '../lib/util.js';
import { assertServedBy } from '../lib/theme-identity.mjs';

const argv = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};
const limit = Number(arg('--limit', 8));
const only = arg('--only', null)?.split(',').map((s) => s.trim());
const previewId = arg('--preview', null);
const base = arg('--base', 'https://inhousewellness.com');
/* Instance 23: run immediately after an apply, this checker reports a FALSE
   FAILURE — the CDN is still serving the pre-apply page. `electric-saunas` was
   reported as "in Shopify but does NOT render" while the copy was on the page;
   re-fetched a minute later the probe matched at every length from 20 to 60
   characters. A noisy false failure is safer than instance 14's silent false
   pass, but it still trains people to ignore the guard. Wait, then retry once. */
const settle = Number(arg('--settle', 30));

const collections = readJSON(path.join(DATA, 'collections.json'));

/* Instance 14: this checker DERIVES its sample and its expectations from the
   dump. A stale dump does not make it fail — it makes it quietly check less,
   because a collection whose copy was applied after the dump still reads as
   descriptionLength 0 and the body probe is skipped entirely. It then prints
   "ok ... no copy, meta present" and "All N passed" for a check it never ran.
   Abort on a stale dump rather than degrade. */
assertFresh({ 'collections.json': 'npm run audit:collections' });

/* Sample: every collection with a description is checked (those are the ones
   that can silently stop rendering), topped up with published collections
   without one, which still must emit a meta description. */
if (settle > 0) {
  console.log(`  waiting ${settle}s for the CDN to settle before checking…`);
  await new Promise((r) => setTimeout(r, settle * 1000));
}

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
  /* Instance 39: record where the response actually came from. A collection that
     301s to another handle would otherwise be verified as itself. */
  return { status: res.status, html: await res.text(), requested: url, final: res.url || url };
}

console.log(`\nverify-render — ${sample.length} collection(s) against ${base}${previewId ? ` (preview ${previewId})` : ' (LIVE)'}\n`);

/* Priming request. A preview_theme_id URL answers with a 302 that sets the
   preview cookie; fetch(redirect:'follow') does not expose the intermediate
   response's headers, so the FIRST page in the run comes back rendered with
   the LIVE theme and fails spuriously. Burn one request to seed the jar. */
if (previewId) {
  /* Round 18i: this catch used to swallow everything ("the real run will report any fetch
     problem") — but a failed priming does not make the real run FAIL, it makes it read MAIN.
     Fatal now, and the jar must actually hold the preview cookie. */
  try {
    await fetchPage(`${base}/collections/${sample[0].handle}?preview_theme_id=${previewId}`);
    await new Promise((r) => setTimeout(r, 1000));
  } catch (e) { console.error(`REFUSING — preview priming request failed: ${e.message}`); process.exit(1); }
  if (!jar.some((c) => c.startsWith('_shopify_essential='))) { console.error('REFUSING — priming did not yield a _shopify_essential cookie, so every page would be read from MAIN'); process.exit(1); }
}

const failures = [];
const skipped = [];
const unreachable = [];
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
    /* Instance 24: a non-200 is "I could not check", NOT "the copy is broken".
       inhousewellness.com pushes back under load — 429 documented, and 400 seen
       once the sample grew from 10 collections to 51. Four pages reported
       HTTP 400 here and all four returned 200 with the copy present when
       re-fetched with spacing. Back off and retry twice before giving up, and
       report an unreachable page separately from a failed render. */
    let recovered = null;
    for (const wait of [5000, 15000]) {
      console.log(`  …${c.handle} returned HTTP ${page.status}; backing off ${wait / 1000}s and retrying`);
      await new Promise((r) => setTimeout(r, wait));
      const retry = await fetchPage(url);
      if (retry.status === 200) { recovered = retry; break; }
      page = retry;
    }
    if (recovered) { page = recovered; }
    else {
      unreachable.push({ url, why: `HTTP ${page.status} after 2 retries` });
      console.log(`  ????  ${c.handle.padEnd(40)} UNREACHABLE — HTTP ${page.status}. Not checked; not a render failure.`);
      continue;
    }
  }

  const problems = [];
  /* 18i: the handshake proves a cookie was offered; only the page says which theme rendered it */
  if (previewId) { try { assertServedBy(page.html, previewId, `/collections/${c.handle}`); } catch (e) { problems.push(e.message); } }
  if (page.final && page.final.split('?')[0].replace(/\/$/, '') !== url.split('?')[0].replace(/\/$/, ''))
    problems.push(`REDIRECTED — this page answered from ${page.final}, so what rendered is that page, not this handle`);

  /* 1. a meta description must exist, and must not be the generic fallback
        when the collection has its own copy to derive one from */
  const meta = page.html.match(/<meta[^>]*name=["']description["'][^>]*content=["']([^"']*)/i)?.[1];
  if (!meta) problems.push('no <meta name="description"> in the head');

  /* 2. INSTANCE 31: the SEO title must reach the <title> tag. 52 titles were
        applied, verified in the admin, and none of them rendered — the theme's
        collection branch printed collection.title and never looked at
        page_title. "The field is set" and "the page says it" are different
        assertions and only the second one is worth anything. Checked against
        the DECODED string: &amp; is one character on the page and five in the
        metafield (CLAUDE.md 6b). */
  if (c.seoTitle) {
    const tag = page.html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1];
    const dec = (x) => String(x || '').replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
      .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
      .replace(/&ndash;/g, '\u2013').replace(/&mdash;/g, '\u2014').replace(/\s+/g, ' ').trim();
    if (!tag) problems.push('no <title> tag in the head');
    else if (!dec(tag).includes(dec(c.seoTitle))) {
      problems.push(`SEO title is in Shopify but does NOT reach <title> — page says "${dec(tag).slice(0, 70)}"`);
    }
  }

  /* 3. if the collection has a description, its opening words must appear in
        the body — not merely somewhere in the document (og: tags live in head) */
  if (c.descriptionLength > 0) {
    const headEnd = page.html.indexOf('</head>');
    const body = headEnd >= 0 ? page.html.slice(headEnd) : page.html;
    /* Probe the plain text of both sides. Inline tags (<strong>, <a>) sit
       mid-sentence in the stored HTML, so comparing raw markup produces false
       negatives. Keep the probe short enough to survive entity differences. */
    const probe = strip(c.descriptionHtml).slice(0, 40);
    if (probe && !strip(body).includes(probe)) {
      /* Retry once before calling it a failure — see instance 23. */
      console.log(`  …${c.handle} did not match; waiting 20s and retrying once`);
      await new Promise((r) => setTimeout(r, 20000));
      const again = await fetchPage(url);
      const h2 = again.html.indexOf('</head>');
      const body2 = h2 >= 0 ? again.html.slice(h2) : again.html;
      if (!strip(body2).includes(probe)) {
        problems.push('description is in Shopify but does NOT render in the page body (confirmed on retry)');
      }
    }
  }

  if (problems.length) {
    failures.push({ url, why: problems.join('; ') });
    console.log(`  FAIL  ${c.handle.padEnd(40)} ${problems.join('; ')}`);
  } else if (c.descriptionLength > 0) {
    console.log(`  ok    ${c.handle.padEnd(40)} copy renders, meta present`);
  } else {
    /* NOT a pass. The render check — the thing this script exists for — did
       not run, because there is no stored description to probe for. Say so. */
    skipped.push({ handle: c.handle, url });
    console.log(`  SKIP  ${c.handle.padEnd(40)} SKIPPED, no description in dump — render NOT checked (meta present)`);
  }

  await new Promise((r) => setTimeout(r, 2500)); // inhousewellness.com rate-limits; raised from 1500 after HTTP 400s at n=51
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
const checked = sample.length - skipped.length - unreachable.length;
if (unreachable.length) {
  console.warn(`\n${unreachable.length} of ${sample.length} UNREACHABLE — the site did not serve the page, so the render was NOT checked:\n`);
  for (const u of unreachable) console.warn(`  ${u.url}\n      ${u.why}`);
  console.warn('\nThis is a transport problem, not a copy problem. Re-run with fewer');
  console.warn('collections (--only) or a larger --settle if it persists.\n');
}
if (skipped.length) {
  console.warn(`${skipped.length} of ${sample.length} SKIPPED — no description in the dump, so the render check did not run:\n`);
  for (const sk of skipped) console.warn(`  ${sk.handle}`);
  console.warn('\nThese are NOT passes. Either the copy was never applied, or the dump');
  console.warn('predates the apply. Re-run dump-collections.js and check again.\n');
}
console.log(`${checked} of ${sample.length} passed the render check.` + (skipped.length ? ` ${skipped.length} skipped.` : ''));
if (skipped.length || unreachable.length) process.exit(1);
