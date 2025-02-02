from pydantic import BaseModel
from typing import List


class CartCreate(BaseModel):
    movie_id: int


class CartItemResponse(BaseModel):
    message: str


class CartItemDetail(BaseModel):
    movie_id: int
    title: str
    price: float
    genre: str
    release_year: int


class CartResponse(BaseModel):
    user_id: int
    movies: List[CartItemDetail]
