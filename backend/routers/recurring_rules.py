import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth, require_cron_secret
from backend.models.account import Account
from backend.models.category import Category
from backend.models.recurring_rule import RecurringRule
from backend.schemas.recurring_rule import (
    RecurringRuleCreate,
    RecurringRuleOut,
    RecurringRuleUpdate,
)
from backend.services.recurring import generate_due, generate_for_rule

router = APIRouter(tags=["recurring-rules"])

rules_router = APIRouter(
    prefix="/api/recurring-rules", dependencies=[Depends(require_auth)]
)


def _validate_refs(db: Session, account_id: int | None, category_id: int | None):
    if account_id is not None and db.get(Account, account_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown account_id"
        )
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown category_id"
        )


@rules_router.get("", response_model=list[RecurringRuleOut])
def list_rules(db: Session = Depends(get_db)) -> list[RecurringRule]:
    return list(
        db.execute(
            select(RecurringRule).order_by(RecurringRule.name)
        ).scalars()
    )


@rules_router.post(
    "",
    response_model=RecurringRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(deny_in_demo)],
)
def create_rule(
    body: RecurringRuleCreate, db: Session = Depends(get_db)
) -> RecurringRule:
    _validate_refs(db, body.account_id, body.category_id)
    rule = RecurringRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@rules_router.patch(
    "/{rule_id}",
    response_model=RecurringRuleOut,
    dependencies=[Depends(deny_in_demo)],
)
def update_rule(
    rule_id: int, body: RecurringRuleUpdate, db: Session = Depends(get_db)
) -> RecurringRule:
    rule = db.get(RecurringRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rule not found")
    data = body.model_dump(exclude_unset=True)
    _validate_refs(db, data.get("account_id"), data.get("category_id"))
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@rules_router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> None:
    rule = db.get(RecurringRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rule not found")
    db.delete(rule)
    db.commit()


@rules_router.post("/{rule_id}/run", dependencies=[Depends(deny_in_demo)])
def run_rule(rule_id: int, db: Session = Depends(get_db)) -> dict:
    rule = db.get(RecurringRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rule not found")
    created = generate_for_rule(db, rule, dt.date.today())
    db.commit()
    return {"generated": created}


@router.post(
    "/api/cron/generate-recurring",
    dependencies=[Depends(require_cron_secret)],
)
def cron_generate(db: Session = Depends(get_db)) -> dict:
    return generate_due(db)


router.include_router(rules_router)
