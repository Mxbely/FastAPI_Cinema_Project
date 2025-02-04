from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager
from database import Genre, Star, get_db
from database.crud.movies import (
    filter_movies,
    get_all_genres,
    get_all_stars,
    get_detail_movies_by_id,
    get_favourite_movie,
    get_genre_by_id,
    get_genre_by_name,
    get_liked_movie,
    get_movie_by_id,
    get_movie_by_name,
    get_star_by_id,
    get_star_by_name,
    get_user_by_id,
    create_movie_post,
    rollback,
    movie_update,
    delete_instance,
    create_instance,
    commit_instance,
    toggle_favourites_and_likes_movie,
)
from database.models.movies import FavoriteMovie, MovieLike
from schemas.movies import (
    GenreResponseSchema,
    GenresSchema,
    MovieCreateSchema,
    MovieDetailSchema,
    MovieFavoriteResponseSchema,
    MovieLikeResponseSchema,
    MovieListItemSchema,
    MovieListResponseSchema,
    MovieSortEnum,
    MovieUpdateSchema,
    StarsResponseSchema,
    StarsSchema, DetailMessageSchema,
)
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface

router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    summary="Retrieve a paginated list of movies",
    description=(
            "<h3>Retrieve a paginated list of movies with optional filters.</h3>"
            "<p>This endpoint allows clients to fetch a paginated list of movies.</p>"
            "<p>Users can apply various filters, including:</p>"
            "<ul>"
            "<li><b>Movie name</b> (`name`)</li>"
            "<li><b>Year</b> (`year`)</li>"
            "<li><b>IMDB rating range</b> (`min_imdb`, `max_imdb`)</li>"
            "<li><b>Votes count range</b> (`min_votes`, `max_votes`)</li>"
            "<li><b>Price range</b> (`min_price`, `max_price`)</li>"
            "<li><b>Sorting</b> (`sort_by`)</li>"
            "</ul>"
            "<p>Pagination is controlled using the `page` "
            "and `per_page` parameters.</p>"
    ),
    responses={
        200: {
            "description": "A list of movies retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "movies": [
                            {
                                "id": 1,
                                "name": "Inception",
                                "year": 2010,
                                "time": 80,
                                "description": "Description of movie"
                            }
                        ],
                        "prev_page": None,
                        "next_page": "/movies/?page=2&per_page=10",
                        "total_pages": 5,
                        "total_items": 50
                    }
                }
            },
        },
        404: {
            "description": "No movies found matching the criteria.",
            "content": {
                "application/json": {
                    "example": {"detail": "No movies found."}
                }
            },
        },
    }
)
def get_movie_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)."),
        per_page: int = Query(10, ge=1, le=20, description="Number of items per page."),
        name: Optional[str] = Query(None, description="Filter movies by name."),
        year: Optional[int] = Query(None, description="Filter movies by release year."),
        min_imdb: Optional[float] = Query(None, description="Minimum IMDB rating."),
        max_imdb: Optional[float] = Query(None, description="Maximum IMDB rating."),
        min_votes: Optional[int] = Query(None, description="Minimum number of votes."),
        max_votes: Optional[int] = Query(None, description="Maximum number of votes."),
        min_price: Optional[float] = Query(None, description="Minimum movie price."),
        max_price: Optional[float] = Query(None, description="Maximum movie price."),
        sort_by: Optional[MovieSortEnum] = Query(
            None, description="Sort movies by criteria."
        ),
        db: Session = Depends(get_db),
) -> MovieListResponseSchema:
    """
    Retrieve a paginated list of movies with optional filters.

    This endpoint returns a paginated list of movies from the database.
    Clients can specify filtering and sorting options, as well as pagination parameters.

    **Filters available:**
    - `name`: Filter by movie name.
    - `year`: Filter by release year.
    - `min_imdb`, `max_imdb`: Set an IMDB rating range.
    - `min_votes`, `max_votes`: Filter by the number of votes.
    - `min_price`, `max_price`: Define a price range.
    - `sort_by`: Sort results based on specific attributes.

    **Pagination:**
    - `page` (default: 1) - Defines which page of results to return.
    - `per_page` (default: 10, max: 20) - Defines the number of movies per page.

    **Returns:**
    - A `MovieListResponseSchema` object containing:
      - A list of movies matching the criteria.
      - Links to `prev_page` and `next_page` (if applicable).
      - The total number of pages and total movies available.

    **Raises:**
    - `HTTPException 404`: If no movies match the filters or pagination parameters.

    :param page: The page number to retrieve (1-based index, must be >= 1).
    :param per_page: The number of items per page (between 1 and 20).
    :param name: Filter movies by name.
    :param year: Filter movies by release year.
    :param min_imdb: Minimum IMDB rating.
    :param max_imdb: Maximum IMDB rating.
    :param min_votes: Minimum number of votes.
    :param max_votes: Maximum number of votes.
    :param min_price: Minimum price.
    :param max_price: Maximum price.
    :param sort_by: Sorting criteria.
    :param db: The SQLAlchemy database session.

    :return: A `MovieListResponseSchema` containing paginated movie data.
    :rtype: MovieListResponseSchema
    """

    movies_filter = {
        "name": name, "year": year, "min_imdb": min_imdb, "max_imdb": max_imdb,
        "min_votes": min_votes, "max_votes": max_votes,
        "min_price": min_price, "max_price": max_price
    }

    filtered_movies = filter_movies(db, movies_filter, sort_by)

    total_items = len(filtered_movies)
    total_pages = (total_items + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    paginated_movies = filtered_movies[start:end]

    if not paginated_movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    return MovieListResponseSchema(
        movies=[
            MovieListItemSchema.model_validate(movie) for movie in paginated_movies
        ],
        prev_page=(
            f"/movies/?page={page - 1}&per_page={per_page}"
            if page > 1 else None
        ),
        next_page=(
            f"/movies/?page={page + 1}&per_page={per_page}"
            if page < total_pages else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Retrieve movie details by ID",
    description=(
            "<h3>Get detailed information about a specific movie by its unique ID.</h3>"
            "<p>This endpoint fetches all available details for a movie, including:</p>"
            "<ul>"
            "<li><b>Name</b></li>"
            "<li><b>Genre</b></li>"
            "<li><b>Director and cast</b></li>"
            "<li><b>IMDB rating</b></li>"
            "<li><b>Budget and revenue</b></li>"
            "<li><b>Release date</b></li>"
            "</ul>"
            "<p>If the movie with the given ID does not exist, a "
            "<b>404 Not Found</b> error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Movie details retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Inception",
                        "genre": ["Sci-Fi", "Thriller"],
                        "director": "Christopher Nolan",
                        "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
                        "imdb_rating": 8.8,
                        "budget": 160000000,
                        "revenue": 829895144,
                        "release_date": "2010-07-16"
                    }
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    }
)
def movie_detail(
        movie_id: int,
        db: Session = Depends(get_db),
) -> MovieDetailSchema:
    """
    Retrieve detailed information about a specific movie by its ID.

    This endpoint fetches full details about a movie,
    including its title, genre, director, cast, budget, revenue,
    and release date.

    **Parameters:**
    - `movie_id` (int, required): The unique identifier of the movie.
    - `db` (Session, required): SQLAlchemy database session (injected via dependency).

    **Returns:**
    - A `MovieDetailSchema` containing:
      - Movie name, genre, and director.
      - Cast list.
      - IMDB rating.
      - Budget and revenue details.
      - Release date.

    **Raises:**
    - `HTTPException 404`: If the movie with the given ID is not found.

    :param movie_id: The unique identifier of the movie.
    :param db: The SQLAlchemy database session.
    :return: A `MovieDetailSchema` containing movie details.
    :rtype: MovieDetailSchema
    """
    movie = get_detail_movies_by_id(db, movie_id)

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return MovieDetailSchema.model_validate(movie)


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    summary="Add a new movie",
    description=(
            "<h3>Create a new movie entry in the database.</h3>"
            "<p>This endpoint allows users to add a new movie with details such as:</p>"
            "<ul>"
            "<li><b>Name</b></li>"
            "<li><b>Release date</b></li>"
            "<li><b>Genres</b></li>"
            "<li><b>Actors</b></li>"
            "<li><b>Languages</b></li>"
            "<li><b>IMDB rating</b></li>"
            "<li><b>Budget and revenue</b></li>"
            "</ul>"
            "<p>Any related entities (genres, actors, languages) "
            "will be automatically created or linked if they already exist.</p>"
            "<p>If a movie with the same name already exists, a "
            "<b>409 Conflict</b> error is returned.</p>"
    ),
    responses={
        201: {
            "description": "Movie created successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 12,
                        "name": "The Matrix",
                        "release_date": "1999-03-31",
                        "genre": ["Sci-Fi", "Action"],
                        "actors": ["Keanu Reeves", "Laurence Fishburne"],
                        "languages": ["English"],
                        "imdb_rating": 8.7,
                        "budget": 63000000,
                        "revenue": 467222728
                    }
                }
            },
        },
        400: {
            "description": "Invalid input data.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        },
        409: {
            "description": "Movie with the given name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A movie with the name 'The Matrix' already exists."
                    }
                }
            },
        }
    },
    status_code=201
)
def create_movie(
        movie_data: MovieCreateSchema,
        db: Session = Depends(get_db)
) -> MovieDetailSchema:
    """
    Create a new movie entry in the database.

    This endpoint allows users to add a new movie with various
    attributes like name, release date, genres, actors, and languages.
    It automatically links or creates associated entities if they do not exist.

    **Parameters:**
    - `movie_data` (MovieCreateSchema, required):
    The movie data containing all necessary details.
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - A `MovieDetailSchema` object containing:
      - The created movie's name, release date, genres, actors, and languages.
      - IMDB rating, budget, and revenue.

    **Raises:**
    - `HTTPException 400`: If the input data is invalid.
    - `HTTPException 409`: If a movie with the same name already exists.

    :param movie_data: The data required to create a new movie.
    :param db: The SQLAlchemy database session.
    :return: A `MovieDetailSchema` containing the created movie details.
    :rtype: MovieDetailSchema
    """
    existing_movie = get_movie_by_name(db, movie_data)

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{movie_data.name}'"
            )
        )

    try:
        movie = create_movie_post(db, movie_data)

        return MovieDetailSchema.model_validate(movie)
    except HTTPException:
        rollback(db)
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.patch(
    "/movies/{movie_id}/",
    response_model=DetailMessageSchema,
    summary="Update a movie by ID",
    description=(
            "<h3>Modify details of a specific movie using its unique ID.</h3>"
            "<p>This endpoint allows updating partial details of an existing movie. "
            "Fields that are not provided in the request remain unchanged.</p>"
            "<p>If the movie with the given ID does not exist, "
            "a <b>404 Not Found</b> error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Movie updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie updated successfully."}
                }
            },
        },
        400: {
            "description": "Invalid input data.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        }
    }
)
def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: Session = Depends(get_db),
) -> DetailMessageSchema:
    """
    Update a specific movie by its unique ID.

    This function updates an existing movie with new details. Only the fields
    provided in the request will be modified; all others will remain unchanged.

    **Parameters:**
    - `movie_id` (int, required): The unique identifier of the movie to update.
    - `movie_data` (MovieUpdateSchema, required): The partial data to update.
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - A `DetailMessageSchema` response indicating the successful update.

    **Raises:**
    - `HTTPException 400`: If the input data is invalid.
    - `HTTPException 404`: If the movie with the given ID does not exist.

    :param movie_id: The ID of the movie to update.
    :param movie_data: The new data to update.
    :param db: The database session.
    :return: A success message.
    :rtype: DetailMessageSchema
    """
    movie = get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    try:
        movie_update(db, movie)
    except HTTPException:
        rollback(db)
        raise HTTPException(status_code=400, detail="Invalid input data.")
    else:
        return DetailMessageSchema(detail="Movie updated successfully.")


@router.delete(
    "/movies/{movie_id}/",
    summary="Delete a movie by ID",
    description=(
            "<h3>Remove a specific movie from the database using its unique ID.</h3>"
            "<p>This endpoint permanently deletes a movie if it exists.</p>"
            "<p>If the movie with the given ID is not found, a "
            "<b>404 Not Found</b> error is returned.</p>"
    ),
    responses={
        204: {
            "description": "Movie deleted successfully."
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    },
    status_code=204
)
def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a specific movie from the database by its unique ID.

    This function removes a movie from the database. If the movie does not exist,
    a 404 error is raised.

    **Parameters:**
    - `movie_id` (int, required): The unique identifier of the movie to delete.
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - No content (status code 204) on successful deletion.

    **Raises:**
    - `HTTPException 404`: If the movie with the given ID does not exist.

    :param movie_id: The ID of the movie to delete.
    :param db: The database session.
    :return: None.
    """
    movie = get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    delete_instance(db, movie)
    return


@router.post(
    "/stars/",
    description=(
        "<h3>Add a new star to the database.</h3>"
        "<p>This endpoint allows clients to create a new star "
        "(e.g., an actor or director). "
        "If a star with the given name already exists, a "
        "<b>400 Bad Request</b> error is returned.</p>"
    ),
    responses={
        201: {
            "description": "Star created successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Leonardo DiCaprio"
                    }
                }
            },
        },
        400: {
            "description": "Star already exists.",
            "content": {
                "application/json": {
                    "example": {"detail": "Star already exists."}
                }
            },
        },
    },
)
def create_star(
        stars_data: StarsSchema,
        db: Session = Depends(get_db),
) -> StarsResponseSchema:
    """
    Create a new star in the database.

    This function allows the creation of a new star (actor, director, etc.).
    If a star with the given name already exists, a 400 error is raised.

    **Parameters:**
    - `stars_data` (StarsSchema, required): The data required to create a new star.
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - `StarsResponseSchema`: The created star details.

    **Raises:**
    - `HTTPException 400`: If the star with the given name already exists.

    :param stars_data: The data of the star to create.
    :param db: The database session.
    :return: The created star object.
    """
    star = get_star_by_name(db, stars_data)
    if star:
        raise HTTPException(
            status_code=400,
            detail="Star already exists.",
        )

    star = Star(name=stars_data.name)
    create_instance(db, star)

    return StarsResponseSchema.model_validate(star)


@router.get(
    "/stars/",
    response_model=list[StarsResponseSchema],
    summary="Get a list of all stars",
    description=(
        "<h3>Retrieve a list of all stars in the database.</h3>"
        "<p>This endpoint returns a list of all stars stored in the database.</p>"
    ),
    responses={
        200: {
            "description": "List of all stars retrieved successfully.",
            "content": {
                "application/json": {
                    "example": [
                        {"id": 1, "name": "Leonardo DiCaprio"},
                        {"id": 2, "name": "Robert De Niro"},
                        {"id": 3, "name": "Meryl Streep"}
                    ]
                }
            },
        }
    }
)
def star_list(
        db: Session = Depends(get_db),
) -> list[Star]:
    """
    Retrieve a list of all stars.

    This function returns all stars (actors, directors, etc.) stored in the database.

    **Parameters:**
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - `list[StarsResponseSchema]`: A list of all stars.

    :param db: The database session.
    :return: A list of stars.
    """
    return cast(List[Star], get_all_stars(db))


@router.patch(
    "/stars/{star_id}/",
    summary="Update a star by ID",
    description=(
        "<h3>Update details of a specific star by its unique ID.</h3>"
        "<p>This endpoint allows updating the name of an existing star. "
        "If the star with the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Star updated successfully.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "name": "Updated Star Name"}
                }
            },
        },
        404: {
            "description": "Star not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Star with the given ID was not found."}
                }
            },
        },
    }
)
def star_update(
        star_id: int,
        star_data: StarsSchema,
        db: Session = Depends(get_db),
) -> StarsResponseSchema:
    """
    Update details of a specific star by its ID.

    This function updates the name of a star (actor, director, etc.)
    identified by its unique ID.
    If the star does not exist, a 404 error is raised.

    **Parameters:**
    - `star_id` (int, required): The unique identifier of the star to update.
    - `star_data` (StarsSchema, required): The updated data for the star.
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - `StarsResponseSchema`: The updated star data.

    **Raises:**
    - `HTTPException 404`: If the star is not found.

    :param star_id: The unique identifier of the star.
    :param star_data: The updated data for the star.
    :param db: The database session.
    :return: The updated star.
    """
    star = get_star_by_id(db, star_id)

    if not star:
        raise HTTPException(
            status_code=404,
            detail="Star with the given ID was not found."
        )

    if star_data.name:
        star.name = star_data.name

    return StarsResponseSchema.model_validate(star)


@router.delete(
    "/stars/{star_id}/",
    response_model=DetailMessageSchema,
    summary="Delete a star by ID",
    description=(
        "<h3>Delete a specific star from the database by its unique ID.</h3>"
        "<p>If the star exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        200: {
            "description": "Star deleted successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Star deleted successfully."}
                }
            },
        },
        404: {
            "description": "Star not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Star with the given ID was not found."}
                }
            },
        },
    },
)
def star_delete(
        star_id: int,
        db: Session = Depends(get_db),
) -> DetailMessageSchema:
    """
    Delete a specific star by its ID.

    This function deletes a star (actor, director, etc.) identified by its unique ID.
    If the star does not exist, a 404 error is raised.

    **Parameters:**
    - `star_id` (int, required): The unique identifier of the star to delete.
    - `db` (Session, required): SQLAlchemy database session
    (provided via dependency injection).

    **Returns:**
    - `DetailMessageSchema`: A response message confirming deletion.

    **Raises:**
    - `HTTPException 404`: If the star is not found.

    :param star_id: The unique identifier of the star.
    :param db: The database session.
    :return: A confirmation message that the star was deleted.
    """
    star = get_star_by_id(db, star_id)

    if not star:
        raise HTTPException(
            status_code=404,
            detail="Star with the given ID was not found."
        )

    delete_instance(db, star)
    return DetailMessageSchema(detail="Star deleted successfully.")


@router.post(
    "/genres/",
    summary="Create a new genre",
    description=(
        "<h3>Add a new genre to the database.</h3>"
        "<p>This endpoint allows clients to create a new genre. If the genre already "
        "exists, a 400 error is returned.</p>"
    ),
    responses={
        201: {
            "description": "Genre created successfully.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "name": "Action"}
                }
            },
        },
        400: {
            "description": "Genre already exists.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre already exists."}
                }
            },
        },
    },
)
def create_genre(
        genres_data: GenresSchema,
        db: Session = Depends(get_db),
) -> GenreResponseSchema:
    """
    Create a new genre.

    This function allows adding a new genre to the database.
    If a genre with the same name already exists, it returns a 400 error.

    **Parameters:**
    - `genres_data` (GenresSchema, required): The data required to create a genre.
    - `db` (Session, required): SQLAlchemy database session.

    **Returns:**
    - `GenreResponseSchema`: The created genre with its details.

    **Raises:**
    - `HTTPException 400`: If the genre already exists.

    :param genres_data: The genre data to create.
    :param db: The database session.
    :return: The created genre.
    """

    genre = get_genre_by_name(db, genres_data)
    if genre:
        raise HTTPException(
            status_code=400,
            detail="Genre already exists.",
        )

    genre = Genre(name=genres_data.name)
    create_instance(db, genre)

    return GenreResponseSchema.model_validate(genre)


@router.get(
    "/genres/",
    response_model=list[GenreResponseSchema],
    summary="Get a list of all genres",
    description=(
        "<h3>Retrieve all genres from the database.</h3>"
        "<p>This endpoint returns a list of all available genres.</p>"
    ),
    responses={
        200: {
            "description": "List of genres retrieved successfully.",
            "content": {
                "application/json": {
                    "example": [
                        {"id": 1, "name": "Action"},
                        {"id": 2, "name": "Comedy"},
                        {"id": 3, "name": "Drama"}
                    ]
                }
            },
        }
    }
)
def genre_list(
        db: Session = Depends(get_db),
) -> list[Genre]:
    """
    Retrieve a list of all genres.

    This function returns a list of all genres stored in the database.

    **Returns:**
    - `list[GenreResponseSchema]`: A list of genres.

    :param db: The database session.
    :return: A list of all genres.
    """
    return cast(List[Genre], get_all_genres(db))


@router.get(
    "/genres/{genre_id}/",
    summary="Get details of a specific genre",
    description=(
        "<h3>Retrieve details of a genre by its unique ID.</h3>"
        "<p>This endpoint returns detailed information about a specific genre.</p>"
    ),
    responses={
        200: {
            "description": "Genre details retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "name": "Action"}
                }
            },
        },
        404: {
            "description": "Genre not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre with the given ID was not found."}
                }
            },
        },
    }
)
def genre_detail(
        genre_id: int,
        db: Session = Depends(get_db),
) -> GenreResponseSchema:
    """
    Retrieve details of a specific genre by ID.

    This function returns details about a genre stored in the database.

    **Parameters:**
    - `genre_id` (int): The unique identifier of the genre.

    **Returns:**
    - `GenreResponseSchema`: The genre details.

    **Raises:**
    - `HTTPException 404`: If the genre is not found.
    """
    genre = get_genre_by_id(db, genre_id)

    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre with the given ID was not found."
        )

    return GenreResponseSchema.model_validate(genre)


@router.patch(
    "/genres/{genre_id}/",
    summary="Update a genre by ID",
    description=(
        "<h3>Update details of a specific genre by its unique ID.</h3>"
        "<p>This endpoint allows updating the name of an existing genre.</p>"
    ),
    responses={
        200: {
            "description": "Genre updated successfully.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "name": "Adventure"}
                }
            },
        },
        404: {
            "description": "Genre not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre with the given ID was not found."}
                }
            },
        },
    }
)
def genre_update(
        genre_id: int,
        genre_data: GenresSchema,
        db: Session = Depends(get_db),
) -> GenreResponseSchema:
    """
    Update details of a specific genre by ID.

    **Parameters:**
    - `genre_id` (int): The unique identifier of the genre.
    - `genre_data` (GenresSchema): The updated genre data.

    **Returns:**
    - `GenreResponseSchema`: The updated genre details.

    **Raises:**
    - `HTTPException 404`: If the genre with the given ID is not found.
    """
    genre = get_genre_by_id(db, genre_id)

    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre with the given ID was not found."
        )

    if genre_data.name:
        genre.name = genre_data.name

    return GenreResponseSchema.model_validate(genre)


@router.delete(
    "/genres/{genre_id}/",
    response_model=DetailMessageSchema,
    summary="Delete a genre by ID",
    description=(
        "<h3>Delete a specific genre from the database by its unique ID.</h3>"
        "<p>If the genre exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        200: {
            "description": "Genre deleted successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre deleted successfully."}
                }
            },
        },
        404: {
            "description": "Genre not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre with the given ID was not found."}
                }
            },
        },
    }
)
def genre_delete(
        genre_id: int,
        db: Session = Depends(get_db),
) -> DetailMessageSchema:
    """
    Delete a specific genre by ID.

    **Parameters:**
    - `genre_id` (int): The unique identifier of the genre.

    **Returns:**
    - `DetailMessageSchema`: A message confirming the deletion.

    **Raises:**
    - `HTTPException 404`: If the genre with the given ID is not found.
    """
    genre = get_genre_by_id(db, genre_id)

    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre with the given ID was not found."
        )

    delete_instance(db, genre)
    return DetailMessageSchema(detail="Genre deleted successfully.")


@router.post(
    "/{movie_id}/like/",
    response_model=MovieLikeResponseSchema,
    summary="Like or dislike a movie",
    description=(
        "<h3>Toggle like or dislike for a movie by its unique ID.</h3>"
        "<p>If the user has already liked the movie, this action will remove the like. "
        "If the movie was not liked before, this action will add a like.</p>"
    ),
    responses={
        200: {
            "description": "Movie like status updated.",
            "content": {
                "application/json": {
                    "example": {
                        "is_liked": True,
                        "created_at": "2024-02-03T12:34:56",
                        "user": {
                            "id": 1,
                            "username": "john_doe"
                        },
                        "movie": {
                            "id": 10,
                            "name": "Inception"
                        }
                    }
                }
            },
        },
        404: {
            "description": "Movie or user not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        401: {
            "description": "Unauthorized access.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired token."}
                }
            },
        },
    }
)
def like_or_dislike(
        movie_id: int,
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db),
) -> MovieLikeResponseSchema:
    """
    Toggle like or dislike for a specific movie.

    **Parameters:**
    - `movie_id` (int): The unique identifier of the movie.
    - `token` (str): User authentication token.

    **Returns:**
    - `MovieLikeResponseSchema`: The updated like status and associated movie/user info.

    **Raises:**
    - `HTTPException 404`: If the movie or user is not found.
    - `HTTPException 401`: If the token is invalid or expired.
    """
    movie = get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )
    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]
    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    movie_like = get_liked_movie(db, movie, user)

    if movie_like:
        movie_like.is_liked = not movie_like.is_liked
    else:
        movie_like = MovieLike(
            user_id=user_id,
            movie_id=movie_id,
            is_liked=True,
        )
        toggle_favourites_and_likes_movie(db, movie_like)

    commit_instance(db, movie_like)

    return MovieLikeResponseSchema(
        is_liked=movie_like.is_liked,
        created_at=movie_like.created_at,
        user=movie_like.user,
        movie=movie_like.movie,
    )


@router.post(
    "/{movie_id}/favorite/",
    response_model=MovieFavoriteResponseSchema,
    summary="Add or remove a movie from favorites",
    description=(
        "<h3>Toggle favorite status for a movie by its unique ID.</h3>"
        "<p>If the user has already added the movie to favorites, "
        "this action will remove it. "
        "If the movie was not in favorites before, this action will add it.</p>"
    ),
    responses={
        200: {
            "description": "Movie favorite status updated.",
            "content": {
                "application/json": {
                    "example": {
                        "is_favorited": True,
                        "created_at": "2024-02-03T12:34:56",
                        "user": {
                            "id": 1,
                            "username": "john_doe"
                        },
                        "movie": {
                            "id": 10,
                            "name": "Inception"
                        }
                    }
                }
            },
        },
        404: {
            "description": "Movie or user not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
        401: {
            "description": "Unauthorized access.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired token."}
                }
            },
        },
    }
)
def favorite_or_unfavorite(
        movie_id: int,
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db),
) -> MovieFavoriteResponseSchema:
    """
    Toggle favorite status for a specific movie.

    **Parameters:**
    - `movie_id` (int): The unique identifier of the movie.
    - `token` (str): User authentication token.

    **Returns:**
    - `MovieFavoriteResponseSchema`: The updated favorite status
       and associated movie/user info.

    **Raises:**
    - `HTTPException 404`: If the movie or user is not found.
    - `HTTPException 401`: If the token is invalid or expired.
    """
    movie = get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]
    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    movie_favorite = get_favourite_movie(db, movie, user)

    if movie_favorite:
        movie_favorite.is_favorited = not movie_favorite.is_favorited

    else:
        movie_favorite = FavoriteMovie(
            user_id=user_id,
            movie_id=movie_id,
            is_favorited=True,
        )
        toggle_favourites_and_likes_movie(db, movie_favorite)

    commit_instance(db, movie_favorite)

    return MovieFavoriteResponseSchema(
        is_favorited=movie_favorite.is_favorited,
        created_at=movie_favorite.created_at,
        user=movie_favorite.user,
        movie=movie_favorite.movie,
    )
