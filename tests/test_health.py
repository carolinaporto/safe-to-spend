from fastapi.testclient import TestClient


def test_health_is_liveness_only(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    # No infra details leaked to the public.
    assert "database" not in resp.json()


def test_health_db_requires_the_cron_secret(client: TestClient) -> None:
    assert client.get("/api/health/db").status_code == 401

    ok = client.get(
        "/api/health/db", headers={"X-Cron-Secret": "test-cron-secret"}
    )
    assert ok.status_code == 200
    assert ok.json()["database"] is True
