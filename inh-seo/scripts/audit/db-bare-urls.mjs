/* CORRECTION to db-label-shape.mjs: it counted scholarly HREFS. Three of the four articles it
 * reported as having "zero scholarly links" carry their URLs as PLAIN TEXT in the Sources list.
 * A link-based probe reported them unverifiable; they are merely unclickable. */
import fs from 'node:fs';
const rows = JSON.parse(fs.readFileSync('data/db-label-big29.json','utf8'));
import { gql } from '../lib/shopify.js';
let after=null, arts=new Map();
do { const q=await gql(`query($a:String){ articles(first:50, after:$a){ pageInfo{hasNextPage endCursor} nodes{ handle body } } }`,{a:after});
  q.articles.nodes.forEach(n=>arts.set(n.handle,n.body)); after=q.articles.pageInfo.hasNextPage?q.articles.pageInfo.endCursor:null; } while(after);
const SCH=/pubmed|ncbi\.nlm|pmc\.|doi\.org|tandfonline|sciencedirect|springer|nature\.com|jamanetwork|bmj|nejm|bioresources/i;
console.log(' href  bare  total  handle');
let fixed=0;
for (const r of rows) {
  const b = arts.get(r.handle) || '';
  const hrefs = [...b.matchAll(/href="(https?:[^"]+)"/g)].map(m=>m[1]).filter(u=>SCH.test(u));
  const stripped = b.replace(/<a\b[^>]*>.*?<\/a>/gs,' ').replace(/<[^>]+>/g,' ');
  const bare = [...stripped.matchAll(/https?:\/\/[^\s<"')\]]+/g)].map(m=>m[0]).filter(u=>SCH.test(u));
  const tot = new Set([...hrefs,...bare].map(u=>u.replace(/\/$/,''))).size;
  if (r.scholarlyDistinct===0 && bare.length) fixed++;
  console.log(`${String(hrefs.length).padStart(5)} ${String(bare.length).padStart(5)} ${String(tot).padStart(6)}  ${r.handle}`);
}
console.log(`\narticles previously reported as "zero scholarly links" that in fact carry bare URLs: ${fixed}`);
