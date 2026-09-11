#!/usr/bin/env python3
"""Round 14 — schedule a whole week into Blotato in one session.

WHY THIS SHAPE. Blotato's REST key is dead (401 on every documented endpoint
and header, padding variants included; the plan tier appears not to include
REST). The MCP tool works, but it exists only inside an agent session. So there
is no unattended runner, and there does not need to be one: Blotato schedules
natively, and publishes from its own infrastructure. One session a week hands it
seven days of posts with future timestamps. The Mac can then be off.

THE AGENT IS A DUMB EXECUTOR. Everything with judgement in it -- selection,
dedup, captions, rendering, validation, slot arithmetic, idempotency, state --
happens in this file. The agent only relays precomputed arguments to MCP and
feeds the responses back. That keeps the standing rule intact: the LLM writes
copy and nothing else.

    1  python3 scripts/schedule_week.py plan --live
    2  (agent) blotato_create_presigned_upload_url for each file in the plan
    3  python3 scripts/schedule_week.py upload  --presigned <json>
    4  python3 scripts/schedule_week.py calls
    5  (agent) blotato_create_post for each emitted argument set
    6  python3 scripts/schedule_week.py record  --results <json>
    7  (next week) schedule_week.py reconcile --posts <json>
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src import breadcrumb as BC
from src import captions as CAP
from src import media as MEDIA
from src import workorders as WO
from src.limits import BLOTATO_ACCOUNTS
from src.validator import validate
import render as RENDER
import run_cycle as RC

WEEK_DIR = ROOT / "out" / "weeks"
STATE = ROOT / "state" / "scheduled-weeks.json"

# ── SLOTS ───────────────────────────────────────────────────────────────────
# Pinterest runs 2/day, deliberately EIGHT HOURS APART rather than back to
# back. The legacy account once pushed 13 posts in a single day, during the
# window when 27% of output was broken; clustering is part of what that looked
# like. Both slots land in useful US windows, and evening ET is Pinterest's
# strongest.
#   15:00 UTC = 11:00 ET / 08:00 PT      23:00 UTC = 19:00 ET / 16:00 PT
PIN_SLOTS_UTC = ("15:00", "23:00")
# One Facebook finding a week, Tuesday midday US.
#   16:00 UTC = 12:00 ET / 09:00 PT
FB_DOW, FB_SLOT_UTC = 1, "16:00"          # Monday=0
DAYS = 7
PINS_PER_DAY = 2

ET, PT = ZoneInfo("America/New_York"), ZoneInfo("America/Los_Angeles")


def _utc(day, hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return dt.datetime.combine(day, dt.time(h, m), tzinfo=dt.timezone.utc)


def local_label(when):
    return (f"{when.strftime('%a %d %b %H:%M')}Z  "
            f"({when.astimezone(ET):%H:%M} ET / {when.astimezone(PT):%H:%M} PT)")


def week_slots(week_start):
    """Every slot for the week, as (platform, datetime), chronological."""
    out = []
    for i in range(DAYS):
        day = week_start + dt.timedelta(days=i)
        for hhmm in PIN_SLOTS_UTC[:PINS_PER_DAY]:
            out.append(("pinterest", _utc(day, hhmm)))
        if day.weekday() == FB_DOW:
            out.append(("facebook", _utc(day, FB_SLOT_UTC)))
    out.sort(key=lambda x: x[1])
    return out


def _load_state():
    if not STATE.exists():
        return {"weeks": {}}
    try:
        return json.loads(STATE.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"HALT: {STATE} is corrupt ({e}). Do not delete it.")


def _save_state(s):
    STATE.parent.mkdir(exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    tmp.replace(STATE)                     # atomic; a crash never truncates state


def plan_path(week_start):
    return WEEK_DIR / str(week_start) / "plan.json"


# ── 1. PLAN ─────────────────────────────────────────────────────────────────
def cmd_plan(a):
    week_start = (dt.date.fromisoformat(a.start) if a.start
                  else dt.date.today() + dt.timedelta(days=1))
    slots = week_slots(week_start)
    now = dt.datetime.now(dt.timezone.utc)
    past = [s for _, s in slots if s <= now]
    if past:
        raise SystemExit(
            f"HALT: {len(past)} slot(s) are already in the past "
            f"(earliest {past[0].isoformat()}). Scheduling into the past either "
            f"errors or publishes instantly — pick a later --start.")

    if BC.check():
        raise SystemExit("HALT: a D5 breadcrumb is present. A previous run may "
                         "have created a post without recording it. A human "
                         "clears this after checking Blotato.")

    pin_slots = [s for p, s in slots if p == "pinterest"]
    fb_slots = [s for p, s in slots if p == "facebook"]
    need = len(pin_slots)
    print(f"week {week_start} → {week_start + dt.timedelta(days=DAYS - 1)}   "
          f"{need} pins + {len(fb_slots)} finding\n")

    # ---- select, one day at a time, carrying dedup across the WHOLE week ----
    rows = json.load(open(ROOT / "data" / "pinterest-keyword-queue.json"))["items"]
    state = json.loads(json.dumps(WO.load_state()))     # working copy
    orders, sigs = [], set()
    for i in range(DAYS):
        day = (week_start + dt.timedelta(days=i)).isoformat()
        # The selector suppresses near-duplicate keywords within ONE call, which
        # is right for a day and wrong for a batch: without this the week drew
        # "dry sauna vs wet sauna" AND "wet sauna vs dry sauna". Filtering the
        # pool keeps that suppression week-wide without touching the selector.
        pool = [r for r in rows if WO.keyword_signature(r.get("keyword")) not in sigs]
        got, _ = WO.build_work_orders(pool, state, {"pinterest": PINS_PER_DAY}, today=day)
        for o in got:
            sigs.add(WO.keyword_signature(o["keyword"]))
            state.setdefault("seen", {})[WO.dedup_key("pinterest", o["item_id"])] = day
        orders.extend(got)

    if len(orders) < need:
        raise SystemExit(
            f"HALT: the queue yielded {len(orders)} usable rows for {need} slots. "
            f"Scheduling a short week leaves gaps; refill the queue instead.")
    orders = orders[:need]

    # ---- captions: ONE batched call for all 14 pins ------------------------
    brief = WO.brief_for_model(orders)
    if a.live:
        from src import model as MODEL
        call = MODEL.make_caller()
        print(f"  [caption] live model: {call.model}")
    else:
        call = RC.offline_model
    planned = {o["order_id"]:
               [f"https://database.blotato.io/staged/{o['platform']}-{o['item_id']}.png"]
               for o in orders}
    try:
        posts, usage = CAP.generate(orders, brief, call, media_by_order=planned)
    except CAP.CaptionError as e:
        raise SystemExit(f"🔴 BLOCKED — captions failed after retry:\n{e}")
    print(f"  [caption] {usage.report(len(posts))}")
    for e in usage.attempt_errors:
        print(f"  [caption] RETRY CAUSE — {e}")

    # ---- render + validate -------------------------------------------------
    outdir = WEEK_DIR / str(week_start)
    pngs = RENDER.render([RC.card_for(o, p) for o, p in zip(orders, posts)],
                         outdir / "media")
    for png in pngs:
        if png.stat().st_size == 0:
            raise SystemExit(f"🔴 BLOCKED — {png} rendered zero bytes")
    print(f"  [render] {len(pngs)} cards, local, 0 credits")

    bad = [r for r in (validate(p) for p in posts) if not r.ok]
    if bad:
        # Never schedule a partial week with gaps.
        raise SystemExit("🔴 BLOCKED — validator rejected copy; whole batch halted:\n"
                         + "\n".join(r.summary() for r in bad))
    print(f"  [validate] {len(posts)}/{len(posts)} pass")

    items = []
    for o, p, png, when in zip(orders, posts, pngs, pin_slots):
        items.append({"order_id": o["order_id"], "platform": "pinterest",
                      "item_id": o["item_id"], "keyword": o["keyword"],
                      "scheduled_time": when.isoformat().replace("+00:00", "Z"),
                      "local": local_label(when),
                      "media_local": str(png), "public_url": None,
                      "post": {k: v for k, v in p.items() if not k.startswith("_")}})

    # ---- Track B: reuse run_finding rather than copying its prompt ---------
    if fb_slots and not a.no_finding:
        items.append(_stage_finding(fb_slots[0], a.live))

    plan = {"week_start": str(week_start), "created_at": now.isoformat(),
            "usd": round(usage.usd, 4), "items": items}
    plan_path(week_start).parent.mkdir(parents=True, exist_ok=True)
    plan_path(week_start).write_text(json.dumps(plan, indent=1))
    print(f"\n  [plan] {len(items)} posts → {plan_path(week_start)}")
    print(f"  [plan] batch cost ${plan['usd']:.4f}")
    if plan["usd"] > 1.00:
        print("\n🔴 BLOCKED: batch cost exceeded the $1.00 ceiling.")
        return 2
    return 0


def _stage_finding(when, live):
    """Run run_finding.py and adopt its staged post.

    Calling the existing script rather than re-implementing its prompt: a second
    copy of that logic would drift, and drift in a finding means an unsourced
    claim going out on Facebook.
    """
    print("\n  [finding] staging via run_finding.py")
    cmd = [sys.executable, str(ROOT / "scripts" / "run_finding.py")]
    cmd.append("--live" if live else "--list")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    sys.stdout.write("".join(f"    {l}\n" for l in r.stdout.strip().splitlines()[-6:]))
    if r.returncode != 0:
        raise SystemExit(f"🔴 BLOCKED — run_finding.py exited {r.returncode}; "
                         f"the week is halted rather than scheduled without it.")
    staged = sorted((ROOT / "out" / "findings").glob("*/finding.json"))
    if not staged:
        raise SystemExit("🔴 BLOCKED — run_finding.py produced no finding.json")
    f = json.loads(staged[-1].read_text())
    return {"order_id": f["post"]["id"], "platform": "facebook",
            "item_id": f["post"]["id"], "keyword": f["finding"]["claim"][:60],
            "scheduled_time": when.isoformat().replace("+00:00", "Z"),
            "local": local_label(when),
            "media_local": f["media_local"], "public_url": None,
            "post": {k: v for k, v in f["post"].items() if not k.startswith("_")}}


# ── 2. PRESIGN / UPLOAD ─────────────────────────────────────────────────────
def cmd_presign(a):
    plan = json.loads(plan_path(dt.date.fromisoformat(a.start)).read_text())
    todo = [i for i in plan["items"] if not i["public_url"]]
    print(json.dumps([{"order_id": i["order_id"],
                       "filename": pathlib.Path(i["media_local"]).name}
                      for i in todo], indent=1))
    return 0


def cmd_upload(a):
    p = plan_path(dt.date.fromisoformat(a.start))
    plan = json.loads(p.read_text())
    signed = {s["order_id"]: s for s in json.loads(pathlib.Path(a.presigned).read_text())}
    done = 0
    for item in plan["items"]:
        if item["public_url"]:
            continue
        s = signed.get(item["order_id"])
        if not s:
            raise SystemExit(f"HALT: no presigned URL supplied for {item['order_id']}")
        # PUT + prove the public URL resolves AND the byte count matches, before
        # the URL is ever handed to create_post.
        res = MEDIA.upload(item["media_local"], s["presignedUrl"], s["publicUrl"])
        item["public_url"] = res["public_url"]
        item["media_bytes"] = res["bytes"]
        done += 1
        print(f"  ✅ {item['order_id']:34s} {res['bytes']:>8,}B verified")
    p.write_text(json.dumps(plan, indent=1))
    print(f"\n  [upload] {done} uploaded and verified")
    return 0


# ── 3. CALLS ────────────────────────────────────────────────────────────────
def cmd_calls(a):
    plan = json.loads(plan_path(dt.date.fromisoformat(a.start)).read_text())
    missing = [i["order_id"] for i in plan["items"] if not i["public_url"]]
    if missing:
        raise SystemExit(f"HALT: {len(missing)} item(s) have no verified media URL: "
                         f"{missing[:3]}")
    calls = []
    for i in plan["items"]:
        acct = BLOTATO_ACCOUNTS.get(i["platform"])
        if not acct:
            raise SystemExit(f"HALT: no Blotato account for {i['platform']}")
        p = i["post"]
        args = {"accountId": acct["accountId"], "platform": i["platform"],
                "text": p["text"], "mediaUrls": [i["public_url"]],
                "scheduledTime": i["scheduled_time"]}
        if i["platform"] == "pinterest":
            # All five or the pin underperforms: 75 blank pins averaged 3.0
            # impressions against 106.2 for pins with text, same account.
            for k in ("title", "altText", "link", "boardId"):
                v = p.get(k) or p.get({"boardId": "board_id"}.get(k, k))
                if not v:
                    raise SystemExit(f"HALT: {i['order_id']} is missing {k}")
                args[k] = v
        else:
            args["pageId"] = acct["pageId"]
            if p.get("firstComment"):
                args["firstComment"] = p["firstComment"]   # link NEVER in body
        calls.append({"order_id": i["order_id"], "arguments": args})
    print(json.dumps(calls, indent=1))
    return 0


# ── 4. RECORD ───────────────────────────────────────────────────────────────
def cmd_record(a):
    week = dt.date.fromisoformat(a.start)
    p = plan_path(week)
    plan = json.loads(p.read_text())
    results = {r["order_id"]: r for r in json.loads(pathlib.Path(a.results).read_text())}
    st = _load_state()
    wk = st["weeks"].setdefault(str(week), {"items": {}})
    problems = []
    for item in plan["items"]:
        r = results.get(item["order_id"])
        if not r:
            problems.append(f"{item['order_id']}: no result recorded")
            continue
        sub = r.get("postSubmissionId") or r.get("id")
        got = (r.get("scheduledTime") or "").replace("+00:00", "Z")
        want = item["scheduled_time"]
        if not sub:
            problems.append(f"{item['order_id']}: no submission id returned")
        # Verification AT SCHEDULE TIME: the resolved time must be the requested
        # one. Publication itself is verified next week by reconcile.
        if got and _norm(got) != _norm(want):
            problems.append(f"{item['order_id']}: scheduled {got}, requested {want}")
        wk["items"][item["order_id"]] = {
            "platform": item["platform"], "keyword": item["keyword"],
            "submission_id": sub, "requested": want, "resolved": got or want,
            "link": item["post"].get("link"), "status": "scheduled"}
        item["submission_id"] = sub
    p.write_text(json.dumps(plan, indent=1))
    wk["scheduled_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    wk["usd"] = plan.get("usd")
    _save_state(st)
    BC.clear()
    if problems:
        print("🔴 BLOCKED — scheduling did not match the plan:")
        for x in problems:
            print("   -", x)
        return 2
    print(f"  [record] {len(wk['items'])} posts scheduled and verified against the plan")
    return 0


def _norm(iso):
    return iso.replace("Z", "+00:00")[:16]     # to the minute


# ── 5. RECONCILE ────────────────────────────────────────────────────────────
def cmd_reconcile(a):
    """Did last week's scheduled posts actually publish?

    Replaces the daily broken-post increment: a scheduled post publishes days
    after it is created, so the counter now advances on a reconciled clean week.
    """
    st = _load_state()
    if not st["weeks"]:
        print("no scheduled weeks on record yet — nothing to reconcile")
        return 0
    week = a.start or sorted(st["weeks"])[-1]
    wk = st["weeks"][week]
    rows = json.loads(pathlib.Path(a.posts).read_text())
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    by_sub = {str(r.get("id") or r.get("postSubmissionId")): r for r in rows}

    published, failed, unknown = [], [], []
    for oid, rec in wk["items"].items():
        sub = rec.get("submission_id")
        if not sub:
            # No id was ever captured for this post, which is the D5 case: it
            # may exist on the platform. str(None) would have looked up "None"
            # and quietly reported it as merely unaccounted-for.
            rec["status"] = "no-submission-id"
            unknown.append(f"{oid} (no submission id was ever recorded)")
            continue
        r = by_sub.get(str(sub))
        status = (r or {}).get("status", "").lower()
        if status in ("published", "sent", "complete"):
            rec["status"] = "published"
            rec["post_url"] = (r.get("postUrl") or r.get("publicUrl") or r.get("url"))
            published.append(oid)
        elif status in ("failed", "error"):
            rec["status"] = "failed"
            rec["error"] = r.get("errorMessage") or r.get("error")
            failed.append((oid, rec["error"]))
        else:
            # Absent is NOT the same as published. Never let a missing row
            # advance a clean-week counter.
            rec["status"] = "unknown"
            unknown.append(oid)
    wk["reconciled_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    _save_state(st)

    print(f"week {week}: {len(published)} published, {len(failed)} failed, "
          f"{len(unknown)} unaccounted")
    for oid, err in failed:
        print(f"   ❌ {oid}: {err}")
    for oid in unknown:
        print(f"   ? {oid}")
    if failed:
        print("\n🔴 BLOCKED — a scheduled post failed. The new batch is halted "
              "until this is understood. The counter does not advance.")
        return 2
    if unknown:
        print("\n🔴 BLOCKED — posts unaccounted for. Absence is not proof of "
              "publication; check Blotato by hand before scheduling more.")
        return 2
    print("  clean week — the broken-post counter may advance")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--start"); p.add_argument("--live", action="store_true")
    p.add_argument("--no-finding", action="store_true"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("presign"); p.add_argument("--start", required=True); p.set_defaults(fn=cmd_presign)
    p = sub.add_parser("upload"); p.add_argument("--start", required=True)
    p.add_argument("--presigned", required=True); p.set_defaults(fn=cmd_upload)
    p = sub.add_parser("calls"); p.add_argument("--start", required=True); p.set_defaults(fn=cmd_calls)
    p = sub.add_parser("record"); p.add_argument("--start", required=True)
    p.add_argument("--results", required=True); p.set_defaults(fn=cmd_record)
    p = sub.add_parser("reconcile"); p.add_argument("--posts", required=True)
    p.add_argument("--start"); p.set_defaults(fn=cmd_reconcile)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
