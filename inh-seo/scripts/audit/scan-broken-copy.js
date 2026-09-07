import fs from 'node:fs';
import path from 'node:path';
import { readJSON, writeJSON, DATA, REPORTS, BROKEN_PATTERNS, scanForBroken, contextAround } from '../lib/util.js';

const need = ['collections.json','products.json','content.json'].map(f=>path.join(DATA,f));
for (const f of need) if (!fs.existsSync(f)) {
  console.error(`Missing ${path.basename(f)} — run the dump scripts first (npm run audit).`);
  process.exit(1);
}

const collections = readJSON(need[0]);
const products    = readJSON(need[1]);
const content     = readJSON(need[2]);

const findings = [];
function check(kind, id, handle, field, html) {
  const hits = scanForBroken(html);
  for (const h of hits) {
    const pat = BROKEN_PATTERNS.find(p => p.id === h.id);
    findings.push({
      kind, id, handle, field,
      pattern: h.id, severity: h.severity,
      context: contextAround(html, pat.re),
    });
  }
}

for (const c of collections) check('collection', c.id, c.handle, 'descriptionHtml', c.descriptionHtml);
for (const p of products)    check('product',    p.id, p.handle, 'descriptionHtml', p.descriptionHtml);
for (const a of content.articles) check('article', a.id, a.handle, 'body', a.body);
for (const p of content.pages)    check('page',    p.id, p.handle, 'body', p.body);

writeJSON(path.join(DATA,'broken-copy.json'), findings);

const bySeverity = findings.reduce((m,f)=>((m[f.severity]=(m[f.severity]||0)+1),m),{});
const byPattern  = findings.reduce((m,f)=>((m[f.pattern]=(m[f.pattern]||0)+1),m),{});

const lines = [
  '# Broken copy scan',
  '',
  `Run: ${new Date().toISOString()}`,
  '',
  `**${findings.length} findings** across ${collections.length} collections, ${products.length} products, ${content.articles.length} articles, ${content.pages.length} pages.`,
  '',
  '## By severity',
  ...Object.entries(bySeverity).sort().map(([k,v])=>`- ${k}: ${v}`),
  '',
  '## By pattern',
  ...Object.entries(byPattern).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`- \`${k}\`: ${v}`),
  '',
  '## Findings',
  '',
  '| Severity | Kind | Handle | Pattern | Context |',
  '|---|---|---|---|---|',
  ...findings
    .sort((a,b)=>a.severity.localeCompare(b.severity))
    .map(f=>`| ${f.severity} | ${f.kind} | \`${f.handle}\` | ${f.pattern} | ${(f.context||'').replace(/\|/g,'\\|').slice(0,110)} |`),
];
fs.writeFileSync(path.join(REPORTS,'broken-copy.md'), lines.join('\n'));
console.log(`\n${findings.length} findings — see reports/broken-copy.md`);
