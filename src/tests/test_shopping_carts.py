import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from database import Movie, User, get_db
from main import app


@pytest.fixture(scope="session", autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        "SECRET_KEY_ACCESS": "test_secret_key_access",
        "SECRET_KEY_REFRESH": "test_secret_key_refresh",
        "STRIPE_SECRET_KEY": "test_stripe_secret_key",
        "STRIPE_PUBLIC_KEY": "test_stripe_public_key",
        "STRIPE_WEBHOOK_SECRET": "test_stripe_webhook_secret"
    }):
        yield


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def create_movie(db_session):
    movie = Movie(name="Test Movie", price=9.99)
    db_session.add(movie)
    db_session.commit()
    db_session.refresh(movie)
    return movie


@pytest.fixture
def create_user(db_session):
    user = User(email="testuser@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_get_cart_empty(client, auth_headers):
    response = client.get("/api/v1/cart/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["movies"] == []


def test_add_to_cart(client, auth_headers, create_movie):
    movie = create_movie
    response = client.post(
        "/api/v1/cart/add",
        json={"movie_id": movie.id},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert any(movie_item["id"] == movie.id for movie_item in response.json()["movies"])


def test_add_to_cart_duplicate(client, auth_headers, create_movie):
    movie = create_movie
    client.post("/api/v1/cart/add", json={"movie_id": movie.id}, headers=auth_headers)
    response = client.post(
        "/api/v1/cart/add",
        json={"movie_id": movie.id},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Movie is already in the cart"


def test_remove_from_cart(client, auth_headers, create_movie):
    movie = create_movie
    client.post("/api/v1/cart/add", json={"movie_id": movie.id}, headers=auth_headers)
    response = client.delete(f"/api/v1/cart/remove/{movie.id}", headers=auth_headers)
    assert response.status_code == 200


def test_remove_nonexistent_movie(client, auth_headers):
    response = client.delete("/api/v1/cart/remove/99999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not in cart"


def test_clear_cart(client, auth_headers, create_movie):
    movie = create_movie
    client.post("/api/v1/cart/add", json={"movie_id": movie.id}, headers=auth_headers)
    response = client.delete("/api/v1/cart/clear", headers=auth_headers)
    assert response.status_code == 200


def test_clear_empty_cart(client, auth_headers):
    response = client.delete("/api/v1/cart/clear", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart is already empty"


def test_checkout(client, auth_headers, create_movie):
    movie = create_movie
    client.post("/api/v1/cart/add", json={"movie_id": movie.id}, headers=auth_headers)
    response = client.post("/api/v1/cart/checkout", headers=auth_headers)
    assert response.status_code == 200


def test_checkout_empty_cart(client, auth_headers):
    response = client.post("/api/v1/cart/checkout", headers=auth_headers)
    assert response.status_code == 400


def test_checkout_inactive_user(client, auth_headers, create_movie):
    movie = create_movie
    response = client.post(
        "/api/v1/cart/add",
        json={"movie_id": movie.id},
        headers=auth_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == ("Please activate your "
                                         "account before making a purchase.")


def test_get_purchased_movies(client, auth_headers, create_movie):
    movie = create_movie
    client.post("/api/v1/cart/add", json={"movie_id": movie.id}, headers=auth_headers)
    client.post("/api/v1/cart/checkout", headers=auth_headers)
    response = client.get("/api/v1/cart/purchased", headers=auth_headers)
    assert response.status_code == 200
    assert movie.name in response.json()["purchased_movies"]


def test_get_user_cart_admin(client, auth_headers, create_movie, create_user):
    user = create_user
    movie = create_movie
    client.post("/api/v1/cart/add", json={"movie_id": movie.id}, headers=auth_headers)
    response = client.get(f"/api/v1/cart/admin/{user.id}", headers=auth_headers)
    assert response.status_code == 200
    user_cart_movies = response.json()["movies"]
    assert any(movie_item["id"] == movie.id for movie_item in user_cart_movies)


def test_delete_movie(client, auth_headers, create_movie):
    movie = create_movie
    response = client.delete(
        f"/api/v1/cart/admin/movies/{movie.id}",
        headers=auth_headers
    )
    assert response.status_code == 200


def test_delete_movie_not_found(client, auth_headers):
    response = client.delete("/api/v1/cart/admin/movies/99999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_admin_access_restricted(client, auth_headers, create_movie):
    movie = create_movie
    response = client.delete(
        f"/api/v1/cart/admin/movies/{movie.id}",
        headers=auth_headers
    )
    assert response.status_code in [403, 401]
