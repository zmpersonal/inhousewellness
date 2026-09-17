/* Round 16 — assert every FIGURE printed in the drafts against a live re-derivation.
 * This is the MEASUREMENT, re-run after the edit, not the read-back (CLAUDE.md).
 * A figure that drifts in the catalogue fails this run, which is the point.
 */
import fs from 'node:fs';
const P = JSON.parse(fs.readFileSync('data/products.json', 'utf8'));
const ALL = Array.isArray(P) ? P : (P.products || P.nodes);
const A = ALL.filter((p) => (p.status || '').toUpperCase() === 'ACTIVE');
const inC = (p, h) => (p.collections || []).some((c) => (c.handle || c) === h);
const txt = (p) => `${p.title || ''} ${p.descriptionHtml || ''}`;
const SP = '[\\u0020\\u00A0\\u202F\\u2009\\u200B]*';
const med = (arr) => { const v = arr.map((p) => +p.priceMin).filter(Number.isFinite).sort((a, b) => a - b); return v[Math.floor(v.length / 2)]; };
const T = fs.readFileSync('content/drafts/infrared-vs-traditional-sauna.html', 'utf8');
const S = fs.readFileSync('content/drafts/infrared-vs-steam-sauna.html', 'utf8');

const IR = A.filter((p) => inC(p, 'infrared-saunas'));
const TR = A.filter((p) => inC(p, 'sauna'));
const ST = A.filter((p) => inC(p, 'steam-saunas') || inC(p, 'steam-showers'));
const SS = A.filter((p) => inC(p, 'steam-showers'));
const SA = A.filter((p) => inC(p, 'steam-saunas'));
const v120 = A.filter((p) => new RegExp(`\\b120${SP}v`, 'i').test(txt(p)));
const v240 = A.filter((p) => new RegExp(`\\b(?:240|220)${SP}v`, 'i').test(txt(p)));
const s1 = new Set(v120), s2 = new Set(v240);
const neither = A.filter((p) => !s1.has(p) && !s2.has(p));
const heat = A.filter((p) => /heat(?:s)?[-\s]?up|pre[-\s]?heat|reaches?\s+\d+\s*°?\s*F\s+in/i.test(txt(p)));
const degF = A.filter((p) => /\d{2,3}\s*°?\s*F\b/i.test(txt(p)));
const HS = A.filter((p) => inC(p, 'sauna-heaters'));
const kw = HS.filter((p) => /\d+(?:\.\d+)?\s*kW/i.test(txt(p)));

// [label, derived value, must appear in this doc]
const CLAIMS = [
  ['ACTIVE population',        481,      A.length,        [T, S]],
  ['total products',           673,      ALL.length,      [T, S]],
  ['infrared set size',        90,       IR.length,       [T, S]],
  ['infrared median',          3699,     med(IR),         [T, S]],
  ['traditional set size',     57,       TR.length,       [T]],
  ['traditional median',       7999,     med(TR),         [T]],
  ['steam set size',           39,       ST.length,       [T]],
  ['steam-showers set size',   24,       SS.length,       [S]],
  ['steam-showers median',     11625,    med(SS),         [S]],
  ['steam-saunas set size',    15,       SA.length,       [S]],
  ['names 120V',               82,       v120.length,     [T]],
  ['names 240V',               48,       v240.length,     [T]],
  ['names neither voltage',    367,      neither.length,  [T]],
  ['publishes heat-up time',   39,       heat.length,     [T]],
  ['states a °F figure',       82,       degF.length,     [T]],
  ['heaters publishing kW',    90,       kw.length,       [T]],
  ['sauna-heaters ACTIVE',     95,       HS.length,       [T]],
];
let bad = 0;
console.log('FIGURE                        printed   re-derived   in copy');
for (const [label, printed, derived, docs] of CLAIMS) {
  const match = printed === derived;
  const present = docs.every((d) => d.includes(printed.toLocaleString('en-US')) || d.includes(String(printed)));
  const good = match && present;
  if (!good) bad++;
  console.log(`  ${good ? 'ok  ' : 'FAIL'} ${label.padEnd(26)} ${String(printed).padStart(6)}   ${String(derived).padStart(8)}   ${present ? 'yes' : 'NOT FOUND'}`);
}
// figures that must NOT survive
for (const [doc, name, needles] of [[T, 'T', ['480', '672', '121 name', '288 of', '40 kW', '161 of']],
                                    [S, 'S', ['95 active', '5kW to 30kW']]]) {
  for (const n of needles) if (doc.includes(n)) { console.log(`  FAIL [${name}] superseded figure still present: "${n}"`); bad++; }
}
console.log(bad ? `\nFAILED — ${bad}` : '\nEVERY PUBLISHED FIGURE MATCHES THE CATALOGUE');
process.exitCode = bad ? 1 : 0;
