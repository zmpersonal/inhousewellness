#!/usr/bin/env python3
"""Fingerprint the rendered cards so a CI render can be compared to a local one.

"The runner renders differently from local" is a stop-and-ask condition, which
needs something objective to compare. Dimensions catch a viewport or DPR
difference; the byte hash catches font substitution, shaping differences and
auto-fit line breaks -- the failures a green build hides.

Text differs between runs (the model writes it), so a hash mismatch is not
automatically a fault. Dimensions mismatching always is.

  python3 scripts/render_manifest.py out/staged/2026-09-02
"""
import hashlib
import json
import pathlib
import struct
import sys


def png_size(path):
    """Width/height from the IHDR chunk -- no image library needed."""
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", head[16:24])


def main():
    target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "out/staged")
    pngs = sorted(target.rglob("*.png"))
    if not pngs:
        print(f"no renders under {target}")
        return 1
    rows = []
    for p in pngs:
        b = p.read_bytes()
        w, h = png_size(p)
        rows.append({"file": p.name, "w": w, "h": h, "bytes": len(b),
                     "sha256": hashlib.sha256(b).hexdigest()[:16]})
        print(f"  {p.name:34s} {w}x{h}  {len(b):>8,}B  sha {rows[-1]['sha256']}")
    out = target / "render-manifest.json"
    out.write_text(json.dumps({"renders": rows}, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
