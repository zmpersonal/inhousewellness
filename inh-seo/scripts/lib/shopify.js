import 'dotenv/config';

const SHOP = process.env.SHOPIFY_SHOP;
const TOKEN = process.env.SHOPIFY_ADMIN_TOKEN;
const VERSION = process.env.SHOPIFY_API_VERSION || '2026-07';

if (!SHOP || !TOKEN) {
  console.error('Missing SHOPIFY_SHOP or SHOPIFY_ADMIN_TOKEN. Copy .env.example to .env and fill it in.');
  process.exit(1);
}

const ENDPOINT = `https://${SHOP}/admin/api/${VERSION}/graphql.json`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Execute a GraphQL query against the Admin API.
 * Handles the cost-based leaky bucket: if available points run low, waits for
 * the bucket to refill before returning. Retries on 429 and THROTTLED.
 */
export async function gql(query, variables = {}, attempt = 1) {
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': TOKEN,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (res.status === 429) {
    const wait = Number(res.headers.get('Retry-After') || 2) * 1000;
    if (attempt > 6) throw new Error('Rate limited after 6 attempts');
    console.warn(`  429 — waiting ${wait}ms (attempt ${attempt})`);
    await sleep(wait);
    return gql(query, variables, attempt + 1);
  }

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }

  const body = await res.json();

  if (body.errors) {
    const throttled = body.errors.some((e) => e.extensions?.code === 'THROTTLED');
    if (throttled) {
      if (attempt > 6) throw new Error('THROTTLED after 6 attempts');
      const backoff = 1000 * 2 ** attempt;
      console.warn(`  THROTTLED — backing off ${backoff}ms (attempt ${attempt})`);
      await sleep(backoff);
      return gql(query, variables, attempt + 1);
    }
    throw new Error('GraphQL errors: ' + JSON.stringify(body.errors, null, 2));
  }

  // Proactive throttle: if the bucket is nearly empty, pause until it refills.
  const t = body.extensions?.cost?.throttleStatus;
  if (t && t.currentlyAvailable < 200) {
    const need = (400 - t.currentlyAvailable) / t.restoreRate;
    await sleep(Math.ceil(need * 1000));
  }

  return body.data;
}

/**
 * Paginate a connection. `path` is a dotted path to the connection in the
 * response, e.g. 'collections' or 'collection.products'.
 */
export async function paginate(query, path, variables = {}, pageSize = 100) {
  const out = [];
  let cursor = null;
  let page = 0;

  for (;;) {
    const data = await gql(query, { ...variables, first: pageSize, after: cursor });
    const conn = path.split('.').reduce((o, k) => o?.[k], data);
    if (!conn) throw new Error(`No connection at path "${path}"`);
    out.push(...conn.nodes);
    page += 1;
    process.stdout.write(`\r  fetched ${out.length}…`);
    if (!conn.pageInfo.hasNextPage) break;
    cursor = conn.pageInfo.endCursor;
    if (page > 200) throw new Error('Pagination guard tripped at 200 pages');
  }
  process.stdout.write('\n');
  return out;
}

/** Resolve the Online Store publication id (needed to publish/unpublish). */
export async function onlineStorePublicationId() {
  const data = await gql(`{ publications(first: 25) { nodes { id name } } }`);
  const pub = data.publications.nodes.find((p) => p.name === 'Online Store');
  if (!pub) throw new Error('Online Store publication not found. Check read_publications scope.');
  return pub.id;
}

/**
 * Count the products in a collection by ENUMERATING the connection.
 *
 * Do NOT use `Collection.productsCount` — it is cached behind the write that
 * changed it. On 2026-09-07 it returned 26 for `low-emf` in the same session,
 * milliseconds after two products were removed from it; enumerating returned
 * the correct 24. The stale value is the PRE-write count, returned with no
 * error and no staleness marker, so it reads as authoritative.
 *
 * Round-1 instance 12: an API field can be cached behind the write that
 * changed it. "A command that reports success has told you what it believes,
 * not what is true" applies to reads that follow your own writes.
 */
export async function countProducts(handle) {
  let cursor = null;
  let n = 0;
  let pages = 0;
  for (;;) {
    const d = await gql(
      `query($h: String!, $c: String) {
        collectionByHandle(handle: $h) {
          products(first: 250, after: $c) {
            pageInfo { hasNextPage endCursor }
            nodes { id }
          }
        }
      }`,
      { h: handle, c: cursor },
    );
    const col = d.collectionByHandle;
    if (!col) throw new Error(`countProducts: collection "${handle}" not found`);
    n += col.products.nodes.length;
    if (!col.products.pageInfo.hasNextPage) return n;
    cursor = col.products.pageInfo.endCursor;
    if (++pages > 200) throw new Error('countProducts: pagination guard tripped');
  }
}

/**
 * Every channel a collection is published to — not just Online Store.
 *
 * Unpublishing from Online Store leaves other channels untouched, and nobody
 * looked at those the first time: `cold-plunge-favorites` stayed live in the
 * Shop app and `non-bb` stayed live on Point of Sale after both were recorded
 * as "unpublished". Callers must show the full list before removing any one
 * channel.
 */
export async function publicationsOf(handle) {
  const d = await gql(
    `query($h: String!) {
      collectionByHandle(handle: $h) {
        resourcePublications(first: 25) {
          nodes { isPublished publication { name } }
        }
      }
    }`,
    { h: handle },
  );
  const col = d.collectionByHandle;
  if (!col) throw new Error(`publicationsOf: collection "${handle}" not found`);
  return col.resourcePublications.nodes
    .filter((n) => n.isPublished)
    .map((n) => n.publication.name);
}

export const shopDomain = SHOP;
export const apiVersion = VERSION;
