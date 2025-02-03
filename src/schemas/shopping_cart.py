from typing import List, Optional

from pydantic import BaseModel


class CartCreate(BaseModel):
    movie_id: int


class CartItemResponse(BaseModel):
    message: str


class CartItemDetail(BaseModel):
    movie_id: int
    title: str
    price: float
    genre: Optional[str]
    release_year: int


class CartResponse(BaseModel):
    user_id: int
    movies: List[CartItemDetail]


class PurchasedMoviesResponse(BaseModel):
    purchased_movies: List[str]
