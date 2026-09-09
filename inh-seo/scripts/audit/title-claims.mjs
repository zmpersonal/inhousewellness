/**
 * Do the SEO TITLES still say true things?
 *
 * The claims block covers description prose. Titles were outside it — and a
 * title is the harder case: it is the shortest copy on the page, so it is
 * almost entirely figures, and it is the copy Google shows. 52 titles went
 * live carrying counts, price bands, capacity spans and temperatures with
 * nothing re-deriving any of them.
 *
 * Declarations are HAND-WRITTEN here, one row per title, because a title's
 * numerals cannot be parsed into claims reliably (the same rejection that
 * produced the claims block: prose parsing ran 14% precision). What the
 * machine does is re-derive each declared figure and compare.
 *
 * Three categories, deliberately distinct:
 *   figures       re-derivable from data/products.json — checked every run
 *   definitional  a category or tier DEFINITION ("low EMF means 5–10 mG").
 *                 True independently of which SKUs are in stock. Not a
 *                 coverage claim, so re-deriving it from products would be
 *                 checking the wrong thing (CLAUDE.md 6a).
 *   unchecked     numerals nothing can re-derive — human-verify-only, counted
 *                 and named rather than quietly passed.
 *
 * VOLATILITY is computed, never typed. A figure is volatile-sourced when the
 * products holding it are all from a vendor whose stock fluctuates (Golden
 * Designs / Maxxus / Dynamic Saunas — client, 2026-09-08). That is the
 * distinction the client asked for: "this number changed" vs "this number was
 * always going to change".
 *
 *   node scripts/audit/title-claims.mjs             # check
 *   node scripts/audit/title-claims.mjs --write     # write title: into front matter
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, CONTENT, assertFresh } from '../lib/util.js';
import { runProbe, runScalar, scalarHolders } from '../lib/probes.mjs';

const write = process.argv.includes('--write');
const selfTest = process.argv.includes('--self-test');
assertFresh({ 'products.json': 'npm run audit:products' });
const products = readJSON(path.join(DATA, 'products.json'));
const liveTitles = readJSON(path.join(DATA, 'live-collection-titles.json'));

const VOLATILE = new Set(['Golden Designs Inc', 'Maxxus', 'Dynamic Saunas']);
/* FIXTURE_MEMBERS lets the self-test evaluate against a constructed catalogue
   instead of the live one. See SELF_TEST below for why that is not optional. */
const FIXTURE_MEMBERS = new Map();
const active = (h) => FIXTURE_MEMBERS.get(h)
  ?? products.filter((p) => p.collections.includes(h) && p.status === 'ACTIVE');

/* One row per collection with an SEO title. `figures` maps a NAME to the value
   the title asserts. Names resolve in this order: structural, extractor, probe. */
const STRUCTURAL = new Set(['set_size', 'price_min', 'price_max']);
const D = {
  'barrel-saunas':            { figures:{ set_size:17, price_min:4999 } },
  'cabin-sauna':              { figures:{ set_size:3, price_min:6953, price_max:7999, capacity_min:2, capacity_max:5 } },
  'chimneys':                 { figures:{ set_size:7, price_min:708, price_max:1518, 'vendor:Dundalk Leisurecraft':7 } },
  'chromotherapy':            { figures:{}, definitional:{ coloured_led:'Chromotherapy in a sauna is coloured LED lighting. Saying so is what the term means, not a measurement of these units.' } },
  'cold-plunge-accessories':  { figures:{ price_min:590 } },
  'cold-plunge-cooling-system':{ figures:{}, note:'Pre-existing title, not written in this round.' },
  'cold-plunge':              { figures:{ set_size:18, price_min:760, chiller:7 } },
  'delta':                    { figures:{ set_size:7, price_min:2470, price_max:12009 } },
  'designer-sauna-heaters':   { figures:{ kw_min:4.5, kw_max:8 } },
  'dreampod':                 { figures:{ 'in_collection:floatation-therapy-tanks':5, 'in_collection:cold-plunge':4, price_min:760 } },
  'dynamic-cold-therapy':     { figures:{ set_size:5, price_min:899 } },
  'dynamic-saunas':           { figures:{}, definitional:{ emf_tier_span:'Names the two EMF tiers this vendor sells into. Tier language, not a per-unit measurement.' } },
  'electric-saunas':          { figures:{}, note:'Pre-existing title, not written in this round.' },
  'far-infrared':             { figures:{ max_temp_f:140, capacity_min:1, capacity_max:8 } },
  'finnmark-designs':         { figures:{ set_size:6 } },
  'float-tank-upgrades':      { figures:{} },
  'floatation-therapy-tanks': { figures:{} },
  'full-spectrum':            { figures:{}, definitional:{ spectrum_definition:'Full spectrum means near and mid wavelengths on top of far. That is what the term denotes, so it needs no coverage count — and the previous title, "Low EMF, Near, Mid & Far IR", did read as one: 5 of 26 publish all three wavelengths and 10 of 26 are near-zero tier.' } },
  'golden-designs':           { figures:{ hybrid:'>0', 'in_collection:outdoor-saunas':'>0' } },
  'harvia-sauna-heaters':     { figures:{ set_size:36, kw_min:4.5, kw_max:40 } },
  'health-smart':             { figures:{ nm_set:[660,850] } },
  'helios-massage-chair':     { figures:{ price_min:4000, price_max:5000 } },
  'hot-tubs':                 { figures:{ set_size:7, hot_and_cold:4 } },
  'huum-sauna-heaters':       { figures:{ set_size:31, price_min:773, price_max:6278 } },
  'ice-tubs':                 { figures:{ set_size:6, integrated_cooling:'ALL', thermo_wood_either:'ALL' } },
  'indoor-sauna':             { figures:{ set_size:3, price_min:11999, price_max:22800 } },
  'infrared-saunas':          { figures:{ capacity_min:1, capacity_max:8 }, majority:['names_120v'] },
  'kohler':                   { figures:{ needs_240v:'ALL' } },
  'leisurecraft-cold-plunge': { figures:{ cedar_either:'>0', chiller:0 } },
  'leisurecraft':             { figures:{ set_size:7, cedar_either:'ALL' } },
  'low-emf':                  { figures:{}, definitional:{ mg_tier:'Low EMF in this catalogue means 5–10 mG. A tier definition; the page states separately how many units publish a figure.' } },
  'mande-spa':                { figures:{ set_size:3, thermo_wood_either:'ALL', capacity_min:2, capacity_max:6 } },
  'massage-chairs':           { figures:{ set_size:8, price_min:4000, price_max:10599 } },
  'maxxus':                   { figures:{ capacity_min:2, capacity_max:4, cedar_either:'>0', canadian_hemlock_either:'>0' } },
  'medical-breakthrough':     { figures:{}, note:'Pre-existing title, not written in this round.' },
  'medical-sauna':            { figures:{ set_size:13, price_min:5799, price_max:28649, capacity_min:2, capacity_max:6 } },
  'mr-steam':                 { figures:{ set_size:5, price_min:3500, price_max:13800 } },
  'narvi':                    { figures:{ set_size:7, wood_burning:'ALL', kw_min:16, kw_max:24 } },
  'near-zero-emf':            { figures:{ distance_in_min:2, distance_in_max:3 }, definitional:{ mg_tier:'Near zero EMF means 2–3 mG. Tier definition.' } },
  'outdoor-saunas':           { figures:{ price_min:4940, price_max:26890, capacity_min:2, capacity_max:8 } },
  'red-light-therapy-panel-skin-pain-recovery': { figures:{ nm_set:[660,850] } },
  'red-light-therapy':        { figures:{ publishes_wavelength_nm:0 } },
  'ripavi':                   { figures:{ set_size:2, price_min:36900, price_max:49900 } },
  'roof-option':              { figures:{ set_size:4 } },
  'sauna-accessories':        { figures:{ set_size:30, price_min:65, price_max:1742 } },
  'sauna-heaters':            { figures:{ set_size:95, kw_min:4, kw_max:40 } },
  'sauna-life':               { figures:{ set_size:16 } },
  'sauna-maintenance-product':{ figures:{} },
  'sauna':                    { figures:{ price_min:4940, price_max:49900, wood_burning:'>0' } },
  'saunas':                   { figures:{ capacity_min:1, capacity_max:8, max_temp_f:195, hybrid:'>0' } },
  'scandia-manufacturing':    { figures:{ set_size:10, price_min:1300, price_max:6400 } },
  'scandia':                  { figures:{ set_size:9, capacity_min:4, capacity_max:8 } },
  'service-upgrades':         { figures:{}, unchecked:{ '600/1800':'Service fees are contract terms, not product data — see data/shipping-facts.json.' } },
  'steam-saunas':             { figures:{ set_size:15, max_temp_f:195 } },
  'thermasol':                { figures:{ set_size:12, price_min:8360, price_max:13985 } },
  'ultra-low-emf':            { figures:{}, definitional:{ mg_tier:'Ultra low EMF means 3–5 mG. Tier definition.' } },
};

function structural(h) {
  const a = active(h);
  const priced = a.filter((p) => +p.priceMin > 0);
  return {
    set_size: { value: a.length, holders: a },
    price_min: (() => { const v = Math.min(...priced.map(p => +p.priceMin)); return { value: priced.length ? v : null, holders: priced.filter(p => +p.priceMin === v) }; })(),
    price_max: (() => { const v = Math.max(...priced.map(p => +p.priceMax || +p.priceMin)); return { value: priced.length ? v : null, holders: priced.filter(p => (+p.priceMax || +p.priceMin) === v) }; })(),
  };
}

/** now-value + who holds it, for any declared figure name. */
function derive(h, name) {
  const a = active(h);
  if (STRUCTURAL.has(name)) return structural(h)[name];
  try { const v = runScalar(name, a); return { value: v, holders: scalarHolders(name, a) }; }
  catch { /* not an extractor */ }
  const v = runProbe(name, a);
  return { value: v, holders: a.filter(p => { try { return runProbe(name, [p]) > 0; } catch { return false; } }) };
}

/* A guard that has never failed has not been tested. Each case is a claim we
   KNOW is false, in a shape this checker exists to catch; if any of them passes,
   the checker is decoration. The fourth is a true claim, present so a checker
   that simply flags everything fails the test too. */
const P = (over = {}) => ({
  id: `gid://fixture/${Math.random()}`, handle: 'fx', status: 'ACTIVE',
  vendor: 'Fixture Co', title: '', body: '', collections: ['__fixture__'],
  priceMin: 1000, ...over,
});

/* A CONSTRUCTED catalogue. Six products, chosen so every assertion below is
   decidable from this list alone.

   The previous version pointed at real collections — cold-plunge,
   medical-sauna, outdoor-saunas, red-light-therapy, leisurecraft — and audited
   on 9 September 2026 it was ONE DOLLAR from breaking: the medical-sauna
   fixture asserted a price_max of 28650 against a real 28649. Two others were a
   restock away, with three DRAFT products sitting in each of red-light-therapy
   and leisurecraft ready to republish and falsify a universal claim the fixture
   depends on being true.

   Every one of those would have failed as "the checker is broken" when the
   checker was fine and the CATALOGUE had moved. A guard that cries wolf on a
   restock gets its self-test commented out, and then it is decoration.

   The test of a fixture: can repairing — or merely restocking — the estate break
   it? If yes, it is measuring the estate rather than the code. */
const FIXTURE_CATALOGUE = [
  P({ handle: 'fx-1', title: '2 Person Cedar Barrel Sauna', body: 'Canadian red cedar. 660 nm red light.', priceMin: 1000 }),
  P({ handle: 'fx-2', title: '4 Person Cedar Cabin', body: 'Canadian red cedar staves.', priceMin: 2000 }),
  P({ handle: 'fx-3', title: '6 Person Cedar Sauna', body: 'Canadian red cedar throughout.', priceMin: 3000 }),
  P({ handle: 'fx-4', title: 'Cedar Sauna Heater 8 kW', body: 'Canadian red cedar guard rail.', priceMin: 4000 }),
  P({ handle: 'fx-5', title: 'Cedar Plunge', body: 'Canadian red cedar surround. Integrated chiller.', priceMin: 5000 }),
  P({ handle: 'fx-6', title: 'Cedar Steam Room', body: 'Canadian red cedar bench.', priceMin: 6000, vendor: 'Golden Designs Inc' }),
];
FIXTURE_MEMBERS.set('__fixture__', FIXTURE_CATALOGUE);

/* Three known-FALSE claims in shapes this checker exists to catch — if any
   passes, the checker is decoration. Two known-TRUE, so a checker that simply
   flags everything fails too. */
const SELF_TEST = [
  { h:'__fixture__', fig:{ set_size: 999 },        expect:'fail', why:'count that is not the set size (6)' },
  { h:'__fixture__', fig:{ price_max: 6001 },      expect:'fail', why:'price band off by one dollar (real 6000)' },
  { h:'__fixture__', fig:{ capacity_max: 4 },      expect:'fail', why:'span narrower than the catalogue supports (6)' },
  { h:'__fixture__', fig:{ set_size: 6 },          expect:'pass', why:'the true set size' },
  { h:'__fixture__', fig:{ cedar_either: 'ALL' },  expect:'pass', why:'universal claim that holds — all six say cedar' },
];
if (selfTest) {
  let bad = 0;
  for (const t of SELF_TEST) {
    const drifted = evaluate(t.h, { figures: t.fig }).drift.length > 0;
    const got = drifted ? 'fail' : 'pass';
    const ok = got === t.expect;
    if (!ok) bad++;
    console.log(`  ${ok ? 'OK  ' : 'BUG '} ${t.h.padEnd(20)} expected ${t.expect}, got ${got.padEnd(5)} — ${t.why}`);
  }
  console.log(bad ? `\n${bad} self-test case(s) wrong — the title check does not do what it claims.` : '\nSelf-test passed: the checker flags each known-false claim and clears each true one.');
  process.exit(bad ? 1 : 0);
}

function evaluate(h, spec) {
  const a = active(h);
  const ownVendors = new Set(a.map(p => p.vendor));
  const vendorCollection = ownVendors.size === 1 && VOLATILE.has([...ownVendors][0]);
  const figures = {}, volatile = [], drift = [];
  for (const [name, asserted] of Object.entries(spec.figures || {})) {
    const { value, holders } = derive(h, name);
    const eq = Array.isArray(asserted) ? JSON.stringify(asserted) === JSON.stringify(value)
      : asserted === '>0' ? value > 0
      : asserted === 'ALL' ? value === a.length
      /* A price in a title is written in whole dollars. $708.13 shown as "$708"
         and $12,008.95 shown as "$12,009" are both correct copy, so compare at
         dollar resolution rather than reporting three titles as drifted when
         what drifted was the comparison. */
      : STRUCTURAL.has(name) && typeof value === 'number'
        ? (Math.round(value) === Number(asserted) || Math.floor(value) === Number(asserted))
      : String(asserted) === String(value);
    figures[name] = value;
    if (!eq) drift.push({ name, asserted, now: value, of: a.length });
    /* A count moves if any volatile member matches; a boundary is false the
       moment its holders go, so it is volatile only when NO stable product
       ties it. Different fragilities, different tests. */
    const vol = STRUCTURAL.has(name) || name === 'set_size'
      ? holders.some(p => VOLATILE.has(p.vendor))
      : holders.length > 0 && holders.every(p => VOLATILE.has(p.vendor));
    if (vol) volatile.push({ name, holders: holders.length, vendors: [...new Set(holders.map(p => p.vendor))] });
  }
  /* "Most plug into a 120V outlet" — a majority claim, not a count. */
  const majority = [];
  for (const name of spec.majority || []) {
    const v = runProbe(name, a);
    majority.push({ name, count: v, of: a.length, holds: v * 2 > a.length });
    if (!(v * 2 > a.length)) drift.push({ name, asserted: 'MAJORITY', now: `${v}/${a.length}`, of: a.length });
  }
  return { handle: h, title: liveTitles[h], n: a.length, figures, volatile, majority, drift,
    vendorCollection, definitional: spec.definitional || {}, unchecked: spec.unchecked || {}, note: spec.note };
}

const rows = [];
for (const [h, spec] of Object.entries(D)) rows.push(evaluate(h, spec));

const bad = rows.filter(r => r.drift.length);
console.log(`title-claims — ${rows.length} titles, ${rows.reduce((n, r) => n + Object.keys(r.figures).length, 0)} declared figures\n`);
if (bad.length) {
  console.log(`${bad.length} TITLE(S) STATING SOMETHING THAT NO LONGER RE-DERIVES:\n`);
  for (const r of bad) {
    console.log(`  ${r.handle}  —  ${r.title}`);
    r.drift.forEach(d => console.log(`     ${d.name.padEnd(26)} title says ${String(d.asserted).padEnd(12)} data gives ${d.now}`));
  }
  console.log('');
}
const vol = rows.filter(r => r.volatile.length && !r.vendorCollection);
console.log(`${vol.length} title(s) carrying a VOLATILE-SOURCED figure (would move on a restock, not on an error):`);
for (const r of vol) console.log(`  ${r.handle.padEnd(30)} ${r.volatile.map(v => `${v.name}(${v.holders} holder(s): ${v.vendors.join(', ')})`).join('; ')}`);
const vc = rows.filter(r => r.vendorCollection);
console.log(`\n${vc.length} vendor collection(s) — every figure is volatile by construction, so flagging each one says nothing: ${vc.map(r => r.handle).join(', ')}`);
console.log(`\n${rows.filter(r => !r.drift.length).length} clean · ${bad.length} drifted · ${rows.filter(r => Object.keys(r.definitional).length).length} carrying a definitional claim · ${rows.filter(r => Object.keys(r.unchecked).length).length} with an unchecked numeral.`);

if (write) {
  let n = 0;
  for (const r of rows) {
    const p = path.join(CONTENT, 'collections', `${r.handle}.md`);
    if (!fs.existsSync(p)) continue;
    const s = fs.readFileSync(p, 'utf8');
    const volNames = new Set(r.volatile.map(v => v.name));
    let b = '  title:\n';
    b += `    text: ${JSON.stringify(r.title || '')}\n`;
    b += `    applied: 2026-09-08\n`;
    if (Object.keys(r.figures).length) {
      b += '    figures:\n';
      for (const [k, v] of Object.entries(r.figures)) {
        const mark = volNames.has(k) ? '   # VOLATILE-SOURCED' : '';
        b += `      ${JSON.stringify(k)}: ${JSON.stringify(v)}${mark}\n`;
      }
    }
    if (r.majority.length) b += '    majority:\n' + r.majority.map(m => `      ${m.name}: ${m.count}/${m.of}`).join('\n') + '\n';
    if (r.vendorCollection) b += '    vendor_collection: true   # single volatile vendor; every figure moves with its stock\n';
    for (const [k, v] of Object.entries(r.definitional)) b += `    definitional:\n      ${k}: ${JSON.stringify(v)}\n`;
    for (const [k, v] of Object.entries(r.unchecked)) b += `    unchecked:\n      ${JSON.stringify(k)}: ${JSON.stringify(v)}\n`;
    if (r.note) b += `    note: ${JSON.stringify(r.note)}\n`;
    let out = s.replace(/^  title:\n(?:[ ]{4,}.*\n)*/m, '');
    const parts = out.split(/^---$/m);
    parts[1] = parts[1].replace(/\n+$/, '\n') + b;
    fs.writeFileSync(p, parts.join('---'));
    n++;
  }
  console.log(`\ntitle: block written to ${n} file(s).`);
}
process.exit(bad.length ? 1 : 0);
