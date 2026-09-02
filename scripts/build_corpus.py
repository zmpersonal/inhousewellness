#!/usr/bin/env python3
"""Build the full-network corpus index: INH + all ten satellite domains.

Round 2's sweep covered inhousewellness.com only and reported a "content gap"
that was really a scope artifact -- the satellites are substantive content
properties (1,800+ pages), not thin link pages.

Sitemap-based, same method that fixed the atom-feed truncation. Deterministic,
no model calls.

Usage:  python3 scripts/build_corpus.py [out.json]
"""
import concurrent.futures as cf
import json, pathlib, re, sys, urllib.error, urllib.request
from xml.etree import ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (compatible; inhousewellness-corpus)"}
ATOM = "{http://www.w3.org/2005/Atom}"
INH = "inhousewellness.com"

DOMAINS = [
    INH,
    "besthomeinfraredsauna.com", "healthresearchdatabase.com", "arcticsoak.com",
    "saunasfactorydirect.com", "outdoorsteamsauna.com", "tubsandsaunas.com",
    "saunaimport.com", "commercialinfraredsauna.com", "homenhealthy.com",
    "infinitesauna.com",
]

# URL patterns that are navigation/boilerplate, never a post destination.
# Deliberately does NOT skip payment/financing/price-match: those are real
# commercial-intent destinations for cost keywords on a retailer.
SKIP = re.compile(
    r"/(?:privacy|terms|disclaimer|policy|security|cookies?|"
    r"data-sharing|opt-out|mobile-terms|"
    r"cart|account|search|login|checkout)\b", re.I)

# A sub-sitemap is identified by path, not suffix: Shopify emits
# "sitemap_collections_1.xml?from=...&to=...", which does not END with .xml and
# was silently skipped -- costing all 88 collection pages.
_IS_SITEMAP = re.compile(r"(?:^|/)[^/?]*sitemap[^/?]*\.xml(?:\?|$)", re.I)


def get(url, timeout=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return None, b""


def strip_html(s):
    s = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"&[a-z]+;|&#\d+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sitemap_pages(domain, max_sub=25):
    """Every page URL for a domain, following sitemap indexes."""
    seen, out = set(), []
    queue = [f"https://{domain}/sitemap.xml"]
    while queue and len(seen) < max_sub:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        st, body = get(sm)
        if st != 200 or not body:
            continue
        locs = re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8", "replace"))
        for l in locs:
            l = l.replace("&amp;", "&")
            if _IS_SITEMAP.search(l):
                queue.append(l)
            else:
                u = l.split("#")[0].rstrip("/")
                if u and not SKIP.search(u):
                    out.append(u)
    return sorted(dict.fromkeys(out))


def atom_meta(domain):
    """Richer titles/summaries for INH blog posts, free from the feeds."""
    if domain != INH:
        return {}
    meta = {}
    for blog in ("saunas", "wellness", "cold-plunge", "news", "fire", "institute"):
        st, body = get(f"https://{domain}/blogs/{blog}.atom")
        if st != 200 or not body:
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            continue
        for e in root.findall(f"{ATOM}entry"):
            link = e.find(f"{ATOM}link")
            u = (link.get("href") if link is not None else e.findtext(f"{ATOM}id") or "")
            u = u.split("?")[0].rstrip("/")
            if u:
                meta[u] = {
                    "title": strip_html(e.findtext(f"{ATOM}title") or ""),
                    "summary": strip_html(e.findtext(f"{ATOM}summary")
                                          or e.findtext(f"{ATOM}content") or "")[:1500],
                }
    return meta


_TITLE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_H1 = re.compile(r"(?is)<h1[^>]*>(.*?)</h1>")
_DESC = re.compile(r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']')
_OGD = re.compile(r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']')


def scrape(url):
    st, body = get(url)
    if st != 200 or not body:
        return url, None
    html = body.decode("utf-8", "replace")
    t = _TITLE.search(html)
    title = strip_html(t.group(1)) if t else ""
    title = re.sub(r"\s*[|–—-]\s*[^|–—-]{0,40}$", "", title).strip() or title
    h1 = _H1.search(html)
    d = _DESC.search(html) or _OGD.search(html)
    summary = strip_html(d.group(1))[:1200] if d else ""
    if h1:
        summary = (strip_html(h1.group(1)) + ". " + summary)[:1200]
    return url, {"title": title, "summary": summary}


def slug_of(url):
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.html?$", "", tail)


def main(dest="data/corpus-index.json"):
    articles, per_domain = [], {}
    for dom in DOMAINS:
        pages = sitemap_pages(dom)
        meta = atom_meta(dom)
        need = [u for u in pages if u not in meta]
        print(f"  {dom:30s} {len(pages):5d} pages ({len(need)} to scrape)", file=sys.stderr)
        with cf.ThreadPoolExecutor(16) as ex:
            for url, m in ex.map(scrape, need):
                if m and m.get("title"):
                    meta[url] = m
        kept = 0
        for u in pages:
            m = meta.get(u)
            if not m or not m.get("title"):
                continue
            articles.append({
                "url": u, "domain": dom, "slug": slug_of(u),
                "blog": (u.split("/blogs/")[1].split("/")[0] if "/blogs/" in u else ""),
                "title": m["title"], "summary": m.get("summary", ""),
                "is_inh": dom == INH,
                "kind": ("collection" if "/collections/" in u else
                         "product" if "/products/" in u else
                         "article" if "/blogs/" in u else "page"),
            })
            kept += 1
        per_domain[dom] = kept
        print(f"  {dom:30s} indexed {kept}", file=sys.stderr)

    articles.sort(key=lambda a: a["url"])
    pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"source": "sitemaps across INH + 10 satellites",
               "count": len(articles), "per_domain": per_domain,
               "articles": articles}, open(dest, "w"), indent=1)
    print(f"\nindexed {len(articles)} pages across {len(DOMAINS)} domains -> {dest}")
    for d, n in sorted(per_domain.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {d}")
    return articles


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/corpus-index.json")
