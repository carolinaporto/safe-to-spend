from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.enums import CategoryNature, MerchantMatchType
from backend.models.merchant_rule import MerchantRule
from backend.services.merchant_rules import (
    bump_hit_counts,
    load_rules,
    match_merchant,
    suggest_rule,
)


@pytest.fixture
def category(db: Session) -> Category:
    c = Category(name="Coffee", nature=CategoryNature.discretionary)
    db.add(c)
    db.flush()
    return c


def _rule(db, pattern, *, match_type=MerchantMatchType.contains, priority=100, cat=None):
    r = MerchantRule(
        pattern=pattern,
        match_type=match_type,
        priority=priority,
        category_id=cat.id if cat else None,
        merchant_clean=pattern.title(),
    )
    db.add(r)
    db.flush()
    return r


def test_contains_is_case_insensitive(db: Session, category: Category) -> None:
    _rule(db, "blue bottle", cat=category)
    match = match_merchant(load_rules(db), "SQ *BLUE BOTTLE COFFEE #4")
    assert match is not None
    assert match.category_id == category.id


def test_regex_match(db: Session, category: Category) -> None:
    _rule(db, r"^AMZN.*MKTP", match_type=MerchantMatchType.regex, cat=category)
    assert match_merchant(load_rules(db), "AMZN Mktp US*2X4TY") is not None
    assert match_merchant(load_rules(db), "WHOLE FOODS") is None


def test_higher_priority_wins(db: Session) -> None:
    food = Category(name="Groceries", nature=CategoryNature.essential)
    coffee = Category(name="Coffee", nature=CategoryNature.discretionary)
    db.add_all([food, coffee])
    db.flush()
    _rule(db, "MARKET", priority=10, cat=food)
    _rule(db, "STAR MARKET", priority=200, cat=coffee)
    match = match_merchant(load_rules(db), "STAR MARKET #12")
    assert match.category_id == coffee.id


def test_invalid_regex_is_skipped_not_raised(db: Session) -> None:
    _rule(db, "([", match_type=MerchantMatchType.regex)
    assert match_merchant(load_rules(db), "anything") is None


def test_bump_hit_counts(db: Session) -> None:
    r = _rule(db, "LYFT")
    bump_hit_counts(db, Counter({r.id: 3}))
    db.flush()
    db.refresh(r)
    assert r.hit_count == 3


def test_suggest_rule_strips_store_numbers() -> None:
    s = suggest_rule("TRADER JOE'S #201")
    assert s["pattern"] == "TRADER JOE'S"
    assert s["match_type"] == "contains"


def test_crud_via_api(
    api_client: TestClient, auth_headers: dict, category: Category
) -> None:
    created = api_client.post(
        "/api/merchant-rules",
        headers=auth_headers,
        json={
            "pattern": "BLUE BOTTLE",
            "category_id": category.id,
            "merchant_clean": "Blue Bottle",
        },
    )
    assert created.status_code == 201
    rule_id = created.json()["id"]

    listed = api_client.get("/api/merchant-rules", headers=auth_headers).json()
    assert listed[0]["pattern"] == "BLUE BOTTLE"

    api_client.patch(
        f"/api/merchant-rules/{rule_id}",
        headers=auth_headers,
        json={"priority": 250},
    )
    assert (
        api_client.get("/api/merchant-rules", headers=auth_headers).json()[0][
            "priority"
        ]
        == 250
    )

    assert (
        api_client.delete(
            f"/api/merchant-rules/{rule_id}", headers=auth_headers
        ).status_code
        == 204
    )


def test_create_blocked_in_demo(
    api_client: TestClient, auth_headers: dict, demo_mode
) -> None:
    resp = api_client.post(
        "/api/merchant-rules",
        headers=auth_headers,
        json={"pattern": "X"},
    )
    assert resp.status_code == 403
