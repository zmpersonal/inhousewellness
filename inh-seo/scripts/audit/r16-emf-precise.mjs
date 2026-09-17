/* The mG count, corrected. The first pattern matched \b(mg|milligauss)\b and caught wood-stove
 * EMISSIONS figures — "CO (13% O2): 346 mg/m³", "Dust emission: 22 mg/m³" — on HUUM and Cozy Heat
 * stoves. Those are milligrams per cubic metre, not milligauss. A unit collision, and it would
 * have inflated the headline count in the article.
 *
 * Corrected: require EMF context within the fragment, and exclude anything followed by /m³. */
import { gql } from '../lib/shopify.js';
let after=null,P=[];
do{const q=await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
  nodes{ handle title status vendor descriptionHtml kf: metafield(namespace:"custom",key:"key_feature"){value} } } }`,{a:after});
  P.push(...q.products.nodes); after=q.products.pageInfo.hasNextPage?q.products.pageInfo.endCursor:null;}while(after);
const txt=p=>{const b=[p.descriptionHtml||''];const v=p.kf?.value;if(v){try{const j=JSON.parse(v);const o=[];(function w(n){if(!n)return;if(n.type==='text')o.push(n.value);(n.children||[]).forEach(w);})(j);b.push(o.join(' '));}catch{b.push(v);}}
  return b.join(' ').replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/ /g,' ').replace(/\s+/g,' ');};
const A=P.filter(p=>p.status==='ACTIVE');

/* a real EMF reading: a number + mG/milligauss, NOT followed by /m³, with EMF named nearby */
const EMF_MG = /(?:emf|electromagnetic)[^.]{0,120}?[\d.]+\s*(?:to|–|-|—|and)?\s*[\d.]*\s*(?:mg|milligauss)\b(?!\s*\/)|[\d.]+\s*(?:to|–|-|—|and)?\s*[\d.]*\s*(?:mg|milligauss)\b(?!\s*\/)[^.]{0,120}?(?:emf|electromagnetic)/i;
const FIX=[
  ['Ultra Low EMF levels below 3 mG measured 6–8 inches', true],
  ['EMF under ~2–3 milligauss at 2–3 inches from emitters', true],
  ['CO (13% O2): 346 mg/m³', false],                 // wood-stove emissions — the false positive
  ['Dust emission: 22 mg/m³', false],
  ['200 mg of magnesium per serving', false],
  ['Low EMF technology throughout', false],           // tier word, no number
];
let sf=0; for(const [s,w] of FIX){ if(EMF_MG.test(s)!==w){ console.log(`  FIXTURE FAIL ${JSON.stringify(s)}`); sf++; } }
console.log(`constructed fixtures: ${FIX.length-sf}/${FIX.length}${sf?'  REFUSING':''}`);
if(sf) process.exit(1);

const hits=A.filter(p=>EMF_MG.test(txt(p)));
const DIST=/(\d+\s*(?:to|–|-|—|and)?\s*\d*)\s*(?:inch|in\b|")/i;
/* Locate the mG token itself, then look +/-160 chars around IT. Anchoring the window to the
 * alternation's own match was too narrow and reported 2 where the data plainly shows many. */
const MG_TOKEN=/[\d.]+\s*(?:to|–|-|—|and)?\s*[\d.]*\s*(?:mg|milligauss)\b(?!\s*\/)/i;
let withD=0, near=0, far=0; const examples=[];
for(const p of hits){
  const t=txt(p); const m=t.match(MG_TOKEN); if(!m) continue;
  const i=t.indexOf(m[0]);
  const win=t.slice(Math.max(0,i-160), i+160);
  const d=win.match(DIST);
  if(d){ withD++; const n=parseInt(d[1],10); if(n<=3) near++; else far++;
    examples.push(`${p.vendor} | ${m[0].trim()} @ ${d[1].replace(/\s+/g,'')} in`); }
}
console.log('\nsample readings with their stated distance:');
[...new Set(examples)].slice(0,8).forEach(e=>console.log('   '+e));
const vend={}; for(const p of hits) vend[p.vendor]=(vend[p.vendor]||0)+1;
console.log(`\nACTIVE products publishing a genuine EMF milligauss figure: ${hits.length}`);
console.log(`   …that also state the measuring DISTANCE: ${withD}`);
console.log(`   …measured CLOSE to the panel (2–3 in):   ${near}`);
console.log(`   …measured FURTHER away (6–8 in):         ${far}`);
console.log(`   by vendor: ${JSON.stringify(vend)}`);
