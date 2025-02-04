from datetime import datetime

from fastapi import APIRouter, Request, Depends, status, Query
from sqlalchemy.orm import Session

from database import get_db
from database.crud.orders import (
    create_order,
    update_order_with_stripe_url,
    get_user_orders,
    format_order_detail,
    get_order_by_id,
)
from database.models.accounts import User
from database.models.orders import OrderStatusEnum
from routes.profiles import get_current_user
from schemas.orders import OrderItemResponseSchema, MessageResponseSchema
from services import create_checkout_session

router = APIRouter()


"""
1. Place an Order
Endpoint: POST /orders/
Description: Allows users to place an order for movies in their cart.
"""
@router.post("/orders/")
def place_order(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponseSchema:
    order = create_order(user_id=current_user.id, db=db)

    stripe_url = create_checkout_session(
        request=request, order=order, user_id=current_user.id, db=db
    )
    update_order_with_stripe_url(order, stripe_url, db=db)

    return MessageResponseSchema(
        message=f"Order placed successfully, your order_id: {order.id}"
    )


"""
2. View User Orders (depending on whether it is an admin or a user...)
Endpoint: GET /orders/
Description: Retrieves a list of all orders placed by a specific user.
"""
@router.get(
    "/orders/",
    response_model=list[OrderItemResponseSchema],
    status_code=status.HTTP_200_OK,
)
def get_user_orders_route(
    user_id: int | None = Query(default=None, description="Filter orders by user ID"),
    date_from: datetime | None = Query(
        default=None, description="Filter orders from this date"
    ),
    date_to: datetime | None = Query(
        default=None, description="Filter orders until this date"
    ),
    order_status: OrderStatusEnum | None = Query(
        default=None, description="Filter orders by status"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderItemResponseSchema]:
    orders: list[OrderItemResponseSchema] = get_user_orders(
        current_user=current_user,
        db=db,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        order_status=order_status,
    )
    return orders


"""
3. Detail view of order
Endpoint: GET /orders/{order_id}/
Description: Allows user to view details about order.
"""
@router.get(
    "/orders/{order_id}/",
    response_model=OrderItemResponseSchema,
    status_code=status.HTTP_200_OK,
)
def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderItemResponseSchema:
    order = get_order_by_id(db, order_id, current_user.id)

    return format_order_detail(order)
