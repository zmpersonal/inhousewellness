/* The mG count, corrected. The first pattern matched \b(mg|milligauss)\b and caught wood-stove
 * EMISSIONS figures — "CO (13% O2): 346 mg/m³", "Dust emission: 22 mg/m³" — on HUUM and Cozy Heat
 * stoves. Those are milligrams per cubic metre, not milligauss. A unit collision, and it would
 * have inflated the headline count in the article.
 *
 * Corrected: require EMF context within the fragment, and exclude anything followed by /m³.
 *
 *   node scripts/audit/r16-emf-precise.mjs              # fixtures, then the live count
 *   node scripts/audit/r16-emf-precise.mjs --selftest   # fixtures only (18i: they ran AFTER the
 *                                                       # Admin API fetch, so no credential = no test) */
/* a real EMF reading: a number + mG/milligauss, NOT followed by /m³, with EMF named nearby */
const EMF_MG = /(?:emf|electromagnetic)[^.]{0,120}?[\d.]+\s*(?:to|–|-|—|and)?\s*[\d.]*\s*(?:mg|milligauss)\b(?!\s*\/)|[\d.]+\s*(?:to|–|-|—|and)?\s*[\d.]*\s*(?:mg|milligauss)\b(?!\s*\/)[^.]{0,120}?(?:emf|electromagnetic)/i;
const FIX=[
  ['Ultra Low EMF levels below 3 mG measured 6–8 inches', true],
  ['EMF under ~2–3 milligauss at 2–3 inches from emitters', true],
  ['CO (13% O2): 346 mg/m³', false],                 // wood-stove emissions — the false positive
  ['Dust emission: 22 mg/m³', false],
  ['200 mg of magnesium per serving', false],
  ['Low EMF technology throughout', false],           // tier word, no number
  ['EMF-rated stove: CO 346 mg/m³', false],           // 18i: proves the /m³ exclusion when EMF precedes the figure
  ['CO 346 mg/m³, EMF-rated stove', false],           // 18i: …and when EMF follows it
];
const DIST=/(\d+\s*(?:to|–|-|—|and)?\s*\d*)\s*(?:inch|in\b|")/i;
/* Locate the mG token itself, then look +/-160 chars around IT. Anchoring the window to the
 * alternation's own match was too narrow and reported 2 where the data plainly shows many. */
const MG_TOKEN=/[\d.]+\s*(?:to|–|-|—|and)?\s*[\d.]*\s*(?:mg|milligauss)\b(?!\s*\/)/i;
/** The mG token, the distance stated near it, and whether that distance is close (<= 3 in). */
function readingOf(t){
  const m=t.match(MG_TOKEN); if(!m) return null;
  const i=t.indexOf(m[0]);
  const d=t.slice(Math.max(0,i-160), i+160).match(DIST);
  return { mg: m[0].trim(), dist: d ? d[1].replace(/\s+/g,'') : null, near: d ? parseInt(d[1],10)<=3 : null };
}
/* 18i: the near/far split had no fixture. [text, stated distance, near?] */
const DFIX=[
  ['Ultra Low EMF below 3 mG measured at 2–3 inches', '2–3', true],
  ['EMF under 1 mG at 3 inches from the panel', '3', true],       // the boundary: 3 is near
  ['EMF under 1 mG at 6–8 inches from the panel', '6–8', false],
  ['EMF 3 mG, no distance given', null, null],
];
let sf=0; for(const [s,w] of FIX){ if(EMF_MG.test(s)!==w){ console.log(`  FIXTURE FAIL ${JSON.stringify(s)}`); sf++; } }
for(const [s,dist,nr] of DFIX){ const r=readingOf(s); if(!r||r.dist!==dist||r.near!==nr){ console.log(`  FIXTURE FAIL distance ${JSON.stringify(s)} -> ${JSON.stringify(r)}`); sf++; } }
const NFIX=FIX.length+DFIX.length;
console.log(`constructed fixtures: ${NFIX-sf}/${NFIX}${sf?'  REFUSING':''}`);
if(sf) process.exit(1);
if(process.argv.includes('--selftest')) process.exit(0);

const { gql } = await import('../lib/shopify.js');
let after=null,P=[];
do{const q=await gql(`query($a:String){ products(first:250, after:$a){ pageInfo{hasNextPage endCursor}
  nodes{ handle title status vendor descriptionHtml kf: metafield(namespace:"custom",key:"key_feature"){value} } } }`,{a:after});
  P.push(...q.products.nodes); after=q.products.pageInfo.hasNextPage?q.products.pageInfo.endCursor:null;}while(after);
const txt=p=>{const b=[p.descriptionHtml||''];const v=p.kf?.value;if(v){try{const j=JSON.parse(v);const o=[];(function w(n){if(!n)return;if(n.type==='text')o.push(n.value);(n.children||[]).forEach(w);})(j);b.push(o.join(' '));}catch{b.push(v);}}
  return b.join(' ').replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/ /g,' ').replace(/\s+/g,' ');};
const A=P.filter(p=>p.status==='ACTIVE');

const hits=A.filter(p=>EMF_MG.test(txt(p)));
let withD=0, near=0, far=0; const examples=[];
for(const p of hits){
  const r=readingOf(txt(p)); if(!r||!r.dist) continue;
  withD++; if(r.near) near++; else far++;
  examples.push(`${p.vendor} | ${r.mg} @ ${r.dist} in`);
}
console.log('\nsample readings with their stated distance:');
[...new Set(examples)].slice(0,8).forEach(e=>console.log('   '+e));
const vend={}; for(const p of hits) vend[p.vendor]=(vend[p.vendor]||0)+1;
console.log(`\nACTIVE products publishing a genuine EMF milligauss figure: ${hits.length}`);
console.log(`   …that also state the measuring DISTANCE: ${withD}`);
console.log(`   …measured CLOSE to the panel (2–3 in):   ${near}`);
console.log(`   …measured FURTHER away (6–8 in):         ${far}`);
console.log(`   by vendor: ${JSON.stringify(vend)}`);
