## Round 18i — guard audit (complete), Layer 1 built, zero-review export. NOTHING LIVE: Admin token 401.

**Token.** The Admin API token returns 401 on every client, including `scripts/lib/shopify.js`. Last confirmed
success **14:39:22Z**, first 401 **14:44:29Z**, and still refused at 14:56Z, with `.env` unchanged since Sep 17. It
died mid-session, so this is not a stale value. (My earlier in-session "about 14:25Z" was wrong; these two
timestamps come from the session record.) Not worked around; the client is checking the app's install date and scope history. **No live write this
round.** The read-only Shopify connector was used, with the client's authorisation, only for the review export
and for resolving MAIN by role (MAIN = `146318491715`).

**Guard audit: every guard checked.** Full report in `reports/r18i-guard-audit.md`. In summary:
- 72 apply scripts: linted; 60 statically reviewed.
- 42 audit and lib scripts: about 210 mutants.
- Round 18 write paths: replayed in a mock store against their own backups.
- Shared write guards: a self-test run against the old `util.js`, which fails exactly its 9 holes.

What was broken, all of it green before:
- 22 failed-write branches exited 0, and `theme-push` logged failed pushes as pushed.
- `assertWellFormed` passed further damage to an already-unbalanced tag, and could not see span, div or table tags.
- `assertFresh` read a missing changelog as fresh.
- The `apply-collection-copy` approval gate matched `approved-pending-read`. Those are the 4 STALE files; an unscoped
  run would have written older copy over live.
- A hold list held nothing (`huum-hive`).
- A reach guard sat after `process.exit`.
- An escaper escaped nothing.
- A dry run overwrote the only backup.
- 5 preview verifiers never checked which theme served the page, and passed while reading MAIN.
- `drift-check` skipped 63 of 183 claims (13 collections drift, not 6).
- The 18h product proof counted a restore that wrote-then-failed as "refused".
- "Unwrap only" was unenforced.

Everything fixed was re-proved with a mutant. 7 consumed one-shots are retired: they refuse at the top and say why.
**New standing rule in CLAUDE.md: a guard that cannot be shown to fail is not a guard.**

**Built, proven, NOT applied** (each runs through `r18i-article-proof.sh` in the mock; one command each once the token
works):
- `r18i-edit.mjs`, Lugano sentence 2. Proven on a reconstruction whose md5 equals what Shopify stored.
- `r18i-frozen-edit.mjs`, Medical Frozen (client-approved):
  - 3 deletions and 1 heading change;
  - the fifth link repointed to the Finnmark SoulCold;
  - new `delete` kind, mutation-proved.
- `r18i-catalonia.mjs`, "indoor" and "118°F–132°F, heats up to 140°F" added to the live $9,999 listing. Sourced from
  our own archived listing of the same model; the restore gained a product mode.
- The live Catalonia description carries a leaked generation instruction (*"The first 205 characters emphasise…"*).
  Flagged, not changed.

**Layer 1: `scripts/audit/linked-product-status.mjs` plus `.github/workflows/linked-product-status.yml`** (nightly
11:30 UTC, read-only, installs nothing).
- Self-test: 23 fixtures; 7 mutations each make it fail.
- On a labelled REPLAY of today's Admin reads it FAILS on Medical Frozen Plunge 1 (DRAFT, 7 links, 5 articles). All
  90 other linked products answered 200 live.
- It passes only with an expiring acknowledgement, which is **not committed** (client decision).
- Live mode today exits 1 on the 401: a check that cannot run is not a pass.

**Zero-review export:** `reports/zero-review-products.csv`.
- 483 ACTIVE products; **298 with zero Judge.me reviews (61.7%)**.
- **$1,183,103** of $2,370,032 entry-price catalogue value (49.9%) has no reviews. 77 are priced ≥ $5,000; 29 ≥ $10,000.
- Basis: the `reviews.rating_count` metafield, cross-checked where both exist against the Judge.me widget
  (0 disagreements in 48). The storefront badge showed 0 on all 8 zero-review samples, and 15 = 15 on the
  2 reviewed controls.

**Client rulings recorded:**
- Frozen 4 XL / 6 XL stay live; not touched.
- `/blogs/news/best-6-person-sauna` stays where it is: struck from BACKLOG.
- `custom.capacity_` stays overloaded: closed in BACKLOG, and the analysis caveat added to CLAUDE.md.

**Local path** (contains spaces): `/Users/convertcoldmedia/Desktop/Claude Master/InHouseWellness/inh-seo`.
- The spaces-in-path fix is applied everywhere the pattern exists: the two places it bit, plus the one new file,
  written correctly. No raw `file://${process.argv[1]}` comparison remains.

**Queued for the token, in the client's order:**
1. Lugano sentence 2
2. Medical Frozen edits
3. Catalonia specs
4. Layer 1 live run
5. Frozen 4 XL / 6 XL inventory
6. Products orderable at zero stock
7. Site-wide reconciliation

**Friction:** twice this round, an exit code alone counted as "refused", once in a runner I had just written. And
the Medical Frozen spec was typed from a display with U+00A0 in it, the exact trap CLAUDE.md names. Both were
caught by a count or a premise check, not by reading.

---

## Round 18h — Versailles ×2 republished sold out; Osla channels matched; Lugano tier line. LIVE.

**⚠️ KLAVIYO — the Shopify integration must be REPAIRED before the flows are enabled.**
- The client shut the flows off on 2 March, deliberately, and is re-enabling them next week. Nothing was changed from here.
- **Zero "Placed Order" events have reached Klaviyo since March**, while Shopify recorded orders in August and September.
- Flows keyed on order events would therefore switch on and never fire. That is a **silent channel**: enabled, green, and sending nothing.
- Repair the connection first. Then check that a test order arrives as a Placed Order event. Only then enable the flows.

**Versailles, both listings.** Edition `dynamic-infrared-sauna-versailles` and Elite `dynamic-versailles-elite-2-person-infrared-sauna`.
- Sequence: policy **DENY first**, `availableForSale` asserted false, then ACTIVE, then channels. Never live and orderable.
- The full restore-proof sequence ran on each listing: apply → restore → no-op → faked change refused → apply.
- Rendered result for both: **HTTP 200**, schema `OutOfStock`, cart disabled, $2,299.
- Both article links (functional-health-coaching, dynamic-saunas-review) point at the Edition and resolve 200. **The Elite carries no article link.**
- Channels:
  - Edition: Meta, Copilot, Online Store, Shop, plus POS. POS was its pre-round state, revealed on activation.
  - Elite: Meta, Copilot, Online Store, Shop.
- Backups: `…T14-05-36-565Z`, `…T14-05-58-906Z`.

**Osla channels.** The convention across the 166 comparable ACTIVE saunas:

| channel | share |
|---|---|
| Online Store | 166/166 |
| Shop | 166/166 |
| Copilot | 166/166 |
| Meta | 165/166 |
| POS | 95/166 (Golden Designs 21/39, Dynamic 17/39) |

- Osla was matched on the four consistent channels: **Meta added**.
- **POS held.** The catalogue is inconsistent on POS, so it was neither added nor removed.
- Osla is now on Meta, Copilot, Online Store, POS and Shop: ACTIVE, DENY, 200, `OutOfStock`.

**Correction to 18g.** I reported the Osla as live on the Online Store only. It was also on Copilot, POS and Shop. The 18g script read the Online Store alone, and that one channel was all it could see.

**Incident during the Osla proof, found and repaired in-session.**
1. Meta could be added but its **unpublish silently did not take**, so the restore step failed.
2. The proof steps were piped through `grep`, so the failure did not halt the chain.
3. The tamper step altered only the recorded `before`. Live still matched `after`, so the guard passed.
4. The restore therefore wrote the tampered state. **The live Osla was ARCHIVED for about 7 seconds.** It was never orderable, because DENY was already set.
5. The final re-apply then dropped POS, which the client had said to hold.

Repair: POS re-added and verified.
Prevention:
- the proof now runs through `scripts/apply/r18h-proof.sh`, which halts on any non-zero exit;
- the tamper alters **both** recorded states;
- on apply, the script manages only the convention channels and never touches POS.

**Lugano tier line (dynamic-saunas-review), corrected to catalogue naming**

| | text |
|---|---|
| before | "from $2,699 (**FAR**) to $3,499 (**Low EMF**) to $3,899 (Near Zero full spectrum)" |
| after | "from $2,699 (**Low EMF**) to $3,499 (**Ultra Low EMF**) to $3,899 (Near Zero full spectrum)" |

- The restore-proof ran first. The injected word and injected link were both refused, and the injections now assert that they landed.
- Rendered result: the new string 1×, `$2,699 (FAR)` 0×, `$3,499 (Low EMF)` 0×, and the row unchanged.
- Backup: `…T14-07-28-543Z`.
- **Held, not changed.** The same article restates the tiers as *"offered as a FAR-infrared version ($2,699) and a Near Zero full-spectrum version ($3,899)"*. Proposed rewording: *"…as an Ultra Low EMF Elite ($3,499) and a Near Zero full-spectrum version ($3,899)"*. It needs authorising.

**Reported, nothing changed.** Details in `reports/r18h-medical-frozen.md` and `reports/r18h-draft-linked-check.md`.

- **Medical Frozen Plunge 1:** 7 links in 5 articles.
  - **4 of the 5 sentences name it and recommend it**, three of them for safety or reliability, the property it was withdrawn over.
  - The 5th recommends only through its link destination.
  - The live `cold-plunge-brand-we-dont-recommend` says *"we do not recommend them first"*, which contradicts those four.
  - Closest substitute from another vendor: **Finnmark SoulCold, $9,320**. It is a reclined one-person tub, the same form. The IceBarrel ($9,800) is closer in volume but upright.
  - A repoint alone leaves Frozen named in 4 sentences.
  - Frozen XL 4 and XL 6 ($12,649 each, **CONTINUE**) are ACTIVE and have 0 article links. Whether the quality ruling covers the whole brand is the client's call.
- **Standing check:**
  - Measured: 91 linked products, 90 ACTIVE, 87 inventory-tracked.
  - Proposal: a nightly read-only outcome check (status, channel, HTTP) that fails on any linked product that is not live.
  - Then a pinned product metafield warning, placed where the person drafting the product will see it.
  - A Shopify Flow alert is optional.
  - No auto-fix is proposed.

**Site-wide, 18g → 18h:** external 3,627 → 3,627, internal 1,210 → 1,210, institute 2,047 → 2,047.
- 120 articles, 362 domains.
- **0 per-article records moved and 0 link-multiset differences**, which is expected for a text-only edit and product-side writes.
- The pre-state file was restored byte-identical afterwards.

**Friction:** a guard fired correctly while the chain around it kept going. The proof was sound, but its runner was not.

---

## Round 18g — Osla republished sold out; 4 articles corrected; Klaviyo reported. LIVE.

**Osla** (`golden-6-person-sauna`): policy CONTINUE → **DENY first**, then ACTIVE, then Online Store —
never live and orderable. Restore-proof run on the product (apply → restore → no-op → faked change
refused → apply). **Rendered: HTTP 200, "Out of Stock", add-to-cart disabled, JSON-LD OutOfStock,
$8,499 shown. All 14 links share one href and it resolves 200.** Meta / Copilot / POS / Shop not
restored — only the Online Store is addressable from `publications()` and it is the one that fixes the 404.

**Articles** (restore-proof on the Monaco article first; injected word and link both refused):
| article | change |
|---|---|
| golden-designs-saunas-review | 9 Catalonia links → live twin (same model GDI-6880-02 Elite); $14,999 → **$9,999** ×2. No sentence's argument depends on the old price — the Budget tiers never named Catalonia |
| dynamic-saunas-review | `dynamic-garcia` → live DYN-6119-01 (same price); Lugano **row** $3,499 → **$2,699** |
| costco-sauna-guide-worth-it | the 8 approved "identical" phrases |
| dynamic-saunas-monaco-dyn-6996-01-elite | all 5 MSRP / street-price claims → "$6,499 at InHouse Wellness" |
Rendered: every check passes; both new link targets resolve to the right SKU and price, available.
Site-wide external 3,627 · internal 1,210 · institute 2,047 — all unchanged, as expected.
Backups: `…T13-46-24-061Z/r18g-osla.json`, `…T13-48-43-617Z/r18g-edit.json`.

**Flagged, not changed:** the Lugano **tier line** ("$2,699 (FAR) to $3,499 (Low EMF)") mislabels both
tiers against our own titles (Low EMF = $2,699; the $3,499 Elite is *Ultra* Low EMF). The live Catalonia
listing does not state the article's "~140°F" or "indoor" (not contradicted). A stale editor's HTML
comment in dynamic-saunas-review still names `/products/dynamic-garcia` (unrendered).

**Draft-linked products now:** 2 — Medical Frozen Plunge 1 (7 links) and Versailles (2), both held by
the client. Down from 5 / 33. Catalogue: 168 DRAFT, 21 ARCHIVED. **0** active products are tracked,
at zero stock and still orderable — the practice is effectively pull-to-draft.

**Klaviyo (report only, nothing enabled):** 20 flows — **17 disabled, all at 2026-03-02T20:40:51Z**
(the same second — a bulk action), **3 drafts** from Jan–Feb 2025 that were never live. Abandoned Cart
and Browse Abandonment are among the 17. **Shopify "Placed Order" events into Klaviyo: Jan 5, Feb 8,
then 0 every month Mar–Sep, while Shopify recorded orders in Aug and Sep** — the integration is not
delivering. Onsite script: absent from the storefront, **no Klaviyo app embed in the live theme at all**
(only Judge.me, Triple Whale, UpPromote); Hyperspeed defers `static.klaviyo.com` regardless. A
back-in-stock form existed once (metrics created 8 July 2025).

---

## Round 18f — 3 Gracia repoints + 1 price LIVE; 8 sentences drafted; 5 unavailable products reported

**Live (restore-proof sequence on best-2-person-sauna-buyers-guide first):**
costco-sauna-guide-worth-it — the 3 remaining Gracia links repointed DYN-6119-03 FS → DYN-6119-01,
anchor text unchanged (rendered: 0 full-spectrum links left in the article, 4 to DYN-6119-01) ·
best-2-person-sauna-buyers-guide — Maxxus Seattle "under $2,000" → "at $2,299".
Proof re-proved on this script (injected word and injected link both refused). Backup
`data/backups/2026-09-18T13-21-07-410Z/r18f-edit.json`. Site-wide: external 3,627, internal 1,210,
institute 2,047 — all unchanged, as expected for repoints and a price.

**Drafted, NOT applied (hard rule 5):** `content/drafts/r18f-identical-rewrites.md` — **8** sentences,
not 10 (the ~10 counted table cells; 4 more wider-net hits are a scope line, a disclaimer and an
instruction, left alone). All 8 before-strings verified unique in the live body.

**Held for a decision:** Lugano row (identity, not price) · Monaco "$5,999 MSRP" ×5 (positioning).

**Reported, nothing changed:** `reports/r18f-unavailable-products.md` — 5 products, 33 links, all 404.
Osla (client: OOS) · **Catalonia and `dynamic-garcia` are duplicates of live listings** · Medical
Frozen Plunge 1 and Versailles ambiguous. **Osla's sell-when-OOS policy is ON** — republishing as-is
would make it orderable. Sold-out pages render well (200, "Out of Stock", disabled cart, OutOfStock
schema); **no back-in-stock capture exists**. Outside scope: **all 20 Klaviyo flows disabled or draft**
since 2 March 2026, abandoned cart included.

**GSC:** the Search Console connector now loads but lists **zero sites** — still no fresh GSC.

**Correction owed and made:** the client called the four items authorised in the previous message;
that message held them for review. Read this message as the authorisation, and said so.

---

## Round 18e — Option A, the Gracia and Bellagio rows, the orphaned LifeTrend sentence. LIVE.

| change | before | after |
|---|---|---|
| Sources: 3 Dynamic citations | linked to Costco | **unwrapped, names kept, no wording change** |
| Table 7 Bellagio · InHouse price | ~$2,499 | **$2,699** |
| Table 7 Bellagio · relationship | Exact same model | **Same model line** |
| Table 7 Gracia · link | DYN-6119-03 FS ($2,899) | **DYN-6119-01 ($1,999)** |
| Table 7 Gracia · InHouse price | ~$1,899 | **$1,999** |
| Table 7 Gracia · relationship | Exact same model | **Same model line** |
| note under Table 7 | — | *"Same model line" is matched on the model name. Confirm specifications against the current Costco listing before comparing.* |
| LifeTrend | …confirm on the live page before purchase. | …confirm with Costco before purchase. |

**There is no San Marino Elite row in the comparison table.** Its two links resolve to
DYN-6206-01 Elite, which name-matches Costco's listing; no InHouse price is quoted for it anywhere.

**Proof:** link multiset as declared (−4 +1, the Gracia repoint); visible text outside declared changes
byte-identical in both articles; **the proof was made to fail on purpose** with an injected word and an
injected link, and refused both. **Restore sequence** on costco-sauna-guide-worth-it — an article
carrying an earlier round's edit — md5 round-trip, no-op re-run, faked edit refused, then full apply.
Backup: `data/backups/2026-09-18T03-09-09-379Z/r18e-edit.json`.

**Rendered:** Table 7 correct; Gracia row → `/products/1-2-person-infrared-sauna-hemlock-chromotherapy`
(DYN-6119-01, $1,999, available); one Costco link left (return policy); "Exact same model" absent.

**Site-wide:** external 3,630 → **3,627** (Δ3) · internal **1,210** (Gracia swap is one-for-one) ·
institute **2,047** · costco 4 → **1** · 13 withheld unchanged.

**Costco guide audit (report):** 22 InHouse product links; **all 4 Gracia links point at the wrong
product** (1 fixed, 3 remain); ~10 prose representations of "identical / same hardware".

**Site-wide price staleness (report):** 119 published articles · 15 quote a price beside a product link ·
122 link/price pairs · **109 state the live price** · 13 read by hand → **3 genuinely stale**:
Maxxus Seattle "under $2,000" (live $2,299), Lugano DYN-6336-02 "$3,499" (live $2,699), Monaco
"around $5,999 MSRP" (live $6,499). **Not widespread.** The bigger finding: **33 links to 5 DRAFT or
ARCHIVED products, all returning 404.**

---

## Round 18d — 13 competitor links removed, 4 orphaned sentences rewritten, item 1 HELD. LIVE.

**Executed:** Costco ×10 (#1–4, #8, #10–14) · rcwilley.com · homedepot.com · realrelaxmall.com
(reclassified T1 per the quote-gated rule) · 4 minimal rewrites. **Kept:** Costco #9 (return policy),
bachmanns.com ×2. **HELD:** Costco #5–7 — they are source citations, not purchase links (see LEARNINGS).

| article | external before → after | rewrites |
|---|---|---|
| costco-sauna-guide-worth-it | 18 → 13 | 3 |
| arcadia-barrel-sauna-guide | 10 → 8 | — |
| homedics-premium-steam-sauna-review | 13 → 12 | — |
| lifetrend-cold-plunge-review | 13 → 11 | 1 |
| benefits-of-massage-chairs-for-seniors | 21 → 19 | — |
| top-fire-pits-outdoor-meditation | 18 → 17 | — |

**Site-wide:** external 3,643 → **3,630** (Δ13, as declared) · internal **1,210** unchanged (no link
added) · institute **2,047** unchanged · costco 14 → **4** · 13 withheld unchanged · citation spot-check
unchanged.

**Restore proof, per CLAUDE.md, on `lifetrend-cold-plunge-review`** (both rewrite and unwrap paths):
apply → restore md5 `b73b2dd5…` == before → restore again no-op → faked edit REFUSED (exit 1) → full apply.
Backup: `data/backups/2026-09-18T02-42-34-077Z/r18d-edit.json`.

**Rendered:** all six pages as intended; the four new sentences live; the three originals absent.

**Substitution candidates (item 8):** 73 unwrapped competitor destinations in ordinary articles
matched on vendor + model against our ACTIVE catalogue → **3**, all of them the held Costco citations.
One brand-level near-miss: saunamarketplace.com's SaunaLife brand page (no model named).

**Found while checking item 1 — a live defect:** the Costco guide's comparison table calls the Gracia
at InHouse "Exact same model" at ~$1,899 and links DYN-6119-03 FS at $2,899. The matching unit is
DYN-6119-01 at $1,999, which we stock and the article does not link.

---

## Round 18c — 3dmassagechair unwrapped; general retailers classified by linked URL. 1 LIVE EDIT.

**Executed:** decision 1 only — the single ordinary-article `3dmassagechair.com` link in
`massage-chairs-office-workers`. **Costco and the general-retailer class are REPORTED, not cut**:
the brief asked to see destinations before cutting, and the DONE list confirms one removal.

| | R18 start | R18c start | now |
|---|---|---|---|
| external | 3,730 | 3,644 | **3,643** (Δ1) |
| internal | 1,210 | 1,210 | **1,210** |
| institute external (control) | 2,047 | 2,047 | **2,047** |
| 3dmassagechair.com | 9 | 9 | **8** (all institute) |
| costco.com | 14 | 14 | **14** (untouched) |
| 13 withheld | — | — | **all unchanged** |

**Restore proof, full sequence, on the real target:** apply → restore (md5 `3830ddba…` ==
before-state) → restore again (no-op) → faked third-party edit **REFUSED** (exit 1) → re-apply.
**And the stacked-round guard:** the 18b restore on this article now REFUSES, so the two rounds
can only be undone in reverse order.
Backup: `data/backups/2026-09-18T02-34-23-655Z/r18c-unwrap-3dmassagechaircom.json`.

**Rendered:** 0 `3dmassagechair.com` hrefs on the live page; the URL survives as plain text.

**General retailers — 4 domains, 18 links, all ordinary, 0 institute:**
costco.com 14 (13 REMOVE / 1 KEEP) · homedepot.com 1 (CALL — fire pit) · rcwilley.com 1
(REMOVE — massage recliners) · bachmanns.com 2 (KEEP — maintenance guide).

**Counts in the brief:** `costco-sauna-guide-worth-it` holds **9** Costco links, not 4.

**Friction:** the classifier's own self-test silently never ran (spaces in the repo path), and
its normaliser erased the `.product.` marker. Both caught by fixtures, neither by reading.

---

## Round 18b — T1 competitor links unwrapped in 23 ordinary articles. LIVE.

**This is a live content edit, not a theme change.** Article bodies have no preview theme; the
brief's "live content edit across 24 articles" acknowledged that, and the proven restore path is
the safety net. MAIN theme untouched.

**Institute blog excluded entirely** (client ruling: the section is being removed) — **6 articles,
not 5**: `plunge-immune-function` carries 1 T1 link beyond the five Sources pages. So the edit set
is **23 articles / 84 links**, not 24 / 85, **plus 2** `lifeprofitness.com` links hand-classified T1
this round = **86 anchors**.

| article | external before | after | T1 unwrapped |
|---|---|---|---|
| `are-infrared-saunas-safe` | 49 | **33** | 16 |
| `dry-sauna-for-home` | 39 | **29** | 10 |
| `best-inflatable-cold-plunge-tubs` | 12 | **4** | 8 |
| `cold-plunge-maintenance-tips` | 15 | **8** | 7 |
| `home-sauna-steam-room-lifetime-operating-costs` | 34 | **28** | 6 |
| `cold-plunge-buyers-checklist` | 26 | **20** | 6 |
| `hidden-failure-points-diy-sauna-steam-projects` | 22 | **18** | 4 |
| `red-light-therapy-sauna-guide` | 8 | **5** | 3 |
| `best-infrared-sauna-muscle-recovery` | 25 | **22** | 3 |
| `sisu-sauna-review` | 10 | **7** | 3 |
| `massage-chairs-office-workers` | 19 | **16** | 3 |
| `benefits-of-massage-chairs-for-seniors` | 23 | **21** | 2 |
| `sauna-detox-science-explained` | 16 | **14** | 2 |
| `polar-monkeys-cold-plunge-review` | 20 | **18** | 2 |
| `downdraft-sauna-ventilation-design-patterns` | 24 | **22** | 2 |
| `maxxus-saunas-review-buyers-guide` | 24 | **22** | 2 |
| `costco-sauna-guide-worth-it` | 19 | **18** | 1 |
| `top-fire-pits-outdoor-meditation` | 19 | **18** | 1 |
| `thermal-stress-hormetic-window-human-studies` | 24 | **23** | 1 |
| `how-float-tanks-improve-sleep-quality` | 18 | **17** | 1 |
| `what-is-a-german-sauna` | 19 | **18** | 1 |
| `lifetrend-cold-plunge-review` | 10 | **9** | 1 |
| `golden-designs-saunas-review` | 17 | **16** | 1 |

**Site-wide:** external 3,730 → **3,644** (Δ86, exactly as planned) · internal 1,210 → **1,210** ·
institute 2,047 → **2,047** (control held) · 13 withheld domains **all unchanged**.

**Verified from the RENDERED storefront article**, not the API: 23/23 zero T1, withheld counts
equal, none redirected. Visible text byte-identical on all 23 — no prose touched.

**Restore — proven before the full apply, on a real article:** applied to
`lifetrend-cold-plunge-review`, restored, read-back md5 `dd130bc4…` **== before-state**, a second
restore was a no-op, and a faked out-of-band edit made the restore **refuse** (exit 1). Then the
full apply ran. Backup: `data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json`.

```bash
node scripts/apply/r18-restore.mjs data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json            # dry run
node scripts/apply/r18-restore.mjs data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json --apply    # all 23
node scripts/apply/r18-restore.mjs data/backups/2026-09-18T02-20-15-007Z/r18-unwrap-t1.json --only <handle> --apply
```

**Out of scope, flagged, untouched:** `costco.com` 14 links in 4 ordinary articles (probe
false-negative — see LEARNINGS); `3dmassagechair.com` 1 link (Real Relax's content blog, no
cart — a relationship call); 50 bot-blocked domains stay REVIEW.

**Friction:** three of the brief's counts (24, 85, "six withheld" naming seven) disagreed with the
data. None changed the work; each would have, had I edited to the stated number.

---

## Round 18 — outbound competitor classification. NOTHING EDITED. Gated on your approval.

**Read as a show-me gate: the brief says "EXECUTE (after the T1 list is approved)". No article
was touched, no theme created.**

### PRE-STATE SNAPSHOT — 2026-09-18, live Admin API (data/r18-prestate.json)

| | |
|---|---|
| live articles | **120** |
| total external links | **3,730** |
| distinct external domains | **398** |
| articles carrying ≥1 external link | **102** |
| total internal links | **1,210** |

3,730 vs Round 17's 3,664 = exactly the **66 bare URLs inside JSON-LD**, which an `<a href>`
probe cannot see.

| context | links |
|---|---|
| inline prose | 3,368 |
| **TABLE CELL** | **296** |
| JSON-LD | 66 |
| button / CTA | **0** |
| image wrapper | **0** |

### CLASSIFICATION

| tier | domains | links |
|---|---|---|
| **T1 REMOVE** | **54** | **356** |
| T2 keep (adjacent) | 27 | 111 |
| T3 keep (non-commercial) | 204 | 1,210 |
| MANUFACTURER — withheld | 6 | 37 |
| REVIEW — not classified | 62 | 211 |

**102 links were pulled OUT of the probe's T1 before it was shown.** The probe put
`goldendesigninc.com` (26 links) in T1; it is the MANUFACTURER that warrants the Dynamic and
Maxxus units we sell, and CLAUDE.md already records that exact domain being misclassified as a
competitor once before. Also withheld: `globalwellnessinstitute.org` (40, industry body),
`ndnr.com` (10, journal), `medicalsaunas.com`, `dream-pod.com`, `almostheaven.com`, `homedics.com`.

### Concentration

**Five `institute`-blog Sources pages carry 271 of the 356 T1 links (76%).**
`dynamic-santiago-ultra-low-emf-sauna-sources` alone carries 140, of which 28 are table cells.

### Two probe failures caught by their own guards

1. **Known-positive block.** `hightechhealth.com` — which you named as T1 — scored
   `cart=5, cats=[sauna,infrared], price=0` and my rule required a price, so it fell to T3.
   It is a **quote-gated seller**, the Sunlighten shape CLAUDE.md already documents. My
   fixtures did not include that class.
2. **Vendor cross-check near-miss.** Matching T1 domains against our own 41 vendor strings
   caught `dream-pod.com`, `dynamicsaunasdirect.com` and `medicalsaunas.com` and **missed
   `goldendesigninc.com`** — the domain drops the `s` in "Designs", so the substring test
   failed on the single most important row.

---

## Round 17 — Skimlinks verification tag. NOT PUBLISHED.

**Theme `146351784003` — "Round 17 — Skimlinks verification tag (TEMPORARY)", UNPUBLISHED.**
Preview: https://inhousewellness.com/?preview_theme_id=146351784003
Theme slots: **13 of 20 used, 7 free** at start; 14 of 20 used, 6 free after.

| item | outcome |
|---|---|
| tag before `</body>` in `layout/theme.liquid` | ✅ 1 occurrence, markers both ends |
| MD5 read-back | ✅ `7bf6856331e4f44d1a2021e7cf3b7846` byte-identical |
| raw served HTML (curl, no JS) | ✅ present on home, article, product, collection, page |
| differential vs MAIN | ✅ preview 1, MAIN 0 |
| `avadaLightJsExclude` | ✅ not added; string absent from the file entirely |
| MAIN contaminated? | ✅ no — md5 unchanged at `6022499a30fa37837cd114a35d61151a` |
| outbound-link audit | report only, nothing changed |

**🔴 THE PROMPT'S MAIN ID WAS STALE, AND IT WAS NOT A HARMLESS ERROR.** The brief said MAIN is
`146290704451`. **MAIN is `146318491715`** — the Round 15 theme, which the client published after
Round 15 closed. `146290704451` is Round 14 and is now UNPUBLISHED. Duplicating the id as given
would have branched from a theme that predates Round 15, and **publishing that branch would have
silently reverted the server-rendered `aggregateRating` and the gtin quoting fix.** Caught by
querying theme roles instead of trusting the id. `theme-branch.mjs` resolves MAIN by role, so the
tooling was already immune; the reasoning was not.

**And the client's article count was right where my dump was wrong.** The brief said 120 articles;
`data/content.json` holds 118. The live store has **120** — `are-saunas-good-for-you` and
`how-often-should-you-use-sauna` postdate the dump. The audit was re-pointed at the live API. The
usual direction of this rule is reversed: here the artefact was stale and the instruction was current.

**Friction:** `themeDuplicate` took ~4 minutes to copy 575 files and reported 36 at first poll.
Curling the preview before it completed would have tested a half-built theme.

---

## Round 16 — two comparison drafts. NOTHING PUBLISHED.

`content/drafts/infrared-vs-traditional-sauna.html` (37,341 chars)
`content/drafts/infrared-vs-steam-sauna.html` (36,385 chars)

Draft only. No article created, no Admin API write, no theme touched. Anthropic spend $0.

| phase | outcome |
|---|---|
| Cannibalisation audit | 1 real overlap: `dry-sauna-for-home` holds its own "Infrared vs Traditional" section. Trim is a **publishing precondition**, not done this round |
| Data inventory | accepted; then **re-derived and nine figures moved** — see LEARNINGS |
| Drafts | written, swept, committed `3f19ce3` |
| GSC for `dry-sauna-for-home` | **BLOCKED — unobtainable from here.** Open on the client's side |

**Verification, all re-run after the final edit:**
`r16-verify-drafts.mjs` (8 constructed fixtures, structure, links, FAQ 1:1, anchors) ·
`r16-claims-vs-data.mjs` (17 figures re-derived; all match) ·
the repo's own `health-claim-screen.mjs` imported and run over both drafts: **0 assertions,
0 property claims.** 31 internal links resolved against real data; none retyped.

**Friction:** the correction script refused four times, every refusal caused by a `from`
string typed from memory rather than extracted. Extracting first would have cost one command.

---


## Round 15 — server-rendered aggregateRating, H1, telephone, nav-bar. NOT PUBLISHED.

**Theme `146318491715` — "Round 15 — server-rendered rating, H1, telephone, nav-bar", UNPUBLISHED.**
Preview: https://inhousewellness.com/?preview_theme_id=146318491715
Free slots at start: **8 of 20** (the client had deleted superseded round themes).

**7 files, all MD5-verified byte-identical in the theme.** 14/14 post-build checks, 19/19 rendered
preview checks, 6/6 template types structurally valid.

| item | outcome |
|---|---|
| `aggregateRating` server-side | **3 sections**, not 1 — see below |
| Organization `telephone` | on the node and the ContactPoint, E.164 |
| Organization `aggregateRating` | **4.82 / 1431, read live from shop metafields** |
| homepage H1 | logo → `div`, hero → `h1`, both guarded to `index` |
| nav-bar render error | gone; the redundant direct call removed |
| Font Awesome | link removed, two icons inlined as SVG |
| jQuery | **deliberately left** — see HANDOFF.md |

### Two enumerations changed the scope, both toward more work

**THREE sections emit the Product node** — `main-product`, `bundle-product`, `main-product-layout-2`.
**84 ACTIVE products sit on `product.Bundle.json`, 32 of them with ratings.** Editing only
`main-product.liquid` would have shipped the rating to 396 products and silently missed 84. That is
the Round 9 template-partition failure, and the validation now covers both Bundle branches — one
rated (`ct-georgian-cabin-sauna`, 4.6/5) and one not (`huum-hive-12`, guard holds).

**`image-with-text-overlay` renders on `index` AND on the featuredexperts template**, which has a
live page at `/pages/featured-experts-consultants`. An unguarded `h2`→`h1` would have put a second
H1 there. The promotion is guarded to `index`; verified the hero stayed an `h2` on that page.

### Four errors of mine, all caught before the client saw them

1. **`git checkout -- theme/` reverts NOTHING** — `theme/` is gitignored, the command exits
   non-zero, and I read a failed revert as a successful one. Re-running the build then inserted a
   **second `aggregateRating` block** into `layout/theme.liquid`, because that edit re-emits its own
   anchor. `scripts/apply/theme-pull.mjs` now restores from MAIN with MD5 proof, and the build
   carries an **idempotency guard proved to refuse a second run**.
2. **`{%- comment -%}` inside a `{%- liquid -%}` block is a syntax error.** Shopify refused the file
   rather than accepting it — the push failing was the correct outcome.
3. **My MD5 verifier declared `$n` and passed `names`.** The filter never bound, the query returned
   the first 25 files alphabetically, and all 7 targets reported "(absent)" against a theme that
   held them correctly. **A false negative — the safe direction, but a broken verifier.**
4. **I derived a page URL from a template name** and got a 404 with 0 H1s, which read as a
   regression. The handle is `featured-experts-consultants`. Identifiers come from the data.

### And the duplicate was still copying when I first pushed

`themeDuplicate` is asynchronous. At first push the branch held **175 files against MAIN's 575** and
was still growing. Polled to 575/575, then re-pushed and verified. **A branch short of the live
theme is a broken preview, not a draft** — and a file pushed into a still-copying duplicate can be
overwritten by the copy.

### Not done, and not claimed

- **Google's Rich Results Test was NOT run.** It has no public API. What was run is structural
  validation: JSON parses, one Product node per page, `AggregateRating` well-formed and in range,
  on all six template types. **Google's verdict needs a human paste.**
- **Search Console was not read.** The "33 valid Review URLs, zero invalid" figure could not be
  re-derived from here, so it is carried as the client's number, not confirmed.
- **Hyperspeed caches aggressively.** After the client publishes, a cache rebuild is likely needed
  before the changes are visible on the live domain.

## Round 15b — gtin quoting. Theme 146318491715, still UNPUBLISHED.

Client's Rich Results check found a pre-existing bug that nullified Round 15 on 31 products.
9 edits across the 3 Product emitters, 3 files MD5-verified byte-identical.

**Blast radius, measured 478/478 from the public storefront:** 270 products emit a gtin; **30 have
a leading-zero barcode and 1 is non-numeric**; **31 published products had their whole Product node
discarded**; **24 of those were rated and ACTIVE — 13.1% of the ACTIVE rated set.**

**Verified on fixtures chosen to break the property**, not clean samples:

| fixture | why it was chosen | result |
|---|---|---|
| `dynamic-venice-elite` | leading-zero barcode, the reported case | parses · `gtin12` `"019962854569"` **as a string** · aggregateRating **4.93/15** · offers intact at 2699 |
| `huum-hive` | **U+2011** non-breaking hyphens | parses · `gtin13` `"537‑AZ‑128267"` |
| `maxxus-3-person-sauna-hemlock-ultralow` | **the only Bundle-template product that is both affected and rated** | parses · aggregateRating **4.5/20** |
| `laguna-q-gpv3100-outdoor-island` | no reviews | aggregateRating **absent** — guard holds |

Round 15's work confirmed intact: **aggregateRating exactly once in all three emitters, raw gtin
zero, quoted three** — read back from the theme, not from local files. All 19 rendered preview
checks and all 6 template-type validations still pass.

**Themes: 13.** The 12 that existed before this round plus `146318491715`. MAIN is unchanged at
`146290704451`. **Nothing was created that I did not create.** (The t/NN in asset paths is
Shopify's creation counter, not a theme count — client's correction, noted.)
