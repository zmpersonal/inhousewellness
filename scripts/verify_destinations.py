#!/usr/bin/env python3
"""Verify every destination URL: resolves 200, and (for satellites) links to INH.

Run before any scheduling cycle. Deterministic, no model calls.
Exit code 1 if any satellite fails either gate.
"""
import concurrent.futures as cf, json, pathlib, re, sys, urllib.error, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-link-verify)"}
INH = "inhousewellness.com"


def fetch(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return f"ERR:{type(e).__name__}", ""


def verify(url):
    status, html = fetch(url)
    is_inh = INH in url.lower()
    links_inh = INH in html.lower() if html else False
    ok = (status == 200) and (is_inh or links_inh)
    reason = None
    if status != 200:
        reason = f"HTTP {status}"
    elif not is_inh and not links_inh:
        reason = "does not link back to inhousewellness.com"
    return {"url": url, "http_status": str(status), "links_to_inh": links_inh,
            "ok": ok, "reason": reason}


def main(path="data/satellite-destinations.json"):
    cfg = json.load(open(path))
    urls = [u for d in cfg["domains"].values() for u in d["urls"]]
    results = {}
    with cf.ThreadPoolExecutor(10) as ex:
        for r in ex.map(verify, urls):
            results[r["url"]] = r

    bad = [r for r in results.values() if not r["ok"]]
    for dom, d in sorted(cfg["domains"].items()):
        states = [results[u] for u in d["urls"]]
        good = [s for s in states if s["ok"]]
        mark = "ok  " if good else "FAIL"
        print(f"  {mark} {dom:30s} {len(good)}/{len(states)} usable")
        for s in states:
            if not s["ok"]:
                print(f"         ✗ {s['url']}  ({s['reason']})")
    print(f"\n{len(urls)-len(bad)}/{len(urls)} destination URLs pass")
    pathlib.Path("out").mkdir(exist_ok=True)
    json.dump(list(results.values()), open("out/destination-verify.json", "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:] or [])))
