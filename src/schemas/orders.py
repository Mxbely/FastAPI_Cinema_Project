from datetime import datetime

from pydantic import BaseModel

from database.models.orders import OrderStatusEnum


""" Message... """
class MessageResponseSchema(BaseModel):
    message: str


""" 2. View User Orders """
class MovieItemResponse(BaseModel):  # ToDo Test delete in future because it must be from movies schemas
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class OrderItemResponseSchema(BaseModel):
    created_at: datetime
    movies: list[MovieItemResponse]  # ToDo from movies schemas will be...
    total_amount: float | None
    status: OrderStatusEnum

    model_config = {
        "from_attributes": True
    }
