#!/usr/bin/env python3
"""
relay.py — hand the Gmail payload from an agent session to the pipeline.

WHY THIS EXISTS AS CODE RATHER THAN A HABIT
  Gmail is an MCP tool and MCP exists only inside an agent session, so the
  agent must fetch and the script must process. The payload is ~638KB, which
  is far too large to return through the tool channel: it lands in a
  tool-results file on disk and the path is all the agent gets back.

  In Round 4 that copy was a manual step. A manual step in a pipeline that is
  about to run unattended every day is a silent failure waiting to happen —
  the specific failure being a run that finds no file, processes nothing, and
  reports a quiet zero. This project has already shipped that exact bug once:
  an empty result from the wrong mailbox read as an empty inbox.

  So: every failure here RAISES. There is no path that returns an empty
  payload and lets the caller continue.
"""

import json, os, shutil, time

class RelayError(Exception):
    """Any failure to obtain a usable payload. Never caught internally."""


# A payload smaller than this is not a real Media/* pull. The smallest
# observed real payload was ~72KB (3 messages); a single message is ~25KB.
MIN_PLAUSIBLE_BYTES = 10_000
MAX_AGE_SECONDS = 6 * 3600     # a payload older than this is a previous run's


def resolve(path, *, max_age_seconds=MAX_AGE_SECONDS, min_bytes=MIN_PLAUSIBLE_BYTES,
            now=None):
    """Validate a payload file path and return its parsed contents.

    Raises rather than returning anything falsy. Four distinct failures, each
    with its own message, because 'no items today' and 'the relay broke' look
    identical downstream and must never be confused.
    """
    if not path:
        raise RelayError(
            "no payload path given. The agent must fetch the Gmail payload "
            "first and pass the tool-results file path; the pipeline cannot "
            "call MCP itself.")
    if not os.path.exists(path):
        raise RelayError(
            "payload file does not exist: %s\n"
            "The agent's Gmail call either was not made or its tool-results "
            "file was not copied. This is NOT an empty inbox — do not report "
            "zero items." % path)
    size = os.path.getsize(path)
    if size < min_bytes:
        raise RelayError(
            "payload file is %d bytes (< %d), which is too small to be a real "
            "Media/* pull: %s\nA truncated or empty relay file must not be "
            "processed as a quiet day." % (size, min_bytes, path))
    age = (now or time.time()) - os.path.getmtime(path)
    if age > max_age_seconds:
        raise RelayError(
            "payload file is %.1f hours old (> %.1f), so it is a previous "
            "run's file: %s\nProcessing it would re-report yesterday's mail as "
            "today's and make the trend line lie."
            % (age / 3600.0, max_age_seconds / 3600.0, path))
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as e:
        raise RelayError("payload file is not valid JSON: %s (%s)" % (path, e))
    if not isinstance(payload, dict) or "results" not in payload:
        raise RelayError(
            "payload has no 'results' key — this is not a gmail_find_email "
            "response: %s" % path)
    return payload


def stage(src, dest_dir, *, name="gmail-payload.json"):
    """Copy a tool-results file into the working directory and return the
    path. Kept explicit so the copy is a recorded pipeline step rather than
    something a human remembers to do."""
    if not os.path.exists(src):
        raise RelayError("cannot stage: source does not exist: %s" % src)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name)
    shutil.copyfile(src, dest)
    return dest


def describe(payload):
    n = len(payload.get("results") or [])
    return "payload: %d message(s)" % n
