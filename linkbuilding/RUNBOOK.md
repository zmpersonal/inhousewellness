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

- **Read-only on the mailbox, with ONE exception: the pipeline may CREATE a
  Gmail draft.** It may never send, delete, archive, label, mark read, or
  modify any existing message or draft. The exception is enforced in
  `lib/gmail_draft.py`, which names exactly one write action
  (`gmail_create_draft`) and is tested by parsing its own AST — the executable
  surface, not the prose — for every forbidden verb.
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

**Nothing about a run is allowed to fail quietly.** It is bracketed by two
checks that each exist because the corresponding failure already happened:
a `probe` before (2026-09-14, a run that read the wrong mailbox and reported
an empty inbox) and a `verify-push` after (2026-09-14, a run that exited 0 and
persisted nothing because the push was denied and the container was reclaimed).

```bash
# 0. Does the database exist? It is gitignored and absent on a cold start.
python3 linkbuilding/pipelines/rebuild.py verify
python3 linkbuilding/pipelines/rebuild.py run        # if missing or incomplete

# 1. Fetch Gmail (agent-side; MCP only exists inside a session).
#    Zapier tool: gmail_find_email
#    connection_id: 029715c5-3a50-8935-b200-6e6eba55ac62   <-- ALWAYS PIN THIS
#    query:
#    (to:media@inhousewellness.com OR to:timur@inhousewellness.com OR
#     to:tripler@inhousewellness.com)
#    (label:Media OR label:Media/Qwoted OR label:Media/SourceOfSources OR
#     label:Media/HARO OR label:Media/Featured OR label:Media/Connectively)

# 2. The response is ~700KB and lands in a tool-results file. Stage it:
python3 -c "import sys;sys.path.insert(0,'linkbuilding/pipelines/lib');import relay;\
print(relay.stage('<tool-results path>','<scratchpad dir>'))"

# 3. PROBE BOTH CONNECTORS. Save the RAW result of each call to a file.
#    Gmail : the payload from step 1 is itself a real result — reuse it.
#    Slack : slack_read_channel on C0C26J8JX8U. Use a narrow, empty time
#            window so the reply is tiny but still names the channel:
#              channel_id=C0C26J8JX8U limit=1 response_format=concise
#              oldest=1789000000.000000 latest=1789100000.000000
#            -> {"messages":"Channel: #media (C0C26J8JX8U)\n\n", ...}
python3 linkbuilding/pipelines/01_source.py probe \
  --gmail <staged payload> --slack <slack result file>

# 4. Run. Refuses to start unless the probe is present, passing and < 30 min old.
python3 linkbuilding/pipelines/01_source.py run \
  --payload <staged path> \
  --connection-id 029715c5-3a50-8935-b200-6e6eba55ac62

# 5. Commit and push everything under linkbuilding/data and linkbuilding/reports.

# 6. VERIFY THE PUSH LANDED. The run is not finished until this passes.
python3 linkbuilding/pipelines/01_source.py verify-push

# 7. Commit push-log.json and the re-rendered trend (one small follow-up commit).

# 8. Post to Slack #media: the heartbeat if one was written, and the alert
#    file if one was written. Then you are done.
```

**Exit codes:** `0` success · `3` a stop condition fired · `4` the run or the
probe failed and `reports/ALERT-failure.md.slack.txt` is waiting to be posted ·
`5` the push could not be verified — **this run does not count and the trend
report will say so.**

### Why the probe judges raw results instead of reading a health flag

The 2026-09-14 failure read `is_stale: false` off a connection listing and
proceeded to query the wrong mailbox, which answered with zero rows and no
error. A self-reported flag is not reachability. `probe` therefore takes the
**raw result of an actual call** to each connector and decides for itself:
a Gmail reply with zero messages fails, a reply delivered to an address outside
`EXPECTED_RECIPIENTS` fails, and a Slack reply that does not name `C0C26J8JX8U`
fails. The agent relays; the code judges.

Cloud Routine sessions use a **separate OAuth registration** from interactive
sessions, so a connector that works in chat can be stale for the Routine. That
is why the probe must be less than 30 minutes old — a probe from another
session proves nothing about this one.

### Why `verify-push` does not just check that `git push` returned

It reads `linkbuilding/data/source-state.json` **out of the commit the remote
branch points at** and confirms this run's `run_at` is in it. A ref that
advanced, a commit that exists locally, and a push that printed no error are
all satisfiable while the run's rows sit only in a container about to be
deleted. It also re-confirms every earlier local run against the same remote
blob, so a run that predates the log is not falsely reported as lost.

`reports/source-trend.md` counts **verified days only**. The newest run always
reads `⏳ pending` (verification happens after the commit exists, so the log is
committed one run behind). A run still `pending` after the next run has gone
through is a run that never persisted, and the report opens with a banner
saying the counter cannot be trusted.

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
| `answerable` > 0 **and an APPROVED expert matched** | Post `reports/ALERT-answerable.md.slack.txt`. This is the event the pipeline exists for and may happen once a fortnight. |
| `answerable` > 0, **provisional expert only** | **No alert.** One line in the daily heartbeat. |
| First run of any day | Post `reports/heartbeat.slack.txt`. |
| Run or probe failed (exit 4) | Post `reports/ALERT-failure.md.slack.txt`. **A failed run is an event.** |
| Push unverified (exit 5) | Post `reports/ALERT-failure.md.slack.txt`. |
| `answerable` = 0 | Nothing beyond the heartbeat. |

Alert files are deleted automatically when the condition clears — a stale alert
is worse than none.

### Alerting is gated on approval (Round 7 §6)

The 2026-09-15 run alerted on three answerable items, all matched against
Tripler's **provisional** topic set: agent-authored, `approved: false`, never
reviewed by her. Nothing could have been sent from any of them, and the same
three would have alerted on every run until the corpus changed — training the
channel to be ignored before a real item ever arrived.

An immediate alert now requires an approved expert behind the match:

| Expert | Gate | Status |
|---|---|---|
| Dr. Alptunaer | `claims.json` `approval_status == "approved"` | `awaiting_review` → **not approved** |
| Tripler | `experts.json` `approved == true` | `false` → **not approved** |

So the **correct current state is zero immediate alerts and one heartbeat a
day**, and that is what the pipeline does. This is the design, not a failure.
`approved_experts()` reads the real status rather than hardcoding zero, so
alerting starts working the day either is signed, with no code change.

Items already alerted on are recorded in `data/alerted-items.json` and never
re-alert.

### The heartbeat (Round 7 §3)

One line to `#media` on the first run of each day: items ingested, bucket
counts, day N, held provisional items, unparsed platforms, and push status.

At the expected rate an answerable item may be weeks away, and a channel
silent for two weeks is indistinguishable from a channel whose posting path is
broken. The heartbeat makes the silence informative. Use
`run --force-heartbeat` to emit one when the day's first run has already gone.

### Fallback when Slack is unreachable (Round 7 §7)

**Slack unreachable is a failure state, not a degraded mode.** `probe` exits 4
and the run does not start. Send the fallback instead:

> `PushNotification` with **`status: "proactive"`** and a message under 200
> characters.

`status` is a **constant** in that tool's schema — `"proactive"` is the only
value that validates, and anything else (including `"normal"`, and omitting it)
fails schema validation. That is why it appeared to "error regardless of
input". Verified working 2026-09-15; it is no longer an untested fallback.

There is no email fallback in this session and none is claimed.

**Why a failed run must alert:** a pipeline that stops running produces the
same observable as a quiet niche — zero answerable, every day. The 14-day
decision below depends entirely on telling those apart.

---

## Gmail drafts for approved HARO replies

```bash
python3 linkbuilding/pipelines/01_source.py gmail-draft [--key K]   # on demand
python3 linkbuilding/pipelines/01_source.py gmail-drafted --key K --draft-id ID
python3 linkbuilding/pipelines/01_source.py detect-sends --payload <Sent read>
```

`gmail-draft` is runnable on demand because HARO deadlines are routinely under
24 hours and waiting for the next scheduled fire loses them. It emits the exact
Zapier call; the session relays it, because MCP exists only inside a session.

**A draft is built only when `assert_ready_to_send()` passes** — every
experience statement confirmed, expert review recorded. A Gmail draft can never
contain `[CONFIRM: experience]`; `build_draft_args()` raises on it.

| Field | Value |
|---|---|
| To | the item's `reply+<uuid>@helpareporter.com`, **read from the stored item** |
| From | `timur@inhousewellness.com` — ✅ a verified Send-as alias on julian@ |
| Subject | the query's title as it appeared in the HARO digest |
| Body | the approved draft, plain text, credential line verbatim |
| Attachments | none, ever |

**HARO only.** Connectively and Qwoted have no reply address — only an
in-platform click-through — so there is nowhere for an email to go. They are
skipped and said so.

### Zapier specifics, verified 2026-09-21

- **`gmail_create_draft` (`draft_v2`) was already enabled.** Nothing needed
  enabling and nothing was enabled.
- ⚠️ **Other Gmail write actions are also enabled on this Zapier account** —
  Send Email, Delete, Archive, Add/Remove Label, Reply. The pipeline cannot
  reach them (see the AST test), but they exist. Disabling them is a judgement
  call for the account owner, since other automations may use them.
- ⚠️ **`inspect_zapier_actions` rejects the UUID `connection_id`** with a NaN
  type error. Use the numeric id from the connection's `reconnect_url`
  (`53367330` for julian@) when resolving a dynamic enum. With the UUID it
  silently resolves against the **default** connection (support@) and shows
  the wrong mailbox's aliases — which is how "timur@ is not available" would
  have been concluded, wrongly.
- **The draft is created in julian@'s mailbox** (the pinned connection). There
  is no Gmail connection for timur@; `timur@` works only as a Send-as alias.

### The subject line, and when it is missing

The subject is the **digest title, read from the mail**. It is stored per item
in `source_items.summary`. If it is NULL, `build_draft_args()` raises rather
than inventing a subject from the query text — a plausible-looking subject
invented from the body is an absence dressed up as a value.

Backfill the titles for live items after re-fetching the digests:

```bash
# 1. Fetch the digests over a window covering the OLDEST live deadline.
#    Per-sender, or the pull times out:
#      from:haro@helpareporter.com after:YYYY/MM/DD before:YYYY/MM/DD
#      (from:sourceofsources.com OR from:noreply@connectively.us OR
#       from:qwoted.com) after:YYYY/MM/DD before:YYYY/MM/DD
#    Pinned connection only (029715c5-3a50-8935-b200-6e6eba55ac62).
# 2. Backfill, passing every saved payload in ONE invocation:
python3 linkbuilding/pipelines/backfill_summaries.py <payload> [<payload> ...]
# 3. Persist it, or a cold start loses it:
python3 linkbuilding/pipelines/01_source.py export-state
```

Two rules the script asserts on the database and exits 1 if it broke either:

- **Expired items stay NULL.** No value in a title for a query nobody can
  answer, and filling them inflates the count of rows that look draftable.
- **Only platforms whose digest carries a real title header are filled** —
  HARO, SOS, Qwoted. **Connectively is excluded**: its digest has no title
  field, so its parser `summary` is a 140-char excerpt of the query body, and
  using that would be inferring a title from query text. Costs nothing —
  `build_draft_args()` refuses Connectively items anyway.

⚠️ **`export-state`, not `rescore`.** `rescore` also exports but re-decides
every bucket on the way through. After an out-of-band correction you want the
state file refreshed and nothing else.

⚠️ **`links.db` is gitignored; `source-state.json` is not.** A Routine-fired
run can commit rows this checkout has never seen, and exporting from a stale
database would delete them silently. `export-state` refuses to write when the
database is missing anything the committed state holds. If it refuses, run
`rebuild.py run --force` (or re-import the state file), re-apply your change,
then export again.

⚠️ **Live digests are CRLF; the committed samples are LF.** Any new
whitespace-sensitive parser rule must be tested against both — `self-test`
parses the whole HARO corpus in both line endings for exactly this reason.

### Detecting the send

`detect-sends` reads Sent mail for messages to known `reply+` addresses and
records those items sent with the actual send time. **Read-only on Sent.** This
replaces the manual `sent --key` step for HARO items — the send already
happened in Gmail, and asking a human to also type it into a CLI is the step
they skip on the day it matters.

Absence from Sent means nothing was **found**, never that nothing was sent.

⚠️ **No wildcard in a Gmail address term.** The query was
`in:sent to:reply+*@helpareporter.com`, which Gmail does not support: it
matched nothing against a mailbox that held the send. It is now
`in:sent to:helpareporter.com`, with the `reply+<uuid>` shape enforced by
regex in `find_sent` where a regex can actually do it. An empty result reads
exactly like "nothing was sent", so this was a silent false negative.

### What went out is stored, not what was drafted

`detect-sends` stores the **body read back from Sent** on the send record, and
keeps the queued draft beside it:

| Field | Meaning |
|---|---|
| `sent_body` | the text the journalist actually received — what outcomes attribute to |
| `drafted_body` | what the pipeline had queued for that item |
| `divergence` | `diverged`, `similarity`, and a unified diff |

Whitespace is normalised **for comparison only**; a rewrapped paragraph is not
an edit. `diverged` is `None`, never `False`, when no queued draft exists —
"no draft on file" and "the draft matched" are different facts.

A sent message does not change, so a later read returning **different** text is
not a correction: the first capture stands and the conflict is appended to
`sent_body_conflicts` for a human. Overwriting would destroy the only copy of
what was sent.

Measured on the first real send: **23% similarity** to the queued draft. That
diff is the signal on how the drafter should change, and it is why the sent
body is stored rather than assumed.

### Delivery is tri-state, and `True` is never assumed

`delivered` is `None` by default. HARO issues **no delivery receipt**, so the
absence of a bounce is not evidence of arrival. Only a non-delivery notice —
read from mail, sender checked, matched against a closed set of markers — ever
sets it `False`, with the stated reason recorded as written.

An undelivered pitch is taken **out of the fair-try denominator** in
`summarise()` and the outcomes report. It measures a delivery problem, not the
drafting, and counting it as a pitch nobody used would report the drafter as
performing worse than it did.

```bash
python3 linkbuilding/pipelines/01_source.py detect-sends \
    --payload <in:sent to:helpareporter.com> \
    [--notices <from:helpareporter.com in:anywhere>]
```

`--notices` is optional; without it the same payload is scanned for both.

## The loop: sent → published → linked (Round 14)

**This replaces answerable-rate as the headline metric.** Answerable was always
a proxy — a guess about what a journalist might use. This measures what they
did.

**Recording a send.** The human sends; the pipeline never does. The mechanism
is a **CLI command writing a committed file**:

```bash
python3 linkbuilding/pipelines/01_source.py sent \
  --key <item key from the queue> --from media@inhousewellness.com [--at ISO]

python3 linkbuilding/pipelines/01_source.py outcome \
  --key <item key> --url <published URL> [--at ISO]
```

`data/sends.json` is the durable store; the commands are the doors. They
validate, they are idempotent on the item key, and the file stays hand-editable
for corrections. A hand-edited JSON file alone was rejected: a trailing comma
at the busiest moment loses the only record of what went out.

**A sent item drops from the draft queue and is never re-surfaced.**

**Statuses are `pending` and `published`. There is no third.** A pitch nobody
answered stays `pending` indefinitely and is never counted as a failure —
publication is never inferred from silence, and no rate treats pending as a
rejection.

### The weekly check

```bash
python3 linkbuilding/pipelines/01_source.py outcomes   # writes reports/outcomes.md
```

⚠️ **There was no weekly verify job in `linkbuilding` before Round 14.**
`00_audit` exists but nothing schedules it. This command *is* the weekly job
and **is not attached to a Routine yet** — that is an open item, not something
quietly assumed to be running. Until it is scheduled, `last_checked` is the
honest record of when anything was actually looked at.

### Two routes to "is there a link", because one of them is blocked here

| Route | How | Works in this environment? |
|---|---|---|
| Page fetch | GET the published URL, parse anchors, record `rel` as written | ❌ **No** — the network policy denies CONNECT to publisher domains (403). Verified against healthline.com and eatthis.com. |
| Backlink audit | `00_audit`'s referring-domain pull, which goes through an MCP tool | ✅ Yes — confirmed the eatthis link with `rel=follow` |

**A failed fetch never sets `linked: false`.** "We could not look" and "it is
not there" are different facts, and recording the first as the second would
mark real earned links as missing. The audit route only ever *upgrades* a
record; it can establish a link, never erase one.

A plain-text mention of the domain is **not** a link. The anchor has to be in
the markup.

## Posting drafts to #media

**Every new draft goes to `#media` in full — the text itself, not a link.** A
link means opening a repo to copy a paragraph, and the person doing that is
usually on a phone with a four-hour deadline.

```bash
python3 linkbuilding/pipelines/01_source.py draft         # build the queue
python3 linkbuilding/pipelines/01_source.py post-drafts   # write unposted bodies
# post each body to #media (C0C26J8JX8U), then:
python3 linkbuilding/pipelines/01_source.py posted --key K --ts TS --link URL
```

Each post carries outlet, deadline and hours remaining, platform, reply path
(or "submit via Connectively — no reply address"), regime and framing, the
citations with PMIDs, whether it needs Dr. Alptunaer's review, and — listed
separately — **the experience statements awaiting his confirmation**.

**Deduped on item key AND content hash** (`data/posted-drafts.json`). Posting
the same pitch on every queue regeneration is how a channel becomes noise; but
keying on the item alone means a *corrected* draft never reaches the channel
and someone pastes the stale copy. A materially changed draft reposts once,
marked **REVISED** and naming the post it supersedes.

## Experience statements: flagged, not removed

The drafter writes first-person clinical experience in his voice — "the
presentations I see in the ED" — and those sentences are what make a pitch
land. **They are also the only text in a draft that nothing verifies.** A
citation checks a literature claim; there is no equivalent check for a claim
about his own practice, and until Round 15 the two sat in the same paragraph
and read identically.

| Unit | Verified by | Marked with |
|---|---|---|
| `assertions` | a citation resolved at draft time | `(PMID …)` |
| `experience_statements` | **nothing** — only his confirmation | `[CONFIRM: experience]` |

- Every unconfirmed experience sentence carries a visible `[CONFIRM: experience]`
  in the draft text and is listed separately in the Slack post.
- **A draft cannot be marked ready-to-send while any flag remains.**
  `assert_ready_to_send()` raises. *Pitchable* (may be queued and shown) and
  *ready-to-send* are deliberately different gates.
- Flags are stripped by **his confirmation and nothing else**:
  `01_source.py confirm-experience --key K --all` (or `--index N`). Never
  remove them by hand.
- **The sentences are not deleted.** They make pitches land; the fix is that
  they are reviewable, not that they are gone.

⚠️ Splitting these out was not cosmetic. It found experience claims riding
*inside* cited sentences — "The bigger concern **I see clinically** is
contamination…" sat in an assertion whose PMID supports the adulteration fact
and nothing about his clinical impression. It also found "stop it several days
before scheduled bloodwork", which sat next to a citation that does not state
that interval.

⚠️ **Tokens are scrubbed before anything is posted.** Connectively's deadline
line carries a single-use magic-link auth token, and it reached the Slack
renderer through the parser. Fixed at the parser, and the renderer scrubs
`token=` and bare URLs out of field values anyway — a Slack post is visible to
the whole channel and permanent, so this is defence in depth, not tidiness.

## The routines

| Routine | Cron (UTC) | Runs/day | Trigger ID |
|---|---|---|---|
| `01_source` media scan | `37 11,18,21 * * *` | 3 | `trig_01JTW5ufQ4xb4fvmS2G2TwSX` |
| Weekly outcome check | `15 9 * * 1` (Mondays) | 1, Mondays only | `trig_01KYk42V6YxEkmW6SUDGwCeb` |

**Peak: 4 runs on Mondays, 3 every other day.**

⚠️ **The weekly routine has NO connectors attached** (`mcp_connections: []`).
Connectors are not API-attachable for this organisation — the Round 6 finding,
unchanged. **Zapier and Slack must be attached in the claude.ai Routines UI
before it can run.** Until then every Monday firing will start a session with
no Slack and no Gmail.

## The decision this is all feeding — RECALIBRATED (Round 7 §5)

### ✅ The 14-day clock STARTED 2026-09-15

**Clock start: 2026-09-15 21:07 UTC — the first HARO query digest.** The
`media@` verification mail arrived 18:37 the same day and the first digest
followed 2.5 hours later, so the signup is verified and the channel is live.
HARO has since sent three digests a day without a gap.

Everything in the section below is kept because it explains *why* the clock
starts here rather than at the first run — but the blocking condition is
cleared.

<details><summary>Superseded — the pre-2026-09-15 state</summary>

**It starts on the first HARO query digest, not on the first run.** As of
2026-09-15, no HARO query digest has ever arrived at any address in this
mailbox. The only HARO mail is five account-lifecycle messages, captured in
`data/samples/`:

| Date | To | Subject |
|---|---|---|
| 2026-01-12 | julian@ | Your sign up link |
| 2026-01-13 | julian@ | Your HARO **Journalist** Profile Is Ready to Claim |
| 2026-01-21 | julian@ | Your sign in link |
| 2026-09-14 | media@ | Your Featured sign-in link |
| 2026-09-15 | media@ | **Welcome to HARO – Please Verify Your Email** |

Two things follow. The January signup is on `julian@`, which is not in
`EXPECTED_RECIPIENTS`, and the profile offered was a **journalist** profile,
not a source profile — a journalist profile receives no query digests. And the
`media@` signup is **still unverified**: the verification mail arrived
2026-09-15 18:37 UTC and the link has not been clicked. That is the open item
blocking everything below.

</details>

### Why zero from SOS and Qwoted proves nothing

All four proven links — healthline DR91, eatthis DR83, womansworld DR66,
singlecare DR63 — have `first_seen` between 2026-01-20 and 2026-07-02, all in
the Featured-operated HARO era, and all through a former contractor's own
account. **Not one came through SOS or Qwoted.**

So counting SOS-and-Qwoted days toward fourteen would measure two channels that
have never produced a link, and then draw a conclusion about a third. A zero
result currently reads as *a live channel not reaching this inbox* — plumbing,
not a dead niche.

### Expected order of magnitude

One link per six weeks, from a pitch volume necessarily higher than four. That
implies **a handful of answerable items per month — single digits, low ones.**
Not per day, and not per run.

**Zero answerable on any given day is the expected result and is not a signal.
A week of zeros is not a signal either.** What would genuinely condemn the
pipeline is a month of HARO digests arriving and filtering to zero.

### Assess after 14 days OF DIGESTS

| After 14 days of digests | Conclusion |
|---|---|
| ≥2 answerable per month | `01_source` earns its place. Build the drafter. |
| Answerable but all Qwoted | Evaluate Qwoted Pro ($149/mo); the free tier's 7 pitch credits and request delay become binding. |
| Zero answerable, marginals clustering in one topic | The gap is in the claim bank, not the pipeline. |
| Zero answerable, marginals scattered | The niche is quiet. Keep the filter cheap; put effort into dealer pages and outreach. |
| High `deadline misses on arrival` | The pipeline is finding real requests too late. Check this row before concluding the niche is quiet. |
| **No digests arriving at all** | The live row. A plumbing problem; none of the five above apply. |

---

## The four channels

Routing is by **sender**, never subject (inherited rule 5). Reply paths differ
per platform and that difference is a property of the product, not of the
parser:

| Channel | Sender | Shape | Reply path | Manual? |
|---|---|---|---|---|
| **HARO** | `helpareporter.com` | newsletter, 3 digests/day, ~20 queries each | `reply+<uuid>@helpareporter.com`, one per query | **no** |
| SOS | `sourceofsources.com` | newsletter digest | journalist address in the digest | no |
| **Connectively** | `connectively.us` | platform alert digest | single-use magic-link auth redirect | **yes** |
| Qwoted | `qwoted.com` | one request per email | per-recipient click redirect | yes |
| Featured | `featured.com` | auth mail only, never a digest | — | n/a |

**HARO is the one that matters.** All four proven links came through it, and
the direct reply mailbox is why: no account, no dashboard, no click-through.

**No address is ever constructed.** A reply address is recorded only when it is
present in the mail. Connectively's magic-link is an authentication redirect,
not a reply path; the only addresses ever seen on Connectively are third-party
`send+<id>@tmxmessenger.com` relays on syndicated *opportunity* items, never on
its own Q&A items. `01_source` raises if a Connectively row is ever marked
non-manual without one.

**Both new parsers guard the same trap SOS taught.** Journalists write
label-shaped lines inside their query prose — `Clinical Implications:`,
`Questions include:`, `Note:` — and an open `^Word:` regex eats them as fields.
Both parsers use a **closed alternation** over the real field names, with an
assertion after parsing that re-checks it.

## The clinical vocabulary is DERIVED from the bank (Round 10)

**A filter term that no claim backs cannot match.** This is a code gate, not a
convention: `01_source.py` reconciles its candidate term lists against
`claims.json` at load time and drops anything unbacked before it can match.

Round 9 caught the pipeline printing *"modality ['infrared'] named; the claim
bank covers this directly"* for a term in zero of 30 claims. Two lists
maintained by different hands will always drift; the only fix that holds is for
one to be computed from the other.

| Source | Counts as backing? | Why |
|---|---|---|
| claim text, hedge, citation titles | **yes** | what the claim asserts |
| `do_not_say` | **no** | what it FORBIDS. `cold plunge` appears in the bank *only* here |
| `topics` | **no** | an index label, not a statement. `hydration` is a topic on claims whose text never mentions it |

**11 of 38 candidate terms (29%) are orphaned and removed** — see
`reports/filter-bank-reconciliation.md` for the full list and the three
different fixes they need. **No claim was added to the bank**; it is awaiting
signature and writing into it outside that process would make the signature
meaningless.

Check the reconciliation any time:

```bash
python3 linkbuilding/pipelines/lib/claims.py synonyms   # exit 3 if orphans exist
```

⚠️ **Clinical answerable across the whole corpus is 0** and has effectively
always been. The one recorded match was `infrared` — a vocabulary accident with
no claim behind it. The clinical filter has never matched a request the bank
could answer.

## The expert roster — two people, two evidentiary regimes

See `data/experts.json`.

| Expert | Regime | Source | Status |
|---|---|---|---|
| Dr. Timur Alptunaer, MD | cited | `data/claims.json` | `awaiting_review` |
| — **specialty** | **Emergency Medicine** (General EM) | | reachable HARO requests: 9 → **17 of 112** |
| Tripler (health coach, MSc Org Behaviour) | experience-based | none, by design | provisional, `approved: false` |

### HARD RULE — the BYLINE (Round 11)

His credential line is a **verbatim literal**, stored once in `experts.json`:

```
Timur Alptunaer, MD, RN, EMT-T, FACEP
```

**It is never reconstructed, abbreviated, reordered or expanded.** There is
deliberately no code path that assembles it from parts, because a builder is a
thing that can build it wrong — drop the RN, reorder the post-nominals, expand
FACEP — and each of those misstates a real person's credentials.
`assert_pitchable()` requires exact string equality; an item cannot be marked
pitchable without it, and `mark_pitchable()` is the only door.

**The guard blocks the DESCRIPTION, not the subject matter.** Confusing the two
would throw away most of what he can do. He is willing to speak outside his
clinical practice; the condition is that the byline must not misrepresent him.

| | |
|---|---|
| A pitch **about** dermatology | ✅ fine |
| "Dr. Alptunaer, **a dermatologist**" | ❌ blocked |
| "Alptunaer, a **skin expert**" | ❌ blocked |
| "**sleep specialist**", "specialist in X" for any X | ❌ blocked |
| "Dr. Alptunaer, an **emergency medicine physician**" | ✅ the one permitted expansion |

`assert_attribution_safe()` matches descriptor *shapes* — `X-ologist`,
`board-certified X`, `specialist in X`, `X expert`, `professor of X`, `chief of
X`, `X physician` — within 140 characters of his name, rather than keeping a
list of specialty nouns that would never be complete.

**Framing.** A pitch drawing on the claim bank is framed as *published evidence
he is interpreting*; one drawing on the experience set is framed as *clinical or
personal experience*. Both carry the same credential line, and `framing` is
required on every pitchable item.

⚠️ **Observation for a human, recorded and NOT acted on:** EMT-T is tactical
EMT, directly relevant to the military and sports-performance topics in the
experience set. Nothing widened scope automatically and no filter term was added
from it — see `observations_for_human` in `experts.json`.

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
- ✅ **RESOLVED — HARO is verified and delivering.** First digest 2026-09-15
  21:07 UTC, 2.5 hours after the verification mail. Three a day since, no gap.
  The January `julian@` profile was a **journalist** profile and remains
  irrelevant; the working signup is the source profile on `media@`.
- ✅ **RESOLVED — HARO and Connectively parsers exist** (Round 8), tested
  against 8 and 2 real digests. `Media/Featured` is **kept, not retired**:
  Featured and Connectively are the same product but still send from different
  domains (`featured.com` vs `connectively.us`), and featured.com has only ever
  sent auth mail. Deleting the route would mean a Featured-domain digest lands
  nowhere and counts as nothing.
- 🟡 **HARO repeats queries across its three daily editions — 31% duplication**
  (162 rows, 112 distinct reply addresses). The dedup key is per-digest
  (`haro:<gmail_id>:<item_no>`) and cannot see across editions, so row counts
  overstate opportunities. The trend report shows rows AND distinct requests
  side by side rather than picking one. Cross-edition dedup was NOT built —
  out of Round 8's scope, and changing the dedup key changes what every
  historical count means. Proposed for Round 9.
- 🟡 **Zero clinical answerables in 162 HARO items.** Dr. Alptunaer drew 14
  *marginal* on HARO and nothing answerable; the single clinical answerable in
  the whole corpus came from Connectively (red light therapy / `infrared`).
  All 11 HARO answerable rows are Tripler-provisional, and most matched on the
  bare word `founders` — including a "Holiday Stocking Stuffers" gift-guide
  request. That is the same single-generic-anchor failure `employees` produced
  in Round 6. The filter was **not** tuned in Round 8: tuning it to change a
  count is the one thing this project forbids, and the anchor list is exactly
  what Tripler's review document asks her to fix.
- Five paid-pattern links remain `unresolved` pending human provenance check.
