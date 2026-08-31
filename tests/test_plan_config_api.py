from fastapi.testclient import TestClient


def test_get_creates_and_returns_a_default_config(
    api_client: TestClient, auth_headers: dict
) -> None:
    body = api_client.get("/api/plan-config", headers=auth_headers).json()
    assert "academic_year_start" in body
    assert body["emergency_reserve_usd"] == "0.00"
    assert body["committed_costs"] == []


def test_put_updates_fields_and_committed_costs(
    api_client: TestClient, auth_headers: dict
) -> None:
    resp = api_client.put(
        "/api/plan-config",
        headers=auth_headers,
        json={
            "academic_year_start": "2026-08-25",
            "academic_year_end": "2027-05-20",
            "emergency_reserve_usd": "2500",
            "committed_costs": [
                {
                    "label": "Tuition",
                    "amount_usd": "9200.5",
                    "due_date": "2027-01-10",
                }
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["emergency_reserve_usd"] == "2500.00"
    assert body["committed_costs"][0]["amount_usd"] == "9200.50"

    # persisted
    again = api_client.get("/api/plan-config", headers=auth_headers).json()
    assert again["academic_year_end"] == "2027-05-20"
    assert again["committed_costs"][0]["label"] == "Tuition"


def test_requires_auth(api_client: TestClient) -> None:
    assert api_client.get("/api/plan-config").status_code == 403
