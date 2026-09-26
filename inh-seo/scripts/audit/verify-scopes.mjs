/* Read the granted scopes FROM THE TOKEN, never from the app configuration screen.
 *   node scripts/audit/verify-scopes.mjs
 *
 * A rotation silently dropped read_files and write_files once. The app screen showed them; the token
 * did not carry them. This asks the token, names anything missing that this repo needs, and exits
 * non-zero so it can gate a round rather than being read past.
 */
import fs from 'node:fs';

const env = Object.fromEntries(fs.readFileSync('.env', 'utf8').split('\n').filter((l) => l.includes('='))
  .map((l) => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=') + 1).trim().replace(/^["']|["']$/g, '')]));
const SHOP = env.SHOPIFY_SHOP || 'inhousewellness.myshopify.com';
/* what this repo actually uses, with the caller named so a missing one points somewhere */
const NEEDED = {
  read_products: 'every accordion and product read', write_products: 'metafield and description writes',
  read_content: 'pages, articles, blogs', write_content: 'the FAQ page and article bodies',
  read_themes: 'theme pulls and diffs', write_themes: 'theme branches (hard rule 2: branches only)',
  read_publications: 'resourcePublications — channel state', write_publications: 'publish/unpublish',
  read_files: 'theme file bodies', write_files: 'theme file upserts',
  read_online_store_pages: 'page reads', write_online_store_pages: 'page writes',
};
const res = await fetch(`https://${SHOP}/admin/oauth/access_scopes.json`, { headers: { 'X-Shopify-Access-Token': env.SHOPIFY_ADMIN_TOKEN } });
if (res.status !== 200) {
  console.log(`  HTTP ${res.status} from the scopes endpoint — the token is refused, so nothing about scope can be established.`);
  console.log(`  token length ${(env.SHOPIFY_ADMIN_TOKEN || '').length}, .env last modified ${fs.statSync('.env').mtime.toISOString()}`);
  console.log('  Four tokens have now died mid-session with .env untouched. Check the app INSTALL HISTORY before rotating again.');
  process.exit(1);
}
const granted = new Set((await res.json()).access_scopes.map((s) => s.handle));
console.log(`  ${granted.size} scopes granted on ${SHOP}\n`);
const missing = Object.entries(NEEDED).filter(([s]) => !granted.has(s));
for (const [s, why] of Object.entries(NEEDED)) console.log(`  ${granted.has(s) ? 'ok     ' : 'MISSING'} ${s.padEnd(28)} ${why}`);
const extra = [...granted].filter((s) => !NEEDED[s]);
if (extra.length) console.log(`\n  also granted, unused by this repo: ${extra.join(', ')}`);
if (missing.length) { console.log(`\n  ${missing.length} REQUIRED scope(s) missing: ${missing.map(([s]) => s).join(', ')}`); process.exit(1); }
console.log('\n  every scope this repo needs is present.');
