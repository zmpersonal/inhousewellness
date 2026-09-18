/**
 * INBOUND-REFERENCE SWEEP — the third defect class with US as the mechanism.
 *
 * A claim can be corrected at source and left standing in another page's prose
 * or link text. The german-sauna case: we changed the title of
 * how-saunas-improve-circulation on 9 September and left "how saunas improve
 * circulation" as the anchor text on the highest-impression article in the
 * flagged set. The assertion we removed is still on the site, in our voice.
 *
 * A RENAME IS A MECHANISM CHANGE AND LINK TEXT IS PROSE DESCRIBING IT.
 *
 * This is read-only. It never writes.
 *
 * The register below is HAND-DECLARED, not derived. A derived list would be
 * built from data/changelog.jsonl, and the changelog is exactly what missed
 * this: the how-saunas-improve-circulation title change has NO changelog row.
 * Deriving the register from the log would have reproduced the omission.
 *
 *   node scripts/audit/stale-references.mjs
 *   node scripts/audit/stale-references.mjs --self-test
 */
import fs from 'node:fs';
import path from 'node:path';
import { DATA, REPORTS } from '../lib/util.js';

const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

/* SCOPE LIMIT, and it is a real gap — recorded rather than hidden.
   ---------------------------------------------------------------------------
   This register carries claims we CORRECTED. It does not carry figures we
   RESTATED. A page that quotes another page's number is depending on it, and
   nothing tracks that dependency.
   
   Live example: `indoor-sauna` says "55 of 91 units run on a standard 120V
   circuit" — a figure quoted from `infrared-saunas`, which was rewritten to
   "most" and whose set size is now 90. Instance 53 in miniature, and this sweep
   did not catch it because nobody CORRECTED the 55; we simply stopped saying it.
   
   WHY IT IS NOT SIMPLY ADDED HERE. A cross-page figure reference is not a
   string this register can hold, because the stale form is not knowable in
   advance — it is any number on page A that was derived from page B. Detecting
   it needs the OTHER shape of check: re-derive every figure and compare, which
   is what `drift-check` and `seo-field-drift` already do, per page.
   
   THE GAP IS THE JOIN. `drift-check` re-derives a page's OWN claims block. It
   has no notion that `indoor-sauna`'s prose contains a figure belonging to
   `infrared-saunas`. The fix is a `cites:` block in the front matter — "this
   figure is <name> on <handle>" — so drift-check can re-derive it from the
   SOURCE collection rather than from this one. Costed and deferred; see BACKLOG.
   
   Until then: when a figure in one page's copy comes from another page, put it
   in that page's `claims:` block anyway, keyed to the source handle. A figure
   with no method attached is the thing rule 6c exists to prevent, and a figure
   borrowed from another page has a method — it is just someone else's. */

/* Each entry: something this project changed AT SOURCE, and the wording that
   would now be stale anywhere else. `re` is matched against decoded text. */
const CORRECTIONS = [
  { id: 'circulation-title', kind: 'article title',
    target: 'how-saunas-improve-circulation',
    was: 'The Science of Heat: How Saunas Improve Circulation and Cardiovascular Health',
    now: 'Sauna Temperature, Session Length, and What the Circulation Research Actually Shows',
    when: '2026-09-09',
    re: /saunas?\s+(?:improve|improves|boost|boosts)\s+(?:your\s+)?(?:circulation|blood\s+flow)/gi },

  { id: 'circulation-lead', kind: 'body claim (cut)',
    target: 'how-saunas-improve-circulation',
    was: 'Saunas improve circulation primarily through heat-driven vasodilation',
    when: '2026-09-09',
    re: /heat[- ]driven\s+vasodilation|the\s+two\s+ways\s+saunas\s+boost\s+blood\s+flow/gi },

  { id: 'immune-boost', kind: 'body claim (cut)',
    target: 'plunge-immune-function',
    was: 'boost immune system functioning',
    when: '2026-09-09',
    re: /boosts?\s+(?:your\s+)?immun\w*|immune[- ]system\s+boost|boosts?\s+immunity/gi },

  { id: 'scandia-collections', kind: 'collection title',
    target: 'scandia-manufacturing',
    was: 'Scandia Manufacturing',
    now: 'Scandia Sauna Heaters',
    when: '2026-09-07',
    re: /Scandia\s+Manufacturing/gi },

  { id: 'alzheimers-clause', kind: 'body claim (hedged)',
    target: 'sauna-alzheimers',
    was: 'sauna improves some measures of blood-vessel function ... cardiovascular health is tied to dementia risk',
    when: '2026-09-09',
    re: /sauna\s+(?:use\s+)?(?:reduces?|lowers?|cuts?)\s+(?:the\s+)?(?:risk\s+of\s+)?(?:alzheimer|dementia)/gi },

  { id: 'sunlighten-pricing', kind: 'finding corrected (instance 36)',
    target: 'sunlighten-saunas-review',
    was: 'Sunlighten gates all pricing behind a consultation',
    now: 'shop-us.sunlighten.com publishes 111 of 111 prices',
    when: '2026-09-09',
    re: /Sunlighten[^.]{0,120}(?:does\s+not|doesn.t|won.t|refuses?\s+to)\s+publish[^.]{0,40}pric/gi },

  { id: 'named-health-terms', kind: 'product claim terms (cut catalogue-wide)',
    target: '(673 products)',
    was: 'detoxif*, boosts immunity, burns calories, reduces inflammation as assertion',
    when: '2026-09-09',
    re: /\b(?:detoxifies|detoxification\s+(?:occurs|happens)|burns?\s+\d+\s*(?:to|-|–)?\s*\d*\s*calories)\b/gi },
];

/* Decode before matching — limits and matches apply to what a person reads. */
const decode = (s) => s
  .replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—');

const strip = (s) => decode(s).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

/* Anchors are pulled separately from prose: an anchor repeating a corrected
   claim is worse than the same words in a sentence, because it is a promise
   about the destination as well as an assertion. */
const ANCHOR = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;

function surfaces() {
  const content = readJSON(path.join(DATA, 'content.json'));
  const collections = readJSON(path.join(DATA, 'collections.json'));
  const out = [];
  for (const a of content.articles) out.push({ kind: 'article', handle: a.handle, title: a.title, html: a.body || '' });
  for (const p of content.pages) out.push({ kind: 'page', handle: p.handle, title: p.title, html: p.body || p.bodyHtml || '' });
  for (const c of collections) out.push({ kind: 'collection', handle: c.handle, title: c.title, html: c.descriptionHtml || '' });
  return out;
}

function scan(rows) {
  const hits = [];
  for (const s of rows) {
    const text = strip(s.html);
    const anchors = [];
    let m;
    ANCHOR.lastIndex = 0;
    while ((m = ANCHOR.exec(s.html))) anchors.push({ href: m[1], text: strip(m[2]).trim() });

    for (const c of CORRECTIONS) {
      /* self-reference is not a stale reference: the page that was corrected
         may legitimately still discuss the thing it corrected */
      const selfRef = s.handle === c.target;

      c.re.lastIndex = 0;
      let mm;
      while ((mm = c.re.exec(text))) {
        const i = mm.index;
        hits.push({
          correction: c.id, where: 'prose', kind: s.kind, handle: s.handle,
          selfRef, match: mm[0],
          context: text.slice(Math.max(0, i - 130), i + mm[0].length + 130).trim(),
        });
      }
      for (const a of anchors) {
        c.re.lastIndex = 0;
        if (c.re.test(a.text)) {
          hits.push({
            correction: c.id, where: 'ANCHOR', kind: s.kind, handle: s.handle,
            selfRef, match: a.text, href: a.href,
            pointsAtTarget: a.href.includes('/' + c.target),
          });
        }
      }
    }
  }
  return hits;
}

const rows = surfaces();

/* Round 18i: the fixtures run on EVERY invocation, not only under --self-test — a normal run
   whose register cannot fire must not print a clean sweep. --self-test stops after them. */
{
  /* SYNTHETIC. The first version of this test asserted that the probe finds the
     german-sauna anchor in the LIVE estate. It passed, the anchor was fixed the
     same day, and the test then FAILED — the guard died at the moment its
     subject was repaired, which is the live-anchor rule this repo already
     carries, reproduced by the author of the fix hours after writing it down.

     These fixtures are constructed and immune to any edit in the estate. The
     first two are the shapes that motivated the script; the last three are the
     ones a careless pattern would over-fire on. */
  const FIXTURES = [
    { name: 'stale anchor repeating a corrected claim',
      row: { kind: 'article', handle: 'fixture-a', title: 'A',
             html: '<p>it helps to understand <a href="/blogs/saunas/how-saunas-improve-circulation">how saunas improve circulation</a> first.</p>' },
      correction: 'circulation-title', where: 'ANCHOR', expect: true },
    { name: 'same claim in prose with no link',
      row: { kind: 'article', handle: 'fixture-b', title: 'B',
             html: '<p>Everyone knows saunas improve circulation.</p>' },
      correction: 'circulation-title', where: 'prose', expect: true },
    { name: 'the corrected page discussing its own subject — not a stale reference',
      row: { kind: 'article', handle: 'how-saunas-improve-circulation', title: 'C',
             html: '<p>Whether saunas improve circulation is what the research asks.</p>' },
      correction: 'circulation-title', where: 'prose', expect: false },
    { name: 'a vendor name that matches a renamed collection title',
      row: { kind: 'collection', handle: 'fixture-d', title: 'D',
             html: '<p>Dundalk supplies eight and Scandia Manufacturing six.</p>' },
      correction: 'scandia-collections', where: 'prose', expect: true },
    { name: 'the destination title itself must NOT trip the probe',
      row: { kind: 'article', handle: 'fixture-e', title: 'E',
             html: '<p>See <a href="/x">what the circulation research actually shows</a>.</p>' },
      correction: 'circulation-title', where: 'ANCHOR', expect: false },
    // 18i: one constructed positive per correction id that had none — a register entry with no
    // positive is a pattern nobody has shown can fire
    { name: 'circulation-lead: the cut mechanism sentence',
      row: { kind: 'article', handle: 'fixture-f', title: 'F', html: '<p>Heat-driven vasodilation is the whole story.</p>' },
      correction: 'circulation-lead', where: 'prose', expect: true },
    { name: 'immune-boost: the cut benefit claim',
      row: { kind: 'article', handle: 'fixture-g', title: 'G', html: '<p>A cold plunge boosts your immune system.</p>' },
      correction: 'immune-boost', where: 'prose', expect: true },
    { name: 'alzheimers-clause: the hedged risk claim, unhedged',
      row: { kind: 'article', handle: 'fixture-h', title: 'H', html: '<p>Regular sauna use reduces the risk of dementia.</p>' },
      correction: 'alzheimers-clause', where: 'prose', expect: true },
    { name: 'sunlighten-pricing: the withdrawn finding',
      row: { kind: 'page', handle: 'fixture-i', title: 'I', html: '<p>Sunlighten does not publish its prices online.</p>' },
      correction: 'sunlighten-pricing', where: 'prose', expect: true },
    { name: 'named-health-terms: a banned assertion',
      row: { kind: 'collection', handle: 'fixture-j', title: 'J', html: '<p>This cabin detoxifies the body.</p>' },
      correction: 'named-health-terms', where: 'prose', expect: true },
    // 18i: proves matching runs on DECODED text — a stored &nbsp; must not hide the claim
    { name: 'entity inside the claim: saunas improve&nbsp;circulation',
      row: { kind: 'article', handle: 'fixture-k', title: 'K', html: '<p>Most saunas improve&nbsp;circulation.</p>' },
      correction: 'circulation-title', where: 'prose', expect: true },
  ];
  // 18i: every register entry must carry a positive fixture, or the run fails
  const unproved = CORRECTIONS.map((c) => c.id).filter((id) => !FIXTURES.some((f) => f.correction === id && f.expect));
  let bad = 0;
  if (unproved.length) { bad += 1; console.log(`FAIL  correction id(s) with no positive fixture: ${unproved.join(', ')}`); }
  for (const f of FIXTURES) {
    const hits = scan([f.row]).filter((h) => !h.selfRef);
    const found = hits.some((h) => h.correction === f.correction && h.where === f.where);
    const ok = found === f.expect;
    if (!ok) bad += 1;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${f.name} — expected ${f.expect}, got ${found}`);
  }
  /* The scandia fixture is a deliberate trap: the probe SHOULD fire, and a human
     must then decide it is a vendor name and not the renamed collection. A probe
     that suppressed it would be hiding the judgement, not making it. */
  console.log(bad ? `\n${bad} fixture(s) failed — refusing.` : '\nAll fixtures pass.\n');
  if (bad) process.exit(1);
  if (process.argv.includes('--self-test')) process.exit(0);
}

const hits = scan(rows);
const live = hits.filter((h) => !h.selfRef);
console.log(`surfaces scanned: ${rows.length} (${rows.filter(r=>r.kind==='article').length} articles, ${rows.filter(r=>r.kind==='page').length} pages, ${rows.filter(r=>r.kind==='collection').length} collections)`);
console.log(`hits: ${hits.length} total, ${live.length} outside the corrected page itself\n`);

for (const c of CORRECTIONS) {
  const mine = live.filter((h) => h.correction === c.id);
  const self = hits.filter((h) => h.correction === c.id && h.selfRef);
  console.log(`── ${c.id}  [${c.kind}]  target=${c.target}`);
  console.log(`   inbound: ${mine.length}   (on the corrected page itself: ${self.length})`);
  for (const h of mine) {
    console.log(`   ${h.where === 'ANCHOR' ? '⚑ ANCHOR' : '  prose '} ${h.kind}/${h.handle}`);
    console.log(`      "${h.match}"${h.href ? `  ->  ${h.href}` : ''}`);
    if (h.context) console.log(`      … ${h.context} …`);
  }
  console.log('');
}

fs.writeFileSync(path.join(DATA, 'stale-references.json'),
  JSON.stringify({ _meta: { ran: new Date().toISOString(), surfaces: rows.length, corrections: CORRECTIONS.map(c => ({ id: c.id, target: c.target, was: c.was, when: c.when })) }, hits }, null, 2));
console.log('wrote data/stale-references.json');
