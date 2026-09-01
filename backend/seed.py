"""Seed the database with realistic fake data.

Idempotent: wipes the ledger tables and refills them. Safe to run repeatedly.

    python -m backend.seed

Cross-account movements are real linked transfers (two ledger legs plus an
FX-cost row). Rent is logged in full with the roommates' slices as
expense_shares, and a couple of purchases sit on Dad's external card as
"I owe it back" liabilities.
"""

import datetime as dt
import random
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.account import Account
from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.enums import (
    AccountKind,
    CategoryNature,
    Currency,
    MerchantMatchType,
    PersonRole,
    RecurringFrequency,
    TransactionDirection,
    TransactionKind,
    TransactionSource,
)
from backend.models.expense_share import ExpenseShare
from backend.models.fx_rate import FxRate
from backend.models.merchant_rule import MerchantRule
from backend.models.person import Person
from backend.models.plan_config import PLAN_CONFIG_ID, PlanConfig
from backend.models.recurring_rule import RecurringRule
from backend.models.transaction import Transaction
from backend.models.transfer import Transfer
from backend.money import money
from backend.reset import wipe_ledger
from backend.services.dates import add_months
from backend.services.fx import convert_to_usd
from backend.services.transfers import TransferInput, build_transfer

END = dt.date.today()
START = add_months(END, -3)  # ~4 months of history, ending today

PEOPLE = [
    ("You", PersonRole.me),
    ("Marina (roommate)", PersonRole.roommate),
    ("Theo (roommate)", PersonRole.roommate),
    ("Dad", PersonRole.parent),
]

ACCOUNTS = [
    # name, institution, kind, currency, opening_balance, color, statement_day, due_day
    ("Wise BRL", "Wise", AccountKind.checking, Currency.BRL, "20000.00", "#37517e", None, None),
    ("Wise USD", "Wise", AccountKind.checking, Currency.USD, "900.00", "#2f7d5b", None, None),
    ("Chase Checking", "Chase", AccountKind.checking, Currency.USD, "3200.00", "#117ac9", None, None),
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
    wipe_ledger(db)


def _seed_people(db: Session) -> dict[str, Person]:
    by_name: dict[str, Person] = {}
    for name, role in PEOPLE:
        person = Person(name=name, role=role)
        db.add(person)
        by_name[name] = person
    db.flush()
    return by_name


def _seed_accounts(
    db: Session, people: dict[str, Person]
) -> dict[str, Account]:
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
            owner_person_id=(
                people["Dad"].id if name == "Dad's Card" else None
            ),
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


MY_RENT_SHARE = Decimal("1300.00")


def _add_shared_rent(
    db: Session,
    day: dt.date,
    account: Account,
    cats: dict[str, Category],
    roommates: list[Person],
) -> None:
    """Full rent on my account; each roommate's third is an expense_share, so
    my reported spend is just my own slice."""
    full = MY_RENT_SHARE * (len(roommates) + 1)
    conversion = convert_to_usd(db, full, account.currency.value, day)
    txn = Transaction(
        date=day,
        account_id=account.id,
        kind=TransactionKind.expense,
        direction=TransactionDirection.out,
        amount=money(full),
        currency=account.currency.value,
        fx_rate_to_usd=conversion.rate,
        amount_usd=conversion.amount_usd,
        category_id=cats["Rent"].id,
        merchant_raw="BEACON ST APARTMENTS",
        merchant_clean="Beacon St Apartments",
        is_shared=True,
        source=TransactionSource.manual,
        shares=[
            ExpenseShare(person_id=mate.id, share_amount_usd=MY_RENT_SHARE)
            for mate in roommates
        ],
    )
    db.add(txn)


def _add_owe_purchase(
    db: Session,
    *,
    day: dt.date,
    account: Account,
    category: Category,
    amount: Decimal,
    merchant: str,
    owner: Person,
) -> None:
    """A purchase on someone else's card that I intend to pay back — counts
    as my spending and as a liability against the card's owner."""
    conversion = convert_to_usd(db, amount, account.currency.value, day)
    db.add(
        Transaction(
            date=day,
            account_id=account.id,
            kind=TransactionKind.expense,
            direction=TransactionDirection.out,
            amount=money(amount),
            currency=account.currency.value,
            fx_rate_to_usd=conversion.rate,
            amount_usd=conversion.amount_usd,
            category_id=category.id,
            merchant_raw=merchant.upper(),
            merchant_clean=merchant,
            source=TransactionSource.manual,
            shares=[
                ExpenseShare(
                    person_id=owner.id,
                    share_amount_usd=conversion.amount_usd,
                )
            ],
        )
    )


def _add_transfer(
    db: Session,
    *,
    day: dt.date,
    src: Account,
    dst: Account,
    amount_out: Decimal,
    amount_in: Decimal,
    provider: str,
) -> None:
    build_transfer(
        db,
        TransferInput(
            date=day,
            from_account_id=src.id,
            to_account_id=dst.id,
            amount_out=money(amount_out),
            amount_in=money(amount_in),
            provider=provider,
        ),
    )


def _seed_transactions(
    db: Session,
    acct: dict[str, Account],
    cats: dict[str, Category],
    people: dict[str, Person],
) -> None:
    rng = random.Random(7)
    roommates = [people["Marina (roommate)"], people["Theo (roommate)"]]

    # The year's grant lands as a lump sum in the Wise BRL account.
    _add_txn(
        db,
        day=START,
        account=acct["Wise BRL"],
        kind=TransactionKind.income,
        direction=TransactionDirection.in_,
        amount=Decimal("130000.00"),
        category=cats["Funding"],
        merchant="CAPES scholarship",
        notes="year's funding",
    )

    # Each month a chunk is converted to USD, and a small TA stipend comes in.
    for month in _months(START, END):
        stipend_day = month.replace(day=15)
        if START <= stipend_day <= END:
            _add_txn(
                db,
                day=stipend_day,
                account=acct["Chase Checking"],
                kind=TransactionKind.income,
                direction=TransactionDirection.in_,
                amount=Decimal("430.00"),
                category=cats["Work"],
                merchant="Harvard TA stipend",
            )

        fund_day = max(START, month.replace(day=2))
        if fund_day <= END:
            rate = convert_to_usd(db, Decimal("1"), "BRL", fund_day).rate
            brl_out = Decimal("14000.00")
            # Wise keeps a slice: land a touch less than the mid-market value.
            usd_in = (brl_out * rate * Decimal("0.992")).quantize(Decimal("0.01"))
            _add_transfer(
                db,
                day=fund_day,
                src=acct["Wise BRL"],
                dst=acct["Chase Checking"],
                amount_out=brl_out,
                amount_in=usd_in,
                provider="Wise",
            )

        rent_day = max(START, month.replace(day=1))
        if rent_day <= END and rent_day > START + dt.timedelta(days=1):
            _add_shared_rent(db, rent_day, acct["Chase Checking"], cats, roommates)

        atm_day = month.replace(day=6)
        if START <= atm_day <= END:
            _add_transfer(
                db,
                day=atm_day,
                src=acct["Chase Checking"],
                dst=acct["Cash"],
                amount_out=Decimal("220.00"),
                amount_in=Decimal("220.00"),
                provider="ATM",
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

    # A couple of things Dad put on his card that I owe back.
    for offset, (cat_name, merchant, amount) in enumerate(
        [
            ("Electronics", "Apple Store", "349.00"),
            ("Health/Insurance", "MIT Medical", "120.00"),
        ]
    ):
        day = START + dt.timedelta(days=20 + offset * 30)
        if day <= END:
            _add_owe_purchase(
                db,
                day=day,
                account=acct["Dad's Card"],
                category=cats[cat_name],
                amount=Decimal(amount),
                merchant=merchant,
                owner=people["Dad"],
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


def _seed_recurring_rules(
    db: Session, acct: dict[str, Account], cats: dict[str, Category]
) -> None:
    """Templates for the predictable monthly movements. History is already
    seeded, so last_generated_date is pinned to END — the cron job picks up
    from the next occurrence forward."""
    chase = acct["Chase Checking"]
    rows = [
        # name, category, amount, day_of_month, is_income
        ("Rent (my share)", "Rent", "1300.00", 1, False),
        ("Spotify", "Subscriptions", "11.99", 7, False),
        ("Netflix", "Subscriptions", "15.49", 12, False),
        ("Renters insurance", "Health/Insurance", "22.00", 5, False),
        ("Harvard TA stipend", "Work", "430.00", 15, True),
    ]
    for name, cat, amount, dom, is_income in rows:
        db.add(
            RecurringRule(
                name=name,
                account_id=chase.id,
                category_id=cats[cat].id,
                amount=Decimal(amount),
                currency=chase.currency.value,
                frequency=RecurringFrequency.monthly,
                day_of_month=dom,
                start_date=START,
                last_generated_date=END,
                is_income=is_income,
            )
        )
    db.flush()


MONTHLY_BUDGET = {
    None: "2600.00",  # global ceiling
    "Rent": "1300.00",
    "Groceries": "360.00",
    "Restaurants": "240.00",
    "Coffee": "70.00",
    "Bars": "90.00",
    "Transport": "80.00",
    "Utilities": "95.00",
    "Phone/Internet": "70.00",
    "Entertainment": "60.00",
    "Subscriptions": "35.00",
    "Clothing": "120.00",
}


def _seed_plan_config(db: Session) -> None:
    db.add(
        PlanConfig(
            id=PLAN_CONFIG_ID,
            academic_year_start=START,
            academic_year_end=add_months(END, 7).replace(day=20),
            emergency_reserve_usd=Decimal("1500.00"),
            committed_costs=[
                {
                    "label": "Spring break trip",
                    "amount_usd": "640.00",
                    "due_date": (END + dt.timedelta(days=52)).isoformat(),
                },
                {
                    "label": "Renters insurance renewal",
                    "amount_usd": "210.00",
                    "due_date": (END + dt.timedelta(days=88)).isoformat(),
                },
                {
                    "label": "Flight home",
                    "amount_usd": "780.00",
                    "due_date": (END + dt.timedelta(days=150)).isoformat(),
                },
            ],
        )
    )
    db.flush()


def _seed_budgets(db: Session, cats: dict[str, Category]) -> None:
    for month in _months(START, add_months(END, 1)):
        for name, amount in MONTHLY_BUDGET.items():
            db.add(
                Budget(
                    month=month.replace(day=1),
                    category_id=cats[name].id if name else None,
                    amount_usd=Decimal(amount),
                    rollover=name in {"Clothing", "Entertainment"},
                )
            )
    db.flush()


# pattern -> (category name, clean name)
MERCHANT_RULES = {
    "TRADER JOE": ("Groceries", "Trader Joe's"),
    "WHOLE FOODS": ("Groceries", "Whole Foods"),
    "STAR MARKET": ("Groceries", "Star Market"),
    "H MART": ("Groceries", "H Mart"),
    "BLUE BOTTLE": ("Coffee", "Blue Bottle"),
    "TATTE": ("Coffee", "Tatte"),
    "DUNKIN": ("Coffee", "Dunkin'"),
    "MBTA": ("Transport", "MBTA"),
    "BLUEBIKES": ("Transport", "Bluebikes"),
    "LYFT": ("Transport", "Lyft"),
    "COMCAST": ("Phone/Internet", "Comcast"),
    "EVERSOURCE": ("Utilities", "Eversource"),
    "NATIONAL GRID": ("Utilities", "National Grid"),
    "SPOTIFY": ("Subscriptions", "Spotify"),
    "NETFLIX": ("Subscriptions", "Netflix"),
    "CVS": ("Health/Insurance", "CVS Pharmacy"),
}


def _seed_merchant_rules(db: Session, cats: dict[str, Category]) -> None:
    for priority, (pattern, (cat_name, clean)) in enumerate(
        reversed(MERCHANT_RULES.items()), start=100
    ):
        db.add(
            MerchantRule(
                pattern=pattern,
                match_type=MerchantMatchType.contains,
                category_id=cats[cat_name].id,
                merchant_clean=clean,
                priority=priority,
            )
        )
    db.flush()


def seed() -> dict[str, int]:
    db = SessionLocal()
    try:
        _wipe(db)
        people = _seed_people(db)
        accounts = _seed_accounts(db, people)
        categories = _seed_categories(db)
        _seed_fx(db)
        _seed_transactions(db, accounts, categories, people)
        _seed_recurring_rules(db, accounts, categories)
        _seed_plan_config(db)
        _seed_budgets(db, categories)
        _seed_merchant_rules(db, categories)
        db.commit()
        return {
            "people": db.query(Person).count(),
            "accounts": db.query(Account).count(),
            "categories": db.query(Category).count(),
            "fx_rates": db.query(FxRate).count(),
            "transactions": db.query(Transaction).count(),
            "transfers": db.query(Transfer).count(),
            "expense_shares": db.query(ExpenseShare).count(),
            "recurring_rules": db.query(RecurringRule).count(),
            "budgets": db.query(Budget).count(),
            "merchant_rules": db.query(MerchantRule).count(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    for name, count in seed().items():
        print(f"{name:>13}: {count}")
