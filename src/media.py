"""Media pipeline: local render -> Blotato presigned upload -> public URL.

The last link between the validator and a real post. The validator already
rejects unreachable media, so this is testable end to end without publishing.

Verified 2026-09-02: PUT returns 200 with {"Key": ...}, and the publicUrl
resolves to image/png with a byte count matching the local file exactly.

The presigned URL is obtained through the Blotato MCP tool by the caller and
passed in, so this module stays a pure function of its inputs and is testable
offline.
"""
from __future__ import annotations

import pathlib
import urllib.error
import urllib.request

CONTENT_TYPE = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".mp4": "video/mp4", ".webm": "video/webm"}


class MediaError(Exception):
    pass


def content_type_for(path):
    ext = pathlib.Path(path).suffix.lower()
    ct = CONTENT_TYPE.get(ext)
    if not ct:
        raise MediaError(f"unsupported media type {ext!r} for {path}")
    return ct


def put(local_path, presigned_url, *, opener=None):
    """Upload raw bytes. Body must be the file itself -- not JSON, not multipart."""
    p = pathlib.Path(local_path)
    if not p.exists():
        raise MediaError(f"local file does not exist: {local_path}")
    size = p.stat().st_size
    if size == 0:
        raise MediaError(f"refusing to upload a zero-byte file: {local_path}")

    req = urllib.request.Request(
        presigned_url, data=p.read_bytes(), method="PUT",
        headers={"Content-Type": content_type_for(p)})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=180) as r:
            if r.status not in (200, 201):
                raise MediaError(f"upload returned HTTP {r.status} for {local_path}")
    except urllib.error.HTTPError as e:
        raise MediaError(f"upload failed HTTP {e.code} for {local_path}: "
                         f"{e.read()[:200]!r}") from None
    return size


def verify(public_url, *, expect_bytes=None, opener=None):
    """Confirm the publicUrl actually resolves BEFORE handing it to create_post.

    A presigned PUT returning 200 does not by itself prove the object is
    publicly readable, and the validator's MEDIA_UNREACHABLE rule would only
    catch it later. Check here, at the point the URL is minted.
    """
    req = urllib.request.Request(public_url, method="GET",
                                 headers={"User-Agent": "inhousewellness-media-verify"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=120) as r:
            if r.status != 200:
                raise MediaError(f"publicUrl returned HTTP {r.status}: {public_url}")
            body = r.read()
    except urllib.error.HTTPError as e:
        raise MediaError(f"publicUrl unreachable HTTP {e.code}: {public_url}") from None
    if not body:
        raise MediaError(f"publicUrl returned an empty body: {public_url}")
    if expect_bytes is not None and len(body) != expect_bytes:
        raise MediaError(
            f"publicUrl byte count {len(body)} != uploaded {expect_bytes}: {public_url}")
    return len(body)


def upload(local_path, presigned_url, public_url, *, opener=None, verify_public=True):
    """Full path: PUT the bytes, then prove the public URL resolves."""
    size = put(local_path, presigned_url, opener=opener)
    if verify_public:
        verify(public_url, expect_bytes=size, opener=opener)
    return {"local": str(local_path), "public_url": public_url, "bytes": size}
