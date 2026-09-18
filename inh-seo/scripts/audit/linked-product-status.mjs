/* Round 18i — STANDING CHECK, LAYER 1: every product an article links to must still be live.
 *
 *   node scripts/audit/linked-product-status.mjs              self-test, then the live check
 *   node scripts/audit/linked-product-status.mjs --self-test  fixtures only (no network, no credential)
 *   node scripts/audit/linked-product-status.mjs --acks <file> use a different acknowledgement file
 *
 * READ-ONLY. It writes nothing to Shopify and nothing to disk. Runs nightly in Actions
 * (.github/workflows/linked-product-status.yml) and installs nothing: Node built-ins only, asserted below.
 *
 * WHY: a product pulled to draft 404s at once, and nothing noticed. Osla sat at 404 behind 14 links and
 * Catalonia behind 9 until an audit went looking, because every existing check reads markup or hrefs, not the
 * status of the thing an href points at. This watches the OUTCOME, so it also catches a product archived,
 * unpublished from the Online Store, deleted, or re-handled.
 *
 * A product FAILS if any of these holds:
 *   MISSING        no product has that handle any more
 *   NOT ACTIVE     status DRAFT or ARCHIVED — a draft reads back with NO channels, so status is tested first
 *   OFF STOREFRONT ACTIVE but not published to the Online Store (onlineStoreUrl is null)
 *   HTTP <n>       the storefront URL does not answer 200 (redirect NOT followed — a 301 is not the product)
 *   UNREACHABLE    429 or a network error that outlasted the retries. An unchecked page is not a passed page.
 * Sold out is NOT a failure: a sold-out page answers 200 and is the approved treatment for a stock-out.
 *
 * ACKNOWLEDGEMENTS (config/linked-product-acks.json) let a known, decided-on failure print as ACKNOWLEDGED until
 * its expiry. An expired ack fails. An ack whose product now PASSES, or that matches no linked product, also fails
 * — a hold that protects nothing is indistinguishable from one that missed, so it must be removed, not kept.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('../..', import.meta.url));
const ORIGINS = ['inhousewellness.com', 'www.inhousewellness.com', 'inhousewellness.myshopify.com'];

/* ── pure functions, proved by the fixtures below ─────────────────────────────────────────────────────── */

// A path WITH its origin (CLAUDE.md: a slug is a substring; poison.org publishes are-saunas-good-for-you too).
export function linkedHandles(body) {
  const out = [];
  for (const m of String(body).matchAll(/<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["']/gi)) {
    let u;
    try { u = new URL(m[1], 'https://inhousewellness.com'); } catch { continue; }
    if (!ORIGINS.includes(u.hostname.toLowerCase())) continue;
    const p = /^\/(?:collections\/[^/]+\/)?products\/([^/?#]+)\/?$/i.exec(u.pathname);
    if (p) out.push(decodeURIComponent(p[1]).toLowerCase());
  }
  return out;
}

export function verdictOf({ product, http }) {
  if (!product) return 'MISSING';
  if (product.status !== 'ACTIVE') return `NOT ACTIVE (${product.status})`;
  if (!product.onlineStoreUrl) return 'OFF STOREFRONT';
  if (http === 'UNREACHABLE') return 'UNREACHABLE';
  if (http !== 200) return `HTTP ${http}`;
  return 'PASS';
}

// Returns { fail: [...], acked: [...], ackProblems: [...] } — every ack must be live, unexpired and still needed.
export function applyAcks(results, acks, today) {
  const fail = [], acked = [], ackProblems = [];
  const byHandle = new Map(results.map((r) => [r.handle, r]));
  for (const a of acks) {
    const r = byHandle.get(a.handle);
    if (!r) ackProblems.push(`ack "${a.handle}" matches no linked product — remove it`);
    else if (r.verdict === 'PASS') ackProblems.push(`ack "${a.handle}" is no longer needed (it passes) — remove it`);
    else if (!a.expires || a.expires < today) ackProblems.push(`ack "${a.handle}" ${a.expires ? 'expired ' + a.expires : 'has no expiry'} — decide or renew`);
  }
  for (const r of results) {
    if (r.verdict === 'PASS') continue;
    const a = acks.find((x) => x.handle === r.handle && x.expires && x.expires >= today);
    (a ? acked : fail).push(a ? { ...r, ack: a } : r);
  }
  return { fail, acked, ackProblems };
}

/* ── the check's own proof: constructed, never live content ──────────────────────────────────────────── */
function selfTest() {
  let bad = 0;
  const eq = (name, got, want) => { const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { console.log(`FIXTURE FAIL: ${name} — want ${JSON.stringify(want)} got ${JSON.stringify(got)}`); bad++; } };
  eq('absolute product link', linkedHandles('<a href="https://inhousewellness.com/products/osla">x</a>'), ['osla']);
  eq('relative product link', linkedHandles('<a href="/products/osla?variant=1#r">x</a>'), ['osla']);
  eq('collection-scoped link', linkedHandles('<a class="c" href="/collections/saunas/products/osla">x</a>'), ['osla']);
  eq('www and myshopify origins', linkedHandles('<a href="https://www.inhousewellness.com/products/a"></a><a href="https://inhousewellness.myshopify.com/products/b"></a>'), ['a', 'b']);
  eq('another origin with the same path is NOT ours', linkedHandles('<a href="https://www.poison.org/products/osla">x</a><a href="https://competitor.com/products/osla">y</a>'), []);
  eq('a collection is not a product', linkedHandles('<a href="/collections/osla">x</a>'), []);
  eq('single-quoted href', linkedHandles("<a href='/products/osla'>x</a>"), ['osla']);
  eq('every occurrence counts', linkedHandles('<a href="/products/a">1</a><a href="/products/a">2</a>'), ['a', 'a']);
  const P = (s, url = 'https://inhousewellness.com/products/x') => ({ status: s, onlineStoreUrl: url });
  eq('deleted or re-handled', verdictOf({ product: null, http: 404 }), 'MISSING');
  eq('draft (reads back with no channels)', verdictOf({ product: P('DRAFT', null), http: 404 }), 'NOT ACTIVE (DRAFT)');
  eq('archived', verdictOf({ product: P('ARCHIVED', null), http: 404 }), 'NOT ACTIVE (ARCHIVED)');
  eq('active but off the Online Store', verdictOf({ product: P('ACTIVE', null), http: 404 }), 'OFF STOREFRONT');
  eq('active, on storefront, but 404 anyway', verdictOf({ product: P('ACTIVE'), http: 404 }), 'HTTP 404');
  eq('a redirect is not the product', verdictOf({ product: P('ACTIVE'), http: 301 }), 'HTTP 301');
  eq('rate-limited past the retries is not a pass', verdictOf({ product: P('ACTIVE'), http: 'UNREACHABLE' }), 'UNREACHABLE');
  eq('live, sold out or not, answers 200', verdictOf({ product: P('ACTIVE'), http: 200 }), 'PASS');
  const R = [{ handle: 'a', verdict: 'NOT ACTIVE (DRAFT)' }, { handle: 'b', verdict: 'PASS' }];
  eq('unacknowledged failure fails', applyAcks(R, [], '2026-09-18').fail.map((r) => r.handle), ['a']);
  eq('acknowledged failure, in date, is acked', applyAcks(R, [{ handle: 'a', expires: '2026-10-01' }], '2026-09-18').acked.map((r) => r.handle), ['a']);
  eq('expired ack fails the product AND the ack', (() => { const x = applyAcks(R, [{ handle: 'a', expires: '2026-09-01' }], '2026-09-18'); return [x.fail.length, x.ackProblems.length]; })(), [1, 1]);
  eq('ack on a passing product is a problem', applyAcks(R, [{ handle: 'b', expires: '2026-10-01' }], '2026-09-18').ackProblems.length, 1);
  eq('ack matching nothing is a problem', applyAcks(R, [{ handle: 'zz', expires: '2026-10-01' }], '2026-09-18').ackProblems.length, 1);
  eq('ack with no expiry is a problem', applyAcks(R, [{ handle: 'a' }], '2026-09-18').ackProblems.length, 1);
  // The job installs nothing, so this file may import Node built-ins only. Asserted, not assumed.
  const imports = [...fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').matchAll(/^import .* from '([^']+)';$/gm)].map((m) => m[1]);
  eq('imports are node: built-ins only', imports.filter((i) => !i.startsWith('node:')), []);
  return bad;
}

const bad = selfTest();
if (bad) { console.log(`\nself-test: ${bad} fixture(s) failed — the check is not trustworthy, refusing to run`); process.exit(2); }
console.log('self-test: every fixture holds');
if (process.argv.includes('--self-test')) process.exit(0);

/* ── live check ───────────────────────────────────────────────────────────────────────────────────────── */
// Credentials: the environment (Actions secret), else a local .env. Only the token is a secret.
if (!process.env.SHOPIFY_ADMIN_TOKEN && fs.existsSync(path.join(ROOT, '.env'))) {
  for (const l of fs.readFileSync(path.join(ROOT, '.env'), 'utf8').split('\n')) {
    const m = /^\s*([A-Z_]+)\s*=\s*"?([^"\n]*)"?\s*$/.exec(l); if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
  }
}
const SHOP = process.env.SHOPIFY_SHOP, TOKEN = process.env.SHOPIFY_ADMIN_TOKEN, VERSION = process.env.SHOPIFY_API_VERSION || '2026-07';
/* --replay <file>: the Admin reads come from a SNAPSHOT { articles:[…], products:{ handle:{status,onlineStoreUrl} } }
   instead of the API; the storefront check is still live. For proving the pipeline when the Admin API is
   unavailable — every replay run says so on its first line, and it is never what the nightly job runs. */
const REPLAY = process.argv.includes('--replay') ? JSON.parse(fs.readFileSync(process.argv[process.argv.indexOf('--replay') + 1], 'utf8')) : null;
if (REPLAY) console.log(`REPLAY — Admin data from a snapshot taken ${REPLAY.takenAt || '(undated)'}, NOT a live read. Storefront responses are live.`);
if (!REPLAY && (!SHOP || !TOKEN)) { console.log('REFUSING: no SHOPIFY_SHOP / SHOPIFY_ADMIN_TOKEN — a check that cannot run is not a pass'); process.exit(1); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function gql(query, variables = {}) {
  for (let attempt = 1; attempt <= 6; attempt++) {
    const res = await fetch(`https://${SHOP}/admin/api/${VERSION}/graphql.json`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Shopify-Access-Token': TOKEN }, body: JSON.stringify({ query, variables }) });
    if (res.status === 429 || res.status >= 500) { await sleep(2000 * attempt); continue; }
    const j = await res.json();
    if (Array.isArray(j.errors) && j.errors.some((e) => e.extensions?.code === 'THROTTLED')) { await sleep(2000 * attempt); continue; }
    if (!res.ok || j.errors) throw new Error(`Admin API ${res.status}: ${JSON.stringify(j.errors || j).slice(0, 300)}`);
    return j.data;
  }
  throw new Error('Admin API: throttled past 6 attempts');
}
async function httpStatus(handle) {
  for (let attempt = 1; attempt <= 6; attempt++) {
    try {
      const r = await fetch(`https://inhousewellness.com/products/${encodeURIComponent(handle)}`, { method: 'GET', redirect: 'manual', headers: { 'User-Agent': 'inh-seo linked-product-status (read-only)' } });
      if (r.status === 429) { await sleep(8000); continue; }                       // backoff, never a dead link
      return r.status;
    } catch { await sleep(3000); }
  }
  return 'UNREACHABLE';
}

const arts = REPLAY ? REPLAY.articles : []; let cur = null;
if (!REPLAY) do {
  const d = await gql(`query($c:String){ articles(first:100, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ handle isPublished body blog{ handle } } } }`, { c: cur });
  arts.push(...d.articles.nodes); cur = d.articles.pageInfo.hasNextPage ? d.articles.pageInfo.endCursor : null;
} while (cur);
const pub = arts.filter((a) => a.isPublished);
const linked = new Map();
for (const a of pub) for (const h of linkedHandles(a.body)) {
  if (!linked.has(h)) linked.set(h, { links: 0, articles: new Set() });
  const x = linked.get(h); x.links++; x.articles.add(`/blogs/${a.blog.handle}/${a.handle}`);
}
console.log(`\n${pub.length} published articles (of ${arts.length}) link to ${linked.size} distinct products, ${[...linked.values()].reduce((s, x) => s + x.links, 0)} links`);
if (!linked.size) { console.log('REFUSING: zero linked products — that is a broken extractor or a broken read, not a clean estate'); process.exit(1); }

const results = [];
let soldOut = 0;
for (const [handle, x] of linked) {
  const d = REPLAY ? { productByHandle: REPLAY.products[handle] ? { variants: { nodes: [] }, ...REPLAY.products[handle] } : null } : await gql(`query($h:String!){ productByHandle(handle:$h){ status onlineStoreUrl totalInventory tracksInventory variants(first:50){ nodes{ availableForSale } } } }`, { h: handle });
  const product = d.productByHandle;
  const http = await httpStatus(handle);                                          // always: the storefront is the outcome
  const verdict = verdictOf({ product, http });
  if (verdict === 'PASS' && product.variants.nodes.length && product.variants.nodes.every((v) => !v.availableForSale)) soldOut++;
  results.push({ handle, verdict, http, links: x.links, articles: [...x.articles] });
}

const ackFile = process.argv.includes('--acks') ? process.argv[process.argv.indexOf('--acks') + 1] : path.join(ROOT, 'config', 'linked-product-acks.json');
const acks = fs.existsSync(ackFile) ? JSON.parse(fs.readFileSync(ackFile, 'utf8')).acks || [] : [];
const today = new Date().toISOString().slice(0, 10);
const { fail, acked, ackProblems } = applyAcks(results, acks, today);

console.log(`PASS ${results.length - fail.length - acked.length}   (of which sold out, which is allowed: ${REPLAY ? 'n/a in a replay — no variant data' : soldOut})`);
for (const r of acked) console.log(`ACKNOWLEDGED until ${r.ack.expires}  ${r.handle} — ${r.verdict} — ${r.links} link(s) — ${r.ack.reason || ''}`);
for (const r of fail) {
  console.log(`\nFAIL  ${r.handle} — ${r.verdict} — ${r.links} link(s) in ${r.articles.length} article(s):`);
  r.articles.forEach((a) => console.log(`        ${a}`));
}
for (const p of ackProblems) console.log(`\nACK PROBLEM  ${p}`);
const failed = fail.length + ackProblems.length;
// The summary is derived from the same three lists printed above it, never written separately (18i: the first version
// said "every linked product is live" while printing an ACKNOWLEDGED product that was not).
console.log(failed ? `\n${fail.length} linked product(s) not live, ${ackProblems.length} acknowledgement problem(s) — a reader following these links reaches a dead page`
  : acked.length ? `\nno UNACKNOWLEDGED failures — but ${acked.length} linked product(s) are NOT live and are acknowledged (listed above)` : '\nevery linked product is live');
process.exit(failed ? 1 : 0);
