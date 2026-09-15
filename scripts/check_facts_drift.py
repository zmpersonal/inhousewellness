#!/usr/bin/env python3
"""Watch the DERIVED facts for drift, and hold them to invariants.

WHY THIS EXISTS
tests/test_validator.py::test_source_data_grounding_round_trips asserted that
"90", "71", "46" and "34" appear in the EMF grounding text. On 2026-09-15 the
besthomeinfraredsauna index was republished: 90 models became 87 (two Dynamic
models retired, one duplicate record resolved), so 71 "Near Zero EMF" labels
became 68. The source was right, the refresh was right, and the test failed --
in the Sweep step of `fetch manufacturer specs`, blocking a crawl that has
nothing to do with EMF labels.

Any test that pins a literal value from refreshed third-party data WILL fail on
some future refresh. The question is only whether that failure blocks a pipeline
or produces a report. This is the report.

THE SPLIT
  invariants  Relationships that must hold whatever the publisher does: a subset
              is never larger than its superset, a median sits between its min
              and max, a count is never negative, two clusters reading the same
              file agree on how many rows it has, and a metric that has always
              been non-zero does not silently become zero. These HALT. They
              catch a truncated file, a column rename, a parse regression --
              real corruption -- without naming a single expected value.
  drift       Everything else. Reported with old value, new value and percent
              change, exit 0. A human reads it; nothing is blocked.

A move beyond --tolerance (default 25%) is treated as an invariant breach rather
than drift: 90 -> 87 is maintenance, 90 -> 9 is an accident, and the difference
is a magnitude, not a category.

    python3 scripts/check_facts_drift.py                 # report + invariants
    python3 scripts/check_facts_drift.py --accept        # re-baseline (deliberate)
    python3 scripts/check_facts_drift.py --self-test
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASELINE = ROOT / "data" / "facts-baseline.json"

# Metrics allowed to be zero without it counting as a collapse -- an optional
# sub-block, not a count that should always have members.
MAY_BE_ZERO = set()

# A percentage move only counts as a breach if the ABSOLUTE move also exceeds
# this. A count of 4 cannot change at all without moving 25%, so a percentage
# tolerance alone would halt on one retired model in a four-model group --
# exactly the false positive this whole exercise is about. Same "don't act on
# noise" rule as the feedback loop's 30-post minimum and the destination
# audit's n >= 25 threshold: below a certain n, a ratio is not evidence.
MIN_ABS_MOVE = 2


def derive():
    """Every cluster's fact block, freshly computed from the current cache."""
    import src.facts as F
    out = {}
    for cluster, fn in F.CLUSTER_FACTS.items():
        block = fn()
        if block is not None:
            out[cluster] = block
    return out


def flatten(obj, prefix=""):
    """Numeric leaves only, as dotted paths. Strings (city names, source URLs)
    and dates are deliberately excluded: this watches quantities."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        out[prefix] = obj
    return out


def metrics_of(facts):
    m = {}
    for cluster, block in facts.items():
        m.update(flatten(block, cluster))
    return m


# ── INVARIANTS ──────────────────────────────────────────────────────────────
# Each takes the derived facts plus the flattened metrics and returns a list of
# problems. None of them names an expected value.

def inv_subsets(facts, m):
    """A filtered count can never exceed the set it was filtered from."""
    problems = []
    e = facts.get("emf")
    if e:
        n = e["models_indexed"]
        for field in ("models_with_an_emf_label", "models_with_a_numeric_emf_claim",
                      "models_stating_the_measurement_distance"):
            if e[field] > n:
                problems.append(f"emf.{field} = {e[field]} exceeds models_indexed = {n}")
        if e["models_stating_the_measurement_distance"] > e["models_with_a_numeric_emf_claim"]:
            problems.append(
                "emf: more models state a measurement distance "
                f"({e['models_stating_the_measurement_distance']}) than state a numeric "
                f"claim ({e['models_with_a_numeric_emf_claim']}) — distance is filtered "
                "from the numeric-claim set, so this is impossible")
        if sum(n for _, n in e["top_labels"]) > n:
            problems.append("emf.top_labels sums to more than models_indexed")
    return problems


def inv_min_median_max(facts, m):
    """Every min/median/max triple must be ordered. Catches a column swap or a
    unit-parse regression without knowing what the values should be."""
    problems = []
    triples = {}
    for path, val in m.items():
        for suffix in (".min", ".median", ".max"):
            if path.endswith(suffix):
                triples.setdefault(path[: -len(suffix)], {})[suffix[1:]] = val
    for base, t in sorted(triples.items()):
        if {"min", "median", "max"} <= set(t):
            if not (t["min"] <= t["median"] <= t["max"]):
                problems.append(f"{base}: min/median/max out of order — "
                                f"{t['min']} / {t['median']} / {t['max']}")
    # amps_min <= amps_median <= amps_max, which do not share the dotted suffix
    for cluster_path in [p for p in m if p.endswith(".amps_min")]:
        stem = cluster_path[: -len(".amps_min")]
        lo, mid, hi = (m.get(f"{stem}.amps_{k}") for k in ("min", "median", "max"))
        if None not in (lo, mid, hi) and not (lo <= mid <= hi):
            problems.append(f"{stem}: amps min/median/max out of order — {lo} / {mid} / {hi}")
    return problems


def inv_non_negative(facts, m):
    return [f"{p} is negative: {v}" for p, v in sorted(m.items()) if v < 0]


def inv_same_source_agrees(facts, m):
    """emf and electrical both read bhis_saunas. If they disagree on how many
    rows that file has, one of them is reading a stale or partial load."""
    a, b = m.get("emf.models_indexed"), m.get("electrical.models_indexed")
    if a is not None and b is not None and a != b:
        return [f"emf.models_indexed = {a} but electrical.models_indexed = {b}; "
                f"both read data/facts/bhis_saunas.json and must agree"]
    return []


def inv_label_coverage(facts, m):
    """A label-parse regression (renamed column, changed wording) would empty
    emf_label while leaving the row count intact. A floor at HALF the index
    catches that without asserting a count."""
    e = facts.get("emf")
    if not e:
        return []
    n, lab = e["models_indexed"], e["models_with_an_emf_label"]
    if n and lab < n * 0.5:
        return [f"emf: only {lab} of {n} models carry an EMF label "
                f"({lab / n:.0%}) — below the 50% floor, which points at a parse "
                f"or column change rather than a publisher edit"]
    return []


INVARIANTS = [
    ("filtered counts never exceed their source set", inv_subsets),
    ("min <= median <= max everywhere", inv_min_median_max),
    ("no metric is negative", inv_non_negative),
    ("clusters reading one file agree on its row count", inv_same_source_agrees),
    ("EMF labels cover at least half the index", inv_label_coverage),
]


def check_invariants(facts, m):
    problems = []
    for label, fn in INVARIANTS:
        for p in fn(facts, m):
            problems.append(f"[{label}] {p}")
    return problems


# ── DRIFT ───────────────────────────────────────────────────────────────────

def compare(base, cur, tolerance):
    """(drift rows, halting problems). A metric moving more than `tolerance`, or
    collapsing to zero from a non-zero baseline, halts; anything else reports."""
    drift, halts = [], []
    for path in sorted(set(base) | set(cur)):
        old, new = base.get(path), cur.get(path)
        if old == new:
            continue
        if old is None:
            drift.append((path, "—", new, "new metric"))
            continue
        if new is None:
            halts.append(f"{path} is in the baseline but no longer derived at all — "
                         f"a metric that disappears is a schema change, not drift")
            continue
        if old == 0:
            drift.append((path, old, new, "was zero"))
            continue
        pct = (new - old) / abs(old)
        drift.append((path, old, new, f"{pct:+.1%}"))
        if new == 0 and path not in MAY_BE_ZERO:
            halts.append(f"{path} collapsed from {old} to 0")
        elif abs(pct) > tolerance and abs(new - old) > MIN_ABS_MOVE:
            halts.append(f"{path} moved {pct:+.1%} ({old} -> {new}), beyond the "
                         f"{tolerance:.0%} tolerance — too large to be maintenance")
    return drift, halts


def load_baseline():
    if not BASELINE.exists():
        return None
    return json.loads(BASELINE.read_text())


def write_baseline(m, facts):
    doc = {
        "note": "Baseline for scripts/check_facts_drift.py. Derived facts, not raw "
                "rows. Updated ONLY by an explicit --accept run, so that a "
                "publisher's edit is acknowledged by a human rather than absorbed "
                "silently. Drift against this is a report; the invariants in that "
                "script are what halt.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_fetched_at": {c: b.get("fetched_at") for c, b in sorted(facts.items())},
        "metrics": {k: m[k] for k in sorted(m)},
    }
    BASELINE.write_text(json.dumps(doc, indent=1) + "\n")


def self_test():
    """Every invariant, fired at facts that break it."""
    fails = []

    def expect(label, facts, needle):
        m = metrics_of(facts)
        blob = " | ".join(check_invariants(facts, m))
        if needle not in blob:
            fails.append(f"{label}: expected a problem containing {needle!r}, got {blob!r}")

    base_emf = {"models_indexed": 90, "models_with_an_emf_label": 90,
                "models_with_a_numeric_emf_claim": 46,
                "models_stating_the_measurement_distance": 34,
                "distinct_label_wordings": 4, "top_labels": [["Near Zero EMF", 71]]}
    ok = {"emf": dict(base_emf)}
    if check_invariants(ok, metrics_of(ok)):
        fails.append("invariants fired against a healthy fact block")

    e = dict(base_emf); e["models_with_an_emf_label"] = 200
    expect("subset", {"emf": e}, "exceeds models_indexed")

    e = dict(base_emf); e["models_stating_the_measurement_distance"] = 60
    expect("distance subset", {"emf": e}, "impossible")

    e = dict(base_emf); e["models_with_an_emf_label"] = 3
    expect("label coverage", {"emf": e}, "50% floor")

    expect("ordering", {"fit": {"width_in": {"min": 90, "median": 50, "max": 60}}},
           "out of order")
    expect("amps ordering",
           {"electrical": {"by_voltage": [{"volts": 120, "models": 4, "amps_min": 30,
                                           "amps_median": 15, "amps_max": 20}]}},
           "amps min/median/max out of order")
    expect("negative", {"fit": {"models": -1}}, "is negative")
    expect("cross-cluster", {"emf": dict(base_emf),
                             "electrical": {"models_indexed": 12}}, "must agree")

    # drift: maintenance reports, a collapse and a big move halt
    d, h = compare({"a": 90}, {"a": 87}, 0.25)
    if h:
        fails.append(f"a 3% move halted: {h}")
    if not d:
        fails.append("a 3% move produced no drift row")
    _, h = compare({"a": 90}, {"a": 0}, 0.25)
    if not any("collapsed" in x for x in h):
        fails.append("a collapse to zero did not halt")
    _, h = compare({"a": 90}, {"a": 9}, 0.25)
    if not any("beyond" in x for x in h):
        fails.append("a 90% move did not halt")
    # small-n: one model leaving a four-model group is 25%, and must NOT halt
    d, h = compare({"a": 4}, {"a": 3}, 0.25)
    if h:
        fails.append(f"a 4 -> 3 move halted on percentage alone: {h}")
    if not d:
        fails.append("a 4 -> 3 move produced no drift row")
    # but most of a small group vanishing does halt
    _, h = compare({"a": 5}, {"a": 1}, 0.25)
    if not any("beyond" in x for x in h):
        fails.append("a 5 -> 1 move did not halt")
    _, h = compare({"a": 90}, {}, 0.25)
    if not any("no longer derived" in x for x in h):
        fails.append("a vanished metric did not halt")
    d, h = compare({}, {"a": 5}, 0.25)
    if h or not d:
        fails.append("a brand-new metric should report, not halt")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tolerance", type=float, default=0.25,
                    help="fractional move above which drift is treated as a breach")
    ap.add_argument("--accept", action="store_true",
                    help="rewrite the baseline from the current cache. Deliberate "
                         "act: it acknowledges a publisher's edit.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        fails = self_test()
        if fails:
            sys.exit("HALT: this checker's own controls did not fire:\n  " + "\n  ".join(fails))
        print("check_facts_drift self-test: every invariant fires against a "
              "known-bad fact block, and drift/halt thresholds behave")
        return

    facts = derive()
    if not facts:
        sys.exit("HALT: no fact cluster could be derived at all — the cache is "
                 "missing or unreadable. Absence is not a clean result.")
    m = metrics_of(facts)
    print(f"derived {len(facts)} cluster(s), {len(m)} numeric metric(s): "
          f"{', '.join(sorted(facts))}")

    problems = check_invariants(facts, m)

    if args.accept:
        if problems:
            sys.exit("HALT: refusing to baseline facts that break their own "
                     "invariants:\n  " + "\n  ".join(problems))
        write_baseline(m, facts)
        print(f"baseline rewritten: {BASELINE.relative_to(ROOT)} "
              f"({len(m)} metrics)")
        return

    base = load_baseline()
    if base is None:
        print(f"\nno baseline yet — run --accept to create "
              f"{BASELINE.relative_to(ROOT)}. Invariants still applied.")
        drift, halts = [], []
    else:
        drift, halts = compare(base["metrics"], m, args.tolerance)

    if drift:
        print(f"\nDRIFT vs baseline of {base['generated_at'][:10]} "
              f"({len(drift)} metric(s) moved). This is a FINDING, not a failure:")
        for path, old, new, note in drift:
            print(f"  {path:56s} {str(old):>10} -> {str(new):<10} {note}")
    elif base is not None:
        print("\nno drift: every metric matches the baseline")

    for p in problems:
        print(f"\n  INVARIANT  {p}")
    for h in halts:
        print(f"  THRESHOLD  {h}")

    if problems or halts:
        sys.exit(f"\nHALT: {len(problems)} invariant breach(es) and {len(halts)} "
                 f"threshold breach(es). These are not publisher edits — a subset "
                 f"larger than its source, an unordered median or a collapsed count "
                 f"means the data or the parse is wrong.")
    if drift:
        print("\nDrift only, no breach. If these values are the publisher's doing, "
              "acknowledge them with --accept.")


if __name__ == "__main__":
    main()
