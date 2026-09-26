/* Round 23f — the White Glove product description.
 *   node scripts/apply/r23f-whiteglove.mjs [--apply] | --self-test | --restore <backup.json> [--apply]
 *
 * Client ruling 2026-09-26: White Glove DOES cover items other than saunas, so the 127 non-sauna
 * offers are correct and the defect is this product's own copy, which said "your sauna delivery
 * experience" and "the sauna will be carried inside your home". This is the primary source for 258
 * accordions, so it is fixed here first and the panels follow.
 *
 * ⚠️ This is a WHOLE-DESCRIPTION replacement, so there is no "outside the edited region" to compare.
 * The identity guard other Round 23 scripts rely on does not apply, and saying so matters: the guards
 * below are FACT-RETENTION checks instead — every commercial term in the old copy must survive, and
 * the banned constructions must be gone. That is a weaker guarantee than byte identity and it is the
 * strongest one available for a rewrite.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const HANDLE = 'white-glove-delivery-service';
const LIVE_MD5 = process.env.WG_LIVE_MD5 || '';
const AFTER = fs.readFileSync('/private/tmp/wg-after.html', 'utf8').trim();
const EM = '—';

/* every commercial term in the old copy, which the rewrite must still carry */
const MUST_KEEP = ['48 hours before delivery', 'non-refundable', '2–5 business days', 'Haul-Away',
  'protective equipment', 'original packaging', 'Inside Delivery', 'Multi-Level Placement'];
const MUST_GO = ['Upgrade your sauna delivery experience', 'The sauna will be carried inside your home',
  'does not include wiring or connecting the sauna to power', EM];

export function check(before, after) {
  const probs = [];
  for (const s of MUST_KEEP) { const n = after.split(s).length - 1; if (n < 1) probs.push(`LOST: "${s}" is in the old copy and not the new`); }
  for (const s of MUST_GO) if (after.includes(s)) probs.push(`GONE-check: "${s.slice(0, 40)}" survives`);
  const saunas = (after.match(/sauna/gi) || []).length;
  if (saunas > 1) probs.push(`"sauna" appears ${saunas}x, want at most 1 (the Premium Installation route)`);
  if (saunas < 1) probs.push('the Premium Installation route for saunas was removed — a reader with a sauna is left with nowhere to go');
  const links = (s) => (s.match(/href="[^"]*"/g) || []).sort().join('|');
  if (links(before) !== links(after)) probs.push('LINK SET CHANGED');
  /* assertWellFormed EXITS rather than throwing, so it cannot be used inside a probe a fixture drives.
     Balance is counted locally here; the real outgoing string still goes through assertWellFormed below,
     where exiting is the correct behaviour. */
  for (const t of ['p', 'li', 'ul', 'h4', 'strong', 'a']) {
    const o = (after.match(new RegExp(`<${t}[ >]`, 'g')) || []).length;
    const c = (after.match(new RegExp(`</${t}>`, 'g')) || []).length;
    if (o !== c) probs.push(`<${t}> ${o} open / ${c} close — unbalanced, and the platform would silently repair it`);
  }
  return probs;
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  const OLD = '<p>Upgrade your sauna delivery experience with our sauna service</p>';
  eq('the real rewrite passes', check(OLD, AFTER).length, 0);
  eq('dropping a commercial term is caught', check(OLD, AFTER.replace('48 hours before delivery', 'some time')).length > 0, true);
  eq('an em dash is caught', check(OLD, AFTER.replace('. It stays', ` ${EM} it stays`)).length > 0, true);
  eq('leaving the stock opener in is caught', check(OLD, AFTER + '<p>Upgrade your sauna delivery experience</p>').length > 0, true);
  eq('removing the sauna route entirely is caught', check(OLD, AFTER.replace(/sauna/gi, 'unit')).length > 0, true);
  eq('sauna-flavoured copy coming back is caught', check(OLD, AFTER.replace('the item you ordered', 'your sauna and your sauna')).length > 0, true);
  eq('a new link is caught', check(OLD, AFTER + '<p><a href="https://x.test">x</a></p>').length > 0, true);
  eq('unbalanced markup is caught', check(OLD, AFTER + '<p>oops').length > 0, true);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

const read = async () => (await gql(`query($h:String!){ productByHandle(handle:$h){ id title descriptionHtml } }`, { h: HANDLE })).productByHandle;
const write = async (id, html) => {
  const r = await gql(`mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ descriptionHtml } userErrors{ message } } }`, { p: { id, descriptionHtml: html } });
  if (r.productUpdate.userErrors.length) throw new Error(JSON.stringify(r.productUpdate.userErrors));
  return r.productUpdate.product.descriptionHtml;
};

const RESTORE = arg('--restore');
if (RESTORE) {
  const s = JSON.parse(fs.readFileSync(RESTORE, 'utf8'))[0];
  const live = md5((await read()).descriptionHtml);
  if (live === s.md5) { console.log('  already restored'); process.exit(0); }
  if (live !== s.storedMd5) { console.log(`  REFUSE: live ${live} is neither the before-state nor what the apply stored — edited since`); process.exit(1); }
  if (!APPLY) { console.log('  would restore the description'); process.exit(0); }
  const back = md5(await write(s.id, s.before));
  const ok = back === s.md5;
  console.log(`  ${ok ? 'RESTORED' : 'FAIL'}  read-back ${back}${ok ? ' == before-state' : ' != ' + s.md5}`);
  if (ok) logChange({ resource: s.id, handle: HANDLE, field: 'descriptionHtml', old: 'Round 23f rewrite', new: 'restored', note: `restore from ${RESTORE}` });
  process.exit(ok ? 0 : 1);
}

const p = await read();
const before = p.descriptionHtml;
if (LIVE_MD5 && md5(before) !== LIVE_MD5) { console.log(`REFUSING: live is ${md5(before)}, expected ${LIVE_MD5}`); process.exit(1); }
let after = AFTER;
if (process.argv.includes('--inject-stray')) after += '<p>Upgrade your sauna delivery experience</p>';
if (process.argv.includes('--inject-link')) after = after.replace('</p>\n<h4>', '<a href="https://example.com/x"></a></p>\n<h4>');
const probs = check(before, after);
console.log(`\n  ${p.title}: ${before.length} -> ${after.length} chars   md5 ${md5(before)} -> ${md5(after)}`);
console.log(`  "sauna": ${(before.match(/sauna/gi) || []).length} -> ${(after.match(/sauna/gi) || []).length}   em dashes: ${(before.split(EM).length - 1)} -> ${(after.split(EM).length - 1)}`);
if (probs.length) { probs.forEach((x) => console.log(`  FAIL ${x}`)); console.log('\n  REFUSING — nothing written'); process.exit(1); }
assertWellFormed(after, 'white glove description', before);   // exits on failure, which is right for the real string
console.log('  every fact-retention check passed, and the outgoing string is well formed');
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = [{ id: p.id, handle: HANDLE, md5: md5(before), afterMd5: md5(after), before }];
const bpath = backup('r23f-whiteglove', snap);
const stored = await write(p.id, after);
snap[0].storedMd5 = md5(stored);
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
logChange({ script: 'r23f-whiteglove', resource: p.id, handle: HANDLE, field: 'descriptionHtml', old: 'sauna-scoped copy', new: 'covers the item you ordered; electrical/gas/plumbing excluded', note: `backup ${bpath}` });
console.log(`  WROTE. stored md5 ${snap[0].storedMd5}${snap[0].storedMd5 === snap[0].afterMd5 ? ' = sent' : ' — NORMALISED by the platform'}`);
console.log(`  BACKUP ${bpath}`);
