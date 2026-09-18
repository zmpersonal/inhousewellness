/* Restores the one blog meta description that blog-seo.mjs overwrote.
   The copy spec says "Only fill null fields. Do not overwrite an existing meta
   description unless the task says so explicitly." The task did not. A skip
   guard was added for exactly this and it silently did not take effect. */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, logChange } from '../lib/util.js';

/* RETIRED by the Round 18i guard audit (2026-09-18): overwrites the blog meta without checking live still holds the known-bad value.
   It ran once and its specs are consumed, so its guards can no longer be demonstrated against the live estate —
   and a guard that cannot be shown to fail is not a guard. To run it again, delete these lines in a reviewed commit. */
console.error('RETIRED (Round 18i guard audit): restore-blog-meta.mjs — overwrites the blog meta without checking live still holds the known-bad value.'); process.exit(1);
const flags = parseArgs();
banner('restore-blog-meta', flags);
const ORIGINAL = 'Honest reviews of upgraded home improvement projects with real pros, cons, costs, and insights you won’t find anywhere else. Unique, practical, homeowner-focused.';
const r = await gql(`query{ blogs(first:50){ nodes{ id handle d: metafield(namespace:"global", key:"description_tag"){ value } } } }`);
const b = r.blogs.nodes.find((x) => x.handle === 'home-improvement-reviews');
console.log(`  current : ${b.d?.value}`);
console.log(`  restore : ${ORIGINAL}`);
console.log(`  note    : the original is ${ORIGINAL.length} chars, OVER the 155 limit. Restoring it re-introduces a`);
console.log(`            spec violation that predates this session. That is a separate decision from`);
console.log(`            whether I was entitled to overwrite it, and I was not.`);
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
const m = await gql(`mutation($metafields:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$metafields){ metafields{ key } userErrors{ field message } } }`,
  { metafields: [{ ownerId: b.id, namespace: 'global', key: 'description_tag', type: 'single_line_text_field', value: ORIGINAL }] });
if (m.metafieldsSet.userErrors.length) { console.error(m.metafieldsSet.userErrors); process.exit(1); }
logChange({ script: 'restore-blog-meta', kind: 'blog', id: b.id, handle: b.handle, field: 'global.description_tag',
  before: b.d?.value, after: ORIGINAL, reason: 'Restoring an existing meta that blog-seo.mjs overwrote against the copy spec. The skip guard did not take effect and the apply was not checked against the guard.' });
/* verify the OUTCOME, not the write */
const back = await gql(`query{ blogs(first:50){ nodes{ handle d: metafield(namespace:"global", key:"description_tag"){ value } } } }`);
const now = back.blogs.nodes.find((x) => x.handle === 'home-improvement-reviews').d?.value;
console.log(`\n  ${now === ORIGINAL ? 'RESTORED — verified by re-reading, not by the mutation result' : 'FAILED — value is still ' + now}`);
if (now !== ORIGINAL) process.exitCode = 1;   // guard audit 18i: FAILED was print-only
