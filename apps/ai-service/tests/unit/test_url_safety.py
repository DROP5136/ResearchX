"""URL safety / SSRF guard tests."""

from __future__ import annotations

import pytest

from app.utils.url_safety import UnsafeURLError, validate_public_http_url


def test_allows_https_public():
    assert validate_public_http_url("https://example.com/path") == "https://example.com/path"


def test_rejects_file_scheme():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("file:///etc/passwd")


def test_rejects_localhost():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://127.0.0.1/admin")
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://localhost:8000/health")


def test_rejects_metadata_host():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://metadata.google.internal/computeMetadata/v1")


def test_rejects_credentials_in_url():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("https://user:pass@example.com/x")
