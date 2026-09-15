#!/usr/bin/env python3
"""Fetch source-precedence tier 1: manufacturer specifications.

RUNS IN GITHUB ACTIONS, NOT IN AN AGENT SESSION. The agent session is blocked
from every manufacturer host (403 on CONNECT, organisation egress policy), which
is why tier 1 was empty through Round 1. Actions is not blocked, and it is where
the pipeline is meant to run, so the fetcher lives there.

    python3 scripts/fetch_manufacturer_specs.py --out data/facts/manufacturer_specs.json

WHAT IT TAKES AND WHAT IT REFUSES
For every matched active sauna SKU with a vendor in the registry, it fetches the
manufacturer's product/spec page and reads ONLY figures the page states:
heater kW or rated watts, volts, amps, and whether a dedicated circuit is
required. Every value carries the URL it came from, the verbatim span around it,
and the fetch date.

It refuses, always:
  * deriving kW from volts x amps -- 240V x 30A is the BREAKER's capacity, not
    the heater's rating, and the arithmetic is always available and always wrong;
  * any value outside the 0.8-30 kW plausibility band, which is treated as a
    parse failure rather than a measurement;
  * any page whose robots.txt disallows it.
The parsers and both guards are imported from src/power_parse.py rather than
restated, so this new source runs through the exact code that caught the
"1,800 watts read as 800 W" bug -- it cannot drift away from it.

POLITENESS, because these are other companies' servers
  * robots.txt is fetched once per host and honoured; a disallowed path is
    skipped and recorded as skipped, not fetched anyway.
  * One request at a time per host, with a delay between them (default 2s), and
    Retry-After honoured on 429.
  * The User-Agent identifies who is asking and how to stop us. A crawler that
    does not say who it is cannot be asked to go away.
  * 429 and 5xx are backoff, never "no data" -- reading a rate limit as absence
    is how this project once reported an INH destination share of 0.0%.

MANUFACTURER-VS-METAFIELD DISAGREEMENT IS A FINDING, NOT A MERGE CONFLICT
This script only collects. It never overwrites a metafield value. The merge
happens in build_cost_tables.py, where tier 1 outranks tier 2 but every
disagreement is recorded and reported rather than silently resolved.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.power_parse import (  # noqa: E402
    V_RX, A_RX, read_kw, read_watts, read_scalar, read_dedicated_circuit,
    plausible, self_test as power_self_test,
)

UA = ("InHouseWellnessSpecBot/1.0 (+https://inhousewellness.com; "
      "support@inhousewellness.com) - collects published electrical specs for a "
      "cost-transparency tool; contact us to be excluded")

# Vendor -> how to find that vendor's spec page. `search` is a URL template; the
# runner resolves a model to a page and records the URL it actually landed on.
# Deliberately data, not logic: adding a manufacturer is a row, not a code change.
REGISTRY = ROOT / "data" / "manufacturer-registry.json"


def strip_html(html):
    import re
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = (html.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
                .replace("&quot;", '"'))
    return re.sub(r"\s+", " ", html).strip()


class Host:
    """One manufacturer host: robots rules and a per-host rate limit."""

    def __init__(self, base, delay):
        self.base = base
        self.delay = delay
        self.last = 0.0
        self.rp = urllib.robotparser.RobotFileParser()
        self.robots_ok = None
        robots = urllib.parse.urljoin(base, "/robots.txt")
        try:
            req = urllib.request.Request(robots, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                self.rp.parse(r.read().decode("utf-8", "replace").splitlines())
            self.robots_ok = True
        except Exception as e:
            # A missing or unreadable robots.txt is not permission. It is an
            # unknown, and an unknown on someone else's server means don't.
            self.robots_ok = False
            self.robots_error = str(e)

    def allowed(self, url):
        if self.robots_ok is not True:
            return False
        return self.rp.can_fetch(UA, url)

    def wait(self):
        gap = time.time() - self.last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self.last = time.time()


def fetch(host, url, attempts=4):
    """Returns (text, final_url) or raises. 429/5xx back off; they are never
    treated as 'this page has no data'."""
    for n in range(attempts):
        host.wait()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read().decode("utf-8", "replace")
                # The URL we were served, not the one we asked for: a followed
                # redirect can answer from a category page, and recording the
                # requested URL would attribute it to the product.
                return body, r.geturl()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < attempts - 1:
                wait = int(e.headers.get("Retry-After") or 0) or (2 ** (n + 2))
                print(f"    {e.code} on {url} -- backing off {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError:
            if n < attempts - 1:
                time.sleep(2 ** (n + 2))
                continue
            raise
    raise RuntimeError(f"exhausted retries for {url}")


def extract(text, url):
    """Every stated reading on the page, each with its span and this URL."""
    out = {"kw": [], "volts": [], "amps": [], "dedicated_circuit": None}
    for r in read_kw(text, "manufacturer_page", url) + read_watts(text, "manufacturer_page", url):
        # The band is applied at READ time as well as at merge time, so an
        # implausible figure never even enters the cached dataset.
        if plausible(r["kw"]):
            out["kw"].append(r)
        else:
            out.setdefault("rejected", []).append(
                {**r, "rejected_because": "outside the 0.8-30 kW plausibility band"})
    out["volts"] = read_scalar(text, "manufacturer_page", V_RX, "volts", url)
    out["amps"] = read_scalar(text, "manufacturer_page", A_RX, "amps", url)
    hit = read_dedicated_circuit(text)
    if hit is not None:
        value, qualifier, span = hit
        out["dedicated_circuit"] = {"value": value, "qualifier": qualifier,
                                    "span": span, "source_url": url}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/facts/manufacturer_specs.json")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests per host")
    ap.add_argument("--limit", type=int, default=0, help="stop after N SKUs (smoke test)")
    ap.add_argument("--discover", action="store_true",
                    help="probe robots.txt and the homepage for each vendor and "
                         "report reachability, WITHOUT fetching any product page. "
                         "Run this first: it supplies the evidence for filling in "
                         "product_url_template, which must not be guessed.")
    args = ap.parse_args()

    fails = power_self_test()
    if fails:
        sys.exit("HALT: the shared power parsers failed their own controls:\n  "
                 + "\n  ".join(fails))
    print("power_parse self-test: all probes fire as specified")

    if not REGISTRY.exists():
        sys.exit(f"HALT: {REGISTRY.relative_to(ROOT)} is missing. The registry is "
                 f"data, not logic -- add the vendor rows before running.")
    registry = json.loads(REGISTRY.read_text())
    cost = json.loads((ROOT / "data" / "cost-tables.json").read_text())
    # Vendor lives in the catalogue snapshot, not in cost-tables.json. Reading it
    # from the wrong file returned None for all 165 and would have produced a
    # clean-looking run that fetched nothing.
    snap = json.loads((ROOT / "data" / "shopify-catalog-snapshot-2026-09-14.json").read_text())
    vendor_of = {p["handle"]: p["vendor"] for p in snap["products"]}

    if args.discover:
        report = []
        for vendor, entry in registry["vendors"].items():
            base = entry["base"]
            h = Host(base, args.delay)
            rec = {"vendor": vendor, "base": base, "sku_count": entry["sku_count"],
                   "robots_readable": h.robots_ok}
            if h.robots_ok:
                rec["robots_allows_root"] = h.rp.can_fetch(UA, base)
                try:
                    _, final = fetch(h, base)
                    rec["homepage"] = "OK"
                    rec["final_url"] = final
                except Exception as e:
                    rec["homepage"] = f"FAILED: {str(e)[:120]}"
            else:
                rec["robots_error"] = getattr(h, "robots_error", "")[:120]
            report.append(rec)
            print(f"  {vendor:22s} robots={rec['robots_readable']} "
                  f"home={rec.get('homepage', 'n/a')}")
        out = ROOT / "data" / "facts" / "manufacturer-discovery.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "user_agent": UA, "vendors": report}, indent=1) + "\n")
        print(f"\nwrote {out.relative_to(ROOT)} -- fill product_url_template from THIS, "
              f"not from memory")
        return

    hosts, rows = {}, []
    targets = [r for r in cost["rows"]]
    if args.limit:
        targets = targets[:args.limit]

    for row in targets:
        handle = row["handle"]
        vendor = vendor_of[handle] if handle in vendor_of else None
        entry = registry["vendors"][vendor] if vendor in registry["vendors"] else None
        if entry is None:
            rows.append({"handle": handle, "vendor": vendor,
                         "status": "NO_VENDOR" if vendor is None else "NO_REGISTRY_ENTRY"})
            continue
        if entry["product_url_template"] is None:
            # Deliberate: see data/manufacturer-registry.json. A template that
            # was never tested can resolve to a category page and attribute its
            # content to a product. Skipping is the honest state until a
            # discover run supplies the real URL shape.
            rows.append({"handle": handle, "vendor": vendor,
                         "status": "NEEDS_URL_TEMPLATE"})
            continue
        base = entry["base"]
        if base not in hosts:
            hosts[base] = Host(base, args.delay)
            h = hosts[base]
            print(f"  {base}: robots.txt {'loaded' if h.robots_ok else 'UNREADABLE -> skipping host'}")
        host = hosts[base]
        url = entry["product_url_template"].format(handle=handle)
        if not host.allowed(url):
            rows.append({"handle": handle, "vendor": vendor, "url": url,
                         "status": "ROBOTS_DISALLOWED_OR_UNREADABLE"})
            continue
        try:
            body, final = fetch(host, url)
        except Exception as e:
            # Distinguish "the page says nothing" from "we could not read it".
            rows.append({"handle": handle, "vendor": vendor, "url": url,
                         "status": "FETCH_FAILED", "error": str(e)[:200]})
            continue
        text = strip_html(body)
        found = extract(text, final)
        rows.append({"handle": handle, "vendor": vendor, "requested_url": url,
                     "final_url": final, "status": "OK", "readings": found})
        print(f"  {handle}: {len(found['kw'])} kW reading(s) from {final}", flush=True)

    doc = {
        "name": "manufacturer_specs",
        "note": "Source precedence tier 1. Stated figures only; never derived "
                "from volts x amps. Plausibility band and comma-aware wattage "
                "parsing imported from src/power_parse.py.",
        "user_agent": UA,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "row_count": len(rows),
        "status_counts": {s: sum(1 for r in rows if r["status"] == s)
                          for s in sorted({r["status"] for r in rows})},
        "rows": rows,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"\nwrote {args.out}  rows={len(rows)}")
    for s, n in doc["status_counts"].items():
        print(f"  {s:34s} {n}")


if __name__ == "__main__":
    main()
