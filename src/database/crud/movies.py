from typing import List

from sqlalchemy.orm import Session
from database import Movie, Genre
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

# def filter_movies(db: Session, movies_filter: MovieFilter):
#     query = db.query(Movie)
#
#     if movies_filter.name:
#         query = query.filter(Movie.name.ilike(f"%{movies_filter.name}%"))
#
#     if movies_filter.year:
#         query = query.filter(Movie.year == movies_filter.year)
#
#     if movies_filter.min_imdb:
#         query = query.filter(Movie.imdb >= movies_filter.min_imdb)
#
#     if movies_filter.max_imdb:
#         query = query.filter(Movie.imdb <= movies_filter.max_imdb)
#
#     if movies_filter.min_votes:
#         query = query.filter(Movie.votes >= movies_filter.min_votes)
#
#     if movies_filter.max_votes:
#         query = query.filter(Movie.votes <= movies_filter.max_votes)
#
#     if movies_filter.genre:
#         query = query.join(Movie.genres).filter(Genre.name.ilike(f"%{movies_filter.genre}%"))
#
#     return query.all()