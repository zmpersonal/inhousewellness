#!/usr/bin/env python3
"""Electrical tool, Round 1 Part A — what the Verified database can answer (read-only).

    .venv/bin/python scripts/electrical_coverage.py            # prints the report
    .venv/bin/python scripts/electrical_coverage.py --json OUT # also writes it

Reads data/verified/saunas.json, the frozen handles, the live launch state, the INH navigation
map and data/cost-tables.json. Writes nothing unless --json is given. Offline, deterministic.

Each record gets ONE answer class, in this order (the tool's precedence, rule 1 first):

  A  manufacturer states a breaker size            (electrical.breaker_amps)
  B  manufacturer states a circuit rating          (circuits[], or stated_amperage that the
                                                    source ties to a circuit — the approved
                                                    Round 3 rule, verified_pages.amperage_is_circuit)
  C  rated heater kW AND its voltage are stated    -> a code-based minimum is computable
  C? rated heater kW stated, voltage NOT stated    -> computable only if the reader supplies it
  D  an amperage is stated but not tied to a circuit (a draw, or ambiguous: never chosen)
  E  nothing electrical that answers the question

kW is never derived from volts x amps (rule 3). A kW from data/cost-tables.json is reported in
its own column and never promoted: it comes from InHouse Wellness's own catalogue, which the
editorial-independence rule bars as evidence.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from verified_pages import amperage_is_circuit  # noqa: E402  (the approved R3 wording rule)

HEATER_PURPOSE = ("stove", "heater", "kw")


def heater_voltage(e: dict) -> str | None:
    """The voltage the HEATER is stated to run on: heater_voltage, else a circuit whose stated
    purpose names the stove/heater, else supply_voltage when it is the only circuit stated.
    Never a guess from kW."""
    if e["heater_voltage"]["value"]:
        return e["heater_voltage"]["value"]
    for c in e["circuits"]:
        p = (c["purpose"]["value"] or "").lower()
        if c["voltage"]["value"] and any(w in p for w in HEATER_PURPOSE):
            return c["voltage"]["value"]
    if not e["circuits"] and e["supply_voltage"]["value"]:
        return e["supply_voltage"]["value"]
    return None


def answer_class(r: dict) -> str:
    e = r["electrical"]
    if e["breaker_amps"]["value"] is not None:
        return "A"
    if e["circuits"] or (e["stated_amperage"]["value"] is not None and amperage_is_circuit(e["stated_amperage"])):
        return "B"
    if e["heater_kw"]["value"]:
        return "C" if heater_voltage(e) else "C?"
    if e["stated_amperage"]["value"] is not None:
        return "D"
    return "E"


def load():
    d = json.loads((ROOT / "data/verified/saunas.json").read_text())
    handles = json.loads((ROOT / "data/verified/handles.json").read_text())["handles"]
    active = set(json.loads((ROOT / "data/verified/golive/launch-state.json").read_text())["active_handles"])
    mapped = json.loads((ROOT / "data/verified/inh-navigation.json").read_text())["mapped"]
    cost = json.loads((ROOT / "data/cost-tables.json").read_text())["rows"]
    return d["records"], handles, active, mapped, cost


def build() -> dict:
    records, handles, active, mapped, cost = load()
    hd = lambda r: (handles.get(r["inh_id"]) or {}).get("handle")  # noqa: E731
    by_id = {r["inh_id"]: r for r in records}
    pops = {"active": [r for r in records if hd(r) in active],
            "published": [r for r in records if r["status"] == "published"]}
    out: dict = {"populations": {}}
    for name, pop in pops.items():
        cls = collections.Counter()
        for r in pop:
            sold = "inh_sells" if r["inh_id"] in mapped else "not_sold"
            cls[(sold, r["heat_type"]["value"] or "unknown", answer_class(r))] += 1
        out["populations"][name] = {"n": len(pop),
                                    "classes": [{"inh": k[0], "heat": k[1], "class": k[2], "n": v}
                                                for k, v in sorted(cls.items())]}
    # priced INH SKUs (the cost calculator's population)
    by_product = {v["product_handle"]: k for k, v in mapped.items()}
    priced = [x for x in cost if x["fields"]["price_usd"]["value"] is not None]
    pc = collections.Counter()
    for x in priced:
        rid = by_product.get(x["handle"])
        c = answer_class(by_id[rid]) if rid else "unmapped"
        own_kw = x["fields"]["rated_power_kw"]["value"] is not None
        pc[(c, "own_catalogue_kw" if own_kw else "no_own_kw")] += 1
    out["priced_inh_skus"] = {"n": len(priced),
                              "classes": [{"class": k[0], "own_catalogue": k[1], "n": v} for k, v in sorted(pc.items())]}
    # answer-page candidates: ACTIVE records by stated heater kW
    pages = collections.defaultdict(list)
    for r in pops["active"]:
        kw = r["electrical"]["heater_kw"]["value"]
        if kw:
            e = r["electrical"]
            pages[kw].append({"handle": hd(r), "class": answer_class(r), "heater_voltage": heater_voltage(e),
                              "inh_sells": r["inh_id"] in mapped,
                              "kw_grade": f'{e["heater_kw"]["grade"]}/{e["heater_kw"]["source_type"]}'})
    out["answer_page_candidates"] = {f"{k:g}": sorted(v, key=lambda x: x["handle"]) for k, v in sorted(pages.items())}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    out = build()
    for name, p in out["populations"].items():
        print(f"\n{name}: n={p['n']}")
        for c in p["classes"]:
            print(f"  {c['inh']:9} {c['heat']:12} {c['class']:3} {c['n']}")
    print(f"\npriced INH SKUs: n={out['priced_inh_skus']['n']}")
    for c in out["priced_inh_skus"]["classes"]:
        print(f"  {c['class']:9} {c['own_catalogue']:17} {c['n']}")
    print("\nanswer-page candidates (active):")
    for k, v in out["answer_page_candidates"].items():
        print(f"  {k} kW: {len(v)}")
        for m in v:
            print(f"     {m['handle']:52} {m['class']:3} V={m['heater_voltage']} sells={m['inh_sells']}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
