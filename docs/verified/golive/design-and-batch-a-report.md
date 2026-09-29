# INH Verified: design changes live, Batch A stopped and reverted

2026-09-29. Branch `verified/go-live`. **API spend $0**: the Shopify Admin API and storefront are
unbilled, and no Blotato credits were used.

**State now (verified logged-out):**
- the canary as approved: hub, methodology and 3 model pages, in the new design;
- 128 entries DRAFT;
- the Copenhagen product link.

**Not merged.** Step 2 failed, so the launch stopped there and Step 4's merge was not run.

## Latent theme risk (approved, done)

- **CLAUDE.md rule:** a new governance section, "Before ANY theme is published — INH Verified must
  travel with it". It lists every file and patch, and requires the hub row check and one
  model-page check on the theme's preview.
- **`scripts/verified_theme_check.py --theme-id ID`** (read-only). It checks every file against
  the repo (MD5 or parsed JSON), the layout branch and the product link placement, then the hub row
  check and one model value-match on the theme's preview.
  - MAIN `167150092355`: **PASS**.
  - Round 23 `167149797443`: **FAIL**, with 10 files missing, no layout branch and no link section.
  - 2 tests.
- **Hub page body rewritten** (its fallback), with the template set explicitly and read back. It is
  still published. Seen through an older theme's preview, the hub now reads:
  > The InHouse Wellness Verified Sauna Database lists home sauna models with their specifications
  > and electrical requirements. Every value is copied from the manufacturer's own product page or
  > manual, and each one is graded, dated and linked to its source. How values are sourced, and
  > which models get a page, is explained in How the Sauna Database Is Verified. To report an error,
  > email data@inhousewellness.com with the source that shows the correct value.

  There is no model list and no count.

## Step 1: design changes (live)

**What changed:**

| Item | What was built |
|---|---|
| a) Sources as footnotes | Each value keeps its grade and date. Its inline link is replaced by `[n]`, linking to `#inhv-src-n`. A single **Sources** list at the bottom links each distinct URL once, with the grades of the values citing it (e.g. "Listed · Claimed") and the fetch date. Quoted source text keeps its field and gets the same marker. Option rows cite the option evidence |
| b) Outbound links | Every link to another domain carries `rel="nofollow noopener"`: the Sources list and the manufacturer link. Checked on every live page |
| c) Model number | "Model GDI-7389-02" appears under the H1 when verified; `mpn` in JSON-LD when there is exactly one model number. **The title tag gets it only for brands InHouse Wellness does not sell** (brand-level, so a model a mapping missed can never gain it), only for a single model number, and never twice. 57 of the 86 not-sold pages gain it. No URL or handle changed |
| d) Store buttons | `btn btn-primary` (the theme's Add to Cart style). One compact button directly under the key facts, only where a product mapping exists, set apart by rules. The store block stays below the specifications |
| e) Similar models | Only on pages of brands INH does not sell. The fixed rule: same verified heat type, same verified placement, nearest capacity (midpoint distance), ties by title. It links to the INH product page and states "Chosen by that rule alone, not a claim that they are equivalent: compare the specifications." With no matches, only the collection link shows |
| f) Hub Power supply | The header is renamed. The cell is read from the model page's own rows: a verified voltage, "Multiple circuits" (every such record has exactly 2), "Depends on heater", or "Not verified" (4 pages) |

**Deploy.**
- MAIN's 4 affected files and all 131 entries' fields were snapshotted and committed
  (`data/verified/golive/step-design/`).
- Entries were updated first, with status unchanged. The page data is backward compatible, so the
  old template kept working. Then the 4 files were deployed behind the snapshot gate and the named
  override. They read back **4 of 4 byte-identical**.
- Diff: `design.diff` (93 lines).

**Found before deploying, by rendering locally:** the button text was invisible (dark on the black
button), because `.inhv a` outranked the theme's `:is(.btn-primary…)` colour. It's fixed with the
theme's own `--btn-color`.

**Live checks after the design deploy: PASS.** All through the logged-out visitor fetch, with no
preview cookie:
- 3 model pages: 62 fact rows, including every marker resolving to the dataset's source, the
  model-number rules, the similar-model rules and outbound rel;
- hub: 3 of 3 rows, all 15 cells re-derived from the records;
- 11 store links and 4 sources answer;
- Copenhagen linked, Toledo not, and the sections above the reviews unchanged.

**New checks** (18 new tests; 819 in total):
- source markers resolve to the value's dataset source (quotes included);
- every hub cell against the record;
- outbound rel;
- model-number subheading, title rule and `mpn`;
- the top button only when mapped;
- the similar-models rule.

Mutation tests prove each one fails on a broken page.

**Screenshots** (clean session, desktop and mobile) in `docs/verified/golive/shots/`:
- `live-model-golden-designs-copenhagen-3-person-*` (sold);
- `live-model-almost-heaven-pinnacle-barrel-4-person-*` (not sold, with the similar models);
- the hub, the methodology page, Solara and the Copenhagen product page.

## Step 2: Batch A (failed, reverted)

**Pre-activation baselines:** all 39 product pages were fetched logged-out from the live theme,
with no link yet.

**Activated 44 entries** (Dynamic 25, Maxxus 12, Golden Designs 5, Dundalk 2). Read back: 47
ACTIVE.

**Live checks** (`live-checks-batchA-failed.json`):

| Check | Result |
|---|---|
| Hub | 47 of 47 rows; 235 cells match |
| Model pages | 47 answered 200 from the live theme (plus the hub and methodology); 1,126 fact rows match; 47 meta descriptions exact |
| Links | 59 store links 200; sources 47 × 200 and 26 × 206 |
| Above the reviews | unchanged on all 40 product pages |
| Product links | **39 of 40 rendered.** `leisurecraft-luna` has no link, although its entry was active: **FAIL** |

**Root cause.** `leisurecraft-luna` is the only mapped product using the alternate template
`product.Bundle.json` (`templateSuffix: Bundle`). The go-live patch added the link section only to
the default `product.json`. The metafield was set and the entry active, but the template has no
section to render it. The page was not broken, only missing the link.

**Response, as instructed.** All 44 entries were set back to DRAFT. Read back: 3 ACTIVE and 128
DRAFT. The live check on the canary state passes (`live-checks-after-revert.json`).

### Decision needed: the Bundle template

| Option | What | Effect |
|---|---|---|
| **A (recommended)** | Patch MAIN's own `templates/product.Bundle.json` with the same patch: the link section directly after its one enabled reviews section (`judgeme_reviews_bundle`), snapshot first, read back, diff. Extend the theme check and the CLAUDE.md file list to cover **every product template a mapped product uses**. Then re-run Batch A | Luna gets its link. The gap cannot recur on a future template |
| B | Remove Luna's metafield (reversal file) and activate Batch A without it | Luna never shows the link. The check expects none |
| C | Accept a product without its link | Not recommended: it weakens a gate that caught a real gap |

## Finding: any path under /pages/sauna-database/ answers 200 with the hub

`/pages/sauna-database/<draft or nonexistent>` answers **200**. It renders the hub with a canonical
pointing at the requested URL itself: a soft 404.

- **Before the hub was published** (the canary baseline), draft URLs answered 404.
- **Cause:** the definition's URL handle equals the hub page's handle (D-I), so Shopify falls
  through to the page.
- **Not caused by Batch A.** Draft URLs are not in the sitemap, and no page links to them, so today
  it is reachable only by typing a URL.

**Options:**
1. **(Recommended)** In the hub template, when the request path is not exactly
   `/pages/sauna-database`, emit `<meta name="robots" content="noindex">` and a canonical pointing
   at the hub. This is a small template change on MAIN.
2. Move the model URL handle off the page handle (e.g. `/pages/sauna/<handle>`). Every URL
   changes, which is costly after launch.
3. Accept as is.

## Step 3: similar models for Batch B (not activated)

| Matches | Pages (of 84) |
|---|---|
| 3 | 51 |
| 2 | 2 (Salus Harmony, Salus Serenity) |
| 1 | 0 |
| 0 | 31 |

The 31 pages with no match break down as follows:
- **14 have no verified placement.** The rule requires the same placement, so they get only the
  collection link.
- **15 are traditional indoor models.** INH has no mapped traditional indoor sauna.
- **2 are infrared outdoor models.** INH has no mapped infrared outdoor sauna.

By brand: Salus 9, Almost Heaven 7, Clearlight 6, Sun Home 6, Redwood 3.

**Example pairings:**
- **Salus Glamour, 1 Person** [infrared, indoor, 1]:
  - Golden Designs Reserve Edition, 1 Person [infrared, indoor, 1];
  - Maxxus S-Line, 1 Person [infrared, indoor, 1];
  - Dynamic Avila, 1–2 Person [infrared, indoor, 1–2].
- **Sun Home Eclipse, 2 Person** [infrared, indoor, 2]:
  - Dynamic Cordoba, 2 Person;
  - Dynamic Heming DYN-6225-02;
  - Dynamic Heming DYN-6225-02 Elite.

  Note two variants of one model, which are separate store products. If you'd rather the rule
  show one per model series, that's a change to the rule.
- **Redwood Barrel, 6 Person** [traditional, outdoor, 6]:
  - Golden Designs Kaarina, 6 Person;
  - Golden Designs Vorarlberg, 5 Person;
  - Dundalk CT Luna, 4 Person.

## Step 4: sitemap (read-only) and merge

- `sitemap_pages_1.xml` lists the hub and the methodology page.
- `sitemap_metaobject_pages_1.xml` lists exactly the 3 active model pages.
- No draft entry appears. After the temporary 47-entry activation and its revert, the sitemap was
  read again and lists the 3 again.
- Details: `sitemap-findings.json`.
- **Merge not run:** the launch stopped at Step 2. The branch is committed and not pushed to
  `main`.
