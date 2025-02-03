from datetime import datetime

from pydantic import BaseModel

from database.models.orders import OrderStatusEnum
from schemas.movies import MovieListItemSchema


class MessageResponseSchema(BaseModel):
    message: str


class OrderItemResponseSchema(BaseModel):
    created_at: datetime
    movies: list[MovieListItemSchema]
    total_amount: float | None
    status: OrderStatusEnum

    model_config = {"from_attributes": True}
