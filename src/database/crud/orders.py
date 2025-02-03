from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from database import Order, OrderItem, Cart, User
from schemas import OrderItemResponseSchema, MovieListItemSchema


def create_order(user_id: int, db: Session) -> Order:
    """Creates a new order for the current user."""
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty."
        )

    try:
        order = Order(
            user_id=user_id, total_amount=sum(item.movie.price for item in cart.items)
        )
        db.add(order)
        db.flush()

        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                movie_id=cart_item.movie_id,
                price_at_order=cart_item.movie.price,
            )
            db.add(order_item)

        db.commit()
        db.refresh(order)
        return order
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


def update_order_with_stripe_url(order: Order, stripe_url: str, db: Session) -> None:
    """Updates the order with a Stripe URL."""
    try:
        order.stripe_url = stripe_url
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order with Stripe URL: {str(e)}"
        )


def get_user_orders(
    current_user: User,
    db: Session,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    order_status: str | None = None,
) -> list[OrderItemResponseSchema]:
    """Retrieves orders for a specific user or all users for admin."""
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
        orders_query = db.query(Order).filter(*filters)
    else:
        if user_id or date_from or date_to or order_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission.",
            )
        orders_query = db.query(Order).filter(Order.user_id == current_user.id)
    orders = orders_query.options(
        joinedload(Order.order_items).joinedload(OrderItem.movie)
    )
    orders = orders.order_by(Order.created_at.desc()).all()
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No orders found."
        )
    order_list = [
        OrderItemResponseSchema(
            created_at=order.created_at,
            movies=[
                MovieListItemSchema(
                    id=item.movie.id,
                    name=item.movie.name,
                    year=item.movie.year,
                    time=item.movie.time,
                    description=item.movie.description,
                )
                for item in order.order_items
            ],
            total_amount=order.total_amount,
            status=order.status,
        )
        for order in orders
    ]

    return order_list
