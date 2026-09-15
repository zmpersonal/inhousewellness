# InHouse Wellness link building — RUNBOOK

**Written for a session with no memory of this project.** If you were fired by
a Routine, start here and read the whole thing before touching anything.

Everything lives under `linkbuilding/`. The repo-root `CLAUDE.md` governs other
projects; `linkbuilding/CLAUDE.md` governs this one.

---

## The one-paragraph version

We monitor journalist-request platforms for questions a sauna and cold-plunge
retailer's medical expert could credibly answer, so that answering them earns
high-authority editorial links. Right now we are **measuring**, not pitching.
The pipeline ingests, parses and filters; it does not draft and does not send.
Nothing may be attributed to Dr. Alptunaer until he signs the claim bank,
which is still `awaiting_review`.

## Hard constraints — do not relax any of these

- **Read-only on the mailbox.** Never archive, mark read, label, reply or send.
- **No drafts, no pitches, no sending.** The claim bank is unapproved.
- **Never loosen the filter to produce an answerable count.** Zero answerable
  is the expected result and a valid one. Tightening against false positives
  is fine; loosening to manufacture a hit is not.
- **Facebook Groups stay manual, permanently** (root `CLAUDE.md`, adjustment D3).

---

## What runs when

**Routine `trig_01JTW5ufQ4xb4fvmS2G2TwSX` — 3x daily at 11:37, 18:37, 21:37 UTC.**

Those times are not arbitrary:

| Fire | Why |
|---|---|
| 11:37 UTC | ~1h after the SOS morning digest (observed 10:32 UTC) |
| 18:37 UTC | ~1h after the SOS afternoon digest (observed 17:35 UTC) |
| 21:37 UTC | Evening catch-all for late Qwoted sends |

SOS sends up to three times a day and deadlines are frequently same-day — the
tightest observed was a Qwoted request arriving 14:38 UTC with a 20:00 UTC
deadline. A single daily fire would have let afternoon queries sit ~20 hours.

⚠️ **The Routine currently has NO MCP connectors attached** (`mcp_connections:
[]`), so its sessions have no Gmail and no Slack and cannot do the job. The
`connectors` parameter is **not available for this organization** — it was
tested and returned *"the connectors parameter is not available for this
organization"*. Connectors must be attached from the **claude.ai Routines UI**.
Until that is done, every fire will fail.

---

## Running it by hand

```bash
# 0. Does the database exist? It is gitignored and absent on a cold start.
python3 linkbuilding/pipelines/rebuild.py verify
python3 linkbuilding/pipelines/rebuild.py run        # if missing or incomplete

# 1. Fetch Gmail (agent-side; MCP only exists inside a session).
#    Zapier tool: gmail_find_email
#    connection_id: 029715c5-3a50-8935-b200-6e6eba55ac62   <-- ALWAYS PIN THIS
#    query:
#    to:media@inhousewellness.com (label:Media OR label:Media/Qwoted OR
#    label:Media/SourceOfSources OR label:Media/HARO OR label:Media/Featured)

# 2. The response is ~700KB and lands in a tool-results file. Stage it:
python3 -c "import sys;sys.path.insert(0,'linkbuilding/pipelines/lib');import relay;\
print(relay.stage('<tool-results path>','<scratchpad dir>'))"

# 3. Run.
python3 linkbuilding/pipelines/01_source.py run \
  --payload <staged path> \
  --connection-id 029715c5-3a50-8935-b200-6e6eba55ac62
```

**Exit codes:** `0` success · `3` a stop condition fired · `4` the run failed
and `reports/ALERT-failure.md.slack.txt` is waiting to be posted.

---

## Rebuilding from scratch

`links.db` is a gitignored build artifact. `rebuild.py` reconstructs it from
**committed files only** — no scratchpad, no `/tmp`:

- `data/payloads/{overview,backlinks}.json` → re-runs `00_audit`
- `data/payloads/{gap,serp,mentions}.json` → re-runs `03_discover` + `04_qualify`
- `data/source-state.json` → restores `01_source` rows and the trend counter

It re-asserts the Round 1 acceptance test on every rebuild: **17 earned / 10
owned / 6 affiliate / 9 syndication / 14 spam / 4 local aggregator / 6
unresolved, delta +0**. If a rebuild produces different numbers it raises,
because a rebuild that quietly rewrites the baseline is worse than no rebuild.

**Never start a run against an empty database.** That silently resets the
14-day trend counter, and a reset counter looks exactly like a quiet week.

---

## The six inherited access rules

From `data/samples/README.md`, all asserted in `01_source.py` with tests. Each
came from a real failure on 2026-09-14 where the pipeline reported an empty
inbox that was actually a wrong-mailbox read.

1. **Pin `connection_id 029715c5-3a50-8935-b200-6e6eba55ac62`** on every Gmail
   call. The Zapier default is `support@inhousewellness.com` and returns an
   empty result set rather than an error.
2. **Assert the recipient on the response**, not the request. Membership in
   `EXPECTED_RECIPIENTS` — `media@`, `timur@`, `tripler@` — defined once in
   `01_source.py`. Anything else raises. The recipient is persisted on every
   item because it identifies which expert the query is for.
3. **Zero rows where rows are expected is a connection signal, not an empty
   inbox.** Raise; never report nothing.
4. **Include the bare `Media` parent label.** `Media/Featured` exists but is
   empty — Featured's mail landed on the parent.
5. **Route by sender, never subject.** SOS subjects vary between sends.
6. **Exclude `IMPORTANT:` from SOS field extraction.** It appears twice per
   digest as a house notice and a naive field regex captures it.

A seventh, learned later: **`slack_search_channels` defaults to PUBLIC channels
only.** `#media` is private. Searching without `channel_types` including
`private_channel` will tell you the channel does not exist. It does.

---

## Alerting

**Slack `#media`, channel ID `C0C26J8JX8U` (private).**

| Event | Action |
|---|---|
| `answerable` > 0 | Post `reports/ALERT-answerable.md.slack.txt`. This is the event the pipeline exists for and may happen once a fortnight. |
| Run failed (exit 4) | Post `reports/ALERT-failure.md.slack.txt`. **A failed run is an event.** |
| `answerable` = 0 | Post nothing. The trend report is the record. |

Both alert files are deleted automatically when the condition clears — a stale
alert is worse than none.

**Why a failed run must alert:** a pipeline that stops running produces the
same observable as a quiet niche — zero answerable, every day. The 14-day
decision below depends entirely on telling those apart.

---

## The decision this is all feeding

From `reports/source-trend.md`, fixed before the data arrived:

| After 14 days | Conclusion |
|---|---|
| ≥1 answerable per week | `01_source` earns its place. Build the drafter. |
| Answerable but all Qwoted | Evaluate Qwoted Pro ($149/mo); the free tier's 7 pitch credits and request delay become binding. |
| Zero answerable, marginals clustering in one topic | The gap is in the claim bank, not the pipeline. |
| Zero answerable, marginals scattered | The niche is quiet. Keep the filter cheap; put effort into dealer pages and outreach. |
| High `deadline misses on arrival` | The pipeline is finding real requests too late. Check this row before concluding the niche is quiet. |

**Context that changes how a zero reads:** all four high-DR links
(healthline DR91, eatthis DR83, womansworld DR66, singlecare DR63) have
`first_seen` between 2026-01-20 and 2026-07-02 — all in the Featured-operated
HARO era, none from Cision, none from the Connectively dead zone. The channel
that produced them is **live**. Meanwhile `Media/HARO` has received exactly one
email since signup: a verification request. So a zero result currently reads as
*a live channel not reaching this inbox*, which is a plumbing problem, not a
dead-niche problem.

---

## The expert roster — two people, two evidentiary regimes

See `data/experts.json`.

| Expert | Regime | Source | Status |
|---|---|---|---|
| Dr. Timur Alptunaer, MD | cited | `data/claims.json` | `awaiting_review` |
| Tripler (health coach, MSc Org Behaviour) | experience-based | none, by design | provisional, `approved: false` |

**HARD RULE — clinical attribution.** Every claim in `claims.json` is
attributable to Dr. Alptunaer and to nobody else.
`assert_clinical_attribution()` raises if claim-bank vocabulary is ever routed
to another expert. A certified health coach quoted on cardiovascular mortality
literature is a scope-of-practice failure and a credibility failure at once,
and "functional health" is precisely the boundary where that mistake happens.

Tripler deliberately has **no `claims.json` equivalent**. The regimes are
different and merging them would weaken the clinical one. Her topic set is
provisional and exists for measurement only — nothing is pitched from it.

Matching for her requires a specific ANCHOR (`founders`, `solopreneurs`,
`small business`, `habit formation`, `health coaching`…). Generic workplace
words (`employee`, `operations`, `leadership`) only SUPPORT; alone they yield
`marginal`. The first pass used them as anchors and promoted a Pet Age story
about holiday staffing to `answerable`.

## Open items

- **Claim bank is `awaiting_review`.** Nothing ships under the physician's name
  until `reports/claim-bank-review.md` is signed.
- **Routine has no connectors.** Must be attached via the claude.ai UI.
- **HARO is signed up but silent.** Worth chasing before drawing conclusions.
- **No HARO or Featured parser.** Neither has sent a request, so neither can be
  tested. Do not write one speculatively.
- Five paid-pattern links remain `unresolved` pending human provenance check.
