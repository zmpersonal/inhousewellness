/**
 * Adds products to, and removes products from, MANUAL collections.
 *
 * Driven by data/membership-fixes.json so the change is reviewable as data
 * before it is reviewable as a diff. Each entry states the RULE membership
 * follows, not just the products moved — a collection whose rule isn't
 * written down drifts again.
 *
 * Uses productUpdate { collectionsToJoin / collectionsToLeave }, which is
 * additive per product. It never replaces a collection's whole product list,
 * so a product missing from the spec can't be silently dropped.
 *
 * Idempotent: joining a collection a product is already in is a no-op, and
 * the script skips those before calling the API at all.
 */
import path from 'node:path';
import { gql } from '../lib/shopify.js';
import { assertReach, reachAllowFromArgv, captureMembership } from '../lib/reach.mjs';
import {
  readJSON, DATA, parseArgs, banner, backup, logChange, assertFresh,
} from '../lib/util.js';

const flags = parseArgs();
banner('fix-membership', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/collections.json, data/membership-fixes.json, data/products.json');

assertFresh({
  'collections.json': 'npm run audit:collections',
  'products.json': 'npm run audit:products',
});

const fixes = readJSON(path.join(DATA, 'membership-fixes.json'));
const collections = readJSON(path.join(DATA, 'collections.json'));
const products = readJSON(path.join(DATA, 'products.json'));

const collByHandle = new Map(collections.map((c) => [c.handle, c]));
const prodByHandle = new Map(products.map((p) => [p.handle, p]));

const work = [];

for (const fix of fixes) {
  if (flags.only && !flags.only.includes(fix.handle)) continue;

  const coll = collByHandle.get(fix.handle);
  if (!coll) {
    console.error(`  ! ${fix.handle} — no such collection, skipping`);
    continue;
  }
  if (coll.smart) {
    console.error(`  ! ${fix.handle} — SMART collection. Membership is rule-driven; edit the rule, not the members. Skipping.`);
    continue;
  }

  console.log(`\n${fix.handle} (${coll.products} products)`);
  console.log(`  rule:   ${fix.rule}`);
  console.log(`  reason: ${fix.reason}\n`);

  for (const h of fix.add || []) {
    const p = prodByHandle.get(h);
    if (!p) { console.error(`    ? ${h} — not in products.json, skipping`); continue; }
    if (p.collections.includes(fix.handle)) {
      console.log(`    = ${h} — already a member, no-op`);
      continue;
    }
    work.push({ op: 'join', collection: fix.handle, collectionId: coll.id, product: p });
    console.log(`    + ${p.title.slice(0, 78)}`);
    console.log(`        ${h}  $${p.priceMin}  ${p.vendor}`);
  }

  for (const h of fix.remove || []) {
    const p = prodByHandle.get(h);
    if (!p) { console.error(`    ? ${h} — not in products.json, skipping`); continue; }
    if (!p.collections.includes(fix.handle)) {
      console.log(`    = ${h} — not a member, no-op`);
      continue;
    }
    work.push({ op: 'leave', collection: fix.handle, collectionId: coll.id, product: p });
    console.log(`    - ${p.title.slice(0, 78)}`);
    console.log(`        ${h}  $${p.priceMin}  ${p.vendor}`);
  }
}

const joins = work.filter((w) => w.op === 'join').length;
const leaves = work.filter((w) => w.op === 'leave').length;

console.log(`\n${work.length} change(s): ${joins} addition(s), ${leaves} removal(s).`);
console.log('Products are not deleted and keep every other collection they are in.\n');

if (!work.length) { console.log('Nothing to do — membership already matches the spec.'); process.exit(0); }
if (!flags.apply) { console.log('Dry run. Re-run with --apply.'); process.exit(0); }

backup('membership-before', work.map((w) => ({


  op: w.op,
  collection: w.collection,
  productId: w.product.id,
  productHandle: w.product.handle,
  collectionsBefore: w.product.collections,
})));

/* REACH GUARD — reports/reach-guard.md. Membership is an EDGE, not a field, so
   the capture is taken from the PRODUCT side: each product's sorted collection
   list. Capturing collection fields would have measured the wrong thing and
   passed while membership moved underneath it. */
const _reachBefore = await captureMembership(gql);
/* every product this plan names, on either side of a join or a leave */
/* Respect --only. Declaring every product in the PLAN while writing only a
   filtered subset makes the guard permissive on exactly the records it is not
   touching: collateral there would be classified DECLARED and pass silently.
   Same shape as instance 55, where the reviewed command and the executed
   command diverged. */
const _reachHandles = [...new Set(
  fixes
    .filter((f) => !flags.only || flags.only.includes(f.handle))
    .flatMap((f) => [...(f.add || []), ...(f.remove || [])]),
)];
const _reachDeclared = { handles: _reachHandles, fields: ['collections'] };

const M = `mutation($input: ProductInput!){
  productUpdate(input: $input) {
    product { id handle collections(first: 40) { nodes { handle } } }
    userErrors { field message }
  }
}`;

let ok = 0;
for (const w of work) {
  const input = { id: w.product.id };
  if (w.op === 'join') input.collectionsToJoin = [w.collectionId];
  else input.collectionsToLeave = [w.collectionId];

  const r = await gql(M, { input });
  const errs = r.productUpdate.userErrors;
  if (errs.length) { console.error(`  FAILED ${w.product.handle}:`, errs); process.exitCode = 1; continue; }  /* guard audit 18i */

  const after = r.productUpdate.product.collections.nodes.map((n) => n.handle);
  const isMember = after.includes(w.collection);
  const expected = w.op === 'join';
  if (isMember !== expected) {
    console.error(`  FAILED ${w.product.handle}: expected member=${expected}, got ${isMember}`);
    process.exitCode = 1;   // guard audit 18i: an outcome that did not land must fail the run
    continue;
  }

  logChange({
    script: 'fix-membership', kind: 'product', id: w.product.id, handle: w.product.handle,
    field: `collections.${w.collection}`,
    before: w.op === 'join' ? 'absent' : 'member',
    after: w.op === 'join' ? 'member' : 'absent',
  });
  ok += 1;
  console.log(`  ${w.op === 'join' ? 'added  ' : 'removed'} ${w.product.handle}`);
}

console.log(`\n${ok}/${work.length} applied. Re-run npm run audit to verify.`);

const _reachAfter = await captureMembership(gql);
try {
  assertReach(_reachBefore, _reachAfter, _reachDeclared, { allow: reachAllowFromArgv() });
} catch (e) {
  console.error(`\n${e.message}`);
  console.error('The reach capture holds the full before-state. Roll back from it.');
  process.exit(1);
}
