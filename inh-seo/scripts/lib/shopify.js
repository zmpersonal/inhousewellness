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

export const shopDomain = SHOP;
export const apiVersion = VERSION;
