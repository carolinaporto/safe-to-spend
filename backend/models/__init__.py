# SQLAlchemy models are registered here so Alembic autogenerate sees them.
# The full data model lands in Phase 1.

from backend.database import Base
from backend.models.login_attempt import LoginAttempt

__all__ = ["Base", "LoginAttempt"]
