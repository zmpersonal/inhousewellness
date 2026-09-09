import fs from 'node:fs';
import path from 'node:path';
import { readJSON, DATA } from './scripts/lib/util.js';
const C = readJSON(path.join(DATA,'collections.json'));
const P = readJSON(path.join(DATA,'products.json'));
const VOL = new Set(['Golden Designs Inc','Maxxus','Dynamic Saunas']);   // client-named, exactly
const members = h => P.filter(p=>p.collections.includes(h));
const W = {one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,eleven:11,twelve:12,thirteen:13,fourteen:14,fifteen:15,sixteen:16,seventeen:17,eighteen:18,nineteen:19,twenty:20,'twenty-four':24,'twenty-eight':28,thirty:30,'thirty-two':32,'thirty-three':33,'thirty-six':36};
const rows = [];
for (const c of C) {
  if (!c.seoTitle && !c.descriptionLength) continue;
  const m = members(c.handle);
  const act = m.filter(p=>p.status==='ACTIVE');
  const drafts = m.filter(p=>p.status==='DRAFT');
  const volAct = act.filter(p=>VOL.has(p.vendor)).length;
  const volDraft = drafts.filter(p=>VOL.has(p.vendor)).length;
  const share = act.length ? volAct/act.length : 0;
  /* does the TITLE carry a count claim? a bare integer, or a spelled number,
     that is not part of a price, kW, mG, nm, °F or capacity span */
  const t = c.seoTitle || '';
  let claim = null;
  const nm = t.match(/(?<![$\d.,–-])\b(\d{1,3})\b(?!\s*(?:kW|mG|nm|°|V\b|Person|People|–|-))/i);
  if (nm) claim = +nm[1];
  else { const wm = t.toLowerCase().match(new RegExp('\\b('+Object.keys(W).join('|')+')\\b')); if (wm) claim = W[wm[1]]; }
  rows.push({ h:c.handle, title:t, hasTitle:!!c.seoTitle, act:act.length, volAct, volDraft, share, claim,
              exposed: share >= 0.34 && claim !== null });
}
const titled = rows.filter(r=>r.hasTitle);
console.log('=== EXPOSURE: share of ACTIVE members from Golden Designs / Maxxus / Dynamic Saunas ===\n');
console.log('  handle                        act  vol  draft  share  claim  verdict');
titled.filter(r=>r.claim!==null).sort((a,b)=>b.share-a.share).forEach(r=>{
  const v = r.share>=0.34 ? 'EXPOSED' : (r.share>0 ? 'partial' : 'STABLE');
  console.log(`  ${r.h.slice(0,28).padEnd(29)}${String(r.act).padStart(4)}${String(r.volAct).padStart(5)}${String(r.volDraft).padStart(7)}  ${(r.share*100).toFixed(0).padStart(3)}%   ${String(r.claim).padStart(4)}  ${v}`);
});
const exp = titled.filter(r=>r.exposed);
const stable = titled.filter(r=>r.claim!==null && !r.exposed);
const noClaim = titled.filter(r=>r.claim===null);
console.log(`\n  titles with a count claim : ${titled.length-noClaim.length} of ${titled.length}`);
console.log(`  EXPOSED (>=34% volatile)  : ${exp.length}`);
console.log(`  stable                    : ${stable.length}`);
console.log(`  no count claim at all     : ${noClaim.length}  (${noClaim.map(r=>r.h).slice(0,8).join(', ')}${noClaim.length>8?' …':''})`);
console.log(`\n  total volatile products currently DRAFT across titled collections: ${titled.reduce((s,r)=>s+r.volDraft,0)}`);
fs.writeFileSync('data/title-volatility.json', JSON.stringify({ volatileVendors:[...VOL], rows:titled },null,2));
console.log('\n  wrote data/title-volatility.json');
