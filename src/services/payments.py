from typing import List, Optional

import stripe
from fastapi import Request
from sqlalchemy.orm import Session

from config import get_settings
from database import Order, Payment, PaymentStatusEnum
from database.crud import create_payment, create_payment_items
from exceptions import handle_stripe_error
from schemas import StripePaymentMethod, PaymentCreateSchema

stripe.api_key = get_settings().STRIPE_SECRET_KEY


def create_checkout_session(
    request: Request,
    order: Order,
    user_id: int,
    db: Session,
    payment_methods: Optional[List[StripePaymentMethod]] = None,
) -> Optional[str]:
    """
    Creates a Stripe checkout session for a given order.

    Args:
        request (Request): The FastAPI request object.
        order (Order): The order object containing order details.
        user_id (int): The ID of the user making the payment.
        db (Session): The SQLAlchemy database session.
        payment_methods (List[StripePaymentMethod], optional): The list of
            payment methods to be accepted. Defaults to None.
    Returns:
        str | None: The URL of the created Stripe checkout
        session, or None if the session couldn't be created.
    """
    existing_payment = db.query(Payment).filter_by(
        order_id=order.id, status=PaymentStatusEnum.PENDING.value
    ).first()

    session = None
    if existing_payment:
        try:
            if hasattr(existing_payment, "external_payment_id"):
                stripe_external_id = existing_payment.external_payment_id
                session = stripe.checkout.Session.retrieve(
                    str(stripe_external_id)
                )
        except stripe.StripeError as e:
            handle_stripe_error(e)

    if session:
        return session.url

    total_amount = order.total_amount

    if not total_amount:
        raise ValueError("Order total amount is invalid")

    if not order.order_items:
        raise ValueError("Order has no items")

    product_data = " ".join(
        [
            f"|{item.movie.name} x {item.price_at_order}| "
            for item in order.order_items
        ]
    )

    success_url = str(
        request.url_for("payment_success")
    ) + "?session_id={CHECKOUT_SESSION_ID}"

    cancel_url = str(
        request.url_for("payment_cancel")
    ) + "?session_id={CHECKOUT_SESSION_ID}"

    try:
        if not payment_methods:
            payment_method_types = (
                [method.value for method in payment_methods]
                if payment_methods else ["card"]
            )

        session = stripe.checkout.Session.create(
            payment_method_types=payment_method_types,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": product_data,
                        },
                        "unit_amount": int(total_amount * 100),
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        new_payment = PaymentCreateSchema(
            user_id=user_id,
            order_id=order.id,
            amount=total_amount,
            external_payment_id=session.id
        )

        created_payment = create_payment(new_payment, db)

        if created_payment:
            create_payment_items(created_payment, order, db)
            return session.url

        return None
    except stripe.StripeError as e:
        handle_stripe_error(e)
        return None
