/* Round 14 — file-level alt text for 16 homepage images. --dry-run default.
 *
 * Alt belongs to the FILE, and a file can be referenced from more than one
 * template. Usage was enumerated on MAIN before drafting (see data/file-alts.json
 * note): the benefits icon also renders on three product templates.
 *
 * Only fills an empty alt. A file whose live alt is not "" is HELD and printed:
 * something other than us wrote it.
 *
 * Verification is a SEPARATE read from the Files library after the write, never
 * the mutation payload.
 */
import { gql } from '../lib/shopify.js';
import { backup, logChange, readJSON, DATA, assertOneWritePerRecord } from '../lib/util.js';
import path from 'node:path';

const APPLY = process.argv.includes('--apply');
const { rows } = readJSON(path.join(DATA, 'file-alts.json'));

assertOneWritePerRecord(rows, (r) => r.id, 'file alts');
if (rows.length !== 16) throw new Error(`expected 16 rows, got ${rows.length}`);
for (const r of rows) {
  if (!r.alt.trim() || r.alt.length > 125) throw new Error(`bad alt length on ${r.filename}`);
  if (/undefined|null|\[object/.test(r.alt)) throw new Error(`JS artefact on ${r.filename}`);
}
if (new Set(rows.map((r) => r.alt)).size !== rows.length) throw new Error('duplicate alt in batch');

const readLive = async () => {
  const q = await gql(`query($ids:[ID!]!){ nodes(ids:$ids){ ... on MediaImage { id alt image { url } } } }`,
    { ids: rows.map((r) => r.id) });
  return new Map(q.nodes.filter(Boolean).map((n) => [n.id, n]));
};

/* Pure classifier, so the hold-back guard can be proved on constructed cases. */
function classify(rows, live) {
  const todo = [], held = [], done = [];
  for (const r of rows) {
    const n = live.get(r.id);
    if (!n) throw new Error(`file not found: ${r.filename}`);
    if (!n.image.url.includes(r.filename.replace(/\.[a-z]+$/i, ''))) throw new Error(`id/filename mismatch: ${r.filename} -> ${n.image.url}`);
    if (n.alt === r.alt) done.push(r);
    else if (n.alt !== '' && n.alt !== null) held.push({ ...r, was: n.alt });
    else todo.push({ ...r, was: n.alt });
  }
  return { todo, held, done };
}

/* SELF-TEST — constructed fixtures, never live content. Fails the run. */
{
  const fx = [
    { id: 'A', filename: 'a.png', alt: 'new A' },
    { id: 'B', filename: 'b.png', alt: 'new B' },
    { id: 'C', filename: 'c.png', alt: 'new C' },
    { id: 'D', filename: 'd.png', alt: 'new D' },
  ];
  const lv = new Map([
    ['A', { alt: '', image: { url: 'https://x/a.png' } }],                 // empty -> WRITE
    ['B', { alt: 'hand-written by a person', image: { url: 'https://x/b.png' } }], // other -> HELD
    ['C', { alt: 'new C', image: { url: 'https://x/c.png' } }],            // ours -> SAME
    ['D', { alt: null, image: { url: 'https://x/d.png' } }],               // null -> WRITE
  ]);
  const t = classify(fx, lv);
  const got = `todo=${t.todo.map((r) => r.id)} held=${t.held.map((r) => r.id)} done=${t.done.map((r) => r.id)}`;
  const want = 'todo=A,D held=B done=C';
  let mis = false;
  try { classify([{ id: 'A', filename: 'z.png', alt: 'x' }], lv); } catch { mis = true; }
  if (got !== want || !mis) throw new Error(`SELF-TEST FAILED: ${got} (want ${want}), mismatch-guard ${mis}`);
  console.log(`  self-test: ${got}  filename-mismatch refused: ${mis}`);
}

const live = await readLive();
const { todo, held, done } = classify(rows, live);
for (const r of todo) console.log(`  WRITE  ${r.kind.padEnd(5)} ${JSON.stringify(r.was)} -> ${JSON.stringify(r.alt)}`);
for (const r of done) console.log(`  SAME   ${r.kind.padEnd(5)} ${r.filename}`);
for (const r of held) console.log(`  HELD   ${r.kind.padEnd(5)} ${r.filename} live alt ${JSON.stringify(r.was)}`);
console.log(`\n  write ${todo.length}   already ${done.length}   held ${held.length}`);
if (held.length) { console.log('  refusing: held rows need a read'); process.exit(1); }

if (!APPLY) { console.log('\n  DRY RUN — nothing written. Re-run with --apply.\n'); process.exit(0); }
if (!todo.length) process.exit(0);

const bpath = backup('file-alts', todo.map((r) => ({ id: r.id, filename: r.filename, was: r.was })));
console.log(`  backup -> ${bpath}`);

const res = await gql(`mutation($files:[FileUpdateInput!]!){ fileUpdate(files:$files){
    files{ id } userErrors{ field message code } } }`,
  { files: todo.map((r) => ({ id: r.id, alt: r.alt })) });
if (res.fileUpdate.userErrors.length) {
  res.fileUpdate.userErrors.forEach((e) => console.log(`  ERR ${e.code || ''} ${e.message}`));
  process.exit(1);
}

/* Outcome, not payload: re-read from the Files library. */
await new Promise((r) => setTimeout(r, 3000));
const after = await readLive();
let ok = 0, fail = 0;
for (const r of todo) {
  const got = after.get(r.id)?.alt;
  if (got === r.alt) {
    ok++;
    logChange({ resource: r.id, field: 'alt', old: r.was, new: r.alt, note: `Round 14 file alt ${r.filename}` });
  } else { fail++; console.log(`  FAIL   ${r.filename} reads ${JSON.stringify(got)}`); }
}
console.log(`\n  re-read from Files library: ${ok} match, ${fail} fail`);
if (fail) process.exitCode = 1;
