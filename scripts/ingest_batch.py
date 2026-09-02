#!/usr/bin/env python3
"""Ingest a new keyword batch into the queue. Deterministic; no model calls.

Contract:
  * `source_article` arrives null and is resolved by the existing remap engine
    against the 11-domain corpus at the unchanged 0.40 threshold. Rows that fail
    are BLOCKED. URLs are never inferred.
  * `link` arrives pre-set to an interactive asset and is PRESERVED -- the row is
    marked link_locked so the router cannot overwrite it with a generic match.
  * Merge dedups against the existing queue on the normalised keyword signature
    (the Round 3 near-duplicate fix), so a reordered restatement of an existing
    keyword does not enter twice.

Usage:
  python3 scripts/ingest_batch.py data/keyword-batch-02-interactive.json [--write]
"""
import argparse, json, pathlib, sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.limits import ALLOWED_LINK_HOSTS
from src.workorders import keyword_signature
from src import destinations as D

QUEUE = "data/pinterest-keyword-queue.json"
REQUIRED = ("keyword", "link")


def load_batch(path):
    raw = json.load(open(path))
    rows = raw["items"] if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise SystemExit(f"FAIL: {path} is not a list or {{items: [...]}}")
    return rows


def normalise(row, i, seq):
    """Shape a batch row into queue form. Fails loudly on a bad destination."""
    for f in REQUIRED:
        if not row.get(f):
            raise SystemExit(f"FAIL: batch row {i} is missing required field {f!r}")

    link = row["link"].strip()
    host = D.domain_of(link)
    if host not in ALLOWED_LINK_HOSTS:
        raise SystemExit(
            f"FAIL: batch row {i} ({row['keyword']!r}) points at {host!r}, which is "
            f"not in the verified destination allow-list. Run "
            f"scripts/verify_destinations.py and add it there first.")

    out = dict(row)
    out.setdefault("id", f"b02-{seq:04d}")
    out["source_article"] = None          # resolved by the remap engine
    out["link"] = link
    out["link_locked"] = True             # router must not overwrite this
    out.setdefault("status", "queued")
    out.setdefault("reuse_class", "evergreen")
    out.setdefault("min_repost_days", 120)
    out.setdefault("archetype", "reality_check")
    out.setdefault("dimensions", "1000x1500")
    out["batch"] = "02-interactive"
    return out


def merge(existing, batch):
    """Dedup on normalised keyword signature; existing rows win."""
    sigs = {keyword_signature(r.get("keyword")): r["id"] for r in existing}
    merged, added, skipped = list(existing), [], []
    for r in batch:
        sig = keyword_signature(r["keyword"])
        if sig in sigs:
            skipped.append((r["keyword"], sigs[sig]))
            continue
        sigs[sig] = r["id"]
        merged.append(r)
        added.append(r)
    return merged, added, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    if not pathlib.Path(a.batch).exists():
        raise SystemExit(f"FAIL: {a.batch} does not exist. Nothing ingested.")

    raw = load_batch(a.batch)
    batch = [normalise(r, i, i + 1) for i, r in enumerate(raw)]
    print(f"batch rows: {len(batch)}")
    print("  clusters:", dict(Counter(r.get("cluster") or r.get("archetype") for r in batch)))
    print("  destinations:", dict(Counter(D.domain_of(r["link"]) for r in batch)))
    print("  volume:", sum(r.get("volume") or 0 for r in batch))

    q = json.load(open(QUEUE))
    existing = q["items"]
    merged, added, skipped = merge(existing, batch)

    print(f"\nmerge: {len(added)} added, {len(skipped)} skipped as near-duplicates")
    for kw, other in skipped[:10]:
        print(f"   ~ {kw!r} duplicates existing row {other}")

    if a.write:
        q["items"] = merged
        q["count"] = len(merged)
        json.dump(q, open(QUEUE, "w"), indent=1)
        print(f"\nwrote {QUEUE} ({len(merged)} rows)")
        print("NEXT: python3 scripts/remap_queue.py --write   "
              "(resolves source_article, preserves link_locked, re-enforces quota)")
    else:
        print("\n(dry run — pass --write to merge)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
