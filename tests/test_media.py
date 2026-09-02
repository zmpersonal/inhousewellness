"""Media pipeline tests. No network: the opener is stubbed."""
import io, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from src.media import MediaError, content_type_for, put, upload, verify


class Resp:
    def __init__(self, status=200, body=b"x" * 10):
        self.status, self._b = status, body
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def opener_for(responses):
    seq = list(responses)
    calls = []
    def op(req, timeout=None):
        calls.append(req)
        return seq.pop(0) if len(seq) > 1 else seq[0]
    op.calls = calls
    return op


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "card.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"d" * 100)
    return p


def test_upload_puts_raw_bytes_with_correct_content_type(png):
    op = opener_for([Resp(200, b'{"Key":"k"}'), Resp(200, png.read_bytes())])
    r = upload(png, "https://up", "https://pub", opener=op)
    put_req = op.calls[0]
    assert put_req.method == "PUT"
    assert put_req.data == png.read_bytes(), "body must be the raw file"
    assert put_req.headers["Content-type"] == "image/png"
    assert r["bytes"] == png.stat().st_size


def test_public_url_is_verified_before_use(png):
    op = opener_for([Resp(200, b'{"Key":"k"}'), Resp(200, png.read_bytes())])
    upload(png, "https://up", "https://pub", opener=op)
    assert len(op.calls) == 2, "must verify the publicUrl, not just PUT"
    assert op.calls[1].full_url == "https://pub"


def test_unreachable_public_url_raises(png):
    op = opener_for([Resp(200, b'{"Key":"k"}'), Resp(404, b"")])
    with pytest.raises(MediaError) as e:
        upload(png, "https://up", "https://pub", opener=op)
    assert "404" in str(e.value)


def test_byte_mismatch_raises(png):
    """A 200 that returns different bytes is a silent corruption, not a success."""
    op = opener_for([Resp(200, b'{"Key":"k"}'), Resp(200, b"short")])
    with pytest.raises(MediaError) as e:
        upload(png, "https://up", "https://pub", opener=op)
    assert "byte count" in str(e.value)


def test_empty_public_body_raises(png):
    op = opener_for([Resp(200, b'{"Key":"k"}'), Resp(200, b"")])
    with pytest.raises(MediaError):
        upload(png, "https://up", "https://pub", opener=op)


def test_zero_byte_file_refused(tmp_path):
    z = tmp_path / "empty.png"
    z.write_bytes(b"")
    with pytest.raises(MediaError) as e:
        put(z, "https://up", opener=opener_for([Resp()]))
    assert "zero-byte" in str(e.value)


def test_missing_file_refused(tmp_path):
    with pytest.raises(MediaError) as e:
        put(tmp_path / "nope.png", "https://up", opener=opener_for([Resp()]))
    assert "does not exist" in str(e.value)


def test_unsupported_extension_refused(tmp_path):
    f = tmp_path / "x.svg"
    f.write_bytes(b"<svg/>")
    with pytest.raises(MediaError):
        put(f, "https://up", opener=opener_for([Resp()]))


@pytest.mark.parametrize("name,ct", [
    ("a.png", "image/png"), ("a.jpg", "image/jpeg"), ("a.mp4", "video/mp4")])
def test_content_types(name, ct):
    assert content_type_for(name) == ct


def test_upload_http_error_surfaces(png):
    import urllib.error
    def op(req, timeout=None):
        raise urllib.error.HTTPError("u", 403, "Forbidden", {}, io.BytesIO(b"denied"))
    with pytest.raises(MediaError) as e:
        put(png, "https://up", opener=op)
    assert "403" in str(e.value)
