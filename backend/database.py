from collections.abc import Iterator

from sqlalchemy import create_engine, event
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


@event.listens_for(engine, "connect")
def _pin_search_path(dbapi_connection, _record) -> None:
    """Force ``search_path`` to ``public`` on every new connection.

    Neon's connection pooler does not carry the role's default search_path,
    so without this the app's unqualified table names fail to resolve.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET search_path TO public")
    finally:
        cursor.close()
    dbapi_connection.commit()

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
