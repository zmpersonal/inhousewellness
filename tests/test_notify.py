"""Round 19 — failure notification."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import notify


class _R:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_a_missing_webhook_does_not_pretend_to_have_delivered(capsys):
    assert notify.send("blocked", "t", "b", webhook="") is False
    assert "NOT delivered" in capsys.readouterr().out


def test_a_webhook_failure_reports_failure_rather_than_success(capsys):
    def opener(req, timeout=None):
        raise OSError("connection refused")
    assert notify.send("blocked", "t", "b", webhook="https://h", opener=opener) is False
    assert "NOT delivered" in capsys.readouterr().out


def test_a_delivered_message_carries_the_harness_prefix():
    seen = {}
    def opener(req, timeout=None):
        seen["body"] = req.data.decode()
        return _R()
    assert notify.send("blocked", "queue dry", "runway 0.4w",
                       webhook="https://h", opener=opener) is True
    # json.dumps escapes non-ASCII, so read the decoded payload, not the wire
    # bytes -- asserting on the escaped form tests the encoder, not the message.
    import json as _json
    text = _json.loads(seen["body"])["text"]
    assert "🔴 BLOCKED" in text and "queue dry" in text and "runway 0.4w" in text


def test_notify_never_gates_the_work_it_reports():
    """A missing webhook must not turn a healthy run red, nor a failed run
    green. main() always exits 0."""
    import ast, inspect
    src = inspect.getsource(notify.main)
    returns = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Return)]
    assert len(returns) == 1 and returns[0].value.value == 0
