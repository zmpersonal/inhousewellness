/**
 * Named, re-runnable probes — the ONLY way a derived count enters copy.
 *
 * Instance 28: the claims block tracked five structural fields (set_size, the
 * three prices, draft_count) because they were easy to derive, not because they
 * were what the copy actually claims. Two collections understated a prose count
 * for a full session while drift-check reported "56 clean".
 *
 * Each probe carries its method, so re-derivation is EXACT rather than
 * approximate — the same definition produces the number in the draft and checks
 * it later. Keep this file the single definition; if the spec generator and the
 * drift checker ever hold separate copies they will drift apart (CLAUDE.md 6c).
 */
import { probeText } from './util.js';

const T = 'title-only', B = 'title-or-body';

export const PROBES = {
  publishes_mg_figure:      { m:B, re:/(?:under\s+|below\s+|less than\s+)?\d+(?:\.\d+)?\s*(?:[-–—]\s*\d+(?:\.\d+)?\s*)?(?:mg|milligauss)\b/ },
  states_measure_distance:  { m:B, re:/\d+\s*(?:to|[-–—])\s*\d+\s*inch/ },
  canadian_hemlock:         { m:T, re:/canadian hemlock/ },
  cedar:                    { m:T, re:/\bcedar\b/ },
  spruce:                   { m:T, re:/spruce/ },
  thermo_wood:              { m:T, re:/thermo/ },
  full_spectrum:            { m:T, re:/full[- ]spectrum/ },
  low_emf_tier:             { m:T, re:/low emf/ },
  ultra_low_emf_tier:       { m:T, re:/ultra[- ]?low emf/ },
  near_zero_emf_tier:       { m:T, re:/near[- ]?zero emf/ },
  hybrid:                   { m:T, re:/\bhybrid\b/ },
  inflatable:               { m:T, re:/inflatable/ },
  stainless_steel:          { m:T, re:/stainless steel/ },
  chromotherapy:            { m:B, re:/chromotherap/ },
  bluetooth:                { m:B, re:/bluetooth/ },
  red_light:                { m:B, re:/red light/ },
  chiller:                  { m:B, re:/chiller/ },
  tool_free_assembly:       { m:B, re:/(tool[- ]free|clasp[- ]together|snaps? together)/ },
  names_120v:               { m:B, re:/\b1[12]0\s*v\b/ },
  needs_240v:               { m:B, re:/\b2[24]0\s*v\b/ },
  dedicated_circuit:        { m:B, re:/dedicated (\d+\s*amp\s*)?circuit/ },
  publishes_wavelength_nm:  { m:B, re:/\d{3}\s*nm\b/ },
  /* "person" OR "people" — the probe matched only "person" and missed
     "Spacious Luxury for 5-6 People", understating mande-spa's capacity range.
     Instance 29 again: the exclusion was invisible in the output. */
  capacity_stated:          { m:T, re:/\d{1,2}\s*(?:[-–—]\s*\d{1,2})?\s*[-–—]?\s*(?:person|people)/ },
  wood_burning:             { m:B, re:/wood[- ]?burn/ },
  states_kw_output:         { m:B, re:/\d+(?:\.\d+)?\s*kw\b/ },
  /* Sixth in the exclusion series (16, 24, 27, 29, 30): a "hot or cold" probe
     written with "or" missed "Hot & Cold Temperature Control" and reported 3
     where the title claims 4. The separator is the variable, not the claim. */
  hot_and_cold:             { m:B, re:/(?:hot\s*(?:&|and|or|\/)\s*cold|cold\s*(?:&|and|or|\/)\s*hot)/ },
  /* The Icetubs range never says "chiller" — it says "cooling engine",
     "integrated engine system", "18 kW cooling capacity". A probe for the word
     we happened to use in the title found 0 of 6 and looked like a false claim;
     the claim was true and the vocabulary was ours, not the manufacturer's. */
  integrated_cooling:       { m:B, re:/(chiller|cooling engine|integrated (?:engine|cooling)|cooling capacity)/ },
  /* Category 1, added 2026-09-08: real claims that were sitting unchecked only
     because no probe existed. Wood in the BODY as well as the title — copy
     routinely says "N listings mention Canadian Hemlock", which is title-or-body. */
  canadian_hemlock_either:  { m:B, re:/canadian hemlock/ },
  cedar_either:             { m:B, re:/\bcedar\b/ },
  thermo_wood_either:       { m:B, re:/thermo/ },
  full_spectrum_either:     { m:B, re:/full[- ]spectrum/ },
};

/* Parameterised probes. Written in a claims block as "vendor:Maxxus" or
   "product_type:Infrared Sauna" — structured fields, so exact by construction. */
export const PARAMETERISED = {
  vendor:       (members, arg) => members.filter(p => (p.vendor || '') === arg).length,
  product_type: (members, arg) => members.filter(p => (p.productType || '') === arg).length,
  /* Collection intersection. "Sixty-four are infrared" on /collections/saunas is
     membership of infrared-saunas ∩ saunas — a real, exact method that had no
     probe, so the claim read as unreproducible when it was correct. */
  in_collection: (members, arg) => members.filter(p => (p.collections || []).includes(arg)).length,
};

const titleOf = p => probeText(p.title || '');
const bodyOf  = p => probeText(String(p.descriptionHtml || '').replace(/<[^>]+>/g, ' '));

const matches = (p, x) => p.re.test(p.m === T ? titleOf(x) : `${titleOf(x)} ${bodyOf(x)}`);

/**
 * Run one probe over a product set. Three forms:
 *   "chromotherapy"                  a named regex probe
 *   "vendor:Maxxus"                  a parameterised structured-field probe
 *   "publishes_mg_figure+states_measure_distance"   a COMPOSITION: A AND B
 *
 * Category 2: "six of those 13 say what distance they measure at" is the
 * intersection of two probes over the same set. An intersection is composable,
 * so it is expressible rather than human-verify-only.
 *
 * ⚠️ A COMPOSITION'S VALUE IS VERIFIED; ITS LABEL MAY BE WRONG.
 * Where two different intersections yield the same number, the backfill cannot
 * tell which one the prose means. ultra-low-emf's "six of those 13" is
 * publishes_mg_figure+states_measure_distance and is recorded as
 * states_measure_distance+red_light, which also equals 6. Drift still fires if
 * either value moves, so the check is sound — but do not read a composed entry
 * as authoritative about WHICH claim it tracks.
 *
 * Two heuristics were tried (prefer plain probes; prefer components the page
 * already cites) and a third was deliberately NOT added. Past that point the
 * adjustment stops being principled and becomes tuning until the output looks
 * right, which is how a guard quietly stops meaning anything.
 */
export function runProbe(name, members) {
  if (name.includes('+')) {
    const parts = name.split('+');
    return members.filter(x => parts.every(n => {
      const p = PROBES[n];
      if (!p) throw new Error(`unknown probe "${n}" in composition "${name}"`);
      return matches(p, x);
    })).length;
  }
  if (name.includes(':')) {
    const [fn, ...rest] = name.split(':');
    const f = PARAMETERISED[fn];
    if (!f) throw new Error(`unknown parameterised probe "${fn}"`);
    return f(members, rest.join(':'));
  }
  const p = PROBES[name];
  if (!p) throw new Error(`unknown probe "${name}" — add it to scripts/lib/probes.mjs or mark the claim human-verify-only`);
  return members.filter(x => matches(p, x)).length;
}

/** Candidate compositions: pairwise intersections of probes that fire on this set. */
export function composeCandidates(members) {
  const live = Object.keys(PROBES).filter(n => runProbe(n, members) > 0);
  const out = {};
  for (let i = 0; i < live.length; i++)
    for (let j = i + 1; j < live.length; j++) {
      const name = `${live[i]}+${live[j]}`;
      const v = runProbe(name, members);
      if (v > 0) out[name] = v;
    }
  return out;
}

/** Vendor, productType and sibling-collection values, as parameterised names. */
export function structuredCandidates(members, ownHandle) {
  const out = {};
  for (const v of new Set(members.map(p => p.vendor).filter(Boolean))) out[`vendor:${v}`] = runProbe(`vendor:${v}`, members);
  for (const t of new Set(members.map(p => p.productType).filter(Boolean))) out[`product_type:${t}`] = runProbe(`product_type:${t}`, members);
  const cols = new Set();
  for (const p of members) for (const c of (p.collections || [])) if (c !== ownHandle) cols.add(c);
  for (const c of cols) out[`in_collection:${c}`] = runProbe(`in_collection:${c}`, members);
  return out;
}

/** Every probe's current value for a product set. */
export function runAll(members) {
  const out = {};
  for (const name of Object.keys(PROBES)) out[name] = runProbe(name, members);
  return out;
}

/* ─────────────────────────────────────────────────────────────────────────────
 * EXTRACTORS — scalars, not counts.
 *
 * The count registry above answers "how many members match?". An SEO TITLE
 * mostly asserts something else: a BOUNDARY ("2–8 Person", "$4,940–$26,890",
 * "3kW to 50kW", "Reaching 195°F") or an ENUMERATION ("660nm & 850nm").
 * Those are not counts and cannot be expressed as one, so recording them as
 * counts would have meant recording them wrongly or not at all.
 *
 * A boundary is more fragile than a count in one specific way: a count moves
 * when ANY member appears or disappears, but it moves by one and stays roughly
 * true, whereas a boundary is held by a SINGLE product and is simply false the
 * moment that product goes. That is why every extractor returns its holders —
 * volatility is a property of who holds the edge, not of the number itself.
 * ────────────────────────────────────────────────────────────────────────── */

/** kind: 'min' | 'max' | 'set'. `g` captures the numbers to consider. */
export const EXTRACTORS = {
  capacity_min: { m:T, kind:'min', g:/(\d{1,2})\s*(?:[-–—]\s*(\d{1,2})\s*)?[-–—]?\s*(?:person|people)/gi, part:'lo' },
  capacity_max: { m:T, kind:'max', g:/(\d{1,2})\s*(?:[-–—]\s*(\d{1,2})\s*)?[-–—]?\s*(?:person|people)/gi, part:'hi' },
  max_temp_f:   { m:B, kind:'max', g:/(\d{2,3})\s*°?\s*f\b/gi },
  /* TITLE-ONLY, and this is not a preference. Body kW mentions are routinely
     about a DIFFERENT model: Narvi's 24kW stove carries "The 50kW model takes 5
     boxes" in a stones-bundling note, and "Natural Sauna Rocks" — a bag of
     rocks — mentions 3 kW. Read from bodies, /collections/sauna-heaters spanned
     "3kW to 50kW"; neither end was a heater in the collection. A heater states
     its own output in its title. */
  kw_min:       { m:T, kind:'min', g:/(\d+(?:\.\d+)?)\s*kw\b/gi },
  kw_max:       { m:T, kind:'max', g:/(\d+(?:\.\d+)?)\s*kw\b/gi },
  nm_set:       { m:B, kind:'set', g:/(\d{3})\s*nm\b/gi },
  distance_in_min: { m:B, kind:'min', g:/(\d+)\s*(?:to|[-–—])\s*(\d+)\s*inch/gi, part:'lo' },
  distance_in_max: { m:B, kind:'max', g:/(\d+)\s*(?:to|[-–—])\s*(\d+)\s*inch/gi, part:'hi' },
};

/** Every number one product contributes to an extractor, with the product. */
function contributions(name, members) {
  const e = EXTRACTORS[name];
  if (!e) throw new Error(`unknown extractor "${name}"`);
  const out = [];
  for (const p of members) {
    const text = e.m === T ? titleOf(p) : `${titleOf(p)} ${bodyOf(p)}`;
    for (const m of text.matchAll(e.g)) {
      const lo = parseFloat(m[1]);
      const hi = m[2] != null ? parseFloat(m[2]) : lo;
      const v = e.part === 'hi' ? hi : e.part === 'lo' ? lo : lo;
      if (Number.isFinite(v)) out.push({ v, p });
      if (e.part == null && m[2] != null && Number.isFinite(hi)) out.push({ v: hi, p });
    }
  }
  return out;
}

/** The extractor's value now, or null when nothing in the set publishes one. */
export function runScalar(name, members) {
  const c = contributions(name, members);
  if (!c.length) return null;
  const e = EXTRACTORS[name];
  if (e.kind === 'set') return [...new Set(c.map(x => x.v))].sort((a, b) => a - b);
  return e.kind === 'min' ? Math.min(...c.map(x => x.v)) : Math.max(...c.map(x => x.v));
}

/** Which products hold that value. A boundary held by one product is one
 *  restock away from being false; the caller decides what to do about it. */
export function scalarHolders(name, members) {
  const c = contributions(name, members);
  if (!c.length) return [];
  const e = EXTRACTORS[name];
  if (e.kind === 'set') return c.map(x => x.p);
  const v = e.kind === 'min' ? Math.min(...c.map(x => x.v)) : Math.max(...c.map(x => x.v));
  return [...new Set(c.filter(x => x.v === v).map(x => x.p))];
}
