import { gql } from '../lib/shopify.js';
let after=null,P=[];
do{const q=await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
  nodes{ handle title status vendor descriptionHtml kf: metafield(namespace:"custom",key:"key_feature"){value} collections(first:25){nodes{handle}} } } }`,{a:after});
  P.push(...q.products.nodes); after=q.products.pageInfo.hasNextPage?q.products.pageInfo.endCursor:null;}while(after);
const txt=p=>{const b=[p.descriptionHtml||''];const v=p.kf?.value;if(v){try{const j=JSON.parse(v);const o=[];(function w(n){if(!n)return;if(n.type==='text')o.push(n.value);(n.children||[]).forEach(w);})(j);b.push(o.join(' '));}catch{b.push(v);}}
  return b.join(' ').replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/ /g,' ').replace(/\s+/g,' ');};
const A=P.filter(p=>p.status==='ACTIVE');
const MG=/([\d.]+\s*(?:to|–|-|—)?\s*[\d.]*)\s*(?:mg|milligauss)\b/i;
const DIST=/(\d+\s*(?:to|–|-|—|and)?\s*\d*)\s*(?:inch|in\b|")/i;
console.log('EMF figures WITH the distance they were measured at:\n');
const seen=new Set(); let withDist=0, withoutDist=0;
for(const p of A){
  const t=txt(p); if(!MG.test(t)) continue;
  const w=t.match(new RegExp('.{0,110}'+MG.source+'.{0,80}','i'));
  const frag=(w?w[0]:'').replace(/\s+/g,' ').trim();
  const d=frag.match(DIST);
  if(d) withDist++; else withoutDist++;
  const key=p.vendor+'|'+(d?d[1]:'none');
  if(seen.has(key)) continue; seen.add(key);
  console.log(`  ${p.vendor.padEnd(18)} distance=${d?d[1].replace(/\s+/g,''):'NOT STATED'}`);
  console.log(`      …${frag.slice(0,150)}`);
}
console.log(`\n  ACTIVE products publishing a mG figure: ${withDist+withoutDist}`);
console.log(`     …that also state a measuring DISTANCE: ${withDist}`);
console.log(`     …that state a number with NO distance:  ${withoutDist}`);
