#!/usr/bin/env python3
"""Build a complete URL -> {title, summary, slug} index for inhousewellness.com.

Source is the Shopify SITEMAP, not the .atom feeds -- the feeds cap at the 30
most recent posts per blog and silently under-collect. Titles come from the
atom feeds where available (cheap) and from the page <title> otherwise.

Deterministic. No model calls.

Usage:  python3 scripts/build_blog_index.py [out.json]
"""
import concurrent.futures as cf
import json, pathlib, re, sys, urllib.error, urllib.request
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
UA = {"User-Agent": "Mozilla/5.0 (inhousewellness-indexer)"}
SITEMAP = "https://inhousewellness.com/sitemap.xml"


def get(url, timeout=40):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return None, b""


def strip_html(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = re.sub(r"&[a-z]+;|&#\d+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sitemap_urls():
    """Every article URL, plus collection and page URLs (destination targets)."""
    _, body = get(SITEMAP)
    subs = re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8", "replace"))
    arts, colls, pages = [], [], []
    for sm in subs:
        if not any(k in sm for k in ("_blogs_", "_collections_", "_pages_")):
            continue
        _, b = get(sm.replace("&amp;", "&"))
        locs = re.findall(r"<loc>([^<]+)</loc>", b.decode("utf-8", "replace"))
        for u in locs:
            u = u.split("?")[0].rstrip("/")
            if "/blogs/" in u and u.count("/") > 4:
                arts.append(u)
            elif "/collections/" in u:
                colls.append(u)
            elif "/pages/" in u:
                pages.append(u)
    dedup = lambda xs: sorted(dict.fromkeys(xs))
    return dedup(arts), dedup(colls), dedup(pages)


def atom_titles():
    """Cheap title/summary source for recent posts across every known blog."""
    out = {}
    for blog in ("saunas", "wellness", "cold-plunge", "news", "fire", "institute"):
        status, body = get(f"https://inhousewellness.com/blogs/{blog}.atom")
        if status != 200 or not body:
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            continue
        for e in root.findall(f"{ATOM}entry"):
            link = e.find(f"{ATOM}link")
            u = (link.get("href") if link is not None else e.findtext(f"{ATOM}id") or "")
            u = u.split("?")[0].rstrip("/")
            if not u:
                continue
            out[u] = {
                "title": strip_html(e.findtext(f"{ATOM}title") or ""),
                "summary": strip_html(e.findtext(f"{ATOM}summary") or
                                      e.findtext(f"{ATOM}content") or "")[:1500],
                "published": e.findtext(f"{ATOM}published") or "",
            }
    return out


_TITLE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_META = re.compile(r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']')
_OGD = re.compile(r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']')


def scrape(url):
    status, body = get(url)
    if status != 200 or not body:
        return url, {"title": "", "summary": "", "http_status": status}
    html = body.decode("utf-8", "replace")
    t = _TITLE.search(html)
    title = strip_html(t.group(1)) if t else ""
    title = re.sub(r"\s*[|–-]\s*inhousewellness.*$", "", title, flags=re.I).strip()
    d = _META.search(html) or _OGD.search(html)
    return url, {"title": title, "summary": strip_html(d.group(1))[:1500] if d else "",
                 "http_status": 200}


def slug_words(url):
    return url.rsplit("/", 1)[-1].replace("-", " ")


def main(dest="data/blog-index.json"):
    arts, colls, pages = sitemap_urls()
    print(f"sitemap: {len(arts)} articles, {len(colls)} collections, {len(pages)} pages",
          file=sys.stderr)

    meta = atom_titles()
    missing = [u for u in arts if u not in meta or not meta[u].get("title")]
    print(f"atom covered {len(arts)-len(missing)}; scraping {len(missing)}", file=sys.stderr)

    with cf.ThreadPoolExecutor(10) as ex:
        for url, m in ex.map(scrape, missing):
            if m.get("title"):
                meta[url] = m

    articles = []
    for u in arts:
        m = meta.get(u, {})
        title = m.get("title") or slug_words(u).title()
        articles.append({
            "url": u,
            "slug": u.rsplit("/", 1)[-1],
            "blog": u.split("/blogs/")[1].split("/")[0],
            "title": title,
            "summary": m.get("summary", ""),
            "published": m.get("published", ""),
            "title_source": "atom" if u in meta and m.get("summary") else
                            ("scrape" if m.get("title") else "slug"),
        })

    pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"source": "inhousewellness.com sitemap",
               "count": len(articles), "articles": articles,
               "collections": colls, "pages": pages},
              open(dest, "w"), indent=1)
    print(f"indexed {len(articles)} articles -> {dest}")
    return articles


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/blog-index.json")
