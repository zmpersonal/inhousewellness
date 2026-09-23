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


def test_schedule_returns_the_submission_id_and_resolved_time():
    op = _opener_returning([{"postSubmissionId": "sub_1",
                             "scheduledTime": "2026-10-01T15:00:00Z"}])
    got = B.schedule(B.PostSpec(**PIN), "k", "2026-10-01T15:00:00Z", opener=op)
    assert got["submission_id"] == "sub_1"
    assert got["resolved"] == "2026-10-01T15:00:00Z"


def test_schedule_raises_when_no_submission_id_comes_back():
    op = _opener_returning([{"nothing": True}])
    with pytest.raises(B.BlotatoError, match="no submission id"):
        B.schedule(B.PostSpec(**PIN), "k", "2026-10-01T15:00:00Z", opener=op)


def test_scheduled_time_sits_beside_post_not_inside_it():
    body = B.PostSpec(**PIN).rest_body("2026-10-01T15:00:00Z")
    assert body["scheduledTime"] == "2026-10-01T15:00:00Z"
    assert "scheduledTime" not in body["post"]


def test_a_body_with_no_scheduled_time_omits_the_key_entirely():
    assert "scheduledTime" not in B.PostSpec(**PIN).rest_body()


def test_the_status_endpoint_is_never_called():
    """GET /v2/posts/{id} returns 200 "in-progress" for ANY id -- "not-an-id",
    a zero UUID, anything. It echoes the argument back and invents a status, so
    polling it can never observe publication and could be mistaken for proof."""
    import inspect
    src = inspect.getsource(B)
    assert '"/posts/"' not in src and "f\"/posts/{" not in src, (
        "something is calling the per-id status endpoint, which fabricates")


# ------------------------------------------------------------- the two locks
def test_lock_two_refuses_another_page_under_the_same_account():
    """Account 49743 holds twelve pages. Texas Home Intelligence publishes
    through the same account and the same key."""
    spec = B.PostSpec(**{**FB, "page_id": "1335273942995805"})
    with pytest.raises(B.BlotatoError, match="LOCK 2 FAILED"):
        B.assert_target_pinned(spec)


def test_lock_one_refuses_a_different_account():
    with pytest.raises(B.BlotatoError, match="LOCK 1 FAILED"):
        B.assert_target_pinned(B.PostSpec(**{**FB, "account_id": "68734"}))


def test_lock_two_refuses_a_board_that_is_not_ours():
    with pytest.raises(B.BlotatoError, match="LOCK 2 FAILED"):
        B.assert_target_pinned(B.PostSpec(**{**PIN, "board_id": "123456789"}))


def test_an_unpinned_platform_raises_rather_than_defaulting_to_allowed():
    spec = B.PostSpec(**PIN)
    spec.platform = "threads"
    with pytest.raises(B.BlotatoError, match="no pinned target"):
        B.assert_target_pinned(spec)


def test_both_real_targets_pass_the_locks():
    assert B.assert_target_pinned(B.PostSpec(**PIN))
    assert B.assert_target_pinned(B.PostSpec(**FB))


def test_schedule_asserts_the_locks_before_sending_anything():
    """There is no delete route, so a wrong target cannot be taken back."""
    sent = []

    def opener(req, timeout=None):
        sent.append(req)
        return _FakeResp({"postSubmissionId": "x"})

    with pytest.raises(B.BlotatoError, match="LOCK 2 FAILED"):
        B.schedule(B.PostSpec(**{**FB, "page_id": "1335273942995805"}), "k",
                   "2026-10-01T15:00:00Z", opener=opener)
    assert not sent, "a request was sent despite a failed lock"


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


def test_an_unrecognised_response_shape_is_unverified_not_verified_good():
    """A response that echoes nothing must not pass the text check by default.

    The missing-value rule: absence taking a branch and producing a confident
    false finding. Here that finding would be "the post is fine".
    """
    result = {"submission_id": "s", "status": "published",
              "url": "https://pin/1", "raw": {"somethingElse": 1}}
    with pytest.raises(B.BlotatoError, match="could not be verified"):
        B.verify_published(result, B.PostSpec(**PIN), link_checker=_ok_link)


def test_a_flat_response_shape_is_still_verified():
    result = {"submission_id": "s", "status": "published", "url": "https://pin/1",
              "raw": {"text": PIN["text"], "mediaUrls": PIN["media_urls"]}}
    assert B.verify_published(result, B.PostSpec(**PIN), link_checker=_ok_link)


def test_a_post_that_lost_its_media_fails_verification():
    result = {"submission_id": "s", "status": "published", "url": "https://pin/1",
              "raw": {"content": {"text": PIN["text"], "mediaUrls": []}}}
    with pytest.raises(B.BlotatoError, match="media differs"):
        B.verify_published(result, B.PostSpec(**PIN), link_checker=_ok_link)
