/* Round 18i — Medical Frozen Plunge 1 (discontinued on quality grounds): the four recommending sentences, as drafted in
 * content/drafts/r18i-medical-frozen-rewrites.md and APPROVED by the client (the recommended version of each), plus the
 * fifth link repointed to the Finnmark SoulCold. 7 hrefs in 5 articles: 6 removed, 1 repointed.
 * Every FROM is copied from the live bodies (read 2026-09-18), never retyped.
 * New kind 'delete': the text proof compares against the before-state with EXACTLY the declared string removed —
 * an independently computed expectation, not a mask (a mask of an empty replacement cannot be placed).
 *   node scripts/apply/r18i-frozen-edit.mjs [--apply] [--only <handle>]   — run it through r18i-article-proof.sh
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const ONLY = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const visible = (b) => b.replace(/<[^>]*>/g, '');
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const hrefs = (b) => [...b.matchAll(/<a\b[^>]*?href="([^"]+)"/gi)].map((m) => m[1]);
const anchorRx = (href, text) => new RegExp(`<a\\b(?=[^>]*\\bhref="${esc(href)}")[^>]*>${esc(text)}<\\/a>`, 'g');
const TD = '<td style="padding: 8px; border-bottom: 1px solid #eee;">';
const FS = 'https://inhousewellness.com/products/dynamic-saunas-dyn-6119-03-fs-gracia';
const LOWEMF = 'https://inhousewellness.com/products/1-2-person-infrared-sauna-hemlock-chromotherapy';   // DYN-6119-01, $1,999
const row = (cells) => '<tr>\n' + cells.map((c) => TD + c + '</td>').join('\n') + '\n</tr>';

// ABSOLUTE, copied from the body. A display that stripped the domain produced a relative spec that
// matched 0 of 9 — the asserted count refused it. An identifier comes from the data, never a display.
const MF = 'https://inhousewellness.com/products/medical-frozen-plunge-1-cold-therapy';
const SPEC = {
  'heat-cold-pain-modulation-not-elimination': [
    { kind: 'delete', note: '1 — delete the product line from the medical-caution section', removes: [MF, MF],
      from: '<p>For at-home protocols, consider controlled equipment like the<a href="' + MF + '"> </a><a href="' + MF + '">Medical Frozen Plunge for controlled cold exposure</a> to minimize risk while maximizing consistency.</p>\n' },
  ],
  'thermal-modalities-interfere-training-adaptation': [
    { kind: 'replace', note: '2 — the linked product-name heading becomes a plain heading (id kept)', removes: [MF],
      from: '<h3 id="h.s2sfup1fmnra"><a href="' + MF + '">Medical Frozen Plunge cold therapy tub</a></h3>',
      to:   '<h3 id="h.s2sfup1fmnra">Equipment for cold-water immersion</h3>' },
  ],
  'heat-cold-inflammatory-timeline-musculoskeletal-injuries': [
    { kind: 'delete', note: '3 — delete the "reliable equipment" sentence', removes: [MF],
      from: ' For readers exploring structured cold exposure with reliable equipment, the <a href="' + MF + '">Medical Frozen Plunge for Cold Therapy</a> offers controlled temperature management.' },
  ],
  'cold-plunge-buying-mistakes': [
    { kind: 'delete', note: '4 — delete the "one example" paragraph', removes: [MF, MF],
      // U+00A0 twice (inside the empty anchor, and after </a>) — read from the body's code points. The first spec typed
      // plain spaces from a display and matched 0x; the count refused it.
      from: '<p>The<a href="' + MF + '">\u00A0</a><a href="' + MF + '">Medical Frozen Plunge 1 cold therapy tub</a>\u00A0is one example of a purpose-built option for buyers prioritizing performance and safety over building their own.</p>\n' },
  ],
  'beyond-sauna-heat-cold-exposures-hsp-map': [
    { kind: 'repoint', note: '5 — repoint to the Finnmark SoulCold ($9,320, reclined one-person tub)', href: MF, text: 'consider options designed for consistency and safety',
      to: 'https://inhousewellness.com/products/finnmark-soulcold-plunge' },
  ],
};
const GONE = Object.fromEntries(Object.keys(SPEC).map((h) => [h, ['medical-frozen-plunge-1-cold-therapy', 'Medical Frozen']]));

function wordDiff(a, b) {
  const A = a.split(/(\s+)/), B = b.split(/(\s+)/), n = A.length, m = B.length;
  const L = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  let i = 0, j = 0, o = '';
  while (i < n && j < m) { if (A[i] === B[j]) { o += A[i]; i++; j++; } else if (L[i + 1][j] >= L[i][j + 1]) o += `[-${A[i++]}-]`; else o += `{+${B[j++]}+}`; }
  while (i < n) o += `[-${A[i++]}-]`; while (j < m) o += `{+${B[j++]}+}`;
  return o.replace(/-\]\[-/g, '').replace(/\+\}\{\+/g, '').replace(/\s+/g, ' ');
}
const cells = (h) => [...h.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) => visible(c[1]));

const plan = []; let fail = 0;
for (const [handle, edits] of Object.entries(SPEC)) {
  if (ONLY && handle !== ONLY) continue;
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body blog{handle} } } }`, { q: `handle:${handle}` });
  const a = q.articles.nodes.find((x) => x.handle === handle);
  let body = a.body, mB = a.body, mA = a.body;           // working copy + the two masked twins
  const problems = [], removed = [], added = [], shown = [];
  console.log(`\n── ${handle}`);
  edits.forEach((e, k) => {
    if (e.kind === 'repointAll') {
      const tok = `href="${e.href}"`, n = body.split(tok).length - 1;
      if (n !== e.count) return problems.push(`${e.note}: href matched ${n}x, want ${e.count}`);
      body = body.split(tok).join(`href="${e.to}"`); mB = mB.split(tok).join(`href="${e.to}"`); mA = mA.split(tok).join(`href="${e.to}"`);
      for (let k = 0; k < n; k++) { removed.push(e.href); added.push(e.to); }
      console.log(`   repoint  ${e.note}  (x${n}, anchor texts unchanged)`);
      return;
    }
    if (e.kind === 'repoint') {
      const rx = anchorRx(e.href, e.text), m = body.match(rx) || [];
      if (m.length !== 1) return problems.push(`${e.note}: matched ${m.length}x`);
      const na = m[0].replace(`href="${e.href}"`, `href="${e.to}"`);
      if (na === m[0]) return problems.push(`${e.note}: href not rewritten`);
      body = body.replace(m[0], na); mB = mB.replace(m[0], na); mA = mA.replace(m[0], na);
      removed.push(e.href); added.push(e.to);
      console.log(`   repoint  ${e.note}\n      link : ${e.href.split('/products/')[1]}  ->  ${e.to.split('/products/')[1]}   (anchor text unchanged: "${e.text}")`);
      return;
    }
    if (e.kind === 'unwrap') {
      const rx = anchorRx(e.href, e.text), n = (body.match(rx) || []).length;
      if (n !== 1) return problems.push(`${e.note}: matched ${n}x`);
      body = body.replace(rx, e.text); mB = mB.replace(rx, e.text); mA = mA.replace(rx, e.text); removed.push(e.href);
      console.log(`   unwrap   ${e.note}`);
    } else if (e.kind === 'replace') {
      const n = body.split(e.from).length - 1;
      if (n !== 1) return problems.push(`${e.note}: 'from' matched ${n}x`);
      body = body.replace(e.from, e.to); mB = mB.replace(e.from, `⟦${k}⟧`); mA = mA.replace(e.from, `⟦${k}⟧`);
      (e.removes || []).forEach((h) => removed.push(h)); (e.adds || []).forEach((h) => added.push(h));
      shown.push(e);
    } else if (e.kind === 'delete') {
      const n = body.split(e.from).length - 1;
      if (n !== 1) return problems.push(`${e.note}: 'from' matched ${n}x`);
      // expectation computed independently: the before-state with exactly this string removed, on BOTH twins
      body = body.replace(e.from, ''); mB = mB.replace(e.from, ''); mA = mA.replace(e.from, '');
      (e.removes || []).forEach((h) => removed.push(h));
      shown.push({ ...e, to: '' });
    } else if (e.kind === 'insert') {
      const anchor = e.after + e.before, n = body.split(anchor).length - 1;
      if (n !== 1) return problems.push(`${e.note}: anchor matched ${n}x`);
      body = body.replace(anchor, e.after + e.text + e.before); mB = mB.replace(anchor, e.after + `⟦${k}⟧` + e.before); mA = mA.replace(anchor, e.after + `⟦${k}⟧` + e.before);
      shown.push({ ...e, from: '', to: e.text });
    }
  });
  // TEST ONLY: injections are ARTICLE-AGNOSTIC and assert they landed. Round 18h: the old one replaced
  // 'Tradeoff:', absent from this article, so it changed nothing and the proof 'passed' vacuously.
  if (process.argv.includes('--inject-stray')) { if (APPLY) { console.log('refusing: --inject-stray with --apply'); process.exit(1); } const b0 = body; body = body.replace('<p>', '<p>X'); if (body === b0) { console.log('refusing: injection did not land — the test would be vacuous'); process.exit(1); } }
  if (process.argv.includes('--inject-link')) { if (APPLY) process.exit(1); const b1 = body; body = body.replace('</p>', '<a href="https://example.com/x"></a></p>');   /* 18i: NO visible text, so only the LINK proof can refuse it */ if (body === b1) { console.log('refusing: injection did not land'); process.exit(1); } }
  // the masked AFTER twin must carry the real edits outside the masks — rebuild it from `body`
  { let t = body; edits.forEach((e, k) => { if (e.kind === 'replace') t = t.replace(e.to, `⟦${k}⟧`); if (e.kind === 'insert') t = t.replace(e.text, `⟦${k}⟧`); }); mA = t; }
  const bh = hrefs(a.body), ah = hrefs(body), expect = [...bh];
  for (const h of removed) { const i = expect.indexOf(h); if (i < 0) problems.push('declared removal not present: ' + h); else expect.splice(i, 1); }
  expect.push(...added);
  const linksOk = JSON.stringify([...expect].sort()) === JSON.stringify([...ah].sort());
  if (!linksOk) problems.push('LINK MULTISET moved beyond the declared changes');
  for (const g of GONE[handle] || []) { const n = body.split(g).length - 1; if (n) problems.push(`GONE check: "${g}" still present ${n}x`); else console.log(`   gone     "${g}"`); }
  const textOk = visible(mB) === visible(mA);
  if (!textOk) problems.push('TEXT OUTSIDE THE DECLARED CHANGES MOVED');
  try { assertWellFormed(body, handle, a.body); } catch (e) { problems.push('wellformed: ' + e.message.slice(0, 80)); }
  for (const e of shown) {
    console.log(`   ${e.kind.padEnd(8)} ${e.note}`);
    if (e.from.startsWith('<tr>')) {
      const cb = cells(e.from), ca = cells(e.to);
      cb.forEach((c, i) => { if (c !== ca[i]) console.log(`      cell ${i + 1}: "${c}"  ->  "${ca[i]}"`); });
      const hb = hrefs(e.from)[0], ha = hrefs(e.to)[0]; if (hb !== ha) console.log(`      link : ${hb.split('/products/')[1]}  ->  ${ha.split('/products/')[1]}`);
    } else {
      console.log(`      before: ${visible(e.from) || '(nothing)'}`);
      console.log(`      after : ${visible(e.to).trim()}`);
      if (e.from) console.log(`      diff  : ${wordDiff(visible(e.from), visible(e.to))}`);
    }
  }
  console.log(`   links ${bh.length} -> ${ah.length}  (-${removed.length} +${added.length})  multiset ${linksOk ? 'as declared' : 'MOVED'}   text outside declared changes: ${textOk ? 'BYTE-IDENTICAL' : 'MOVED'}`);
  if (problems.length) { fail++; problems.forEach((p) => console.log('   FAIL ' + p)); }
  plan.push({ a, out: body });
}
if (fail) { console.log(`\n  REFUSING: ${fail} article(s) failed`); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }
const snap = plan.map((p) => ({ id: p.a.id, handle: p.a.handle, blog: p.a.blog.handle, md5: md5(p.a.body), afterMd5: md5(p.out), before: p.a.body }));
const bpath = backup('r18i-frozen-edit', snap);
for (const p of plan) {
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ body } userErrors{ message } } }`, { id: p.a.id, article: { body: p.out } });
  if (m.articleUpdate.userErrors.length) { console.log('  ERR', p.a.handle, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  const s = snap.find((x) => x.handle === p.a.handle); s.storedMd5 = md5(m.articleUpdate.article.body);
  logChange({ resource: p.a.id, handle: p.a.handle, field: 'body', old: 'Round 18i before-state', new: 'Round 18i Medical Frozen edits', note: `backup ${bpath}` });
  console.log(`  wrote ${p.a.handle.padEnd(36)} stored ${s.storedMd5 === s.afterMd5 ? '= sent' : 'NORMALISED'}`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
