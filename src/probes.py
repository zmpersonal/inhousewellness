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
import re
import statistics
from collections import Counter, defaultdict

from . import facts as F

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "state" / "published-findings.json"

# A finding must clear this to be publishable at all.
NOTABILITY_FLOOR = 0.45

# Which site holds the data is which site the finding links to.
DATASET_HOME = {
    "cpsc_recalls": "https://healthresearchdatabase.com/",
    "clinical_trials": "https://healthresearchdatabase.com/",
    "openalex_topics": "https://healthresearchdatabase.com/",
    "fda_device_events": "https://healthresearchdatabase.com/",
    "bhis_saunas": "https://besthomeinfraredsauna.com/",
    "outdoor_climate": "https://outdoorsteamsauna.com/climate-index",
    "outdoor_cities": "https://outdoorsteamsauna.com/climate-index",
    "hrd_studies": "https://healthresearchdatabase.com/",
    "hrd_topics": "https://healthresearchdatabase.com/",
    # Round 12 keyed datasets. Running cost and housing fit are electrical /
    # space questions, so they route to the site that holds those tools.
    "eia_electricity": "https://besthomeinfraredsauna.com/",
    "fred_series": "https://besthomeinfraredsauna.com/",
    "census_housing": "https://besthomeinfraredsauna.com/best/small-spaces",
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
             chart=None, note=None, baseline=None, population_is_the_subject=False):
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
        # A share needs a base rate, or an explicit statement that it describes
        # the indexed population itself. See validator.check_denominator.
        "baseline": baseline,
        "population_is_the_subject": population_is_the_subject,
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
                       "items": [[b, n] for b, n in brands.most_common(6)]},
                population_is_the_subject=True))

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
                note="A concentrated evidence base is a finding about the evidence.",
                population_is_the_subject=True))
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
            note='"Near zero" is a marketing phrase, not a measurement.',
            population_is_the_subject=True))

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
                   "label_filled": "Standard outlet", "label_rest": "Dedicated circuit"},
            population_is_the_subject=True))
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
            chart={"type": "bar", "items": [[k, v] for k, v in classes.most_common(6)]},
            population_is_the_subject=True))
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
            note="Design is the first thing to check before a claim is quoted.",
            population_is_the_subject=True))

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
                       "label_filled": "Has a DOI", "label_rest": "None"},
                population_is_the_subject=True))
    return out


# ---------------------------------------------------------------- recalls
def recall_probes():
    """CPSC recalls. Nobody in this category publishes this, and it is the
    most direct expression of the transparency position the brand holds."""
    d = _ds("cpsc_recalls")
    if not d:
        return []
    rows, out = d["rows"], []
    years = Counter((r.get("RecallDate") or "")[:4] for r in rows if r.get("RecallDate"))
    years = {y: n for y, n in years.items() if y.isdigit()}
    since = {y: n for y, n in years.items() if int(y) >= 2015}
    if since:
        total = sum(since.values())
        out.append(_finding(
            "disclosure", "recalls_since_2015",
            f"{total} sauna, heater and related product recalls have been filed "
            f"with the CPSC since 2015.",
            {"recalls": total, "first_year": min(since), "last_year": max(since),
             "years_covered": len(since),
             "busiest_year": max(since, key=since.get),
             "busiest_count": max(since.values())},
            "cpsc_recalls", d, total, min(1.0, 0.55 + min(total, 80) / 160),
            chart={"type": "bar",
                   "items": [[y, since[y]] for y in sorted(since)[-6:]]},
            note="Filed with the US Consumer Product Safety Commission."))

    # What actually fails, from the hazard text.
    haz = Counter()
    for r in rows:
        h = (r.get("Hazards") or "")
        text = h if isinstance(h, str) else json.dumps(h)
        for label, pat in (("Burn", r"burn"), ("Fire", r"fire|flame|ignit"),
                           ("Shock", r"shock|electrocut"), ("Impact", r"impact|laceration"),
                           ("Fall", r"fall|tip[- ]?over"), ("Entrapment", r"entrap|trap")):
            if re.search(pat, text, re.I):
                haz[label] += 1
    if sum(haz.values()) >= 20:
        top, cnt = haz.most_common(1)[0]
        out.append(_finding(
            "concentration", "recall_hazards",
            f"{top} is the most common hazard across {sum(haz.values())} recall "
            f"filings — {cnt} of them.",
            {"top_hazard": top, "count": cnt, "total": sum(haz.values()),
             "distinct_hazards": len(haz)},
            "cpsc_recalls", d, sum(haz.values()),
            min(1.0, 0.5 + cnt / max(sum(haz.values()), 1) * 0.5),
            chart={"type": "bar", "items": [[k, v] for k, v in haz.most_common(6)]},
            note="Hazard categories parsed from CPSC recall notices.",
            population_is_the_subject=True))

    # Manufacturing-country share is DELIBERATELY not emitted as a finding.
    #
    # "China accounts for 55% of recalled units" needs the share of US home
    # saunas manufactured in China to mean anything, and no dataset here holds
    # it. Without that denominator the number is not consumer safety, it is
    # nationality. If an import-share source is added later, supply it as
    # `baseline` and the finding becomes publishable.
    countries = Counter()
    for r in rows:
        c = r.get("ManufacturerCountries")
        for item in (c if isinstance(c, list) else []):
            name = item.get("Country") if isinstance(item, dict) else str(item)
            if name:
                countries[name] += 1
    if sum(countries.values()) >= 20:
        top, cnt = countries.most_common(1)[0]
        share = cnt / sum(countries.values())
        out.append(_finding(
            "concentration", "recall_origin",
            f"{top} accounts for {cnt} of {sum(countries.values())} recalled "
            f"units by manufacturing country — {share:.0%}.",
            {"top": top, "count": cnt, "total": sum(countries.values()),
             "share": round(share, 3)},
            "cpsc_recalls", d, sum(countries.values()),
            min(1.0, 0.4 + share * 0.6),
            chart={"type": "bar", "items": [[k, v] for k, v in countries.most_common(6)]},
            baseline=None))          # no import-share source -> blocks, by design
    return out


# ---------------------------------------------------------------- trials
def trial_probes():
    d = _ds("clinical_trials")
    if not d:
        return []
    rows, out = d["rows"], []
    status = Counter(r.get("status") for r in rows if r.get("status"))
    active = sum(n for s, n in status.items()
                 if s in ("RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING"))
    if rows and active:
        out.append(_finding(
            "trend", "trials_active",
            f"{active} of {len(rows)} registered heat and cold-immersion trials "
            f"are still running or recruiting.",
            {"active": active, "total": len(rows),
             "completed": status.get("COMPLETED", 0),
             "recruiting": status.get("RECRUITING", 0)},
            "clinical_trials", d, len(rows),
            min(1.0, 0.4 + active / max(len(rows), 1)),
            chart={"type": "dot", "total": len(rows), "filled": active,
                   "label_filled": "Still running", "label_rest": "Closed"},
            note="Registered on ClinicalTrials.gov.",
            population_is_the_subject=True))

    enr = sorted(v for v in (_num(r.get("enrollment")) for r in rows) if v)
    if len(enr) >= 20:
        med = statistics.median(enr)
        out.append(_finding(
            "distribution", "trial_enrollment",
            f"The median heat-therapy trial enrols {med:g} people; the largest "
            f"enrols {max(enr):g}.",
            {"median": med, "min": min(enr), "max": max(enr), "trials": len(enr)},
            "clinical_trials", d, len(enr),
            min(1.0, 0.35 + min(max(enr) / max(med, 1), 40) / 60),
            chart={"type": "range", "min": min(enr), "median": med, "max": max(enr),
                   "unit": "", "min_label": "smallest", "max_label": "largest"},
            note="Small trials are the norm in this literature."))
    return out


# ---------------------------------------------------------------- openalex
def scholarly_probes():
    d = _ds("openalex_topics")
    if not d:
        return []
    years = {}
    for r in d["rows"]:
        y = str(r.get("year") or "")
        if y.isdigit():
            years[int(y)] = years.get(int(y), 0) + int(r.get("works") or 0)
    ys = sorted(y for y in years if 2000 <= y <= dt.date.today().year)
    if len(ys) < 8:
        return []
    recent = sum(years[y] for y in ys[-5:])
    prior = sum(years[y] for y in ys[-10:-5]) or 1
    change = recent / prior
    if abs(change - 1) < 0.2:
        return []
    return [_finding(
        "trend", "scholarly_volume",
        f"Published research on this topic has {'grown' if change > 1 else 'fallen'} "
        f"{change:.1f}x: {recent} papers in the last five years against {prior} "
        f"in the five before.",
        {"recent": recent, "prior": prior, "change": round(change, 2),
         "window": f"{ys[-5]}-{ys[-1]}"},
        "openalex_topics", d, sum(years.values()),
        min(1.0, 0.4 + abs(change - 1) * 0.3),
        chart={"type": "bar", "items": [[str(y), years[y]] for y in ys[-6:]]},
        note="Indexed by OpenAlex.")]


# ALL_PROBES is defined at the foot of this file, after every probe.


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


# ---------------------------------------------------------------- running cost
# Round 12: the three keyed datasets. Each probe family reads ONE dataset and
# returns [] if it is absent, so a missing key degrades to fewer findings rather
# than a failed run -- the same independence rule the four idea feeds follow.

# A sauna's electrical load. Stated here as data, not prose, because every
# numeral that reaches copy must be groundable in a finding's `figures`.
SAUNA_KW = 8
SESSION_HOURS = 1

# EIA returns census divisions and a national row alongside the states. They
# are aggregates of the same rows, so leaving them in would double-count and
# put "U.S. Total" in a list of states.
_EIA_AGGREGATES = {"US", "ENC", "ESC", "MAT", "MTN", "NEW", "PCC", "PCN",
                   "SAT", "WNC", "WSC"}


def electricity_cost_probes():
    """What an hour in the sauna actually costs, by state.

    The buyer's question is "what will it cost to run"; every answer online is
    a single national number. The spread is 4x, and it is the one input the
    buyer cannot change by choosing a different cabin.
    """
    d = _ds("eia_electricity")
    if not d:
        return []
    by_period = defaultdict(dict)
    for r in d["rows"]:
        price = _num(r.get("price_cents_kwh"))
        code = str(r.get("state") or "").strip()
        if price is None or code in _EIA_AGGREGATES or len(code) != 2:
            continue
        by_period[str(r.get("period") or "")][code] = (price, r.get("state_name"))
    if not by_period:
        return []
    period = max(by_period)
    snap = by_period[period]
    if len(snap) < 40:
        return []                      # a partial month is not a national picture

    ranked = sorted(snap.items(), key=lambda kv: kv[1][0])
    lo_code, (lo_price, lo_name) = ranked[0]
    hi_code, (hi_price, hi_name) = ranked[-1]
    prices = [p for p, _ in snap.values()]
    med = sorted(prices)[len(prices) // 2]

    def hour_cost(cents):
        return round(SAUNA_KW * SESSION_HOURS * cents / 100, 2)

    lo_usd, hi_usd, med_usd = hour_cost(lo_price), hour_cost(hi_price), hour_cost(med)
    ratio = round(hi_price / lo_price, 1)
    out = [_finding(
        "distribution", "electricity_state_spread",
        f"The same {SAUNA_KW} kW sauna costs ${lo_usd:.2f} an hour to run in "
        f"{lo_name} and ${hi_usd:.2f} in {hi_name} — {ratio} times more for "
        f"identical heat.",
        {"kw": SAUNA_KW, "hours": SESSION_HOURS,
         "low_usd": lo_usd, "low_state": lo_name,
         "high_usd": hi_usd, "high_state": hi_name,
         "median_usd": med_usd, "ratio": ratio,
         "low_cents_kwh": lo_price, "high_cents_kwh": hi_price,
         "period": period, "states": len(snap)},
        "eia_electricity", d, len(snap), min(1.0, 0.40 + (ratio - 1) * 0.08),
        chart={"type": "range", "min": lo_usd, "median": med_usd, "max": hi_usd,
               "unit": "$", "min_label": lo_name, "max_label": hi_name},
        note=f"Residential rates, {period}. Running cost is set by your utility, "
             f"not by your cabin.")]

    # Where the median sits inside the spread says whether the average is
    # representative or dragged by outliers. Buyers are quoted the average.
    if hi_price > lo_price:
        pos = (med - lo_price) / (hi_price - lo_price)
        if pos <= 0.35:
            out.append(_finding(
                "distribution", "electricity_median_vs_mean",
                f"Most states sit near the bottom of the electricity range: the "
                f"median state pays ${med_usd:.2f} an hour against a top end of "
                f"${hi_usd:.2f}. The spread is a few expensive states, not a "
                f"national trend.",
                {"kw": SAUNA_KW, "median_usd": med_usd, "high_usd": hi_usd,
                 "low_usd": lo_usd, "states": len(snap), "period": period},
                "eia_electricity", d, len(snap), 0.52,
                chart={"type": "range", "min": lo_usd, "median": med_usd,
                       "max": hi_usd, "unit": "$",
                       "min_label": lo_name, "max_label": hi_name}))
    return out


def electricity_trend_probes():
    """What the running cost has done over a decade — the number that matters
    for a purchase people keep for fifteen years."""
    d = _ds("fred_series")
    if not d:
        return []
    obs = []
    for r in d["rows"]:
        v = _num(r.get("value"))          # FRED writes "." for a missing month
        if v is not None and r.get("date"):
            obs.append((str(r["date"]), v))
    if len(obs) < 24:
        return []
    obs.sort()
    (d0, v0), (d1, v1) = obs[0], obs[-1]
    if v0 <= 0:
        return []
    change = (v1 / v0) - 1
    if abs(change) < 0.10:
        return []
    direction = "risen" if change > 0 else "fallen"
    # The claim shows a WHOLE percent, so the whole percent is what must be
    # grounded -- carrying only the unrounded 42.8 while printing "43%" is the
    # UNGROUNDED_NUMERAL failure, committed by the probe rather than the model.
    change_whole = round(abs(change) * 100)
    start_cost = round(SAUNA_KW * SESSION_HOURS * v0, 2)
    end_cost = round(SAUNA_KW * SESSION_HOURS * v1, 2)
    return [_finding(
        "trend", "electricity_decade_trend",
        f"US electricity has {direction} {change_whole}% since {d0[:4]}. The "
        f"same {SAUNA_KW} kW hour that cost ${start_cost:.2f} then costs "
        f"${end_cost:.2f} now.",
        {"kw": SAUNA_KW, "start_year": d0[:4], "end_year": d1[:4],
         "start_usd_kwh": v0, "end_usd_kwh": v1,
         "start_hour_usd": start_cost, "end_hour_usd": end_cost,
         "change_pct": round(change * 100, 1), "change_pct_whole": change_whole,
         "months": len(obs)},
        "fred_series", d, len(obs), min(1.0, 0.42 + abs(change) * 0.5),
        chart={"type": "bar",
               "items": [[y, round(next(v for dd, v in obs if dd.startswith(y)) * 100, 1)]
                         for y in sorted({o[0][:4] for o in obs})[-6:]]},
        note="Cost per kWh, US city average. A running cost compounds over the "
             "life of the cabin.")]


def housing_stock_probes():
    """Whether the housing stock can physically take a sauna.

    Detached share is the closest published proxy for "has somewhere to put
    one" -- a garage, basement or yard. It varies from 10% to 74% by state.
    """
    d = _ds("census_housing")
    if not d:
        return []
    rows = []
    for r in d["rows"]:
        total, detached = _num(r.get("B25041_001E")), _num(r.get("B25024_002E"))
        if total and detached is not None and total > 0:
            rows.append((str(r.get("NAME") or ""), detached / total, int(total)))
    if len(rows) < 40:
        return []
    rows.sort(key=lambda x: x[1])
    lo_name, lo_share, _ = rows[0]
    hi_name, hi_share, _ = rows[-1]
    tot = sum(t for _, _, t in rows)
    det = sum(s * t for _, s, t in rows)
    national = det / tot
    return [_finding(
        "distribution", "detached_housing_spread",
        f"{national:.0%} of US homes are single-family detached — but that runs "
        f"from {lo_share:.0%} in {lo_name} to {hi_share:.0%} in {hi_name}. "
        f"Where a sauna can physically go is a regional question.",
        {"national_share": round(national, 3),
         "low_share": round(lo_share, 3), "low_state": lo_name,
         "high_share": round(hi_share, 3), "high_state": hi_name,
         "states": len(rows), "total_units": int(tot)},
        "census_housing", d, len(rows), 0.55,
        chart={"type": "range", "min": round(lo_share * 100), "median": round(national * 100),
               "max": round(hi_share * 100), "unit": "%",
               "min_label": lo_name, "max_label": hi_name},
        note="American Community Survey, 1-year estimates.",
        # The figure describes the indexed housing stock itself, so the base
        # rate IS the population. See validator.check_denominator.
        population_is_the_subject=True)]


ALL_PROBES = (disclosure_probes, distribution_probes, concentration_probes,
              trend_probes, contradiction_probes, climate_probes,
              evidence_quality_probes, recall_probes, trial_probes,
              scholarly_probes,
              # Round 12 — the three keyed datasets.
              electricity_cost_probes, electricity_trend_probes,
              housing_stock_probes)
