/**
 * Are the numbers in live collection copy still true?
 *
 * Draft products republish when suppliers restock ("a lot of products go draft
 * when suppliers run out of inventory" — client, 2026-09-08). Every description
 * states live counts, so every count goes stale the day stock returns.
 *
 * This does NOT parse prose. Prose parsing was measured and rejected: 481
 * candidate numbers across 46 descriptions, only 14% matching the declared set
 * size, the rest a mix of secondary counts and false positives ("lower 48",
 * "one each", "8.0kW", "Traditional 5"). Instead it reads the `claims:` block
 * in each draft's front matter — a machine-readable record of what was asserted
 * and how it was derived — and re-derives each figure now.
 *
 *   node scripts/audit/drift-check.mjs              # report drift
 *   node scripts/audit/drift-check.mjs --backfill   # write claims: from current data
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, CONTENT, probeText, assertFresh } from '../lib/util.js';
import { runAll, PROBES, composeCandidates, structuredCandidates } from '../lib/probes.mjs';

const backfill = process.argv.includes('--backfill');

/* This check compares live copy against re-derived product data. Run against a
   dump older than the last write, it compares STALE TO STALE and passes —
   silently, on the very check that exists to catch a number going out of date.
   That is instance 14 aimed at its own successor: a test written to prove a
   guard works, defeated by the same condition the guard exists to catch.
   Assert freshness before deriving anything. */
assertFresh({ 'products.json': 'npm run audit:products', 'collections.json': 'npm run audit:collections' });
const products = readJSON(path.join(DATA, 'products.json'));
/* Category 3: prose numbers that are not claims, exempted BY NAME per page.
   Never widen the extractor regex to make the count fall — see
   data/claim-exemptions.json. */
const EXEMPT = (() => {
  try {
    const j = readJSON(path.join(DATA, 'claim-exemptions.json'));
    const m = new Map();
    for (const e of j.exemptions) {
      if (!m.has(e.handle)) m.set(e.handle, new Set());
      m.get(e.handle).add(e.number);
    }
    return m;
  } catch { return new Map(); }
})();
const dir = CONTENT ? path.join(CONTENT, 'collections') : 'content/collections';

const members = (h) => products.filter((p) => p.collections.includes(h));
const active = (h) => members(h).filter((p) => p.status === 'ACTIVE');
const draft = (h) => members(h).filter((p) => p.status === 'DRAFT');

/** The figures copy actually asserts. Keep this list small and exact. */
function derive(h) {
  const a = active(h);
  if (!a.length) return null;
  const priced = a.filter((p) => +p.priceMin > 0);
  const lows = priced.map((p) => +p.priceMin).sort((x, y) => x - y);
  const highs = priced.map((p) => +p.priceMax || +p.priceMin).sort((x, y) => x - y);
  const med = lows.length % 2 ? lows[(lows.length - 1) / 2] : (lows[lows.length / 2 - 1] + lows[lows.length / 2]) / 2;
  return {
    _members: a,
    set_size: a.length,
    price_min: lows[0] ?? null,
    price_max: highs[highs.length - 1] ?? null,
    price_median: med ?? null,
    draft_count: draft(h).length,
  };
}

/* Spelled numbers one..ninety-nine, generated rather than listed. A hand-written
   map held "twenty-one" but not "sixty-four" or "ninety-two", so three claims on
   /collections/saunas were invisible to the checker — neither verified nor
   flagged as unchecked. Same shape as instance 29: what a probe silently drops
   leaves no trace in the output. */
const WORDNUM = (() => {
  const ones = ['one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen'];
  const tens  = { twenty:20, thirty:30, forty:40, fifty:50, sixty:60, seventy:70, eighty:80, ninety:90 };
  const m = {};
  ones.forEach((w,i) => m[w] = i+1);
  for (const [t,v] of Object.entries(tens)) {
    m[t] = v;
    for (let i=0;i<9;i++) m[`${t}-${ones[i]}`] = v+i+1;
  }
  return m;
})();
/** Integers a reader would take as a count. Excludes prices, units, and 48. */
function numbersInProse(text){
  const out=new Set();
  /* Longest-first. Alternation is ordered, so "sixty" matched before "sixty-one"
     and "Sixty-one" was read as 60 — the claim silently became a different number
     rather than being flagged. */
  const words = Object.keys(WORDNUM).sort((a,b)=>b.length-a.length).join('|');
  const re=new RegExp('(?<![$\\d.,])\\b(' + words + '|\\d{1,3})\\b','gi');
  for(const m of text.matchAll(re)){
    const after=text.slice(m.index+m[0].length, m.index+m[0].length+16);
    /* "of" was in this list and it excluded the exact shape of a count claim —
       "eight OF the 21 cabins". Units and range-joiners stay; "of" does not. */
    if(/^\s*(?:°|f\b|mg\b|kw\b|nm\b|v\b|amp|inch|hp\b|gallon|business|hour|year|month|day|to\b|and\b)/i.test(after)) continue;
    if(text.slice(Math.max(0,m.index-2), m.index).includes('$')) continue;
    const n=WORDNUM[m[0].toLowerCase()] ?? parseInt(m[0],10);
    /* 48 was banned outright for "lower 48" — and that hid a real claim,
       "Forty-eight are wood-burning", on sauna-heaters. Exempt the PHRASE, not
       the number (instance 29: an exclusion must not swallow the case it exists
       to catch). */
    const pre = text.slice(Math.max(0, m.index - 7), m.index).toLowerCase();
    if (n === 48 && /lower\s*$/.test(pre)) continue;
    if (n) out.add(n);
  }
  return out;
}

const files = fs.readdirSync(dir).filter((f) => f.endsWith('.md'));
const drifted = [], clean = [], noClaims = [], noStock = [], unchecked = [];
const runProbeSafe = (n, m) => { const { runProbe } = probesMod; return runProbe(n, m); };
import * as probesMod from '../lib/probes.mjs';

for (const f of files) {
  const p = path.join(dir, f);
  const s = fs.readFileSync(p, 'utf8');
  if (!/^status: approved/m.test(s)) continue;
  const handle = f.replace('.md', '');
  const now = derive(handle);
  if (!now) { noStock.push(handle); continue; }

  if (backfill) {
    const body = s.split(/^---$/m).slice(2).join('---').replace(/<[^>]*>/g, ' ');
    const proseNums = numbersInProse(body);
    const probes = { ...runAll(now._members), ...structuredCandidates(now._members, handle), ...composeCandidates(now._members) };
    /* A probe joins the block only when its CURRENT value appears as a number in
       this page's prose — that is the evidence the page is claiming it. Probes
       whose value is not cited are left out rather than guessed at. */
    const structural = { set_size: now.set_size, price_min: now.price_min, price_max: now.price_max, price_median: now.price_median, draft_count: now.draft_count };
    /* Plain probes first — they are unambiguous. Their names then inform which
       COMPOSITION to prefer: a composition of two probes this page already
       cites is far likelier to be the claim than a coincidental pair at the
       same value. Without this, ultra-low-emf's "six of those 13 say what
       distance" was recorded as states_measure_distance+red_light, which
       happens to equal 6 and is not what the sentence means. */
    const plainCited = new Map();
    for (const [k, v] of Object.entries(probes)) {
      if (!(v > 0) || !proseNums.has(v) || k.includes('+') || k.includes(':')) continue;
      const cur = plainCited.get(v);
      if (!cur || k.length < cur.length) plainCited.set(v, k);
    }
    const plainNames = new Set(Object.keys(probes).filter(k => !k.includes('+') && !k.includes(':') && probes[k] > 0 && proseNums.has(probes[k])));
    const byVal = new Map(([...plainCited].map(([v, k]) => [v, { k, v, rank: 0 }])));
    for (const [k, v] of Object.entries(probes)) {
      if (!(v > 0) || !proseNums.has(v) || byVal.has(v)) continue;
      const isComp = k.includes('+');
      const bothCited = isComp && k.split('+').every(n => plainNames.has(n));
      const rank = isComp ? (bothCited ? 1 : 3) : 2;   // cited-composition beats parameterised beats stray composition
      const cur = byVal.get(v);
      if (!cur || rank < cur.rank || (rank === cur.rank && k.length < cur.k.length)) byVal.set(v, { k, v, rank });
    }
    const cited = [...byVal.values()].map(x => [x.k, x.v]);
    const accounted = new Set([...Object.values(structural), ...cited.map(([, v]) => v)]);
    /* Prose numbers no probe or structural field explains. NOT a pass — they are
       claims nothing can re-derive, and the file says so. */
    const ex = EXEMPT.get(handle) || new Set();
    const unchecked = [...proseNums].filter(n => !accounted.has(n) && !ex.has(n));
    let block = 'claims:\n' + Object.entries(structural).map(([k, v]) => `  ${k}: ${v}`).join('\n') + '\n';
    if (cited.length) block += '  derived:\n' + cited.map(([k, v]) => `    ${k}: ${v}`).join('\n') + '\n';
    block += `  unchecked_claims: ${unchecked.length}${unchecked.length ? '   # numbers in prose no probe explains — human-verify-only' : ''}\n`;
    let out = s.replace(/^claims:\n(?:[ ]{2,}.*\n)*/m, '');
    const parts = out.split(/^---$/m);
    parts[1] = parts[1].replace(/\n+$/, '\n') + block;
    fs.writeFileSync(p, parts.join('---'));
    continue;
  }

  const m = s.match(/^claims:\n((?:  .*\n)*)/m);
  if (!m) { noClaims.push(handle); continue; }
  const declared = {};
  for (const line of m[1].split('\n')) {
    const kv = line.match(/^  (\w+):\s*(.+)$/);
    if (kv) declared[kv[1]] = kv[2].trim();
  }
  const diffs = [];
  for (const [k, v] of Object.entries(now)) {
    if (k === '_members' || !(k in declared)) continue;
    if (String(v) !== declared[k]) diffs.push({ k, was: declared[k], now: v });
  }
  /* re-run every declared derived probe */
  const dm = s.match(/^  derived:\n((?:    .*\n)*)/m);
  if (dm) {
    for (const line of dm[1].split('\n')) {
      const kv = line.match(/^    (\w+):\s*(\d+)/);
      if (!kv) continue;
      let val;
      try { val = runProbeSafe(kv[1], now._members); } catch (e) { diffs.push({ k: kv[1], was: kv[2], now: 'PROBE MISSING' }); continue; }
      if (String(val) !== kv[2]) diffs.push({ k: kv[1], was: kv[2], now: val });
    }
  }
  const uc = Number((s.match(/^  unchecked_claims:\s*(\d+)/m) || [])[1] || 0);
  if (diffs.length) drifted.push({ handle, diffs, uc });
  else if (uc > 0) unchecked.push({ handle, uc });
  else clean.push({ handle });
}

if (backfill) { console.log(`claims: block written to ${files.length} candidate file(s). Re-run without --backfill to check.`); process.exit(0); }

console.log(`drift-check — ${clean.length + drifted.length} approved description(s) with a claims block\n`);
if (drifted.length) {
  console.log(`${drifted.length} DRIFTED — the live copy states a number that is no longer true:\n`);
  for (const d of drifted) {
    console.log(`  ${d.handle}`);
    d.diffs.forEach((x) => console.log(`     ${x.k.padEnd(14)} copy says ${String(x.was).padEnd(12)} now ${x.now}`));
  }
  console.log('');
}
if (unchecked.length) {
  console.log(`${unchecked.length} with UNCHECKED CLAIMS PRESENT — numbers in the prose that no probe can re-derive.`);
  console.log('These are NOT passes. They need a human, or a probe adding to scripts/lib/probes.mjs:\n');
  unchecked.sort((a,b)=>b.uc-a.uc).forEach(u => console.log(`  ${u.handle.padEnd(38)} ${u.uc} unverifiable number(s)`));
  console.log('');
}
if (noClaims.length) console.log(`${noClaims.length} without a claims block (run --backfill): ${noClaims.join(', ')}\n`);
if (noStock.length) console.log(`${noStock.length} with zero live products — copy cannot be true: ${noStock.join(', ')}\n`);
console.log(`${clean.length} fully clean · ${unchecked.length} unchecked-claims-present · ${drifted.length} drifted.`);
/* The vocabulary check runs BEFORE this exit, not after. It was appended below
   it first, and the guard's own self-test then never executed — a validation
   block placed after the exit is the silent version of having no validation at
   all, and the run still printed a confident report. */
const REPORT_EXIT = drifted.length || unchecked.length ? 1 : 0;

/* ---- KNOWN-POSITIVE CHECK ------------------------------------------------
 *
 * This guard re-derives every published figure from `lib/probes.mjs`. The copy
 * it checks was DRAFTED from `collection-spec.js`, which counts with the same
 * probes. So a monolingual probe makes the copy wrong and makes drift-check
 * confirm the wrong number, forever, with no error anywhere.
 *
 * Eight probe-vocabulary instances are on record (16, 24, 27, 29, 30, 33, 40,
 * and the changelog matcher). This is the guard that cannot catch the ninth.
 *
 * The fixtures are SYNTHETIC — repairing or restocking the catalogue cannot
 * break them — but the VOCABULARY in them was taken from a hand read of real
 * manufacturer copy, because reading the probe list can only confirm what the
 * probe list already knows. Icetubs never write "chiller"; they write "cooling
 * engine" and "18 kW cooling capacity", which is how `/chiller/` once returned
 * 0 of 6 on a range where every unit ships one.
 */
import { PROBES as _P, runProbe as _run } from '../lib/probes.mjs';

/* Field names matter: probes read `title` and `descriptionHtml`. The first
   version of these fixtures passed `body`, every positive returned 0, and the
   three NEGATIVE controls passed trivially — a validation block that is broken
   in the direction of silence looks like a probe that is simply strict. */
const _p = (title, descriptionHtml) => ({ id: 'fx', handle: 'fx', status: 'ACTIVE', vendor: 'Fixture Co', title, descriptionHtml, collections: ['__fixture__'], priceMin: 1000 });

/* [probe, product, expected count, why this wording and not ours] */
const VOCAB = [
  ['integrated_cooling', _p('Icetubs Regular', 'Ships with an integrated cooling engine, 18 kW cooling capacity.'), 1,
    'manufacturer says "cooling engine"; /chiller/ once returned 0 of 6 on this range'],
  ['integrated_cooling', _p('Plunge Pro', 'Includes a chiller unit.'), 1,
    'and our own word must still match'],
  /* cedar and canadian_hemlock are TITLE-ONLY by rule 6c — a wood species is a
     product-defining attribute, and a body match counts "unlike our cedar
     cabins" on a hemlock unit. The first version of these two fixtures put the
     species in the BODY and failed, which was the fixture being wrong about the
     method rather than the probe being wrong about the word. Both forms are
     asserted now so the method itself is pinned. */
  ['cedar', _p('Canadian Red Cedar Barrel Sauna', 'Staves and benches.'), 1, 'title-only: the species in the title'],
  ['cedar', _p('Barrel Sauna', 'Built from Canadian red cedar staves.'), 0, 'title-only: a body mention must NOT count'],
  ['cedar_either', _p('Barrel Sauna', 'Built from Canadian red cedar staves.'), 1, 'the _either variant is title-or-body'],
  ['canadian_hemlock', _p('3 Person Canadian Hemlock Cabin', 'Reforested timber.'), 1, 'title-only'],
  ['hot_and_cold', _p('Dual Unit', 'A hot and cold therapy tub.'), 1, '"and" separator'],
  ['hot_and_cold', _p('Dual Unit', 'Hot & cold in one shell.'), 1, '"&" separator — the form a title uses'],
  ['needs_240v', _p('Heater', 'Requires a dedicated 240V hardwired circuit.'), 1, 'hardwired phrasing'],
];
/* Negative controls: the probe must not count a product that MENTIONS the
   concept while being something else. "unlike our cedar cabins" on a hemlock
   unit is the cross-sell miscount rule 6c names. */
const NEG = [
  ['cedar_either', _p('Hemlock Cabin', 'Warmer to the touch than our cedar cabins.'), 1,
    'KNOWN LIMITATION, asserted so it cannot be forgotten: title-or-body cannot tell a comparison from a material. This is why wood species is title-only.'],
  ['red_light', _p('Rock Bag', 'Natural sauna rocks. No lighting of any kind.'), 0, 'unrelated product'],
];

/* A DOCUMENTED WEAKNESS, deliberately not fixed.

   `integrated_cooling` counts "No chiller included; add ice by hand" as a
   cooling feature. A negation guard is the obvious fix and it would be WORSE
   than the bug: the two live products this pattern touches are
   medical-frozen-2 and medical-frozen-3, whose copy reads "No More Ice Bags —
   The built-in cooling system eliminates the need for adding ice". Both DO have
   cooling, and every plausible negation guard turns both into false negatives.

   Zero live false positives today. The residue rule applies: the check points,
   a person decides, and here the person decided the guard costs more than the
   defect. Recorded here rather than in a comment nobody reads, so that anyone
   who "fixes" it meets the two products first. */
const KNOWN_WEAKNESS = ['integrated_cooling', _p('Ice Barrel', 'No chiller included; add ice by hand.'), 1,
  'negation counted as a feature — documented, NOT fixed; see the note above'];

console.log('\nPROBE VOCABULARY CHECK (synthetic; wording taken from real manufacturer copy)');
let bad = 0;
for (const [name, prod, want, why] of [...VOCAB, ...NEG, KNOWN_WEAKNESS]) {
  let got;
  try { got = _run(name, [prod]); } catch (e) { got = `ERROR ${e.message}`; }
  const ok = got === want;
  if (!ok) bad += 1;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(20)} expected ${want}, got ${got}   — ${why}`);
}
if (bad) {
  console.error(`\n${bad} vocabulary fixture(s) failed. A probe that misses the manufacturer's word reports a`);
  console.error('false ZERO, and this guard would then confirm the wrong figure in live copy every time it runs.');
  process.exitCode = 1;
}

process.exit(process.exitCode || REPORT_EXIT);
