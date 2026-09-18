/**
 * Restores five SEO titles that `apply-seo-fields.js` nulled.
 *
 * THE BUG: Shopify's `collectionUpdate` treats the `seo` input as a WHOLE
 * OBJECT. Sending `seo: { description: "..." }` with no `title` sets the title
 * to null. The script builds `seo` from whichever fields the plan supplies, so
 * writing a meta description to a collection that already had a title silently
 * deleted the title — and `showDiff` printed only the description, because the
 * script did not know it was making a second change.
 *
 * A diff that shows one change while the mutation makes two is worse than no
 * diff: it is a review that certifies the wrong thing.
 *
 *   node scripts/apply/restore-seo-titles.mjs [--apply]
 */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange } from '../lib/util.js';

/* RETIRED by the Round 18i guard audit (2026-09-18): restores from a snapshot without checking live, and never re-reads both seo fields.
   It ran once and its specs are consumed, so its guards can no longer be demonstrated against the live estate —
   and a guard that cannot be shown to fail is not a guard. To run it again, delete these lines in a reviewed commit. */
console.error('RETIRED (Round 18i guard audit): restore-seo-titles.mjs — restores from a snapshot without checking live, and never re-reads both seo fields.'); process.exit(1);

const flags = parseArgs();
banner('restore-seo-titles', flags);

const RESTORE = {
  'sauna-heaters':        'Sauna Heaters | 95 Electric & Wood, 4kW to 40kW',
  'infrared-saunas':      'Infrared Saunas | 1–8 Person, Most Plug Into a 120V Outlet',
  'harvia-sauna-heaters': 'Harvia Sauna Heaters | 36 Models, 4.5kW to 40kW',
  'full-spectrum':        'Full Spectrum Infrared Saunas | Near and Mid on Top of Far',
  'ultra-low-emf':        'Ultra Low EMF Saunas | 3–5 mG Measured | InHouse Wellness',
};

const targets = [];
for (const [handle, title] of Object.entries(RESTORE)) {
  const r = await gql(`query($h:String!){ collectionByHandle(handle:$h){ id handle seo{ title description } } }`, { h: handle });
  const c = r.collectionByHandle;
  if (c.seo.title) { console.log(`  = ${handle}: title already present, skipping`); continue; }
  if (!c.seo.description) { console.error(`  ! ${handle}: description missing too — investigate before restoring`); continue; }
  console.log(`  + ${handle}`);
  console.log(`      title:       ${title}`);
  console.log(`      description: ${c.seo.description.slice(0, 70)}… (preserved)`);
  targets.push({ c, title });
}
if (!targets.length) { console.log('\nNothing to restore.'); process.exit(0); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }

backup('seo-titles-restore-before', targets.map((t) => ({ id: t.c.id, handle: t.c.handle, seo: t.c.seo })));
let ok = 0;
for (const t of targets) {
  /* BOTH fields, always. That is the fix. */
  const m = await gql(`mutation($input:CollectionInput!){ collectionUpdate(input:$input){ collection{ id } userErrors{ field message } } }`,
    { input: { id: t.c.id, seo: { title: t.title, description: t.c.seo.description } } });
  if (m.collectionUpdate.userErrors.length) { console.error(`  FAILED ${t.c.handle}:`, m.collectionUpdate.userErrors); process.exitCode = 1; continue; }  /* guard audit 18i: a failed write must fail the run */
  logChange({ script: 'restore-seo-titles', kind: 'collection', id: t.c.id, handle: t.c.handle, field: 'seo',
    before: { title: null, description: t.c.seo.description }, after: { title: t.title, description: t.c.seo.description },
    reason: 'Restoring a title nulled by apply-seo-fields.js sending a partial seo object. Shopify treats seo as a whole object.' });
  ok += 1; console.log(`  restored ${t.c.handle}`);
}
console.log(`\n${ok}/${targets.length} restored.`);
