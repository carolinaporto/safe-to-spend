from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD


def test_login_with_correct_password_returns_token(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_is_rejected(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"password": "nope"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_protected_route_rejects_garbage_token(client: TestClient) -> None:
    resp = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401


def test_protected_route_accepts_valid_token(
    client: TestClient, auth_token: str
) -> None:
    resp = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["subject"] == "owner"
