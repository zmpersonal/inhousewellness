#!/usr/bin/env python3
"""Electrical tool LAUNCH step (D11): two 301s. NOT run in Round 1; dry run unless --write.

    .venv/bin/python scripts/electrical_redirects_launch.py           # dry run: reads, prints, writes nothing
    .venv/bin/python scripts/electrical_redirects_launch.py --write   # at launch only, after approval

    /tools/panel-check -> /pages/sauna-electrical-requirements   (legacy social-queue path)
    /tools/will-it-fit -> /pages/sauna-database                  (a space question; the hub, not this tool)

Order and proof follow scripts/deploy_redirects.py (Round 13): a redirect only fires on a 404, so it
is safe to create first; each is read back BY ID (never by search, CLAUDE.md "A search index is not a
read-back"), then proved from outside by following the chain from the primary domain.
Refuses if a source path does not 404 today, or a target does not answer 200 without a preview.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
STORE = "https://inhousewellness.com"
REDIRECTS = [("/tools/panel-check", "/pages/sauna-electrical-requirements"),
             ("/tools/will-it-fit", "/pages/sauna-database")]


def status(url: str) -> int:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, headers={"User-Agent": "INH-launch-check"}), timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    problems = []
    for src, dst in REDIRECTS:
        s, d = status(STORE + src), status(STORE + dst)
        print(f"  {src} answers {s} (must be 404)   ->   {dst} answers {d} (must be 200)")
        if s != 404:
            problems.append(f"{src} answers {s}, not 404: a redirect would never fire")
        if d != 200:
            problems.append(f"{dst} answers {d}, not 200: the target is not live")
    if problems:
        for p in problems:
            print(f"NOT READY: {p}")
        if a.write:
            return 1
    if not a.write:
        print("DRY RUN: nothing created." + (" (Expected before launch: the tool page is hidden.)" if problems else ""))
        return 0
    from verify_theme_asset_path import load_env, gql
    shop, token = load_env()
    for src, dst in REDIRECTS:
        r = gql(shop, token, "mutation($r: UrlRedirectInput!) { urlRedirectCreate(urlRedirect: $r) { urlRedirect { id path target } "
                "userErrors { field message } } }", {"r": {"path": src, "target": dst}})["urlRedirectCreate"]
        if r["userErrors"]:
            print(f"HALT: {src}: {r['userErrors']}")
            return 1
        back = gql(shop, token, "query($id: ID!) { urlRedirect(id: $id) { id path target } }", {"id": r["urlRedirect"]["id"]})["urlRedirect"]
        ok = back and back["path"] == src and back["target"] == dst
        print(f"  created {back['id'] if back else '?'} {src} -> {dst}: read back by id {'OK' if ok else 'MISMATCH'}")
        # Recorded so `electrical_launch.py rollback` deletes exactly these, by id, never by search.
        import electrical_launch as el
        el.lsave(redirects={**el.lstate().get("redirects", {}), src: r["urlRedirect"]["id"]})
        if not ok:
            return 1
    import time
    for src, dst in REDIRECTS:
        # A redirect created seconds ago can still answer 404 at the edge (seen at launch, 2026-10-07:
        # will-it-fit 404 for a few seconds, then 301). Retry briefly; a persistent 404 still halts.
        for attempt in range(12):
            try:
                with urllib.request.urlopen(urllib.request.Request(STORE + src, headers={"User-Agent": "INH-launch-check"}), timeout=30) as r:
                    final = r.geturl()
                break
            except urllib.error.HTTPError as e:
                if e.code != 404 or attempt == 11:
                    print(f"HALT: {src} answers {e.code} after creation")
                    return 1
                time.sleep(5)
        print(f"  {src} ends at {final}")
        if not final.split("?")[0].endswith(dst):
            print("HALT: redirect does not end at its target")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
