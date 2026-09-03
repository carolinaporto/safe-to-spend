from fastapi.testclient import TestClient

from backend.config import get_settings
from tests.conftest import TEST_PASSWORD

settings = get_settings()


def test_security_headers_present_on_every_response(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert (
        resp.headers["Strict-Transport-Security"]
        == "max-age=63072000; includeSubDomains; preload"
    )
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"


def test_cors_allows_localhost_origin(client: TestClient) -> None:
    resp = client.get(
        "/api/health", headers={"Origin": "http://localhost:5173"}
    )
    assert (
        resp.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    resp = client.get(
        "/api/health", headers={"Origin": "https://evil.example.com"}
    )
    assert "access-control-allow-origin" not in resp.headers


def test_cors_preflight_allows_every_method_the_app_uses(
    client: TestClient,
) -> None:
    # PUT is used by /api/plan-config and /api/budgets; a missing method in
    # allow_methods makes the browser preflight fail with 400.
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        resp = client.options(
            "/api/plan-config",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert resp.status_code == 200, method
        allowed = resp.headers.get("access-control-allow-methods", "")
        assert method in allowed, f"{method} not in {allowed!r}"


def test_login_locks_out_after_repeated_failures(client: TestClient) -> None:
    ip = {"X-Forwarded-For": "203.0.113.7"}
    for _ in range(settings.login_max_failures):
        r = client.post(
            "/api/auth/login", json={"password": "wrong"}, headers=ip
        )
        assert r.status_code == 401

    locked = client.post(
        "/api/auth/login", json={"password": "wrong"}, headers=ip
    )
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0

    # Even the correct password is refused while locked out.
    still_locked = client.post(
        "/api/auth/login", json={"password": TEST_PASSWORD}, headers=ip
    )
    assert still_locked.status_code == 429


def test_lockout_is_scoped_per_ip(client: TestClient) -> None:
    for _ in range(settings.login_max_failures):
        client.post(
            "/api/auth/login",
            json={"password": "wrong"},
            headers={"X-Forwarded-For": "203.0.113.8"},
        )

    other_ip = client.post(
        "/api/auth/login",
        json={"password": TEST_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert other_ip.status_code == 200


def test_successful_login_clears_failure_streak(client: TestClient) -> None:
    ip = {"X-Forwarded-For": "203.0.113.10"}
    for _ in range(settings.login_max_failures - 1):
        client.post("/api/auth/login", json={"password": "wrong"}, headers=ip)

    ok = client.post(
        "/api/auth/login", json={"password": TEST_PASSWORD}, headers=ip
    )
    assert ok.status_code == 200

    # Streak was reset, so a single new failure does not lock the account.
    again = client.post(
        "/api/auth/login", json={"password": "wrong"}, headers=ip
    )
    assert again.status_code == 401
