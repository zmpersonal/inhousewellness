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
 * The changelog decides: if the live value was written by a script OTHER than
 * the one that applies this file, and after the file's mtime, it is STALE.
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
  if (!prev || t > prev.t) lastWrite.set(r.handle, { t, script: r.script, at: r.at });
}

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
  /* STALE only if the live write happened AFTER this file was last touched.
     The first version marked anything ever written by another script as stale
     forever, which flagged steam-showers — cleared on 7 September, drafted
     today — as a revert risk when the draft is strictly newer. */
  const liveNewer = lw && lw.t > mtime;
  const state = liveNewer ? 'STALE — applying would REVERT live' : 'PENDING — staged edit not yet applied';

  rows.push({ handle, file: f, approved, state, delta: staged.length - current.length,
    stagedLen: staged.length, liveLen: current.length,
    lastLiveWrite: lw ? `${lw.script} @ ${lw.at.slice(0, 19)}` : '(never logged)' });
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
