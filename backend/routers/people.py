from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.person import Person
from backend.schemas.person import (
    PersonBalanceOut,
    PersonCreate,
    PersonOut,
    PersonUpdate,
    SettleRequest,
)
from backend.schemas.transaction import TransactionOut
from backend.services.people import people_balances, settle_person

router = APIRouter(
    prefix="/api/people", tags=["people"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[PersonOut])
def list_people(db: Session = Depends(get_db)) -> list[Person]:
    return list(
        db.execute(select(Person).order_by(Person.name)).scalars()
    )


@router.get("/balances", response_model=list[PersonBalanceOut])
def balances(db: Session = Depends(get_db)) -> list[PersonBalanceOut]:
    return [
        PersonBalanceOut(
            person_id=b.person.id,
            name=b.person.name,
            role=b.person.role,
            owed_to_me_usd=b.owed_to_me_usd,
            i_owe_usd=b.i_owe_usd,
            net_usd=b.net_usd,
        )
        for b in people_balances(db)
    ]


@router.post(
    "",
    response_model=PersonOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(deny_in_demo)],
)
def create_person(body: PersonCreate, db: Session = Depends(get_db)) -> Person:
    person = Person(**body.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.patch(
    "/{person_id}",
    response_model=PersonOut,
    dependencies=[Depends(deny_in_demo)],
)
def update_person(
    person_id: int, body: PersonUpdate, db: Session = Depends(get_db)
) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "person not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete_person(person_id: int, db: Session = Depends(get_db)) -> None:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "person not found")
    db.delete(person)
    db.commit()


@router.post(
    "/{person_id}/settle",
    response_model=TransactionOut,
    dependencies=[Depends(deny_in_demo)],
)
def settle(
    person_id: int, body: SettleRequest, db: Session = Depends(get_db)
):
    return settle_person(db, person_id, body.account_id)
