from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[StrEnum]) -> SAEnum:
    """A VARCHAR-backed enum column that stores the enum *value*.

    ``native_enum=False`` keeps migrations simple (no ALTER TYPE); the
    ``values_callable`` makes SQLAlchemy persist ``member.value`` rather than
    ``member.name`` (which matters for e.g. ``in`` vs the ``in_`` member name).
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda cls: [m.value for m in cls],
    )


class AccountKind(StrEnum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    cash = "cash"
    external = "external"


class Currency(StrEnum):
    USD = "USD"
    BRL = "BRL"


class CategoryNature(StrEnum):
    essential = "essential"
    discretionary = "discretionary"
    setup = "setup"
    fee = "fee"
    income = "income"


class TransactionDirection(StrEnum):
    in_ = "in"
    out = "out"


class TransactionKind(StrEnum):
    expense = "expense"
    income = "income"
    transfer = "transfer"
    adjustment = "adjustment"


class TransactionSource(StrEnum):
    manual = "manual"
    csv = "csv"
    api = "api"


class PersonRole(StrEnum):
    me = "me"
    roommate = "roommate"
    parent = "parent"
    other = "other"


class MerchantMatchType(StrEnum):
    contains = "contains"
    regex = "regex"
