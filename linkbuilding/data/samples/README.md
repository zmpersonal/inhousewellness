# Media inbox samples — parser ground truth for Round 4

Captured 2026-09-15 from `julian@inhousewellness.com`. Read-only: nothing was
archived, marked read, labelled, or replied to.

Everything is unmodified except credential redaction — magic sign-in links,
verification tokens and confirmation tokens are replaced with
`[REDACTED-CREDENTIAL]`. Nothing else was touched; the per-recipient Qwoted
click-tracking URLs are left intact because the reply path's shape is exactly
what the parser has to handle.

---

## Three rules Round 4 inherits

These came out of a failed run on 2026-09-14 where the task reported an empty
inbox that was in fact a wrong-mailbox read. They are not style preferences.

### 1. Verify access with a live call. A flag read is not evidence.

Zapier reported `is_stale: false` on a connection whose token was dead. It read
healthy until a real call exercised it, then flipped to `true`. **Never accept
a status field as proof of access.** Make a call that returns data and check
the data.

### 2. Pin `connection_id` on every Gmail call, and assert the account on the
### response — not the request.

The Zapier default connection for this account is
`support@inhousewellness.com`, **not** the mailbox this pipeline needs. A call
that omits `connection_id` silently reads the wrong mailbox and returns
`{"results": []}` — a success, not an error, and indistinguishable from an
empty inbox.

```
connection_id: 029715c5-3a50-8935-b200-6e6eba55ac62   # julian@inhousewellness.com
```

Assert on what comes back. Every message must carry
`Delivered-To: media@inhousewellness.com` in `raw.payload.headers`. Checking
the request you sent proves nothing; check the response.

### 3. Scope queries on label AND recipient. Treat an unexpected zero as a
### connection fault until proven otherwise.

Everything the pipeline needs is addressed to `media@inhousewellness.com` and
labelled `Media/*`:

```
label:Media/Qwoted to:media@inhousewellness.com
```

**A query that should return rows and returns zero is a signal, not a result.**
Before reporting an empty label, re-run without the recipient filter and
confirm against the label list. On this run that discipline is what separated
"`Media/Featured` is empty" (true) from "we are reading the wrong mailbox"
(what it looked like).

---

## What is here

| File | Platform | Type |
|---|---|---|
| `qwoted-request-2026-09-15-vice.txt` | Qwoted | media request |
| `qwoted-noise-2026-09-14-welcome.txt` | Qwoted | platform noise |
| `sos-2026-09-15-morning.txt` | Source of Sources | digest, send 1 of 2 |
| `sos-2026-09-15-afternoon.txt` | Source of Sources | digest, send 2 of 2 |
| `sos-2026-09-14-welcome.txt` | Source of Sources | platform noise |
| `haro-2026-09-15-verify.txt` | HARO | platform noise |
| `featured-2026-09-14-signin.txt` | Featured | platform noise |

**Both SOS digests received to date are captured, not a sample of one.** SOS
sends up to three times daily; two arrived on 2026-09-15 (morning and
afternoon) and their structure is identical — see the structural notes in the
run report. One digest would not have shown that.

No Featured or HARO *request* sample exists yet, because neither platform has
sent one. The only mail from either is onboarding. Round 4 cannot write a
tested parser for those two on this evidence.

## Label reality vs. expectation

`Media/Featured` exists as a label but holds zero messages. Featured's only
email landed on the bare `Media` parent, as did the SOS welcome and the Qwoted
confirmation. **Sub-label filters are not catching everything** — a parser
scoped strictly to `Media/*` sub-labels will miss mail that lands on `Media`.
