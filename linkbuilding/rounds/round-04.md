# Round 4 — Build `01_source` (filter only)

Load the `agent-harness` skill. Standard round rules. Commit the spec to
`linkbuilding/rounds/round-04.md` first, since pushes keep not landing.

> **Scope.** Ingest, parse, filter, report. NO drafting, NO pitching, NO
> sending. The claim bank is still awaiting Dr. Alptunaer's approval and the
> relevance rate is unmeasured — a drafter built now would fire roughly once a
> fortnight against claims nobody has signed off.

## Inherited rules — from `data/samples/README.md`

These are not suggestions. Assert each in code:

1. Pin `connection_id 029715c5` on every Gmail call. Never omit it — the
   Zapier default is `support@` and all five connections are still listed.
2. Assert `Delivered-To: media@inhousewellness.com` on the **response**, not
   the request.
3. Scope queries on label AND recipient. **Zero rows from a query that should
   return rows is a connection signal, not an empty inbox** — raise, don't
   report empty.
4. Include the bare `Media` parent label. `Media/Featured` exists but is
   empty; Featured's mail landed on the parent.
5. Never match on subject line. SOS subjects vary
   (`"...Queries"` vs `"...Queries - \"24 Hour Ad Sale!\" Edition"`).
6. `IMPORTANT:` appears twice per digest as a non-item field. A naive field
   regex catches it. Exclude explicitly.

## Scope — build ONLY these

- `linkbuilding/pipelines/01_source.py`
- `linkbuilding/pipelines/lib/parsers/sos.py`
- `linkbuilding/pipelines/lib/parsers/qwoted.py`
- `linkbuilding/reports/source-digest.md` (regenerated per run)
- `requests` table populated per `schema.sql`

Do NOT build parsers for HARO or Featured — neither has sent a request, so
neither can be tested. Do NOT write drafts.

## SOS parser — the primary source

Structure confirmed identical across both captured sends. Parse from
`*** INDEX ***`, split items on `N) SUMMARY:`, extract the ten labelled
fields: `CATEGORY`, `NAME`, `EMAIL`, `MUCK RACK URL`, `MEDIA OUTLET`,
`MEDIA WEBSITE`, `DEADLINE DATE`, `DEADLINE TIME`, `TIME ZONE`, `QUERY`.

Test against both captured digests in `data/samples/`. Expect 9 items each.

## Qwoted parser — surface only

Reliable: outlet from `From:`, headline, `Submit By:` with timezone, and the
`Because you follow #Tag` line — capture that, it exposes feed configuration
and lets a later run measure whether tag changes worked.

**First, check whether the HTML part carries the untruncated query.** Plaintext
truncates with `...` and HTML is ~5× larger. Report which you used.

Qwoted items carry no journalist name, no email, and only a per-recipient
`url1940.qwoted.com` click redirect. Mark every Qwoted row
`requires_manual: true`. These get surfaced for a human to click through, never
auto-handled.

## Filter

Match against topics in `data/claims.json`. Three buckets:

- `answerable` — squarely covered by an approved claim
- `marginal` — adjacent but would require stretching a claim beyond its
  `do_not_say`
- `rejected` — everything else

**Log rejections with a reason, don't discard them.** At the current rate the
rejections are the dataset; they're how you learn whether the filter is too
tight or the niche is genuinely quiet.

Do not tune the filter to produce hits. Zero answerable is a valid result.

## Report

`reports/source-digest.md` per run: items ingested by source, bucket counts,
every `answerable` and `marginal` item in full with deadline and reply path,
top rejection categories, and a running cumulative count across runs.

## Acceptance criteria

- [ ] All six inherited rules asserted in code, each with a test
- [ ] SOS parser extracts 9 items from each captured digest, all ten fields
- [ ] Qwoted rows all carry `requires_manual: true`
- [ ] HTML-vs-plaintext question answered explicitly
- [ ] Rejections logged with reasons, not discarded
- [ ] Re-running on the same messages does not double-insert
- [ ] Zero drafts written, zero messages sent, mailbox unmodified

## Stop and ask if

- The SOS parser yields anything other than 9 items on either sample
- A Gmail call returns zero rows where rows are expected
- You want to loosen the filter to produce a non-zero answerable count
- Parsing requires the claim bank's approval status to be anything but
  `awaiting_review`
