/**
 * Rule 4 has two halves. Which articles honour only the first?
 *
 *   1. never assert a health benefit          — enforced hard, all session
 *   2. route the evidence to healthresearchdatabase.com — never checked
 *
 * `sauna-detox-science-explained` is the case that raised it: the estate's most
 * careful article about a health claim, reporting a systematic review, with two
 * PRODUCT links and no evidence route at all.
 *
 * An article that hedges correctly and routes nowhere is doing half the job, and
 * the half it skips is the one that makes the hedge CHECKABLE. A reader who
 * wants to see the study has nowhere to go.
 *
 * Read-only.
 *   node scripts/audit/evidence-routing.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, assertFresh } from '../lib/util.js';

assertFresh({ 'content.json': 'npm run audit:content' });
const arts = readJSON(path.join(DATA, 'content.json')).articles || [];

/* Health-adjacent: the article discusses a physiological subject at all. Wide on
   purpose — a false positive here costs a read, a false negative hides the gap. */
const HEALTH_G = /\b(?:cardiovascular|blood pressure|inflammation|immune|circulation|vasodilation|detox|cortisol|heart rate|recovery|sleep|pain|arthritis|autoimmune|dementia|alzheimer|metabolic|heat shock protein|endorphin|study|trial|evidence|research)\b/gi;
const HEALTH = new RegExp(HEALTH_G.source, 'i');
const SATELLITE = /healthresearchdatabase\.com/i;
/* the other satellites, so "routes somewhere sanctioned" is measured fairly */
const OTHER_SAT = /besthomeinfraredsauna\.com|healthresearchdatabase\.com/i;
const PRIMARY = /pubmed|ncbi\.nlm\.nih\.gov|doi\.org|jamanetwork|nih\.gov|cochrane/i;

const rows = [];
for (const a of arts) {
  const body = String(a.body || '');
  const text = body.replace(/<[^>]+>/g, ' ');
  if (!HEALTH.test(text)) continue;
  HEALTH_G.lastIndex = 0;
  const hits = text.match(HEALTH_G) || [];
  const healthHits = hits.length;
  /* DISTINCT terms is the better signal than raw hits: an article that says
     "recovery" forty times is not the same as one discussing five different
     physiological subjects. A raw count made a fire-pit safety guide look
     health-adjacent. */
  const distinct = new Set(hits.map((h) => h.toLowerCase())).size;
  rows.push({
    handle: a.handle,
    published: a.published,
    healthHits, distinct,
    satellite: SATELLITE.test(body),
    anySatellite: OTHER_SAT.test(body),
    primaryLink: PRIMARY.test(body),
    words: Math.round(text.trim().split(/\s+/).length),
  });
}

const noRoute = rows.filter((r) => !r.anySatellite && !r.primaryLink);
const satelliteOnly = rows.filter((r) => r.satellite);
const primaryOnly = rows.filter((r) => !r.anySatellite && r.primaryLink);

console.log(`health-adjacent articles: ${rows.length} of ${arts.length}\n`);
console.log(`  route to healthresearchdatabase.com : ${satelliteOnly.length}`);
console.log(`  route to a primary source instead   : ${primaryOnly.length}`);
console.log(`  route NOWHERE — no satellite, no primary link : ${noRoute.length}\n`);

console.log('── NO EVIDENCE ROUTE AT ALL, published first, largest first');
for (const r of noRoute.sort((a, b) => (b.distinct - a.distinct) || (b.healthHits - a.healthHits)).slice(0, 30)) {
  console.log(`  ${r.published ? 'LIVE' : 'draft'}  ${String(r.distinct).padStart(2)} distinct / ${String(r.healthHits).padStart(3)} hits  ${String(r.words).padStart(5)}w  ${r.handle}`);
}
if (noRoute.length > 30) console.log(`  … and ${noRoute.length - 30} more`);

fs.writeFileSync(path.join(DATA, 'evidence-routing.json'), JSON.stringify({ _meta: { ran: new Date().toISOString(), rule: 'CLAUDE.md hard rule 4, second half' }, rows, noRoute }, null, 2));
console.log('\nwrote data/evidence-routing.json');
