/* Round 15 — repoint 8 blog URLs from the HOMEPAGE to their nearest live equivalent.
 * --dry-run default. Client ruling 16 Sep 2026: non-product URLs go to the nearest live
 * equivalent; a redirect to the homepage is a soft 404 that spends the URL's history.
 *
 *   node scripts/apply/apply-blog-redirects.mjs [--apply]
 *
 * Each target was chosen by READING the live destination and the anchor text the link
 * promises, never by term overlap. Two rows carry a recorded qualification, and one row
 * exists because the term score picked the wrong page.
 *
 * Verification is the OUTCOME: fetch the source URL afterwards, confirm a 301 to the new
 * target and that the target itself answers 200.
 */
import { gql, paginate } from '../lib/shopify.js';
import { backup, logChange } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');

const MOVES = [
  { path: '/blogs/saunas/health-benefits-traditional-sauna-vs-infrared-sauna',
    to: '/blogs/saunas/infrared-sauna-benefits', links: 15,
    note: 'PARTIAL — destination is infrared-centred, anchor promises a two-way comparison. If a real infrared-vs-traditional page is ever built, this redirect moves to it.' },
  { path: '/blogs/saunas/harnessing-the-power-of-contrast-therapy-benefits-and-insights',
    to: '/blogs/saunas/contrast-therapy-demystified-human-studies', links: 10, note: '' },
  { path: '/blogs/saunas/the-ultimate-recovery-routine-for-athletes-sauna-and-cold-plunge-essentials',
    to: '/blogs/saunas/benefits-of-cold-plunge-and-sauna', links: 6, note: '' },
  { path: '/blogs/saunas/optimizing-recovery-mastering-the-sauna-and-cold-plunge-routine',
    to: '/blogs/saunas/benefits-of-cold-plunge-and-sauna', links: 4, note: '' },
  { path: '/blogs/saunas/unlocking-the-power-of-cold-plunge-tubs-a-beginner-s-guide',
    to: '/blogs/cold-plunge/at-home-cold-plunge', links: 8,
    note: 'anchor promises orientation, not a shortlist, so the beginner guide beats the buying guides' },
  { path: '/blogs/saunas/health-benefits-of-fire-pits',
    to: '/blogs/fire/backyard-fire-pit-benefits-beyond-warmth', links: 4,
    note: 'END OF A CHAIN: /blogs/home-wellness/health-benefits-of-fire-pits redirects into this path, which then went to "/". Fixing this hop fixes both. NB a near-duplicate destination exists at fire/12-fire-benefits (3,411 words vs 4,355).' },
  { path: '/blogs/saunas/how-to-build-a-home-wellness-spa-your-ultimate-guide',
    to: '/blogs/wellness/renovation-sequencing-wellness-installations', links: 15,
    note: 'WEAKEST CALL, flagged as such and approved on that basis. A partial answer beats the homepage. Revisit if a build-a-spa page is written.' },
  { path: '/blogs/saunas/dynamic-santiago-elite-vs-maxxus-seattle-2-person-sauna-2026',
    to: '/blogs/saunas/best-2-person-sauna-buyers-guide', links: 3,
    note: 'the term score ranked the single-brand Santiago review first; reading found the guide that covers BOTH brands' },
];

/* Existing redirects, so we update rather than create duplicates. */
const existing = await paginate(`query($first:Int,$after:String){ urlRedirects(first:$first, after:$after){ pageInfo{hasNextPage endCursor} nodes{ id path target } } }`, 'urlRedirects', {}, 250);
const byPath = new Map(existing.map((r) => [r.path.replace(/\/$/, ''), r]));

const rows = [];
for (const m of MOVES) {
  const cur = byPath.get(m.path.replace(/\/$/, ''));
  if (!cur) { console.log(`  MISSING redirect for ${m.path} — expected one pointing at "/"`); process.exitCode = 1; continue; }
  if (cur.target !== '/' && cur.target !== 'https://inhousewellness.com/') {
    console.log(`  SKIP ${m.path} — already points at ${cur.target}, not the homepage`); continue;
  }
  const r = await fetch(`https://inhousewellness.com${m.to}`, { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; inh-seo-audit)' } });
  if (r.status !== 200) { console.log(`  TARGET NOT 200 (${r.status}) ${m.to}`); process.exitCode = 1; continue; }
  console.log(`  ${String(m.links).padStart(2)} links  ${m.path.replace('/blogs/', '').slice(0, 56)}`);
  console.log(`            "/"  ->  ${m.to}   [target 200]`);
  if (m.note) console.log(`            note: ${m.note}`);
  rows.push({ id: cur.id, ...m, was: cur.target });
}
if (process.exitCode === 1) { console.log('\n  refusing: a row failed its checks'); process.exit(1); }
if (!APPLY) { console.log(`\n  DRY RUN — ${rows.length} redirects would be repointed. Re-run with --apply.\n`); process.exit(0); }

backup('blog-redirects', rows.map((r) => ({ id: r.id, path: r.path, was: r.was, to: r.to, note: r.note })));

for (const r of rows) {
  const m = await gql(`mutation($id:ID!,$urlRedirect:UrlRedirectInput!){ urlRedirectUpdate(id:$id, urlRedirect:$urlRedirect){
    urlRedirect{ id path target } userErrors{ field message } } }`, { id: r.id, urlRedirect: { path: r.path, target: r.to } });
  if (m.urlRedirectUpdate.userErrors.length) { console.log(`  ERR ${r.path}`, m.urlRedirectUpdate.userErrors); process.exitCode = 1; continue; }
  logChange({ resource: r.id, handle: r.path, field: 'urlRedirect.target', old: r.was, new: r.to, note: `Round 15 nearest live equivalent${r.note ? ' — ' + r.note : ''}` });
}

/* Outcome: what does the URL actually do now? */
console.log('');
let ok = 0;
for (const r of rows) {
  const res = await fetch(`https://inhousewellness.com${r.path}`, { redirect: 'manual', headers: { 'User-Agent': 'Mozilla/5.0 (compatible; inh-seo-audit)' } });
  const loc = res.headers.get('location') || '';
  const good = res.status === 301 && loc.replace('https://inhousewellness.com', '').split('?')[0] === r.to;
  console.log(`  ${good ? 'OK  ' : 'FAIL'}  ${res.status} -> ${loc.replace('https://inhousewellness.com', '') || '(none)'}   ${r.path.split('/').pop().slice(0, 44)}`);
  good ? ok++ : (process.exitCode = 1);
}
console.log(`\n  ${ok} / ${rows.length} now redirect to their nearest live equivalent`);
