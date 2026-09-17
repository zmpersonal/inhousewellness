/* Round 15 — internal links INTO the retargeted cardiovascular page. --dry-run default.
 *
 *   node scripts/apply/apply-cardio-inlinks.mjs [--apply]
 *
 * The page had ONE inbound link and zero impressions. These five sources were chosen by
 * impressions AND by already carrying a sentence the link belongs in: a link is added where
 * the page already makes the claim, never manufactured.
 *
 * Anchor text states what the destination supports — what the cohorts found — never
 * "saunas improve heart health".
 *
 * Every target asserts EXACTLY ONE match. Zero is a FAILURE, not a skip.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const URL = 'https://inhousewellness.com/blogs/saunas/how-saunas-improve-circulation';
const A = (text) => `<a href="${URL}">${text}</a>`;

const EDITS = [
  { handle: 'what-is-a-german-sauna',
    why: 'existing anchor names the OLD title; a rename is a mechanism change we perform',
    from: '>what the circulation research actually shows</a>',
    to: '>what the Finnish cohorts actually found</a>' },

  { handle: 'costco-sauna-guide-worth-it',
    why: 'already cites Laukkanen 2018 for the mortality association',
    from: 'associates frequent use with lower cardiovascular mortality (',
    to: `associates frequent use with lower cardiovascular mortality, though only at four to seven sessions a week. ${A('The intervals, and where the evidence stops')}. (` },

  { handle: 'nurecover-tropic-home-sauna-review',
    why: 'states the outcome list without its design or population',
    from: 'lower risk of cardiovascular and all-cause mortality with frequent use (Instalab, 2025; Laukkanen et al., 2018; Healthline, 2024).</p>',
    to: `lower risk of cardiovascular and all-cause mortality with frequent use (Instalab, 2025; Laukkanen et al., 2018; Healthline, 2024). That evidence is observational and the significant results sit at four to seven sessions a week: ${A('what the Finnish cohorts actually found')}.</p>` },

  { handle: 'heavenly-heat-sauna-review',
    why: 'already says larger studies are needed; the link says how much larger',
    from: 'Larger studies are still needed (PubMed, 2024).</p>',
    to: `Larger studies are still needed (PubMed, 2024). For what the existing cohorts did and did not establish, see ${A('sauna and cardiovascular health')}.</p>` },

  { handle: 'santiago-2-person-ultra-low-emf-sauna-review',
    why: 'already hedged correctly as observational; the link supplies the numbers',
    from: 'in large observational studies of traditional saunas — favorable cardiovascular patterns.',
    to: `in large observational studies of traditional saunas — favorable cardiovascular patterns (${A('the hazard ratios, and the group that missed significance')}).` },
];

const rows = [];
for (const e of EDITS) {
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ id handle body } } }`, { q: `handle:${e.handle}` });
  const a = q.articles.nodes.find((x) => x.handle === e.handle);
  if (!a) { console.log(`  MISSING ${e.handle}`); process.exitCode = 1; continue; }
  const n = a.body.split(e.from).length - 1;
  console.log(`  ${e.handle.padEnd(46)} matches=${n}   ${n === 1 ? '' : 'FAILURE'}`);
  if (n !== 1) { process.exitCode = 1; continue; }
  const after = a.body.replace(e.from, e.to);
  assertWellFormed(after, e.handle);
  const before = (a.body.match(new RegExp(URL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
  const now = (after.match(new RegExp(URL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
  console.log(`     ${e.why}`);
  console.log(`     links to target: ${before} -> ${now}`);
  console.log(`     + ${e.to.replace(/<[^>]+>/g, '').slice(0, 150)}`);
  rows.push({ id: a.id, handle: e.handle, before: a.body, after });
}
if (process.exitCode === 1) { console.log('\n  refusing: a target failed its match count'); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }

backup('cardio-inlinks', rows.map((r) => ({ id: r.id, handle: r.handle, before: r.before })));
for (const r of rows) {
  const m = await gql(`mutation($id:ID!,$article:ArticleUpdateInput!){ articleUpdate(id:$id, article:$article){ article{ id } userErrors{ field message } } }`,
    { id: r.id, article: { body: r.after } });
  if (m.articleUpdate.userErrors.length) { console.log(`  ERR ${r.handle}`, m.articleUpdate.userErrors); process.exitCode = 1; continue; }
  logChange({ resource: r.id, handle: r.handle, field: 'body', old: 'no link to how-saunas-improve-circulation', new: 'internal link added', note: 'Round 15 inbound links for the cardiovascular retarget' });
}

/* Outcome: re-read each source, then count inbound links across the estate. */
let ok = 0;
for (const r of rows) {
  const q = await gql(`query($q:String!){ articles(first:5, query:$q){ nodes{ handle body } } }`, { q: `handle:${r.handle}` });
  const b = q.articles.nodes.find((x) => x.handle === r.handle).body;
  const good = b.includes(URL);
  console.log(`  re-read ${r.handle.padEnd(46)} ${good ? 'OK' : 'FAIL'}`);
  good ? ok++ : (process.exitCode = 1);
}
console.log(`\n  ${ok} / ${rows.length} sources now link to the cardiovascular page`);
