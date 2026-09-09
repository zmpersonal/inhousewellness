import { gql } from '../lib/shopify.js';
const H = ['true-total-cost-home-sauna','dry-sauna-for-home','sauna-detox-science-explained'];
for (const h of H) {
  const r = await gql(`query($q:String!){ articles(first:1, query:$q){ nodes{ id handle title isPublished
    t: metafield(namespace:"global", key:"title_tag"){ value }
    d: metafield(namespace:"global", key:"description_tag"){ value } } } }`, { q: 'handle:' + h });
  const a = r.articles.nodes[0];
  if (!a) { console.log(h + ': NOT FOUND'); continue; }
  const t = a.t?.value, d = a.d?.value;
  console.log(`\n### ${h}   published=${a.isPublished}`);
  console.log(`  article title : ${a.title}`);
  console.log(`  title_tag     : ${t ? `${t}  (${t.length})` : '(none)'}`);
  console.log(`  description   : ${d ? `${d.slice(0,120)}…  (${d.length})` : '(none)'}`);
}
