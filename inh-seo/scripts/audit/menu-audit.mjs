import fs from 'node:fs';
import path from 'node:path';
import { DATA, ROOT } from '../lib/util.js';
import { gql } from '../lib/shopify.js';
const g = await gql(`{ menus(first:60){ nodes{ handle title items{ id title url type resourceId items{ id title url type resourceId items{ id title url type resourceId items{ id title url type resourceId } } } } } } }`);
const walkDir=(d,out=[])=>{for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=d+'/'+e.name; if(e.isDirectory())walkDir(p,out); else if(!/ 2\./.test(e.name)) out.push(p);} return out;};
const blob = walkDir(path.join(ROOT,'theme')).map(f=>{try{return fs.readFileSync(f,'utf8');}catch{return '';}}).join('\n');
const flat=[]; const walk=(it,tr,mh)=>{for(const x of it||[]){flat.push({menu:mh,trail:[...tr,x.title].join(' > '),url:x.url,type:x.type,rid:x.resourceId});walk(x.items,[...tr,x.title],mh);}};
g.menus.nodes.forEach(mn=>walk(mn.items,[],mn.handle));
const orphan=[],live=[];
for(const mn of g.menus.nodes){
  (blob.includes(`'${mn.handle}'`)||blob.includes(`"${mn.handle}"`)) ? live.push(mn) : orphan.push(mn);
}
console.log(`MENUS: ${g.menus.nodes.length} total | ${live.length} referenced by the theme | ${orphan.length} ORPHANED\n`);
console.log('ORPHANED — no theme file names them, so their contents reach no customer:');
orphan.forEach(mn=>{
  const items=flat.filter(x=>x.menu===mn.handle);
  console.log(`   ${mn.handle.padEnd(30)}${String(items.length).padStart(3)} items   "${mn.title}"`);
});
fs.writeFileSync(path.join(DATA,'menu-audit.json'),JSON.stringify({orphanHandles:orphan.map(o=>o.handle),liveHandles:live.map(o=>o.handle),items:flat},null,2));
console.log(`\ntotal menu items across all menus: ${flat.length}`);
console.log('wrote data/menu-audit.json');
