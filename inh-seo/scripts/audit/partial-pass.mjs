/* partial-pass — articles that were EDITED but never READ.
 *
 * An article corrected on one axis reads as reviewed to anyone who sees the
 * changelog. The note saying otherwise is per-article prose, which nobody
 * aggregates. This computes the class.
 *
 * READ  = an entry in data/article-claim-register.json, which records who read it,
 *         when, a verdict and a line of reasoning.
 * EDITED= a mutation against the article in data/changelog.jsonl.
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, REPORTS } from '../lib/util.js';

const T = readJSON(path.join(DATA, 'content.json'));
const reg = readJSON(path.join(DATA, 'article-claim-register.json'));
const list = (x) => (Array.isArray(x) ? x : Object.values(x).find(Array.isArray) || []);
const READ = new Set(list(reg).map((r) => r.handle).filter(Boolean));

const edits = new Map();
for (const line of fs.readFileSync(path.join(DATA, 'changelog.jsonl'), 'utf8').split('\n')) {
  if (!line.trim()) continue;
  let j; try { j = JSON.parse(line); } catch { continue; }
  const h = j.handle; if (!h) continue;
  if (!(j.field === 'body' || /article/i.test(j.resource || ''))) continue;
  edits.set(h, (edits.get(h) || 0) + 1);
}

const articles = new Set((T.articles || []).map((a) => a.handle));
const rows = [...edits.entries()]
  .filter(([h]) => articles.has(h))
  .map(([h, n]) => ({ handle: h, edits: n, read: READ.has(h) }))
  .sort((a, b) => b.edits - a.edits);

const partial = rows.filter((r) => !r.read);
console.log(`\npartial-pass — articles edited but with no recorded read\n`);
console.log(`  articles edited            : ${rows.length}`);
console.log(`  of those, read and recorded: ${rows.length - partial.length}`);
console.log(`  PARTIAL PASS              : ${partial.length}\n`);
for (const r of partial) console.log(`      ${String(r.edits).padStart(3)} edit(s)   ${r.handle}`);
console.log(`\n  An article here has been changed and never assessed. The changelog says`);
console.log(`  it was worked on; nothing says how much of it was looked at.`);
fs.writeFileSync(path.join(REPORTS, 'partial-pass.md'),
  `# Partial-pass articles\n\nRun ${new Date().toISOString()}\n\n` +
  `**${partial.length} articles have been edited and never read.** An article corrected on one axis reads as reviewed to anyone who sees the changelog.\n\n` +
  partial.map((r) => `- \`${r.handle}\` — ${r.edits} edit(s), no entry in the claim register`).join('\n'));
