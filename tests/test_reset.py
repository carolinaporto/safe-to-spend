from backend.models.account import Account
from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.fx_rate import FxRate
from backend.models.plan_config import PlanConfig
from backend.models.transaction import Transaction
from backend.reset import reset, wipe_ledger
from backend.seed import seed


def test_reset_empties_every_ledger_table() -> None:
    seed()
    removed = reset()
    assert removed["transactions"] > 0
    assert removed["accounts"] == 7

    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        for model in (
            Account,
            Category,
            Transaction,
            FxRate,
            Budget,
            PlanConfig,
        ):
            assert db.query(model).count() == 0
    finally:
        db.close()


def test_wipe_ledger_is_safe_to_run_on_an_empty_db(db) -> None:
    wipe_ledger(db)  # no rows, no error
    wipe_ledger(db)
