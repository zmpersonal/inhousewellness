# Link Building — HANDOFF

Current as of 2026-09-14, end of Round 1.

## State

`00_audit` is built and passing. The backlink profile is classified, snapshotted
and diffable. Nothing has been sent to anyone; no outreach exists yet.

| Metric | Value |
|---|---|
| Referring domains (reported) | 66 — never the number to report |
| Referring domains (earned) | **17 confirmed, 23 ceiling** |
| Domain Authority | 18 |
| Velocity used this week | 0 of 8 |
| Pipelines built | `00_audit` only |

## Re-running the audit

Two MCP calls, then one command. The script does everything else.

```
1  (agent) backlinks_overview(domain="inhousewellness.com")          -> overview.json
2  (agent) backlinks(domain="inhousewellness.com", mode="domain",
             one_per_domain=true, limit=70)                          -> backlinks.json
   # retry once if it returns {"done": false, "backlinks": []}
3  python3 pipelines/00_audit.py run --overview <f> --backlinks <f>
```

It stops itself rather than producing a wrong answer if any class diverges from
`BASELINE` by more than ±1, or if fewer than 60 referring domains come back.
**If it stops, the rules are wrong — diagnose them. Do not edit `BASELINE`.**
That constant caught two real bugs on the first live run.

`python3 pipelines/00_audit.py self-test` checks the diff logic and the Hard
Rule 8 guard without needing live data.

## Open decisions for a human

1. **Provenance of five paid-pattern links** — `momdaughts.com`,
   `journalismband.com`, `morpheus8london.com`, `lumiluxlimited.com`,
   `functionalacademy.org`. Three point at the same red-light-therapy article
   with mid-sentence phrase anchors. Held as `unresolved`. If clean, earned
   rises to 22. **Only someone who knows whether these were paid for can answer.**
2. **`xwifkv-j0.myshopify.com`** — owned, affiliate, or unrelated.
3. **Canonical NAP** (`data/identity.json`) — still missing, and the local
   aggregators already assert an Austin, TX address. Blocks citation work.
4. **Two domains lost since September** — unrecoverable; no snapshot existed.
   Now closed going forward.

## Next round

`01_source` is the priority per `CLAUDE.md` — journalist request monitoring.
All four links that matter came from that one tactic. Do not start it without
resolving Dr. Alptunaer's review cadence (daily or weekly), which decides
whether requests route to him or to the outreach lead.

## Standing prohibitions

Facebook Groups stay manual. Never send — every pipeline drafts. Never propose
a network link; `arcticsoak.com` and `commercialinfraredsauna.com` are
quarantined. Disavow file is a prepared artifact, not a recommended action.
