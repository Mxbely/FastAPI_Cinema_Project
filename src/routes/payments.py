from datetime import datetime
from typing import Annotated, Optional

import stripe
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
    BackgroundTasks
)
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.links import Page
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager, get_accounts_email_notificator, get_settings
from database import Order, Payment, PaymentStatusEnum, UserGroupEnum, get_db, User
from database.crud import get_payment_by_session_id, update_payment_status
from database.models.orders import OrderStatusEnum
from exceptions import handle_stripe_error
from notifications import EmailSenderInterface
from schemas import PaymentHistoryResponse
from schemas.accounts import MessageResponseSchema
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from utils import retrieve_user_from_token

router = APIRouter()


@router.get(
    "/",
    response_model=Page[PaymentHistoryResponse],
    summary="Read Payments",
    description="Retrieve a paginated list of payments. "
                "Admins can filter by user ID, start date, end date, and payment "
                "status. Non-admin users can only view their own payments.",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "order_id": 1,
                                "amount": 100.0,
                                "status": "PENDING",
                                "created_at": "2023-01-01T00:00:00",
                                "updated_at": "2023-01-01T00:00:00"
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "size": 50
                    }
                }
            }
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
    },
)
def read_payments(
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> Page[PaymentHistoryResponse] | MessageResponseSchema:
    user = retrieve_user_from_token(db, token, jwt_manager)

    query = db.query(Payment)

    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    if payment_status:
        query = query.filter_by(status=payment_status)

    if user.group.name != UserGroupEnum.ADMIN.value:
        return paginate(query.filter_by(user_id=user.id))

    return paginate(query)


@router.get(
    "/success",
    response_model=MessageResponseSchema,
    summary="Payment Success",
    description="Handles the success of a payment session. "
                "Verifies the session ID and updates the "
                "payment and order status accordingly.",
    responses={
        200: {
            "description": "Payment was successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Payment with session_id {session_id}"
                                   " was successful."
                    }
                }
            }
        },
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
    },
)
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

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if not session or session.payment_status != "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment was not successful."
            )
        update_payment_status(payment, PaymentStatusEnum.SUCCESSFUL, db)

        order = db.query(Order).filter_by(id=payment.order_id).first()

        if order:
            order.status = OrderStatusEnum.PAID
            db.commit()
        return MessageResponseSchema(message=f"Payment {session_id} was successful.")
    except stripe.StripeError as e:
        handle_stripe_error(e)


@router.get(
    "/cancel",
    summary="Cancel Payment",
    description="Cancels a payment session by its session ID. "
                "Updates the payment and order status accordingly.",
    responses={
        200: {
            "description": "Payment was cancelled successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Payment with session_id {session_id} was cancelled."
                    }
                }
            }
        },
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
    }
)
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
    except stripe.StripeError as e:
        handle_stripe_error(e)

    update_payment_status(payment, PaymentStatusEnum.CANCELLED, db)

    order = db.query(Order).filter_by(id=payment.order_id).first()
    if order:
        order.status = OrderStatusEnum.CANCELED
        db.commit()

    return MessageResponseSchema(
        message=f"Payment with session_id {session_id} was cancelled."
    )


@router.post(
    "/refund",
    response_model=MessageResponseSchema,
    summary="Refund Payment",
    description="Refunds a payment for a given order ID. "
                "Updates the payment and order status accordingly.",
    responses={
        200: {
            "description": "Order was refunded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Order with id {order_id} was refunded successfully."
                    }
                }
            }
        },
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
    }
)
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
            detail="Order was already cancelled or"
                   " not paid, and cannot be refunded."
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
            payment_intent=str(session.payment_intent)
        )

        order.status = OrderStatusEnum.CANCELED
        payment.status = PaymentStatusEnum.REFUNDED
        db.commit()

        return MessageResponseSchema(
            message=f"Order with id {order_id} was refunded successfully."
        )
    except stripe.StripeError as e:
        handle_stripe_error(e)


@router.post(
    "/stripe-webhook",
    summary="Stripe Webhook",
    description="Handles Stripe webhook events, specifically "
                "the `checkout.session.completed` event. "
                "Verifies the session ID, and sends a success email.",
    responses={
        200: {
            "description": "Webhook handled successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Success"
                    }
                }
            }
        },
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
    }
)
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator)
) -> MessageResponseSchema:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Handling Stripe event
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, get_settings().STRIPE_WEBHOOK_SECRET
        )  # type: ignore
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )
    except stripe.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}"
        )

    # Handling "checkout.session.completed" event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")

        # Retrieving payment from the database
        payment = get_payment_by_session_id(session_id, db)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found."
            )

        # Generating order link and retrieving user's email
        order_link = request.url_for("get_order_detail", order_id=payment.order_id)
        user = db.query(User).filter_by(id=payment.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Sending email in the background
        background_tasks.add_task(
            email_sender.send_payment_success_email,
            str(user.email),
            str(order_link)
        )

    return MessageResponseSchema(message="Success")
