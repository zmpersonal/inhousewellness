"""Track B probe library — deterministic passes over the cached fact layer.

Probes COMPUTE. No model call happens here; the model writes copy afterwards
from what a probe emits. That keeps Track B's token cost to one post a week
while the finding itself is exact.

The proof this generalises: the EMF finding — 90 models labelled, 46 with a
number, 34 with a stated distance — came out of a CSV, needed no camera, and is
the strongest copy the system has produced.

Every probe emits: claim, figures, dataset, fetch_date, n, notability.
Findings are SINGLE USE — `state/published-findings.json` records what has run,
and a probe is never republished with a trivially different cut.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import statistics
from collections import Counter

from . import facts as F

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "state" / "published-findings.json"

# A finding must clear this to be publishable at all.
NOTABILITY_FLOOR = 0.45

# Which site holds the data is which site the finding links to.
DATASET_HOME = {
    "bhis_saunas": "https://besthomeinfraredsauna.com/",
    "outdoor_climate": "https://outdoorsteamsauna.com/climate-index",
    "outdoor_cities": "https://outdoorsteamsauna.com/climate-index",
    "hrd_studies": "https://healthresearchdatabase.com/",
    "hrd_topics": "https://healthresearchdatabase.com/",
}


def _num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _ds(name):
    d = F._load(name)
    return d if d else None


def _finding(kind, key, claim, figures, dataset, meta, n, notability,
             chart=None, note=None):
    return {
        "id": f"{kind}:{key}",
        "kind": kind,
        "claim": claim,
        "figures": figures,
        "dataset": meta["url"],
        "dataset_name": dataset,
        "fetch_date": meta["fetched_at"][:10],
        "n": n,
        "notability": round(notability, 3),
        "destination": DATASET_HOME.get(dataset, "https://inhousewellness.com/"),
        "chart": chart,
        "note": note,
    }


# ---------------------------------------------------------------- disclosure
def disclosure_probes():
    """Of N items claiming X, how many substantiate it?

    Generalises the EMF finding: a claim is cheap, a stated measurement
    condition is not.
    """
    d = _ds("bhis_saunas")
    if not d:
        return []
    rows, out = d["rows"], []
    n = len(rows)

    def gap(field, label, claim_field=None):
        claimed = [r for r in rows if str(r.get(claim_field or field) or "").strip()]
        stated = [r for r in rows if str(r.get(field) or "").strip()]
        if not claimed:
            return None
        share = len(stated) / len(claimed)
        return claimed, stated, share

    checks = [
        ("emf_distance", "state the distance an EMF reading was taken at", "emf_label"),
        ("emf_claim", "put a number on their EMF claim", "emf_label"),
        ("watts", "publish the heater wattage", None),
        ("amps", "publish the amp draw", None),
        ("max_temp", "publish a maximum temperature", None),
        ("wood", "name the wood species", None),
        ("height", "publish an exterior height", None),
    ]
    for field, label, claim_field in checks:
        g = gap(field, label, claim_field)
        if not g:
            continue
        claimed, stated, share = g
        undisclosed = len(claimed) - len(stated)
        if undisclosed < 3:
            continue
        # The bigger the gap, the more notable. Weight by how many models it covers.
        notability = (1 - share) * 0.75 + min(1.0, len(claimed) / 90) * 0.25
        out.append(_finding(
            "disclosure", field,
            f"Of {len(claimed)} models, only {len(stated)} {label}.",
            {"claimed": len(claimed), "disclosed": len(stated),
             "undisclosed": undisclosed, "share_disclosed": round(share, 3)},
            "bhis_saunas", d, len(claimed), notability,
            chart={"type": "dot", "total": len(claimed), "filled": len(stated),
                   "label_filled": "Publishes it", "label_rest": "Does not"}))
    return out


# ---------------------------------------------------------------- distribution
def distribution_probes():
    out = []
    c = _ds("outdoor_climate")
    if c:
        costs = [(_num(r.get("estimated_9kw_session_cost")), r) for r in c["rows"]]
        costs = sorted([(v, r) for v, r in costs if v], key=lambda t: t[0])
        if len(costs) >= 20:
            lo, hi = costs[0], costs[-1]
            med = statistics.median([v for v, _ in costs])
            ratio = hi[0] / lo[0]
            out.append(_finding(
                "distribution", "session_cost_by_metro",
                f"The same 9 kW session costs ${lo[0]:.2f} in {lo[1]['city']} "
                f"and ${hi[0]:.2f} in {hi[1]['city']} — {ratio:.1f}x, same cabin.",
                {"min": lo[0], "min_city": f"{lo[1]['city']}, {lo[1]['state']}",
                 "median": round(med, 2), "max": hi[0],
                 "max_city": f"{hi[1]['city']}, {hi[1]['state']}",
                 "ratio": round(ratio, 2), "metros": len(costs)},
                "outdoor_climate", c, len(costs),
                min(1.0, 0.35 + (ratio - 1) * 0.28),
                chart={"type": "range", "min": lo[0], "median": round(med, 2),
                       "max": hi[0], "unit": "$",
                       "min_label": lo[1]["city"], "max_label": hi[1]["city"]}))

    d = _ds("bhis_saunas")
    if d:
        for field, label, unit in (("price", "price", "$"),
                                   ("amps", "amp draw", "A"),
                                   ("width", "cabin width", "in")):
            vals = sorted(v for v in (_num(r.get(field)) for r in d["rows"]) if v)
            if len(vals) < 15:
                continue
            lo, hi = vals[0], vals[-1]
            med = statistics.median(vals)
            if lo <= 0 or hi / lo < 1.6:
                continue
            out.append(_finding(
                "distribution", f"{field}_spread",
                f"Across {len(vals)} indexed models, {label} runs from "
                f"{unit}{lo:g} to {unit}{hi:g}, median {unit}{med:g}.",
                {"min": lo, "median": med, "max": hi, "models": len(vals),
                 "ratio": round(hi / lo, 2)},
                "bhis_saunas", d, len(vals),
                min(1.0, 0.30 + (hi / lo - 1) * 0.10),
                chart={"type": "range", "min": lo, "median": med, "max": hi,
                       "unit": unit, "min_label": "lowest", "max_label": "highest"}))
    return out


# ---------------------------------------------------------------- concentration
def concentration_probes():
    out = []
    d = _ds("bhis_saunas")
    if d:
        brands = Counter(str(r.get("brand") or "").strip() for r in d["rows"] if r.get("brand"))
        if len(brands) >= 3:
            top, cnt = brands.most_common(1)[0]
            share = cnt / sum(brands.values())
            out.append(_finding(
                "concentration", "brand_share",
                f"{top} accounts for {cnt} of {sum(brands.values())} indexed "
                f"models — {share:.0%} of the field.",
                {"top_brand": top, "top_count": cnt, "total": sum(brands.values()),
                 "share": round(share, 3), "brands": len(brands)},
                "bhis_saunas", d, sum(brands.values()),
                min(1.0, 0.30 + share * 0.9),
                chart={"type": "bar",
                       "items": [[b, n] for b, n in brands.most_common(6)]}))

    s = _ds("hrd_studies")
    if s:
        # Real fields on this dataset -- an earlier version guessed "country"
        # and "topic", which do not exist, and quietly produced nothing.
        for field in ("journal", "topics", "design"):
            vals = Counter(str(r.get(field) or "").strip() for r in s["rows"] if r.get(field))
            if len(vals) < 3:
                continue
            top, cnt = vals.most_common(1)[0]
            total = sum(vals.values())
            share = cnt / total
            if share < 0.25:
                continue
            out.append(_finding(
                "concentration", f"studies_{field}",
                f"{top} accounts for {cnt} of {total} indexed studies — "
                f"{share:.0%} of the evidence base.",
                {"top": top, "count": cnt, "total": total,
                 "share": round(share, 3), "distinct": len(vals)},
                "hrd_studies", s, total, min(1.0, 0.32 + share * 0.85),
                chart={"type": "bar", "items": [[k, v] for k, v in vals.most_common(6)]},
                note="A concentrated evidence base is a finding about the evidence."))
    return out


# ---------------------------------------------------------------- trend
def trend_probes():
    s = _ds("hrd_studies")
    if not s:
        return []
    out = []
    years = Counter()
    for r in s["rows"]:
        y = _num(str(r.get("year") or r.get("published") or "")[:4])
        if y and 1990 <= y <= dt.date.today().year:
            years[int(y)] += 1
    if len(years) >= 5:
        ys = sorted(years)
        recent = sum(years[y] for y in ys[-3:])
        prior = sum(years[y] for y in ys[-6:-3]) or 1
        change = recent / prior
        if abs(change - 1) >= 0.25:
            direction = "accelerating" if change > 1 else "slowing"
            out.append(_finding(
                "trend", "publication_rate",
                f"Publication on this topic is {direction}: {recent} studies in "
                f"{ys[-3]}–{ys[-1]} against {prior} in the three years before.",
                {"recent": recent, "prior": prior, "change": round(change, 2),
                 "window": f"{ys[-3]}-{ys[-1]}"},
                "hrd_studies", s, sum(years.values()),
                min(1.0, 0.30 + abs(change - 1) * 0.4),
                chart={"type": "bar", "items": [[str(y), years[y]] for y in ys[-6:]]}))
    return out


# ---------------------------------------------------------------- contradiction
def contradiction_probes():
    """Where a marketing claim and the published data disagree."""
    d = _ds("bhis_saunas")
    if not d:
        return []
    out, rows = [], d["rows"]
    labelled = [r for r in rows if "near zero" in str(r.get("emf_label") or "").lower()]
    with_num = [r for r in labelled if str(r.get("emf_claim") or "").strip()]
    if len(labelled) >= 10 and len(with_num) < len(labelled):
        share = len(with_num) / len(labelled)
        out.append(_finding(
            "contradiction", "near_zero_unquantified",
            f'{len(labelled)} models are marketed as "Near Zero EMF"; '
            f"{len(labelled) - len(with_num)} of them publish no number at all.",
            {"labelled": len(labelled), "quantified": len(with_num),
             "unquantified": len(labelled) - len(with_num)},
            "bhis_saunas", d, len(labelled), min(1.0, 0.5 + (1 - share) * 0.5),
            chart={"type": "dot", "total": len(labelled), "filled": len(with_num),
                   "label_filled": "Publishes a number", "label_rest": "Does not"},
            note='"Near zero" is a marketing phrase, not a measurement.'))

    v120 = [r for r in rows if str(r.get("voltage") or "").strip() == "120"]
    if len(v120) >= 20:
        share = len(v120) / len(rows)
        out.append(_finding(
            "contradiction", "electrician_myth",
            f"{len(v120)} of {len(rows)} indexed infrared saunas run from a "
            f"standard 120V outlet — {share:.0%} need no electrician at all.",
            {"models_120v": len(v120), "total": len(rows), "share": round(share, 3)},
            "bhis_saunas", d, len(rows), min(1.0, 0.35 + share * 0.6),
            chart={"type": "dot", "total": len(rows), "filled": len(v120),
                   "label_filled": "Standard outlet", "label_rest": "Dedicated circuit"}))
    return out


def climate_probes():
    """The 75-metro index carries more than cost: freeze months, January lows,
    snow load and a planning-load class."""
    c = _ds("outdoor_climate")
    if not c:
        return []
    out, rows = [], c["rows"]

    for field, label, unit, dp in (
            ("electricity_cents_kwh", "residential electricity", "c/kWh", 2),
            ("jan_normal_low_f", "the January normal low", "F", 1),
            ("freeze_months", "months below freezing", "", 0),
            ("annual_snow_in", "annual snowfall", "in", 0)):
        vals = sorted(((_num(r.get(field)), r) for r in rows
                       if _num(r.get(field)) is not None),
                      key=lambda t: t[0])   # sort on the value; dicts are not orderable
        if len(vals) < 20:
            continue
        lo, hi = vals[0], vals[-1]
        med = statistics.median([v for v, _ in vals])
        if hi[0] - lo[0] <= 0:
            continue
        spread = (hi[0] - lo[0]) / (abs(med) or 1)
        out.append(_finding(
            "distribution", f"metro_{field}",
            f"Across {len(vals)} US metros, {label} runs from {lo[0]:.{dp}f}{unit} "
            f"in {lo[1]['city']} to {hi[0]:.{dp}f}{unit} in {hi[1]['city']}.",
            {"min": lo[0], "min_city": f"{lo[1]['city']}, {lo[1]['state']}",
             "median": round(med, dp), "max": hi[0],
             "max_city": f"{hi[1]['city']}, {hi[1]['state']}", "metros": len(vals)},
            "outdoor_climate", c, len(vals),
            min(1.0, 0.32 + min(spread, 3) * 0.18),
            chart={"type": "range", "min": lo[0], "median": round(med, dp),
                   "max": hi[0], "unit": unit,
                   "min_label": lo[1]["city"], "max_label": hi[1]["city"]}))

    classes = Counter(str(r.get("class") or "").strip() for r in rows if r.get("class"))
    if len(classes) >= 2:
        top, cnt = classes.most_common(1)[0]
        share = cnt / sum(classes.values())
        out.append(_finding(
            "concentration", "metro_planning_class",
            f'{cnt} of {sum(classes.values())} US metros fall into "{top}" '
            f"for outdoor sauna planning — {share:.0%}.",
            {"top": top, "count": cnt, "total": sum(classes.values()),
             "share": round(share, 3)},
            "outdoor_climate", c, sum(classes.values()),
            min(1.0, 0.30 + share * 0.7),
            chart={"type": "bar", "items": [[k, v] for k, v in classes.most_common(6)]}))
    return out


def evidence_quality_probes():
    """How much of the indexed evidence is actually a trial?"""
    s = _ds("hrd_studies")
    if not s:
        return []
    rows, out = s["rows"], []
    designs = Counter(str(r.get("design") or "").strip() for r in rows if r.get("design"))
    total = sum(designs.values())
    if total >= 50:
        trials = sum(n for d, n in designs.items()
                     if any(k in d.lower() for k in ("randomi", "trial", "rct")))
        share = trials / total
        out.append(_finding(
            "disclosure", "study_design_quality",
            f"Of {total} indexed studies, {trials} are randomised trials — "
            f"{share:.0%}. The rest is observational or other research.",
            {"total": total, "trials": trials, "other": total - trials,
             "share": round(share, 3)},
            "hrd_studies", s, total, min(1.0, 0.42 + (1 - share) * 0.45),
            chart={"type": "dot", "total": total, "filled": trials,
                   "label_filled": "Randomised trial", "label_rest": "Other design"},
            note="Design is the first thing to check before a claim is quoted."))

    with_doi = [r for r in rows if str(r.get("doi") or "").strip()]
    if rows and len(with_doi) < len(rows):
        share = len(with_doi) / len(rows)
        if share < 0.95:
            out.append(_finding(
                "disclosure", "study_doi_coverage",
                f"{len(rows) - len(with_doi)} of {len(rows)} indexed studies "
                f"carry no DOI.",
                {"total": len(rows), "with_doi": len(with_doi),
                 "without": len(rows) - len(with_doi), "share": round(share, 3)},
                "hrd_studies", s, len(rows), min(1.0, 0.28 + (1 - share) * 0.8),
                chart={"type": "dot", "total": len(rows), "filled": len(with_doi),
                       "label_filled": "Has a DOI", "label_rest": "None"}))
    return out


ALL_PROBES = (disclosure_probes, distribution_probes, concentration_probes,
              trend_probes, contradiction_probes, climate_probes,
              evidence_quality_probes)


# ---------------------------------------------------------------- ledger
def published_ids():
    if not LEDGER.exists():
        return set()
    try:
        return {f["id"] for f in json.loads(LEDGER.read_text())}
    except json.JSONDecodeError:
        raise SystemExit(f"HALT: {LEDGER} is corrupt. A findings ledger must never "
                         f"be silently reset — that is how a finding gets republished.")


def record_published(finding, post_url=None):
    rows = []
    if LEDGER.exists():
        rows = json.loads(LEDGER.read_text())
    rows.append({"id": finding["id"], "claim": finding["claim"],
                 "published_at": dt.date.today().isoformat(), "post_url": post_url})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(rows, indent=1))
    return len(rows)


def run_all(exclude_published=True):
    """Every probe, ranked. Findings are single-use."""
    seen = published_ids() if exclude_published else set()
    out = []
    for fn in ALL_PROBES:
        try:
            out.extend(fn())
        except Exception as e:
            # One probe failing must not take down the library.
            print(f"  ! probe {fn.__name__} failed: {type(e).__name__}: {e}")
    out = [f for f in out if f["id"] not in seen]
    out.sort(key=lambda f: -f["notability"])
    return out


def publishable(findings):
    return [f for f in findings if f["notability"] >= NOTABILITY_FLOOR]
