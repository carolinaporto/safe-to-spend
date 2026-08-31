import datetime as dt
from decimal import Decimal

import httpx
import pytest

from backend.services import fx_provider


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_rate_uses_frankfurter_first() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "frankfurter" in str(request.url)
        return httpx.Response(200, json={"rates": {"BRL": 5.4321}})

    result = fx_provider.fetch_rate("USD", "BRL", client=_client(handler))
    assert result == Decimal("5.43210000")


def test_fetch_rate_falls_back_to_er_api_on_frankfurter_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "frankfurter" in str(request.url):
            return httpx.Response(503)
        return httpx.Response(
            200, json={"result": "success", "rates": {"BRL": 5.11}}
        )

    result = fx_provider.fetch_rate("USD", "BRL", client=_client(handler))
    assert result == Decimal("5.11000000")


def test_fetch_usd_brl_returns_both_directions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rates": {"BRL": 5.0}})

    pairs = fx_provider.fetch_usd_brl(client=_client(handler))
    assert pairs[("USD", "BRL")] == Decimal("5.00000000")
    assert pairs[("BRL", "USD")] == Decimal("0.20000000")


def test_fetch_rate_raises_when_both_providers_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(Exception):
        fx_provider.fetch_rate("USD", "BRL", client=_client(handler))


def test_frankfurter_dated_endpoint_is_requested_for_a_past_date() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"rates": {"BRL": 5.2}})

    fx_provider.fetch_rate(
        "USD", "BRL", dt.date(2025, 1, 15), client=_client(handler)
    )
    assert "2025-01-15" in seen["url"]
