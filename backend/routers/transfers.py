from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.transfer import Transfer
from backend.schemas.transfer import (
    TransferCreate,
    TransferOut,
    TransferSummary,
)
from backend.services.transfers import (
    TransferInput,
    create_transfer,
    delete_transfer,
    summary,
)

router = APIRouter(
    prefix="/api/transfers", tags=["transfers"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[TransferOut])
def list_transfers(db: Session = Depends(get_db)) -> list[Transfer]:
    return list(
        db.execute(select(Transfer).order_by(Transfer.date.desc(), Transfer.id.desc()))
        .scalars()
    )


@router.get("/summary", response_model=TransferSummary)
def transfer_summary(db: Session = Depends(get_db)) -> dict:
    return summary(db)


@router.post(
    "",
    response_model=TransferOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(deny_in_demo)],
)
def create(body: TransferCreate, db: Session = Depends(get_db)) -> Transfer:
    return create_transfer(
        db,
        TransferInput(
            date=body.date,
            from_account_id=body.from_account_id,
            to_account_id=body.to_account_id,
            amount_out=body.amount_out,
            amount_in=body.amount_in,
            currency_out=body.currency_out,
            currency_in=body.currency_in,
            explicit_fee=body.explicit_fee,
            explicit_fee_currency=body.explicit_fee_currency,
            market_rate=body.market_rate,
            provider=body.provider,
            notes=body.notes,
        ),
    )


@router.delete(
    "/{transfer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete(transfer_id: int, db: Session = Depends(get_db)) -> None:
    transfer = db.get(Transfer, transfer_id)
    if transfer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "transfer not found")
    delete_transfer(db, transfer)
