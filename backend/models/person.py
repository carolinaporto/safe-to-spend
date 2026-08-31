from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models.enums import PersonRole, pg_enum


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[PersonRole] = mapped_column(pg_enum(PersonRole))
    notes: Mapped[str] = mapped_column(Text, default="")
