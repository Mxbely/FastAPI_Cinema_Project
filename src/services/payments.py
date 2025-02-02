import stripe
from fastapi import Request
from sqlalchemy.orm import Session

from config import get_settings
from database import Order
from database.crud import create_payment, create_payment_items
from exceptions import handle_stripe_error
from schemas.payments import PaymentCreateSchema

stripe.api_key = get_settings().STRIPE_SECRET_KEY


def create_checkout_session(
    request: Request,
    order: Order,
    user_id: int,
    db: Session
):
    total_amount = order.total_amount

    product_data = " ".join(
        [
            f"{item.movie.name} x {item.price_at_order}" for item in order.order_items
        ]
    )

    success_url = str(
        request.url_for("payment_success")
    ) + "?session_id={CHECKOUT_SESSION_ID}"

    cancel_url = str(
        request.url_for("payment_cancel")
    ) + "?session_id={CHECKOUT_SESSION_ID}"

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
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

        payment = PaymentCreateSchema(
            user_id=user_id,
            order_id=order.id,
            amount=total_amount,
            external_payment_id=session.id
        )

        payment = create_payment(payment, db)
        create_payment_items(payment, order, db)

        return session.url
    except stripe.error.StripeError as e:
        handle_stripe_error(e)
