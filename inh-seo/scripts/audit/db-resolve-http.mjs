/* Resolve every distinct scholarly URL across the 26. Records requested AND final — a followed
 * redirect answers from a different URL than the one asked for. */
import fs from 'node:fs';
const rows = JSON.parse(fs.readFileSync('data/db-scholarly-urls.json', 'utf8'));
const UA = { 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122 Safari/537.36' };
const out = []; let done = 0;
const one = async (r) => {
  const rec = { ...r, status: null, final: null, title: null };
  try {
    const res = await fetch(r.url, { headers: UA, redirect: 'follow', signal: AbortSignal.timeout(25000) });
    rec.status = res.status; rec.final = res.url;
    const t = await res.text();
    rec.title = (t.match(/<title[^>]*>([\s\S]{0,300}?)<\/title>/i)?.[1] || '').replace(/\s+/g, ' ').trim().slice(0, 150);
  } catch (e) { rec.status = 'ERR'; rec.title = e.message.slice(0, 60); }
  out.push(rec); if (++done % 25 === 0) console.log(`  …${done}/${rows.length}`);
};
const q = [...rows]; await Promise.all(Array.from({ length: 8 }, async () => { while (q.length) await one(q.pop()); }));
fs.writeFileSync('data/db-resolved.json', JSON.stringify(out, null, 1));
const bad = out.filter((r) => r.status !== 200);
const redir = out.filter((r) => r.status === 200 && r.final && r.final.replace(/\/$/,'') !== r.url.replace(/\/$/,''));
console.log(`\n  resolved ${out.length} distinct scholarly URLs`);
console.log(`  NOT 200: ${bad.length}`);
for (const r of bad) console.log(`     ${String(r.status).padEnd(5)} ${r.url.slice(0,78)}\n           in: ${r.articles.join(', ').slice(0,120)}`);
console.log(`\n  answered from a DIFFERENT url than requested: ${redir.length}`);
for (const r of redir.slice(0, 12)) console.log(`     ${r.url.slice(0,60)}\n        → ${r.final.slice(0,90)}`);
