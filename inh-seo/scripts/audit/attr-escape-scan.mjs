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

/* 18i: tag and quote state, walked once over the MASKED text. The old test — "the last '<' has
   no '>' after it" — was fooled by a '>' or '<' inside a quoted value: alt="a > b {{ x }}" read as
   a text node and scored 0. State per index: 0 text, 1 in a tag, 2 in "…", 3 in '…'. */
function tagState(masked) {
  const st = new Uint8Array(masked.length), open = new Int32Array(masked.length).fill(-1);
  let mode = 0, at = -1;
  for (let i = 0; i < masked.length; i++) {
    const c = masked[i];
    st[i] = mode; open[i] = at;
    if (mode === 0) { if (c === '<' && /[A-Za-z/§]/.test(masked[i + 1] || '')) { mode = 1; at = i; } }   // § = <{{ tag }}
    else if (mode === 1) { if (c === '"') mode = 2; else if (c === "'") mode = 3; else if (c === '>') { mode = 0; at = -1; } }
    else if (mode === 2) { if (c === '"') mode = 1; }
    else if (c === "'") mode = 1;
  }
  return { st, open };
}

export function scan(src) {
  const masked = src.replace(/\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\}/g, (m) => '§'.repeat(m.length));
  const { st, open: tagAt } = tagState(masked);
  const hits = [];
  const re = /\{\{-?([\s\S]*?)-?\}\}/g;
  let m;
  while ((m = re.exec(src))) {
    const p = m.index;
    if (st[p] !== 2) continue;                       // not inside a double-quoted attribute value
    const before = masked.slice(tagAt[p], p);
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
    ['<img alt="{% if a > b %}{{ product.title }}{% endif %}">', 1],       // 18i: a '>' inside {% %} inside a value
    ['<img {% if a > b %}class="x"{% endif %} alt="{{ product.title }}">', 1], // 18i: proves the Liquid mask — this '>' sits between attributes
    ['<div data-t="{% if a == "x" %}{{ b }}{% endif %}">', 1],             // 18i: proves the mask for quotes inside a Liquid tag
    ['<img alt="a > b {{ product.title }}">', 1],                          // 18i: a '>' inside a quoted value is not the tag's end
    ['<img alt="a < b {{ product.title }}">', 1],                          // 18i: nor is a '<' inside one the start of a new tag
    ['<{{ tag }} href="{{ block.settings.link }}">', 1],                   // 18i: a Liquid-named tag is still a tag
  ];
  /* 18i: the DATA axis — [expr, is it merchant text that can carry a double quote?] */
  const ax = [
    ['product.title', true],
    ['block.settings.name', true],
    ["'general.search.title' | t", false],                                 // pure translation key
    ['shop.name', false],                                                  // set by us, excluded by name
    ['settings.logo_width', false],                                        // matches nothing in RISKY
  ];
  const bad = fx.filter(([s, n]) => scan(s).length !== n);
  const badAx = ax.filter(([e, w]) => dataAxis({ expr: e }) !== w);
  if (bad.length || badAx.length) {
    bad.forEach(([s, n]) => console.error(`  SELF-TEST ${JSON.stringify(s)} want ${n} got ${scan(s).length}`));
    badAx.forEach(([e, w]) => console.error(`  SELF-TEST dataAxis(${JSON.stringify(e)}) want ${w}`));
    process.exit(1);
  }
  var SELF_TEST_N = fx.length + ax.length;                                 // 18i: derived, not typed
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
  console.log(`  self-test: ${SELF_TEST_N}/${SELF_TEST_N}   liquid files scanned: ${files.length}   unescaped attribute outputs: ${all.length}`);
  const byAttr = {};
  for (const h of all) { const k = /^aria-/.test(h.attr) ? 'aria-*' : /^data-/.test(h.attr) ? 'data-*' : h.attr; (byAttr[k] ??= []).push(h); }
  for (const [k, v] of Object.entries(byAttr).sort((a, b) => b[1].length - a[1].length))
    console.log(`  ${k.padEnd(14)} ${String(v.length).padStart(4)}  in ${new Set(v.map((h) => h.f)).size} files`);
  if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(all, null, 1));
}
