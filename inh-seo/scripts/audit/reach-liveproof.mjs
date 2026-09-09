/* LIVE PROOF — assertReach must fire against the real Shopify API, not only
   against fixtures. Deliberately writes TWO fields while declaring ONE, on the
   smallest collection in the catalogue, then restores both. Reversible by
   construction: the restore uses the values read one line earlier.
   node scripts/audit/reach-liveproof.mjs */
import { gql } from '../lib/shopify.js';
import { captureReach, assertReach } from '../lib/reach.mjs';

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
/* the deliberate defect: two fields changed, one declared */
await gql(M, { input: { id: c.id, seo: { title: ORIG.title + ' ', description: (ORIG.description || '') + ' ' } } });
const after = await captureReach(fetchAll);

let fired = false;
try {
  assertReach(before, after, { handles: [H], fields: ['seo.description'] });
} catch (e) { fired = true; console.log(`\n  GUARD FIRED as required: ${e.blocking.length} collateral field(s)`); }

/* restore, unconditionally, before reporting */
await gql(M, { input: { id: c.id, seo: ORIG } });
const back = await gql(`query($h:String!){ collectionByHandle(handle:$h){ seo{ title description } } }`, { h: H });
const restored = back.collectionByHandle.seo.title === ORIG.title && back.collectionByHandle.seo.description === ORIG.description;

console.log(`\n  ${fired ? 'PASS' : 'FAIL'}  assertReach fired on a real two-field write declared as one`);
console.log(`  ${restored ? 'PASS' : 'FAIL'}  the collection was restored exactly`);
process.exit(fired && restored ? 0 : 1);
