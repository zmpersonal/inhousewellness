"""Supply the caption brief with real figures, so NO_FIGURE is satisfiable.

The first two live cards published adjectives — "Lower / Higher",
"Occasional / Regular" — because comparison rows were built from prose articles,
and prose yields adjectives. A rule demanding measurements is only fair if the
brief carries measurements.

Order of supply:
  1. the fact layer, where it holds figures for BOTH sides of the comparison
  2. figures extracted from the source article's own text
  3. nothing — and then the row BLOCKS rather than generating an adjective table

A blocked row is a content signal, not a failure.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter

import json
import pathlib

from . import facts as F

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTICLE_CACHE = ROOT / "data" / "article-figures.json"


def cached_article_figures(url):
    """Measurement fragments pulled from a source article, cached offline.

    Anchored to the repo root, not the cwd. Returns [] on a missing or corrupt
    cache -- a missing cache means "no figures from this source", which then
    blocks the row, rather than silently passing prose through.
    """
    if not url or not ARTICLE_CACHE.exists():
        return []
    try:
        data = json.loads(ARTICLE_CACHE.read_text())
    except json.JSONDecodeError:
        return []
    return (data.get("articles", {}).get(url) or {}).get("figures", [])


def _num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _g(rows, field):
    return [v for v in (_num(r.get(field)) for r in rows) if v is not None]


def _fmt(v, unit="", dp=0):
    if v is None:
        return None
    s = f"{v:,.{dp}f}" if abs(v) >= 1000 else f"{v:g}"
    return f"{s}{unit}"


# ---------------------------------------------------------------------------
# 1. Fact-layer comparisons. Only axes where the CSV genuinely covers BOTH
#    columns — a comparison needs two measured sides, not one plus an adjective.
# ---------------------------------------------------------------------------

def _by_capacity(rows, cap):
    return [r for r in rows if _num(r.get("capacity")) == float(cap)]


def voltage_comparison():
    """120V models vs 240V models — the split that decides most installs."""
    d = F._load("bhis_saunas")
    if not d:
        return None
    rows = d["rows"]
    a = [r for r in rows if str(r.get("voltage") or "").strip() == "120"]
    b = [r for r in rows if str(r.get("voltage") or "").strip() == "240"]
    if len(a) < 5 or len(b) < 2:
        return None
    out = {"a": "120V models", "b": "240V models", "rows": []}
    out["rows"].append(["Models indexed", str(len(a)), str(len(b))])
    for field, label, unit, dp in (("amps", "Amp draw", " amps", 0),
                                   ("price", "Price, median", "", 0),
                                   ("max_temp", "Max temperature", "°F", 0)):
        va, vb = _g(a, field), _g(b, field)
        if not va or not vb:
            continue
        if field == "price":
            out["rows"].append([label, f"${_fmt(statistics.median(va))}",
                                f"${_fmt(statistics.median(vb))}"])
        else:
            out["rows"].append([
                label,
                f"{_fmt(min(va))} to {_fmt(max(va))}{unit}" if min(va) != max(va)
                else f"{_fmt(min(va))}{unit}",
                f"{_fmt(min(vb))} to {_fmt(max(vb))}{unit}" if min(vb) != max(vb)
                else f"{_fmt(min(vb))}{unit}"])
    return out if len(out["rows"]) >= 3 else None


def capacity_comparison(cap_a=2, cap_b=4):
    """2-person against 4-person: dimensions, draw and price, all measured."""
    d = F._load("bhis_saunas")
    if not d:
        return None
    A, B = _by_capacity(d["rows"], cap_a), _by_capacity(d["rows"], cap_b)
    if len(A) < 4 or len(B) < 4:
        return None
    out = {"a": f"{cap_a}-person", "b": f"{cap_b}-person", "rows": []}
    for field, label, unit, dp in (("width", "Width", " in", 0),
                                   ("depth", "Depth", " in", 0),
                                   ("height", "Height", " in", 0),
                                   ("amps", "Amp draw", " amps", 0),
                                   ("price", "Price, median", "", 0)):
        va, vb = _g(A, field), _g(B, field)
        if not va or not vb:
            continue
        if field == "price":
            out["rows"].append([label, f"${_fmt(statistics.median(va))}",
                                f"${_fmt(statistics.median(vb))}"])
        else:
            out["rows"].append([label,
                                f"{_fmt(min(va))} to {_fmt(max(va))}{unit}",
                                f"{_fmt(min(vb))} to {_fmt(max(vb))}{unit}"])
    return out if len(out["rows"]) >= 3 else None


def capacity_spec(cap=2):
    """A spec table for one capacity — every value measured across the index."""
    d = F._load("bhis_saunas")
    if not d:
        return None
    A = _by_capacity(d["rows"], cap)
    if len(A) < 5:
        return None
    rows = []
    for field, label, unit in (("width", "Width", " in"), ("depth", "Depth", " in"),
                               ("height", "Height", " in"), ("amps", "Amp draw", " amps"),
                               ("max_temp", "Max temperature", "°F")):
        v = _g(A, field)
        if not v:
            continue
        rows.append([label, f"{_fmt(min(v))}–{_fmt(max(v))}{unit}"])
    price = _g(A, "price")
    if price:
        rows.append(["Price, median", f"${_fmt(statistics.median(price))}"])
    return {"rows": rows, "models": len(A)} if len(rows) >= 3 else None


def metro_cost_spec():
    d = F._load("outdoor_climate")
    if not d:
        return None
    rows = d["rows"]
    cost = _g(rows, "estimated_9kw_session_cost")
    rate = _g(rows, "electricity_cents_kwh")
    if not cost or not rate:
        return None
    return {"figure": f"${_fmt(statistics.median(cost), dp=2)}",
            "unit": "median cost of one 9 kW session across 75 US metros",
            "rows": [["Cheapest metro", f"${min(cost):.2f}"],
                     ["Most expensive", f"${max(cost):.2f}"],
                     ["Electricity rate", f"{min(rate):.1f}–{max(rate):.1f} c/kWh"],
                     ["Metros indexed", str(len(cost))]]}


def infrared_vs_traditional():
    """The comparison the network could not make until now.

    Round 9 blocked 12 rows -- the highest-volume cluster in the queue, roughly
    6,000 monthly searches -- because the fact layer held infrared specs and no
    traditional equivalent. infinitesauna.com publishes both: 88 Traditional and
    77 Infrared models with heater kW, voltage, amperage, capacity, price and
    max temperature. Both sides are now measured, from published specs, with no
    measurement of our own required.
    """
    d = F._load("infinite_saunas")
    if not d:
        return None
    import re as _re

    def num(v):
        m = _re.search(r"[\d.]+", str(v or ""))
        return float(m.group(0)) if m else None

    A = [r for r in d["rows"] if r.get("type") == "Infrared"]
    B = [r for r in d["rows"] if r.get("type") == "Traditional"]
    if len(A) < 20 or len(B) < 20:
        return None

    def rng(grp, field, unit="", dp=0):
        v = sorted(x for x in (num(r.get(field)) for r in grp) if x is not None)
        if len(v) < 5:
            return None
        lo, hi = v[0], v[-1]
        if lo == hi:
            return f"{lo:g}{unit}"
        return f"{lo:g} to {hi:g}{unit}"

    def med(grp, field, pre="", unit=""):
        import statistics as st
        v = [x for x in (num(r.get(field)) for r in grp) if x is not None]
        if len(v) < 5:
            return None
        m = st.median(v)
        return f"{pre}{m:,.0f}{unit}" if m >= 1000 else f"{pre}{m:g}{unit}"

    # Derived values the model would otherwise COMPUTE. A difference or a
    # multiple is the natural thing to say -- "40 to 60F hotter", "nearly twice
    # the price" -- and UNGROUNDED_NUMERAL correctly rejects arithmetic on
    # grounded figures. So compute them here, where they become grounded facts
    # the model may quote verbatim. Supply the derivation; never relax the rule.
    def _derived():
        import statistics as st
        d = {}
        ta = [x for x in (num(r.get("max_temp")) for r in A) if x]
        tb = [x for x in (num(r.get("max_temp")) for r in B) if x]
        if ta and tb:
            d["temp_gap_low_f"] = round(min(tb) - max(ta))
            d["temp_gap_high_f"] = round(max(tb) - min(ta))
        pa = [x for x in (num(r.get("price")) for r in A) if x]
        pb = [x for x in (num(r.get("price")) for r in B) if x]
        if pa and pb:
            ma, mb = st.median(pa), st.median(pb)
            d["price_gap_usd"] = round(mb - ma)
            d["price_multiple"] = round(mb / ma, 1)
        return d

    out = {"a": "Infrared", "b": "Traditional", "rows": [], "derived": _derived()}
    for label, fn, args in (
            ("Models indexed", lambda g, **k: str(len(g)), {}),
            ("Max temperature", rng, {"field": "max_temp", "unit": "°F"}),
            ("Heater output", rng, {"field": "heater_kw", "unit": " kW"}),
            ("Amp draw", rng, {"field": "amperage", "unit": " amps"}),
            ("Price, median", med, {"field": "price", "pre": "$"}),
            ("Weight", rng, {"field": "weight", "unit": " lb"})):
        va, vb = fn(A, **args), fn(B, **args)
        if va and vb:
            out["rows"].append([label, va, vb])
    return out if len(out["rows"]) >= 3 else None


FACT_BUILDERS = [
    (re.compile(r"\b(?:infrared|ir)\s*(?:sauna\s*)?(?:vs|versus)|"
                r"(?:vs|versus)\s*infrared|"
                r"\b(?:traditional|steam|dry|wet|regular|wood)\b.*\b(?:vs|versus)\b|"
                r"\b(?:vs|versus)\b.*\b(?:traditional|steam|dry|wet|regular|wood)\b", re.I),
     "comparison", infrared_vs_traditional),
    (re.compile(r"\b(?:electric\w*|circuit|breaker|amp|volt|120v|240v|wiring|outlet|panel)\b", re.I),
     "comparison", voltage_comparison),
    (re.compile(r"\b(?:dimension\w*|size|sizing|fit|space|width|depth|height|"
                r"\d\s*person|two\s*person|four\s*person)\b", re.I),
     "spec", lambda: capacity_spec(2)),
    (re.compile(r"\b(?:cost|price|pricing|electricity|kwh|bill|run\w*\s+cost)\b", re.I),
     "cost", metro_cost_spec),
    (re.compile(r"\b(?:2\s*person|two\s*person).*(?:4\s*person|four\s*person)|"
                r"(?:4\s*person|four\s*person).*(?:2\s*person|two\s*person)", re.I),
     "comparison", lambda: capacity_comparison(2, 4)),
]


# ---------------------------------------------------------------------------
# 2. Figures extracted from the source article's own prose.
# ---------------------------------------------------------------------------

_MEASURE = re.compile(
    r"[^.!?\n]{0,90}?"
    r"(?:\d[\d,.]*\s*(?:°\s*[FC]|degrees|%|percent|kWh|kW|W\b|V\b|volts?|amps?|A\b|"
    r"in\b|inches|ft\b|feet|cm|mm|lb|lbs|kg|min\b|minutes?|hours?|hrs?|psi|gal|"
    # Duration units were listed in the validator but not here, so "15-25 years"
    # and "24 months" extracted as nothing at all.
    r"days?|weeks?|months?|years?|"
    r"mG|milligauss|micron|nm)"
    r"|\$\s*\d[\d,.]*)"
    r"[^.!?\n]{0,90}", re.I)


def from_article(text, limit=10):
    """Measurement-bearing fragments from an article. Prose in, figures out."""
    if not text:
        return []
    seen, out = set(), []
    for m in _MEASURE.finditer(text):
        frag = re.sub(r"\s+", " ", m.group(0)).strip(" -–—,;")
        if len(frag) < 12 or frag.lower() in seen:
            continue
        seen.add(frag.lower())
        out.append(frag)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# 3. What the brief gets.
# ---------------------------------------------------------------------------

def count_figures(payload):
    from .validator import is_figure
    if not payload:
        return 0
    cells = []
    for r in payload.get("rows", []):
        cells.extend(list(r)[1:] if isinstance(r, (list, tuple)) else [r])
    if payload.get("figure"):
        cells.append(payload["figure"])
    return sum(1 for c in cells if is_figure(c))


def figures_for(row, article_text=None):
    """Return (payload, source) for a row, or (None, reason) when it must block.

    `payload` is a ready-made card body carrying real values. The model may
    reword the labels but must not alter the figures.
    """
    kw = row.get("keyword") or ""
    arch = row.get("card_archetype") or ""

    for rx, builds_arch, fn in FACT_BUILDERS:
        if not rx.search(kw):
            continue
        try:
            payload = fn()
        except Exception:
            payload = None
        if payload and count_figures(payload) >= 2:
            return payload, f"fact layer ({builds_arch})"

    frags = from_article(article_text) or cached_article_figures(row.get("source_article"))
    if len(frags) >= 2:
        return {"article_figures": frags}, "source article"

    return None, ("no figures available: the fact layer holds nothing for this "
                  "keyword and the source article states no measurements")
