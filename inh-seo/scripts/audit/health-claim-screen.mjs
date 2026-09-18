/**
 * Finds physiological claims asserted as fact in article bodies.
 *
 * Hard rule 4: no health claim. The test is not "does the word inflammation
 * appear" — it is "does this sentence say a sauna DOES something to a body,
 * without a hedge, outside a debunk".
 *
 * The earlier pass over-fired badly: "prevent mold", "prevent structural
 * damage", and sentences whose whole purpose was to knock a claim down
 * ("detoxification claims are overstated"). Counting those as violations makes
 * the screen useless, because a reader stops trusting it.
 *
 * Three gates, all required:
 *   1. a SUBJECT that is the heat, not the room  (sauna, infrared, heat, sweating)
 *   2. a VERB of effect on a BODILY object       (improves circulation, not prevents mold)
 *   3. NO hedge and NO debunk frame in the sentence
 *
 * Validated against a known positive before it is trusted (instance 40).
 */
import path from 'node:path';
import { readJSON, DATA } from '../lib/util.js';

const SUBJECT = /\b(saunas?|sauna use|sauna sessions?|infrared|far[- ]infrared|heat exposure|heat therapy|sweating|thermal stress|cold plunge|cold water immersion|red light(?: therapy)?)\b/i;
const VERB = /\b(improves?|increases?|reduces?|lowers?|boosts?|enhances?|strengthens?|burns?|detoxif\w+|heals?|cures?|treats?|relieves?|prevents?|promotes?|triggers?|delivers?|produces?|flushes?|eliminates?)\b/i;
/* the object has to be a BODY, which is what separates a health claim from
   "prevents mold" and "reduces operating cost" */
const BODY = /\b(circulation|blood pressure|blood flow|inflammation|immunity|immune|toxins?|calories?|pain|soreness|recovery|heart|cardiovascular|cardiac|metabolism|metabolic|cholesterol|anxiety|depression|sleep|muscle|joints?|skin|detox\w*|longevity|lifespan|healthspan|weight|stress hormones?|cortisol|blood sugar|glucose|arteries|vascular|endothelial)\b/i;
const HEDGE = /\b(may|might|could|can\b|associated with|evidence|studies|study|research|linked|potential\w*|suggests?|appears?|some people|in (?:one|a) (?:trial|study)|reported|observational|preliminary|limited|mixed|not proven|unclear)\b/i;
const DEBUNK = /\b(does not|do not|don't|doesn't|no evidence|not show|overstated|myth|misconception|claims? (?:are|is)|is not|are not|rather than|instead of|contrary to|little evidence|weak evidence)\b/i;

/* Not prose: table-of-contents runs, heading stacks, and bibliography lines all
   match SUBJECT+VERB+BODY and none of them asserts anything. A screen that
   counts them trains the reader to skim it. */
const NOT_PROSE = [
  /Table of Contents/i,
  /https?:\/\//,                              // a citation line
  /\b(?:PubMed|PMC|NCBI|doi)\b[^.]{0,40}\d{4}/i,
  /\?\s*$/,                                   // an FAQ question, not a claim
  /\bvs\.?\s/i,                               // heading stacks: "Traditional vs. Infrared ..."
];
/* A contrastive clause is the sentence qualifying itself: "sweat contains trace
   metals BUT most detoxification occurs in the liver" is the article being
   careful, not the article claiming. */
const CONTRAST = /(?:—|,|\s)but\s|however|although|whereas|rather than|not because/i;

/* ---- EXEMPT BY KIND (client ruling, 9 September 2026) ----
   Rule 4 governs claims of BENEFIT. Two shapes are the rule working rather than
   exceptions to it, and hedging either makes the copy worse:

     WARNING     — tells the reader a harm follows from use or misuse
     CORRECTION  — quotes a false claim in order to knock it down

   The test is what the sentence DOES. A benefit claim does not become exempt by
   containing the word "risk", so the warning test requires BOTH an instruction
   or risk framing AND a named physical harm — burns, arrhythmia, hypothermia —
   never a wellness outcome inverted ("skipping sauna increases your risk of
   poor recovery" stays in scope). */
const HARM = /\b(dehydration|arrhythmias?|hypotension|hypothermia|hyperthermia|fainting|faint|burns?|scald|overheating|heat ?stroke|electrocution|shock|drowning|death|die|injur\w+|nausea|dizz\w+|seizure|cardiac (?:event|arrest)|sudden death|miscarriage)\b/i;
const WARNING_FRAME = /\b(should (?:be )?avoid|avoid\b|do not\b|don't\b|never\b|caution|be careful|seek medical|consult (?:a|your) (?:doctor|physician)|contraindicat\w+|safety risk|risk of|increases? (?:the )?risks?|not recommended|stop (?:using|immediately)|exit (?:the sauna|immediately))\b/i;
/* A following sentence that supplies the limitation: design, population scope,
   or an explicit refusal to generalise. Deliberately narrow — a vague "more
   research is needed" does not count. */
const LIMITATION_FOLLOWS = /\b(observational|not random(?:ly|ised|ized)|association rather than cause|shows association|cannot establish|self[- ]selection|cohort of|clinical population|do(?:es)? not transfer|acute responses|not an outcome of|what the term denotes|separate question|trials reviewed|have not read|preclinical|in (?:mice|rats|cell))\b/i;
const CORRECTION_FRAME = /(^|\s)(Correction:|Myth:|Reality:|Assuming\b|Believing\b)|\b(?:is|are) (?:overstated|a myth|not supported|unsupported)\b|\bcorrection\b/i;

/** A sentence exempt by kind, with the kind named so the log can show its work. */
export function exemptKind(s) {
  if (CORRECTION_FRAME.test(s)) return 'correction';
  if (WARNING_FRAME.test(s) && HARM.test(s)) return 'warning';
  return null;
}

/* ---- PROPERTY CLAIMS: a second class, with no verb and no object ----
   `finnmark-fd-4` carried "healing steam", "antimicrobial cedar" and
   "medical-grade Spectrum Red Light" and the screen saw none of them, because
   the subject-verb-body test is built for "X does Y to your body". An ADJECTIVE
   asserting a therapeutic property is the same violation with the grammar
   removed, and it is how supplier copy usually phrases it.

   Brand names collide badly here: Medical Saunas and Medical Breakthrough are
   VENDORS, Dynamic Cold Therapy is a vendor, and red light therapy and
   chromotherapy are product categories. A term inside one of those is not a
   claim, so the phrase is checked against a brand and category list before it
   counts. */
const PROPERTY = /\b(healing|therapeutic|medical[- ]grade|hospital[- ]grade|pharmaceutical[- ]grade|clinical[- ]grade|antimicrobial|anti[- ]?bacterial|anti[- ]?fungal|anti[- ]?inflammatory|purifying|detoxifying|rejuvenating|restorative|curative|remedial|immune[- ]boosting|health[- ]boosting|clinically proven|doctor[- ]recommended|FDA[- ]approved)\b/gi;
/* Brand, vendor and category strings in which these words are names, not claims. */
const NOT_A_CLAIM_IN = [
  /Medical Saunas?/i, /Medical Breakthrough/i, /Dynamic Cold Therapy/i, /Health Smart/i,
  /red light therapy/i, /chromotherapy/i, /floatation therapy/i, /cold therapy/i,
  /heat therapy/i, /infrared therapy/i, /therapy (?:panel|tower|room|mat|lamp)/i,
];

/* A property term is not a claim when the copy is DENYING it. Every one of the
   15 "FDA-approved" and "clinically proven" hits in the article estate turned
   out to be a negation — "devices are not FDA-approved", "Avoid: 'clinically
   proven'", "Myth: … Correction:". Counting those would have reported the
   articles doing exactly the right thing as the most serious finding in the
   sweep. Negation is checked in the 46 characters BEFORE the term, where a
   denial actually sits, rather than anywhere in the sentence. */
const DENIED = /\b(not|aren'?t|isn'?t|never|no|avoid|rather than|instead of|premature|questionable|unless)\b[^.]{0,46}$/i;

/** Property-claim phrases in a text, with brand collisions and denials removed. */
export function propertyClaims(text) {
  const out = [];
  for (const m of text.matchAll(PROPERTY)) {
    const window = text.slice(Math.max(0, m.index - 34), m.index + m[0].length + 34);
    if (NOT_A_CLAIM_IN.some((re) => re.test(window))) continue;
    if (DENIED.test(text.slice(Math.max(0, m.index - 46), m.index))) continue;
    /* "Myth: X … Correction:" — the term is quoted in order to be knocked down */
    const around = text.slice(Math.max(0, m.index - 160), m.index + m[0].length + 200);
    if (/\b(Myth|Correction|Myths?:)\b/i.test(around)) continue;
    out.push({ term: m[0], context: text.slice(Math.max(0, m.index - 70), m.index + m[0].length + 70).trim() });
  }
  return out;
}

export function screen(text) {
  const out = [];
  /* split on sentence ends that are followed by a capital, so "1.5 in." survives */
  const sentences = text.split(/(?<=[.!?])\s+(?=[A-Z"“])/);
  for (let i = 0; i < sentences.length; i++) {
    const s = sentences[i];
    if (s.length < 40 || s.length > 400) continue;
    if (NOT_PROSE.some((re) => re.test(s))) continue;
    if (!BODY.test(s) || HEDGE.test(s) || DEBUNK.test(s) || CONTRAST.test(s)) continue;
    if (exemptKind(s)) continue;                       // a warning or a correction
    /* A myth is usually quoted in one sentence and knocked down in the next.
       Judging the quote alone flags the article for repeating the claim it
       exists to correct. Look one sentence ahead. */
    if (sentences[i + 1] && CORRECTION_FRAME.test(sentences[i + 1])) continue;
    /* Rule 4 as amended asks a cited finding to carry its population AND its
       limitation. The limitation is usually the NEXT sentence — that is exactly
       the shape the Tier B pass applied. Judging the finding alone reports the
       compliant form as a violation, which would make the screen argue against
       its own remedy. */
    if (sentences[i + 1] && LIMITATION_FOLLOWS.test(sentences[i + 1])) continue;
    /* the subject must be doing the verb, not merely present in the same
       paragraph: require them within 80 characters of each other */
    const sub = s.match(SUBJECT); if (!sub) continue;
    const verbNear = new RegExp(VERB.source, 'i').exec(s.slice(Math.max(0, sub.index - 80), sub.index + sub[0].length + 80));
    if (!verbNear) continue;
    out.push(s.trim());
  }
  return out;
}

const arts = readJSON(path.join(DATA, 'content.json')).articles || [];
const strip = (a) => String(a.bodyHtml || a.body || '')
  .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&#39;|&rsquo;/g, "'").replace(/\s+/g, ' ');

/* ---- VALIDATION, before any count is trusted ----
   The fixture is SYNTHETIC on purpose. It was originally the real opening line
   of how-saunas-improve-circulation; fixing that article deleted the sentence
   the screen validated against, and the screen then refused to run for ever.
   A guard anchored to live content stops working the moment the content is
   corrected — which is exactly when you most want it running. */
const POSITIVE = 'Saunas improve circulation primarily through heat-driven vasodilation, which increases blood flow.';
const NEGATIVES = [
  'Indoor installations demand vapor barriers and ventilation to prevent mold; outdoor units need weatherproof construction.',
  'Men using saunas 4-7 times per week had lower cardiac mortality (Laukkanen et al., 2015), an observational cohort that cannot establish cause.',
  'Detoxification claims are overstated, and the evidence does not show dramatic outcomes for sweat-based toxin removal.',
  /* exempt by kind — a warning and a correction */
  'Alcohol should be avoided before or during sauna use because it increases risks of dehydration, low blood pressure, arrhythmias, and even death in extreme cases.',
  'All saunas burn large numbers of calories and are good for weight loss. Correction: most immediate weight loss in saunas is fluid, not fat.',
  // 18i: proves the limitation lookahead — the finding's limitation arrives in the NEXT sentence
  'Saunas improve circulation through heat-driven vasodilation, which increases blood flow. That finding comes from an observational cohort of Finnish men.',
  // 18i: proves the 80-character subject-verb proximity — "sauna" and "improves" are over 80 characters apart
  'Our sauna ships flat-packed with cedar benches, tempered glass, a wall-mounted control panel, two speaker grilles and a printed manual that improves circulation of warm air.',
  /* NOT exempt — a benefit claim wearing a warning's clothes. Must still fire. */
];
const STILL_FIRES = 'Skipping your sauna increases the risk that your circulation and recovery decline over time.';
let validated = screen(POSITIVE).length === 1;
console.log(`  known positive  synthetic assertion: probe ${validated ? 'FIRES' : 'DOES NOT FIRE — BAD'}`);
const LABELS = ['prevent mold', 'cited + limited study result', 'a debunk', 'a safety warning (exempt by kind)', 'a myth + its correction (exempt by kind)',
  'a finding + its limitation in the next sentence', 'subject and verb over 80 characters apart'];
NEGATIVES.forEach((n, i) => {
  const q = screen(n).length === 0;
  console.log(`  known negative  ${LABELS[i]}: probe ${q ? 'stays silent' : 'FIRES — BAD'}`);
  if (!q) validated = false;
});
const wolf = screen(STILL_FIRES).length === 1;
console.log(`  known positive  benefit claim in warning's clothes: probe ${wolf ? 'FIRES' : 'DOES NOT FIRE — the exemption is too wide'}`);
if (!wolf) validated = false;
/* 18i: proves both lookaheads are narrow — a claim followed by an UNRELATED sentence must still
   fire. Every earlier fixture was a single sentence, so "skip whenever a next sentence exists"
   passed them all. */
const FOLLOWED = 'Saunas improve circulation through heat-driven vasodilation, which increases blood flow. The cabin ships in four boxes and assembles in an afternoon.';
const followed = screen(FOLLOWED).length === 1;
console.log(`  known positive  claim followed by an unrelated sentence: probe ${followed ? 'FIRES' : 'DOES NOT FIRE — a lookahead is excusing any next sentence'}`);
if (!followed) validated = false;
if (!validated) { console.error('\nREFUSING to report a count from a probe that failed validation.'); process.exit(1); }

console.log(`\nhealth-claim-screen — ${arts.length} articles in data/content.json\n`);
const rows = [];
for (const a of arts) {
  const hits = screen(strip(a));
  if (hits.length) rows.push({ handle: a.handle, title: a.title, hits });
}
rows.sort((x, y) => y.hits.length - x.hits.length);
for (const r of rows) {
  console.log(`  ${r.handle}   ${r.hits.length} claim(s)`);
  r.hits.slice(0, 4).forEach((s) => console.log(`      ⚠ ${s.slice(0, 175)}`));
}
console.log(`\n${rows.length} of ${arts.length} articles carry a physiological claim asserted as fact.`);
console.log(`${rows.reduce((n, r) => n + r.hits.length, 0)} sentences total.`);
