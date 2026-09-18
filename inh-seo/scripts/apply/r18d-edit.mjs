/* Round 18d — Costco / RC Willey / Home Depot / realrelaxmall, plus four authorised rewrites.
 *   node scripts/apply/r18d-edit.mjs [--apply] [--only <handle>]
 *
 * HELD, NOT IN THIS SPEC: costco-sauna-guide-worth-it links #5-#7 (Bellagio, Gracia, San Marino
 * Elite). They are SOURCE CITATIONS in "Sources and disclosure", and repointing them at our pages
 * would misattribute the source. Awaiting a client decision.
 *
 * Every anchor is located by EXACT href + EXACT inner text taken from the live body — never
 * retyped. Every edit asserts its match count. PROOF THAT NOTHING ELSE CHANGED, two ways:
 *   1. LINK MULTISET: hrefs(after) == hrefs(before) minus exactly the declared removals. This also
 *      proves no link was ADDED (a rewrite rule).
 *   2. TEXT: with each declared sentence masked as ⟦i⟧ on both sides, visible text is
 *      BYTE-IDENTICAL. Articles with no rewrite must be byte-identical with nothing masked.
 */
import crypto from 'node:crypto';
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const ONLY = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const visible = (b) => b.replace(/<[^>]*>/g, '');
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const hrefs = (b) => [...b.matchAll(/<a\b[^>]*?href="([^"]+)"/gi)].map((m) => m[1]);

const MORGAN = 'https://www.costco.com/almost-heaven-saunas-morgan-4-person-barrel-sauna.product.100481876.html';
const SPEC = {
  'costco-sauna-guide-worth-it': [
    { kind: 'unwrap', href: MORGAN, text: 'Almost Heaven Morgan 4P', note: '#1 table cell' },
    { kind: 'rewrite', href: MORGAN, text: 'view the Morgan on Costco', pre: 'You can ', post: '.', to: 'Costco lists the Morgan.', note: '#2' },
    { kind: 'rewrite', href: MORGAN, text: 'view it on Costco', pre: 'Not carried by InHouse; ', post: '.', to: 'Not carried by InHouse; Costco lists it.', note: '#3' },
    { kind: 'rewrite', href: 'https://www.costco.com/s?keyword=sauna', text: 'Costco sauna listings', pre: 'which we don’t carry, you can check the current ', post: '.', to: 'which we don’t carry, Costco currently lists them.', note: '#4' },
    { kind: 'unwrap', href: 'https://www.costco.com/backyard-discovery-bennett-2-4-person-outdoor-sauna-with-remote-wi-fi-heating.product.4201030663.html', text: 'Backyard Discovery Bennett', note: '#8 sources' },
  ],
  'arcadia-barrel-sauna-guide': [
    { kind: 'unwrap', href: 'https://www.costco.com/p/-/almost-heaven-arcadia-2-person-outdoor-barrel-sauna/4000431664', text: 'Costco — Almost Heaven Arcadia 2-person barrel sauna listing', note: '#10 sources' },
    { kind: 'unwrap', href: 'https://www.costco.com/p/-/almost-heaven-saunas-duet-2-person-outdoor-barrel-sauna/4000225468', text: 'Costco — Almost Heaven Duet 2-person barrel sauna listing', note: '#11 sources' },
  ],
  'homedics-premium-steam-sauna-review': [
    { kind: 'unwrap', href: 'https://www.costco.com/p/-/homedics-premium-steam-sauna/4000383998', text: 'Costco — HoMedics Premium Steam Sauna listing (SPE-SN400, item 2849544)', note: '#12 sources' },
  ],
  'lifetrend-cold-plunge-review': [
    { kind: 'rewrite', href: 'https://www.costco.com/p/-/lifetrend-solitude-integrated-cold-plunge-hot-soak-tub/4000388365?langId=-1', text: "See Costco's current LifeTrend Solitude listing", pre: '', post: '.', to: 'Costco currently lists the LifeTrend Solitude.', note: '#13' },
    { kind: 'unwrap', href: 'https://www.costco.com/p/-/lifetrend-solitude-integrated-cold-plunge-hot-soak-tub/4000388365?langId=-1', text: 'Costco — LifeTrend Solitude integrated cold plunge and hot soak tub listing', note: '#14 sources' },
  ],
  'benefits-of-massage-chairs-for-seniors': [
    { kind: 'unwrap', href: 'https://www.rcwilley.com/dp/OV-zero-gravity-massage-recliners', text: 'rcwilley.com', note: 'rcwilley' },
    { kind: 'unwrap', href: 'https://realrelaxmall.com/blogs/news/does-medicare-pay-for-real-relax-massage-chairs', text: 'realrelaxmall.com', note: 'realrelaxmall — reclassified T1' },
  ],
  'top-fire-pits-outdoor-meditation': [
    { kind: 'unwrap', href: 'https://www.homedepot.com/p/reviews/Breeo-X-Series-19-Smokeless-Fire-Pit', text: 'https://www.homedepot.com/p/reviews/Breeo-X-Series-19-Smokeless-Fire-Pit', note: 'homedepot' },
  ],
};
// the anchor itself, found by exact href + exact inner text. Attributes may appear in any order.
const anchorRx = (href, text) => new RegExp(`<a\\b(?=[^>]*\\bhref="${esc(href)}")[^>]*>${esc(text)}<\\/a>`, 'g');

// ── word-level diff (LCS) for the report ──
function wordDiff(a, b) {
  const A = a.split(/(\s+)/), B = b.split(/(\s+)/);
  const n = A.length, m = B.length, L = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  let i = 0, j = 0, out = '';
  while (i < n && j < m) { if (A[i] === B[j]) { out += A[i]; i++; j++; } else if (L[i + 1][j] >= L[i][j + 1]) { out += `[-${A[i]}-]`; i++; } else { out += `{+${B[j]}+}`; j++; } }
  while (i < n) out += `[-${A[i++]}-]`; while (j < m) out += `{+${B[j++]}+}`;
  return out.replace(/\]\[-/g, '').replace(/\+\}\{\+/g, '');
}

// ── constructed fixtures ──
{
  const b = '<p>A. You can <a href="https://x.com/p" title="t">view it</a>. B <a href="https://x.com/q">Q</a>.</p>';
  const r = anchorRx('https://x.com/p', 'view it');
  const FIX = [
    ['anchor found by href+text',        (b.match(r) || []).length === 1],
    ['attribute order does not matter',  ('<a title="t" href="https://x.com/p">view it</a>'.match(anchorRx('https://x.com/p', 'view it')) || []).length === 1],
    ['a different anchor text does NOT match (shared href)', ('<a href="https://x.com/p">other</a>'.match(anchorRx('https://x.com/p', 'view it')) || []).length === 0],
    ['word diff marks the change',        wordDiff('You can view it.', 'It is listed.').includes('{+')],
  ];
  for (const [l, ok] of FIX) if (!ok) { console.log('FIXTURE FAIL: ' + l); process.exit(1); }
}

const plan = []; let fail = 0;
for (const [handle, edits] of Object.entries(SPEC)) {
  if (ONLY && handle !== ONLY) continue;
  const r = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body blog{handle} } } }`, { q: `handle:${handle}` });
  const a = r.articles.nodes.find((x) => x.handle === handle);
  let body = a.body; const problems = []; const masks = []; const removed = [];
  console.log(`\n── ${handle}`);
  for (const e of edits) {
    const rx = anchorRx(e.href, e.text);
    const anchors = body.match(rx) || [];
    if (e.kind === 'unwrap') {
      if (anchors.length !== 1) { problems.push(`${e.note}: anchor matched ${anchors.length}x, want 1`); continue; }
      body = body.replace(rx, e.text); removed.push(e.href);
      console.log(`   unwrap  ${e.note.padEnd(34)} "${e.text.slice(0, 60)}"`);
    } else {
      if (anchors.length !== 1) { problems.push(`${e.note}: anchor matched ${anchors.length}x, want 1`); continue; }
      const from = e.pre + anchors[0] + e.post;
      const n = body.split(from).length - 1;
      if (n !== 1) { problems.push(`${e.note}: sentence matched ${n}x, want 1`); continue; }
      body = body.replace(from, e.to); removed.push(e.href);
      masks.push({ note: e.note, fromV: visible(from), toV: e.to });
    }
  }
  // proof 1 — link multiset
  const before = hrefs(a.body), after = hrefs(body);
  const expect = [...before]; for (const h of removed) expect.splice(expect.indexOf(h), 1);
  if (JSON.stringify([...expect].sort()) !== JSON.stringify([...after].sort())) problems.push('LINK MULTISET: something other than the declared removals changed');
  // proof 2 — text, with declared sentences masked
  let vb = visible(a.body), va = visible(body);
  for (const [k, mk] of masks.entries()) {
    const cb = vb.split(mk.fromV).length - 1, ca = va.split(mk.toV).length - 1;
    if (cb !== 1 || ca !== 1) { problems.push(`${mk.note}: mask not unique (before ${cb}, after ${ca})`); continue; }
    vb = vb.replace(mk.fromV, `⟦${k}⟧`); va = va.replace(mk.toV, `⟦${k}⟧`);
  }
  const textOk = vb === va;
  if (!textOk) problems.push('TEXT OUTSIDE THE DECLARED SENTENCES CHANGED');
  try { assertWellFormed(body, handle, a.body); } catch (e) { problems.push('wellformed: ' + e.message.slice(0, 80)); }
  for (const mk of masks) {
    console.log(`   REWRITE ${mk.note}`);
    console.log(`      before: ${mk.fromV}`);
    console.log(`      after : ${mk.toV}`);
    console.log(`      diff  : ${wordDiff(mk.fromV, mk.toV)}`);
  }
  console.log(`   links ${before.length} -> ${after.length} (removed ${removed.length})   ` +
    (masks.length ? `text outside the ${masks.length} declared sentence(s): ${textOk ? 'BYTE-IDENTICAL' : 'CHANGED'}` : `visible text: ${textOk ? 'BYTE-IDENTICAL' : 'CHANGED'}`));
  if (problems.length) { fail++; problems.forEach((p) => console.log('   FAIL ' + p)); }
  plan.push({ a, out: body, removed: removed.length, rewrites: masks.length });
}
console.log(`\n  ${plan.length} articles · ${plan.reduce((s, p) => s + p.removed, 0)} anchors removed · ${plan.reduce((s, p) => s + p.rewrites, 0)} sentences rewritten`);
if (fail) { console.log(`  REFUSING: ${fail} article(s) failed`); process.exit(1); }
if (!APPLY) { console.log('  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

const snap = plan.map((p) => ({ id: p.a.id, handle: p.a.handle, blog: p.a.blog.handle, md5: md5(p.a.body), afterMd5: md5(p.out), before: p.a.body }));
const bpath = backup('r18d-edit', snap);
for (const p of plan) {
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ body } userErrors{ message } } }`, { id: p.a.id, article: { body: p.out } });
  if (m.articleUpdate.userErrors.length) { console.log('  ERR', p.a.handle, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  const s = snap.find((x) => x.handle === p.a.handle); s.storedMd5 = md5(m.articleUpdate.article.body);
  logChange({ resource: p.a.id, handle: p.a.handle, field: 'body', old: 'Round 18d before-state', new: `${p.removed} anchors removed, ${p.rewrites} sentence(s) rewritten`, note: `backup ${bpath}` });
  console.log(`  wrote ${p.a.handle.padEnd(40)} stored ${s.storedMd5 === s.afterMd5 ? '= sent' : 'NORMALISED'}`);
}
(await import('node:fs')).writeFileSync(bpath, JSON.stringify(snap, null, 2));
console.log(`  BACKUP ${bpath}`);
