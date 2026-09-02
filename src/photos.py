"""Image band sourcing for the Band card direction.

Every Band card carries a photograph across the top third. Sourcing order per
the brief:
  1. Unsplash MCP  -- NOT CONNECTED as of 2026-09-02 (verified against the
     connector registry; no unsplash tool is installed)
  2. the user's own Golden Designs footage -- not yet supplied

NEVER manufacturer product photography: it is indexed on dozens of dealer sites
and carries no uniqueness signal.

Until a source is connected, `brief_for` returns the shot the card needs and the
renderer draws the design bundle's labelled photo well. That is the design's own
treatment for this state -- a card that names the image it is missing, not a card
pretending it has one.

Constraints from the design notes, carried here so a future sourcing step
inherits them: low-key, warm light in one band, no people under 40, no
towel-on-shoulder or meditation clichés. The band is a horizontal strip -- check
the crop at the real aspect before accepting an image.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "photos.json"
NO_REPEAT_DAYS = 30

# Shot brief per cluster. Written as the photographer's instruction, so the
# placeholder states what it holds.
BRIEFS = {
    "emf": "Photo: heater panel close-up, warm low-key light, no people",
    "electrical": "Photo: open stud wall with sauna rough-in and a breaker panel, one frame",
    "fit": "Photo: cedar cabin in a real room with the surrounding wall visible for scale",
    "cost": "Photo: utility meter and the cabin control panel in one frame",
    "infrared_compare": "Photo: infrared cabin and steam room in the same house, one frame",
    "cold_plunge": "Photo: plunge tub rim and chiller line, cold blue light, no people",
    "hot_tub": "Photo: hot tub and sauna cabin sharing a deck, dusk, no people",
    "outdoor_steam": "Photo: outdoor cabin in winter light, snow on the roofline",
    "evidence": "Photo: bench thermometer and a notebook, warm low-key light",
    "brands": "Photo: cabin joinery detail, raking light across the grain",
    "commercial_install": "Photo: multi-cabin install in a commercial room, no people",
}
DEFAULT_BRIEF = "Photo: cedar grain and warm low-key interior light, no people"


def brief_for(row):
    """The shot this card needs."""
    return BRIEFS.get(row.get("cluster") or "", DEFAULT_BRIEF)


def _load():
    if not CACHE.exists():
        return {"images": {}}
    try:
        return json.loads(CACHE.read_text())
    except json.JSONDecodeError:
        return {"images": {}}          # a corrupt cache contributes nothing


def available(today=None):
    """Cached images not used within NO_REPEAT_DAYS. Empty until a source is wired."""
    today = dt.date.fromisoformat(today) if today else dt.date.today()
    out = []
    for url, meta in _load()["images"].items():
        used = meta.get("last_used_on")
        if used and (today - dt.date.fromisoformat(used)).days < NO_REPEAT_DAYS:
            continue
        out.append({"url": url, **meta})
    return out


def image_for(row, today=None):
    """Return (url, attribution) or (None, None) when no source is connected."""
    pool = [i for i in available(today) if i.get("cluster") == row.get("cluster")]
    if not pool:
        return None, None
    pick = pool[0]
    return pick["url"], pick.get("attribution")
