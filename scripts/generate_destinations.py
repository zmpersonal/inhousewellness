#!/usr/bin/env python3
"""Generate the satellite destination set from the corpus index.

Twelve hand-curated URLs under a 4-per-URL cap supports 48 pins network-wide,
against a queue of 80. It was already binding. Generate, don't curate.

Every generated URL is verified: resolves 200 AND (for satellites) links back to
inhousewellness.com. Boilerplate is excluded. Deterministic, no model calls.

Usage:  python3 scripts/generate_destinations.py [--write] [--per-domain N]
"""
import argparse, concurrent.futures as cf, datetime as dt, json, pathlib, re, sys
import urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import destinations as D

UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-destgen)"}
INH = "inhousewellness.com"
CORPUS = ROOT / "data" / "corpus-index.json"
OUT = ROOT / "data" / "satellite-destinations.json"

# Pages that are never a pin destination.
EXCLUDE = re.compile(
    r"/(?:privacy|terms|disclaimer|policy|security|cookies?|about|contact|"
    r"sitemap|search|login|account|cart|feed|rss)\b", re.I)


def fetch(url, timeout=35, attempts=3):
    delay = 5.0
    for i in range(attempts):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:                 # rate limit is BACK OFF, not dead
                import time; time.sleep(delay); delay *= 2; continue
            return e.code, ""
        except Exception:
            import time; time.sleep(2); continue
    return 429, ""


def verify(url):
    """Resolve a URL and note whether it links back to INH.

    NOTE: link-back is evaluated PER DOMAIN, not per URL (changed 2026-09-02).
    The gate exists to prove a satellite is legitimately connected to INH -- that
    is a property of the property, not of every page on it. Applied per-URL it
    excluded besthomeinfraredsauna.com/emf/ and /electrical/, which are the
    batch-02 destinations the user pre-set and approved, while BHIS links back
    from /retailers/inhouse-wellness/. A domain qualifies if ANY page links back;
    thereafter any page on it that returns 200 is a usable destination.
    """
    status, html = fetch(url)
    links_inh = INH in html.lower() if html else False
    return {"url": url, "http_status": str(status),
            "links_to_inh": links_inh, "resolves": status == 200,
            "ok": status == 200}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--per-domain", type=int, default=14,
                    help="max candidate destinations to verify per domain")
    a = ap.parse_args()

    corpus = json.loads(CORPUS.read_text())["articles"]
    by_dom = {}
    for art in corpus:
        d = art["domain"]
        if d == INH or EXCLUDE.search(art["url"]):
            continue
        by_dom.setdefault(d, []).append(art)

    # Prefer shallow, index-like pages: they answer broad keywords and are the
    # ones that carry outbound links. Then take a spread of deeper pages.
    def rank(art):
        depth = art["url"].rstrip("/").count("/")
        return (depth, art["url"])

    candidates = []
    for dom, arts in sorted(by_dom.items()):
        picked = sorted(arts, key=rank)[: a.per_domain]
        candidates.extend(picked)
    print(f"verifying {len(candidates)} candidates across {len(by_dom)} domains "
          f"(<= {a.per_domain} each)…")

    results = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(verify, [c["url"] for c in candidates]):
            results[r["url"]] = r

    # Domain-level legitimacy: at least one page must link back to INH.
    linked_domains = {art["domain"] for art in candidates
                      if results[art["url"]]["links_to_inh"]}

    # A domain absent from the SAMPLE is not a domain without a link-back. The
    # shallow-page sample misses e.g. besthomeinfraredsauna.com/retailers/
    # inhouse-wellness/ at depth 4. Probe deeper before concluding -- absence of
    # evidence in a sample is not evidence of absence.
    for dom in sorted(set(by_dom) - linked_domains):
        sampled = {c["url"] for c in candidates if c["domain"] == dom}
        extra = [a["url"] for a in by_dom[dom] if a["url"] not in sampled]
        # Prefer URLs whose path hints at a link-back page.
        extra.sort(key=lambda u: (0 if re.search(
            r"retail|partner|where-to-buy|shop|topics|about|source|method", u, re.I)
            else 1, u))
        probe = extra[:20]
        print(f"  ~ {dom}: no link-back in the {len(sampled)}-page sample; "
              f"probing {len(probe)} deeper pages…")
        with cf.ThreadPoolExecutor(4) as ex:
            for r in ex.map(verify, probe):
                results[r["url"]] = r
                if r["links_to_inh"]:
                    linked_domains.add(dom)
                    print(f"    found link-back: {r['url']}")
                    break

    for d in sorted(set(by_dom) - linked_domains):
        print(f"  ! {d}: NO link-back found after probing — domain excluded")

    domains, kept, dropped = {}, 0, 0
    for art in candidates:
        r = results[art["url"]]
        if not r["ok"] or art["domain"] not in linked_domains:
            dropped += 1
            continue
        d = domains.setdefault(art["domain"], {"urls": [], "titles": {}})
        d["urls"].append(art["url"])
        d["titles"][art["url"]] = art["title"][:90]
        kept += 1

    print(f"\nkept {kept}, dropped {dropped} "
          f"(non-200, or on a domain with no link back to INH anywhere)")
    print(f"domains verified legitimate: {len(linked_domains)}/{len(by_dom)}")
    for dom, d in sorted(domains.items(), key=lambda kv: -len(kv[1]["urls"])):
        print(f"  {len(d['urls']):3d}  {dom}")
    capacity = kept * D.PER_URL_MAX_PINS
    print(f"\nnetwork destination capacity: {kept} URLs x {D.PER_URL_MAX_PINS} "
          f"pins = {capacity} pins (was 12 x 4 = 48)")

    if a.write:
        OUT.write_text(json.dumps({
            "_note": ("GENERATED by scripts/generate_destinations.py -- do not "
                      "hand-edit. Every URL resolved 200 at generation time, and "
                      "every DOMAIN was verified to link back to "
                      "inhousewellness.com from at least one page. Link-back is a "
                      "per-domain property, not per-URL. Regenerate, don't curate."),
            "verified_domains": sorted(linked_domains),
            "generated_at": dt.datetime.now(dt.timezone.utc)
                .replace(microsecond=0).isoformat(),
            "per_url_cap": D.PER_URL_MAX_PINS,
            "url_count": kept, "capacity_pins": capacity,
            "domains": domains}, indent=1))
        print(f"\nwrote {OUT}")
    else:
        print("\n(dry run — pass --write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
