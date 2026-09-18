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
 *   node scripts/audit/collection-spec.js --selftest   # proves derive() refuses a method-less count
 */
import path from 'node:path';
import { readJSON, DATA, probeText } from '../lib/util.js';

const argv = process.argv.slice(2);
const asJson = argv.includes('--json');
const handles = argv.filter((a) => !a.startsWith('--'));
const selftest = argv.includes('--selftest');
if (!handles.length && !selftest) {
  console.error('Usage: node scripts/audit/collection-spec.js <handle> [handle...] [--json]');
  process.exit(1);
}

const products = readJSON(path.join(DATA, 'products.json'));
const collections = readJSON(path.join(DATA, 'collections.json'));
const byHandle = new Map(collections.map((c) => [c.handle, c]));

/* Three text sources, reported separately, because they disagree and the
   disagreement matters. A body mention can be a CROSS-SELL rather than a
   property of the unit — "check out our Golden Designs Full Spectrum Sauna for
   a space-saving alternative" counted a non-full-spectrum cabin as full
   spectrum. The title is the manufacturer's own designation and is the safer
   source for an attribute claim; body widens recall and adds false positives.
   Round 2 drafts silently mixed the two and the numbers drifted. */
/* Normalise Unicode dashes and quotes. Shopify titles carry U+2011 non-breaking
   hyphens ("Full‑Spectrum") that /full[- ]spectrum/ silently misses, which
   undercounted full-spectrum by one and put a wrong number into live copy.
   Character class is part of the pattern, and the pattern is part of the
   method (CLAUDE.md 6c). Keep this identical to membership-integrity.mjs. */
const clean = probeText; // shared: see util.js normalizeText, instance 16
const titleOf = (p) => clean(p.title);
const bodyOf = (p) => clean(p.descriptionHtml.replace(/<[^>]+>/g, ' '));
const text = (p) => `${titleOf(p)} ${bodyOf(p)}`;
const money = (n) => '$' + Number(n).toLocaleString('en-US');
const pct = (n, d) => (d ? Math.round((100 * n) / d) : 0);
/* ONE median definition, applied everywhere (client ruling 5, 8 Sept 2026).
   ACTIVE members only, from the enumerated connection. The harvia draft used a
   median over ALL members including drafts and was $14.50 out. */
const medianOf = (sorted) => {
  const a = sorted.slice().sort((x, y) => x - y);
  if (!a.length) return null;
  return a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2;
};

/**
 * METHOD RULING (client, 8 September 2026) — the method is part of the fact.
 *
 * There is no single correct counting method, so a count without its method is
 * not a value. `derive()` REFUSES to return one: no default, no fallback, no
 * warning-and-continue. It throws.
 *
 * This exists because instance 13 found six figures in approved, drafted copy
 * that reproduce under NEITHER method — not a wrong method, no method at all —
 * and nine of ten drafts carried at least one. Prose reads as authoritative
 * whether or not the number behind it is real, so the guard has to be in the
 * tool, not in the reading.
 */
const METHOD = {
  /* Product-defining attributes that belong in a title: full spectrum, EMF
     tier, barrel, hybrid, wood species. A body mention is a cross-sell risk
     (instance 11) — "unlike our cedar cabins" counts a hemlock unit as cedar. */
  TITLE: 'title-only',
  /* Fitted features a title rarely mentions: chromotherapy, Bluetooth, red
     light, tool-free assembly, chiller. Title-only undercounts these massively
     — 2 of 28 Maxxus titles say chromotherapy; 28 of 28 listings do. */
  BOTH: 'title-or-body',
};

/** Divergence above this makes the choice of method material, not cosmetic. */
const DIVERGENCE_FLAG = 20;

function derive(members, label, re, method) {
  if (method !== METHOD.TITLE && method !== METHOD.BOTH) {
    throw new Error(
      `collection-spec: "${label}" was counted with no method.\n` +
      '  A count and its method are ONE value. Pass METHOD.TITLE or METHOD.BOTH.\n' +
      '  See the method ruling of 8 September 2026 and round-1 instance 13.',
    );
  }
  const d = members.length;
  const t = members.filter((p) => re.test(titleOf(p))).length;
  const b = members.filter((p) => re.test(bodyOf(p))).length;
  const e = members.filter((p) => re.test(text(p))).length;

  const n = method === METHOD.TITLE ? t : e;
  const divergence = e ? Math.round((100 * (e - t)) / e) : 0;
  /* Divergence only means "the method choice is contestable" for a TITLE fact,
     where a body match may be a cross-sell and either number is arguable.
     For a BOTH fact the divergence is EXPECTED and is the reason BOTH was
     chosen — titles do not mention fitted features. Flagging those the same
     way produced the advice "state the conservative figure (2)" for a
     chromotherapy fact that is genuinely 28 of 28, which would have made the
     copy worse. So the flag is scoped to TITLE facts; BOTH facts always show
     their split and carry a cross-sell spot-check note instead. */
  const flagged = method === METHOD.TITLE && divergence > DIVERGENCE_FLAG;
  const bodyOnly = method === METHOD.BOTH && t === 0 && e > 0;
  const p = pct(n, d);

  return {
    label, method, n, d, pct: p,
    title: t, body: b, either: e,
    divergence, flagged,
    /* When the two methods differ materially the draft may not simply pick one
       silently. Same handling as the mG figures: state the conservative count,
       or say how many publish the attribute at all. */
    handling: flagged
      ? `METHODS DIVERGE ${divergence}% on a title-only attribute (title ${t}, either ${e}). A body match here may be a cross-sell. State the conservative figure (${Math.min(t, e)}), or say how many publish it at all. Do not pick one silently.`
      : bodyOnly
        ? `Rests entirely on listing body — 0 of ${d} titles state it. Expected for a fitted feature, but spot-check that the body mention describes THIS unit and is not a comparison or cross-sell before writing it as a collection property.`
        : null,
    universal: p >= 90 ? 'safe as a universal claim'
      : p >= 50 ? 'majority only — say "most", never "all"'
      : p > 0 ? `EXISTENCE ONLY — ${n} of ${d}. Do not write as a property of the collection`
      : 'absent',
  };
}

/* 18i: the method-less-count throw had no test. A constructed member set; nothing live. */
if (selftest) {
  const fx = [{ title: 'Cedar Barrel Sauna', descriptionHtml: '<p>Spruce benches.</p>' }];
  const cases = [
    ['no method THROWS', () => derive(fx, 'cedar', /cedar/), true],
    ['an unknown method THROWS', () => derive(fx, 'cedar', /cedar/, 'title-first'), true],
    ['METHOD.TITLE returns a count', () => derive(fx, 'cedar', /cedar/, METHOD.TITLE), false],
  ];
  let bad = 0;
  for (const [label, fn, wantThrow] of cases) {
    let threw = false; try { fn(); } catch { threw = true; }
    const ok = threw === wantThrow; if (!ok) bad++;
    console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label}`);
  }
  process.exit(bad ? 1 : 0);
}

function spec(handle) {
  const c = byHandle.get(handle);
  if (!c) return { handle, error: 'no such collection in data/collections.json' };

  const all = products.filter((p) => p.collections.includes(handle));
  const A = all.filter((p) => p.status === 'ACTIVE' && p.priceMin > 0);
  if (!A.length) return { handle, error: `no ACTIVE priced products (${all.length} total members)` };

  /* A shopper's range spans the CHEAPEST cheapest variant to the DEAREST dearest
     variant. Both ends were previously taken from priceMin, which silently
     understates the top wherever a product has a variant spread: indoor-sauna
     published "$11,999 to $18,667" while a Kohler variant sells at $22,800.
     Min from priceMin, max from priceMax, median from priceMin (the entry
     price is what a median is useful for). */
  const prices = A.map((p) => p.priceMin).sort((a, b) => a - b);
  const topPrices = A.map((p) => p.priceMax || p.priceMin).sort((a, b) => a - b);
  const vendors = {}; A.forEach((p) => { vendors[p.vendor] = (vendors[p.vendor] || 0) + 1; });
  const types = {}; A.forEach((p) => { types[p.productType || '(none)'] = (types[p.productType || '(none)'] || 0) + 1; });

  /* capacity: read from titles only. Body text repeats figures and double-counts. */
  const cap = new Set(); let capN = 0;
  A.forEach((p) => {
    /* \d\s*-?\s*\d? read "10 Person" as capacities 1 AND 0, and "12-person" as 2.
       No live product has a double-digit capacity today, so this was latent —
       it would have silently published "0 to 8 person". Match whole numbers. */
    const ms = [...p.title.matchAll(/(\d{1,2})\s*(?:[-–—]\s*(\d{1,2}))?\s*[-–—]?\s*(?:person|people)/gi)];
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
    price: { min: prices[0], max: topPrices[topPrices.length - 1], median: medianOf(prices), grade: 'SOLID', note: 'min = lowest priceMin, max = highest priceMax (variant spreads count), median = median priceMin. ACTIVE members only, enumerated. Never productsCount, never all members.' },
    vendors: { grade: 'SOLID', breakdown: Object.entries(vendors).sort((a, b) => b[1] - a[1]) },
    productTypes: { grade: 'SOLID', breakdown: Object.entries(types).sort((a, b) => b[1] - a[1]), warn: Object.keys(types).length > 4 ? `${Object.keys(types).length} distinct values — see BACKLOG B6` : null },
    capacity: { grade: 'DERIVED', range: caps.length ? `${caps[0]} to ${caps[caps.length - 1]} person` : null, stated: capN, of: A.length, pct: pct(capN, A.length) },
    temperature: { grade: 'DERIVED', min: temps.length ? Math.min(...temps) : null, max: temps.length ? Math.max(...temps) : null, stated: withTemp, of: A.length, pct: pct(withTemp, A.length) },
    materials: [
      derive(A, 'Canadian Hemlock', /canadian hemlock/, METHOD.TITLE),
      derive(A, 'cedar', /\bcedar\b/, METHOD.TITLE),
      derive(A, 'spruce', /spruce/, METHOD.TITLE),
      derive(A, 'thermo-wood', /thermo/, METHOD.TITLE),
      derive(A, 'stainless steel', /stainless steel/, METHOD.TITLE),
      derive(A, 'inflatable', /inflatable/, METHOD.TITLE),
    ].filter((f) => f.n > 0),
    electrical: [
      derive(A, '120V / 110V named', /\b1[12]0\s*v\b/, METHOD.BOTH),
      derive(A, '240V / 220V named', /\b2[24]0\s*v\b/, METHOD.BOTH),
      derive(A, 'dedicated circuit', /dedicated (\d+\s*amp\s*)?circuit/, METHOD.BOTH),
      derive(A, '20 amp', /\b20\s*amp/, METHOD.BOTH),
    ].filter((f) => f.n > 0),
    features: [
      derive(A, 'tool-free / clasp assembly', /(tool[- ]free|clasp[- ]together|snaps? together)/, METHOD.BOTH),
      derive(A, 'low EMF (any tier)', /low emf/, METHOD.TITLE),
      derive(A, 'ultra-low EMF', /ultra[- ]?low emf/, METHOD.TITLE),
      derive(A, 'near-zero EMF', /near[- ]?zero emf/, METHOD.TITLE),
      derive(A, 'red light therapy', /red light/, METHOD.BOTH),
      derive(A, 'chromotherapy', /chromotherap/, METHOD.BOTH),
      derive(A, 'Bluetooth', /bluetooth/, METHOD.BOTH),
      derive(A, 'chiller', /chiller/, METHOD.BOTH),
      derive(A, 'full spectrum', /full[- ]spectrum/, METHOD.TITLE),
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
  const line = (f) =>
    `    ${String(f.pct + '%').padStart(4)}  ${String(f.n + '/' + f.d).padStart(7)}  ${f.label.padEnd(26)} [${f.method}]  ${f.universal}`
    + `\n${' '.repeat(11)}title ${f.title}  body ${f.body}  either ${f.either}`
    + (f.handling ? `\n${' '.repeat(11)}${f.flagged ? '!!' : ' ~'} ${f.handling}` : '');
  if (s.capacity.range) console.log(`    ${String(s.capacity.pct + '%').padStart(4)}  ${String(s.capacity.stated + '/' + s.capacity.of).padStart(7)}  ${'capacity'.padEnd(26)} range ${s.capacity.range}`);
  if (s.temperature.max) console.log(`    ${String(s.temperature.pct + '%').padStart(4)}  ${String(s.temperature.stated + '/' + s.temperature.of).padStart(7)}  ${'temperature'.padEnd(26)} ${s.temperature.min}°F to ${s.temperature.max}°F published`);
  for (const g of ['materials', 'electrical', 'features']) {
    if (!s[g].length) continue;
    console.log(`    -- ${g} --`);
    s[g].forEach((f) => console.log(line(f)));
  }
  console.log('');
  const flagged = ['materials', 'electrical', 'features'].flatMap((g) => s[g]).filter((f) => f.flagged);
  console.log('  BEFORE WRITING: any fact under 90% coverage is an existence claim, not a');
  console.log('  property of the collection. "Two of eighteen is not a collection fact."');
  console.log('  Every count above carries [its method]. Put that method in the draft front');
  console.log('  matter — a figure whose derivation cannot be shown cannot be defended.');
  if (flagged.length) {
    console.log('');
    console.log(`  !! ${flagged.length} title-only attribute(s) diverge by more than ${DIVERGENCE_FLAG}% between methods:`);
    flagged.forEach((f) => console.log(`     ${f.label} — title ${f.title}, either ${f.either} (${f.divergence}%)`));
    console.log('     Each needs the conservative figure or a coverage statement. Not a silent pick.');
  }
}
