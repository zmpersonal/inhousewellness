/* Round 23d — the FAQ page's installation answer.
 *   node scripts/apply/r23d-faq-install.mjs [--apply] | --self-test | --restore <backup.json> [--apply]
 *
 * The live answer says installation is NOT provided. The primary source — the installation-assembly
 * product a customer buys — offers it on saunas at $1,800, and 106 sauna accordions now say so. Two
 * sources disagreeing about installation is the defect; this is the second half of the same fix as
 * r23c's V3, and the two strings were written together for that reason.
 *
 * FROM is copied from the live body, never retyped: the apostrophe in "manufacturer's" is U+0027 here
 * while the paragraph above it uses U+2019, and a retyped string would not match.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import { gql } from '../lib/shopify.js';
import { backup, logChange, assertWellFormed } from '../lib/util.js';

const APPLY = process.argv.includes('--apply');
const arg = (k) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const md5 = (s) => crypto.createHash('md5').update(s).digest('hex');
const PAGE = 'gid://shopify/Page/117038710851';

/* EDIT 1, APPLIED 2026-09-26: the "installation is not provided" answer -> "Yes, on saunas".
   Its FROM is spent and is kept here as the record of what ran:
     '<p><strong>Q: Are installation services provided for saunas and hot tubs?</strong><br>A: Installation
      services are not provided directly by us. …manufacturer\'s instructions.</p>'

   EDIT 2, this one: the em dash in edit 1's own text breaks the voice guide's ban on em-dash asides.
   Client's replacement: a full stop and a new sentence. FROM copied from the live body. */
const FROM = 'Premium installation ($1,800) covers everything except electrical work \u2014 local '
  + 'regulations require your own licensed electrician for that.';
const TO = 'Premium installation ($1,800) covers everything except electrical work. Local regulations '
  + 'require your own licensed electrician for that.';

export function edit(body) {
  const hits = body.split(FROM).length - 1;
  if (hits !== 1) throw new Error(`the FROM paragraph appears ${hits}x, want exactly 1`);
  return body.replace(FROM, () => TO);
}
/* everything outside the replaced paragraph must be byte-identical */
export function onlyThatParagraph(before, after) {
  const i = before.indexOf(FROM);
  if (i < 0) return false;
  return before.slice(0, i) === after.slice(0, i)              // everything before it
    && after.slice(i, i + TO.length) === TO                     // exactly the new paragraph
    && before.slice(i + FROM.length) === after.slice(i + TO.length);   // everything after it
}

function selfTest() {
  let bad = 0;
  const eq = (n, g, w) => { if (g !== w) { console.log(`FIXTURE FAIL: ${n} — want ${w} got ${g}`); bad++; } };
  const body = `<h3>x</h3><p>Yes, on saunas. ${FROM} Send us your ZIP code.</p><p>after</p>`;
  const out = edit(body);
  eq('the new sentence lands', out === `<h3>x</h3><p>Yes, on saunas. ${TO} Send us your ZIP code.</p><p>after</p>`, true);
  eq('nothing outside the paragraph moved', onlyThatParagraph(body, out), true);
  eq('a change elsewhere is caught', onlyThatParagraph(body, out.replace('<p>after</p>', '<p>AFTER</p>')), false);
  eq('no em dash survives', out.includes('\u2014'), false);
  eq('the two-sentence form is present once', out.split(TO).length - 1, 1);
  let threw = false; try { edit('<p>nothing here</p>'); } catch { threw = true; }
  eq('a missing FROM refuses rather than no-opping', threw, true);
  threw = false; try { edit(body + FROM); } catch { threw = true; }
  eq('TWO copies of FROM refuse — an ambiguous target is not a target', threw, true);
  /* assertWellFormed EXITS rather than throwing, so a fixture must not drive it: a broken string would
     kill the run instead of failing a test. Balance is counted locally here; the real outgoing string
     still goes through assertWellFormed on the write path, where exiting is correct. */
  const bal = (h, t) => (h.match(new RegExp(`<${t}[ >]`, 'g')) || []).length === (h.match(new RegExp(`</${t}>`, 'g')) || []).length;
  eq('the outgoing string is balanced', ['p', 'strong', 'a'].every((t) => bal(out, t)), true);
  eq('an unbalanced string is caught', ['p'].every((t) => bal(out + '<p>oops', t)), false);
  return bad;
}
const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — refusing`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

const read = async () => (await gql(`query($id:ID!){ page(id:$id){ id title body } }`, { id: PAGE })).page;
const write = async (body) => {
  const r = await gql(`mutation($id:ID!,$p:PageUpdateInput!){ pageUpdate(id:$id, page:$p){ page{ body } userErrors{ message } } }`, { id: PAGE, p: { body } });
  if (r.pageUpdate.userErrors.length) throw new Error(JSON.stringify(r.pageUpdate.userErrors));
  return r.pageUpdate.page.body;
};

const RESTORE = arg('--restore');
if (RESTORE) {
  const s = JSON.parse(fs.readFileSync(RESTORE, 'utf8'))[0];
  const live = md5((await read()).body);
  if (live === s.md5) { console.log('  already restored'); process.exit(0); }
  if (live !== s.storedMd5) { console.log(`  REFUSE: live ${live} is neither the before-state nor what the apply stored — edited since`); process.exit(1); }
  if (!APPLY) { console.log('  would restore the FAQ body'); process.exit(0); }
  const back = md5(await write(s.before));
  const ok = back === s.md5;
  console.log(`  ${ok ? 'RESTORED' : 'FAIL'}  read-back ${back}${ok ? ' == before-state' : ' != ' + s.md5}`);
  if (ok) logChange({ resource: PAGE, handle: 'faq-page', field: 'body', old: 'Round 23d edit', new: 'restored', note: `restore from ${RESTORE}` });
  process.exit(ok ? 0 : 1);
}

const page = await read();
const before = page.body;
let after = edit(before);
if (process.argv.includes('--inject-stray')) after += '<p>INJECTED</p>';
/* --inject-link is not offered: see the note below on why a link guard is subsumed here. */
const probs = [];
if (!onlyThatParagraph(before, after)) probs.push('SOMETHING OUTSIDE THAT ONE PARAGRAPH CHANGED');
/* No separate link guard here, deliberately. onlyThatParagraph is a BYTE comparison over the whole
   body, so it already catches every link change — and a link injection therefore trips it too, which
   means a link guard could never be shown to fail on its own. Subsumed, not skipped. */
if (/not provided directly by us/.test(after)) probs.push('GONE: the pre-edit-1 answer is back');
if (after.includes('\u2014')) probs.push('GONE: an em dash survives in the FAQ body');
for (const s of ['Yes, on saunas', '$1,800', '$600', 'Send us your ZIP code', TO]) {
  const n = after.split(s).length - 1; if (n !== 1) probs.push(`"${s}" appears ${n}x, want 1`);
}
/* Called UNWRAPPED on purpose: assertWellFormed exits, so a try/catch around it never fires and only
   reads as if the failure were handled. Exiting is the right behaviour for an outgoing string. */
if (!probs.length) assertWellFormed(after, 'faq body', before);
console.log(`\n  FAQ body ${before.length} -> ${after.length} chars   md5 ${md5(before)} -> ${md5(after)}`);
console.log(`  - ${FROM.replace(/<[^>]+>/g, ' ').trim().slice(0, 150)}`);
console.log(`  + ${TO.replace(/<[^>]+>/g, ' ').trim().slice(0, 190)}`);
if (probs.length) { probs.forEach((p) => console.log(`  FAIL ${p}`)); console.log('\n  REFUSING — nothing written'); process.exit(1); }
console.log('  every check passed');
if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.'); process.exit(0); }

const snap = [{ id: PAGE, handle: 'faq-page', md5: md5(before), afterMd5: md5(after), before }];
const bpath = backup('r23d-faq-install', snap);
const stored = await write(after);
snap[0].storedMd5 = md5(stored);
fs.writeFileSync(bpath, JSON.stringify(snap, null, 2));
logChange({ script: 'r23d-faq-install', resource: PAGE, handle: 'faq-page', field: 'body', old: 'em-dash aside', new: 'em dash replaced by a full stop and a new sentence', note: `backup ${bpath}` });
console.log(`  WROTE. stored md5 ${snap[0].storedMd5}${snap[0].storedMd5 === snap[0].afterMd5 ? ' = sent' : ' — NORMALISED by the platform'}`);
console.log(`  BACKUP ${bpath}`);
