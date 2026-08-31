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

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 14  # 14 days

    # Login throttle
    login_max_failures: int = 5
    login_lockout_minutes: int = 15

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v.strip()) < 16:
            raise ValueError(
                "JWT_SECRET must be set to a value of at least 16 characters"
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
