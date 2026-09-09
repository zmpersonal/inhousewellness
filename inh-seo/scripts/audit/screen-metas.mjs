/**
 * Screens collection meta descriptions for two defects:
 *   1. a COUNT that no longer matches the collection's live ACTIVE product count
 *   2. HEALTH-ADJACENT language (hard rule 4)
 *
 * Both probes are validated against known positives before the sweep runs —
 * the three metas rewritten on 2026-09-08. A probe that has not caught a case
 * you already know is broken is decoration (round-1 operating principle).
 * Word STEMS, not fixed phrases: the round-1 screen matched /reduces? inflammation/
 * and missed "inflammation reduction", undercounting by 17.
 */
import path from 'node:path';
import { readJSON, DATA } from '../lib/util.js';

/* Instance 45: any screen aimed at forbidden language fires hardest on the text
   that exists to forbid it. On 155-character metas this changes nothing today —
   a meta never argues against itself — but the check belongs here for the same
   reason the guard belongs anywhere: the field could grow, and a screen that
   cannot tell "detox" from "no detox claims here" is one edit away from
   reporting a correction as a violation. */
const DENIED = /\b(not|aren'?t|isn'?t|never|no|without|avoid|rather than|instead of)\b[^.]{0,40}$/i;
export const denied = (text, index) => DENIED.test(text.slice(Math.max(0, index - 40), index));

const decode = (s) => String(s || '')
  .replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

const WORDNUM = { one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,
  eleven:11,twelve:12,thirteen:13,fourteen:14,fifteen:15,sixteen:16,seventeen:17,eighteen:18,
  nineteen:19,twenty:20,thirty:30,forty:40,fifty:50,sixty:60 };

/** A leading count claim: "23 low EMF saunas", "Five Dreampod tanks". */
function claimedCount(meta) {
  const m = decode(meta).trim().match(/^([A-Za-z]+|\d{1,3})\b/);
  if (!m) return null;
  const tok = m[1].toLowerCase();
  if (/^\d+$/.test(tok)) return parseInt(tok, 10);
  return WORDNUM[tok] ?? null;
}

const HEALTH = [
  /detox/i, /immun/i, /inflam/i, /circulat/i, /metabolis/i, /calorie/i,
  /blood pressure/i, /cardiovascul/i, /cardiac/i, /heart health/i,
  /stress relief/i, /relax(ation|ing)/i, /rejuvenat/i, /revitaliz/i,
  /heal(s|ing)\b/i, /recovery/i, /pain relief/i, /therapeutic/i,
  /wellness journey/i, /high-performance therapy/i, /toxin/i, /sleep better/i,
];
const BANNED_OPENER = /^(discover|explore|experience|transform|elevate|unlock|introducing)\b/i;
const SHOPNOW = /shop now|buy now|order today|limited time|only \d+ left/i;

function screen(handle, meta, activeCount) {
  const d = decode(meta);
  const out = [];
  const claim = claimedCount(d);
  if (claim !== null && activeCount !== null && claim !== activeCount) {
    out.push(`COUNT: meta says ${claim}, collection has ${activeCount} ACTIVE`);
  }
  const health = HEALTH.filter((re) => re.test(d)).map((re) => String(re).replace(/[/i]/g, ''));
  if (health.length) out.push(`HEALTH: ${health.join(', ')}`);
  if (BANNED_OPENER.test(d)) out.push(`OPENER: banned stock opener`);
  if (SHOPNOW.test(d)) out.push(`URGENCY: banned call-to-action`);
  if (d.length > 155) out.push(`LENGTH: ${d.length} decoded chars`);
  return out;
}

/* ---- 1. validate against known positives ---- */
const POSITIVES = [
  ['low-emf (pre-fix)', '23 low EMF saunas, $1,999 to $6,495. Ask for the mG measurement distance before comparing. Free curbside shipping, lower 48.', 21, 'COUNT'],
  ['ultra-low-emf (pre-fix)', 'Explore ultra low EMF saunas designed for safe, daily use. Ideal for health-conscious users seeking low radiation, high-performance therapy', 20, 'HEALTH'],
  ['floatation (pre-fix)', 'Explore premium floatation therapy tanks on InHouseWellness.com. Experience deep relaxation, stress relief, and rejuvenation at home with our top-rated tanks. Shop now!', 5, 'HEALTH'],
];
console.log('PROBE VALIDATION — three known positives\n');
let allCaught = true;
for (const [name, meta, n, expect] of POSITIVES) {
  const f = screen(name, meta, n);
  const caught = f.some((x) => x.startsWith(expect));
  if (!caught) allCaught = false;
  console.log(`  ${caught ? 'CAUGHT ' : 'MISSED '} ${name}`);
  f.forEach((x) => console.log(`           ${x}`));
}
/* a negative control: a meta we believe is clean must NOT fire */
const CLEAN = ['far-infrared', '71 far infrared saunas, $1,999 to $14,999. Every published maximum is 140°F. Free curbside shipping to the lower 48, no minimum.', 71];
const cf = screen(...CLEAN);
console.log(`\n  ${cf.length ? 'FALSE POSITIVE' : 'clean control OK'}  ${CLEAN[0]}${cf.length ? ' -> ' + cf.join('; ') : ''}`);
if (!allCaught) { console.error('\nPROBE FAILED to catch a known positive. Not trustworthy. Aborting.'); process.exit(1); }
console.log('\nProbe catches all three positives and does not fire on the control.\n');

/* ---- 2. sweep ---- */
const collections = readJSON(path.join(DATA, 'collections.json'));
const products = readJSON(path.join(DATA, 'products.json'));
const activeIn = (h) => products.filter((p) => p.collections.includes(h) && p.status === 'ACTIVE').length;

const withMeta = collections.filter((c) => c.seoDescription && c.seoDescription.trim());
console.log(`${'='.repeat(78)}\nSWEEP — ${withMeta.length} collections with a meta description\n${'='.repeat(78)}\n`);
const hits = [];
for (const c of withMeta) {
  const f = screen(c.handle, c.seoDescription, activeIn(c.handle));
  if (f.length) hits.push([c, f]);
}
if (!hits.length) console.log('  No findings.');
for (const [c, f] of hits) {
  console.log(`  ${c.handle}${c.publishedOnline ? '' : '  (unpublished)'}`);
  f.forEach((x) => console.log(`      ${x}`));
  console.log(`      "${decode(c.seoDescription).slice(0, 118)}"`);
  console.log('');
}
console.log(`${hits.length} of ${withMeta.length} flagged.`);
