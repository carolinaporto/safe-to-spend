from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.enums import MerchantMatchType, pg_enum


class MerchantRule(Base):
    """Maps a raw merchant string to a category and a clean name during import
    and (optionally) live re-categorisation. Highest ``priority`` wins."""

    __tablename__ = "merchant_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(Text)
    match_type: Mapped[MerchantMatchType] = mapped_column(
        pg_enum(MerchantMatchType)
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    merchant_clean: Mapped[str | None] = mapped_column(String(120))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
