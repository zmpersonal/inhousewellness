/* Verify the disclosure block on a theme preview, one product per state per template.
 *
 * Verifies the OUTCOME, not the write: fetches each preview URL and asserts the
 * rendered text matches the state that product is EXPECTED to be in. A write
 * that succeeds and renders the wrong line is the failure this exists to catch.
 *
 *   node scripts/audit/verify-disclosure.mjs <themeId>
 */
const themeId = (process.argv[2] || '').replace(/\D/g, '');
if (!themeId) throw new Error('theme id required');

/* Hand-picked, one per state per template. Each row is a KNOWN expected state,
 * derived independently of the Liquid — the fixture the checker must satisfy. */
const CASES = [
  ['(default)', 'A', 'cal-flame-costa-bbq-island'],
  ['(default)', 'B', 'laguna-q-gpv3100-outdoor-island'],
  ['(default)', 'C', 'scandia-electric-heater-6kw'],
  ['(default)', 'D', 'cal-flame-outdoor-entertainment-center'],
  ['Bundle',    'A', 'dynamic-cold-therapy-pvc-barrel-cold-plunge'],
  ['Bundle',    'B', 'starlight-wood-burning-hot-tub-ct372w'],
  /* Bundle + state C is UNTESTED and untestable: all three state-C products sit
   * on the default template. Recorded here rather than silently omitted. */
  ['Bundle',    'D', 'ct-georgian-cabin-sauna'],
  ['(default)', 'NONE', 'anti-vibration-mat'],   // accessory — must render nothing
];

const MARK = {
  A: /Needs a dedicated (\d+)V circuit/,
  B: /Combustion-fired\. No electrical supply needed/,
  C: /Rated .{1,12}\. This model does not publish its supply voltage/,
  D: /We do not publish an electrical requirement for this model/,
};

const FREIGHT = /Free to the lower 48, no minimum, and it stops at the curb/;
const BLOCK = /class="inh-disclosure"/;

const UA = 'Mozilla/5.0 (compatible; inh-seo-audit)';
let fail = 0;
for (const [tpl, want, handle] of CASES) {
  const url = `https://inhousewellness.com/products/${handle}?preview_theme_id=${themeId}`;
  /* Shopify does NOT serve the preview from ?preview_theme_id=. It 302s to the
   * clean URL and hands you a _shopify_essential cookie that carries the theme.
   * A plain fetch drops it and silently reads the LIVE theme — which would have
   * verified this branch against MAIN and reported a false pass. res.url is the
   * evidence: it differed from the request, and that is what exposed it. */
  let html = '';
  try {
    const first = await fetch(url, { redirect: 'manual', headers: { 'User-Agent': UA } });
    const jar = (first.headers.getSetCookie ? first.headers.getSetCookie() : [first.headers.get('set-cookie')])
      .filter(Boolean).map((c) => c.split(';')[0]).join('; ');
    if (first.status !== 302 || !jar) throw new Error(`expected a 302 + cookie, got ${first.status}`);
    const dest = first.headers.get('location');
    const res = await fetch(dest, { headers: { 'User-Agent': UA, cookie: jar } });
    html = await res.text();
  } catch (e) {
    console.log(`  UNREACHABLE  ${handle}: ${e.message}`);
    fail++;
    continue;
  }
  const txt = html.replace(/<[^>]+>/g, ' ').replace(/&#39;|&rsquo;/g, "'").replace(/&amp;/g, '&').replace(/\s+/g, ' ');
  const hasBlock = BLOCK.test(html);

  if (want === 'NONE') {
    const ok = !hasBlock;
    console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${tpl.padEnd(11)} must render nothing  ${handle}`);
    if (!ok) fail++;
    continue;
  }

  const states = Object.entries(MARK).filter(([, re]) => re.test(txt)).map(([k]) => k);
  const freight = FREIGHT.test(txt);
  const ok = hasBlock && states.length === 1 && states[0] === want && freight;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${tpl.padEnd(11)} state ${want}  ${handle}`);
  if (!ok) {
    console.log(`         block=${hasBlock}  matched=[${states.join(',')}]  freight=${freight}`);
    fail++;
  } else if (want === 'A') {
    console.log(`         "${txt.match(MARK.A)[0]}"`);
  } else if (want === 'C') {
    console.log(`         "${txt.match(MARK.C)[0].slice(0, 60)}"`);
  }
}

console.log(`\n  ${CASES.length - fail}/${CASES.length} passed`);
console.log('  UNTESTED: Bundle + state C — no ACTIVE state-C product uses the Bundle template.');
if (fail) process.exitCode = 1;
