"""Live model client for the caption call. The ONE model call in the cycle.

Loads ANTHROPIC_API_KEY from .env at repo root via python-dotenv.

ANTHROPIC_BASE_URL is deliberately NOT read from .env. If it is set in the shell
and points at a proxy, we ignore it and use the SDK default endpoint -- a proxy
in the shell environment is not necessarily the endpoint this key belongs to.
"""
from __future__ import annotations

import os
import pathlib

MODEL = "claude-sonnet-5"
# Sonnet 5 emits extended-thinking tokens before its text. The first live cycle
# spent 3,237 of a 4,000 budget thinking, hit max_tokens, and truncated the JSON
# array mid-object. Budget for thinking AND the answer.
MAX_TOKENS = 16000

# Extended thinking is ON by default for this model and dominated the first live
# cycle: 13,224 output tokens across 2 calls, of which the great majority was
# thinking, at $0.0884 per published post against a $0.05 ceiling.
#
# Caption writing is a short, heavily-constrained transformation of a structured
# brief -- the reasoning budget buys little here, and the output is validated in
# code either way. Disabled by default; flip to None to re-enable and measure.
THINKING = {"type": "disabled"}
ROOT = pathlib.Path(__file__).resolve().parents[1]


class ModelUnavailable(Exception):
    pass


def load_env():
    """Return every value from .env at the repo root, as a dict."""
    try:
        from dotenv import dotenv_values
    except ImportError:
        raise ModelUnavailable(
            "python-dotenv is not installed. Run: .venv/bin/pip install python-dotenv")
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise ModelUnavailable(
            f"{env_path} does not exist. Create it with:\n"
            f"    ANTHROPIC_API_KEY=sk-ant-...\n"
            f"(.gitignore already covers it.)")
    # dotenv_values/load_dotenv with no argument search the CURRENT WORKING
    # DIRECTORY, not the repo root, so anything run from scripts/ or src/ would
    # silently find nothing. Always pass the resolved path.
    return dotenv_values(env_path), env_path


def load_workspace_id():
    """Identity-linked keys require a workspace id header. Optional otherwise."""
    values, _ = load_env()
    return (values.get("ANTHROPIC_WORKSPACE_ID") or "").strip() or None


def load_key():
    values, env_path = load_env()
    key = (values.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise ModelUnavailable(f"{env_path} has no ANTHROPIC_API_KEY value.")
    if key != key.strip():
        raise ModelUnavailable("ANTHROPIC_API_KEY has surrounding whitespace.")
    # Presence is not usability. A placeholder loads perfectly well and then
    # fails at the API with a 401 -- the same missing-value shape that has
    # produced three false findings in this project already. Check the shape
    # here, where the diagnostic is cheap and specific.
    if not key.startswith("sk-ant-"):
        raise ModelUnavailable(
            f"ANTHROPIC_API_KEY does not start with 'sk-ant-' (starts {key[:7]!r}).")
    if len(key) < 60:
        raise ModelUnavailable(
            f"ANTHROPIC_API_KEY is {len(key)} characters; real keys are ~100+. "
            f"This looks like a placeholder, not a key. The value in .env begins "
            f"{key[:10]!r} — replace it with the real key from the Anthropic console.")
    return key


def make_caller(model=MODEL, max_tokens=MAX_TOKENS):
    """Return call(prompt) -> (text, input_tokens, output_tokens)."""
    try:
        import anthropic
    except ImportError:
        raise ModelUnavailable(
            "the anthropic SDK is not installed. Run: .venv/bin/pip install anthropic")

    key = load_key()
    # Identity-linked keys (sk-ant-api03-... issued against a user identity rather
    # than a workspace) require the workspace to be named explicitly:
    #   400 invalid_request_error: anthropic-workspace-id is required when
    #   authenticating with an identity-linked API key
    headers = {}
    ws = load_workspace_id()
    if ws:
        headers["anthropic-workspace-id"] = ws
    # Ignore any shell ANTHROPIC_BASE_URL: use the SDK default endpoint.
    client = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com",
                                 default_headers=headers or None)

    def call(prompt):
        kwargs = {"model": model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]}
        if THINKING is not None:
            kwargs["thinking"] = THINKING
        r = client.messages.create(**kwargs)
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")

        # A truncated response is NOT malformed output -- it is an incomplete
        # request, and reporting it as "response is not valid JSON" sends the
        # reader hunting for a schema bug that does not exist. Same shape as
        # every other missing-value failure in this project: surface the real
        # cause where it is known.
        if r.stop_reason == "max_tokens":
            thinking = getattr(r.usage, "output_tokens_details", None)
            tk = getattr(thinking, "thinking_tokens", 0) if thinking else 0
            raise ModelUnavailable(
                f"response hit max_tokens ({max_tokens}) and was truncated after "
                f"{len(text)} chars of text ({tk} tokens went to thinking). "
                f"Raise MAX_TOKENS in src/model.py; the output is incomplete, not "
                f"malformed.")
        if not text.strip():
            raise ModelUnavailable(
                f"model returned no text block (stop_reason={r.stop_reason!r}, "
                f"{len(r.content)} content block(s)).")
        return text, r.usage.input_tokens, r.usage.output_tokens

    call.model = model
    return call
