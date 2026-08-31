import os

import bcrypt

TEST_PASSWORD = "correct-horse-battery-staple"

# Environment must be populated before anything under backend/ is imported,
# because backend.config.Settings requires these at construction time.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://sts:sts@localhost:5432/safe_to_spend",
)
os.environ["APP_PASSWORD_HASH"] = bcrypt.hashpw(
    TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()
).decode("utf-8")
os.environ["JWT_SECRET"] = "test-secret-at-least-16-chars-long"
os.environ["CRON_SECRET"] = "test-cron-secret"
os.environ["CORS_ORIGINS"] = "https://app.example.com"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.database import engine  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrate() -> None:
    """Bring the test database up to head once per test session."""
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def _clean_tables() -> None:
    """Every test starts from empty tables. Anything committed by a test
    (e.g. the seed script) is cleared before the next one runs."""
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE transactions, fx_rates, accounts, categories, "
                "people, login_attempts RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
def demo_mode() -> None:
    """Run the app with DEMO_MODE=true for the duration of a test."""
    from backend.config import get_settings

    monkey = pytest.MonkeyPatch()
    get_settings.cache_clear()
    monkey.setenv("DEMO_MODE", "true")
    try:
        yield
    finally:
        monkey.undo()
        get_settings.cache_clear()


@pytest.fixture
def db() -> Session:
    """A session wrapped in a transaction that is rolled back after the test,
    so nothing it writes persists between tests."""
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_token(client: TestClient) -> str:
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers() -> dict[str, str]:
    from backend.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token()}"}


@pytest.fixture
def api_client(db: Session) -> TestClient:
    """TestClient whose request-scoped DB session is the rollback `db`
    session, so endpoint writes never persist between tests."""
    from backend.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
