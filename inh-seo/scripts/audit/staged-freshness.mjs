/**
 * Does staged copy still match the live value it claims to represent?
 *
 * `assertFresh` compares DUMPS against the changelog and refuses to write from a
 * stale one. It has no opinion about `content/`. On 9 September a bulk
 * `apply-collection-copy` reverted three C4 cluster links because the staged
 * markdown was EIGHT DAYS older than the store and nothing knew (instance 55).
 *
 * So every staged file in this repo is a regression waiting for someone to apply
 * it, and this counts them.
 *
 * A difference is NOT automatically a defect. There are three states and only a
 * human can tell them apart:
 *
 *   PENDING   staged is newer — an approved edit not yet applied
 *   STALE     LIVE is newer — applying would REVERT an out-of-band edit
 *   UNKNOWN   both changed, or the change cannot be attributed
 *
 * The changelog decides: if the live value was last written AFTER the file's
 * mtime — by any script — it is STALE. (Round 18i: this comment used to say
 * "by a script OTHER than the one that applies this file"; the code has never
 * checked the script, deliberately — see the note at the STALE rule below.)
 *
 * WARN-ONLY no longer: exits 1 when any row is STALE, because a STALE row is an
 * apply that would revert live work.
 *
 * Read-only.
 *   node scripts/audit/staged-freshness.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, CONTENT, cleanHTML, assertFresh } from '../lib/util.js';

/* This audit compares staged copy against a DUMP of live. A stale dump makes it
   report the state before the last apply — it reported two collections as still
   reverted minutes after they had been restored. The guard that exists for
   writes applies to a read whose whole purpose is comparison. */
assertFresh({ 'collections.json': 'npm run audit:collections' });

const collections = readJSON(path.join(DATA, 'collections.json'));
const byHandle = new Map(collections.map((c) => [c.handle, c]));
const log = fs.readFileSync(path.join(DATA, 'changelog.jsonl'), 'utf8').trim().split('\n').map((l) => JSON.parse(l));

/* last mutation to this handle's description, and which script made it */
const lastWrite = new Map();
for (const r of log) {
  if (!r.handle || r.field !== 'descriptionHtml') continue;
  const t = new Date(r.at).getTime();
  const prev = lastWrite.get(r.handle);
  if (!prev || t > prev.t) lastWrite.set(r.handle, { t, script: r.script, at: r.at, note: r.note });
}

/* The state rule and the label, as pure functions so fixtures can hold them to account. */
/* STALE only if the live write happened AFTER this file was last touched.
   The first version marked anything ever written by another script as stale
   forever, which flagged steam-showers — cleared on 7 September, drafted
   today — as a revert risk when the draft is strictly newer. */
const stateOf = (lw, mtime) => (lw && lw.t > mtime) ? 'STALE — applying would REVERT live' : 'PENDING — staged edit not yet applied';
/* Log rows are not a schema; some carry no `script`. Print what IS known, never "undefined". */
const writeLabel = (lw) => !lw ? '(never logged)'
  : `${lw.script || '(script not recorded)'} @ ${lw.at ? String(lw.at).slice(0, 19) : '(time not recorded)'}${lw.note ? ` — ${String(lw.note).slice(0, 60)}` : ''}`;
// 18i: constructed fixtures — the STALE rule and the label must hold before any row is judged
const SFIX = [
  ['live written after the file is STALE',     stateOf({ t: 2000 }, 1000).startsWith('STALE')],
  ['live written before the file is PENDING',  stateOf({ t: 500 }, 1000).startsWith('PENDING')],
  ['never logged is PENDING',                  stateOf(undefined, 1000).startsWith('PENDING')],
  ['a row with no script prints no undefined', !/undefined/.test(writeLabel({ t: 1, at: '2026-09-18T14:07:28.925Z', note: 'backup /x' }))],
  ['a row with a script names it',             writeLabel({ t: 1, script: 'apply-collection-copy', at: '2026-09-09T10:00:00Z' }) === 'apply-collection-copy @ 2026-09-09T10:00:00'],
];
const sbad = SFIX.filter(([, ok]) => !ok);
for (const [l, ok] of SFIX) if (!ok) console.error(`  FIXTURE FAIL ${l}`);
if (sbad.length) { console.error('refusing — staged-freshness fixtures did not hold'); process.exit(1); }

const dir = path.join(CONTENT, 'collections');
/* Only files that are actually STAGING copy. A report that happens to live in
   this directory and carries `handle:` in its front matter was scanned as if it
   were copy, and its 4,179-character body reported as a 2,504-char divergence
   from live. A directory is not a schema. */
const files = fs.readdirSync(dir)
  .filter((f) => f.endsWith('.md') && !/\.[A-Z]+\.md$/.test(f))
  .filter((f) => /^status:/m.test(fs.readFileSync(path.join(dir, f), 'utf8')));
const rows = [];
const claimed = new Map();

for (const f of files) {
  const p = path.join(dir, f);
  const raw = fs.readFileSync(p, 'utf8');
  const handle = (raw.match(/^handle:\s*(\S+)/m) || [])[1] || f.replace(/\.md$/, '');
  const approved = /^status:\s*approved\s*$/m.test(raw);
  if (claimed.has(handle)) console.error(`  !! ${f} and ${claimed.get(handle)} both claim handle "${handle}"`);
  claimed.set(handle, f);
  const live = byHandle.get(handle);
  if (!live) { rows.push({ handle, file: f, state: 'NO LIVE COLLECTION', approved }); continue; }

  /* body is everything after the second --- fence */
  const parts = raw.split(/^---\s*$/m);
  const body = parts.slice(2).join('---').trim();
  if (!body) { rows.push({ handle, file: f, state: 'NO BODY', approved }); continue; }

  const staged = cleanHTML(body);
  const current = String(live.descriptionHtml || '');
  /* Markdown keeps newlines BETWEEN block tags; Shopify stores them stripped.
     Collapsing whitespace turns "</p>\n<h2>" into "</p> <h2>" and leaves it
     differing from "</p><h2>" by one character per boundary — which reported 50
     collections as stale on a uniform +6/+8 delta. A uniform delta across a set
     is a signature, not fifty findings. */
  const norm = (h) => h.replace(/>\s+</g, '><').replace(/\s+/g, ' ').trim();
  const same = norm(staged) === norm(current);

  if (same) { rows.push({ handle, file: f, state: 'MATCHES', approved, delta: 0 }); continue; }

  const mtime = fs.statSync(p).mtimeMs;
  const lw = lastWrite.get(handle);
  /* live written by something other than the copy applier, after this file was
     last touched -> applying this file would revert that write */
  const state = stateOf(lw, mtime);   // rule and its reason: see stateOf above

  rows.push({ handle, file: f, approved, state, delta: staged.length - current.length,
    stagedLen: staged.length, liveLen: current.length,
    lastLiveWrite: writeLabel(lw) });
}

const matches = rows.filter((r) => r.state === 'MATCHES');
const differ = rows.filter((r) => r.state.startsWith('STALE') || r.state.startsWith('PENDING'));
const other = rows.filter((r) => !['MATCHES'].includes(r.state) && !differ.includes(r));

console.log(`staged collection files: ${files.length}   approved: ${rows.filter((r) => r.approved).length}\n`);
console.log(`  MATCHES live      : ${matches.length}`);
console.log(`  DIFFERS from live : ${differ.length}`);
console.log(`  other             : ${other.length}\n`);

for (const r of differ.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))) {
  console.log(`  ${r.state.startsWith('STALE') ? '!!' : '  '} ${r.handle.padEnd(28)} staged ${String(r.stagedLen).padStart(5)}ch  live ${String(r.liveLen).padStart(5)}ch  delta ${(r.delta >= 0 ? '+' : '') + r.delta}`);
  console.log(`     ${r.state}   last live write: ${r.lastLiveWrite}`);
}
for (const r of other) console.log(`  ?? ${r.handle.padEnd(28)} ${r.state}`);

fs.writeFileSync(path.join(DATA, 'staged-freshness.json'), JSON.stringify({ _meta: { ran: new Date().toISOString() }, rows }, null, 2));
console.log('\nwrote data/staged-freshness.json');
/* Round 18i: exit non-zero on STALE. A report nobody reads is how three links disappeared. */
const stale = rows.filter((r) => r.state.startsWith('STALE'));
if (stale.length) { console.error(`\n${stale.length} STALE — applying these would revert live: ${stale.map((r) => r.handle).join(', ')}`); process.exitCode = 1; }
