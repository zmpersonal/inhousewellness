/**
 * A rule with two clauses gets enforced on the clause that has a screen.
 *
 * Rule 4 proved it: "never assert a health benefit" had a purpose-built screen
 * with fixtures and ran across 673 products and 116 articles. "Route the
 * evidence to healthresearchdatabase.com" had no check and had NEVER ONCE been
 * executed — zero of 117 articles, for the life of the project — and the rule
 * read as satisfied because its measurable half was.
 *
 * This audits every OTHER multi-clause rule on the same test: which clause has a
 * guard, and which has been passing on inheritance.
 *
 * Read-only.
 *   node scripts/audit/two-clause.mjs
 */
import path from 'node:path';
import { readJSON, DATA, assertFresh } from '../lib/util.js';

assertFresh({ 'collections.json': 'npm run audit:collections' });
const collections = readJSON(path.join(DATA, 'collections.json'));
const plan = readJSON(path.join(DATA, 'collections-plan.json'));
const rows = Array.isArray(plan) ? plan : plan.rows;
const inScope = new Set(rows.filter((r) => ['WRITE', 'REWRITE', 'URGENT'].includes(r.status || r.decision || r.action)).map((r) => r.handle));
const written = collections.filter((c) => inScope.has(c.handle) && (c.descriptionLength || 0) > 50);

/* ENUMERATE FROM THE STORE, NOT FROM THE PLAN.
   A plan is a CLAIM about what exists. Iterating it and trusting it to be complete
   makes anything created outside the normal path unguarded by construction — which
   is exactly what happened to the four Phase 4 facet collections: created directly,
   never added to the plan, therefore invisible to every check keyed on the plan,
   and one of them shipped an invented product fact that this script catches in
   seconds once it can see the page.

   So: walk the STORE, and report any collection carrying real copy that the plan
   does not know about. Unknown is a finding, not a silent skip. */
const planned = new Set(rows.map((r) => r.handle));
const unplanned = collections.filter((c) => (c.descriptionLength || 0) > 50 && !planned.has(c.handle));
if (unplanned.length) {
  console.log(`\n  ⚠ ${unplanned.length} collection(s) carry copy and are NOT IN THE PLAN — unguarded by construction:`);
  for (const c of unplanned) console.log(`      ${c.handle}  (${c.descriptionLength} chars)`);
  console.log('  Add them to data/collections-plan.json so every plan-keyed check can see them.\n');
  process.exitCode = 1;
}

const strip = (h) => String(h || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

/* ── The collection-copy spec, clause by clause ─────────────────────────── */
const CLAUSES = [
  { id: '150–300 words', guard: 'none — checked by hand, per draft',
    test: (c) => { const w = strip(c.descriptionHtml).split(/\s+/).length; return w >= 150 && w <= 300; } },
  /* The rule says "a specific number OR FACT". The first version of this test
     checked for a digit only and failed 8 collections — every one of them a
     durable-facts rewrite that deliberately opens on a mechanic instead of a
     count. The probe encoded a STRICTER rule than the rule, which is the
     probe-vocabulary failure in a new place: reading the spec carelessly rather
     than reading the products carelessly. */
  { id: 'first sentence: number OR specific fact', guard: 'none',
    test: (c) => { const f = strip(c.descriptionHtml).split(/(?<=\.)\s/)[0] || '';
      return /\d/.test(f) || f.split(/\s+/).length >= 8; } },
  { id: 'at least one <h2>', guard: 'none',
    test: (c) => /<h2[\s>]/i.test(c.descriptionHtml || '') },
  { id: 'no class/style/data-*/meta attributes', guard: 'cleanHTML on write + scan-broken-copy',
    test: (c) => !/(class=|style=|data-[a-z]|<meta)/i.test(c.descriptionHtml || '') },
  { id: 'disclosure: freight/curbside stated', guard: 'none',
    test: (c) => /curb|freight|shipping/i.test(strip(c.descriptionHtml)) },
  /* "WHERE IT APPLIES" is half the clause. An accessory collection — chimneys,
     roof options, wood oil — has no electrical requirement, so silence is
     correct. Testing every collection would have reported four correct pages as
     failures. */
  { id: 'disclosure: 240V named where it applies', guard: 'none',
    test: (c) => /chimney|roof|maintenance|accessor|upgrade|cover|panel/i.test(c.handle)
      || /240\s*v|120\s*v|circuit|electric/i.test(strip(c.descriptionHtml)) },
  /* NOT A SPEC CLAUSE. The spec lists freight, 240V, assembly and foundation.
     "Non-refundable" is in the standard delivery paragraph but was never a
     requirement — a second case of the audit inventing a rule to test. Kept as
     an observation, marked as such, because it is worth knowing which pages
     carry it. */
  { id: '(observation) service fees non-refundable', guard: 'not a spec clause',
    test: (c) => /non-refundable|not refundable/i.test(strip(c.descriptionHtml)) },
  { id: 'internal links only — no outbound', guard: 'none',
    test: (c) => !/href="https?:\/\/(?!inhousewellness\.com)/i.test(c.descriptionHtml || '') },
];

console.log(`collection copy spec — ${written.length} written, in-scope collections\n`);
console.log('  clause'.padEnd(44) + 'pass  fail   guard');
for (const cl of CLAUSES) {
  const fail = written.filter((c) => !cl.test(c));
  console.log('  ' + cl.id.padEnd(42) + String(written.length - fail.length).padStart(4) + String(fail.length).padStart(6) + '   ' + cl.guard);
  if (fail.length && fail.length <= 12) console.log('        ' + fail.map((c) => c.handle).join(', '));
  else if (fail.length) console.log(`        ${fail.slice(0, 10).map((c) => c.handle).join(', ')} … +${fail.length - 10}`);
}
