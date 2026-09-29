# INH Verified go-live: canary report (stopped for review)

2026-09-28 to 29 UTC. Branch `verified/go-live`, cut from `main` at `8f28eb1`.

**API spend: $0.** The Shopify Admin API and storefront requests are unbilled, and no Blotato
credits were used.

**Live now:**
- the hub and the methodology page;
- 3 model pages;
- a product-page link on Golden Designs Copenhagen.

128 entries stay DRAFT.

## Round 3 close-out (approved)

- **Titles and handles:** all 64 rows are marked `y`, and titles and handles are frozen (131 of
  each). Commit `8f28eb1`. The 64 built pages are identical to the approved preliminary pages.
- **Amperage wording:** kept as built.
- **Curve Dome:** left as is. The report's reasoning is corrected: under D-1 a dome meets the
  dimension requirement with a diameter and height; this one misses because its capacity is not
  stated.
- **`inh-seo/scripts/apply/r23j-plain-text.mjs`:** untouched and uncommitted throughout.

## Preconditions

| # | Check | Result |
|---|---|---|
| 1 | Admin token scopes (read-only) | **PASS.** 10 scopes held, including `write_metaobject_definitions`, `write_metaobjects` and `write_products` |
| 2 | Workflow triggers; merge | **PASS.** No workflow triggers on push, on `main` or the branch (only `schedule` and `workflow_dispatch`). `main` pulled without rebase, fast-forwarded to `verified/r3-parity`, pushed: `origin/main` = `8f28eb1`. The first push failed with HTTP 400 (pack size) and succeeded with a larger `http.postBuffer` |
| 3 | MAIN resolved at run time; patch anchors | **PASS.** MAIN = `167150092355` "Round 23b — product-to-collection links removed", role MAIN. The layout anchor occurs once, and there is exactly one enabled reviews section. None of the 10 new files existed on MAIN. The patch was applied to MAIN's own files (which differ from the preview's, carrying Round 23), never copied |
| — | URL path | Your brief said `/pages/sauna/<handle>`. On asking, you kept D-I's `/pages/sauna-database/<handle>`. Shopify accepted a definition URL handle equal to the hub page's handle |

## Step 1: invisible setup

- **Definition:** `gid://shopify/MetaobjectDefinition/24951128131`. It is read back with web
  pages enabled (`urlHandle: sauna-database`), draft/active publishing, `PUBLIC_READ` storefront
  access, and exactly the planned 13 fields.
  - The first attempt was refused, with nothing written: Shopify allows `access.admin` only on
    app-reserved types. Admin access is now omitted.
- **Entries:** 131 created DRAFT.
  - Each was read back and checked against `saunas.json` independently of the payload builder:
    the record equals the dataset record minus internal keys, `page_data` equals the built page,
    every scalar field matches, and no price or banned phrase appears.
- **Metafields:** 40 mapped products (`inh_verified.sauna`).
  - The reversal was proved on the first product: written, reversed, confirmed absent,
    rewritten.
  - All 40 were read back.
  - Reversal file: `data/verified/internal/metafield-writes/metafield-writes-20260928T235827Z.jsonl`.
- **Preview proof** (`preview-proof.json`), on the real preview storefront for
  `golden-designs-copenhagen`:
  - the metafield is set to the entry, and the entry is DRAFT;
  - the link section's wrapper is on the page, and the link rendered: **false**.

## Step 2: live theme deploy

- **Snapshot:** MAIN's `layout/theme.liquid` (md5 `6db1848c…`) and `templates/product.json`
  (md5 `0009bdb9…`), committed in `data/verified/golive/main-167150092355-snapshot/`. The
  manifest also records that the 10 new files were absent.
- **Gate before writing:** MAIN was re-read at the last moment and still matched the snapshot by
  MD5. The banner naming `167150092355` was printed before any upsert.
- **Read-back:** all 12 files are byte-identical by MD5: 10 new files and 2 patched.
- **The MAIN patch diff** (`main-patch.diff`) is +12 lines, −0. The raw byte diff agrees: layout
  +7/−0, product template +5/−0. No line of MAIN's own content changed:

```diff
--- MAIN 167150092355 snapshot/layout/theme.liquid
+++ MAIN 167150092355 live/layout/theme.liquid
@@ -112,4 +112,11 @@
         {{ page_title }}
         {%- if paginate.current_page > 1 %} – Page {{ paginate.current_page }}{% endif %}
+      {%- elsif metaobject -%}
+        {%- comment -%}
+          INH Verified model pages (Round 2): the title tag is exactly the SEO title,
+          "[Title]: Verified Specs & Electrical Requirements", with no shop-name suffix.
+          Scoped to metaobject pages only; every other branch is unchanged.
+        {%- endcomment -%}
+        {{ page_title }}
       {%- else -%}
--- MAIN 167150092355 snapshot/templates/product.json
+++ MAIN 167150092355 live/templates/product.json
@@ -910,4 +910,8 @@
       "settings": {}
+    },
+    "inh_verified_link": {
+      "type": "inh-verified-product-link",
+      "settings": {}
     }
@@ -923,4 +927,5 @@
     "17374944778045764f",
+    "inh_verified_link",
     "17327782801d3d3cc5",
```

- **Nothing visible after the deploy** (`invisible-after-deploy.json`):
  - all 5 new URLs answered 404;
  - 131 entries DRAFT, 0 ACTIVE; both pages hidden;
  - on Copenhagen and Toledo, the link section wrapper is present with no link rendered;
  - the 7 sections above it are identical to the pre-deploy baseline, in order and in visible
    text.

### Rollback: written, dry-run clean, one half proved on the preview

`verified_golive.py rollback` (dry run by default; `--execute --allow-live-theme-id 167150092355`
to run). It works in the order that strands no reader:

1. set the ACTIVE entries to DRAFT;
2. hide the two pages;
3. reverse the 40 metafields from the reversal file;
4. restore MAIN's two files from the committed snapshot (MD5-checked) and delete the 10 created
   files.

**Proved on the preview theme:**
- Deleting in-use templates works: `page.inh-verified-hub.json` and `metaobject/sauna.json` were
  deleted while pages and entries used them.
- Shopify re-serialises a JSON template when it is recreated. The rollback's read-back now
  accepts parsed-JSON equality for `.json` (as the deploy does), not only MD5.
- The preview was then restored to 12 of 12 byte-identical.

The full rollback has **not** been executed on MAIN. `rollback-dry-run.txt` holds the plan, and
its prerequisites are OK.

## Step 3: canary

**Activated** (read back: 3 ACTIVE, 128 DRAFT):

| Canary | Record | Why |
|---|---|---|
| Labelled circuits | `golden-designs-copenhagen-3-person` | Golden Designs Copenhagen, 2 labelled circuits; INH sells it |
| Salus / Sun Home | `salus-solara-6-person` | Salus Solara, 2 labelled circuits |
| Option row | `almost-heaven-pinnacle-barrel-4-person` | "Depends on the heater option chosen" |

The hub and methodology pages were refreshed (bodies read back identical in visible text) and
published.

### Live checks (`live-checks.json`): PASS

| Check | Result |
|---|---|
| Served by | every page answered 200 from the live theme `167150092355` |
| Value match | Copenhagen 26 fact rows, Solara 25, Pinnacle 11. Every value, grade, source and number matches `saunas.json` |
| Head tags | model title tags exactly "[Title]: Verified Specs & Electrical Requirements"; self-referencing canonicals on all 5 pages; exactly one meta description on each model page, equal to its SEO description word for word |
| Structured data | valid against the current schema.org vocabulary on all 5 pages |
| Hub | lists exactly the 3 active entries; count reads "3 models from 3 manufacturers" |
| Forbidden content | none in our content: no price, no "Infinite Sauna", no "Not stated on the manufacturer's page"; health-claims gate clean |
| Links | 3 internal model links. 6 store URLs answer 200, including the theme CSS. 4 manufacturer source links answer 200/206, requested under the fetch policy |
| Product with an active entry | Copenhagen: link rendered, pointing at `/pages/sauna-database/golden-designs-copenhagen-3-person`. The sections above it are identical to the pre-deploy baseline, in order and visible text |
| Product with a draft entry | Toledo: no link rendered |

**Two live checks first failed. Both were check errors, not page errors, so nothing was rolled
back:**
- **Meta description.** MAIN's layout writes the tag across several lines, and the check's
  one-line pattern reported a present, correct description as empty. The check now allows the
  line breaks and is stricter than before: exactly one tag, equal to the SEO description.
- **CSS link.** It was reported as 404 because the link check requested the protocol-relative
  URL (`//inhousewellness.com/cdn/…`) as-is. Over https the asset answers 200 `text/css`. The
  check now resolves such URLs to https and checks the store's own URLs against the store.

### Screenshots: `docs/verified/golive/shots/`

Each shot exists at 1280 px and 390 px, from the live storefront:

- the hub;
- the methodology page;
- the 3 model pages;
- the Copenhagen product page, scrolled to the link directly below the reviews.

## For your review

1. **The hub's "Supply voltage" column** reads "Not verified" for all three canaries.
   - Copenhagen and Solara state voltage per labelled circuit, and Pinnacle's depends on the
     heater option.
   - The model pages show those answers ("See the labelled circuits above", "Depends on the
     heater option chosen"), so the hub under-states what is verified.
   - This is the Round 2 design and nothing is wrong in the data. Once everything is active, 50
     of 131 hub rows read "Not verified": 10 of them have labelled circuits and 36 depend on
     the heater option.
   - **Recommend** a hub cell reading "Per circuit" or "Depends on heater", mirroring the model
     page. That's a live template change, so it's yours to approve.
2. **Two copy changes made for staged activation**, so nothing claims pages that aren't live yet:
   - the hub's SEO description no longer states a model count;
   - the methodology adds "Model pages are published in stages. The database page lists every
     model whose page is live."

## Activation plan for the remaining 128

Each batch uses the same four commands. A failure at any step stops the batch and rolls back its
activation (`activate` sets the named entries only; `rollback` covers everything).

```bash
.venv/bin/python scripts/verified_golive.py activate --handles <batch> --write
```
```bash
.venv/bin/python scripts/verified_golive.py live-check --links
```
```bash
.venv/bin/python scripts/verified_golive.py live-shots
```
```bash
.venv/bin/python scripts/verified_golive.py verify-entries
```

| Batch | What | Entries | Visible effect |
|---|---|---|---|
| A | the remaining brands INH sells: Dynamic 25, Maxxus 12, Golden Designs 5, Dundalk 2 | 44 | 39 more product pages gain the link (40 mapped, 1 already live) |
| B | the remaining brands INH does not sell: Salus 29, Almost Heaven 22, Sun Home 14, Redwood 13, Clearlight 6 | 84 | model pages only |

- Batch A goes first because it touches product pages, where a regression would cost sales.
  `live-check` then compares every active page, not a sample.
- After batch B, hub = 131 rows. The live check asserts that the count equals the active
  entries.
- Still out of scope: the sitemap and Search Console submission, llms.txt, question pages, the
  conflict ledger, outreach and cold plunges.
