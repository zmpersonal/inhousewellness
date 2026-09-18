/* Round 18 — unwrap T1 competitor links in ORDINARY articles. Institute blog excluded entirely
 * (client ruling: the section is being removed).
 *   node scripts/apply/r18-unwrap-t1.mjs [--apply] [--only <handle>]
 *
 * UNWRAP ONLY: <a …href="T1">INNER</a>  ->  INNER, byte for byte. No anchor text authored, no
 * internal link placed, no prose touched. The revised brief ("Unwrap only") supersedes the
 * original brief's internal-link placement.
 *
 * THE INVARIANT THAT MAKES "NO PROSE REWRITTEN" MECHANICAL: the article's VISIBLE TEXT (every
 * tag stripped) must be byte-identical before and after. Unwrapping removes tags and nothing
 * else, so any text difference means the edit did something it was not allowed to do.
 *
 * Plus: T1 anchors -> 0; every NON-T1 external link, every internal link, and every
 * withheld-domain link unchanged in count; outgoing body well-formed.
 */
import fs from 'node:fs';
import crypto from 'node:crypto';
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const ONLY = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;

const MULTI = new Set(['com.au','net.au','org.au','edu.au','gov.au','co.uk','org.uk','ac.uk','gov.uk','co.nz','co.za','co.jp','com.br','com.mx','com.sg','co.in','com.cn']);
const reg = (h) => { h = h.toLowerCase().replace(/^www\./, ''); const p = h.split('.'); if (p.length <= 2) return h; const l2 = p.slice(-2).join('.'); return MULTI.has(l2) ? p.slice(-3).join('.') : l2; };

const ct = JSON.parse(fs.readFileSync('data/r18-cart-test.json', 'utf8')).results;
const T1 = new Set(ct.filter((r) => r.tier === 'T1').map((r) => r.d));
T1.add('lifeprofitness.com');            // hand-read Round 18: cart + prices + "10% Off Saunas"
const WITHHELD = new Set(['goldendesigninc.com','medicalsaunas.com','dream-pod.com','almostheaven.com','homedics.com','homedics.com.au',
  'globalwellnessinstitute.org','ndnr.com','peakprimalwellness.com','saunasociety.org','drdferguson.com','fisiologiadelejercicio.com','soeberginstitute.com']);
for (const w of WITHHELD) if (T1.has(w)) { console.log(`REFUSING: withheld domain ${w} is in T1`); process.exit(1); }
if (T1.has('3dmassagechair.com')) { console.log('REFUSING: 3dmassagechair is REVIEW'); process.exit(1); }

const A = /<a\b[^>]*?href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
const domOf = (href) => { if (!/^https?:\/\//i.test(href)) return null; try { return reg(new URL(href).hostname); } catch { return null; } };
const visible = (b) => b.replace(/<[^>]*>/g, '');
function census(body) {
  const c = { t1: 0, withheld: 0, otherExt: 0, internal: 0 };
  for (const m of body.matchAll(A)) {
    const d = domOf(m[1]);
    if (!d) { c.internal++; continue; }
    if (d === 'inhousewellness.com') c.internal++;
    else if (T1.has(d)) c.t1++;
    else if (WITHHELD.has(d)) c.withheld++;
    else c.otherExt++;
  }
  return c;
}
const unwrap = (body) => body.replace(A, (full, href, inner) => (T1.has(domOf(href) || '') ? inner : full));

// ── constructed fixtures ──
const fx = '<p>See <a href="https://www.plunge.com/x">Plunge</a> and <a href="https://pubmed.ncbi.nlm.nih.gov/1">a study</a>.</p>';
const FIX = [
  ['T1 anchor unwrapped, inner kept',   unwrap(fx).includes('See Plunge and')],
  ['citation anchor untouched',         unwrap(fx).includes('href="https://pubmed.ncbi.nlm.nih.gov/1"')],
  ['visible text identical',            visible(unwrap(fx)) === visible(fx)],
  ['empty T1 anchor vanishes cleanly',  unwrap('<p>x<a href="https://plunge.com"> </a>y</p>') === '<p>x y</p>'],
  ['withheld not in T1',                !T1.has('goldendesigninc.com')],
  ['relative internal link untouched',  unwrap('<a href="/collections/saunas">s</a>') === '<a href="/collections/saunas">s</a>'],
];
let bad = 0;
for (const [l, ok] of FIX) { if (!ok) { console.log(`FIXTURE FAIL: ${l}`); bad++; } }
if (bad) process.exit(1);
console.log(`fixtures ${FIX.length}/${FIX.length}   T1 domains ${T1.size}   withheld ${WITHHELD.size}\n`);

// ── population: live, ordinary blogs only ──
let cur = null; const arts = [];
while (true) {
  const r = await gql(`query($c:String){ articles(first:250, after:$c){ pageInfo{hasNextPage endCursor} nodes{ id handle isPublished body blog{handle} } } }`, { c: cur });
  arts.push(...r.articles.nodes);
  if (!r.articles.pageInfo.hasNextPage) break; cur = r.articles.pageInfo.endCursor;
}
const targets = arts.filter((a) => a.blog.handle !== 'institute' && census(a.body).t1 > 0 && (!ONLY || a.handle === ONLY));
const done = arts.filter((a) => a.blog.handle !== 'institute' && census(a.body).t1 === 0);
console.log(`ordinary articles with T1 links: ${targets.length}`);

const plan = [];
let fail = 0;
for (const a of targets) {
  const before = census(a.body);
  const out = unwrap(a.body);
  const after = census(out);
  const checks = [
    ['T1 -> 0', after.t1 === 0],
    ['withheld unchanged', after.withheld === before.withheld],
    ['other external unchanged', after.otherExt === before.otherExt],
    ['internal unchanged', after.internal === before.internal],
    ['VISIBLE TEXT byte-identical', visible(out) === visible(a.body)],
    ['anchors removed == T1 count', (a.body.match(/<a\b/gi) || []).length - (out.match(/<a\b/gi) || []).length === before.t1],
  ];
  const f = checks.filter(([, ok]) => !ok).map(([l]) => l);
  try { assertWellFormed(out, a.handle, a.body); } catch (e) { f.push('wellformed: ' + e.message.slice(0, 60)); }
  if (f.length) fail++;
  console.log(`  ${f.length ? 'FAIL' : 'ok  '} ${a.handle.padEnd(52)} ext ${String(before.t1 + before.withheld + before.otherExt).padStart(3)}->${String(after.t1 + after.withheld + after.otherExt).padStart(3)}  T1 ${before.t1}->0${f.length ? '  ' + f.join('; ') : ''}`);
  plan.push({ a, before, after, out });
}
const tot = plan.reduce((s, p) => s + p.before.t1, 0);
console.log(`\n  T1 anchors to unwrap: ${tot} across ${plan.length} articles`);
console.log(`  ordinary articles already at T1=0 (idempotent skip): ${done.length}`);
if (fail) { console.log(`  REFUSING: ${fail} article(s) failed a post-condition`); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const snap = plan.map((p) => ({ id: p.a.id, handle: p.a.handle, blog: p.a.blog.handle, md5: crypto.createHash('md5').update(p.a.body).digest('hex'), afterMd5: crypto.createHash('md5').update(p.out).digest('hex'), before: p.a.body, counts: p.before }));
const bpath = backup('r18-unwrap-t1', snap);
console.log(`\n  BACKUP: ${bpath}  (${snap.length} bodies, md5 per body)`);
for (const p of plan) {
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id body } userErrors{ field message } } }`, { id: p.a.id, article: { body: p.out } });
  if (m.articleUpdate.userErrors.length) { console.log(`  ERR ${p.a.handle}`, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  const back = census(m.articleUpdate.article.body);
  p.stored = crypto.createHash('md5').update(m.articleUpdate.article.body).digest('hex');
  logChange({ resource: p.a.id, handle: p.a.handle, field: 'body', old: `${p.before.t1} T1 competitor links`, new: 'unwrapped, anchor text verbatim', note: `Round 18; backup ${bpath}` });
  console.log(`  wrote ${p.a.handle.padEnd(52)} read-back T1=${back.t1}  stored-md5 ${p.stored === crypto.createHash('md5').update(p.out).digest('hex') ? '= sent' : 'NORMALISED by Shopify'}`);
}
// the restore guard compares live against what Shopify STORED, not what we sent
for (const s of snap) { const p = plan.find((x) => x.a.handle === s.handle); s.storedMd5 = p.stored; }
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  backup updated with stored md5s: ${bpath}`);
