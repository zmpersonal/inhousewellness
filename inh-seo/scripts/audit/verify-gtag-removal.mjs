/* Verify the hardcoded Google tag (gtag.js) block is gone from the LIVE theme, and that GTM still loads it.
 *
 *   node scripts/audit/verify-gtag-removal.mjs              run the checks against the live storefront
 *   node scripts/audit/verify-gtag-removal.mjs --self-test  fixtures only, no network
 *
 * READ-ONLY. Node built-ins only, asserted by the self-test. Exits non-zero on any failure, and a page it
 * could not read is a FAILURE, never a pass.
 *
 * The SERVER-HTML half is checked here. The RENDERED half needs a browser, so this prints the exact snippet
 * to run there — because "no hardcoded tag" and "GTM still loads the tag" are two different claims, and only
 * the rendered page can show the second. Run this BEFORE publishing too: it must FAIL on the server-HTML
 * checks while the block is still live. A check not seen to fail has not been tested.
 */
import fs from 'node:fs';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const PAGES = [
  'https://inhousewellness.com/',
  'https://inhousewellness.com/products/finnmark-soulcold-plunge',
];
const HARDCODED = 'gtag/js?id=AW-11489901160';   // the script src the theme block loaded
const GTM = 'GTM-T6L8NK6L';

/* ── pure checks, proved by fixtures below ─────────────────────────────────────────────────────────────── */
export function serverChecks(html) {
  return {
    hardcoded_gtag_loads: (html.match(/gtag\/js\?id=AW-11489901160/g) || []).length,   // want 0
    gtm_container_mentions: (html.match(/GTM-T6L8NK6L/g) || []).length,                // want >= 1
    gtag_marker: (html.match(/<!-- Google tag \(gtag\.js\) -->/g) || []).length,       // want 0
  };
}
export function verdict(c) {
  const fails = [];
  if (c.hardcoded_gtag_loads !== 0) fails.push(`server HTML still loads ${HARDCODED} ${c.hardcoded_gtag_loads}x — the block is still in the theme`);
  if (c.gtm_container_mentions < 1) fails.push(`server HTML no longer mentions ${GTM} — the GTM snippet was removed too, which was NOT the change`);
  if (c.gtag_marker !== 0) fails.push('the "<!-- Google tag (gtag.js) -->" marker is still present');
  return fails;
}

function selfTest() {
  let bad = 0;
  const eq = (name, got, want) => { const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { console.log(`FIXTURE FAIL: ${name} — want ${JSON.stringify(want)} got ${JSON.stringify(got)}`); bad++; } };
  const AFTER = '<head><script>(…\'GTM-T6L8NK6L\');</script></head><body><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-T6L8NK6L"></iframe></body>';
  const SCRIPT_ONLY = AFTER + '<script async src="https://www.googletagmanager.com/gtag/js?id=AW-11489901160"></script>';
  const BEFORE = AFTER + '<!-- Google tag (gtag.js) --><script async src="https://www.googletagmanager.com/gtag/js?id=AW-11489901160"></script>';
  eq('after-state passes', verdict(serverChecks(AFTER)), []);
  eq('the script alone fails (one reason)', verdict(serverChecks(SCRIPT_ONLY)).length, 1);
  eq('the real before-state fails on BOTH the script and the marker', verdict(serverChecks(BEFORE)).length, 2);
  eq('a page with the tag gone but GTM ALSO gone fails', verdict(serverChecks('<html>nothing here</html>')).length, 1);
  eq('the marker alone fails', verdict(serverChecks(AFTER + '<!-- Google tag (gtag.js) -->')).length, 1);
  eq('counts are counts, not booleans', serverChecks(BEFORE + BEFORE).hardcoded_gtag_loads, 2);
  // the job installs nothing, so this file may import node: built-ins only — read from the source, not assumed
  const src = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8');
  const imports = [...src.matchAll(/^import .* from '([^']+)';$/gm)].map((m) => m[1]);
  eq('node built-ins only', imports.filter((i) => !i.startsWith('node:')), []);
  return bad;
}

const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing to run`); process.exit(2); }
console.log('self-test: every fixture holds\n');
if (process.argv.includes('--self-test')) process.exit(0);

let failed = 0;
for (const url of PAGES) {
  let html;
  try {
    const res = await fetch(url, { redirect: 'manual', headers: { 'User-Agent': 'inh-seo verify-gtag-removal (read-only)' } });
    if (res.status !== 200) { console.log(`FAIL  ${url} — HTTP ${res.status} (a page that will not render is not a pass)`); failed++; continue; }
    html = await res.text();
  } catch (e) { console.log(`FAIL  ${url} — unreachable: ${String(e.message).slice(0, 60)}`); failed++; continue; }
  const c = serverChecks(html);
  const fails = verdict(c);
  console.log(`${fails.length ? 'FAIL' : 'ok  '}  ${url}`);
  console.log(`        hardcoded ${HARDCODED}: ${c.hardcoded_gtag_loads} (want 0)   ${GTM} mentions: ${c.gtm_container_mentions} (want >=1)`);
  fails.forEach((f) => console.log(`        ${f}`));
  failed += fails.length ? 1 : 0;
}

console.log(`\n── RENDERED half — run this in the browser on ${PAGES[0]} (the server HTML cannot show it) ──`);
console.log(`
await new Promise(r=>setTimeout(r,6000));
const res = performance.getEntriesByType('resource').map(e=>e.name);
const aw  = res.filter(u=>u.includes('/gtag/js') && u.includes('AW-11489901160'));
const png = res.filter(u=>u.includes('viewthroughconversion/11489901160'));
JSON.stringify({
  aw_gtag_loads: aw.length,                         // want exactly 1
  injected_by_gtm: aw.every(u=>u.includes('cx=c')), // want true — GTM's own signature
  aw_urls: aw.map(u=>u.split('googletagmanager.com')[1]),
  remarketing_ping: png.length,                     // want >= 1
  gtm_container_loaded: res.some(u=>u.includes('/gtm.js')),
}, null, 1);`);

console.log(failed ? `\n${failed} page(s) FAILED the server-HTML checks` : '\nserver HTML: clean on every page checked');
process.exit(failed ? 1 : 0);
