from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from database.models.accounts import User
from database.models.orders import Order, OrderItem, OrderStatusEnum
from routes.profiles import get_current_user
from schemas.orders import OrderItemResponseSchema, MovieItemResponse, MessageResponseSchema

router = APIRouter()


@router.get("/")
def root() -> dict:
    return {"message": "Hello Test"}


"""
1. Place an Order
Endpoint: POST /orders/
Description: Allows users to place an order for movies in their cart.
"""
# @router.post("/orders/")
# def place_order(user_id: int, db: Session = Depends(get_db)):
#     pass


"""
2. View User Orders (depending on whether it is an admin or a user...)
Endpoint: GET /orders/
Description: Retrieves a list of all orders placed by a specific user.
"""
@router.get("/orders/", response_model=list[OrderItemResponseSchema], status_code=status.HTTP_200_OK)
def get_user_orders(
    user_id: int | None = Query(default=None, description="Filter orders by user ID"),
    date_from: datetime | None = Query(default=None, description="Filter orders from this date"),
    date_to: datetime | None = Query(default=None, description="Filter orders until this date"),
    order_status: OrderStatusEnum | None = Query(default=None, description="Filter orders by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.group.name != "user":
        filters = []
        if user_id:
            filters.append(Order.user_id == user_id)
        if date_from:
            filters.append(Order.created_at >= date_from)
        if date_to:
            filters.append(Order.created_at <= date_to)
        if order_status:
            filters.append(Order.status == order_status)
        orders = db.query(Order).filter(*filters)
    else:
        if user_id or date_from or date_to or order_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission."
            )
        orders = db.query(Order).filter(Order.user_id == current_user.id)

    orders = orders.options(joinedload(Order.order_items).joinedload(OrderItem.movie))
    orders = orders.order_by(Order.created_at.desc()).all()

    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No orders found.")

    order_list = [
        OrderItemResponseSchema(
            created_at=order.created_at,
            movies=[                                # ToDo - change it in future (can be N+1)
                MovieItemResponse(
                    id=item.movie.id, name=item.movie.name
                ) for item in order.order_items
            ],
            total_amount=order.total_amount,
            status=order.status
        )
        for order in orders
    ]

    return order_list


"""
3. Confirm an Order
Endpoint: POST /orders/{order_id}/confirm/
Description: Confirms an order and redirects the user to a payment gateway.
"""
@router.post("/orders/{order_id}/confirm/", response_model=MessageResponseSchema, status_code=status.HTTP_200_OK)
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.status != OrderStatusEnum.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be confirmed."
        )

    # ToDo - redirect to payment...

    order.status = OrderStatusEnum.PAID.value
    db.commit()
    db.refresh(order)

    return MessageResponseSchema(
        message="Order successfully confirmed."
    )


"""
4. Cancel an Order  
Endpoint: POST /orders/{order_id}/cancel/
Description: Allows users to cancel an order before payment is completed.
"""
@router.post("/orders/{order_id}/cancel/", response_model=MessageResponseSchema, status_code=status.HTTP_200_OK)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    if order.status != OrderStatusEnum.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be canceled."
        )

    order.status = OrderStatusEnum.CANCELED.value
    db.commit()
    db.refresh(order)

    return MessageResponseSchema(
        message="Order successfully canceled."
    )


"""
5. Request a Refund
Endpoint: POST /orders/{order_id}/refund_request/
Description: Allows users to request a refund for a paid order.
"""
# @router.post("/orders/{order_id}/refund_request/", response_model=OrderRefundRequestSchema)
# def request_refund(order_id: int, db: Session = Depends(get_db)):
#     pass
