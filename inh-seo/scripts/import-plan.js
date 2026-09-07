/**
 * Merges the client-filled worksheet back into data/collections-plan.json.
 *
 * Export the Google Sheet "Collections" tab as CSV, save it to
 * data/worksheet.csv, then run:  npm run import:plan
 *
 * Only the client-owned columns are merged. Audit columns are never
 * overwritten from the CSV — they come from the live store.
 */
import fs from 'node:fs';
import path from 'node:path';
import { readJSON, writeJSON, DATA } from './lib/util.js';

const csvPath = path.join(DATA, 'worksheet.csv');
if (!fs.existsSync(csvPath)) {
  console.error('Missing data/worksheet.csv — export the Collections tab as CSV first.');
  process.exit(1);
}

function parseCSV(text) {
  const rows = [];
  let row = [], field = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"' && text[i+1] === '"') { field += '"'; i++; }
      else if (ch === '"') q = false;
      else field += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (ch !== '\r') field += ch;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

const rows = parseCSV(fs.readFileSync(csvPath, 'utf8')).filter(r => r.some(c => c.trim()));
const header = rows.shift().map(h => h.trim());
const col = (name) => header.findIndex(h => h.toLowerCase() === name.toLowerCase());

const IDX = {
  handle: col('Handle'),
  action: col('ACTION'),
  keyword: col('PRIMARY KEYWORD'),
  seoTitle: col('NEW SEO TITLE'),
  meta: col('NEW META DESCRIPTION'),
  notes: col('WRITER NOTES'),
};
for (const [k, v] of Object.entries(IDX)) {
  if (v === -1) { console.error(`CSV is missing the "${k}" column. Headers found: ${header.join(' | ')}`); process.exit(1); }
}

const plan = readJSON(path.join(DATA, 'collections-plan.json'));
const byHandle = new Map(plan.map(p => [p.handle, p]));
let merged = 0, unknown = [];

for (const r of rows) {
  const handle = (r[IDX.handle] || '').trim();
  if (!handle) continue;
  const p = byHandle.get(handle);
  if (!p) { unknown.push(handle); continue; }
  const set = (key, val) => { const v = (val || '').trim(); if (v) p[key] = v; };
  set('action', r[IDX.action]);
  set('primaryKeyword', r[IDX.keyword]);
  set('newSeoTitle', r[IDX.seoTitle]);
  set('newMetaDescription', r[IDX.meta]);
  set('writerNotes', r[IDX.notes]);
  merged++;
}

writeJSON(path.join(DATA, 'collections-plan.json'), plan);
console.log(`\nMerged ${merged} rows.`);
if (unknown.length) console.log(`Unknown handles ignored: ${unknown.join(', ')}`);

const ready = plan.filter(p => p.newSeoTitle).length;
const toWrite = plan.filter(p => ['WRITE','REWRITE','URGENT'].includes(p.action)).length;
console.log(`${ready} have an SEO title ready to apply.`);
console.log(`${toWrite} still need description copy.`);
