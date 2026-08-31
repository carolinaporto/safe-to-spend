from fastapi.testclient import TestClient


def test_health_returns_ok_and_reaches_database(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] is True
