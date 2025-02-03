from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from database import Movie, Genre
from schemas.movies import MovieSortEnum


# from schemas.movies import MovieFilter


def get_movies_paginated(page: int, per_page: int,db: Session):
    offset = (page - 1) * per_page

    query = db.query(Movie).order_by()

    order_by = Movie.default_order_by()
    if order_by:
        query = query.order_by(*order_by)

    total_items = query.count()
    movies = query.offset(offset).limit(per_page).all()

    return total_items, movies

def check_if_exists(db: Session, query):
    return db.query(query).first() is not None


def filter_movies(db: Session, filters: dict, sort_by: Optional[MovieSortEnum] = None):
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