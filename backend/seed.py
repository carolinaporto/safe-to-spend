"""Seed the database with realistic fake data.

Idempotent: wipes the ledger tables and refills them. Safe to run repeatedly.

    python -m backend.seed

Note: transfers between accounts are modelled here as paired ``adjustment``
rows (money out of one account, money in to another at the day's FX rate).
Phase 4 replaces these with real linked transfers plus FX-cost tracking.
"""

import datetime as dt
import random
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import (
    AccountKind,
    CategoryNature,
    Currency,
    PersonRole,
    TransactionDirection,
    TransactionKind,
    TransactionSource,
)
from backend.models.fx_rate import FxRate
from backend.models.person import Person
from backend.models.transaction import Transaction
from backend.money import money
from backend.services.fx import convert_to_usd

def _months_back(date: dt.date, n: int) -> dt.date:
    """First day of the month ``n`` months before ``date``'s month."""
    month_index = date.year * 12 + (date.month - 1) - n
    return dt.date(month_index // 12, month_index % 12 + 1, 1)


END = dt.date.today()
START = _months_back(END, 3)  # ~4 months of history, ending today

PEOPLE = [
    ("You", PersonRole.me),
    ("Marina (roommate)", PersonRole.roommate),
    ("Theo (roommate)", PersonRole.roommate),
    ("Dad", PersonRole.parent),
]

ACCOUNTS = [
    # name, institution, kind, currency, opening_balance, color, statement_day, due_day
    ("Wise BRL", "Wise", AccountKind.checking, Currency.BRL, "9200.00", "#37517e", None, None),
    ("Wise USD", "Wise", AccountKind.checking, Currency.USD, "740.00", "#2f7d5b", None, None),
    ("Chase Checking", "Chase", AccountKind.checking, Currency.USD, "5100.00", "#117ac9", None, None),
    ("Amex", "American Express", AccountKind.credit_card, Currency.USD, "0.00", "#2e77bb", 3, 25),
    ("Macy's", "Macy's", AccountKind.credit_card, Currency.USD, "0.00", "#b3272d", 12, 5),
    ("Cash", "Cash", AccountKind.cash, Currency.USD, "160.00", "#6b7280", None, None),
    ("Dad's Card", "Dad", AccountKind.external, Currency.USD, "0.00", "#a371f7", None, None),
]

CATEGORIES: dict[CategoryNature, list[str]] = {
    CategoryNature.essential: [
        "Rent",
        "Groceries",
        "Utilities",
        "Transport",
        "Health/Insurance",
        "Phone/Internet",
        "Academic materials",
        "Laundry",
    ],
    CategoryNature.discretionary: [
        "Restaurants",
        "Bars",
        "Coffee",
        "Clothing",
        "Entertainment",
        "Travel",
        "Subscriptions",
        "Gifts",
    ],
    CategoryNature.setup: [
        "Furniture",
        "Kitchenware",
        "Bedding",
        "Deposit",
        "Electronics",
    ],
    CategoryNature.fee: [
        "Transfer fee",
        "FX spread",
        "Bank fee",
        "Foreign transaction fee",
    ],
    CategoryNature.income: [
        "Funding",
        "Roommate reimbursement",
        "Work",
        "Scholarship",
        "Refund",
    ],
}

# category -> (merchants, min, max, roughly-per-week frequency)
SPEND_PROFILE = {
    "Groceries": (["Trader Joe's", "Star Market", "H Mart", "Whole Foods"], 22, 78, 1.4),
    "Coffee": (["Blue Bottle", "Tatte", "Dunkin'", "Pavement Coffeehouse"], 4, 9, 2.6),
    "Restaurants": (["Sweetgreen", "Mala Project", "Life Alive", "Saloniki"], 14, 44, 1.1),
    "Bars": (["The Sevens", "Lamplighter", "Trina's"], 18, 48, 0.4),
    "Transport": (["MBTA", "Bluebikes", "Lyft"], 2, 24, 1.6),
    "Utilities": (["Eversource", "National Grid"], 38, 88, 0.1),
    "Phone/Internet": (["Comcast Xfinity", "Mint Mobile"], 30, 65, 0.22),
    "Health/Insurance": (["CVS Pharmacy", "MIT Medical"], 8, 38, 0.22),
    "Academic materials": (["MIT Press", "Amazon", "The Coop"], 12, 55, 0.3),
    "Laundry": (["CleanWash Laundromat"], 5, 11, 0.7),
    "Entertainment": (["AMC Boston Common", "Coolidge Corner", "Steam"], 9, 28, 0.35),
    "Subscriptions": (["Spotify", "Netflix", "iCloud"], 3, 16, 0.35),
    "Clothing": (["Uniqlo", "Nike", "Aritzia"], 20, 110, 0.25),
    "Gifts": (["Paper Source", "Bodega"], 15, 55, 0.14),
}

SETUP_PURCHASES = [
    ("Deposit", "Beacon St Apartments", "2850.00", "Chase Checking"),
    ("Furniture", "IKEA", "214.00", "Amex"),
    ("Kitchenware", "IKEA", "76.40", "Amex"),
    ("Bedding", "Target", "62.99", "Amex"),
    ("Electronics", "Best Buy", "119.00", "Amex"),
]


def _daterange(start: dt.date, end: dt.date):
    day = start
    while day <= end:
        yield day
        day += dt.timedelta(days=1)


def _months(start: dt.date, end: dt.date):
    month = start.replace(day=1)
    while month <= end:
        yield month
        month = (month.replace(day=28) + dt.timedelta(days=7)).replace(day=1)


def _wipe(db: Session) -> None:
    db.execute(delete(Transaction))
    db.execute(delete(FxRate))
    db.execute(delete(Account))
    db.execute(delete(Category))
    db.execute(delete(Person))
    db.flush()


def _seed_people(db: Session) -> None:
    db.add_all([Person(name=n, role=r) for n, r in PEOPLE])


def _seed_accounts(db: Session) -> dict[str, Account]:
    by_name: dict[str, Account] = {}
    for order, row in enumerate(ACCOUNTS):
        name, inst, kind, cur, opening, color, sday, dday = row
        account = Account(
            name=name,
            institution=inst,
            kind=kind,
            currency=cur,
            opening_balance=Decimal(opening),
            opening_date=START,
            color=color,
            statement_day=sday,
            due_day=dday,
            sort_order=order,
        )
        db.add(account)
        by_name[name] = account
    db.flush()
    return by_name


def _seed_categories(db: Session) -> dict[str, Category]:
    by_name: dict[str, Category] = {}
    for nature, names in CATEGORIES.items():
        for name in names:
            category = Category(name=name, nature=nature)
            db.add(category)
            by_name[name] = category
    db.flush()
    return by_name


def _seed_fx(db: Session) -> None:
    rng = random.Random(1)
    usd_brl = Decimal("5.15")
    for day in _daterange(START, END):
        usd_brl += Decimal(str(round(rng.uniform(-0.03, 0.03), 4)))
        usd_brl = max(Decimal("4.80"), min(Decimal("5.60"), usd_brl))
        brl_usd = (Decimal("1") / usd_brl).quantize(Decimal("0.00000001"))
        db.add(FxRate(date=day, base="USD", quote="BRL", rate=usd_brl, source="seed"))
        db.add(FxRate(date=day, base="BRL", quote="USD", rate=brl_usd, source="seed"))
    db.flush()


def _add_txn(
    db: Session,
    *,
    day: dt.date,
    account: Account,
    kind: TransactionKind,
    direction: TransactionDirection,
    amount: Decimal,
    category: Category | None = None,
    merchant: str,
    notes: str = "",
) -> None:
    conversion = convert_to_usd(db, amount, account.currency.value, day)
    db.add(
        Transaction(
            date=day,
            account_id=account.id,
            kind=kind,
            direction=direction,
            amount=money(amount),
            currency=account.currency.value,
            fx_rate_to_usd=conversion.rate,
            amount_usd=conversion.amount_usd,
            category_id=category.id if category else None,
            merchant_raw=merchant.upper(),
            merchant_clean=merchant,
            notes=notes,
            source=TransactionSource.manual,
        )
    )


def _seed_transactions(
    db: Session, acct: dict[str, Account], cats: dict[str, Category]
) -> None:
    rng = random.Random(7)

    for month in _months(START, END):
        fund_day = max(START, month.replace(day=2))
        if fund_day <= END:
            _add_txn(
                db,
                day=fund_day,
                account=acct["Wise BRL"],
                kind=TransactionKind.income,
                direction=TransactionDirection.in_,
                amount=Decimal("17500.00"),
                category=cats["Funding"],
                merchant="Family transfer",
            )
            # Convert most of it to USD (modelled as paired adjustments).
            rate = convert_to_usd(
                db, Decimal("1"), "BRL", fund_day
            ).rate
            brl_out = Decimal("15500.00")
            usd_in = (brl_out * rate).quantize(Decimal("0.01"))
            _add_txn(
                db,
                day=fund_day,
                account=acct["Wise BRL"],
                kind=TransactionKind.adjustment,
                direction=TransactionDirection.out,
                amount=brl_out,
                merchant="Wise conversion BRL->USD",
                notes="transfer leg (real transfers arrive in Phase 4)",
            )
            _add_txn(
                db,
                day=fund_day,
                account=acct["Chase Checking"],
                kind=TransactionKind.adjustment,
                direction=TransactionDirection.in_,
                amount=usd_in,
                merchant="Wise conversion BRL->USD",
                notes="transfer leg (real transfers arrive in Phase 4)",
            )

        rent_day = max(START, month.replace(day=1))
        if rent_day <= END and rent_day > START + dt.timedelta(days=1):
            _add_txn(
                db,
                day=rent_day,
                account=acct["Chase Checking"],
                kind=TransactionKind.expense,
                direction=TransactionDirection.out,
                amount=Decimal("2850.00"),
                category=cats["Rent"],
                merchant="Beacon St Apartments",
            )

        atm_day = month.replace(day=6)
        if START <= atm_day <= END:
            _add_txn(
                db,
                day=atm_day,
                account=acct["Chase Checking"],
                kind=TransactionKind.adjustment,
                direction=TransactionDirection.out,
                amount=Decimal("220.00"),
                merchant="ATM withdrawal",
            )
            _add_txn(
                db,
                day=atm_day,
                account=acct["Cash"],
                kind=TransactionKind.adjustment,
                direction=TransactionDirection.in_,
                amount=Decimal("220.00"),
                merchant="ATM withdrawal",
            )

    for offset, (cat_name, merchant, amount, account_name) in enumerate(SETUP_PURCHASES):
        day = START + dt.timedelta(days=1 + offset * 2)
        if day <= END:
            _add_txn(
                db,
                day=day,
                account=acct[account_name],
                kind=TransactionKind.expense,
                direction=TransactionDirection.out,
                amount=Decimal(amount),
                category=cats[cat_name],
                merchant=merchant,
            )

    card_accounts = [acct["Amex"], acct["Chase Checking"]]
    cash_on_hand = Decimal(ACCOUNTS[5][4])  # Cash opening balance
    atm_days = {m.replace(day=6) for m in _months(START, END)}

    for day in _daterange(START, END):
        if day in atm_days:
            cash_on_hand += Decimal("220.00")
        for cat_name, (merchants, lo, hi, per_week) in SPEND_PROFILE.items():
            if rng.random() > per_week / 7:
                continue
            amount = Decimal(str(round(rng.uniform(lo, hi), 2)))
            wants_cash = cat_name == "Laundry" or (
                cat_name in {"Coffee", "Transport"} and rng.random() < 0.5
            )
            if wants_cash and cash_on_hand - amount >= 0:
                account = acct["Cash"]
                cash_on_hand -= amount
            elif cat_name == "Clothing" and rng.random() < 0.6:
                account = acct["Macy's"]
            else:
                account = rng.choice(card_accounts)
            _add_txn(
                db,
                day=day,
                account=account,
                kind=TransactionKind.expense,
                direction=TransactionDirection.out,
                amount=amount,
                category=cats[cat_name],
                merchant=rng.choice(merchants),
            )

    db.flush()


def seed() -> dict[str, int]:
    db = SessionLocal()
    try:
        _wipe(db)
        _seed_people(db)
        accounts = _seed_accounts(db)
        categories = _seed_categories(db)
        _seed_fx(db)
        _seed_transactions(db, accounts, categories)
        db.commit()
        return {
            "people": db.query(Person).count(),
            "accounts": db.query(Account).count(),
            "categories": db.query(Category).count(),
            "fx_rates": db.query(FxRate).count(),
            "transactions": db.query(Transaction).count(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    for name, count in seed().items():
        print(f"{name:>13}: {count}")
