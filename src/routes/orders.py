from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db, Cart
from database.models.accounts import User
from database.models.orders import Order, OrderItem, OrderStatusEnum
from routes.profiles import get_current_user
from schemas.orders import OrderItemResponseSchema, MovieItemResponse, MessageResponseSchema

router = APIRouter()


@router.get("/")
def root() -> dict:
    return {"message": "Hello Test"}


# Зробити detail view, створення order, і також можна update і delete; додати пагінацію до list,
# Написати тести і свагер


"""
1. Place an Order
Endpoint: POST /orders/
Description: Allows users to place an order for movies in their cart.
"""
@router.post("/orders/")
def place_order(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")

    order = Order(
        user_id=current_user.id,
        total_amount=sum(item.movie.price for item in cart.items)
    )
    # order create
    db.add(order)
    db.commit()
    db.refresh(order)

    # order item create
    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            movie_id=cart_item.movie_id,
            price_at_order=cart_item.movie.price
        )
        db.add(order_item)
        db.delete(cart_item)

    db.commit()

    return MessageResponseSchema(
        message=f"Order placed successfully, your order_id: {order.id}"
    )


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
            movies=[
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
3. Detail view of order
Endpoint: GET /orders/{order_id}/
Description: Allows user to view details about order.
"""


"""
4. Update order  
Endpoint: PATCH /orders/{order_id}/
Description: Allows user to update order.
"""


"""
4. Delete order  
Endpoint: DELETE /orders/{order_id}/
Description: Allows user to delete order.
"""





















# """
# 3. Confirm an Order
# Endpoint: POST /orders/{order_id}/confirm/
# Description: Confirms an order and redirects the user to a payment gateway.
# """
# @router.post("/orders/{order_id}/confirm/", response_model=MessageResponseSchema, status_code=status.HTTP_200_OK)
# def confirm_order(order_id: int, db: Session = Depends(get_db)):
#     order = db.query(Order).filter(Order.id == order_id).first()
#     if not order:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
#
#     if order.status != OrderStatusEnum.PENDING.value:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only pending orders can be confirmed."
#         )
#
#     # ToDo - redirect to payment...
#
#     order.status = OrderStatusEnum.PAID.value
#     db.commit()
#     db.refresh(order)
#
#     return MessageResponseSchema(
#         message="Order successfully confirmed."
#     )
#
#
# """
# 4. Cancel an Order
# Endpoint: POST /orders/{order_id}/cancel/
# Description: Allows users to cancel an order before payment is completed.
# """
# @router.post("/orders/{order_id}/cancel/", response_model=MessageResponseSchema, status_code=status.HTTP_200_OK)
# def cancel_order(order_id: int, db: Session = Depends(get_db)):
#     order = db.query(Order).filter(Order.id == order_id).first()
#     if not order:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
#
#     if order.status != OrderStatusEnum.PENDING.value:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only pending orders can be canceled."
#         )
#
#     order.status = OrderStatusEnum.CANCELED.value
#     db.commit()
#     db.refresh(order)
#
#     return MessageResponseSchema(
#         message="Order successfully canceled."
#     )
#
#
# """
# 5. Request a Refund
# Endpoint: POST /orders/{order_id}/refund_request/
# Description: Allows users to request a refund for a paid order.
# """
# # @router.post("/orders/{order_id}/refund_request/", response_model=OrderRefundRequestSchema)
# # def request_refund(order_id: int, db: Session = Depends(get_db)):
# #     pass


# @router.post("/refund", status_code=status.HTTP_200_OK)
# def refund_order(
#         order_id: int,
#         db: Session = Depends(get_db),
#         token: str = Depends(get_token),
#         jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
# ):
#     try:
#         payload = jwt_manager.decode_access_token(token)
#         user_id = payload.get("user_id")
#     except BaseSecurityError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=str(e)
#         )
#
#     # Отримуємо замовлення та платіж
#     order = db.query(OrderModel).filter_by(id=order_id).first()
#     payment = db.query(PaymentModel).filter_by(order_id=order_id).first()
#
#     # Перевірка, чи належить це замовлення користувачу і чи не було воно вже повернене
#     if order.user_id != user_id or payment.status == "refunded":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Order is either not yours or has already been refunded."
#         )
#
#     # Перевірка статусу платежу через Stripe Checkout
#     try:
#         session = stripe.checkout.Session.retrieve(payment.external_payment_id)
#
#         # Якщо сесія не успішна, рефандити не можна
#         if session.payment_status != "paid":
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Only successful payments can be refunded."
#             )
#
#         # Отримуємо PaymentIntent з сесії Stripe
#         payment_intent_id = session.payment_intent
#
#         # Здійснюємо рефанд через Stripe API
#         stripe.Refund.create(payment_intent=payment_intent_id)
#
#         # Оновлюємо статус замовлення і платежу
#         order.status = "canceled"
#         payment.status = "refunded"
#
#         # Видаляємо покупку (якщо є)
#         movie_ids = [order_item.movie_id for order_item in order.order_items]
#         db.query(Purchases).filter(
#             and_(Purchases.movie_id.in_(movie_ids), Purchases.user_id == user_id)
#         ).delete()
#
#         db.commit()
#
#         return {"message": "Your order was refunded successfully."}
#
#     except stripe.error.StripeError as e:
#         handle_stripe_error(e)
#
#     except SQLAlchemyError:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Database error while processing the refund."
#         )









"""
---------- DEPRECATED ---------
6. View All Orders with Filters (only for moderator & admin)
Endpoint: GET /orders/
Description: Allows admins to view all user orders with filters for users, dates, and statuses.
"""
# @router.get("/orders/", response_model=list[OrderItemResponseSchema])
# def get_all_orders(data: AllOrdersAdminRequestSchema, db: Session = Depends(get_db)):
#     query = db.query(Order)
#     user_id, date_from, date_to, status_filter = data.user_id, data.date_from, data.date_to, data.status_filter
#
#     if user_id:
#         query = query.filter(Order.user_id == user_id)
#     if date_from:
#         query = query.filter(Order.created_at >= date_from)
#     if date_to:
#         query = query.filter(Order.created_at <= date_to)
#     if status_filter:
#         query = query.filter(Order.status == status_filter)
#
#     orders = query.order_by(Order.created_at.desc()).all()
#     if not orders:
#         raise HTTPException(status_code=404, detail="No orders found.")
#     return orders
