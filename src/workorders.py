"""Assemble the daily work orders. Pure code -- selection, dedup and routing.

This is the half of the cycle the model never sees. It picks which rows run
today, enforces cadence, dedup and the destination quota, and emits a compact
brief. Keeping this deterministic is what makes the model call cheap: the model
receives a short structured brief and returns only prose.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
from collections import Counter

from . import destinations as D

# Pinterest is throttled to 2/day, not the target 4, because only 24 queue rows
# survived the remap and 79 are blocked on a content gap (2026-09-01 decision).
# 24 rows at 2/day is ~12 days of runway -- enough to prove the pipe and start the
# 14-day zero-broken-post clock. Cadence is config: lift `pinterest` back to 4 the
# moment the content gap closes. Do not raise it to consume the queue faster.
CADENCE = {"pinterest": 2, "instagram": 1, "facebook": 1}
CADENCE_TARGET = {"pinterest": 4, "instagram": 1, "facebook": 1}
MAX_PER_DAY = 6
MIN_REPOST_DAYS = 120           # evergreen rows may recycle after this


def _today():
    return dt.date.today().isoformat()


def load_state(path="state/posting-state.json"):
    p = pathlib.Path(path)
    if not p.exists():
        return {"seen": {}, "published": [], "created_at": _today()}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        # Corrupt state HALTS. Never silently reinitialise -- that is how
        # duplicate history happens.
        raise SystemExit(f"HALT: state file {path} is corrupt ({e}). "
                         f"Investigate before running again; do not delete it.")


def save_state(state, path="state/posting-state.json"):
    """Atomic write: temp file then replace, so a crash mid-write cannot
    truncate the state."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(p)


def keyword_signature(keyword):
    """Normalised token set for near-duplicate detection.

    The queue contains many rows that are the SAME query reordered:
    "infrared vs steam sauna", "infrared sauna vs steam", "steam vs infrared
    sauna". Selecting two of them on one day puts near-identical pins on the same
    board, which reads as spam on a search surface and wastes a slot.

    Exact-text dedup cannot catch this -- the captions differ. It has to be caught
    at SELECTION, on the keyword itself.
    """
    stop = {"vs", "versus", "a", "an", "the", "of", "for", "to", "in", "is", "are",
            "and", "or", "do", "does", "you", "your", "i", "my", "it"}
    toks = [t for t in re.split(r"[^a-z0-9]+", (keyword or "").lower())
            if t and t not in stop]
    # Crude plural fold so "saunas" == "sauna" AND "tubs" == "tub". The length
    # floor is 4 (not 5): "tubs" is exactly four characters, and requiring five
    # left "hot tub vs sauna" and "hot tubs vs saunas" as distinct queries.
    toks = [t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t
            for t in toks]
    return frozenset(toks)


def dedup_key(platform, item_id):
    """One article may legitimately produce a pin, a Reel and an FB post."""
    return f"{platform}:{item_id}"


def eligible(row, platform, state, today=None):
    if row.get("status") != "queued":
        return False, "not queued"
    key = dedup_key(platform, row["id"])
    last = state.get("seen", {}).get(key)
    if last:
        if row.get("reuse_class") != "evergreen":
            return False, "timely row already used"
        days = (dt.date.fromisoformat(today or _today()) - dt.date.fromisoformat(last)).days
        floor = row.get("min_repost_days", MIN_REPOST_DAYS)
        if days < floor:
            return False, f"evergreen cooldown ({days}/{floor} days)"
    return True, None


def select(rows, state, cadence=None, today=None):
    """Choose today's rows per platform. Deterministic: priority, then id."""
    cadence = cadence or CADENCE
    today = today or _today()
    pool = sorted(rows, key=lambda r: (-(float(r.get("priority") or 0)), r["id"]))

    chosen, used_ids = {}, set()
    used_signatures = set()          # near-duplicate suppression, cycle-wide
    for platform, n in cadence.items():
        picks = []
        for row in pool:
            if len(picks) >= n:
                break
            if row["id"] in used_ids and platform != "pinterest":
                continue
            sig = keyword_signature(row.get("keyword"))
            if sig in used_signatures:
                continue             # same query, different wording
            ok, _ = eligible(row, platform, state, today)
            if ok:
                picks.append(row)
                used_ids.add(row["id"])
                used_signatures.add(sig)
        chosen[platform] = picks
    return chosen


def destination_for(row, platform):
    """Per-platform destination.

    A row's stored `link` is its default. Interactive assets are a per-platform
    preference: the Healthspan Habits Score carries a challenge-a-friend share
    mechanic, and sharing is native on Instagram and Facebook but not on
    Pinterest, which is a search surface. So the asset wins on the feeds and the
    row's normal destination wins on Pinterest.
    """
    asset = D.interactive_asset_for(row.get("keyword"), row.get("archetype"), platform)
    if asset:
        return asset[1], f"interactive: {asset[0]} (preferred on {platform})"
    return row.get("link"), row.get("destination_reason", "row default")


def build_work_orders(rows, state, cadence=None, today=None):
    """Return the compact brief the model call consumes, plus the full orders."""
    today = today or _today()
    chosen = select(rows, state, cadence, today)

    orders = []
    for platform, picks in chosen.items():
        for row in picks:
            link, why = destination_for(row, platform)
            orders.append({
                "order_id": f"{today}:{platform}:{row['id']}",
                "platform": platform,
                "item_id": row["id"],
                "keyword": row["keyword"],
                "archetype": row.get("archetype"),
                "cluster": row.get("cluster"),
                "evidence_tier": row.get("evidence_tier", "moderate"),
                "source_article": row.get("source_article"),
                "source_title": row.get("source_title"),
                "link": link,
                "link_domain": D.domain_of(link),
                "destination_reason": why,
                "board_id": row.get("board_id"),
                "board": row.get("board"),
                "volume": row.get("volume"),
            })

    total = len(orders)
    if total > MAX_PER_DAY:
        raise SystemExit(f"HALT: {total} orders exceeds max_posts_per_day_total={MAX_PER_DAY}")

    audit = D.audit([o["link"] for o in orders if o.get("link")])
    return orders, audit


def brief_for_model(orders):
    """The ONLY thing the model sees. Deliberately tiny -- no article bodies,
    no HTML, no analytics. One compact record per post."""
    return [{
        "order_id": o["order_id"],
        "platform": o["platform"],
        "keyword": o["keyword"],
        "archetype": o["archetype"],
        "evidence_tier": o["evidence_tier"],
        "source_title": o["source_title"],
        "destination": o["link_domain"],
    } for o in orders]
