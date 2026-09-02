#!/usr/bin/env python3
"""Track B — the weekly finding. Facebook only, 1/week.

Probes compute the finding; the model writes only the copy around it. One post
carrying a full finding, so it may run a longer brief than a Track A pin — but
it is one post a week against Pinterest's fourteen, so it must not distort the
weekly total. Cost is reported per track.

Destination bypasses the router: a finding links to the site holding the data,
and is exempt from the per-URL cap because a finding is a one-off.

The link goes in the FIRST COMMENT, never the body -- Meta throttles posts that
send people off-platform. Code owns the URL; any the model emits is stripped.

Usage:
  python3 scripts/run_finding.py --list
  python3 scripts/run_finding.py --live [--publish]
"""
import argparse, datetime as dt, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src import breadcrumb as BC
from src import probes as P
from src.validator import validate
import render as RENDER

STAGE = ROOT / "out" / "findings"


def build_prompt(f):
    return f"""You write for InHouse Wellness, a US retailer of home saunas and cold plunges.
Audience: forty to sixty, middle to upper-middle class, researching a major
considered purchase over months. Adult-to-adult. Specific numbers over
adjectives. Corrective and contrarian is the proven register. No hype, no emoji,
no engagement bait.

(Note: this brief deliberately spells out any quantity in words. Every DIGIT you
write is checked against the figures block below, so a number echoed from these
instructions will be rejected.)

This is the WEEKLY FINDING: one Facebook post carrying one result computed from
a published dataset.

THE FINDING (computed, not written by you):
  claim      {f['claim']}
  figures    {json.dumps(f['figures'])}
  dataset    {f['dataset_name']}   fetched {f['fetch_date']}   n = {f['n']}
  {('note       ' + f['note']) if f.get('note') else ''}

RULES, enforced in code:
- Every numeral you write must come from `figures` above, verbatim. Do not
  round, convert, average or extrapolate. Introduce no figure of your own.
- The post MUST name the dataset ({f['dataset_name']}) and the fetch date
  ({f['fetch_date']}). A finding without its source is an opinion.
- Put NO URL anywhere. The system appends the link to the first comment itself.
- Say what the finding means for someone choosing a cabin. One implication,
  not three.
- On any health-adjacent point (heat, cold, circulation, recovery, sleep,
  blood pressure, cardiac load) you MUST hedge -- "may support", "associated
  with", "evidence is limited" -- and add a contraindication where cold exposure
  or cardiac load is involved. Unhedged health copy is rejected in code.

Return ONLY this JSON object, no prose, no markdown fence:
{{"text": "<600-1100 chars, Facebook native>",
  "first_comment": "<short lead-in phrase, NO url>",
  "card": {{"kicker": "<2-4 words, sentence case, never ALL-CAPS>",
            "headline": "<6-14 words, the finding itself>",
            "note": "<one line naming {f['dataset_name']} and {f['fetch_date']}>"}}}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--pick", type=int, default=0)
    a = ap.parse_args()

    findings = P.publishable(P.run_all())
    print(f"unpublished findings above the {P.NOTABILITY_FLOOR} floor: {len(findings)}")
    if a.list or not (a.live or a.publish):
        for i, f in enumerate(findings[:10], 1):
            print(f"{i:2d}. [{f['notability']:.2f}] {f['kind']:14s} n={f['n']:<5} "
                  f"{f['dataset_name']}")
            print(f"    {f['claim']}")
            print(f"    chart={f['chart']['type']:6s} -> {f['destination']}")
        return 0

    if len(findings) < 10:
        print(f"\n🔴 BLOCKED: only {len(findings)} findings clear the floor. The probe "
              f"library is too narrow — widen it rather than lowering the floor.")
        return 2

    f = findings[a.pick]
    print(f"\nselected: [{f['notability']:.2f}] {f['claim']}")

    from src import model as MODEL
    call = MODEL.make_caller()
    import re
    prompt, tin_tot, tout_tot, attempts = build_prompt(f), 0, 0, []

    def parse(raw):
        m = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
        return json.loads((m.group(1) if m else raw).strip())

    # grounding: only the probe's own figures
    from src.facts import _walk_numbers, _fmt_num
    nums = []
    _walk_numbers(f["figures"], nums)
    _walk_numbers(f["chart"], nums)
    grounding = " ".join(_fmt_num(n) for n in nums) + " " + f["fetch_date"]

    STAGE.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().isoformat()

    post = pngs = None
    for attempt in range(2):
        raw, tin, tout = call(prompt)
        tin_tot += tin
        tout_tot += tout
        obj = parse(raw)

        card = dict(obj.get("card") or {})
        card["chart"] = f["chart"]
        lead = re.sub(r"https?://\S+", "", obj.get("first_comment", "")).strip(" :-\u2014")
        post = {
            "id": f["id"].replace(":", "-"), "platform": "facebook",
            "text": obj["text"], "mediaUrls": [],
            "firstComment": f"{lead}: {f['destination']}" if lead else f["destination"],
            "_is_finding": True, "_dataset_name": f["dataset_name"],
            "_fetch_date": f["fetch_date"], "_archetype": "chart", "_body": card,
        }
        cards = [{"id": post["id"], "size": "ig", "type": "chart",
                  "kicker": card.get("kicker", "Weekly finding"),
                  "headline": card.get("headline", f["claim"]),
                  "note": card.get("note", ""), "chart": f["chart"]}]
        pngs = RENDER.render(cards, STAGE / day)
        post["mediaUrls"] = [f"https://database.blotato.io/staged/{pngs[0].name}"]

        r = validate(post, grounding=grounding)
        if r.ok:
            break
        attempts.append(f"attempt {attempt + 1}: {r.summary()}")
        print(f"[validate] RETRY — {r.summary()}")
        prompt = build_prompt(f) + (
            "\n\nYour previous attempt was REJECTED in code. Fix exactly these "
            "problems and return the full corrected object:\n" + r.summary())
    else:
        usd = tin_tot / 1e6 * 5.0 + tout_tot / 1e6 * 25.0
        print(f"[caption] tokens {tin_tot} in / {tout_tot} out = ${usd:.4f}")
        print("\n🔴 BLOCKED — finding rejected after 2 attempts, nothing published")
        for aerr in attempts:
            print("  " + aerr)
        return 2

    usd = tin_tot / 1e6 * 5.0 + tout_tot / 1e6 * 25.0
    print(f"[caption] tokens {tin_tot} in / {tout_tot} out = ${usd:.4f}  "
          f"(Track B, 1 post/week)")
    print(f"[validate] PASS")

    out = STAGE / day / "finding.json"
    out.write_text(json.dumps({"finding": f, "post": post, "usd": round(usd, 4),
                               "tokens_in": tin_tot, "tokens_out": tout_tot,
                               "attempts": attempts,
                               "media_local": str(pngs[0])}, indent=1))
    print(f"[stage]   {out}")
    print(f"[stage]   card {pngs[0]} ({pngs[0].stat().st_size:,} bytes)")
    if not a.publish:
        print("[stage]   published nothing — pass --publish to go live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
