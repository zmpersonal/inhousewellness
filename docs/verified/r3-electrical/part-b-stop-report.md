# r3-electrical Part B: stop point (step 6), awaiting approval

2026-10-07 · branch `verified/r3-electrical-coverage` · **nothing published, nothing frozen, no Shopify write
in this round so far**

The approval sheet is **`publish-review.csv`**, with the same rows in `publish-review.md`. Both are generated
by `scripts/r3_publish_review.py --base 7ded6fd`; nothing in them is typed by hand.

## 1. Token check (§0): PASS

| Check | Result |
|---|---|
| Loader reads `InHouseWellness/.env` | yes (updated 2026-10-07 13:30) |
| Scopes | all 22, nothing extra |
| `tool-electrical/.env` | gone |

## 2. What was applied (steps 2–5)

**D1, shared covers.**
- **What qualifies.** The cover must:
  - name 2 or more models, including this one;
  - state exactly one voltage/amperage pair;
  - carry no conditional figure.
  The full cover span is stored as the evidence.
- **How it is used.** It is a last resort: dropped wherever any other source states the field.
- **What it changed.** It adds no publishable value this round:
  - every qualifying cover states multiple circuits, which the existing rule withholds (D12);
  - the barrels' lighting-only covers are superseded by their pages' fuller option-dependent
    statement (D4).
- **What was corrected along the way.** First drafts:
  - took a live record's correct figure away (Soria, Maxxus K306);
  - gave GDI-8202-01 a lighting outlet as its supply;
  - moved 10 live Dynamic records' citations onto covers, which would have blanked them in the tool.
  All were caught by diffing, and none remain.

**D2, trailing labels.** The quote builder now binds "…Required (DYN-6115-05/DYN-6215-05)".
- Lucca Elite (DYN-6215-05) now shows its 15 A in the tool.
- A parenthesised model list closes the previous clause and never labels the next figure. The
  regression test pins DYN-6215-05 = 15 A and DYN-6315-05 = 20 A.

**D5, exteriors.** "Exterior (WDH)" is read only from the 6 approved records' own sources
(`data/verified/r3/d5-exterior-approved.json`): GDI-8202, 8203, 8222, 8223, 8506 and 8526.

**D8, dead link.** Golden Designs' current GDI-8040-03 entry links a new manual (`723ec1a8…pdf`). It
states the same requirement, and the record now cites it in place of the 404. The value stays withheld
as multi-circuit (D12).

**D3, our-page manuals.**
- 63 were downloaded and hashed (`data/verified/r3/ownpage-manual-hashes.json`).
- 7 are byte-identical to a copy on the brand's own host, and are cited by that URL.
- 1 matched a Harvia manual on **Salus's** store and was rejected: a copy must be on the brand's
  own host.
- D3 enabled no new publishable record this round.

**D6, new records.**
- 16 identity-only leads (our SKU plus the manufacturer's URL and title; no values from our pages)
  produced **16 new records, all meeting the threshold**.
- 2 candidates were **duplicates** of existing records and were not created:
  - GDI-8206-01 Bergen;
  - GDI-6996-02.
  They are map gaps (D14).
- The record brand follows the manufacturer's title: Golden Designs' store lists Dynamic models
  under its own vendor name.

**D11, fetches.** Log: `d11-fetch-log.json`.
- **What was requested:** only what's needed (discovery refresh plus matched pages), **23 requests**.
- **Skipped**, still unreachable on a fresh probe today:
  - Kohler: robots.txt timeout;
  - Ripavi: TLS EOF;
  - Mande Spa: TLS alert.
- **Golden Designs' own product pages link 7 PDFs that answer 404** (logged).
- **Finnmark** was added to the registry with its own domain (finnmarkdesigns.com hosts its manual)
  and gave **1 new record (FD-1)**.
- Medical, SaunaLife, Dundalk and Scandia matched **existing** records only (see D14).

**Live records.** No live record's value changed except one identity field: `dyn-6315-05` gains a
manual-sourced configuration (`DYN-6315-05`) because its new Elite sibling now exists. It is not
deployed: live metaobjects are untouched.

## 3. Coverage projection (priced INH saunas, counted exactly as the tool counts)

| | Stated circuit | Current draw only | Neither | Share |
|---|---|---|---|---|
| Start of round | 38 | 0 | 101 | 27.3% |
| Now (D2 only; nothing published) | 39 | 0 | 100 | 28.1% |
| **If all 21 linked rows are approved** | **60** | 0 | 79 | **43.2%** |
| + D14 (link records matched by exact manufacturer SKU) | 64 | 0 | 75 | 46.0% |
| + D12 (read "N separate circuits"; 9 records, titles needed too) | up to ~73 | 0 | ~66 | ~52% |

- Lighting-only circuits are counted separately: 0 this round.
- By brand (before → after approval):

  | Brand | Before | After |
  |---|---|---|
  | Dynamic | 24 | 35 of 38 |
  | Golden Designs | 6 | 14 of 31 |
  | Maxxus | 9 | 11 of 34 |
  | All others | 0 | 0 |

- Details: `coverage-projection.json`.

## 4. Handles that need your choice (4 rows)

| Record | Proposed | Problem | Suggestion (R2 rules: edition token, then model number) |
|---|---|---|---|
| `dyn-6203-01` Cordoba | `dynamic-cordoba-2-person` | frozen for the live Cordoba **Elite** | `dynamic-cordoba-dyn-6203-01-2-person` |
| `dyn-6315-05-elite` Toscana Elite | `dynamic-toscana-3-person` | frozen for the live base Toscana | `dynamic-toscana-elite-3-person` |
| `gdi-8020-03` Reserve Edition | 77 characters | over 60; "Edition" | `golden-designs-reserve-edition-2-person` (precedent: `golden-designs-reserve-edition-1-person`) |
| `gdi-8030-03` Reserve Edition | 77 characters | over 60; "Edition" | `golden-designs-reserve-edition-3-person` |

## 5. Decisions still open (not applied)

- **D12, multi-circuit statements.** For example, "TWO SEPARATE 120V/15AMP DEDICATED CIRCUITS
  REQUIRED".
  - Options:
    - (a) store the per-circuit figure with the stated count and a note;
    - (b) keep withholding, as the build's recorded rule says ("one amperage would misstate it").
  - Affects 9 priced records:
    - DYN-6996-01 Elite, GDI-6996-01 Elite;
    - GDI-8040-03, 8230-01, 8260-01;
    - MX-J306-02S;
    - MX-K356-01-ZF-CED, MX-K406-01-ZF-CED, MX-K406-01-ZF-HEM.
  - **Recommend (a).** The tool already quotes the sentence verbatim, so "two separate" is visible.
- **D13, "Exterior (WDH)" on the ~89 other records** (≈55 live) where the same stated form was never
  read. It would change live page data at the next entry update. **Recommend:** a separate, small
  round with its own diff review.
- **D14, linking by the manufacturer's exact variant SKU.** Records matched to our SKU by the
  manufacturer's own catalogue, which the R2-D12 map cannot link because they hold no verified
  model-number field.
  - It would link 4 priced saunas with stated circuits:
    - the Toscana Elite and Finnmark FD-1 (new);
    - live `mx-k206-01-hemlock` and `mx-s306-01`.
  - It would also link the Medical and SaunaLife records, which do not meet the threshold.
  - **Recommend:** approve, as the same exact-match principle on the manufacturer's SKU.
- **Barrels (D4).** GDI-B002/B004 state "240V / 30AMP (6KW Stove) OR 240V / 40AMP (8KW Stove) and
  120V / 15AMP (Control for Lights)", which is option-dependent and withheld. The cover's
  lighting-only line is not shown alone, because it would present half the requirement as the
  whole.

## 6. Still failing the threshold (19 touched priced records)

Listed in `publish-review.md`:
- 9 are withheld only as multi-circuit (D12);
- 2 barrels are option-dependent;
- 7 Golden Designs records state no exterior dimensions anywhere cached: GDI-7202-01, 7203-01, 7206-01,
  8003-01, 8005-01, 8123-01 and 8125-01;
- the Scandia DIY kit is missing everything.

## 7. Tests and sweep

| Check | Result |
|---|---|
| Tests | **878 pass** (877 prior + the D2 regression) |
| Missing-value lint | 0 |
| Preflight | clean |
| Dataset rebuild | deterministic (identical MD5) |
| Electrical build `--check` | no drift |

**Prior assertions amended, each to its stated intent, never weakened:**
1. **The line-table quote test** now allows only a co-label inside the parenthesised label that names
   this model (D2).
2. **The page-count invariant** also reads this round's review file, as it reads Round 3's.
3. **My own Round 1 test** pinned literal counts (74/25) from data this round changes. It now asserts
   the set relationship instead (CLAUDE.md, "never assert a literal from refreshed data").

**After approval (steps 7–8):**
- freeze the approved titles and handles;
- create and activate the entries with read-back;
- log the handles with a one-command revert;
- rebuild the tool asset;
- deploy to preview `188725788739` only;
- update the 3 hidden answer pages;
- run the render checks and the hand checks.
