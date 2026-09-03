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


def test_blank_reserve_from_the_form_is_treated_as_zero(
    api_client: TestClient, auth_headers: dict
) -> None:
    # The Settings form sends "" when the reserve field is left empty.
    resp = api_client.put(
        "/api/plan-config",
        headers=auth_headers,
        json={
            "academic_year_start": "2026-09-01",
            "academic_year_end": "2027-05-31",
            "emergency_reserve_usd": "",
            "committed_costs": [],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["emergency_reserve_usd"] == "0.00"


def test_a_non_numeric_amount_is_a_clean_422_not_a_500(
    api_client: TestClient, auth_headers: dict
) -> None:
    resp = api_client.put(
        "/api/plan-config",
        headers=auth_headers,
        json={"emergency_reserve_usd": "not a number"},
    )
    assert resp.status_code == 422


def test_requires_auth(api_client: TestClient) -> None:
    assert api_client.get("/api/plan-config").status_code == 401
