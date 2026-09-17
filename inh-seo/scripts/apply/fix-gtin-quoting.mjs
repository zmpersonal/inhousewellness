/* Round 15b — quote the gtin values. Local build only; theme-push does the write.
 *   node scripts/apply/fix-gtin-quoting.mjs
 *
 * THE BUG, pre-existing in the offers emitter and not introduced by Round 15:
 *
 *     "gtin12": {{ variant.barcode }},        ->  "gtin12": 019962854569,
 *
 * A leading-zero number literal. JSON forbids it, so a strict parser discards the WHOLE Product
 * node — offers, price, availability and the aggregateRating Round 15 just added. The rating was
 * server-rendered correctly and then thrown away with the node it sat in.
 *
 * gtin12/13/14 are schema.org TEXT properties. Quoting is not a JSON workaround, it is the
 * correct type — a barcode is an identifier, never a quantity. `| json` quotes AND escapes.
 *
 * AUDIT OF EVERY OTHER UNQUOTED VALUE in the same block: sku, priceValidUntil, price,
 * priceCurrency and url all already pass through `| json`. availability and itemCondition are
 * string literals. The aggregateRating values are genuinely numeric — a rating is 1.0-5.0 and
 * reviewCount is an integer, neither can carry a leading zero. The three gtin lines were the
 * only raw interpolations.
 *
 * THREE EMITTERS AGAIN. Round 9's partition trap, third time this round.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve('.');
const T = (f) => path.join(ROOT, 'theme', f);
const FILES = ['sections/main-product.liquid', 'sections/bundle-product.liquid', 'sections/main-product-layout-2.liquid'];

/* idempotency: refuse a second run rather than silently no-op or double-apply */
const alreadyDone = FILES.filter((f) => fs.readFileSync(T(f), 'utf8').includes('"gtin12": {{ variant.barcode | json }}'));
if (alreadyDone.length) {
  console.log('  REFUSING — already quoted in:', alreadyDone.join(', '));
  console.log('  Restore from MAIN first: node scripts/apply/theme-pull.mjs 146290704451 <files…>');
  process.exit(1);
}

let failures = 0;
for (const f of FILES) {
  const p = T(f);
  let s = fs.readFileSync(p, 'utf8');
  for (const n of [12, 13, 14]) {
    const from = `"gtin${n}": {{ variant.barcode }},`;
    const to = `"gtin${n}": {{ variant.barcode | json }},`;
    const count = s.split(from).length - 1;
    console.log(`  ${count === 1 ? 'ok  ' : 'FAIL'} ${count}×  ${f.padEnd(42)} gtin${n}`);
    if (count !== 1) { failures++; continue; }
    s = s.replace(from, to);
  }
  fs.writeFileSync(p, s);
}
if (failures) { console.log(`\n  REFUSING — ${failures} target(s) not matched exactly once.`); process.exit(1); }

console.log('\n  post-build verification:');
let bad = 0;
for (const f of FILES) {
  const s = fs.readFileSync(T(f), 'utf8');
  const raw = (s.match(/"gtin\d+": \{\{ variant\.barcode \}\}/g) || []).length;
  const quoted = (s.match(/"gtin\d+": \{\{ variant\.barcode \| json \}\}/g) || []).length;
  const ok = raw === 0 && quoted === 3;
  if (!ok) bad++;
  console.log(`    ${ok ? 'ok  ' : 'FAIL'} ${f.padEnd(42)} raw=${raw} (want 0)  quoted=${quoted} (want 3)`);
}
/* the aggregateRating from Round 15 must still be there, exactly once, in each */
for (const f of FILES) {
  const s = fs.readFileSync(T(f), 'utf8');
  const n = (s.match(/"aggregateRating"/g) || []).length;
  const ok = n === 1;
  if (!ok) bad++;
  console.log(`    ${ok ? 'ok  ' : 'FAIL'} ${f.padEnd(42)} Round 15 aggregateRating intact (${n}, want 1)`);
}
console.log(bad ? `\n  ${bad} FAILURE(S)` : '\n  all post-build checks passed');
process.exitCode = bad ? 1 : 0;
