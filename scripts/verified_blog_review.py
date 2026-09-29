#!/usr/bin/env python3
"""Round 4: write the human review file for blog links from verified_blog_links.py output, with the
agent's recommendation per hub candidate (a judgment, recorded with its reason, for the user to overrule).

    .venv/bin/python scripts/verified_blog_review.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/verified/r4"

HUB_ASSESS = {   # article handle -> (recommend, reason)
    "finnmark-designs-fd-4-review": ("no", "the sentence is about a Finnmark model; the database has no Finnmark pages, so the link would imply coverage it lacks"),
    "finnmark-designs-saunas": ("no", "about the Finnmark lineup, which the database does not cover"),
    "home-sauna-steam-room-lifetime-operating-costs": ("yes", "general sauna advice about electrical requirements; the hub lists them per model"),
    "infrared-sauna-benefits": ("yes", "names exactly what the hub holds (electrical requirement, cabin size) as things a reader should know"),
    "sauna-narrow-hallway-doorway-fit-guide": ("yes", "tells the reader to confirm dimensions and electrical requirements; the hub lists both per model"),
    "sisu-sauna-review": ("no", "compares Sisu, which the database does not cover"),
    "small-space-sauna-guide-corner-straight-wall-compact-cabin": ("no", "the phrase is a heading-like line, not running text"),
    "sunray-roslyn-vs-almost-heaven-madison-which-indoor-sauna-is-right-for-you": ("yes", "a generic 'review electrical requirements' sentence in a buyer comparison"),
    "true-total-cost-home-sauna": ("no", "the sentence already directs the reader to another article; a second link there muddles it"),
    "insurance-permits-code-thermal-rooms": ("no", "the sentence is about cold-plunge plumbing and electrical, not saunas"),
    "sauna-vs-cold-plunge-vs-red-light-therapy": ("no", "the sentence is about a red-light panel's outlet, not saunas"),
    "dry-sauna-for-home": ("yes", "a buyer guide for a home sauna; no phrase to link, so one new closing sentence"),
    "indoor-vs-outdoor-sauna-guide": ("yes", "a buyer guide that weighs electrical and siting; one new closing sentence"),
    "arcadia-barrel-sauna-guide": ("yes", "a buyer guide covering barrel sizes and power; one new closing sentence"),
    "renovation-sequencing-wellness-installations": ("yes", "planning electrical work for a sauna installation; one new closing sentence"),
    "almost-heaven-audra-shenandoah": ("no", "both models are held back in the database (backlog); a database link beside them suggests pages that do not exist"),
    "are-infrared-saunas-safe": ("no", "a safety and health article; a product-database link does not fit"),
    "downdraft-sauna-ventilation-design-patterns": ("no", "ventilation design; the database does not cover ventilation"),
    "finnmark-fd4-vs-almost-heaven-audra": ("no", "compares two models neither of which has a page"),
    "golden-designs-osla-edition-review": ("no", "reviews a Golden Designs model without a page; a hub link invites a search that finds nothing for it"),
    "hidden-failure-points-diy-sauna-steam-projects": ("no", "DIY construction; the database covers manufactured models"),
    "sauna-ventilation-designers-co2-pm25-air-change-targets": ("no", "ventilation engineering; not what the database covers"),
    "saunalife-model-g6-review": ("no", "SaunaLife models have no pages (heat type and electrical not verified)"),
}


def main():
    from src.health_claims import find_banned_claims
    d = json.loads((OUT / "blog-link-proposals.json").read_text())
    missing = []
    for h in d["hub_links"]:
        k = h["article"].rsplit("/", 1)[1]
        if k not in HUB_ASSESS:
            missing.append(k)
        h["recommend"], h["reason"] = HUB_ASSESS.get(k, ("?", "not assessed"))
        if h["new_words"]:
            h["health_gate"] = "FAILED" if find_banned_claims(h["sentence_after"]) else "clean"
    if missing:
        raise SystemExit(f"HALT: hub candidates without an assessment: {missing}")
    (OUT / "blog-link-proposals.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    hubs = sorted(d["hub_links"], key=lambda h: (h["recommend"] != "yes", h["article"]))
    yes = [h for h in hubs if h["recommend"] == "yes"]
    L = ["# Round 4 Part A: blog link review", "",
         "Proposed only; nothing is written. **One link per model, at its first eligible mention; at most 3 per article; no "
         "other word changes.** Eligible text excludes headings, existing links, image alt text, product/CTA blocks, "
         "bold run-in labels (hub links) and reference-list entries (any sentence carrying a URL).", "",
         f"## A. Model links: {len(d['model_links'])} in {len({r['article'] for r in d['model_links']})} articles", "",
         "| # | Article | Linked text | Sentence before | Sentence after | Target page | Note |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(d["model_links"], 1):
        L.append(f"| M{i} | {r['article'].split('.com')[1]} | {r['anchor']} | {r['sentence_before']} | {r['sentence_after']} | "
                 f"{r['target']} | {r.get('note') or ''} |")
    L += ["", "The article text in M1 already quotes a price. We add a link only; the price is the article's own and "
          "unchanged, and the target page shows none.", "",
          f"### Not linked: ambiguous, or no page for that variant ({len(d['ambiguous'])})", "",
          "| Article | Mention | Pages it could mean |", "|---|---|---|"]
    for x in d["ambiguous"]:
        L.append(f"| {x['article'].split('.com')[1]} | {x['mention']} | {', '.join(x['candidates']) or 'none: no page for that variant'} |")
    L += ["", f"## B. Hub links: {len(hubs)} candidates, {len(yes)} recommended", "",
          "Candidates are sauna articles naming no model with a page that discuss electrical requirements or sizing. "
          "'Existing phrase': that phrase is linked and no word changes. 'New sentence': ONE sentence appended as the "
          "article's last paragraph; the health gate was run on it.", "",
          "| # | Article | Recommend | Why | Kind | Sentence before | Sentence after |", "|---|---|---|---|---|---|---|"]
    for i, h in enumerate(hubs, 1):
        kind = "link existing phrase" if not h["new_words"] else f"new sentence (health gate: {h['health_gate']})"
        L.append(f"| H{i} | {h['article'].split('.com')[1]} | **{h['recommend']}** | {h['reason']} | {kind} | "
                 f"{h['sentence_before'] or '(none; appended at the end)'} | {h['sentence_after']} |")
    (OUT / "blog-link-review.md").write_text("\n".join(L) + "\n")
    with (OUT / "blog-link-review.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "article", "kind", "linked_text", "sentence_before", "sentence_after", "target", "recommend", "reason", "approve (y/n)"])
        for i, r in enumerate(d["model_links"], 1):
            w.writerow([f"M{i}", r["article"], "model", r["anchor"], r["sentence_before"], r["sentence_after"], r["target"], "yes", r.get("note") or "", ""])
        for i, h in enumerate(hubs, 1):
            w.writerow([f"H{i}", h["article"], "hub (new sentence)" if h["new_words"] else "hub (existing phrase)", h["anchor"] or "",
                        h["sentence_before"] or "", h["sentence_after"], h["target"], h["recommend"], h["reason"], ""])
    print(f"model {len(d['model_links'])}; hub {len(hubs)} candidates, {len(yes)} recommended "
          f"({sum(1 for h in yes if not h['new_words'])} existing phrase, {sum(1 for h in yes if h['new_words'])} new sentence)")


if __name__ == "__main__":
    main()
