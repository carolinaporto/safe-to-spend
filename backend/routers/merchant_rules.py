from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.category import Category
from backend.models.merchant_rule import MerchantRule
from backend.schemas.merchant_rule import (
    MerchantRuleCreate,
    MerchantRuleOut,
    MerchantRuleUpdate,
    RuleSuggestion,
)
from backend.services.merchant_rules import suggest_rule

router = APIRouter(
    prefix="/api/merchant-rules",
    tags=["merchant-rules"],
    dependencies=[Depends(require_auth)],
)


def _check_category(db: Session, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown category_id"
        )


@router.get("", response_model=list[MerchantRuleOut])
def list_rules(db: Session = Depends(get_db)) -> list[MerchantRule]:
    return list(
        db.execute(
            select(MerchantRule).order_by(
                MerchantRule.priority.desc(), MerchantRule.id
            )
        ).scalars()
    )


@router.get("/suggest", response_model=RuleSuggestion)
def suggest(merchant_raw: str = Query(min_length=1)) -> RuleSuggestion:
    return RuleSuggestion(**suggest_rule(merchant_raw))


@router.post(
    "",
    response_model=MerchantRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(deny_in_demo)],
)
def create_rule(
    body: MerchantRuleCreate, db: Session = Depends(get_db)
) -> MerchantRule:
    _check_category(db, body.category_id)
    rule = MerchantRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch(
    "/{rule_id}",
    response_model=MerchantRuleOut,
    dependencies=[Depends(deny_in_demo)],
)
def update_rule(
    rule_id: int, body: MerchantRuleUpdate, db: Session = Depends(get_db)
) -> MerchantRule:
    rule = db.get(MerchantRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rule not found")
    data = body.model_dump(exclude_unset=True)
    if "category_id" in data:
        _check_category(db, data["category_id"])
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> None:
    rule = db.get(MerchantRule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "rule not found")
    db.delete(rule)
    db.commit()
