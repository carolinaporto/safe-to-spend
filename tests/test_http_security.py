import importlib

import jwt
import pytest
from fastapi.testclient import TestClient

from backend import http_security, security
from backend.config import get_settings


def test_hardening_headers_on_every_response(client: TestClient) -> None:
    h = client.get("/api/health").headers
    assert h["Content-Security-Policy"].startswith("default-src 'none'")
    assert h["Cross-Origin-Opener-Policy"] == "same-origin"
    assert h["Cross-Origin-Resource-Policy"] == "same-site"
    assert h["X-Permitted-Cross-Domain-Policies"] == "none"
    assert "camera=()" in h["Permissions-Policy"]
    assert h["Cache-Control"] == "no-store"


def test_no_interactive_docs_or_schema(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_oversized_body_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/login",
        content=b"x" * (1_100_000),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413


def test_rate_limiter_trips_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    get_settings.cache_clear()
    http_security._hits.clear()
    http_security._writes.clear()
    try:
        with TestClient(importlib.import_module("backend.main").app) as c:
            statuses = [
                c.get("/api/health").status_code
                for _ in range(http_security._MAX_PER_WINDOW + 5)
            ]
        assert 429 in statuses
    finally:
        get_settings.cache_clear()
        http_security._hits.clear()
        http_security._writes.clear()


def test_token_carries_and_verifies_iss_aud_ver() -> None:
    token = security.create_access_token()
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == "safe-to-spend"
    assert claims["aud"] == "safe-to-spend-app"
    assert claims["ver"] == get_settings().token_version
    # Round-trips through the strict decoder.
    assert security.decode_access_token(token)["sub"] == "owner"


def test_token_from_a_superseded_version_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = security.create_access_token()
    monkeypatch.setattr(security.settings, "token_version", "2")
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token(token)
