/* wrong-source-screen — a health or medical domain cited for a commercial fact.
 *
 * Narrow by design. Domain authority and subject relevance are independent, and no
 * screen this project owns looked at the second: the domain is reputable, the link
 * resolves, and only the sentence reveals the mismatch.
 *
 * Finds candidates. A person decides — and per CLAUDE.md, removing one usually
 * orphans a claim, which makes it a content decision rather than a cleanup.
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, REPORTS } from '../lib/util.js';

/* Matched against a de-spaced copy of the sentence, because these appear both as
   domains and as prose names: "clevelandclinic" and "Cleveland Clinic" are the same
   source and a domain-shaped pattern silently misses the second. The known-positive
   caught this before the screen ran. */
const MEDICAL = /webmd|mayoclinic|clevelandclinic|healthline|nih\.gov|ncbi|pubmed|medlineplus|hopkinsmedicine|medicalnewstoday|verywell|drugs\.com|schoolofmedicine|medicalschool|nhs\.uk|who\.int|harvardhealth|massgeneral/i;
const isMedical = (s) => MEDICAL.test(s.replace(/[\s.]/g, ''));
const COMMERCIAL = /\$\s?\d[\d,]{2,}|\bcosts? (can |may |typically |exceed|range|start)|\bpric(e|ing)\b|\bfee\b|\bper (unit|square|month)\b|\d+\s?(inch|inches|"|ft\b|feet)\b|\b\d{3}\s?V\b|\bvoltage\b|\b\d+(\.\d+)?\s?kW\b|\bfreight\b|\bcurbside\b|\bshipping (cost|fee|rate)/i;
/* A sentence that is ABOUT health and merely contains a number is not this. */
const HEALTH = /health|blood|heart|cardio|sleep|pain|inflam|immun|muscle|recover|dehydrat|pregnan|symptom|arrhythm|hypertherm|therap|dose|session length|contraindicat/i;
/* Round 18i: ONE predicate, used by the self-test AND the scan. They were two copies of the same
   expression, so the self-test proved a copy, not the rule that runs. */
const fires = (s) => isMedical(s) && COMMERCIAL.test(s) && !HEALTH.test(s);

/* KNOWN POSITIVES — synthetic. Repairing the estate cannot break this test. Run FIRST: a failing
   self-test must not leave a fresh report behind. */
const MUST_FIRE = [
  'In remote or complex installations, costs can exceed $3,000 (WebMD, 2023; SIU School of Medicine, 2023).',
  'The unit requires a dedicated 240 V circuit (Cleveland Clinic, 2024).',
];
const MUST_NOT = [
  'Keep sessions to 10-20 minutes and watch for dizziness (WebMD, 2023).',
  'Sessions of 15-30 minutes at 60C were used in RA trials (WebMD, 2023; PubMed, 2008).',
  'Premium installation is $1,800 all in.',
  // 18i: medical source + a dollar figure, but the sentence is ABOUT health — the HEALTH exemption must hold
  'Blood pressure fell 8 points in a $3,000 trial (WebMD, 2023).',
];
let fail = 0;
for (const s of MUST_FIRE) if (!fires(s)) { console.error(`  SELFTEST FAIL — should fire: ${s}`); fail = 1; }
for (const s of MUST_NOT) if (fires(s)) { console.error(`  SELFTEST FAIL — should be silent: ${s}`); fail = 1; }
if (fail) { console.error('  SELFTEST FAILED — refusing to scan or write the report'); process.exit(1); }

const docs = [];
const T = readJSON(path.join(DATA, 'content.json'));
const P = readJSON(path.join(DATA, 'products.json'));
const C = readJSON(path.join(DATA, 'collections.json'));
for (const a of T.articles || []) docs.push({ kind: 'article', handle: a.handle, body: a.body || '' });
for (const a of T.pages || []) docs.push({ kind: 'page', handle: a.handle, body: a.body || '' });
for (const a of (Array.isArray(P) ? P : P.products)) docs.push({ kind: 'product', handle: a.handle, body: a.descriptionHtml || '' });
for (const a of (Array.isArray(C) ? C : C.collections)) docs.push({ kind: 'collection', handle: a.handle, body: a.descriptionHtml || '' });

const hits = [];
for (const d of docs) {
  const t = d.body.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
  for (const s of t.split(/(?<=[.!?])\s+/)) {
    if (!fires(s)) continue;                   // HEALTH exemption inside: about health, incidentally numeric
    hits.push({ ...d, sentence: s.trim().slice(0, 300) });
  }
}
console.log(`\nwrong-source-screen — ${hits.length} candidate(s)\n`);
for (const h of hits) console.log(`  [${h.kind}] ${h.handle}\n      ${h.sentence}\n`);

console.log(`  selftest: ${MUST_FIRE.length} known-positives fire, ${MUST_NOT.length} controls silent`);
fs.writeFileSync(path.join(REPORTS, 'wrong-source-screen.md'), `# Wrong-source screen\n\nRun ${new Date().toISOString()}\n\n${hits.length} candidates.\n\n` + hits.map((h) => `- **${h.kind} \`${h.handle}\`**\n  > ${h.sentence}`).join('\n\n'));
process.exit(0);
