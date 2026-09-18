/**
 * assertReach — the guard for the class every other gate is blind to.
 *
 * `assertWellFormed` checks the string you send. `showDiff` prints the field you
 * named. `assertFresh` checks the dump's age. The dry run reviews the invocation
 * you typed. NONE of them measures what ELSE moved, and reach caused three
 * separate regressions on 9 September 2026 in three different scripts.
 *
 * WHY IT RUNS AFTER THE WRITE. A pre-flight prediction of reach would be a
 * second implementation of the API's semantics, and that prediction would have
 * been wrong about `seo` in exactly the way apply-seo-fields.js was wrong:
 * Shopify treats `seo` as a whole object and nulls what you omit. A guard that
 * models the system it guards inherits the system's surprises. So: perform the
 * write, then look.
 *
 * WHICH IS ONLY ACCEPTABLE BECAUSE THE CAPTURE IS THE BACKUP. `captureReach`
 * holds the complete before-state of every record the batch could touch, so a
 * COLLATERAL verdict is recoverable by the caller from data already in memory.
 *
 * Usage:
 *   const before = await captureReach(fetchAll);
 *   … writes …
 *   const after  = await captureReach(fetchAll);
 *   assertReach(before, after, { handles: ['cold-plunge'], fields: ['descriptionHtml'] });
 */

/** Flatten a record to `field` / `nested.field` so a nested object is compared
 *  leaf by leaf. `seo` is the reason this exists: comparing it as one value
 *  reports "seo changed", which is what the author already believed. */
export function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj || {})) {
    if (k === 'id' || k === 'handle') continue;
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
    else out[key] = Array.isArray(v) ? JSON.stringify(v) : (v ?? null);
  }
  return out;
}

/** `fetchAll` returns [{ handle, ...fields }]. Keyed by handle. */
export async function captureReach(fetchAll) {
  const rows = await fetchAll();
  const map = new Map();
  for (const r of rows) map.set(r.handle, flatten(r));
  return map;
}

/** 18i: null and '' are DIFFERENT values. The old `String(x ?? '')` made a field that was
 *  emptied to '' (or nulled from '') invisible — Shopify nulling a meta is exactly the change
 *  this guard exists to see. A missing key and null stay equal: flatten() writes absent as null. */
export const sameValue = (x, y) => {
  const b = x ?? null, a = y ?? null;
  if (b === null || a === null) return b === a;
  return String(b) === String(a);
};

/**
 * Classify every delta against the declaration.
 *   DECLARED   changed, and both handle and field were named
 *   COLLATERAL changed, and one of them was not  -> the finding
 *   VANISHED   present before, absent after (or the reverse)
 */
export function classifyReach(before, after, declared) {
  const handles = new Set(declared.handles || []);
  const fields = new Set(declared.fields || []);
  const anyHandle = handles.has('*');
  const anyField = fields.has('*');
  const out = { declared: [], collateral: [], vanished: [], untouched: 0 };

  const allHandles = new Set([...before.keys(), ...after.keys()]);
  for (const h of allHandles) {
    const b = before.get(h), a = after.get(h);
    if (!b || !a) { out.vanished.push({ handle: h, was: b ? 'present' : 'absent', now: a ? 'present' : 'absent' }); continue; }
    const keys = new Set([...Object.keys(b), ...Object.keys(a)]);
    for (const k of keys) {
      if (sameValue(b[k], a[k])) { out.untouched += 1; continue; }
      const row = { handle: h, field: k, before: b[k], after: a[k] };
      const okHandle = anyHandle || handles.has(h);
      const okField = anyField || fields.has(k);
      (okHandle && okField ? out.declared : out.collateral).push(row);
    }
  }
  return out;
}

const trunc = (v, n = 72) => { const s = v === null || v === undefined ? '(null)' : String(v); return s.length > n ? s.slice(0, n) + '…' : s; };

/** Reports and THROWS on collateral. Never warns — a warning inside a 56-row
 *  apply is the line nobody read, which is how three cluster links disappeared. */
export function assertReach(before, after, declared, opts = {}) {
  const r = classifyReach(before, after, declared);
  const allowed = new Set(opts.allow || []);
  const blocking = r.collateral.filter((c) => !allowed.has(c.field) && !allowed.has(`${c.handle}.${c.field}`));

  console.log(`\n  reach: ${r.declared.length} declared change(s), ${r.collateral.length} collateral, ${r.vanished.length} vanished, ${r.untouched} fields untouched`);
  console.log(`  declared scope: handles=[${(declared.handles || []).join(', ')}] fields=[${(declared.fields || []).join(', ')}]`);

  for (const c of r.vanished) console.error(`  !! VANISHED  ${c.handle}: ${c.was} -> ${c.now}`);
  for (const c of blocking) {
    console.error(`  !! COLLATERAL  ${c.handle}  [${c.field}]`);
    console.error(`       before: ${trunc(c.before)}`);
    console.error(`       after : ${trunc(c.after)}`);
  }
  if (r.collateral.length && !blocking.length) console.log(`  (${r.collateral.length} collateral change(s) explicitly allowed via --reach-ok)`);

  if (blocking.length || r.vanished.length) {
    const e = new Error(`assertReach: ${blocking.length} collateral and ${r.vanished.length} vanished change(s) outside the declared scope. The caller holds the before-state — roll back.`);
    e.reach = r; e.blocking = blocking;
    throw e;
  }
  return r;
}

/* ── Ready-made captures, so each apply script does not re-implement the query
      and get the field list subtly wrong. The field list IS the guard: a field
      omitted here is a field the guard cannot see change. ────────────────── */

export const ARTICLE_REACH_QUERY = `query($after:String){ articles(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle title body summary isPublished publishedAt author{ name } blog{ handle } } } }`;

export const COLLECTION_REACH_QUERY = `query($after:String){ collections(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle title descriptionHtml sortOrder templateSuffix seo{ title description } } } }`;

export const PRODUCT_REACH_QUERY = `query($after:String){ products(first:250, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle title status vendor descriptionHtml seo{ title description } } } }`;

/** Paginates any of the above. `root` is 'articles' | 'collections' | 'products'. */
export function makeFetch(gql, query, root) {
  return async () => {
    const out = []; let after = null, more = true;
    while (more) {
      const r = await gql(query, { after });
      out.push(...r[root].nodes);
      more = r[root].pageInfo.hasNextPage; after = r[root].pageInfo.endCursor;
    }
    return out;
  };
}

/** Reads `--reach-ok a,b` from argv. */
export function reachAllowFromArgv(argv = process.argv) {
  const i = argv.indexOf('--reach-ok');
  return i > -1 && argv[i + 1] ? argv[i + 1].split(',') : [];
}

/** The whole pattern in one call, so a script cannot half-adopt it. */
export async function guardReach(fetchAll, declared, fn, opts = {}) {
  const before = await captureReach(fetchAll);
  const result = await fn();
  const after = await captureReach(fetchAll);
  try {
    assertReach(before, after, declared, { allow: opts.allow || reachAllowFromArgv() });
  } catch (e) {
    console.error(`\n${e.message}`);
    console.error('The reach capture holds the full before-state. Roll back from it.');
    throw e;
  }
  return result;
}

/* Membership is not a FIELD on a collection — it is an edge. So the reach
   question for fix-membership.js is "did any product's collection list change
   other than the ones declared?", which needs the edge captured from the
   product side. Capturing collection fields would have measured the wrong
   thing and passed while membership moved underneath it. */
export const MEMBERSHIP_REACH_QUERY = `query($after:String){ products(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle status collections(first:60){ nodes{ handle } } } } }`;

/** Flattens each product to one comparable field: its sorted collection list. */
export async function captureMembership(gql) {
  const out = []; let after = null, more = true;
  while (more) {
    const r = await gql(MEMBERSHIP_REACH_QUERY, { after });
    out.push(...r.products.nodes);
    more = r.products.pageInfo.hasNextPage; after = r.products.pageInfo.endCursor;
  }
  const map = new Map();
  for (const p of out) map.set(p.handle, { status: p.status, collections: p.collections.nodes.map((c) => c.handle).sort().join(',') });
  return map;
}

/* ── RELATIONSHIP-SHAPED WRITES ──────────────────────────────────────────────
   A guard wired into a script that mutates an EDGE rather than a FIELD passes
   while the thing it was meant to watch moves underneath it — and a clean report
   on a change the guard structurally cannot see is worse than no guard, because
   the clean report is what gets trusted.

   Three shapes on this store are not fields:

     MEMBERSHIP    product <-> collection      captureMembership (above)
     METAFIELDS    a separate resource hung off the record. Article SEO lives
                   here — `global.title_tag` / `global.description_tag` —
                   because Article has no `seo` field in API 2026-07.
     PUBLICATIONS  record <-> sales channel. Deindexing is a publication change
                   and nothing about the collection object moves.

   Audited 9 September 2026 across all 17 apply scripts. The wired six were
   clean except publish-article.js, which calls metafieldsSet and was captured
   with an article query that has no metafields in it. Caught by asking the
   question rather than by an incident — the first guard defect on this project
   found BEFORE it cost anything. ───────────────────────────────────────────── */

export const ARTICLE_METAFIELD_REACH_QUERY = `query($after:String){ articles(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle
    titleTag: metafield(namespace:"global", key:"title_tag"){ value }
    descTag:  metafield(namespace:"global", key:"description_tag"){ value } } } }`;

export async function captureArticleMetafields(gql) {
  const out = []; let after = null, more = true;
  while (more) {
    const r = await gql(ARTICLE_METAFIELD_REACH_QUERY, { after });
    out.push(...r.articles.nodes);
    more = r.articles.pageInfo.hasNextPage; after = r.articles.pageInfo.endCursor;
  }
  const map = new Map();
  for (const a of out) map.set(a.handle, { 'global.title_tag': a.titleTag?.value ?? null, 'global.description_tag': a.descTag?.value ?? null });
  return map;
}

export const COLLECTION_PUBLICATION_REACH_QUERY = `query($after:String){ collections(first:100, after:$after){
  pageInfo{ hasNextPage endCursor }
  nodes{ id handle resourcePublications(first:20){ nodes{ publication{ name } isPublished } } } } }`;

export async function capturePublications(gql) {
  const out = []; let after = null, more = true;
  while (more) {
    const r = await gql(COLLECTION_PUBLICATION_REACH_QUERY, { after });
    out.push(...r.collections.nodes);
    more = r.collections.pageInfo.hasNextPage; after = r.collections.pageInfo.endCursor;
  }
  const map = new Map();
  for (const c of out) map.set(c.handle, { publications: c.resourcePublications.nodes.filter((p) => p.isPublished).map((p) => p.publication.name).sort().join(',') });
  return map;
}

/** Merge two captures keyed by the same handle, so one assertReach call covers
 *  a script that writes BOTH a field and a relationship. */
export function mergeCaptures(a, b) {
  const out = new Map();
  for (const k of new Set([...a.keys(), ...b.keys()])) out.set(k, { ...(a.get(k) || {}), ...(b.get(k) || {}) });
  return out;
}
