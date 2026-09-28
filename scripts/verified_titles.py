#!/usr/bin/env python3
"""INH Verified — propose titles and frozen handles for records that meet the page threshold.

    .venv/bin/python scripts/verified_titles.py        # writes docs/verified/round-2-title-review.csv

PROPOSAL ONLY (R2-D1, R2-D2). Nothing here is applied: titles reach
data/verified/title-overrides.json and handles reach data/verified/handles.json only
after the user approves the review file.

Title  = the Round 1 display title (brand + the manufacturer's own product name + capacity,
         plus the R3 fallback where two models share a name) with a fixed list of marketing
         and year words removed. Words are only ever REMOVED, never added or reworded.
Handle = brand-model-name[-capacity], lowercase, no years, no "new", no marketing words,
         at most 60 characters. When two records would share a handle, the edition token
         the manufacturer uses (elite, zf, fs, hem, ced) is appended from the model number.
         Anything the rule cannot settle is FLAGGED for the reviewer, not guessed.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import verified_pages as vp   # the threshold lives in one place, shared with the page build

OUT = ROOT / "docs/verified/round-2-title-review.csv"
HANDLE_MAX = 60
BRAND_SLUG = {"Dynamic Saunas": "dynamic", "Golden Designs": "golden-designs", "Maxxus": "maxxus",
              "Salus": "salus", "Almost Heaven": "almost-heaven", "Clearlight": "clearlight",
              "Heavenly Heat": "heavenly-heat", "Redwood Outdoors": "redwood-outdoors",
              "Sun Home": "sun-home", "Scandia": "scandia", "Medical Saunas": "medical-saunas",
              "SaunaLife": "saunalife", "Dundalk LeisureCraft": "dundalk-leisurecraft"}
# Removed from the TITLE: the manufacturer's marketing and year words. Heat-type words stay.
TITLE_DROP = [r"\bUpdated\b", r"\bLuxury\b", r"\bNew\b", r"\b20\d\d\b", r"\bN[ea]ro? Zero EMF\b",
              r"\bNear Zero EMF\b", r"\bLow EMF\b", r"\bUltra Low EMF\b"]
# Removed from the HANDLE as well: heat-type, placement and generic words (shown on the page instead).
HANDLE_DROP = TITLE_DROP + [r"\band Harvia Traditional Stove\b", r"\bFar IR\b", r"\bFar Infrared\b", r"\bInfrared\b", r"\bIR\b", r"\bTraditional\b",
                            r"\bHybrid\b", r"\bIndoor/Outdoor\b", r"\bIndoor\b", r"\bOutdoor\b", r"\bSauna\b",
                            r"\bDual Tech\b", r"\bHarvia\b", r"\bStove\b", r"\band$"]
EDITION_RX = re.compile(r"(?i)(?:^|[\s-])(elite|zf|fs|hem|ced|hemlock)\b")
MARKETING_LEFT = re.compile(r"(?i)\b(best|premium|ultimate|luxury|deluxe|new|updated|edition)\b")


def clean(s: str, drops) -> str:
    for rx in drops:
        s = re.sub(rx, " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" ,-")


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def cap_slug(cap: str | None) -> str:
    return (slug(cap.replace("–", "-")) + "-person") if cap else ""


def editions(model_number: str | None) -> list[str]:
    return [m.group(1).lower().replace("hemlock", "hem") for m in EDITION_RX.finditer(model_number or "")]


def propose(rows):
    out = []
    for r, cap in rows:
        brand = r["identity"]["brand"]["value"]
        name = r["identity"]["model_name"]["value"] or ""
        mn = r["identity"]["model_number"]["value"]
        flags = []
        # The Round 1 display title already carries the manufacturer's capacity wording and
        # the R3 fallbacks (wood, heater kW, model number); only marketing words are removed.
        title = clean(r["identity"]["display_title"], TITLE_DROP)
        core = clean(name, HANDLE_DROP)
        if not core or core.lower() in {"full spectrum", "s-line"} and not re.search(r"[A-Za-z]{3,}", clean(core, [r"Full Spectrum"])):
            flags.append("manufacturer title names no model; handle falls back to the model number")
            core = mn or r["inh_id"].rsplit("/", 1)[1]
        if MARKETING_LEFT.search(core):
            flags.append(f"marketing word left in model name: '{MARKETING_LEFT.search(core).group(0)}'")
        out.append({"r": r, "cap": cap, "title": title, "core": core, "mn": mn, "flags": flags,
                    "handle": "-".join(x for x in [BRAND_SLUG.get(brand, slug(brand)), slug(core), cap_slug(cap)] if x)})
    # uniqueness: append the manufacturer's edition token, then the model number, never a counter
    for key in ("handle", "title"):
        groups = {}
        for o in out:
            groups.setdefault(o[key], []).append(o)
        for same in groups.values():
            if len(same) < 2:
                continue
            for o in same:
                ed = [e for e in editions(o["mn"]) if e not in o["core"].lower()]
                if key == "handle":
                    base = "-".join(x for x in [BRAND_SLUG.get(o["r"]["identity"]["brand"]["value"]), slug(o["core"])] + ed + [cap_slug(o["cap"])] if x)
                    o["handle"] = base
                else:
                    o["title"] = f"{o['title']} ({o['mn']})"
                    o["flags"].append("title shares its name with another model; model number added (R3 fallback)")
        groups = {}
        for o in out:
            groups.setdefault(o[key], []).append(o)
        for same in groups.values():
            if len(same) > 1:
                for o in same:
                    o["flags"].append(f"{key} still not unique after edition token: needs a human choice")
    for o in out:
        if len(o["handle"]) > HANDLE_MAX:
            o["flags"].append(f"handle is {len(o['handle'])} characters (max {HANDLE_MAX})")
    return out


def main():
    ds = vp.load_dataset()
    nav = vp.load_navigation()
    rows = [(r, t["capacity_label"]) for r, t in vp.threshold(ds) if t["meets"]]
    props = propose(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["inh_id", "brand", "brand_sold_by_inh", "maps_to_inh_product", "current_display_title",
                    "proposed_title", "proposed_handle", "handle_chars", "flags", "approve (y/n/edit)"])
        for o in sorted(props, key=lambda o: (o["r"]["identity"]["brand"]["value"], o["handle"])):
            r = o["r"]
            m = nav["mapped"].get(r["inh_id"])
            w.writerow([r["inh_id"], r["identity"]["brand"]["value"], "yes" if vp.brand_sold(r) else "no",
                        m["product_handle"] if m else "", r["identity"]["display_title"], o["title"], o["handle"],
                        len(o["handle"]), "; ".join(o["flags"]), ""])
    md = [f"# Round 2 title and handle review ({len(props)} records that meet the threshold)", "",
          "Same rows as `round-2-title-review.csv`. Mark each row approve / edit / reject.", "",
          "| # | Brand | Sold by INH | Maps to INH product | Proposed title | Proposed handle | Flags |",
          "|---|---|---|---|---|---|---|"]
    for i, o in enumerate(sorted(props, key=lambda o: (o["r"]["identity"]["brand"]["value"], o["handle"])), 1):
        r = o["r"]; m = nav["mapped"].get(r["inh_id"])
        md.append(f"| {i} | {r['identity']['brand']['value']} | {'yes' if vp.brand_sold(r) else 'no'} | "
                  f"{('`' + m['product_handle'] + '`') if m else '—'} | {o['title']} | `{o['handle']}` | {'; '.join(o['flags'])} |")
    OUT.with_suffix(".md").write_text("\n".join(md) + "\n")
    print(f"{len(props)} rows -> {OUT.relative_to(ROOT)} (+ .md); flagged: {sum(1 for o in props if o['flags'])}")


if __name__ == "__main__":
    main()
