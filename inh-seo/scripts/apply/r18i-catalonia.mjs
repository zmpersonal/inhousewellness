/* Round 18i — Catalonia spec gap (client-approved): add the operating temperature and indoor placement to the LIVE
 * $9,999 listing so the golden-designs-saunas-review claims ("~140°F", "Indoor", "Indoor-only") are supported by
 * the product the article links to. The PRODUCT changes, not the article.
 *
 * SOURCE (rule 6: product facts come from our data or not at all): our own ARCHIVED listing of the SAME MODEL,
 * catalonia-8p-infrared-sauna (GDI-6880-02 Elite), which states "a typical operating range of 118°F–132°F, with the
 * sauna able to heat up to 140°F" and "an 8-person Near Zero EMF FAR infrared indoor sauna". The new sentence
 * restates those two facts and nothing else. Not added: the article's "placing them outside voids the warranty",
 * which no listing of ours states.
 *
 * Same proofs as the article editors: exact unique anchor; link multiset unchanged; visible text outside the
 * declared insert byte-identical; PRESENT checks for the outcome; well-formed against the before-state; md5 backup
 * with what Shopify STORED; injections that must land. Run it through scripts/apply/r18i-article-proof.sh.
 *   node scripts/apply/r18i-catalonia.mjs [--apply] [--only <handle>] [--inject-stray|--inject-link]
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const HANDLE = 'golden-designs-gdi-6880-02-elite-catalonia';
const ONLY = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : HANDLE;
if (ONLY !== HANDLE) { console.log(`REFUSING: this script edits ${HANDLE} only`); process.exit(1); }
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const visible = (b) => b.replace(/<[^>]*>/g, '');
const hrefs = (b) => [...b.matchAll(/<a\b[^>]*?href="([^"]+)"/gi)].map((m) => m[1]);

// ANCHOR copied from the live body (the end of the paragraph carrying the electrical requirement), never retyped.
const AFTER = 'making professional installation advisable.</p>';
const INSERT = '\n<p>The Catalonia Elite is an <strong>indoor</strong> sauna. Its typical operating range is 118°F–132°F, and it heats up to 140°F.</p>';
const PRESENT = ['indoor</strong> sauna', '118°F–132°F', 'heats up to 140°F'];

const p = (await gql(`query($h:String!){ productByHandle(handle:$h){ id handle status descriptionHtml } }`, { h: HANDLE })).productByHandle;
if (!p) { console.log(`REFUSING: ${HANDLE} not found`); process.exit(1); }
if (p.status !== 'ACTIVE') { console.log(`REFUSING: ${HANDLE} is ${p.status}, not the live listing`); process.exit(1); }
const problems = [];
let body = p.descriptionHtml;
for (const s of PRESENT) if (body.includes(s)) problems.push(`already carries "${s}" — nothing to add, or the spec is stale`);
const n = body.split(AFTER).length - 1;
if (n !== 1) problems.push(`anchor matched ${n}x, want 1`);
body = body.replace(AFTER, AFTER + INSERT);
const mB = p.descriptionHtml.replace(AFTER, AFTER + '⟦0⟧');
if (process.argv.includes('--inject-stray')) { if (APPLY) process.exit(1); const b0 = body; body = body.replace('<p>', '<p>X'); if (body === b0) { console.log('refusing: injection did not land'); process.exit(1); } }
if (process.argv.includes('--inject-link')) { if (APPLY) process.exit(1); const b1 = body; body = body.replace('</p>', '<a href="https://example.com/x"></a></p>'); if (body === b1) { console.log('refusing: injection did not land'); process.exit(1); } }
const mA = body.replace(INSERT, '⟦0⟧');
if (visible(mB) !== visible(mA)) problems.push('TEXT OUTSIDE THE DECLARED CHANGES MOVED');
if (JSON.stringify(hrefs(p.descriptionHtml).sort()) !== JSON.stringify(hrefs(body).sort())) problems.push('LINK MULTISET moved beyond the declared changes');
for (const s of PRESENT) if (body.split(s).length - 1 !== 1) problems.push(`PRESENT check: "${s}" appears ${body.split(s).length - 1}x after, want 1`);
try { assertWellFormed(body, HANDLE, p.descriptionHtml); } catch (e) { problems.push('wellformed: ' + e.message.slice(0, 80)); }
console.log(`\n── ${HANDLE}  (product description)`);
console.log(`   insert   after: …${AFTER.slice(0, 50)}`);
console.log(`      before: (nothing)`);
console.log(`      after : ${visible(INSERT).trim()}`);
console.log(`   links ${hrefs(p.descriptionHtml).length} -> ${hrefs(body).length}   text outside declared insert: ${visible(mB) === visible(mA) ? 'BYTE-IDENTICAL' : 'MOVED'}`);
if (problems.length) { problems.forEach((x) => console.log('   FAIL ' + x)); console.log('\n  REFUSING'); process.exit(1); }
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }
const snap = [{ kind: 'product', id: p.id, handle: HANDLE, md5: md5(p.descriptionHtml), afterMd5: md5(body), before: p.descriptionHtml }];
const bpath = backup('r18i-catalonia', snap);
const m = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ descriptionHtml } userErrors{ message } } }`, { p: { id: p.id, descriptionHtml: body } });
if (m.productUpdate.userErrors.length) { console.log('  ERR', m.productUpdate.userErrors); process.exit(1); }
snap[0].storedMd5 = md5(m.productUpdate.product.descriptionHtml);
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
logChange({ resource: p.id, handle: HANDLE, field: 'descriptionHtml', old: 'Round 18i before-state', new: 'indoor + 118–132°F / up to 140°F, sourced from catalonia-8p-infrared-sauna', note: `backup ${bpath}` });
console.log(`  wrote ${HANDLE}  stored ${snap[0].storedMd5 === snap[0].afterMd5 ? '= sent' : 'NORMALISED'}\n  BACKUP ${bpath}`);
