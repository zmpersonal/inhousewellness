/* Build the Steam Generator / Steam Accessories mapping to a fixed file.
 *
 * The apply reads this file rather than re-deriving, so the list reviewed is
 * byte-for-byte the list written.
 *
 * Titles CHECK the mapping; they never derive it on their own. The one product
 * excluded by hand is named below and the exclusion is part of the artefact —
 * a mapping file with no exceptions in it is indistinguishable from one where
 * nobody looked.
 */
import { gql } from '../lib/shopify.js';
import { writeJSON, DATA } from '../lib/util.js';
import path from 'node:path';

/* No \b before "steam": manufacturers glue it — SimpleSteam, SteamScape.
 * A \b pattern silently missed Delta SimpleSteam 12kW Generator. */
const GEN = /steam.{0,32}\bgenerator\b/i;

/* Hand-excluded: the generator is a FITTED FEATURE, the unit is a cold plunge. */
const EXCLUDE = new Set(['Medical Frozen 6 Cold Plunge | XL Size with Essential Oil Infuser & Steam Generator']);

let after = null, all = [];
for (;;) {
  const r = await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
    nodes{ id handle title status vendor productType } } }`, { a: after });
  all.push(...r.products.nodes);
  if (!r.products.pageInfo.hasNextPage) break;
  after = r.products.pageInfo.endCursor;
}

const steamRoom = all.filter((p) => p.productType === 'Steam Room');
const gens = all.filter((p) => GEN.test(p.title) && !EXCLUDE.has(p.title));
const genIds = new Set(gens.map((p) => p.id));
const accs = steamRoom.filter((p) => !genIds.has(p.id));

const rows = [
  ...gens.map((p) => ({ id: p.id, handle: p.handle, title: p.title, status: p.status, vendor: p.vendor, from: p.productType, to: 'Steam Generator' })),
  ...accs.map((p) => ({ id: p.id, handle: p.handle, title: p.title, status: p.status, vendor: p.vendor, from: p.productType, to: 'Steam Accessories' })),
];

const excluded = all.filter((p) => EXCLUDE.has(p.title))
  .map((p) => ({ handle: p.handle, title: p.title, productType: p.productType,
                 why: 'steam generator is a fitted feature; the unit is a cold plunge' }));

writeJSON(path.join(DATA, 'steam-type-map.json'), { built: new Date().toISOString(), pattern: String(GEN), rows, excluded });

console.log(`  Steam Room before: ${steamRoom.length}`);
console.log(`  -> Steam Generator   ${gens.length}   (${gens.filter((p) => p.status === 'ACTIVE').length} active)`);
console.log(`  -> Steam Accessories ${accs.length}   (${accs.filter((p) => p.status === 'ACTIVE').length} active)`);
console.log(`  Steam Room after:  ${steamRoom.length - gens.filter((p) => p.productType === 'Steam Room').length - accs.length}`);
console.log(`  total writes: ${rows.length}`);
console.log(`  hand-excluded: ${excluded.length}  ${excluded.map((e) => e.handle).join(', ')}`);
