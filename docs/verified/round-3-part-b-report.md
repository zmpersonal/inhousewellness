# INH Verified Round 3, Part B: parity report

Branch `verified/r3-parity`. Nothing was merged, deployed or written to any theme. **API spend: $0.**
The only network traffic was manufacturer fetches under the source policy, including the headless
fallback for Leisurecraft.

## Page counts: 131 (Round 2: 67)

| Brand | Sold by INH | Published records | Pages, Round 2 | Pages, Round 3 | New |
|---|---|---|---|---|---|
| Dynamic Saunas | yes | 26 | 25 | 25 | 0 |
| Maxxus | yes | 17 | 12 | 12 | 0 |
| Golden Designs | yes | 27 | 6 | 6 | 0 |
| Dundalk LeisureCraft | yes | 2 | 0 | **2** | +2 |
| SaunaLife | yes | 6 | 0 | 0 | 0 |
| Scandia | yes | 1 | 0 | 0 | 0 |
| Salus | no | 62 | 24 | **30** | +6 |
| Almost Heaven | no | 40 | 0 | **23** | +23 |
| Sun Home | no | 15 | 0 | **14** | +14 |
| Redwood Outdoors | no | 17 | 0 | **13** | +13 |
| Clearlight | no | 11 | 0 | **6** | +6 |
| Heavenly Heat | no | 8 | 0 | 0 | 0 |
| Medical Saunas | no | 4 | 0 | 0 | 0 |
| **Sold by INH** | | 79 | **43** | **45** | +2 |
| **Not sold by INH** | | 157 | **24** | **86** | +62 |
| **Total** | | 236 | **67** | **131** | **+64** |

**What this means:** before this round, 43 of 67 pages (64%) were brands INH sells. Now 45 of 131
are (34%).

- The 64 new pages sit in `docs/verified/round-3-title-review.csv` (and `.md`), with proposed
  titles and handles and an **approve** column.
- Nothing about them is final until you approve those rows. They're rendered only as preliminary
  local pages (`out/verified/pages-preliminary/`).
- 36 of the 64 show "Depends on the heater option chosen", with its source.

### What the 67 Round 2 pages see

No key fact, electrical value, SEO field, JSON-LD value or store link changed. Two things did:

- Six pages gain a verified wood species in the full-specs table ("Not verified" becomes a
  value, e.g. Maxxus Montilemar).
- Five answer sentences change "a 8" to "an 8". That's grammar only, checked word for word.

## Decisions as applied

| Decision | Result |
|---|---|
| **D-1** exterior complete for its shape, rendered as stated | 53 new pages use `dimensions.exterior`: 51 rectangular and 2 corner (AH Sutton, Clearlight Sanctuary C, every wall plus height). No new page is a barrel stated as diameter × length: every barrel with a page states W×D×H or L×W×H. Only SaunaLife EE6G and EE8G state length × diameter; they carry the exterior but have no page (heat type and electrical are not verified), so the barrel form is shown as a labelled component fixture. **Withheld as ambiguous:** Clearlight's outdoor models (with and without roof cap), Sun Home Pod (round and rectangular both stated), and Redwood sn-cbk (roof and base). Heavenly Heat's "Spacious Design …" and "Footprint" carry no exterior label, so they don't count. |
| **D-2** capacity from page metadata unless contradicted | Evidence is labelled "page metadata". The guard is two-way: metadata that doesn't nest with the page makes capacity ambiguous. Salus Stellar and Clearlight Sanctuary 5 went to backlog (your answer). Nested statements, as in Glamour and Prana, are consistent and unchanged. |
| **D-3** heat type from the heater options only | **24 Almost Heaven records** get "traditional" from option text where every named heater is a sauna stove, and **12 of them now have pages.** Of the other 12, 7 are in backlog (R3/R5, your answers) and 5 lack capacity or exterior. The same rule also qualifies 6 Redwood and 2 Dundalk pages. The löyly paragraph never counts. |
| **D-4** headless for Leisurecraft only | It runs only when the plain fetch lacks a threshold field. It's recorded as `fetch_method: headless` on every value, and it never displaces or contradicts a plain-page statement. |
| **D-5** the Round 1 fixes, all brands | "Lumber Type", escaped PDF links and fractions are applied. None changed a value already published on a Round 2 page. |
| **The 2 failed Almost Heaven JSONs** | Retried 2026-09-28 18:23 UTC. One now reads. `nordik-indoor-saunas.json` answers **404**: Almost Heaven no longer publishes that product JSON, so there is no record for it. It's recorded as the manufacturer's 404, not as our failure. |

## Matcher errors found by the snippet audit, and their fixes

Each has a regression test in `tests/test_verified_r3.py` (55 tests).

1. "Exterior **Bench** Dimensions" and "Assembled Weight … **Crate** Dimensions" were read as the
   exterior. `EXT_GAP` now allows no part word and no digit between the label and the figures.
2. A roof size was read as the unit's size. It now carries the qualifier and renders
   "At the roof: …".
3. `ext_key` crashed on option-marker values.
4. A metric twin after each axis, as in SaunaLife's `95.3"W (242.1 cm) x …`, hid the exterior.
   The parenthetical is now skipped.
5. Fractions in several forms ("51 3/4", "86-5/8", "75 ⅜", "80⁵⁄₁₆") were read as their
   integer part.
6. Sun Home spec sheets were never attached, for three reasons:
   - the series name kept the brand;
   - "™" folded to "tm";
   - the lint checked the raw config, which lacks `_shop_prefix`.
7. Amperage was read from:
   - a figure the text says is not enough;
   - a figure in a "do not use …" prohibition, including across PDF line breaks;
   - a household outlet's rating.

   These are now skipped.
8. **Reverted during assertion replay.** I had also skipped a unit's *draw*. That flipped a Round
   1 assertion ("120 Volts 18.83 A draw" is a stated amperage). The schema defines stated
   amperage as any amperage the source states without calling it a breaker size, and skipping
   draws was the build choosing one stated value over another. With draws counted again, 7 Sun
   Home amperages are ambiguous and withheld. No page count changed. Only Sun Home was affected.
9. The Eclipse 4 GFCI requirement came from "where your local code requires …". Conditional
   sentences are now skipped.
10. Dundalk heater kW came from a "Most common for your sauna" recommendation. Configurator
    choices now make electrical option-dependent, and "No Heater" is excluded.
11. Dundalk heat type cited a configurator fragment. The description rule no longer reads
    headless documents.
12. Wood nesting was order-dependent: a generic "Cedar" could merge two different cedars. Every
    pair must now nest.
13. The metadata guard had three bugs:
    - its appended statement was wiped by a later filter;
    - it cited a synthetic snippet;
    - it treated nested ranges as contradictions.
14. The page answer sentence had two faults, found by reading renders:
    - "is **a up to** 4-person" and "a 8 kW". Articles and the "for up to N people" phrasing are
      fixed.
    - It rendered a whole-unit amperage as a circuit rating. Clearlight's "240 Volts 3,330 Watts
      13.9 Amps" is the unit's draw. The sentence now says "requires a … circuit" only when the
      source ties the figure to a circuit. Otherwise it says "the manufacturer lists at 240V and
      13.9 A". Round 2 pages keep their circuit wording because their sources say "circuit".

**No rule was loosened to raise a count.** Item 8 went the other way: it lowered verified values
to keep a prior rule.

## Still below threshold after the gap refresh

Remaining STATED_MISSED entries, each read:

| Record | Why it stays withheld |
|---|---|
| AH Alpina (electrical, heat) | heater kW from a variant list; heat type only from the löyly copy (D-3) |
| AH Saddle Mountain, View (capacity) | the snippet is another model's row in a multi-model table |
| Clearlight Sanctuary Outdoor 2 and 5 (exterior) | two sizes (roof cap / no cap): ambiguous |
| Clearlight Premier 1 (capacity) | "IS-1 Person" in the title is the model code glued to the count |
| Clearlight Curve Dome (electrical) | **known gap, left as is (decided 2026-09-28):** its electrical text sits after Clearlight's configured spec block. It misses the threshold because **its capacity is not stated**. Being a dome is not the reason: under D-1 a dome (round shape) meets the dimension requirement with a stated diameter and height. *Corrected on 2026-09-28: the first version of this row said a dome "can never meet the threshold", which was wrong.* |
| Heavenly Heat (exterior ×2, electrical) | unlabelled sizes; "either two 120V/15A circuits or …" is an option |
| Redwood sn-cbk (exterior), sn-abu and sn-qbu (heat) | roof and base both stated; heat type only from marketing copy |
| Sun Home Pod (exterior) | round and rectangular both stated |

**What blocks the rest (all brands):** electrical 58, exterior 46, capacity 19, heat type 17.

## Verification

| Check | Result |
|---|---|
| Tests | **793 passed.** 738 prior, 55 new |
| Prior assertions changed deliberately (2) | `test_page_count_is_the_threshold_count` now proves every threshold record has a page **or** is a row in the review CSV, and nothing else. It is stricter than "pages == meets", which can't hold while titles await approval. `test_verified_pages.rec()` gained the now-required `dimensions.exterior` field; no assertion changed |
| Value match, Round 2 pages | 67 pages, **1,655 fact rows**, PASS (`verified_checks.py --nojs`); hub 67 of 67 rows with JS off |
| Value match, new pages | 64 preliminary pages, **1,089 fact rows**, PASS (`verified_checks.py --preliminary`) |
| Price, "Infinite Sauna", "Not stated…", health-claims gate | clean on rendered pages, page data, methodology, theme sources |
| jsonschema and the D1 lint | pass (the build lint raises on failure). The schema now requires `dimensions.exterior` |
| Determinism | dataset identical from two brand orders; page data identical across two builds; gap diagnosis converged (two passes identical) |
| Missing-value lint | **0** |
| Preflight | static and imports clean (run with the venv; the system `python3` is too old for `--self-test`) |
| Facts cache and drift | clean, no drift |
| Deploy self-test | PASS |

## Evidence: `docs/verified/r3-evidence/`

Each render is at 1280 px and 390 px:

- Almost Heaven Pinnacle Barrel (a barrel stated W×D×H, with the "Depends on the heater option
  chosen" row);
- Clearlight Sanctuary C (corner unit; the new amperage wording);
- Redwood Barrel 6;
- Sun Home Eclipse 2;
- Salus Solara 6;
- Dundalk CT Luna (headless);
- the SaunaLife EE6G component fixture: the only diameter × length exterior in the dataset,
  labelled "not a page".

## Needs your decision

1. **Approve the 64 rows** in `docs/verified/round-3-title-review.csv`. Nothing is frozen until
   you do.
2. **The amperage wording (item 14).** I changed the template without asking, because the old
   wording misstated a draw as a circuit rating. It's one function (`amperage_is_circuit`) if you
   want different wording.
3. **The Curve Dome gap:** decided 2026-09-28, leave it. Its capacity is not stated, so it misses the threshold either way.
