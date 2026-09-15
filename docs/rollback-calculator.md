# Rolling back the True Total Cost calculator

The calculator is deployed **into MAIN** — theme `146149867587` — as eleven
files. It was not published as a theme, so rolling it back is a file-level
operation, not a theme swap.

**Backup / restore point: theme `146282053699`**
*"BACKUP of MAIN 2026-09-15 — before calculator"*, UNPUBLISHED.
Proved byte-identical to MAIN at 18:02Z on 2026-09-15 — every file, by checksum,
zero differences ([run 35005004704](https://github.com/zmpersonal/inhousewellness/actions/runs/35005004704)).
It is not "a duplicate that was created"; it is a copy that was compared.

---

## Which rollback do you want?

| Situation | Use |
|---|---|
| The calculator is wrong, broken or unwanted. Everything else on the store is fine. | **A — remove the eleven files.** Fast, surgical, reverses exactly this round. |
| MAIN is damaged in ways beyond the calculator. | **B — restore from the backup theme.** Heavier, and it reverts anything else changed since 2026-09-15 17:57Z. |

Prefer A. B reverts more than this round did.

---

## A — Remove the calculator from MAIN

This deletes exactly `deploy_theme_files.MANIFEST` — the same eleven paths the
deploy writes, read from the same list, so removal and deployment cannot drift
into disagreeing about what the calculator is.

**Dry run first. It prints the plan and sends nothing:**

```bash
python3 scripts/rollback_calculator.py --theme-id 146149867587
```

**The removal. The live-theme id is typed twice and the two must agree:**

```bash
python3 scripts/rollback_calculator.py \
    --theme-id 146149867587 \
    --live \
    --allow-live-theme-id 146149867587
```

Needs `SHOPIFY_SHOP` and `SHOPIFY_ADMIN_TOKEN` in the environment. **An agent
session cannot run this** — `inhousewellness.myshopify.com` answers 403 on
CONNECT from the egress proxy. Run it from a machine with the token, or add a
step to `.github/workflows/deploy-theme.yml` and dispatch it.

What it does, in order:

1. Reads the theme's role and refuses unless `--allow-live-theme-id` names this
   exact id. Naming any other id refuses, exactly as a normal deploy would.
2. Prints a `LIVE-THEME OVERRIDE USED` banner **before** deleting anything.
3. Deletes `templates/page.sauna-cost.json` **first**, then the section and
   assets. The mirror of the deploy's two passes: remove the file that NAMES the
   section before the section itself, or the theme is briefly holding a template
   whose section is gone.
4. Halts on any error rather than continuing into the second pass.
5. **Reads back and proves absence.** A mutation that reported success and a
   file that is actually gone are different facts.

### After removal

`/pages/sauna-cost` still exists and is still published — it falls back to
MAIN's default page template and renders an empty page, not a 404. The three
301s still point at it, so no URL breaks.

If you want the page gone as well:

```bash
python3 scripts/deploy_pages.py --pages draft     # unpublishes it; the URL 404s
```

⚠️ Do **not** delete the three redirects. They catch links to the retired URLs
and are unrelated to whether the calculator renders.

### Putting it back

```bash
python3 scripts/deploy_theme_files.py --theme-id 146149867587 --live \
    --allow-live-theme-id 146149867587
```

Same eleven files, same two passes, same MD5 read-back.

---

## B — Restore MAIN from the backup theme

Use only if MAIN is damaged beyond this round.

1. **Look before overwriting.** Diff the backup against MAIN so you know what
   restoring would change:
   ```bash
   python3 scripts/diff_themes.py --a 146282053699 --b 146149867587
   ```
   Everything it lists under *only in B* would be deleted and everything under
   *different content* overwritten. Read that list before going further.
2. **Publish the backup** (Shopify admin → Online Store → Themes → *BACKUP of
   MAIN 2026-09-15* → Publish), or:
   ```bash
   # themePublish(id: "gid://shopify/OnlineStoreTheme/146282053699")
   ```
3. The backup becomes MAIN. The old MAIN becomes unpublished and is still there
   — nothing is destroyed by publishing, which is why B is recoverable even if
   it is the wrong call.

⚠️ **B reverts every theme change made since 2026-09-15 17:57Z**, not just the
calculator. At the time of writing that is only this round, but that stops being
true the moment anyone edits MAIN.

---

## What this rollback does NOT touch

Deliberately, in both paths:

- **Navigation.** The client places the page by hand. Nothing here reads or
  writes a menu.
- **Pages, redirects, metafields, products.** Not theme files. Path A touches
  eleven theme files; path B swaps which theme is live.
- **Settings, config, locales, app blocks.** A test asserts no manifest entry is
  under `config/` or `locales/` or has `settings` in its name, so neither path
  can reach them.

---

## This path has been run, not just written

A rollback nobody has executed is a paragraph. Both halves were exercised on
theme `146278776899` (Round 13's preview theme) before this document was
committed: the eleven files were deleted, absence was read back, the theme was
redeployed, and the eleven files were read back byte-identical again.

The result of that exercise is in `RUNLOG.md` under Round 18 and in the Actions
run linked there. If you change `MANIFEST`, run the exercise again — the removal
plan is generated from that list, so a file added to the deploy is removed by
the rollback automatically, and a file added *outside* it is not.
