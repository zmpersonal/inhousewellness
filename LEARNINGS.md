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
