#!/usr/bin/env python3
"""INH Verified — which records get a public page, and (Round 2 Part B) how they render.

    .venv/bin/python scripts/verified_pages.py --threshold    # counts, per brand, sold vs not sold

THE MINIMUM-CONTENT THRESHOLD (Round 2 brief). A record gets a page only if it is
published and has all of:
  * an approved title and handle            (checked at build time, not here)
  * a verified heat type
  * a verified capacity (single value or labelled range)
  * verified exterior dimensions            (assembled width, depth AND height)
  * at least one verified electrical value  (supply voltage, stated amperage,
                                             a labelled circuit, or heater kW)
"Verified" means a value with grade certified, documented, listed or
reviewer_measured. "claimed" is not verified.

"Sold by InHouse Wellness" is decided per BRAND from the store's own product list
(an active product whose vendor names the brand), never from the lead file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import os
SAUNAS = Path(os.environ.get("INH_SAUNAS", ROOT / "data/verified/saunas.json"))
NAV = ROOT / "data/verified/inh-navigation.json"
NAV_PRELIM = ROOT / "data/verified/inh-navigation-preliminary.json"
VERIFIED = {"certified", "documented", "listed", "reviewer_measured"}


def ok(f) -> bool:
    return isinstance(f, dict) and f.get("value") is not None and f.get("grade") in VERIFIED


def load_dataset() -> dict:
    return json.loads(SAUNAS.read_text())


def load_navigation() -> dict:
    return json.loads((NAV if NAV.exists() else NAV_PRELIM).read_text())


_SOLD: set | None = None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"(?i)\b(saunas?|inc|llc)\b", "", s).lower())


def brand_sold(r) -> bool:
    global _SOLD
    if _SOLD is None:
        from verified_inh_map import SNAPSHOT, from_census
        snap = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else from_census()
        _SOLD = {_norm(p["vendor"]) for p in snap["products"] if p["status"] == "ACTIVE"}
    b = _norm(r["identity"]["brand"]["value"] or "")
    return bool(b) and any(b in v or v in b for v in _SOLD if v)


def capacity_label(r) -> str | None:
    a, b = r["capacity_min"], r["capacity_max"]
    if not (ok(a) and ok(b)):
        return None
    lo, hi = int(a["value"]), int(b["value"])
    return f"{lo}" if lo == hi else f"{lo}–{hi}"


def has_exterior_dims(r) -> bool:
    a = r["dimensions"]["assembled"]
    return all(ok(a[k]) for k in ("width_in", "depth_in", "height_in"))


def has_electrical(r) -> bool:
    e = r["electrical"]
    return ok(e["supply_voltage"]) or ok(e["stated_amperage"]) or bool(e["circuits"]) or ok(e["heater_kw"])


def threshold(ds):
    for r in ds["records"]:
        if r["status"] != "published":
            continue
        missing = [name for name, good in (("heat type", ok(r["heat_type"])),
                                           ("capacity", capacity_label(r) is not None),
                                           ("exterior dimensions", has_exterior_dims(r)),
                                           ("electrical", has_electrical(r))) if not good]
        yield r, {"meets": not missing, "missing": missing, "capacity_label": capacity_label(r)}


def threshold_report(ds) -> dict:
    per_brand, missing = {}, Counter()
    backlog = Counter()
    for r in ds["records"]:
        if r["status"] == "backlog":
            for w in r.get("withheld_reasons") or ["unspecified"]:
                backlog[str(w).split(":")[0]] += 1
    for r, t in threshold(ds):
        b = r["identity"]["brand"]["value"]
        row = per_brand.setdefault(b, {"sold_by_inh": brand_sold(r), "published": 0, "meets": 0})
        row["published"] += 1
        row["meets"] += t["meets"]
        for m in t["missing"]:
            missing[m] += 1
    sold = [v for v in per_brand.values() if v["sold_by_inh"]]
    not_sold = [v for v in per_brand.values() if not v["sold_by_inh"]]
    return {"per_brand": dict(sorted(per_brand.items())),
            "totals": {"published": sum(v["published"] for v in per_brand.values()),
                       "meets": sum(v["meets"] for v in per_brand.values()),
                       "sold_by_inh": {"published": sum(v["published"] for v in sold), "meets": sum(v["meets"] for v in sold)},
                       "not_sold_by_inh": {"published": sum(v["published"] for v in not_sold), "meets": sum(v["meets"] for v in not_sold)}},
            "below_threshold_missing_field_counts": dict(missing.most_common()),
            "backlog_reasons": dict(backlog.most_common())}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", action="store_true")
    a = ap.parse_args(argv)
    if a.threshold:
        print(json.dumps(threshold_report(load_dataset()), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.exit(main())
