"""Round 13 — the REST publish path, and its parity with the MCP path.

The brief's hard requirement: "The REST path and the MCP path must produce
byte-identical payloads — write a test asserting that, so the two cannot drift."
Both are rendered from ONE PostSpec, and these tests assert they agree.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import blotato as B

PIN = dict(account_id="9630", platform="pinterest",
           text="Traditional units draw 1.2 to 50 amps.",
           media_urls=["https://database.blotato.io/x.png"],
           board_id="902690387751301590", title="Amp draw, measured",
           alt_text="A chart of amp draw by sauna type.",
           link="https://inhousewellness.com/blogs/news/electrical")
FB = dict(account_id="49743", platform="facebook",
          text="Of 196 CPSC recalls since 2015, most name the same component.",
          media_urls=["https://database.blotato.io/y.png"],
          page_id="472026422664772",
          first_comment="Full dataset: https://healthresearchdatabase.com/")


# ------------------------------------------------------------- REST shape
def test_pinterest_rest_body_matches_documented_schema():
    body = B.PostSpec(**PIN).rest_body()
    assert set(body) == {"post"}
    assert set(body["post"]) == {"accountId", "content", "target"}
    assert body["post"]["content"] == {
        "text": PIN["text"], "mediaUrls": PIN["media_urls"], "platform": "pinterest"}
    assert body["post"]["target"] == {
        "targetType": "pinterest", "boardId": PIN["board_id"],
        "title": PIN["title"], "altText": PIN["alt_text"], "link": PIN["link"]}


def test_facebook_puts_the_link_in_the_first_comment_not_the_body():
    body = B.PostSpec(**FB).rest_body()
    assert "http" not in body["post"]["content"]["text"]
    assert body["post"]["target"]["firstComment"] == FB["first_comment"]
    assert "link" not in body["post"]["target"]


# ------------------------------------------------------------- PARITY
def _flatten_rest(body):
    """REST body -> the same flat field/value pairs the MCP tool takes."""
    p = body["post"]
    out = {"accountId": p["accountId"], "platform": p["content"]["platform"],
           "text": p["content"]["text"], "mediaUrls": p["content"]["mediaUrls"]}
    for k, v in p["target"].items():
        if k != "targetType":
            out[k] = v
    return out


@pytest.mark.parametrize("kw", [PIN, FB], ids=["pinterest", "facebook"])
def test_rest_and_mcp_describe_an_identical_post(kw):
    """The two publish paths must never drift apart."""
    spec = B.PostSpec(**kw)
    rest, mcp = _flatten_rest(spec.rest_body()), spec.mcp_arguments()
    assert json.dumps(rest, sort_keys=True) == json.dumps(mcp, sort_keys=True), (
        f"REST and MCP disagree:\n  REST {sorted(rest.items())}\n  MCP  {sorted(mcp.items())}")


@pytest.mark.parametrize("kw", [PIN, FB], ids=["pinterest", "facebook"])
def test_parity_holds_for_every_field_not_just_the_ones_we_remembered(kw):
    spec = B.PostSpec(**kw)
    assert set(_flatten_rest(spec.rest_body())) == set(spec.mcp_arguments())


# ------------------------------------------------------------- mandatory fields
@pytest.mark.parametrize("missing", ["board_id", "title", "alt_text", "link"])
def test_pinterest_refuses_to_publish_without_every_mandatory_field(missing):
    """75 blank pins averaged 3.0 impressions; pins with text averaged 106.2."""
    with pytest.raises(B.BlotatoError, match="missing"):
        B.PostSpec(**{**PIN, missing: None}).rest_body()


def test_facebook_refuses_without_a_page_id():
    with pytest.raises(B.BlotatoError, match="pageId"):
        B.PostSpec(**{**FB, "page_id": None}).rest_body()


def test_unsupported_platform_is_refused_not_guessed():
    with pytest.raises(B.BlotatoError, match="unsupported platform"):
        B.PostSpec(**{**PIN, "platform": "instagram"}).rest_body()


# ------------------------------------------------------------- polling
class _FakeResp:
    def __init__(self, payload): self._p = json.dumps(payload).encode()
    def read(self): return self._p
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _opener_returning(seq):
    calls = {"n": 0}
    def opener(req, timeout=None):
        i = min(calls["n"], len(seq) - 1)
        calls["n"] += 1
        return _FakeResp(seq[i])
    opener.calls = calls
    return opener


def test_publish_polls_until_published():
    op = _opener_returning([{"postSubmissionId": "sub_1"},
                            {"status": "in-progress"},
                            {"status": "published", "publicUrl": "https://pin/1"}])
    got = B.publish(B.PostSpec(**PIN), "k", opener=op, sleep=lambda s: None)
    assert got["status"] == "published" and got["url"] == "https://pin/1"


def test_a_failed_submission_raises_rather_than_reporting_success():
    op = _opener_returning([{"postSubmissionId": "sub_2"},
                            {"status": "failed", "errorMessage": "board not found"}])
    with pytest.raises(B.BlotatoError, match="board not found"):
        B.publish(B.PostSpec(**PIN), "k", opener=op, sleep=lambda s: None)


def test_an_unresolved_submission_is_not_treated_as_success():
    """Post-then-unknown is the D5 case: halt, never retry blind."""
    op = _opener_returning([{"postSubmissionId": "sub_3"}, {"status": "in-progress"}])
    B_orig = B.POLL_TIMEOUT_S
    B.POLL_TIMEOUT_S = 0.01
    try:
        with pytest.raises(B.BlotatoError, match="Do NOT"):
            B.publish(B.PostSpec(**PIN), "k", opener=op, sleep=lambda s: None)
    finally:
        B.POLL_TIMEOUT_S = B_orig


# ------------------------------------------------------------- verification
def _ok_link(url, *, opener=None): return (True, "HTTP 200")
def _dead_link(url, *, opener=None): return (False, "HTTP 404")


def _published(**over):
    base = {"submission_id": "s", "status": "published", "url": "https://pin/1",
            "raw": {"content": {"text": PIN["text"], "mediaUrls": PIN["media_urls"]}}}
    base.update(over)
    return base


def test_verification_passes_on_a_good_post():
    assert B.verify_published(_published(), B.PostSpec(**PIN), link_checker=_ok_link)


def test_verification_fails_when_the_destination_is_dead():
    with pytest.raises(B.BlotatoError, match="destination link"):
        B.verify_published(_published(), B.PostSpec(**PIN), link_checker=_dead_link)


def test_verification_fails_when_the_text_was_altered():
    bad = _published(raw={"content": {"text": "3 same 180f. completely different heat.",
                                      "mediaUrls": PIN["media_urls"]}})
    with pytest.raises(B.BlotatoError, match="text differs"):
        B.verify_published(bad, B.PostSpec(**PIN), link_checker=_ok_link)


def test_verification_fails_when_no_public_url_came_back():
    with pytest.raises(B.BlotatoError, match="no public URL"):
        B.verify_published(_published(url=None), B.PostSpec(**PIN), link_checker=_ok_link)


def test_rate_limited_destination_is_backoff_not_a_dead_link():
    """HTTP 429 is backoff, never a dead link. Reading it as failure once
    blocked every INH row at once and reported an INH share of 0.0%."""
    import urllib.error as ue

    def opener(req, timeout=None):
        raise ue.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    assert B._link_ok("https://inhousewellness.com/x", opener=opener)[0] is True


def test_a_genuinely_dead_destination_still_fails():
    import urllib.error as ue

    def opener(req, timeout=None):
        raise ue.HTTPError(req.full_url, 404, "Not Found", {}, None)

    assert B._link_ok("https://inhousewellness.com/gone", opener=opener)[0] is False
