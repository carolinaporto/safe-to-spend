# SQLAlchemy models are registered here so Alembic autogenerate sees them.

from backend.database import Base
from backend.models.account import Account
from backend.models.category import Category
from backend.models.fx_rate import FxRate
from backend.models.login_attempt import LoginAttempt
from backend.models.person import Person
from backend.models.transaction import Transaction

__all__ = [
    "Base",
    "Account",
    "Category",
    "FxRate",
    "LoginAttempt",
    "Person",
    "Transaction",
]
