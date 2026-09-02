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
from .limits import (ALLOWED_LINK_HOSTS, ARCHETYPE_BODY, MIN_BODY_ROWS,
                     MIN_TEXT_CHARS, PIN_ALT_MAX,
                     PIN_ALT_MIN, PIN_TITLE_MAX, PIN_TITLE_MIN,
                     PLATFORM_TEXT_LIMIT, PLATFORM_TEXT_SOFT_MAX,
                     SUPPORTED_PLATFORMS)

# Strings that reached live posts because an upstream failure was stringified
# and published instead of being raised. "Failed to load this feed ... 503"
# and "Error: No response text" were both published as posts.
ERROR_PATTERN = re.compile(
    r"Error:|Failed to load|\bundefined\b|\bnull\b|No response|"
    r"\[object Object\]|\bNaN\b|Traceback|Exception:|status code \d{3}|"
    r"<!DOCTYPE|<html|"
    # Template artifacts. The first staged run emitted a Facebook first comment
    # reading "Full comparison: PLACEHOLDER" and it passed, because the error
    # check only ever ran against the post body. Same class of failure as the
    # "Error: No response text" posts: an internal artifact reaching a live post.
    r"\bPLACEHOLDER\b|\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|"
    r"lorem ipsum|\{\{|\}\}|<insert |\bYOUR_[A-Z_]+\b", re.I)


def _scan_secondary(r, label, value):
    """Run the error/placeholder check over a secondary copy field.

    Body text was always scanned; first comments, carousel slides and Pinterest
    title/altText were not, and they publish just as visibly.
    """
    if value is None:
        return
    items = value if isinstance(value, (list, tuple)) else [value]
    for i, v in enumerate(items):
        if not isinstance(v, str):
            continue
        m = ERROR_PATTERN.search(v)
        if m:
            where = f"{label}[{i}]" if isinstance(value, (list, tuple)) else label
            r.fail("SECONDARY_ERROR_PATTERN",
                   f"{where} contains an error/placeholder pattern: {m.group(0)!r}")


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


# Numerals that are structural rather than factual claims, and so are not
# required to appear in the grounding.
_ALLOWED_BARE = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "0"}
_NUMERAL = re.compile(r"\d+(?:[.,]\d+)*")


def _numerals(text):
    return [m.group(0) for m in _NUMERAL.finditer(text or "")]


def _in_grounding(num, grounding):
    """Is this numeral supported by the row's source article or source_data?"""
    n = num.replace(",", "")
    if n in grounding.replace(",", ""):
        return True
    try:
        f = float(n)
    except ValueError:
        return False
    for form in ({f"{f:g}", f"{f:.0f}", f"{f:.1f}", f"{f:.2f}", f"{int(f)}"}
                 if f == f else set()):
        if form in grounding.replace(",", ""):
            return True
    return False


def check_numerals(post, grounding, r=None):
    """Reject any numeral in caption copy that appears in neither the row's
    source_article text nor its source_data facts (Round 5, item 2).

    source_article existed to stop the model inventing figures; this makes that
    guarantee explicit and checkable rather than implied.
    """
    r = r or ValidationResult(platform=post.get("platform", "?"), post_id=post.get("id"))
    if grounding is None:
        return r
    fields = [("text", post.get("text")), ("title", post.get("title")),
              ("altText", post.get("altText")), ("firstComment", post.get("firstComment"))]
    for slide in (post.get("_slides") or []):
        fields.append(("slides", slide))
    body = post.get("_body") or {}
    for k, v in body.items():
        if isinstance(v, str):
            fields.append((f"body.{k}", v))
        elif isinstance(v, (list, tuple)):
            for cell in v:
                for c in (cell if isinstance(cell, (list, tuple)) else [cell]):
                    fields.append((f"body.{k}", str(c)))
    for label, val in fields:
        for num in _numerals(val or ""):
            if num in _ALLOWED_BARE:
                continue
            if not _in_grounding(num, grounding):
                r.fail("UNGROUNDED_NUMERAL",
                       f"{label} contains {num!r}, which appears in neither "
                       f"source_article nor source_data")
    return r


def check_body(post, r=None):
    """EMPTY_BODY -- reject a card whose archetype body renders with no rows.

    The first live cycle produced three cards that were ~70% empty: kicker,
    headline, standfirst, nothing. A card that is only a headline must not
    publish; on Pinterest the card IS the post.
    """
    r = r or ValidationResult(platform=post.get("platform", "?"), post_id=post.get("id"))
    arch = (post.get("_archetype") or "").strip().lower()
    spec = ARCHETYPE_BODY.get(arch)
    if not spec:
        return r                       # not a card payload; nothing to check

    body = post.get("_body") or {}
    missing = [f for f in spec["required"]
               if body.get(f) in (None, "", [], {})]
    if missing:
        r.fail("EMPTY_BODY",
               f"{arch} card is missing required body field(s) {missing}; "
               f"expected {spec['desc']}")
        return r

    for field in ("rows", "items", "x", "y"):
        val = body.get(field)
        if val is None:
            continue
        if not isinstance(val, (list, tuple)) or not val:
            r.fail("EMPTY_BODY", f"{arch} card body {field!r} is empty")
            continue
        if field == "rows" and len(val) < MIN_BODY_ROWS:
            r.fail("EMPTY_BODY",
                   f"{arch} card has {len(val)} body row(s); at least "
                   f"{MIN_BODY_ROWS} are needed to fill the frame")
        width = spec.get("rows_of")
        if field == "rows" and width:
            for i, row in enumerate(val):
                if not isinstance(row, (list, tuple)) or len(row) != width:
                    r.fail("EMPTY_BODY",
                           f"{arch} row {i} must be a {width}-item list, got {row!r}")
                elif any(str(c).strip() == "" for c in row):
                    r.fail("EMPTY_BODY", f"{arch} row {i} has an empty cell: {row!r}")
    return r


def validate(post, *, media_checker=None, link_checker=None, grounding=None):
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

    # ---- secondary copy fields --------------------------------------
    # missing-ok: _scan_secondary returns immediately on None (see its guard).
    _scan_secondary(r, "firstComment", post.get("firstComment"))   # missing-ok
    _scan_secondary(r, "slides", post.get("_slides"))              # missing-ok
    _scan_secondary(r, "title", post.get("title"))                 # missing-ok
    _scan_secondary(r, "altText", post.get("altText"))             # missing-ok

    # ---- numeric grounding (Round 5) --------------------------------
    check_numerals(post, grounding, r)

    # ---- card body must not be empty (Round 7) ----------------------
    check_body(post, r)

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
