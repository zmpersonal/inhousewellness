/**
 * Two claim classes that no other screen in this repo looks for.
 *
 * 1. UNSOURCED COMPARATIVE PERFORMANCE — a number attached to a comparison,
 *    with no citation. "30% faster and 40% deeper than standard ceramic
 *    heaters." Rule 6 bans it: a specific figure about a product needs a source.
 *
 *    The distinction that matters: a MECHANISM is an explanation, not a claim.
 *    /collections/barrel-saunas says a barrel "heats faster because the curved
 *    shell encloses less air" — no number, a stated reason, and it must not fire.
 *    The screen requires a FIGURE and a COMPARATIVE and no citation nearby.
 *
 * 2. CLINICAL INSTITUTIONS CITED ON COMMERCIAL PAGES — Harvard Health,
 *    Cleveland Clinic, Mayo Clinic linked from a product description. That is
 *    closer to implying endorsement than the competitor-citation problem was:
 *    a competitor cited is a link-equity and credibility issue, a medical
 *    institution cited to support a product claim reads as approval.
 *
 *   node scripts/audit/unsourced-claims.mjs
 */
import path from 'node:path';
import { readJSON, DATA } from '../lib/util.js';

const FIGURE = /\b\d{1,3}(?:\.\d+)?\s*(?:%|percent|x\b|times|degrees?|°)|\b\d{1,3}(?:\.\d+)?\s*(?:times|x)\s+(?:faster|deeper|hotter|more|longer)/i;
const COMPARATIVE = /\b(faster|deeper|hotter|cooler|longer|stronger|more efficient(?:ly)?|more effective(?:ly)?|greater|better|higher|outperform\w*|superior)\b[^.]{0,40}\b(than|compared (?:to|with)|versus|vs\.?)\b/i;
/* A citation anywhere in the sentence excuses the figure — it is then sourced,
   and whether the source is good is a different screen's problem. */
const CITED = /\([^()]{0,90}(?:\d{4}|et al\.)[^()]{0,40}\)|https?:\/\/|\b(?:according to|per|source:)\b/i;
/* A stated mechanism is an explanation. "because", "since", "which is why". */
const MECHANISM = /\b(because|since|which is why|owing to|due to the fact|the reason)\b/i;

const CLINICAL = /(harvard\.edu|health\.harvard|mayoclinic|clevelandclinic|hopkinsmedicine|nih\.gov|webmd|healthline|mayo clinic|cleveland clinic|harvard health|johns hopkins)/i;

export function performanceClaims(text) {
  const out = [];
  for (const s of text.split(/(?<=[.!?])\s+(?=[A-Z"“])/)) {
    if (s.length < 30 || s.length > 400) continue;
    if (!FIGURE.test(s) || !COMPARATIVE.test(s)) continue;
    if (CITED.test(s) || MECHANISM.test(s)) continue;
    out.push(s.trim());
  }
  return out;
}

/* ---- validation, before any count (instance 40) ---- */
const POS = 'These panels warm 30% faster and penetrate 40% deeper than standard ceramic heaters.';
const NEG = [
  ['a stated mechanism, no number', 'A barrel heats faster than a square cabin because the curved shell encloses less air.'],
  ['a figure with a citation', 'Sauna use raised heart rate 30% more than rest (Laukkanen et al., 2015).'],
  ['a figure, no comparison', 'The cabin reaches 195°F and seats four.'],
  ['a comparison, no figure', 'Infrared runs cooler than a traditional room.'],
];
let ok = performanceClaims(POS).length === 1;
console.log(`  known positive  "30% faster … than ceramic heaters": ${ok ? 'FIRES' : 'DOES NOT FIRE — BAD'}`);
for (const [label, s] of NEG) {
  const q = performanceClaims(s).length === 0;
  console.log(`  known negative  ${label}: ${q ? 'stays silent' : 'FIRES — BAD'}`);
  if (!q) ok = false;
}
if (!ok) { console.error('\nREFUSING to report a count from a probe that failed validation.'); process.exit(1); }

const P = readJSON(path.join(DATA, 'products.json'));
const C = readJSON(path.join(DATA, 'collections.json'));
const A = readJSON(path.join(DATA, 'content.json')).articles || [];
const raw = (o) => String(o.descriptionHtml || o.bodyHtml || o.body || '');
const txt = (o) => raw(o).replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&#39;|&rsquo;/g, "'").replace(/\s+/g, ' ');

console.log('\n=== 1. UNSOURCED COMPARATIVE PERFORMANCE CLAIMS ===\n');
for (const [label, set, key] of [['products', P, 'handle'], ['collections', C, 'handle'], ['articles', A, 'handle']]) {
  const rows = set.map((o) => ({ o, hits: performanceClaims(txt(o)) })).filter((r) => r.hits.length);
  console.log(`  ${label}: ${rows.length} of ${set.length}   ${rows.reduce((n, r) => n + r.hits.length, 0)} sentence(s)`);
  const byV = {};
  rows.forEach((r) => { const v = r.o.vendor || '—'; byV[v] = (byV[v] || 0) + 1; });
  if (label === 'products') Object.entries(byV).sort((a, b) => b[1] - a[1]).forEach(([k, v]) => console.log(`      ${String(v).padStart(2)}  ${k}`));
  rows.slice(0, 12).forEach((r) => r.hits.slice(0, 1).forEach((s) => console.log(`      [${(r.o.status || '').slice(0, 4).padEnd(4)}] ${String(r.o[key]).slice(0, 38).padEnd(40)} ${s.slice(0, 110)}`)));
  console.log('');
}

console.log('=== 2. CLINICAL INSTITUTIONS CITED ON COMMERCIAL PAGES ===\n');
for (const [label, set] of [['products', P], ['collections', C]]) {
  const rows = set.filter((o) => CLINICAL.test(raw(o)));
  console.log(`  ${label}: ${rows.length} of ${set.length}`);
  rows.forEach((o) => {
    const who = [...new Set((raw(o).match(new RegExp(CLINICAL.source, 'gi')) || []).map((x) => x.toLowerCase()))];
    const linked = /<a[^>]+href="[^"]*(?:harvard|mayoclinic|clevelandclinic|hopkins|nih\.gov|webmd|healthline)/i.test(raw(o));
    console.log(`      [${(o.status || '').slice(0, 4).padEnd(4)}] ${String(o.handle).slice(0, 40).padEnd(42)} ${linked ? 'LINKED' : 'named '}  ${who.join(', ')}`);
  });
  console.log('');
}
const artRows = A.filter((a) => /<a[^>]+href="[^"]*(?:harvard|mayoclinic|clevelandclinic|hopkins)/i.test(raw(a)));
console.log(`  articles with a linked clinical institution: ${artRows.length} of ${A.length}`);
console.log('  (articles citing medical sources is normal and expected — listed for contrast, not as a defect)');
