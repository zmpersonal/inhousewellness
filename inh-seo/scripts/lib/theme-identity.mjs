/* Which theme actually served this page? — Round 18i.
 *
 * Every preview verifier here checks the 302 + _shopify_essential handshake, and none of them
 * checked the OUTCOME of it: a client that drops or mangles the cookie is served MAIN at the URL it
 * asked for, with status 200, and every content check then runs against the live theme. The
 * handshake proves a cookie was OFFERED; only the page says which theme RENDERED it.
 *
 * Pattern copied from rendered-title-sweep.mjs: read Shopify.theme from the served HTML and
 * compare its id with the requested theme. MAIN is asserted by role, never by an id someone typed.
 *
 * The fixtures run at import, so every verifier importing this is guarded.
 */
export function servedTheme(html) {
  const m = String(html || '').match(/Shopify\.theme\s*=\s*(\{[^;]*\})/);
  if (!m) return null;
  try { const j = JSON.parse(m[1]); return { id: String(j.id), role: String(j.role), name: j.name }; } catch { return null; }
}

/* want: a theme id (string or number) for a preview, or 'main' for the published theme. */
export function assertServedBy(html, want, where = 'this page') {
  const t = servedTheme(html);
  const asked = want === 'main' ? 'MAIN (role main)' : String(want);
  if (!t) throw new Error(`WRONG THEME — asked for ${asked}, but ${where} carries no readable Shopify.theme, so which theme served it is unknown`);
  const ok = want === 'main' ? t.role === 'main' : t.id === String(want);
  if (!ok) throw new Error(`WRONG THEME — asked for ${asked}, ${where} was served by ${t.id} (role ${t.role})`);
  return t;
}

// 18i: constructed fixtures — the identity check must accept the right theme and refuse every other
const page = (id, role) => `<script>Shopify.theme = {"name":"X","id":${id},"schema_name":"G","role":"${role}"};</script>`;
const throws = (fn) => { try { fn(); return false; } catch (e) { return /^WRONG THEME/.test(e.message); } };
export const THEME_IDENTITY_FIXTURES = [
  ['preview served by the requested theme passes', !throws(() => assertServedBy(page(111, 'unpublished'), '111'))],
  ['numeric id argument passes',                   !throws(() => assertServedBy(page(111, 'unpublished'), 111))],
  ['cookie dropped: MAIN served instead is refused', throws(() => assertServedBy(page(999, 'main'), '111'))],
  ['no Shopify.theme on the page is refused',      throws(() => assertServedBy('<html>Just a moment...</html>', '111'))],
  ['MAIN asserted by role passes on role main',    !throws(() => assertServedBy(page(999, 'main'), 'main'))],
  ['MAIN asserted by role refuses a preview',      throws(() => assertServedBy(page(111, 'unpublished'), 'main'))],
];
const failed = THEME_IDENTITY_FIXTURES.filter(([, ok]) => !ok).map(([l]) => l);
if (failed.length) throw new Error(`theme-identity fixtures FAILED: ${failed.join('; ')}`);
