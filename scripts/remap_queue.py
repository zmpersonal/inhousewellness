#!/usr/bin/env python3
"""Remap the keyword queue onto the FULL network corpus. No model calls.

Round 3: the corpus is INH + all ten satellites (1,908 pages). Round 2's sweep
covered inhousewellness.com alone and reported a "content gap" that was largely a
scope artifact.

Scorer, threshold (0.40), subject gate and IDF handling are UNCHANGED from
Round 2 -- they were hard-won and are correct.

For each row:
  * source_article = best match anywhere in the corpus (the content basis)
  * link           = destination, routed separately: interactive asset if one
                     genuinely fits, else the best match, honouring the
                     INH >= 60% floor and the 15% per-satellite cap
  * rows that cannot be matched or destined honestly become status="blocked"

Never invents a URL. Never degrades a match to fill a quota.

Usage:  python3 scripts/remap_queue.py [--write]
"""
import concurrent.futures as cf
import datetime as dt
import json, pathlib, sys, time, urllib.error, urllib.request
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src import destinations as D
from src import remap as R

UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-remap)"}
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

QUEUE = "data/pinterest-keyword-queue.json"
CORPUS = "data/corpus-index.json"
OUT = QUEUE

BOARDS = {
    "Social": "902690387751301590",
    "The Sauna Shop": "902690387751719051",
    "Wellness At Home": "902690387751256709",
    "Products": "902690387751254421",
}
BOARD_FOR_CLUSTER = {
    "commercial_intent": "The Sauna Shop", "cost": "The Sauna Shop",
    "brands": "Products", "infrared_compare": "The Sauna Shop",
    "commercial_install": "Products", "outdoor_steam": "The Sauna Shop",
    "hot_tub": "Wellness At Home", "cold_plunge": "Wellness At Home",
    "evidence": "Wellness At Home", "home_wellness": "Wellness At Home",
    "home_wellness_alt": "Wellness At Home",
}


def head(url, attempts=6):
    """Resolve a URL, treating 429 as BACK OFF rather than as a dead link.

    A rate-limit is not a 404. Reading 429 as failure once blocked every INH row
    at once and drove the INH destination share to 0%, which would have been a
    completely false finding about the corpus.
    """
    delay = 8.0
    for attempt in range(attempts):
        for method in ("HEAD", "GET"):
            try:
                with urllib.request.urlopen(
                        urllib.request.Request(url, method=method, headers=UA),
                        timeout=30) as r:
                    return r.status
            except urllib.error.HTTPError as e:
                if e.code == 405 and method == "HEAD":
                    continue
                if e.code == 429:
                    break                      # back off, then retry the URL
                return e.code
            except Exception as e:
                return f"ERR:{type(e).__name__}"
        if attempt < attempts - 1:
            time.sleep(delay)
            delay *= 2
    return 429


def main(write=False):
    queue = json.load(open(QUEUE))
    rows = queue["items"] if isinstance(queue, dict) else queue
    corpus = json.load(open(CORPUS))["articles"]
    inh_pages = [a for a in corpus if a["is_inh"]]
    idf = R.build_idf(corpus)

    # ---- 1. match ----------------------------------------------------------
    for row in rows:
        kw = row["keyword"]
        s, art, verdict, reason = R.match_row(kw, corpus, idf)
        si, arti, vi, _ = R.match_row(kw, inh_pages, idf)
        row["cluster"] = D.classify(kw)
        row["match_score"] = round(s, 4)
        for k in ("blocked_reason", "source_title", "match_confidence",
                  "link_domain", "destination_reason", "interactive_asset"):
            row.pop(k, None)
        if verdict == "blocked":
            row["status"] = "blocked"
            row["blocked_reason"] = reason or "no compatible page in the network corpus"
            row["source_article"] = None
            row["_best"] = None
        else:
            row["status"] = "queued"
            row["source_article"] = art["url"]
            row["source_title"] = art["title"]
            row["source_domain"] = art["domain"]
            row["match_confidence"] = verdict
            row["_best"] = {"best_url": art["url"], "best_score": s,
                            "best_domain": art["domain"],
                            "inh_url": arti["url"] if vi != "blocked" else None,
                            "inh_score": round(si, 4) if vi != "blocked" else None,
                            "keyword": kw, "archetype": row.get("archetype")}

    live = [r for r in rows if r["status"] == "queued"]

    # ---- 2. destinations ---------------------------------------------------
    assigned, blocked_idx, per_domain = D.route([r["_best"] for r in live])
    for i, row in enumerate(live):
        if i in blocked_idx:
            row["status"] = "blocked"
            row["blocked_reason"] = blocked_idx[i]
            continue
        a = assigned[i]
        row["link"] = a["link"]
        row["link_domain"] = a["domain"]
        row["destination_reason"] = a["reason"]
        if a["reason"].startswith("interactive:"):
            row["interactive_asset"] = a["reason"].split("interactive: ", 1)[1]

    live = [r for r in rows if r["status"] == "queued"]

    # ---- 3. boards ---------------------------------------------------------
    for row in live:
        name = BOARD_FOR_CLUSTER.get(row["cluster"], "The Sauna Shop")
        row["board"] = name
        row["board_id"] = BOARDS[name]
        row["board_is_placeholder"] = True

    # ---- 4. verify ---------------------------------------------------------
    urls = sorted({u for r in live for u in (r.get("source_article"), r.get("link")) if u})
    status = {}
    with cf.ThreadPoolExecutor(2) as ex:
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

    # ---- 4b. re-enforce the per-satellite cap AFTER verification ------------
    # The cap was computed against the pre-verification row count. When
    # verification then blocks rows, a domain that was inside the cap can end up
    # outside it (6 of 40 is 15.0%; the same 6 of 34 is 17.6%). Enforce again on
    # the surviving set, dropping the lowest-volume offenders -- never
    # redirecting them somewhere weaker.
    # Iterate to a fixpoint: dropping a row shrinks the denominator, which lowers
    # the cap, which can put a domain back over. Converges because each pass
    # strictly reduces the set.
    for _ in range(20):
        live = [r for r in rows if r["status"] == "queued"]
        cap = max(1, int(len(live) * D.SATELLITE_MAX_SHARE))
        counts = Counter(r["link_domain"] for r in live)
        over = {d: n for d, n in counts.items() if d != D.INH and n > cap}
        if not over:
            break
        for dom, n in over.items():
            offenders = sorted([r for r in live if r["link_domain"] == dom],
                               key=lambda r: (r.get("volume") or 0))
            for r in offenders[:n - cap]:
                r["status"] = "blocked"
                r["blocked_reason"] = (
                    f"{dom} exceeded its {D.SATELLITE_MAX_SHARE:.0%} share cap "
                    f"({n}/{len(live)}); dropped rather than redirected to a "
                    f"weaker match")

    live = [r for r in rows if r["status"] == "queued"]
    blocked = [r for r in rows if r["status"] == "blocked"]
    for r in rows:
        r.pop("_best", None)

    # ---- 5. report ---------------------------------------------------------
    print(f"queued  {len(live)}   (Round 2, INH-only corpus: 24)")
    print(f"blocked {len(blocked)}\n")

    audit = D.audit([r["link"] for r in live])
    print(audit.summary())
    v, notices = audit.violations(), audit.notices()
    print("QUOTA:", "ok" if not v else "VIOLATION")
    for x in v:
        print("   !", x)
    for x in notices:
        print("   ~", x)

    ia = Counter(r["interactive_asset"] for r in live if r.get("interactive_asset"))
    print("\ninteractive assets routed:", dict(ia) or "none")
    print("source domains:", dict(Counter(r["source_domain"] for r in live)))
    print("confidence:", dict(Counter(r["match_confidence"] for r in live)))
    print("boards:", dict(Counter(r["board"] for r in live)))

    non200 = [u for u, st in status.items() if str(st) != "200"]
    print(f"\nURL sweep: {len(status)} unique among queued, {len(non200)} non-200")
    for u in non200:
        print("   ", status[u], u)

    if write:
        json.dump({"generated_at": NOW, "count": len(rows), "queued": len(live),
                   "blocked": len(blocked), "items": rows}, open(OUT, "w"), indent=1)
        print(f"\nwrote {OUT}")
    else:
        print("\n(dry run — pass --write to save)")
    return 0 if not v else 1


if __name__ == "__main__":
    sys.exit(main(write="--write" in sys.argv))
