from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_auth
from backend.models.account import Account
from backend.money import ZERO, money_str
from backend.schemas.common import ApiModel, MoneyStr
from backend.services.balances import balance_in_usd, native_balances

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_auth)],
)


class AccountBalance(ApiModel):
    id: int
    name: str
    institution: str
    currency: str
    kind: str
    is_owned: bool
    balance: MoneyStr
    balance_usd: MoneyStr


class BalancesOut(ApiModel):
    net_worth_usd: MoneyStr
    accounts: list[AccountBalance]


@router.get("/balances", response_model=BalancesOut)
def balances(db: Session = Depends(get_db)) -> BalancesOut:
    native = native_balances(db)
    accounts = (
        db.execute(select(Account).order_by(Account.sort_order, Account.name))
        .scalars()
        .all()
    )

    rows: list[AccountBalance] = []
    net_worth = ZERO
    for account in accounts:
        native_balance = native.get(account.id, ZERO)
        usd = balance_in_usd(db, account.currency.value, native_balance)
        rows.append(
            AccountBalance(
                id=account.id,
                name=account.name,
                institution=account.institution,
                currency=account.currency.value,
                kind=account.kind.value,
                is_owned=account.is_owned,
                balance=native_balance,
                balance_usd=usd,
            )
        )
        if account.is_owned:
            net_worth += usd

    return BalancesOut(net_worth_usd=money_str(net_worth), accounts=rows)
