from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database import Base, get_db
from main import app
from security.token_manager import JWTAuthManager

SQLITE_DATABASE_URL = "sqlite:///:memory:"
sqlite_engine = create_engine(
    SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}
)
sqlite_connection = sqlite_engine.connect()
SqliteSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=sqlite_connection
)


@pytest.fixture(scope="function")
def db_session() -> Session:
    db = SqliteSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@contextmanager
def get_sqlite_db_contextmanager() -> Session:
    db = SqliteSessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_sqlite_database():
    with sqlite_connection.begin():
        Base.metadata.drop_all(bind=sqlite_connection)
        Base.metadata.create_all(bind=sqlite_connection)


@pytest.fixture(scope="function", autouse=True)
def reset_db(request):
    reset_sqlite_database()


@pytest.fixture(scope="function")
def jwt_manager(settings):
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )
