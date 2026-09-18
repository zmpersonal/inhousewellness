# Round 8 — HARO and Connectively parsers

Load `agent-harness`. Commit the spec to `linkbuilding/rounds/round-08.md` first.

> Only send this when `Media/HARO` and `Media/Connectively` hold at least two
> digests each. One sample cannot tell you whether format varies between sends
> — the question SOS needed two samples to answer.

## Context that changes the design

Featured acquired Connectively in 2025 and revived it in 2026 by migrating its
own platform onto the Connectively brand. **Connectively and Featured are the
same product.** `Media/Featured` is empty and should be retired unless the
sending domains differ — check before deleting.

HARO is a pure newsletter: three daily digests, no dashboard, no account
required to reply, every query carries its own reply-to. Connectively is the
platform product — browse, filter, pitch in-app.

That difference matters: HARO items should carry a direct reply path like SOS
does. Connectively items likely won't, and would be `requires_manual: true`
like Qwoted.

## Scope — build ONLY these

- `linkbuilding/pipelines/lib/parsers/haro.py`
- `linkbuilding/pipelines/lib/parsers/connectively.py`
- Recipient/label wiring for both
- Sample capture for each

No drafter. No changes to SOS or Qwoted parsing.

## Per parser

Test against at least two captured digests. Report items per digest, which
fields are reliably present, whether structure varies between sends, and
whether a direct journalist reply path exists.

If a reply path is absent or is a click-tracking redirect, mark
`requires_manual: true`. Do not construct a reply address.

## Start the clock

All four proven links came through HARO. The 14-day window starts on the first
HARO digest — record that date in `RUNBOOK.md` and the trend header.

Report HARO's answerable rate separately from SOS and Qwoted. They are
different channels with different track records and averaging them hides the
only signal that has ever mattered here.

## Acceptance criteria

- [ ] Both parsers tested against ≥2 real digests each
- [ ] Format-variance question answered explicitly per platform
- [ ] Reply paths classified; no constructed addresses
- [ ] HARO answerable rate reported separately
- [ ] 14-day clock start date recorded
- [ ] Featured/Connectively consolidation resolved
- [ ] Zero drafts, zero sends, mailbox unmodified

## Stop and ask if

- Either platform's two digests differ structurally — report before parsing
- No HARO digest has arrived within 48 hours of a verified signup
