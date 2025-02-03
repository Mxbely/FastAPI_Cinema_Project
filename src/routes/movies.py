from typing import List
from urllib.request import Request

from fastapi import APIRouter, Query, Depends, HTTPException, requests
from sqlalchemy.orm import Session, joinedload

from config import get_jwt_auth_manager
from database import get_db, Movie, Certification, Genre, Star, Director
from database.crud.movies import get_movies_paginated
from database.models.accounts import TokenBase, User
from database.models.movies import MovieLike, FavoriteMovie
from schemas.movies import MovieListResponseSchema, MovieListItemSchema, MovieDetailSchema, MovieCreateSchema, \
    MovieUpdateSchema, StarsSchema, StarsResponseSchema, \
    GenresSchema, GenreResponseSchema, MovieLikeResponseSchema, MovieFavoriteResponseSchema
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface

router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of movies",
    description=(
            "<h3>This endpoint retrieves a paginated list of movies from the database. "
            "Clients can specify the `page` number and the number of items per page using `per_page`. "
            "The response includes details about the movies, total pages, and total items, "
            "along with links to the previous and next pages if applicable.</h3>"
    ),
    responses={
        404: {
            "description": "No movies found.",
            "content": {
                "application/json": {
                    "example": {"detail": "No movies found."}
                }
            },
        }
    }
)
def movie_list(
        page: int = Query(1, ge=1, description="Page number (1-based index)"),
        per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
        db: Session = Depends(get_db),
) -> MovieListResponseSchema:
    """
    Fetch a paginated list of movies from the database.

    This function retrieves a paginated list of movies, allowing the client to specify
    the page number and the number of items per page. It calculates the total pages
    and provides links to the previous and next pages when applicable.

    :param page: The page number to retrieve (1-based index, must be >= 1).
    :type page: int
    :param per_page: The number of items to display per page (must be between 1 and 20).
    :type per_page: int
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: Session

    :return: A response containing the paginated list of movies and metadata.
    :rtype: MovieListResponseSchema

    :raises HTTPException: Raises a 404 error if no movies are found for the requested page.
    """
    total_items, movies = get_movies_paginated(page, per_page, db)

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    movie_list = [
        MovieListItemSchema.model_validate(movie)
        for movie in movies
    ]

    total_pages = (total_items + per_page - 1) // per_page

    return MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/cinema/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details by ID",
    description=(
            "<h3>Fetch detailed information about a specific movie by its unique ID. "
            "This endpoint retrieves all available details for the movie, such as "
            "its name, genre, crew, budget, and revenue. If the movie with the given "
            "ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
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
def movie_detail(
        movie_id: int,
        db: Session = Depends(get_db),
) -> MovieDetailSchema:
    """
    Retrieve detailed information about a specific movie by its ID.

    This function fetches detailed information about a movie identified by its unique ID.
    If the movie does not exist, a 404 error is returned.

    :param movie_id: The unique identifier of the movie to retrieve.
    :type movie_id: int
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: Session

    :return: The details of the requested movie.
    :rtype: MovieDetailResponseSchema

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.
    """
    movie = (
        db.query(Movie)
        .options(
            joinedload(Movie.certification),
            joinedload(Movie.genres),
            joinedload(Movie.stars),
            joinedload(Movie.directors),
        )
        .filter(Movie.id == movie_id)
        .first()
    )

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
            "<h3>This endpoint allows clients to add a new movie to the database. "
            "It accepts details such as name, date, genres, actors, languages, and "
            "other attributes. The associated country, genres, actors, and languages "
            "will be created or linked automatically.</h3>"
    ),
    responses={
        201: {
            "description": "Movie created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
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
    Add a new movie to the database.

    This endpoint allows the creation of a new movie with details such as
    name, release date, genres, actors, and languages. It automatically
    handles linking or creating related entities.

    :param movie_data: The data required to create a new movie.
    :type movie_data: MovieCreateSchema
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: Session

    :return: The created movie with all details.
    :rtype: MovieDetailSchema

    :raises HTTPException: Raises a 400 error for invalid input.
    """
    existing_movie = db.query(Movie).filter(
        Movie.name == movie_data.name
    ).first()

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie_data.name}' and release date '{movie_data.date}' already exists."
        )

    try:
        certification = db.query(Certification).filter_by(name=movie_data.certification).first()
        if not certification:
            certification = Certification(name=movie_data.certification)
            db.add(certification)
            db.commit()
            db.refresh(certification)

        genres = []
        for genre_name in movie_data.genres:
            genre = db.query(Genre).filter_by(name=genre_name).first()
            if not genre:
                genre = Genre(name=genre_name)
                db.add(genre)
                db.flush()
            genres.append(genre)

        stars = []
        for star_name in movie_data.stars:
            star = db.query(Star).filter_by(name=star_name).first()
            if not star:
                star = Star(name=star_name)
                db.add(star)
                db.flush()
            stars.append(star)

        directors = []
        for director_name in movie_data.directors:
            director = db.query(Director).filter_by(name=director_name).first()
            if not director:
                director = Director(name=director_name)
                db.add(director)
                db.flush()
            directors.append(director)

        movie = Movie(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            price=movie_data.price,
            description=movie_data.description,
            certification_id=certification.id,
            genres=genres,
            stars=stars,
            directors=directors,
        )
        db.add(movie)
        db.commit()
        db.refresh(movie)

        return MovieDetailSchema.model_validate(movie)
    except HTTPException:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.patch(
    "/movies/{movie_id}/",
    summary="Update a movie by ID",
    description=(
        "<h3>Update details of a specific movie by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing movie. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
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
def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: Session = Depends(get_db),
):
    """
    Update a specific movie by its ID.

    This function updates a movie identified by its unique ID.
    If the movie does not exist, a 404 error is raised.

    :param movie_id: The unique identifier of the movie to update.
    :type movie_id: int
    :param movie_data: The updated data for the movie.
    :type movie_data: MovieUpdateSchema
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: Session

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.

    :return: A response indicating the successful update of the movie.
    :rtype: None
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    try:
        db.commit()
        db.refresh(movie)
    except HTTPException:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
    else:
        return {"detail": "Movie updated successfully."}


@router.delete(
    "/movies/{movie_id}/",
    summary="Delete a movie by ID",
    description=(
        "<h3>Delete a specific movie from the database by its unique ID.</h3>"
        "<p>If the movie exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
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
):
    """
    Delete a specific movie by its ID.

    This function deletes a movie identified by its unique ID.
    If the movie does not exist, a 404 error is raised.

    :param movie_id: The unique identifier of the movie to delete.
    :type movie_id: int
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: Session

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.

    :return: A response indicating the successful deletion of the movie.
    :rtype: None
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    db.delete(movie)
    db.commit()
    return {"detail": "Movie deleted successfully."}


@router.post("/stars/")
def create_star(
        stars_data: StarsSchema,
        db: Session = Depends(get_db),
):
    star = db.query(Star).filter_by(name=stars_data.name).first()
    if star:
        raise HTTPException(
            status_code=400,
            detail="Star already exists.",
        )

    star = Star(name=stars_data.name)
    db.add(star)
    db.commit()
    db.refresh(star)

    return StarsResponseSchema.model_validate(star)


@router.get("/stars/", response_model=list[StarsResponseSchema])
def star_list(
        db: Session = Depends(get_db),
):
    return db.query(Star).all()


@router.patch("/stars/{star_id}/")
def star_update(
        star_id: int,
        star_data: StarsSchema,
        db: Session = Depends(get_db),
):
    star = db.query(Star).filter_by(id=star_id).first()

    if not star:
        raise HTTPException(
            status_code=404,
            detail="Star with the given ID was not found."
        )

    if star_data.name:
        star.name = star_data.name

    return StarsResponseSchema.model_validate(star)


@router.delete("/stars/{star_id}/")
def star_delete(
        star_id: int,
        db: Session = Depends(get_db),
):
    star = db.query(Star).filter_by(id=star_id).first()

    if not star:
        raise HTTPException(
            status_code=404,
            detail="Star with the given ID was not found."
        )

    db.delete(star)
    db.commit()
    return {"detail": "Star deleted successfully."}


# ====================================================


@router.post("/genres/")
def create_genre(
        genres_data: GenresSchema,
        db: Session = Depends(get_db),
):
    genre = db.query(Genre).filter_by(name=genres_data.name).first()
    if genre:
        raise HTTPException(
            status_code=400,
            detail="Genre already exists.",
        )

    genre = Genre(name=genres_data.name)
    db.add(genre)
    db.commit()
    db.refresh(genre)

    return GenreResponseSchema.model_validate(genre)


@router.get("/genres/", response_model=list[GenreResponseSchema])
def genre_list(
        db: Session = Depends(get_db),
):
    return db.query(Genre).all()


@router.get("/genres/{genre_id}/")
def genre_detail(
        genre_id: int,
        db: Session = Depends(get_db),
):
    genre = db.query(Genre).filter_by(id=genre_id).first()

    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre with the given ID was not found."
        )

    return GenreResponseSchema.model_validate(genre)


@router.patch("/genres/{genre_id}/")
def genre_update(
        genre_id: int,
        genre_data: GenresSchema,
        db: Session = Depends(get_db),
):
    genre = db.query(Genre).filter_by(id=genre_id).first()

    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre with the given ID was not found."
        )

    if genre_data.name:
        genre.name = genre_data.name

    return GenreResponseSchema.model_validate(genre)


@router.delete("/genres/{genre_id}/")
def genre_delete(
        genre_id: int,
        db: Session = Depends(get_db),
):
    genre = db.query(Genre).filter_by(id=genre_id).first()

    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre with the given ID was not found."
        )

    db.delete(genre)
    db.commit()
    return {"detail": "Genre deleted successfully."}


@router.post("/{movie_id}/like/", response_model=MovieLikeResponseSchema)
def like_or_dislike(
        movie_id: int,
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db),
):
    movie = db.query(Movie).filter_by(id=movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )
    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]
    user = db.query(User).filter_by(id=user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    movie_like = db.query(MovieLike).filter_by(
        movie_id=movie.id, user_id=user.id
    ).first()

    if movie_like:
        movie_like.is_liked = not movie_like.is_liked
    else:
        movie_like = MovieLike(
            user_id=user_id,
            movie_id=movie_id,
            is_liked=True,
        )
        db.add(movie_like)

    db.commit()
    db.refresh(movie_like)

    return MovieLikeResponseSchema(
        is_liked=movie_like.is_liked,
        created_at=movie_like.created_at,
        user=movie_like.user,
        movie=movie_like.movie,
    )


@router.post("/{movie_id}/favorite/", response_model=MovieFavoriteResponseSchema)
def favorite_or_unfavorite(
        movie_id: int,
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
        db: Session = Depends(get_db),
):
    movie = db.query(Movie).filter_by(id=movie_id).first()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]
    user = db.query(User).filter_by(id=user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    movie_favorite = db.query(FavoriteMovie).filter_by(
        movie_id=movie.id, user_id=user.id
    ).first()

    if movie_favorite:
        movie_favorite.is_favorited = not movie_favorite.is_favorited

    else:
        movie_favorite = FavoriteMovie(
            user_id=user_id,
            movie_id=movie_id,
            is_favorited=True,
        )
        db.add(movie_favorite)

    db.commit()
    db.refresh(movie_favorite)

    return MovieFavoriteResponseSchema(
        is_favorited=movie_favorite.is_favorited,
        created_at=movie_favorite.created_at,
        user=movie_favorite.user,
        movie=movie_favorite.movie,
    )
