import { paginate } from '../lib/shopify.js';
import { writeJSON, DATA } from '../lib/util.js';
import path from 'node:path';

const Q = `query($first:Int!,$after:String){
  products(first:$first, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{
      id handle title status vendor productType tags
      descriptionHtml
      seo{ title description }
      priceRangeV2{ minVariantPrice{amount currencyCode} maxVariantPrice{amount} }
      totalInventory
      featuredMedia{ ... on MediaImage { alt } }
      collections(first:25){ nodes{ handle } }
    }
  }
}`;

const rows = await paginate(Q, 'products', {}, 50);
const out = rows.map(p => ({
  id: p.id,
  handle: p.handle,
  title: p.title,
  status: p.status,
  vendor: p.vendor,
  productType: p.productType,
  tags: p.tags,
  descriptionLength: (p.descriptionHtml || '').replace(/<[^>]+>/g,'').trim().length,
  descriptionHtml: p.descriptionHtml || '',
  seoTitle: p.seo?.title || null,
  seoDescription: p.seo?.description || null,
  priceMin: Number(p.priceRangeV2?.minVariantPrice?.amount ?? 0),
  priceMax: Number(p.priceRangeV2?.maxVariantPrice?.amount ?? 0),
  currency: p.priceRangeV2?.minVariantPrice?.currencyCode,
  inventory: p.totalInventory,
  featuredAlt: p.featuredMedia?.alt || null,
  collections: p.collections.nodes.map(c => c.handle),
}));

writeJSON(path.join(DATA, 'products.json'), out);
console.log(`\n${out.length} products`);
console.log(`  ${out.filter(p=>!p.seoTitle).length} missing SEO title`);
console.log(`  ${out.filter(p=>!p.featuredAlt).length} missing featured image alt text`);
console.log(`  ${out.filter(p=>p.descriptionLength<100).length} with under 100 chars of description`);
