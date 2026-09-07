import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as cheerio from 'cheerio';

// fileURLToPath, not .pathname — .pathname is percent-encoded, so a repo path
// containing a space resolved to a literal "Claude%20Master" directory and every
// dump, backup and changelog landed outside the repo.
export const ROOT = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
export const DATA = path.join(ROOT, 'data');
export const REPORTS = path.join(ROOT, 'reports');
export const CONTENT = path.join(ROOT, 'content');

for (const d of [DATA, REPORTS, CONTENT]) fs.mkdirSync(d, { recursive: true });

/* ---------- CLI ---------- */

export function parseArgs() {
  const argv = process.argv.slice(2);
  const flags = { apply: false, limit: null, only: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--apply') flags.apply = true;
    else if (a === '--dry-run') flags.apply = false;
    else if (a === '--limit') flags.limit = Number(argv[++i]);
    else if (a === '--only') flags.only = argv[++i].split(',').map((s) => s.trim());
  }
  return flags;
}

export function banner(name, flags) {
  const mode = flags.apply ? 'APPLY (writes to Shopify)' : 'DRY RUN (no writes)';
  console.log(`\n=== ${name} — ${mode} ===\n`);
  if (!flags.apply) console.log('Pass --apply to execute. Nothing will change until you do.\n');
}

/* ---------- IO ---------- */

export const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

export function writeJSON(p, obj) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(obj, null, 2));
  console.log(`  wrote ${path.relative(ROOT, p)}`);
}

/* ---------- Backups & changelog ---------- */

export function backup(label, payload) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const p = path.join(DATA, 'backups', stamp, `${label}.json`);
  writeJSON(p, payload);
  return p;
}

export function logChange(entry) {
  const p = path.join(DATA, 'changelog.jsonl');
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.appendFileSync(p, JSON.stringify({ at: new Date().toISOString(), ...entry }) + '\n');
}

/* ---------- Staleness guard ---------- */

/**
 * Timestamp of the most recent mutation we have recorded, or null if nothing
 * has ever been written.
 */
export function lastMutationAt() {
  const p = path.join(DATA, 'changelog.jsonl');
  if (!fs.existsSync(p)) return null;
  const lines = fs.readFileSync(p, 'utf8').trim().split('\n').filter(Boolean);
  if (!lines.length) return null;
  let newest = null;
  for (const line of lines) {
    let at;
    try { at = new Date(JSON.parse(line).at); } catch { continue; }
    if (!Number.isNaN(at.getTime()) && (newest === null || at > newest)) newest = at;
  }
  return newest;
}

/**
 * Abort unless every dump this script reads is newer than the last mutation.
 *
 * An apply script that reads a dump taken before the previous apply will
 * happily write pre-change values back to Shopify — silently undoing work that
 * already succeeded. That very nearly reverted the 1.3 clear-broken-copy run,
 * so this is a code gate rather than a note in the README.
 *
 * `dumps` maps a dump filename to the npm script that regenerates it.
 */
export function assertFresh(dumps) {
  const lastWrite = lastMutationAt();
  if (!lastWrite) return;

  const stale = [];
  for (const [file, command] of Object.entries(dumps)) {
    const p = path.join(DATA, file);
    if (!fs.existsSync(p)) {
      stale.push({ file, command, why: 'missing' });
      continue;
    }
    const dumped = fs.statSync(p).mtime;
    if (dumped < lastWrite) {
      stale.push({ file, command, why: `dumped ${dumped.toISOString()}` });
    }
  }
  if (!stale.length) return;

  console.error('\nABORTED — stale audit data.\n');
  console.error(`  Last recorded mutation: ${lastWrite.toISOString()}`);
  console.error('  These dumps predate it, so they no longer describe the store:\n');
  for (const s of stale) console.error(`    ${s.file.padEnd(24)} ${s.why}`);
  console.error('\n  Writing from them could revert a change that already succeeded.');
  console.error('  Re-run first:\n');
  for (const c of [...new Set(stale.map((s) => s.command))]) console.error(`    ${c}`);
  console.error('');
  process.exit(1);
}

/* ---------- Diff output ---------- */

export function showDiff(label, before, after) {
  const trim = (s) => (s == null ? '(empty)' : String(s).replace(/\s+/g, ' ').slice(0, 240));
  console.log(`\n  ${label}`);
  console.log(`    - ${trim(before)}`);
  console.log(`    + ${trim(after)}`);
}

/* ---------- HTML cleaning ---------- */

const ALLOWED_TAGS = new Set([
  'p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'em', 'b', 'i',
  'a', 'br', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'blockquote',
  // Images are allow-listed: an unwrapped <img> is a silently deleted image.
  // src/alt/width/height survive because the stripper only drops data-*,
  // class, style and id.
  'img', 'figure', 'figcaption',
]);

/**
 * Strip pasted-editor residue: data-* attributes, class/style, and any
 * tag outside the allow-list (unwrapped, contents preserved).
 * Uses a real parser — never regex on HTML.
 */
export function cleanHTML(html) {
  if (!html) return html;
  const $ = cheerio.load(html, null, false);

  $('*').each((_, el) => {
    if (el.type !== 'tag') return;
    const attrs = { ...el.attribs };
    for (const name of Object.keys(attrs)) {
      if (name.startsWith('data-') || name === 'class' || name === 'style' || name === 'id') {
        delete el.attribs[name];
      }
    }
    // href/title/target survive on anchors; everything else is dropped above.
    if (!ALLOWED_TAGS.has(el.tagName)) {
      $(el).replaceWith($(el).contents());
    }
  });

  // No `>\s+<` collapse: it welded adjacent inline tags together, turning
  // "<strong>Cedar</strong> <em>barrel</em>" into "Cedarbarrel".
  return $.html()
    .replace(/<p>\s*<\/p>/g, '')
    .replace(/[ \t]*\n[ \t\n]*/g, '\n')
    .trim();
}

/** Patterns that indicate placeholder or leaked-AI content. */
export const BROKEN_PATTERNS = [
  { id: 'ai-citation-ref', re: /:?contentReference|oaicite/i, severity: 'P0' },
  { id: 'placeholder-test', re: /^\s*<p>\s*TEST\s*<\/p>\s*$/i, severity: 'P0' },
  { id: 'placeholder-word', re: /\b(lorem ipsum|placeholder text|TODO:|FIXME)\b/i, severity: 'P0' },
  { id: 'editor-data-attrs', re: /data-(start|end|is-only-node|is-last-node)=/i, severity: 'P1' },
  // cleanHTML unwraps any tag outside ALLOWED_TAGS, <meta> included. Without a
  // matching pattern here the scan reported 4 dirty collections while the
  // cleaner found 7 — the report and the cleaner must agree on "broken".
  { id: 'stray-meta-tag', re: /<meta[\s>]/i, severity: 'P1' },
  { id: 'tailwind-residue', re: /class="[^"]*(-mx-px|relative\s|whitespace-pre|md:-mx-)/i, severity: 'P1' },
  { id: 'empty-paragraph', re: /^\s*(<p>(\s|&nbsp;|<br\s*\/?>)*<\/p>\s*)+$/i, severity: 'P2' },
];

export function scanForBroken(html) {
  if (!html) return [];
  return BROKEN_PATTERNS.filter((p) => p.re.test(html)).map((p) => ({
    id: p.id,
    severity: p.severity,
  }));
}

export function contextAround(html, re, chars = 160) {
  const m = html.match(re);
  if (!m) return null;
  const i = Math.max(0, m.index - chars / 2);
  return html.slice(i, i + chars).replace(/\s+/g, ' ');
}
