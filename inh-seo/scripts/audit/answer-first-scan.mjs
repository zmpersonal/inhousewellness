/* Answer-first compliance across every article.
 *
 * Extracts the ACTUAL first paragraph — the first block element carrying real
 * prose — not the first <p>. Three articles were rewritten into the SECOND
 * paragraph because their lede carries a class (`gsg-lede`, `cp-lede`,
 * `rlt-lede`) and the extraction matched a bare <p>. The tag and class are read
 * from the live body, never assumed.
 */
import fs from 'node:fs';

const arts = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const WS = new RegExp('[\\u00A0\\u202F\\u2009\\u200B]', 'g');
const strip = (h) => h.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#39;|&rsquo;/g, "'").replace(/&quot;|&ldquo;|&rdquo;/g, '"')
  .replace(/&ndash;/g, '–').replace(/&mdash;/g, '—').replace(WS, ' ').replace(/\s+/g, ' ').trim();

/* First BLOCK element with prose in it, whatever tag or class it wears. */
export function firstPara(body) {
  if (!body) return null;
  /* Three articles wrap JSON-LD in <p><script>. The script does not render, but a
   * tag-stripper reads its JSON as prose and offers it as the lede. Remove script
   * and style content before looking at anything. */
  body = body.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ');
  /* The estate names its own lede. Several articles ship scoped CSS defining
   * .gsg-lede / .cp-lede / .rlt-lede, and the paragraph carrying it IS the lede.
   * An explicit signal beats any heuristic, so look for it first. */
  const explicit = /<(p|div)\b([^>]*\bclass="[^"]*\blede\b[^"]*"[^>]*)>([\s\S]*?)<\/\1>/i.exec(body);
  if (explicit) {
    const t = strip(explicit[3]);
    if (t.length >= 40) return { tag: explicit[1], attrs: explicit[2].trim(), text: t, raw: explicit[0], index: explicit.index, via: 'lede-class' };
  }
  /* <li> is never a lede — it is a table of contents or a comparison row. */
  const re = /<(p|div|blockquote)\b([^>]*)>([\s\S]*?)<\/\1>/gi;
  let m;
  while ((m = re.exec(body))) {
    const [full, tag, attrs, inner] = m;
    const text = strip(inner);
    /* Skip list of shapes ENUMERATED across all 118 articles, not patched per case:
     *   62  p > p > ul > li      ordinary lede
     *    7  h2 > p > p > ul      opens on a heading
     *    5  p > div > p > div    wrapped
     *    1  first element is a METADATA line ("Last updated: September 2026 ...")
     *    4  first element carries a class (article-updated, gd-guide, and two
     *       assistant-paste classes)
     * A rewrite applied to a metadata line would have been invisible in every
     * count — the lede-class lesson arriving from the other direction. */
    if (text.length < 40) continue;
    if (/^(h1|h2|h3|h4)$/i.test(tag)) continue;         // a heading is not a lede
    /* A wrapper div can hold the lede as its own first text, before any nested
     * element — golden-designs-saunas-review and small-space-sauna-guide both do.
     * Skipping the whole container loses the lede and offers a later paragraph,
     * which reads as circling when the article arrives immediately. Descend: take
     * the container's leading text if it has any, otherwise keep scanning. */
    if (/<(p|div|ul|ol|table)\b/i.test(inner)) {
      const lead = strip(inner.split(/<(?:p|div|ul|ol|table)\b/i)[0]);
      if (lead.length >= 40 && !/^(last updated|table of contents|what\u2019s in this guide|key takeaways?|tl;?dr)/i.test(lead)) {
        return { tag, attrs: attrs.trim(), text: lead, raw: full, index: m.index, via: 'container-lead' };
      }
      continue;
    }
    if (/^(last updated|updated|published|reviewed|written|by |disclosure|note:|editor|disclaimer|transparency|table of contents|key takeaways?|tl;?dr)/i.test(text)) continue;
    if (/\bclass="[^"]*article-updated/i.test(attrs)) continue;
    /* Component wrappers, not prose: CTAs, tables of contents, nav, share bars. */
    if (/\bclass="[^"]*\b(cta|toc|nav|share|breadcrumb|button|btn|callout|badge)\b/i.test(attrs)) continue;
    return { tag, attrs: attrs.trim(), text, raw: full, index: m.index };
  }
  return null;
}

/* Answer-first = the first sentence carries something checkable: a number, a
 * temperature, a price, a dimension, or a flat definitional statement of fact. */
const NUM = /\b\d/;
/* A lede may open by restating the title as a question and answering it in the
 * next breath: "Is cold plunge good for women? Yes - for many women ...". Cutting
 * at the ? reports the question alone and scores the article as circling when it
 * answers immediately. Take the answer too. */
const firstSentence = (t) => {
  const m = t.match(/^[^.!?]{10,400}[.!?]/);
  if (!m) return t.slice(0, 220).trim();
  let out = m[0];
  if (out.trim().endsWith('?')) {
    const rest = t.slice(out.length).match(/^\s*[^.!?]{5,300}[.!?]/);
    if (rest) out += rest[0];
  }
  return out.trim();
};

if (process.argv[1].endsWith('answer-first-scan.mjs')) {
  const rows = [];
  for (const a of arts) {
    const fp = firstPara(a.body);
    if (!fp) { rows.push({ handle: a.handle, blog: a.blog.handle, state: 'NO-PARAGRAPH', published: a.isPublished }); continue; }
    const s1 = firstSentence(fp.text);
    rows.push({
      handle: a.handle, blog: a.blog.handle, published: a.isPublished,
      tag: fp.tag, attrs: fp.attrs, s1,
      hasNumber: NUM.test(s1),
      note: 'state is a screen, not a verdict',
      /* NOT a compliance verdict. This flags whether a digit is present, which is a
       * cheap screen for building a READING QUEUE and nothing more. The criterion is
       * whether the reader knows something after the first sentence, and that is a
       * read. Calling this COMPLIANT produced a queue of 97 where the real set was 5. */
      state: NUM.test(s1) ? 'HAS-FIGURE' : 'READ-ME',
    });
  }
  fs.writeFileSync(process.argv[3], JSON.stringify(rows, null, 1));
  const c = {}; rows.forEach((r) => { c[r.state] = (c[r.state] || 0) + 1; });
  console.log(`  articles scanned: ${rows.length}`);
  for (const [k, v] of Object.entries(c).sort((a, b) => b[1] - a[1])) console.log(`     ${k.padEnd(14)} ${v}`);
  const classed = rows.filter((r) => r.attrs && /class=/i.test(r.attrs));
  console.log(`\n  ledes carrying a class or style (the assumed-<p> trap): ${classed.length}`);
  [...new Set(classed.map((r) => r.attrs))].slice(0, 8).forEach((a) => console.log(`     ${a.slice(0, 78)}`));
  const tags = {}; rows.forEach((r) => { if (r.tag) tags[r.tag] = (tags[r.tag] || 0) + 1; });
  console.log(`  first-paragraph TAG: ${Object.entries(tags).map(([k, v]) => k + ' ' + v).join(' · ')}`);
}
