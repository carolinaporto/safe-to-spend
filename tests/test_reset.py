from backend.database import SessionLocal
from backend.models.account import Account
from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.fx_rate import FxRate
from backend.models.person import Person
from backend.models.plan_config import PLAN_CONFIG_ID, PlanConfig
from backend.models.transaction import Transaction
from backend.reset import reset, wipe_ledger
from backend.seed import seed


def test_reset_empties_user_data_but_keeps_a_plan_config() -> None:
    seed()
    removed = reset()
    assert removed["transactions"] > 0
    assert removed["accounts"] == 7

    db = SessionLocal()
    try:
        for model in (Account, Category, Person, Transaction, FxRate, Budget):
            assert db.query(model).count() == 0
        # The dashboard always needs a window to reason about.
        assert db.query(PlanConfig).count() == 1
        assert db.get(PlanConfig, PLAN_CONFIG_ID).emergency_reserve_usd == 0
    finally:
        db.close()


def test_wipe_ledger_is_safe_to_run_on_an_empty_db(db) -> None:
    wipe_ledger(db)  # no rows, no error
    wipe_ledger(db)
