#!/usr/bin/env python3
"""Round 19 — tell a human when the unattended system stops.

An unattended system that halts silently is indistinguishable from one that
stopped working, which is how this account went nine days silent in September
without anyone noticing until it was raised.

Transport is a Slack incoming webhook in SLACK_WEBHOOK_URL. If it is absent the
message is PRINTED and the exit code is unchanged -- a missing webhook must
never turn a healthy run red, nor a failed run green.

  python3 scripts/notify.py --level blocked --title "..." --body "..."
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Harness Slack protocol: 🔴 BLOCKED, 🟡 REVIEW, ⚪ FYI.
PREFIX = {"blocked": "🔴 BLOCKED", "review": "🟡 REVIEW", "fyi": "⚪ FYI"}


def send(level, title, body, *, webhook=None, opener=None):
    prefix = PREFIX.get(level, PREFIX["fyi"])
    text = f"*{prefix} — {title}*\n{body}" if body else f"*{prefix} — {title}*"
    hook = webhook if webhook is not None else os.environ.get("SLACK_WEBHOOK_URL", "")
    if not hook.strip():
        # Not a failure. Say so plainly rather than implying it was delivered.
        print(f"[notify] no SLACK_WEBHOOK_URL set — message NOT delivered:\n{text}")
        return False
    req = urllib.request.Request(
        hook, data=json.dumps({"text": text}).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=30) as r:
            ok = 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        print(f"[notify] webhook returned HTTP {e.code} — message NOT delivered")
        return False
    except Exception as e:
        print(f"[notify] webhook failed ({type(e).__name__}) — message NOT delivered")
        return False
    print(f"[notify] delivered: {prefix} — {title}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=sorted(PREFIX), default="fyi")
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", default="")
    a = ap.parse_args()
    send(a.level, a.title, a.body)
    # Always 0: notification is reporting, never a gate on the work it reports.
    return 0


if __name__ == "__main__":
    sys.exit(main())
