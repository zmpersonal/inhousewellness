# Round 14 — Close the loop

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-14.md` first.

> Pitches are now going out, sent by a human. The pipeline has no record of
> what was sent, what was used, or whether a link resulted — so it cannot
> measure the only thing that matters.

## 1. Record sends

A way for the human to mark an item sent, with the address it was sent from
and the timestamp. Simplest workable mechanism — a committed file the human
edits, or a CLI command. State which.

Sent items leave the review queue and are never re-surfaced.

## 2. Track outcomes

For each sent item: published or not, published URL, and whether it carries a
link to inhousewellness.com — follow or nofollow, from the page itself.

Check published URLs on the existing weekly verify cadence. Do not guess
publication from silence; an unconfirmed pitch stays `pending`.

## 3. The number that matters

Report: pitches sent, published, linked, and time from send to publication.
Per regime and per platform. This replaces answerable-rate as the headline —
answerable was always a proxy for this.

## Acceptance criteria

- [ ] Sends recordable by the human; sent items drop from the queue
- [ ] Published URLs checked for an actual link, rel attribute recorded
- [ ] Sent / published / linked reported per regime and platform
- [ ] No publication inferred from silence
- [ ] Zero sends by the pipeline
