"""Empty the ledger. No fake data — run this once to start entering your own.

    python -m backend.reset          # asks for confirmation
    python -m backend.reset --yes    # skip the prompt

Wipes: accounts, categories, people, transactions, fx_rates, budgets,
plan_config. Leaves auth state (login attempts) alone.

Do NOT run `python -m backend.seed` afterwards — it would refill the
database with fake data and erase what you entered.
"""

import sys

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.account import Account
from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.fx_rate import FxRate
from backend.models.person import Person
from backend.models.plan_config import PlanConfig
from backend.models.transaction import Transaction

# FK-safe order.
_LEDGER_MODELS = (
    Budget,
    PlanConfig,
    Transaction,
    FxRate,
    Account,
    Category,
    Person,
)


def wipe_ledger(db: Session) -> None:
    for model in _LEDGER_MODELS:
        db.execute(delete(model))
    db.flush()


def reset() -> dict[str, int]:
    db = SessionLocal()
    try:
        removed = {
            model.__tablename__: db.query(model).count()
            for model in _LEDGER_MODELS
        }
        wipe_ledger(db)
        db.commit()
        return removed
    finally:
        db.close()


def main() -> None:
    if "--yes" not in sys.argv:
        prompt = (
            "This deletes every account, transaction and budget. "
            "Type 'wipe' to confirm: "
        )
        if input(prompt).strip().lower() != "wipe":
            print("Aborted.")
            raise SystemExit(1)
    for table, count in reset().items():
        print(f"{table:>13}: removed {count}")
    print("\nDone. Add your accounts and plan in Settings, then import statements.")


if __name__ == "__main__":
    main()
