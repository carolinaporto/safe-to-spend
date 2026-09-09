"""Per-person balances and settlement (spec 4.3, 4.4)."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import (
    AccountKind,
    CategoryNature,
    TransactionDirection,
    TransactionKind,
)
from backend.models.expense_share import ExpenseShare
from backend.models.person import Person
from backend.models.transaction import Transaction
from backend.money import ONE, ZERO, money
from backend.services.fx import get_rate

_SHARE_SUM = func.coalesce(func.sum(ExpenseShare.share_amount_usd), 0)


@dataclass
class PersonBalance:
    person: Person
    owed_to_me_usd: Decimal
    i_owe_usd: Decimal
    net_usd: Decimal  # positive: they owe me; negative: I owe them


def _unsettled_shares(i_owe: bool, *columns):
    """Query over unsettled ExpenseShare rows in one direction.

    ``i_owe`` false: slices other people owe me (receivables).
    ``i_owe`` true: slices I owe someone (liabilities).
    """
    return select(*(columns or (ExpenseShare,))).where(
        ExpenseShare.settled.is_(False), ExpenseShare.i_owe.is_(i_owe)
    )


def _unsettled_total(db: Session, i_owe: bool) -> Decimal:
    return money(db.scalar(_unsettled_shares(i_owe, _SHARE_SUM)) or ZERO)


def people_balances(db: Session) -> list[PersonBalance]:
    def by_person(i_owe: bool) -> dict[int, Decimal]:
        stmt = _unsettled_shares(
            i_owe, ExpenseShare.person_id, _SHARE_SUM
        ).group_by(ExpenseShare.person_id)
        return dict(db.execute(stmt).all())

    owed = by_person(i_owe=False)
    i_owe = by_person(i_owe=True)
    people = db.execute(select(Person).order_by(Person.name)).scalars().all()
    out: list[PersonBalance] = []
    for person in people:
        a = money(owed.get(person.id, ZERO))
        b = money(i_owe.get(person.id, ZERO))
        if a == 0 and b == 0 and person.role.value == "me":
            continue
        out.append(
            PersonBalance(
                person=person,
                owed_to_me_usd=a,
                i_owe_usd=b,
                net_usd=money(a - b),
            )
        )
    return out


def total_receivables(db: Session) -> Decimal:
    return _unsettled_total(db, i_owe=False)


def total_liabilities(db: Session) -> Decimal:
    return _unsettled_total(db, i_owe=True)


def _usd_to_account(
    db: Session, amount_usd: Decimal, account: Account, on_date: dt.date
) -> tuple[Decimal, Decimal]:
    """(amount in the account's currency, fx_rate_to_usd)."""
    if account.currency.value == "USD":
        return money(amount_usd), ONE
    rate = get_rate(db, on_date, account.currency.value, "USD") or ONE
    native = money(amount_usd / rate) if rate else money(amount_usd)
    return native, rate


def settle_person(
    db: Session, person_id: int, account_id: int
) -> Transaction:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "person not found")
    account = db.get(Account, account_id)
    if account is None or account.kind == AccountKind.external:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "settle into one of your own accounts",
        )

    def shares_for(i_owe: bool) -> list[ExpenseShare]:
        stmt = _unsettled_shares(i_owe).where(
            ExpenseShare.person_id == person_id
        )
        return list(db.execute(stmt).scalars())

    receivable_shares = shares_for(i_owe=False)
    liability_shares = shares_for(i_owe=True)

    owed = money(sum((s.share_amount_usd for s in receivable_shares), ZERO))
    i_owe = money(sum((s.share_amount_usd for s in liability_shares), ZERO))
    net = money(owed - i_owe)
    if net == 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "nothing to settle"
        )

    today = dt.date.today()
    amount_usd = abs(net)
    native, rate = _usd_to_account(db, amount_usd, account, today)

    if net > 0:  # they pay me back
        reimb = db.execute(
            select(Category).where(
                Category.name == "Roommate reimbursement",
                Category.nature == CategoryNature.income,
            )
        ).scalar_one_or_none()
        settle_txn = Transaction(
            date=today,
            account_id=account.id,
            direction=TransactionDirection.in_,
            kind=TransactionKind.income,
            amount=native,
            currency=account.currency.value,
            fx_rate_to_usd=rate,
            amount_usd=amount_usd,
            category_id=reimb.id if reimb else None,
            merchant_clean=f"Settlement from {person.name}",
            description=f"Settled up with {person.name}",
        )
    else:  # I pay them back
        settle_txn = Transaction(
            date=today,
            account_id=account.id,
            direction=TransactionDirection.out,
            kind=TransactionKind.adjustment,
            amount=native,
            currency=account.currency.value,
            fx_rate_to_usd=rate,
            amount_usd=amount_usd,
            excluded_from_my_budget=True,
            merchant_clean=f"Settlement to {person.name}",
            description=f"Paid back {person.name}",
        )

    db.add(settle_txn)
    db.flush()
    for share in receivable_shares + liability_shares:
        share.settled = True
        share.settled_transaction_id = settle_txn.id
    db.commit()
    db.refresh(settle_txn)
    return settle_txn
