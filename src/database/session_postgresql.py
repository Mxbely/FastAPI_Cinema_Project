from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

settings = get_settings()

POSTGRESQL_DATABASE_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:{settings.POSTGRES_DB_PORT}/{settings.POSTGRES_DB}"
)
postgresql_engine = create_engine(POSTGRESQL_DATABASE_URL)
PostgresqlSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=postgresql_engine
)


def get_postgresql_db() -> PostgresqlSessionLocal:
    db = PostgresqlSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_postgresql_db_contextmanager() -> PostgresqlSessionLocal:
    db = PostgresqlSessionLocal()
    try:
        yield db
    finally:
        db.close()
