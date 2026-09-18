# Round 12 — The drafter

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-12.md` first.

> First round that produces something sendable. 17 reachable of 112, the
> attribution guard is in place, and the claim bank has the expert's general
> approval. Everything is drafted for human review — nothing sends.

## Hard constraints

- **Nothing is sent.** Drafts only. Every one reaches a human before a
  journalist.
- **Only from approved material.** Claim bank claims, or the expert's approved
  experience set, or Tripler's set if approved by then. No claim, no draft.
- **`assert_pitchable()` gates every draft.** Verbatim credential line, framing
  set, attribution guard passed.
- **No novel claims.** If answering well requires something not in an approved
  set, the item is flagged `needs_expert_input`, not drafted.

## 1. Drafting

For each reachable item produce a draft carrying: the ready-to-publish answer
first (journalists use what they can paste), the verbatim credential line, and
the InHouse Wellness affiliation.

Constraints from the platforms themselves: under 300 words, lead with
credentials, answer every question asked, include a specific example or
verifiable data point.

Each draft records the claim ids or experience topics it used. A draft whose
sources can't be enumerated doesn't ship.

## 2. Requirement mismatches

4 of the 8 specialty-unlocked items request a profession he doesn't hold —
mental health professional, dermatologist, dentist/dietitian, psychiatrist.

Draft these but mark `requirement_mismatch: true` with the requested profession
named, and surface it at the top of the review queue. The human decides whether
to send. Do not paper over the gap in the draft text.

## 3. Read past the opening clause

Three of 16 tier-B items were not expert requests at all — a fertility panel
that asks for gift bags, a listing seeking a practice to host a writer for a
free procedure. Both read as medical for one sentence.

Before drafting, verify the item actually requests expert commentary. Flag
anything asking for products, samples, hosting, or services as `not_a_query`
and do not draft it.

## 4. Review queue

`reports/draft-queue.md`: requirement mismatches first, then by deadline. Each
entry shows outlet, deadline, reply path, source claim ids, framing, and the
full draft.

HARO replies go to the item's `reply+<uuid>@` address read from the mail —
never constructed. Connectively items are `requires_manual: true`; surface the
draft for copy-paste, no reply path.

Alert to `#media` when the queue gains an item, subject to the Round 7 approval
gate.

## Acceptance criteria

- [ ] Every draft passes `assert_pitchable()`; test proves a failing one is blocked
- [ ] Every draft enumerates its source claim ids
- [ ] `needs_expert_input` used rather than improvising a claim; test proves it
- [ ] Requirement mismatches flagged and surfaced first
- [ ] `not_a_query` detection tested against the three known items
- [ ] Zero sends. Mailbox unmodified.

## Stop and ask if

- More than 12 of 17 draft cleanly — likelier that the bank is being stretched
  than that coverage is that good
- Any draft needs a claim outside the approved sets
- A draft would read as authoritative on a specialty he doesn't hold, even with
  the credential line correct
