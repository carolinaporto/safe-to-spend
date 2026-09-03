from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# CORS: the deployed origin comes from CORS_ORIGINS; localhost dev origins are
# always allowed on top of it, and nothing else (security requirement).
LOCALHOST_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(BaseSettings):
    """Application configuration, read from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(alias="DATABASE_URL")
    app_password_hash: str = Field(default="", alias="APP_PASSWORD_HASH")
    # No default: a missing JWT_SECRET must fail loudly at startup.
    jwt_secret: str = Field(alias="JWT_SECRET")
    cron_secret: str = Field(default="", alias="CRON_SECRET")
    fx_api_url: str = Field(
        default="https://api.frankfurter.dev", alias="FX_API_URL"
    )
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    # Demo deployment: disables destructive actions and lets the frontend
    # hide screens that don't make sense on a shared public instance.
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")

    # Only trust X-Forwarded-For / X-Real-IP when a known proxy sits in front
    # (Vercel). Off by default so a direct client can't spoof its IP to dodge
    # the login throttle. Set TRUST_PROXY_HEADERS=true on the deployed instance.
    trust_proxy_headers: bool = Field(
        default=False, alias="TRUST_PROXY_HEADERS"
    )
    # Coarse in-memory per-IP rate limit on the API. On by default; the test
    # suite turns it off so it can fire thousands of requests.
    rate_limit_enabled: bool = Field(
        default=True, alias="RATE_LIMIT_ENABLED"
    )

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 48  # 48 hours
    jwt_issuer: str = "safe-to-spend"
    jwt_audience: str = "safe-to-spend-app"
    # Bump this (env: TOKEN_VERSION) to invalidate every issued token at once.
    token_version: str = Field(default="1", alias="TOKEN_VERSION")

    # Login throttle
    login_max_failures: int = 5
    login_lockout_minutes: int = 20
    # Circuit breaker: if failures across ALL IPs exceed this in the window,
    # lock the login endpoint entirely (mitigates a distributed spray).
    login_global_max_failures: int = 60

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_strong(cls, v: str) -> str:
        # 32 bytes = the RFC 7518 minimum for HS256. Generate with
        # `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
        if len(v.strip()) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters "
                "(use `secrets.token_urlsafe(32)`)"
            )
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        configured = [
            o.strip() for o in self.cors_origins.split(",") if o.strip()
        ]
        # Dedupe while preserving order.
        return list(dict.fromkeys([*configured, *LOCALHOST_ORIGINS]))

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize the URL to the psycopg (v3) driver."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
