from datetime import datetime
from typing import Annotated, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.links import Page
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager
from database import Order, Payment, PaymentStatusEnum, UserGroupEnum, get_db
from database.crud import get_payment_by_session_id, update_payment_status
from database.models.orders import OrderStatusEnum
from exceptions import handle_stripe_error
from schemas import PaymentHistoryResponse
from schemas.accounts import MessageResponseSchema
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from utils import retrieve_user_from_token

router = APIRouter()


@router.get("/", response_model=Page[PaymentHistoryResponse])
def read_payments(
    request: Request,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> Page[PaymentHistoryResponse] | MessageResponseSchema:
    user = retrieve_user_from_token(db, token, jwt_manager)

    if user.group.name != UserGroupEnum.ADMIN.value:
        return paginate(db.query(Payment).filter_by(user_id=user.id))

    query = db.query(Payment)

    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    if payment_status:
        query = query.filter_by(status=payment_status)

    payments = query.all()

    if not payments:
        return MessageResponseSchema(
            message="No payments found."
        )

    return paginate(query)


@router.get("/success")
def payment_success(
    session_id: Annotated[str, Query(max_length=500)],
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> MessageResponseSchema:
    retrieve_user_from_token(db, token, jwt_manager)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No session_id provided."
        )

    payment = db.query(Payment).filter_by(external_payment_id=session_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with session_id {session_id} not found."
        )

    if payment.status == PaymentStatusEnum.SUCCESSFUL:
        return MessageResponseSchema(
            message=f"Payment with session_id {session_id} was successful."
        )

    session = None

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        handle_stripe_error(e)

    if session.payment_status == "paid":
        update_payment_status(
            payment,
            PaymentStatusEnum.SUCCESSFUL,
            db
        )

        order = db.query(Order).filter_by(id=payment.order_id).first()
        order.status = OrderStatusEnum.PAID
        db.commit()
        return MessageResponseSchema(
            message=f"Payment with session_id {session_id} was successful."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment was not successful."
        )


@router.get("/cancel")
def payment_cancel(
    session_id: Annotated[str, Query(max_length=500)],
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> MessageResponseSchema:
    retrieve_user_from_token(db, token, jwt_manager)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No session_id provided."
        )

    payment = get_payment_by_session_id(session_id, db)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with session_id {session_id} not found."
        )

    if (
        payment.status == PaymentStatusEnum.CANCELLED or
        payment.status == PaymentStatusEnum.SUCCESSFUL
    ):
        return MessageResponseSchema(
            message=f"Payment with session_id {session_id} "
                    f"was already cancelled or successful."
        )

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with id {session_id} not found."
            )

        stripe.checkout.Session.expire(session_id)
    except stripe.error.StripeError as e:
        handle_stripe_error(e)

    update_payment_status(payment, PaymentStatusEnum.CANCELLED, db)

    order = db.query(Order).filter_by(id=payment.order_id).first()
    order.status = OrderStatusEnum.CANCELED
    db.commit()

    return MessageResponseSchema(
        message=f"Payment with session_id {session_id} was cancelled."
    )


@router.post("/refund")
def payment_refund(
    order_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> MessageResponseSchema:
    user = retrieve_user_from_token(db, token, jwt_manager)

    order = db.query(Order).filter_by(id=order_id, user_id=user.id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.status != OrderStatusEnum.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order was already cancelled."
        )

    payment = db.query(Payment).filter_by(order_id=order_id).first()

    if not payment or not payment.external_payment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found."
        )

    try:
        session = stripe.checkout.Session.retrieve(
            payment.external_payment_id
        )

        stripe.Refund.create(
            payment_intent=session.payment_intent
        )

        order.status = OrderStatusEnum.CANCELED
        payment.status = PaymentStatusEnum.REFUNDED
        db.commit()

        return MessageResponseSchema(
            message=f"Order with id {order_id} was refunded successfully."
        )
    except stripe.error.StripeError as e:
        handle_stripe_error(e)
