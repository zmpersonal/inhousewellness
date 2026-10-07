#!/usr/bin/env python3
"""r3-electrical Part B, step 6: the publish review (the round's one stop). Read-only.

    .venv/bin/python scripts/r3_publish_review.py --base 7ded6fd

Scope: every record this round TOUCHED (new, or any field changed since --base) that maps to a priced
InHouse Wellness sauna. For each that now meets the unchanged threshold and has no live page, it proposes
a title and handle (scripts/verified_titles.py rules: R2-D1/D2) and shows the stated circuit VERBATIM
(the same quote the electrical tool would show) and the decision(s) it relies on. Records that still fail
the threshold are listed with what they lack. Writes docs/verified/r3-electrical/publish-review.md and
.../publish-review.csv (the approval sheet). Nothing is published or frozen here.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "docs/verified/r3-electrical"
COVER_TAG = "(shared cover, r3 D1)"


def walk(a, b, p=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            yield from walk(a.get(k), b.get(k), p + "." + k)   # missing-ok: an absent key IS a difference to report
    elif a != b:
        yield p


def decisions_for(r, base_rec, d5_sources, d3_urls, r3_leads) -> list[str]:
    out = []
    blob = json.dumps(r, ensure_ascii=False)                      # source URLs carry "™": compare unescaped
    base_blob = json.dumps(base_rec, ensure_ascii=False) if base_rec else ""
    if base_rec is None:
        lead = r3_leads.get(r["inh_id"])
        out.append("D11 (manufacturer-site fetch)" if lead == "D11" else "D6 (manufacturer product entry)")
    if COVER_TAG in blob:
        out.append("D1 (shared cover)")
    if any(u in blob for u in d5_sources) and (base_rec is None or base_rec["dimensions"]["exterior"] != r["dimensions"]["exterior"]):
        out.append("D5 (exterior WDH)")
    if any(u in blob and u not in base_blob for u in d3_urls):   # only when the hash check ADDED the citation
        out.append("D3 (our-page manual, byte-identical manufacturer copy)")
    return out or ["existing rules (no new decision)"]


def main(argv=None) -> None:
    import verified_pages as vp
    import verified_titles as vt
    import electrical_build as eb
    from electrical_coverage import load
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="commit the round started from")
    a = ap.parse_args(argv)
    ds = vp.load_dataset()
    base = {r["inh_id"]: r for r in json.loads(subprocess.run(["git", "show", f"{a.base}:data/verified/saunas.json"],
                                                             capture_output=True, text=True, cwd=ROOT).stdout)["records"]}
    _, handles, active, mapped, cost = load()
    nav = vp.load_navigation()
    priced = {x["handle"]: x for x in cost if x["fields"]["price_usd"]["value"] is not None}
    rec_to_product = {k: v["product_handle"] for k, v in nav["mapped"].items()}
    th = {r["inh_id"]: t for r, t in vp.threshold(ds)}
    d5 = set(json.loads((ROOT / "data/verified/r3/d5-exterior-approved.json").read_text())["source_urls"])
    d3p = ROOT / "data/verified/r3/ownpage-manual-hashes.json"
    d3 = {m["manufacturer_copy"] for m in json.loads(d3p.read_text())["manuals"].values() if m.get("manufacturer_copy")} if d3p.exists() else set()
    leads = json.loads((ROOT / "data/verified/internal/leads/inh-priced-r3-2026-10-07.json").read_text())["products"]
    lead_kind = {r["model"]: ("D11" if r.get("r3_lead_kind") else "D6") for r in leads}

    touched = []
    for r in ds["records"]:
        b = base.get(r["inh_id"])
        if b is not None and not ({".".join(x.split(".")[:3]) for x in walk(b, r)} - {".provenance.cache_manifest_sha256"}):
            continue
        prod = rec_to_product.get(r["inh_id"])
        if prod not in priced:
            if b is not None:
                continue
            # A NEW record built for a priced sauna that the navigation map cannot link yet (D14):
            # it meets or fails the threshold like any other and must be accounted for here.
            prod = "(unlinked: needs D14)"
        touched.append((r, b, prod))
    r3_leads = {}
    for r, b, _ in touched:
        mn = (r["identity"]["model_number"]["value"] or "")
        r3_leads[r["inh_id"]] = next((k for m, k in lead_kind.items() if re.sub(r"\W", "", m).upper() == re.sub(r"\W", "", mn).upper()), "D6")

    frozen = json.loads(vt.HANDLES.read_text())["handles"]
    eligible = [(r, b, p) for r, b, p in touched if th[r["inh_id"]]["meets"] and (handles.get(r["inh_id"]) or {}).get("handle") not in active]
    props = vt.propose([(r, th[r["inh_id"]]["capacity_label"]) for r, _, _ in eligible])
    taken = {v["handle"] for v in frozen.values()}
    rows = []
    for o, (r, b, prod) in zip(props, eligible):
        if r["inh_id"] in frozen:
            o["handle"], o["flags"] = frozen[r["inh_id"]]["handle"], o["flags"] + ["handle already frozen; kept"]
        elif o["handle"] in taken:
            o["flags"].append(f"'{o['handle']}' is frozen for another record: needs a human choice")
        m = eb.model_entry(r, o["handle"], o["title"], True, {})
        circ = [s for s in m["statements"] if s["about_circuit"]]
        quote = " / ".join(("…" if s["quote"]["lead"] else "") + "“" + s["quote"]["text"] + "”" + ("…" if s["quote"]["trail"] else "") for s in circ)
        src = "; ".join(sorted({s["source_url"] for s in circ}))
        rows.append({"inh_id": r["inh_id"], "brand": r["identity"]["brand"]["value"], "inh_product": prod,
                     "proposed_title": o["title"], "proposed_handle": o["handle"], "stated_circuit_verbatim": quote or "— (none stated)",
                     "circuit_source": src, "decisions": "; ".join(decisions_for(r, b, d5, d3, r3_leads)),
                     "flags": "; ".join(o["flags"]), "approve (y/n/edit)": ""})
    failing = [(r, b, p) for r, b, p in touched if not th[r["inh_id"]]["meets"]]

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "publish-review.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["inh_id"])
        w.writeheader()
        for x in sorted(rows, key=lambda x: (x["brand"], x["proposed_handle"])):
            w.writerow(x)
    with_circuit = sum(1 for x in rows if not x["stated_circuit_verbatim"].startswith("—"))
    md = ["# r3-electrical: publish review (the round's stop point)", "",
          f"Generated by `scripts/r3_publish_review.py --base {a.base}` from the dataset; nothing is published or frozen.",
          "Approve, edit or reject each row in `publish-review.csv` (last column).", "",
          f"**{len(rows)} records proposed** (new or newly eligible, mapped to a priced INH sauna, meeting the unchanged "
          f"threshold, no live page). **{with_circuit}** of them show a manufacturer-stated circuit.", "",
          "| # | Brand | INH product | Proposed title | Proposed handle | Stated circuit (verbatim) | Relies on | Flags |",
          "|---|---|---|---|---|---|---|---|"]
    for i, x in enumerate(sorted(rows, key=lambda x: (x["brand"], x["proposed_handle"])), 1):
        md.append(f"| {i} | {x['brand']} | `{x['inh_product']}` | {x['proposed_title']} | `{x['proposed_handle']}` | "
                  f"{x['stated_circuit_verbatim'][:220]} | {x['decisions']} | {x['flags']} |")
    md += ["", f"## Touched records that still FAIL the threshold ({len(failing)})", "",
           "| Record | Brand | INH product | Missing | Note |", "|---|---|---|---|---|"]
    for r, b, p in sorted(failing, key=lambda t: t[0]["inh_id"]):
        e = r["electrical"]
        note = ""
        if "electrical" in th[r["inh_id"]]["missing"]:
            notes = {e[k].get("note") for k in ("stated_amperage", "supply_voltage") if e[k].get("note")}
            note = "; ".join(sorted(x for x in notes if x))
        md.append(f"| `{r['inh_id']}` | {r['identity']['brand']['value']} | `{p}` | {', '.join(th[r['inh_id']]['missing'])} | {note} |")
    (OUT / "publish-review.md").write_text("\n".join(md) + "\n")
    print(f"{len(touched)} touched priced records; {len(rows)} proposed ({with_circuit} with a stated circuit); {len(failing)} still failing")


if __name__ == "__main__":
    main()
