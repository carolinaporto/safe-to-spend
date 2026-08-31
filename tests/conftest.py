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
os.environ["JWT_SECRET"] = "test-secret"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_token(client: TestClient) -> str:
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200
    return resp.json()["access_token"]
