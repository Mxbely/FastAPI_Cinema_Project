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


@router.post(
    "/orders/",
    response_model=MessageResponseSchema,
    summary="Place an Order",
    description=(
        "<h3>This endpoint allows users to place an order for the movies in their cart."
        "It generates a new order, creates a Stripe checkout session, "
        "and returns a success message along with the order ID.</h3>"
    ),
    responses={
        200: {
            "description": "Order placed successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Order placed successfully, your order_id: 123"
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized access.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {"detail": "Unexpected error occurred."}
                }
            },
        },
    },
)
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


@router.get(
    "/orders/",
    response_model=list[OrderItemResponseSchema],
    summary="View User Orders",
    description=(
        "<h3>This endpoint retrieves a list of orders placed by a user. "
        "Admins can filter orders by user ID, date range, and status, "
        "while regular users can only view their own orders.</h3>"
    ),
    responses={
        200: {
            "description": "List of orders retrieved successfully.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "created_at": "2023-01-01T12:00:00",
                            "movies": [
                                {
                                    "id": 1,
                                    "name": "Movie A",
                                    "year": 2022,
                                    "time": 120,
                                    "description": "A great movie.",
                                }
                            ],
                            "total_amount": 19.99,
                            "status": "completed",
                        }
                    ]
                }
            },
        },
        403: {
            "description": (
                "Forbidden. User does not have permission to view these orders."
            ),
            "content": {
                "application/json": {
                    "example": {"detail": "You don't have permission."}
                }
            },
        },
        404: {
            "description": "No orders found.",
            "content": {
                "application/json": {"example": {"detail": "No orders found."}}
            },
        },
    },
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


@router.get(
    "/orders/{order_id}/",
    response_model=OrderItemResponseSchema,
    summary="Detail View of an Order",
    description=(
        "<h3>This endpoint retrieves detailed information about a specific order. "
        "Admins can view any order, while regular users can only view their own orders."
        "</h3>"
    ),
    responses={
        200: {
            "description": "Order details retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "created_at": "2023-01-01T12:00:00",
                        "movies": [
                            {
                                "id": 1,
                                "name": "Movie A",
                                "year": 2022,
                                "time": 120,
                                "description": "A great movie.",
                            }
                        ],
                        "total_amount": 19.99,
                        "status": "completed",
                    }
                }
            },
        },
        403: {
            "description": (
                "Forbidden. User does not have permission to view this order."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You don't have permission to view this order."
                    }
                }
            },
        },
        404: {
            "description": "Order not found.",
            "content": {
                "application/json": {"example": {"detail": "Order not found."}}
            },
        },
    },
)
def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderItemResponseSchema:
    order = get_order_by_id(db, order_id, current_user.id)

    return format_order_detail(order)
