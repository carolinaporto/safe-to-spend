from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.account import Account
from backend.models.transaction import Transaction
from backend.schemas.account import AccountCreate, AccountOut, AccountUpdate
from backend.services.balances import balance_in_usd, native_balances

router = APIRouter(
    prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_auth)]
)


def _to_out(account: Account, native: dict[int, object], db: Session) -> AccountOut:
    balance = native.get(account.id)
    return AccountOut(
        **{c.name: getattr(account, c.name) for c in Account.__table__.columns},
        is_owned=account.is_owned,
        balance=balance,
        balance_usd=balance_in_usd(db, account.currency.value, balance),
    )


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[AccountOut]:
    accounts = (
        db.execute(select(Account).order_by(Account.sort_order, Account.name))
        .scalars()
        .all()
    )
    native = native_balances(db)
    return [_to_out(a, native, db) for a in accounts]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    body: AccountCreate, db: Session = Depends(get_db)
) -> AccountOut:
    account = Account(**body.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return _to_out(account, native_balances(db), db)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int, body: AccountUpdate, db: Session = Depends(get_db)
) -> AccountOut:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "account not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return _to_out(account, native_balances(db), db)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> None:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "account not found")
    referenced = db.execute(
        select(Transaction.id).where(Transaction.account_id == account_id).limit(1)
    ).first()
    if referenced is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "account has transactions; deactivate it instead",
        )
    db.delete(account)
    db.commit()
