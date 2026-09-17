/* Phase 1 — every article, every blog, scored for overlap with the two planned pages.
 * Counts are OCCURRENCES and the unit is named. Delimiters vary, so patterns match CONTENT. */
import { gql } from '../lib/shopify.js';
import fs from 'node:fs';
let after = null, arts = [];
do {
  const q = await gql(`query($a:String){ articles(first:50, after:$a){ pageInfo{hasNextPage endCursor}
    nodes{ handle title body isPublished blog{ handle } } } }`, { a: after });
  arts.push(...q.articles.nodes);
  after = q.articles.pageInfo.hasNextPage ? q.articles.pageInfo.endCursor : null;
} while (after);

const blogs = {};
for (const a of arts) blogs[a.blog.handle] = (blogs[a.blog.handle] || 0) + 1;
console.log(`articles enumerated: ${arts.length}`);
console.log('by blog:', JSON.stringify(blogs));

/* Two target clusters. Match the CONCEPT, not one phrasing — a probe encodes our vocabulary. */
const IRvTRAD = [/infrared\s+(?:sauna\s+)?vs\.?\s+traditional/i, /traditional\s+(?:sauna\s+)?vs\.?\s+infrared/i,
  /dry\s+sauna\s+vs\.?\s+infrared/i, /infrared\s+vs\.?\s+dry/i, /\bir\s+sauna\s+vs/i,
  /difference between (?:an? )?infrared and (?:a )?traditional/i, /traditional.{0,30}infrared.{0,40}(?:differ|compar|versus)/i];
const IRvSTEAM = [/infrared\s+(?:sauna\s+)?vs\.?\s+steam/i, /steam\s+(?:sauna|room)\s+vs\.?\s+infrared/i,
  /difference between (?:an? )?infrared and (?:a )?steam/i, /infrared.{0,30}steam.{0,40}(?:differ|compar|versus)/i];

const rows = [];
for (const a of arts) {
  const body = a.body || '';
  const text = body.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
  const hay = a.title + ' ' + text;
  const t = IRvTRAD.filter((r) => r.test(hay)).length;
  const s = IRvSTEAM.filter((r) => r.test(hay)).length;
  /* cheap proximity signal: does it discuss both modalities at all? */
  const mentionsIR = (text.match(/infrared/gi) || []).length;
  const mentionsTrad = (text.match(/traditional sauna|finnish sauna|dry sauna/gi) || []).length;
  const mentionsSteam = (text.match(/steam (?:sauna|room|shower)/gi) || []).length;
  if (t || s || (mentionsIR > 3 && mentionsTrad > 3) || (mentionsIR > 3 && mentionsSteam > 3))
    rows.push({ handle: a.handle, blog: a.blog.handle, title: a.title, published: a.isPublished,
      words: text.split(' ').length, trad_patterns: t, steam_patterns: s, mentionsIR, mentionsTrad, mentionsSteam });
}
rows.sort((a, b) => (b.trad_patterns + b.steam_patterns) - (a.trad_patterns + a.steam_patterns) || b.mentionsIR - a.mentionsIR);
fs.writeFileSync('data/r16-overlap.json', JSON.stringify(rows, null, 1));
console.log(`\nARTICLES DISCUSSING BOTH SIDES OF EITHER COMPARISON: ${rows.length}\n`);
console.log(`${'pat-T'} ${'pat-S'}  ${'IR'.padStart(4)} ${'TRAD'.padStart(4)} ${'STEAM'.padStart(5)} ${'words'.padStart(6)}  pub  blog/handle`);
for (const r of rows) console.log(`  ${r.trad_patterns}     ${r.steam_patterns}   ${String(r.mentionsIR).padStart(4)} ${String(r.mentionsTrad).padStart(4)} ${String(r.mentionsSteam).padStart(5)} ${String(r.words).padStart(6)}  ${r.published?'Y':'n'}   ${r.blog}/${r.handle}`);
