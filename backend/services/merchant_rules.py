"""Merchant-rule engine: raw merchant string -> category + clean name.

Rules are tried highest ``priority`` first; the first match wins (spec 5).
"""

import re
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models.enums import MerchantMatchType
from backend.models.merchant_rule import MerchantRule


@dataclass(frozen=True)
class RuleMatch:
    rule_id: int
    category_id: int | None
    merchant_clean: str | None


def load_rules(db: Session) -> list[MerchantRule]:
    return list(
        db.execute(
            select(MerchantRule).order_by(
                MerchantRule.priority.desc(), MerchantRule.id
            )
        ).scalars()
    )


def match_merchant(
    rules: list[MerchantRule], merchant_raw: str | None
) -> RuleMatch | None:
    text = (merchant_raw or "").strip()
    if not text:
        return None
    for rule in rules:
        if rule.match_type == MerchantMatchType.contains:
            hit = rule.pattern.lower() in text.lower()
        else:
            try:
                hit = re.search(rule.pattern, text, re.IGNORECASE) is not None
            except re.error:
                hit = False
        if hit:
            return RuleMatch(rule.id, rule.category_id, rule.merchant_clean)
    return None


def bump_hit_counts(db: Session, rule_ids: Counter[int]) -> None:
    for rule_id, n in rule_ids.items():
        db.execute(
            update(MerchantRule)
            .where(MerchantRule.id == rule_id)
            .values(hit_count=MerchantRule.hit_count + n)
        )


_TRAILING_NOISE = re.compile(r"[\s#*]+\d[\d\s\-]*$")


def suggest_rule(merchant_raw: str) -> dict:
    """A starting point for 'create a rule from this merchant'."""
    cleaned = _TRAILING_NOISE.sub("", merchant_raw.strip())
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -*#")
    pretty = cleaned.title() if cleaned.isupper() or cleaned.islower() else cleaned
    return {
        "pattern": cleaned or merchant_raw.strip(),
        "match_type": MerchantMatchType.contains.value,
        "merchant_clean": pretty or None,
    }
