#!/usr/bin/env python3
"""Build a Reel locally: seed -> story cards -> PNG -> MP4. Zero credits, zero tokens.

Usage:  python3 scripts/build_reel.py reel-3-1 [outdir]
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src import reel as RE
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import render as RENDER


def find(seed, reel_id):
    for s in seed["sets"]:
        for r in s["reels"]:
            if r["id"] == reel_id:
                return s, r
    raise SystemExit(f"FAIL: no reel {reel_id!r} in the seed")


def main(reel_id, outdir="out/reels"):
    seed = json.load(open("data/reels-seed.json"))
    st, r = find(seed, reel_id)
    if r.get("requires_footage"):
        raise SystemExit(f"FAIL: {reel_id} requires real footage; not buildable from cards")

    outdir = pathlib.Path(outdir) / reel_id
    cards = RE.beats_to_cards(r, kicker=st["name"])
    print(f"{reel_id}: {len(cards)} cards, target {r['duration_s']}s")

    pngs = RENDER.render(cards, outdir / "frames")
    for p in pngs:
        print(f"  card {p.name}  {p.stat().st_size:,}b")

    durs = RE.durations_for(r, len(cards))
    dest = outdir / f"{reel_id}.mp4"
    RE.compose([str(p) for p in pngs], durs, dest)
    info = RE.probe(dest)
    print(f"\n  MP4 {dest}")
    print(f"  {info['width']}x{info['height']}  {info['duration_s']}s  "
          f"{info['bytes']:,} bytes  h264={info['has_h264']}")
    if (info["width"], info["height"]) != (RE.W, RE.H):
        raise SystemExit(f"FAIL: expected {RE.W}x{RE.H}, got {info['width']}x{info['height']}")
    return dest


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "reel-3-1",
         sys.argv[2] if len(sys.argv) > 2 else "out/reels")
