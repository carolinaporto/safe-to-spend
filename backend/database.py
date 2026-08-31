from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from backend.config import get_settings

settings = get_settings()

# Serverless (Vercel) constraint: no connection pooling held between invocations.
# Neon does the pooling on its side via the -pooler host.
engine = create_engine(
    settings.sqlalchemy_url,
    poolclass=NullPool,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
