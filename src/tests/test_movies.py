import pytest
from httpx import AsyncClient
from main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_movies(client):
    response = await client.get("/movies/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_movie(client):
    movie_data = {
        "title": "Test Movie",
        "description": "Test Description",
        "release_year": 2024,
        "rating": 8.5,
        "genre_ids": [],
        "actor_ids": []
    }
    response = await client.post("/movies/", json=movie_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == movie_data["title"]
    assert "id" in data


@pytest.mark.asyncio
async def test_get_movie_by_id(client):
    movie_data = {
        "title": "Sample Movie",
        "description": "Sample Description",
        "release_year": 2024,
        "rating": 7.8,
        "genre_ids": [],
        "actor_ids": []
    }
    create_response = await client.post("/movies/", json=movie_data)
    movie_id = create_response.json()["id"]

    response = await client.get(f"/movies/{movie_id}")
    assert response.status_code == 200
    assert response.json()["id"] == movie_id


@pytest.mark.asyncio
async def test_update_movie(client):
    movie_data = {
        "title": "Old Title",
        "description": "Old Description",
        "release_year": 2020,
        "rating": 6.0,
        "genre_ids": [],
        "actor_ids": []
    }
    create_response = await client.post("/movies/", json=movie_data)
    movie_id = create_response.json()["id"]

    update_data = {"title": "New Title"}
    response = await client.patch(f"/movies/{movie_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_movie(client):
    movie_data = {
        "title": "To Be Deleted",
        "description": "Will be removed",
        "release_year": 2021,
        "rating": 5.5,
        "genre_ids": [],
        "actor_ids": []
    }
    create_response = await client.post("/movies/", json=movie_data)
    movie_id = create_response.json()["id"]

    delete_response = await client.delete(f"/movies/{movie_id}")
    assert delete_response.status_code == 204

    response = await client.get(f"/movies/{movie_id}")
    assert response.status_code == 404
