/* Round 14 #1 — enumerate Liquid outputs inside double-quoted HTML attributes that
 * are not escaped. Read-only.
 *
 *   node scripts/audit/attr-escape-scan.mjs <theme-dir> [--json out.json]
 *
 * Why it matters: a product title carrying an inch mark (10") output into alt="…"
 * closes the attribute at the mark. The rest of the title becomes stray attributes.
 *
 * Method, so the count travels with it:
 *   - population: every .liquid file under sections/, snippets/, layout/, blocks/, templates/
 *   - mask every {{…}} and {%…%} to same-length filler so quotes INSIDE Liquid do
 *     not count as attribute quotes
 *   - an output is IN AN ATTRIBUTE when the masked text since the last '<' (with no
 *     '>' after it) ends in  name="<no double quote>
 *   - it is ESCAPED when its filter chain contains escape, escape_once, json, or a
 *     URL-producing filter (a URL cannot carry a raw double quote)
 *   - {%- render/include … -%} and {% liquid %} blocks are not outputs and are skipped
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const SAFE_FILTERS = /\|\s*(escape|escape_once|json|url_encode|url_escape|url_param_escape|image_url|img_url|asset_url|asset_img_url|file_url|file_img_url|shopify_asset_url|global_asset_url|link_to|handle|handleize|money\w*|size|times|plus|minus|divided_by|modulo|round|ceil|floor|abs|at_least|at_most)\b/;

export function scan(src) {
  const masked = src.replace(/\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\}/g, (m) => '§'.repeat(m.length));
  const hits = [];
  const re = /\{\{-?([\s\S]*?)-?\}\}/g;
  let m;
  while ((m = re.exec(src))) {
    const p = m.index;
    const lt = masked.lastIndexOf('<', p), gt = masked.lastIndexOf('>', p);
    if (lt < 0 || gt > lt) continue;
    const before = masked.slice(lt, p);
    const a = before.match(/\s([A-Za-z_:@.\-]+)\s*=\s*"([^"]*)$/);
    if (!a) continue;
    const expr = m[1].trim();
    if (SAFE_FILTERS.test(expr)) continue;
    const line = src.slice(0, p).split('\n').length;
    const open = m[0].startsWith('{{-') ? 3 : 2;
    hits.push({ attr: a[1], line, expr, exprStart: p + open, exprEnd: p + open + m[1].length });
  }
  return hits;
}

/* The DATA axis: only outputs that can carry merchant text with a double quote.
   A pure translation key with no interpolated data cannot, and neither can shop.name
   as set here. Same definition as the Round 14 enumeration (76 on the stale local
   checkout, 103 on MAIN r13 — a strict superset). */
export const RISKY = /\b(product\.title|\.title\b|\.alt\b|image\.alt|media\.alt|article\.title|collection\.title|variant\.title|\.name\b|page_title)/i;
export const dataAxis = (h) => RISKY.test(h.expr)
  && !/^\s*-?\s*'[^']+'\s*\|\s*t\s*-?\s*$/.test(h.expr)
  && !/shop\.name/.test(h.expr);

/* SELF-TEST — constructed, never live content. */
{
  const fx = [
    ['<img alt="{{ product.title }}">', 1],
    ['<img alt="{{ product.title | escape }}">', 0],
    ['<a aria-label="{{ link.title }}" href="{{ link.url }}">', 2],       // href is not exempt by name; url has no filter
    ['<img src="{{ img | image_url: width: 400 }}" alt="{{ img.alt | default: "x" | escape }}">', 0],
    ['<div data-t="{% if a %}{{ b }}{% endif %}">', 1],                     // Liquid tag before the output, quotes masked
    ['<p>{{ product.title }}</p>', 0],                                     // text node, not attribute
    ['<img\n  alt="{{ block.settings.name }}"\n>', 1],                     // multi-line tag
    ['<img alt="{{ x | default: \'a"b\' }}">', 1],                         // quote inside Liquid does not end attribute
  ];
  const bad = fx.filter(([s, n]) => scan(s).length !== n);
  if (bad.length) { bad.forEach(([s, n]) => console.error(`  SELF-TEST ${JSON.stringify(s)} want ${n} got ${scan(s).length}`)); process.exit(1); }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const dir = process.argv[2];
  const jsonOut = process.argv.includes('--json') ? process.argv[process.argv.indexOf('--json') + 1] : null;
  const files = [];
  for (const sub of ['layout', 'sections', 'snippets', 'blocks', 'templates']) {
    const d = path.join(dir, sub);
    if (!fs.existsSync(d)) continue;
    for (const f of fs.readdirSync(d)) if (f.endsWith('.liquid')) files.push(`${sub}/${f}`);
  }
  const all = [];
  for (const f of files) for (const h of scan(fs.readFileSync(path.join(dir, f), 'utf8'))) all.push({ f, ...h });
  console.log(`  self-test: 8/8   liquid files scanned: ${files.length}   unescaped attribute outputs: ${all.length}`);
  const byAttr = {};
  for (const h of all) { const k = /^aria-/.test(h.attr) ? 'aria-*' : /^data-/.test(h.attr) ? 'data-*' : h.attr; (byAttr[k] ??= []).push(h); }
  for (const [k, v] of Object.entries(byAttr).sort((a, b) => b[1].length - a[1].length))
    console.log(`  ${k.padEnd(14)} ${String(v.length).padStart(4)}  in ${new Set(v.map((h) => h.f)).size} files`);
  if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(all, null, 1));
}
