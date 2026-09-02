# LEARNINGS

Candidate patterns distilled from `RUNLOG.md`. Status: `candidate` → `validated` → `promoted`.
Nothing here changes an SOP until it is promoted through an approved retro.

---

### L1 — Re-verify the adjustment doc's blockers before treating them as blocking
**Status:** candidate · **Affects:** social-autoposter Step 7, harness Meta-Rule 1

The adjustments doc declared "Blotato has only Facebook authorized" a 🔴 BLOCKED
condition. It was true when written and false at run time — Pinterest, Instagram,
TikTok and YouTube are all connected now. Had the block been honoured on the
document's authority, Round 1 would have stopped with nothing delivered.

**Apply:** a governing document records the state at authorship. Meta-Rule 1
("read before acting") extends to re-checking the doc's own blockers against the
live system before halting on one.

---

### L2 — Seed data needs a `verified_at`, not just a value
**Status:** candidate · **Affects:** social-autoposter Step 4 (material bank / feed spec)

103 keyword-queue rows carried `source_article` and `link` fields that looked
authoritative. 89 point at URLs that 404. The rows were seeded from keyword
research and the destination URLs were **inferred from the keyword**, but nothing
in the schema distinguished an inferred URL from a checked one.

**Apply:** every externally-resolvable field in a seed bank carries
`verified_at` (or `verified: false`). Step 4's "verify every fact and business
status" should produce a recorded timestamp per row, not a one-time human pass.

---

### L3 — Test a content validator with the copy that actually shipped
**Status:** candidate · **Affects:** adjustment C2 / social-autoposter Step 13

The health-claim rule set passed every case I invented and failed on
"detox heavy metals" — phrasing lifted from real published captions. Invented
test copy tests the pattern you already thought of.

**Apply:** seed validator tests from the real failure corpus first, and only then
add synthetic edge cases. Rules should key on the **claim** (verb + object), not
one sentence shape.

---

### L4 — Measure per-template cost before choosing a format mix, not after
**Status:** candidate · **Affects:** adjustment A3, social-autoposter Step 12

Per-render cost spans 0 to 50 credits across templates that all look equivalent
in the template list. The all-Blotato mix has ~6 days of runway; the
local-render-plus-capped-Reels mix has ~9 weeks. Same content plan, same budget,
15× difference — decided entirely by which renderer draws each card.

**Apply:** A3's "run five test renders and measure" belongs before the cadence is
committed, and the measurement should be expressed as a runway table across
candidate mixes rather than a single cost-per-render figure.

---

### L5 — Paying for generation can cost you the brand
**Status:** candidate · **Affects:** adjustments C3/C7, social-autoposter Steps 5–6

The 0-credit deterministic template accepted the locked palette exactly. The
50-credit AI infographic ignored it entirely and produced a photoreal whiteboard
in primary marker colours. Credit cost tracks generative effort, not brand
fidelity, and the two are inversely related here.

**Apply:** when a design system is locked (Step 5), prefer deterministic
templates and local renders. Treat generative templates as unbranded stock — fine
for a Reel's b-roll, wrong for anything carrying the identity.

---

### L6 — Pin the toolchain to the host, and say why in the file
**Status:** candidate · **Affects:** social-autoposter Step 6/12, Step 17 (CI)

Current Playwright refuses to install on macOS 13. The cached browser was
`chromium-1148`, so `playwright==1.49.1` was the working pin. A future session
that "helpfully" upgrades will break every render on this host while CI (Linux)
stays green — the worst shape of failure.

**Apply:** version pins that exist for host reasons carry the reason in a comment
next to the pin, not only in a runlog.

---

### L7 — Validate a matcher on pairs, never on aggregate counts
**Status:** validated (3 occurrences in one round) · **Affects:** social-autoposter Step 10

Three separate matcher bugs — an under-collecting index, an inverted IDF default,
and cross-product collisions — were all invisible in the summary statistics and
all obvious the instant the keyword and the matched slug were printed on the same
line. "67 rows matched, median 0.36" looks like success in every one of those
states.

**Apply:** the first artifact a selection/matching step produces is a printed
sample of input→output pairs, before any count. Counts are for regression, not
for discovery.

---

### L8 — A default value can silently invert a gate
**Status:** candidate · **Affects:** social-autoposter Step 10

`idf.get(token, 1.0)` gave corpus-absent tokens the *lowest* weight when they are
by definition the *rarest*. The rare-token gate then fired hardest on the queries
it should have protected, and "wallet in a sauna" matched an article about
infrared safety at 0.641 "strong".

**Apply:** when a lookup default feeds a scoring decision, write the default as a
named constant with the reasoning attached, and add a test using a key that is
deliberately absent. A plausible-looking `.get(x, 1.0)` is where this hides.

---

### L9 — Ratio guards need a minimum sample size or they fire on noise
**Status:** candidate · **Affects:** adjustment routing / destination quota

An 8% per-domain cap is arithmetically unsatisfiable below 13 items, so it
reported a violation on a 24-row batch where two posts shared a domain. The cap
is a property of the rolling 30-day published window, not of any batch in hand.

**Apply:** every share/ratio guard carries an explicit minimum-n, and below it
reports a soft notice rather than a hard failure — the same rule the feedback
loop already applies with its 30-post minimum. State the window the ratio is
measured over, in the code, next to the constant.

---

### L10 — Generative rendering degrades copy; deterministic rendering does not
**Status:** validated (confirms Round 1 L5) · **Affects:** adjustments C3/C7, Steps 6/12

Round 1 found paid AI templates ignore the design system. Round 2 found something
worse: given exact copy, Blotato returned "3 same 180f. completely different
heat." — a stray token, lost capitalisation, and a mangled "180°F". The local
ffmpeg path reproduced the copy exactly at zero cost.

**Apply:** never route copy that carries numbers, units or a brand claim through a
generative renderer. Generative output is acceptable as b-roll behind
deterministic text, never as the text itself. Verify by reading a rendered frame,
not by trusting the input you supplied.

---

### L11 — A feed's convenience endpoint may silently cap
**Status:** candidate · **Affects:** social-autoposter Step 8

Shopify `.atom` feeds return only the ~30 most recent posts per blog and accept
`?page=` without error, so pagination "worked" and produced 80 of 109 articles.
The 29 missing ones included the best matches for several queue rows.

**Apply:** prefer the sitemap (or an explicitly paginated API) over a convenience
feed for anything that must be complete, and cross-check the count against a
second source before building on it.

---

### L12 — State the scope of a negative finding, or it will be read as universal
**Status:** validated · **Affects:** social-autoposter Step 4, harness Meta-Rule 5

Round 2 concluded "the blog genuinely has no article for these keywords" and
published a ranked content brief off it. The sweep had covered one of eleven
domains. Widening it moved 10 rows from blocked to queued and changed the
recommended action.

**Apply:** a negative result ("no data exists") must name the exact search space
that was examined, in the sentence that reports it. "No match in the INH blog
corpus (109 pages)" is honest; "no article exists" was not. Before reporting
absence, ask what else was in scope and was not searched.

---

### L13 — A rate limit is not a failure
**Status:** candidate · **Affects:** social-autoposter Steps 4/8, any link verifier

The URL verifier treated HTTP 429 as a dead link. Because throttling hits one
host at a time, every inhousewellness.com row failed at once and the run reported
an INH destination share of 0.0% — a confident, precise, entirely false claim
about the corpus.

**Apply:** classify HTTP status by meaning, not by "200 or not". 429 and 5xx are
retry-with-backoff; 404/410 are dead. Add a politeness budget to any crawler that
touches one host repeatedly, and treat a whole-host failure as evidence about the
crawler before evidence about the site.

---

### L14 — Suffix checks break on query strings
**Status:** candidate · **Affects:** social-autoposter Step 4

`url.endswith(".xml")` silently skipped
`sitemap_collections_1.xml?from=…&to=…`, dropping all 37 INH collection pages —
the exact commercial destinations the INH quota depends on. The sweep reported
success throughout.

**Apply:** match URL structure by path, not by string suffix. And when an indexer
returns zero of an expected category, treat zero as a bug signal, not a finding —
"0 collections on a Shopify store" should have failed a sanity assertion.

---

### L15 — Staging exists to surface what tests cannot
**Status:** validated · **Affects:** social-autoposter Step 18

The first staged run immediately exposed two defects that 114 passing tests did
not: two Pinterest pins for the same reordered query on one board, and a
validator allow-list that still refused every satellite destination. Neither is
visible without real end-to-end output.

**Apply:** treat the first staged run as a discovery step with an expected yield
of defects, not as a formality before launch. Read every staged item as the
audience would, and specifically look for what the validator *passed* but a human
would reject.

---

### L16 — Verify the round's inputs exist before planning around them
**Status:** candidate · **Affects:** harness Meta-Rule 1, build-loop Phase 2.1

Round 4 assumed a keyword batch file and an API key, both described as present.
Neither existed. Two of the round's four items were unreachable, and that was
discoverable in the first thirty seconds.

**Apply:** "read before acting" includes an explicit precondition check — every
file, key and account the round names — run and reported *before* any build work
starts. A missing input is a question to ask immediately, not a wall to hit
halfway through.

---

### L17 — Grounding quality varies by source, and it changes what copy can claim
**Status:** candidate · **Affects:** adjustment B1/B2, social-autoposter Step 11

`blotato_create_source` extracted rich specifics from INH articles (240V circuits,
4.5–9 kW at 19–38 amps, 10–15 minute heat rounds) and almost nothing from the
satellite pages — "No concrete measured numbers are provided." The satellites are
substantive properties, but their data is JS-rendered and invisible to the
scraper.

**Apply:** treat extractable-fact yield as a property of each source, measured and
stored on the row, not assumed uniform across the corpus. A row whose source
yields no numbers cannot support a "specific numbers over adjectives" caption, and
should either route to a richer source or be marked as a lower-specificity post —
never padded with invented figures.

---

### L18 — Render after the copy exists, not before
**Status:** validated · **Affects:** social-autoposter Step 12

Cards were generated before captions, so they could only show the raw keyword and
the SEO article title. The frame carried no specific claim — on Pinterest, where
the card *is* the post. Reordering to caption → render let the card carry the
validated copy and its actual numbers.

**Apply:** the visual is downstream of the approved copy. Any pipeline that
renders first can only draw what it knew before the writing happened.

---

### L19 — A summarizer is not a scraper; never source a number from one
**Status:** validated · **Affects:** adjustment B1, social-autoposter Step 8/11

Round 4 asked `blotato_create_source` for measured figures, got "no concrete
measured numbers are provided", and concluded the satellite sites had no data.
The tool is an LLM summarizer: it read prose, wrote prose, and accurately
reported that its own output had no numbers. The same sites publish CSV and JSON
with 90 models, 75 metros and 583 studies.

**Apply:** route facts and prose through different tools. Numbers come from
structured endpoints parsed deterministically; summarizers supply context only.
When a tool reports absence, ask what that tool can actually see before treating
the absence as a property of the world.

---

### L20 — Re-audit constants when the assumption behind them is disproved
**Status:** validated (2 occurrences) · **Affects:** harness Meta-Rule 9

The 70% INH floor and the 15% per-satellite cap were both calibrated against
"the satellites are thin link pages." The full-network sweep disproved that, and
both constants then produced wrong behaviour — the floor was unreachable, and the
cap makes batch 02 structurally impossible to route (51 rows aimed at one domain,
5 slots available).

**Apply:** when a foundational assumption is overturned, grep for every constant
that was set under it and re-derive each one explicitly. Fixing only the constant
that happened to fail first leaves the rest to fail one at a time.

---

### L21 — State what was verified and what was only accepted
**Status:** candidate · **Affects:** social-autoposter Step 9/20, harness Meta-Rule 7

The first two live pins: existence, description, media and destination links were
all read back from the platform. Title and alt text were submitted and accepted
by an API that returned success, but never independently confirmed — no endpoint
echoes them and Pinterest blocks scraping.

**Apply:** a publish report distinguishes fields READ BACK from fields merely
ACCEPTED. "Published successfully" is a claim about the request, not about what
is on the page.
