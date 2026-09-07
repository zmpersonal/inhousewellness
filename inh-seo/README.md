# inh-seo

SEO tooling for **inhousewellness.com** (Shopify, 673 products, 90 collections).

Read `CLAUDE.md` before doing anything — it's the governing context and its hard rules aren't negotiable. Then read `TASKS.md` for the work order.

---

## Setup

**Node 22 LTS required.** Shopify CLI 4.x needs 20.10+, and 4.0.0 broke on Node 20 and 21, so use 22.

```bash
nvm install 22 && nvm use 22
npm install
cp .env.example .env      # then fill in SHOPIFY_ADMIN_TOKEN
```

Token comes from a custom app at
`https://admin.shopify.com/store/inhousewellness/settings/apps/development`

Scopes needed:
`read_products` `write_products` `read_content` `write_content` `read_themes` `write_themes` `read_online_store_pages` `write_online_store_pages` `read_publications` `write_publications` `read_orders`

`read_orders` is for the best-sellers top-20 task. Add it now so you don't have to reinstall the app later.

Never commit `.env`. If the token ever leaks, uninstall and reinstall the app in Shopify admin — that issues a new token and kills the old one. Rewriting git history is not a substitute.

---

## Commands

Every `apply` script is **dry-run by default**. Nothing writes to Shopify without `--apply`.

```bash
# Read-only audit — run this first, and after every change batch
npm run audit                  # all four dumps + broken-copy scan
npm run audit:collections
npm run audit:products
npm run audit:content
npm run audit:broken           # needs the three dumps to exist

# Does what is in the admin actually reach the page?
npm run audit:render                              # sample of 8, against live
npm run audit:render -- --limit 20
npm run audit:render -- --only far-infrared,cold-plunge
npm run audit:render -- --preview 146038259779    # against an unpublished theme

# P0 fixes
npm run fix:broken             # clears TEST placeholder + leaked AI markers
npm run fix:broken -- --apply
npm run fix:markup             # strips data-* / class / style residue
npm run fix:markup -- --apply
npm run fix:unpublish          # unpublishes DEINDEX/DELETE collections
npm run fix:unpublish -- --apply

# Copy round (after the worksheet comes back)
npm run import:plan            # data/worksheet.csv -> collections-plan.json
npm run apply:seo              # SEO titles + metas; fills empty only
npm run apply:seo -- --apply
npm run apply:copy             # descriptions from content/collections/*.md
npm run apply:copy -- --apply
```

Useful flags on any apply script:

- `--only handle-a,handle-b` — restrict to specific collections
- `--overwrite` — on `apply:seo` only, replaces existing metas instead of filling blanks

---

## Layout

```
CLAUDE.md                       Governing context. Voice, rules, decisions.
TASKS.md                        The work order, in rounds.
docs/seo-action-plan.md         Full strategy, for reference.
docs/collection-worksheet.xlsx  The sheet sent to the client.

data/collections-plan.json      90 collections with action + keyword + copy slots.
data/press-links.json           Press logo row URLs.
data/worksheet.csv              (You add this — the filled sheet, exported as CSV.)
data/collections.json           Audit output. Gitignored.
data/products.json              Audit output. Gitignored.
data/content.json               Audit output. Gitignored.
data/broken-copy.json           Scan output. Gitignored.
data/backups/{timestamp}/       Pre-write snapshots. Gitignored.
data/changelog.jsonl            Every mutation, appended. Gitignored.

content/collections/{handle}.md Drafted copy awaiting review.
reports/                        Human-readable markdown reports. Gitignored.
theme/                          Shopify CLI checkout. Gitignored. Never the live theme.
```

---

## Run `audit:render` after every theme publish

**This is not optional and it is not a formality.**

Collection descriptions were stored correctly in Shopify and rendered nowhere for roughly two
months. Two independent causes, neither of which raised an error:

1. The description block was `"disabled": true` in `templates/collection.json`.
2. An `elsif` with an **empty body** in `layout/theme.liquid` deleted the
   `<meta name="description">` tag from any collection that *had* a description — so writing
   copy actively removed the meta tag.

Both were found only by fetching a live page and looking for the text. Nothing in the admin,
the API, or the theme editor indicated a problem, and copy was written on the assumption it
would appear.

Both failures are one theme-editor click from returning. The section that renders the
description can be reordered, disabled, or deleted by anyone in the customiser, with no
warning and no visible breakage — the page just quietly loses its copy.

```bash
npm run audit:render                            # after any publish
npm run audit:render -- --preview <theme-id>    # before publishing a branch
```

It exits 1 and names the failing URLs. Run it after any theme publish, and on a schedule if
one exists. It takes about ten seconds.

**Two bugs were found in the checker itself while proving it worked, both worth knowing about
if you extend it.** A guard that can lie in either direction is worse than no guard.

- `fetch()` with `redirect: 'follow'` does not expose the intermediate 302 that sets the
  preview cookie, so the **first** page of a `--preview` run rendered with the **live** theme
  and failed spuriously. Fixed with a priming request that seeds the cookie jar. This
  produced a **false failure**.
- The body probe compared text stripped of tags against **raw markup**. Inline `<strong>` and
  `<a>` tags sit mid-sentence in stored descriptions, so a contiguous probe never matched.
  Fixed by stripping both sides and shortening the probe. This produced a **false pass** — the
  more dangerous of the two, because it would have reported a broken page as healthy.

## Check the state, not the report of the state

Publishing the Round 2 theme on 7 September 2026: the first `shopify theme publish` call
returned no useful output, and `shopify theme list` immediately afterwards still showed the
**old** theme as live. A second publish reported success. It was never determined whether the
first call silently failed or the list was serving stale data.

Rather than trust either output, theme roles were queried directly and confirmed: the new
theme live, the old one intact and unpublished as the rollback.

**Do the same for anything that matters.** A command that reports success has told you what
it believes, not what is true. This applies to `theme publish`, `theme list`, an audit dump,
and to `audit:render` itself — which is why it was proven to fail against the live theme
before being trusted to pass against the branch. A guard that has never failed has not been
tested.

There is also a merchant-facing warning inside the section's own `custom_liquid` setting, so
anyone about to delete it in the customiser reads what depends on it first.

## Safety model

1. Audit scripts never write. Apply scripts default to dry-run.
2. Every apply script snapshots to `data/backups/` before mutating.
3. Every mutation is appended to `data/changelog.jsonl` with before and after.
4. Apply scripts are idempotent — running twice changes nothing the second time.
5. Unpublish, never delete. Product membership survives and it's reversible from the admin.
6. `unpublish-collections.js` checks navigation menus and skips referenced handles.
7. Copy is drafted to `content/` as markdown and only applied when a human adds
   `status: approved` to the front matter.
