/* The one sanctioned RESTORE path, the way backup() is the one sanctioned writer.
 *
 * WHY. scripts/audit/restore-branch.mjs found 53 write scripts that back up and cannot restore, 16 of
 * them already written to the store. "We can undo this" was resting on a directory nobody had read
 * back. r23h proved the cost: no --restore branch, so the proof runner's cleanup trap had nothing to
 * call and 12 products were left edited.
 *
 * The VALUABLE part is the decision, not the write, and it is shared:
 *   live == the recorded before-state        -> already restored, do nothing
 *   live == what the apply recorded storing  -> restore, then assert the read-back equals before
 *   live == neither                          -> REFUSE. Something edited it since, and overwriting
 *                                               that would revert someone else's work silently.
 * Per-shape adapters supply only read, write and identity. It THROWS rather than exits, so a fixture
 * can drive it (scripts/audit/exit-vs-throw.mjs records why that matters).
 */

/* An adapter is { label, key, readLive, writeBack, describe, storedOf }.
   storedOf is optional: where an apply recorded what the platform stored, which is what makes the
   third case distinguishable from the second. Without it a restore can only recognise
   already-restored, and must refuse everything else rather than guess. */
export async function restoreRows(rows, adapter, { apply = false, only = null, log = console.log } = {}) {
  if (!Array.isArray(rows) || !rows.length) throw new Error('restore: the backup holds no rows');
  if (typeof adapter?.readLive !== 'function' || typeof adapter?.writeBack !== 'function') {
    throw new Error('restore: the adapter must supply readLive and writeBack');
  }
  const out = { restored: [], already: [], refused: [], failed: [], skipped: [] };
  for (const row of rows) {
    const k = adapter.key(row);
    if (only && k !== only) { out.skipped.push(k); continue; }
    let live;
    try { live = await adapter.readLive(row); }
    catch (e) { out.failed.push(k); log(`  UNREADABLE ${k}: ${e.message.slice(0, 90)}`); continue; }
    const want = adapter.describe(row);
    if (live === want) { out.already.push(k); log(`  already restored  ${k}`); continue; }
    const stored = adapter.storedOf ? adapter.storedOf(row) : null;
    if (stored == null || live !== stored) {
      out.refused.push(k);
      log(stored == null
        ? `  REFUSE ${k}: this backup records no stored value, so a restore cannot be told apart from overwriting a later edit. THIS REFUSAL IS THE MODULE WORKING, not a bug — the before-state is on disk and a person can apply it after checking what live holds.`
        : `  REFUSE ${k}: live matches neither the before-state nor what the apply recorded storing, so something edited it since. Overwriting would revert that silently. THIS REFUSAL IS THE CORRECT OUTCOME.`);
      continue;
    }
    if (!apply) { out.restored.push(k); log(`  would restore     ${k}`); continue; }
    let back;
    try { back = await adapter.writeBack(row); }
    catch (e) { out.failed.push(k); log(`  FAILED ${k}: ${e.message.slice(0, 90)}`); continue; }
    if (back === want) { out.restored.push(k); log(`  RESTORED ${k}  read-back matches the before-state`); }
    else { out.failed.push(k); log(`  FAILED ${k}: read-back does not match the before-state`); }
  }
  return out;
}

export const RESTORE_FIXTURES = [
  ['live already equals the before-state -> already, no write', async () => {
    let wrote = false;
    const r = await restoreRows([{ k: 'a', before: 'X' }], { key: (x) => x.k, describe: (x) => x.before, storedOf: () => 'Y',
      readLive: async () => 'X', writeBack: async () => { wrote = true; return 'X'; } }, { apply: true, log: () => {} });
    return r.already.length === 1 && wrote === false;
  }, true],
  ['live equals the stored value -> restores', async () => {
    const r = await restoreRows([{ k: 'a', before: 'X', stored: 'Y' }], { key: (x) => x.k, describe: (x) => x.before, storedOf: (x) => x.stored,
      readLive: async () => 'Y', writeBack: async () => 'X' }, { apply: true, log: () => {} });
    return r.restored.length === 1;
  }, true],
  ['live equals NEITHER -> refuses and does not write', async () => {
    let wrote = false;
    const r = await restoreRows([{ k: 'a', before: 'X', stored: 'Y' }], { key: (x) => x.k, describe: (x) => x.before, storedOf: (x) => x.stored,
      readLive: async () => 'Z', writeBack: async () => { wrote = true; return 'X'; } }, { apply: true, log: () => {} });
    return r.refused.length === 1 && wrote === false;
  }, true],
  ['a backup with NO stored value refuses rather than guessing', async () => {
    const r = await restoreRows([{ k: 'a', before: 'X' }], { key: (x) => x.k, describe: (x) => x.before,
      readLive: async () => 'Y', writeBack: async () => 'X' }, { apply: true, log: () => {} });
    return r.refused.length === 1;
  }, true],
  ['a write whose read-back does not match is a FAILURE, not a success', async () => {
    const r = await restoreRows([{ k: 'a', before: 'X', stored: 'Y' }], { key: (x) => x.k, describe: (x) => x.before, storedOf: (x) => x.stored,
      readLive: async () => 'Y', writeBack: async () => 'SOMETHING ELSE' }, { apply: true, log: () => {} });
    return r.failed.length === 1 && r.restored.length === 0;
  }, true],
  ['dry run never writes', async () => {
    let wrote = false;
    await restoreRows([{ k: 'a', before: 'X', stored: 'Y' }], { key: (x) => x.k, describe: (x) => x.before, storedOf: (x) => x.stored,
      readLive: async () => 'Y', writeBack: async () => { wrote = true; return 'X'; } }, { apply: false, log: () => {} });
    return wrote === false;
  }, true],
  /* a VALID adapter, so only the empty-rows guard can fire. With {} the adapter guard threw instead and
     this test passed while the empty-rows guard was deleted — one test satisfied by two guards. */
  ['an empty backup throws rather than reporting a clean run', async () => {
    const ok = { key: (x) => x.k, describe: (x) => x.before, readLive: async () => '', writeBack: async () => '' };
    try { await restoreRows([], ok, { log: () => {} }); return false; } catch (e) { return /no rows/.test(e.message); }
  }, true],
  ['an adapter missing writeBack throws', async () => {
    try { await restoreRows([{ k: 'a' }], { key: (x) => x.k, describe: () => '', readLive: async () => '' }, { log: () => {} }); return false; } catch { return true; }
  }, true],
  ['an unreadable record is a failure, not an already-restored', async () => {
    const r = await restoreRows([{ k: 'a', before: 'X' }], { key: (x) => x.k, describe: (x) => x.before,
      readLive: async () => { throw new Error('gone'); }, writeBack: async () => 'X' }, { apply: true, log: () => {} });
    return r.failed.length === 1 && r.already.length === 0;
  }, true],
];
