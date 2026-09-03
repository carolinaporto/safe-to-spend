import os

import bcrypt

TEST_PASSWORD = "correct-horse-battery-staple"

# The test fixtures TRUNCATE every table between tests. That must NEVER touch a
# real database. We force the DB name to end in `_test`: the dev DB is
# `safe_to_spend`, the test DB is `safe_to_spend_test` (create it once with
# `createdb -U sts safe_to_spend_test` or the equivalent). Set TEST_DATABASE_URL
# to override entirely.
_DEFAULT_TEST_DB = "postgresql+psycopg://sts:sts@localhost:5432/safe_to_spend_test"
_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not _url:
    _url = _DEFAULT_TEST_DB
elif not _url.rsplit("/", 1)[-1].split("?", 1)[0].endswith("_test"):
    base, name = _url.rsplit("/", 1)
    _url = f"{base}/{name.split('?', 1)[0]}_test"
os.environ["DATABASE_URL"] = _url

# Environment must be populated before anything under backend/ is imported,
# because backend.config.Settings requires these at construction time.
os.environ["APP_PASSWORD_HASH"] = bcrypt.hashpw(
    TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()
).decode("utf-8")
os.environ["JWT_SECRET"] = "test-secret-at-least-16-chars-long"
os.environ["CRON_SECRET"] = "test-cron-secret"
os.environ["CORS_ORIGINS"] = "https://app.example.com"
# The suite simulates the deployed environment (behind Vercel's proxy) so the
# per-IP login throttle can be exercised with X-Forwarded-For.
os.environ["TRUST_PROXY_HEADERS"] = "true"
# The coarse in-memory rate limiter would trip on the volume of test requests.
os.environ["RATE_LIMIT_ENABLED"] = "false"

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


def _assert_test_database() -> None:
    """Refuse to run the destructive fixtures against a non-test database."""
    name = str(engine.url.database or "")
    if not name.endswith("_test"):
        raise RuntimeError(
            f"refusing to TRUNCATE database {name!r}: the test DB name must "
            "end in '_test' (see conftest.py)"
        )


@pytest.fixture(autouse=True)
def _clean_tables() -> None:
    """Every test starts from empty tables. Anything committed by a test
    (e.g. the seed script) is cleared before the next one runs."""
    from sqlalchemy import text

    _assert_test_database()
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE transactions, fx_rates, accounts, categories, "
                "people, login_attempts, budgets, plan_config, "
                "merchant_rules, import_batches, transfers, expense_shares, "
                "recurring_rules RESTART IDENTITY CASCADE"
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
