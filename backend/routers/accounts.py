from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.account import Account
from backend.models.transaction import Transaction
from backend.schemas.account import AccountCreate, AccountOut, AccountUpdate
from backend.services.balances import AccountBalance, account_balances

router = APIRouter(
    prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_auth)]
)


_COMPUTED = {"is_owned", "balance", "balance_usd"}


def _out(row: AccountBalance) -> AccountOut:
    stored = {
        name: getattr(row.account, name)
        for name in AccountOut.model_fields
        if name not in _COMPUTED
    }
    return AccountOut(
        **stored,
        is_owned=row.account.is_owned,
        balance=row.native,
        balance_usd=row.usd,
    )


def _one(db: Session, account_id: int) -> AccountOut:
    for row in account_balances(db):
        if row.account.id == account_id:
            return _out(row)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "account not found")


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[AccountOut]:
    return [_out(row) for row in account_balances(db)]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    body: AccountCreate, db: Session = Depends(get_db)
) -> AccountOut:
    account = Account(**body.model_dump())
    db.add(account)
    db.commit()
    return _one(db, account.id)


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
    return _one(db, account_id)


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
