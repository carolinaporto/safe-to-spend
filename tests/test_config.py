import pytest
from pydantic import ValidationError

from backend.config import Settings


def _make(monkeypatch, **overrides) -> Settings:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    for key, value in overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_missing_jwt_secret_fails_loudly(monkeypatch) -> None:
    with pytest.raises(ValidationError):
        _make(monkeypatch, JWT_SECRET=None)


def test_short_jwt_secret_is_rejected(monkeypatch) -> None:
    with pytest.raises(ValidationError):
        _make(monkeypatch, JWT_SECRET="tooshort")
    # 31 chars — still one short of the RFC 7518 HS256 minimum.
    with pytest.raises(ValidationError):
        _make(monkeypatch, JWT_SECRET="x" * 31)


def test_cors_list_is_deployed_origin_plus_localhost_only(monkeypatch) -> None:
    settings = _make(
        monkeypatch,
        JWT_SECRET="a-sufficiently-long-secret-of-32+-chars",
        CORS_ORIGINS="https://app.example.com",
    )
    origins = settings.cors_origin_list
    assert "https://app.example.com" in origins
    assert "http://localhost:5173" in origins
    assert all(
        o.startswith("http://localhost")
        or o.startswith("http://127.0.0.1")
        or o == "https://app.example.com"
        for o in origins
    )
