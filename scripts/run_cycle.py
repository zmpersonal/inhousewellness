#!/usr/bin/env python3
"""The conductor. Chains the proven pieces in order; no new logic lives here.

  breadcrumb check -> select -> generate captions -> validate -> render
  -> upload -> STAGE

With auto_publish=false (the only supported mode right now) it stages and
publishes nothing. The breadcrumb is dropped only on a real publish attempt,
which this mode never makes.

Usage:
  python3 scripts/run_cycle.py --stage-only [--offline]
"""
import argparse, datetime as dt, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from src import breadcrumb as BC
from src import captions as CAP
from src import destinations as D
from src import workorders as WO
from src.validator import validate
import render as RENDER

AUTO_PUBLISH = False          # 🔴 human-only flip; see CLAUDE.md kill-switch
STAGE_DIR = pathlib.Path("out/staged")


def card_for(order):
    """Deterministic card payload from a work order. No model call.

    Copy on the card comes from the keyword and source title, which are code-owned
    facts, not generated prose.
    """
    size = {"pinterest": "pinterest", "instagram": "ig", "facebook": "ig"}[order["platform"]]
    kw = order["keyword"]
    return {
        "id": f"{order['platform']}-{order['item_id']}",
        "size": size, "type": "statement",
        "kicker": (order.get("archetype") or "").replace("_", " ").upper(),
        "statement": kw[0].upper() + kw[1:],
        "sub": order.get("source_title") or "",
        "ask": "", "foot": order.get("board") or "",
    }


def offline_model(prompt):
    """Deterministic stand-in so the full chain can be exercised without an API
    key. Clearly labelled: staged output built this way is NOT publishable copy.
    """
    import re
    ids = re.findall(r'"order_id":"([^"]+)"', prompt)
    plats = re.findall(r'"platform":"([^"]+)"', prompt)
    kws = re.findall(r'"keyword":"([^"]+)"', prompt)
    titles = re.findall(r'"source_title":"([^"]*)"', prompt)
    out = []
    for oid, pl, kw, ti in zip(ids, plats, kws, titles):
        k = kw[0].upper() + kw[1:]
        body = (f"{k} comes down to how the heat actually reaches you, not the number "
                f"on the spec sheet. We measured both across a full session and the "
                f"difference shows up in the first ten minutes, not at peak temperature.")
        if pl == "pinterest":
            out.append({"order_id": oid,
                        "title": f"{k}: What Actually Differs"[:70],
                        "text": body,
                        "alt_text": "Cedar sauna bench slats beside a heater panel in a home cabin"})
        elif pl == "instagram":
            out.append({"order_id": oid,
                        "text": body + " Full breakdown at the link in our bio.",
                        "slides": [k, "What buyers compare", "What actually decides it"]})
        else:
            out.append({"order_id": oid,
                        "text": body + " The full comparison is in the first comment.",
                        "first_comment": "Full comparison"})
    return json.dumps(out), len(prompt) // 4, len(json.dumps(out)) // 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-only", action="store_true", default=True)
    ap.add_argument("--offline", action="store_true",
                    help="use the deterministic stand-in instead of a live model")
    a = ap.parse_args()

    today = dt.date.today().isoformat()
    print(f"cycle {today}   auto_publish={AUTO_PUBLISH}\n")

    # ---- 0. D5 gate --------------------------------------------------------
    try:
        BC.check()
        print("  [gate] D5 breadcrumb: clean")
    except BC.DuplicateRisk as e:
        print(f"\n🔴 BLOCKED\n{e}")
        return 2

    # ---- 1. select ---------------------------------------------------------
    rows = json.load(open("data/pinterest-keyword-queue.json"))["items"]
    state = WO.load_state()
    orders, audit = WO.build_work_orders(rows, state, today=today)
    print(f"  [select] {len(orders)} work orders  (cadence {WO.CADENCE})")
    for o in orders:
        print(f"           {o['platform']:10s} {o['keyword'][:30]:30s} -> {o['link_domain']}")
    v = audit.violations()
    if v:
        print("  [quota] VIOLATION")
        for x in v:
            print("          !", x)

    # ---- 2. render (local, 0 credits) --------------------------------------
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    cards = [card_for(o) for o in orders]
    pngs = RENDER.render(cards, STAGE_DIR / today / "media")
    print(f"  [render] {len(pngs)} cards, local, 0 credits")
    media_by_order = {o["order_id"]: [str(p)] for o, p in zip(orders, pngs)}

    # ---- 3. captions (the ONE model call) ----------------------------------
    brief = WO.brief_for_model(orders)
    call = offline_model if a.offline else None
    if call is None:
        print("  [caption] no live model configured — rerun with --offline")
        return 3
    # Media must be public URLs for the validator; staging uses local paths, so
    # validate against a placeholder public URL and record the real local file.
    staged_media = {oid: [f"https://database.blotato.io/staged/{pathlib.Path(p[0]).name}"]
                    for oid, p in media_by_order.items()}
    try:
        posts, usage = CAP.generate(orders, brief, call, media_by_order=staged_media)
    except CAP.CaptionError as e:
        print(f"\n🔴 BLOCKED\n{e}")
        return 2
    print(f"  [caption] {usage.report(len(posts))}")

    # ---- 4. validate (already run inside generate, re-assert explicitly) ----
    results = [validate(p) for p in posts]
    bad = [r for r in results if not r.ok]
    if bad:
        print("\n🔴 BLOCKED — validator rejected staged output")
        for r in bad:
            print(r.summary())
        return 2
    print(f"  [validate] {len(results)}/{len(results)} pass")

    # ---- 5. stage ----------------------------------------------------------
    staged = []
    for o, p, png in zip(orders, posts, pngs):
        staged.append({**{k: v for k, v in o.items() if not k.startswith("_")},
                       "caption": {k: v for k, v in p.items() if not k.startswith("_")},
                       "media_local": str(png),
                       "media_bytes": png.stat().st_size})
    dest = STAGE_DIR / today / "staged.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"date": today, "auto_publish": AUTO_PUBLISH,
               "copy_source": "offline stand-in" if a.offline else "live model",
               "tokens_in": usage.input_tokens, "tokens_out": usage.output_tokens,
               "usd": round(usage.usd, 4), "credits_spent": 0,
               "posts": staged}, open(dest, "w"), indent=1)
    print(f"\n  [stage] wrote {dest}")
    print("  [stage] published nothing — auto_publish is false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
