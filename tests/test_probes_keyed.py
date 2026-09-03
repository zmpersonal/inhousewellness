"""Round 12 — the three keyed datasets (EIA, Census, FRED).

Each family must fail INDEPENDENTLY: a missing key costs findings, never the
run. And a probe's own claim text is validated copy like any other, so every
numeral it prints must be groundable in its figures.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import probes as P
from src.facts import _walk_numbers, _fmt_num
from src.validator import check_denominator

KEYED = (P.electricity_cost_probes, P.electricity_trend_probes,
         P.housing_stock_probes)
NEW_KEYS = {"electricity_state_spread", "electricity_median_vs_mean",
            "electricity_decade_trend", "detached_housing_spread"}


def _new_findings():
    return [f for f in P.run_all(exclude_published=False)
            if f["id"].split(":")[1] in NEW_KEYS]


def test_each_family_returns_findings():
    for fn in KEYED:
        assert fn(), f"{fn.__name__} produced nothing"


def test_absent_dataset_yields_no_findings_not_an_exception(monkeypatch):
    """A missing key must cost findings, never take down the library."""
    monkeypatch.setattr(P, "_ds", lambda name: None)
    for fn in KEYED:
        assert fn() == []


def test_every_numeral_in_a_claim_is_grounded():
    """The probe writes the claim, so the probe must ground it.

    Caught a real defect: the trend claim printed '43%' while figures carried
    only the unrounded 42.8, which is exactly UNGROUNDED_NUMERAL.
    """
    for f in _new_findings():
        nums = []
        _walk_numbers(f["figures"], nums)
        _walk_numbers(f["chart"], nums)
        grounding = " ".join(_fmt_num(n) for n in nums) + " " + f["fetch_date"]
        ungrounded = [n for n in set(re.findall(r"\d+(?:\.\d+)?", f["claim"]))
                      if n not in grounding]
        assert not ungrounded, f"{f['id']} prints ungrounded {ungrounded}"


def test_shares_clear_the_denominator_gate():
    for f in _new_findings():
        probe = {"_is_finding": True, "_finding_kind": f["kind"],
                 "_figures": f["figures"], "_baseline": f.get("baseline"),
                 "_population_is_the_subject": f.get("population_is_the_subject")}
        assert check_denominator(probe).ok, f["id"]


def test_eia_aggregate_rows_are_excluded():
    """EIA ships census divisions and a national row beside the states.
    Leaving them in double-counts and puts 'U.S. Total' in a state list."""
    f = [x for x in P.electricity_cost_probes()
         if x["id"].endswith("electricity_state_spread")][0]
    assert f["figures"]["states"] <= 51
    for label in ("low_state", "high_state"):
        assert "U.S." not in str(f["figures"][label])


def test_keyed_findings_carry_a_real_source_and_destination():
    from src.limits import ALLOWED_LINK_HOSTS
    from urllib.parse import urlparse
    for f in _new_findings():
        assert f["fetch_date"] and f["dataset"].startswith("http")
        host = urlparse(f["destination"]).netloc.replace("www.", "")
        assert host in ALLOWED_LINK_HOSTS, f"{f['id']} -> {host}"


def test_probes_are_registered():
    for fn in KEYED:
        assert fn in P.ALL_PROBES
