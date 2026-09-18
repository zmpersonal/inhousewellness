#!/usr/bin/env python3
"""Render reports/haro-corpus-review.md from links.db + the competence map."""
import json, sqlite3, textwrap
from collections import Counter, defaultdict

rows = json.load(open("/tmp/haro112.json"))
c = sqlite3.connect("data/links.db"); c.row_factory = sqlite3.Row
marg = [dict(r) for r in c.execute("""
    SELECT s.journalist_email k, s.category, s.matched_terms, s.reason,
           s.run_date, r.outlet, r.query_text
    FROM source_items s JOIN requests r ON r.id = s.request_id
    WHERE s.platform='haro' AND s.matched_expert='alptunaer' AND s.bucket='marginal'
    ORDER BY r.outlet""")]
cnt = Counter(r["competence"] for r in rows)
bycat = defaultdict(list)
for r in rows:
    bycat[r["category"] or "(uncategorised)"].append(r)

def q(t, n=None):
    t = " ".join((t or "").split())
    return t if n is None else (t[:n] + ("…" if len(t) > n else ""))

L = []
W = L.append
W("# HARO corpus review — is the claim bank mis-scoped, or is the channel quiet?")
W("")
W("Round 9 · generated from `data/links.db` · 112 distinct HARO requests, "
  "2026-09-15 to 2026-09-18 (8 digests, 162 rows)")
W("")
W("## What this document is, and is not")
W("")
W("It is **evidence for a human decision about scope.** Nothing here changed "
  "the filter, the claim bank, the anchor lists, or any threshold. No draft "
  "was written and nothing was sent.")
W("")
W("The competence classification in the last column is **my reading, not a "
  "code gate.** It is published per item precisely so it can be disagreed "
  "with line by line, and it feeds nothing.")
W("")
W("## The question")
W("")
W("162 HARO items produced **0 clinical answerable** and 14 marginal for Dr. "
  "Alptunaer. HARO produced **all four** of his proven links. Both cannot be "
  "right, and the hypothesis was that `claims.json` is scoped to the *product* "
  "— sauna, heat, cold, recovery — rather than to the *expert's competence*.")
W("")
W("## The answer, in one table")
W("")
W("| Of 112 distinct HARO requests | Count | Share |")
W("|---|---|---|")
W("| **A — within the general competence of a practising physician** | **%d** | %.0f%% |"
  % (cnt["A"], 100.0 * cnt["A"] / len(rows)))
W("| B — medical, but gated on a specialty the roster does not state | %d | %.0f%% |"
  % (cnt["B"], 100.0 * cnt["B"] / len(rows)))
W("| **C — outside any medical scope at all** | **%d** | %.0f%% |"
  % (cnt["C"], 100.0 * cnt["C"] / len(rows)))
W("")
W("**The hypothesis is half right, and the half it gets wrong matters more.**")
W("")
W("The bank *is* narrower than the expert: widening it from the product to "
  "general medicine would take HARO from **0 reachable to at most 9** over "
  "these four days — about two a day. That is real, and it is the difference "
  "between a dead channel and a working one.")
W("")
W("But **87 of 112 requests — 78% — are outside medicine entirely.** Holiday "
  "gift guides, Route 66 road trips, greasing baking pans, artificial "
  "Christmas trees, squirrel-proof bird feeders, cybersecurity for CISOs. "
  "HARO is a general-purpose press-query newsletter that happens to carry a "
  "health category, not a medical channel. No scoping decision reaches those.")
W("")
W("So the answer to \"mis-scoped bank or quiet channel?\" is **both, in that "
  "order**: fix the scope and the channel goes from 0 to roughly 2 a day. It "
  "does not go to 20.")
W("")
W("### Tier B is the number that cannot be settled here")
W("")
W("16 requests are squarely medical but call for a named specialty — "
  "dermatology (4), veterinary (4), psychiatry or behavioural neurology (3), "
  "reproductive medicine (2), transplant, plastic surgery, dentistry. "
  "**`data/experts.json` records Dr. Alptunaer's credential as `MD` and states "
  "no specialty.** Whether those 16 are reachable is a fact about him that "
  "this project does not hold. If he is a dermatologist, A becomes 13. "
  "That is a question for a human, and it is the single cheapest thing that "
  "would sharpen every number above.")
W("")
W("---")
W("")
W("## Two concrete defects the corpus exposed")
W("")
W("### 1. The same question, opposite outcomes, decided by one word")
W("")
W("Red light therapy for skin arrived on both platforms in the same week.")
W("")
W("| | Connectively | HARO |")
W("|---|---|---|")
W("| Wording | \"red or **near-infrared** light\" | \"**light-based** skin treatments\" |")
W("| Matched | `infrared` | nothing |")
W("| Bucket | **answerable**, alptunaer | **rejected** |")
W("")
W("Same subject, same week, same expert. The gate is keyed to product "
  "vocabulary, not to subject matter, and this is what that looks like from "
  "the outside.")
W("")
W("### 2. `infrared` is in the filter and in NO claim in the bank")
W("")
W("The rejection reason the pipeline printed for the match above reads: "
  "*\"modality ['infrared'] named; the claim bank covers this directly.\"*")
W("")
W("It does not. **Zero of the 30 claims mention infrared, and zero are about "
  "skin, dermatology or photobiomodulation.** The bank's topic list is "
  "`heat, cold, cardiovascular, sleep, mood, recovery, safety…` — nothing "
  "optical.")
W("")
W("So the one clinical answerable in the entire corpus is a match on a filter "
  "keyword with no claim behind it. Had the bank been approved and a drafter "
  "existed, that row would have been pitched under a physician's name with "
  "nothing to say. **The filter's vocabulary and the bank's contents have "
  "drifted apart, and nothing currently checks that they agree.**")
W("")
W("Neither defect was fixed. Both are out of Round 9's scope.")
W("")
W("---")
W("")
W("## The 14 Alptunaer marginals, quoted in full")
W("")
W("These are the closest the clinical filter came. **14 rows, %d distinct "
  "requests** — HARO repeats queries across its three daily editions, so the "
  "duplication is visible here too." % len({m["k"] for m in marg}))
W("")
for i, m in enumerate(marg, 1):
    W("### M%02d · %s" % (i, m["outlet"] or "(no outlet)"))
    W("")
    W("- **HARO category:** %s" % (m["category"] or "—"))
    W("- **Anchor that matched:** `%s`" % ", ".join(json.loads(m["matched_terms"])))
    W("- **Why marginal:** %s" % m["reason"])
    W("")
    for para in textwrap.wrap(q(m["query_text"]), 96):
        W("> " + para)
    W("")

W("---")
W("")
W("## All 112 distinct requests, grouped by subject area")
W("")
W("`Tier` is the competence reading: **A** general physician · **B** medical, "
  "other specialty · **C** outside medicine.")
W("")
order = ["Health and Pharma", "General", "Business and Finance", "Gift Bags",
         "Lifestyle and Entertainment", "Podcasts", "Technology", "Travel"]
for cat in order + [k for k in bycat if k not in order]:
    if cat not in bycat:
        continue
    items = bycat[cat]
    cc = Counter(r["competence"] for r in items)
    W("### %s — %d requests  (A %d · B %d · C %d)"
      % (cat, len(items), cc["A"], cc["B"], cc["C"]))
    W("")
    W("| Tier | Outlet | Topic | Bucket | Why not answerable |")
    W("|---|---|---|---|---|")
    for r in items:
        why = r["competence_note"] or ""
        if not why:
            why = ("no sauna/heat/cold/recovery vocabulary; nothing medical in it"
                   if r["bucket"] == "rejected" else "wellness-shaped but no modality named")
        if r["bucket"] == "answerable":
            why = "**answerable — %s (provisional)**" % r["matched_expert"]
        W("| %s | %s | %s | %s | %s |"
          % (r["competence"], q(r["outlet"], 28) or "?", q(r["query_text"], 92),
             r["bucket"], why))
    W("")

W("---")
W("")
W("## What this does not tell you")
W("")
W("**Four days is four days.** 112 requests over one HARO week is enough to "
  "see the shape of the channel and not enough to price it. The 14-day clock "
  "started 2026-09-15 and has 10 days to run.")
W("")
W("**The four proven links are not in this sample.** They were earned "
  "2026-01-20 to 2026-07-02 through a contractor's own HARO account, and "
  "nothing in this corpus is one of them. The Healthline placement is "
  "understood to have been about heart-attack risk in younger males — general "
  "cardiology, tier A, and exactly the kind of request the current bank "
  "cannot match. That is the strongest single piece of support for the "
  "mis-scope hypothesis, and it sits outside this dataset rather than in it.")
W("")
W("**The competence column is a judgement.** Nine is my count, itemised above "
  "so it can be checked. A reviewer who counts differently should say so on "
  "the rows, not on the total.")
open("reports/haro-corpus-review.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote reports/haro-corpus-review.md")
print("A=%d B=%d C=%d  marginal rows=%d distinct=%d"
      % (cnt["A"], cnt["B"], cnt["C"], len(marg), len({m["k"] for m in marg})))
