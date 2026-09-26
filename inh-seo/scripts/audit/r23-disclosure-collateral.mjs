/* Round 23 — prove the disclosure removal moved NOTHING ELSE on the product page.
 *   node scripts/audit/r23-disclosure-collateral.mjs <branchThemeId> <mainThemeId>
 *
 * Verifies the OUTCOME rather than the write. For one product per template it renders the page on
 * BOTH themes, cuts the disclosure block out of MAIN's copy, and asserts the remaining visible text
 * is identical. A removal that also dropped a neighbouring section would pass an md5 read-back and
 * fail here, which is the point.
 *
 * Both themes are read through the preview handshake and assertServedBy, so a dropped cookie cannot
 * silently compare MAIN against MAIN.
 */
import { assertServedBy } from '../lib/theme-identity.mjs';

const [branch, main] = process.argv.slice(2).map((x) => (x || '').replace(/\D/g, ''));
if (!branch || !main) throw new Error('usage: <branchThemeId> <mainThemeId>');
const UA = 'Mozilla/5.0 (compatible; inh-seo-audit)';
const CASES = [['(default)', 'cal-flame-costa-bbq-island'], ['(default)', 'scandia-electric-heater-6kw'],
  ['Bundle', 'dynamic-cold-therapy-pvc-barrel-cold-plunge'], ['Bundle', 'ct-georgian-cabin-sauna'],
  ['wider-images', 'saunalife-g3']];

async function render(handle, themeId) {
  const first = await fetch(`https://inhousewellness.com/products/${handle}?preview_theme_id=${themeId}`, { redirect: 'manual', headers: { 'User-Agent': UA } });
  const jar = (first.headers.getSetCookie ? first.headers.getSetCookie() : [first.headers.get('set-cookie')]).filter(Boolean).map((c) => c.split(';')[0]).join('; ');
  if (first.status !== 302 || !jar) throw new Error(`expected 302 + cookie, got ${first.status}`);
  const res = await fetch(first.headers.get('location'), { headers: { 'User-Agent': UA, cookie: jar } });
  if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
  const html = await res.text();
  assertServedBy(html, themeId, `/products/${handle} on ${themeId}`);
  return html;
}
/* cut the disclosure block by its own container. It is a <section>, not a <div> — read from
   snippets/product-disclosure.liquid line 104, not assumed. The fixtures below use that real shape,
   so they cannot share a blind spot with this pattern. */
const cutBlock = (html) => html.replace(/<section class="inh-disclosure"[\s\S]*?<\/section>/g, '');
const visible = (html) => html.replace(/<script[\s\S]*?<\/script>/g, ' ').replace(/<style[\s\S]*?<\/style>/g, ' ')
  .replace(/<[^>]+>/g, '\n').replace(/&amp;/g, '&').replace(/&#39;|&rsquo;/g, "'").replace(/&nbsp;/g, ' ')
  .split('\n').map((s) => s.trim()).filter(Boolean);

/* the fixture: a constructed pair the checker must judge correctly, so it is not trusted untested */
const SEC = '<section class="inh-disclosure" aria-labelledby="inh-disclosure-heading"><h2>Before you buy</h2><dl><div><dt>Electrical</dt></div></dl></section>';
const FX_SAME = [`<p>a</p>${SEC}<p>b</p>`, '<p>a</p><p>b</p>'];
const FX_DIFF = [`<p>a</p>${SEC}<p>b</p>`, '<p>a</p>'];
const same = (m, b) => JSON.stringify(visible(cutBlock(m))) === JSON.stringify(visible(b));
if (!same(...FX_SAME)) { console.log('FIXTURE FAIL: an identical page pair was reported as different'); process.exit(2); }
if (same(...FX_DIFF)) { console.log('FIXTURE FAIL: a page missing a neighbour was reported as identical'); process.exit(2); }
console.log('fixtures: the comparison accepts an identical pair and refuses a dropped neighbour\n');

let fail = 0;
for (const [tpl, handle] of CASES) {
  try {
    const [b, m] = [await render(handle, branch), await render(handle, main)];
    const bl = visible(b), ml = visible(cutBlock(m));
    const ok = JSON.stringify(bl) === JSON.stringify(ml);
    const gone = !/class="inh-disclosure"/.test(b) && /class="inh-disclosure"/.test(m);
    console.log(`  ${ok && gone ? 'PASS' : 'FAIL'}  ${tpl.padEnd(12)} ${handle}`);
    console.log(`        block present on MAIN and absent on the branch: ${gone}`);
    if (!ok) {
      const onlyB = bl.filter((x) => !ml.includes(x)).slice(0, 6), onlyM = ml.filter((x) => !bl.includes(x)).slice(0, 6);
      console.log(`        lines ${bl.length} branch vs ${ml.length} MAIN-minus-block`);
      onlyM.forEach((l) => console.log(`        - ${l.slice(0, 110)}`));
      onlyB.forEach((l) => console.log(`        + ${l.slice(0, 110)}`));
    }
    if (!(ok && gone)) fail++;
  } catch (e) { console.log(`  ${/^WRONG THEME/.test(e.message) ? 'FAIL' : 'UNREACHABLE'}  ${handle}: ${e.message}`); fail++; }
}
console.log(`\n  ${CASES.length - fail}/${CASES.length} products: the disclosure block is gone and nothing else moved`);
process.exit(fail ? 1 : 0);
