/**
 * What do the five competitor brands publish about themselves?
 *
 * Same principle as gd-spec-fetch: read the manufacturer's own page, extract
 * only what is literally stated, and record ABSENCE as a finding rather than
 * as a gap to fill with a guess. "Nobody publishes a wavelength" is the single
 * most useful thing we know about this category; it is only worth saying if we
 * checked the people who might.
 *
 * Read-only. Politeness: one request at a time, 3s apart.
 */
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36';

export const TARGETS = {
  Sunlighten: [
    'https://www.sunlighten.com/infrared-saunas/mpulse/',
    'https://www.sunlighten.com/infrared-sauna-benefits/low-emf-infrared-sauna/',
  ],
  Clearlight: [
    'https://infraredsauna.com/sanctuary-full-spectrum-saunas/',
    'https://infraredsauna.com/emf-and-your-health/',
  ],
  'Sun Home': [
    'https://sunhomesaunas.com/products/luminar-outdoor-full-spectrum-infrared-sauna',
    'https://sunhomesaunas.com/blogs/news/emf-levels-in-saunas-what-you-need-to-know',
  ],
  'Almost Heaven': [
    'https://almostheaven.com/pages/warranty',
    'https://almostheaven.com/collections/barrel-saunas',
  ],
  HigherDose: [
    'https://higherdose.com/products/infrared-sauna-blanket',
    'https://higherdose.com/pages/warranty',
  ],
};

const PATTERNS = {
  wavelength_nm:  /(\d{3,4})\s*nm\b/gi,
  emf_mg:         /(?:under|below|less than|<)?\s*([\d.]+)\s*(?:-|–|to)?\s*([\d.]*)\s*(?:mg|milligauss)\b/gi,
  emf_distance:   /(\d+)\s*(?:to|-|–)?\s*(\d*)\s*(?:inch|in\.|")\s*(?:from|away)/gi,
  price_usd:      /\$\s?([\d,]{3,9})(?:\.\d\d)?/g,
  warranty_years: /(\d+|one|two|three|five|seven|ten|lifetime)[- ]year\s*(?:limited\s*)?warranty/gi,
  lifetime:       /lifetime\s*(?:limited\s*)?warranty/gi,
  spectrum_bands: /\b(near|mid|far)[- ]infrared\b/gi,
};

export async function probe(url) {
  let res;
  try { res = await fetch(url, { headers: { 'user-agent': UA, accept: 'text/html' }, redirect: 'follow' }); }
  catch (e) { return { url, error: e.message }; }
  if (res.status !== 200) return { url, status: res.status, error: `HTTP ${res.status}` };
  /* Instance 39. /products/luminar-... answers 200 from /collections/best-infrared-saunas;
     recording the requested URL put a category FAQ into a report as a product spec. */
  const redirected = res.url && res.url.replace(/\/$/, '') !== url.replace(/\/$/, '');
  const raw = await res.text();
  const text = raw
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&#\d+;/g, ' ')
    .replace(/\s+/g, ' ');
  const out = { requested: url, final: res.url || url, redirected, status: res.status, bytes: raw.length, words: text.split(' ').length, found: {}, context: {} };
  if (redirected) out.WARNING = `answered from ${res.url} — any finding below describes THAT page, not ${url}`;
  for (const [name, re] of Object.entries(PATTERNS)) {
    const ms = [...text.matchAll(re)];
    out.found[name] = [...new Set(ms.map((m) => m[0].trim()))].slice(0, 8);
    if (ms.length && ['wavelength_nm', 'emf_mg', 'emf_distance', 'warranty_years'].includes(name)) {
      out.context[name] = ms.slice(0, 3).map((m) => text.slice(Math.max(0, m.index - 90), m.index + m[0].length + 70).trim());
    }
  }
  return out;
}

const results = {};
for (const [brand, urls] of Object.entries(TARGETS)) {
  results[brand] = [];
  for (const u of urls) {
    results[brand].push(await probe(u));
    await new Promise((r) => setTimeout(r, 3000));
  }
}
console.log(JSON.stringify(results, null, 1));
