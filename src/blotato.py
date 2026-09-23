"""Blotato REST client — the publish path a CI runner can actually use.

Every post through Round 12 went out via the Blotato MCP tool, which exists
only inside a Claude Code session. A cron runner has no MCP, so `--publish`
printed a notice and returned and the cron would have run green while posting
nothing. This module closes that gap.

PROVEN 2026-09-23 by live request, not inferred from docs:
    POST https://backend.blotato.com/v2/posts
    header  blotato-api-key: <raw key>   (no Bearer, no workspace, no version)
    body    {"post": {"accountId", "target": {...}, "content": {...}},
             "scheduledTime": "<ISO 8601>"}

⚠️ `GET /v2/posts/{id}` IS NOT A STATUS ENDPOINT. It returns 200 with
`{"postSubmissionId": <whatever you passed>, "status": "in-progress"}` for ANY
id -- "999999999", "not-an-id", a zero UUID. It echoes the argument back and
fabricates a status. Polling it can never observe "published", so this module
does not call it. Publication is proved from `GET /v2/posts`, the list, whose
rows carry a real `state: {type, postUrl}`.

⚠️ There is NO delete route. DELETE /v2/posts/{id} is 404 "Route not found";
DELETE /v2/schedules/{id} exists but schedules are recurring SLOTS, not
scheduled posts, and the list is empty while posts sit queued. A scheduled post
cannot be recalled through the API -- which is why a send is guarded rather
than tested-then-cleaned-up.

Endpoint and payload shape (the documented v2 API, matching the proven call):
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


# Sentinel: "the response did not contain this at all", which is different from
# "the response said this was empty". Conflating them is how a missing value
# becomes a confident false pass.
_UNVERIFIABLE = object()


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

    def rest_body(self, scheduled_time=None):
        """The proven body. `scheduledTime` sits BESIDE `post`, not inside it.

        The schema does not validate scheduledTime at all -- a number or
        "not-a-date" is accepted without complaint -- so acceptance proves
        nothing here and the value is checked against the response instead.
        """
        body = {"post": {"accountId": str(self.account_id),
                         "content": {"text": self.text,
                                     "mediaUrls": list(self.media_urls),
                                     "platform": self.platform},
                         "target": self.target()}}
        if scheduled_time:
            body["scheduledTime"] = scheduled_time
        return body

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


def assert_target_pinned(spec):
    """BOTH locks, before every send. Raises; never defaults to allowed.

    accountId alone does not say where a post lands: account 49743 is a
    Facebook user holding twelve pages, and Texas Home Intelligence publishes
    through the same account and the same key. The page or board is what makes
    a target ours, so it is pinned in config and compared here.
    """
    from .limits import BLOTATO_PINNED_TARGETS

    pinned = BLOTATO_PINNED_TARGETS.get(spec.platform)
    if pinned is None:
        raise BlotatoError(
            f"{spec.platform!r} has no pinned target. Publishing to a platform "
            f"nobody pinned is exactly the mistake this guard exists to stop; "
            f"add it to BLOTATO_PINNED_TARGETS deliberately.")

    if str(spec.account_id) != pinned["accountId"]:
        raise BlotatoError(
            f"LOCK 1 FAILED: {spec.platform} accountId {spec.account_id!r} is "
            f"not the pinned {pinned['accountId']!r}.")

    target = spec.target()
    if spec.platform == "facebook":
        got = target.get("pageId")
        if got != pinned["pageId"]:
            raise BlotatoError(
                f"LOCK 2 FAILED: pageId {got!r} is not the pinned "
                f"{pinned['pageId']!r} (InHouse Wellness). Account 49743 holds "
                f"twelve pages including Texas Home Intelligence "
                f"(1335273942995805) -- refusing to send.")
    elif spec.platform == "pinterest":
        got = target.get("boardId")
        if got not in pinned["boardIds"]:
            raise BlotatoError(
                f"LOCK 2 FAILED: boardId {got!r} is not one of the four boards "
                f"pinned for this account: {sorted(pinned['boardIds'])}.")
    else:
        raise BlotatoError(f"no lock-2 rule for {spec.platform!r}")
    return True


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
def schedule(spec, key, scheduled_time, *, opener=None):
    """Create ONE post, scheduled. Returns the submission id and resolved time.

    Both locks are asserted BEFORE the request leaves. There is no delete route,
    so a wrong target cannot be taken back -- the guard is the only safeguard
    and it runs first.

    This does NOT poll for status. `GET /v2/posts/{id}` fabricates
    "in-progress" for any id, so polling it would either hang until timeout or,
    worse, be mistaken for evidence. Publication is proved later by
    `reconcile`, against the post LIST.
    """
    assert_target_pinned(spec)
    resp = _request("POST", "/posts", key, spec.rest_body(scheduled_time),
                    opener=opener)
    sub_id = resp.get("postSubmissionId") or resp.get("id")
    if not sub_id:
        raise BlotatoError(f"create_post returned no submission id: {resp}")
    resolved = resp.get("scheduledTime")
    return {"submission_id": str(sub_id), "requested": scheduled_time,
            "resolved": resolved, "raw": resp}


def list_posts(key, *, opener=None):
    """Every post Blotato holds for this user, newest first.

    The ONLY honest source of publication status. Rows carry
    `state: {type, postUrl}`; `id` here is Blotato's own post id and is NOT the
    postSubmissionId returned at creation, so callers match on
    platform + postTime + text rather than on the submission id.

    ⚠️ HARD CAP OF 10 ROWS, NO PAGINATION. Verified 2026-09-23: `limit=50`,
    `page=2` and `offset=10` all return the same newest ten; `cursor` 422s.
    A 15-post week therefore CANNOT be reconciled in one weekly pass -- ten
    posts is about 4.7 days at 2 pins/day plus a weekly finding. Reconcile must
    run DAILY so no post ages out of the window unseen. A weekly reconcile
    would silently skip the first half of every week, and "not seen" would be
    indistinguishable from "never published".
    """
    d = _request("GET", "/posts", key, opener=opener)
    return d.get("items", d if isinstance(d, list) else [])


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

    # Read the submitted content back out of the response. The shape is either
    # {"content": {...}} or flat, so branch EXPLICITLY on which one arrived --
    # and treat "neither" as unverified rather than as agreement. A silent None
    # here would skip the text check entirely and report success for a post
    # nobody ever compared.
    content = raw.get("content")
    if isinstance(content, dict):
        echoed_text, echoed_media = content.get("text"), content.get("mediaUrls")
    elif "text" in raw or "mediaUrls" in raw:
        echoed_text, echoed_media = raw.get("text"), raw.get("mediaUrls")
    else:
        echoed_text = echoed_media = _UNVERIFIABLE

    if echoed_text is _UNVERIFIABLE:
        problems.append(
            "the publish response echoed no content, so the published text and "
            "media could not be verified. Check the post on the platform by hand; "
            "this is unverified, not verified-good.")
    else:
        if echoed_text is None or echoed_text.strip() != spec.text.strip():
            problems.append(
                f"published text differs from what was submitted "
                f"({len(echoed_text or '')} chars vs {len(spec.text)})")
        if list(echoed_media or []) != list(spec.media_urls):
            problems.append("published media differs from what was submitted")
        elif not spec.media_urls:
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
