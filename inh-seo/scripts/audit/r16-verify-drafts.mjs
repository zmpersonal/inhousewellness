/* Round 16 — verify the two comparison drafts before they go anywhere.
 *
 * Checks markup balance, JSON-LD validity, FAQ mirroring, anchor integrity, link rules, and
 * — the part that matters — resolves EVERY internal handle against real data rather than
 * trusting that I typed it correctly. Retyped/derived handles have produced five false 404s
 * and one wrong page URL on this project (CLAUDE.md: "a handle derived from a title is a guess").
 *
 * Per CLAUDE.md 6c every check carries a CONSTRUCTED fixture it must catch. Repairing the
 * estate cannot break these: none is anchored to live content.
 *
 * 18i: that sentence was not true when written. The <h1>, dead-anchor, FAQ-mirror, handle,
 * ACTIVE and banned-voice checks ran inline in the draft loop and their "fixtures" either did
 * not exist or tested a copy of the regex rather than the check. Each is now a function, the
 * loop calls it, and the fixture calls the same function. NOT fixture-proved: the JSON-LD block
 * COUNT (=== 3), the FAQ house-style range (8-12), the link-attribute rules and the dated-price
 * check — each is a one-line literal comparison, left as read-and-see.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve('.');
const R = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');
const DRAFTS = ['content/drafts/infrared-vs-traditional-sauna.html',
                'content/drafts/infrared-vs-steam-sauna.html'];

let fails = 0;
const fail = (f, m) => { console.log(`  FAIL [${f}] ${m}`); fails++; };
const ok   = (f, m) => console.log(`  ok   [${f}] ${m}`);

// ── data ──
const prods = (() => { const P = JSON.parse(R('data/products.json')); return Array.isArray(P) ? P : (P.products || P.nodes); })();
const cols  = (() => { const C = JSON.parse(R('data/collections.json')); return Array.isArray(C) ? C : (C.collections || C.nodes); })();
const arts  = JSON.parse(R('data/content.json')).articles;
const ACTIVE = prods.filter((p) => (p.status || '').toUpperCase() === 'ACTIVE');

// ── checkers, each a pure fn so a fixture can exercise it ──
const TAGS = ['p','li','ul','ol','h2','h3','a','table','tr','td','th','div','thead','tbody','style','script'];
const stripComments = (s) => s.replace(/<!--[\s\S]*?-->/g, '');
function unbalanced(html) {
  const s = stripComments(html);
  const bad = [];
  for (const t of TAGS) {
    const open  = (s.match(new RegExp(`<${t}(?=[\\s>])`, 'gi')) || []).length;
    const close = (s.match(new RegExp(`</${t}>`, 'gi')) || []).length;
    if (open !== close) bad.push(`${t} ${open}/${close}`);
  }
  return bad;
}
const norm = (q) => q.replace(/&[a-z]+;|["“”'’]/gi, '').replace(/[^\x20-\x7e]/g, '')
                     .replace(/\s+/g, ' ').trim().toLowerCase();
const hasH1 = (body) => /<h1[\s>]/i.test(body);
function faqMirror(body, faq) {
  const schemaQ = faq.mainEntity.map((q) => norm(q.name));
  const visibleQ = [...body.matchAll(/<p><strong>([^<]*\?)<\/strong>/g)].map((m) => norm(m[1]));
  return { schemaQ, visibleQ, missing: schemaQ.filter((q) => !visibleQ.includes(q)), extra: visibleQ.filter((q) => !schemaQ.includes(q)) };
}
function deadAnchors(body) {
  const ids = new Set([...body.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
  const anchors = [...body.matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
  return { anchors, dead: anchors.filter((a) => !ids.has(a)) };
}
/** A problem with one internal URL, resolved against real (or fixture) data; null when it resolves. */
function handleProblem(href, { cols, prods, arts }) {
  const m = href.match(/inhousewellness\.com\/(collections|products|blogs)\/([^/"?#]+)(?:\/([^/"?#]+))?/);
  if (!m) return href !== 'https://inhousewellness.com/' && !href.includes('/cdn/') ? `unparseable internal URL: ${href}` : null;
  const [, kind, a, bh] = m;
  if (kind === 'collections') {
    const c = cols.find((x) => x.handle === a);
    if (!c) return `collection does not exist: ${a}`;
    if (!c.publishedOnline) return `collection not published online: ${a}`;
  } else if (kind === 'products') {
    const p = prods.find((x) => x.handle === a);
    if (!p) return `product does not exist: ${a}`;
    if ((p.status || '').toUpperCase() !== 'ACTIVE') return `product is ${p.status}, not ACTIVE: ${a}`;
  } else if (kind === 'blogs' && bh) {
    const art = arts.find((x) => x.handle === bh);
    const selfRefs = ['infrared-vs-traditional-sauna', 'infrared-vs-steam-sauna'];
    if (!art && !selfRefs.includes(bh)) return `article does not exist: ${bh}`;
    if (art && art.blog !== a) return `article ${bh} is in blog "${art.blog}", link says "${a}"`;
  }
  return null;
}
// banned voice / benefit-assertion screen
const BANNED = ['detoxifies', 'boosts immunity', 'burns calories', 'flushes toxins',
                'elevate your wellness', 'transform your space', 'unlock your',
                'Only 3 Left', 'Limited Time', 'revitalize', 'the ultimate '];
const bannedHits = (body) => BANNED.filter((t) => new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(body));

// ── FIXTURES (constructed; must fail) ──
const FX_DATA = { cols: [{ handle: 'c-live', publishedOnline: true }, { handle: 'c-hidden', publishedOnline: false }],
                  prods: [{ handle: 'p-live', status: 'ACTIVE' }, { handle: 'p-draft', status: 'DRAFT' }],
                  arts: [{ handle: 'a-saunas', blog: 'saunas' }] };
const FIX = [
  ['balance',  unbalanced('<div><p>hi</div>').length > 0,                      'unclosed <p> detected'],
  ['balance',  unbalanced('<div><p>hi</p></div>').length === 0,                'balanced markup passes'],
  ['h1',       hasH1('<h1>x</h1>') === true,                                   'an <h1> in body is detected'],   // 18i: calls the check, not a copy of its regex
  ['h1',       hasH1('<p>h1 is fine in prose</p>') === false,                  'the text "h1" is not a tag'],
  ['comment',  unbalanced('<!-- <p> -->').length === 0,                        'a tag inside an HTML comment is not counted'],
  ['norm',     norm('What does &quot;low EMF&quot; mean?') === norm('What does "low EMF" mean?'), 'entity/quote normalisation matches'],
  ['norm',     norm('pour water, loyly') !== norm('pour water, steam'),        'normalisation does not collapse different questions'],
  ['jsonld',   (() => { try { JSON.parse('{"a":01}'); return false; } catch { return true; } })(), 'leading-zero literal rejected (the Round 15b bug)'],
  // 18i: dead anchors, FAQ mirror, handle resolution, ACTIVE, banned voice — each through the function the draft loop calls
  ['anchors',  JSON.stringify(deadAnchors('<a href="#a">A</a><a href="#b">B</a><h2 id="a">A</h2>').dead) === '["b"]', 'a TOC link to a missing id is dead'],
  ['anchors',  deadAnchors('<a href="#a">A</a><h2 id="a">A</h2>').dead.length === 0,  'a resolving anchor is not dead'],
  ['faq',      (() => { const r = faqMirror('<p><strong>Is it hot?</strong></p><p><strong>Is it wet?</strong></p>', { mainEntity: [{ name: 'Is it hot?' }, { name: 'Is it loud?' }] });
                 return r.missing.join() === 'is it loud?' && r.extra.join() === 'is it wet?'; })(), 'a schema-only and a visible-only question are both reported'],
  ['faq',      (() => { const r = faqMirror('<p><strong>Is it &quot;hot&quot;?</strong></p>', { mainEntity: [{ name: 'Is it "hot"?' }] });
                 return !r.missing.length && !r.extra.length; })(),                  'a mirrored question passes'],
  ['handle',   /does not exist/.test(handleProblem('https://inhousewellness.com/collections/nope', FX_DATA)), 'a missing collection is caught'],
  ['handle',   /not published/.test(handleProblem('https://inhousewellness.com/collections/c-hidden', FX_DATA)), 'an unpublished collection is caught'],
  ['handle',   /does not exist/.test(handleProblem('https://inhousewellness.com/products/nope', FX_DATA)), 'a missing product is caught'],
  ['active',   /not ACTIVE/.test(handleProblem('https://inhousewellness.com/products/p-draft', FX_DATA)), 'a DRAFT product is caught'],
  ['handle',   /is in blog/.test(handleProblem('https://inhousewellness.com/blogs/news/a-saunas', FX_DATA)), 'an article under the wrong blog is caught'],
  ['handle',   handleProblem('https://inhousewellness.com/products/p-live', FX_DATA) === null
               && handleProblem('https://inhousewellness.com/blogs/saunas/a-saunas', FX_DATA) === null, 'resolving handles pass'],
  ['voice',    bannedHits('This cabin detoxifies and will revitalize you.').length === 2, 'banned phrasing is caught'],
  ['voice',    bannedHits('A cedar cabin that seats four.').length === 0,          'clean copy passes'],
];
console.log('FIXTURES');
for (const [f, pass, label] of FIX) { pass ? ok(f, label) : fail(f, `FIXTURE DID NOT HOLD: ${label}`); }

// ── per draft ──
for (const rel of DRAFTS) {
  const html = R(rel);
  const body = stripComments(html);
  console.log(`\n${rel}  (${html.length.toLocaleString()} chars)`);

  const b = unbalanced(html);
  b.length ? fail('balance', `unbalanced: ${b.join(', ')}`) : ok('balance', 'all tracked tags balanced');

  hasH1(body) ? fail('h1', 'body contains an <h1>') : ok('h1', 'no <h1> in body');

  // JSON-LD
  const blocks = [...body.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  let faq = null;
  for (const [i, raw] of blocks.entries()) {
    try { const j = JSON.parse(raw); if (j['@type'] === 'FAQPage') faq = j; }
    catch (e) { fail('jsonld', `block ${i + 1} does not parse: ${e.message}`); }
  }
  blocks.length === 3 ? ok('jsonld', '3 blocks, all parse (Article + BreadcrumbList + FAQPage)')
                      : fail('jsonld', `expected 3 blocks, found ${blocks.length}`);

  // FAQ mirrored 1:1 with the visible section
  if (faq) {
    const { schemaQ, visibleQ, missing, extra } = faqMirror(body, faq);
    if (missing.length || extra.length) {
      fail('faq', `schema ${schemaQ.length} vs visible ${visibleQ.length}; not-visible=${missing.length} not-in-schema=${extra.length}`);
      missing.slice(0, 3).forEach((q) => console.log(`         schema-only: ${q.slice(0, 70)}`));
      extra.slice(0, 3).forEach((q) => console.log(`         visible-only: ${q.slice(0, 70)}`));
    } else ok('faq', `${schemaQ.length} questions mirrored 1:1 with the visible section`);
    (schemaQ.length >= 8 && schemaQ.length <= 12) ? ok('faq', `${schemaQ.length} questions (house style: 8-12)`)
                                                  : fail('faq', `${schemaQ.length} questions, house style wants 8-12`);
  } else fail('faq', 'no FAQPage block found');

  // TOC anchors resolve
  const { anchors, dead } = deadAnchors(body);
  dead.length ? fail('anchors', `dead: ${dead.join(', ')}`)
              : ok('anchors', `${anchors.length} TOC anchors all resolve`);

  // link rules + handle resolution
  const links = [...body.matchAll(/<a\s+href="(https?:\/\/[^"]+)"([^>]*)>/g)];
  let internal = 0, external = 0;
  for (const [, href, attrs] of links) {
    const isInternal = href.includes('inhousewellness.com');
    if (isInternal) {
      internal++;
      if (!/target="_blank"/.test(attrs) || !/rel="noopener"/.test(attrs)) fail('linkrule', `internal link missing target/rel: ${href}`);
      const problem = handleProblem(href, { cols, prods, arts });
      if (problem) fail('handle', problem);
    } else { external++; if (!/rel="nofollow noopener"/.test(attrs)) fail('linkrule', `external link missing nofollow: ${href}`); }
  }
  ok('linkrule', `${internal} internal (target+noopener), ${external} external (nofollow noopener)`);

  const hits = bannedHits(body);
  hits.length ? fail('voice', `banned phrasing: ${hits.join(', ')}`) : ok('voice', 'no banned wellness-dialect or scarcity phrasing');

  // dated price note present (client instruction)
  /September 2026/.test(body) ? ok('dated', 'prices dated in the copy so they can be refreshed')
                              : fail('dated', 'no date on the price figures');
}
console.log(`\n${fails ? `FAILED — ${fails} problem(s)` : 'ALL CHECKS PASSED'}`);
process.exitCode = fails ? 1 : 0;
