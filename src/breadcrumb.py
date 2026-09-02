"""D5 duplicate-post protection.

A breadcrumb is written BEFORE any publish attempt and cleared only after the
post id is captured. If a run starts and finds an uncleared breadcrumb, the
previous run died between "about to publish" and "confirmed published" -- the
post may or may not be live, and republishing would duplicate it forever.

So: HALT, loudly, and make a human look. Never auto-clear.

Enforced in CODE, as a gate -- not as guidance to a model.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

BREADCRUMB = "state/publishing.breadcrumb.json"


class DuplicateRisk(Exception):
    pass


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def check(path=BREADCRUMB):
    """Call at the START of every run, before anything else."""
    p = pathlib.Path(path)
    if not p.exists():
        return None
    try:
        crumb = json.loads(p.read_text())
    except json.JSONDecodeError:
        raise DuplicateRisk(
            f"HALT: a breadcrumb exists at {path} but is unreadable. A previous run "
            f"died mid-publish. Check the platforms for a live post before clearing it.")
    raise DuplicateRisk(
        f"HALT: uncleared breadcrumb from {crumb.get('written_at')} — a previous run "
        f"began publishing {crumb.get('order_id')} to {crumb.get('platform')} and never "
        f"confirmed. The post may already be live. Check the platform, then delete "
        f"{path} by hand. Never auto-clear this.")


def drop(order_id, platform, path=BREADCRUMB):
    """Write BEFORE attempting to publish. Atomic."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(
        {"order_id": order_id, "platform": platform, "written_at": _now()}, indent=1))
    tmp.replace(p)
    return p


def clear(path=BREADCRUMB):
    """Call ONLY after the real post id has been captured."""
    p = pathlib.Path(path)
    if p.exists():
        p.unlink()
