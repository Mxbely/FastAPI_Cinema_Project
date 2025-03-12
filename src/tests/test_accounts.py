import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from ..database.session_postgresql import get_postgresql_db
from unittest.mock import MagicMock

client = TestClient(app)


@pytest.fixture
def db_session():
    mock_db = MagicMock(spec=Session)
    yield mock_db


@pytest.fixture
def override_get_db(db_session):
    app.dependency_overrides[get_postgresql_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()


def test_register_user(override_get_db):
    response = client.post(
        "/register/",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert "email" in response.json()


def test_register_existing_user(override_get_db):
    client.post("/register/", json={"email": "test@example.com", "password": "password123"})
    response = client.post("/register/", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 409
    assert response.json()["detail"].startswith("A user with this email")


def test_activate_account(override_get_db):
    response = client.post(
        "/activate/",
        json={"email": "test@example.com", "token": "valid_token"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User account activated successfully."


def test_login_user(override_get_db):
    response = client.post(
        "/login/",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


def test_request_password_reset(override_get_db):
    response = client.post(
        "/password-reset/request/",
        json={"email": "test@example.com"}
    )
    assert response.status_code == 200
    assert "message" in response.json()


def test_refresh_access_token(override_get_db):
    response = client.post(
        "/refresh/",
        json={"refresh_token": "valid_refresh_token"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
