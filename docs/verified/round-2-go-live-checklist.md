# INH Verified — go-live checklist (for separate approval; NOT part of Round 2)

Going live is gated on the **Round 3 parity round** (Almost Heaven, Clearlight, Sun Home,
Redwood, Heavenly Heat extraction gaps). Nothing below runs until you approve it as its own
step. Every step names its undo.

## 0. Before anything is written
- [ ] Round 3 is merged, and the threshold is re-run: `.venv/bin/python scripts/verified_pages.py --threshold`.
- [ ] Admin token carries `write_metaobject_definitions` and `write_metaobjects`
  (check: `verified_deploy.py entries` no longer prints PENDING).
- [ ] **Confirm the live theme id at the moment of deploy.** It is `167150092355` ("Round 23b")
  as of 2026-09-28, not the `146149867587` CLAUDE.md still lists. Read the role from the API;
  never from a document.
- [ ] **Take a fresh snapshot of MAIN.** Duplicate the live theme in the admin and record its id.
  The 2026-09-15 backup `146282053699` is stale and must not be reused.

## 1. Data (entries stay DRAFT through this step)
- [ ] `verified_deploy.py entries --write`: creates the `sauna` definition (onlineStore
  `urlHandle: sauna-database`) and 67 DRAFT entries. Every entry is read back as DRAFT with a
  record identical to `saunas.json`, minus offers.
  - Undo: delete the entries, then the definition, in Admin → Content → Metaobjects.
- [ ] `verified_deploy.py metafields --write`: 39 product references. Each write is logged to
  `data/verified/internal/metafield-writes/*.jsonl` before it happens. The reversal is proved on
  the first product before the rest are written.
  - Undo: `verified_deploy.py reverse --file <that file>`.

## 2. Storefront proof on the preview, before touching MAIN
- [ ] Activate ONE entry. Probe first: MAIN has no `templates/metaobject/sauna.json`, so its live
  URL should 404. Confirm that, and check `/sitemap.xml` for any `sauna-database` URL.
  **If the live URL renders, or the sitemap lists it, stop and set the entry back to DRAFT.**
- [ ] With that one entry active, load `/pages/sauna-database/<handle>?preview_theme_id=146278776899`
  and screenshot it at 1280 px and 390 px. Run `verified_checks.py` against the storefront HTML:
  value match, forbidden content, head tags, JSON-LD.
- [ ] Load a mapped product on the preview. The link line appears directly below the reviews,
  and nothing above the reviews changes.

## 3. Deploy to MAIN (a file-level change with a file-level undo)
- [ ] Upsert the same 10 files as the preview:
  - 4 sections, 1 snippet, 2 assets;
  - `templates/page.inh-verified-hub.json`, `templates/page.inh-verified-methodology.json`,
    `templates/metaobject/sauna.json`.
- [ ] Patch MAIN's own `layout/theme.liquid` and `templates/product.json`, read from MAIN at
  deploy time, never copied from theme 13. The patch functions in `scripts/verified_deploy.py`
  halt if their anchors are missing.
- [ ] Every file is read back byte-identical by MD5. `product_prefix_unchanged` must hold
  against MAIN's pre-deploy `product.json`.
- [ ] The Round 2 script refuses any theme except `146278776899`. The MAIN write needs the
  approved live-override path (`--allow-live-theme-id` naming MAIN's id twice), not an edit to
  this script's guard.
- Undo: re-upsert the pre-deploy `layout/theme.liquid` and `templates/product.json` saved by
  `snapshot`, and delete the 10 added files.

## 4. Activate
- [ ] Publish the two pages (`sauna-database`, `sauna-database-methodology`).
  - Undo: set them hidden.
- [ ] Set the 67 entries ACTIVE. The hub lists only active entries, so partial activation never
  links to a draft.
  - Undo: set them back to DRAFT.
- [ ] Storefront screenshots of the hub, the methodology page, the five model pages and one
  product page, at 1280 px and 390 px.
- [ ] Run `verified_checks.py --links` against live URLs. This time the internal model links must
  answer 200.
- [ ] Submit the hub URL in Search Console. Confirm the canonical and structured data in the
  URL Inspection tool.

## Rollback (whole feature, minutes)
1. Set the entries to DRAFT; the model pages and product links disappear.
2. Hide the two pages.
3. Re-upsert MAIN's pre-deploy `layout/theme.liquid` and `templates/product.json`, and delete the
   10 added files.
4. Reverse the metafields with the reversal file (optional; they're invisible while the entries
   are drafts).
