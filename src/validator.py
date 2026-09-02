"""Output validator -- adjustment C2.

The single most important component in this project. It sits in the same
architectural slot as the D5 duplicate gate and for the same reason: it is a
CODE gate, not model guidance. It would have blocked all 81 structurally
broken posts in the 322-post history.

Contract:
    validate(post) -> ValidationResult
    assert_publishable(post) -> None, raises PostRejected

There is no "fix it up and publish anyway" path. A post either passes whole
or it does not publish. Never publish a degraded version.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from . import health_claims as hc
from .limits import (ALLOWED_LINK_HOSTS, MIN_TEXT_CHARS, PIN_ALT_MAX,
                     PIN_ALT_MIN, PIN_TITLE_MAX, PIN_TITLE_MIN,
                     PLATFORM_TEXT_LIMIT, PLATFORM_TEXT_SOFT_MAX,
                     SUPPORTED_PLATFORMS)

# Strings that reached live posts because an upstream failure was stringified
# and published instead of being raised. "Failed to load this feed ... 503"
# and "Error: No response text" were both published as posts.
ERROR_PATTERN = re.compile(
    r"Error:|Failed to load|\bundefined\b|\bnull\b|No response|"
    r"\[object Object\]|\bNaN\b|Traceback|Exception:|status code \d{3}|"
    r"<!DOCTYPE|<html", re.I)


class PostRejected(Exception):
    """Raised when a post fails validation. Carries the structured failures."""

    def __init__(self, result):
        self.result = result
        super().__init__(result.summary())


@dataclass(frozen=True)
class Failure:
    code: str
    message: str

    def __str__(self):
        return f"[{self.code}] {self.message}"


@dataclass
class ValidationResult:
    platform: str
    post_id: str | None = None
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.failures

    def fail(self, code, message):
        self.failures.append(Failure(code, message))

    def warn(self, code, message):
        self.warnings.append(Failure(code, message))

    def codes(self):
        return [f.code for f in self.failures]

    def summary(self):
        who = f"{self.platform}/{self.post_id or '<no-id>'}"
        if self.ok:
            return f"OK {who}"
        lines = "\n".join(f"  - {f}" for f in self.failures)
        return f"REJECTED {who} ({len(self.failures)} failure(s)):\n{lines}"


def _is_reachable(url, checker):
    try:
        return bool(checker(url))
    except Exception:
        return False


def validate(post, *, media_checker=None, link_checker=None):
    """Validate one platform-specific post payload.

    post keys: platform, text, mediaUrls, and for pinterest additionally
    title, altText, link. media_checker/link_checker are optional callables
    taking a URL and returning truthy when reachable; when omitted, only
    structural URL checks run (so unit tests need no network).
    """
    platform = (post.get("platform") or "").strip().lower()
    r = ValidationResult(platform=platform, post_id=post.get("id"))

    if platform not in SUPPORTED_PLATFORMS:
        r.fail("PLATFORM_UNSUPPORTED",
               f"platform {platform!r} is not one of {sorted(SUPPORTED_PLATFORMS)}")
        return r

    # ---- text -------------------------------------------------------
    text = post.get("text")
    if text is None or not isinstance(text, str) or not text.strip():
        # 75 blank Pinterest pins averaged 3.0 impressions.
        r.fail("TEXT_EMPTY", "text is empty, whitespace-only or not a string")
    else:
        stripped = text.strip()
        if len(stripped) < MIN_TEXT_CHARS:
            r.fail("TEXT_TOO_SHORT",
                   f"text is {len(stripped)} chars, minimum is {MIN_TEXT_CHARS}")

        m = ERROR_PATTERN.search(text)
        if m:
            r.fail("TEXT_ERROR_PATTERN",
                   f"text contains an error/placeholder pattern: {m.group(0)!r}")

        hard = PLATFORM_TEXT_LIMIT[platform]
        soft = PLATFORM_TEXT_SOFT_MAX[platform]
        if len(text) > hard:
            r.fail("TEXT_OVER_PLATFORM_LIMIT",
                   f"text is {len(text)} chars, {platform} hard limit is {hard}")
        elif len(text) > soft:
            # 39 FB posts of 25k-51k chars averaged ~3 impressions.
            r.fail("TEXT_OVER_SOFT_LIMIT",
                   f"text is {len(text)} chars, our {platform} ceiling is {soft} "
                   f"(raw article dump?)")

        # ---- health claims (A2) -------------------------------------
        for code, matched, why in hc.find_banned_claims(text):
            r.fail(f"HEALTH_{code}", f"{why}: {matched!r}")

        if hc.is_health_adjacent(text) and not hc.has_hedge(text):
            r.fail("HEALTH_UNHEDGED",
                   "health-adjacent post with no hedged framing "
                   "(may / can / associated with / limited evidence)")

        if hc.needs_contraindication(text) and not hc.has_contraindication(text):
            r.fail("HEALTH_NO_CONTRAINDICATION",
                   "cold-exposure topic without contraindication language")

    # ---- media ------------------------------------------------------
    media = post.get("mediaUrls")
    if not media or not isinstance(media, (list, tuple)):
        r.fail("MEDIA_EMPTY", "mediaUrls is empty or not a list")
    else:
        for u in media:
            if not isinstance(u, str) or not u.strip():
                r.fail("MEDIA_INVALID_URL", f"media url is not a non-empty string: {u!r}")
                continue
            parsed = urlparse(u)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                r.fail("MEDIA_INVALID_URL", f"media url is not an absolute http(s) URL: {u!r}")
            elif media_checker and not _is_reachable(u, media_checker):
                r.fail("MEDIA_UNREACHABLE", f"media url is unreachable: {u}")

    # ---- pinterest structured fields (C4) ---------------------------
    if platform == "pinterest":
        _validate_pinterest(post, r, link_checker)

    # ---- facebook: link belongs in the first comment, not the body --
    if platform == "facebook":
        body = post.get("text") or ""
        if re.search(r"https?://", body):
            r.fail("FB_LINK_IN_BODY",
                   "Facebook link must go in firstComment, never the post body")

    return r


def _validate_pinterest(post, r, link_checker):
    title = (post.get("title") or "").strip()
    if not title:
        r.fail("PIN_TITLE_MISSING", "Pinterest pin has no title")
    else:
        if len(title) < PIN_TITLE_MIN:
            r.warn("PIN_TITLE_SHORT",
                   f"title is {len(title)} chars, target is {PIN_TITLE_MIN}-70")
        if len(title) > PIN_TITLE_MAX:
            r.fail("PIN_TITLE_TOO_LONG",
                   f"title is {len(title)} chars, hard cap is {PIN_TITLE_MAX}")
        if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", title):
            r.fail("PIN_TITLE_EMOJI", "Pinterest title must not contain emoji")

    alt = (post.get("altText") or "").strip()
    if not alt:
        r.fail("PIN_ALT_MISSING", "Pinterest pin has no altText")
    elif not (PIN_ALT_MIN <= len(alt) <= PIN_ALT_MAX):
        r.fail("PIN_ALT_LENGTH",
               f"altText is {len(alt)} chars, must be {PIN_ALT_MIN}-{PIN_ALT_MAX}")

    link = (post.get("link") or "").strip()
    if not link:
        r.fail("PIN_LINK_MISSING", "Pinterest pin has no destination link")
    else:
        parsed = urlparse(link)
        if parsed.scheme not in ("http", "https"):
            r.fail("PIN_LINK_INVALID", f"link is not an absolute http(s) URL: {link!r}")
        elif parsed.netloc.lower() not in ALLOWED_LINK_HOSTS:
            r.fail("PIN_LINK_OFFSITE",
                   f"link host {parsed.netloc!r} is not an allowed InHouse Wellness host")
        elif link_checker and not _is_reachable(link, link_checker):
            # 89 of 103 queue rows currently point at a 404.
            r.fail("PIN_LINK_UNREACHABLE", f"link is unreachable (404?): {link}")

    if not (post.get("boardId") or "").strip():
        r.fail("PIN_BOARD_MISSING", "Pinterest pin has no boardId")


def assert_publishable(post, **kw):
    """Gate used by the post helper. Raises rather than returning a flag, so
    a caller cannot accidentally ignore the result."""
    r = validate(post, **kw)
    if not r.ok:
        raise PostRejected(r)
    return r


def validate_batch(posts, **kw):
    return [validate(p, **kw) for p in posts]


def assert_no_shared_text(posts):
    """Per-platform copy always (hard rule). 207 of 300 historical posts
    shared caption text across channels."""
    seen = {}
    for p in posts:
        t = (p.get("text") or "").strip()
        if not t:
            continue
        if t in seen:
            raise PostRejected(ValidationResult(
                platform=p.get("platform", "?"), post_id=p.get("id"),
                failures=[Failure("DUPLICATE_CROSS_PLATFORM_TEXT",
                                  f"identical text also used for {seen[t]!r}")]))
        seen[t] = p.get("platform")
