#!/usr/bin/env python3
"""Remap the Pinterest keyword queue onto live URLs. Deterministic; no model calls.

For every row:
  * match to a real blog article (token score + subject-compatibility gate)
  * assign a destination, filling the INH >= 70% quota first, satellites round-robin
  * assign a Pinterest board from the live board list
  * stamp verified_at + http_status on both source_article and link
  * rows that cannot be matched honestly become status="blocked" with a reason

Never invents a URL. A blocked row is a good outcome.

Usage:  python3 scripts/remap_queue.py [--write]
"""
import concurrent.futures as cf
import datetime as dt
import json, pathlib, sys, urllib.error, urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src import destinations as D
from src import remap as R

UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-remap)"}
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

QUEUE = "data/pinterest-keyword-queue.json"
INDEX = "data/blog-index.json"
SATS = "data/satellite-destinations.json"
OUT = "data/pinterest-keyword-queue.json"

# Live Pinterest boards (blotato_list_pinterest_boards, account 9630, 2026-09-01).
# The six topical boards the queue assumes do not exist yet; these four carry no
# topical signal, so every row is mapped to the closest and flagged.
BOARDS = {
    "Social": "902690387751301590",
    "The Sauna Shop": "902690387751719051",
    "Wellness At Home": "902690387751256709",
    "Products": "902690387751254421",
}
BOARD_FOR_CLUSTER = {
    "commercial_intent": "The Sauna Shop",
    "cost": "The Sauna Shop",
    "brands": "Products",
    "infrared_compare": "The Sauna Shop",
    "commercial_install": "Products",
    "outdoor_steam": "The Sauna Shop",
    "hot_tub": "Wellness At Home",
    "cold_plunge": "Wellness At Home",
    "evidence": "Wellness At Home",
    "home_wellness": "Wellness At Home",
    "home_wellness_alt": "Wellness At Home",
}


def head(url):
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code == 405 and method == "HEAD":
                continue
            return e.code
        except Exception as e:
            return f"ERR:{type(e).__name__}"
    return "ERR"


def main(write=False):
    queue = json.load(open(QUEUE))
    rows = queue if isinstance(queue, list) else (queue.get("items") or list(queue.values())[0])
    articles = json.load(open(INDEX))["articles"]
    sats = json.load(open(SATS))["domains"]
    idf = R.build_idf(articles)

    # ---- 1. match each row to a real article -------------------------------
    for row in rows:
        s, art, verdict, reason = R.match_row(row["keyword"], articles, idf)
        row["match_score"] = round(s, 4)
        row["cluster"] = D.classify(row["keyword"])
        if verdict == "blocked":
            row["status"] = "blocked"
            row["blocked_reason"] = reason or "no compatible article"
            row["source_article"] = None
        else:
            row["status"] = "queued"
            row["source_article"] = art["url"]
            row["source_title"] = art["title"]
            row["match_confidence"] = verdict
            row.pop("blocked_reason", None)

    live = [r for r in rows if r["status"] == "queued"]

    # ---- 2. destinations, INH quota first -----------------------------------
    inh_pages = [a["url"] for a in articles]
    domains = D.plan_destinations(live)
    sat_cursor = defaultdict(int)
    for row, dom in zip(live, domains):
        if dom == D.INH:
            # Destination is the article itself: always live, always on-topic.
            row["link"] = row["source_article"]
        else:
            urls = sats.get(dom, {}).get("urls") or []
            if not urls:
                row["status"] = "blocked"
                row["blocked_reason"] = f"satellite {dom} has no verified destination URL"
                continue
            row["link"] = urls[sat_cursor[dom] % len(urls)]
            sat_cursor[dom] += 1
        row["link_domain"] = D.domain_of(row["link"])

    live = [r for r in rows if r["status"] == "queued"]

    # ---- 3. boards ----------------------------------------------------------
    for row in live:
        name = BOARD_FOR_CLUSTER.get(row["cluster"], "The Sauna Shop")
        row["board"] = name
        row["board_id"] = BOARDS[name]
        row["board_is_placeholder"] = True   # the 6 topical boards do not exist yet

    # ---- 4. verify every URL actually resolves ------------------------------
    urls = sorted({u for r in live for u in (r.get("source_article"), r.get("link")) if u})
    status = {}
    with cf.ThreadPoolExecutor(12) as ex:
        for u, st in zip(urls, ex.map(head, urls)):
            status[u] = st
    for row in live:
        row["http_status"] = {"source_article": str(status.get(row["source_article"])),
                              "link": str(status.get(row["link"]))}
        row["verified_at"] = NOW
        bad = [k for k, v in row["http_status"].items() if v != "200"]
        if bad:
            row["status"] = "blocked"
            row["blocked_reason"] = f"URL did not return 200: {', '.join(bad)}"

    live = [r for r in rows if r["status"] == "queued"]
    blocked = [r for r in rows if r["status"] == "blocked"]

    # ---- 5. report ----------------------------------------------------------
    print(f"queued  {len(live)}")
    print(f"blocked {len(blocked)}\n")

    print("blocked reasons:")
    for reason, n in Counter(
            (r.get("blocked_reason") or "?").split("; ")[0][:78] for r in blocked).most_common():
        print(f"  {n:4d}  {reason}")

    audit = D.audit([r["link"] for r in live])
    print("\n" + audit.summary())
    v, notices = audit.violations(), audit.notices()
    print("QUOTA:", "ok" if not v else "VIOLATION")
    for x in v:
        print("   !", x)
    for x in notices:
        print("   ~", x)

    print("\nboards:", dict(Counter(r["board"] for r in live)))
    print("confidence:", dict(Counter(r["match_confidence"] for r in live)))
    non200 = [u for u, st in status.items() if str(st) != "200"]
    print(f"\nURL sweep over queued rows: {len(status)} unique, {len(non200)} non-200")
    for u in non200:
        print("   ", status[u], u)

    if write:
        out = {"generated_at": NOW, "count": len(rows),
               "queued": len(live), "blocked": len(blocked), "items": rows}
        json.dump(out, open(OUT, "w"), indent=1)
        print(f"\nwrote {OUT}")
    else:
        print("\n(dry run — pass --write to save)")
    return 0 if not audit.violations() else 1


if __name__ == "__main__":
    sys.exit(main(write="--write" in sys.argv))
