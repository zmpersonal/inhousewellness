# CLAUDE.md — InHouse Wellness social content engine

Governed by, in order: `agent-harness` (meta-rules, tiers, Slack protocol,
learning loop) → `social-autoposter` (the 21-step SOP) → **`docs/autoposter-adjustments-inhousewellness.md`**.

**The adjustments doc overrides the skill wherever they conflict.** It encodes
fixes for 81 structurally broken posts and 15 months of measured failure in the
live account. Where it contradicts the skill, the adjustments win. Where it is
silent, the skill governs.

Read this file, `RUNLOG.md` and `HANDOFF.md` before doing anything.

---

## Harness config block

| Key | Value |
|---|---|
| Slack channel | *TBD-nonblocking — no channel provisioned yet; report in-session* |
| Cost ceiling | **1,750 Blotato credits** ($10.50 at $6/1,000). Flag at 80% (1,400 spent / 350 left), STOP at 100% |
| Review cadence | Every round ends 🟡 REVIEW; retro when a learning hits `validated` |
| 🟡 delegation N | 3 clean rounds before any 🟡 step may be downgraded to 🟢 (agent never self-downgrades) |
| Repo | `github.com/zmpersonal/inhousewellness` — ✅ **remote wired and pushed 2026-09-03** (21 commits). Git history audited: **no secret was ever committed**; `.env` is untracked and ignored |
| Governing docs | `docs/autoposter-adjustments-inhousewellness.md`, `docs/BUILD-HANDOFF.md` |

---

## Project brief

**Concept.** An automated content engine for InHouse Wellness — a US retailer of
home saunas and cold plunges — publishing to Pinterest, Facebook and Instagram.
Ideas come from four independent feeds: SEO keyword research, page analytics,
social performance data, and the company blog. Runs hands-off on a cadence until
explicitly stopped.

**Niche.** Home saunas (infrared and traditional), cold plunge, wellness
equipment. Store: inhousewellness.com (Shopify).

**Audience.** 40–60 year old Americans, middle to upper-middle class,
health-interested. Considered purchase, $3,000–$15,000, months-long research
window, frequently a joint decision between partners. **Not** biohackers, not a
young wellness audience. Write adult-to-adult.

**Social objective: REACH.** Not followers, not likes, not vanity engagement.
North-star metric is **monthly impressions across the three channels.**
Baseline to beat: ~11,200 total impressions across 15 months and 322 posts.
Secondary metric: **saves** — 1 recorded ever, as of 2026-09-01.
Engagement rate is already healthy (7.3% IG, 5.0% FB); **do not optimize for it.**
The bottleneck is distribution, not response.

**Primary health metric during review: broken-post rate.** Prior baseline 27%.
Target 0%. (Adjustment D2.)

---

## Per-platform cadence config (adjustment A1)

Cadence is a **map keyed by platform**, never one number, never hardcoded at a
call site. Peak historical volume was 13 posts in a single day, during the window
when 27% of output was broken.

```yaml
platforms:
  pinterest: { posts_per_day: 2, target: 4, role: compounding-search }  # THROTTLED
  instagram: { posts_per_day: 1, role: cold-reach }
  facebook:  { posts_per_day: 1, role: click-driver }
max_posts_per_day_total: 6
```

⚠️ **Pinterest is throttled to 2/day against a target of 4** (decided 2026-09-01).
Only 24 of 103 queue rows survived the remap; 79 are blocked on a content gap, not
a matcher failure. 24 rows at 4/day is ~6 days of runway; at 2/day it is ~12 —
enough to prove the pipe and start the 14-day zero-broken-post clock.

**Lift `pinterest` back to 4 when, and only when, the content gap closes.** Do not
raise it to consume the queue faster, and do not lower the match threshold to
manufacture rows: at 0.35 the matches include "infrared vs steam sauna" pointing
at a Homedics product review. Pins whose destination does not answer the keyword
are how this account got here.

### Per-platform render targets (adjustment C3)

The skill's "native 1080×1080, no scaling" rule is **wrong for Pinterest**.

| Platform | Dimensions | Ratio | Verified |
|---|---|---|---|
| Pinterest | 1000 × 1500 | 2:3 | ✅ 2026-09-01 |
| Instagram feed | 1080 × 1350 | 4:5 | ✅ 2026-09-01 |
| Instagram / Facebook Reels | 1080 × 1920 | 9:16 | ✅ 2026-09-01 |
| Facebook feed | 1200 × 630 or 1080 × 1080 | — | not yet exercised |

Every other template constraint stands: wait for `document.fonts.ready`,
auto-fit long text, self-hosted fonts (CDN fonts fail in CI).

---

## Locked decisions — do not relitigate

- **Blotato is the only posting tool.** Not Buffer for posting, not Revid, not
  Opus, not Higgsfield. Buffer stays connected **for Pinterest analytics only**,
  because Blotato does not collect Pinterest metrics and Buffer is the only
  source in the stack.
- **Blotato is the only video tool.**
- **No AI avatars or synthetic human presenters.** Voiceover (Bill or Brian),
  animation, or real footage only. A generated human making health claims to a
  40–60 US audience evaluating an $8,000 purchase from an unfamiliar retailer is
  a credibility liability, not a shortcut.
- **No trending audio.** The library must stay evergreen.
- **No brand intro card.** Two seconds of logo spends the entire hook window.
- **Design system is locked.** Palette `#1B1613` base / `#E9E5DD` type /
  `#E0A03C` heat / `#6FA8B8` cold. Fraunces 700 display, IBM Plex Sans 400/600/700
  data, self-hosted. Ticked measurement rule on the left edge of every card.
  Do not redesign. Logo pending from the user — footer slot is ready.
- **auto_publish = FALSE.** Do not flip until 14 consecutive days at zero broken
  posts (adjustment D2).

---

## Hard rules — each one traces to measured failure

- **Per-platform copy always.** 207 of 300 historical posts shared caption text
  across channels. Never generate one string for multiple platforms. Enforced by
  `validator.assert_no_shared_text`.
- **Pinterest pins need title + description + altText + link + boardId** or they
  do not perform. 75 blank pins averaged 3.0 impressions; pins with text averaged
  106.2 in the same window on the same account.
- **Facebook: link in the first comment**, never in the post body. Enforced by
  the `FB_LINK_IN_BODY` rule.
- **Health claims are code-gated, not prose-guided** (`src/health_claims.py`).
  This audience is frequently managing blood pressure and cardiac risk, and the
  machine is unattended.
- **The LLM writes copy only.** Selection, counting, dedup, gating, rendering and
  posting are CODE. This is the skill's governing principle and the reason the
  previous system failed.
- **Never publish a degraded version.** The validator raises; it has no
  "clean it up and post anyway" path.
- **A card's subject and its destination must agree** (`DESTINATION_MISMATCH`,
  Round 12). A card headlined "Traditional units cost $3,746 more than infrared"
  once pointed at a wood-durability article: every figure real, every numeral
  grounded, and the reader still arrives at the wrong question. The rule compares
  the entities the figures measure against the destination title, and fires only
  on ZERO topical overlap — it declines to judge rather than guess.

### GitHub Actions — two rules, each of which has now bitten twice

Three consecutive `fetch external data` runs failed, and every failure had the
same shape: **something that exists on the dev host was absent on the runner,
and the absence surfaced at the point of use rather than at the start of the
job.** Runs 1–2 were missing scripts; run 3 was a missing package. Run 3
refreshed all 13 datasets in 17 seconds, cleared the row floors and passed the
lint — then died on `No module named pytest` and discarded the lot.

**1. A workflow and every script it calls must land in the same commit.**
`actions/checkout` checks out the ref you dispatch on, so a workflow pushed to
`main` while its scripts sit on a branch checks out a tree without them. The
workflow appears in the Actions UI and fails at the first step. Never push a
workflow ahead of its scripts to make it *visible* — visible and runnable are
not the same thing, and the gap between them is a run that cannot succeed.
Enforced by `scripts/preflight.py --workflow-paths`, which asserts every `.py`
any workflow names exists in the checkout, and by `tests/test_preflight.py`.

**2. `requirements.txt` is the only declaration of what this repo needs.**
No workflow may carry a hand-written package list. `autoposter.yml` used to
pip-install `python-dotenv anthropic imageio-ffmpeg` on a second line, which put
the correct dependency list inside one workflow instead of the manifest — so the
two fetchers, which install from `requirements.txt`, could not inherit it. Same
failure mode as a cadence number hardcoded at a call site, and the same fix:
**one place, and code that asserts nothing has drifted from it.**
`scripts/preflight.py --deps` walks the AST of `src/`, `scripts/` and `tests/`
and fails on any third-party import the manifest does not declare;
`--imports` then proves the install actually delivered them. Both run in every
workflow, and `--deps` runs in the ordinary suite, so an undeclared import fails
on a laptop rather than after a fetch.

**Corollary — a "nothing is installed here" proof is environmental, not an
invariant.** Two workflows proved their script was stdlib-only by running it on
a bare interpreter before any `pip install`. That is true only while the job
happens to install nothing, and it stopped being true the moment
`fetch-manufacturer-specs.yml` needed pytest. Scripts that reach outside this
repo — the manufacturer crawler, the shared power parsers, the Shopify theme
probe — are listed in `preflight.STDLIB_ONLY` and asserted by AST instead.

### Gate placement: before the expensive work, not after it

**A gate belongs at the earliest point where it can be evaluated.** Partition
gates by what they actually depend on, and run each as early as its inputs allow:

| Depends on | Runs | Examples |
|---|---|---|
| the repo only | **before** the fetch | preflight, `pytest tests/`, the missing-value lint, secret presence |
| the fetched bytes | **after** the fetch | `scripts/check_facts_cache.py` |

The fix for "a test-runner problem discarded a good refresh" is **not** to move
the commit ahead of the test gate — that would land data produced by a tree the
run believes is broken, and this project's validator has no "clean it up and
post anyway" path. The gate was misplaced relative to the **fetch**, not
relative to the commit. Moving it earlier costs nothing, and it buys the
property that was missing: a failure *after* the fetch is now attributable to
the fetch, so discarding the refresh is the correct response rather than an
accident.

Two supporting rules:

- **Never weaken a gate to get a green run.** The reordering above made the
  post-fetch gate stricter, not looser — it now also asserts each dataset
  parses, carries a `fetched_at`, and that `row_count` agrees with `len(rows)`.
- **A halt must not destroy the evidence.** Fetched data uploads as a workflow
  artifact under `if: always()`, so a rejected refresh stays inspectable and a
  crawl of other companies' servers is never repeated merely to see what it
  found. The gate still blocks the commit.

**No workflow logic in a heredoc.** The row floors and the shrink check lived as
~40 lines of Python inside `fetch-external-data.yml`, where pytest, the lint and
preflight could all not see them — data at a call site, and logic no test
covered. Anything with a rule in it is a script in `scripts/`, with a
`--self-test` and a test file.

### Never assert a literal value from refreshed external data

`tests/test_validator.py::test_source_data_grounding_round_trips` asserted that
`"90"`, `"71"`, `"46"` and `"34"` appear in the EMF grounding text. On 2026-09-15
besthomeinfraredsauna republished its index — two Dynamic models retired, one
duplicate record resolved — so 90 models became 87 and 71 *Near Zero EMF* labels
became 68. **The source was right, the refresh was right, and the test failed**,
in the Sweep step of `fetch manufacturer specs`, blocking a crawl that has
nothing to do with EMF labels.

A test that pins a literal from data we re-fetch will fail on some future
refresh. That is not a risk to manage; it is a scheduled outage. So:

| Assert | Where | On failure |
|---|---|---|
| **shape** — the block resolves, the fields we named are present | the suite (blocking) | red build, correctly: our code broke |
| **provenance** — `fetched_at` and `url` are present | the suite (blocking) | red build: an undated figure cannot be cited |
| **extractability** — every number in the block is reachable by the grounding walker | the suite (blocking) | red build: Round 6's bug, where `UNGROUNDED_NUMERAL` rejected the model for citing numbers that lived in key names |
| **internal consistency** — a filtered count never exceeds its source set | the suite + `check_facts_drift.py` | red build: impossible, so it is corruption |
| **content** — the values themselves | `scripts/check_facts_drift.py`, post-fetch | **a reported finding, exit 0** |

`scripts/check_facts_drift.py` compares derived facts against
`data/facts-baseline.json`, prints every moved metric with its percent change to
the run summary, and **halts only on something no publisher edit can produce**: a
subset larger than its superset, an unordered min/median/max, a negative count,
two clusters disagreeing on one file's row count, EMF labels covering under half
the index, a metric collapsing to zero or vanishing from the schema, or a move
beyond tolerance in **both** relative and absolute terms.

Two details that matter:

- **The baseline is updated only by an explicit `--accept`.** The fetcher commits
  a refreshed cache and leaves the baseline alone, so a publisher's edit is
  acknowledged by a human instead of absorbed silently. A drifted baseline is
  therefore the normal state between a refresh and an `--accept`, and **no test
  may assert drift-freedom** — only breach-freedom. Asserting `drift == []`
  rebuilds the original bug one layer down.
- **A percentage alone is not evidence at small n.** A four-model voltage group
  cannot change at all without moving 25%, so a breach needs the absolute move to
  exceed `MIN_ABS_MOVE` as well. Same rule as the feedback loop's 30-post minimum
  and the destination audit's n ≥ 25 threshold.

**The tradeoff, stated plainly.** A change that preserves shape while destroying
meaning — the publisher renaming *Near Zero EMF* to something else, collapsing
that count while the row count holds — no longer turns the build red. It is
caught instead by the collapse-to-zero halt and the 50% label-coverage floor, and
otherwise appears as a drift finding that someone has to read. That is a real
loss of automatic enforcement, accepted because the alternative is a gate
guaranteed to fire on correct data, in an unrelated pipeline, at a time nobody
chose.

### Tier 1 manufacturer specs: a template needs two pieces of evidence

`data/manufacturer-registry.json` carries `product_url_template: null` for all 11
vendors, and discover run 3 (2026-09-15) did not change that. The run succeeded
across every vendor in 1m38s and reported robots.txt status and homepage
reachability — **and nothing about product URLs**, because as written it requested
only `/robots.txt` and `/`. Those do not contain a URL pattern. Filling a template
from that would have been writing from memory.

**A template may only be set when the discovery file shows BOTH:**

1. `sample_product_urls` — real URLs the vendor publishes, so the path shape is
   observed rather than assumed;
2. `sku_matches` — at least one of those real URLs containing one of **our** SKUs,
   so there is something to substitute.

`product_urls_seen > 0` with `sku_matches` empty means their URLs are keyed on
something we do not hold. That is a finding, not a licence to guess.
`tests/test_manufacturer_discovery.py` enforces both, and asserts that
`/collections/…` is never accepted as a product path — that exact page once
answered a product request and put a category FAQ into a report as a product
specification.

**Two open design faults, neither fixed:**

- `product_url_template.format(handle=handle)` substitutes **our** Shopify handle
  into **their** URL space: `arosa-4p-barrel-sauna`,
  `hand-finished-precut-sauna-kit`. Those are our store's marketing slugs. Even a
  correct path shape would request pages that cannot exist.
- Every vendor row declares `model_key` (`sku` for 9 of 11, `title` for Medical
  Saunas) and the fetcher **never reads it**. The registry states the right idea
  and the code ignores it.

Until both are settled, a per-vendor SKU→URL index built from sitemap evidence is
the likelier mechanism than a format string. Do not run `mode: fetch` before then.

**Politeness note:** the fetcher skips any host whose robots.txt is unreadable,
including a 404. RFC 9309 §2.3.1.3 says a 404 means a crawler *may* access any
resource, so this is stricter than the standard and costs us Dundalk Leisurecraft
(7 SKUs). Deliberate, recorded in the discovery output as a note, and a human's
call to change — not a bug to fix in passing.

### A gate must know what it is looking at

`data/facts/` holds two kinds of artifact: row **datasets** (`rows` +
`row_count`) and **reports** (`manufacturer-discovery.json`, keyed on `vendors`,
which has no rows and never will). The first version of
`scripts/check_facts_cache.py` assumed every file there was a dataset and failed
with *"has no rows list"* the moment the discover run committed that report —
breaking the Sweep step of **both** fetchers on a perfectly correct file.

The kind is now decided by **shape, not a filename list that would go stale**:
carrying `rows` or `row_count` makes it a dataset and it gets the full checks;
carrying neither makes it a report, which must still parse and carry a
`fetched_at`. Carrying one of the pair without the other is neither — that is
corruption and it fails.

Same lesson as the EMF literal and the drift baseline, a third time: **a gate that
fires on correct data costs more than the gate is worth.** When a new artifact
lands in a directory a gate scans, the question is always "does this gate know
what kinds live here", not "does this file satisfy the one kind I had in mind".

### The manuals are on OUR pages, as Google Drive embeds — check there first

Phase 1 censused all 165 active sauna SKUs with **zero egress to any vendor**,
reading `descriptionHtml` and every metafield from an Admin API pull.

**The brief assumed a "Download Manual" PDF link. There are none.** Every
document reference on this store is a Google Drive `iframe` in
`custom.product_documents`. A census grepping the body for `.pdf` would have
reported ~0% and been precisely, confidently wrong.

**The field a reference sits in decides what it is.** 35 of the first 180 Drive
embeds found were in `custom.video`. Counting those as manuals put coverage at
106/165 when the documents field alone gives **102**. Role is assigned from the
source field (`DOC_FIELDS` / `VIDEO_FIELDS`), never from "it is a Drive link".

**The 2×2, not a single rate** (all 165 active sauna SKUs):

| | manual on our page | no manual |
|---|---|---|
| **model number** | 13 (7.9%) | **19 (11.5%)** — vendor URL constructible |
| **no model number** | 89 (53.9%) | **44 (26.7%)** — the honest floor |

**A model number must survive the field it sits in.** These metafields pack
several facts on one line (`Brand: … Model: MX-K406-01 CED Capacity: 4 Person`).
A capture requiring terminal punctuation found the model in a rich-text block and
nothing at all in a flat field — one fact, two answers, decided by storage
format. `MODEL_RX` now terminates at a following `Label:` too, and
`trim_to_part_number` walks trailing tokens back until what remains is a part
number, so `MX-1 is the best sauna` still yields `MX-1` while `8 kW heater`,
`6 persons` and `Heming Edition` yield nothing. Two bugs found writing it, both
pinned by tests: `(?i)` made the `[A-Z]` label terminator match lowercase, and a
three-character floor on lowercase words let `is` through.

**Manuals are read, never guessed.** `scripts/extract_manual_specs.py` imports
both guards from `src/power_parse.py` — the comma-aware parser that caught
"1,800 watts" as 800 W, and the 0.8–30 kW band. It adds two rules of its own:

- **A recommendation is not a rating.** "An 8 kW electric heater is recommended"
  states what to *buy*, not what the unit draws. Recorded as rejected, with span.
- **A spec plate outranks marketing copy.** A reading whose span carries rating
  vocabulary is tier `spec_plate` and sorts first; everything else is `body_copy`.
  Both are kept with page number and verbatim span.

Text layer only. A scan is `NEEDS_OCR` and nothing is inferred from it. No OCR.

**Run 1 (2026-09-15): 9 PDFs, 278 pages, 0 OCR needed, and ZERO ratings.** Drive
serves from `drive.usercontent.google.com` with no interstitial and no confirm
token, but Content-Type is `application/octet-stream`, never `application/pdf` —
**test the `%PDF` magic bytes, never the header**, or every real manual is
rejected. The only readings found were 200W / 125W / 300W **per-emitter panel
wattages** on one page; the band refused all three, and summing them would have
been derivation. **Do not widen the band to get numbers out of this.**

**A zero carries its own evidence now.** `electrical_context()` records the spans
around power vocabulary for every PDF whether or not anything parsed, plus
`chars_extracted` and a raw `text_sample` from the densest page. "The manual does
not state it" and "we could not read what it states" are different facts, and a
bare zero cannot tell them apart. Evidence sits beside a reading; it is never
promoted into one.

**Maxxus and Golden Designs do NOT share a model-number scheme in our data.**
Maxxus is `MX-` (34/34 SKUs, 9/9 model numbers); Golden Designs is `GDI-` (37 of
38 SKUs, 7/7 model numbers) plus one `DYN-`. Cross-branding exists but runs the
other way. Whether one *host* serves both is a separate question, and the
upgraded discover answers it for free by testing our SKUs against their sitemap.

### A rating belongs to the model number beside it, not to the SKU we fetched for

A manual is a document about a product **LINE**. Attributing every figure in it to
whichever SKU we happened to fetch it for published three false ratings in run 8:

- `GDI-8503-01` got **both** 6.0 and 8.0 kW from one cover line reading
  `GDI-8503-01 - 240VAC 30AMP Circuit Required (6kW Heater) GDI-8506-01 - 240VAC
  40AMP Circuit Required (8kW Heater)`.
- `CTC22LU` got 6.0 kW **five times** from a HUUM/Harvia/Homecraft **price list** —
  heaters sold separately, none of them that cabin's rating.

**THE RULE: a rating is governed by the model number that most recently PRECEDES
it in its span.** Not the nearest — on that cover the nearest token to the 6 kW is
`GDI-8506-01`, nine characters *after* it, and binding to it gives exactly the
wrong answer. Variant tables and price lists are written label-then-spec.

A rating with **no** model token before it is **UNBOUND**, and unbound means the
other guards decide exactly as before. That is deliberate: Dynamic's drawing reads
`Total power:1650W DYN-6225-02` — our model is adjacent but *follows* the figure,
and adjacency-after is a layout, not a claim.

Where the governing model is not ours the reading is **rejected** carrying
`belongs_to_model`, never left in `readings` as a second candidate value for this
SKU. The reason distinguishes two different facts, because they send a human to
different places: our model **on the same page** bound to a different rating is a
variant table; our model **nowhere on the page** is a foreign catalogue — and a
heater someone can buy separately is not this unit's rating, the same logic as
recommendation-is-not-a-rating. Where a model governs a rating and we hold no SKU
or model number at all, it is rejected as **unverifiable**: an unconfirmed
attribution is not a rating.

⚠️ The brief that prompted this said "same on GDI-8526-01", meaning 6.0. **The span
says 8.0** — on the Kaskinen cover `GDI-8523-01` carries the 6 kW and our
`GDI-8526-01` carries the 8 kW. The rule follows the document. Both spans are
controls in `scripts/extract_manual_specs.py --self-test` (so the workflow gate
fires them before any fetch) and in `tests/test_manual_specs.py`.

Two mechanics this depends on, neither optional:

- **`src/power_parse.py` records where inside the stored span the number sits.**
  The binding is decided by position, so position is recorded rather than
  re-derived by searching the span and guessing which occurrence was the reading.
- **The `MODEL_TOKEN_RX` lookbehind allows a preceding digit.** The Dundalk price
  list prints `1.00BHUDR6L` — the unit price glued to the item code — and a
  lookbehind refusing digits lost four of the five Huum listings, which would then
  have published as unbound 6 kW readings. Standards marks (`UL1026`, `CSA22.2`)
  are shaped like part numbers and are excluded by name.

### Our own limits must never be reported as the source's defects

Run 9 filed three SaunaLife manuals as `PDF_UNREADABLE`, *"Stream has ended
unexpectedly"*. All three were **exactly 30,000,000 bytes** — the number in our own
`r.read(30_000_000)`. The files were not damaged; we cut them off, handed the stump
to pypdf, and wrote its complaint down as a fact about the publisher. Same shape as
reading HTTP 429 as a dead link, as `No module named pytest` discarding a good
refresh, and as a missing census field arriving as `NO_VALUE_OF_OURS`.

The cap is now 120 MB and is read with **one byte to spare**, so exceeding it is
detectable rather than indistinguishable from a short file; an over-cap file is
`TOO_LARGE`, named with the cap, and never parsed. Run 10 read all three.

Every non-OK row now carries a `diagnosis` saying whether retrying could help:
a Google **sign-in** page means the Drive file is not shared publicly and the fix
is on our own product page; a **404** on a Drive id means the embed on our page
points at nothing. "Worth retrying or genuinely lost" is a question the record
answers, not one someone reconstructs from a run they watched.

**`data/own-page-census.json` now records `rated_power_stated`** — what OUR pages
state, through the same two guards (64 of 165 SKUs). Before it, the extractor in
`--all` scope had nothing to compare against and wrote `NO_VALUE_OF_OURS` on 132
rows, which reads as "we hold no rating for this SKU" when the truth was "this
scope never looked".

**What three full passes over ~10,500 manual pages have established:** ratings do
not live in spec plates. `spec_plate` has never once fired. The 17 accepted
readings come from an FAQ page inside an assembly manual (6), an assembly-guide
cover warning (2), and a dimension drawing (2). 90 of 135 readable manuals state a
supply spec and no rating at all. **The manual path structurally cannot close the
kW gap**, and widening a guard to make it look like it can is the failure this
project exists to avoid.

### The True Total Cost calculator — the unknown is the design, not the error path

**66.2% of priced SKUs publish no rated power.** That is the majority state, so
`assets/inh-cost-core.js` designs it first and lets the known-kW case fall out of
it. Order of resort, and there is no fifth branch:

1. the catalogue states a rating → compute from the EIA rate at the reader's state
2. it does not → **invite** the reader to read it off their own spec plate, and
   link the manual where we have a working link
3. it does not and they decline → compute everything else, and say in the total,
   in the per-session line and in a named exclusion list that running cost is out
   because the manufacturer does not publish rated power

**Never estimate from a similar model, a class average, or amperage.** A test
asserts that no combination of inputs reaches a number without a rating.

| Line | Where its figure comes from |
|---|---|
| purchase price | Shopify Admin API |
| delivery | three flat tiers, `$0` / `$600` / `$1,800` — never weight-derived |
| electrical | **the reader's own electrician's quote**, or excluded. Never published |
| foundation, maintenance | no source publishes either: reader's figure, or excluded |
| running cost | `kW × hours × sessions × 52 × state rate`, the formula published 2026-09-09 |

Three rules the round added, each with a test:

- **A zero is a measurement or an absence, and never both.** The rendered total
  read *"$4,099.00 once, plus $0.00 a year"* while BOTH recurring lines were
  excluded — a zero standing in for two figures nobody holds, at 2.4rem.
  `per_year_usd` is now `null` when nothing recurring is known and the page says
  so in words; a reader who **types** zero still gets a real `$0.00`.
- **Delivery shows even when it is free.** `$0 curbside — included in your price`
  beats hiding the line: a hidden line is indistinguishable from an unaccounted one.
- **A manual link is offered only where the PDF actually read.** The five Drive
  sign-in pages and the one dead id are left out; a link we know is broken is
  worse than none.

**The missing-value lint now scans the rendering path**, not only the data.
`assets/*.js`, `sections/*.liquid` and `templates/*.liquid`, for the browser's own
idioms for the same failure: a literal default on `||` or `??`, Liquid's
`default:` filter with a number, and a numeric coercion with no finiteness check
nearby — **`Number("")` is `0`**, which turns an empty quote box into a free
electrician. Inline `/* missing-ok */` where a guard genuinely sits one level up.

**An unresolved ZIP is a coverage gap, and three ZIPs fail three different ways.**
No ZCTA (PO-box and single-building ZIPs), 137 that straddle a state line and so
have *two* rates, and 149 in US territories with no EIA row. The national average
and the ten census-division aggregates ship under `energy.non_fallback_reference`
so the methodology page can print them and explain that they are unused; a test
asserts no render-path file reads that key. The ZIP table is range-compressed
33,505 → 10,659 ranges, **proved lossless against every key AND proved not to
swallow the gaps between them** — a range that absorbs a gap turns "we cannot say"
into a neighbour's state.

### Deploying to a theme: the section must land before the template that names it

Upserting `templates/page.sauna-cost.json` into a theme that does not yet hold
`sections/true-total-cost.liquid` is refused by Shopify:

```
FILE_VALIDATION_ERROR: Section type 'true-total-cost' does not refer to an
existing section file
```

Found by trying it against the real store on 2026-09-15, not inferred. In one
batch the templates are validated before the section has landed, so the deploy
fails on its last files and leaves a theme holding code and none of the pages
that use it. `scripts/deploy_theme_files.py` therefore upserts in **two passes** —
sections and assets, then templates — halts if the first reports an error rather
than compounding it, and **reads every file back and compares sizes** before it
says a word about having deployed anything.

⚠️ **`workflow_dispatch` only surfaces workflows that exist on the DEFAULT branch.**
`.github/workflows/deploy-theme.yml` is on the round branch with its scripts, per
the same-commit rule — and is therefore not dispatchable until the branch merges.
That is not the same failure as pushing a workflow ahead of its scripts, and the
fix is the merge, never a workflow pushed to `main` alone.

⚠️ **The two JSON assets cannot travel the MCP connector.** 405 KB (214 + 269 KB
base64) is past the point where relaying a file through an agent's own output is
either affordable or verifiable. The Admin-API path in Actions is the only route
for them, which is the same outstanding item Round 0 recorded as §5.

### ⛔ Facebook Groups stay manual — never automate (adjustment D3)

The strongest untapped channel for this demographic is genuine participation in
health-condition and home-renovation Facebook Groups — perimenopause, cardiac
health, chronic pain, sleep, home renovation.

**Automating that will get the accounts banned and burn reputation permanently.**
It is a manual daily human task, permanently outside the machine. A future agent
must not helpfully wire it in. This is not a backlog item; it is a prohibition.

---

## Kill-switch criteria (adjustments A4 + D2)

Any of these re-gates the system to `auto_publish=false` automatically, in the
workflow, and emits 🔴 BLOCKED:

1. Any post published with empty or under-length (< 50 char) text
2. Any post text matching an error pattern (`Error:`, `Failed to load`,
   `undefined`, `null`, `No response`, …)
3. Any Pinterest pin published without title, altText, or destination link
4. Any banned health claim reaching a live post
5. Any post exceeding a platform character limit
6. Any factual error or platform warning
7. Blotato credits at 100% of ceiling
8. A D5 duplicate-post breadcrumb found at start of run

Re-gating is enforced in code, not prose. A human clears it after investigating.

---

## Tooling status — verified 2026-09-01

| Item | Status |
|---|---|
| Blotato subscription | ✅ active, plan `starter`, `accounts@inhousewellness.com` |
| Blotato Facebook | ✅ account `49743`, page **InHouse Wellness** `472026422664772` |
| Blotato Pinterest | ✅ account `9630` (`inhousewellness`) — **now authorized** (adjustments doc said missing) |
| Blotato Instagram | ✅ account `68734` (`inhouse.wellness`) — **now authorized** |
| Blotato credits | 1,750 at check-in; 1,620 after the 5 credit-burn test renders |
| Buffer | ✅ org `681037367954398ece80de72`, 3 channels connected (IG, Pinterest, FB) |
| Buffer plan limit | ⚠️ free: 3 channels, 10 scheduled posts, **insights capped at last 31 days** |
| Render environment | ✅ Playwright **1.49.1** in `.venv` (see below) |
| `EIA_API_KEY` | ✅ present 2026-09-03 — 5,000 rows cached (state × month residential price, 2015→2026-06) |
| `CENSUS_API_KEY` | ✅ present 2026-09-03 — 52 rows cached (ACS 1-year housing stock by state) |
| `FRED_API_KEY` | ✅ present 2026-09-03 — 138 rows cached (US avg $/kWh, monthly since 2015) |

### ⚠️ Playwright version is pinned for a reason

This host is macOS 13 (Darwin 22.6). Current Playwright **refuses to install on
mac13** (`Playwright does not support chromium on mac13`). Playwright `1.49.1`
works against the already-cached `chromium-1148`. `requirements.txt` pins it.
Do not upgrade on this host. CI (Linux) may use current Playwright.

### Pinterest boards (live IDs)

| Board | ID |
|---|---|
| Social | `902690387751301590` |
| The Sauna Shop | `902690387751719051` |
| Wellness At Home | `902690387751256709` |
| Products | `902690387751254421` |

The keyword queue references 6 board names that do not exist under these 4.
Board creation is an open item.

### Media path — verified

`blotato_create_post` takes `mediaUrls` as **public URLs**. Locally rendered PNGs
are not public, so the path is:
`blotato_create_presigned_upload_url` → HTTP `PUT` raw bytes → use the returned
`publicUrl` in `mediaUrls`. Base64 `data:` URIs are **not** the path here,
contrary to the skill's step 9. Visuals from `blotato_create_visual` come back as
public URLs already and need no upload.

---

## Credit economics — measured 2026-09-01 (adjustment A3)

Measured empirically by checking the balance before and after each render.
**Local Playwright card renders cost 0 credits** — only Blotato-side generation bills.

| # | Template | Output | Credits | USD |
|---|---|---|---|---|
| 1 | Whiteboard Infographic | 1 static image | 50 | $0.30 |
| 2 | Tutorial Carousel, Minimalist Flat | 7 slides | **0** | $0.00 |
| 3 | When X then Y Text Slideshow | 5-slide MP4, 2 AI images | 30 | $0.18 |
| 4 | Image Slideshow with Text Overlays | 3-slide 9:16 MP4, 3 AI images | 45 | $0.27 |
| 5 | AI Story Video + AI Voice (Brian), no animation | 3-scene 9:16 MP4 + voiceover | 45 | $0.27 |
| — | Local card render (`scripts/render.py`) | any size PNG | **0** | $0.00 |

**Total for the 5 tests: 170 credits ($1.02). 1,580 remaining.**

Two findings that decide the format mix:

1. **AI generation is what bills; layout is free.** Anything that generates an AI
   image or voiceover costs 30–50 credits. Deterministic HTML-template carousels
   cost **0**, and local Playwright card renders cost **0**.
2. **Only the free paths can carry the locked design system.** The Tutorial
   Carousel accepted `#1B1613` / `#E0A03C` / `#E9E5DD` exactly. The 50-credit
   Whiteboard Infographic rendered a photoreal whiteboard in primary colours —
   accurate and legible, but no palette, no type scale, no ticked rule. **Paying
   more buys less brand.**

### Runway, at 1,580 credits

| Mix | Burn | Runway |
|---|---|---|
| All static cards local; Reels 3/week via AI Story Video | 135/wk | **~11.7 weeks** ✅ |
| All static local; Reels 4/week | 180/wk | ~8.8 weeks ✅ |
| All static local; Reels daily | 315/wk | ~5.0 weeks ❌ |
| IG + FB daily via Blotato AI, Pinterest local | 630/wk | ~2.5 weeks ❌ |
| All 6 posts/day via Blotato AI templates | 1,890/wk | **~6 days** ❌ |

**Standing rule: render every static card locally. Spend credits only on Reels,
capped at 4/week.** That is the only mix clearing the 8-week runway threshold.

⚠️ **Unmeasured:** `animateAiImages: true` on the AI Story Video template was not
tested. Adjustment A3 flags animation as materially more expensive. Measure it
before enabling it, not after.

---

## Template allow-list (adjustment C7)

| Pillar | Template | ID |
|---|---|---|
| The Correction | When X then Y Text Slideshow | `/base/v2/images-with-text/c9892c3b-fa75-4ade-821a-a50ff8456230/v1` |
| The Measured Number | AI Story Video with AI Voice (Bill or Brian, **no face**) | `/base/v2/ai-story-video/5903fe43-514d-40ee-a060-0d6628c5f8fd/v1` |
| The Reality Check | Tutorial Carousel — Minimalist Flat | `/base/v2/tutorial-carousel/2491f97b-1b47-4efa-8b96-8c651fa7b3d5/v1` |
| The Evidence Read | Whiteboard Infographic | `ae868019-820d-434c-8fe1-74c9da99129a` |
| The Evidence Read (alt) | Book Page Infographic | `b88c8273-6406-48c6-85e7-096119aefe30` |
| Product context | Product Scene Placement | `f524614b-ba01-448c-967a-ce518c52a700` |
| Pinterest workhorse | Image Slideshow with Text Overlays | `/base/v2/image-slideshow/5903b592-1255-43b4-b9ac-f8ed7cbf6a5f/v1` |

**Block-list** — wrong register, reads gimmicky to this buyer:
Graffiti Mural `3598483b`, Manga Panel `49c61370`, Cave Painting `82ee75b6`,
Egyptian Hieroglyph `a7b0d128`, Steampunk `7b7104f1`, Top Secret `b8707b58`,
Movie Theater `f8f1ebe4`, Breaking News `8800be71`,
**AI Selfie** `/base/v2/ai-selfie-video/…`, **AI Avatar** `/base/v2/ai-avatar-broll/…`.

**Always override `footerText`.** Every template defaults to
*"Follow me for more helpful content | Repost"* — creator-economy language that
reads wrong from a retailer. Use `inhousewellness.com`.

---

## Content pillars (adjustment B3)

| Pillar | Share | Proven by |
|---|---|---|
| The Correction — "X is not the reason to buy Y" | 30% | "$10,000 sauna can be worse than $5,000" (169 FB) |
| The Measured Number — one figure, shown being measured | 25% | "Same 180°F, completely different heat" (113 IG reach, 206 FB) |
| The Reality Check — electrical, space, HOA, delivery | 25% | "I'd love a home sauna but don't want a home improvement project" (106 reach) |
| The Evidence Read — what a study found and didn't | 20% | Untested on social; best demographic fit, lowest compliance risk |

Blog-derived pins outperformed generic wellness pins **5× on mean, 24× on median.**
**Every post traces to a blog article. Nothing is invented for social.**

---

## The four idea feeds — each must fail independently

Failure of one feed must never take down the others.

| Feed | Tool | Status 2026-09-01 |
|---|---|---|
| SEO keywords | Ubersuggest MCP `keyword_overview` / `keyword_suggestions` | ✅ live rows |
| Blog | `blotato_create_source` (`sourceType: article`) | ✅ clean summary; 404 returns an **error**, not a publishable string |
| Pinterest analytics | Buffer `get_aggregated_post_metrics` | ✅ live; 31-day window only |
| IG/FB analytics | Blotato `blotato_list_top_posts` | ✅ tool works, **0 InHouse Wellness rows** (no history in Blotato) |

⚠️ **Do not trust `create_source`'s `title` field.** On a real InHouse Wellness
article it returned `"Visa"`. Use `content` and `referenceUrl`; derive the title
from the keyword queue.

---

## Standing constraint: low-token system

Token cost per published post is a first-class metric, tracked alongside credits.
The skill's governing principle, taken literally: **the LLM writes copy and
nothing else.** Sweeping, matching, routing, dedup, validation and rendering are
deterministic code. If a step can be done without a model call, it must be.

Measured: **one batched call per cycle, ~1,060 input tokens for all 6 posts,
$0.0084 per published post, ≈$1.51/month** at 6 posts/day. One call per post
would be six times that and is forbidden.

## Destination routing (all three platforms)

Destination is a property of every post, not a Pinterest-only field.

| Platform | Where the link lives |
|---|---|
| Pinterest | `link` on the pin — mandatory, validator-enforced |
| Facebook | **first comment**, never the body |
| Instagram | link-in-bio target; captions reference what is currently there |

The satellite network is a **permanent rotation, not a fallback**:
**INH ≥ 60%** of destinations over a rolling 30 days, **no single satellite above
15%**. Asserted in code (`src.destinations.audit`).

**Revised from 70% in Round 3.** The 70% floor assumed the satellites were thin
link pages. The full-network sweep found **1,908 indexed pages across the ten
domains** — real content properties with their own data and tools.

**Match quality outranks the ratio.** If honouring the floor would require a
sub-threshold match, the row is blocked instead. Never degrade a destination to
fill a quota — a pin whose destination does not answer the keyword is the exact
failure that produced the 11,200-impression baseline.

⚠️ **The floor is currently NOT met: 41.2% (14/34), and that is the ceiling.**
Only 14 queued rows have any INH destination scoring ≥0.40. This is an open
🔴 decision, not a routing bug.

Destination is resolved **per platform**. The Healthspan Habits Score carries a
challenge-a-friend share mechanic, so it wins on Instagram and Facebook where
sharing is native, while the row's normal destination wins on Pinterest.

⚠️ **Satellite homepages mostly do NOT link back to INH** — only 4 of 10 do.
Destinations therefore point at the specific inner page that does (verified
2026-09-01, see `data/satellite-destinations.json`). Re-verify with
`scripts/verify_destinations.py` before any scheduling run; it exits 1 on failure.

The validator's `ALLOWED_LINK_HOSTS` carries the same ten domains. That is the
gate's **data**, not its logic — an unknown host still fails `PIN_LINK_OFFSITE`,
and a test asserts the router's list and the validator's list cannot drift apart.
**Do not add a domain without running the verifier.**

### Interactive assets

| Asset | URL | Routed from |
|---|---|---|
| BHIS home-fit finder | `besthomeinfraredsauna.com/best/small-spaces` | dimensions, size, fit, ceiling, space |
| BHIS EMF index | `besthomeinfraredsauna.com/emf` | EMF, safety, transparency, spec claims |
| Healthspan Habits Score | `healthresearchdatabase.com/healthspan` | evidence-read archetype **or** health-curiosity keywords; IG/FB preferred |

Only **2 of 34** queued rows currently reach an asset — the queue holds no
dimension or EMF keywords at all. That is a case for a new keyword batch, not for
loosening the routing rules.

### Crawler politeness

inhousewellness.com rate-limits under load. **HTTP 429 is backoff, never a dead
link** — reading it as failure once blocked every INH row at once and reported an
INH share of 0.0%, a precise and entirely false finding. Verifier: 8s backoff ×6,
concurrency 2.

The 8% per-domain cap is a property of the rolling 30-day **published** window
and is only asserted at n ≥ 25 — below that a single post is arithmetically over
the cap. Same "don't act on noise" rule as the loop's 30-post minimum.

## Rendering: local first, Blotato only for b-roll

**Never route copy carrying numbers, units or a brand claim through a generative
renderer.** Given exact copy, Blotato returned *"3 same 180f. completely
different heat."* — stray token, lost capitalisation, mangled "180°F" — plus a
lime-green highlight outside the palette. The local path reproduced it exactly at
zero cost.

- Static cards and Reels: **local** (Playwright → ffmpeg), 0 credits, 0 tokens — **locked**
- Blotato: reserved for Evidence Read where voiceover genuinely adds value, and
  for b-roll behind deterministic text — never for the text itself
- ffmpeg comes from the `imageio-ffmpeg` wheel. Playwright's bundled ffmpeg is a
  stripped VP8/WebM build with no H.264 and no MP4 muxer — unusable for Reels.
- `animateAiImages` stays **disabled** — still unmeasured.

## ⭐ THE OPERATING PROCEDURE — one session a week (Round 14)

**This is how the account posts. Ten minutes, once a week, human-triggered.**

Blotato schedules natively, so nothing needs to run between sessions: hand it a
week of posts with future timestamps and it publishes from its own
infrastructure. The Mac can be off. GitHub Actions is not in the publishing path.

That removed five things that had each cost a round: the REST key, the runner,
Chromium in CI, state persistence across ephemeral runners, and the cron gate.

The one human step exists because `blotato_create_post` is an MCP tool, and MCP
exists only inside an agent session. Everything else is code.

```
1  python3 scripts/schedule_week.py plan --start <MONDAY> --live
2  (agent) blotato_create_presigned_upload_url  × one per card
3  python3 scripts/schedule_week.py upload --start <D> --presigned <json>
4  python3 scripts/schedule_week.py calls  --start <D>
5  (agent) blotato_create_post × 15, using those exact arguments
6  python3 scripts/schedule_week.py record --start <D> --results <json>
7  next week, before planning:
   python3 scripts/schedule_week.py reconcile --posts <list_posts output>
```

**The agent is a dumb executor.** Selection, dedup, captions, rendering,
validation, slot arithmetic, idempotency and state all live in the script. The
agent only relays precomputed arguments and feeds responses back. The standing
rule holds: the LLM writes copy and nothing else.

### Slots (UTC, with local equivalents)

| Platform | UTC | ET | PT |
|---|---|---|---|
| Pinterest #1 | 15:00 daily | 11:00 | 08:00 |
| Pinterest #2 | 23:00 daily | 19:00 | 16:00 |
| Facebook finding | Tue 16:00 | 12:00 | 09:00 |

Eight hours apart, deliberately. The legacy account once pushed 13 posts in one
day during the window when 27% of output was broken.

### Rules the batch enforces

- **Never schedule a partial week.** Any validator rejection that survives its
  retries halts the whole batch. A week with gaps is not a smaller success.
- **Week-wide dedup.** The selector suppresses near-duplicate keywords within
  one call, which is right for a day and wrong for a batch — the first real
  week drew both "dry sauna vs wet sauna" and "wet sauna vs dry sauna". The
  batch filters the pool so suppression spans the week.
- **Idempotency.** `blotato_list_schedules` is checked before anything is
  created; the D5 breadcrumb still goes down per batch.
- **Verify at schedule time, reconcile at publish time.** At scheduling, assert
  the returned `scheduledTime` matches what was requested. A week later,
  reconcile against `blotato_list_posts`: every post is `published` with a URL,
  or `failed` with a message. **A post that is simply absent counts as neither**
  — absence is not proof of publication.
- **The counter now advances on reconciled clean weeks**, not daily.
- **A scheduled post is a used row.** `plan` selects against a working COPY of
  posting-state, so a halted plan leaves nothing behind; the real state is
  written only by `record`, once the posts exist in Blotato. `record` also
  retires the finding in the ledger. Without both, next week reselects the same
  fourteen keywords and the same finding.
- ⚠️ **Blotato RE-HOSTS media on ingest and rewrites the URL.** The URL in a
  schedule row will not be the `publicUrl` that was uploaded; the content is
  unchanged. `reconcile` matches on submission id only, and a test asserts it
  never compares media URLs — doing so would fail on every post and report a
  clean week as fifteen broken ones.

### Scheduled: week of 2026-09-12 ✅

15 posts live in Blotato (14 pins + 1 Facebook finding), scheduled 2026-09-11,
every resolved `scheduledTime` matching the request exactly. Batch cost $0.3728.
Submission ids in `state/scheduled-weeks.json`. **Reconcile this week before
planning the next one:**

```bash
.venv/bin/python scripts/schedule_week.py reconcile --posts <list_posts output>
```

## The publish path (Round 13)

Two paths exist and they must never drift:

| Path | Used by | Entry point |
|---|---|---|
| **MCP** | a Claude Code session | `blotato_create_post` tool |
| **REST** | the CI runner (no MCP exists there) | `src/blotato.py` |

`PostSpec` renders BOTH the REST body and the MCP arguments, and
`tests/test_blotato_rest.py` asserts they describe an identical post field for
field. Do not add a field to one without the other — the test will fail, which
is the point.

```
POST https://backend.blotato.com/v2/posts     header: blotato-api-key
{"post": {"accountId", "content": {text, mediaUrls, platform},
          "target": {targetType, ...platform fields}}}
```

⚠️ **Blotato API keys are base64 and MAY END IN `=`.** Those characters are part
of the key; Blotato's own docs name stripped padding as the usual cause of 401.
Quote the value in `.env`.

⚠️ **`BLOTATO_API_KEY` currently returns 401** on every documented endpoint and
header variant, with and without padding. The MCP path works on the same
account (`accounts@inhousewellness.com`, 1,550 credits), so API access is live
and it is the key string that is rejected. Regenerate at Settings → API.
**The REST path has therefore never published a real post.**

Post-publish verification (`verify_published`) reads the post back and checks it
exists, the text survived intact, media is attached and the destination
resolves. HTTP 429 on the destination is backoff, never a dead link.

## State lives in git, not in a cache

`state/` is **tracked and committed back by CI**, deliberately. An Actions cache
is evictable (LRU, 7 days) and a cache miss is indistinguishable from a fresh
start — which would silently reset the 14-day streak to zero. That is the same
"absence taken as a value" failure this project keeps hitting. A commit is
durable, diffable and reviewable. A failed run commits only the breadcrumb, so
a halt can never corrupt the counter.

## Media pipeline

`src/media.py`. Verified live 2026-09-02: presigned upload → HTTP `PUT` raw bytes
→ `publicUrl`, which resolved byte-identical to the local file.

The public URL is verified to resolve **before** it is handed to `create_post` —
not left for the validator to catch later — and a byte-count mismatch is treated
as corruption, not success.

## D5 duplicate-post gate

`src/breadcrumb.py`. Written before any publish attempt, cleared only after the
post id is captured. An uncleared breadcrumb **halts the next run** and is
**never auto-cleared** — a human checks the platform first. Enforced as a code
gate, not model guidance.

## The self-improvement loop

`src/feedback.py`. Collect and score are live; **adjust runs `dry_run=True`** and
applies nothing.

| May change | May never change |
|---|---|
| archetype mix weighting | the validator, or any gate |
| keyword priority ordering | health-claim rules |
| board assignment | the 70% INH floor |
| posting time of day | brand palette, type, card layouts |
| satellite rotation order | cadence ceilings |

Guardrails, enforced in code and tested individually:
- the loop **cannot widen its own permissions** — `allowed_knobs`,
  `forbidden_knobs` and `guardrails` are themselves in the forbidden set
- **broken-post rate > 0 halts the loop entirely**, regardless of reach
- no proposal from a segment under **30 posts**
- a change that does not move its stated metric within **14 days reverts**
- every adjustment writes a dated `LEARNINGS.md` entry with evidence, the metric,
  and the revert date
- anything outside the allow-list is a 🟡 REVIEW — the loop proposes, never applies

⚠️ **Pinterest cannot be scored per post.** Buffer's free plan exposes a channel
aggregate over a rolling 31 days only, and Blotato does not collect Pinterest
analytics at all. `collect` marks this `granularity: "channel-aggregate"` rather
than inventing per-pin numbers.

## Decisions taken (2026-09-01)

- **Keyword queue:** remap the 89 dead rows to live blog URLs; no guessed URLs —
  a row with no honest match gets `status: blocked`. Add `verified_at` per row.
- **Legacy `network/customScheduled` path:** shut down by the user 2026-09-01.
  ✅ **Confirmed dead 2026-09-03.** Newest legacy Pinterest post in Buffer is
  **2026-08-22**, twelve days before the check.
  ⚠️ **The test as originally written is WRONG — do not re-run it as stated.**
  It said "the absence of any `via: network` post with `sentAt` after
  2026-09-01". But `via: network` means only "published outside Buffer and
  backfilled", and that is exactly what OUR OWN posts look like: the Facebook
  finding published 2026-09-02T20:26Z appears as `via: network`, `sentAt`
  2026-09-02. The original test would therefore flag our own publishing as the
  legacy path still running — a confident false positive, the same shape as
  every other missing-value failure in this project.
  **Corrected test:** no `via: network` post after 2026-09-01 that is NOT in
  `state/published-log.json`. Match on channel + `sentAt`, not on text.

## Stop and ask the user (surface-don't-assume triggers)

- Credit burn implies under 8 weeks of runway
- Any `source_article` or `link` in the keyword queue 404s
- The legacy `network/customScheduled` RSS path is still live
- Any conflict between this file, the adjustments doc, and the skill

---

## Repo layout

```
CLAUDE.md  RUNLOG.md  LEARNINGS.md  HANDOFF.md
docs/       autoposter-adjustments-inhousewellness.md, BUILD-HANDOFF.md
src/        limits.py  health_claims.py  validator.py      (Round 1)
            remap.py  destinations.py  workorders.py
            captions.py  voice.py  reel.py  feedback.py    (Round 2)
tests/      test_validator.py  test_captions.py  test_feedback.py
            test_probes_keyed.py  test_preflight.py
            test_facts_cache_gate.py  test_facts_drift.py
            test_manufacturer_discovery.py  test_own_page_census.py
            test_manual_specs.py                              (372 tests)
templates/  cards.html (9 archetypes, 3 sizes), tokens.css, fonts/ (4 woff2)
scripts/    render.py  build_blog_index.py  remap_queue.py
            verify_destinations.py  build_reel.py  collect_metrics.py
            preflight.py         runner parity: deps / workflow paths /
                                 stdlib-only / post-install imports
            check_facts_cache.py the post-fetch data gate (was a heredoc)
            check_facts_drift.py derived-fact invariants (halt) + content
                                 drift (report). Baseline:
                                 data/facts-baseline.json, --accept only
            census_own_pages.py  Phase 1: manuals / model numbers / shipping
                                 from OUR pages. Zero egress.
            extract_manual_specs.py  Phase 3: rated power out of manual PDFs
fixtures/   pinterest.json  instagram.json  feedback/ (loop fixtures)
data/       pinterest-keyword-queue.json (103: 24 queued / 79 blocked)
            blog-index.json (109 articles)  satellite-destinations.json
            reels-seed.json (12 Reels / 4 sets)
state/      posting-state.json, metrics-*.json (gitignored)
out/        renders, reels, spike comparison (gitignored)
```

## Commands

```bash
.venv/bin/python -m pytest tests/ -q
```
```bash
# what every workflow runs first: dependency parity, workflow paths,
# the stdlib-only invariant. Seconds, stdlib only, no install needed.
python3 scripts/preflight.py --self-test && python3 scripts/preflight.py --static
python3 scripts/preflight.py --imports   # after a pip install
```
```bash
# the post-fetch data gate: parses, dated, counts agree, above floor
python3 scripts/check_facts_cache.py            # gates
python3 scripts/check_facts_cache.py --report   # prints, never fails
```
```bash
# derived-fact invariants (halt) and content drift (report, exit 0)
.venv/bin/python scripts/check_facts_drift.py
.venv/bin/python scripts/check_facts_drift.py --accept   # acknowledge a real
                                                         # publisher edit
```
```bash
.venv/bin/python scripts/build_blog_index.py && .venv/bin/python scripts/remap_queue.py --write
```
```bash
.venv/bin/python scripts/verify_destinations.py
```
```bash
.venv/bin/python scripts/build_reel.py reel-3-1
```
```bash
.venv/bin/python scripts/collect_metrics.py --buffer fixtures/feedback/buffer-pinterest.json --blotato fixtures/feedback/blotato-top.json --published fixtures/feedback/published-log.json
```
