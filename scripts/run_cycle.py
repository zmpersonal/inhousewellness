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
ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGE_DIR = pathlib.Path("out/staged")


def first_sentence(text, limit=180):
    t = (text or "").strip().split("\n")[0]
    m = re.split(r"(?<=[.!?])\s+", t)
    out = m[0] if m else t
    return out if len(out) <= limit else out[:limit].rsplit(" ", 1)[0] + "…"


def card_for(order, caption):
    """Card payload from the APPROVED caption's own card object.

    The caption call now returns the card body -- rows, items, columns -- not
    just a headline. Before this the renderer could only draw the keyword and
    the SEO title, which is how three ~70%-empty cards reached the live cycle.
    """
    size = {"pinterest": "pinterest", "instagram": "ig", "facebook": "ig"}[order["platform"]]
    body = dict(caption.get("_body") or {})
    arch = order.get("card_archetype") or "spec"
    kicker = body.pop("kicker", "") or (order.get("archetype") or "")
    headline = body.pop("headline", "") or order["keyword"]
    note = body.pop("note", "")
    out = {"id": f"{order['platform']}-{order['item_id']}",
           "size": size, "type": arch,
           "kicker": kicker, "headline": headline, "note": note,
           "photoBrief": order.get("photo_brief") or "",
           "image": order.get("image") or "",
           "flag": arch == "evidence" or bool(order.get("flag"))}
    out.update(body)
    return out


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
    ap.add_argument("--live", action="store_true",
                    help="use the real model (Sonnet) via src/model.py")
    ap.add_argument("--platforms", default="",
                    help="comma-separated platform allow-list, e.g. 'pinterest'. "
                         "Track A is Pinterest-only; without this the cadence map "
                         "also yields instagram and facebook orders, and Instagram "
                         "is out of scope with no configured account.")
    ap.add_argument("--publish", action="store_true",
                    help="actually publish via the Blotato REST API. Without it "
                         "the cycle stages and posts nothing.")
    ap.add_argument("--copy-file",
                    help="stage copy from a JSON file (human- or session-written) "
                         "through the identical validate/render/stage chain")
    a = ap.parse_args()

    today = dt.date.today().isoformat()
    print(f"cycle {today}   auto_publish={AUTO_PUBLISH}\n")

    # ---- 0. D5 gate --------------------------------------------------------
    # (The legacy network/customScheduled check was removed 2026-09-02: the user
    # confirmed that system is off and the Aug 20-21 blank pins are history.)
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
    if a.platforms:
        allow = {x.strip().lower() for x in a.platforms.split(",") if x.strip()}
        before = len(orders)
        orders = [o for o in orders if o["platform"].lower() in allow]
        print(f"  [select] platform filter {sorted(allow)}: "
              f"{before} -> {len(orders)} order(s)")
        if not orders:
            print("  [select] nothing to do for these platforms")
            return 0
    print(f"  [select] {len(orders)} work orders  (cadence {WO.CADENCE})")
    for o in orders:
        print(f"           {o['platform']:10s} {o['keyword'][:30]:30s} -> {o['link_domain']}")
    # Per-cycle: report the ratios, assert only once the sample can express them.
    v, notes = audit.cycle_notices()
    if v:
        print("  [quota] VIOLATION")
        for x in v:
            print("          !", x)
    for x in notes:
        print(f"  [quota] {x}")

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
    elif a.live:
        from src import model as MODEL
        call = MODEL.make_caller()
        source_label = f"LIVE {call.model}"
        print(f"  [caption] live model: {call.model}")
    elif a.offline:
        call = offline_model
        source_label = "offline stand-in"
    else:
        print("  [caption] no copy source — rerun with --live, --offline or --copy-file")
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
    for e in usage.attempt_errors:
        print(f"  [caption] RETRY CAUSE — {e}")

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
                       "card_body": p.get("_body"),
                       "card_archetype": p.get("_archetype"),
                       "caption": {k: v for k, v in p.items() if not k.startswith("_")},
                       "media_local": str(png),
                       "media_bytes": png.stat().st_size})
    dest = STAGE_DIR / today / "staged.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"date": today, "auto_publish": AUTO_PUBLISH,
               "copy_source": source_label,
               "tokens_in": usage.input_tokens, "tokens_out": usage.output_tokens,
               "calls": usage.calls, "attempt_errors": usage.attempt_errors,
               "usd": round(usage.usd, 4), "credits_spent": 0,
               "posts": staged}, open(dest, "w"), indent=1)
    print(f"\n  [stage] wrote {dest}")

    if not a.publish:
        print("  [stage] published nothing — pass --publish to go live")
        return 0

    # ---- 6. publish (REST; a CI runner has no MCP) -------------------------
    from src import blotato as BL
    from src.limits import BLOTATO_ACCOUNTS

    key = BL.load_key()
    published, halted = [], None
    for o, p, png in zip(orders, posts, pngs):
        acct = BLOTATO_ACCOUNTS.get(p["platform"])
        if not acct:
            halted = f"no Blotato account configured for {p['platform']}"
            break
        # D5: the breadcrumb goes down BEFORE the attempt and is cleared only
        # once the id is captured. Post-then-crash is duplicate-forever without it.
        BC.drop(o["id"], p["platform"])
        try:
            public_url = BL.upload_media(png, key)
            spec = BL.spec_from_post({**p, "mediaUrls": [public_url]},
                                     account_id=acct["accountId"],
                                     page_id=acct.get("pageId"))
            result = BL.publish(spec, key)
            BL.verify_published(result, spec)
        except Exception as e:
            # Never skip, degrade, or partially publish to keep running.
            halted = f"{type(e).__name__}: {e}"
            print(f"  [publish] 🔴 HALT on {o['id']}: {halted}")
            break
        BC.clear()
        published.append({"id": o["id"], "platform": p["platform"],
                          "url": result.get("url"),
                          "submission_id": result.get("submission_id"),
                          "published_at": dt.datetime.now(dt.timezone.utc)
                                            .isoformat(timespec="seconds"),
                          "link": p.get("link")})
        print(f"  [publish] ✅ {p['platform']} {result.get('url')}")

    if published:
        log_path = ROOT / "state" / "published-log.json"
        log = json.loads(log_path.read_text()) if log_path.exists() else []
        if isinstance(log, dict):
            log = log.get("posts", [])
        log.extend(published)
        log_path.parent.mkdir(exist_ok=True)
        log_path.write_text(json.dumps(log, indent=1))
        if hasattr(WO, "mark_published"):
            WO.mark_published(state, [x["id"] for x in published])

    if halted:
        print(f"\n🔴 BLOCKED — halted after {len(published)} of {len(orders)} "
              f"posts. The breadcrumb is DOWN and is not auto-cleared: check the "
              f"platform before the next run.")
        return 2
    print(f"\n  [publish] {len(published)} post(s) published and verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
