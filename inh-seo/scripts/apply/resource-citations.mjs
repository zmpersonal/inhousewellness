/**
 * Removes competing-retailer citations from article bodies without leaving the
 * claims unsourced.
 *
 * Two shapes:
 *   CO-CITED  "(Icebound Essentials, 2025; Sun Home Saunas, 2026)"
 *             -> drop the one name. The claim keeps its other source. Pure
 *                deletion, no editorial judgement.
 *   SOLE      "(Sun Home Saunas, 2026)" is the only source.
 *             -> each one is hand-assigned to a disposition below. There is no
 *                automatic rule, because "does this claim need a source at all"
 *                is an editorial question and a regex cannot answer it.
 *
 * Dispositions:
 *   A  category definition or ordinary buyer advice — drop the citation, keep
 *      the claim. Attaching a retailer's name to "a 20-micron filter removes
 *      particles 20 micrometres and larger" is what created the dependency.
 *   B  electrical / code — drop the citation; the section carries one NEC
 *      reference that NAMES the standard and never states its content.
 *   C  (no rows remain) HELD pending a ruling. The eight chest-freezer claims
 *      were C until 8 September 2026; the client ruled CUT, so they are now D.
 *   D  cut the claim. No primary source exists and our own catalogue cannot
 *      carry it (1 of 20 ACTIVE plunges publishes anything like an interval,
 *      and that one is a circulation frequency).
 *   E  our own observation about an evidence gap — drop the citation.
 *   G  a recommendation that is the competitor's, not the category's — cut.
 *
 *   node scripts/apply/resource-citations.mjs <handle>            # dry run
 *   node scripts/apply/resource-citations.mjs <handle> --apply
 */
import fs from 'node:fs';
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { ROOT, parseArgs, banner, logChange, assertWellFormed } from '../lib/util.js';

const flags = parseArgs();
const handle = process.argv[2];
if (!handle || handle.startsWith('--')) { console.error('usage: resource-citations.mjs <handle> [--apply]'); process.exit(1); }
banner('resource-citations', flags);

const BRAND = /Sun\s?Home\s+Saunas?/i;
const CITE = /\([^()]{0,220}?Sun\s?Home\s+Saunas?[^()]{0,220}?,\s*\d{4}\s*\)/gi;

/* Hand-assigned, in the order the citations appear in the body. Keyed by a
   distinctive snippet so a body edit elsewhere cannot silently shift the
   mapping — an index-keyed table would misfile every row after any insertion. */
const PLAN = {
  'cold-plunge-buying-mistakes': [
    ['not designed or certified for human immersion, and using one this way typically voids', 'D'],
    ['ground-fault circuit interrupter that cuts power when it detects leakage current', 'B'],
    ["filter's micron rating describes the minimum particle size", 'A'],
    ['requires a GFCI-protected outlet', 'B'],
    ['Removes visible particles and debris from water as it circulates', 'A'],
    ['Low-maintenance and effective for small home setups', 'A'],
    ['More potent than UV but requires careful integration and venting', 'A'],
    ['provide ongoing antimicrobial protection between filtration cycles', 'A'],
    ['Industry guidance recommends combining UV with a 20-micron mechanical filter', 'G'],
    ['suggests intervals of every 3', 'D'],
    ['using an appliance as a cold plunge typically voids its manufacturer warranty entirely', 'D'],
    ['outlast inflatable liners in outdoor or heavy-use settings', 'A'],
    ['warranty is void the moment the unit is used this way', 'D'],
    ['Voided by use', 'D'],
    ['suggests every 3', 'D'],
    ['commonly cited as suitable for small home cold plunge setups', 'G'],
    ['Using one as a plunge voids the appliance warranty', 'D'],
    ['UV plus a mechanical filter and residual disinfectant', 'G'],
    ['Confirm appropriate electrical supply and GFCI outlet availability', 'B'],
    ['filter replacement, sanitation chemicals, water changes', 'A'],
    ['require careful attention to electrical safety and warranty implications', 'D'],
    ['suggests this interval for UV plus mechanical filter setups', 'D'],
    ['20-micron mechanical filter removes visible particles and debris', 'A'],
    ['UV systems inactivate microbes as water passes through a UV chamber', 'A'],
    ['Ozone provides strong oxidation but requires careful integration', 'A'],
    ['provide residual antimicrobial protection between filter cycles', 'A'],
    ['more portable and affordable but more vulnerable to punctures', 'A'],
    ['need proper bases, drainage, and GFCI-protected electrical connections', 'B'],
    ['Chest freezers are not designed or certified for human immersion', 'D'],
    ['Using a freezer as a cold plunge typically voids the manufacturer warranty', 'D'],
    ['Skimping on filtration creates health risks', 'A'],
    ['Overlooking warranty fine print on outdoor use', 'A'],
    ['Include filter replacement and sanitation chemical costs', 'A'],
    ['standard safety requirement for any powered equipment installed near water', 'B'],
    ['Rinse or replace the mechanical filter on the manufacturer', 'A'],
    ['Perform full water changes approximately every 3', 'D'],
    ['is not available in the research literature', 'E'],
    ['remains an evidence gap', 'E'],
  ],
  'cold-plunge-maintenance-tips': [
    ['run filtration continuously or on automated schedules, reducing manual effort', 'A'],
  ],
  /* Cited to a competitor for a judgement drawn from our OWN catalogue: cold
     plunges start at $760 here and saunas at $1,999. Nothing about it needed an
     outside source, least of all a competing retailer's. */
  'sauna-vs-cold-plunge-vs-red-light-therapy': [
    ['cold plunge offers the most budget-friendly entry point', 'A'],
  ],
};

const q = await gql('query($h:String!){articles(first:5,query:$h){nodes{id handle title body}}}', { h: `handle:${handle}` });
const art = q.articles.nodes.find((a) => a.handle === handle);
if (!art) { console.error(`no article "${handle}"`); process.exit(1); }
let body = art.body;

const plan = PLAN[handle] || [];
const hits = [...body.matchAll(CITE)];
console.log(`  ${hits.length} citation(s) naming the brand: ${hits.filter(m => /;/.test(m[0])).length} co-cited, ${hits.filter(m => !/;/.test(m[0])).length} sole-source\n`);

const text = (i) => body.slice(0, i).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
const edits = [];
for (const m of hits) {
  const co = /;/.test(m[0]);
  if (co) { edits.push({ i: m.index, len: m[0].length, kind: 'CO-CITED', was: m[0] }); continue; }
  /* Match on the text IMMEDIATELY before this citation, not on everything
     before it. Matching the whole prefix filed all 38 under the first row in
     the table — a silent, total misassignment that looked like a clean run.
     Same shape as every other partial-match failure on this project, caught
     only because "38 of 38 are disposition C" was obviously wrong. */
  const pre = text(m.index);
  const win = pre.slice(-260);
  let row = null, at = -1;
  for (const r of plan) { const k = win.lastIndexOf(r[0]); if (k > at) { at = k; row = r; } }
  if (!row) { edits.push({ i: m.index, len: m[0].length, kind: 'UNASSIGNED', was: m[0], claim: pre.slice(-110) }); continue; }
  row[2] = (row[2] || 0) + 1;
  edits.push({ i: m.index, len: m[0].length, kind: row[1], was: m[0], claim: pre.slice(-110) });
}

const unassigned = edits.filter((e) => e.kind === 'UNASSIGNED');
if (unassigned.length) {
  console.error(`REFUSING — ${unassigned.length} sole-source citation(s) have no disposition. A citation nobody assigned is not a citation to delete on a guess:\n`);
  unassigned.forEach((e) => console.error(`  ...${e.claim}\n     ${e.was}\n`));
  process.exit(1);
}

/* Every hand-written row must be used exactly once. A row matching zero
   citations means the table is stale; a row matching several means the snippet
   is not distinctive. Both are silent misassignment, so both refuse. */
const misused = plan.filter((r) => (r[2] || 0) !== 1);
if (misused.length) {
  console.error(`REFUSING — ${misused.length} plan row(s) did not match exactly one citation:\n`);
  misused.forEach((r) => console.error(`  matched ${r[2] || 0}x  [${r[1]}]  "${r[0]}"`));
  process.exit(1);
}

const tally = {};
edits.forEach((e) => { tally[e.kind] = (tally[e.kind] || 0) + 1; });
console.log('  dispositions: ' + Object.entries(tally).sort().map(([k, v]) => `${k}=${v}`).join('  ') + '\n');

/* Apply from the END so earlier indices stay valid. */
const removedClaims = [];
for (const e of [...edits].sort((a, b) => b.i - a.i)) {
  if (e.kind === 'C') continue;                                  // held
  if (e.kind === 'CO-CITED') {
    const inner = e.was.slice(1, -1);
    const kept = inner.split(';').map((s) => s.trim()).filter((s) => !BRAND.test(s));
    const repl = kept.length ? `(${kept.join('; ')})` : '';
    body = body.slice(0, e.i) + repl + body.slice(e.i + e.len);
    continue;
  }
  if (e.kind === 'A' || e.kind === 'B' || e.kind === 'E') {
    /* drop the citation and the space before it; keep the claim */
    let start = e.i; while (start > 0 && /\s/.test(body[start - 1])) start -= 1;
    body = body.slice(0, start) + body.slice(e.i + e.len);
    continue;
  }
  /* D and G: cut the whole claim. Walk back to the start of the sentence or
     list item, never past a tag boundary. */
  const before = body.slice(0, e.i);
  const cut = Math.max(before.lastIndexOf('. '), before.lastIndexOf('> '), before.lastIndexOf('>'), before.lastIndexOf(': '));
  let start = cut >= 0 ? cut + (before[cut] === '>' ? 1 : 2) : e.i;
  let stop = e.i + e.len;
  /* Take the sentence's closing punctuation with it. Left behind, it becomes a
     list item containing a lone full stop — invisible in a word count and
     visible on the page. */
  const tail = body.slice(stop).match(/^\s*[.;,]/);
  if (tail) stop += tail[0].length;

  /* If removing the sentence leaves its element holding nothing but the label
     that introduced it, take the element too. "Verify a filtration and
     sanitation plan: UV plus a mechanical filter and residual disinfectant"
     became "Verify a filtration and sanitation plan: ." — a fragment that reads
     as deliberate and is worse than either keeping or removing the whole item.
     Scoped to the element actually being cut: a global sweep for dangling
     labels also deleted "Electrical:" and "Before committing, confirm:", which
     are lead-ins to lists and entirely intact. */
  const openIdx = Math.max(before.lastIndexOf('<li'), before.lastIndexOf('<p'));
  if (openIdx >= 0) {
    const tag = body.slice(openIdx).match(/^<(li|p)\b/i)?.[1];
    const openEnd = body.indexOf('>', openIdx) + 1;
    const closeIdx = body.toLowerCase().indexOf(`</${tag}>`, e.i);
    if (tag && closeIdx > 0 && openEnd <= start) {
      const rest = (body.slice(openEnd, start) + body.slice(stop, closeIdx))
        .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
      if (rest === '' || /^[A-Za-z][A-Za-z ,'\u2019-]{0,70}:\s*[.;,]?$/.test(rest)) {
        start = openIdx; stop = closeIdx + tag.length + 3;
      }
    }
  }
  removedClaims.push({ kind: e.kind, text: body.slice(start, stop).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() });
  body = body.slice(0, start) + body.slice(stop);
}

/* Three cuts emptied their list item without the enclosing check firing. An
   element whose inner HTML is pure whitespace — no text, no tags, not even an
   image — is never intentional, and this narrow form cannot touch the lead-in
   labels the earlier broad sweep wrongly deleted. The BEFORE body contains zero
   of these, which is the assertion below. */
const EMPTY = /<(li|p)\b[^>]*>\s*<\/\1>/gi;
const emptiedBefore = (art.body.match(EMPTY) || []).length;
let emptied = 0;
/* Only when a claim was actually cut. dry-sauna-for-home carries 14 pre-existing
   empty elements and needs only co-cited deletions; sweeping there would tidy
   markup this edit never touched, which is scope creep with a cleanup badge. */
if (removedClaims.length) {
  const now = (body.match(EMPTY) || []).length;
  if (now <= emptiedBefore) { emptied = 0; }
  else if (emptiedBefore > 0) { console.error(`REFUSING — the ORIGINAL body already has ${emptiedBefore} empty element(s), so this sweep cannot tell mine from theirs.`); process.exit(1); }
  else { emptied = now; body = body.replace(EMPTY, ''); }
}

/* A cut inside a comparison table leaves an EMPTY CELL. The columns do not
   shift — the <td> survives — but a blank cell in a three-way comparison reads
   as "we have nothing to say about this option", which is a gap in the argument
   rather than a removed claim. Named per article, because what belongs in the
   cell is an editorial decision and not something to generate. */
const CELL_REPAIRS = {
  'cold-plunge-buying-mistakes': [
    { after: '<p>Warranty</p>', fill: 'Check the appliance warranty',
      why: 'The cut claim was "Voided by use". The replacement is an instruction rather than an assertion, because we have no primary source for what any given freezer warranty says.' },
  ],
};
const repairs = [];
for (const r of CELL_REPAIRS[handle] || []) {
  const at = body.indexOf(r.after);
  if (at < 0) continue;
  /* the next <td> after the row label, if a cut left it empty */
  const re = /<td[^>]*>\s*<\/td>/;
  const seg = body.slice(at, at + 600);
  const m = seg.match(re);
  if (!m) continue;
  const abs = at + seg.indexOf(m[0]);
  body = body.slice(0, abs) + m[0].replace('</td>', `\n<p>${r.fill}</p>\n</td>`) + body.slice(abs + m[0].length);
  repairs.push(r);
}
if (repairs.length) { console.log('\n  table cells refilled after a cut (a blank cell is a gap in the argument, not a removed claim):'); repairs.forEach((r) => console.log(`    "${r.fill}"  — ${r.why}`)); }

/* A cut can orphan the phrase that INTRODUCED it. "Chest freezer conversions
   present a clear example: <cut> Purpose-built units are designed for..." now
   promises an example and delivers a different sentence. The element is not
   empty, so the emptied-element sweep cannot see it. Named per article, because
   whether a lead-in still earns its place is an editorial judgement. */
const ORPHANED_LEADINS = {
  'cold-plunge-buying-mistakes': [
    { text: 'Chest freezer conversions present a clear example: ',
      why: 'introduced the chest-freezer warranty claim, which the client ruled CUT. Nothing follows it now.' },
  ],
};
const leadins = [];
for (const o of ORPHANED_LEADINS[handle] || []) {
  if (!body.includes(o.text)) continue;
  body = body.split(o.text).join('');
  leadins.push(o);
}
if (leadins.length) { console.log('\n  orphaned lead-in(s) removed (a cut is two edits, not one):'); leadins.forEach((o) => console.log(`    "${o.text.trim()}"  — ${o.why}`)); }

/* B: one NEC reference in the article, naming the standard and never its text. */
const NEC = '<p><strong>On electrical work:</strong> NEC Article 680 covers electrical requirements for pools, spas and hot tubs. Check the current edition against your local code, and have a licensed electrician confirm the circuit before the tub is filled.</p>';
let necAdded = false;
if ((tally.B || 0) > 0 && !body.includes('NEC Article 680')) {
  const anchor = body.search(/<h2[^>]*>[^<]*(?:Electric|Electrical|Power|Install)[^<]*<\/h2>/i);
  if (anchor >= 0) { const end = body.indexOf('</h2>', anchor) + 5; body = body.slice(0, end) + '\n' + NEC + body.slice(end); }
  else { body += '\n' + NEC; }
  necAdded = true;
}

console.log('  claims CUT (D and G — no primary source, and our own catalogue cannot carry them):');
removedClaims.reverse().forEach((r) => console.log(`    [${r.kind}] ${r.text.slice(0, 130)}`));
if (emptied) console.log(`\n  emptied element(s) removed after a cut: ${emptied}`);
console.log(`\n  NEC reference added: ${necAdded ? 'yes, named and not quoted' : 'no'}`);
const left = [...body.matchAll(CITE)].length;
console.log(`  brand citations remaining: ${left}   (all disposition C, held)`);
console.log(`  body ${art.body.length} -> ${body.length} chars`);
const cnt = (s) => (s.match(/href="[^"]*\/products\//gi) || []).length;
console.log(`  product links ${cnt(art.body)} -> ${cnt(body)}`);
if (cnt(art.body) !== cnt(body)) { console.error('REFUSING — product link count moved.'); process.exit(1); }

const dir = path.join(ROOT, 'data', 'citation-edit');
fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, `${handle}.before.html`), art.body);
fs.writeFileSync(path.join(dir, `${handle}.after.html`), body);
console.log(`\n  wrote data/citation-edit/${handle}.{before,after}.html`);

assertWellFormed(body, `${handle} body`, art.body);

if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
const r = await gql('mutation($id:ID!,$b:HTML!){articleUpdate(id:$id,article:{body:$b}){article{id}userErrors{field message}}}', { id: art.id, b: body });
if (r.articleUpdate.userErrors.length) { console.error(r.articleUpdate.userErrors); process.exit(1); }
logChange({ script: 'resource-citations', kind: 'article', id: art.id, handle, field: 'body', before: `${art.body.length} chars, ${hits.length} brand citations`, after: `${body.length} chars, ${left} held` });
console.log(`  updated ${art.id}`);
