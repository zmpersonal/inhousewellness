import { gql } from '../lib/shopify.js';
const txt=(v)=>{try{const j=JSON.parse(v);const o=[];(function w(n){if(!n)return;if(n.type==='text')o.push(n.value);(n.children||[]).forEach(w);})(j);return o.join(' ');}catch{return v;}};
console.log('=== Finnmark combination units (the Infrared vs Steam authority angle) ===');
for (const h of ['finnmark-fd-4','finnmark-fd-5-trinity-xl','finnmark-fd-2','finnmark-fd-3']) {
  const q=await gql(`query($q:String!){ products(first:2, query:$q){ nodes{ handle title status vendor descriptionHtml
    variants(first:2){nodes{price sku}} kf: metafield(namespace:"custom", key:"key_feature"){value} } } }`,{q:`handle:${h}`});
  const p=q.products.nodes.find(x=>x.handle===h);
  if(!p){ console.log(`  ${h}: NOT FOUND`); continue; }
  console.log(`\n  ${p.handle}  ${p.status}  $${p.variants.nodes[0]?.price}  vendor=${p.vendor}`);
  console.log(`    "${p.title}"`);
  const kf=p.kf?.value?txt(p.kf.value).replace(/\s+/g,' '):'(no key_feature)';
  console.log(`    ${kf.slice(0,420)}`);
}
console.log('\n=== collection existence + counts (verify before linking) ===');
for (const h of ['infrared-saunas','sauna','steam-saunas','steam-showers','low-emf','ultra-low-emf','near-zero-emf','far-infrared','full-spectrum','saunas','sauna-heaters']) {
  const q=await gql(`query($q:String!){ collections(first:2, query:$q){ nodes{ handle title productsCount{count} } } }`,{q:`handle:${h}`});
  const c=q.collections.nodes.find(x=>x.handle===h);
  console.log(`  ${c?'ok  ':'MISSING'} /collections/${h.padEnd(18)} ${c?`"${c.title}" — ${c.productsCount.count} products`:''}`);
}
