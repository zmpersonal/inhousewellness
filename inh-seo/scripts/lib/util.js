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
    // Round 18i: a corrupt line used to be skipped, so the newest write could fall back to an older one and a
    // stale dump pass. A log we cannot read is a log we cannot trust — refuse.
    try { at = new Date(JSON.parse(line).at); } catch { throw new Error(`data/changelog.jsonl has an unparseable line — refusing to judge freshness: ${line.slice(0, 80)}`); }
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
  /* Round 18i: a missing or empty changelog used to return here as FRESH — the absence of a record read as
     the absence of writes. data/ is gitignored, so a fresh checkout has no changelog and every dump in it
     would have passed. Refuse instead; a genuinely new store can create an empty-but-dated log by hand. */
  if (!lastWrite) {
    console.error('\nABORTED — no readable data/changelog.jsonl, so nothing can say whether these dumps are current.\n');
    process.exit(1);
  }

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
  /* Round 18i guard audit — two holes, both proved by scripts/audit/util-guards-selftest.mjs:
     1. A tag that was ALREADY unbalanced was waved through whatever this edit did to it ("pre-existing"),
        so stripping one more </p> from a page that was one short passed. The test is now the DELTA: this
        edit must leave each tag's open-minus-close exactly where it found it.
     2. Only nine tags were counted. span, div, the table family, h1/h4-h6, blockquote, b/i/u, sup/sub,
        figure and section were invisible — and three reusable scripts edit spans.
     Plus NESTING: counts cannot see <p>a</li><li>b</p>. Mis-nested closers are counted the same way, by delta. */
  const TAGS = ['p', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'strong', 'em', 'b', 'i', 'u', 'span', 'div',
    'table', 'thead', 'tbody', 'tr', 'td', 'th', 'blockquote', 'figure', 'section', 'sup', 'sub'];
  const TOK = new RegExp(`<(/?)(${TAGS.join('|')})(?=[\\s>/])[^>]*>`, 'gi');
  const count = (s) => {
    const c = {};
    for (const tag of TAGS) c[tag] = [0, 0];
    let misnested = 0; const stack = [];
    for (const m of s.matchAll(TOK)) {
      const tag = m[2].toLowerCase(), close = m[1] === '/';
      if (/\/>$/.test(m[0]) && !close) continue;                          // self-closed: neither opens nor closes
      c[tag][close ? 1 : 0]++;
      if (!close) { stack.push(tag); continue; }
      const at = stack.lastIndexOf(tag);
      if (at === -1) { misnested++; continue; }                            // a closer with nothing open
      misnested += stack.length - 1 - at;                                  // anything still open inside it
      stack.length = at;
    }
    c._misnested = misnested;
    c._empty = (s.match(/<(li|p)\b[^>]*>\s*(?:<(?:p|span)\b[^>]*>\s*<\/(?:p|span)>\s*)?<\/\1>/gi) || []).length;
    return c;
  };
  const now = count(html);
  const was = before == null ? null : count(before);
  const problems = [], preexisting = [];
  for (const tag of TAGS) {
    const [o, c] = now[tag];
    const d = o - c, wasD = was ? was[tag][0] - was[tag][1] : 0;
    if (d === wasD) { if (d !== 0) preexisting.push(`<${tag}> ${o} open / ${c} close (unchanged by this edit)`); continue; }
    problems.push(`<${tag}> ${o} open / ${c} close${was ? ` — was ${was[tag][0]} / ${was[tag][1]}, so this edit changed the balance` : ''}`);
  }
  {
    const introduced = was ? now._misnested - was._misnested : now._misnested;
    if (introduced > 0) problems.push(`${introduced} mis-nested closing tag(s) introduced by this edit`);
    else if (now._misnested) preexisting.push(`${now._misnested} mis-nested closing tag(s), already present before this edit`);
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

/* ---------------------------------------------------------------------------
 * assertNoLinkLoss — instance 55, as a guard rather than a paragraph.
 *
 * Writing staged copy over a live field reverted three C4 cluster links that had been added to LIVE and never to
 * the staged file. assertReach could not see it: the field was DECLARED, so a change inside it was allowed by
 * construction. This compares the hrefs the record carries NOW against the hrefs the write would leave, as a
 * multiset, and refuses if any would disappear. A deliberate removal is named, per href, in `allowed`.
 * ------------------------------------------------------------------------- */
export function linksLost(beforeHtml, afterHtml) {
  const hrefs = (h) => [...String(h || '').matchAll(/<a\b[^>]*?\bhref="([^"]*)"/gi)].map((m) => m[1]);
  const left = hrefs(afterHtml); const lost = [];
  for (const h of hrefs(beforeHtml)) { const i = left.indexOf(h); if (i === -1) lost.push(h); else left.splice(i, 1); }
  return lost;
}
export function assertNoLinkLoss(beforeHtml, afterHtml, label = 'record', allowed = []) {
  const lost = linksLost(beforeHtml, afterHtml).filter((h) => !allowed.includes(h));
  if (!lost.length) return;
  console.error(`REFUSING — ${label}: this write would REMOVE ${lost.length} link(s) the record carries now:`);
  lost.forEach((h) => console.error(`    ${h}`));
  console.error('  If they were added out of band (instance 55), the staged copy is stale — update it. If removal is intended, name each href.');
  process.exit(1);
}

/* ---------------------------------------------------------------------------
 * assertOneWritePerRecord — instance 62.
 *
 * A batch that loops over INSTRUCTIONS and writes per instruction will send two
 * mutations for one record when two instructions name it. Each is computed from
 * the same pre-batch snapshot, so the second erases the first. Nothing fails:
 * both writes succeed, both report success, and `assertReach` cannot see it
 * because the field was DECLARED — a guard cannot catch a defect inside the
 * thing it was told to allow.
 *
 * Call this on the write list, immediately before the mutation loop. It refuses
 * rather than warns: a warning in a 56-row apply is a line nobody reads.
 *
 * The fix when it fires is never `--force`. It is to accumulate the record's
 * state across the instructions and write once.
 * ------------------------------------------------------------------------- */
export function assertOneWritePerRecord(targets, keyOf, label = 'batch') {
  const seen = new Map();
  for (const [i, t] of targets.entries()) {
    const k = keyOf(t);
    if (k === undefined || k === null || k === '') {
      throw new Error(`${label}: write ${i} has no record key — cannot prove one write per record`);
    }
    if (seen.has(k)) seen.get(k).push(i); else seen.set(k, [i]);
  }
  const dup = [...seen.entries()].filter(([, ix]) => ix.length > 1);
  if (!dup.length) return targets;
  const lines = dup.map(([k, ix]) => `    ${k} — writes ${ix.join(', ')}`).join('\n');
  throw new Error(
    `${label}: ${dup.length} record(s) would be written more than once in one run.\n${lines}\n` +
    `  The later write is built from the pre-batch snapshot and will ERASE the earlier one.\n` +
    `  Group the instructions under the record, apply them to one accumulated value, write once.\n` +
    `  See instance 62 in reports/round-1-summary.md.`
  );
}
