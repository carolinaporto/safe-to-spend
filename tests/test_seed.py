from decimal import Decimal

from backend.database import SessionLocal
from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import TransactionDirection
from backend.models.fx_rate import FxRate
from backend.models.person import Person
from backend.models.transaction import Transaction
from backend.seed import seed
from backend.services.balances import native_balances


def test_seed_produces_a_realistic_dataset() -> None:
    counts = seed()
    assert counts["accounts"] == 7
    assert counts["people"] == 4
    assert counts["categories"] == 30
    assert counts["transactions"] > 120
    assert counts["fx_rates"] > 100
    assert counts["budgets"] > 0
    assert counts["merchant_rules"] > 0
    assert counts["transfers"] > 0
    assert counts["expense_shares"] > 0
    assert counts["recurring_rules"] == 5


def test_seed_wires_up_phase_4_relationships() -> None:
    seed()
    db = SessionLocal()
    try:
        from backend.models.expense_share import ExpenseShare
        from backend.models.transfer import Transfer

        # Dad's external card has an owner and carries "I owe it back" slices.
        dad = db.query(Person).filter(Person.name == "Dad").one()
        card = db.query(Account).filter(Account.name == "Dad's Card").one()
        assert card.owner_person_id == dad.id

        # Every transfer's two legs net to zero movement across the ledger in
        # USD terms only loosely (FX), but each has a positive recorded cost
        # field and a matching pair of transaction legs.
        for t in db.query(Transfer):
            legs = (
                db.query(Transaction)
                .filter(Transaction.transfer_group_id == t.transfer_group_id)
                .count()
            )
            assert legs == 2

        # Shared rent: my reported slice is less than the full charge.
        shared = (
            db.query(Transaction).filter(Transaction.is_shared.is_(True)).first()
        )
        assert shared is not None
        others = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.transaction_id == shared.id)
            .count()
        )
        assert others == 2
    finally:
        db.close()


def test_seed_is_idempotent() -> None:
    first = seed()
    second = seed()
    assert first == second


def test_seeded_fx_has_both_directions() -> None:
    seed()
    db = SessionLocal()
    try:
        bases = {b for (b,) in db.query(FxRate.base).distinct()}
        assert bases == {"USD", "BRL"}
    finally:
        db.close()


def test_seeded_transaction_usd_amounts_are_consistent() -> None:
    seed()
    db = SessionLocal()
    try:
        for txn in db.query(Transaction).limit(200):
            expected = (txn.amount * txn.fx_rate_to_usd).quantize(Decimal("0.01"))
            assert abs(txn.amount_usd - expected) <= Decimal("0.01")
    finally:
        db.close()


def test_seeded_balances_reconcile_to_opening_plus_flows() -> None:
    seed()
    db = SessionLocal()
    try:
        native = native_balances(db)
        for account in db.query(Account):
            inflow = sum(
                (
                    t.amount
                    for t in account_txns(db, account.id)
                    if t.direction == TransactionDirection.in_
                ),
                Decimal("0"),
            )
            outflow = sum(
                (
                    t.amount
                    for t in account_txns(db, account.id)
                    if t.direction == TransactionDirection.out
                ),
                Decimal("0"),
            )
            assert native[account.id] == (
                account.opening_balance + inflow - outflow
            ).quantize(Decimal("0.01"))
    finally:
        db.close()


def account_txns(db, account_id):
    return db.query(Transaction).filter(Transaction.account_id == account_id)


def test_seed_leaves_no_orphan_people_table_rows() -> None:
    seed()
    db = SessionLocal()
    try:
        assert db.query(Person).filter(Person.role == "me").count() == 1
        assert db.query(Category).filter(Category.name == "Rent").count() == 1
    finally:
        db.close()
