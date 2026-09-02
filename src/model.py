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
MAX_TOKENS = 4000
ROOT = pathlib.Path(__file__).resolve().parents[1]


class ModelUnavailable(Exception):
    pass


def load_key():
    try:
        from dotenv import dotenv_values
    except ImportError:
        raise ModelUnavailable(
            "python-dotenv is not installed. Run: .venv/bin/pip install python-dotenv")
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise ModelUnavailable(
            f"{env_path} does not exist. Create it with a single line:\n"
            f"    ANTHROPIC_API_KEY=sk-ant-...\n"
            f"(.gitignore already covers it.)")
    values = dotenv_values(env_path)
    key = (values.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise ModelUnavailable(f"{env_path} has no ANTHROPIC_API_KEY value.")
    if key.endswith(" ") or key != key.strip():
        raise ModelUnavailable("ANTHROPIC_API_KEY has surrounding whitespace.")
    return key


def make_caller(model=MODEL, max_tokens=MAX_TOKENS):
    """Return call(prompt) -> (text, input_tokens, output_tokens)."""
    try:
        import anthropic
    except ImportError:
        raise ModelUnavailable(
            "the anthropic SDK is not installed. Run: .venv/bin/pip install anthropic")

    key = load_key()
    # Ignore any shell ANTHROPIC_BASE_URL: use the SDK default endpoint.
    client = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")

    def call(prompt):
        r = client.messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return text, r.usage.input_tokens, r.usage.output_tokens

    call.model = model
    return call
