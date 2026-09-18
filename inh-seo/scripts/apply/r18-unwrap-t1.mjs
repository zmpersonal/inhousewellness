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

/* --domains a,b : an EXPLICIT client-ruled set replaces the cart-test T1 set entirely.
   Used in Round 18c for 3dmassagechair.com, which fails the cart test and was removed on a
   relationship ruling. The label goes into the backup name so restores stay distinguishable. */
const DOMS = process.argv.includes('--domains') ? process.argv[process.argv.indexOf('--domains') + 1].split(',') : null;
const LABEL = DOMS ? 'r18c-unwrap-' + DOMS.join('+').replace(/[^a-z0-9+]/gi, '') : 'r18-unwrap-t1';
const ct = JSON.parse(fs.readFileSync('data/r18-cart-test.json', 'utf8')).results;
const T1 = DOMS ? new Set(DOMS) : new Set(ct.filter((r) => r.tier === 'T1').map((r) => r.d));
if (!DOMS) T1.add('lifeprofitness.com');            // hand-read Round 18: cart + prices + "10% Off Saunas"
const WITHHELD = new Set(['goldendesigninc.com','medicalsaunas.com','dream-pod.com','almostheaven.com','homedics.com','homedics.com.au',
  'globalwellnessinstitute.org','ndnr.com','peakprimalwellness.com','saunasociety.org','drdferguson.com','fisiologiadelejercicio.com','soeberginstitute.com']);
for (const w of WITHHELD) if (T1.has(w)) { console.log(`REFUSING: withheld domain ${w} is in T1`); process.exit(1); }
if (!DOMS && T1.has('3dmassagechair.com')) { console.log('REFUSING: 3dmassagechair is REVIEW'); process.exit(1); }

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
// Round 18i guard audit: "unwrap only" was not enforced — stripping a <strong> INSIDE a T1 anchor left visible
// text and every link count unchanged, and passed. The only tags allowed to disappear are the T1 <a …> openers
// and their </a> closers; every other tag must survive in exactly the same number.
const tagsOf = (b) => b.match(/<[^>]+>/g) || [];
function onlyT1TagsRemoved(before, after, t1) {
  const m = new Map();
  for (const t of tagsOf(before)) m.set(t, (m.get(t) || 0) + 1);
  for (const t of tagsOf(after)) m.set(t, (m.get(t) || 0) - 1);
  let opens = 0, closes = 0;
  for (const [t, n] of m) {
    if (n === 0) continue;
    if (n < 0) return false;                                            // a tag appeared
    if (t === '</a>') { closes += n; continue; }
    const h = /^<a\b[^>]*?href="([^"]+)"/i.exec(t);
    if (h && T1.has(domOf(h[1]) || '')) { opens += n; continue; }
    return false;                                                       // some other tag vanished
  }
  return opens === t1 && closes === t1;
}

// ── constructed fixtures ──
// fixtures use a domain drawn from the ACTIVE set, so they exercise the configuration that
// will actually run — a hard-coded plunge.com failed the moment --domains replaced the set
const FXD = [...T1][0];
const fx = `<p>See <a href="https://www.${FXD}/x">Plunge</a> and <a href="https://pubmed.ncbi.nlm.nih.gov/1">a study</a>.</p>`;
const FIX = [
  ['T1 anchor unwrapped, inner kept',   unwrap(fx).includes('See Plunge and')],
  ['citation anchor untouched',         unwrap(fx).includes('href="https://pubmed.ncbi.nlm.nih.gov/1"')],
  ['visible text identical',            visible(unwrap(fx)) === visible(fx)],
  ['empty T1 anchor vanishes cleanly',  unwrap(`<p>x<a href="https://${FXD}"> </a>y</p>`) === '<p>x y</p>'],
  ['withheld not in T1',                !T1.has('goldendesigninc.com')],
  ['relative internal link untouched',  unwrap('<a href="/collections/saunas">s</a>') === '<a href="/collections/saunas">s</a>'],
  ['markup inside a T1 anchor survives', unwrap(`<p><a href="https://${FXD}/y"><strong>Bold</strong> x</a></p>`) === '<p><strong>Bold</strong> x</p>'],
  ['tag check refuses a stripped <strong>', !onlyT1TagsRemoved(`<p><a href="https://${FXD}/y"><strong>B</strong></a></p>`, '<p>B</p>', 1)],
  ['tag check accepts a clean unwrap',  onlyT1TagsRemoved(`<p><a href="https://${FXD}/y"><strong>B</strong></a></p>`, '<p><strong>B</strong></p>', 1)],
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
    ['ONLY the T1 <a> tags removed', onlyT1TagsRemoved(a.body, out, before.t1)],
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
const bpath = backup(LABEL, snap);
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
