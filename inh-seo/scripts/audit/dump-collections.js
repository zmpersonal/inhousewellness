import { paginate } from '../lib/shopify.js';
import { writeJSON, DATA } from '../lib/util.js';
import path from 'node:path';

const Q = `query($first:Int!,$after:String){
  collections(first:$first, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{
      id handle title updatedAt sortOrder
      descriptionHtml
      # productsCount is NOT read here: it is cached behind the write that
      # changed it (Round-1 instance 12). The dump counts by enumeration.
      products(first: 250) { pageInfo { hasNextPage } nodes { id } }
      seo{ title description }
      ruleSet{ appliedDisjunctively rules{ column relation condition } }
      resourcePublicationsCount{ count }
      resourcePublications(first:10){ nodes{ isPublished publication{ name } } }
    }
  }
}`;

const rows = await paginate(Q, 'collections');
const out = rows.map(c => ({
  id: c.id,
  handle: c.handle,
  title: c.title,
  products: c.products?.nodes?.length ?? 0,
  // Flagged rather than silently truncated — see instance 12.
  productsCountTruncated: c.products?.pageInfo?.hasNextPage === true,
  descriptionHtml: c.descriptionHtml || '',
  descriptionLength: (c.descriptionHtml || '').replace(/<[^>]+>/g,'').trim().length,
  seoTitle: c.seo?.title || null,
  seoDescription: c.seo?.description || null,
  smart: !!c.ruleSet,
  sortOrder: c.sortOrder,
  publications: c.resourcePublicationsCount?.count ?? 0,
  publicationNames: (c.resourcePublications?.nodes ?? []).map(n => n.publication.name),
  // Named Online Store publication, NOT "published to any channel".
  // resourcePublicationsCount > 0 counted Point of Sale and Shop too, so after
  // the 1.5 unpublish it reported 7 of 8 deindexed collections as still
  // published — a confident wrong answer, and it would have made a re-run of
  // unpublish-collections.js re-target them. publishedOnCurrentPublication is
  // NOT the fix here: it needs read_product_listings, which this app lacks.
  publishedOnline: (c.resourcePublications?.nodes ?? [])
    .some(n => n.publication.name === 'Online Store' && n.isPublished),
  updatedAt: c.updatedAt,
}));

writeJSON(path.join(DATA, 'collections.json'), out);
console.log(`\n${out.length} collections`);
console.log(`  ${out.filter(c=>c.descriptionLength===0).length} with no description`);
console.log(`  ${out.filter(c=>!c.seoTitle).length} with no SEO title`);
console.log(`  ${out.filter(c=>c.products===0).length} with zero products`);
