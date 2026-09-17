/* B2 — alt text for images with none, on ACTIVE products.
 *
 * We cannot see the images, and hard rule 6 forbids inventing product facts, so
 * the alt is derived from what we hold: the product title and the image's
 * position. It describes WHICH image rather than WHAT IS IN IT — honest, and
 * better for a screen reader than the existing convention.
 *
 * THE EXISTING CONVENTION IS NOT COPIED, deliberately. 1,255 images carry
 * "{title}-{vendor}-InHouse Wellness", median 111 chars, 305 over 125, and it is
 * IDENTICAL on every image of a product. A screen reader hearing that six times
 * learns nothing. Reported separately rather than propagated.
 *
 * Titles are trimmed to 125 chars on a word boundary; 7 of 481 exceed it.
 */
import fs from 'node:fs';
import { writeJSON, DATA } from '../lib/util.js';
import path from 'node:path';

const media = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const blank = (s) => !s || !String(s).trim();

/* Collapse whitespace built from CODE POINTS, not typed glyphs. */
const WS = new RegExp('[\\u00A0\\u202F\\u2009\\u200B]', 'g');
const clean = (s) => s.replace(WS, ' ').replace(/\s+/g, ' ').trim();

function trim125(s) {
  if (s.length <= 125) return s;
  const cut = s.slice(0, 125);
  const sp = cut.lastIndexOf(' ');
  return (sp > 90 ? cut.slice(0, sp) : cut).replace(/[\s,\-–—]+$/, '');
}

const rows = [];
const held = [];
for (const p of media.filter((x) => x.status === 'ACTIVE')) {
  const imgs = (p.media.nodes || []).filter((m) => m && m.image);
  /* ALL images, not only the blanks. Client ruling: one pass, one convention.
   * Leaving the 1,255 existing alts would make the estate half-new and
   * half-stuffed, with nothing to tell the next person which was intended. */
  if (!imgs.length) continue;
  const title = trim125(clean(p.title));
  const total = imgs.length;
  for (const m of imgs) {
    const pos = imgs.indexOf(m) + 1;
    /* Position 1 is the featured image: the product, plainly named.
     * Later positions say which view, so they are distinguishable. */
    /* Reserve room for the suffix BEFORE trimming the title. Trimming the
     * COMPOSED string silently drops the suffix on long titles — caught in the
     * 20-row sample, where a 123-char title gave all 5 images identical alt,
     * which is the exact failure the position suffix exists to prevent. */
    let alt;
    if (pos === 1 || total === 1) {
      alt = title;
    } else {
      const suffix = `, image ${pos} of ${total}`;
      /* Cut on a word boundary. A mid-word truncation ("...Himala, image 2 of 5")
       * is worse than a shorter alt and was visible only in the sample. */
      let room = clean(p.title).slice(0, 125 - suffix.length);
      if (room.length < clean(p.title).length) {
        const sp = room.lastIndexOf(' ');
        if (sp > 40) room = room.slice(0, sp);
      }
      room = room.replace(/[\s,\-–—]+$/, '');
      /* Drop a trailing function word. "…Side Burner and, image 2 of 14" reads as
       * a truncation; 65 rows ended this way and it was invisible in every count. */
      room = room.replace(/[\s,]+\b(and|with|for|the|a|an|in|of|to|or|plus|by|from)$/i, '')
                 .replace(/[\s,\-–—]+$/, '');
      alt = room + suffix;
    }
    const wasBlank = blank(m.image.altText);
    if (!wasBlank && m.image.altText.trim() === alt) continue;   // already correct
    /* Only the machine-stuffed convention gets replaced. Two images on
     * dynamic-venice-elite read "venice-front" and "venice-right" — hand-written,
     * and they say WHICH VIEW, which is more than the generated alt can. Generic
     * text would destroy real information. Held and reported instead. */
    const STUFFED = /-[^-]+-InHouse Wellness\s*$/i;
    if (!wasBlank && !STUFFED.test(m.image.altText)) { held.push({ handle: p.handle, pos, was: m.image.altText }); continue; }
    rows.push({ productHandle: p.handle, productId: p.id, mediaId: m.id, pos, total,
                title: p.title, alt, kind: wasBlank ? 'FILL' : 'REPLACE',
                was: wasBlank ? null : m.image.altText });
  }
}

/* SHARED MEDIA. Alt text is a property of the FILE, not of the product-image
 * relationship. icetubs-icebath and icetubs-icebath-xl share all 8 images, so a
 * product-specific alt would be FALSE on one of the two pages -- it would put
 * "89 in" on the 96-inch product. Caught by assertOneWritePerRecord, which is
 * exactly the read-modify-write shape instance 62 recorded.
 *
 * Resolution: for a shared file use the longest common prefix of the sharing
 * titles, and NO position suffix, because the position differs per product. It
 * says less, and everything it says is true of every page it appears on. */
const byMedia = {};
for (const r of rows) (byMedia[r.mediaId] = byMedia[r.mediaId] || []).push(r);
const sharedNotes = [];
const sharedIdx = {};
const sharedGroups = {};
for (const [mediaId, group] of Object.entries(byMedia).filter(([, g]) => g.length > 1)) {
  const titles = group.map((g) => clean(g.title));
  const shortest = Math.min(...titles.map((t) => t.length));
  let i = 0;
  while (i < shortest && titles.every((t) => t[i] === titles[0][i])) i++;
  let common = titles[0].slice(0, i);
  const sp = common.lastIndexOf(' ');
  if (sp > 0) common = common.slice(0, sp);
  common = common.replace(/[\s,\-\u2013\u2014]+$/, '');
  if (common.length < 12) {
    sharedNotes.push({ mediaId, alt: null, why: 'common prefix too short', products: group.map((g) => g.productHandle) });
    for (const g of group) g.__drop = true;
    continue;
  }
  /* A bare common prefix would be IDENTICAL on all 8 shared files, which is the
   * very defect this pass exists to remove. "image N of M" cannot be used either:
   * the display position differs between the two products, so it would be false on
   * one of them. "view N" distinguishes the files and claims nothing about where
   * they appear. */
  sharedIdx[mediaId] = (sharedGroups[common] = (sharedGroups[common] || 0) + 1);
  const label = common + ', view ' + sharedIdx[mediaId];
  sharedNotes.push({ mediaId, alt: trim125(label), products: group.map((g) => g.productHandle) });
  group[0].alt = trim125(label);
  group[0].shared = group.map((g) => g.productHandle);
  for (const g of group.slice(1)) g.__drop = true;
}
for (let k = rows.length - 1; k >= 0; k--) if (rows[k].__drop) rows.splice(k, 1);
if (sharedNotes.length) {
  console.log('  SHARED MEDIA collapsed: ' + sharedNotes.length + ' file(s)');
  for (const n of sharedNotes.slice(0, 3)) {
    const what = n.alt ? JSON.stringify(n.alt) : 'DROPPED (' + n.why + ')';
    console.log('     ' + n.products.join(' + ') + ' -> ' + what);
  }
}

/* Guard: no alt may carry a JS artefact. A patched replace() lost its second
 * argument and substituted the literal string "undefined" into 8 rows. It was
 * visible only as an over-length count, not as a wrong word. */
const junk = rows.filter((r) => /undefined|null|\[object/.test(r.alt));
if (junk.length) {
  junk.slice(0, 3).forEach((r) => console.log(`  JUNK IN ALT ${r.productHandle}: ${r.alt}`));
  throw new Error(`${junk.length} alt(s) contain a JS artefact`);
}
const oversize = rows.filter((r) => r.alt.length > 125);
if (oversize.length) throw new Error(`${oversize.length} alt(s) over 125 chars`);

/* Guard: within one product, no two generated alts may be identical. This is the
 * defect the sample exposed, so it fails the build rather than warning. */
const perProd = {};
for (const r of rows) (perProd[r.productHandle] = perProd[r.productHandle] || []).push(r.alt);
const dupes = Object.entries(perProd).filter(([, a]) => a.length > 1 && new Set(a).size !== a.length);
if (dupes.length) {
  dupes.slice(0, 5).forEach(([h, a]) => console.log(`  DUPLICATE ALT on ${h}: ${a.length} images, ${new Set(a).size} distinct`));
  throw new Error(`${dupes.length} product(s) would get duplicate alt text`);
}

writeJSON(path.join(DATA, 'alt-text.json'), { built: new Date().toISOString(), rows });
console.log(`  HELD (hand-written alt, not overwritten): ${held.length}`);
held.forEach((h) => console.log(`     ${h.handle} pos ${h.pos}: ${JSON.stringify(h.was)}`));
const prods = new Set(rows.map((r) => r.productHandle)).size;
console.log(`  images needing alt : ${rows.length}`);
console.log(`  products affected  : ${prods}`);
console.log(`  longest alt        : ${Math.max(...rows.map((r) => r.alt.length))} chars`);
console.log(`  any over 125       : ${rows.filter((r) => r.alt.length > 125).length}`);
console.log(`  any blank          : ${rows.filter((r) => blank(r.alt)).length}`);
