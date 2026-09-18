# Round 10 — Close the filter/bank gap

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-10.md` first.

> Round 9 found the filter reporting "the claim bank covers this directly" for
> `infrared`, a term appearing in zero of 30 claims. The filter's vocabulary and
> the bank's contents are maintained independently and nothing reconciles them.
> That is a correctness bug, not a tuning question.

## 1. Every filter keyword must map to a claim

Build the reconciliation: each clinical filter term resolves to at least one
claim id in `claims.json`, or it is not a valid match term.

`claims.py` raises on any clinical term with no backing claim. Run it against
the current vocabulary and report every orphan — `infrared` will not be alone.

An item matching only orphaned terms is `rejected`, not `answerable`.

Do NOT fix this by adding claims. The bank is a reviewed artifact and adding to
it outside Dr. Alptunaer's process defeats its purpose. Orphaned terms are
removed from the filter; the gap is reported for him to fill or decline.

## 2. Match on concept, not keyword

"Red or near-infrared light" matched; "light-based skin treatments" did not.
Same subject, opposite outcomes, one word apart.

Give each claim an explicit synonym set stored alongside it, derived from the
claim text and its citations, so matching is against a claim's concept rather
than a term list maintained elsewhere. Report any case where this changes an
existing verdict.

## 3. Record the specialty gap

`experts.json` holds `MD` and nothing more. 16 tier-B items are gated on a
specialty the project doesn't know.

Add a `specialty` field, leave it null, and have the report state plainly that
16 items are unresolvable until it's filled. Do not guess it.

## Acceptance criteria

- [ ] Every clinical filter term maps to a claim id, or raises
- [ ] All orphaned terms reported; none silently removed
- [ ] Items matching only orphans are rejected
- [ ] Synonym sets derived per claim; verdict changes reported
- [ ] `specialty` present and null; the 16 gated items named
- [ ] No claims added to `claims.json`
- [ ] Zero drafts, zero sends, mailbox unmodified

## Stop and ask if

- More than a third of clinical filter terms turn out to be orphans
- Removing orphans takes clinical answerable to zero across the whole corpus —
  report it, that is a real finding rather than a failure
