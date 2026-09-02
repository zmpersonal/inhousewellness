"""Structured fact layer.

Exact numbers parsed from the network's published datasets. The caption
generator may CITE these; it must never invent one.

Round 4 wrongly concluded the satellites yield no numbers. The failure was the
tool: `blotato_create_source` is an LLM summarizer, not a scraper. It read prose,
wrote prose, and truthfully reported that its own output had no figures. The
underlying data was published as CSV and JSON the whole time.

Rule: create_source is for PROSE CONTEXT ONLY. Never source a number from it.
"""
from __future__ import annotations

import json
import pathlib
import statistics
from collections import Counter

# Anchored to the repo root, never the cwd. A cwd-relative cache silently
# returned None for every fact when run from scripts/ -- the same shape as
# load_dotenv() searching the cwd instead of the repo root.
ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "facts"


def _load(name):
    p = CACHE / f"{name}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None      # a corrupt cache contributes nothing; it never guesses


def _num(v):
    try:
        f = float(str(v).strip())
        return f
    except (TypeError, ValueError):
        return None


def _fmt(x, unit="", dp=0):
    if x is None:
        return None
    s = f"{x:,.{dp}f}"
    return f"{s}{unit}"


def emf_facts():
    """EMF cluster: what the 90 indexed models actually claim."""
    d = _load("bhis_saunas")
    if not d:
        return None
    rows = d["rows"]
    labelled = [r for r in rows if (r.get("emf_label") or "").strip()]
    claims = Counter((r.get("emf_label") or "").strip() for r in labelled)
    with_number = [r for r in rows if (r.get("emf_claim") or "").strip()]
    with_distance = [r for r in with_number if (r.get("emf_distance") or "").strip()]
    return {
        "source": d["url"], "fetched_at": d["fetched_at"],
        "models_indexed": len(rows),
        "models_with_an_emf_label": len(labelled),
        "models_with_a_numeric_emf_claim": len(with_number),
        "models_stating_the_measurement_distance": len(with_distance),
        "distinct_label_wordings": len(claims),
        "top_labels": claims.most_common(6),
        "note": ("An EMF claim without a stated measurement distance is not "
                 "comparable: field strength falls off sharply with distance."),
    }


def fit_facts(capacity=None):
    """Fit cluster: real dimensions by capacity, from the indexed models."""
    d = _load("bhis_saunas")
    if not d:
        return None
    rows = [r for r in d["rows"] if _num(r.get("width")) and _num(r.get("depth"))]
    if capacity is not None:
        rows = [r for r in rows if _num(r.get("capacity")) == float(capacity)]
    if not rows:
        return None
    w = [_num(r["width"]) for r in rows]
    dp = [_num(r["depth"]) for r in rows]
    h = [_num(r["height"]) for r in rows if _num(r.get("height"))]
    return {
        "source": d["url"], "fetched_at": d["fetched_at"],
        "capacity": capacity, "models": len(rows),
        "width_in": {"min": min(w), "median": round(statistics.median(w), 1), "max": max(w)},
        "depth_in": {"min": min(dp), "median": round(statistics.median(dp), 1), "max": max(dp)},
        "height_in": ({"min": min(h), "median": round(statistics.median(h), 1),
                       "max": max(h)} if h else None),
    }


def electrical_facts():
    """Electrical cluster: the 120V-vs-240V split that decides most installs."""
    d = _load("bhis_saunas")
    if not d:
        return None
    rows = d["rows"]
    volts = Counter(str(r.get("voltage") or "").strip() for r in rows if r.get("voltage"))
    def _volt(r):
        v = r.get("voltage")
        return str(v).strip() if v is not None else ""   # explicit: absent != "None"

    v120 = [r for r in rows if _volt(r) == "120"]
    v240 = [r for r in rows if _volt(r) == "240"]
    amps120 = [a for a in (_num(r.get("amps")) for r in v120) if a]
    amps240 = [a for a in (_num(r.get("amps")) for r in v240) if a]
    return {
        "source": d["url"], "fetched_at": d["fetched_at"],
        "models_indexed": len(rows),
        "models_120v": len(v120), "models_240v": len(v240),
        "voltage_breakdown": dict(volts),
        "amps_120v": ({"min": min(amps120), "median": statistics.median(amps120),
                       "max": max(amps120)} if amps120 else None),
        "amps_240v": ({"min": min(amps240), "median": statistics.median(amps240),
                       "max": max(amps240)} if amps240 else None),
        "note": ("A 120V unit runs from a standard outlet; a 240V unit needs a "
                 "dedicated circuit and a free double-pole breaker slot."),
    }


def price_facts(capacity=None):
    d = _load("bhis_saunas")
    if not d:
        return None
    rows = [r for r in d["rows"] if _num(r.get("price"))]
    if capacity is not None:
        rows = [r for r in rows if _num(r.get("capacity")) == float(capacity)]
    if not rows:
        return None
    p = sorted(_num(r["price"]) for r in rows)
    return {"source": d["url"], "fetched_at": d["fetched_at"],
            "models": len(p), "capacity": capacity,
            "price_usd": {"min": p[0], "median": statistics.median(p), "max": p[-1]}}


def climate_facts(city=None):
    """Running-cost and climate index across 75 US metros."""
    d = _load("outdoor_climate")
    if not d:
        return None
    rows = d["rows"]
    costs = [(_num(r.get("estimated_9kw_session_cost")), r) for r in rows]
    costs = [(c, r) for c, r in costs if c]
    if not costs:
        return None
    costs.sort(key=lambda t: t[0])   # sort on the cost only; dicts are not orderable
    picked = None
    if city:
        picked = next((r for _, r in costs if (r.get("city") or "").lower() == city.lower()), None)
    return {
        "source": d["url"], "fetched_at": d["fetched_at"],
        "metros_indexed": len(rows),
        "cheapest": {"city": costs[0][1]["city"], "state": costs[0][1]["state"],
                     "session_cost_usd": costs[0][0],
                     "cents_kwh": _num(costs[0][1].get("electricity_cents_kwh"))},
        "most_expensive": {"city": costs[-1][1]["city"], "state": costs[-1][1]["state"],
                           "session_cost_usd": costs[-1][0],
                           "cents_kwh": _num(costs[-1][1].get("electricity_cents_kwh"))},
        "median_session_cost_usd": round(statistics.median([c for c, _ in costs]), 2),
        "city": ({"city": picked["city"], "state": picked["state"],
                  "session_cost_usd": _num(picked.get("estimated_9kw_session_cost")),
                  "jan_normal_low_f": _num(picked.get("jan_normal_low_f")),
                  "cents_kwh": _num(picked.get("electricity_cents_kwh"))} if picked else None),
        "basis": "NOAA 1991-2020 normals and EIA electricity rates; 9 kW session",
    }


# cluster -> the fact bundle a caption for that cluster may cite
CLUSTER_FACTS = {
    "emf": emf_facts,
    "fit": lambda: fit_facts(2),
    "electrical": electrical_facts,
    "cost": climate_facts,
}


def for_row(row):
    """Structured facts a caption for this row may cite. Never invents."""
    cluster = row.get("cluster")
    fn = CLUSTER_FACTS.get(cluster) if cluster else None   # explicit: None never keys in
    if fn:
        f = fn()
        if f:
            return f
    kw = (row.get("keyword") or "").lower()
    if "emf" in kw:
        return emf_facts()
    if "dimension" in kw or "size" in kw:
        return fit_facts(2)
    if "electric" in kw or "circuit" in kw or "volt" in kw:
        return electrical_facts()
    if "cost" in kw or "price" in kw:
        return climate_facts()
    return None


def summary():
    out = {}
    for name in ("bhis_saunas", "outdoor_climate", "hrd_studies", "hrd_topics"):
        d = _load(name)
        out[name] = {"rows": d["row_count"], "fetched_at": d["fetched_at"]} if d else None
    return out


# ---------------------------------------------------------------------------
# source_data: a citable reference into the cached fact layer (Round 5, item 2)
#
# `source_article` existed to stop the model inventing figures. The fact layer
# does that better: exact data, a named dataset, and a fetch date. A row now
# qualifies if source_article OR source_data resolves.
# ---------------------------------------------------------------------------

def source_data_for(row):
    """Build a source_data reference for a row, or None if nothing fits.

    Returns {dataset, url, fetched_at, selector, facts} -- `facts` is the exact
    figure set the caption may cite verbatim and must not alter or extrapolate.
    """
    f = for_row(row)
    if not f:
        return None
    cluster = row.get("cluster") or ""
    kw = (row.get("keyword") or "").lower()
    if cluster == "fit" or "dimension" in kw or "size" in kw:
        selector = "besthomeinfraredsauna infrared_saunas.csv, capacity == 2"
    elif cluster == "emf" or "emf" in kw:
        selector = "besthomeinfraredsauna infrared_saunas.csv, all 90 models"
    elif cluster == "electrical" or "electric" in kw:
        selector = "besthomeinfraredsauna infrared_saunas.csv, voltage split"
    else:
        selector = "outdoorsteamsauna outdoor-sauna-index.csv, 75 metros"
    return {
        "dataset": f.get("source", "").rsplit("/", 1)[-1] or "unknown",
        "url": f.get("source"),
        "fetched_at": f.get("fetched_at"),
        "selector": selector,
        "facts": {k: v for k, v in f.items()
                  if k not in ("source", "fetched_at", "note", "basis")},
        "note": f.get("note") or f.get("basis"),
    }


def _walk_numbers(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk_numbers(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(obj)
    elif isinstance(obj, str):
        import re as _re
        for m in _re.findall(r"\d+(?:\.\d+)?", obj):
            out.append(float(m))


def grounding_text(source_data=None, article_text=None):
    """Everything a caption's numerals are allowed to draw from."""
    parts = []
    if article_text:
        parts.append(article_text)
    if source_data:
        nums = []
        _walk_numbers(source_data.get("facts"), nums)
        parts.append(" ".join(_fmt_num(n) for n in nums))
        parts.append(str(source_data.get("selector") or ""))
    return " ".join(p for p in parts if p)


def _fmt_num(n):
    """Emit a number in the shapes copy might legitimately use."""
    if float(n).is_integer():
        i = int(n)
        return f"{i} {i:,} {float(i)}"
    return f"{n} {n:.1f} {n:.2f}"
