"""Fetch USD/BRL rates from an external provider.

Primary: Frankfurter (ECB data, no key). Fallback: open.er-api.com.
Only used by the daily cron; conversion at write time reads ``fx_rates``.
"""

import datetime as dt
from decimal import Decimal

import httpx

from backend.config import get_settings
from backend.money import rate as quantize_rate

FALLBACK_URL = "https://open.er-api.com/v6"
_TIMEOUT = httpx.Timeout(10.0)


class FxFetchError(RuntimeError):
    pass


def _frankfurter(
    client: httpx.Client, base: str, quote: str, on_date: dt.date | None
) -> Decimal:
    root = get_settings().fx_api_url.rstrip("/")
    path = on_date.isoformat() if on_date else "latest"
    resp = client.get(
        f"{root}/v1/{path}", params={"base": base, "symbols": quote}
    )
    resp.raise_for_status()
    rates = resp.json().get("rates", {})
    if quote not in rates:
        raise FxFetchError(f"frankfurter returned no {base}->{quote}")
    return quantize_rate(Decimal(str(rates[quote])))


def _er_api(client: httpx.Client, base: str, quote: str) -> Decimal:
    resp = client.get(f"{FALLBACK_URL}/latest/{base}")
    resp.raise_for_status()
    body = resp.json()
    rates = body.get("rates", {})
    if body.get("result") != "success" or quote not in rates:
        raise FxFetchError(f"er-api returned no {base}->{quote}")
    return quantize_rate(Decimal(str(rates[quote])))


def fetch_rate(
    base: str,
    quote: str,
    on_date: dt.date | None = None,
    *,
    client: httpx.Client | None = None,
) -> Decimal:
    owns_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT)
    try:
        try:
            return _frankfurter(client, base, quote, on_date)
        except (httpx.HTTPError, FxFetchError, ValueError):
            # er-api only serves the latest rate.
            return _er_api(client, base, quote)
    finally:
        if owns_client:
            client.close()


def fetch_usd_brl(
    on_date: dt.date | None = None,
    *,
    client: httpx.Client | None = None,
) -> dict[tuple[str, str], Decimal]:
    """Both directions, so conversion never needs to invert."""
    owns_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT)
    try:
        usd_brl = fetch_rate("USD", "BRL", on_date, client=client)
        brl_usd = quantize_rate(Decimal("1") / usd_brl)
        return {("USD", "BRL"): usd_brl, ("BRL", "USD"): brl_usd}
    finally:
        if owns_client:
            client.close()
