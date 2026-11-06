"""Check the built container's compression, caching and Web Serial headers."""

import gzip
import hashlib
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081").rstrip("/")


def request(path, headers=None):
    try:
        response = urlopen(Request(base + path, headers=headers or {}), timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read()


def assert_security(headers):
    assert headers["Permissions-Policy"] == "serial=(self)"
    assert "connect-src 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


status, headers, html = request("/")
assert status == 200 and headers["Cache-Control"] == "no-cache"
assert_security(headers)
assets = re.findall(rb'(?:src|href)="([^"?]+\.(?:js|css|svg))\?v=([a-f0-9]{16})"', html)
assert len(assets) == 3, "all assets need content hashes so deployments bypass old caches"

for path, expected_hash in [(b"", None), *assets]:
    url = "/" + path.decode()
    if expected_hash:
        url += "?v=" + expected_hash.decode()
    status, headers, raw = request(url)
    assert status == 200
    assert_security(headers)
    if expected_hash:
        assert hashlib.sha256(raw).hexdigest()[:16] == expected_hash.decode()
        assert "max-age=3600" in headers["Cache-Control"]
    status, compressed_headers, compressed = request(url, {"Accept-Encoding": "gzip"})
    assert status == 200 and compressed_headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in compressed_headers["Vary"]
    assert gzip.decompress(compressed) == raw
    assert len(compressed) < len(raw)
    assert_security(compressed_headers)
    status, _, body = request(url, {"If-None-Match": headers["ETag"]})
    assert status == 304 and not body

status, headers, _ = request("/missing.js")
assert status == 404 and "max-age=3600" not in headers.get("Cache-Control", "")
assert_security(headers)
print("HTML revalidation, hashed assets, gzip, ETag/304, 404 and Web Serial headers: OK")
