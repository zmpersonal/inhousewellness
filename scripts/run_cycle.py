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
import argparse, datetime as dt, json, pathlib, re, sys

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


def first_sentence(text, limit=180):
    t = (text or "").strip().split("\n")[0]
    m = re.split(r"(?<=[.!?])\s+", t)
    out = m[0] if m else t
    return out if len(out) <= limit else out[:limit].rsplit(" ", 1)[0] + "…"


def card_for(order, caption):
    """Card payload built from the APPROVED caption, not from the raw keyword.

    Cards used to render the bare keyword as a headline plus the SEO article
    title as a subhead, which left the frame ~60% empty and said nothing
    specific. The card is what people actually see on Pinterest, so it carries
    the same copy that was validated -- headline from the pin title (already
    written as a keyword-front-loaded page title), supporting line from the
    caption's own first sentence.
    """
    size = {"pinterest": "pinterest", "instagram": "ig", "facebook": "ig"}[order["platform"]]
    text = caption.get("text", "")
    if order["platform"] == "pinterest":
        headline = caption.get("title") or order["keyword"]
        sub = first_sentence(text)
        # Avoid printing the same sentence twice when title and lead overlap.
        if sub.lower().startswith(order["keyword"].lower()):
            parts = re.split(r"(?<=[.!?])\s+", text.strip())
            sub = parts[1] if len(parts) > 1 else sub
    else:
        headline = first_sentence(text, 120)
        paras = [x for x in text.split("\n") if x.strip()]
        sub = first_sentence(paras[1], 200) if len(paras) > 1 else ""
    return {
        "id": f"{order['platform']}-{order['item_id']}",
        "size": size, "type": "statement",
        "kicker": (order.get("archetype") or "").replace("_", " ").upper(),
        "statement": headline,
        "sub": sub,
        "ask": "",
        "foot": order.get("board") or "",
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
    ap.add_argument("--copy-file",
                    help="stage copy from a JSON file (human- or session-written) "
                         "through the identical validate/render/stage chain")
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

    # ---- 2. captions (the ONE model call) ----------------------------------
    brief = WO.brief_for_model(orders)
    if a.copy_file:
        supplied = json.load(open(a.copy_file))
        by_kw = {c["keyword"]: c for c in supplied}
        missing = [o["keyword"] for o in orders if o["keyword"] not in by_kw]
        if missing:
            print(f"\n🔴 BLOCKED — copy file has no entry for: {missing}")
            return 2
        payload = []
        for o in orders:
            c = dict(by_kw[o["keyword"]])
            c.pop("keyword", None)
            c["order_id"] = o["order_id"]
            payload.append(c)
        blob = json.dumps(payload)
        call = lambda prompt, _b=blob: (_b, len(prompt) // 4, len(_b) // 4)
        source_label = f"supplied copy ({a.copy_file})"
    elif a.offline:
        call = offline_model
        source_label = "offline stand-in"
    else:
        print("  [caption] no live model configured — rerun with --offline or --copy-file")
        return 3

    # Media does not exist yet, so validate copy against the URL the render WILL
    # produce; the real bytes are checked again after rendering.
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    planned = {o["order_id"]:
               [f"https://database.blotato.io/staged/{o['platform']}-{o['item_id']}.png"]
               for o in orders}
    try:
        posts, usage = CAP.generate(orders, brief, call, media_by_order=planned)
    except CAP.CaptionError as e:
        print(f"\n🔴 BLOCKED\n{e}")
        return 2
    print(f"  [caption] {usage.report(len(posts))}")

    # ---- 3. render from the APPROVED copy (local, 0 credits) ---------------
    cards = [card_for(o, p) for o, p in zip(orders, posts)]
    pngs = RENDER.render(cards, STAGE_DIR / today / "media")
    print(f"  [render] {len(pngs)} cards from approved copy, local, 0 credits")
    for p_, png in zip(posts, pngs):
        if png.stat().st_size == 0:
            print(f"\n🔴 BLOCKED — {png} rendered zero bytes")
            return 2

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
               "copy_source": source_label,
               "tokens_in": usage.input_tokens, "tokens_out": usage.output_tokens,
               "usd": round(usage.usd, 4), "credits_spent": 0,
               "posts": staged}, open(dest, "w"), indent=1)
    print(f"\n  [stage] wrote {dest}")
    print("  [stage] published nothing — auto_publish is false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
