import { gql, paginate } from '../lib/shopify.js';
import { writeJSON, DATA } from '../lib/util.js';
import path from 'node:path';

const BLOGS = `{ blogs(first:25){ nodes{ id handle title articlesCount{count} } } }`;
const ARTICLES = `query($first:Int!,$after:String){
  articles(first:$first, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{
      id handle title publishedAt isPublished
      blog{ handle }
      author{ name }
      summary
      body
    }
  }
}`;
const PAGES = `query($first:Int!,$after:String){
  pages(first:$first, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{ id handle title isPublished body }
  }
}`;

const blogs = (await gql(BLOGS)).blogs.nodes.map(b => ({
  id: b.id, handle: b.handle, title: b.title, articles: b.articlesCount?.count ?? 0,
}));

const articles = (await paginate(ARTICLES, 'articles', {}, 50)).map(a => ({
  id: a.id, handle: a.handle, title: a.title, blog: a.blog?.handle,
  author: a.author?.name || null,
  published: a.isPublished, publishedAt: a.publishedAt,
  summaryLength: (a.summary || '').length,
  bodyLength: (a.body || '').replace(/<[^>]+>/g,'').trim().length,
  body: a.body || '',
}));

const pages = (await paginate(PAGES, 'pages', {}, 50)).map(p => ({
  id: p.id, handle: p.handle, title: p.title, published: p.isPublished,
  bodyLength: (p.body || '').replace(/<[^>]+>/g,'').trim().length,
  body: p.body || '',
}));

writeJSON(path.join(DATA, 'content.json'), { blogs, articles, pages });
console.log(`\n${blogs.length} blogs, ${articles.length} articles, ${pages.length} pages`);
console.log(`  empty blogs: ${blogs.filter(b=>b.articles===0).map(b=>b.handle).join(', ') || 'none'}`);
console.log(`  articles with no summary: ${articles.filter(a=>a.summaryLength===0).length}`);
