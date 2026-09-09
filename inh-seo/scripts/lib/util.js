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
  { id: 'editor-data-attrs', rawOnly: true, re: /data-(start|end|is-only-node|is-last-node)=/i, severity: 'P1' },
  // cleanHTML unwraps any tag outside ALLOWED_TAGS, <meta> included. Without a
  // matching pattern here the scan reported 4 dirty collections while the
  // cleaner found 7 — the report and the cleaner must agree on "broken".
  { id: 'stray-meta-tag', rawOnly: true, re: /<meta[\s>]/i, severity: 'P1' },
  { id: 'tailwind-residue', rawOnly: true, re: /class="[^"]*(-mx-px|relative\s|whitespace-pre|md:-mx-)/i, severity: 'P1' },
  /* Added 9 September 2026 from a HAND read of the estate, not from this list.
     36 Finnmark products carry Material-UI and Emotion class attributes pasted
     from a supplier's React storefront. The scanner had a Tailwind pattern and
     nothing for any other framework, so all 36 were reported clean — by the same
     script that also specifies what gets cleaned. */
  { id: 'framework-class-residue', rawOnly: true, re: /class="[^"]*(?:Mui[A-Z]|\bcss-[a-z0-9]{6,}\b)/, severity: 'P1' },
  /* <h2></h2> renders as nothing and still enters the heading outline. */
  { id: 'empty-heading', rawOnly: true, re: /<h[1-6][^>]*>\s*(?:&nbsp;|\s)*<\/h[1-6]>/i, severity: 'P2' },
  /* Markdown anchor syntax that was never converted. `{#calculator}` renders as
     literal text, usually inside a heading, and makes a page look unmaintained
     to a reader and to a quality rater. 14 articles carry it, 13-17 instances
     each. THIRTEENTH defect form found by READING rather than by this scanner —
     the second in a week, on the script whose scanner both specifies the work
     and verifies it. Unambiguous: `{#slug}` has no legitimate use in stored
     HTML, so this is a clean addition rather than a judgement call. */
  { id: 'markdown-anchor-literal', re: /\{#[a-z0-9][a-z0-9-]*\}/i, severity: 'P1' },
  { id: 'empty-paragraph', rawOnly: true, re: /^\s*(<p>(\s|&nbsp;|<br\s*\/?>)*<\/p>\s*)+$/i, severity: 'P2' },
];

/* CONSIDERED AND REJECTED — kept so it is not "found" again and added.

   `dangling-colon-end`  /:\s*<\/p>\s*(?:<hr>|<h[23])/
   Nine hits across the estate, read by hand, ALL NINE CORRECT: a colon
   introducing the subheading that follows ("actionable techniques you can
   implement:" then <h3>1. Mindful Breathing</h3>). That is ordinary writing.
   Adding it would have made the scanner fire on nine well-formed documents, and
   a scanner that cries wolf gets ignored. The residue rule stands: a check finds
   candidates and a person decides.

   `empty-anchor` (62) — <a id="unknowns"></a> jump targets, all legitimate.
   `empty-table-cell` (63) — blank cells in comparison tables, all legitimate.
   `style-attr` (43 products) — supplier copy; the no-style rule is for
   collection descriptions we write, not for product copy we received. */

export function scanForBroken(html) {
  if (!html) return [];
  /* `textOnly` patterns are tested against the document with <style> and
     <script> contents removed. A negative control caught this: `<style>.a{#fff}
     </style>` fired markdown-anchor-literal, because CSS legitimately contains
     `{#...}`. The pattern was right and the SCOPE was wrong — narrowing the
     regex would have weakened a clean rule to accommodate a place it should
     never have been looking. */
  const visible = html.replace(/<(style|script)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ');
  /* DEFAULT, not a flag — client ruling 9 September 2026. A content probe has no
     business reading <style> or <script>: those are not copy, and every false
     positive they produce costs a narrowing of a rule that was correct. The two
     patterns that DO need the raw document say so with `rawOnly`, because they
     are looking for markup rather than for text. */
  return BROKEN_PATTERNS.filter((p) => p.re.test(p.rawOnly ? html : visible)).map((p) => ({
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

/**
 * Normalise text that came from the store before ANY pattern is run against it.
 *
 * Instance 16: `finnmark-fd-1`'s title reads "Full‑Spectrum" with U+2011
 * NON-BREAKING HYPHEN. It is visually identical to "-" and defeats
 * /full[- ]spectrum/. A correct regex, correct data, and a wrong answer that
 * went into live copy. Earlier, a ZERO-WIDTH SPACE inside `cal-flame` copy
 * did the same thing to a different probe.
 *
 * Text you did not author can contain characters that look identical and are
 * not. Any probe run against product or collection text must normalise first.
 *
 * Handles: the Unicode dash block, soft hyphen, curly quotes, non-breaking and
 * exotic spaces, and zero-width characters (which are DELETED, not spaced —
 * they sit mid-word).
 */
export function normalizeText(s) {
  return String(s ?? '')
    .replace(/[\u200B-\u200D\uFEFF\u2060]/g, '')          // zero-width: delete
    .replace(/[\u2010-\u2015\u2212\u00AD]/g, '-')          // dashes, minus, soft hyphen
    .replace(/[\u2018\u2019\u201B]/g, "'")                  // curly single quotes
    .replace(/[\u201C\u201D\u201F]/g, '"')                  // curly double quotes
    .replace(/[\u00A0\u2000-\u200A\u202F\u205F\u3000]/g, ' ') // exotic spaces
    .normalize('NFKC');
}

/** normalizeText + entity decode + lowercase. The default for any text probe. */
export function probeText(s) {
  return normalizeText(s)
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&')
    .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;/g, '"')
    .replace(/&ndash;/g, '-').replace(/&mdash;/g, '-')
    .toLowerCase();
}

/**
 * Refuses to send structurally broken markup.
 *
 * Instance 38: a regex ate a closing </p>, Shopify's sanitiser repaired the
 * balance on save, and the read-back verification passed while the live page
 * carried an empty <li><p></p></li>. A downstream system that repairs your
 * input hides your defect and substitutes its own artefact, so the read-back
 * reports on the repair rather than on your change.
 *
 * Assert on the string you are about to SEND. Read-back stays as a second check.
 */
export function assertWellFormed(html, label = 'body', before = null) {
  /* Compare against the ORIGINAL when one is given. A guard that blocks on
     defects it did not cause gets routed around, and a routed-around guard is
     worse than no guard: science-of-temperature-therapy-routines already
     carried an empty <p>, and refusing to append one sentence because of it
     would have taught the next person to pass --force. Fail on what this edit
     INTRODUCED; report the rest as pre-existing. */
  const count = (s) => {
    const c = {};
    for (const tag of ['p', 'li', 'ul', 'ol', 'h2', 'h3', 'a', 'strong', 'em']) {
      c[tag] = [(s.match(new RegExp(`<${tag}(?=[\\s>])`, 'gi')) || []).length,
                (s.match(new RegExp(`</${tag}>`, 'gi')) || []).length];
    }
    c._empty = (s.match(/<(li|p)\b[^>]*>\s*(?:<(?:p|span)\b[^>]*>\s*<\/(?:p|span)>\s*)?<\/\1>/gi) || []).length;
    return c;
  };
  const now = count(html);
  const was = before == null ? null : count(before);
  const problems = [], preexisting = [];
  for (const tag of ['p', 'li', 'ul', 'ol', 'h2', 'h3', 'a', 'strong', 'em']) {
    const [o, c] = now[tag];
    if (o === c) continue;
    const wasBroken = was && was[tag][0] !== was[tag][1];
    (wasBroken ? preexisting : problems).push(`<${tag}> ${o} open / ${c} close`);
  }
  if (now._empty) {
    const introduced = was ? now._empty - was._empty : now._empty;
    if (introduced > 0) problems.push(`${introduced} empty <li>/<p> element(s) introduced by this edit`);
    else preexisting.push(`${now._empty} empty <li>/<p> element(s), already present before this edit`);
  }
  if (preexisting.length) {
    console.log(`  note — ${label} carries pre-existing markup problems this edit did not cause and does not fix:`);
    preexisting.forEach((p) => console.log(`    ${p}`));
  }
  if (problems.length) {
    console.error(`REFUSING — ${label} is not well formed, so it would be sent broken and silently repaired downstream:\n`);
    problems.forEach((p) => console.error(`  ${p}`));
    console.error('\nFix the string before sending. A clean read-back afterwards would be the platform\'s repair, not your change.');
    process.exit(1);
  }
}
