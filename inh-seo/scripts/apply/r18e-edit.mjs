/* Round 18e — costco-sauna-guide-worth-it (Option A + Gracia/Bellagio rows + a confirm-specs note)
 * and lifetrend-cold-plunge-review (the orphaned "confirm on the live page").
 *   node scripts/apply/r18e-edit.mjs [--apply] [--only <handle>]
 *
 * Kinds: unwrap (exact href + exact inner text) · replace (exact unique HTML) · insert (after an
 * exact unique anchor). PROOF, as Round 18d:
 *   1. LINK MULTISET after == before − declared removals + declared additions (the Gracia repoint
 *      is one of each). Nothing else may move, and nothing undeclared may be added.
 *   2. TEXT: every replace/insert is masked ⟦i⟧ on both sides at the HTML level; the remaining
 *      visible text must be BYTE-IDENTICAL. Unwraps need no mask — they change no visible text.
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

const SPEC = {
  'costco-sauna-guide-worth-it': [
    { kind: 'unwrap', note: 'Sources: Dynamic Bellagio (Option A)', href: 'https://www.costco.com/p/-/dynamic-bellagio-3-person-low-emf-far-infrared-sauna/100370044', text: 'Dynamic Bellagio' },
    { kind: 'unwrap', note: 'Sources: Dynamic Gracia (Option A)', href: 'https://www.costco.com/p/-/dynamic-gracia-1-2-person-low-emf-infrared-sauna/100675807', text: 'Dynamic Gracia' },
    { kind: 'unwrap', note: 'Sources: San Marino Elite (Option A)', href: 'https://www.costco.com/p/-/dynamic-san-marino-elite-2-person-ultra-low-emf-far-infrared-sauna/4000384560', text: 'San Marino Elite' },
    { kind: 'replace', note: 'Table 7 Bellagio row: price + relationship',
      from: row(['Dynamic Bellagio 3P', '~$1,999 (promo)', '<a href="https://inhousewellness.com/products/dynamic-bellagio-3-person-indoor-infrared-sauna" rel="noopener noreferrer" title="Dynamic Bellagio 3P" target="_blank">Dynamic Bellagio 3P</a>', '~$2,499', 'Exact same model', 'Budget-focused DIYers vs. buyers wanting install help']),
      to:   row(['Dynamic Bellagio 3P', '~$1,999 (promo)', '<a href="https://inhousewellness.com/products/dynamic-bellagio-3-person-indoor-infrared-sauna" rel="noopener noreferrer" title="Dynamic Bellagio 3P" target="_blank">Dynamic Bellagio 3P</a>', '$2,699', 'Same model line', 'Budget-focused DIYers vs. buyers wanting install help']) },
    { kind: 'replace', note: 'Table 7 Gracia row: repoint FS -> DYN-6119-01, price, relationship', removes: [FS], adds: [LOWEMF],
      from: row(['Dynamic Gracia 1–2P', '~$1,799', `<a href="${FS}" rel="noopener noreferrer" title="Dynamic Gracia" target="_blank">Dynamic Gracia</a>`, '~$1,899', 'Exact same model', 'First-time buyers wanting guidance']),
      to:   row(['Dynamic Gracia 1–2P', '~$1,799', `<a href="${LOWEMF}" rel="noopener noreferrer" title="Dynamic Gracia" target="_blank">Dynamic Gracia</a>`, '$1,999', 'Same model line', 'First-time buyers wanting guidance']) },
    { kind: 'insert', note: 'confirm-specs note under Table 7',
      after: '</table>\n</div>\n', before: '<p>Where the channels genuinely differ:</p>',
      text: '<p><em>“Same model line” is matched on the model name. Confirm specifications against the current Costco listing before comparing.</em></p>\n' },
  ],
  'lifetrend-cold-plunge-review': [
    { kind: 'replace', note: 'orphaned "confirm on the live page"',
      from: 'Price and availability change—confirm on the live page before purchase.',
      to:   'Price and availability change—confirm with Costco before purchase.' },
  ],
};

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
    } else if (e.kind === 'insert') {
      const anchor = e.after + e.before, n = body.split(anchor).length - 1;
      if (n !== 1) return problems.push(`${e.note}: anchor matched ${n}x`);
      body = body.replace(anchor, e.after + e.text + e.before); mB = mB.replace(anchor, e.after + `⟦${k}⟧` + e.before); mA = mA.replace(anchor, e.after + `⟦${k}⟧` + e.before);
      shown.push({ ...e, from: '', to: e.text });
    }
  });
  // TEST ONLY: --inject-stray slips an UNDECLARED one-word change in, to prove the text proof fires
  if (process.argv.includes('--inject-stray')) { if (APPLY) { console.log('refusing: --inject-stray with --apply'); process.exit(1); } body = body.replace('Price:', 'Cost:'); }
  if (process.argv.includes('--inject-link')) { if (APPLY) process.exit(1); body = body.replace('</ul>', '<a href="https://example.com/x">x</a></ul>'); }
  // the masked AFTER twin must carry the real edits outside the masks — rebuild it from `body`
  { let t = body; edits.forEach((e, k) => { if (e.kind === 'replace') t = t.replace(e.to, `⟦${k}⟧`); if (e.kind === 'insert') t = t.replace(e.text, `⟦${k}⟧`); }); mA = t; }
  const bh = hrefs(a.body), ah = hrefs(body), expect = [...bh];
  for (const h of removed) { const i = expect.indexOf(h); if (i < 0) problems.push('declared removal not present: ' + h); else expect.splice(i, 1); }
  expect.push(...added);
  const linksOk = JSON.stringify([...expect].sort()) === JSON.stringify([...ah].sort());
  if (!linksOk) problems.push('LINK MULTISET moved beyond the declared changes');
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
const bpath = backup('r18e-edit', snap);
for (const p of plan) {
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ body } userErrors{ message } } }`, { id: p.a.id, article: { body: p.out } });
  if (m.articleUpdate.userErrors.length) { console.log('  ERR', p.a.handle, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  const s = snap.find((x) => x.handle === p.a.handle); s.storedMd5 = md5(m.articleUpdate.article.body);
  logChange({ resource: p.a.id, handle: p.a.handle, field: 'body', old: 'Round 18e before-state', new: 'Round 18e edits', note: `backup ${bpath}` });
  console.log(`  wrote ${p.a.handle.padEnd(36)} stored ${s.storedMd5 === s.afterMd5 ? '= sent' : 'NORMALISED'}`);
}
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
