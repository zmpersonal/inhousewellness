"""Blotato REST client — the publish path a CI runner can actually use.

Every post through Round 12 went out via the Blotato MCP tool, which exists
only inside a Claude Code session. A cron runner has no MCP, so `--publish`
printed a notice and returned and the cron would have run green while posting
nothing. This module closes that gap.

Endpoint and payload shape are Blotato's documented v2 API:
    POST https://backend.blotato.com/v2/posts
    header  blotato-api-key: <key>
    body    {"post": {"accountId", "content": {...}, "target": {...}}}

The REST body and the MCP tool's flat arguments must describe the SAME post.
`mcp_arguments()` renders the MCP form from the same PostSpec that builds the
REST body, and a test asserts they agree field for field -- the two paths
cannot drift.

⚠️ API keys are base64 and MAY END IN '='. Those characters are part of the
key. Never strip them; quote the value in .env.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

from . import media as MEDIA

API_ROOT = "https://backend.blotato.com/v2"
AUTH_HEADER = "blotato-api-key"
# Blotato rate-limits post creation to 30/min per user. Track A publishes 2/day.
POLL_INTERVAL_S = 10
POLL_TIMEOUT_S = 180


class BlotatoError(Exception):
    pass


class AuthError(BlotatoError):
    """401 from Blotato. Its own docs name stripped '=' padding as the usual
    cause; a revoked or mistyped key looks identical from here."""


def load_key(env_path=None):
    """Environment first, .env second.

    On a CI runner there is no .env -- secrets arrive as environment variables.
    Locally .env is the source. Reading only .env made the code unrunnable on a
    runner; reading only the environment would break every local invocation.
    """
    import os
    key = (os.environ.get("BLOTATO_API_KEY") or "").strip()
    if not key:
        from dotenv import dotenv_values
        root = pathlib.Path(__file__).resolve().parents[1]
        env_file = env_path or root / ".env"
        if env_file.exists():
            key = (dotenv_values(env_file).get("BLOTATO_API_KEY") or "").strip()
    if not key:
        raise AuthError("BLOTATO_API_KEY is not set. In CI it comes from "
                        "secrets.BLOTATO_API_KEY; locally from .env at the repo root.")
    return key


def _request(method, path, key, body=None, *, opener=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API_ROOT + path, data=data, method=method,
        headers={AUTH_HEADER: key, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf8", "replace")
        if e.code == 401:
            raise AuthError(
                f"401 Unauthorized from {path}. The endpoint and header are correct, "
                f"so the key itself is being rejected. Blotato's docs name stripped "
                f"'=' padding as the usual cause; regenerate at Settings -> API. "
                f"Body: {detail}") from None
        raise BlotatoError(f"HTTP {e.code} from {method} {path}: {detail}") from None


# ----------------------------------------------------------------- the spec
@dataclasses.dataclass
class PostSpec:
    """One post, platform-neutral at the top and platform-specific in `target`.

    Built from a validated post dict, so every field here has already passed the
    validator. This class does NOT re-validate -- it renders.
    """
    account_id: str
    platform: str
    text: str
    media_urls: list
    # Pinterest
    board_id: str = None
    title: str = None
    alt_text: str = None
    link: str = None
    # Facebook
    page_id: str = None
    first_comment: str = None

    def target(self):
        t = {"targetType": self.platform}
        if self.platform == "pinterest":
            # All five are mandatory: 75 blank pins averaged 3.0 impressions
            # against 106.2 for pins with text, on this account.
            for name, value in (("boardId", self.board_id), ("title", self.title),
                                ("altText", self.alt_text), ("link", self.link)):
                if not value:
                    raise BlotatoError(f"pinterest post is missing {name}")
                t[name] = value
        elif self.platform == "facebook":
            if not self.page_id:
                raise BlotatoError("facebook post is missing pageId")
            t["pageId"] = self.page_id
            # The link goes in the FIRST COMMENT, never the body. Meta throttles
            # posts that send people off-platform.
            if self.first_comment:
                t["firstComment"] = self.first_comment
        else:
            raise BlotatoError(f"unsupported platform {self.platform!r}")
        return t

    def rest_body(self):
        return {"post": {"accountId": str(self.account_id),
                         "content": {"text": self.text,
                                     "mediaUrls": list(self.media_urls),
                                     "platform": self.platform},
                         "target": self.target()}}

    def mcp_arguments(self):
        """The same post as the MCP tool's flat arguments.

        Exists so a test can assert the two paths describe an identical post.
        """
        args = {"accountId": str(self.account_id), "platform": self.platform,
                "text": self.text, "mediaUrls": list(self.media_urls)}
        t = self.target()
        for rest_name, mcp_name in (("boardId", "boardId"), ("title", "title"),
                                    ("altText", "altText"), ("link", "link"),
                                    ("pageId", "pageId"),
                                    ("firstComment", "firstComment")):
            if rest_name in t:
                args[mcp_name] = t[rest_name]
        return args


def spec_from_post(post, *, account_id, page_id=None):
    """Build a PostSpec from a post dict the validator has already passed."""
    return PostSpec(
        account_id=account_id, platform=post["platform"], text=post["text"],
        media_urls=list(post.get("mediaUrls") or []),
        board_id=post.get("boardId"), title=post.get("title"),
        alt_text=post.get("altText"), link=post.get("link"),
        page_id=page_id, first_comment=post.get("firstComment"))


# ----------------------------------------------------------------- media
def upload_media(local_path, key, *, opener=None):
    """presigned -> PUT raw bytes -> verified public URL.

    Reuses src.media for the PUT and the byte-count check rather than owning a
    second copy: duplicated upload logic drifts, and drift here means a post
    published against a URL that does not resolve.
    """
    name = pathlib.Path(local_path).name
    signed = _request("POST", "/media", key, {"filename": name}, opener=opener)
    presigned, public = signed.get("presignedUrl"), signed.get("publicUrl")
    if not presigned or not public:
        raise BlotatoError(f"presign response missing a URL: {signed}")
    return MEDIA.upload(local_path, presigned, public, opener=opener)["public_url"]


# ----------------------------------------------------------------- publish
def publish(spec, key, *, opener=None, sleep=time.sleep):
    """Create the post, then poll to a terminal state. Never returns on 'pending'."""
    resp = _request("POST", "/posts", key, spec.rest_body(), opener=opener)
    sub_id = resp.get("postSubmissionId") or resp.get("id")
    if not sub_id:
        raise BlotatoError(f"create_post returned no submission id: {resp}")

    deadline = time.monotonic() + POLL_TIMEOUT_S
    status, last = None, {}
    while time.monotonic() < deadline:
        last = _request("GET", f"/posts/{urllib.parse.quote(str(sub_id))}",
                        key, opener=opener)
        status = (last.get("status") or "").lower()
        if status in ("published", "scheduled"):
            return {"submission_id": sub_id, "status": status,
                    "url": last.get("publicUrl") or last.get("url"), "raw": last}
        if status == "failed":
            raise BlotatoError(f"publish failed: {last.get('errorMessage') or last}")
        sleep(POLL_INTERVAL_S)
    # An unresolved submission is NOT a success. The breadcrumb stays down and a
    # human checks the platform -- exactly the D5 case.
    raise BlotatoError(
        f"submission {sub_id} still {status!r} after {POLL_TIMEOUT_S}s. Do NOT "
        f"retry: check the platform first, the post may be live.")


# ----------------------------------------------------------------- verify
def verify_published(result, spec, *, opener=None, link_checker=None):
    """Read the post back and prove it is what we meant to publish.

    A 'published' status is Blotato's word for it. This checks the artefact:
    the post URL exists, the text survived intact, media is attached, and the
    destination resolves. Any failure is a HALT and resets the counter -- a
    post that published wrong is a broken post, not a successful run.
    """
    problems = []
    if not result.get("url"):
        problems.append("no public URL returned for the published post")

    raw = result.get("raw") or {}
    # Blotato echoes the submitted content back; where it does, compare it.
    echoed = ((raw.get("content") or {}).get("text")
              if isinstance(raw.get("content"), dict) else raw.get("text"))
    if echoed is not None and echoed.strip() != spec.text.strip():
        problems.append(
            f"published text differs from what was submitted "
            f"({len(echoed)} chars vs {len(spec.text)})")

    echoed_media = ((raw.get("content") or {}).get("mediaUrls")
                    if isinstance(raw.get("content"), dict) else raw.get("mediaUrls"))
    if echoed_media is not None and list(echoed_media) != list(spec.media_urls):
        problems.append("published media differs from what was submitted")
    elif echoed_media is None and not spec.media_urls:
        problems.append("post carries no media")

    # The destination is the whole point of a pin; a dead link wastes the reach.
    if spec.link:
        check = link_checker or _link_ok
        ok, detail = check(spec.link, opener=opener)
        if not ok:
            problems.append(f"destination link did not resolve: {detail}")

    if problems:
        raise BlotatoError("post-publish verification FAILED: " + "; ".join(problems))
    return True


def _link_ok(url, *, opener=None):
    req = urllib.request.Request(
        url, method="GET", headers={"User-Agent": "inhousewellness-verify"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=60) as r:
            return (r.status == 200, f"HTTP {r.status}")
    except urllib.error.HTTPError as e:
        # 429 is backoff, never a dead link. Reading it as failure once blocked
        # every INH row at once and reported a precise, entirely false finding.
        if e.code == 429:
            return (True, "HTTP 429 (rate limited, treated as reachable)")
        return (False, f"HTTP {e.code}")
    except Exception as e:
        return (False, f"{type(e).__name__}")
