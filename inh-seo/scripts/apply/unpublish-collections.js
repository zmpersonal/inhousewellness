/**
 * Unpublishes collections from the Online Store channel.
 *
 * NEVER deletes. Unpublishing is reversible and preserves product membership.
 *
 * Before unpublishing, checks whether each handle is referenced by a
 * navigation menu. Referenced handles are SKIPPED and reported — unpublishing
 * a collection that's in the nav leaves a dead link.
 *
 * Theme templates and section settings are NOT checked here (the Admin API
 * can't see them reliably). Run a grep over the theme/ checkout as well:
 *   grep -rn "collections/non-bb" theme/
 */
import path from 'node:path';
import { gql, onlineStorePublicationId, publicationsOf } from '../lib/shopify.js';
import { readJSON, DATA, parseArgs, banner, backup, logChange, assertFresh } from '../lib/util.js';

const flags = parseArgs();
banner('unpublish-collections', flags);

/* Instance 15: a staging file nothing reads is indistinguishable from one that
   works. Every apply script names its inputs before it does anything, so a
   value staged into the wrong file is visible in the first line of output
   instead of silently ignored. */
console.log('  READS FROM: data/collections-plan.json, data/collections.json, data/unpublish-blocks.json');

// collections-plan.json is tracked config, not an audit dump, so it is not checked.
assertFresh({ 'collections.json': 'npm run audit:collections' });

const plan = readJSON(path.join(DATA, 'collections-plan.json'));
const collections = readJSON(path.join(DATA, 'collections.json'));

// Handles held back by an open decision. Reported in their own section rather
// than skipped, so a blocked row can never quietly drop off the list.
const blocks = readJSON(path.join(DATA, 'unpublish-blocks.json'));
const byHandle = new Map(collections.map((c) => [c.handle, c]));

let handles = plan
  .filter((p) => p.action === 'DEINDEX' || p.action === 'DELETE')
  .map((p) => p.handle);

if (flags.only) handles = handles.filter((h) => flags.only.includes(h));

if (!handles.length) {
  console.log('No collections marked DEINDEX or DELETE in collections-plan.json.');
  process.exit(0);
}

/* ---- Check navigation menus for references ---- */

console.log('Checking navigation menus for references…\n');
// Four levels deep. The store has menus nested to 3 (verified 2026-09-06); the
// original query fetched 2, which would have silently reported a target at
// depth 3 as "clear". `overflow` below catches it if anyone nests deeper still.
const MENU_ITEM = 'id title url resourceId';
const menus = await gql(`{
  menus(first: 50) {
    nodes {
      id handle title
      items { ${MENU_ITEM}
        items { ${MENU_ITEM}
          items { ${MENU_ITEM}
            items { ${MENU_ITEM} }
          }
        }
      }
    }
  }
}`);

const referenced = new Map();
let scanned = 0;
let overflow = 0;
const walk = (items, menuHandle, trail, depth) => {
  for (const it of items || []) {
    scanned += 1;
    const url = it.url || '';
    const m = url.match(/\/collections\/([^/?#]+)/);
    if (m) {
      if (!referenced.has(m[1])) referenced.set(m[1], []);
      referenced.get(m[1]).push(`${menuHandle} > ${[...trail, it.title].join(' > ')} (depth ${depth})`);
    }
    // At the deepest level we fetched, `items` is undefined rather than [] —
    // we cannot tell "no children" from "not fetched", so flag it.
    if (depth >= 4 && it.items === undefined) overflow += 1;
    walk(it.items, menuHandle, [...trail, it.title], depth + 1);
  }
};
for (const menu of menus.menus.nodes) walk(menu.items, menu.handle, [], 1);
console.log(`  ${menus.menus.nodes.length} menus, ${scanned} items scanned to depth 4.`);
if (overflow) {
  console.warn(`  ! ${overflow} item(s) sit at the deepest fetched level — menus may nest deeper than this query reads.`);
  console.warn('    Increase the nesting in MENU_ITEM before trusting a "clear" result.\n');
}

const blocked = [];
const decisionBlocked = [];
const alreadyOff = [];
const safe = [];
for (const h of handles) {
  const c = byHandle.get(h);
  if (!c) {
    console.warn(`  ? ${h} — not found in collections.json, skipping`);
    continue;
  }
  if (blocks[h]) {
    decisionBlocked.push({ handle: h, products: c.products, ...blocks[h] });
    continue;
  }
  if (!c.publishedOnline) {
    alreadyOff.push(c);
    continue;
  }
  if (referenced.has(h)) {
    blocked.push({ handle: h, where: referenced.get(h) });
  } else {
    safe.push(c);
  }
}

if (alreadyOff.length) {
  console.log('ALREADY UNPUBLISHED — no-op, not counted as clear:\n');
  for (const c of alreadyOff) {
    console.log(`  = ${c.handle.padEnd(26)} ${String(c.products).padStart(4)} products   (publications: ${c.publications})`);
  }
  console.log('');
}

if (decisionBlocked.length) {
  console.log('BLOCKED ON AN OPEN DECISION — not unpublished, not skipped:\n');
  for (const b of decisionBlocked) {
    console.log(`  # ${b.handle}  (${b.products} products)`);
    console.log(`      blocked by: ${b.blocked_by}`);
    console.log(`      ${b.reason}\n`);
  }
}

if (blocked.length) {
  console.log('SKIPPED — referenced in navigation. Remove from the menu first:\n');
  for (const b of blocked) console.log(`  ! ${b.handle}\n      ${b.where.join('\n      ')}`);
  console.log('');
}

if (!safe.length) {
  console.log('Nothing safe to unpublish.');
  process.exit(0);
}

const accounted = safe.length + blocked.length + decisionBlocked.length + alreadyOff.length;
console.log(`Of ${handles.length} planned target(s): ${safe.length} clear, ${blocked.length} in navigation, ${decisionBlocked.length} blocked on a decision, ${alreadyOff.length} already unpublished.`);
if (accounted !== handles.length) {
  console.error(`  ! RECONCILIATION FAILED: ${accounted} accounted for, ${handles.length} planned. ${handles.length - accounted} target(s) unexplained.`);
  process.exit(1);
}
console.log('');

console.log(`${safe.length} collection(s) will be unpublished from Online Store:\n`);
let totalProducts = 0;
for (const c of safe) {
  totalProducts += c.products;
  console.log(`  ${c.handle.padEnd(34)} ${String(c.products).padStart(4)} products   ${c.title}`);
}
console.log(`\n  ${totalProducts} products affected. They remain in the catalogue and in other collections.`);
console.log('  Collections are NOT deleted. This is reversible from the admin.\n');

// Every channel, not just Online Store. Unpublishing from Online Store leaves
// the others live, and that was missed the first time: cold-plunge-favorites
// stayed in the Shop app and non-bb on Point of Sale after both were recorded
// as "unpublished". Show what else each collection touches BEFORE removing it
// from one channel.
console.log('Channels each target is published to (this script only removes Online Store):\n');
let otherChannels = 0;
for (const c of safe) {
  let names;
  try {
    names = await publicationsOf(c.handle);
  } catch (e) {
    console.log(`  ${c.handle.padEnd(34)} ! could not read publications: ${e.message}`);
    continue;
  }
  const others = names.filter((n) => n !== 'Online Store');
  if (others.length) otherChannels += 1;
  console.log(
    `  ${c.handle.padEnd(34)} ${names.join(', ') || '(none)'}` +
      (others.length ? `   <-- STAYS LIVE ON: ${others.join(', ')}` : ''),
  );
}
if (otherChannels) {
  console.log(
    `\n  ! ${otherChannels} collection(s) remain published on another channel after this runs.` +
      '\n    Unpublishing from Online Store does NOT deindex those surfaces. Decide each one deliberately.',
  );
}
console.log('');

console.log('Also grep the theme before applying:');
for (const c of safe) console.log(`  grep -rn "collections/${c.handle}" theme/`);

console.log('\nKNOWN BLIND SPOT: the token lacks read_discounts, so automatic and code');
console.log('discounts targeting these collections are invisible to this check.');
console.log('A collection can also be wired to an app, feed or automation that no');
console.log('Admin API query exposes (see hard rule 8). Contents are not function.');

if (!flags.apply) {
  console.log('\nDry run. Re-run with --apply.');
  process.exit(0);
}

const pubId = await onlineStorePublicationId();
backup('unpublish-before', safe.map((c) => ({ id: c.id, handle: c.handle, publishedOnline: c.publishedOnline })));

const M = `mutation($id: ID!, $input: [PublicationInput!]!){
  publishableUnpublish(id: $id, input: $input) {
    publishable { ... on Collection { id handle } }
    userErrors { field message }
  }
}`;

for (const c of safe) {
  const r = await gql(M, { id: c.id, input: [{ publicationId: pubId }] });
  const errs = r.publishableUnpublish.userErrors;
  if (errs.length) {
    console.error(`  FAILED ${c.handle}:`, errs);
    continue;
  }
  logChange({
    script: 'unpublish-collections', kind: 'collection', id: c.id, handle: c.handle,
    field: 'publishedOnline', before: true, after: false,
  });
  console.log(`  unpublished ${c.handle}`);
}

console.log('\nDone. Verify in Search Console coverage after the next crawl — not immediately.');
