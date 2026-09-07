/**
 * Prints what is ACTUALLY in a collection, from data/products.json.
 *
 * Read-only. This is the input to a collection description — nothing goes into
 * copy that does not appear here, per CLAUDE.md hard rule 6.
 *
 * Every fact carries a COVERAGE percentage, because CLAUDE.md 6a needs it
 * before the fact can be written as a property of the collection:
 *
 *   EXISTENCE claim  ("from inflatable to stainless steel")  needs >= 1 instance
 *   UNIVERSAL claim  ("none run above 140F")                 needs coverage across the set
 *
 * Facts are graded:
 *   SOLID    a structured field — price, vendor, status, count. Safe as written.
 *   DERIVED  counted from title or description text. Measures what the listing
 *            SAYS, not what the unit is. Coverage matters most here.
 *
 *   node scripts/audit/collection-spec.js cold-plunge
 *   node scripts/audit/collection-spec.js cold-plunge outdoor-saunas --json
 */
import path from 'node:path';
import { readJSON, DATA } from '../lib/util.js';

const argv = process.argv.slice(2);
const asJson = argv.includes('--json');
const handles = argv.filter((a) => !a.startsWith('--'));
if (!handles.length) {
  console.error('Usage: node scripts/audit/collection-spec.js <handle> [handle...] [--json]');
  process.exit(1);
}

const products = readJSON(path.join(DATA, 'products.json'));
const collections = readJSON(path.join(DATA, 'collections.json'));
const byHandle = new Map(collections.map((c) => [c.handle, c]));

const text = (p) => `${p.title} ${p.descriptionHtml.replace(/<[^>]+>/g, ' ')}`
  .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').toLowerCase();
const money = (n) => '$' + Number(n).toLocaleString('en-US');
const pct = (n, d) => (d ? Math.round((100 * n) / d) : 0);

/** Count how many members match, and grade the claim shape. */
function derive(members, label, re) {
  const hits = members.filter((p) => re.test(text(p)));
  const n = hits.length, d = members.length, p = pct(n, d);
  return {
    label, n, d, pct: p,
    // a claim about the whole set needs coverage; a claim that something exists needs one
    universal: p >= 90 ? 'safe as a universal claim'
      : p >= 50 ? 'majority only — say "most", never "all"'
      : p > 0 ? `EXISTENCE ONLY — ${n} of ${d}. Do not write as a property of the collection`
      : 'absent',
  };
}

function spec(handle) {
  const c = byHandle.get(handle);
  if (!c) return { handle, error: 'no such collection in data/collections.json' };

  const all = products.filter((p) => p.collections.includes(handle));
  const A = all.filter((p) => p.status === 'ACTIVE' && p.priceMin > 0);
  if (!A.length) return { handle, error: `no ACTIVE priced products (${all.length} total members)` };

  const prices = A.map((p) => p.priceMin).sort((a, b) => a - b);
  const vendors = {}; A.forEach((p) => { vendors[p.vendor] = (vendors[p.vendor] || 0) + 1; });
  const types = {}; A.forEach((p) => { types[p.productType || '(none)'] = (types[p.productType || '(none)'] || 0) + 1; });

  /* capacity: read from titles only. Body text repeats figures and double-counts. */
  const cap = new Set(); let capN = 0;
  A.forEach((p) => {
    const ms = [...p.title.matchAll(/(\d)\s*[-–]?\s*(\d)?\s*person/gi)];
    if (ms.length) capN += 1;
    ms.forEach((m) => { cap.add(+m[1]); if (m[2]) cap.add(+m[2]); });
  });
  const caps = [...cap].sort((a, b) => a - b);

  /* temperatures: collect every °F figure, report the envelope and how many publish one */
  const temps = [];
  A.forEach((p) => (text(p).match(/\b\d{2,3}\s*°?\s*f\b/gi) || []).forEach((x) => {
    const n = parseInt(x, 10); if (n >= 32 && n <= 230) temps.push(n);
  }));
  const withTemp = A.filter((p) => /\b\d{2,3}\s*°?\s*f\b/i.test(text(p))).length;

  return {
    handle,
    title: c.title,
    products: { total: all.length, active: A.length, note: all.length !== A.length ? `${all.length - A.length} draft/archived or unpriced, excluded` : null },
    published: c.publishedOnline,
    gsc: null,
    price: { min: prices[0], max: prices[prices.length - 1], median: prices[Math.floor(prices.length / 2)], grade: 'SOLID', note: 'priceMin across ACTIVE members; no variant spread on this catalogue' },
    vendors: { grade: 'SOLID', breakdown: Object.entries(vendors).sort((a, b) => b[1] - a[1]) },
    productTypes: { grade: 'SOLID', breakdown: Object.entries(types).sort((a, b) => b[1] - a[1]), warn: Object.keys(types).length > 4 ? `${Object.keys(types).length} distinct values — see BACKLOG B6` : null },
    capacity: { grade: 'DERIVED', range: caps.length ? `${caps[0]} to ${caps[caps.length - 1]} person` : null, stated: capN, of: A.length, pct: pct(capN, A.length) },
    temperature: { grade: 'DERIVED', min: temps.length ? Math.min(...temps) : null, max: temps.length ? Math.max(...temps) : null, stated: withTemp, of: A.length, pct: pct(withTemp, A.length) },
    materials: [
      derive(A, 'Canadian Hemlock', /canadian hemlock/),
      derive(A, 'cedar', /\bcedar\b/),
      derive(A, 'spruce', /spruce/),
      derive(A, 'thermo-wood', /thermo/),
      derive(A, 'stainless steel', /stainless steel/),
      derive(A, 'inflatable', /inflatable/),
    ].filter((f) => f.n > 0),
    electrical: [
      derive(A, '120V / 110V named', /\b1[12]0\s*v\b/),
      derive(A, '240V / 220V named', /\b2[24]0\s*v\b/),
      derive(A, 'dedicated circuit', /dedicated (\d+\s*amp\s*)?circuit/),
      derive(A, '20 amp', /\b20\s*amp/),
    ].filter((f) => f.n > 0),
    features: [
      derive(A, 'tool-free / clasp assembly', /(tool[- ]free|clasp[- ]together|snaps? together)/),
      derive(A, 'low EMF (any tier)', /low emf/),
      derive(A, 'ultra-low EMF', /ultra[- ]?low emf/),
      derive(A, 'near-zero EMF', /near[- ]?zero emf/),
      derive(A, 'red light therapy', /red light/),
      derive(A, 'chromotherapy', /chromotherap/),
      derive(A, 'Bluetooth', /bluetooth/),
      derive(A, 'chiller', /chiller/),
      derive(A, 'full spectrum', /full[- ]spectrum/),
    ].filter((f) => f.n > 0),
  };
}

const out = handles.map(spec);
if (asJson) { console.log(JSON.stringify(out, null, 2)); process.exit(0); }

for (const s of out) {
  console.log('\n' + '='.repeat(78));
  if (s.error) { console.log(`  ${s.handle}: ${s.error}`); continue; }
  console.log(`  ${s.handle}  —  "${s.title}"`);
  console.log('='.repeat(78));
  console.log(`  ${s.products.active} ACTIVE priced products${s.products.note ? '  (' + s.products.note + ')' : ''}`);
  console.log(`  published to Online Store: ${s.published}`);
  console.log('');
  console.log('  SOLID — structured fields, safe as written');
  console.log(`    price band     ${money(s.price.min)} to ${money(s.price.max)}   median ${money(s.price.median)}`);
  console.log(`    vendors        ${s.vendors.breakdown.map(([k, n]) => `${k} ${n}`).join(', ')}`);
  console.log(`    productTypes   ${s.productTypes.breakdown.map(([k, n]) => `${k} ${n}`).join(', ')}`);
  if (s.productTypes.warn) console.log(`                   ! ${s.productTypes.warn}`);
  console.log('');
  console.log('  DERIVED — counted from listing text. Coverage decides what you may claim.');
  const line = (f) => `    ${String(f.pct + '%').padStart(4)}  ${String(f.n + '/' + f.d).padStart(7)}  ${f.label.padEnd(26)} ${f.universal}`;
  if (s.capacity.range) console.log(`    ${String(s.capacity.pct + '%').padStart(4)}  ${String(s.capacity.stated + '/' + s.capacity.of).padStart(7)}  ${'capacity'.padEnd(26)} range ${s.capacity.range}`);
  if (s.temperature.max) console.log(`    ${String(s.temperature.pct + '%').padStart(4)}  ${String(s.temperature.stated + '/' + s.temperature.of).padStart(7)}  ${'temperature'.padEnd(26)} ${s.temperature.min}°F to ${s.temperature.max}°F published`);
  for (const g of ['materials', 'electrical', 'features']) {
    if (!s[g].length) continue;
    console.log(`    -- ${g} --`);
    s[g].forEach((f) => console.log(line(f)));
  }
  console.log('');
  console.log('  BEFORE WRITING: any fact under 90% coverage is an existence claim, not a');
  console.log('  property of the collection. "Two of eighteen is not a collection fact."');
}
