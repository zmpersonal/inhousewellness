/**
 * Pulls the Golden Designs spec table for a model, from the page's own product
 * JSON rather than the rendered HTML.
 *
 * Why: the rendered page carries two contaminants — a template disclaimer about
 * red light therapy on every page, and a related-products carousel whose entries
 * describe OTHER models. Naive regex over the stripped HTML returns the
 * carousel's "Interior Lighting" first. The product's own spec sits inside a
 * <script> JSON blob, which a tag-stripper deletes. Parse the blob.
 *
 * Validated against 14 models whose values were read independently first.
 */
import fs from 'node:fs';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36';

export async function fetchSpec(slug) {
  const url = `https://goldendesignsaunas.com/products/${slug}`;
  const res = await fetch(url, { headers: { 'user-agent': UA } });
  if (!res.status || res.status !== 200) return { slug, url, error: `HTTP ${res.status}` };
  /* Instance 39: a followed redirect answers from a different URL than the one
     asked for. Record both and refuse to attribute the content to the request. */
  if (res.url && res.url.replace(/\/$/, '') !== url.replace(/\/$/, ''))
    return { slug, requested: url, final: res.url, error: `REDIRECTED to ${res.url} — content belongs to that page, not this one` };
  const raw = await res.text();
  /* Unescape the JSON blob's encoding so the spec reads as plain text. */
  const un = raw.replace(/\\\//g, '/').replace(/\\u0026amp;/g, '&').replace(/\\u0026/g, '&').replace(/\\"/g, '"').replace(/\\n/g, ' ');
  const grab = (label) => {
    /* Anchor on the FIRST occurrence — the product's own JSON precedes the
       carousel markup. Stop at the next "Label:" so rows cannot bleed. */
    const re = new RegExp(label + '\\s*:\\s*([^]{0,300}?)(?=\\s{1,3}[A-Z][A-Za-z ]{2,28}\\s*:|$)');
    const m = un.match(re);
    return m ? m[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() : null;
  };
  const dist = (t) => { if (!t) return null; const m = t.match(/(\d+\s*(?:to|-|–)\s*\d+)\s*inches/i); return m ? m[1].replace(/\s+/g,'') + ' in' : null; };
  const emfLevels = grab('EMF Levels');
  const heating = grab('Heating Elements');
  return {
    slug, url,
    interiorLighting: grab('Interior Lighting'),
    emfLevels, heatingElements: heating,
    distEmfRow: dist(emfLevels), distHeatingRow: dist(heating),
    woodType: grab('Wood Type'),
  };
}

/* ---- validation harness: 14 models read independently before this existed ---- */
const KNOWN = {
  'golden-designs-sauna-dyn-6203-01-elite': { rl:false, d:'6to8 in' },
  'golden-designs-sauna-dyn-6996-01-elite': { rl:false, d:'6to8 in' },
  'golden-designs-sauna-dyn-6336-02-elite': { rl:false, d:'6to8 in' },
  'golden-designs-sauna-dyn-6210-01-elite': { rl:false, d:'6to8 in' },
  'golden-designs-sauna-dyn-6106-01-elite': { rl:false, d:'6to8 in' },
  'golden-designs-sauna-dyn-6103-01':       { rl:true,  d:'6to8 in' },
  'golden-designs-sauna-dyn-6225-02':       { rl:false, d:'6to8 in' },
  'golden-designs-sauna-dyn-6440-01':       { rl:false, d:'6to8 in' },
  'golden-designs-sauna-mx-k206-01':        { rl:false, d:'6to8 in' },
  'golden-designs-sauna-mx-k356-01-ced':    { rl:false, d:'6to8 in' },
  'golden-designs-sauna-mx-k406-01-ced':    { rl:false, d:'6to8 in' },
  'golden-designs-sauna-mx-k306-01-zf-ced': { rl:false, d:'2to3 in' },
  'golden-designs-sauna-mx-k356-01-zf-ced': { rl:false, d:'2to3 in' },
  'golden-designs-sauna-mx-m306-01-fs-ced': { rl:true,  d:'2to3 in' },
};
if (process.argv.includes('--validate')) {
  let pass = 0, fail = 0;
  for (const [slug, want] of Object.entries(KNOWN)) {
    const r = await fetchSpec(slug);
    const gotRl = /red light/i.test(r.interiorLighting || '');
    const ok = gotRl === want.rl && r.distEmfRow === want.d;
    ok ? pass++ : fail++;
    console.log(`  ${ok ? 'PASS' : '**FAIL**'} ${slug.replace('golden-designs-sauna-','').padEnd(22)} redLight=${String(gotRl).padEnd(5)}(want ${want.rl})  dist=${String(r.distEmfRow).padEnd(9)}(want ${want.d})`);
    if (!ok) console.log(`         lighting: ${String(r.interiorLighting).slice(0,90)}`);
    await new Promise(r2 => setTimeout(r2, 900));
  }
  console.log(`\n  ${pass} passed, ${fail} failed of ${Object.keys(KNOWN).length}`);
  if (fail) { console.error('\n  Extractor does not reproduce known-good values. NOT trustworthy. Aborting.'); process.exit(1); }
  console.log('  Extractor reproduces all 14 independently-read values. Safe for the remaining models.');
}
