import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.deps import deny_in_demo


def test_meta_defaults_to_full_instance(client: TestClient) -> None:
    resp = client.get("/api/meta")
    assert resp.status_code == 200
    assert resp.json() == {"demo_mode": False, "import_enabled": True}


def test_meta_reflects_demo_mode(demo_mode, client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert body["demo_mode"] is True
    assert body["import_enabled"] is False


def test_deny_in_demo_is_noop_on_a_full_instance() -> None:
    assert deny_in_demo() is None


def test_deny_in_demo_blocks_when_demo_mode_is_on(demo_mode) -> None:
    with pytest.raises(HTTPException) as exc:
        deny_in_demo()
    assert exc.value.status_code == 403
