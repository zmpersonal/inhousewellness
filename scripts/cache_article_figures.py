#!/usr/bin/env python3
"""Cache measurement-bearing fragments from source articles.

Prose yields adjectives; the figures inside it yield measurements. This pulls
each source article ONCE, extracts every fragment carrying a real value, and
caches it so the caption brief can reach figures with no network and no model
call — which is what lets the cron run this unattended.

Deterministic. Uses a plain fetch, not an LLM summarizer: a summarizer reads
prose, writes prose, and drops the tables (Round 4, learning L19).

Usage:  python3 scripts/cache_article_figures.py [--all] [--write]
"""
import argparse, datetime as dt, json, pathlib, re, sys, urllib.error, urllib.request
import concurrent.futures as cf

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import figures as G
from src.limits import QUANTITATIVE_ARCHETYPES, card_archetype

CACHE = ROOT / "data" / "article-figures.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-figures)"}


def strip_html(html):
    html = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>|</(p|div|li|tr|h[1-6])>", ". ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;|&#160;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&[a-z]+;|&#\d+;", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def fetch(url, attempts=4):
    import time
    delay = 4.0
    for i in range(attempts):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:            # rate limit is BACK OFF, not a dead page
                time.sleep(delay); delay *= 2; continue
            return e.code, ""
        except Exception:
            time.sleep(3); continue
    return 429, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="every source article, not only those whose rows block")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    rows = json.loads((ROOT / "data" / "pinterest-keyword-queue.json").read_text())["items"]
    live = [r for r in rows if r["status"] == "queued" and r.get("source_article")]

    wanted = set()
    for r in live:
        ca = card_archetype(r.get("archetype"))
        if a.all:
            wanted.add(r["source_article"]); continue
        if ca not in QUANTITATIVE_ARCHETYPES:
            continue
        payload, _ = G.figures_for({**r, "card_archetype": ca})
        if payload is None:
            wanted.add(r["source_article"])

    print(f"fetching {len(wanted)} article(s)…")
    out = {}
    if CACHE.exists():
        try:
            out = json.loads(CACHE.read_text()).get("articles", {})
        except json.JSONDecodeError:
            out = {}

    def work(url):
        st, html = fetch(url)
        if st != 200 or not html:
            return url, {"http_status": str(st), "figures": []}
        text = strip_html(html)
        return url, {"http_status": "200", "chars": len(text),
                     "figures": G.from_article(text, limit=14)}

    with cf.ThreadPoolExecutor(3) as ex:
        for url, rec in ex.map(work, sorted(wanted)):
            rec["fetched_at"] = dt.date.today().isoformat()
            out[url] = rec
            n = len(rec["figures"])
            flag = "ok " if n >= 2 else "THIN"
            print(f"  {flag} {n:2d} figure(s)  {url[:82]}")
            for f in rec["figures"][:2]:
                print(f"          {f[:96]}")

    usable = sum(1 for r in out.values() if len(r["figures"]) >= 2)
    print(f"\n{usable}/{len(out)} articles yield >= 2 figures")
    if a.write:
        CACHE.write_text(json.dumps(
            {"generated_at": dt.datetime.now(dt.timezone.utc)
                .replace(microsecond=0).isoformat(),
             "articles": out}, indent=1))
        print(f"wrote {CACHE}")
    else:
        print("(dry run — pass --write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
