/* LIVE PROOF — assertReach must fire against the real Shopify API, not only
   against fixtures. Deliberately writes TWO fields while declaring ONE, on the
   smallest collection in the catalogue, then restores both. Reversible by
   construction: the restore uses the values read one line earlier.
   node scripts/audit/reach-liveproof.mjs */
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach } from '../lib/reach.mjs';
import { firedAsRequired } from './reach-liveproof-predicate.mjs';   // 18i: pure, fixture-tested predicate

const H = 'float-tank-upgrades';
const Q = `query($after:String){ collections(first:100, after:$after){
  pageInfo{ hasNextPage endCursor } nodes{ id handle seo{ title description } } } }`;
const fetchAll = async () => { const out=[]; let a=null,m=true;
  while(m){ const r=await gql(Q,{after:a}); out.push(...r.collections.nodes); m=r.collections.pageInfo.hasNextPage; a=r.collections.pageInfo.endCursor; } return out; };

const one = await gql(`query($h:String!){ collectionByHandle(handle:$h){ id handle seo{ title description } } }`, { h: H });
const c = one.collectionByHandle;
const ORIG = { title: c.seo.title, description: c.seo.description };
console.log(`  target: ${H}`);
console.log(`    title:       ${ORIG.title}`);
console.log(`    description: ${ORIG.description}`);

const before = await captureReach(fetchAll);
const M = `mutation($input:CollectionInput!){ collectionUpdate(input:$input){ collection{ id } userErrors{ field message } } }`;

/* Round 18i: three changes, none of them run (this script writes to the live store).
   1. `fired` used to be "assertReach threw anything" — a network error or a vanished record read
      as the proof. It now requires EXACTLY one collateral row, {handle:H, field:'seo.title'}, and
      nothing vanished (firedAsRequired, fixture-tested in reach-liveproof-predicate.mjs).
   2. The write's userErrors are checked: a rejected write changes nothing, and "the guard did not
      fire" on an unchanged record is not a finding about the guard.
   3. The restore sits in `finally`, so it runs if anything between the write and the report throws.
      It used to be a straight-line statement that an exception skipped, leaving the live record
      carrying the deliberate defect. */
let fired = false, restored = false, failure = null;
try {
  /* the deliberate defect: two fields changed, one declared */
  const w = await gql(M, { input: { id: c.id, seo: { title: ORIG.title + ' ', description: (ORIG.description || '') + ' ' } } });
  const ue = w?.collectionUpdate?.userErrors;
  if (!Array.isArray(ue)) throw new Error('the deliberate write returned no collectionUpdate.userErrors — cannot tell whether it landed');
  if (ue.length) throw new Error(`the deliberate write was REJECTED (${JSON.stringify(ue)}) — nothing changed, so nothing is proved`);
  const after = await captureReach(fetchAll);
  try {
    assertReach(before, after, { handles: [H], fields: ['seo.description'] });
    console.log('\n  GUARD DID NOT FIRE on a two-field write declared as one');
  } catch (e) {
    fired = firedAsRequired(e, H);
    console.log(fired
      ? `\n  GUARD FIRED as required: exactly seo.title on ${H}, nothing vanished`
      : `\n  assertReach threw, but NOT with the expected shape: ${e.message} (blocking ${JSON.stringify(e.blocking?.map((b) => `${b.handle}.${b.field}`) ?? null)}, vanished ${e.reach?.vanished?.length ?? 'n/a'})`);
  }
} catch (e) {
  failure = e;
} finally {
  /* restore, unconditionally, before reporting */
  const r = await gql(M, { input: { id: c.id, seo: ORIG } });
  const rue = r?.collectionUpdate?.userErrors || [];
  if (rue.length) console.error(`  RESTORE userErrors: ${JSON.stringify(rue)}`);
  const back = await gql(`query($h:String!){ collectionByHandle(handle:$h){ seo{ title description } } }`, { h: H });
  restored = back.collectionByHandle.seo.title === ORIG.title && back.collectionByHandle.seo.description === ORIG.description;
}

if (failure) console.error(`\n  ABORTED before the proof: ${failure.message}`);
console.log(`\n  ${fired ? 'PASS' : 'FAIL'}  assertReach fired on a real two-field write declared as one`);
console.log(`  ${restored ? 'PASS' : 'FAIL'}  the collection was restored exactly`);
process.exit(fired && restored && !failure ? 0 : 1);
