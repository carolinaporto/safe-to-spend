# All models are imported here so Alembic autogenerate sees their metadata.

from backend.database import Base
from backend.models.account import Account
from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.fx_rate import FxRate
from backend.models.import_batch import ImportBatch
from backend.models.login_attempt import LoginAttempt
from backend.models.merchant_rule import MerchantRule
from backend.models.person import Person
from backend.models.plan_config import PlanConfig
from backend.models.transaction import Transaction

# The user's data, in FK-safe order for delete/wipe. Auth tables (login
# attempts) are deliberately excluded. Used by backend.reset and the backup job.
LEDGER_MODELS: tuple[type[Base], ...] = (
    Budget,
    PlanConfig,
    MerchantRule,
    Transaction,
    ImportBatch,
    FxRate,
    Account,
    Category,
    Person,
)

__all__ = [
    "Base",
    "Account",
    "Budget",
    "Category",
    "FxRate",
    "ImportBatch",
    "LoginAttempt",
    "MerchantRule",
    "PlanConfig",
    "Person",
    "Transaction",
    "LEDGER_MODELS",
]
