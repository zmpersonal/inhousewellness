/* unwrap-editor-spans — remove the assistant's wrapper <span> while KEEPING its
 * children. This is the second pass and it is structurally different from the
 * attribute strip: these spans wrap real copy, so a mistake here eats a sentence.
 *
 * Balanced-span walk, never a lazy regex — the wrapped copy contains <strong> and
 * nested spans, and `[\s\S]*?</span>` terminates on the first inner close.
 *
 * Refusal conditions, identical to the attribute pass: the word sequence and the
 * count of every tag EXCEPT <span> must be unchanged, or the batch refuses.
 */
import { gql } from '../lib/shopify.js';
import { parseArgs, banner, backup, logChange, showDiff, assertWellFormed, assertOneWritePerRecord } from '../lib/util.js';
import { readJSON, DATA } from '../lib/util.js';
import path from 'node:path';

const flags = parseArgs();
banner('unwrap-editor-spans', flags);

const OPEN = /<span class="relative -mx-px[^"]*">/;
/* Render-faithful text, not a space-inserting proxy.
   Replacing EVERY tag with a space models block elements correctly and INLINE
   elements wrongly: `setting</span>.` renders as "setting." and the proxy read it
   as "setting ." So unwrapping an inline span looked like a text change on three
   products where the rendered output is byte-identical. Verified by hand on
   leisurecraft-luna before this was changed — the guard was over-strict, not
   wrong to fire, and the fix is to model the renderer rather than to loosen it. */
const BLOCK = /<\/?(p|h[1-6]|ul|ol|li|div|br|table|tr|td|th|hr|blockquote)\b[^>]*>/gi;
const words = (h) => h.replace(BLOCK, '\n').replace(/<[^>]+>/g, '').replace(/[ \t]+/g, ' ').replace(/\n\s*/g, '\n').trim();
const shape = (h) => ['p','h2','h3','h4','ul','ol','li','strong','em','a','img','br','table','td'].map((t) => `${t}:${(h.match(new RegExp(`<${t}\\b`, 'gi')) || []).length}`).join(' ');

function endOfSpan(h, from) {
  const t = /<\/?span\b[^>]*>/g; t.lastIndex = from;
  let d = 0, m;
  while ((m = t.exec(h))) { d += m[0].startsWith('</') ? -1 : 1; if (d === 0) return m.index + m[0].length; }
  return -1;
}
function unwrap(h) {
  let o = h, n = 0, guard = 0;
  for (;;) {
    if (guard++ > 500) throw new Error('runaway unwrap');
    const m = o.match(OPEN); if (!m) break;
    const s = m.index, e = endOfSpan(o, s);
    if (e === -1) throw new Error('unbalanced wrapper span — refusing to guess');
    const inner = o.slice(s + m[0].length, e - '</span>'.length);
    o = o.slice(0, s) + inner + o.slice(e); n += 1;
  }
  return { out: o, n };
}

const P = readJSON(path.join(DATA, 'products.json'));
const candidates = (Array.isArray(P) ? P : P.products).filter((p) => /transition-colors duration-100/.test(p.descriptionHtml || '')).map((p) => p.handle);
console.log(`  products with the wrapper span: ${candidates.length}\n`);

const Q = `query($q:String!){ products(first:50, query:$q){ nodes{ id handle title descriptionHtml } } }`;
const targets = []; let hardFail = false;
for (const h of candidates) {
  const r = await gql(Q, { q: `handle:${h}` });
  const p = r.products.nodes.find((n) => n.handle === h);
  if (!p) { console.error(`  ✗ ${h}: NOT FOUND live`); hardFail = true; continue; }
  const before = p.descriptionHtml || '';
  let res; try { res = unwrap(before); } catch (e) { console.error(`  ✗ ${h}: ${e.message}`); hardFail = true; continue; }
  if (!res.n) { console.error(`  ✗ ${h}: ZERO wrappers — plan stale. Not a skip.`); hardFail = true; continue; }
  if (words(before) !== words(res.out)) { console.error(`  ✗ ${h}: WORD SEQUENCE CHANGED — a span unwrap must never do this`); hardFail = true; continue; }
  if (shape(before) !== shape(res.out)) { console.error(`  ✗ ${h}: NON-SPAN TAG COUNTS CHANGED\n      ${shape(before)}\n      ${shape(res.out)}`); hardFail = true; continue; }
  assertWellFormed(res.out, `${h} description`, before);
  targets.push({ p, before, after: res.out, n: res.n });
}

const tot = targets.reduce((a, t) => a + t.n, 0);
const bytes = targets.reduce((a, t) => a + (t.before.length - t.after.length), 0);
console.log(`  ${targets.length} clean, ${candidates.length - targets.length} refused`);
console.log(`  ${tot} wrappers, ${bytes} bytes`);
console.log(`  word sequence: unchanged on all ${targets.length}   non-span tags: unchanged on all ${targets.length}`);
for (const t of targets.slice(0, 2)) showDiff(t.p.handle, t.before, t.after);

if (hardFail) { console.error('\nAt least one target failed. NOTHING APPLIED.'); process.exit(1); }
if (!flags.apply) { console.log('\nDry run. Re-run with --apply.'); process.exit(0); }
assertOneWritePerRecord(targets, (t) => t.p.handle, 'unwrap-editor-spans');
backup('editor-spans-before', targets.map((t) => ({ id: t.p.id, handle: t.p.handle, title: t.p.title, descriptionHtml: t.before })));

const M = `mutation($input:ProductInput!){ productUpdate(input:$input){ product{ id } userErrors{ field message } } }`;
let ok = 0;
for (const t of targets) {
  const r = await gql(M, { input: { id: t.p.id, descriptionHtml: t.after } });
  if (r.productUpdate.userErrors.length) { console.error(`  FAILED ${t.p.handle}:`, r.productUpdate.userErrors); continue; }
  logChange({ resource: t.p.id, handle: t.p.handle, field: 'descriptionHtml', before: t.before, after: t.after, note: `unwrapped ${t.n} editor wrapper span(s), children kept` });
  ok += 1;
}
console.log(`\n${ok}/${targets.length} updated.`);
