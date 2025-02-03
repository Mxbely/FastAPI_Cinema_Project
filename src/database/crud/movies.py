from typing import Optional, List, Type

from sqlalchemy.orm import Session, joinedload

from database import Certification, Director, Genre, Movie, Star, User
from database.models.movies import FavoriteMovie, MovieLike
from schemas.movies import GenresSchema, MovieCreateSchema, MovieSortEnum, StarsSchema


def get_movies_paginated(page: int, per_page: int,db: Session) -> [int, list[Movie]]:
    offset = (page - 1) * per_page

    query = db.query(Movie).order_by()

    order_by = Movie.default_order_by()
    if order_by:
        query = query.order_by(*order_by)

    total_items = query.count()
    movies = query.offset(offset).limit(per_page).all()

    return total_items, movies


def filter_movies(db: Session, filters: dict[str, str], sort_by: Optional[MovieSortEnum] = None) -> list[Movie]:
    query = db.query(Movie)

    if filters.get("name"):
        query = query.filter(Movie.name.ilike(f"%{filters['name']}%"))
    if filters.get("year"):
        query = query.filter(Movie.year == filters["year"])
    if filters.get("min_imdb"):
        query = query.filter(Movie.imdb >= filters["min_imdb"])
    if filters.get("max_imdb"):
        query = query.filter(Movie.imdb <= filters["max_imdb"])
    if filters.get("min_votes"):
        query = query.filter(Movie.votes >= filters["min_votes"])
    if filters.get("max_votes"):
        query = query.filter(Movie.votes <= filters["max_votes"])
    if filters.get("min_price"):
        query = query.filter(Movie.price >= filters["min_price"])
    if filters.get("max_price"):
        query = query.filter(Movie.price <= filters["max_price"])

    if sort_by:
        if sort_by == MovieSortEnum.PRICE_ASC:
            query = query.order_by(Movie.price)
        elif sort_by == MovieSortEnum.PRICE_DESC:
            query = query.order_by(Movie.price.desc())
        elif sort_by == MovieSortEnum.RELEASE_YEAR_ASC:
            query = query.order_by(Movie.year)
        elif sort_by == MovieSortEnum.RELEASE_YEAR_DESC:
            query = query.order_by(Movie.year.desc())
        elif sort_by == MovieSortEnum.VOTES_ASC:
            query = query.order_by(Movie.votes)
        elif sort_by == MovieSortEnum.VOTES_DESC:
            query = query.order_by(Movie.votes.desc())
        elif sort_by == MovieSortEnum.IMDb_ASC:
            query = query.order_by(Movie.imdb)
        elif sort_by == MovieSortEnum.IMDb_DESC:
            query = query.order_by(Movie.imdb.desc())

    return query.all()

def get_detail_movies_by_id(db: Session, movie_id: int) -> Movie | None:
    return (
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

def get_movie_by_id(db: Session, movie_id: int) -> Movie | None:
    return db.query(Movie).filter(Movie.id == movie_id).first()


def get_movie_by_name(db: Session, movie_data: MovieCreateSchema) -> Movie | None:
    return (
        db.query(Movie).filter(
            Movie.name == movie_data.name
        ).first()
    )

def get_certification_by_name(db: Session, movie_data: MovieCreateSchema) -> Certification | None:
    return db.query(Certification).filter_by(name=movie_data.certification).first()

def get_or_create_certification(db: Session, movie_data: MovieCreateSchema) -> Certification:
    certification = get_certification_by_name(db, movie_data)
    if not certification:
        certification = Certification(name=movie_data.certification)
        db.add(certification)
        db.commit()
        db.refresh(certification)

    return certification

def get_genre_by_id(db: Session, genre_id: int) -> Genre | None:
    return db.query(Genre).filter_by(id=genre_id).first()

def get_genre_by_name(db: Session, genres_data: GenresSchema) -> Genre | None:
    return db.query(Genre).filter_by(name=genres_data.name).first()

def get_all_genres(db: Session) -> list[Genre]:
    return db.query(Genre).all()

def get_or_create_genres(db: Session, movie_data: MovieCreateSchema) -> list[Genre | Type[Genre]]:
    genres = []

    for genre_name in movie_data.genres:
        genre = db.query(Genre).filter_by(name=genre_name).first()
        if not genre:
            genre = Genre(name=genre_name)
            db.add(genre)
            db.flush()
        genres.append(genre)

    return genres

def get_star_by_name(db:Session, stars_data: StarsSchema) -> Star | None:
    return db.query(Star).filter_by(name=stars_data.name).first()

def get_star_by_id(db: Session, star_id: int) -> Star | None:
    return db.query(Star).filter_by(id=star_id).first()

def get_all_stars(db: Session) -> list[Star]:
    return db.query(Star).all()

def get_or_create_stars(db: Session, movie_data: MovieCreateSchema) -> list[Star | Type[Star]]:
    stars = []

    for star_name in movie_data.stars:
        star = db.query(Star).filter_by(name=star_name).first()
        if not star:
            star = Star(name=star_name)
            db.add(star)
            db.flush()
        stars.append(star)

    return stars

def get_or_create_directors(db: Session, movie_data: MovieCreateSchema) -> list[Director | Type[Director]]:
    directors = []

    for director_name in movie_data.directors:
        director = db.query(Director).filter_by(name=director_name).first()
        if not director:
            director = Director(name=director_name)
            db.add(director)
            db.flush()
        directors.append(director)

    return directors

def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter_by(id=user_id).first()

def get_liked_movie(db: Session, movie: Movie, user: User) -> MovieLike | None:
    return (
        db.query(MovieLike).filter_by(
            movie_id=movie.id, user_id=user.id
        ).first()
    )

def get_favourite_movie(db: Session, movie: Movie, user: User) -> FavoriteMovie | None:
    return (
        db.query(FavoriteMovie).filter_by(
            movie_id=movie.id, user_id=user.id
        ).first()
    )
