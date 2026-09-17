/* Round 16 — correct every figure in the two drafts to the ONE definition re-derived by
 * scripts/audit/r16-figures.mjs (ACTIVE members of the named collection).
 *
 * Every target asserts an exact occurrence count. A target matching a different number of
 * times FAILS THE RUN rather than silently applying to a subset — a partial match is the
 * dangerous outcome (CLAUDE.md). Drafts only; nothing here touches Shopify.
 *   node scripts/apply/r16-fix-figures.mjs [--apply]
 */
import fs from 'node:fs';

const APPLY = process.argv.includes('--apply');
const F1 = 'content/drafts/infrared-vs-traditional-sauna.html';
const F2 = 'content/drafts/infrared-vs-steam-sauna.html';

// [file, expectedCount, from, to]
const EDITS = [
  // ── population ──
  [F1, 1, '672 products, 480 of them active', '673 products, 481 of them active'],
  [F1, 1, '672 products (480 active)', '673 products (481 active)'],

  // ── set sizes: 95→90 infrared, 53→57 traditional (collection membership) ──
  [F1, 2, 'Across 95 active infrared cabins', 'Across 90 active infrared cabins'],
  [F1, 2, 'Across 53 active traditional saunas', 'Across 57 active traditional saunas'],
  [F1, 1, '<td>Infrared</td><td>95</td>', '<td>Infrared</td><td>90</td>'],
  [F1, 1, '<td>Traditional</td><td>53</td>', '<td>Traditional</td><td>57</td>'],
  [F1, 1, 'median $3,699</strong> (95 active)', 'median $3,699</strong> (90 active)'],
  [F1, 1, 'median $7,999</strong> (53 active)', 'median $7,999</strong> (57 active)'],
  [F2, 2, 'Our 95 active infrared cabins run', 'Our 90 active infrared cabins run'],
  [F2, 1, '<strong>$3,699</strong> across 95 active models', '<strong>$3,699</strong> across 90 active models'],

  // ── voltage: re-derived 82 / 48 / 367 (76%), 16 both ──
  [F1, 2, 'Of 480 active products in our catalogue, 121 name a 120V requirement, 102 name 240V, and 288 name no voltage at all.',
          'Of 481 active products in our catalogue, only 82 name a 120V requirement and 48 name 240V. 367 — more than three quarters — name no voltage at all.'],
  [F1, 1, "<strong>288 of our 480 active products don't state a voltage at all.</strong>",
          '<strong>367 of our 481 active products — 76% — don’t state a voltage at all.</strong>'],
  [F1, 1, '<tr><td>Names a 120V requirement</td><td>121</td><td>25%</td></tr>',
          '<tr><td>Names a 120V requirement</td><td>82</td><td>17%</td></tr>'],
  [F1, 1, '<tr><td>Names a 240V requirement</td><td>102</td><td>21%</td></tr>',
          '<tr><td>Names a 240V requirement</td><td>48</td><td>10%</td></tr>'],
  [F1, 1, '<td class="ivt-pick"><strong>288</strong></td><td class="ivt-pick"><strong>60%</strong></td>',
          '<td class="ivt-pick"><strong>367</strong></td><td class="ivt-pick"><strong>76%</strong></td>'],
  [F1, 1, 'Those shares overlap — 31 products name both, usually because different models in a line differ. <strong>The finding is the 60%.</strong>',
          'Those shares overlap — 16 products name both, usually because different models in a line differ. <strong>The finding is the 76%.</strong>'],

  // ── heat-up and temperature coverage ──
  [F1, 2, '44 of 480 active products', '39 of 481 active products'],
  [F1, 1, '<strong>Only 44 of our 480 active products publish a heat-up or preheat time — 9%.</strong> Operating temperature in °F is published on 131 of 480 — 27%.',
          '<strong>Only 39 of our 481 active products publish a heat-up or preheat time — 8%.</strong> A temperature in °F appears on 82 of 481 — 17%.'],

  // ── EMF denominator ──
  [F1, 1, 'We counted. Across all 480 active products:', 'We counted. Across all 481 active products:'],
  [F1, 2, '45 of 480 active products publish a genuine milligauss figure', '45 of 481 active products publish a genuine milligauss figure'],

  // ── sauna heaters: drop the kW RANGE (CLAUDE.md records "3kW to 50kW" as a false claim) ──
  [F1, 1, '<strong>90 of 95 active heaters publish a kW rating</strong>, from 3 kW to 40 kW. Anything above roughly 2.4 kW',
          '<strong>90 of 95 active heaters publish a kW rating</strong>. Anything above roughly 2.4 kW'],

  // ── steam generator range: lowest 5kW, highest 120kW. Use a durable FLOOR. ──
  [F2, 4, '5kW to 30kW', '5kW upward'],
  [F2, 1, 'The steam generators in our catalogue are rated from 5kW upward, and even the smallest is far beyond what a standard 120V household circuit can supply. Every one of them needs a dedicated circuit sized by an electrician, and the larger commercial units need three-phase power.',
          'The steam generators in our catalogue start at 5kW and run up into commercial units rated far higher. Even the smallest is well beyond what a standard 120V household circuit can supply. Every one needs a dedicated circuit sized by an electrician, and the largest need three-phase power.'],
  [F2, 1, 'Our steam generators are rated <strong>5kW upward</strong>, and the entry point is',
          'Our steam generators start at <strong>5kW</strong>, and the entry point is'],
  [F2, 1, '<td><strong>Every</strong> generator we sell needs a dedicated circuit — 5kW upward</td>',
          '<td><strong>Every</strong> generator we sell needs a dedicated circuit — 5kW and up</td>'],
  [F1, 1, 'Prices/specs checked: September 2026 \u2014 480 active products', 'Prices/specs checked: September 2026 \u2014 481 active products'],
  [F2, 1, '<strong>median $3,699</strong> (95 active)', '<strong>median $3,699</strong> (90 active)'],
  [F1, 1, '<strong>Only 44 of our 480 active products publish one at all</strong>', '<strong>Only 39 of our 481 active products publish one at all</strong>'],
];

// the capacity table: every row was wrong. Replace the whole <tbody>.
const CAP_OLD = `    <tr><td>1 person</td><td>3</td><td>$2,299 – $4,695</td><td>$2,299</td></tr>
    <tr><td>2 person</td><td class="ivt-pick">41</td><td>$1,999 – $14,999</td><td class="ivt-pick">$2,699</td></tr>
    <tr><td>3 person</td><td>31</td><td>$2,699 – $16,999</td><td>$4,299</td></tr>
    <tr><td>4 person</td><td>8</td><td>$3,299 – $6,999</td><td>$4,699</td></tr>
    <tr><td>6 person</td><td>5</td><td>$6,499 – $9,999</td><td>$7,499</td></tr>
    <tr><td>8 person</td><td>2</td><td>$9,999</td><td>$9,999</td></tr>`;
const CAP_NEW = `    <tr><td>1 person</td><td>2</td><td>$2,299 – $4,695</td><td>—</td></tr>
    <tr><td>2 person</td><td class="ivt-pick">35</td><td>$1,999 – $14,999</td><td class="ivt-pick">$2,699</td></tr>
    <tr><td>3 person</td><td>28</td><td>$2,699 – $16,999</td><td>$4,499</td></tr>
    <tr><td>4 person</td><td>7</td><td>$3,699 – $6,999</td><td>$4,699</td></tr>
    <tr><td>5 person</td><td>1</td><td>$7,999</td><td>—</td></tr>
    <tr><td>6 person</td><td>4</td><td>$6,499 – $8,999</td><td>$7,499</td></tr>
    <tr><td>8 person</td><td>2</td><td>$9,999</td><td>$9,999</td></tr>`;
EDITS.push([F1, 1, CAP_OLD, CAP_NEW]);

EDITS.push([F1, 1,
  '<strong>A limitation worth knowing.</strong> Capacity is only usable where it is published. <strong>161 of our 480 active products carry a person-count</strong> — the rest either don\u0027t publish one or use that field for something else entirely. The capacity table above covers the infrared cabins that do.',
  '<strong>A limitation worth knowing.</strong> These are the cabins that state a capacity in the product name — <strong>79 of the 90</strong>. The other 11 don\u0027t, so they aren\u0027t in the table. Where a row holds one or two products we\u0027ve left the median out rather than print a median of one.']);

// ── run ──
const files = {};
let fails = 0;
for (const [f, want, from, to] of EDITS) {
  files[f] ??= fs.readFileSync(f, 'utf8');
  const n = files[f].split(from).length - 1;
  const good = n === want;
  console.log(`  ${good ? 'ok  ' : 'FAIL'} ${String(n)}/${want}  ${f.includes('traditional') ? 'T' : 'S'}  ${from.replace(/\s+/g, ' ').slice(0, 72)}`);
  if (!good) { fails++; continue; }
  files[f] = files[f].split(from).join(to);
}
if (fails) { console.log(`\n  REFUSING: ${fails} target(s) did not match the asserted count`); process.exit(1); }

// post-conditions: the wrong figures must be GONE
const post = [
  [F1, '480', 0], [F1, '672', 0], [F1, '95 active infrared', 0], [F1, '90 of 95 active heaters', null], [F1, '53 active', 0],
  [F1, '121', 0], [F1, '288', 0], [F1, '40 kW', 0],
  [F1, '481', null], [F1, '367', null], [F1, '90 active', null],
  [F2, '5kW to 30kW', 0], [F2, '95 active', 0], [F2, '481 active', null],
];
console.log('\n  post-conditions:');
for (const [f, needle, want] of post) {
  const n = files[f].split(needle).length - 1;
  const good = want === null ? n > 0 : n === want;
  console.log(`    ${good ? 'ok  ' : 'FAIL'} "${needle}" ×${n}${want === null ? ' (want >0)' : ` (want ${want})`}  in ${f.includes('traditional') ? 'T' : 'S'}`);
  if (!good) fails++;
}
if (fails) { console.log('\n  REFUSING on post-conditions'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }
for (const [f, c] of Object.entries(files)) fs.writeFileSync(f, c);
console.log(`\n  written: ${Object.keys(files).length} files\n`);
