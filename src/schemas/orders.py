from datetime import datetime

from pydantic import BaseModel

from database.models.orders import OrderStatusEnum


""" Message... """
class MessageResponseSchema(BaseModel):
    message: str
#
#
# """ Cart schems (delete) """
# class CartItemDetail(BaseModel):
#     movie_id: int
#     title: str
#     price: float
#     genre: str | None
#     release_year: int
#
#
# class CartResponse(BaseModel):
#     user_id: int
#     movies: list[CartItemDetail]
#
#
# class PlaceOrderRequestSchema(BaseModel):
#     ...


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


# class AllOrdersRequestSchema(BaseModel):
#     user_id: int
#
#
# class AllOrdersUserRequestSchema(AllOrdersRequestSchema):
#     pass
#
#
# class AllOrdersAdminRequestSchema(AllOrdersRequestSchema):
#     date_from: datetime
#     date_to: datetime
#     status_filter: OrderStatusEnum
#
#     model_config = {
#         "from_attributes": True
#     }