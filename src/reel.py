"""Local Reel compositor. Story cards rendered by Playwright, composed by ffmpeg.

Zero Blotato credits and zero model tokens. Round 1 measured Blotato at 30-50
credits per Reel and, more importantly, found that the paid AI templates cannot
carry the locked design system while the free deterministic ones can. This path
renders the real brand cards at 1080x1920 and stitches them.

Everything here is deterministic: beat -> card payload -> PNG -> MP4.
"""
from __future__ import annotations

import json, pathlib, re, subprocess, sys

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1080, 1920, 30
CRF = "19"                      # visually lossless for flat brand cards
XFADE = 0.4                     # crossfade seconds between beats


# Beats in the seed are a mix of real content and stage directions written for a
# human editor. Directions must not become on-screen text.
STAGE_DIRECTIONS = re.compile(
    r"^(?:claim|hook|title)\b.*\bframe\b"
    r"|^show the gap$"
    r"|^(?:animation|footage|b-?roll)\b"
    r"|\bcarries this better than\b"
    r"|^hedge explicitly[:]?", re.I)


def beats_to_cards(reel, *, kicker=None):
    """Turn a reels-seed reel into story-card payloads. Pure data, no model call.

    The first content beat becomes the hook card's supporting line rather than a
    slide of its own, so the opening frame is not 70% empty. Each remaining beat
    is one card and is NOT split into heading + detail -- splitting on the first
    comma produced a heading that simply repeated the sentence under it.
    """
    kicker = (kicker or reel.get("format", "")).replace("_", " ").upper()
    beats = [b for b in reel["beats"] if not STAGE_DIRECTIONS.search(b.strip())]

    sub = beats.pop(0) if beats else ""
    cards = [{
        "id": f"{reel['id']}-00", "size": "story", "type": "statement",
        "kicker": kicker,
        "statement": reel["title"],
        "sub": sub,
        "ask": "",
        "foot": "",
    }]
    n = len(beats)
    for i, beat in enumerate(beats, 1):
        cards.append({
            "id": f"{reel['id']}-{i:02d}", "size": "story", "type": "point",
            "n": f"{i} / {n}",
            "point": beat,          # whole beat, one field -- autofit handles length
            "detail": "",
            "foot": "",
        })
    return cards


def durations_for(reel, n_cards):
    """Split the reel's target duration across cards, giving the hook longer."""
    total = float(reel.get("duration_s", 30))
    hook = min(4.0, total * 0.18)
    rest = (total - hook) / max(1, n_cards - 1)
    return [hook] + [rest] * (n_cards - 1)


def compose(pngs, durations, dest, *, xfade=XFADE, ken_burns=False):
    """Stitch stills into an H.264 MP4 with crossfades, optional slow zoom."""
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if len(pngs) != len(durations):
        raise ValueError("pngs and durations must be the same length")

    cmd = [FFMPEG, "-y"]
    for p, d in zip(pngs, durations):
        # Each still is held for its own duration (+ the crossfade tail).
        cmd += ["-loop", "1", "-t", f"{d + xfade:.3f}", "-i", str(p)]

    filt, last = [], None
    for i, d in enumerate(durations):
        lbl = f"v{i}"
        chain = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                 f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1B1613,"
                 f"setsar=1,fps={FPS},format=yuv420p")
        if ken_burns:
            frames = int((d + xfade) * FPS)
            chain += (f",zoompan=z='min(zoom+0.0006,1.06)':d={frames}"
                      f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H},fps={FPS}")
        filt.append(f"[{i}:v]{chain}[{lbl}]")

    if len(durations) == 1:
        last, offset = "v0", durations[0]
    else:
        last = "v0"
        offset = durations[0]
        for i in range(1, len(durations)):
            out = f"x{i}"
            filt.append(f"[{last}][v{i}]xfade=transition=fade:duration={xfade}"
                        f":offset={offset:.3f}[{out}]")
            last = out
            offset += durations[i]

    cmd += ["-filter_complex", ";".join(filt), "-map", f"[{last}]",
            "-c:v", "libx264", "-preset", "medium", "-crf", CRF,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-r", str(FPS), str(dest)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-15:])
        raise SystemExit(f"FAIL: ffmpeg compose failed for {dest}\n{tail}")
    return dest


def probe(path):
    """Read back the real dimensions/duration -- never trust the encoder."""
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    txt = r.stderr
    import re
    dim = re.search(r"(\d{3,5})x(\d{3,5})", txt)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    seconds = None
    if dur:
        seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    return {
        "width": int(dim.group(1)) if dim else None,
        "height": int(dim.group(2)) if dim else None,
        "duration_s": round(seconds, 2) if seconds else None,
        "bytes": pathlib.Path(path).stat().st_size,
        "has_h264": "h264" in txt.lower(),
    }
