/* The pass condition for reach-liveproof.mjs, as a PURE module — Round 18i.
 *
 * reach-liveproof writes to the live store, so it must never be run to test itself. Its old pass
 * condition was "assertReach threw ANYTHING": a network error, a vanished record, or collateral on
 * some other collection would all have read as "GUARD FIRED as required". The proof it claims is
 * narrower: exactly one collateral field — seo.title on the one target collection — and nothing
 * vanished. This module holds that predicate so it can be tested with constructed error objects.
 *
 * The fixtures run at import, so reach-liveproof cannot even start with a predicate that is wrong.
 */
export function firedAsRequired(e, handle) {
  if (!e || !Array.isArray(e.blocking) || !e.reach || !Array.isArray(e.reach.vanished)) return false;
  if (e.reach.vanished.length !== 0) return false;
  if (e.blocking.length !== 1) return false;
  const [b] = e.blocking;
  return b.handle === handle && b.field === 'seo.title';
}

// 18i: constructed error objects — only the exact expected shape counts as the guard firing
const H = 'target-collection';
const err = (blocking, vanished = []) => Object.assign(new Error('assertReach: …'), { blocking, reach: { vanished, collateral: blocking } });
export const PREDICATE_FIXTURES = [
  ['exactly seo.title on the target, nothing vanished', firedAsRequired(err([{ handle: H, field: 'seo.title' }]), H) === true],
  ['a network error is not the guard firing',            firedAsRequired(new Error('HTTP 401: Invalid API key'), H) === false],
  ['collateral on ANOTHER collection is not the proof',  firedAsRequired(err([{ handle: 'other', field: 'seo.title' }]), H) === false],
  ['the declared field as collateral is not the proof',  firedAsRequired(err([{ handle: H, field: 'seo.description' }]), H) === false],
  ['two collateral rows is not the proof',               firedAsRequired(err([{ handle: H, field: 'seo.title' }, { handle: H, field: 'title' }]), H) === false],
  ['a vanished record is not the proof',                 firedAsRequired(err([{ handle: H, field: 'seo.title' }], [{ handle: 'x', was: 'present', now: 'absent' }]), H) === false],
  ['vanished-only (no collateral) is not the proof',     firedAsRequired(err([], [{ handle: H, was: 'present', now: 'absent' }]), H) === false],
  ['no error at all is not the proof',                   firedAsRequired(undefined, H) === false],
];
const failed = PREDICATE_FIXTURES.filter(([, ok]) => !ok).map(([l]) => l);
if (failed.length) throw new Error(`reach-liveproof predicate fixtures FAILED: ${failed.join('; ')}`);
