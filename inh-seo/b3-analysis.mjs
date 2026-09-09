import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA, probeText } from './scripts/lib/util.js';
const C = readJSON(path.join(DATA,'collections.json'));
const P = readJSON(path.join(DATA,'products.json'));
const arts = (readJSON(path.join(DATA,'content.json')).articles)||[];
const KR = readJSON(path.join(DATA,'keyword-research.json'));
const T1 = new Set(KR.b3_link_tiers.tier_1_link_from_every_relevant_article);
const T2 = new Set(KR.b3_link_tiers.tier_2_real_volume_moderate_cpc);
const tier = h => T1.has(h) ? 1 : T2.has(h) ? 2 : 3;
const byHandle = new Map(P.map(p=>[p.handle,p]));
const withCopy = new Set(C.filter(c=>c.descriptionLength>0).map(c=>c.handle));
const body = a => String(a.bodyHtml||a.body||'');
const OPS = new Set(['non-bb','more','free-bonus','avada-best-sellers','newest-products','best-selling-products','cold-plunge-favorites','frontpage']);

console.log('=== 1. MISDIRECTED PRODUCT LINKS ===\n');
console.log('An article linking 3+ products that share a collection, without linking that collection.');
console.log('A review linking its subject product is correct and is excluded by the 3+ threshold.\n');
const mis = [];
for (const a of arts) {
  const h = body(a);
  const prods = [...new Set([...h.matchAll(/href="[^"]*\/products\/([a-z0-9-]+)/gi)].map(m=>m[1]))];
  const cols  = new Set([...h.matchAll(/href="[^"]*\/collections\/([a-z0-9-]+)/gi)].map(m=>m[1]));
  if (prods.length < 3) continue;
  const tally = {};
  for (const ph of prods) { const p = byHandle.get(ph); if(!p) continue;
    for (const c of (p.collections||[])) { if(OPS.has(c) || !withCopy.has(c)) continue; (tally[c] ||= []).push(ph); } }
  for (const [c, list] of Object.entries(tally)) {
    if (list.length >= 3 && !cols.has(c)) mis.push({ article:a.handle, title:a.title, collection:c, tier:tier(c), n:list.length, totalProdLinks:prods.length });
  }
}
mis.sort((x,y)=> x.tier-y.tier || y.n-x.n);
const t1 = mis.filter(m=>m.tier===1), t2 = mis.filter(m=>m.tier===2);
console.log(`  misdirected article/collection pairs : ${mis.length}`);
console.log(`  distinct articles involved           : ${new Set(mis.map(m=>m.article)).size} of ${arts.length}`);
console.log(`  product links inside them            : ${mis.reduce((s,m)=>s+m.n,0)} of 581`);
console.log(`  pairs pointing at a TIER 1 collection: ${t1.length}   tier 2: ${t2.length}   tier 3: ${mis.length-t1.length-t2.length}\n`);
console.log('  sample — tier 1, worst first:');
t1.slice(0,10).forEach(m=>console.log(`    ${String(m.n).padStart(2)} products -> ${m.collection.padEnd(20)} | ${String(m.title).slice(0,58)}`));
console.log('\n  sample — tier 2:');
t2.slice(0,5).forEach(m=>console.log(`    ${String(m.n).padStart(2)} products -> ${m.collection.padEnd(20)} | ${String(m.title).slice(0,58)}`));

console.log('\n\n=== 2. DEAD-END ARTICLES ===\n');
const dead = arts.filter(a=>!/href="[^"]*\/(collections|products)\//i.test(body(a)));
const STOP = new Set(['sauna','saunas','with','from','your','that','this','best','guide','review','home','wellness','what','how','the','and','for','are','you','can','does','why','when','2026','2025']);
const tok = s => new Set(probeText(s).replace(/[^a-z0-9 ]/g,' ').split(/\s+/).filter(w=>w.length>3&&!STOP.has(w)));
const cands = C.filter(c=>withCopy.has(c.handle)&&!OPS.has(c.handle));
console.log(`  ${dead.length} of ${arts.length} articles link to no collection and no product.\n`);
console.log('  article                                                   best collection      tier  matched on');
const rows = dead.map(a=>{
  const at = tok((a.title||'')+' '+body(a).replace(/<[^>]+>/g,' ').slice(0,2500));
  const scored = cands.map(c=>{
    const ct = tok(c.title+' '+c.handle.replace(/-/g,' '));
    const hit = [...ct].filter(w=>at.has(w));
    return { h:c.handle, tier:tier(c.handle), score:hit.length + (tier(c.handle)===1?1.5:tier(c.handle)===2?0.5:0), raw:hit };
  }).filter(x=>x.raw.length).sort((x,y)=>y.score-x.score);
  return { title:a.title, best:scored[0]||null };
});
rows.sort((a,b)=>(a.best?a.best.tier:9)-(b.best?b.best.tier:9));
rows.forEach(r=>console.log(`  ${String(r.title).slice(0,56).padEnd(57)} ${r.best?r.best.h.padEnd(20)+'  '+r.best.tier+'    '+r.best.raw.slice(0,3).join(', '):'(no match — needs a human)'}`));
const noMatch = rows.filter(r=>!r.best).length;
console.log(`\n  ${rows.length-noMatch} have a plausible target · ${noMatch} have none and need a human.`);
